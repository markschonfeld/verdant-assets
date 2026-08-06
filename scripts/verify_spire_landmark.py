#!/usr/bin/env python3
"""Verify and render the generated VERDANT spire landmark OBJ assets."""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "SourceMesh" / "props"
QA = ROOT / "qa" / "spire_landmark"

EXPECTED = {
    "VD_SpireBase": {"size": (360.0, 360.0, 110.0), "min_z": 0.0},
    "VD_Spire": {"size": (360.0, 360.0, 1200.0), "min_z": 0.0},
}

Vec3 = tuple[float, float, float]
Face = tuple[str, tuple[int, ...]]


@dataclass
class ObjMesh:
    vertices: list[Vec3]
    faces: list[Face]
    mtllib: str | None

COLORS = {
    "M_Spire_Concrete": (82, 78, 68),
    "M_Spire_PaintedSteel": (45, 72, 69),
    "M_Spire_BareMetal": (105, 113, 112),
    "M_Spire_ServicePanel": (126, 63, 28),
    "M_Spire_Fin": (55, 83, 77),
    "M_Spire_Fastener": (52, 54, 54),
}


def parse_obj(path: Path) -> ObjMesh:
    vertices: list[Vec3] = []
    faces: list[Face] = []
    material = ""
    mtllib = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if not parts:
            continue
        if parts[0] == "v":
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif parts[0] == "usemtl":
            material = parts[1]
        elif parts[0] == "mtllib":
            mtllib = parts[1]
        elif parts[0] == "f":
            faces.append((material, tuple(int(token.split("/")[0]) - 1 for token in parts[1:])))
    return ObjMesh(vertices, faces, mtllib)


def triangle_area(a, b, c) -> float:
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    cross = (ab[1] * ac[2] - ab[2] * ac[1],
             ab[2] * ac[0] - ab[0] * ac[2],
             ab[0] * ac[1] - ab[1] * ac[0])
    return 0.5 * math.sqrt(sum(v * v for v in cross))


def validate(name: str, data: ObjMesh) -> dict[str, object]:
    vertices = data.vertices
    faces = data.faces
    failures: list[str] = []
    if not vertices or not faces:
        failures.append("mesh is empty")
        return {"pass": False, "failures": failures}
    for material, face in faces:
        if not material:
            failures.append("face without material")
        if len(face) < 3 or any(i < 0 or i >= len(vertices) for i in face):
            failures.append("invalid face indices")
            continue
        for i in range(1, len(face) - 1):
            if triangle_area(vertices[face[0]], vertices[face[i]], vertices[face[i + 1]]) < 1e-5:
                failures.append("degenerate face")
                break

    edges = Counter()
    for _, face in faces:
        for i, a in enumerate(face):
            b = face[(i + 1) % len(face)]
            edges[tuple(sorted((a, b)))] += 1
    nonmanifold = sum(1 for count in edges.values() if count != 2)
    if nonmanifold:
        failures.append(f"{nonmanifold} boundary/non-manifold edges")

    mins = tuple(min(v[i] for v in vertices) for i in range(3))
    maxs = tuple(max(v[i] for v in vertices) for i in range(3))
    size = tuple(maxs[i] - mins[i] for i in range(3))
    expected = EXPECTED[name]
    if any(abs(size[i] - expected["size"][i]) > 0.01 for i in range(3)):
        failures.append(f"bounds size {size} != expected {expected['size']}")
    if abs(mins[2] - expected["min_z"]) > 0.01:
        failures.append(f"pivot plane min Z {mins[2]} != 0")
    if data.mtllib != "VD_Spire_Landmark.mtl":
        failures.append("unexpected or missing mtllib")

    return {
        "pass": not failures,
        "failures": failures,
        "vertices": len(vertices),
        "faces": len(faces),
        "triangles": sum(len(face) - 2 for _, face in faces),
        "bounds_cm": {"min": mins, "max": maxs, "size": size},
        "material_slots": sorted({material for material, _ in faces}),
        "edge_incidence": {"total": len(edges), "nonmanifold": nonmanifold},
    }


def render_preview(base: ObjMesh, spire: ObjMesh, output: Path) -> None:
    width, height = 1900, 1320
    image = Image.new("RGB", (width, height), (20, 24, 23))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    scale = 0.82
    origin_x, ground_y = 570, 1170

    assembled = []
    for data, z_offset in ((base, 0), (spire, 110)):
        verts = [(x, y, z + z_offset) for x, y, z in data.vertices]
        for material, face in data.faces:
            points = [verts[i] for i in face]
            assembled.append((sum(p[1] for p in points) / len(points), material, points))
    # Front elevation, looking along -Y. Painter order handles the authored solids well enough for QA.
    for _, material, points in sorted(assembled, reverse=True):
        poly = [(origin_x + p[0] * scale, ground_y - p[2] * scale) for p in points]
        draw.polygon(poly, fill=COLORS.get(material, (110, 110, 110)), outline=(155, 164, 157))

    # Ground and dimension bars.
    draw.line((110, ground_y, 1030, ground_y), fill=(202, 173, 91), width=3)
    dim_x = 920
    draw.line((dim_x, ground_y, dim_x, ground_y - 1310 * scale), fill=(236, 198, 93), width=2)
    draw.line((dim_x - 12, ground_y, dim_x + 12, ground_y), fill=(236, 198, 93), width=2)
    draw.line((dim_x - 12, ground_y - 1310 * scale, dim_x + 12, ground_y - 1310 * scale), fill=(236, 198, 93), width=2)
    draw.text((dim_x + 18, ground_y - 660 * scale), "13.10 m assembly", fill=(247, 215, 120), font=font)

    # 1.80 m human reference keeps the landmark scale explicit in the handoff.
    human_x = 175
    human_top = ground_y - 180 * scale
    human_color = (211, 205, 184)
    draw.ellipse((human_x - 9, human_top, human_x + 9, human_top + 18), fill=human_color)
    draw.line((human_x, human_top + 18, human_x, ground_y - 52), fill=human_color, width=6)
    draw.line((human_x, human_top + 48, human_x - 22, human_top + 90), fill=human_color, width=4)
    draw.line((human_x, human_top + 48, human_x + 22, human_top + 90), fill=human_color, width=4)
    draw.line((human_x, ground_y - 52, human_x - 18, ground_y), fill=human_color, width=5)
    draw.line((human_x, ground_y - 52, human_x + 18, ground_y), fill=human_color, width=5)
    draw.text((human_x - 34, ground_y + 12), "1.80 m", fill=human_color, font=font)
    draw.text((110, 45), "VD SPIRE LANDMARK — FRONT ELEVATION / TOP PLAN", fill=(235, 225, 197), font=font)
    draw.text((110, 68), "Unreal centimetres, 1:1 · Z-up · bottom-centre pivots", fill=(164, 175, 166), font=font)

    # Base top plan at right.
    plan_cx, plan_cy, plan_scale = 1450, 400, 1.25
    plan_faces = []
    verts = base.vertices
    for material, face in base.faces:
        points = [verts[i] for i in face]
        plan_faces.append((sum(p[2] for p in points) / len(points), material, points))
    for _, material, points in sorted(plan_faces):
        poly = [(plan_cx + p[0] * plan_scale, plan_cy + p[1] * plan_scale) for p in points]
        draw.polygon(poly, fill=COLORS.get(material, (100, 100, 100)), outline=(155, 164, 157))
    draw.text((1270, 650), "3.60 m base footprint", fill=(247, 215, 120), font=font)

    # Legend / import lock.
    y = 790
    draw.text((1200, y), "MATERIAL SLOTS", fill=(235, 225, 197), font=font)
    for material, color in COLORS.items():
        y += 35
        draw.rectangle((1200, y, 1230, y + 18), fill=color, outline=(170, 170, 160))
        draw.text((1245, y + 2), material, fill=(190, 199, 190), font=font)
    y += 55
    for line in ("Spire: 12.00 m high / 3.60 m instrument span",
                 "Base: 1.10 m high / 3.60 m footprint",
                 "Opaque geometry: Nanite ON",
                 "Recommended: base simple collision; mast NoCollision"):
        draw.text((1200, y), line, fill=(190, 199, 190), font=font)
        y += 27

    image.save(output)


def main() -> None:
    QA.mkdir(parents=True, exist_ok=True)
    meshes = {name: parse_obj(SOURCE / f"{name}.obj") for name in EXPECTED}
    results = {name: validate(name, data) for name, data in meshes.items()}
    report = {
        "all_pass": all(result["pass"] for result in results.values()),
        "assembly_height_cm": 1310.0,
        "checks": results,
    }
    (QA / "spire_landmark_verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    render_preview(meshes["VD_SpireBase"], meshes["VD_Spire"], QA / "spire_landmark_preview.png")
    print(json.dumps(report, indent=2))
    if not report["all_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

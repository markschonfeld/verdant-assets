#!/usr/bin/env python3
"""Verify and render the generated VERDANT exhaust-stack landmark OBJ assets."""

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
    "VD_SpireBase": {"size": (2400.0, 2400.0, 1200.0), "min_z": 0.0},
    "VD_Spire": {"size": (2200.0, 2200.0, 18000.0), "min_z": 0.0},
    "VD_SpireLights": {"size": (1320.0, 1320.0, 11790.0), "min_z": 5980.0},
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
    "M_Spire_StackConcrete": (112, 104, 84),
    "M_Spire_PaintedSteel": (45, 72, 69),
    "M_Spire_BareMetal": (105, 113, 112),
    "M_Spire_ServicePanel": (126, 63, 28),
    "M_Spire_Fastener": (52, 54, 54),
    "M_Spire_Soot": (12, 12, 10),
    "M_Spire_WarningLens": (235, 42, 28),
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
        failures.append(f"geometry min Z {mins[2]} != expected {expected['min_z']}")
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


def render_preview(meshes: dict[str, ObjMesh], output: Path) -> None:
    width, height = 2200, 1400
    image = Image.new("RGB", (width, height), (20, 24, 23))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    def draw_elevation(origin_x: float, ground_y: float, scale: float,
                       z_max: float | None = None) -> None:
        assembled = []
        for data in meshes.values():
            for material, face in data.faces:
                points = [data.vertices[i] for i in face]
                if z_max is not None and max(p[2] for p in points) > z_max:
                    continue
                assembled.append((sum(p[1] for p in points) / len(points), material, points))
        for _, material, points in sorted(assembled, reverse=True):
            poly = [(origin_x + p[0] * scale, ground_y - p[2] * scale) for p in points]
            draw.polygon(poly, fill=COLORS.get(material, (110, 110, 110)),
                         outline=(155, 164, 157))

    # Full 180 m elevation establishes skyline silhouette and staged taper.
    full_x, ground_y, full_scale = 500, 1280, 0.065
    draw_elevation(full_x, ground_y, full_scale)
    draw.line((120, ground_y, 890, ground_y), fill=(202, 173, 91), width=3)
    dim_x = 850
    draw.line((dim_x, ground_y, dim_x, ground_y - 18000 * full_scale),
              fill=(236, 198, 93), width=2)
    draw.line((dim_x - 12, ground_y, dim_x + 12, ground_y), fill=(236, 198, 93), width=2)
    draw.line((dim_x - 12, ground_y - 18000 * full_scale,
               dim_x + 12, ground_y - 18000 * full_scale), fill=(236, 198, 93), width=2)
    draw.text((dim_x + 18, ground_y - 9000 * full_scale), "180 m total",
              fill=(247, 215, 120), font=font)
    draw.text((315, 1320), "FULL ELEVATION", fill=(235, 225, 197), font=font)

    # Lower 40 m inset exposes the human-scale detail invisible at the entrance sightline.
    inset_x, inset_ground, inset_scale = 1510, 1280, 0.25
    draw.rectangle((1030, 215, 2110, 1320), outline=(78, 91, 84), width=2)
    draw_elevation(inset_x, inset_ground, inset_scale, z_max=4200)
    draw.line((1080, inset_ground, 2050, inset_ground), fill=(202, 173, 91), width=3)
    draw.text((1080, 235), "LOWER 40 m DETAIL BAND", fill=(235, 225, 197), font=font)
    draw.text((1080, 258), "tram-approach priority: process ducts, doors, ladder, pods, platforms",
              fill=(164, 175, 166), font=font)

    # 1.80 m human reference in the enlarged inset.
    human_x = 1110
    human_top = inset_ground - 180 * inset_scale
    human_color = (211, 205, 184)
    draw.ellipse((human_x - 6, human_top, human_x + 6, human_top + 12), fill=human_color)
    draw.line((human_x, human_top + 12, human_x, inset_ground - 17), fill=human_color, width=4)
    draw.line((human_x, human_top + 22, human_x - 9, human_top + 35), fill=human_color, width=3)
    draw.line((human_x, human_top + 22, human_x + 9, human_top + 35), fill=human_color, width=3)
    draw.line((human_x, inset_ground - 17, human_x - 7, inset_ground), fill=human_color, width=3)
    draw.line((human_x, inset_ground - 17, human_x + 7, inset_ground), fill=human_color, width=3)
    draw.text((1080, inset_ground + 12), "1.80 m", fill=human_color, font=font)

    draw.text((110, 38), "VD EXHAUST STACK / SIGNAL-MAST ADAPTATION", fill=(235, 225, 197), font=font)
    draw.text((110, 62), "Unreal centimetres, 1:1 · Z-up · shared ground-centre origin",
              fill=(164, 175, 166), font=font)
    draw.text((110, 86), "24 m service base · 22 m max stack hardware span · separate warning-light mesh",
              fill=(164, 175, 166), font=font)

    # Compact material legend between the two elevation studies.
    y = 145
    x = 865
    draw.text((x, y), "MATERIAL SLOTS", fill=(235, 225, 197), font=font)
    for material, color in COLORS.items():
        y += 30
        draw.rectangle((x, y, x + 24, y + 15), fill=color, outline=(170, 170, 160))
        draw.text((x + 34, y + 1), material, fill=(190, 199, 190), font=font)

    image.save(output)


def main() -> None:
    QA.mkdir(parents=True, exist_ok=True)
    meshes = {name: parse_obj(SOURCE / f"{name}.obj") for name in EXPECTED}
    results = {name: validate(name, data) for name, data in meshes.items()}
    opaque_names = ("VD_SpireBase", "VD_Spire")
    lens_material = "M_Spire_WarningLens"
    separation_pass = (
        {material for material, _ in meshes["VD_SpireLights"].faces} == {lens_material}
        and all(lens_material not in {material for material, _ in meshes[name].faces}
                for name in opaque_names)
    )
    report = {
        "all_pass": all(result["pass"] for result in results.values()) and separation_pass,
        "assembly_height_cm": 18000.0,
        "warning_lens_separation": {
            "pass": separation_pass,
            "opaque_meshes": list(opaque_names),
            "non_nanite_mesh": "VD_SpireLights",
        },
        "checks": results,
    }
    (QA / "spire_landmark_verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    render_preview(meshes, QA / "spire_landmark_preview.png")
    print(json.dumps(report, indent=2))
    if not report["all_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

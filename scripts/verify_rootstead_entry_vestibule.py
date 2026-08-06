#!/usr/bin/env python3
"""Verify and render the Rootstead entry vestibule OBJ delivery."""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "SourceMesh" / "architecture"
QA = ROOT / "qa" / "rootstead_entry_vestibule"
EXPECTED = {
    "VD_RootsteadEntryVestibule_Frame": {
        "materials": {
            "M_Vestibule_PaintedSteel", "M_Vestibule_BareSteel",
            "M_Vestibule_RubberSeal", "M_Vestibule_Kickplate",
        },
        "closed": True,
    },
    "VD_RootsteadEntryVestibule_Glazing": {
        "materials": {"M_Vestibule_GlassAged", "M_Vestibule_GlassRepair"},
        "closed": False,
    },
}
COLORS = {
    "M_Vestibule_PaintedSteel": (36, 75, 70, 255),
    "M_Vestibule_BareSteel": (100, 108, 104, 255),
    "M_Vestibule_RubberSeal": (17, 21, 19, 255),
    "M_Vestibule_Kickplate": (61, 66, 58, 255),
    "M_Vestibule_GlassAged": (74, 119, 105, 105),
    "M_Vestibule_GlassRepair": (117, 166, 153, 82),
}

Vec3 = tuple[float, float, float]
Vec2 = tuple[float, float]
Face = tuple[str, tuple[int, ...], tuple[int, ...]]


@dataclass
class ObjMesh:
    name: str
    vertices: list[Vec3]
    texcoords: list[Vec2]
    faces: list[Face]
    mtllib: str | None
    object_names: list[str]
    group_count: int


def parse_obj(name: str) -> ObjMesh:
    path = SOURCE / f"{name}.obj"
    vertices: list[Vec3] = []
    texcoords: list[Vec2] = []
    faces: list[Face] = []
    material = ""
    mtllib = None
    object_names: list[str] = []
    group_count = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if not parts:
            continue
        if parts[0] == "v":
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif parts[0] == "vt":
            texcoords.append((float(parts[1]), float(parts[2])))
        elif parts[0] == "o":
            object_names.append(parts[1])
        elif parts[0] == "g":
            group_count += 1
        elif parts[0] == "mtllib":
            mtllib = parts[1]
        elif parts[0] == "usemtl":
            material = parts[1]
        elif parts[0] == "f":
            corners = [token.split("/") for token in parts[1:]]
            vertices_for_face = tuple(int(corner[0]) - 1 for corner in corners)
            uvs_for_face = tuple(
                int(corner[1]) - 1 if len(corner) > 1 and corner[1] else -1
                for corner in corners
            )
            faces.append((material, vertices_for_face, uvs_for_face))
    return ObjMesh(name, vertices, texcoords, faces, mtllib,
                   object_names, group_count)


def triangle_area(a: Vec3, b: Vec3, c: Vec3) -> float:
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    return 0.5 * math.sqrt(sum(value * value for value in cross))


def validate(mesh: ObjMesh) -> dict[str, object]:
    failures: list[str] = []
    if mesh.object_names != [mesh.name]:
        failures.append(f"expected one object named {mesh.name}, got {mesh.object_names}")
    if mesh.group_count:
        failures.append(f"OBJ contains {mesh.group_count} forbidden g group records")
    if mesh.mtllib != "VD_RootsteadEntryVestibule.mtl":
        failures.append(f"unexpected mtllib {mesh.mtllib}")
    if not mesh.vertices or not mesh.faces or not mesh.texcoords:
        failures.append("missing vertices, faces, or texture coordinates")

    uv_corner_count = 0
    edges: Counter[tuple[int, int]] = Counter()
    for material, face, uv_indices in mesh.faces:
        if material not in EXPECTED[mesh.name]["materials"]:
            failures.append(f"unexpected or missing material {material!r}")
        if len(face) < 3 or any(index < 0 or index >= len(mesh.vertices) for index in face):
            failures.append("invalid face vertex indices")
            continue
        if len(uv_indices) != len(face) or any(
            index < 0 or index >= len(mesh.texcoords) for index in uv_indices
        ):
            failures.append("face corner without a valid UV index")
        else:
            uv_corner_count += len(uv_indices)
        for index in range(1, len(face) - 1):
            if triangle_area(mesh.vertices[face[0]], mesh.vertices[face[index]],
                             mesh.vertices[face[index + 1]]) < 1e-5:
                failures.append("degenerate face")
                break
        for index, vertex in enumerate(face):
            following = face[(index + 1) % len(face)]
            edge = (min(vertex, following), max(vertex, following))
            edges[edge] += 1

    non_two_face_edges = sum(count != 2 for count in edges.values())
    if EXPECTED[mesh.name]["closed"] and non_two_face_edges:
        failures.append(f"opaque frame has {non_two_face_edges} boundary/non-manifold edges")

    mins = tuple(min(point[axis] for point in mesh.vertices) for axis in range(3))
    maxs = tuple(max(point[axis] for point in mesh.vertices) for axis in range(3))
    if mins[0] < -0.01 or maxs[0] > 375.0 or mins[1] < -975.0 or maxs[1] > 975.0:
        failures.append(f"mesh exceeds vestibule footprint envelope: min={mins}, max={maxs}")
    if mins[2] < -0.01 or maxs[2] > 915.0:
        failures.append(f"mesh exceeds vertical envelope: minZ={mins[2]}, maxZ={maxs[2]}")

    material_slots = {material for material, _, _ in mesh.faces}
    if material_slots != EXPECTED[mesh.name]["materials"]:
        failures.append(
            f"material slots {sorted(material_slots)} != expected "
            f"{sorted(EXPECTED[mesh.name]['materials'])}"
        )

    return {
        "pass": not failures,
        "failures": failures,
        "vertices": len(mesh.vertices),
        "texture_coordinates": len(mesh.texcoords),
        "faces": len(mesh.faces),
        "triangles": sum(len(face) - 2 for _, face, _ in mesh.faces),
        "uv_indexed_face_corners": uv_corner_count,
        "object_names": mesh.object_names,
        "group_records": mesh.group_count,
        "bounds_cm": {"min": mins, "max": maxs,
                      "size": tuple(maxs[i] - mins[i] for i in range(3))},
        "material_slots": sorted(material_slots),
        "edge_incidence": {"total": len(edges), "non_two_face": non_two_face_edges},
    }


def validate_walkthrough(meshes: dict[str, ObjMesh]) -> dict[str, object]:
    intrusions: list[dict[str, object]] = []
    for mesh in meshes.values():
        for face_index, (_, face, _) in enumerate(mesh.faces):
            points = [mesh.vertices[index] for index in face]
            # The east face must remain empty inside +/-460 Y and below Z=520.
            if (min(point[0] for point in points) >= 339.0
                    and max(point[1] for point in points) > -460.0
                    and min(point[1] for point in points) < 460.0
                    and max(point[2] for point in points) > 0.0
                    and min(point[2] for point in points) < 520.0):
                intrusions.append({"mesh": mesh.name, "face": face_index})
    return {
        "pass": not intrusions,
        "clear_width_cm": 920.0,
        "clear_height_cm": 520.0,
        "intrusions": intrusions,
    }


def normalize(vector: Vec3) -> Vec3:
    length = math.sqrt(sum(value * value for value in vector))
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def dot(a: Vec3, b: Vec3) -> float:
    return sum(a[index] * b[index] for index in range(3))


def render_view(image: Image.Image, meshes: dict[str, ObjMesh], box: tuple[int, int, int, int],
                camera: Vec3, target: Vec3, label: str) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    view = normalize((camera[0] - target[0], camera[1] - target[1],
                      camera[2] - target[2]))
    right = normalize(cross((0.0, 0.0, 1.0), view))
    up = cross(view, right)

    def project(point: Vec3) -> tuple[float, float, float]:
        relative = (point[0] - target[0], point[1] - target[1],
                    point[2] - target[2])
        return dot(relative, right), dot(relative, up), dot(relative, view)

    all_points = [project(point) for mesh in meshes.values() for point in mesh.vertices]
    min_x, max_x = min(p[0] for p in all_points), max(p[0] for p in all_points)
    min_y, max_y = min(p[1] for p in all_points), max(p[1] for p in all_points)
    x0, y0, x1, y1 = box
    padding = 55
    scale = min((x1 - x0 - 2 * padding) / (max_x - min_x),
                (y1 - y0 - 2 * padding) / (max_y - min_y))
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    screen_center = ((x0 + x1) / 2, (y0 + y1) / 2 + 15)

    polygons = []
    for mesh in meshes.values():
        for material, face, _ in mesh.faces:
            projected = [project(mesh.vertices[index]) for index in face]
            screen = [
                (screen_center[0] + (point[0] - center_x) * scale,
                 screen_center[1] - (point[1] - center_y) * scale)
                for point in projected
            ]
            polygons.append((sum(point[2] for point in projected) / len(projected),
                             material, screen))
    for _, material, polygon in sorted(polygons):
        color = COLORS[material]
        outline = (150, 164, 154, 190) if "Glass" in material else (178, 180, 164, 255)
        draw.polygon(polygon, fill=color, outline=outline)

    draw.rectangle(box, outline=(75, 88, 81, 255), width=2)
    draw.text((x0 + 18, y0 + 16), label, fill=(233, 225, 201, 255),
              font=ImageFont.load_default())


def render_preview(meshes: dict[str, ObjMesh], output: Path) -> None:
    image = Image.new("RGBA", (2200, 1350), (20, 24, 23, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default()
    draw.text((70, 35), "ROOTSTEAD WEST ENTRY / GLAZED STEEL VESTIBULE",
              fill=(237, 226, 197, 255), font=font)
    draw.text((70, 60), "1 uu = 1 cm · +X east · shared back-bottom-centre origin · frame/glazing split",
              fill=(157, 174, 164, 255), font=font)

    render_view(image, meshes, (55, 105, 1385, 930),
                (1500, -2300, 1300), (180, 0, 430), "EAST-SOUTHEAST HERO VIEW")
    render_view(image, meshes, (1420, 105, 2145, 650),
                (1600, 0, 430), (180, 0, 430), "EAST / WALK-THROUGH ELEVATION")
    render_view(image, meshes, (1420, 685, 2145, 1285),
                (180, -1800, 430), (180, 0, 430), "SOUTH SIDE / 3.6 m PROJECTION")

    # Dimension/intent callouts beneath the hero panel.
    notes = [
        "19.44 m overall wall-shoe envelope; 18.4 m internal trellis clearance",
        "8.1 m clear eave; 9.0 m ridge; 9.2 x 5.2 m unobstructed entry",
        "aged original panes + selective laminated repairs; bolted wall shoes and gutters",
        "Place both meshes at world (128, 0, 3500); Nanite OFF on glazing",
    ]
    for index, note in enumerate(notes):
        draw.text((80, 985 + index * 45), note, fill=(194, 202, 187, 255), font=font)
    image.convert("RGB").save(output)


def main() -> None:
    QA.mkdir(parents=True, exist_ok=True)
    meshes = {name: parse_obj(name) for name in EXPECTED}
    checks = {name: validate(mesh) for name, mesh in meshes.items()}
    walkthrough = validate_walkthrough(meshes)
    separation = {
        "pass": all("Glass" not in material
                    for material, _, _ in meshes["VD_RootsteadEntryVestibule_Frame"].faces)
                and all("Glass" in material
                        for material, _, _ in meshes["VD_RootsteadEntryVestibule_Glazing"].faces),
        "opaque_mesh": "VD_RootsteadEntryVestibule_Frame",
        "non_nanite_translucent_mesh": "VD_RootsteadEntryVestibule_Glazing",
    }
    report = {
        "all_pass": all(check["pass"] for check in checks.values())
                    and walkthrough["pass"] and separation["pass"],
        "checks": checks,
        "walkthrough": walkthrough,
        "material_separation": separation,
        "placement_world_cm": [128, 0, 3500],
    }
    (QA / "rootstead_entry_vestibule_verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    render_preview(meshes, QA / "rootstead_entry_vestibule_preview.png")
    print(json.dumps(report, indent=2))
    if not report["all_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

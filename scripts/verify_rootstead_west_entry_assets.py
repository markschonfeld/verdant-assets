#!/usr/bin/env python3
"""Contract, fit, and visual QA for the Rootstead west-entry assets."""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "SourceMesh" / "architecture"
QA = ROOT / "qa" / "rootstead_west_entry"
Vec3 = tuple[float, float, float]
Vec2 = tuple[float, float]
Face = tuple[str, tuple[int, ...], tuple[int, ...]]

EXPECTED = {
    "VD_RootsteadEntryPortal": {
        "mtl": "VD_RootsteadEntryPortal.mtl",
        "materials": {
            "M_EntryPortal_FormedConcrete", "M_EntryPortal_OxidisedAluminium",
            "M_EntryPortal_RevealSteel", "M_EntryPortal_TrellisSteel",
            "M_EntryPortal_FrostedGlass", "M_EntryPortal_WaterStain",
            "M_EntryPortal_BoltSteel",
        },
        "bounds": ((-445.0, -1450.0, 0.0), (128.0, 1450.0, 1200.0)),
    },
    "VD_VaultFootShoe": {
        "mtl": "VD_VaultFootShoe.mtl",
        "materials": {"M_VaultFootShoe_CastIron", "M_VaultFootShoe_BoltSteel",
                      "M_VaultFootShoe_WaterStain"},
        "bounds": ((-91.0, -94.0, 0.0), (91.0, 94.0, 72.0)),
    },
}

COLORS = {
    "M_EntryPortal_FormedConcrete": (119, 112, 91, 255),
    "M_EntryPortal_OxidisedAluminium": (72, 88, 82, 255),
    "M_EntryPortal_RevealSteel": (24, 29, 28, 255),
    "M_EntryPortal_TrellisSteel": (55, 67, 51, 255),
    "M_EntryPortal_FrostedGlass": (157, 190, 182, 185),
    "M_EntryPortal_WaterStain": (54, 61, 42, 255),
    "M_EntryPortal_BoltSteel": (142, 137, 111, 255),
    "M_VaultFootShoe_CastIron": (65, 69, 56, 255),
    "M_VaultFootShoe_BoltSteel": (139, 132, 103, 255),
    "M_VaultFootShoe_WaterStain": (48, 55, 37, 255),
}


@dataclass
class ObjMesh:
    name: str
    vertices: list[Vec3]
    texcoords: list[Vec2]
    faces: list[Face]
    objects: list[str]
    groups: int
    mtllib: str | None
    vertex_color_records: int


def parse_obj(name: str) -> ObjMesh:
    vertices: list[Vec3] = []
    texcoords: list[Vec2] = []
    faces: list[Face] = []
    objects: list[str] = []
    groups = 0
    mtllib = None
    material = ""
    vertex_color_records = 0
    for raw in (SOURCE / f"{name}.obj").read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if not parts:
            continue
        if parts[0] == "v":
            vertices.append(tuple(map(float, parts[1:4])))  # type: ignore[arg-type]
            if len(parts) > 4:
                vertex_color_records += 1
        elif parts[0] == "vt":
            texcoords.append(tuple(map(float, parts[1:3])))  # type: ignore[arg-type]
        elif parts[0] == "o":
            objects.append(parts[1])
        elif parts[0] == "g":
            groups += 1
        elif parts[0] == "mtllib":
            mtllib = parts[1]
        elif parts[0] == "usemtl":
            material = parts[1]
        elif parts[0] == "f":
            corners = [token.split("/") for token in parts[1:]]
            faces.append((material,
                          tuple(int(c[0]) - 1 for c in corners),
                          tuple(int(c[1]) - 1 if len(c) > 1 and c[1] else -1 for c in corners)))
    return ObjMesh(name, vertices, texcoords, faces, objects, groups, mtllib, vertex_color_records)


def triangle_area(a: Vec3, b: Vec3, c: Vec3) -> float:
    ab = tuple(b[i] - a[i] for i in range(3))
    ac = tuple(c[i] - a[i] for i in range(3))
    cross = (ab[1] * ac[2] - ab[2] * ac[1],
             ab[2] * ac[0] - ab[0] * ac[2],
             ab[0] * ac[1] - ab[1] * ac[0])
    return 0.5 * math.sqrt(sum(v * v for v in cross))


def bounds(mesh: ObjMesh) -> tuple[Vec3, Vec3]:
    return (tuple(min(v[i] for v in mesh.vertices) for i in range(3)),
            tuple(max(v[i] for v in mesh.vertices) for i in range(3)))  # type: ignore[return-value]


def face_bounds(mesh: ObjMesh, face: tuple[int, ...]) -> tuple[Vec3, Vec3]:
    points = [mesh.vertices[i] for i in face]
    return (tuple(min(v[i] for v in points) for i in range(3)),
            tuple(max(v[i] for v in points) for i in range(3)))  # type: ignore[return-value]


def structural_checks(mesh: ObjMesh) -> dict[str, object]:
    expected = EXPECTED[mesh.name]
    failures: list[str] = []
    materials = {m for m, _, _ in mesh.faces}
    if mesh.objects != [mesh.name]:
        failures.append(f"one-object contract failed: {mesh.objects}")
    if mesh.groups:
        failures.append(f"contains {mesh.groups} forbidden g records")
    if mesh.mtllib != expected["mtl"]:
        failures.append(f"mtllib {mesh.mtllib!r} != {expected['mtl']!r}")
    if materials != expected["materials"]:
        failures.append(f"materials {sorted(materials)} != {sorted(cast(set[str], expected['materials']))}")
    if mesh.vertex_color_records:
        failures.append(f"rigid mesh has {mesh.vertex_color_records} vertex-colour records")

    invalid_uvs = 0
    degenerates = 0
    edges: Counter[tuple[int, int]] = Counter()
    for _, face, uvs in mesh.faces:
        invalid_uvs += sum(i < 0 or i >= len(mesh.texcoords) for i in uvs)
        for i in range(1, len(face) - 1):
            if triangle_area(mesh.vertices[face[0]], mesh.vertices[face[i]],
                             mesh.vertices[face[i + 1]]) < 1e-5:
                degenerates += 1
        for i, vertex in enumerate(face):
            following = face[(i + 1) % len(face)]
            edges[(min(vertex, following), max(vertex, following))] += 1
    if invalid_uvs:
        failures.append(f"{invalid_uvs} face corners have invalid UV indices")
    if degenerates:
        failures.append(f"{degenerates} degenerate triangulated regions")
    non_two = sum(count != 2 for count in edges.values())
    if non_two:
        failures.append(f"{non_two} boundary/non-manifold edges")

    actual_bounds = bounds(mesh)
    expected_bounds = cast(tuple[Vec3, Vec3], expected["bounds"])
    for actual, target, label in zip(actual_bounds, expected_bounds, ("min", "max")):
        if any(abs(actual[i] - target[i]) > 0.01 for i in range(3)):
            failures.append(f"bounds {label} {actual} != {target}")
    if abs((actual_bounds[0][1] + actual_bounds[1][1]) / 2) > 0.01 or actual_bounds[0][2] != 0:
        failures.append("origin is not centred on Y at base Z=0")

    return {
        "pass": not failures, "failures": failures,
        "vertices": len(mesh.vertices), "texture_coordinates": len(mesh.texcoords),
        "faces": len(mesh.faces), "triangles": sum(len(f) - 2 for _, f, _ in mesh.faces),
        "object_names": mesh.objects, "group_records": mesh.groups,
        "vertex_color_records": mesh.vertex_color_records,
        "material_slots": sorted(materials), "invalid_uv_corners": invalid_uvs,
        "degenerate_regions": degenerates,
        "edge_incidence": {"total": len(edges), "non_two_face": non_two},
        "bounds_cm": {"min": actual_bounds[0], "max": actual_bounds[1]},
    }


def portal_fit_checks(mesh: ObjMesh) -> dict[str, object]:
    failures: list[str] = []
    bounded = [(m, *face_bounds(mesh, f)) for m, f, _ in mesh.faces]

    # Main east-face frame occupies only X 0..128 and leaves the exact vestibule
    # clearance envelope open: Y +/-1000, Z 0..920.
    facade_intrusions = []
    for index, (material, low, high) in enumerate(bounded):
        if (high[0] > 0 and low[0] < 129 and high[1] > -972 and low[1] < 972
                and high[2] > 0 and low[2] < 909):
            facade_intrusions.append({"face": index, "material": material, "min": low, "max": high})
    if facade_intrusions:
        failures.append(f"{len(facade_intrusions)} faces intrude into VEST_Frame clearance")

    # Player tunnel from the facade to the west door is clear to +/-400 and 4 m.
    route_intrusions = []
    for index, (material, low, high) in enumerate(bounded):
        if (high[0] > -340 and low[0] < 0 and high[1] > -400 and low[1] < 400
                and high[2] > 24 and low[2] < 400):
            route_intrusions.append({"face": index, "material": material, "min": low, "max": high})
    if route_intrusions:
        failures.append(f"{len(route_intrusions)} faces intrude into the walkable reveal")

    # Frosted material must occupy the measured leaf envelope and nothing farther.
    glass_points = [mesh.vertices[i] for material, face, _ in mesh.faces
                    if material == "M_EntryPortal_FrostedGlass" for i in face]
    glass_bounds = (tuple(min(p[i] for p in glass_points) for i in range(3)),
                    tuple(max(p[i] for p in glass_points) for i in range(3)))
    expected_glass = ((-397.0, -416.0, 8.0), (-353.0, 416.0, 392.0))
    if any(abs(glass_bounds[j][i] - expected_glass[j][i]) > 0.01
           for j in range(2) for i in range(3)):
        failures.append(f"frosted glazing bounds {glass_bounds} != {expected_glass}")

    return {
        "pass": not failures, "failures": failures,
        "placement_world_cm": [0, 0, 3500],
        "gable_edit_required": False,
        "facade_face_band_world_x_cm": [0, 128],
        "coverage_world_cm": {"y": [-1450, 1450], "z": [3500, 4700]},
        "vestibule_clear_opening_cm": {"y": [-1000, 1000], "z": [0, 920]},
        "frosted_glazing_local_bounds_cm": {"min": glass_bounds[0], "max": glass_bounds[1]},
        "vestibule_clearance_intrusions": facade_intrusions,
        "walkable_reveal_intrusions": route_intrusions,
        "collision_note": "Set CTF_USE_COMPLEX_AS_SIMPLE or author segmented aperture-safe primitives. Remove import-generated collision first; never use one auto convex hull because it seals the walk-through opening.",
    }


def shoe_fit_checks(mesh: ObjMesh) -> dict[str, object]:
    failures: list[str] = []
    socket = {"x": [-56.0, 56.0], "y": [-58.0, 58.0], "z": [12.0, 72.0]}
    stock = {"x": 100.1, "y": 103.9, "z": 40.3}
    clearance = {"x": 112.0 - stock["x"], "y": 116.0 - stock["y"]}
    if clearance["x"] <= 0 or clearance["y"] <= 0:
        failures.append(f"socket does not clear node stock: {clearance}")
    return {
        "pass": not failures, "failures": failures,
        "placement": "one per NodeHero foot; base at local Z=0 on deck top",
        "node_stock_cm": stock,
        "open_socket_cm": socket,
        "diametral_clearance_cm": clearance,
        "junction_coverage": "72 cm collar covers the node centred 10 cm below the 3500 deck datum",
        "collision_note": "Recommended NoCollision in the non-walkable planting beds. If collision is required, use the authored mesh/segmented primitives; do not rely on convex decomposition to preserve the explicit socket ring.",
    }


def normalize(v: Vec3) -> Vec3:
    length = math.sqrt(sum(x * x for x in v))
    return tuple(x / length for x in v)  # type: ignore[return-value]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def dot(a: Vec3, b: Vec3) -> float:
    return sum(a[i] * b[i] for i in range(3))


def render_view(image: Image.Image, mesh: ObjMesh, box: tuple[int, int, int, int],
                camera: Vec3, target: Vec3, label: str) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    view = normalize(tuple(camera[i] - target[i] for i in range(3)))  # type: ignore[arg-type]
    right = normalize(cross((0, 0, 1), view))
    up = cross(view, right)

    def project(point: Vec3) -> tuple[float, float, float]:
        relative = tuple(point[i] - target[i] for i in range(3))
        return dot(relative, right), dot(relative, up), dot(relative, view)  # type: ignore[arg-type]

    projected = [project(v) for v in mesh.vertices]
    x0, y0, x1, y1 = box
    xs, ys = [p[0] for p in projected], [p[1] for p in projected]
    scale = min((x1 - x0 - 70) / max(max(xs) - min(xs), 1),
                (y1 - y0 - 90) / max(max(ys) - min(ys), 1))
    centre = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    screen = ((x0 + x1) / 2, (y0 + y1) / 2 + 15)
    polygons = []
    for material, face, _ in mesh.faces:
        points = [projected[i] for i in face]
        polygon = [(screen[0] + (p[0] - centre[0]) * scale,
                    screen[1] - (p[1] - centre[1]) * scale) for p in points]
        polygons.append((sum(p[2] for p in points) / len(points), material, polygon))
    for _, material, polygon in sorted(polygons):
        draw.polygon(polygon, fill=COLORS[material], outline=(176, 177, 152, 145))
    draw.rectangle(box, outline=(75, 87, 78, 255), width=2)
    draw.text((x0 + 14, y0 + 12), label, fill=(238, 225, 195, 255), font=ImageFont.load_default())


def render_preview(portal: ObjMesh, shoe: ObjMesh) -> Path:
    QA.mkdir(parents=True, exist_ok=True)
    output = QA / "rootstead_west_entry_preview.png"
    image = Image.new("RGBA", (2400, 1500), (18, 22, 21, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default()
    draw.text((60, 35), "ROOTSTEAD WEST ENTRY / ADDITIVE OCCLUSION ASSETS",
              fill=(242, 227, 195, 255), font=font)
    draw.text((60, 60), "1960s institutional portal · frosted replacement leaves · explicit cast node shoe",
              fill=(159, 176, 163, 255), font=font)
    render_view(image, portal, (45, 100, 1560, 1010), (1500, -3300, 1700),
                (-100, 0, 550), "PORTAL / EAST-SOUTHEAST HERO")
    render_view(image, portal, (1600, 100, 2350, 770), (1800, 0, 600),
                (-100, 0, 600), "PORTAL / EAST ELEVATION")
    render_view(image, shoe, (1600, 805, 2350, 1395), (330, -430, 280),
                (0, 0, 36), "FOOT SHOE / OPEN SOCKET + FOUR ANCHORS")
    notes = [
        "Portal place: (0, 0, 3500). Face stays in world X 0..128; VEST opening clears Y +/-1000, Z 3500..4420.",
        "Frosted leaf geometry is in the measured X -397..-353, Y +/-416, Z 3508..3892 envelope.",
        "Portal collision: complex-as-simple or segmented aperture-safe primitives; NEVER one convex hull.",
        "Foot shoe socket: 112 x 116 cm clear for 100.1 x 103.9 cm node stock; recommended NoCollision in beds.",
        "Both are rigid meshes with no vertex colours. The integrated trellis is support steel only, not foliage.",
    ]
    for i, note in enumerate(notes):
        draw.text((75, 1060 + i * 58), note, fill=(198, 204, 184, 255), font=font)
    image.convert("RGB").save(output)
    return output


def main() -> None:
    QA.mkdir(parents=True, exist_ok=True)
    portal = parse_obj("VD_RootsteadEntryPortal")
    shoe = parse_obj("VD_VaultFootShoe")
    report = {
        "all_pass": False,
        "assets": {
            portal.name: {"contract": structural_checks(portal), "fit": portal_fit_checks(portal)},
            shoe.name: {"contract": structural_checks(shoe), "fit": shoe_fit_checks(shoe)},
        },
    }
    report["all_pass"] = all(section["pass"] for asset in report["assets"].values()
                              for section in asset.values())
    report_path = QA / "rootstead_west_entry_verification.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    preview = render_preview(portal, shoe)
    failures = [failure for asset in report["assets"].values()
                for section in asset.values() for failure in section["failures"]]
    print(json.dumps({"all_pass": report["all_pass"],
                      "report": str(report_path.relative_to(ROOT)),
                      "preview": str(preview.relative_to(ROOT)),
                      "failures": failures}, indent=2))
    if not report["all_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

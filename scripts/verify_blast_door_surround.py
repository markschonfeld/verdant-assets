#!/usr/bin/env python3
"""Verify and render the VD_BlastDoorSurround delivery."""

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
QA = ROOT / "qa" / "blast_door_surround"
NAME = "VD_BlastDoorSurround"
MTL = "VD_BlastDoorSurround.mtl"
EXPECTED_MATERIALS = {
    "M_BlastSurround_CastConcrete",
    "M_BlastSurround_AgedSteel",
    "M_BlastSurround_ShadowSteel",
    "M_BlastSurround_HandWear",
    "M_BlastSurround_WaterStain",
    "M_BlastSurround_BoltSteel",
}
COLORS = {
    "M_BlastSurround_CastConcrete": (92, 91, 80, 255),
    "M_BlastSurround_AgedSteel": (55, 68, 65, 255),
    "M_BlastSurround_ShadowSteel": (19, 24, 23, 255),
    "M_BlastSurround_HandWear": (126, 124, 107, 255),
    "M_BlastSurround_WaterStain": (45, 55, 45, 255),
    "M_BlastSurround_BoltSteel": (151, 147, 123, 255),
}
Vec3 = tuple[float, float, float]
Vec2 = tuple[float, float]
Face = tuple[str, tuple[int, ...], tuple[int, ...]]


@dataclass
class ObjMesh:
    vertices: list[Vec3]
    texcoords: list[Vec2]
    faces: list[Face]
    object_names: list[str]
    group_count: int
    mtllib: str | None


def parse_obj() -> ObjMesh:
    vertices: list[Vec3] = []
    texcoords: list[Vec2] = []
    faces: list[Face] = []
    object_names: list[str] = []
    group_count = 0
    mtllib = None
    material = ""
    for raw in (SOURCE / f"{NAME}.obj").read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if not parts:
            continue
        if parts[0] == "v":
            vertices.append(tuple(map(float, parts[1:4])))  # type: ignore[arg-type]
        elif parts[0] == "vt":
            texcoords.append(tuple(map(float, parts[1:3])))  # type: ignore[arg-type]
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
            faces.append((material,
                          tuple(int(corner[0]) - 1 for corner in corners),
                          tuple(int(corner[1]) - 1 if len(corner) > 1 and corner[1] else -1
                                for corner in corners)))
    return ObjMesh(vertices, texcoords, faces, object_names, group_count, mtllib)


def triangle_area(a: Vec3, b: Vec3, c: Vec3) -> float:
    ab = tuple(b[i] - a[i] for i in range(3))
    ac = tuple(c[i] - a[i] for i in range(3))
    cross = (ab[1] * ac[2] - ab[2] * ac[1],
             ab[2] * ac[0] - ab[0] * ac[2],
             ab[0] * ac[1] - ab[1] * ac[0])
    return 0.5 * math.sqrt(sum(value * value for value in cross))


def face_bounds(mesh: ObjMesh, face: tuple[int, ...]) -> tuple[Vec3, Vec3]:
    points = [mesh.vertices[index] for index in face]
    return (tuple(min(point[axis] for point in points) for axis in range(3)),
            tuple(max(point[axis] for point in points) for axis in range(3)))  # type: ignore[return-value]


def covers(minimum: float, maximum: float, low: float, high: float,
           tolerance: float = 0.01) -> bool:
    return minimum <= low + tolerance and maximum >= high - tolerance


def structural_checks(mesh: ObjMesh) -> dict[str, object]:
    failures: list[str] = []
    materials = {material for material, _, _ in mesh.faces}
    if mesh.object_names != [NAME]:
        failures.append(f"one-object contract failed: {mesh.object_names}")
    if mesh.group_count:
        failures.append(f"contains {mesh.group_count} forbidden g records")
    if mesh.mtllib != MTL:
        failures.append(f"mtllib is {mesh.mtllib!r}, expected {MTL!r}")
    if materials != EXPECTED_MATERIALS:
        failures.append(f"material slots {sorted(materials)} != {sorted(EXPECTED_MATERIALS)}")
    if not mesh.vertices or not mesh.texcoords or not mesh.faces:
        failures.append("empty vertices, UVs, or faces")

    invalid_uv_corners = 0
    degenerate_regions = 0
    edges: Counter[tuple[int, int]] = Counter()
    for _, face, uv_indices in mesh.faces:
        if len(face) < 3 or any(index < 0 or index >= len(mesh.vertices) for index in face):
            failures.append("invalid face vertex index")
            continue
        invalid_uv_corners += sum(index < 0 or index >= len(mesh.texcoords)
                                  for index in uv_indices)
        for index in range(1, len(face) - 1):
            if triangle_area(mesh.vertices[face[0]], mesh.vertices[face[index]],
                             mesh.vertices[face[index + 1]]) < 1e-5:
                degenerate_regions += 1
        for index, vertex in enumerate(face):
            following = face[(index + 1) % len(face)]
            edges[(min(vertex, following), max(vertex, following))] += 1
    non_two_edges = sum(count != 2 for count in edges.values())
    if invalid_uv_corners:
        failures.append(f"{invalid_uv_corners} face corners lack valid indexed UVs")
    if degenerate_regions:
        failures.append(f"{degenerate_regions} degenerate triangulated regions")
    if non_two_edges:
        failures.append(f"{non_two_edges} boundary/non-manifold edges")

    mins = tuple(min(point[axis] for point in mesh.vertices) for axis in range(3))
    maxs = tuple(max(point[axis] for point in mesh.vertices) for axis in range(3))
    expected_min = (-132.0, -520.0, -48.0)
    expected_max = (54.0, 520.0, 470.0)
    if any(abs(mins[i] - expected_min[i]) > 0.01 for i in range(3)):
        failures.append(f"unexpected minimum bounds {mins}, expected {expected_min}")
    if any(abs(maxs[i] - expected_max[i]) > 0.01 for i in range(3)):
        failures.append(f"unexpected maximum bounds {maxs}, expected {expected_max}")

    return {
        "pass": not failures,
        "failures": failures,
        "vertices": len(mesh.vertices),
        "texture_coordinates": len(mesh.texcoords),
        "faces": len(mesh.faces),
        "triangles": sum(len(face) - 2 for _, face, _ in mesh.faces),
        "object_names": mesh.object_names,
        "group_records": mesh.group_count,
        "material_slots": sorted(materials),
        "invalid_uv_corners": invalid_uv_corners,
        "degenerate_regions": degenerate_regions,
        "edge_incidence": {"total": len(edges), "non_two_face": non_two_edges},
        "bounds_cm": {"min": mins, "max": maxs,
                      "size": tuple(maxs[i] - mins[i] for i in range(3))},
    }


def gameplay_checks(mesh: ObjMesh) -> dict[str, object]:
    failures: list[str] = []
    bounded_faces = [(material, *face_bounds(mesh, face)) for material, face, _ in mesh.faces]

    # Each inner return face must run continuously from wall west face to jamb line.
    return_evidence: dict[str, list[dict[str, object]]] = {"south": [], "north": []}
    for side, target_y in (("south", -400.0), ("north", 400.0)):
        for material, mins, maxs in bounded_faces:
            if (abs(mins[1] - target_y) < 0.01 and abs(maxs[1] - target_y) < 0.01
                    and covers(mins[0], maxs[0], -129.0, 12.0)
                    and covers(mins[2], maxs[2], 8.0, 378.0)):
                return_evidence[side].append({"material": material, "min": mins, "max": maxs})
        if not return_evidence[side]:
            failures.append(f"no continuous {side} reveal-return face from X -129 to 12")

    # Central player volume remains open. Edge rub hardware is allowed outside
    # Y +/-380; overhead track hardware begins above Z 340.
    intrusions: list[dict[str, object]] = []
    for index, (material, mins, maxs) in enumerate(bounded_faces):
        intersects = (maxs[0] > -128 and mins[0] < 29
                      and maxs[1] > -380 and mins[1] < 380
                      and maxs[2] > 12 and mins[2] < 340)
        if intersects:
            intrusions.append({"face": index, "material": material,
                               "min": mins, "max": maxs})
    if intrusions:
        failures.append(f"{len(intrusions)} faces intrude into central player-clear volume")

    threshold_faces = []
    head_faces = []
    for material, mins, maxs in bounded_faces:
        if (abs(mins[2] - 8.0) < 0.01 and abs(maxs[2] - 8.0) < 0.01
                and covers(mins[0], maxs[0], -129.0, 30.0)
                and covers(mins[1], maxs[1], -400.0, 400.0)):
            threshold_faces.append({"material": material, "min": mins, "max": maxs})
        if (mins[2] >= 392.0 and covers(mins[0], maxs[0], -129.0, 12.0)
                and covers(mins[1], maxs[1], -400.0, 400.0)):
            head_faces.append({"material": material, "min": mins, "max": maxs})
    if not threshold_faces:
        failures.append("threshold plate does not span full reveal and 800 cm aperture")
    if not head_faces:
        failures.append("head does not span the full 800 cm aperture")

    return {
        "pass": not failures,
        "failures": failures,
        "placement_world_cm": [-380, 0, 3500],
        "origin_contract": "opening base-centre",
        "door_leaf_ownership": "separate existing animated meshes; not included",
        "clear_aperture_cm": {"width": 800, "height_below_track": 340,
                              "depth": 159},
        "required_side_return_world_bounds_cm": {
            "south": {"x": [-509, -350], "y": [-500, -400]},
            "north": {"x": [-509, -350], "y": [400, 500]},
        },
        "return_face_evidence": return_evidence,
        "threshold_face_evidence": threshold_faces,
        "head_face_evidence": head_faces,
        "central_volume_intrusions": intrusions,
        "collision_requirement": "CTF_USE_COMPLEX_AS_SIMPLE or authored aperture-safe primitives; never one auto convex hull",
    }


def normalize(vector: Vec3) -> Vec3:
    size = math.sqrt(sum(value * value for value in vector))
    return tuple(value / size for value in vector)  # type: ignore[return-value]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def dot(a: Vec3, b: Vec3) -> float:
    return sum(a[index] * b[index] for index in range(3))


def render_view(image: Image.Image, mesh: ObjMesh, box: tuple[int, int, int, int],
                camera: Vec3, target: Vec3, label: str) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    view = normalize(tuple(camera[i] - target[i] for i in range(3)))  # type: ignore[arg-type]
    right = normalize(cross((0, 0, 1), view))
    up = cross(view, right)

    def project(point: Vec3) -> tuple[float, float, float]:
        relative = tuple(point[i] - target[i] for i in range(3))
        return dot(relative, right), dot(relative, up), dot(relative, view)  # type: ignore[arg-type]

    projected = [project(point) for point in mesh.vertices]
    x0, y0, x1, y1 = box
    xs = [point[0] for point in projected]
    ys = [point[1] for point in projected]
    scale = min((x1 - x0 - 70) / max(max(xs) - min(xs), 1),
                (y1 - y0 - 90) / max(max(ys) - min(ys), 1))
    centre = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    screen_centre = ((x0 + x1) / 2, (y0 + y1) / 2 + 18)
    polygons = []
    for material, face, _ in mesh.faces:
        points = [projected[index] for index in face]
        screen = [(screen_centre[0] + (point[0] - centre[0]) * scale,
                   screen_centre[1] - (point[1] - centre[1]) * scale)
                  for point in points]
        polygons.append((sum(point[2] for point in points) / len(points), material, screen))
    for _, material, polygon in sorted(polygons):
        draw.polygon(polygon, fill=COLORS[material], outline=(172, 174, 153, 170))
    draw.rectangle(box, outline=(82, 92, 83, 255), width=2)
    draw.text((x0 + 14, y0 + 12), label, fill=(238, 226, 198, 255),
              font=ImageFont.load_default())


def render_plan(image: Image.Image, box: tuple[int, int, int, int]) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    x0, y0, x1, y1 = box
    scale = min((x1 - x0 - 90) / 220.0, (y1 - y0 - 90) / 1120.0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + 15

    def p(x: float, y: float) -> tuple[float, float]:
        return cx + x * scale, cy - y * scale

    def rect(ax: float, ay: float, bx: float, by: float, color: tuple[int, int, int, int]) -> None:
        points = [p(ax, ay), p(bx, by)]
        draw.rectangle((points[0][0], points[1][1], points[1][0], points[0][1]),
                       fill=color, outline=(182, 181, 156, 255), width=2)

    rect(-129, -520, 30, -400, COLORS["M_BlastSurround_CastConcrete"])
    rect(-129, 400, 30, 520, COLORS["M_BlastSurround_CastConcrete"])
    rect(-129, -400, 30, 400, (40, 62, 54, 95))
    # Player route arrow stays between the returns instead of escaping sideways.
    draw.line((*p(-150, 0), *p(60, 0)), fill=(231, 189, 83, 255), width=7)
    draw.polygon((p(60, 0), p(42, 16), p(42, -16)), fill=(231, 189, 83, 255))
    for y in (-400, 400):
        draw.line((*p(-129, y), *p(30, y)), fill=(236, 99, 80, 255), width=5)
    draw.rectangle(box, outline=(82, 92, 83, 255), width=2)
    draw.text((x0 + 14, y0 + 12), "PLAN CUT / SOLID 159 cm RETURNS AT Y +/-400",
              fill=(238, 226, 198, 255), font=ImageFont.load_default())
    draw.text((x0 + 14, y1 - 32), "gold: doorway axis   red: bounded reveal faces",
              fill=(174, 186, 170, 255), font=ImageFont.load_default())


def render_preview(mesh: ObjMesh) -> Path:
    output = QA / "blast_door_surround_preview.png"
    image = Image.new("RGBA", (2200, 1350), (18, 22, 21, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default()
    draw.text((65, 34), "VD_BLASTDOORSURROUND / ROOTSTEAD WEST PORTAL",
              fill=(240, 226, 194, 255), font=font)
    draw.text((65, 59), "older cast concrete + bolted steel · opening-base-centre origin · animated leaves excluded",
              fill=(158, 174, 162, 255), font=font)
    render_view(image, mesh, (50, 100, 1400, 950),
                (1050, -1450, 850), (-35, 0, 235), "EAST-SOUTHEAST HERO / TRACK + GUIDE SHOES")
    render_view(image, mesh, (1440, 100, 2150, 655),
                (1300, 0, 235), (-35, 0, 235), "EAST ELEVATION / 8.0 x 3.92 m OPENING")
    render_plan(image, (1440, 700, 2150, 1295))
    notes = [
        "Place at world (-380, 0, 3500), rotation zero, scale 1.0",
        "Returns occupy world X -509..-350 at world Y -500..-400 and 400..500",
        "Opaque one-object OBJ; six semantic material slots; UV on every face corner",
        "COLLISION: complex-as-simple or authored aperture-safe primitives — never one convex hull",
    ]
    for index, note in enumerate(notes):
        draw.text((78, 995 + index * 52), note, fill=(197, 203, 185, 255), font=font)
    image.convert("RGB").save(output)
    return output


def main() -> None:
    QA.mkdir(parents=True, exist_ok=True)
    mesh = parse_obj()
    contract = structural_checks(mesh)
    gameplay = gameplay_checks(mesh)
    report = {"all_pass": contract["pass"] and gameplay["pass"],
              "contract": contract, "gameplay": gameplay}
    report_path = QA / "blast_door_surround_verification.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    preview = render_preview(mesh)
    failures = (cast(list[str], contract["failures"])
                + cast(list[str], gameplay["failures"]))
    print(json.dumps({"all_pass": report["all_pass"],
                      "report": str(report_path.relative_to(ROOT)),
                      "preview": str(preview.relative_to(ROOT)),
                      "failures": failures}, indent=2))
    if not report["all_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

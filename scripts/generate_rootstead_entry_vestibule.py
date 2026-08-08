#!/usr/bin/env python3
"""Generate the Rootstead west-entry glazed-steel vestibule OBJ kit.

Coordinates are Unreal centimetres, Z-up.  The shared origin is the porch
back-bottom-centre: +X projects east into the greenhouse, +/-Y spans the
entrance, and +Z rises from the terrace.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "SourceMesh" / "architecture"
QA = ROOT / "qa" / "rootstead_entry_vestibule"
MTL_NAME = "VD_RootsteadEntryVestibule.mtl"

Vec3 = tuple[float, float, float]


@dataclass
class Mesh:
    name: str
    vertices: list[Vec3] = field(default_factory=list)
    faces: list[tuple[str, tuple[int, ...]]] = field(default_factory=list)

    def vertex(self, point: Vec3) -> int:
        self.vertices.append(point)
        return len(self.vertices)

    def face(self, material: str, indices: Iterable[int]) -> None:
        self.faces.append((material, tuple(indices)))

    def add_quad(self, corners: tuple[Vec3, Vec3, Vec3, Vec3], material: str) -> None:
        self.face(material, [self.vertex(point) for point in corners])

    def add_box(self, minimum: Vec3, maximum: Vec3, material: str) -> None:
        x0, y0, z0 = minimum
        x1, y1, z1 = maximum
        ids = [
            self.vertex((x, y, z))
            for z in (z0, z1)
            for y in (y0, y1)
            for x in (x0, x1)
        ]
        self.face(material, (ids[0], ids[1], ids[3], ids[2]))
        self.face(material, (ids[4], ids[6], ids[7], ids[5]))
        self.face(material, (ids[0], ids[4], ids[5], ids[1]))
        self.face(material, (ids[2], ids[3], ids[7], ids[6]))
        self.face(material, (ids[0], ids[2], ids[6], ids[4]))
        self.face(material, (ids[1], ids[5], ids[7], ids[3]))

    def add_beam(self, start: Vec3, end: Vec3, width: float, material: str) -> None:
        """Add a closed square-section beam between arbitrary points."""
        delta = tuple(end[i] - start[i] for i in range(3))
        length = math.sqrt(sum(value * value for value in delta))
        axis = tuple(value / length for value in delta)
        seed = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.92 else (0.0, 1.0, 0.0)
        side = (
            axis[1] * seed[2] - axis[2] * seed[1],
            axis[2] * seed[0] - axis[0] * seed[2],
            axis[0] * seed[1] - axis[1] * seed[0],
        )
        side_length = math.sqrt(sum(value * value for value in side))
        side = tuple(value / side_length for value in side)
        up = (
            axis[1] * side[2] - axis[2] * side[1],
            axis[2] * side[0] - axis[0] * side[2],
            axis[0] * side[1] - axis[1] * side[0],
        )
        half = width / 2.0
        rings: list[list[int]] = []
        for point in (start, end):
            ring = []
            for side_sign, up_sign in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                ring.append(self.vertex((
                    point[0] + half * (side_sign * side[0] + up_sign * up[0]),
                    point[1] + half * (side_sign * side[1] + up_sign * up[1]),
                    point[2] + half * (side_sign * side[2] + up_sign * up[2]),
                )))
            rings.append(ring)
        self.face(material, reversed(rings[0]))
        self.face(material, rings[1])
        for index in range(4):
            following = (index + 1) % 4
            self.face(material, (rings[0][index], rings[1][index],
                                 rings[1][following], rings[0][following]))

    def add_cylinder(self, start: Vec3, end: Vec3, radius: float,
                     sides: int, material: str) -> None:
        delta = tuple(end[i] - start[i] for i in range(3))
        length = math.sqrt(sum(value * value for value in delta))
        axis = tuple(value / length for value in delta)
        seed = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.92 else (1.0, 0.0, 0.0)
        side = (
            axis[1] * seed[2] - axis[2] * seed[1],
            axis[2] * seed[0] - axis[0] * seed[2],
            axis[0] * seed[1] - axis[1] * seed[0],
        )
        side_length = math.sqrt(sum(value * value for value in side))
        side = tuple(value / side_length for value in side)
        up = (
            axis[1] * side[2] - axis[2] * side[1],
            axis[2] * side[0] - axis[0] * side[2],
            axis[0] * side[1] - axis[1] * side[0],
        )
        rings: list[list[int]] = []
        for point in (start, end):
            ring = []
            for index in range(sides):
                angle = 2.0 * math.pi * index / sides
                ring.append(self.vertex((
                    point[0] + radius * (math.cos(angle) * side[0] + math.sin(angle) * up[0]),
                    point[1] + radius * (math.cos(angle) * side[1] + math.sin(angle) * up[1]),
                    point[2] + radius * (math.cos(angle) * side[2] + math.sin(angle) * up[2]),
                )))
            rings.append(ring)
        self.face(material, reversed(rings[0]))
        self.face(material, rings[1])
        for index in range(sides):
            following = (index + 1) % sides
            self.face(material, (rings[0][index], rings[0][following],
                                 rings[1][following], rings[1][index]))

    def face_uvs(self, face: tuple[int, ...], centimetres_per_uv: float = 100.0) -> list[tuple[float, float]]:
        points = [self.vertices[index - 1] for index in face]
        nx = ny = nz = 0.0
        for point, following in zip(points, points[1:] + points[:1]):
            nx += (point[1] - following[1]) * (point[2] + following[2])
            ny += (point[2] - following[2]) * (point[0] + following[0])
            nz += (point[0] - following[0]) * (point[1] + following[1])
        dominant = max(range(3), key=lambda axis: abs((nx, ny, nz)[axis]))
        if dominant == 0:
            return [(point[1] / centimetres_per_uv, point[2] / centimetres_per_uv)
                    for point in points]
        if dominant == 1:
            return [(point[0] / centimetres_per_uv, point[2] / centimetres_per_uv)
                    for point in points]
        return [(point[0] / centimetres_per_uv, point[1] / centimetres_per_uv)
                for point in points]

    def write_obj(self, path: Path) -> None:
        lines = [
            "# Generated by scripts/generate_rootstead_entry_vestibule.py",
            f"mtllib {MTL_NAME}",
            f"o {self.name}",
        ]
        lines.extend(f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in self.vertices)
        uv_indices: list[tuple[int, ...]] = []
        next_uv = 1
        for _, face in self.faces:
            uvs = self.face_uvs(face)
            lines.extend(f"vt {u:.6f} {v:.6f}" for u, v in uvs)
            uv_indices.append(tuple(range(next_uv, next_uv + len(uvs))))
            next_uv += len(uvs)
        current_material = None
        for (material, face), face_uvs in zip(self.faces, uv_indices):
            if material != current_material:
                lines.extend((f"usemtl {material}", "s 1"))
                current_material = material
            lines.append("f " + " ".join(
                f"{vertex}/{uv}" for vertex, uv in zip(face, face_uvs)
            ))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def roof_height(y: float) -> float:
    return 900.0 - 80.0 * abs(y) / 940.0


def build_frame() -> Mesh:
    mesh = Mesh("VD_RootsteadEntryVestibule_Frame")
    painted = "M_Vestibule_PaintedSteel"
    base_wear = "M_Vestibule_PaintedSteel_BaseWear"
    bare = "M_Vestibule_BareSteel"
    seal = "M_Vestibule_RubberSeal"
    kick = "M_Vestibule_Kickplate"

    # Main posts: 18.8 m clear outer frame, 3.6 m projection, 8.2 m eaves.
    # Split the lower 85 cm into a weathered slot so water staining and paint loss
    # can be authored without adding plinth-like geometry around the sections.
    for x in (10.0, 180.0, 350.0):
        for y in (-930.0, 930.0):
            mesh.add_box((x - 10, y - 10, 0), (x + 10, y + 10, 85), base_wear)
            mesh.add_box((x - 10, y - 10, 85), (x + 10, y + 10, 820), painted)
    # Keep only the front opening jambs. The former rear pair at X=10, Y=+/-470
    # read as freestanding poles from the player approach and are intentionally gone.
    for y in (-470.0, 470.0):
        mesh.add_box((340, y - 10, 0), (360, y + 10, 85), base_wear)
        mesh.add_box((340, y - 10, 85), (360, y + 10, 820), painted)

    # A deeper continuous rear head member carries the full span between corner
    # posts after removal of the intermediate rear supports.
    mesh.add_box((0, -930, 780), (20, 930, 820), painted)

    # Side-wall sills, transoms, eaves, and greenhouse roof ribs.
    for y in (-930.0, 930.0):
        for z in (75.0, 430.0, 810.0):
            mesh.add_box((0, y - 9, z - 9), (360, y + 9, z + 9), painted)
    for x in (10.0, 180.0, 350.0):
        mesh.add_beam((x, -930, 820), (x, 0, 900), 18, painted)
        mesh.add_beam((x, 0, 900), (x, 930, 820), 18, painted)
    for y in (-470.0, 0.0, 470.0):
        z = roof_height(y)
        mesh.add_box((0, y - 8, z - 8), (360, y + 8, z + 8), painted)

    # East/front face preserves a 9.2 m wide x 5.2 m clear walk-through.
    for y0, y1 in ((-930, -480), (480, 930)):
        for z in (75.0, 430.0, 810.0):
            mesh.add_box((340, y0, z - 9), (360, y1, z + 9), painted)
    mesh.add_box((340, -480, 520), (360, 480, 542), painted)
    mesh.add_box((340, -10, 532), (360, 10, 820), painted)

    # Low sacrificial steel skirts stop glass at terrace level without closing the opening.
    for y in (-930.0, 930.0):
        mesh.add_box((0, y - 6, 0), (360, y + 6, 65), kick)
    for y0, y1 in ((-930, -480), (480, 930)):
        mesh.add_box((348, y0, 0), (360, y1, 65), kick)

    # Rubber glazing seats read as continuous dark shadow-lines around the panes.
    for y in (-940.0, 940.0):
        for z in (85.0, 438.0, 802.0):
            mesh.add_box((8, y - 3, z - 4), (352, y + 3, z + 4), seal)
    for y in (-940.0, -480.0, 480.0, 940.0):
        mesh.add_box((347, y - 3, 72), (353, y + 3, 810), seal)
    mesh.add_box((347, -476, 536), (353, 476, 544), seal)

    # Bolted corner wall shoes make the light addition visibly secondary to the
    # concrete wall. One enlarged replacement washer breaks factory symmetry.
    for y in (-930.0, 930.0):
        mesh.add_box((0, y - 42, 0), (12, y + 42, 95), bare)
        for bolt_y in (y - 27, y + 27):
            for bolt_z in (20.0, 72.0):
                replacement = y > 0 and bolt_y > y and bolt_z > 50
                radius = 7 if replacement else 5
                sides = 12 if replacement else 8
                mesh.add_cylinder((12, bolt_y, bolt_z), (22, bolt_y, bolt_z),
                                  radius, sides, bare)

    # Age and repair: two unapologetically visible fishplates and restrained side bracing.
    mesh.add_box((338, -735, 795), (362, -555, 827), bare)
    for bolt_y in (-705.0, -585.0):
        mesh.add_cylinder((362, bolt_y, 811), (370, bolt_y, 811), 5, 8, bare)
    mesh.add_box((165, -18, 875), (195, 18, 907), bare)
    mesh.add_cylinder((185, -900, 455), (185, -900, 785), 7, 10, bare)
    mesh.add_cylinder((185, 900, 455), (185, 900, 785), 7, 10, bare)

    # Greenhouse gutters and one surviving downpipe give the porch a functional silhouette.
    for y in (-942.0, 942.0):
        mesh.add_box((0, y - 8, 805), (360, y + 8, 825), bare)
    mesh.add_cylinder((348, -947, 805), (348, -947, 95), 12, 12, bare)
    mesh.add_cylinder((348, -947, 95), (320, -947, 65), 12, 12, bare)
    return mesh


def build_glazing() -> Mesh:
    mesh = Mesh("VD_RootsteadEntryVestibule_Glazing")
    aged = "M_Vestibule_GlassAged"
    repair = "M_Vestibule_GlassRepair"

    # Side walls: independently replaceable rectangular panes.
    for side_y, reverse in ((-941.0, False), (941.0, True)):
        for x0, x1 in ((12.0, 174.0), (186.0, 348.0)):
            for z0, z1 in ((90.0, 424.0), (440.0, 800.0)):
                material = repair if (side_y > 0 and x0 > 180 and z0 > 430) else aged
                corners = ((x0, side_y, z0), (x1, side_y, z0),
                           (x1, side_y, z1), (x0, side_y, z1))
                if reverse:
                    corners = (corners[3], corners[2], corners[1], corners[0])
                mesh.add_quad(corners, material)

    # East/front outer bays and transom; central opening remains completely empty.
    front_x = 361.0
    for y0, y1 in ((-928.0, -482.0), (482.0, 928.0)):
        for z0, z1 in ((78.0, 424.0), (440.0, 800.0)):
            material = repair if (y0 > 0 and z0 < 430) else aged
            mesh.add_quad(((front_x, y1, z0), (front_x, y0, z0),
                           (front_x, y0, z1), (front_x, y1, z1)), material)
    for y0, y1 in ((-462.0, -8.0), (8.0, 462.0)):
        mesh.add_quad(((front_x, y1, 548), (front_x, y0, 548),
                       (front_x, y0, 800), (front_x, y1, 800)), aged)

    # Four roof bays per slope; a few clearer laminated repairs break the age pattern.
    for x0, x1 in ((12.0, 174.0), (186.0, 348.0)):
        for y0, y1 in ((-922.0, -474.0), (-462.0, -12.0),
                       (12.0, 462.0), (474.0, 922.0)):
            z0, z1 = roof_height(y0), roof_height(y1)
            material = repair if (x0 > 180 and y0 < -450) or (x0 < 180 and y0 > 450) else aged
            mesh.add_quad(((x0, y0, z0), (x1, y0, z0),
                           (x1, y1, z1), (x0, y1, z1)), material)
    return mesh


def write_mtl(path: Path) -> None:
    materials = {
        "M_Vestibule_PaintedSteel": (0.105, 0.205, 0.190, 0.75, 0.52, 1.0),
        "M_Vestibule_PaintedSteel_BaseWear": (0.085, 0.125, 0.105, 0.70, 0.78, 1.0),
        "M_Vestibule_BareSteel": (0.290, 0.315, 0.305, 0.95, 0.38, 1.0),
        "M_Vestibule_RubberSeal": (0.025, 0.030, 0.026, 0.0, 0.88, 1.0),
        "M_Vestibule_Kickplate": (0.155, 0.165, 0.145, 0.85, 0.62, 1.0),
        "M_Vestibule_GlassAged": (0.280, 0.390, 0.350, 0.0, 0.24, 0.28),
        "M_Vestibule_GlassRepair": (0.410, 0.540, 0.510, 0.0, 0.12, 0.16),
    }
    lines = ["# Unreal material-slot placeholders; PBR intent follows as comments."]
    for name, (r, g, b, metallic, roughness, opacity) in materials.items():
        lines.extend((
            f"newmtl {name}", f"Kd {r:.3f} {g:.3f} {b:.3f}",
            f"d {opacity:.3f}", f"# metallic {metallic:.2f}",
            f"# roughness {roughness:.2f}", "",
        ))
    path.write_text("\n".join(lines), encoding="utf-8")


def mesh_record(mesh: Mesh) -> dict[str, object]:
    mins = [min(point[axis] for point in mesh.vertices) for axis in range(3)]
    maxs = [max(point[axis] for point in mesh.vertices) for axis in range(3)]
    return {
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "triangles_after_import": sum(len(face) - 2 for _, face in mesh.faces),
        "bounds_cm": {
            "min": [round(value, 3) for value in mins],
            "max": [round(value, 3) for value in maxs],
            "size": [round(maxs[axis] - mins[axis], 3) for axis in range(3)],
        },
        "materials": sorted({material for material, _ in mesh.faces}),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    meshes = (build_frame(), build_glazing())
    write_mtl(OUT / MTL_NAME)
    for mesh in meshes:
        mesh.write_obj(OUT / f"{mesh.name}.obj")
    report = {
        "units": "centimetres (1 OBJ unit = 1 Unreal uu = 1 cm)",
        "axis": "Z-up; +X projects east into the greenhouse",
        "pivot": "shared porch back-bottom-centre at (0, 0, 0)",
        "placement_world_cm": [128, 0, 3500],
        "walkthrough_clear_cm": {"width": 920, "height": 520},
        "trellis_internal_clear_cm": {"width": 1840, "eave_height": 810},
        "meshes": {mesh.name: mesh_record(mesh) for mesh in meshes},
    }
    (QA / "rootstead_entry_vestibule_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate the entrance-terrace modular planter and botanical OBJ kit.

Units are Unreal centimetres, Z-up. Every OBJ has one object, no group records,
indexed UVs on every face corner, and a base-centred origin. The morning-glory
assets use the bottom of the hanging curtain as Z=0 so they can be aligned to
the deck while their upper edge meets the planter rim.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "SourceMesh" / "terrace_botanical"
QA = ROOT / "qa" / "terrace_planter_botanical"
MTL_NAME = "VD_TerraceBotanical.mtl"
Vec3 = tuple[float, float, float]


def add(a: Vec3, b: Vec3) -> Vec3:
    return tuple(a[i] + b[i] for i in range(3))  # type: ignore[return-value]


def sub(a: Vec3, b: Vec3) -> Vec3:
    return tuple(a[i] - b[i] for i in range(3))  # type: ignore[return-value]


def mul(a: Vec3, value: float) -> Vec3:
    return tuple(a[i] * value for i in range(3))  # type: ignore[return-value]


def length(a: Vec3) -> float:
    return math.sqrt(sum(value * value for value in a))


def normalize(a: Vec3) -> Vec3:
    size = length(a)
    return mul(a, 1.0 / size)


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


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

    def quad(self, points: tuple[Vec3, Vec3, Vec3, Vec3], material: str,
             two_sided: bool = False) -> None:
        ids = tuple(self.vertex(point) for point in points)
        self.face(material, ids)
        if two_sided:
            self.face(material, reversed(ids))

    def box(self, minimum: Vec3, maximum: Vec3, material: str) -> None:
        x0, y0, z0 = minimum
        x1, y1, z1 = maximum
        ids = [self.vertex((x, y, z)) for z in (z0, z1)
               for y in (y0, y1) for x in (x0, x1)]
        for face in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
                     (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            self.face(material, tuple(ids[i] for i in face))

    def cylinder(self, start: Vec3, end: Vec3, radius0: float, radius1: float,
                 sides: int, material: str, capped: bool = True) -> None:
        axis = normalize(sub(end, start))
        seed = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.9 else (1.0, 0.0, 0.0)
        side = normalize(cross(axis, seed))
        up = cross(axis, side)
        rings: list[list[int]] = []
        for point, radius in ((start, radius0), (end, radius1)):
            ring = []
            for index in range(sides):
                angle = 2 * math.pi * index / sides
                offset = add(mul(side, math.cos(angle) * radius),
                             mul(up, math.sin(angle) * radius))
                ring.append(self.vertex(add(point, offset)))
            rings.append(ring)
        if capped:
            self.face(material, reversed(rings[0]))
            self.face(material, rings[1])
        for index in range(sides):
            following = (index + 1) % sides
            self.face(material, (rings[0][index], rings[0][following],
                                 rings[1][following], rings[1][index]))

    def ribbon_leaf(self, start: Vec3, azimuth: float, leaf_length: float,
                    width: float, rise: float, droop: float, material: str,
                    segments: int = 6, twist: float = 0.0) -> None:
        """Add a V-folded, tapered blade with authored curvature."""
        direction = (math.cos(azimuth), math.sin(azimuth), 0.0)
        lateral = (-direction[1], direction[0], 0.0)
        rows: list[tuple[int, int, int]] = []
        for index in range(segments + 1):
            t = index / segments
            centre = add(start, (direction[0] * leaf_length * t,
                                 direction[1] * leaf_length * t,
                                 rise * math.sin(math.pi * t) - droop * t * t))
            half_width = width * max(0.035, math.sin(math.pi * min(t, 0.999))) * 0.5
            angle = twist * t
            lat = add(mul(lateral, math.cos(angle)), (0.0, 0.0, math.sin(angle)))
            left = add(centre, add(mul(lat, -half_width), (0.0, 0.0, 0.9)))
            right = add(centre, add(mul(lat, half_width), (0.0, 0.0, 0.9)))
            rows.append((self.vertex(left), self.vertex(centre), self.vertex(right)))
        for index in range(segments):
            a, b, c = rows[index]
            d, e, f = rows[index + 1]
            for face in ((a, d, e, b), (b, e, f, c)):
                self.face(material, face)
                self.face(material, reversed(face))

    def broad_leaf(self, centre: Vec3, direction: Vec3, leaf_length: float,
                   width: float, material: str, heart: bool = False) -> None:
        """Add a two-sided six-section leaf with a shallow centre crease."""
        axis = normalize(direction)
        lateral = normalize(cross(axis, (0.0, 0.0, 1.0))) if abs(axis[2]) < 0.92 else (1.0, 0.0, 0.0)
        normal = normalize(cross(lateral, axis))
        fractions = (0.0, 0.18, 0.42, 0.68, 0.88, 1.0)
        widths = (0.18 if heart else 0.035, 0.78, 1.0, 0.82, 0.42, 0.035)
        rows = []
        base = add(centre, mul(axis, -leaf_length * 0.5))
        for t, w in zip(fractions, widths):
            mid = add(base, mul(axis, leaf_length * t))
            if heart and t < 0.22:
                mid = add(mid, mul(axis, -2.2 * (0.22 - t)))
            half = width * w * 0.5
            rows.append((self.vertex(add(mid, add(mul(lateral, -half), mul(normal, 0.8)))),
                         self.vertex(mid),
                         self.vertex(add(mid, add(mul(lateral, half), mul(normal, 0.8))))))
        for index in range(len(rows) - 1):
            a, b, c = rows[index]
            d, e, f = rows[index + 1]
            for face in ((a, d, e, b), (b, e, f, c)):
                self.face(material, face)
                self.face(material, reversed(face))

    def flower_bell(self, centre: Vec3, direction: Vec3, radius: float,
                    depth: float, material: str, sides: int = 10) -> None:
        axis = normalize(direction)
        seed = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.9 else (1.0, 0.0, 0.0)
        lateral = normalize(cross(axis, seed))
        up = cross(axis, lateral)
        throat = add(centre, mul(axis, -depth))
        throat_ring, mouth_ring = [], []
        for index in range(sides):
            angle = 2 * math.pi * index / sides
            radial = add(mul(lateral, math.cos(angle)), mul(up, math.sin(angle)))
            throat_ring.append(self.vertex(add(throat, mul(radial, radius * 0.22))))
            petal = radius * (1.0 + 0.13 * math.cos(5 * angle))
            mouth_ring.append(self.vertex(add(centre, mul(radial, petal))))
        for index in range(sides):
            following = (index + 1) % sides
            face = (throat_ring[index], throat_ring[following],
                    mouth_ring[following], mouth_ring[index])
            self.face(material, face)
            self.face(material, reversed(face))

    def face_uvs(self, face: tuple[int, ...], scale: float = 100.0) -> list[tuple[float, float]]:
        points = [self.vertices[index - 1] for index in face]
        nx = ny = nz = 0.0
        for point, following in zip(points, points[1:] + points[:1]):
            nx += (point[1] - following[1]) * (point[2] + following[2])
            ny += (point[2] - following[2]) * (point[0] + following[0])
            nz += (point[0] - following[0]) * (point[1] + following[1])
        dominant = max(range(3), key=lambda i: abs((nx, ny, nz)[i]))
        if dominant == 0:
            return [(p[1] / scale, p[2] / scale) for p in points]
        if dominant == 1:
            return [(p[0] / scale, p[2] / scale) for p in points]
        return [(p[0] / scale, p[1] / scale) for p in points]

    def write_obj(self, path: Path) -> None:
        lines = ["# Generated by scripts/generate_terrace_planter_botanical_kit.py",
                 f"mtllib {MTL_NAME}", f"o {self.name}"]
        lines.extend(f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in self.vertices)
        face_uvs: list[tuple[int, ...]] = []
        next_uv = 1
        for _, face in self.faces:
            uvs = self.face_uvs(face)
            lines.extend(f"vt {u:.6f} {v:.6f}" for u, v in uvs)
            face_uvs.append(tuple(range(next_uv, next_uv + len(uvs))))
            next_uv += len(uvs)
        current = None
        for (material, face), uvs in zip(self.faces, face_uvs):
            if material != current:
                lines.extend((f"usemtl {material}", "s 1"))
                current = material
            lines.append("f " + " ".join(f"{v}/{uv}" for v, uv in zip(face, uvs)))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_planter() -> Mesh:
    mesh = Mesh("VD_TerracePlanter")
    concrete, repair, soil = "M_Planter_AgedConcrete", "M_Planter_CastRepair", "M_Planter_Soil"
    # 245 cm module matches the existing BALUS bay cadence. Ends remain open so
    # neighbouring modules share a continuous section without doubled end walls.
    mesh.box((-60, -122.5, 0), (-47, 122.5, 102), concrete)
    mesh.box((47, -122.5, 0), (60, 122.5, 102), concrete)
    mesh.box((-47, -122.5, 0), (47, 122.5, 12), concrete)
    mesh.box((-63, -122.5, 102), (-42, 122.5, 110), repair)
    mesh.box((42, -122.5, 102), (63, 122.5, 110), repair)
    mesh.box((-46.5, -122.5, 86), (46.5, 122.5, 93), soil)
    # Two recessed cast drain/scupper details break the slab without obstructing tiling.
    for y in (-61.25, 61.25):
        mesh.cylinder((-60.5, y, 22), (-47.0, y, 22), 4.5, 4.5, 10, repair)
    return mesh


def build_endcap() -> Mesh:
    mesh = Mesh("VD_TerracePlanter_EndCap")
    concrete, repair = "M_Planter_AgedConcrete", "M_Planter_CastRepair"
    mesh.box((-60, -4, 0), (60, 4, 102), concrete)
    mesh.box((-63, -6, 102), (63, 6, 110), repair)
    # Four exposed retrofit bolts make the terminal condition legible as bolted, not moulded.
    for x in (-45, 45):
        for z in (28, 78):
            mesh.cylinder((x, -7, z), (x, -3, z), 3.2, 3.2, 8, repair)
    return mesh


def build_dracaena(name: str, height: float, canes: int, seed: int) -> Mesh:
    rng = random.Random(seed)
    mesh = Mesh(name)
    cane_mat, leaf_mat, scar_mat = "M_Dracaena_Cane", "M_Dracaena_Leaf", "M_Dracaena_LeafScar"
    for cane_index in range(canes):
        angle = 2 * math.pi * cane_index / canes + rng.uniform(-0.45, 0.45)
        radius = 8 + 10 * (cane_index / max(1, canes - 1))
        base = (math.cos(angle) * radius, math.sin(angle) * radius, 0.0)
        cane_height = height * rng.uniform(0.72 if canes > 1 else 0.95, 0.98)
        top = add(base, (rng.uniform(-5, 5), rng.uniform(-5, 5), cane_height))
        mesh.cylinder(base, top, rng.uniform(4.2, 5.7), rng.uniform(2.8, 4.2), 10, cane_mat)
        # Raised annular scars read at sky silhouette distance without texture dependence.
        for z in range(28, int(cane_height - 18), 24):
            t = z / cane_height
            centre = add(base, mul(sub(top, base), t))
            mesh.cylinder(add(centre, (0, 0, -1.0)), add(centre, (0, 0, 1.0)),
                          5.1, 5.1, 10, scar_mat)
        crown_start = add(top, (0, 0, -2))
        leaf_count = 17 + cane_index * 2
        for leaf_index in range(leaf_count):
            azimuth = 2 * math.pi * leaf_index / leaf_count + rng.uniform(-0.12, 0.12)
            leaf_length = rng.uniform(52, 82) * (height / 190.0) ** 0.25
            mesh.ribbon_leaf(crown_start, azimuth, leaf_length,
                             rng.uniform(3.2, 5.4), rng.uniform(11, 24),
                             rng.uniform(25, 48), leaf_mat, twist=rng.uniform(-0.22, 0.22))
    return mesh


def build_zz(name: str, target_height: float, fronds: int, seed: int) -> Mesh:
    rng = random.Random(seed)
    mesh = Mesh(name)
    stem_mat, leaf_mat = "M_ZZ_Stem", "M_ZZ_Leaf"
    for frond in range(fronds):
        angle = 2 * math.pi * frond / fronds + rng.uniform(-0.3, 0.3)
        lean = rng.uniform(15, 32)
        height = target_height * rng.uniform(0.76, 1.0)
        p0 = (rng.uniform(-5, 5), rng.uniform(-5, 5), 0.0)
        p1 = (math.cos(angle) * lean * 0.38, math.sin(angle) * lean * 0.38, height * 0.58)
        p2 = (math.cos(angle) * lean, math.sin(angle) * lean, height)
        mesh.cylinder(p0, p1, 1.8, 1.25, 8, stem_mat)
        mesh.cylinder(p1, p2, 1.25, 0.65, 8, stem_mat)
        for pair in range(4):
            t = 0.42 + pair * 0.13
            if t < 0.58:
                q = add(p0, mul(sub(p1, p0), t / 0.58))
                tangent = sub(p1, p0)
            else:
                q = add(p1, mul(sub(p2, p1), (t - 0.58) / 0.42))
                tangent = sub(p2, p1)
            lateral = normalize(cross(normalize(tangent), (0.0, 0.0, 1.0)))
            for side in (-1, 1):
                centre = add(q, mul(lateral, side * rng.uniform(8, 11)))
                direction = normalize(add(mul(lateral, side), mul(normalize(tangent), 0.35)))
                mesh.broad_leaf(centre, direction, rng.uniform(17, 23),
                                rng.uniform(7, 10), leaf_mat)
        mesh.broad_leaf(add(p2, mul(normalize(sub(p2, p1)), 7)), normalize(sub(p2, p1)),
                        rng.uniform(16, 21), rng.uniform(7, 9), leaf_mat)
    return mesh


def build_morning_glory(name: str, width: float, strands: int, seed: int) -> Mesh:
    rng = random.Random(seed)
    mesh = Mesh(name)
    stem_mat, leaf_mat, flower_mat = "M_MorningGlory_Stem", "M_MorningGlory_Leaf", "M_MorningGlory_Flower"
    for strand in range(strands):
        y = -width * 0.5 + width * (strand + 0.5) / strands + rng.uniform(-4, 4)
        top = (rng.uniform(-1, 1), y, rng.uniform(91, 103))
        mid = (rng.uniform(-16, -8), y + rng.uniform(-7, 7), rng.uniform(45, 66))
        bottom = (rng.uniform(-24, -14), y + rng.uniform(-10, 10), rng.uniform(2, 13))
        mesh.cylinder(bottom, mid, 1.15, 1.0, 7, stem_mat)
        mesh.cylinder(mid, top, 1.0, 0.8, 7, stem_mat)
        for index, t in enumerate((0.18, 0.4, 0.62, 0.82)):
            if t < 0.5:
                q = add(bottom, mul(sub(mid, bottom), t * 2))
                tangent = normalize(sub(mid, bottom))
            else:
                q = add(mid, mul(sub(top, mid), (t - 0.5) * 2))
                tangent = normalize(sub(top, mid))
            side = -1 if (index + strand) % 2 else 1
            lateral = normalize(cross(tangent, (1.0, 0.0, 0.0)))
            if length(lateral) < 0.1:
                lateral = (0.0, 1.0, 0.0)
            centre = add(q, mul(lateral, side * rng.uniform(7, 12)))
            mesh.broad_leaf(centre, normalize(add(mul(lateral, side), (0.15, 0, 0.15))),
                            rng.uniform(18, 27), rng.uniform(16, 24), leaf_mat, heart=True)
            if index in (1, 3) and rng.random() > 0.28:
                flower_centre = add(q, (-rng.uniform(5, 11), side * rng.uniform(2, 6), rng.uniform(-2, 4)))
                mesh.flower_bell(flower_centre, (-1.0, side * 0.18, -0.12),
                                 rng.uniform(6.5, 9.0), rng.uniform(7, 10), flower_mat)
        # Short horizontal crown run lets adjacent instances visually knit over the rim.
        if strand < strands - 1:
            next_y = -width * 0.5 + width * (strand + 1.5) / strands
            mesh.cylinder(top, (top[0], next_y, top[2] + rng.uniform(-2, 2)),
                          0.8, 0.8, 7, stem_mat)
    return mesh


def write_mtl() -> None:
    materials = {
        "M_Planter_AgedConcrete": ((0.29, 0.31, 0.28), 0.0, 0.88),
        "M_Planter_CastRepair": ((0.38, 0.36, 0.30), 0.0, 0.82),
        "M_Planter_Soil": ((0.09, 0.07, 0.045), 0.0, 0.95),
        "M_Dracaena_Cane": ((0.27, 0.21, 0.13), 0.0, 0.72),
        "M_Dracaena_LeafScar": ((0.18, 0.14, 0.09), 0.0, 0.78),
        "M_Dracaena_Leaf": ((0.14, 0.25, 0.12), 0.0, 0.54),
        "M_ZZ_Stem": ((0.20, 0.32, 0.14), 0.0, 0.38),
        "M_ZZ_Leaf": ((0.10, 0.25, 0.11), 0.0, 0.24),
        "M_MorningGlory_Stem": ((0.18, 0.30, 0.13), 0.0, 0.52),
        "M_MorningGlory_Leaf": ((0.20, 0.39, 0.19), 0.0, 0.42),
        "M_MorningGlory_Flower": ((0.22, 0.31, 0.68), 0.0, 0.36),
    }
    lines = ["# Unreal material-slot placeholder library"]
    for name, (colour, metallic, roughness) in materials.items():
        lines.extend((f"newmtl {name}", f"Kd {colour[0]} {colour[1]} {colour[2]}",
                      f"Pm {metallic}", f"Pr {roughness}", ""))
    (OUT / MTL_NAME).write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    meshes = [build_planter(), build_endcap(),
              build_dracaena("VD_Dracaena_A", 145, 2, 4101),
              build_dracaena("VD_Dracaena_B", 170, 3, 4102),
              build_dracaena("VD_Dracaena_C", 195, 3, 4103),
              build_zz("VD_ZZPlant_A", 54, 7, 4201),
              build_zz("VD_ZZPlant_B", 66, 9, 4202),
              build_zz("VD_ZZPlant_C", 78, 11, 4203),
              build_morning_glory("VD_DwarfMorningGlory_A", 92, 4, 4301),
              build_morning_glory("VD_DwarfMorningGlory_B", 118, 5, 4302),
              build_morning_glory("VD_DwarfMorningGlory_C", 144, 6, 4303)]
    write_mtl()
    for mesh in meshes:
        mins = [min(point[axis] for point in mesh.vertices) for axis in range(3)]
        maxs = [max(point[axis] for point in mesh.vertices) for axis in range(3)]
        offset = (-(mins[0] + maxs[0]) * 0.5,
                  -(mins[1] + maxs[1]) * 0.5,
                  -mins[2])
        mesh.vertices = [add(point, offset) for point in mesh.vertices]
        mesh.write_obj(OUT / f"{mesh.name}.obj")
    manifest = {
        "units": "centimetres; Z-up",
        "module_length_y_cm": 245.0,
        "planter_size_cm": [126.0, 245.0, 110.0],
        "mesh_count": len(meshes),
        "meshes": [{"name": m.name, "vertices": len(m.vertices), "faces": len(m.faces)} for m in meshes],
    }
    (QA / "generation_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate the entrance-terrace planter, foliage-card textures, and botanical OBJs.

Units are Unreal centimetres, Z-up. Every OBJ has one object, no group records,
indexed UVs on every face corner, and RGB vertex colours. Foliage stiffness is
encoded as grayscale vertex colour: attachment/root = 0, free tip = 1.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "SourceMesh" / "terrace_botanical"
CUTOUTS = ROOT / "cutouts" / "terrace_botanical"
QA = ROOT / "qa" / "terrace_planter_botanical"
MTL_NAME = "VD_TerraceBotanical.mtl"
Vec3 = tuple[float, float, float]
UV = tuple[float, float]
Colour = tuple[float, float, float]


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


def stiffness(value: float) -> Colour:
    value = max(0.0, min(1.0, value))
    return (value, value, value)


@dataclass
class Face:
    material: str
    indices: tuple[int, ...]
    uvs: tuple[UV, ...]


@dataclass
class Mesh:
    name: str
    vertices: list[Vec3] = field(default_factory=list)
    colours: list[Colour] = field(default_factory=list)
    faces: list[Face] = field(default_factory=list)

    def vertex(self, point: Vec3, colour: Colour = (0.0, 0.0, 0.0)) -> int:
        self.vertices.append(point)
        self.colours.append(colour)
        return len(self.vertices)

    def face(self, material: str, indices: Iterable[int], uvs: Iterable[UV] | None = None) -> None:
        ids = tuple(indices)
        mapped = tuple(uvs) if uvs is not None else ()
        if mapped and len(ids) != len(mapped):
            raise ValueError("face vertex and UV counts differ")
        self.faces.append(Face(material, ids, mapped))

    def quad(self, points: tuple[Vec3, Vec3, Vec3, Vec3], material: str,
             uvs: tuple[UV, UV, UV, UV] = ((0, 0), (0, 1), (1, 1), (1, 0)),
             colours: tuple[Colour, Colour, Colour, Colour] | None = None) -> None:
        resolved_colours: tuple[Colour, Colour, Colour, Colour] = colours or (
            (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        ids = tuple(self.vertex(point, colour) for point, colour in zip(points, resolved_colours))
        self.face(material, ids, uvs)

    def box(self, minimum: Vec3, maximum: Vec3, material: str) -> None:
        x0, y0, z0 = minimum
        x1, y1, z1 = maximum
        ids = [self.vertex((x, y, z)) for z in (z0, z1)
               for y in (y0, y1) for x in (x0, x1)]
        for face in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
                     (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            self.face(material, tuple(ids[i] for i in face))

    def cylinder(self, start: Vec3, end: Vec3, radius0: float, radius1: float,
                 sides: int, material: str, weight0: float = 0.0,
                 weight1: float = 0.0, capped: bool = True) -> None:
        axis = normalize(sub(end, start))
        seed = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.9 else (1.0, 0.0, 0.0)
        side = normalize(cross(axis, seed))
        up = cross(axis, side)
        rings: list[list[int]] = []
        for point, radius, weight in ((start, radius0, weight0), (end, radius1, weight1)):
            ring = []
            for index in range(sides):
                angle = 2 * math.pi * index / sides
                offset = add(mul(side, math.cos(angle) * radius),
                             mul(up, math.sin(angle) * radius))
                ring.append(self.vertex(add(point, offset), stiffness(weight)))
            rings.append(ring)
        if capped:
            self.face(material, reversed(rings[0]))
            self.face(material, rings[1])
        for index in range(sides):
            following = (index + 1) % sides
            self.face(material, (rings[0][index], rings[0][following],
                                 rings[1][following], rings[1][index]))

    def dracaena_card(self, start: Vec3, azimuth: float, leaf_length: float,
                      width: float, rise: float, tip_drop: float, twist: float) -> None:
        """One curved alpha ribbon: three quads / six triangles / four wind rows."""
        direction = (math.cos(azimuth), math.sin(azimuth), 0.0)
        lateral = (-direction[1], direction[0], 0.0)
        rows: list[tuple[int, int]] = []
        row_positions = (0.0, 0.26, 0.62, 1.0)
        for t in row_positions:
            radial = leaf_length * (t ** 0.76)
            centre = add(start, (direction[0] * radial,
                                 direction[1] * radial,
                                 rise * math.sin(math.pi * t) - tip_drop * (t ** 1.65)))
            angle = twist * t
            local_lateral = normalize(add(mul(lateral, math.cos(angle)),
                                          (0.0, 0.0, math.sin(angle))))
            # The alpha sheet supplies the final taper; geometry only narrows the last row.
            half = width * (0.5 if t < 0.99 else 0.22)
            rows.append((self.vertex(add(centre, mul(local_lateral, -half)), stiffness(t)),
                         self.vertex(add(centre, mul(local_lateral, half)), stiffness(t))))
        for index in range(3):
            a, b = rows[index]
            c, d = rows[index + 1]
            t0, t1 = row_positions[index], row_positions[index + 1]
            self.face("M_Dracaena_Leaf", (a, c, d, b), ((0, t0), (0, t1), (1, t1), (1, t0)))

    def zz_leaflet_pair(self, centre: Vec3, tangent: Vec3, lateral: Vec3,
                        spread: float, leaflet_length: float, width: float,
                        weight: float) -> None:
        """Paired leaflet section: two alpha quads / four triangles total."""
        tangent = normalize(tangent)
        lateral = normalize(lateral)
        # Nearly horizontal upper faces catch light; small tangent offset prevents a ruler row.
        for side, u0, u1 in ((-1, 0.0, 0.5), (1, 0.5, 1.0)):
            base = add(centre, add(mul(lateral, side * 1.4), mul(tangent, -1.0)))
            tip = add(centre, add(mul(lateral, side * spread), mul(tangent, leaflet_length * 0.18)))
            along = normalize(sub(tip, base))
            across = normalize(cross((0.0, 0.0, 1.0), along))
            if length(across) < 0.2:
                across = tangent
            points = (add(base, mul(across, -width * 0.25)),
                      add(tip, mul(across, -width * 0.5)),
                      add(tip, mul(across, width * 0.5)),
                      add(base, mul(across, width * 0.25)))
            w0, w1 = stiffness(max(0, weight - 0.08)), stiffness(min(1, weight + 0.12))
            self.quad(points, "M_ZZ_Leaf", ((u0, 0), (u0, 1), (u1, 1), (u1, 0)),
                      (w0, w1, w1, w0))

    def heart_card(self, centre: Vec3, size: float, yaw: float, weight: float) -> None:
        """Six-triangle alpha card with a heart-like geometry silhouette."""
        side = (0.0, math.cos(yaw), math.sin(yaw) * 0.18)
        up = (0.0, -math.sin(yaw) * 0.12, 1.0)
        points = [add(centre, add(mul(side, sx * size), mul(up, sz * size)))
                  for sx, sz in ((0, -0.55), (-0.58, 0.02), (-0.46, 0.50),
                                 (0, 0.34), (0.46, 0.50), (0.58, 0.02))]
        centre_id = self.vertex(centre, stiffness(weight))
        ids = [self.vertex(point, stiffness(min(1, weight + max(0, sz) * 0.15)))
               for point, (_, sz) in zip(points, ((0, -0.55), (-0.58, 0.02), (-0.46, 0.50),
                                                      (0, 0.34), (0.46, 0.50), (0.58, 0.02)))]
        uvs = ((0.30, 0.55), (0.30, 0.94), (0.04, 0.58), (0.08, 0.10),
               (0.30, 0.25), (0.52, 0.10), (0.56, 0.58))
        for index in range(6):
            following = (index + 1) % 6
            self.face("M_MorningGlory_Leaf", (centre_id, ids[index], ids[following]),
                      (uvs[0], uvs[index + 1], uvs[following + 1]))

    def flower_card(self, centre: Vec3, radius: float, weight: float, roll: float) -> None:
        side = (0.0, math.cos(roll), math.sin(roll) * 0.3)
        up = (0.0, -math.sin(roll) * 0.2, 1.0)
        centre_id = self.vertex(centre, stiffness(weight))
        ring = []
        for index in range(8):
            angle = 2 * math.pi * index / 8
            petal = radius * (1.0 + 0.12 * math.cos(5 * angle))
            ring.append(self.vertex(add(centre, add(mul(side, math.cos(angle) * petal),
                                                     mul(up, math.sin(angle) * petal))),
                                    stiffness(min(1, weight + 0.1))))
        uv_c = (0.79, 0.50)
        for index in range(8):
            following = (index + 1) % 8
            a = 2 * math.pi * index / 8
            b = 2 * math.pi * following / 8
            self.face("M_MorningGlory_Flower", (centre_id, ring[index], ring[following]),
                      (uv_c, (0.79 + 0.18 * math.cos(a), 0.50 + 0.18 * math.sin(a)),
                       (0.79 + 0.18 * math.cos(b), 0.50 + 0.18 * math.sin(b))))

    def project_uvs(self, face: tuple[int, ...], scale: float = 100.0) -> list[UV]:
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
        has_wind_colours = any(any(channel > 0.0 for channel in colour) for colour in self.colours)
        lines = ["# Generated by scripts/generate_terrace_planter_botanical_kit.py",
                 f"mtllib {MTL_NAME}", f"o {self.name}"]
        if has_wind_colours:
            lines.insert(1, "# Vertex RGB encodes wind stiffness: 0=root/rigid, 1=free tip")
            lines.extend(f"v {x:.6f} {y:.6f} {z:.6f} {r:.6f} {g:.6f} {b:.6f}"
                         for (x, y, z), (r, g, b) in zip(self.vertices, self.colours))
        else:
            lines.extend(f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in self.vertices)
        next_uv = 1
        face_uv_indices: list[tuple[int, ...]] = []
        for face in self.faces:
            mapped_uvs = face.uvs or tuple(self.project_uvs(face.indices))
            lines.extend(f"vt {u:.6f} {v:.6f}" for u, v in mapped_uvs)
            face_uv_indices.append(tuple(range(next_uv, next_uv + len(mapped_uvs))))
            next_uv += len(mapped_uvs)
        current = None
        for face, uv_ids in zip(self.faces, face_uv_indices):
            if face.material != current:
                lines.extend((f"usemtl {face.material}", "s 1"))
                current = face.material
            lines.append("f " + " ".join(f"{v}/{uv}" for v, uv in zip(face.indices, uv_ids)))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_planter() -> Mesh:
    mesh = Mesh("VD_TerracePlanter")
    concrete, repair, soil = "M_Planter_AgedConcrete", "M_Planter_CastRepair", "M_Planter_Soil"
    mesh.box((-60, -122.5, 0), (-47, 122.5, 102), concrete)
    mesh.box((47, -122.5, 0), (60, 122.5, 102), concrete)
    mesh.box((-47, -122.5, 0), (47, 122.5, 12), concrete)
    mesh.box((-63, -122.5, 102), (-42, 122.5, 110), repair)
    mesh.box((42, -122.5, 102), (63, 122.5, 110), repair)
    mesh.box((-46.5, -122.5, 86), (46.5, 122.5, 93), soil)
    for y in (-61.25, 61.25):
        mesh.cylinder((-60.5, y, 22), (-47.0, y, 22), 4.5, 4.5, 10, repair)
    return mesh


def build_endcap() -> Mesh:
    mesh = Mesh("VD_TerracePlanter_EndCap")
    concrete, repair = "M_Planter_AgedConcrete", "M_Planter_CastRepair"
    mesh.box((-60, -4, 0), (60, 4, 102), concrete)
    mesh.box((-63, -6, 102), (63, 6, 110), repair)
    for x in (-45, 45):
        for z in (28, 78):
            mesh.cylinder((x, -7, z), (x, -3, z), 3.2, 3.2, 8, repair)
    return mesh


def build_dracaena(name: str, height: float, canes: int, leaves_per_head: int, seed: int) -> Mesh:
    rng = random.Random(seed)
    mesh = Mesh(name)
    for cane_index in range(canes):
        angle = 2 * math.pi * cane_index / canes + rng.uniform(-0.42, 0.42)
        radius = 7 + 9 * (cane_index / max(1, canes - 1))
        base = (math.cos(angle) * radius, math.sin(angle) * radius, 0.0)
        cane_height = height * rng.uniform(0.77 if canes > 1 else 0.94, 0.98)
        top = add(base, (rng.uniform(-4, 4), rng.uniform(-4, 4), cane_height))
        # Smooth tapered canes; no bamboo-like annular geometry.
        mesh.cylinder(base, top, rng.uniform(4.1, 5.3), rng.uniform(2.8, 3.8),
                      10, "M_Dracaena_Cane", 0.0, 0.10)
        crown = add(top, (0, 0, -1.5))
        for leaf_index in range(leaves_per_head):
            cohort = leaf_index % 10
            azimuth = 2 * math.pi * leaf_index / leaves_per_head + rng.uniform(-0.10, 0.10)
            if cohort < 2:  # young centre spears break the umbrella/helmet profile
                leaf_length, rise, drop = rng.uniform(40, 48), rng.uniform(24, 34), rng.uniform(4, 12)
            elif cohort < 5:
                leaf_length, rise, drop = rng.uniform(48, 60), rng.uniform(17, 27), rng.uniform(20, 34)
            else:  # mature outer leaves carry the low mop silhouette
                leaf_length, rise, drop = rng.uniform(58, 70), rng.uniform(9, 18), rng.uniform(38, 56)
            attachment = add(crown, (rng.uniform(-1.4, 1.4), rng.uniform(-1.4, 1.4),
                                     rng.uniform(-4.0, 4.0)))
            mesh.dracaena_card(attachment, azimuth, leaf_length, rng.uniform(2.4, 3.8),
                               rise, drop, rng.uniform(-0.45, 0.45))
    return mesh


def bezier3(a: Vec3, b: Vec3, c: Vec3, t: float) -> Vec3:
    return add(add(mul(a, (1 - t) ** 2), mul(b, 2 * (1 - t) * t)), mul(c, t * t))


def build_zz(name: str, target_height: float, fronds: int, seed: int) -> Mesh:
    rng = random.Random(seed)
    mesh = Mesh(name)
    for frond in range(fronds):
        angle = 2 * math.pi * frond / fronds + rng.uniform(-0.25, 0.25)
        height = target_height * rng.uniform(0.82, 1.0)
        reach = rng.uniform(28, 46) * (height / 70)
        p0 = (rng.uniform(-5, 5), rng.uniform(-5, 5), 0.0)
        p1 = (math.cos(angle) * reach * 0.35, math.sin(angle) * reach * 0.35, height * 0.78)
        p2 = (math.cos(angle) * reach, math.sin(angle) * reach, height * rng.uniform(0.72, 0.88))
        last = p0
        segments = 5
        for segment in range(1, segments + 1):
            t = segment / segments
            point = bezier3(p0, p1, p2, t)
            mesh.cylinder(last, point, 1.5 * (1 - t * 0.45), 1.5 * (1 - t * 0.55),
                          7, "M_ZZ_Stem", max(0, (t - 0.25) * 0.38), t * 0.48)
            last = point
        pair_count = rng.randint(5, 8)  # 10–16 leaflets per frond.
        for pair in range(pair_count):
            t = 0.30 + pair * (0.62 / max(1, pair_count - 1))
            q = bezier3(p0, p1, p2, t)
            q2 = bezier3(p0, p1, p2, min(1, t + 0.02))
            tangent = normalize(sub(q2, q))
            lateral = normalize(cross(tangent, (0.0, 0.0, 1.0)))
            if length(lateral) < 0.2:
                lateral = (-math.sin(angle), math.cos(angle), 0.0)
            mesh.zz_leaflet_pair(q, tangent, lateral, rng.uniform(12, 18),
                                 rng.uniform(14, 21), rng.uniform(7, 10), t)
    return mesh


def build_morning_glory(name: str, width: float, strands: int, seed: int) -> Mesh:
    rng = random.Random(seed)
    mesh = Mesh(name)
    for strand in range(strands):
        y = -width * 0.5 + width * (strand + 0.5) / strands + rng.uniform(-3, 3)
        top = (rng.uniform(-1, 1), y, rng.uniform(93, 103))
        mid = (rng.uniform(-18, -10), y + rng.uniform(-6, 6), rng.uniform(48, 64))
        bottom = (rng.uniform(-26, -16), y + rng.uniform(-8, 8), rng.uniform(2, 11))
        mesh.cylinder(bottom, mid, 1.05, 0.9, 6, "M_MorningGlory_Stem", 0.35, 0.12)
        mesh.cylinder(mid, top, 0.9, 0.7, 6, "M_MorningGlory_Stem", 0.12, 0.0)
        leaf_count = rng.randint(7, 9)
        for index in range(leaf_count):
            t = 0.08 + index * (0.84 / max(1, leaf_count - 1))
            q = bezier3(bottom, mid, top, t)
            side = -1 if (index + strand) % 2 else 1
            leaf_centre = add(q, (-rng.uniform(1.5, 4.5), side * rng.uniform(5, 9), rng.uniform(-1, 3)))
            mesh.heart_card(leaf_centre, rng.uniform(10, 14), rng.uniform(-0.35, 0.35), 0.2 + 0.75 * (1 - t))
            # Put blooms on the visitor-facing outer X side, not buried behind the drape.
            if index >= 1 and (index % 3 == strand % 3 or rng.random() < 0.18):
                flower_centre = add(q, (-rng.uniform(8, 13), side * rng.uniform(2, 7), rng.uniform(-1, 5)))
                mesh.flower_card(flower_centre, rng.uniform(6.5, 8.8), 0.28 + 0.65 * (1 - t),
                                 rng.uniform(-0.5, 0.5))
        if strand < strands - 1:
            next_y = -width * 0.5 + width * (strand + 1.5) / strands
            mesh.cylinder(top, (top[0], next_y, top[2] + rng.uniform(-2, 2)),
                          0.7, 0.7, 6, "M_MorningGlory_Stem", 0.0, 0.1)
    return mesh


def supersampled_texture(draw_fn, path: Path) -> None:
    scale = 4
    image = Image.new("RGBA", (1024 * scale, 1024 * scale), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(image, "RGBA"), scale)
    image.resize((1024, 1024), Image.Resampling.LANCZOS).save(path)


def write_cutouts() -> None:
    CUTOUTS.mkdir(parents=True, exist_ok=True)

    def dracaena(draw: ImageDraw.ImageDraw, s: int) -> None:
        pts = [(512, 990), (450, 810), (432, 420), (472, 78), (512, 20),
               (552, 78), (592, 420), (574, 810)]
        draw.polygon([(x * s, y * s) for x, y in pts], fill=(44, 92, 43, 255))
        draw.line([(512 * s, 960 * s), (510 * s, 80 * s)], fill=(87, 132, 64, 180), width=7 * s)
        draw.line([(466 * s, 790 * s), (458 * s, 310 * s)], fill=(92, 25, 39, 230), width=9 * s)
        draw.line([(558 * s, 790 * s), (566 * s, 310 * s)], fill=(92, 25, 39, 230), width=9 * s)

    def zz(draw: ImageDraw.ImageDraw, s: int) -> None:
        # Paired glossy leaflets with transparent centre/outer silhouette.
        left = [(500, 548), (430, 432), (250, 326), (74, 350), (26, 486),
                (94, 614), (278, 652), (446, 590)]
        right = [(524, 548), (594, 432), (774, 326), (950, 350), (998, 486),
                 (930, 614), (746, 652), (578, 590)]
        draw.polygon([(x * s, y * s) for x, y in left], fill=(37, 104, 47, 255))
        draw.polygon([(x * s, y * s) for x, y in right], fill=(33, 96, 42, 255))
        draw.line([(490 * s, 546 * s), (82 * s, 478 * s)], fill=(101, 157, 89, 210), width=7 * s)
        draw.line([(534 * s, 546 * s), (942 * s, 478 * s)], fill=(93, 149, 80, 210), width=7 * s)

    def morning_glory(draw: ImageDraw.ImageDraw, s: int) -> None:
        # Non-overlapping slots: heart leaf on the left, flower on the right.
        leaf = [(307, 950), (42, 590), (58, 196), (176, 76), (307, 250),
                (438, 76), (556, 196), (572, 590)]
        draw.polygon([(x * s, y * s) for x, y in leaf], fill=(58, 137, 65, 255))
        draw.line([(307 * s, 904 * s), (307 * s, 220 * s)], fill=(118, 173, 94, 190), width=8 * s)
        centre = (808 * s, 512 * s)
        ring = []
        for index in range(40):
            angle = 2 * math.pi * index / 40
            radius = (178 + 18 * math.cos(5 * angle)) * s
            ring.append((centre[0] + math.cos(angle) * radius, centre[1] + math.sin(angle) * radius))
        draw.polygon(ring, fill=(93, 110, 210, 255))
        draw.ellipse((746 * s, 450 * s, 870 * s, 574 * s), fill=(234, 202, 221, 230))
        draw.ellipse((784 * s, 488 * s, 832 * s, 536 * s), fill=(246, 223, 133, 255))

    supersampled_texture(dracaena, CUTOUTS / "dracaena_marginata_leaf_rgba_1024.png")
    supersampled_texture(zz, CUTOUTS / "zz_leaflet_pair_rgba_1024.png")
    supersampled_texture(morning_glory, CUTOUTS / "morning_glory_leaf_flower_rgba_1024.png")


def write_mtl() -> None:
    materials = {
        "M_Planter_AgedConcrete": ((0.29, 0.31, 0.28), 0.0, 0.88, None),
        "M_Planter_CastRepair": ((0.38, 0.36, 0.30), 0.0, 0.82, None),
        "M_Planter_Soil": ((0.09, 0.07, 0.045), 0.0, 0.95, None),
        "M_Dracaena_Cane": ((0.27, 0.21, 0.13), 0.0, 0.72, None),
        "M_Dracaena_Leaf": ((0.14, 0.25, 0.12), 0.0, 0.54, "dracaena_marginata_leaf_rgba_1024.png"),
        "M_ZZ_Stem": ((0.20, 0.32, 0.14), 0.0, 0.38, None),
        "M_ZZ_Leaf": ((0.10, 0.25, 0.11), 0.0, 0.24, "zz_leaflet_pair_rgba_1024.png"),
        "M_MorningGlory_Stem": ((0.18, 0.30, 0.13), 0.0, 0.52, None),
        "M_MorningGlory_Leaf": ((0.20, 0.39, 0.19), 0.0, 0.42, "morning_glory_leaf_flower_rgba_1024.png"),
        "M_MorningGlory_Flower": ((0.22, 0.31, 0.68), 0.0, 0.36, "morning_glory_leaf_flower_rgba_1024.png"),
    }
    lines = ["# Unreal material-slot placeholder library"]
    for name, (colour, metallic, roughness, texture) in materials.items():
        lines.extend((f"newmtl {name}", f"Kd {colour[0]} {colour[1]} {colour[2]}",
                      f"Pm {metallic}", f"Pr {roughness}"))
        if texture:
            relative = f"../../cutouts/terrace_botanical/{texture}"
            lines.extend((f"map_Kd {relative}", f"map_d {relative}"))
        lines.append("")
    (OUT / MTL_NAME).write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    write_cutouts()
    meshes = [build_planter(), build_endcap(),
              build_dracaena("VD_Dracaena_A", 158, 2, 52, 4101),
              build_dracaena("VD_Dracaena_B", 178, 3, 58, 4102),
              build_dracaena("VD_Dracaena_C", 202, 3, 64, 4103),
              build_zz("VD_ZZPlant_A", 75, 7, 4201),
              build_zz("VD_ZZPlant_B", 88, 9, 4202),
              build_zz("VD_ZZPlant_C", 100, 11, 4203),
              build_morning_glory("VD_DwarfMorningGlory_A", 98, 6, 4301),
              build_morning_glory("VD_DwarfMorningGlory_B", 126, 8, 4302),
              build_morning_glory("VD_DwarfMorningGlory_C", 154, 10, 4303)]
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
        "foliage_contract": {
            "alpha_cut_rgba_sheets": 3,
            "wind_encoding": "OBJ vertex RGB grayscale; 0=root/attachment, 1=free tip",
            "dracaena_leaves_per_head": [52, 58, 64],
            "zz_fronds_per_crown": [7, 9, 11],
            "zz_leaflets_per_frond": "10-16",
            "morning_glory_strands": [6, 8, 10],
        },
        "meshes": [{"name": m.name, "vertices": len(m.vertices), "faces": len(m.faces)} for m in meshes],
    }
    (QA / "generation_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

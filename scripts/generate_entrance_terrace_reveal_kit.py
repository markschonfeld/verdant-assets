#!/usr/bin/env python3
"""Generate the Rootstead entrance-terrace reveal kit (vertical slice 1).

Assets in this slice:
  * Two large round specimen planters (aged cast concrete + period glazed
    ceramic), open-looking with visible dressed soil.
  * One Phoenix/date-palm hero specimen: real trunk geometry carrying a
    diamond leaf-base lattice, arching pinnate fronds built from alpha-cut
    leaflet ribbons. RGB vertex colour encodes wind stiffness on every vertex.
  * Three separate scatterable soil-dressing meshes: uneven soil mound,
    leaf/bark litter cards, and a small stone cluster.

Units are Unreal centimetres, Z-up. Every OBJ has exactly one `o` record, no
`g` records, named `usemtl` slots, indexed UVs on every face corner, and a
Z=0 / base-centred origin. One object per OBJ. Foliage stiffness is encoded as
grayscale vertex colour: attachment/root = 0, free tip = 1.
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
OUT = ROOT / "SourceMesh" / "entrance_terrace_reveal"
CUTOUTS = ROOT / "cutouts" / "entrance_terrace_reveal"
QA = ROOT / "qa" / "entrance_terrace_reveal"
DOCS = ROOT / "docs"
MTL_NAME = "VD_EntranceTerraceReveal.mtl"
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
    if size < 1e-9:
        return (0.0, 0.0, 1.0)
    return mul(a, 1.0 / size)


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def stiffness(value: float) -> Colour:
    value = max(0.0, min(1.0, value))
    return (value, value, value)


def bezier3(a: Vec3, b: Vec3, c: Vec3, t: float) -> Vec3:
    return add(add(mul(a, (1 - t) ** 2), mul(b, 2 * (1 - t) * t)), mul(c, t * t))


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
        resolved: tuple[Colour, Colour, Colour, Colour] = colours or (
            (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        ids = tuple(self.vertex(point, colour) for point, colour in zip(points, resolved))
        self.face(material, ids, uvs)

    def ring(self, centre: Vec3, radius: float, sides: int, weight: float = 0.0,
             phase: float = 0.0) -> list[int]:
        ids = []
        for index in range(sides):
            angle = 2 * math.pi * index / sides + phase
            offset = (math.cos(angle) * radius, math.sin(angle) * radius, 0.0)
            ids.append(self.vertex(add(centre, offset), stiffness(weight)))
        return ids

    def bridge(self, lower: list[int], upper: list[int], material: str, flip: bool = False) -> None:
        count = len(lower)
        for index in range(count):
            following = (index + 1) % count
            if flip:
                self.face(material, (lower[index], upper[index], upper[following], lower[following]))
            else:
                self.face(material, (lower[index], lower[following], upper[following], upper[index]))

    def cap(self, ring: list[int], centre: int, material: str, reverse: bool = False) -> None:
        count = len(ring)
        for index in range(count):
            following = (index + 1) % count
            if reverse:
                self.face(material, (centre, ring[following], ring[index]))
            else:
                self.face(material, (centre, ring[index], ring[following]))

    def cylinder(self, start: Vec3, end: Vec3, radius0: float, radius1: float,
                 sides: int, material: str, weight0: float = 0.0,
                 weight1: float = 0.0, capped: bool = False) -> None:
        axis = normalize(sub(end, start))
        seed = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.9 else (1.0, 0.0, 0.0)
        side = normalize(cross(axis, seed))
        up = cross(axis, side)
        rings: list[list[int]] = []
        for point, radius, weight in ((start, radius0, weight0), (end, radius1, weight1)):
            row = []
            for index in range(sides):
                angle = 2 * math.pi * index / sides
                offset = add(mul(side, math.cos(angle) * radius),
                             mul(up, math.sin(angle) * radius))
                row.append(self.vertex(add(point, offset), stiffness(weight)))
            rings.append(row)
        if capped:
            self.face(material, tuple(reversed(rings[0])))
            self.face(material, tuple(rings[1]))
        for index in range(sides):
            following = (index + 1) % sides
            self.face(material, (rings[0][index], rings[0][following],
                                 rings[1][following], rings[1][index]))

    def leaflet(self, base: Vec3, direction: Vec3, across: Vec3, leaf_length: float,
                half_width: float, weight_base: float, weight_tip: float,
                u0: float, u1: float) -> None:
        """One alpha-cut pinnate leaflet: two quads / four triangles / three wind rows."""
        direction = normalize(direction)
        across = normalize(across)
        rows = (0.0, 0.5, 1.0)
        pairs: list[tuple[int, int]] = []
        for t in rows:
            centre = add(base, mul(direction, leaf_length * t))
            half = half_width * (1.0 - 0.55 * t)  # blade narrows toward the tip
            weight = weight_base + (weight_tip - weight_base) * t
            pairs.append((self.vertex(add(centre, mul(across, -half)), stiffness(weight)),
                          self.vertex(add(centre, mul(across, half)), stiffness(weight))))
        for index in range(2):
            a, b = pairs[index]
            c, d = pairs[index + 1]
            t0, t1 = rows[index], rows[index + 1]
            self.face("M_DatePalm_Leaflet", (a, c, d, b),
                      ((u0, t0), (u0, t1), (u1, t1), (u1, t0)))

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
        has_wind = any(any(channel > 0.0 for channel in colour) for colour in self.colours)
        lines = ["# Generated by scripts/generate_entrance_terrace_reveal_kit.py",
                 f"mtllib {MTL_NAME}", f"o {self.name}"]
        if has_wind:
            lines.insert(1, "# Vertex RGB encodes wind stiffness: 0=root/rigid, 1=free tip")
            lines.extend(f"v {x:.6f} {y:.6f} {z:.6f} {r:.6f} {g:.6f} {b:.6f}"
                         for (x, y, z), (r, g, b) in zip(self.vertices, self.colours))
        else:
            lines.extend(f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in self.vertices)
        next_uv = 1
        face_uv_indices: list[tuple[int, ...]] = []
        for face in self.faces:
            mapped = face.uvs or tuple(self.project_uvs(face.indices))
            lines.extend(f"vt {u:.6f} {v:.6f}" for u, v in mapped)
            face_uv_indices.append(tuple(range(next_uv, next_uv + len(mapped))))
            next_uv += len(mapped)
        current = None
        for face, uv_ids in zip(self.faces, face_uv_indices):
            if face.material != current:
                lines.extend((f"usemtl {face.material}", "s 1"))
                current = face.material
            lines.append("f " + " ".join(f"{v}/{uv}" for v, uv in zip(face.indices, uv_ids)))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
#  Round specimen planters
# --------------------------------------------------------------------------- #

def build_round_planter(name: str, diameter: float, height: float, body_mat: str,
                        rim_mat: str, soil_mat: str, seed: int, sides: int = 48) -> Mesh:
    """Open urn-form planter: widening body, rim lip, inner wall, dressed soil.

    The interior stays hollow below the visible soil disc, so collision must be
    authored as a segmented ring (see handoff) and never a single convex hull.
    """
    rng = random.Random(seed)
    mesh = Mesh(name)
    radius = diameter / 2.0
    wall = radius * 0.09
    foot_frac = 0.72
    soil_depth = height * 0.18
    levels = 8

    def outer_radius(fraction: float) -> float:
        return radius * (foot_frac + (1 - foot_frac) * math.sin(fraction * math.pi * 0.5))

    outer_rings = [mesh.ring((0, 0, (i / levels) * height), outer_radius(i / levels), sides)
                   for i in range(levels + 1)]
    for i in range(levels):
        mesh.bridge(outer_rings[i], outer_rings[i + 1], body_mat)
    base_centre = mesh.vertex((0, 0, 0))
    mesh.cap(outer_rings[0], base_centre, body_mat, reverse=True)

    inner_top_r = radius - wall
    inner_top = mesh.ring((0, 0, height), inner_top_r, sides)
    mesh.bridge(outer_rings[levels], inner_top, rim_mat)  # rim annulus / lip

    soil_z = height - soil_depth
    inner_bot_r = inner_top_r * 0.93
    inner_bot = mesh.ring((0, 0, soil_z), inner_bot_r, sides)
    mesh.bridge(inner_top, inner_bot, body_mat, flip=True)  # inner wall faces inward

    # Build the dressed soil as several irregular concentric contours rather
    # than one centre fan.  The latter reads as a flat polygonal lid in engine;
    # these contours create a shallow, uneven mound right up to the inner wall.
    soil_rings: list[list[int]] = []
    for ring_index, radius_fraction in enumerate((0.96, 0.70, 0.38)):
        ring = []
        phase = rng.uniform(-0.04, 0.04)
        for index in range(sides):
            angle = 2 * math.pi * index / sides + phase
            radial_noise = rng.uniform(0.965, 1.025)
            rr = inner_bot_r * radius_fraction * radial_noise
            broad_undulation = math.sin(angle * 3.0 + seed * 0.17) * (1.2 + ring_index * 0.45)
            local_bump = rng.uniform(-0.9, 1.8)
            rise = (1.0 - radius_fraction) * 8.5
            ring.append(mesh.vertex((math.cos(angle) * rr, math.sin(angle) * rr,
                                     soil_z + rise + broad_undulation + local_bump)))
        soil_rings.append(ring)
    mesh.bridge(inner_bot, soil_rings[0], body_mat, flip=True)
    mesh.bridge(soil_rings[0], soil_rings[1], soil_mat)
    mesh.bridge(soil_rings[1], soil_rings[2], soil_mat)
    soil_centre = mesh.vertex((rng.uniform(-4, 4), rng.uniform(-4, 4),
                               soil_z + 9.0 + rng.uniform(-0.6, 1.2)))
    mesh.cap(soil_rings[2], soil_centre, soil_mat)
    return mesh


# --------------------------------------------------------------------------- #
#  Date palm hero specimen
# --------------------------------------------------------------------------- #

def add_diamond_bosses(mesh: Mesh, trunk_height: float, base_r: float, top_r: float,
                       material: str) -> None:
    """Raised diamond leaf-base scars in a quincunx lattice around the trunk."""
    sides = 8
    row_spacing = 21.0
    z = 14.0
    row = 0
    while z < trunk_height - 14.0:
        fraction = z / trunk_height
        radius = base_r + (top_r - base_r) * fraction
        half_h = row_spacing * 0.42
        half_ang = (2 * math.pi / sides) * 0.40
        phase = (math.pi / sides) if row % 2 else 0.0
        for index in range(sides):
            angle = 2 * math.pi * index / sides + phase

            def surf(a: float, zz: float, rr: float) -> Vec3:
                return (math.cos(a) * rr, math.sin(a) * rr, zz)

            top = mesh.vertex(surf(angle, z + half_h, radius))
            bot = mesh.vertex(surf(angle, z - half_h, radius))
            left = mesh.vertex(surf(angle - half_ang, z, radius))
            right = mesh.vertex(surf(angle + half_ang, z, radius))
            apex = mesh.vertex(surf(angle, z, radius + 4.2))
            for a, b in ((top, right), (right, bot), (bot, left), (left, top)):
                mesh.face(material, (a, b, apex))
        z += row_spacing
        row += 1


def build_frond(mesh: Mesh, crown: Vec3, azimuth: float, out1: float, rise1: float,
                out2: float, dz2: float, base_len: float, rng: random.Random) -> None:
    out_dir = (math.cos(azimuth), math.sin(azimuth), 0.0)
    p0 = crown
    p1 = add(crown, add(mul(out_dir, out1), (0.0, 0.0, rise1)))
    p2 = add(crown, add(mul(out_dir, out2), (0.0, 0.0, dz2)))

    segments = 7
    last = p0
    for segment in range(1, segments + 1):
        t = segment / segments
        point = bezier3(p0, p1, p2, t)
        mesh.cylinder(last, point, 2.2 * (1 - 0.7 * (segment - 1) / segments),
                      2.2 * (1 - 0.7 * t), 6, "M_DatePalm_Rachis",
                      min(0.9, (segment - 1) / segments * 0.9), min(0.95, t * 0.95))
        last = point

    pairs = 24
    for index in range(pairs):
        t = 0.10 + index * (0.86 / (pairs - 1))
        q = bezier3(p0, p1, p2, t)
        q2 = bezier3(p0, p1, p2, min(1.0, t + 0.01))
        tangent = normalize(sub(q2, q))
        lateral = normalize(cross(tangent, (0.0, 0.0, 1.0)))
        if length(lateral) < 0.2:
            lateral = (-math.sin(azimuth), math.cos(azimuth), 0.0)
        profile = 0.45 + 0.55 * math.sin(math.pi * min(1.0, t))
        leaf_length = base_len * profile
        slot = index % 4
        u0, u1 = slot * 0.25, slot * 0.25 + 0.25
        weight_base = min(0.9, t * 0.9)
        weight_tip = min(1.0, 0.55 + 0.5 * t)
        for side in (-1, 1):
            leaf_dir = normalize(add(add(mul(lateral, side * 1.0), mul(tangent, 0.5)),
                                     (0.0, 0.0, 0.32)))
            across = normalize(cross(leaf_dir, tangent))
            if length(across) < 0.2:
                across = tangent
            mesh.leaflet(q, leaf_dir, across, leaf_length, 2.3,
                         weight_base, weight_tip, u0, u1)


def build_date_palm(name: str, trunk_height: float, fronds: int, seed: int) -> Mesh:
    rng = random.Random(seed)
    mesh = Mesh(name)
    sides = 12
    base_r, top_r = 26.0, 17.0
    levels = 14
    rings = []
    for i in range(levels + 1):
        fraction = i / levels
        radius = base_r + (top_r - base_r) * fraction
        rings.append(mesh.ring((0, 0, fraction * trunk_height), radius, sides))
    for i in range(levels):
        mesh.bridge(rings[i], rings[i + 1], "M_DatePalm_Trunk")
    base_centre = mesh.vertex((0, 0, 0))
    mesh.cap(rings[0], base_centre, "M_DatePalm_Trunk", reverse=True)
    add_diamond_bosses(mesh, trunk_height, base_r, top_r, "M_DatePalm_Trunk")

    crown = (0.0, 0.0, trunk_height)
    tiers = (
        (42.0, 152.0, 118.0, 122.0),   # upright central spears
        (55.0, 120.0, 168.0, 52.0),    # high arch
        (60.0, 84.0, 192.0, -16.0),    # spreading arch
        (58.0, 52.0, 178.0, -82.0),    # drooping outer skirt
    )
    for k in range(fronds):
        out1, rise1, out2, dz2 = tiers[k % 4]
        azimuth = 2 * math.pi * k / fronds + rng.uniform(-0.05, 0.05)
        jitter = rng.uniform(-6, 6)
        build_frond(mesh, crown, azimuth, out1 + jitter, rise1 + rng.uniform(-6, 6),
                    out2 + jitter, dz2 + rng.uniform(-6, 6), 55.0, rng)
    return mesh


# --------------------------------------------------------------------------- #
#  Scatterable soil dressing
# --------------------------------------------------------------------------- #

def build_soil_mound(name: str, radius: float, height: float, seed: int) -> Mesh:
    rng = random.Random(seed)
    mesh = Mesh(name)
    sides = 20
    base = []
    mid = []
    for index in range(sides):
        angle = 2 * math.pi * index / sides
        rr = radius * rng.uniform(0.82, 1.0)
        base.append(mesh.vertex((math.cos(angle) * rr, math.sin(angle) * rr, 0.0)))
        mr = radius * 0.55 * rng.uniform(0.8, 1.05)
        mz = height * rng.uniform(0.5, 0.72)
        mid.append(mesh.vertex((math.cos(angle) * mr, math.sin(angle) * mr, mz)))
    mesh.bridge(base, mid, "M_SoilDressing_Mound")
    apex = mesh.vertex((rng.uniform(-4, 4), rng.uniform(-4, 4), height))
    mesh.cap(mid, apex, "M_SoilDressing_Mound")
    base_centre = mesh.vertex((0, 0, 0))
    mesh.cap(base, base_centre, "M_SoilDressing_Mound", reverse=True)
    return mesh


def build_litter(name: str, seed: int) -> Mesh:
    rng = random.Random(seed)
    mesh = Mesh(name)
    cards = 15
    reach = 42.0
    for index in range(cards):
        angle = rng.uniform(0, 2 * math.pi)
        dist = reach * math.sqrt(rng.uniform(0.0, 1.0))
        cx, cy = math.cos(angle) * dist, math.sin(angle) * dist
        size = rng.uniform(8.0, 17.0)
        yaw = rng.uniform(0, 2 * math.pi)
        tilt = rng.uniform(0.0, 0.20)
        side = (math.cos(yaw), math.sin(yaw), 0.0)
        forward = (-math.sin(yaw) * math.cos(tilt), math.cos(yaw) * math.cos(tilt), math.sin(tilt))
        lift = 0.5 + index * 0.35  # stack cards to avoid perfect coplanar z-fight
        centre = (cx, cy, lift)
        slot = index % 4
        u0 = 0.5 * (slot % 2)
        v0 = 0.5 * (slot // 2)
        u1, v1 = u0 + 0.5, v0 + 0.5
        half_s = mul(side, size * 0.5)
        half_f = mul(forward, size * 0.5)
        points = (add(centre, add(mul(half_s, -1), mul(half_f, -1))),
                  add(centre, add(mul(half_s, -1), half_f)),
                  add(centre, add(half_s, half_f)),
                  add(centre, add(half_s, mul(half_f, -1))))
        mesh.quad(points, "M_SoilDressing_Litter",
                  ((u0, v0), (u0, v1), (u1, v1), (u1, v0)))
    return mesh


def build_stones(name: str, seed: int) -> Mesh:
    rng = random.Random(seed)
    mesh = Mesh(name)
    count = 6
    reach = 40.0
    for stone in range(count):
        angle = 2 * math.pi * stone / count + rng.uniform(-0.4, 0.4)
        dist = reach * rng.uniform(0.2, 1.0)
        cx, cy = math.cos(angle) * dist, math.sin(angle) * dist
        scale = rng.uniform(5.0, 11.0)
        petals = 5
        mids = []
        for index in range(petals):
            a = 2 * math.pi * index / petals + rng.uniform(-0.2, 0.2)
            rr = scale * rng.uniform(0.7, 1.15)
            mids.append(mesh.vertex((cx + math.cos(a) * rr, cy + math.sin(a) * rr,
                                     scale * rng.uniform(0.32, 0.6))))
        top = mesh.vertex((cx + rng.uniform(-2, 2), cy + rng.uniform(-2, 2),
                           scale * rng.uniform(1.05, 1.45)))
        bottom = mesh.vertex((cx, cy, 0.0))
        for index in range(petals):
            following = (index + 1) % petals
            mesh.face("M_SoilDressing_Stone", (top, mids[index], mids[following]))
            mesh.face("M_SoilDressing_Stone", (bottom, mids[following], mids[index]))
    return mesh


# --------------------------------------------------------------------------- #
#  RGBA cutout atlases
# --------------------------------------------------------------------------- #

def supersampled_texture(draw_fn, path: Path) -> None:
    scale = 4
    image = Image.new("RGBA", (1024 * scale, 1024 * scale), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(image, "RGBA"), scale)
    image.resize((1024, 1024), Image.Resampling.LANCZOS).save(path)


def write_cutouts() -> None:
    CUTOUTS.mkdir(parents=True, exist_ok=True)

    def palm_leaflets(draw: ImageDraw.ImageDraw, s: int) -> None:
        # Four slender lanceolate blades, base at v=0 (bottom), tip at v=1 (top).
        greens = [(46, 96, 44, 255), (54, 108, 49, 255), (40, 88, 40, 255), (60, 114, 52, 255)]
        for column in range(4):
            cx = int((column + 0.5) * 256)
            base_y, tip_y = 1004, 26
            half_base, half_mid = 70, 96
            blade = [(cx - half_base, base_y), (cx - half_mid, int(base_y * 0.62)),
                     (cx - 30, int(base_y * 0.30)), (cx, tip_y),
                     (cx + 30, int(base_y * 0.30)), (cx + half_mid, int(base_y * 0.62)),
                     (cx + half_base, base_y)]
            draw.polygon([(x * s, y * s) for x, y in blade], fill=greens[column])
            draw.line([(cx * s, (base_y - 12) * s), (cx * s, (tip_y + 20) * s)],
                      fill=(96, 150, 82, 210), width=5 * s)

    def leaf_bark_litter(draw: ImageDraw.ImageDraw, s: int) -> None:
        # 2x2 atlas of dry litter fragments; each slot self-contained with padding.
        def slot(ox: int, oy: int, drawer) -> None:
            drawer(ox, oy)

        def dry_leaf(ox: int, oy: int) -> None:
            cx, cy = ox + 256, oy + 256
            pts = [(cx, cy - 190), (cx + 120, cy - 40), (cx + 70, cy + 180),
                   (cx, cy + 120), (cx - 70, cy + 180), (cx - 120, cy - 40)]
            draw.polygon([(x * s, y * s) for x, y in pts], fill=(150, 96, 44, 255))
            draw.line([(cx * s, (cy - 180) * s), (cx * s, (cy + 150) * s)],
                      fill=(110, 66, 28, 230), width=5 * s)

        def bark_chip(ox: int, oy: int) -> None:
            cx, cy = ox + 256, oy + 256
            pts = [(cx - 150, cy - 90), (cx + 160, cy - 130), (cx + 130, cy + 110),
                   (cx - 130, cy + 140)]
            draw.polygon([(x * s, y * s) for x, y in pts], fill=(96, 66, 42, 255))
            for k in range(-2, 3):
                draw.line([((cx - 140) * s, (cy + k * 40) * s), ((cx + 150) * s, (cy + k * 40) * s)],
                          fill=(66, 44, 26, 200), width=3 * s)

        def small_leaf(ox: int, oy: int) -> None:
            cx, cy = ox + 256, oy + 256
            pts = [(cx, cy - 150), (cx + 150, cy), (cx, cy + 150), (cx - 150, cy)]
            draw.polygon([(x * s, y * s) for x, y in pts], fill=(120, 128, 52, 255))
            draw.line([((cx - 130) * s, cy * s), ((cx + 130) * s, cy * s)],
                      fill=(86, 92, 36, 220), width=4 * s)

        def twig(ox: int, oy: int) -> None:
            cx, cy = ox + 256, oy + 256
            draw.line([((cx - 170) * s, (cy + 120) * s), ((cx + 160) * s, (cy - 130) * s)],
                      fill=(104, 74, 44, 255), width=34 * s)
            draw.line([(cx * s, cy * s), ((cx + 80) * s, (cy + 90) * s)],
                      fill=(104, 74, 44, 255), width=20 * s)

        slot(0, 0, dry_leaf)
        slot(512, 0, bark_chip)
        slot(0, 512, small_leaf)
        slot(512, 512, twig)

    supersampled_texture(palm_leaflets, CUTOUTS / "date_palm_leaflet_ribbon_rgba_1024.png")
    supersampled_texture(leaf_bark_litter, CUTOUTS / "leaf_bark_litter_rgba_1024.png")


# --------------------------------------------------------------------------- #
#  Material library
# --------------------------------------------------------------------------- #

MATERIALS = {
    "M_ConcretePlanter_Cast": ((0.40, 0.40, 0.37), 0.0, 0.90, None),
    "M_ConcretePlanter_Rim": ((0.47, 0.46, 0.42), 0.0, 0.84, None),
    "M_CeramicPlanter_Glaze": ((0.12, 0.34, 0.33), 0.05, 0.22, None),
    "M_CeramicPlanter_Rim": ((0.16, 0.40, 0.38), 0.05, 0.18, None),
    "M_Planter_DressedSoil": ((0.11, 0.08, 0.05), 0.0, 0.95, None),
    "M_DatePalm_Trunk": ((0.32, 0.24, 0.15), 0.0, 0.86, None),
    "M_DatePalm_Rachis": ((0.30, 0.33, 0.16), 0.0, 0.62, None),
    "M_DatePalm_Leaflet": ((0.20, 0.36, 0.17), 0.0, 0.46, "date_palm_leaflet_ribbon_rgba_1024.png"),
    "M_SoilDressing_Mound": ((0.13, 0.09, 0.055), 0.0, 0.95, None),
    "M_SoilDressing_Litter": ((0.42, 0.30, 0.16), 0.0, 0.72, "leaf_bark_litter_rgba_1024.png"),
    "M_SoilDressing_Stone": ((0.35, 0.35, 0.34), 0.0, 0.80, None),
}


def write_mtl() -> None:
    lines = ["# Unreal material-slot placeholder library for the entrance-terrace reveal kit"]
    for name, (colour, metallic, roughness, texture) in MATERIALS.items():
        lines.extend((f"newmtl {name}", f"Kd {colour[0]} {colour[1]} {colour[2]}",
                      f"Pm {metallic}", f"Pr {roughness}"))
        if texture:
            relative = f"../../cutouts/entrance_terrace_reveal/{texture}"
            lines.extend((f"map_Kd {relative}", f"map_d {relative}"))
        lines.append("")
    (OUT / MTL_NAME).write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------- #
#  Handoff
# --------------------------------------------------------------------------- #

HANDOFF = """# Entrance-Terrace Reveal Kit — Handoff (Slice 1)

Source: `scripts/generate_entrance_terrace_reveal_kit.py`
Verify: `scripts/verify_entrance_terrace_reveal_kit.py`
Units: Unreal centimetres, Z-up. Every OBJ is one object, no `g` records,
named `usemtl` slots, indexed UVs on every corner, Z=0 / base-centred origin.
Foliage vertex RGB encodes wind stiffness (0 = rigid root, 1 = free tip).

MTL: `SourceMesh/entrance_terrace_reveal/VD_EntranceTerraceReveal.mtl`
RGBA cutouts: `cutouts/entrance_terrace_reveal/` (referenced by both `map_Kd`
and `map_d`).

## Import steps (Unreal)
1. Import each OBJ as its own Static Mesh; keep "Combine Meshes" OFF (one object
   per file already).
2. Import the two RGBA sheets as textures; connect RGB -> Base Color and A ->
   Opacity Mask on the leaflet/litter masked materials.
3. On the date palm, enable "Vertex Colors" import and drive a wind/pivot-sway
   node from vertex-colour luminance (0 anchored, 1 free). Trunk vertices are 0.
4. Author collision per the notes below; do NOT let Unreal auto-generate a
   single convex hull on the planters — it seals the open mouth.

{assets}

## Scatter usage
The three `VD_SoilDressing_*` meshes are base-centred at Z=0 and sized to drop
into both these planters and the existing `SourceMesh/terrace_botanical`
planters. Scatter/rotate freely around Z; they carry no wind colour.
"""

ASSET_DOCS = [
    ("VD_SpecimenPlanter_Concrete", "Round specimen planter — aged cast concrete",
     "224 cm outer diameter x 98 cm tall; wall ~10 cm; soil disc ~18 cm below rim.",
     "M_ConcretePlanter_Cast (body + inner wall + base), M_ConcretePlanter_Rim (top lip), M_Planter_DressedSoil (visible soil).",
     "Segmented ring collision: 8-16 convex wall segments + a base disc, leaving the mouth open. NEVER a single auto convex hull (it fills the bowl and blocks planting)."),
    ("VD_SpecimenPlanter_Ceramic", "Round specimen planter — period glazed ceramic",
     "188 cm outer diameter x 116 cm tall; wall ~8.5 cm; soil disc ~21 cm below rim.",
     "M_CeramicPlanter_Glaze (glazed body + inner wall + base), M_CeramicPlanter_Rim (glazed lip), M_Planter_DressedSoil (visible soil).",
     "Same as the concrete planter: ring/segmented convex primitives around the wall + base disc; keep the opening clear. No single convex hull."),
    ("VD_DatePalm_Hero", "Phoenix/date-palm hero specimen",
     "~4.1 m tall overall; trunk ~2.7 m with a raised diamond leaf-base lattice; 16 arching pinnate fronds.",
     "M_DatePalm_Trunk (trunk + diamond bosses, rigid), M_DatePalm_Rachis (frond midribs), M_DatePalm_Leaflet (alpha-cut pinnate leaflet ribbons).",
     "Trunk-only vertical capsule or 8-sided cylinder collision (~0.5 m radius). Fronds/leaflets: NO collision (overlap-only), so visitors and camera pass through the canopy."),
    ("VD_SoilDressing_Mound", "Scatter — uneven dressed soil mound",
     "~110 cm diameter x ~15 cm tall irregular dome.",
     "M_SoilDressing_Mound.",
     "Single simple convex hull or a low box is fine (it is a solid mass)."),
    ("VD_SoilDressing_Litter", "Scatter — leaf / bark litter cards",
     "~85 cm spread of 15 near-flat alpha cards, a few cm thick.",
     "M_SoilDressing_Litter (alpha-cut leaf/bark/twig atlas).",
     "No collision (decorative overlay)."),
    ("VD_SoilDressing_Stones", "Scatter — small stone cluster",
     "~80 cm spread of 6 faceted stones, ~10-16 cm each.",
     "M_SoilDressing_Stone.",
     "Per-stone simple convex collision, or none if purely decorative. Do not wrap the whole cluster in one hull across the gaps."),
]


def write_handoff() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    blocks = []
    for name, title, dims, slots, collision in ASSET_DOCS:
        blocks.append(f"### {name}\n**{title}**\n\n"
                      f"- Dimensions: {dims}\n"
                      f"- Material slots: {slots}\n"
                      f"- Collision: {collision}")
    text = HANDOFF.format(assets="## Assets\n\n" + "\n\n".join(blocks))
    (DOCS / "entrance_terrace_reveal_handoff.md").write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- #
#  Main
# --------------------------------------------------------------------------- #

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    write_cutouts()
    meshes = [
        build_round_planter("VD_SpecimenPlanter_Concrete", 224.0, 98.0,
                            "M_ConcretePlanter_Cast", "M_ConcretePlanter_Rim",
                            "M_Planter_DressedSoil", 7701),
        build_round_planter("VD_SpecimenPlanter_Ceramic", 188.0, 116.0,
                            "M_CeramicPlanter_Glaze", "M_CeramicPlanter_Rim",
                            "M_Planter_DressedSoil", 7702),
        build_date_palm("VD_DatePalm_Hero", 268.0, 16, 7801),
        build_soil_mound("VD_SoilDressing_Mound", 55.0, 15.0, 7901),
        build_litter("VD_SoilDressing_Litter", 7902),
        build_stones("VD_SoilDressing_Stones", 7903),
    ]
    write_mtl()
    write_handoff()
    manifest_meshes = []
    for mesh in meshes:
        mins = [min(point[axis] for point in mesh.vertices) for axis in range(3)]
        maxs = [max(point[axis] for point in mesh.vertices) for axis in range(3)]
        offset = (-(mins[0] + maxs[0]) * 0.5, -(mins[1] + maxs[1]) * 0.5, -mins[2])
        mesh.vertices = [add(point, offset) for point in mesh.vertices]
        mesh.write_obj(OUT / f"{mesh.name}.obj")
        size = [maxs[i] - mins[i] for i in range(3)]
        manifest_meshes.append({"name": mesh.name, "vertices": len(mesh.vertices),
                                "faces": len(mesh.faces),
                                "size_cm": [round(v, 2) for v in size]})
    manifest = {
        "units": "centimetres; Z-up",
        "slice": "entrance-terrace reveal kit 1",
        "mesh_count": len(meshes),
        "foliage_contract": {
            "alpha_cut_rgba_sheets": 2,
            "wind_encoding": "OBJ vertex RGB grayscale; 0=root/rigid, 1=free tip",
            "palm_fronds": 16,
            "palm_leaflet_pairs_per_frond": 24,
        },
        "meshes": manifest_meshes,
    }
    (QA / "generation_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

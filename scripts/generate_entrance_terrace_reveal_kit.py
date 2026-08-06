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
#  Supporting specimens: aloe, philodendron, coleus
# --------------------------------------------------------------------------- #

def add_leaf_card(mesh: Mesh, origin: Vec3, x_axis: Vec3, y_axis: Vec3, z_axis: Vec3,
                  width: float, leaf_length: float, material: str,
                  slot: tuple[float, float, float, float], w_base: float, w_tip: float,
                  curl: float, cup: float, lsegs: int, wsegs: int) -> int:
    """A curved, subdivided alpha-cut leaf sheet (not a flat rectangle).

    The blade droops along its length (`curl`) and cups across its width (`cup`),
    so the silhouette comes from the RGBA alpha while the surface still catches
    light like a real leaf. UVs address the atlas slot; wind stiffness rises from
    `w_base` at the petiole to `w_tip` at the free tip. Returns the quad count.
    """
    u0, v0, u1, v1 = slot
    grid: list[list[tuple[int, float, float]]] = []
    for i in range(lsegs + 1):
        t = i / lsegs
        row = []
        for j in range(wsegs + 1):
            s = j / wsegs
            droop = -curl * leaf_length * (t * t)
            cupz = cup * width * (((s - 0.5) ** 2) - 0.25)
            pos = add(add(add(origin, mul(y_axis, leaf_length * t)),
                          mul(x_axis, width * (s - 0.5))),
                      mul(z_axis, droop + cupz))
            weight = min(1.0, w_base + (w_tip - w_base) * t)
            row.append((mesh.vertex(pos, stiffness(weight)),
                        u0 + (u1 - u0) * s, v0 + (v1 - v0) * t))
        grid.append(row)
    quads = 0
    for i in range(lsegs):
        for j in range(wsegs):
            a, b = grid[i][j], grid[i + 1][j]
            c, d = grid[i + 1][j + 1], grid[i][j + 1]
            mesh.face(material, (a[0], b[0], c[0], d[0]),
                      ((a[1], a[2]), (b[1], b[2]), (c[1], c[2]), (d[1], d[2])))
            quads += 1
    return quads


def add_aloe_leaf(mesh: Mesh, base: Vec3, azimuth: float, up_angle: float,
                  leaf_length: float, width0: float, thick0: float, w_tip: float) -> None:
    """One genuinely 3-D succulent blade: a tapering diamond cross-section lofted
    along an arching spine, with marginal teeth for a serrated silhouette."""
    out = (math.cos(azimuth), math.sin(azimuth), 0.0)
    rise = math.sin(up_angle)
    reach = math.cos(up_angle)
    p0 = base
    p1 = add(base, (out[0] * leaf_length * 0.35 * reach, out[1] * leaf_length * 0.35 * reach,
                    leaf_length * 0.55 * rise))
    p2 = add(base, (out[0] * leaf_length * reach, out[1] * leaf_length * reach,
                    leaf_length * rise - leaf_length * 0.14 * (1.0 - rise)))
    default_side = (-math.sin(azimuth), math.cos(azimuth), 0.0)
    segs = 8
    ring_prev: list[int] | None = None
    # Loft rings up to t=(segs-1)/segs only; the apex forms the pointed tip so
    # the final cross-section never collapses to a degenerate zero-area ring.
    for i in range(segs):
        t = i / segs
        c = bezier3(p0, p1, p2, t)
        tangent = normalize(sub(bezier3(p0, p1, p2, min(1.0, t + 0.01)), c))
        side = cross(tangent, (0.0, 0.0, 1.0))
        side = normalize(side) if length(side) > 0.2 else default_side
        upn = normalize(cross(side, tangent))
        w = width0 * (1.0 - t) ** 0.65
        th = thick0 * (1.0 - t) ** 0.7
        col = stiffness(w_tip * (t ** 1.3))
        ring = [mesh.vertex(add(c, mul(upn, th * 0.35)), col),   # channelled top
                mesh.vertex(add(c, mul(side, w * 0.5)), col),    # right margin
                mesh.vertex(add(c, mul(upn, -th * 0.65)), col),  # convex keel
                mesh.vertex(add(c, mul(side, -w * 0.5)), col)]   # left margin
        if ring_prev is not None:
            for k in range(4):
                mesh.face("M_Aloe_Leaf", (ring_prev[k], ring_prev[(k + 1) % 4],
                                          ring[(k + 1) % 4], ring[k]))
            if i % 2 == 0 and t < 0.9:
                spike_l = mesh.vertex(add(c, mul(side, -(w * 0.5 + w * 0.4 + 0.6))), col)
                mesh.face("M_Aloe_Leaf", (ring_prev[3], ring[3], spike_l))
                spike_r = mesh.vertex(add(c, mul(side, w * 0.5 + w * 0.4 + 0.6)), col)
                mesh.face("M_Aloe_Leaf", (ring[1], ring_prev[1], spike_r))
        ring_prev = ring
    tip_c = bezier3(p0, p1, p2, 1.0)
    tip_dir = normalize(sub(tip_c, bezier3(p0, p1, p2, 0.985)))
    apex = mesh.vertex(add(tip_c, mul(tip_dir, width0 * 0.35 + 1.5)), stiffness(w_tip))
    assert ring_prev is not None
    for k in range(4):
        mesh.face("M_Aloe_Leaf", (ring_prev[k], ring_prev[(k + 1) % 4], apex))


def build_aloe(name: str, seed: int) -> Mesh:
    """Strong multi-tier aloe rosette (a composed display specimen)."""
    rng = random.Random(seed)
    mesh = Mesh(name)
    base_r = 13.0
    ring0 = mesh.ring((0, 0, 0), base_r, 16)
    ring1 = mesh.ring((0, 0, 6.0), base_r * 0.72, 16)
    mesh.bridge(ring0, ring1, "M_Aloe_Base")
    crown = mesh.vertex((0, 0, 8.5))
    mesh.cap(ring1, crown, "M_Aloe_Base")
    base_centre = mesh.vertex((0, 0, 0))
    mesh.cap(ring0, base_centre, "M_Aloe_Base", reverse=True)

    # (count, length, up_angle, width0, thick0, w_tip, z_base)
    tiers = [
        (11, 60.0, math.radians(24), 7.6, 3.2, 0.60, 5.0),
        (9, 66.0, math.radians(44), 6.8, 2.9, 0.70, 6.5),
        (7, 70.0, math.radians(64), 5.8, 2.6, 0.80, 7.5),
        (5, 72.0, math.radians(82), 4.6, 2.2, 0.85, 8.0),
    ]
    golden = math.radians(137.507)
    index = 0
    for count, leaf_length, angle, w0, th0, w_tip, z_base in tiers:
        for _ in range(count):
            azimuth = golden * index + rng.uniform(-0.08, 0.08)
            index += 1
            offset_r = base_r * 0.34
            base = (math.cos(azimuth) * offset_r, math.sin(azimuth) * offset_r, z_base)
            add_aloe_leaf(mesh, base, azimuth, angle + rng.uniform(-0.05, 0.05),
                          leaf_length * rng.uniform(0.94, 1.06), w0, th0, w_tip)
    return mesh


SUPPORT_LEAF_SLOTS = [(0.0, 0.0, 0.5, 0.5), (0.5, 0.0, 1.0, 0.5),
                      (0.0, 0.5, 0.5, 1.0), (0.5, 0.5, 1.0, 1.0)]


def build_philodendron(name: str, seed: int) -> Mesh:
    """Upright-to-spreading philodendron: real petioles carrying large lobed
    alpha-cut leaf sheets on curved ribbons."""
    rng = random.Random(seed)
    mesh = Mesh(name)
    crown_r = 16.0
    r0 = mesh.ring((0, 0, 0), crown_r, 18)
    r1 = mesh.ring((0, 0, 10.0), crown_r * 0.72, 18)
    mesh.bridge(r0, r1, "M_Philodendron_Crown")
    top = mesh.vertex((0, 0, 13.0))
    mesh.cap(r1, top, "M_Philodendron_Crown")
    base_centre = mesh.vertex((0, 0, 0))
    mesh.cap(r0, base_centre, "M_Philodendron_Crown", reverse=True)

    leaves = 11
    golden = math.radians(137.507)
    for k in range(leaves):
        azimuth = golden * k + rng.uniform(-0.1, 0.1)
        frac = k / (leaves - 1)
        lean = math.radians(16.0 + frac * 48.0)
        petiole_len = rng.uniform(74.0, 116.0) * (1.0 - 0.14 * frac)
        out = (math.cos(azimuth), math.sin(azimuth), 0.0)
        start = add((0.0, 0.0, 11.0), mul(out, crown_r * 0.4))
        tip = add(start, (out[0] * petiole_len * math.sin(lean),
                          out[1] * petiole_len * math.sin(lean),
                          petiole_len * math.cos(lean)))
        ctrl = add(start, (out[0] * petiole_len * 0.30, out[1] * petiole_len * 0.30,
                           petiole_len * 0.74))
        psegs = 6
        last = start
        for s in range(1, psegs + 1):
            t = s / psegs
            pt = bezier3(start, ctrl, tip, t)
            mesh.cylinder(last, pt, 2.7 * (1 - 0.5 * (s - 1) / psegs), 2.7 * (1 - 0.5 * t),
                          6, "M_Philodendron_Petiole",
                          min(0.3, (s - 1) / psegs * 0.3), min(0.35, t * 0.35))
            last = pt
        ldir = normalize(sub(tip, ctrl))
        xax = cross(ldir, (0.0, 0.0, 1.0))
        xax = normalize(xax) if length(xax) > 0.2 else (-math.sin(azimuth), math.cos(azimuth), 0.0)
        zax = normalize(cross(xax, ldir))
        add_leaf_card(mesh, tip, xax, ldir, zax,
                      rng.uniform(26.0, 34.0), rng.uniform(40.0, 52.0),
                      "M_Philodendron_Leaf", SUPPORT_LEAF_SLOTS[k % 4],
                      0.35, 1.0, 0.30, 0.55, 6, 4)
    return mesh


def build_coleus(name: str, seed: int) -> Mesh:
    """Low dense coleus mound: branching real stems with opposite decussate
    pairs of patterned alpha-cut leaves."""
    rng = random.Random(seed)
    mesh = Mesh(name)
    base_r = 12.0
    r0 = mesh.ring((0, 0, 0), base_r, 16)
    r1 = mesh.ring((0, 0, 6.0), base_r * 0.7, 16)
    mesh.bridge(r0, r1, "M_Coleus_Base")
    top = mesh.vertex((0, 0, 8.0))
    mesh.cap(r1, top, "M_Coleus_Base")
    base_centre = mesh.vertex((0, 0, 0))
    mesh.cap(r0, base_centre, "M_Coleus_Base", reverse=True)

    stems = 6
    nodes = 5
    leaf_index = 0
    for k in range(stems):
        azimuth = 2 * math.pi * k / stems + rng.uniform(-0.2, 0.2)
        lean = math.radians(rng.uniform(20.0, 34.0))
        out = (math.cos(azimuth), math.sin(azimuth), 0.0)
        base = (math.cos(azimuth) * base_r * 0.4, math.sin(azimuth) * base_r * 0.4, 5.0)
        height = rng.uniform(46.0, 60.0)
        top_pt = add(base, (out[0] * height * math.sin(lean), out[1] * height * math.sin(lean),
                            height * math.cos(lean)))
        ctrl = add(base, (out[0] * height * 0.15, out[1] * height * 0.15, height * 0.6))
        prev = base
        for n in range(1, nodes + 1):
            t = n / nodes
            pt = bezier3(base, ctrl, top_pt, t)
            mesh.cylinder(prev, pt, 1.9 * (1 - 0.42 * (n - 1) / nodes), 1.9 * (1 - 0.42 * t),
                          6, "M_Coleus_Stem", min(0.2, (n - 1) / nodes * 0.2),
                          min(0.25, t * 0.25))
            sdir = normalize(sub(pt, prev))
            perp = cross(sdir, (0.0, 0.0, 1.0))
            perp = normalize(perp) if length(perp) > 0.2 else (1.0, 0.0, 0.0)
            if n % 2 == 0:  # decussate: alternate node pairs rotate 90 degrees
                perp = normalize(cross(sdir, perp))
            for sign in (-1.0, 1.0):
                ldir = normalize(add(add(mul(perp, sign), mul(sdir, 0.35)), (0.0, 0.0, 0.28)))
                xax = cross(ldir, (0.0, 0.0, 1.0))
                xax = normalize(xax) if length(xax) > 0.2 else perp
                zax = normalize(cross(xax, ldir))
                scale = 1.0 - 0.45 * t
                add_leaf_card(mesh, pt, xax, ldir, zax,
                              rng.uniform(7.0, 10.0) * scale + 4.0,
                              rng.uniform(10.0, 14.0) * scale + 5.0,
                              "M_Coleus_Leaf", SUPPORT_LEAF_SLOTS[leaf_index % 4],
                              0.30, 1.0, 0.24, 0.45, 3, 2)
                leaf_index += 1
            prev = pt
    return mesh


# --------------------------------------------------------------------------- #
#  Vertical slice 3: public visitor furniture (benches, brochure stand, fountain)
# --------------------------------------------------------------------------- #

def beam_ring(mesh: Mesh, centre: Vec3, right_axis: Vec3, up_axis: Vec3,
             half_w: float, half_h: float) -> list[int]:
    pts = (add(centre, add(mul(right_axis, -half_w), mul(up_axis, -half_h))),
          add(centre, add(mul(right_axis, half_w), mul(up_axis, -half_h))),
          add(centre, add(mul(right_axis, half_w), mul(up_axis, half_h))),
          add(centre, add(mul(right_axis, -half_w), mul(up_axis, half_h))))
    return [mesh.vertex(p) for p in pts]


def build_beam(mesh: Mesh, path: list[Vec3], right_axis: Vec3, up_axis: Vec3,
              half_w: float, half_h: float, material: str) -> None:
    """A straight or bent rectangular timber beam lofted along `path`.

    Rigid furniture geometry only -- vertices never carry stiffness colour, so
    a beam with a bowed path (see the sagging bench seat) reads as damage
    through shape alone, never through vertex colour.
    """
    rings = [beam_ring(mesh, p, right_axis, up_axis, half_w, half_h) for p in path]
    for i in range(len(rings) - 1):
        mesh.bridge(rings[i], rings[i + 1], material)
    mesh.face(material, tuple(reversed(rings[0])))
    mesh.face(material, tuple(rings[-1]))


def tube_polyline(mesh: Mesh, points: list[Vec3], radius: float, sides: int,
                  material: str) -> None:
    """A chain of open (uncapped) round tube segments, matching the existing
    frond-rachis/petiole/stem convention elsewhere in this file."""
    for i in range(len(points) - 1):
        mesh.cylinder(points[i], points[i + 1], radius, radius, sides, material)


def build_bench(name: str, damaged: bool, seed: int) -> Mesh:
    """1960s municipal park bench: tubular welded/cast-steel end frames carrying
    real slatted timber seat and back boards, paired end to end in the same
    footprint as its sibling variant.

    `damaged` sags the seat boards, drops one seat stretcher, and leans the
    back frame further -- damage is entirely geometric (bowed beam paths,
    offset frame points), never vertex colour, since this is rigid furniture.
    """
    rng = random.Random(seed)
    mesh = Mesh(name)
    frame_x = 95.0
    slat_span = 2.0 * frame_x - 4.0
    seat_h = 44.0

    frame_mat = "M_Bench_CastFrame_Damaged" if damaged else "M_Bench_CastFrame_Intact"
    seat_mat = "M_Bench_SeatSlat_Damaged" if damaged else "M_Bench_SeatSlat_Intact"
    back_mat = "M_Bench_BackSlat_Damaged" if damaged else "M_Bench_BackSlat_Intact"

    back_lean = math.radians(15.0 if damaged else 11.0)
    back_up = (0.0, -math.sin(back_lean), math.cos(back_lean))
    back_depth = (0.0, math.cos(back_lean), math.sin(back_lean))
    back_top_z = 74.0 if damaged else 78.0

    for side in (-1.0, 1.0):
        x = side * frame_x
        arc = [(x, 21.0, 0.0), (x, 21.0, seat_h), (x, 24.5, 64.0),
              (x, 9.0, 72.0), (x, -4.0, 58.0)]
        tube_polyline(mesh, arc, 2.2, 8, frame_mat)
        upright_top_y = -21.0 - (4.0 if damaged else 0.0)
        upright = [(x, -21.0, 0.0), (x, -21.0, 40.0), (x, upright_top_y, back_top_z)]
        tube_polyline(mesh, upright, 2.0, 8, frame_mat)
        strut_drop = 6.0 if damaged else 0.0
        tube_polyline(mesh, [(x, 21.0, seat_h), (x, -16.0, 50.0 - strut_drop)], 1.6, 8, frame_mat)
        tube_polyline(mesh, [(x, 21.0, 0.0), (x, -21.0, 0.0)], 1.6, 8, frame_mat)

    seg = 6
    seat_slats = 6
    seat_width, seat_thick, seat_gap = 5.6, 3.4, 1.0
    seat_start_y = 19.0
    sag_amp = 5.0 if damaged else 0.0
    for i in range(seat_slats):
        y = seat_start_y - i * (seat_width + seat_gap)
        jitter = rng.uniform(-0.6, 0.6) if damaged else 0.0
        path = []
        for s in range(seg):
            t = s / (seg - 1)
            x = -slat_span / 2.0 + t * slat_span
            bow = (1.0 - (2.0 * t - 1.0) ** 2)
            dip = (sag_amp + jitter) * bow
            path.append((x, y, seat_h + seat_thick / 2.0 - dip))
        build_beam(mesh, path, (0.0, 1.0, 0.0), (0.0, 0.0, 1.0),
                  seat_width / 2.0, seat_thick / 2.0, seat_mat)

    back_slats = 4
    back_width, back_thick, back_gap = 6.0, 3.0, 1.4
    back_start = 52.0
    for i in range(back_slats):
        rise = back_start + i * (back_width + back_gap) + back_width / 2.0
        centre = add((0.0, -21.0, 0.0), mul(back_up, rise))
        path = [(-slat_span / 2.0 + (s / (seg - 1)) * slat_span, centre[1], centre[2])
               for s in range(seg)]
        build_beam(mesh, path, back_depth, back_up,
                  back_thick / 2.0, back_width / 2.0, back_mat)
    return mesh


def build_brochure_stand(name: str, seed: int) -> Mesh:
    """Freestanding period institutional literature rack: one tubular post on a
    splayed tripod foot, five shallow angled sheet-metal pockets, and a warped
    paper leaflet still standing in each pocket."""
    rng = random.Random(seed)
    mesh = Mesh(name)
    post_top = 148.0
    tube_polyline(mesh, [(0.0, 0.0, 0.0), (0.0, 0.0, post_top)], 2.4, 10, "M_BrochureStand_Frame")
    for k in range(3):
        angle = 2 * math.pi * k / 3 + math.radians(60)
        tip = (math.cos(angle) * 21.0, math.sin(angle) * 21.0, 0.0)
        tube_polyline(mesh, [(0.0, 0.0, 9.0), tip], 1.8, 8, "M_BrochureStand_Frame")

    tilt = math.radians(24.0)
    floor_dir = (0.0, math.cos(tilt), -math.sin(tilt))
    lip_dir = (0.0, math.sin(tilt), math.cos(tilt))
    floor_len, lip_len, width = 18.0, 4.5, 32.0
    pockets = 5
    for p in range(pockets):
        origin = (0.0, 0.0, 42.0 + p * 21.0)
        p1 = add(origin, mul(floor_dir, floor_len))
        p2 = add(p1, mul(lip_dir, lip_len))

        def side_points(centre: Vec3) -> tuple[Vec3, Vec3]:
            return (add(centre, (-width / 2, 0.0, 0.0)), add(centre, (width / 2, 0.0, 0.0)))

        a0, b0 = side_points(origin)
        a1, b1 = side_points(p1)
        a2, b2 = side_points(p2)
        mesh.quad((a0, a1, b1, b0), "M_BrochureStand_Pocket")
        mesh.quad((a1, a2, b2, b1), "M_BrochureStand_Pocket")

        card_lean = math.radians(46.0)
        card_y = (0.0, math.cos(card_lean), -math.sin(card_lean))
        card_z = (0.0, math.sin(card_lean), math.cos(card_lean))
        card_origin = add(p1, (0.0, 1.0, 0.5))
        add_leaf_card(mesh, card_origin, (1.0, 0.0, 0.0), card_y, card_z,
                      13.0 + rng.uniform(-1.0, 1.0), 20.0 + rng.uniform(-1.5, 1.5),
                      "M_BrochureStand_Paper", (0.0, 0.0, 1.0, 1.0), 0.0, 0.0,
                      0.16, 0.30, 3, 2)
    return mesh


def build_fountain(name: str, seed: int) -> Mesh:
    """Dry, non-functioning octagonal public-garden fountain. The floor sits
    well below the rim so the empty basin reads immediately, a stained
    pedestal stub replaces any spray nozzle, and drifted leaf litter has
    collected across the dry floor. No water material appears anywhere."""
    rng = random.Random(seed)
    mesh = Mesh(name)
    sides = 8
    outer_r = 190.0
    height = 112.0
    wall = 15.0
    floor_z = 46.0

    levels = 5
    outer_rings = [mesh.ring((0, 0, (i / levels) * height), outer_r, sides)
                  for i in range(levels + 1)]
    for i in range(levels):
        mesh.bridge(outer_rings[i], outer_rings[i + 1], "M_Fountain_BasinWall")
    base_centre = mesh.vertex((0, 0, 0))
    mesh.cap(outer_rings[0], base_centre, "M_Fountain_BasinWall", reverse=True)

    inner_top_r = outer_r - wall
    inner_top = mesh.ring((0, 0, height), inner_top_r, sides)
    mesh.bridge(outer_rings[levels], inner_top, "M_Fountain_BasinWall")  # rim lip

    inner_floor_r = inner_top_r * 0.94
    inner_floor_ring = mesh.ring((0, 0, floor_z), inner_floor_r, sides)
    mesh.bridge(inner_top, inner_floor_ring, "M_Fountain_BasinWall", flip=True)  # dry drop to the floor

    ped_base_r = inner_floor_r * 0.32
    ped_base_ring = mesh.ring((0, 0, floor_z), ped_base_r, sides)
    mesh.bridge(inner_floor_ring, ped_base_ring, "M_Fountain_BasinFloor", flip=True)

    ped_mid = mesh.ring((0, 0, floor_z + 28.0), ped_base_r * 0.75, sides)
    ped_top_ring = mesh.ring((0, 0, floor_z + 40.0), ped_base_r * 0.5, sides)
    mesh.bridge(ped_base_ring, ped_mid, "M_Fountain_Pedestal")
    mesh.bridge(ped_mid, ped_top_ring, "M_Fountain_Pedestal")
    ped_cap = mesh.vertex((0, 0, floor_z + 40.0))
    mesh.cap(ped_top_ring, ped_cap, "M_Fountain_Pedestal")

    litter_count = 10
    reach_inner = ped_base_r * 1.15
    reach_outer = inner_floor_r * 0.92
    for index in range(litter_count):
        angle = rng.uniform(0, 2 * math.pi)
        dist = reach_inner + (reach_outer - reach_inner) * rng.uniform(0.0, 1.0)
        cx, cy = math.cos(angle) * dist, math.sin(angle) * dist
        size = rng.uniform(14.0, 26.0)
        yaw = rng.uniform(0, 2 * math.pi)
        side_axis = (math.cos(yaw), math.sin(yaw), 0.0)
        forward_axis = (-math.sin(yaw), math.cos(yaw), 0.0)
        lift = floor_z + 0.4 + index * 0.28
        centre = (cx, cy, lift)
        slot = index % 4
        u0, v0 = 0.5 * (slot % 2), 0.5 * (slot // 2)
        u1, v1 = u0 + 0.5, v0 + 0.5
        half_s = mul(side_axis, size * 0.5)
        half_f = mul(forward_axis, size * 0.5)
        points = (add(centre, add(mul(half_s, -1), mul(half_f, -1))),
                 add(centre, add(mul(half_s, -1), half_f)),
                 add(centre, add(half_s, half_f)),
                 add(centre, add(half_s, mul(half_f, -1))))
        mesh.quad(points, "M_Fountain_LeafLitter",
                 ((u0, v0), (u0, v1), (u1, v1), (u1, v0)))
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

    def philodendron_leaves(draw: ImageDraw.ImageDraw, s: int) -> None:
        # 2x2 atlas of deeply pinnatifid display-philodendron blades. Each side
        # alternates broad outward lobes with deep sinuses toward the midrib;
        # this must read as philodendron rather than a generic heart-shaped leaf.
        greens = [(28, 82, 40, 255), (34, 92, 44, 255), (24, 74, 36, 255), (38, 98, 48, 255)]
        vein_colours = [(112, 156, 88, 225), (126, 170, 96, 225),
                        (104, 148, 82, 225), (132, 174, 100, 225)]
        for slot in range(4):
            ox, oy = (slot % 2) * 512, (slot // 2) * 512
            cx = ox + 256
            base_y, tip_y = oy + 472, oy + 42
            lobe_count = 6
            right: list[tuple[int, int]] = []
            lobe_tips: list[tuple[int, int]] = []
            span = 184 + slot * 4
            samples = 96
            for step in range(samples + 1):
                f = step / samples
                y = int(base_y + (tip_y - base_y) * f)
                envelope = math.sin(math.pi * f) ** 0.52
                lobe_wave = abs(math.sin(math.pi * lobe_count * f)) ** 0.72
                width = span * envelope * (0.48 + 0.52 * lobe_wave)
                right.append((int(cx + width), y))
            for lobe in range(lobe_count):
                f = (lobe + 0.5) / lobe_count
                y = int(base_y + (tip_y - base_y) * f)
                envelope = math.sin(math.pi * f) ** 0.52
                width = int(span * envelope)
                lobe_tips.append((cx + width, y))
            outline = right + [(2 * cx - x, y) for x, y in reversed(right)]
            draw.polygon([(x * s, y * s) for x, y in outline], fill=greens[slot])
            vein = vein_colours[slot]
            draw.line([(cx * s, (base_y - 8) * s), (cx * s, (tip_y + 12) * s)],
                      fill=vein, width=7 * s)
            for x, y in lobe_tips:
                attach_y = int(y + (base_y - y) * 0.05)
                draw.line([(cx * s, attach_y * s), ((x - 10) * s, y * s)],
                          fill=vein, width=3 * s)
                draw.line([(cx * s, attach_y * s), ((2 * cx - x + 10) * s, y * s)],
                          fill=vein, width=3 * s)

    def coleus_leaves(draw: ImageDraw.ImageDraw, s: int) -> None:
        # 2x2 atlas: irregular burgundy field, chartreuse serrated margin,
        # branching veins and small green islands. Avoid a clean central oval —
        # real coleus patterning bleeds and feathers along the venation.
        margins = [(150, 176, 46, 255), (128, 158, 40, 255), (162, 182, 58, 255), (120, 150, 38, 255)]
        cores = [(122, 34, 52, 255), (104, 28, 46, 255), (134, 44, 60, 255), (96, 24, 42, 255)]
        darks = [(82, 24, 42, 220), (74, 20, 38, 220), (94, 28, 46, 220), (68, 18, 34, 220)]
        for slot in range(4):
            ox, oy = (slot % 2) * 512, (slot // 2) * 512
            cx, cy = ox + 256, oy + 256
            half_w, half_h = 168, 210
            teeth = 12
            right: list[tuple[float, float]] = []
            for step in range(teeth * 2 + 1):
                f = step / (teeth * 2)
                y = cy + half_h - 2 * half_h * f
                body = math.sin(math.pi * f) ** 0.72
                serr = 1.10 if step % 2 else 0.91
                right.append((cx + half_w * body * serr, y))
            outline = right + [(2 * cx - x, y) for x, y in reversed(right)]
            draw.polygon([(int(x * s), int(y * s)) for x, y in outline], fill=margins[slot])

            core_right: list[tuple[float, float]] = []
            for step in range(25):
                f = step / 24
                y = cy + half_h * 0.78 - 2 * half_h * 0.78 * f
                body = math.sin(math.pi * f) ** 0.76
                wobble = 1.0 + 0.10 * math.sin((f * 7.0 + slot * 0.8) * math.pi)
                core_right.append((cx + half_w * 0.66 * body * wobble, y))
            core = core_right + [(2 * cx - x, y) for x, y in reversed(core_right)]
            draw.polygon([(int(x * s), int(y * s)) for x, y in core], fill=cores[slot])

            vein = (214, 211, 151, 225)
            draw.line([(cx * s, (cy + half_h - 22) * s), (cx * s, (cy - half_h + 24) * s)],
                      fill=vein, width=5 * s)
            for branch in range(1, 7):
                f = branch / 7
                y = int(cy + half_h * 0.72 - 2 * half_h * 0.72 * f)
                reach = half_w * 0.58 * math.sin(math.pi * f) ** 0.7
                draw.line([(cx * s, y * s), (int((cx + reach) * s), int((y - 18) * s))],
                          fill=darks[slot], width=3 * s)
                draw.line([(cx * s, y * s), (int((cx - reach) * s), int((y - 18) * s))],
                          fill=darks[slot], width=3 * s)
            for blotch in range(8):
                angle = 2 * math.pi * blotch / 8 + slot * 0.33
                dx = math.cos(angle) * half_w * (0.30 + 0.04 * (blotch % 3))
                dy = math.sin(angle) * half_h * 0.38
                radius = 9 + (blotch % 3) * 3
                points = []
                for corner in range(7):
                    a = 2 * math.pi * corner / 7 + angle * 0.35
                    variation = 0.72 + 0.28 * math.sin(corner * 2.17 + blotch)
                    points.append(((cx + dx + math.cos(a) * radius * 1.45 * variation) * s,
                                   (cy + dy + math.sin(a) * radius * variation) * s))
                draw.polygon(points,
                             fill=(margins[slot][0], margins[slot][1], margins[slot][2], 175))

    supersampled_texture(palm_leaflets, CUTOUTS / "date_palm_leaflet_ribbon_rgba_1024.png")
    supersampled_texture(leaf_bark_litter, CUTOUTS / "leaf_bark_litter_rgba_1024.png")
    supersampled_texture(philodendron_leaves, CUTOUTS / "philodendron_lobed_leaf_rgba_1024.png")
    supersampled_texture(coleus_leaves, CUTOUTS / "coleus_leaf_rgba_1024.png")


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
    "M_Aloe_Leaf": ((0.24, 0.42, 0.22), 0.0, 0.55, None),
    "M_Aloe_Base": ((0.20, 0.16, 0.10), 0.0, 0.90, None),
    "M_Philodendron_Crown": ((0.18, 0.14, 0.09), 0.0, 0.90, None),
    "M_Philodendron_Petiole": ((0.28, 0.34, 0.16), 0.0, 0.60, None),
    "M_Philodendron_Leaf": ((0.10, 0.26, 0.13), 0.0, 0.42, "philodendron_lobed_leaf_rgba_1024.png"),
    "M_Coleus_Base": ((0.18, 0.13, 0.08), 0.0, 0.90, None),
    "M_Coleus_Stem": ((0.34, 0.28, 0.20), 0.0, 0.60, None),
    "M_Coleus_Leaf": ((0.36, 0.16, 0.20), 0.0, 0.50, "coleus_leaf_rgba_1024.png"),
    "M_Bench_CastFrame_Intact": ((0.16, 0.24, 0.16), 0.15, 0.55, None),
    "M_Bench_SeatSlat_Intact": ((0.42, 0.27, 0.14), 0.0, 0.62, None),
    "M_Bench_BackSlat_Intact": ((0.40, 0.26, 0.13), 0.0, 0.62, None),
    "M_Bench_CastFrame_Damaged": ((0.30, 0.18, 0.10), 0.05, 0.72, None),
    "M_Bench_SeatSlat_Damaged": ((0.34, 0.30, 0.24), 0.0, 0.80, None),
    "M_Bench_BackSlat_Damaged": ((0.33, 0.29, 0.23), 0.0, 0.80, None),
    "M_BrochureStand_Frame": ((0.10, 0.10, 0.11), 0.10, 0.50, None),
    "M_BrochureStand_Pocket": ((0.44, 0.44, 0.40), 0.05, 0.42, None),
    "M_BrochureStand_Paper": ((0.82, 0.78, 0.66), 0.0, 0.70, None),
    "M_Fountain_BasinWall": ((0.46, 0.45, 0.40), 0.0, 0.86, None),
    "M_Fountain_BasinFloor": ((0.30, 0.28, 0.23), 0.0, 0.92, None),
    "M_Fountain_Pedestal": ((0.24, 0.22, 0.19), 0.0, 0.88, None),
    "M_Fountain_LeafLitter": ((0.42, 0.30, 0.16), 0.0, 0.72, "leaf_bark_litter_rgba_1024.png"),
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

HANDOFF = """# Entrance-Terrace Reveal Kit — Handoff (Slice 1 base + Slice 2 supporting species + Slice 3 furniture)

Source: `scripts/generate_entrance_terrace_reveal_kit.py`
Verify: `scripts/verify_entrance_terrace_reveal_kit.py`
Units: Unreal centimetres, Z-up. Every OBJ is one object, no `g` records,
named `usemtl` slots, indexed UVs on every corner, Z=0 / base-centred origin.
Foliage vertex RGB encodes wind stiffness (0 = rigid root, 1 = free tip).

Slice 2 adds three supporting display specimens: an aloe rosette, a
philodendron, and a coleus mound. Each is a composed specimen, not a hedge
module.

Slice 3 adds public visitor furniture: a pair of 1960s municipal park benches
(one intact, one subtly sagged/damaged), a freestanding period brochure/
leaflet stand, and one dry, non-functioning octagonal public-garden fountain.
All four are rigid props and carry **no vertex colour** -- the damaged bench
shows its damage through bowed beam geometry and a distinct weathered
material, never through paint-by-vertex.

MTL: `SourceMesh/entrance_terrace_reveal/VD_EntranceTerraceReveal.mtl`
RGBA cutouts: `cutouts/entrance_terrace_reveal/` — four alpha sheets (date-palm
leaflet, leaf/bark litter, philodendron lobed leaf, coleus patterned leaf),
each referenced by both `map_Kd` and `map_d`. Slice 3 reuses the leaf/bark
litter sheet for the fountain's collected leaf debris rather than adding a
fifth sheet.

## Import steps (Unreal)
1. Import each OBJ as its own Static Mesh; keep "Combine Meshes" OFF (one object
   per file already).
2. Import the RGBA sheets as textures; connect RGB -> Base Color and A ->
   Opacity Mask on every masked leaf/leaflet/litter material.
3. On every foliage mesh (date palm, aloe, philodendron, coleus) enable "Vertex
   Colors" import and drive a wind/pivot-sway node from vertex-colour luminance
   (0 anchored/rigid, 1 free tip). Trunks, stems, petioles and leaf attachments
   are 0; free leaf tips approach 1. The Slice 3 furniture (benches, brochure
   stand, fountain) imports with no vertex colour at all -- do not wire a wind
   node to it.
4. Author collision per the notes below; do NOT let Unreal auto-generate a
   single convex hull on the planters or the fountain — it seals the open
   mouth / basin. Foliage leaves generally take NO collision.

{assets}

## Scatter usage
The three `VD_SoilDressing_*` meshes are base-centred at Z=0 and sized to drop
into both these planters and the existing `SourceMesh/terrace_botanical`
planters. Scatter/rotate freely around Z; they carry no wind colour.

## Slice 3 furniture usage
`VD_Bench_Municipal_Intact` and `VD_Bench_Municipal_Damaged` share the same
196 cm footprint and frame layout so they place cleanly in pairs (e.g. flanking
a walkway) without visually mismatching in scale. Mix them freely; the damaged
variant reads as a single neglected bench in an otherwise-maintained row, not
a different bench type. `VD_BrochureStand_Institutional` and
`VD_Fountain_DryBasin` are each single freestanding props.
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
    ("VD_Aloe_Specimen", "Supporting specimen — aloe rosette",
     "~80 cm tall x ~1.2 m spread; 32 thick 3-D succulent leaves in four tiers with serrated margins.",
     "M_Aloe_Leaf (thick lofted diamond-section blades, no alpha), M_Aloe_Base (basal crown).",
     "No leaf collision. If a physical blocker is wanted, one short vertical capsule (~10 cm radius x ~20 cm) over the basal crown only; never hull the spreading leaves."),
    ("VD_Philodendron_Specimen", "Supporting specimen — philodendron",
     "~1.1-1.7 m tall; 11 large lobed alpha-cut leaf sheets on real curved petioles rising from a crown clump.",
     "M_Philodendron_Crown (rootball clump), M_Philodendron_Petiole (real petiole tubes), M_Philodendron_Leaf (lobed alpha-cut leaf sheets).",
     "No leaf/petiole collision (overlap-only). If needed, a single small capsule (~12 cm radius) over the crown clump so visitors do not walk through the base; leaves stay non-colliding."),
    ("VD_Coleus_Specimen", "Supporting specimen — coleus mound",
     "~45-75 cm tall low dense mound, wider than tall; branching real stems with 60 opposite decussate patterned alpha-cut leaves (burgundy centre, chartreuse margin).",
     "M_Coleus_Base (soil crown), M_Coleus_Stem (real branching stems), M_Coleus_Leaf (patterned alpha-cut leaves).",
     "No leaf collision. Optionally one low box/capsule (~12 cm radius x ~12 cm) over the base crown; do not hull the mound of leaves."),
    ("VD_Bench_Municipal_Intact", "Public visitor furniture — 1960s municipal park bench (intact)",
     "196 cm long x ~46 cm deep x ~78 cm tall (to back top); ~44 cm seat height; tubular welded/cast-steel end frames, 6 seat slats + 4 back slats, flat and true.",
     "M_Bench_CastFrame_Intact (tubular end frames + stretchers), M_Bench_SeatSlat_Intact (6 real timber seat boards), M_Bench_BackSlat_Intact (4 real timber back boards). No vertex colour.",
     "Two simple boxes (seat slab + back slab) plus a capsule or box per end frame, OR complex-as-simple on the tube frame silhouette. Do not collide individual slats separately."),
    ("VD_Bench_Municipal_Damaged", "Public visitor furniture — 1960s municipal park bench (damaged/sagged)",
     "Same 196 cm x ~46 cm footprint as the intact bench so the pair reads as one row; seat boards bow down to ~5 cm mid-span sag, the back frame leans further (~74 cm back top), one seat stretcher has dropped.",
     "M_Bench_CastFrame_Damaged (leaning/corroded frame), M_Bench_SeatSlat_Damaged (weathered, sagging boards), M_Bench_BackSlat_Damaged (weathered back boards). No vertex colour -- damage is geometric + a distinct weathered material only.",
     "Same collision approach as the intact bench (simple boxes/capsules per frame end + seat/back slabs, or complex-as-simple); size the seat-slab box to the sagged mid-span, not the flat rest height."),
    ("VD_BrochureStand_Institutional", "Public visitor furniture — freestanding brochure/leaflet stand",
     "~148 cm tall; ~45 cm footprint on a splayed 3-leg tripod foot; 5 shallow angled sheet-metal pockets climbing the post, each still holding one warped paper leaflet card.",
     "M_BrochureStand_Frame (post + tripod legs), M_BrochureStand_Pocket (5 angled pocket trays), M_BrochureStand_Paper (5 warped leaflet cards). No vertex colour.",
     "One simple box or vertical capsule around the post + tripod footprint. Paper cards get NO collision (overlap-only)."),
    ("VD_Fountain_DryBasin", "Public visitor furniture — dry, non-functioning octagonal public-garden fountain",
     "~380 cm across x 112 cm tall; octagonal basin, dry recessed floor at 46 cm (well below the rim), stained central pedestal/nozzle stub to ~86 cm, 10 leaf-litter cards collected on the floor. No water material.",
     "M_Fountain_BasinWall (outer wall + rim lip + inner drop), M_Fountain_BasinFloor (dry floor annulus), M_Fountain_Pedestal (stained pedestal/nozzle stub), M_Fountain_LeafLitter (collected leaf-litter cards, reuses the Slice 1 leaf/bark litter sheet). No vertex colour.",
     "Segmented ring collision: 8 convex wall segments (one per octagon face) + a separate floor-annulus disc + a short cylinder/capsule for the pedestal. NEVER one convex hull across the whole prop -- that seals the dry basin and hides/blocks the recessed floor."),
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
        build_aloe("VD_Aloe_Specimen", 8101),
        build_philodendron("VD_Philodendron_Specimen", 8102),
        build_coleus("VD_Coleus_Specimen", 8103),
        build_bench("VD_Bench_Municipal_Intact", False, 8301),
        build_bench("VD_Bench_Municipal_Damaged", True, 8302),
        build_brochure_stand("VD_BrochureStand_Institutional", 8401),
        build_fountain("VD_Fountain_DryBasin", 8501),
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
        "slice": "entrance-terrace reveal kit (slice 1 base + slice 2 supporting species + slice 3 furniture)",
        "mesh_count": len(meshes),
        "foliage_contract": {
            "alpha_cut_rgba_sheets": 4,
            "wind_encoding": "OBJ vertex RGB grayscale; 0=root/rigid, 1=free tip",
            "palm_fronds": 16,
            "palm_leaflet_pairs_per_frond": 24,
        },
        "supporting_species": {
            "VD_Aloe_Specimen": {
                "form": "multi-tier succulent rosette; thick 3-D diamond-section leaves, serrated margins",
                "leaves": 32,
                "alpha_sheets": [],
            },
            "VD_Philodendron_Specimen": {
                "form": "real petioles carrying large lobed alpha-cut leaf sheets on curved ribbons",
                "leaves": 11,
                "alpha_sheets": ["philodendron_lobed_leaf_rgba_1024.png"],
            },
            "VD_Coleus_Specimen": {
                "form": "low dense mound; branching real stems, opposite decussate patterned alpha-cut leaves",
                "leaves": 60,
                "alpha_sheets": ["coleus_leaf_rgba_1024.png"],
            },
        },
        "public_furniture": {
            "contract": "rigid props; zero vertex colour on every furniture mesh",
            "VD_Bench_Municipal_Intact": {
                "form": "tubular end frames + real slatted timber seat/back, flat and true",
                "seat_slats": 6, "back_slats": 4, "sag_cm": 0.0,
            },
            "VD_Bench_Municipal_Damaged": {
                "form": "same frame layout as the intact bench; boards bow down mid-span, frame leans further",
                "seat_slats": 6, "back_slats": 4, "sag_cm": 5.0,
            },
            "VD_BrochureStand_Institutional": {
                "form": "tripod-footed post with angled sheet-metal pockets, each holding one warped paper card",
                "pockets": 5, "paper_cards": 5,
            },
            "VD_Fountain_DryBasin": {
                "form": "dry octagonal basin, recessed floor well below the rim, stained pedestal stub, no water material",
                "sides": 8, "leaf_litter_cards": 10,
                "rim_to_floor_drop_cm": 66.0,
            },
        },
        "meshes": manifest_meshes,
    }
    (QA / "generation_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

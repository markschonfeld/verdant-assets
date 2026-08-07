#!/usr/bin/env python3
"""Generate the Rootstead west-endwall + entrance replacement asset.

Builds one rigid OBJ (`VD_RootsteadWestEndwallEntry`) that integrates the full
west gable triangular lattice, the ENDGLAZE_W transfer/sill junction, an
architectural entrance reveal/jamb/head/sill with a topology-integrated
aperture, and a rigid climbing trellis standing proud of the entrance facade --
plus a separate, explicitly optional animated-leaf replacement OBJ.

This is a REPLACEMENT for the whole west gable, not the additive occlusion
pattern on `origin/feat/rootstead-west-entry-assets` (PR #17): that delivery
never touched the lattice (it only masked it with a facade box) and it baked
static "frosted leaf" glass into the same rigid object that fills the animated
door-leaf sweep volume, so the doorway would always read as shut. Neither
mistake is repeated: the lattice is cut through by the entrance via node
snapping (not arbitrary member deletion), and the leaf envelope stays
completely empty in the main mesh.

See `scripts/rootstead_west_endwall_entry_spec.py` for the shared numeric
contract this generator and `scripts/verify_rootstead_west_endwall_entry.py`
both work from, and `references/architecture/ROOTSTEAD_WEST_ENDWALL_ENTRY_HANDOFF.md`
for the Unreal-side integration notes (collision, placement, PIE walk test).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import rootstead_west_endwall_entry_spec as spec  # noqa: E402

OUT = ROOT / "SourceMesh" / "architecture"
QA = ROOT / "qa" / "rootstead_west_endwall_entry"

Vec3 = tuple[float, float, float]
Vec2 = tuple[float, float]


# ---------------------------------------------------------------------------
# Mesh authoring helpers
# ---------------------------------------------------------------------------

class Mesh:
    def __init__(self, name: str, mtl_name: str) -> None:
        self.name = name
        self.mtl_name = mtl_name
        self.vertices: list[Vec3] = []
        self.faces: list[tuple[str, tuple[int, ...]]] = []

    def vertex(self, point: Vec3) -> int:
        """Returns the new vertex's 1-based OBJ index."""
        self.vertices.append(point)
        return len(self.vertices)

    def face(self, material: str, indices: Iterable[int]) -> None:
        self.faces.append((material, tuple(indices)))

    def box(self, minimum: Vec3, maximum: Vec3, material: str) -> None:
        self.box_multi(minimum, maximum, {
            "z0": material, "z1": material, "x0": material, "x1": material, "y0": material, "y1": material,
        })

    def box_multi(self, minimum: Vec3, maximum: Vec3, face_materials: dict[str, str]) -> None:
        """A single connected box with an independently assigned material per face.

        Face keys: x0/x1 (the two X-normal faces, the leaf's glazed front/back),
        y0/y1, z0/z1. One shared 8-vertex box, so the result is one connected
        component even though it carries multiple `usemtl` slots.
        """
        x0, y0, z0 = minimum
        x1, y1, z1 = maximum
        ids = [self.vertex((x, y, z)) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
        faces = {"z0": (0, 1, 3, 2), "z1": (4, 6, 7, 5), "y0": (0, 4, 5, 1),
                  "y1": (2, 3, 7, 6), "x0": (0, 2, 6, 4), "x1": (1, 5, 7, 3)}
        for key, f in faces.items():
            self.face(face_materials[key], (ids[i] for i in f))

    def extrude_poly_x(self, x0: float, x1: float, points_yz: list[Vec2], material: str) -> list[int]:
        """Extrude a closed (y, z) polygon along X into a closed solid.

        Returns the x1-cap vertex ids, in the same order as `points_yz`, so
        the caller can record cross-checkable vertex references.
        """
        n = len(points_yz)
        cap0 = [self.vertex((x0, y, z)) for y, z in points_yz]
        cap1 = [self.vertex((x1, y, z)) for y, z in points_yz]
        self.face(material, list(reversed(cap0)))
        self.face(material, cap1)
        for i in range(n):
            j = (i + 1) % n
            self.face(material, (cap0[i], cap0[j], cap1[j], cap1[i]))
        return cap1

    def cylinder(self, start: Vec3, end: Vec3, radius: float, sides: int,
                 material: str) -> tuple[tuple[int, int], tuple[int, int]]:
        """Closed solid cylinder. Returns ((start_idx, count), (end_idx, count))."""
        delta = tuple(end[i] - start[i] for i in range(3))
        length = math.sqrt(sum(v * v for v in delta))
        axis = tuple(v / length for v in delta)
        seed = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.92 else (1.0, 0.0, 0.0)
        side = (axis[1] * seed[2] - axis[2] * seed[1],
                axis[2] * seed[0] - axis[0] * seed[2],
                axis[0] * seed[1] - axis[1] * seed[0])
        sl = math.sqrt(sum(v * v for v in side))
        side = tuple(v / sl for v in side)
        up = (axis[1] * side[2] - axis[2] * side[1],
              axis[2] * side[0] - axis[0] * side[2],
              axis[0] * side[1] - axis[1] * side[0])
        ring_ranges: list[tuple[int, int]] = []
        rings: list[list[int]] = []
        for point in (start, end):
            first = None
            ring = []
            for i in range(sides):
                angle = 2.0 * math.pi * i / sides
                idx = self.vertex((
                    point[0] + radius * (math.cos(angle) * side[0] + math.sin(angle) * up[0]),
                    point[1] + radius * (math.cos(angle) * side[1] + math.sin(angle) * up[1]),
                    point[2] + radius * (math.cos(angle) * side[2] + math.sin(angle) * up[2]),
                ))
                if first is None:
                    first = idx
                ring.append(idx)
            ring_ranges.append((first, sides))
            rings.append(ring)
        self.face(material, reversed(rings[0]))
        self.face(material, rings[1])
        for i in range(sides):
            j = (i + 1) % sides
            self.face(material, (rings[0][i], rings[0][j], rings[1][j], rings[1][i]))
        return (ring_ranges[0], ring_ranges[1])

    def face_uvs(self, face: tuple[int, ...], scale: float = 100.0) -> list[Vec2]:
        points = [self.vertices[i - 1] for i in face]
        nx = ny = nz = 0.0
        for p, q in zip(points, points[1:] + points[:1]):
            nx += (p[1] - q[1]) * (p[2] + q[2])
            ny += (p[2] - q[2]) * (p[0] + q[0])
            nz += (p[0] - q[0]) * (p[1] + q[1])
        dominant = max(range(3), key=lambda i: abs((nx, ny, nz)[i]))
        if dominant == 0:
            return [(p[1] / scale, p[2] / scale) for p in points]
        if dominant == 1:
            return [(p[0] / scale, p[2] / scale) for p in points]
        return [(p[0] / scale, p[1] / scale) for p in points]

    def write(self) -> None:
        lines = [f"# Generated by {Path(__file__).name} -- do not hand-edit", f"mtllib {self.mtl_name}",
                  f"o {self.name}"]
        lines.extend(f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in self.vertices)
        uv_index_lists: list[tuple[int, ...]] = []
        next_uv = 1
        for _, face in self.faces:
            uvs = self.face_uvs(face)
            lines.extend(f"vt {u:.6f} {v:.6f}" for u, v in uvs)
            uv_index_lists.append(tuple(range(next_uv, next_uv + len(uvs))))
            next_uv += len(uvs)
        current = None
        for (material, face), uv_ids in zip(self.faces, uv_index_lists):
            if material != current:
                lines.extend((f"usemtl {material}", "s 1"))
                current = material
            lines.append("f " + " ".join(f"{v}/{uv}" for v, uv in zip(face, uv_ids)))
        (OUT / f"{self.name}.obj").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_mtl(name: str, materials: dict[str, tuple[Vec3, float, float]]) -> None:
    lines = [f"# Semantic preview materials for {name}"]
    for material, (color, roughness, opacity) in materials.items():
        lines.extend((f"newmtl {material}", f"Kd {color[0]:.3f} {color[1]:.3f} {color[2]:.3f}",
                      f"Pr {roughness:.3f}", f"d {opacity:.3f}", "illum 2", ""))
    (OUT / f"{name}.mtl").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Lattice: triangular grid over the arch, boundary-snapped to the true arc and
# to the entrance-hole rectangle, so the aperture is integrated by topology.
# ---------------------------------------------------------------------------

ROW_HEIGHT = spec.GABLE_PITCH * math.sqrt(3.0) / 2.0
HOLE_HALF_Y = spec.ENTRANCE_HOLE_HALF_Y
HOLE_TOP_Z_LOCAL = spec.local_z(spec.ENTRANCE_HOLE_TOP_Z_WORLD)
DOMAIN_MARGIN = spec.GABLE_PITCH * 0.5
HOLE_MARGIN = spec.GABLE_PITCH * 0.5
SNAP_DEDUP_DIST = 8.0


def hole_nearest_point(y: float, z_local: float) -> tuple[float, float]:
    ymin, ymax = -HOLE_HALF_Y, HOLE_HALF_Y
    zmin, zmax = 0.0, HOLE_TOP_Z_LOCAL
    outside = y < ymin or y > ymax or z_local < zmin or z_local > zmax
    if outside:
        return (min(max(y, ymin), ymax), min(max(z_local, zmin), zmax))
    dist_left, dist_right = y - ymin, ymax - y
    dist_bottom, dist_top = z_local - zmin, zmax - z_local
    m = min(dist_left, dist_right, dist_bottom, dist_top)
    if m == dist_left:
        return (ymin, z_local)
    if m == dist_right:
        return (ymax, z_local)
    if m == dist_bottom:
        return (y, zmin)
    return (y, zmax)


def hole_signed_distance(y: float, z_local: float) -> float:
    dy = abs(y) - HOLE_HALF_Y
    dz = max(-z_local, z_local - HOLE_TOP_Z_LOCAL)
    if dy <= 0 and dz <= 0:
        return max(dy, dz)
    return math.hypot(max(dy, 0.0), max(dz, 0.0))


def build_grid() -> tuple[list[list[int]], dict[tuple[int, int], tuple[float, float]]]:
    """Regular unsnapped equilateral grid. Positions are (y, world_z)."""
    raw: dict[tuple[int, int], tuple[float, float]] = {}
    rows: list[list[int]] = []
    i = 0
    max_z = spec.CROWN_Z + ROW_HEIGHT * 1.5
    while spec.FIELD_BASE_Z_WORLD + i * ROW_HEIGHT <= max_z:
        z_world = spec.FIELD_BASE_Z_WORLD + i * ROW_HEIGHT
        offset = spec.GABLE_PITCH / 2.0 if i % 2 == 1 else 0.0
        ks: list[int] = []
        k = 0
        y = -spec.HALF_SPAN_Y - spec.GABLE_PITCH + offset
        while y <= spec.HALF_SPAN_Y + spec.GABLE_PITCH:
            raw[(i, k)] = (y, z_world)
            ks.append(k)
            k += 1
            y = -spec.HALF_SPAN_Y - spec.GABLE_PITCH + offset + k * spec.GABLE_PITCH
        rows.append(ks)
        i += 1
    return rows, raw


def classify_nodes(raw: dict[tuple[int, int], tuple[float, float]]) -> dict[tuple[int, int], dict]:
    nodes: dict[tuple[int, int], dict] = {}
    for key, (y, z_world) in raw.items():
        r_node = math.hypot(y, z_world - spec.ARCH_CENTER_Z)
        delta = spec.ARCH_RADIUS - r_node
        if delta < -DOMAIN_MARGIN:
            continue  # clearly outside the arch envelope
        boundary = "interior"
        if delta <= DOMAIN_MARGIN:
            scale = spec.ARCH_RADIUS / r_node if r_node > 1e-6 else 1.0
            y = y * scale
            z_world = spec.ARCH_CENTER_Z + (z_world - spec.ARCH_CENTER_Z) * scale
            boundary = "arch"

        z_local = spec.local_z(z_world)
        hd = hole_signed_distance(y, z_local)
        if hd < -HOLE_MARGIN:
            continue  # clearly inside the entrance hole -- no lattice there
        if abs(hd) <= HOLE_MARGIN:
            y, z_local = hole_nearest_point(y, z_local)
            z_world = spec.world_z(z_local)
            boundary = "hole"

        nodes[key] = {"y": y, "z_world": z_world, "boundary": boundary}

    # Dedup near-coincident hole-snapped nodes (can happen right at a hole corner).
    hole_keys = [k for k, n in nodes.items() if n["boundary"] == "hole"]
    redirect: dict[tuple[int, int], tuple[int, int]] = {}
    for a_idx, a in enumerate(hole_keys):
        if a in redirect:
            continue
        for b in hole_keys[a_idx + 1:]:
            if b in redirect:
                continue
            na, nb = nodes[a], nodes[b]
            if math.hypot(na["y"] - nb["y"], na["z_world"] - nb["z_world"]) < SNAP_DEDUP_DIST:
                redirect[b] = a
    for dead in redirect:
        del nodes[dead]
    return nodes, redirect


def apex_col(k: int, row_offset_is_half: bool) -> int:
    return k + 1 if row_offset_is_half else k


def build_edges(rows: list[list[int]], nodes: dict[tuple[int, int], dict],
                 redirect: dict[tuple[int, int], tuple[int, int]]) -> set[tuple[tuple[int, int], tuple[int, int]]]:
    def resolve(key: tuple[int, int]) -> tuple[int, int] | None:
        key = redirect.get(key, key)
        return key if key in nodes else None

    edges: set[tuple[tuple[int, int], tuple[int, int]]] = set()

    def add_row_edges(row_idx: int) -> None:
        for k in rows[row_idx]:
            a, b = resolve((row_idx, k)), resolve((row_idx, k + 1))
            if a and b and a != b:
                edges.add((min(a, b), max(a, b)))

    for i in range(len(rows)):
        add_row_edges(i)

    for i in range(len(rows) - 1):
        offset_half = (i % 2 == 1)
        for k in rows[i]:
            a, b = resolve((i, k)), resolve((i, k + 1))
            c = resolve((i + 1, apex_col(k, offset_half)))
            if a and b and c and len({a, b, c}) == 3:
                edges.add((min(a, c), max(a, c)))
                edges.add((min(b, c), max(b, c)))
        offset_half_next = ((i + 1) % 2 == 1)
        for k in rows[i + 1]:
            a, b = resolve((i + 1, k)), resolve((i + 1, k + 1))
            c = resolve((i, apex_col(k, offset_half_next)))
            if a and b and c and len({a, b, c}) == 3:
                edges.add((min(a, c), max(a, c)))
                edges.add((min(b, c), max(b, c)))
    return edges


def build_panes(rows: list[list[int]], nodes: dict[tuple[int, int], dict],
                 redirect: dict[tuple[int, int], tuple[int, int]]) -> list[tuple[tuple[int, int], tuple[int, int], tuple[int, int]]]:
    def resolve(key: tuple[int, int]) -> tuple[int, int] | None:
        key = redirect.get(key, key)
        return key if key in nodes else None

    tris: list[tuple[tuple[int, int], tuple[int, int], tuple[int, int]]] = []
    seen: set[frozenset] = set()

    def add(a, b, c) -> None:
        if a is None or b is None or c is None:
            return
        s = frozenset((a, b, c))
        if len(s) != 3 or s in seen:
            return
        seen.add(s)
        tris.append((a, b, c))

    for i in range(len(rows) - 1):
        offset_half = (i % 2 == 1)
        for k in rows[i]:
            a, b = resolve((i, k)), resolve((i, k + 1))
            c = resolve((i + 1, apex_col(k, offset_half)))
            add(a, b, c)
        offset_half_next = ((i + 1) % 2 == 1)
        for k in rows[i + 1]:
            a, b = resolve((i + 1, k)), resolve((i + 1, k + 1))
            c = resolve((i, apex_col(k, offset_half_next)))
            add(a, b, c)
    return tris


def pane_material(node_ids: tuple[tuple[int, int], ...]) -> str:
    h = sum(hash(n) for n in node_ids) & 0xFFFFFFFF
    return spec.MAT_GLAZE_REPAIR if h % 5 == 0 else spec.MAT_GLAZE_ACRYLIC


def build_lattice(mesh: Mesh) -> tuple[dict, dict, list]:
    rows, raw = build_grid()
    nodes, redirect = classify_nodes(raw)
    edge_keys = build_edges(rows, nodes, redirect)
    pane_keys = build_panes(rows, nodes, redirect)

    node_id_of: dict[tuple[int, int], str] = {k: f"{k[0]}_{k[1]}" for k in nodes}
    graph_nodes: dict[str, dict] = {}
    node_touch_radius: dict[tuple[int, int], float] = {k: 0.0 for k in nodes}

    for a, b in edge_keys:
        za, zb = nodes[a]["z_world"], nodes[b]["z_world"]
        r = spec.tube_radius_for_z((za + zb) / 2.0)
        node_touch_radius[a] = max(node_touch_radius[a], r)
        node_touch_radius[b] = max(node_touch_radius[b], r)

    for key, n in nodes.items():
        radius = node_touch_radius[key] or spec.TUBE_RADIUS_MID
        collar_r = radius * spec.JOINT_COLLAR_RADIUS_FACTOR
        h = spec.JOINT_COLLAR_HALF_LENGTH
        z_local = spec.local_z(n["z_world"])
        (start_idx, start_count), _ = mesh.cylinder(
            (spec.TUBE_X - h, n["y"], z_local), (spec.TUBE_X + h, n["y"], z_local),
            collar_r, 10, spec.MAT_ALUMINIUM)
        combined_count = start_count * 2
        graph_nodes[node_id_of[key]] = {
            "y": n["y"], "z_world": n["z_world"], "boundary": n["boundary"],
            "collar_vertex_start": start_idx - 1, "collar_vertex_count": combined_count,
        }

    graph_edges: list[dict] = []
    for a, b in edge_keys:
        na, nb = nodes[a], nodes[b]
        z_mid = (na["z_world"] + nb["z_world"]) / 2.0
        radius = spec.tube_radius_for_z(z_mid)
        za, zb = spec.local_z(na["z_world"]), spec.local_z(nb["z_world"])
        (s_idx, s_cnt), (e_idx, e_cnt) = mesh.cylinder(
            (spec.TUBE_X, na["y"], za), (spec.TUBE_X, nb["y"], zb), radius, 8, spec.MAT_ALUMINIUM)
        graph_edges.append({
            "a": node_id_of[a], "b": node_id_of[b], "z_mid_world": z_mid, "radius": radius,
            "start_vertex_start": s_idx - 1, "start_vertex_count": s_cnt,
            "end_vertex_start": e_idx - 1, "end_vertex_count": e_cnt,
        })

    pane_thickness = 5.0
    graph_panes: list[dict] = []
    for a, b, c in pane_keys:
        material = pane_material((a, b, c))
        pts_yz = [(nodes[k]["y"], spec.local_z(nodes[k]["z_world"])) for k in (a, b, c)]
        cap = mesh.extrude_poly_x(spec.PANE_X - pane_thickness / 2.0, spec.PANE_X + pane_thickness / 2.0,
                                   pts_yz, material)
        graph_panes.append({
            "nodes": [node_id_of[a], node_id_of[b], node_id_of[c]],
            "material": material,
            "vertex_ids": [i - 1 for i in cap],
        })

    return graph_nodes, {"edges": graph_edges}, graph_panes, nodes, edge_keys


# ---------------------------------------------------------------------------
# Transfer/sill cap: continuous ENDGLAZE_W contact, minus the entrance gap.
# ---------------------------------------------------------------------------

def build_transfer_cap(mesh: Mesh) -> list[list[float]]:
    max_width = spec.arch_half_width_at_z(spec.ENDGLAZE_Z_TOP)
    segments = [(-max_width, -HOLE_HALF_Y), (HOLE_HALF_Y, max_width)]
    for y0, y1 in segments:
        mesh.box((spec.ENDGLAZE_X_FAR, y0, 0.0), (spec.TUBE_X, y1, spec.TRANSFER_CAP_Z_HEIGHT), spec.MAT_ALUMINIUM)
    return [[y0, y1] for y0, y1 in segments]


# ---------------------------------------------------------------------------
# Entrance reveal / jamb / head / sill, and the facade piers + trellis.
# ---------------------------------------------------------------------------

def build_entrance(mesh: Mesh) -> None:
    reveal = spec.MAT_ENTRANCE_REVEAL
    gap = spec.MAT_SEAL_SHADOW_GAP

    head_bottom = spec.local_z(spec.EXISTING_HEAD_Z_WORLD[0])  # 392, world 3892
    head_top = spec.local_z(spec.EXISTING_HEAD_Z_WORLD[1])     # 450, world 3950
    head_return_top = spec.local_z(3974.0)

    # Sill: main slab + a stepped nosing lip toward the exterior. Kept below
    # the animated leaf envelope's bottom (world 3508, local 8) with a 2 uu
    # clearance -- must never intrude into the leaf sweep volume.
    mesh.box((-430.0, -480.0, 0.0), (-300.0, 480.0, 6.0), reveal)
    mesh.box((-445.0, -480.0, 0.0), (-430.0, 480.0, 3.0), reveal)

    gap_half = 2.0
    for side in (-1.0, 1.0):
        y_inner = side * spec.JAMB_Y_INNER
        y_step = side * (spec.JAMB_Y_INNER + 41.0)
        y_outer = side * spec.JAMB_Y_OUTER
        y_step_near = y_step - math.copysign(gap_half, y_step)
        y_step_far = y_step + math.copysign(gap_half, y_step)
        y0, y1 = sorted((y_inner, y_step_near))
        y0b, y1b = sorted((y_step_far, y_outer))
        # Outer face (flush with the reveal opening).
        mesh.box((-430.0, y0, 0.0), (-390.0, y1, head_bottom), reveal)
        # Stepped inner return, offset in from the outer face -- a real return,
        # not a second copy of the same box.
        mesh.box((-390.0, y0b, 0.0), (-350.0, y1b, head_bottom), reveal)
        # Shadow-gap groove straddling the step line, recessed a uu deeper
        # than either adjacent face so it actually reads as a cut line.
        gap_y0, gap_y1 = sorted((y_step_near, y_step_far))
        mesh.box((-391.0, gap_y0, 0.0), (-389.0, gap_y1, head_bottom), gap)

    # Head: same stepped-return language as the jambs, plus a soffit/drip
    # return that closes the top of the opening.
    mesh.box((-430.0, -480.0, head_bottom), (-390.0, 480.0, head_top), reveal)
    mesh.box((-390.0, -465.0, head_bottom), (-350.0, 465.0, head_top), reveal)
    mesh.box((-392.0, -465.0, head_bottom), (-388.0, 465.0, head_top), gap)
    mesh.box((-430.0, -480.0, head_top), (-350.0, 480.0, head_return_top), reveal)

    # Fixed frosted transom above the head return -- architecturally useful,
    # clear of both the head return and the animated leaf envelope.
    mesh.box((spec.FROSTED_TRANSOM_X[0], spec.FROSTED_TRANSOM_Y[0], spec.local_z(spec.FROSTED_TRANSOM_Z_WORLD[0])),
              (spec.FROSTED_TRANSOM_X[1], spec.FROSTED_TRANSOM_Y[1], spec.local_z(spec.FROSTED_TRANSOM_Z_WORLD[1])),
              spec.MAT_FROSTED_TRANSOM)


def build_facade_and_trellis(mesh: Mesh) -> tuple[list[dict], list[dict]]:
    reveal = spec.MAT_ENTRANCE_REVEAL
    trellis = spec.MAT_TRELLIS_STEEL
    facade_solids: list[dict] = []

    # facade_solids are recorded in WORLD (x, y, z) throughout, matching
    # trellis_rails -- both get converted to local Z the same way downstream.
    pier_z = (0.0, spec.local_z(spec.PIER_Z_WORLD[1]))
    for side in (-1.0, 1.0):
        y0 = side * spec.PIER_Y_INNER
        y1 = side * spec.PIER_Y_OUTER
        mn = (spec.PIER_X[0], min(y0, y1), pier_z[0])
        mx = (spec.PIER_X[1], max(y0, y1), pier_z[1])
        mesh.box(mn, mx, reveal)
        facade_solids.append({"name": f"PIER_{'L' if side < 0 else 'R'}",
                               "min": [mn[0], mn[1], spec.world_z(mn[2])],
                               "max": [mx[0], mx[1], spec.world_z(mx[2])]})

    band_z = (spec.local_z(spec.HEAD_BAND_Z_WORLD[0]), spec.local_z(spec.HEAD_BAND_Z_WORLD[1]))
    band_mn = (spec.HEAD_BAND_X[0], spec.HEAD_BAND_Y[0], band_z[0])
    band_mx = (spec.HEAD_BAND_X[1], spec.HEAD_BAND_Y[1], band_z[1])
    mesh.box(band_mn, band_mx, reveal)
    facade_solids.append({"name": "HEAD_BAND",
                           "min": [band_mn[0], band_mn[1], spec.world_z(band_mn[2])],
                           "max": [band_mx[0], band_mx[1], spec.world_z(band_mx[2])]})

    rails: list[dict] = []
    rail_x = spec.TRELLIS_RAIL_X_CENTER
    rail_r = spec.TRELLIS_RAIL_RADIUS
    tie_r = spec.TRELLIS_TIE_RADIUS
    rail_z0, rail_z1 = pier_z

    for side in (-1.0, 1.0):
        ys = [side * spec.PIER_Y_INNER + side * 40.0,
              side * (spec.PIER_Y_INNER + spec.PIER_Y_OUTER) / 2.0,
              side * spec.PIER_Y_OUTER - side * 40.0]
        for y in ys:
            start = (rail_x, y, rail_z0)
            end = (rail_x, y, rail_z1)
            mesh.cylinder(start, end, rail_r, 10, trellis)
            rails.append({"start": [start[0], start[1], spec.world_z(start[2])],
                          "end": [end[0], end[1], spec.world_z(end[2])], "radius": rail_r, "kind": "rail_side"})
        for z_local in (rail_z0 + 130.0, rail_z0 + 300.0, rail_z0 + 470.0, rail_z0 + 640.0):
            start = (rail_x, ys[0], z_local)
            end = (rail_x, ys[-1], z_local)
            mesh.cylinder(start, end, tie_r, 8, trellis)
            rails.append({"start": [start[0], start[1], spec.world_z(start[2])],
                          "end": [end[0], end[1], spec.world_z(end[2])], "radius": tie_r, "kind": "tie_side"})

    head_rail_z = spec.local_z(spec.HEAD_BAND_Z_WORLD[1]) + 30.0
    start = (rail_x, -spec.PIER_Y_INNER, head_rail_z)
    end = (rail_x, spec.PIER_Y_INNER, head_rail_z)
    mesh.cylinder(start, end, rail_r, 10, trellis)
    rails.append({"start": [start[0], start[1], spec.world_z(start[2])],
                  "end": [end[0], end[1], spec.world_z(end[2])], "radius": rail_r, "kind": "rail_head"})
    for y in (-spec.PIER_Y_INNER + 40.0, 0.0, spec.PIER_Y_INNER - 40.0):
        start = (rail_x, y, spec.local_z(spec.HEAD_BAND_Z_WORLD[0]))
        end = (rail_x, y, head_rail_z)
        mesh.cylinder(start, end, tie_r, 8, trellis)
        rails.append({"start": [start[0], start[1], spec.world_z(start[2])],
                      "end": [end[0], end[1], spec.world_z(end[2])], "radius": tie_r, "kind": "tie_head"})

    return rails, facade_solids


# ---------------------------------------------------------------------------
# Optional animated-leaf replacement (separate object, not additive).
# ---------------------------------------------------------------------------

def build_leaves() -> Mesh:
    """Two disconnected leaf components in one object -- each a single
    connected solid (so the connected-component count is exactly 2), with the
    two X-normal faces (the ones a player actually sees head-on) carrying the
    required frosted-glass slot and the thin perimeter carrying the frame
    slot. This mesh REPLACES the existing DOOR_LeafL/DOOR_LeafR meshes; it is
    not additive geometry.
    """
    mesh = Mesh(spec.LEAF_OBJ_NAME, f"{spec.LEAF_OBJ_NAME}.mtl")
    frame = spec.LEAF_MAT_FRAME
    glass = spec.LEAF_MAT_FROSTED

    x0, x1 = spec.LEAF_ENVELOPE_X
    z0, z1 = (spec.local_z(spec.LEAF_ENVELOPE_Z_WORLD[0]), spec.local_z(spec.LEAF_ENVELOPE_Z_WORLD[1]))
    centre_gap = 6.0

    for side in (-1.0, 1.0):
        y_hinge = side * spec.LEAF_ENVELOPE_Y[1]
        y_meeting = side * centre_gap
        y0, y1 = (y_hinge, y_meeting) if side < 0 else (y_meeting, y_hinge)
        mesh.box_multi((x0, y0, z0), (x1, y1, z1), {
            "x0": glass, "x1": glass,
            "y0": frame, "y1": frame, "z0": frame, "z1": frame,
        })

    return mesh


def write_leaf_mtl() -> None:
    write_mtl(spec.LEAF_OBJ_NAME, {
        spec.LEAF_MAT_FRAME: ((0.30, 0.34, 0.30), 0.62, 1.0),
        spec.LEAF_MAT_FROSTED: ((0.66, 0.74, 0.72), 0.55, 0.55),
    })


def rebase_to_z0(mesh: Mesh) -> float:
    """Shift every vertex up so the mesh's true lowest point sits at local Z=0.

    Joint-collar cylinders (finite radius, centred on a node) dip below their
    node's nominal Z, so the lowest point of the authored geometry is not
    exactly at the nominal datum. Rather than hand-derive that dip, measure it
    and shift by exactly that amount; the applied shift is written to the
    graph JSON as `z_datum_shift` so the verifier can align its own local-Z
    bookkeeping to the same rebased vertices.
    """
    shift = -min(v[2] for v in mesh.vertices)
    mesh.vertices = [(x, y, z + shift) for x, y, z in mesh.vertices]
    return shift


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)

    mesh = Mesh(spec.MAIN_OBJ_NAME, f"{spec.MAIN_OBJ_NAME}.mtl")
    graph_nodes, edge_bucket, graph_panes, _nodes, _edge_keys = build_lattice(mesh)
    cap_segments = build_transfer_cap(mesh)
    build_entrance(mesh)
    rails, facade_solids = build_facade_and_trellis(mesh)
    z_shift = rebase_to_z0(mesh)
    mesh.write()

    write_mtl(mesh.name, {
        spec.MAT_ALUMINIUM: ((0.30, 0.36, 0.34), 0.72, 1.0),
        spec.MAT_GLAZE_ACRYLIC: ((0.58, 0.72, 0.78), 0.35, 0.45),
        spec.MAT_GLAZE_REPAIR: ((0.68, 0.76, 0.60), 0.30, 0.45),
        spec.MAT_ENTRANCE_REVEAL: ((0.44, 0.42, 0.35), 0.88, 1.0),
        spec.MAT_TRELLIS_STEEL: ((0.20, 0.24, 0.19), 0.76, 1.0),
        spec.MAT_SEAL_SHADOW_GAP: ((0.06, 0.06, 0.06), 0.95, 1.0),
        spec.MAT_FROSTED_TRANSOM: ((0.64, 0.73, 0.70), 0.60, 0.55),
    })

    leaf_mesh = build_leaves()
    leaf_z_shift = rebase_to_z0(leaf_mesh)
    leaf_mesh.write()
    write_leaf_mtl()

    graph = {
        "spec_version": 1,
        "z_datum_shift": z_shift,
        "world_placement": [0.0, 0.0, spec.FIELD_BASE_Z_WORLD - z_shift],
        "leaf_z_datum_shift": leaf_z_shift,
        "leaf_world_placement": [0.0, 0.0, spec.FIELD_BASE_Z_WORLD - leaf_z_shift],
        "nodes": graph_nodes,
        "edges": edge_bucket["edges"],
        "panes": graph_panes,
        "transfer_cap_segments_y": cap_segments,
        "trellis_rails": rails,
        "facade_solids": facade_solids,
        "hole": {"half_y": HOLE_HALF_Y, "top_z_world": spec.ENTRANCE_HOLE_TOP_Z_WORLD},
        "arch": {"center_y": spec.ARCH_CENTER_Y, "center_z": spec.ARCH_CENTER_Z,
                  "radius": spec.ARCH_RADIUS, "crown_z": spec.CROWN_Z},
        "counts": {"nodes": len(graph_nodes), "edges": len(edge_bucket["edges"]), "panes": len(graph_panes)},
    }
    (QA / "rootstead_west_endwall_entry_lattice_graph.json").write_text(
        json.dumps(graph, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {mesh.name}: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces, "
          f"{len(graph_nodes)} lattice nodes, {len(edge_bucket['edges'])} tubes, {len(graph_panes)} panes")
    print(f"wrote {leaf_mesh.name}: {len(leaf_mesh.vertices)} vertices, {len(leaf_mesh.faces)} faces")


if __name__ == "__main__":
    main()

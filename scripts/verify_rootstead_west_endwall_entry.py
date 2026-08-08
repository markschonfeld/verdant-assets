#!/usr/bin/env python3
"""Prove -- not just report -- the Rootstead west-endwall-entry replacement asset.

Reads the generated OBJ/MTL pair, the companion lattice-graph JSON the
generator emits alongside them, and the handoff doc, then independently
recomputes every claim in `docs/VERDANT_PROJECT_BRIEF.md`'s asset brief:
one-object/no-group/UV/no-vertex-colour contract, world placement and arch
envelope, 300 uu triangular-lattice coherence with a topology-integrated
entrance aperture (no floating tube ends, no orphan nodes), vault-kit-matched
tube sizing and source-mesh-derived fitting profiles, continuous ENDGLAZE
contact, an empty animated-door-leaf envelope in the main mesh, a matching
optional leaf-replacement mesh, and positive trellis stand-off within the
VEST_Frame hard east limit.

The graph JSON is not trusted at face value: every node/edge/pane record it
makes is cross-checked against the *actual* vertex coordinates the generator
wrote into the OBJ (see `_cross_check_*`), so a generator bug that only wrote
a correct-looking JSON without correct geometry would fail here.
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import cast

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import rootstead_west_endwall_entry_spec as spec  # noqa: E402
from rootstead_vault_node_profile import (  # noqa: E402
    VaultNodeProfile,
    generated_triangles_per_node,
    load_vault_node_profile,
)

SOURCE = ROOT / "SourceMesh" / "architecture"
QA = ROOT / "qa" / "rootstead_west_endwall_entry"
HANDOFF = ROOT / "references" / "architecture" / "ROOTSTEAD_WEST_ENDWALL_ENTRY_HANDOFF.md"

Vec3 = tuple[float, float, float]
Vec2 = tuple[float, float]
Face = tuple[str, tuple[int, ...], tuple[int, ...]]

REQUIRED_MIN_MATERIALS = {
    spec.MAT_ALUMINIUM, spec.MAT_GLAZE_ACRYLIC, spec.MAT_GLAZE_REPAIR,
    spec.MAT_ENTRANCE_REVEAL, spec.MAT_TRELLIS_STEEL, spec.MAT_SEAL_SHADOW_GAP,
}


# ---------------------------------------------------------------------------
# OBJ parsing
# ---------------------------------------------------------------------------

class ObjMesh:
    def __init__(self, name: str) -> None:
        self.name = name
        self.vertices: list[Vec3] = []
        self.texcoords: list[Vec2] = []
        self.faces: list[Face] = []
        self.objects: list[str] = []
        self.groups = 0
        self.mtllib: str | None = None
        self.vertex_color_records = 0


def parse_obj(path: Path) -> ObjMesh:
    mesh = ObjMesh(path.stem)
    material = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if not parts:
            continue
        tag = parts[0]
        if tag == "v":
            mesh.vertices.append(tuple(map(float, parts[1:4])))  # type: ignore[arg-type]
            if len(parts) > 4:
                mesh.vertex_color_records += 1
        elif tag == "vt":
            mesh.texcoords.append(tuple(map(float, parts[1:3])))  # type: ignore[arg-type]
        elif tag == "o":
            mesh.objects.append(parts[1])
        elif tag == "g":
            mesh.groups += 1
        elif tag == "mtllib":
            mesh.mtllib = parts[1]
        elif tag == "usemtl":
            material = parts[1]
        elif tag == "f":
            corners = [token.split("/") for token in parts[1:]]
            verts = tuple(int(c[0]) - 1 for c in corners)
            uvs = tuple(int(c[1]) - 1 if len(c) > 1 and c[1] else -1 for c in corners)
            mesh.faces.append((material, verts, uvs))
    return mesh


def triangle_area(a: Vec3, b: Vec3, c: Vec3) -> float:
    ab = tuple(b[i] - a[i] for i in range(3))
    ac = tuple(c[i] - a[i] for i in range(3))
    cross = (ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2],
              ab[0] * ac[1] - ab[1] * ac[0])
    return 0.5 * math.sqrt(sum(v * v for v in cross))


def face_triangle_area(mesh: ObjMesh, face: tuple[int, ...]) -> float:
    pts = [mesh.vertices[i] for i in face]
    return sum(triangle_area(pts[0], pts[i], pts[i + 1]) for i in range(1, len(pts) - 1))


def face_bounds(mesh: ObjMesh, face: tuple[int, ...]) -> tuple[Vec3, Vec3]:
    pts = [mesh.vertices[i] for i in face]
    return (tuple(min(p[i] for p in pts) for i in range(3)),
            tuple(max(p[i] for p in pts) for i in range(3)))  # type: ignore[return-value]


def material_component_bounds(mesh: ObjMesh, material: str) -> list[tuple[Vec3, Vec3]]:
    """Measure disconnected components for one material from actual OBJ vertices."""
    face_ids = [i for i, (mat, _, _) in enumerate(mesh.faces) if mat == material]
    vertex_faces: dict[int, list[int]] = defaultdict(list)
    for face_id in face_ids:
        for vertex_id in mesh.faces[face_id][1]:
            vertex_faces[vertex_id].append(face_id)

    unseen = set(face_ids)
    bounds: list[tuple[Vec3, Vec3]] = []
    while unseen:
        start = unseen.pop()
        stack = [start]
        component_faces = {start}
        while stack:
            current = stack.pop()
            for vertex_id in mesh.faces[current][1]:
                for neighbour in vertex_faces[vertex_id]:
                    if neighbour in unseen:
                        unseen.remove(neighbour)
                        component_faces.add(neighbour)
                        stack.append(neighbour)
        vertex_ids = {
            vertex_id
            for face_id in component_faces
            for vertex_id in mesh.faces[face_id][1]
        }
        points = [mesh.vertices[vertex_id] for vertex_id in vertex_ids]
        bounds.append((
            tuple(min(point[axis] for point in points) for axis in range(3)),
            tuple(max(point[axis] for point in points) for axis in range(3)),
        ))  # type: ignore[arg-type]
    return bounds


def aabb_overlap(a_min: Vec3, a_max: Vec3, b_min: Vec3, b_max: Vec3) -> bool:
    return all(a_min[i] < b_max[i] and b_min[i] < a_max[i] for i in range(3))


# ---------------------------------------------------------------------------
# Contract checks (shared shape for main + leaf OBJ)
# ---------------------------------------------------------------------------

def contract_checks(mesh: ObjMesh, *, expected_name: str, expected_mtl: str,
                     allowed_materials: set[str], required_min: set[str],
                     check_manifold: bool, min_faces: int = 500) -> dict[str, object]:
    failures: list[str] = []
    materials = {m for m, _, _ in mesh.faces}

    if mesh.objects != [expected_name]:
        failures.append(f"one-object contract failed: {mesh.objects}")
    if mesh.groups:
        failures.append(f"contains {mesh.groups} forbidden g records")
    if mesh.mtllib != expected_mtl:
        failures.append(f"mtllib {mesh.mtllib!r} != {expected_mtl!r}")
    if not materials.issubset(allowed_materials):
        failures.append(f"materials outside allowed set: {sorted(materials - allowed_materials)}")
    if not required_min.issubset(materials):
        failures.append(f"missing required material slots: {sorted(required_min - materials)}")
    if mesh.vertex_color_records:
        failures.append(f"{mesh.vertex_color_records} vertex-colour records on a rigid mesh")
    if any(name.startswith("UCX_") for name in mesh.objects):
        failures.append("object name starts with UCX_ (would bake per-poly import collision)")

    invalid_uvs = 0
    degenerate = 0
    edges: Counter[tuple[int, int]] = Counter()
    for _, face, uvs in mesh.faces:
        invalid_uvs += sum(i < 0 or i >= len(mesh.texcoords) for i in uvs)
        if len(uvs) != len(face):
            invalid_uvs += 1
        if face_triangle_area(mesh, face) < spec.DEGENERATE_AREA_EPS:
            degenerate += 1
        for i, v in enumerate(face):
            j = face[(i + 1) % len(face)]
            edges[(min(v, j), max(v, j))] += 1
    if invalid_uvs:
        failures.append(f"{invalid_uvs} face corners have invalid/missing UV indices")
    if degenerate:
        failures.append(f"{degenerate} degenerate (near-zero-area) faces")

    non_two = sum(c != 2 for c in edges.values())
    if check_manifold and non_two:
        failures.append(f"{non_two} non-manifold/boundary edges (every solid/prism must close)")

    bounds_min = tuple(min(v[i] for v in mesh.vertices) for i in range(3))
    bounds_max = tuple(max(v[i] for v in mesh.vertices) for i in range(3))
    if abs(bounds_min[2]) > spec.TOL_BOUNDS:
        failures.append(f"base is not at local Z=0: min Z = {bounds_min[2]}")

    face_count = len(mesh.faces)
    if not (min_faces < face_count < 400_000):
        failures.append(f"face count {face_count} outside practical bounds ({min_faces}, 400000)")

    return {
        "pass": not failures, "failures": failures,
        "vertices": len(mesh.vertices), "texture_coordinates": len(mesh.texcoords),
        "faces": face_count, "triangles": sum(len(f) - 2 for _, f, _ in mesh.faces),
        "object_names": mesh.objects, "group_records": mesh.groups,
        "vertex_color_records": mesh.vertex_color_records,
        "material_slots": sorted(materials), "invalid_uv_corners": invalid_uvs,
        "degenerate_faces": degenerate,
        "edge_incidence": {"total": len(edges), "non_two_face": non_two,
                            "checked": check_manifold},
        "bounds_local_cm": {"min": bounds_min, "max": bounds_max},
    }


# ---------------------------------------------------------------------------
# Lattice-graph cross checks
# ---------------------------------------------------------------------------

def _vertex_centroid(mesh: ObjMesh, start: int, count: int) -> Vec3:
    pts = mesh.vertices[start:start + count]
    n = len(pts)
    return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n, sum(p[2] for p in pts) / n)


def _vertex_ring_radius(mesh: ObjMesh, start: int, count: int, centroid: Vec3) -> float:
    pts = mesh.vertices[start:start + count]
    return sum(math.dist(p, centroid) for p in pts) / len(pts)



def hole_signed_distance(y: float, z: float, half_y: float, z_min: float, z_max: float) -> float:
    """Positive outside the hole rectangle, negative (magnitude = depth) inside.

    Deliberately takes an explicit `z_min` rather than assuming 0: this is
    used both against WORLD z (z_min=FIELD_BASE_Z_WORLD, for graph-only
    domain/hole classification, which must stay independent of the mesh's
    Z-datum rebase) and could be reused against local z if ever needed --
    hardcoding 0 here previously caused it to silently disagree with a
    rebased local Z.
    """
    dy = abs(y) - half_y
    dz_lo = z_min - z
    dz_hi = z - z_max
    dz = max(dz_lo, dz_hi)
    if dy <= 0 and dz <= 0:
        return max(dy, dz)
    ox = max(dy, 0.0)
    oz = max(dz, 0.0)
    return math.hypot(ox, oz)


def _joint_face_components(mesh: ObjMesh, node: dict) -> tuple[list[list[Vec3]], list[str], int]:
    """Measure edge-connected components from the actual OBJ face/vertex ranges."""
    failures: list[str] = []
    face_start = node.get("joint_face_start")
    face_count = node.get("joint_face_count")
    vertex_start = node.get("collar_vertex_start")
    vertex_count = node.get("collar_vertex_count")
    if not all(isinstance(value, int) for value in (face_start, face_count, vertex_start, vertex_count)):
        return [], ["joint profile ranges are missing from the graph"], 0
    face_start = cast(int, face_start)
    face_count = cast(int, face_count)
    vertex_start = cast(int, vertex_start)
    vertex_count = cast(int, vertex_count)
    if face_start < 0 or face_count <= 0 or face_start + face_count > len(mesh.faces):
        return [], ["joint face range is outside the actual OBJ"], 0
    if vertex_start < 0 or vertex_count <= 0 or vertex_start + vertex_count > len(mesh.vertices):
        return [], ["joint vertex range is outside the actual OBJ"], 0

    selected = mesh.faces[face_start:face_start + face_count]
    allowed = range(vertex_start, vertex_start + vertex_count)
    allowed_min, allowed_max = allowed.start, allowed.stop
    if any(vertex < allowed_min or vertex >= allowed_max for _, face, _ in selected for vertex in face):
        failures.append("joint face range references vertices outside its declared joint vertex range")
    if any(material != spec.MAT_ALUMINIUM for material, _, _ in selected):
        failures.append("joint face range contains a non-aluminium material")

    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    triangles = 0
    for local_index, (_, face, _) in enumerate(selected):
        triangles += len(face) - 2
        for a, b in zip(face, face[1:] + face[:1]):
            edge_faces[(min(a, b), max(a, b))].append(local_index)
    adjacency: dict[int, set[int]] = defaultdict(set)
    for touching in edge_faces.values():
        for face_index in touching:
            adjacency[face_index].update(other for other in touching if other != face_index)

    seen: set[int] = set()
    components: list[list[Vec3]] = []
    for start in range(len(selected)):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        component_faces: set[int] = set()
        while stack:
            current = stack.pop()
            component_faces.add(current)
            for neighbour in adjacency[current]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        vertex_ids = sorted({
            vertex for face_index in component_faces for vertex in selected[face_index][1]
        })
        components.append([mesh.vertices[vertex] for vertex in vertex_ids])
    return components, failures, triangles


def _measure_joint_profile(
    components: list[list[Vec3]], center: Vec3,
) -> tuple[list[dict[str, float]], dict[int, list[dict[str, float]]]]:
    """Map actual gable fitting points back into the reference node's X/Y/Z frame."""
    cx, cy, cz = center
    central: list[dict[str, float]] = []
    radial: dict[int, list[dict[str, float]]] = defaultdict(list)
    for component in components:
        # Reference X/Y are the gable Y/Z plane; reference Z is local X depth.
        points = [(point[1] - cy, point[2] - cz, point[0] - cx) for point in component]
        center_x = sum(point[0] for point in points) / len(points)
        center_y = sum(point[1] for point in points) / len(points)
        if math.hypot(center_x, center_y) < 5.0:
            central.append({
                "z_min": min(point[2] for point in points),
                "z_max": max(point[2] for point in points),
                "radius": max(math.hypot(point[0], point[1]) for point in points),
            })
            continue
        sector = round(math.atan2(center_y, center_x) / (math.pi / 3.0)) % 6
        direction = (math.cos(sector * math.pi / 3.0), math.sin(sector * math.pi / 3.0))
        tangent = (-direction[1], direction[0])
        radial_values = [point[0] * direction[0] + point[1] * direction[1] for point in points]
        tangent_values = [point[0] * tangent[0] + point[1] * tangent[1] for point in points]
        radial[sector].append({
            "radial_min": min(radial_values),
            "radial_max": max(radial_values),
            "tangent_extent": max(abs(min(tangent_values)), abs(max(tangent_values))),
            "axial_extent": max(abs(point[2]) for point in points),
        })
    central.sort(key=lambda item: item["z_min"])
    for pieces in radial.values():
        pieces.sort(key=lambda item: item["radial_max"] - item["radial_min"], reverse=True)
    return central, radial


def joint_profile_checks(mesh: ObjMesh, graph: dict) -> dict[str, object]:
    """Compare every generated fitting's actual geometry to VD_VaultNode_Far."""
    failures: list[str] = []
    profile: VaultNodeProfile = load_vault_node_profile()
    nodes = graph["nodes"]
    shift = graph.get("z_datum_shift", 0.0)
    expected_triangles = generated_triangles_per_node(spec.JOINT_PROFILE_SIDES)
    profile_metadata = graph.get("joint_profile", {})
    if profile_metadata.get("source_sha256") != profile.source_sha256:
        failures.append("graph joint-profile SHA does not match the committed reference OBJ")

    component_mismatch = 0
    central_mismatch = 0
    radial_group_mismatch = 0
    profile_extent_mismatch = 0
    triangle_mismatch = 0
    range_failures = 0
    measured_triangle_counts: list[int] = []
    tolerance = 0.05

    expected_central = [
        {"z_min": piece.z_min, "z_max": piece.z_max, "radius": piece.radius}
        for piece in profile.central
    ]
    expected_radial = {
        sector: [
            {"radial_min": piece.radial_min, "radial_max": piece.radial_max,
             "tangent_extent": piece.tangent_extent, "axial_extent": piece.axial_extent}
            for piece in pieces
        ]
        for sector, pieces in profile.radial_groups.items()
    }

    for node in nodes.values():
        components, local_failures, triangles = _joint_face_components(mesh, node)
        range_failures += len(local_failures)
        measured_triangle_counts.append(triangles)
        if len(components) != profile.source_components:
            component_mismatch += 1
        if triangles != expected_triangles:
            triangle_mismatch += 1
        center = (spec.TUBE_X, node["y"], spec.local_z(node["z_world"]) + shift)
        central, radial = _measure_joint_profile(components, center)
        if len(central) != len(expected_central):
            central_mismatch += 1
        else:
            for actual, expected in zip(central, expected_central):
                if any(abs(actual[key] - expected[key]) > tolerance for key in expected):
                    central_mismatch += 1
                    break
        if set(radial) != set(expected_radial) or any(
            len(radial.get(sector, [])) != len(expected_radial[sector]) for sector in expected_radial
        ):
            radial_group_mismatch += 1
        else:
            mismatch = False
            for sector in expected_radial:
                for actual, expected in zip(radial[sector], expected_radial[sector]):
                    if any(abs(actual[key] - expected[key]) > tolerance for key in expected):
                        mismatch = True
                        break
                if mismatch:
                    break
            if mismatch:
                profile_extent_mismatch += 1

    if range_failures:
        failures.append(f"{range_failures} joint face/vertex ranges do not describe actual aluminium geometry")
    if component_mismatch:
        failures.append(f"{component_mismatch} joints do not preserve the reference's "
                        f"{profile.source_components} edge-connected fitting components")
    if central_mismatch:
        failures.append(f"{central_mismatch} joints do not match the reference centre-piece profile")
    if radial_group_mismatch:
        failures.append(f"{radial_group_mismatch} joints do not contain six barrel/flange direction pairs")
    if profile_extent_mismatch:
        failures.append(f"{profile_extent_mismatch} joints differ from the reference barrel/flange extents")
    if triangle_mismatch:
        failures.append(f"{triangle_mismatch} joints do not use the {expected_triangles}-triangle far profile")

    return {
        "pass": not failures,
        "failures": failures,
        "reference_source": str(profile.source_path.relative_to(ROOT)),
        "reference_sha256": profile.source_sha256,
        "reference_triangles": profile.source_triangles,
        "reference_components": profile.source_components,
        "reference_central_components": len(profile.central),
        "reference_radial_groups": {str(sector): len(pieces) for sector, pieces in profile.radial_groups.items()},
        "generated_sides": spec.JOINT_PROFILE_SIDES,
        "generated_triangles_per_node": expected_triangles,
        "measured_triangle_range": [min(measured_triangle_counts), max(measured_triangle_counts)]
        if measured_triangle_counts else None,
        "component_mismatch_count": component_mismatch,
        "central_profile_mismatch_count": central_mismatch,
        "radial_group_mismatch_count": radial_group_mismatch,
        "profile_extent_mismatch_count": profile_extent_mismatch,
        "triangle_mismatch_count": triangle_mismatch,
        "range_failure_count": range_failures,
    }


def lattice_checks(mesh: ObjMesh, graph: dict) -> dict[str, object]:
    failures: list[str] = []
    nodes = graph["nodes"]
    edges = graph["edges"]
    panes = graph["panes"]
    shift = graph.get("z_datum_shift", 0.0)

    def lz(world_z_value: float) -> float:
        """Local Z of an actual OBJ vertex for a given world Z (rebase-aware)."""
        return spec.local_z(world_z_value) + shift

    # -- graph well-formedness -------------------------------------------------
    node_ids = set(nodes)
    dangling = [e for e in edges if e["a"] not in node_ids or e["b"] not in node_ids]
    if dangling:
        failures.append(f"{len(dangling)} edges reference a node id that does not exist")

    degree: Counter[str] = Counter()
    for e in edges:
        degree[e["a"]] += 1
        degree[e["b"]] += 1
    orphans = [n for n in node_ids if degree[n] < 2]
    if orphans:
        failures.append(f"{len(orphans)} nodes have degree < 2 (orphan/unsupported stub): "
                         f"{orphans[:10]}{'...' if len(orphans) > 10 else ''}")

    # -- nodes follow the arch and stay clear of the hole -----------------------
    # Deliberately WORLD z here, not local: domain/hole classification is a
    # property of the design graph and must stay independent of whatever
    # Z-datum rebase the generator applied to the OBJ vertices afterwards.
    hole_half_y = graph["hole"]["half_y"]
    hole_top_z_world = graph["hole"]["top_z_world"]
    bad_domain = []
    bad_hole = []
    bad_arch_snap = []
    bad_hole_snap = []
    for nid, n in nodes.items():
        y, z_world = n["y"], n["z_world"]
        half_width = spec.arch_half_width_at_z(z_world)
        if abs(y) > half_width + spec.TOL_ARCH_NODE:
            bad_domain.append(nid)
        hd = hole_signed_distance(y, z_world, hole_half_y, spec.FIELD_BASE_Z_WORLD, hole_top_z_world)
        if hd < -spec.TOL_HOLE_NODE:
            bad_hole.append(nid)
        if n["boundary"] == "arch":
            target_y, target_z = n.get("boundary_target") or (y, n["z_world"])
            r = math.hypot(target_y, target_z - spec.ARCH_CENTER_Z)
            if abs(r - spec.ARCH_RADIUS) > spec.TOL_ARCH_NODE:
                bad_arch_snap.append(nid)
        if n["boundary"] == "hole":
            if abs(hd) > spec.TOL_HOLE_NODE:
                bad_hole_snap.append(nid)
    if bad_domain:
        failures.append(f"{len(bad_domain)} nodes fall outside the arch envelope")
    if bad_hole:
        failures.append(f"{len(bad_hole)} nodes fall strictly inside the entrance hole")
    if bad_arch_snap:
        failures.append(f"{len(bad_arch_snap)} arch-boundary nodes are not on the circle "
                         f"(radius tolerance {spec.TOL_ARCH_NODE})")
    if bad_hole_snap:
        failures.append(f"{len(bad_hole_snap)} hole-boundary nodes are not on the hole rectangle")

    # -- pitch coherence ---------------------------------------------------
    short_or_long = 0
    for e in edges:
        a, b = nodes[e["a"]], nodes[e["b"]]
        d = math.hypot(a["y"] - b["y"], a["z_world"] - b["z_world"])
        boundary_edge = nodes[e["a"]]["boundary"] != "interior" or nodes[e["b"]]["boundary"] != "interior"
        lo, hi = (0.35, 1.9) if boundary_edge else (0.85, 1.15)
        if not (spec.GABLE_PITCH * lo <= d <= spec.GABLE_PITCH * hi):
            short_or_long += 1
        if d < 1.0:
            failures.append(f"edge {e['a']}-{e['b']} is near-zero length ({d:.3f})")
    if short_or_long:
        failures.append(f"{short_or_long} edges fall outside pitch-coherence tolerance for their kind")

    # -- cross-check declared graph geometry against actual OBJ vertices -------
    node_mismatch = 0
    for nid, n in nodes.items():
        c = _vertex_centroid(mesh, n["collar_vertex_start"], n["collar_vertex_count"])
        if math.hypot(c[1] - n["y"], c[2] - lz(n["z_world"])) > spec.TOL_NODE_TO_VERTEX:
            node_mismatch += 1
    if node_mismatch:
        failures.append(f"{node_mismatch} node joint collars are not centred on their declared position")

    edge_mismatch = 0
    floating_ends = 0
    for e in edges:
        a, b = nodes[e["a"]], nodes[e["b"]]
        cs = _vertex_centroid(mesh, e["start_vertex_start"], e["start_vertex_count"])
        ce = _vertex_centroid(mesh, e["end_vertex_start"], e["end_vertex_count"])
        da = math.hypot(cs[1] - a["y"], cs[2] - lz(a["z_world"]))
        db = math.hypot(ce[1] - b["y"], ce[2] - lz(b["z_world"]))
        da2 = math.hypot(ce[1] - a["y"], ce[2] - lz(a["z_world"]))
        db2 = math.hypot(cs[1] - b["y"], cs[2] - lz(b["z_world"]))
        best = min(da + db, da2 + db2)
        if best > 2 * spec.TOL_NODE_TO_VERTEX:
            edge_mismatch += 1
        if min(da, da2, db, db2) > spec.TOL_NODE_TO_VERTEX and best > 2 * spec.TOL_NODE_TO_VERTEX:
            floating_ends += 1
    if edge_mismatch:
        failures.append(f"{edge_mismatch} tube endpoints do not coincide with their declared nodes "
                         "(floating tube end)")

    pane_mismatch = 0
    for p in panes:
        for nid, vid in zip(p["nodes"], p["vertex_ids"]):
            n = nodes[nid]
            v = mesh.vertices[vid]
            if math.hypot(v[1] - n["y"], v[2] - lz(n["z_world"])) > spec.TOL_NODE_TO_VERTEX:
                pane_mismatch += 1
    if pane_mismatch:
        failures.append(f"{pane_mismatch} pane corners do not coincide with their declared lattice node")

    # -- measured member sizing against the installed vault kit ----------------
    band_radii: dict[str, list[float]] = {"lower": [], "mid": [], "upper": []}
    radius_mismatch = 0
    for e in edges:
        cs = _vertex_centroid(mesh, e["start_vertex_start"], e["start_vertex_count"])
        measured = _vertex_ring_radius(mesh, e["start_vertex_start"], e["start_vertex_count"], cs)
        if abs(measured - e["radius"]) > 0.5:
            radius_mismatch += 1
        z_mid = e["z_mid_world"]
        band = "lower" if z_mid < spec.BAND_LOWER_Z_WORLD else ("mid" if z_mid < spec.BAND_UPPER_Z_WORLD else "upper")
        band_radii[band].append(measured)
    if radius_mismatch:
        failures.append(f"{radius_mismatch} tube radii measured from the OBJ do not match the declared radius")

    avg = {k: (sum(v) / len(v) if v else 0.0) for k, v in band_radii.items()}
    if not (9.4 <= avg["mid"] <= 10.5):
        failures.append(f"z4000..6000 band (avg r={avg['mid']:.2f}) is outside the vault-tube "
                         "barrel range 9.4..10.5")

    joint_profile = joint_profile_checks(mesh, graph)
    if not joint_profile["pass"]:
        failures.extend(cast(list[str], joint_profile["failures"]))

    # -- area coverage: proves the field has no unintended gaps ----------------
    def domain_area() -> float:
        steps = 4000
        z0, z1 = spec.FIELD_BASE_Z_WORLD, spec.CROWN_Z
        h = (z1 - z0) / steps
        total = 0.0
        for i in range(steps + 1):
            z = z0 + i * h
            w = 2.0 * spec.arch_half_width_at_z(z)
            weight = 0.5 if i in (0, steps) else 1.0
            total += w * weight * h
        return total

    hole_area = 2.0 * hole_half_y * (graph["hole"]["top_z_world"] - spec.FIELD_BASE_Z_WORLD)
    expected_area = domain_area() - hole_area
    pane_area = 0.0
    for p in panes:
        pts = [mesh.vertices[i] for i in p["vertex_ids"]]
        pane_area += triangle_area(pts[0], pts[1], pts[2])
    ratio = pane_area / expected_area if expected_area else 0.0
    if not (0.80 <= ratio <= 1.05):
        failures.append(f"pane area coverage ratio {ratio:.3f} outside [0.80, 1.05] "
                         f"(measured {pane_area:.0f} vs expected {expected_area:.0f} sq-cm) "
                         "-- possible gap or overlap in the field")

    return {
        "pass": not failures, "failures": failures,
        "node_count": len(nodes), "edge_count": len(edges), "pane_count": len(panes),
        "orphan_nodes": len(orphans), "dangling_edges": len(dangling),
        "pitch_out_of_tolerance_edges": short_or_long,
        "floating_tube_ends": edge_mismatch,
        "measured_band_avg_radius_cm": avg,
        "vault_joint_profile": joint_profile,
        "pane_area_coverage": {"measured_sq_cm": pane_area, "expected_sq_cm": expected_area, "ratio": ratio},
    }


def locked_delivery_checks(mesh: ObjMesh, graph: dict) -> dict[str, object]:
    """Guard every PR #18 in-engine lock that regeneration could move."""
    failures: list[str] = []
    placement = tuple(map(float, graph.get("world_placement", ())))
    if len(placement) != 3 or any(abs(placement[i] - spec.WORLD_PLACEMENT[i]) > 1e-6 for i in range(3)):
        failures.append(f"world placement {placement} != locked {spec.WORLD_PLACEMENT}")

    bounds_min = tuple(min(v[i] for v in mesh.vertices) for i in range(3))
    bounds_max = tuple(max(v[i] for v in mesh.vertices) for i in range(3))
    for label, actual, expected in (
        ("minimum", bounds_min, spec.LOCKED_LOCAL_BOUNDS_MIN),
        ("maximum", bounds_max, spec.LOCKED_LOCAL_BOUNDS_MAX),
    ):
        if any(abs(actual[i] - expected[i]) > 0.01 for i in range(3)):
            failures.append(f"local bounds {label} {actual} != locked {expected}")

    materials = {material for material, _, _ in mesh.faces}
    if materials != spec.MAIN_MATERIALS:
        failures.append(f"material slots changed: {sorted(materials)} != {sorted(spec.MAIN_MATERIALS)}")

    reveal_components = material_component_bounds(mesh, spec.MAT_ENTRANCE_REVEAL)
    placement_z = placement[2] if len(placement) == 3 else spec.WORLD_PLACEMENT[2]
    jambs = [
        (lo, hi) for lo, hi in reveal_components
        if abs(lo[0] + 430.0) < 0.01 and abs(hi[0] + 390.0) < 0.01
        and abs(lo[2] + placement_z - 3500.0) < 0.01
        and abs(hi[2] + placement_z - 3892.0) < 0.01
    ]
    jamb_inner_edges = sorted(round(lo[1] if lo[1] > 0 else hi[1], 3) for lo, hi in jambs)
    if jamb_inner_edges != [-spec.JAMB_Y_INNER, spec.JAMB_Y_INNER]:
        failures.append(f"jamb inner edges {jamb_inner_edges} != locked +/-{spec.JAMB_Y_INNER}")

    sill_tops = [
        hi[2] + placement_z for lo, hi in reveal_components
        if abs(lo[2] + placement_z - 3500.0) < 0.01 and hi[1] - lo[1] >= 900.0
        and hi[0] <= -300.0
    ]
    sill_top = max(sill_tops, default=float("nan"))
    if not math.isfinite(sill_top) or abs(sill_top - 3506.0) > 0.01:
        failures.append(f"sill top world Z {sill_top} != locked 3506.0")

    triangles = sum(len(face) - 2 for _, face, _ in mesh.faces)
    if triangles > spec.JOINT_TRIANGLE_BUDGET:
        failures.append(f"triangle budget {triangles} exceeds the "
                        f"{spec.JOINT_TRIANGLE_BUDGET} source-profile ceiling")

    return {
        "pass": not failures,
        "failures": failures,
        "world_placement_cm": placement,
        "bounds_local_cm": {"min": bounds_min, "max": bounds_max},
        "jamb_inner_edges_y_cm": jamb_inner_edges,
        "sill_top_world_z_cm": sill_top,
        "material_slots": sorted(materials),
        "triangles": triangles,
        "triangle_budget_ceiling": spec.JOINT_TRIANGLE_BUDGET,
    }


def transfer_cap_checks(mesh: ObjMesh, graph: dict) -> dict[str, object]:
    failures: list[str] = []
    # Find the two actual wide aluminium box components which run from the
    # ENDGLAZE contact plane to the inboard tube plane. This deliberately does
    # not trust `transfer_cap_segments_y` from the generator's graph JSON.
    component_bounds = material_component_bounds(mesh, spec.MAT_ALUMINIUM)
    transfer_components = [
        (lo, hi) for lo, hi in component_bounds
        if lo[0] <= spec.ENDGLAZE_X_FAR + 0.5
        and hi[0] >= spec.TUBE_X - 0.5
        and hi[1] - lo[1] > 1000.0
        and abs((hi[2] - lo[2]) - spec.TRANSFER_CAP_Z_HEIGHT) <= 0.5
    ]
    if len(transfer_components) != 2:
        failures.append(f"found {len(transfer_components)} actual transfer-cap components, expected 2")
    segments = sorted((lo[1], hi[1]) for lo, hi in transfer_components)
    half_width = spec.arch_half_width_at_z(spec.ENDGLAZE_Z_TOP)
    hole_half_y = spec.ENTRANCE_HOLE_HALF_Y
    expected_gap = (-hole_half_y, hole_half_y)

    placement_z = float(graph["world_placement"][2])
    measured_contact_x: list[float] = []
    measured_world_z: list[float] = []
    for lo, hi in transfer_components:
        measured_contact_x.extend((lo[0], hi[0]))
        measured_world_z.extend((lo[2] + placement_z, hi[2] + placement_z))
        if abs(lo[0] - spec.ENDGLAZE_X_FAR) > 0.5 or abs(hi[0] - spec.TUBE_X) > 0.5:
            failures.append(f"actual transfer-cap X bounds {lo[0]:.2f}..{hi[0]:.2f} do not land on "
                            f"ENDGLAZE x={spec.ENDGLAZE_X_FAR} and tube plane x={spec.TUBE_X}")
        if abs((lo[2] + placement_z) - spec.ENDGLAZE_Z_TOP) > 0.5 or \
                abs((hi[2] + placement_z) - (spec.ENDGLAZE_Z_TOP + spec.TRANSFER_CAP_Z_HEIGHT)) > 0.5:
            failures.append(f"actual transfer-cap world Z bounds {lo[2] + placement_z:.2f}.."
                            f"{hi[2] + placement_z:.2f} do not meet ENDGLAZE top z={spec.ENDGLAZE_Z_TOP}")

    merged: list[list[float]] = []
    for s in segments:
        if merged and s[0] <= merged[-1][1] + 1.0:
            merged[-1][1] = max(merged[-1][1], s[1])
        else:
            merged.append(list(s))

    covered = sum(b - a for a, b in merged)
    expected_covered = 2 * half_width - (expected_gap[1] - expected_gap[0])
    if abs(covered - expected_covered) > 5.0:
        failures.append(f"transfer cap covers {covered:.1f} of {expected_covered:.1f} expected uu "
                         "of wall width -- gap beyond the entrance opening")
    if not merged or merged[0][0] > -half_width + 5.0 or merged[-1][1] < half_width - 5.0:
        failures.append("transfer cap does not reach the wall's outer y extent")
    gap_ok = any(abs(m1[1] - expected_gap[0]) < 5.0 for m1 in merged) and \
        any(abs(m2[0] - expected_gap[1]) < 5.0 for m2 in merged)
    if not gap_ok:
        failures.append("transfer cap gap is not aligned with the entrance hole width")

    return {
        "pass": not failures, "failures": failures,
        "actual_component_count": len(transfer_components),
        "actual_contact_x_range": [min(measured_contact_x), max(measured_contact_x)] if measured_contact_x else None,
        "actual_world_z_range": [min(measured_world_z), max(measured_world_z)] if measured_world_z else None,
        "required_ENDGLAZE_contact_x_range": [spec.ENDGLAZE_X_FAR, spec.ENDGLAZE_X_NEAR],
        "covered_y_uu": covered, "expected_y_uu": expected_covered,
        "segments": merged,
    }


def leaf_envelope_empty_check(mesh: ObjMesh, z_datum_shift: float) -> dict[str, object]:
    lo = (spec.LEAF_ENVELOPE_X[0], spec.LEAF_ENVELOPE_Y[0],
          spec.local_z(spec.LEAF_ENVELOPE_Z_WORLD[0]) + z_datum_shift)
    hi = (spec.LEAF_ENVELOPE_X[1], spec.LEAF_ENVELOPE_Y[1],
          spec.local_z(spec.LEAF_ENVELOPE_Z_WORLD[1]) + z_datum_shift)
    intrusions = []
    for idx, (material, face, _) in enumerate(mesh.faces):
        fmin, fmax = face_bounds(mesh, face)
        if aabb_overlap(fmin, fmax, lo, hi):
            intrusions.append({"face": idx, "material": material, "min": fmin, "max": fmax})
    failures = [f"{len(intrusions)} main-mesh faces intrude into the animated door-leaf envelope"] if intrusions else []
    return {
        "pass": not failures, "failures": failures,
        "envelope_local_cm": {"min": lo, "max": hi},
        "envelope_world_cm": {"x": spec.LEAF_ENVELOPE_X, "y": spec.LEAF_ENVELOPE_Y,
                               "z": spec.LEAF_ENVELOPE_Z_WORLD},
        "intrusions": intrusions[:20],
        "intrusion_count": len(intrusions),
    }


def trellis_checks(mesh: ObjMesh, graph: dict) -> dict[str, object]:
    failures: list[str] = []
    # Re-derive rail and facade AABBs from disconnected OBJ components. Graph
    # records are used only as a count cross-check, never as measured geometry.
    rails = material_component_bounds(mesh, spec.MAT_TRELLIS_STEEL)
    reveal_components = material_component_bounds(mesh, spec.MAT_ENTRANCE_REVEAL)
    facades = [
        (lo, hi) for lo, hi in reveal_components
        if abs(lo[0] - spec.PIER_X[0]) <= 0.5
        and abs(hi[0] - spec.PIER_X[1]) <= 0.5
        and hi[1] - lo[1] >= 500.0
    ]
    if len(rails) != 18:
        failures.append(f"actual OBJ contains {len(rails)} trellis components, expected 18")
    if len(rails) != len(graph["trellis_rails"]):
        failures.append(f"actual trellis component count {len(rails)} != graph record count "
                        f"{len(graph['trellis_rails'])}")
    if len(facades) != 3:
        failures.append(f"actual OBJ contains {len(facades)} facade solids, expected 3")
    clearances = []
    overlap_count = 0
    over_limit = 0
    facade_face_x = max((hi[0] for _, hi in facades), default=spec.TRELLIS_FACADE_FACE_X)
    for rmin, rmax in rails:
        if rmax[0] > spec.VEST_FRAME_X_HARD_LIMIT + 1e-6:
            over_limit += 1
        clearance = rmin[0] - facade_face_x
        clearances.append(clearance)
        if clearance <= 0:
            failures.append(f"actual trellis component {rmin}->{rmax} has non-positive "
                            f"clearance to facade: {clearance:.2f}")
        for fmin, fmax in facades:
            if aabb_overlap(rmin, rmax, fmin, fmax):
                overlap_count += 1
    if overlap_count:
        failures.append(f"{overlap_count} trellis-rail/facade-solid AABB overlaps")
    if over_limit:
        failures.append(f"{over_limit} trellis rails exceed the VEST_Frame hard east limit "
                         f"x={spec.VEST_FRAME_X_HARD_LIMIT}")
    min_clear = min(clearances) if clearances else None
    if min_clear is None:
        failures.append("no trellis rail was matched against a facade solid to measure clearance")

    return {
        "pass": not failures, "failures": failures,
        "actual_rail_component_count": len(rails), "actual_facade_solid_count": len(facades),
        "min_clearance_cm": min_clear,
        "hard_east_limit_cm": spec.VEST_FRAME_X_HARD_LIMIT,
    }


def leaf_obj_checks(mesh: ObjMesh) -> dict[str, object]:
    failures: list[str] = []
    contract = contract_checks(
        mesh, expected_name=spec.LEAF_OBJ_NAME, expected_mtl=f"{spec.LEAF_OBJ_NAME}.mtl",
        allowed_materials=spec.LEAF_MATERIALS, required_min={spec.LEAF_MAT_FROSTED},
        check_manifold=True, min_faces=5,
    )
    if not contract["pass"]:
        failures.extend(cast(list, contract["failures"]))

    adjacency: dict[int, set[int]] = defaultdict(set)
    for idx, (_, face, _) in enumerate(mesh.faces):
        for i in range(len(face)):
            a, b = face[i], face[(i + 1) % len(face)]
            key = (min(a, b), max(a, b))
            adjacency[idx]  # touch
    edge_to_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for idx, (_, face, _) in enumerate(mesh.faces):
        for i in range(len(face)):
            a, b = face[i], face[(i + 1) % len(face)]
            edge_to_faces[(min(a, b), max(a, b))].append(idx)
    for faces_sharing in edge_to_faces.values():
        for f in faces_sharing:
            adjacency[f].update(x for x in faces_sharing if x != f)

    seen: set[int] = set()
    components = 0
    for start in adjacency:
        if start in seen:
            continue
        components += 1
        stack = [start]
        seen.add(start)
        while stack:
            cur = stack.pop()
            for nxt in adjacency[cur]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
    if components != 2:
        failures.append(f"leaf OBJ has {components} connected components, expected exactly 2 (two leaves)")

    bounds_min = tuple(min(v[i] for v in mesh.vertices) for i in range(3))
    bounds_max = tuple(max(v[i] for v in mesh.vertices) for i in range(3))
    # X/Y are authored directly from world-measured values (no rebase), so
    # they compare exactly. Z gets its own independent base-at-zero rebase
    # (see `rebase_to_z0` in the generator), so only the Z *span* -- not its
    # absolute position -- is checked against the measured envelope height.
    if abs(bounds_min[0] - spec.LEAF_ENVELOPE_X[0]) > 2.0 or abs(bounds_max[0] - spec.LEAF_ENVELOPE_X[1]) > 2.0:
        failures.append(f"leaf X bounds ({bounds_min[0]}, {bounds_max[0]}) != measured envelope "
                         f"{spec.LEAF_ENVELOPE_X}")
    if abs(bounds_min[1] - spec.LEAF_ENVELOPE_Y[0]) > 2.0 or abs(bounds_max[1] - spec.LEAF_ENVELOPE_Y[1]) > 2.0:
        failures.append(f"leaf Y bounds ({bounds_min[1]}, {bounds_max[1]}) != measured envelope "
                         f"{spec.LEAF_ENVELOPE_Y}")
    z_span = bounds_max[2] - bounds_min[2]
    expected_z_span = spec.LEAF_ENVELOPE_Z_WORLD[1] - spec.LEAF_ENVELOPE_Z_WORLD[0]
    if abs(z_span - expected_z_span) > 2.0:
        failures.append(f"leaf Z span {z_span} != measured envelope height {expected_z_span}")

    return {
        "pass": not failures, "failures": failures,
        "contract": contract,
        "connected_components": components,
        "bounds_local_cm": {"min": bounds_min, "max": bounds_max},
        "measured_envelope_world_cm": {"x": spec.LEAF_ENVELOPE_X, "y": spec.LEAF_ENVELOPE_Y,
                                        "z": spec.LEAF_ENVELOPE_Z_WORLD},
        "replaces_actors": ["DOOR_LeafL", "DOOR_LeafR"],
        "additive": False,
    }


def handoff_doc_checks() -> dict[str, object]:
    failures: list[str] = []
    if not HANDOFF.exists():
        return {"pass": False, "failures": [f"{HANDOFF} does not exist"], "path": str(HANDOFF)}
    text = HANDOFF.read_text(encoding="utf-8")
    required_phrases = [
        "NoCollision", "segmented", "convex hull", "PIE", "complex-as-simple",
        "does not bridge", "DOOR_LeafL", "DOOR_LeafR", "not additive",
    ]
    missing = [p for p in required_phrases if p.lower() not in text.lower()]
    if missing:
        failures.append(f"handoff doc missing required guidance phrases: {missing}")
    return {"pass": not failures, "failures": failures, "path": str(HANDOFF.relative_to(ROOT))}


# ---------------------------------------------------------------------------
# Preview render (PIL; matplotlib is unavailable in this environment)
# ---------------------------------------------------------------------------

def render_preview(mesh: ObjMesh, leaf: ObjMesh | None) -> Path:
    QA.mkdir(parents=True, exist_ok=True)
    output = QA / "rootstead_west_endwall_entry_preview.png"
    image = Image.new("RGB", (2400, 1500), (16, 19, 18))
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default()

    color = {
        spec.MAT_ALUMINIUM: (150, 168, 160, 255),
        spec.MAT_GLAZE_ACRYLIC: (150, 195, 205, 130),
        spec.MAT_GLAZE_REPAIR: (185, 205, 150, 130),
        spec.MAT_ENTRANCE_REVEAL: (110, 102, 88, 255),
        spec.MAT_TRELLIS_STEEL: (70, 84, 66, 255),
        spec.MAT_SEAL_SHADOW_GAP: (30, 30, 28, 255),
        spec.MAT_FROSTED_TRANSOM: (170, 190, 185, 170),
        spec.LEAF_MAT_FROSTED: (165, 195, 190, 160),
        spec.LEAF_MAT_FRAME: (90, 96, 82, 255),
    }

    def draw_mesh(m: ObjMesh, box: tuple[int, int, int, int], axis: str, label: str,
                  y_range: tuple[float, float] | None = None, z_range: tuple[float, float] | None = None) -> None:
        x0, y0, x1, y1 = box
        pts = m.vertices
        if y_range or z_range:
            pts = [p for p in pts if (y_range is None or y_range[0] <= p[1] <= y_range[1])
                   and (z_range is None or z_range[0] <= p[2] <= z_range[1])]
        if not pts:
            pts = m.vertices
        if axis == "front":
            xs_all = [p[1] for p in pts]
        else:
            xs_all = [p[0] for p in pts]
        ys_all = [p[2] for p in pts]
        sx = (x1 - x0 - 60) / max(max(xs_all) - min(xs_all), 1.0)
        sy = (y1 - y0 - 60) / max(max(ys_all) - min(ys_all), 1.0)
        s = min(sx, sy)
        cx, cy = (min(xs_all) + max(xs_all)) / 2, (min(ys_all) + max(ys_all)) / 2
        screen_cx, screen_cy = (x0 + x1) / 2, (y0 + y1) / 2

        def project(p: Vec3) -> Vec2:
            px = p[1] if axis == "front" else p[0]
            py = p[2]
            return (screen_cx + (px - cx) * s, screen_cy - (py - cy) * s)

        polys = []
        for material, face, _ in m.faces:
            face_pts = [m.vertices[i] for i in face]
            # Detail panels are intentionally clipped to their measured window.
            # Requiring the whole face to be inside prevents full-width transfer
            # members from bleeding across adjacent preview panels.
            if y_range and not all(y_range[0] <= p[1] <= y_range[1] for p in face_pts):
                continue
            if z_range and not all(z_range[0] <= p[2] <= z_range[1] for p in face_pts):
                continue
            screen = [project(p) for p in face_pts]
            depth = sum(p[0] for p in face_pts) / len(face_pts)
            polys.append((depth, color.get(material, (200, 200, 200, 255)), screen))
        for _, col, poly in sorted(polys, key=lambda t: t[0]):
            draw.polygon(poly, fill=col, outline=(60, 66, 60, 120))
        draw.rectangle(box, outline=(90, 100, 90, 255), width=2)
        draw.text((box[0] + 12, box[1] + 10), label, fill=(235, 222, 190, 255), font=font)

    draw.text((50, 25), "ROOTSTEAD WEST ENDWALL + ENTRANCE / REPLACEMENT ASSET",
              fill=(240, 226, 192, 255), font=font)
    draw.text((50, 48), "full gable lattice, integrated entrance aperture, transfer sill, "
              "proud trellis -- leaves are a separate optional mesh",
              fill=(160, 176, 163, 255), font=font)

    draw_mesh(mesh, (40, 90, 1500, 1420), "front", "WEST GABLE / FRONT ELEVATION (full arch)")
    draw_mesh(mesh, (1540, 90, 2360, 760), "front",
              "ENTRANCE DETAIL (front)", y_range=(-900, 900), z_range=(0, 900))
    draw_mesh(mesh, (1540, 800, 2360, 1420), "side",
              "ENTRANCE DETAIL (side, sill->trellis)", z_range=(-50, 800))

    if leaf is not None:
        notes_y = 1430
    image.save(output)
    return output


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    obj_path = SOURCE / f"{spec.MAIN_OBJ_NAME}.obj"
    leaf_path = SOURCE / f"{spec.LEAF_OBJ_NAME}.obj"
    graph_path = QA / "rootstead_west_endwall_entry_lattice_graph.json"

    missing = [p for p in (obj_path, leaf_path, graph_path) if not p.exists()]
    if missing:
        report = {
            "all_pass": False,
            "failures": [f"required generated file missing: {p.relative_to(ROOT)}" for p in missing],
        }
        QA.mkdir(parents=True, exist_ok=True)
        (QA / "rootstead_west_endwall_entry_verification.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        raise SystemExit(1)

    mesh = parse_obj(obj_path)
    leaf_mesh = parse_obj(leaf_path)
    graph = json.loads(graph_path.read_text(encoding="utf-8"))

    sections = {
        "contract": contract_checks(
            mesh, expected_name=spec.MAIN_OBJ_NAME, expected_mtl=f"{spec.MAIN_OBJ_NAME}.mtl",
            allowed_materials=spec.MAIN_MATERIALS, required_min=REQUIRED_MIN_MATERIALS,
            check_manifold=True,
        ),
        "lattice": lattice_checks(mesh, graph),
        "locked_delivery": locked_delivery_checks(mesh, graph),
        "transfer_cap": transfer_cap_checks(mesh, graph),
        "leaf_envelope_empty": leaf_envelope_empty_check(mesh, graph.get("z_datum_shift", 0.0)),
        "trellis": trellis_checks(mesh, graph),
        "leaf_replacement_obj": leaf_obj_checks(leaf_mesh),
        "handoff_doc": handoff_doc_checks(),
    }

    report = {
        "all_pass": all(s["pass"] for s in sections.values()),
        "world_placement_cm": graph.get("world_placement", list(spec.WORLD_PLACEMENT)),
        "leaf_world_placement_cm": graph.get("leaf_world_placement", list(spec.WORLD_PLACEMENT)),
        "sections": sections,
        "collision_note": (
            "NoCollision on the render mesh. Do not accept Unreal's import-generated single "
            "convex hull (it bridges the door aperture on a 150 m-wide asset) and do not use "
            "convex decomposition. Do not use complex-as-simple for the whole asset. Author "
            "explicit segmented Unreal box collision primitives for the left/right entrance "
            "piers, head, jamb/reveal returns, and sill only where needed, plus broad lower "
            "structural zones; no primitive may bridge the door aperture. Glazing and the high "
            "lattice stay NoCollision."
        ),
    }

    QA.mkdir(parents=True, exist_ok=True)
    report_path = QA / "rootstead_west_endwall_entry_verification.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    preview = render_preview(mesh, leaf_mesh)

    failures = [f for s in sections.values() for f in s["failures"]]
    print(json.dumps({
        "all_pass": report["all_pass"],
        "report": str(report_path.relative_to(ROOT)),
        "preview": str(preview.relative_to(ROOT)),
        "failures": failures,
    }, indent=2))
    if not report["all_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Deterministic OBJ merge-by-distance and coincident-face hygiene.

The procedural generators build many closed primitives. When two primitives meet,
both can retain a cap on the same plane. This pass welds coincident coordinates,
removes faces collapsed by the weld, and retains one polygon from each exact
coincident polygon group. UVs and material assignments from the retained face are
preserved.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

Vec3 = tuple[float, float, float]


@dataclass
class Face:
    material: str
    smoothing: str | None
    corners: tuple[tuple[int, int | None, int | None], ...]


@dataclass
class Obj:
    comments: list[str]
    mtllib: str | None
    object_name: str
    vertices: list[Vec3]
    texcoords: list[tuple[float, ...]]
    normals: list[Vec3]
    faces: list[Face]


def _parse_corner(token: str) -> tuple[int, int | None, int | None]:
    parts = token.split("/")
    return (
        int(parts[0]) - 1,
        int(parts[1]) - 1 if len(parts) > 1 and parts[1] else None,
        int(parts[2]) - 1 if len(parts) > 2 and parts[2] else None,
    )


def parse_obj(path: Path) -> Obj:
    comments: list[str] = []
    mtllib = None
    object_name = path.stem
    vertices: list[Vec3] = []
    texcoords: list[tuple[float, ...]] = []
    normals: list[Vec3] = []
    faces: list[Face] = []
    material = ""
    smoothing: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if not parts:
            continue
        tag = parts[0]
        if tag == "#":
            comments.append(raw)
        elif raw.startswith("#"):
            comments.append(raw)
        elif tag == "mtllib":
            mtllib = " ".join(parts[1:])
        elif tag == "o":
            object_name = parts[1]
        elif tag == "v":
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif tag == "vt":
            texcoords.append(tuple(map(float, parts[1:])))
        elif tag == "vn":
            normals.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif tag == "usemtl":
            material = parts[1]
        elif tag == "s":
            smoothing = parts[1]
        elif tag == "f":
            faces.append(Face(material, smoothing, tuple(_parse_corner(token) for token in parts[1:])))
        elif tag == "g":
            raise ValueError(f"{path}: forbidden OBJ group record")
    if not vertices or not faces:
        raise ValueError(f"{path}: empty OBJ")
    return Obj(comments, mtllib, object_name, vertices, texcoords, normals, faces)


def _triangle_area(a: Vec3, b: Vec3, c: Vec3) -> float:
    ab = tuple(b[i] - a[i] for i in range(3))
    ac = tuple(c[i] - a[i] for i in range(3))
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    return 0.5 * math.sqrt(sum(value * value for value in cross))


def _face_is_degenerate(vertices: list[Vec3], ids: tuple[int, ...], area_epsilon: float) -> bool:
    if len(set(ids)) < 3:
        return True
    return any(
        _triangle_area(vertices[ids[0]], vertices[ids[index]], vertices[ids[index + 1]]) <= area_epsilon
        for index in range(1, len(ids) - 1)
    )


def _face_geometry(vertices: list[Vec3], face: Face) -> tuple[Vec3, Vec3, tuple[Vec3, ...]]:
    points = tuple(vertices[corner[0]] for corner in face.corners)
    centroid: Vec3 = (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
        sum(point[2] for point in points) / len(points),
    )
    normal = [0.0, 0.0, 0.0]
    for first, second in zip(points, points[1:] + points[:1]):
        normal[0] += (first[1] - second[1]) * (first[2] + second[2])
        normal[1] += (first[2] - second[2]) * (first[0] + second[0])
        normal[2] += (first[0] - second[0]) * (first[1] + second[1])
    length = math.sqrt(sum(value * value for value in normal))
    unit: Vec3 = (normal[0] / length, normal[1] / length, normal[2] / length)
    return centroid, unit, points


def _cyclic_corner_distance(first: tuple[Vec3, ...], second: tuple[Vec3, ...]) -> float:
    count = len(first)
    return min(
        max(math.dist(first[index], second[(start + direction * index) % count])
            for index in range(count))
        for direction in (1, -1)
        for start in range(count)
    )


def _stacked_face_pairs(vertices: list[Vec3], faces: list[Face], tolerance: float) -> list[tuple[int, int]]:
    """Match render-indistinguishable polygons using the Unreal audit tolerance."""
    if tolerance <= 0:
        return []
    records = [_face_geometry(vertices, face) for face in faces]
    bins: dict[tuple[object, ...], list[int]] = {}
    pairs: list[tuple[int, int]] = []
    for index, face in enumerate(faces):
        centroid, normal, points = records[index]
        cell = tuple(math.floor(value / tolerance) for value in centroid)
        for offset in itertools.product((-1, 0, 1), repeat=3):
            key = (len(points), face.material) + tuple(cell[axis] + offset[axis] for axis in range(3))
            for earlier in bins.get(key, []):
                other_centroid, other_normal, other_points = records[earlier]
                if math.dist(centroid, other_centroid) > tolerance:
                    continue
                if abs(sum(normal[axis] * other_normal[axis] for axis in range(3))) < 0.999999:
                    continue
                if _cyclic_corner_distance(points, other_points) > tolerance:
                    continue
                pairs.append((earlier, index))
        bins.setdefault((len(points), face.material) + cell, []).append(index)
    return pairs


def clean_obj(data: Obj, *, merge_distance: float = 0.0001,
              stack_tolerance: float = 1.0,
              area_epsilon: float = 1e-10,
              vertex_remap_out: list[int | None] | None = None,
              face_remap_out: list[int | None] | None = None) -> tuple[Obj, dict[str, int | float]]:
    if merge_distance <= 0:
        raise ValueError("merge_distance must be positive")

    cell_to_vertex: dict[tuple[int, int, int], int] = {}
    welded_vertices: list[Vec3] = []
    vertex_remap: list[int] = []
    for vertex in data.vertices:
        cell = (
            round(vertex[0] / merge_distance),
            round(vertex[1] / merge_distance),
            round(vertex[2] / merge_distance),
        )
        index = cell_to_vertex.get(cell)
        if index is None:
            index = len(welded_vertices)
            cell_to_vertex[cell] = index
            welded_vertices.append(vertex)
        vertex_remap.append(index)

    remapped_faces: list[tuple[int, Face]] = []
    degenerate_faces_removed = 0
    for original_index, face in enumerate(data.faces):
        corners = tuple((vertex_remap[v], vt, vn) for v, vt, vn in face.corners)
        ids = tuple(corner[0] for corner in corners)
        if _face_is_degenerate(welded_vertices, ids, area_epsilon):
            degenerate_faces_removed += 1
            continue
        remapped_faces.append((original_index, Face(face.material, face.smoothing, corners)))

    stacked_pairs = _stacked_face_pairs(
        welded_vertices, [face for _, face in remapped_faces], stack_tolerance
    )
    stacked_remove = {later for _, later in stacked_pairs}
    stacked_faces_removed = len(stacked_remove)
    remapped_faces = [
        item for index, item in enumerate(remapped_faces)
        if index not in stacked_remove
    ]

    seen: set[tuple[int, tuple[int, ...]]] = set()
    unique_faces: list[tuple[int, Face]] = []
    duplicate_faces_removed = 0
    for original_index, face in remapped_faces:
        ids = tuple(corner[0] for corner in face.corners)
        key = (len(ids), tuple(sorted(ids)))
        if key in seen:
            duplicate_faces_removed += 1
            continue
        seen.add(key)
        unique_faces.append((original_index, face))

    used_vertices = sorted({corner[0] for _, face in unique_faces for corner in face.corners})
    compact = {old: new for new, old in enumerate(used_vertices)}
    compact_vertices = [welded_vertices[old] for old in used_vertices]
    if vertex_remap_out is not None:
        vertex_remap_out.extend(compact.get(welded) for welded in vertex_remap)
    if face_remap_out is not None:
        mapped_faces: list[int | None] = [None] * len(data.faces)
        for compact_index, (original_index, _) in enumerate(unique_faces):
            mapped_faces[original_index] = compact_index
        face_remap_out.extend(mapped_faces)
    compact_faces = [
        Face(face.material, face.smoothing,
             tuple((compact[v], vt, vn) for v, vt, vn in face.corners))
        for _, face in unique_faces
    ]
    cleaned = Obj(data.comments, data.mtllib, data.object_name, compact_vertices,
                  data.texcoords, data.normals, compact_faces)
    before_triangles = sum(len(face.corners) - 2 for face in data.faces)
    after_triangles = sum(len(face.corners) - 2 for face in compact_faces)
    stats: dict[str, int | float] = {
        "merge_distance_cm": merge_distance,
        "vertices_before": len(data.vertices),
        "vertices_after": len(compact_vertices),
        "vertices_merged_or_orphaned": len(data.vertices) - len(compact_vertices),
        "faces_before": len(data.faces),
        "faces_after": len(compact_faces),
        "duplicate_faces_removed": duplicate_faces_removed,
        "stacked_faces_removed_1cm": stacked_faces_removed,
        "degenerate_faces_removed": degenerate_faces_removed,
        "triangles_before": before_triangles,
        "triangles_after": after_triangles,
        "triangles_removed": before_triangles - after_triangles,
    }
    return cleaned, stats


def audit_obj(data: Obj, *, stack_tolerance: float = 1.0,
              area_epsilon: float = 1e-10) -> dict[str, int | bool]:
    groups: dict[tuple[int, tuple[Vec3, ...]], int] = {}
    degenerate = 0
    triangles = 0
    for face in data.faces:
        ids = tuple(corner[0] for corner in face.corners)
        triangles += len(ids) - 2
        if _face_is_degenerate(data.vertices, ids, area_epsilon):
            degenerate += 1
        key = (len(ids), tuple(sorted(data.vertices[index] for index in ids)))
        groups[key] = groups.get(key, 0) + 1
    duplicate_groups = sum(count > 1 for count in groups.values())
    duplicate_faces = sum(count - 1 for count in groups.values() if count > 1)
    stacked_pairs = _stacked_face_pairs(data.vertices, data.faces, stack_tolerance)
    stacked_faces = {index for pair in stacked_pairs for index in pair}
    return {
        "pass": duplicate_groups == 0 and not stacked_pairs and degenerate == 0,
        "vertices": len(data.vertices),
        "faces": len(data.faces),
        "triangles": triangles,
        "duplicate_face_groups": duplicate_groups,
        "redundant_duplicate_faces": duplicate_faces,
        "stacked_face_pairs_1cm": len(stacked_pairs),
        "stacked_faces_1cm": len(stacked_faces),
        "degenerate_faces": degenerate,
    }


def assert_obj_hygiene(path: Path, *, stack_tolerance: float = 1.0,
                       area_epsilon: float = 1e-10) -> dict[str, int | bool]:
    """Hard gate used by individual asset verifiers and the tree audit."""
    report = audit_obj(parse_obj(path), stack_tolerance=stack_tolerance,
                       area_epsilon=area_epsilon)
    if not report["pass"]:
        raise AssertionError(f"mesh hygiene failed for {path}: {report}")
    return report


def _corner_text(corner: tuple[int, int | None, int | None]) -> str:
    vertex, texcoord, normal = corner
    if normal is not None:
        return f"{vertex + 1}/{texcoord + 1 if texcoord is not None else ''}/{normal + 1}"
    if texcoord is not None:
        return f"{vertex + 1}/{texcoord + 1}"
    return str(vertex + 1)


def write_obj(path: Path, data: Obj) -> None:
    lines = list(data.comments) or ["# Deterministically generated and mesh-hygiene cleaned"]
    if data.mtllib:
        lines.append(f"mtllib {data.mtllib}")
    lines.append(f"o {data.object_name}")
    lines.extend(f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in data.vertices)
    lines.extend("vt " + " ".join(f"{value:.6f}" for value in texcoord) for texcoord in data.texcoords)
    lines.extend(f"vn {x:.6f} {y:.6f} {z:.6f}" for x, y, z in data.normals)
    current_material = None
    current_smoothing = None
    for face in data.faces:
        if face.material != current_material:
            lines.append(f"usemtl {face.material}")
            current_material = face.material
        if face.smoothing != current_smoothing and face.smoothing is not None:
            lines.append(f"s {face.smoothing}")
            current_smoothing = face.smoothing
        lines.append("f " + " ".join(_corner_text(corner) for corner in face.corners))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def clean_obj_file(path: Path, *, merge_distance: float = 0.0001,
                   stack_tolerance: float = 1.0,
                   area_epsilon: float = 1e-10,
                   vertex_remap_out: list[int | None] | None = None,
                   face_remap_out: list[int | None] | None = None) -> dict[str, int | float]:
    original = parse_obj(path)
    cleaned, stats = clean_obj(original, merge_distance=merge_distance,
                               stack_tolerance=stack_tolerance, area_epsilon=area_epsilon,
                               vertex_remap_out=vertex_remap_out,
                               face_remap_out=face_remap_out)
    write_obj(path, cleaned)
    final_audit = audit_obj(parse_obj(path), stack_tolerance=stack_tolerance,
                            area_epsilon=area_epsilon)
    if not final_audit["pass"]:
        raise AssertionError(f"post-clean audit failed for {path}: {final_audit}")
    return stats


def audit_tree(root: Path) -> dict[str, object]:
    assets = {str(path.relative_to(root)): audit_obj(parse_obj(path)) for path in sorted(root.rglob("*.obj"))}
    return {
        "root": str(root),
        "asset_count": len(assets),
        "all_pass": all(record["pass"] for record in assets.values()),
        "assets": assets,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--audit-tree", type=Path)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args(argv)
    if args.audit_tree:
        report = audit_tree(args.audit_tree)
        print(json.dumps(report, indent=2))
        return 0 if report["all_pass"] else 1
    result = {}
    for path in args.paths:
        result[str(path)] = clean_obj_file(path) if args.clean else audit_obj(parse_obj(path))
    print(json.dumps(result, indent=2))
    return 0 if all((record.get("pass", True) for record in result.values())) else 1


if __name__ == "__main__":
    raise SystemExit(main())

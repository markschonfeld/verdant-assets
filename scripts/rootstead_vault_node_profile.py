#!/usr/bin/env python3
"""Extract the Rootstead vault-node profile directly from the committed kit OBJ.

The gable generator and verifier use this module so the installed vault kit—not
prose or manually copied dimensions—remains the geometry authority.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from math import atan2, cos, hypot, pi, sin
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE = ROOT / "reference-kit/rootstead-vault/VD_VaultNode_Far.obj"


@dataclass(frozen=True)
class CentralPiece:
    z_min: float
    z_max: float
    radius: float


@dataclass(frozen=True)
class RadialPiece:
    sector: int
    kind: str
    radial_min: float
    radial_max: float
    tangent_extent: float
    axial_extent: float


@dataclass(frozen=True)
class VaultNodeProfile:
    source_path: Path
    source_sha256: str
    source_triangles: int
    source_components: int
    bounds_min: tuple[float, float, float]
    bounds_max: tuple[float, float, float]
    central: tuple[CentralPiece, ...]
    radial: tuple[RadialPiece, ...]

    @property
    def max_radial_reach(self) -> float:
        return max(hypot(x, y) for x, y in (
            (self.bounds_min[0], self.bounds_min[1]),
            (self.bounds_min[0], self.bounds_max[1]),
            (self.bounds_max[0], self.bounds_min[1]),
            (self.bounds_max[0], self.bounds_max[1]),
        ))

    @property
    def radial_groups(self) -> dict[int, tuple[RadialPiece, ...]]:
        return {
            sector: tuple(sorted((piece for piece in self.radial if piece.sector == sector),
                                 key=lambda piece: piece.radial_max - piece.radial_min,
                                 reverse=True))
            for sector in range(6)
        }


def _parse_obj(path: Path) -> tuple[list[tuple[float, float, float]], list[tuple[int, ...]]]:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if not parts:
            continue
        if parts[0] == "v":
            x, y, z = map(float, parts[1:4])
            vertices.append((x, y, z))
        elif parts[0] == "f":
            face = []
            for token in parts[1:]:
                index = int(token.split("/")[0])
                face.append(index - 1 if index > 0 else len(vertices) + index)
            faces.append(tuple(face))
    return vertices, faces


def _triangulate(faces: list[tuple[int, ...]]) -> list[tuple[int, int, int]]:
    return [(face[0], face[i], face[i + 1]) for face in faces for i in range(1, len(face) - 1)]


def _edge_connected_component_points(
    vertices: list[tuple[float, float, float]], faces: list[tuple[int, ...]],
) -> list[list[tuple[float, float, float]]]:
    """Split by shared welded edges, matching mesh-piece connectivity.

    Shared points alone do not connect pieces: the far node's radial barrels
    touch the centre geometrically but remain separate fitting components.
    """
    coordinate_id: dict[tuple[float, float, float], int] = {}
    welded_vertex_ids: list[int] = []
    for vertex in vertices:
        coordinate_id.setdefault(vertex, len(coordinate_id))
        welded_vertex_ids.append(coordinate_id[vertex])

    welded_faces = [tuple(welded_vertex_ids[index] for index in face) for face in _triangulate(faces)]
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(welded_faces):
        for a, b in zip(face, face[1:] + face[:1]):
            edge_faces[(min(a, b), max(a, b))].append(face_index)

    adjacency: dict[int, set[int]] = defaultdict(set)
    for touching in edge_faces.values():
        for face_index in touching:
            adjacency[face_index].update(other for other in touching if other != face_index)

    seen: set[int] = set()
    component_faces: list[set[int]] = []
    for start in range(len(welded_faces)):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        component: set[int] = set()
        while stack:
            current = stack.pop()
            component.add(current)
            for neighbour in adjacency[current]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        component_faces.append(component)

    id_to_coordinate = {index: coordinate for coordinate, index in coordinate_id.items()}
    return [
        [id_to_coordinate[index] for index in sorted({
            vertex for face_index in component for vertex in welded_faces[face_index]
        })]
        for component in component_faces
    ]


@lru_cache(maxsize=4)
def load_vault_node_profile(path: Path = DEFAULT_REFERENCE) -> VaultNodeProfile:
    path = path.resolve()
    vertices, faces = _parse_obj(path)
    components = _edge_connected_component_points(vertices, faces)

    central_points: list[list[tuple[float, float, float]]] = []
    sector_points: dict[int, list[list[tuple[float, float, float]]]] = defaultdict(list)
    for points in components:
        center_x = sum(point[0] for point in points) / len(points)
        center_y = sum(point[1] for point in points) / len(points)
        if hypot(center_x, center_y) < 5.0:
            central_points.append(points)
        else:
            sector = round(atan2(center_y, center_x) / (pi / 3.0)) % 6
            sector_points[sector].append(points)

    central = tuple(sorted((
        CentralPiece(
            z_min=min(point[2] for point in points),
            z_max=max(point[2] for point in points),
            radius=max(hypot(point[0], point[1]) for point in points),
        )
        for points in central_points
    ), key=lambda piece: piece.z_min))

    radial: list[RadialPiece] = []
    for sector in range(6):
        direction = (cos(sector * pi / 3.0), sin(sector * pi / 3.0))
        tangent = (-direction[1], direction[0])
        measured = []
        for points in sector_points[sector]:
            radial_values = [point[0] * direction[0] + point[1] * direction[1] for point in points]
            tangent_values = [point[0] * tangent[0] + point[1] * tangent[1] for point in points]
            measured.append((
                min(radial_values), max(radial_values),
                max(abs(min(tangent_values)), abs(max(tangent_values))),
                max(abs(point[2]) for point in points),
            ))
        measured.sort(key=lambda item: item[1] - item[0], reverse=True)
        for index, (radial_min, radial_max, tangent_extent, axial_extent) in enumerate(measured):
            radial.append(RadialPiece(
                sector=sector,
                kind="barrel" if index == 0 else "flange",
                radial_min=radial_min,
                radial_max=radial_max,
                tangent_extent=tangent_extent,
                axial_extent=axial_extent,
            ))

    bounds_min = tuple(min(vertex[axis] for vertex in vertices) for axis in range(3))
    bounds_max = tuple(max(vertex[axis] for vertex in vertices) for axis in range(3))
    profile = VaultNodeProfile(
        source_path=path,
        source_sha256=sha256(path.read_bytes()).hexdigest(),
        source_triangles=sum(len(face) - 2 for face in faces),
        source_components=len(components),
        bounds_min=bounds_min,  # type: ignore[arg-type]
        bounds_max=bounds_max,  # type: ignore[arg-type]
        central=central,
        radial=tuple(radial),
    )
    if profile.source_triangles != 672 or profile.source_components != 16:
        raise ValueError(
            f"unexpected vault-node reference profile: {profile.source_triangles} triangles, "
            f"{profile.source_components} edge-connected components"
        )
    if len(profile.central) != 4 or any(len(group) != 2 for group in profile.radial_groups.values()):
        raise ValueError("vault-node reference no longer has four centre pieces and six barrel/flange pairs")
    return profile


def generated_triangles_per_node(sides: int) -> int:
    """Triangles for 16 closed low-sided cylinders derived from the kit pieces."""
    if sides < 3:
        raise ValueError("joint profile needs at least three radial sides")
    triangles_per_component = 4 * sides - 4
    return 16 * triangles_per_component


def generated_profile_bounds(
    profile: VaultNodeProfile, sides: int,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Bounds after mapping reference Z->local X and reference X/Y->local Y/Z."""
    if sides < 3:
        raise ValueError("joint profile needs at least three radial sides")
    points: list[tuple[float, float, float]] = []
    for piece in profile.central:
        for local_x in (piece.z_min, piece.z_max):
            for index in range(sides):
                angle = 2.0 * pi * index / sides
                points.append((local_x, piece.radius * cos(angle), piece.radius * sin(angle)))

    max_sine = max(abs(sin(2.0 * pi * index / sides)) for index in range(sides))
    for piece in profile.radial:
        sector_angle = piece.sector * pi / 3.0
        direction = (cos(sector_angle), sin(sector_angle))
        tangent = (-direction[1], direction[0])
        axial_scale = piece.axial_extent / max_sine
        for radial in (piece.radial_min, piece.radial_max):
            for index in range(sides):
                section_angle = 2.0 * pi * index / sides
                tangent_offset = piece.tangent_extent * cos(section_angle)
                points.append((
                    axial_scale * sin(section_angle),
                    direction[0] * radial + tangent[0] * tangent_offset,
                    direction[1] * radial + tangent[1] * tangent_offset,
                ))
    return (
        tuple(min(point[axis] for point in points) for axis in range(3)),
        tuple(max(point[axis] for point in points) for axis in range(3)),
    )  # type: ignore[return-value]

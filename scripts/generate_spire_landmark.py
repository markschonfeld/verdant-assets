#!/usr/bin/env python3
"""Generate the VERDANT exhaust-stack landmark as Unreal-centimetre OBJ assets.

Outputs are dependency-free Wavefront OBJ files. Geometry is authored 1:1 in cm,
Z-up, with a shared ground-centre assembly origin. Opaque stack/base and translucent
warning emitters remain separate so Nanite can stay enabled on opaque geometry.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from mesh_hygiene import clean_obj_file, parse_obj

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "SourceMesh" / "props"
QA = ROOT / "qa" / "spire_landmark"


@dataclass
class Mesh:
    name: str
    vertices: list[tuple[float, float, float]] = field(default_factory=list)
    faces: list[tuple[str, tuple[int, ...]]] = field(default_factory=list)

    def vertex(self, p: tuple[float, float, float]) -> int:
        self.vertices.append(p)
        return len(self.vertices)

    def face(self, material: str, indices: Iterable[int]) -> None:
        self.faces.append((material, tuple(indices)))

    def add_frustum(
        self,
        z0: float,
        z1: float,
        r0: float,
        r1: float,
        sides: int,
        material: str,
        phase_deg: float = 22.5,
        cap_bottom: bool = True,
        cap_top: bool = True,
    ) -> None:
        phase = math.radians(phase_deg)
        bottom = [
            self.vertex((r0 * math.cos(phase + 2 * math.pi * i / sides),
                         r0 * math.sin(phase + 2 * math.pi * i / sides), z0))
            for i in range(sides)
        ]
        top = [
            self.vertex((r1 * math.cos(phase + 2 * math.pi * i / sides),
                         r1 * math.sin(phase + 2 * math.pi * i / sides), z1))
            for i in range(sides)
        ]
        for i in range(sides):
            j = (i + 1) % sides
            self.face(material, (bottom[i], bottom[j], top[j], top[i]))
        if cap_bottom:
            self.face(material, reversed(bottom))
        if cap_top:
            self.face(material, top)

    def add_box(
        self,
        center: tuple[float, float, float],
        size: tuple[float, float, float],
        yaw_deg: float,
        material: str,
    ) -> None:
        cx, cy, cz = center
        sx, sy, sz = (v / 2 for v in size)
        a = math.radians(yaw_deg)
        ca, sa = math.cos(a), math.sin(a)
        ids = []
        for z in (-sz, sz):
            for y in (-sy, sy):
                for x in (-sx, sx):
                    rx, ry = x * ca - y * sa, x * sa + y * ca
                    ids.append(self.vertex((cx + rx, cy + ry, cz + z)))
        # Per z layer: --, +-, -+, ++
        self.face(material, (ids[0], ids[1], ids[3], ids[2]))
        self.face(material, (ids[4], ids[6], ids[7], ids[5]))
        self.face(material, (ids[0], ids[4], ids[5], ids[1]))
        self.face(material, (ids[2], ids[3], ids[7], ids[6]))
        self.face(material, (ids[0], ids[2], ids[6], ids[4]))
        self.face(material, (ids[1], ids[5], ids[7], ids[3]))

    def add_cylinder_between(
        self,
        start: tuple[float, float, float],
        end: tuple[float, float, float],
        radius: float,
        sides: int,
        material: str,
    ) -> None:
        sx, sy, sz = start
        ex, ey, ez = end
        dx, dy, dz = ex - sx, ey - sy, ez - sz
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        w = (dx / length, dy / length, dz / length)
        seed = (0.0, 0.0, 1.0) if abs(w[2]) < 0.9 else (1.0, 0.0, 0.0)
        ux = seed[1] * w[2] - seed[2] * w[1]
        uy = seed[2] * w[0] - seed[0] * w[2]
        uz = seed[0] * w[1] - seed[1] * w[0]
        ul = math.sqrt(ux * ux + uy * uy + uz * uz)
        u = (ux / ul, uy / ul, uz / ul)
        v = (w[1] * u[2] - w[2] * u[1],
             w[2] * u[0] - w[0] * u[2],
             w[0] * u[1] - w[1] * u[0])
        rings = []
        for ox, oy, oz in (start, end):
            ring = []
            for i in range(sides):
                a = 2 * math.pi * i / sides
                p = (ox + radius * (u[0] * math.cos(a) + v[0] * math.sin(a)),
                     oy + radius * (u[1] * math.cos(a) + v[1] * math.sin(a)),
                     oz + radius * (u[2] * math.cos(a) + v[2] * math.sin(a)))
                ring.append(self.vertex(p))
            rings.append(ring)
        for i in range(sides):
            j = (i + 1) % sides
            self.face(material, (rings[0][i], rings[0][j], rings[1][j], rings[1][i]))
        self.face(material, reversed(rings[0]))
        self.face(material, rings[1])

    def add_radial_fin(
        self,
        yaw_deg: float,
        z0: float,
        z1: float,
        root_r0: float,
        root_r1: float,
        outer_r: float,
        thickness: float,
        material: str,
    ) -> None:
        """Add an extruded four-point radial fin, with a swept atomic-age profile."""
        profile = [
            (root_r0, z0),
            (outer_r, z0 + 0.34 * (z1 - z0)),
            (outer_r * 0.82, z0 + 0.80 * (z1 - z0)),
            (root_r1, z1),
        ]
        a = math.radians(yaw_deg)
        radial = (math.cos(a), math.sin(a))
        tangent = (-math.sin(a), math.cos(a))
        sides = []
        for t in (-thickness / 2, thickness / 2):
            side = []
            for r, z in profile:
                side.append(self.vertex((radial[0] * r + tangent[0] * t,
                                         radial[1] * r + tangent[1] * t, z)))
            sides.append(side)
        self.face(material, reversed(sides[0]))
        self.face(material, sides[1])
        for i in range(len(profile)):
            j = (i + 1) % len(profile)
            self.face(material, (sides[0][i], sides[0][j], sides[1][j], sides[1][i]))

    def face_uvs(self, face: tuple[int, ...], centimetres_per_uv: float = 100.0) -> list[tuple[float, float]]:
        """Return a stable planar UV0 projection for one polygon.

        OBJ permits a separate texture-coordinate index per face corner.  Using
        the polygon's dominant normal axis keeps every generated solid textured
        at a consistent one-UV-unit-per-metre density without forcing unrelated
        hard-surface faces to share UV seams.
        """
        points = [self.vertices[index - 1] for index in face]
        nx = ny = nz = 0.0
        for point, following in zip(points, points[1:] + points[:1]):
            nx += (point[1] - following[1]) * (point[2] + following[2])
            ny += (point[2] - following[2]) * (point[0] + following[0])
            nz += (point[0] - following[0]) * (point[1] + following[1])
        dominant = max(range(3), key=lambda axis: abs((nx, ny, nz)[axis]))
        if dominant == 0:  # YZ projection
            return [(point[1] / centimetres_per_uv, point[2] / centimetres_per_uv)
                    for point in points]
        if dominant == 1:  # XZ projection
            return [(point[0] / centimetres_per_uv, point[2] / centimetres_per_uv)
                    for point in points]
        return [(point[0] / centimetres_per_uv, point[1] / centimetres_per_uv)
                for point in points]

    def write_obj(self, path: Path, mtl_name: str) -> None:
        lines = [f"# Generated by scripts/generate_spire_landmark.py", f"mtllib {mtl_name}",
                 f"o {self.name}"]
        lines.extend(f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in self.vertices)
        face_uv_indices: list[tuple[int, ...]] = []
        next_uv_index = 1
        for _, face in self.faces:
            uvs = self.face_uvs(face)
            lines.extend(f"vt {u:.6f} {v:.6f}" for u, v in uvs)
            face_uv_indices.append(tuple(range(next_uv_index, next_uv_index + len(uvs))))
            next_uv_index += len(uvs)
        current = None
        for (material, face), uv_indices in zip(self.faces, face_uv_indices):
            if material != current:
                lines.extend((f"usemtl {material}", "s 1"))
                current = material
            lines.append("f " + " ".join(
                f"{vertex_index}/{uv_index}"
                for vertex_index, uv_index in zip(face, uv_indices)
            ))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def add_platform(mesh: Mesh, z: float, radius: float, body_radius: float, detailed: bool) -> None:
    """Add a closed maintenance deck with human-scale rail geometry."""
    mesh.add_frustum(z, z + 28, radius, radius, 16, "M_Spire_BareMetal")
    post_count = 16 if detailed else 8
    for i in range(post_count):
        a = 2 * math.pi * i / post_count
        p = (radius * math.cos(a), radius * math.sin(a))
        mesh.add_cylinder_between((p[0], p[1], z + 28), (p[0], p[1], z + 138),
                                  5, 8, "M_Spire_Fastener")
    # Continuous top rail remains real geometry even on far-band platforms.
    for i in range(post_count):
        a0 = 2 * math.pi * i / post_count
        a1 = 2 * math.pi * (i + 1) / post_count
        mesh.add_cylinder_between(
            (radius * math.cos(a0), radius * math.sin(a0), z + 138),
            (radius * math.cos(a1), radius * math.sin(a1), z + 138),
            5,
            8,
            "M_Spire_Fastener",
        )
    # Four radial bearers make the deck read as supported, not floating.
    for yaw in (0, 90, 180, 270):
        a = math.radians(yaw)
        mesh.add_cylinder_between(
            (body_radius * math.cos(a), body_radius * math.sin(a), z - 80),
            ((radius - 35) * math.cos(a), (radius - 35) * math.sin(a), z + 4),
            9 if detailed else 7,
            8,
            "M_Spire_BareMetal",
        )


def add_lower_ladder(mesh: Mesh) -> None:
    """Add a fixed-width ladder that follows the lower stack taper."""
    y0, y1 = -32, 32
    z0, z1, step = 1200, 4000, 35

    def x_at(z: float) -> float:
        # Lower shell radius is 800 -> 650 cm over the first 40 m.
        shell_r = 800 - 150 * (z / 4000)
        return shell_r + 55

    levels = list(range(z0, z1, step)) + [z1]
    for a, b in zip(levels, levels[1:]):
        for y in (y0, y1):
            mesh.add_cylinder_between((x_at(a), y, a), (x_at(b), y, b),
                                      4, 8, "M_Spire_Fastener")
    for z in levels[1:-1]:
        mesh.add_cylinder_between((x_at(z), y0, z), (x_at(z), y1, z),
                                  3, 8, "M_Spire_Fastener")
    for z in range(z0 + 140, z1, 140):
        shell_r = x_at(z) - 55
        mesh.add_cylinder_between((shell_r, 0, z), (x_at(z), 0, z),
                                  4, 8, "M_Spire_BareMetal")


def build_base() -> Mesh:
    m = Mesh("VD_SpireBase")
    # 24 m across cardinal flats, 12 m high. This is an authored process/service
    # enclosure rather than a scaled copy of the placeholder's 60 m cylinder.
    outer_r = 1200 / math.cos(math.pi / 8)
    m.add_frustum(0, 120, outer_r, outer_r, 8, "M_Spire_Concrete")
    m.add_frustum(120, 240, outer_r, 1120, 8, "M_Spire_BareMetal")
    m.add_frustum(240, 1050, 950, 900, 8, "M_Spire_PaintedSteel")
    m.add_frustum(1050, 1200, 1000, 850, 8, "M_Spire_BareMetal")

    # Four full-height access/plant doors with correctly human-scale fasteners.
    for yaw in (0, 90, 180, 270):
        a = math.radians(yaw)
        radial = (math.cos(a), math.sin(a))
        tangent = (-math.sin(a), math.cos(a))
        face_r = 900
        m.add_box((face_r * radial[0], face_r * radial[1], 485),
                  (24, 180, 250), yaw, "M_Spire_ServicePanel")
        for offset in (-72, -24, 24, 72):
            for z in (380, 590):
                start = ((face_r + 13) * radial[0] + offset * tangent[0],
                         (face_r + 13) * radial[1] + offset * tangent[1], z)
                end = ((face_r + 20) * radial[0] + offset * tangent[0],
                       (face_r + 20) * radial[1] + offset * tangent[1], z)
                m.add_cylinder_between(start, end, 4, 8, "M_Spire_Fastener")

    # Two 3 m process ducts and flange collars establish exhaust function at ground level.
    for yaw in (45, 225):
        a = math.radians(yaw)
        radial = (math.cos(a), math.sin(a))
        m.add_cylinder_between((760 * radial[0], 760 * radial[1], 720),
                               (1200 * radial[0], 1200 * radial[1], 720),
                               150, 16, "M_Spire_BareMetal")
        m.add_cylinder_between((1160 * radial[0], 1160 * radial[1], 720),
                               (1220 * radial[0], 1220 * radial[1], 720),
                               175, 16, "M_Spire_Fastener")
    return m


def build_spire() -> Mesh:
    m = Mesh("VD_Spire")
    # 180 m working exhaust stack. Closed staged shells overlap at collars so each
    # generated component remains manifold while the silhouette tapers materially.
    sections = (
        (0, 4000, 800, 650),
        (4000, 9000, 650, 500),
        (9000, 14000, 500, 390),
        (14000, 17400, 390, 300),
        (17400, 17920, 300, 280),
    )
    for z0, z1, r0, r1 in sections:
        m.add_frustum(z0, z1, r0, r1, 16, "M_Spire_StackConcrete")

    # Dark recessed exhaust mouth and heavy rim make chimney function unambiguous.
    m.add_frustum(17920, 18000, 330, 330, 16, "M_Spire_BareMetal")
    m.add_frustum(17996, 18000, 270, 270, 16, "M_Spire_Soot")

    # Lower 40 m: dense human-scale access, instrumentation, and settlement repair.
    add_lower_ladder(m)
    for yaw, z in ((0, 1550), (90, 2350), (180, 3150), (270, 3950)):
        a = math.radians(yaw)
        radial = (math.cos(a), math.sin(a))
        body_r = 745 - z * 0.025
        m.add_cylinder_between((body_r * radial[0], body_r * radial[1], z),
                               (1030 * radial[0], 1030 * radial[1], z),
                               15, 10, "M_Spire_BareMetal")
        m.add_cylinder_between((body_r * radial[0], body_r * radial[1], z - 85),
                               (1010 * radial[0], 1010 * radial[1], z - 8),
                               9, 8, "M_Spire_BareMetal")
        m.add_cylinder_between((1030 * radial[0], 1030 * radial[1], z),
                               (1100 * radial[0], 1100 * radial[1], z),
                               50, 12, "M_Spire_ServicePanel")

    # Maintenance platforms are detailed below 40 m and simplified in the far band.
    for z, radius, body_radius, detailed in (
        (1800, 980, 730, True),
        (3600, 920, 665, True),
        (8200, 740, 525, False),
        (12600, 620, 420, False),
        (16600, 500, 320, False),
    ):
        add_platform(m, z, radius, body_radius, detailed)

    # Structural collars mark staged construction without scaling bolt size upward.
    for z, radius in ((3950, 690), (8950, 540), (13950, 430), (17350, 340)):
        m.add_frustum(z, z + 55, radius, radius, 16, "M_Spire_BareMetal")
        for i in range(12):
            a = 2 * math.pi * i / 12
            m.add_cylinder_between(((radius - 4) * math.cos(a), (radius - 4) * math.sin(a), z + 27),
                                   ((radius + 12) * math.cos(a), (radius + 12) * math.sin(a), z + 27),
                                   4, 8, "M_Spire_Fastener")

    # A later settlement signal yard and braces reuse the industrial stack at 90 m.
    m.add_cylinder_between((-900, 0, 9000), (900, 0, 9000), 12, 12, "M_Spire_BareMetal")
    m.add_cylinder_between((-620, 0, 8800), (-860, 0, 9000), 8, 8, "M_Spire_BareMetal")
    m.add_cylinder_between((620, 0, 8800), (860, 0, 9000), 8, 8, "M_Spire_BareMetal")
    for x in (-875, 875):
        m.add_box((x, 0, 8980), (42, 28, 72), 0, "M_Spire_ServicePanel")
    return m


def build_warning_lights() -> Mesh:
    m = Mesh("VD_SpireLights")
    # Separate translucent/emissive asset: shared ground-centre assembly origin.
    for z, body_r in ((6000, 590), (12000, 435), (17750, 290)):
        for yaw in (0, 90, 180, 270):
            a = math.radians(yaw)
            radial = (math.cos(a), math.sin(a))
            r = body_r + 45
            m.add_cylinder_between((r * radial[0], r * radial[1], z - 20),
                                   (r * radial[0], r * radial[1], z + 20),
                                   25, 12, "M_Spire_WarningLens")
    return m


def write_mtl(path: Path) -> None:
    materials = {
        "M_Spire_Concrete": (0.19, 0.18, 0.16, 0.0, 0.86),
        "M_Spire_StackConcrete": (0.34, 0.32, 0.27, 0.0, 0.78),
        "M_Spire_PaintedSteel": (0.16, 0.24, 0.23, 0.75, 0.42),
        "M_Spire_BareMetal": (0.31, 0.34, 0.34, 0.95, 0.32),
        "M_Spire_ServicePanel": (0.35, 0.18, 0.08, 0.8, 0.48),
        "M_Spire_Fastener": (0.16, 0.17, 0.17, 1.0, 0.26),
        "M_Spire_Soot": (0.025, 0.025, 0.022, 0.0, 0.96),
        "M_Spire_WarningLens": (0.72, 0.025, 0.018, 0.0, 0.18),
    }
    lines = ["# Unreal material-slot placeholders; PBR values documented as comments."]
    for name, (r, g, b, metallic, roughness) in materials.items():
        lines.extend((f"newmtl {name}", f"Kd {r:.3f} {g:.3f} {b:.3f}",
                      f"# metallic {metallic:.2f}", f"# roughness {roughness:.2f}", ""))
    path.write_text("\n".join(lines), encoding="utf-8")


def mesh_record(path: Path, hygiene: dict[str, int | float]) -> dict[str, object]:
    mesh = parse_obj(path)
    xs = [v[0] for v in mesh.vertices]
    ys = [v[1] for v in mesh.vertices]
    zs = [v[2] for v in mesh.vertices]
    return {
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "triangles_after_import": sum(len(face.corners) - 2 for face in mesh.faces),
        "bounds_cm": {
            "min": [round(min(xs), 3), round(min(ys), 3), round(min(zs), 3)],
            "max": [round(max(xs), 3), round(max(ys), 3), round(max(zs), 3)],
            "size": [round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3),
                     round(max(zs) - min(zs), 3)],
        },
        "materials": sorted({face.material for face in mesh.faces}),
        "mesh_hygiene": hygiene,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    mtl = OUT / "VD_Spire_Landmark.mtl"
    write_mtl(mtl)
    meshes = [build_base(), build_spire(), build_warning_lights()]
    hygiene = {}
    for mesh in meshes:
        path = OUT / f"{mesh.name}.obj"
        mesh.write_obj(path, mtl.name)
        hygiene[mesh.name] = clean_obj_file(path)
    report = {
        "units": "centimetres (1 unit = 1 Unreal uu = 1 cm)",
        "axis": "Z-up",
        "pivot": "shared ground-centre assembly origin",
        "assembly_height_cm": 18000,
        "canonical_function": "research exhaust stack later adapted as signal/observation mast",
        "meshes": {mesh.name: mesh_record(OUT / f"{mesh.name}.obj", hygiene[mesh.name]) for mesh in meshes},
    }
    (QA / "spire_landmark_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

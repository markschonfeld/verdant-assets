#!/usr/bin/env python3
"""Generate the VERDANT atomic-age landmark spire as Unreal-centimetre OBJ assets.

Outputs are dependency-free Wavefront OBJ files. Geometry is authored 1:1 in cm,
Z-up, with each pivot at bottom centre. The spire and base remain separate so the
base can receive simple collision while the inaccessible mast can use NoCollision.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

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

    def write_obj(self, path: Path, mtl_name: str) -> None:
        lines = [f"# Generated by scripts/generate_spire_landmark.py", f"mtllib {mtl_name}",
                 f"o {self.name}"]
        lines.extend(f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in self.vertices)
        current = None
        for material, face in self.faces:
            if material != current:
                lines.extend((f"g {self.name}_{material}", f"usemtl {material}", "s 1"))
                current = material
            lines.append("f " + " ".join(map(str, face)))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_base() -> Mesh:
    m = Mesh("VD_SpireBase")
    # 3.6 m across the cardinal flats, 1.1 m high. For the 22.5-degree phase,
    # circumradius must account for the octagon apothem rather than equal 180 cm.
    outer_r = 180 / math.cos(math.pi / 8)
    m.add_frustum(0, 24, outer_r, outer_r, 8, "M_Spire_Concrete")
    m.add_frustum(24, 38, outer_r, 158, 8, "M_Spire_BareMetal")
    m.add_frustum(38, 82, 158, 145, 8, "M_Spire_PaintedSteel")
    m.add_frustum(82, 110, 145, 118, 8, "M_Spire_BareMetal")

    # Four raised service plates, oriented to cardinal faces.
    for yaw in (0, 90, 180, 270):
        a = math.radians(yaw)
        r = 150
        m.add_box((r * math.cos(a), r * math.sin(a), 61), (4, 72, 34), yaw,
                  "M_Spire_ServicePanel")
        # Six real fasteners per plate; cylinders point radially out.
        for tangent_offset in (-25, 0, 25):
            for z in (49, 73):
                tx, ty = -math.sin(a), math.cos(a)
                start = (151 * math.cos(a) + tangent_offset * tx,
                         151 * math.sin(a) + tangent_offset * ty, z)
                end = (156 * math.cos(a) + tangent_offset * tx,
                       156 * math.sin(a) + tangent_offset * ty, z)
                m.add_cylinder_between(start, end, 2.4, 8, "M_Spire_Fastener")
    return m


def build_spire() -> Mesh:
    m = Mesh("VD_Spire")
    # 12.0 m faceted research mast. Assembly height with base is 13.1 m.
    m.add_frustum(0, 250, 80, 68, 12, "M_Spire_PaintedSteel")
    m.add_frustum(250, 650, 68, 50, 12, "M_Spire_PaintedSteel")
    m.add_frustum(650, 1050, 50, 24, 12, "M_Spire_PaintedSteel")

    # Short lower buttresses keep the base planted without creating a rocket silhouette.
    for yaw in (0, 90, 180, 270):
        m.add_radial_fin(yaw, 90, 410, 76, 60, 115, 10, "M_Spire_Fin")

    # Staggered environmental-instrument arms make the function legible and break
    # axial symmetry. Each pod remains opaque; future lights/lenses must be separate.
    for yaw, z in ((0, 430), (90, 610), (180, 790), (270, 970)):
        a = math.radians(yaw)
        radial = (math.cos(a), math.sin(a))
        arm_start = (42 * radial[0], 42 * radial[1], z)
        arm_end = (150 * radial[0], 150 * radial[1], z)
        brace_start = (38 * radial[0], 38 * radial[1], z - 62)
        brace_end = (142 * radial[0], 142 * radial[1], z - 4)
        m.add_cylinder_between(arm_start, arm_end, 6, 10, "M_Spire_BareMetal")
        m.add_cylinder_between(brace_start, brace_end, 4, 8, "M_Spire_BareMetal")
        m.add_cylinder_between(
            (145 * radial[0], 145 * radial[1], z),
            (180 * radial[0], 180 * radial[1], z),
            18,
            10,
            "M_Spire_ServicePanel",
        )

    # Structural collars and visible bolted seams.
    for z, radius in ((220, 105), (590, 90), (920, 65)):
        m.add_frustum(z, z + 18, radius, radius, 16, "M_Spire_BareMetal")
        for i in range(8):
            a = 2 * math.pi * i / 8
            start = ((radius - 1) * math.cos(a), (radius - 1) * math.sin(a), z + 9)
            end = ((radius + 5) * math.cos(a), (radius + 5) * math.sin(a), z + 9)
            m.add_cylinder_between(start, end, 2.2, 8, "M_Spire_Fastener")

    # Flat service cap, antenna rod, and cross-vane avoid a missile-like cone.
    m.add_frustum(1050, 1080, 30, 24, 12, "M_Spire_BareMetal")
    m.add_frustum(1080, 1200, 5, 3, 8, "M_Spire_Fastener")
    m.add_cylinder_between((-75, 0, 1160), (75, 0, 1160), 4, 8, "M_Spire_BareMetal")
    m.add_box((69, 0, 1160), (28, 8, 32), 0, "M_Spire_ServicePanel")
    return m


def write_mtl(path: Path) -> None:
    materials = {
        "M_Spire_Concrete": (0.19, 0.18, 0.16, 0.0, 0.86),
        "M_Spire_PaintedSteel": (0.16, 0.24, 0.23, 0.75, 0.42),
        "M_Spire_BareMetal": (0.31, 0.34, 0.34, 0.95, 0.32),
        "M_Spire_ServicePanel": (0.35, 0.18, 0.08, 0.8, 0.48),
        "M_Spire_Fin": (0.19, 0.28, 0.26, 0.8, 0.40),
        "M_Spire_Fastener": (0.16, 0.17, 0.17, 1.0, 0.26),
    }
    lines = ["# Unreal material-slot placeholders; PBR values documented as comments."]
    for name, (r, g, b, metallic, roughness) in materials.items():
        lines.extend((f"newmtl {name}", f"Kd {r:.3f} {g:.3f} {b:.3f}",
                      f"# metallic {metallic:.2f}", f"# roughness {roughness:.2f}", ""))
    path.write_text("\n".join(lines), encoding="utf-8")


def mesh_record(mesh: Mesh) -> dict[str, object]:
    xs = [v[0] for v in mesh.vertices]
    ys = [v[1] for v in mesh.vertices]
    zs = [v[2] for v in mesh.vertices]
    return {
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "triangles_after_import": sum(max(1, len(face) - 2) for _, face in mesh.faces),
        "bounds_cm": {
            "min": [round(min(xs), 3), round(min(ys), 3), round(min(zs), 3)],
            "max": [round(max(xs), 3), round(max(ys), 3), round(max(zs), 3)],
            "size": [round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3),
                     round(max(zs) - min(zs), 3)],
        },
        "materials": sorted({material for material, _ in mesh.faces}),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    mtl = OUT / "VD_Spire_Landmark.mtl"
    write_mtl(mtl)
    meshes = [build_base(), build_spire()]
    for mesh in meshes:
        mesh.write_obj(OUT / f"{mesh.name}.obj", mtl.name)
    report = {
        "units": "centimetres (1 unit = 1 Unreal uu = 1 cm)",
        "axis": "Z-up",
        "pivot": "bottom centre for each mesh",
        "assembly_height_cm": 1310,
        "meshes": {mesh.name: mesh_record(mesh) for mesh in meshes},
    }
    (QA / "spire_landmark_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

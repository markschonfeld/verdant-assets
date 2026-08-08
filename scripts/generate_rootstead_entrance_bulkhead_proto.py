#!/usr/bin/env python3
"""Generate the Rootstead entrance-bulkhead TRIANGLE-BUDGET PROTOTYPE.

Authors ONE representative held precast module at true scale (see
`scripts/rootstead_entrance_bulkhead_proto_spec.py` for the shared numeric
contract and the period rationale) and reports its per-category triangle cost so
the full-wall detail count can be projected BEFORE anyone models the whole wall.

Outputs (all deterministic; no randomness, no timestamps):
  SourceMesh/architecture/VD_RootsteadEntranceBulkhead_Proto.obj
  SourceMesh/architecture/VD_RootsteadEntranceBulkhead_Proto.mtl
  qa/rootstead_entrance_bulkhead/prototype/..._metrics.json

The OBJ is a single object, no `g` records, semantic `usemtl` slots, a UV index
on every face corner. The module carries every detail the spec calls for:
exposed-aggregate precast face + body, chamfered arrises, a recessed/perished
sealant joint, the board-marked in-situ plinth construction junction, a sparse
corner spall exposing a rebar/fixing lug, and geometry-obedient weather streaks
below joint/fixing origins. No rivets, plate seams, welds, or steel-plate.

The metrics JSON separates FIXED base-massing categories (do not multiply per
module) from REPEATED decorative-detail categories (multiply by module count),
so the scaling risk is visible: the projected full-wall detail count is
dominated by whatever recurs 36 times.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import rootstead_entrance_bulkhead_proto_spec as spec  # noqa: E402
from mesh_hygiene import clean_obj_file, parse_obj  # noqa: E402

OUT = ROOT / "SourceMesh" / "architecture"
QA = ROOT / "qa" / "rootstead_entrance_bulkhead" / "prototype"

Vec3 = tuple[float, float, float]
Vec2 = tuple[float, float]


# ---------------------------------------------------------------------------
# Mesh authoring helpers (same shape/idioms as the PR #18 west-endwall builder).
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

    def quad(self, a: Vec3, b: Vec3, c: Vec3, d: Vec3, material: str) -> None:
        ids = [self.vertex(p) for p in (a, b, c, d)]
        self.face(material, ids)

    def tri(self, a: Vec3, b: Vec3, c: Vec3, material: str) -> None:
        ids = [self.vertex(p) for p in (a, b, c)]
        self.face(material, ids)

    def box(self, minimum: Vec3, maximum: Vec3, material: str) -> None:
        self.box_multi(minimum, maximum, {k: material for k in
                                          ("x0", "x1", "y0", "y1", "z0", "z1")})

    def box_multi(self, minimum: Vec3, maximum: Vec3,
                  face_materials: dict[str, str]) -> None:
        """One connected 8-vertex box; per-face material assignment.

        Face keys: x0/x1 (X-normal), y0/y1 (Y-normal), z0/z1 (Z-normal). One
        shared box so the result stays a single connected, closed component even
        with several `usemtl` slots on it. Winding is outward on every face.
        """
        x0, y0, z0 = minimum
        x1, y1, z1 = maximum
        ids = [self.vertex((x, y, z))
               for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
        faces = {"z0": (0, 1, 3, 2), "z1": (4, 6, 7, 5), "y0": (0, 4, 5, 1),
                 "y1": (2, 3, 7, 6), "x0": (0, 2, 6, 4), "x1": (1, 5, 7, 3)}
        for key, f in faces.items():
            self.face(face_materials[key], tuple(ids[i] for i in f))

    def cylinder(self, start: Vec3, end: Vec3, radius: float, sides: int,
                 material: str) -> None:
        """Closed solid cylinder between two points."""
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
        rings: list[list[int]] = []
        for point in (start, end):
            ring = []
            for i in range(sides):
                angle = 2.0 * math.pi * i / sides
                ring.append(self.vertex((
                    point[0] + radius * (math.cos(angle) * side[0] + math.sin(angle) * up[0]),
                    point[1] + radius * (math.cos(angle) * side[1] + math.sin(angle) * up[1]),
                    point[2] + radius * (math.cos(angle) * side[2] + math.sin(angle) * up[2]),
                )))
            rings.append(ring)
        self.face(material, tuple(reversed(rings[0])))
        self.face(material, tuple(rings[1]))
        for i in range(sides):
            j = (i + 1) % sides
            self.face(material, (rings[0][i], rings[0][j], rings[1][j], rings[1][i]))

    def face_uvs(self, face: tuple[int, ...], scale: float = 100.0) -> list[Vec2]:
        """Planar UVs from the face's dominant-axis projection (metres)."""
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

    def triangle_count(self) -> int:
        return sum(len(f) - 2 for _, f in self.faces)

    def category_triangles(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for material, face in self.faces:
            counts[material] = counts.get(material, 0) + (len(face) - 2)
        return counts

    def write(self) -> Path:
        lines = [f"# Generated by {Path(__file__).name} -- do not hand-edit",
                 f"mtllib {self.mtl_name}", f"o {self.name}"]
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
        path = OUT / f"{self.name}.obj"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path


def write_mtl(name: str, materials: dict[str, tuple[Vec3, float, float]]) -> Path:
    lines = [f"# Semantic preview materials for {name}"]
    for material, (color, roughness, opacity) in materials.items():
        lines.extend((f"newmtl {material}",
                      f"Kd {color[0]:.3f} {color[1]:.3f} {color[2]:.3f}",
                      f"Pr {roughness:.3f}", f"d {opacity:.3f}", "illum 2", ""))
    path = OUT / f"{name}.mtl"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_preview(metrics: dict) -> Path:
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (1600, 900), (238, 236, 229))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=22)
    small = ImageFont.load_default(size=17)
    draw.text((45, 28), "ROOTSTEAD ENTRANCE BULKHEAD - TRIANGLE-BUDGET PROTOTYPE", fill=(28,32,30), font=font)
    draw.text((45, 62), "Candidate only | one true-scale west-face module | STOP before replication", fill=(132,45,38), font=small)
    # Orthographic west/front view.
    ox, oy, sw, sh = 80, 135, 430, 620
    draw.rectangle((ox, oy, ox+sw, oy+sh), fill=spec.PREVIEW_COLORS[spec.MAT_BASE_MASSING], outline=(30,30,30), width=3)
    ph = int(sh * spec.PLINTH_H / (spec.PLINTH_H + spec.MODULE_H))
    draw.rectangle((ox, oy+sh-ph, ox+sw, oy+sh), fill=spec.PREVIEW_COLORS[spec.MAT_BOARD_PLINTH], outline=(50,50,50), width=2)
    for i in range(1, spec.PLINTH_BOARD_COUNT):
        yy=oy+sh-ph+i*ph/spec.PLINTH_BOARD_COUNT; draw.line((ox,yy,ox+sw,yy), fill=(100,92,78), width=2)
    pad=(ox+28,oy+26,ox+sw-28,oy+sh-ph-25)
    draw.rectangle(pad, fill=spec.PREVIEW_COLORS[spec.MAT_PRECAST], outline=spec.PREVIEW_COLORS[spec.MAT_CHAMFER], width=10)
    # Same deterministic aggregate positions, visually varied and non-grid.
    dots=[(.12,.18,7),(.31,.11,10),(.56,.20,6),(.81,.13,12),(.21,.39,8),(.47,.34,11),(.73,.43,7),(.91,.34,9),(.08,.62,10),(.37,.58,6),(.63,.67,9),(.84,.60,11),(.26,.83,7),(.69,.86,10)]
    for u,v,r in dots:
        x=pad[0]+18+u*(pad[2]-pad[0]-36); y=pad[1]+18+v*(pad[3]-pad[1]-36)
        draw.regular_polygon((x,y,r), 5+(int(u*100)%3), fill=spec.PREVIEW_COLORS[spec.MAT_AGGREGATE])
    draw.text((ox,oy-30), "ORTHOGRAPHIC WEST / FRONT", fill=(35,35,35), font=small)
    draw.text((ox,oy+sh+14), "146 uu bay x 225 uu course; 150 uu plinth", fill=(35,35,35), font=small)
    # Simple isometric/side depth cue.
    ax, ay = 610, 190
    front=[(ax,ay),(ax+300,ay+70),(ax+300,ay+440),(ax,ay+370)]
    side=[front[1],(front[1][0]+150,front[1][1]-85),(front[2][0]+150,front[2][1]-85),front[2]]
    draw.polygon(side, fill=(126,122,113), outline=(30,30,30)); draw.polygon(front, fill=(190,181,160), outline=(30,30,30))
    draw.text((ax,ay-45), "ISOMETRIC / SIDE", fill=(35,35,35), font=small)
    draw.text((ax,ay+470), "Visible west plane world x = -461 uu\nRelief projects toward -X; local Z + 3500 = world Z", fill=(35,35,35), font=small, spacing=8)
    # Legend and counts.
    lx, ly = 1120, 120
    draw.text((lx,ly), "SEMANTIC LEGEND", fill=(30,30,30), font=font); ly += 45
    for mat in sorted(metrics["triangle_counts_by_category"]):
        draw.rectangle((lx,ly,lx+22,ly+22), fill=spec.PREVIEW_COLORS[mat], outline=(30,30,30))
        label=mat.replace("M_EntranceBulkhead_","")
        draw.text((lx+32,ly), f"{label}: {metrics['triangle_counts_by_category'][mat]} tri", fill=(35,35,35), font=small); ly+=32
    ly += 15
    draw.text((lx,ly), f"PROTOTYPE TOTAL  {metrics['total_prototype_triangles']} tri", fill=(20,20,20), font=font); ly+=40
    proj=metrics["projection"]["projected_full_wall"]
    draw.text((lx,ly), f"Fixed/base: {proj['fixed_base_massing']['base_massing_triangles']}\nRepeated detail: {proj['repeated_decorative_detail']['detail_triangles']}\nProjection total: {proj['total_projected_triangles']}", fill=(35,35,35), font=small, spacing=8)
    path=QA / "rootstead_entrance_bulkhead_proto_preview.png"
    image.save(path, optimize=True)
    return path


def write_report(metrics: dict) -> Path:
    proj=metrics["projection"]["projected_full_wall"]
    text=f"""# Rootstead entrance bulkhead prototype gate

**Candidate decision:** HOLD. The 146 × 225 uu west-face module and 191 × 225 uu return module are viable candidates, but aggregate/detail replication is not authorized until art/tech review accepts this measured projection.

- Measured prototype: **{metrics['total_prototype_triangles']} triangles**, including **{metrics['aggregate_geometry']['count']}** closed proud aggregate stones ({metrics['triangle_counts_by_category'][spec.MAT_AGGREGATE]} triangles).
- Projection: {metrics['projection']['module_layout']['module_count_full_wall']} repeated module instances; {metrics['projection']['module_layout']['spall_modules_full_wall']} sparse-spall instances; {proj['fixed_base_massing']['base_massing_triangles']} fixed structural/base triangles + {proj['repeated_decorative_detail']['detail_triangles']} repeated-detail triangles = **{proj['total_projected_triangles']} triangles**.
- Placement/bounds: transform `(0, 0, 3500)`; parsed local bounds are recorded in metrics. The visible west face is world `x=-461`, not the defective `x=-300` void edge.
- Surfaces: both west wing faces, outer returns at `y=±1300`, and doorway returns at `y=±424`; east `x=112` abuts WEND_Entry and is undecorated.
- Collision: render prototype only. Integration must use hand-authored segmented boxes; no primitive may cross `x=-509..112, y=±424, z=3500..3892`. No generated hull or convex decomposition.
- Limitations: no full wall is authored; material/shader fidelity, LODs, Unreal import, lightmap UVs, and face-volume clearance tests belong to the production asset gate.

Commands: `python3 scripts/generate_rootstead_entrance_bulkhead_proto.py`; `python3 scripts/verify_rootstead_entrance_bulkhead_proto.py`.

## STOP before scaling

Do not replicate aggregate, streak, sealant, spall, or module geometry across the full wall until this candidate count and visual density are explicitly accepted.
"""
    path=QA / "rootstead_entrance_bulkhead_proto_report.md"; path.write_text(text,encoding="utf-8"); return path


# ---------------------------------------------------------------------------
# Local-Z helper: authored geometry is base-centred (local z 0 == world 3500).
# X and Y stay world-aligned (local == world).
# ---------------------------------------------------------------------------
def lz(world_z_value: float) -> float:
    return spec.local_z(world_z_value)


# ---------------------------------------------------------------------------
# Build the one representative module.
# ---------------------------------------------------------------------------

def build() -> Mesh:
    """Author the module entirely from CLOSED SOLIDS (boxes, a chamfered
    frustum, a closed spall chip, a cylinder). Every primitive is watertight in
    isolation, so the assembled mesh is fully manifold (every edge shared by
    exactly two faces) even where primitives interpenetrate -- the same property
    the PR #18 west-endwall asset certifies. Interpenetration is fine for a
    render+box-collision asset and keeps the detail honest to author."""
    mesh = Mesh(spec.OBJ_NAME, f"{spec.OBJ_NAME}.mtl")

    y0, y1 = spec.CELL_Y                 # world y 424..570
    face_x = spec.FACE_X                 # -300 proud face plane
    recess_x = face_x + spec.JOINT_RECESS_DEPTH  # -288 recessed reveal/joint floor
    back_x = spec.BACKING_X              # -230 base-massing back plane
    ch = spec.CHAMFER
    half_j = spec.JOINT_WIDTH / 2.0      # this module owns a half-joint per side

    plinth_top = spec.PLINTH_H           # local z 150
    mod_bot = plinth_top                 # precast course starts at top of plinth
    mod_top = plinth_top + spec.MODULE_H  # local z 375

    # --- 1. FIXED BASE MASSING: solid backing (proves "solid, no void"). -------
    # Two stacked closed boxes spanning the recessed plane back to the sample
    # back plane. The plinth-region box is all base massing; the field-region
    # box exposes its front (recessed) face as the joint-reveal plane, so the
    # perimeter recess around the pad reads as the recessed joint. The full-wall
    # solid is NOT modelled here -- it is projected separately as hand-placed
    # segmented box primitives (collision rule: none crossing the doorway).
    mesh.box((recess_x, y0, 0.0), (back_x, y1, mod_bot), spec.MAT_BASE_MASSING)
    mesh.box_multi((recess_x, y0, mod_bot), (back_x, y1, mod_top), {
        "x0": spec.MAT_JOINT,  # recessed reveal floor the joint reads against
        "x1": spec.MAT_BASE_MASSING, "y0": spec.MAT_BASE_MASSING,
        "y1": spec.MAT_BASE_MASSING, "z0": spec.MAT_BASE_MASSING,
        "z1": spec.MAT_BASE_MASSING,
    })

    # --- 2. FIXED BASE MASSING: board-marked in-situ plinth + junction. --------
    # Distinct pour from the precast above. Board-form impressions run
    # horizontally: each board is a proud closed box; the thin gaps between them
    # expose the base massing behind = recessed board-form grooves (real relief,
    # not a texture change). The material change at z=plinth_top is the
    # construction junction where the in-situ plinth meets the precast field.
    board_pitch = plinth_top / spec.PLINTH_BOARD_COUNT
    groove = 3.0  # recessed groove between boards
    for b in range(spec.PLINTH_BOARD_COUNT):
        bz0 = b * board_pitch + (groove if b else 0.0)
        bz1 = (b + 1) * board_pitch - groove
        mesh.box((face_x, y0, bz0), (recess_x, y1, bz1), spec.MAT_BOARD_PLINTH)

    # Pad footprint (this module's half-joint reveal is the perimeter gap).
    pad_y0 = y0 + half_j
    pad_y1 = y1 - half_j
    pad_z0 = mod_bot + half_j
    pad_z1 = mod_top - half_j

    # --- 3-5. REPEATED DETAIL: exposed-aggregate precast pad, chamfered arris. --
    _build_pad(mesh, pad_y0, pad_y1, pad_z0, pad_z1, face_x, recess_x, ch)

    # Proud coarse aggregate is deliberately real geometry in this gate: its
    # measured cost is the scaling-risk signal, not hidden in a shader claim.
    _build_aggregate(mesh, pad_y0, pad_y1, pad_z0, pad_z1, face_x)

    # --- 6. REPEATED DETAIL: recessed / perished sealant bead in the joint. ----
    _build_sealant(mesh, y0, pad_y0, pad_y1, mod_bot, pad_z1, recess_x)

    # --- 7. REPEATED (SPARSE) DETAIL: corner spall exposing a rebar lug. -------
    _build_spall(mesh, pad_y0, pad_z0, face_x)

    # --- 8. REPEATED DETAIL: geometry-obedient weather streaks. ----------------
    _build_streaks(mesh, pad_y0, pad_y1, pad_z0, pad_z1, face_x)

    return mesh


def _build_aggregate(mesh: Mesh, y0: float, y1: float, z0: float, z1: float,
                     face_x: float) -> None:
    """Restrained deterministic non-grid sample of closed low-poly stones.

    Each stone is an irregular bipyramid embedded slightly into the matrix.
    Sizes, positions, side counts and rotations vary intentionally; the list is
    hand-held and deterministic so regeneration remains byte stable.
    """
    samples = [
        (.12,.18,3.1,5,.20,2.2), (.31,.11,4.4,6,.71,3.2), (.56,.20,2.8,5,1.07,1.8),
        (.81,.13,5.2,7,.38,4.2), (.21,.39,3.7,6,1.31,2.7), (.47,.34,4.8,7,.04,3.8),
        (.73,.43,3.0,5,.86,2.1), (.91,.34,4.1,6,1.55,3.0), (.08,.62,4.6,7,.52,3.5),
        (.37,.58,2.7,5,1.18,1.7), (.63,.67,3.9,6,.28,2.9), (.84,.60,4.9,7,1.02,3.9),
        (.26,.83,3.3,5,.62,2.4), (.69,.86,4.3,6,1.43,3.3),
    ]
    margin_y, margin_z = 12.0, 13.0
    for uy, uz, radius, sides, rotation, proud in samples:
        cy = y0 + margin_y + uy * (y1 - y0 - 2 * margin_y)
        cz = z0 + margin_z + uz * (z1 - z0 - 2 * margin_z)
        ring = []
        for i in range(sides):
            a = rotation + 2 * math.pi * i / sides
            wobble = 1.0 + 0.13 * math.sin(3.0 * a + uy * 5.0)
            ring.append(mesh.vertex((face_x - proud * .25,
                                     cy + radius * wobble * math.cos(a),
                                     cz + radius * .82 * wobble * math.sin(a))))
        front = mesh.vertex((face_x - proud, cy + radius * .08, cz - radius * .05))
        back = mesh.vertex((face_x + 1.0, cy - radius * .06, cz + radius * .04))
        for i in range(sides):
            j = (i + 1) % sides
            mesh.face(spec.MAT_AGGREGATE, (front, ring[i], ring[j]))
            mesh.face(spec.MAT_AGGREGATE, (back, ring[j], ring[i]))


def _build_pad(mesh: Mesh, y0: float, y1: float, z0: float, z1: float,
               face_x: float, recess_x: float, ch: float) -> None:
    """Exposed-aggregate precast pad as a CLOSED chamfered frustum.

    The proud front rectangle (at face_x) is inset by the chamfer from the pad
    footprint; the larger back rectangle (at recess_x) is the pad footprint. The
    four connecting quads ARE the chamfered arrises. Front + back carry the
    precast/aggregate material; the four bevels carry the chamfer material.
    """
    fy0, fy1 = y0 + ch, y1 - ch      # proud front rectangle (inset by chamfer)
    fz0, fz1 = z0 + ch, z1 - ch
    # front (proud, +viewer) and back (at reveal floor) corners
    f = [mesh.vertex((face_x, yy, zz))
         for zz in (fz0, fz1) for yy in (fy0, fy1)]     # 0..3
    b = [mesh.vertex((recess_x, yy, zz))
         for zz in (z0, z1) for yy in (y0, y1)]         # 0..3
    # front face (outward normal toward -X) and back face (toward +X)
    mesh.face(spec.MAT_PRECAST, (f[0], f[1], f[3], f[2]))
    mesh.face(spec.MAT_PRECAST, (b[0], b[2], b[3], b[1]))
    # four chamfer bevels connecting front rect to back rect
    mesh.face(spec.MAT_CHAMFER, (f[0], f[2], b[2], b[0]))  # y0 (left)
    mesh.face(spec.MAT_CHAMFER, (f[3], f[1], b[1], b[3]))  # y1 (right)
    mesh.face(spec.MAT_CHAMFER, (f[1], f[0], b[0], b[1]))  # z0 (bottom)
    mesh.face(spec.MAT_CHAMFER, (f[2], f[3], b[3], b[2]))  # z1 (top)


def _build_sealant(mesh: Mesh, y0: float, pad_y0: float, pad_y1: float,
                   mod_bot: float, pad_z1: float, recess_x: float) -> None:
    """Broken, recessed sealant-bead segments (perished: shrunken, split, fallen
    out). Beads sit in the joint gap, their faces recessed behind the pad face
    (SEALANT_INSET), and are deliberately discontinuous -- never a full bead."""
    inset = spec.SEALANT_INSET
    bx0 = recess_x - inset          # bead face (recessed behind the -300 pad face)
    bx1 = recess_x - inset + 4.0    # bead depth toward the reveal floor
    bw = 5.0                        # bead cross-section
    zc = mod_bot + (spec.JOINT_WIDTH / 2.0) / 2.0  # bottom joint centre band
    # bottom joint: two segments with a gap between them (middle fallen out)
    for sy0, sy1 in [(y0 + 6.0, pad_y0 - 4.0), (pad_y0 + 20.0, pad_y1 - 30.0)]:
        mesh.box((bx0, sy0, zc - bw / 2), (bx1, sy1, zc + bw / 2), spec.MAT_SEALANT)
    # left joint: one short shrunken segment near the top (rest perished away)
    yc = y0 + (spec.JOINT_WIDTH / 2.0) / 2.0
    mesh.box((bx0, yc - bw / 2, pad_z1 - 34.0),
             (bx1, yc + bw / 2, pad_z1 + 4.0), spec.MAT_SEALANT)


def _build_spall(mesh: Mesh, pad_y0: float, pad_z0: float, face_x: float) -> None:
    """Sparse corner spall: a CLOSED chip (four fracture facets + a rim base
    quad) broken off the pad's lower-outer corner, exposing a short corroded
    rebar / fixing-lug stub. 'Sparingly' -- one corner only on this module."""
    sy1 = pad_y0 + 30.0   # spall footprint on the pad face (y)
    sz1 = pad_z0 + 26.0   # spall footprint (z)
    depth_x = face_x + 18.0  # fracture bites back into the pad (+X)
    rim = [(face_x, pad_y0, pad_z0), (face_x, sy1, pad_z0),
           (face_x, sy1, sz1), (face_x, pad_y0, sz1)]
    apex = (depth_x, pad_y0 + 9.0, pad_z0 + 7.0)
    # base quad closes the chip against the pad face plane (keeps it watertight)
    ids = [mesh.vertex(p) for p in rim]
    mesh.face(spec.MAT_SPALL, (ids[0], ids[3], ids[2], ids[1]))
    a = mesh.vertex(apex)
    for i in range(4):
        j = (i + 1) % 4
        mesh.face(spec.MAT_SPALL, (ids[i], ids[j], a))
    # exposed corroded rebar / fixing-lug stub protruding from the fracture
    mesh.cylinder(apex, (face_x + 5.0, pad_y0 + 13.0, pad_z0 + 11.0),
                  2.4, 8, spec.MAT_REBAR)


def _build_streaks(mesh: Mesh, pad_y0: float, pad_y1: float, pad_z0: float,
                   pad_z1: float, face_x: float) -> None:
    """Geometry-obedient weather streaks as thin CLOSED proud ribs. Each starts
    at an originating detail (a top joint corner, or the fixing/spall) and runs
    down the pad face, so the staining read follows the panel layout -- the tell
    that it was not painted on. Stepped-down widths fake the run-out taper while
    keeping every rib a closed box."""
    proud = spec.STREAK_PROUD
    # (origin_y, top_z): below the two top joint corners, and below the fixing.
    streaks = [(pad_y0 + 8.0, pad_z1), (pad_y1 - 10.0, pad_z1),
               (pad_y0 + 15.0, pad_z0 + 26.0)]
    for oy, top in streaks:
        bottom = pad_z0 + 4.0
        segs = 3
        for s in range(segs):
            zt = top - (top - bottom) * s / segs
            zb = top - (top - bottom) * (s + 1) / segs
            w = 3.0 * (1.0 - 0.22 * s)
            mesh.box((face_x - proud, oy - w / 2, zb),
                     (face_x, oy + w / 2, zt), spec.MAT_STREAK)


# ---------------------------------------------------------------------------
# Projection: from measured per-category counts to a full-wall estimate.
# ---------------------------------------------------------------------------

def project(cat: dict[str, int]) -> dict:
    n = spec.MODULE_COUNT_FULL_WALL
    spall_modules = int(round(spec.SPALL_FRACTION * n))

    repeated = {m: cat.get(m, 0) for m in sorted(spec.REPEATED_DETAIL_MATERIALS)}
    sparse = {m: cat.get(m, 0) for m in sorted(spec.SPARSE_DETAIL_MATERIALS)}
    fixed_sample = {m: cat.get(m, 0) for m in sorted(spec.FIXED_MASSING_MATERIALS)}

    per_module_repeated = sum(repeated.values())
    per_module_sparse = sum(sparse.values())

    repeated_full = {m: v * n for m, v in repeated.items()}
    sparse_full = {m: v * spall_modules for m, v in sparse.items()}

    # Fixed base massing does NOT multiply per module. It is authored once as
    # hand-placed segmented box primitives (PR #18 collision rule: none may
    # cross the door clear volume). Transparent estimate below; stated as a
    # constant, not derived by multiplying the module sample.
    #   solid backing: ~10 boxes per wing (segmented for collision) x 12 tris
    #   plinth board-marked band: authored once per wing as a subdivided strip
    backing_boxes = 4  # two solid wings, segmented above doorway as integration requires
    backing_full = backing_boxes * 12
    # Six horizontal board lifts on each of six exposed face runs.
    exposed_face_runs = 6  # 2 west wings + 2 outer returns + 2 doorway returns
    plinth_full = exposed_face_runs * spec.PLINTH_BOARD_COUNT * 12
    base_massing_full = backing_full + plinth_full

    detail_full = sum(repeated_full.values()) + sum(sparse_full.values())
    total_full = base_massing_full + detail_full

    return {
        "module_layout": {
            "module_dimensions_uu": {"width_Y": spec.MODULE_W,
                                     "height_Z": spec.MODULE_H,
                                     "plinth_height_Z": spec.PLINTH_H},
            "wing_width_uu": spec.WING_WIDTH,
            "columns_per_wing": spec.COLUMNS_PER_WING,
            "rows": spec.ROWS,
            "wings": spec.WINGS,
            "face_families": {
                "west_exterior_wings": {"faces": 2, "run_uu": 876.0,
                    "bay_width_uu": spec.MODULE_W, "bays_per_face": 6,
                    "courses": spec.ROWS, "module_equivalents": spec.WEST_MODULES},
                "outer_returns_y_plus_minus_1300": {"faces": 2, "run_uu": 573.0,
                    "bay_width_uu": spec.RETURN_BAY_W, "bays_per_face": 3,
                    "courses": spec.ROWS, "module_equivalents": spec.OUTER_RETURN_MODULES},
                "doorway_returns_y_plus_minus_424": {"faces": 2, "run_uu": 573.0,
                    "bay_width_uu": spec.RETURN_BAY_W, "bays_per_face": 3,
                    "courses": spec.ROWS, "module_equivalents": spec.DOOR_RETURN_MODULES},
            },
            "surface_assumptions": [
                "Architectural precast applies to west exterior faces of both wings.",
                "It also applies to outer return faces at y=+/-1300 and doorway return faces at y=+/-424.",
                "The east face x=112 abuts WEND_Entry and receives no exposed decoration.",
                "All families hold the 225 uu vertical course; west bays are 146 uu and return bays 191 uu, closing exactly on 876 and 573 uu respectively."
            ],
            "module_count_full_wall": n,
            "spall_fraction": spec.SPALL_FRACTION,
            "spall_modules_full_wall": spall_modules,
        },
        "per_module": {
            "repeated_detail_by_category": repeated,
            "repeated_detail_total": per_module_repeated,
            "sparse_detail_by_category": sparse,
            "sparse_detail_total_if_present": per_module_sparse,
        },
        "projected_full_wall": {
            "fixed_base_massing": {
                "note": ("Does NOT scale with module count. Authored once as "
                         "hand-placed segmented box primitives (none crossing "
                         "the door clear volume) + a per-wing board-marked "
                         "plinth strip. Estimate is stated, not multiplied "
                         "from the module sample."),
                "backing_boxes": backing_boxes,
                "backing_triangles": backing_full,
                "plinth_triangles": plinth_full,
                "base_massing_triangles": base_massing_full,
            },
            "repeated_decorative_detail": {
                "note": ("Scales LINEARLY with module count -- this is where "
                         "the scaling risk lives."),
                "by_category": repeated_full,
                "sparse_by_category": sparse_full,
                "detail_triangles": detail_full,
            },
            "total_projected_triangles": total_full,
            "scaling_risk": {
                "detail_multiplier": n,
                "detail_share_of_total": (round(detail_full / total_full, 4)
                                          if total_full else 0.0),
                "statement": (
                    f"Decorative detail multiplies x{n} (module count); base "
                    f"massing is ~constant. Detail is "
                    f"{round(100 * detail_full / total_full, 1) if total_full else 0}% "
                    f"of the projected total. Any increase in per-module detail "
                    f"density (e.g. modelling exposed aggregate as geometry "
                    f"instead of material) is amplified {n}x."),
            },
        },
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)

    mesh = build()
    obj_path = mesh.write()
    hygiene = clean_obj_file(obj_path)
    cleaned = parse_obj(obj_path)

    preview_mtl = {
        m: (tuple(c / 255.0 for c in spec.PREVIEW_COLORS[m]), 0.85, 1.0)
        for m in [spec.MAT_BASE_MASSING, spec.MAT_BOARD_PLINTH, spec.MAT_PRECAST,
                  spec.MAT_AGGREGATE,
                  spec.MAT_CHAMFER, spec.MAT_JOINT, spec.MAT_SEALANT,
                  spec.MAT_SPALL, spec.MAT_REBAR, spec.MAT_STREAK]
    }
    mtl_path = write_mtl(spec.OBJ_NAME, preview_mtl)

    cat: dict[str, int] = {}
    for face in cleaned.faces:
        cat[face.material] = cat.get(face.material, 0) + len(face.corners) - 2
    metrics = {
        "asset": spec.OBJ_NAME,
        "purpose": ("Triangle-budget prototype gate: one representative held "
                    "precast module at true scale. NOT the full wall."),
        "modules_represented": 1,
        "world_placement_cm": list(spec.WORLD_PLACEMENT),
        "intended_placement": {
            "note": ("World-aligned local coordinates (local X==world X, local "
                     "Y==world Y, local Z==world Z-3500 so base is at local "
                     "Z=0). Authored at the representative cell (first column, "
                     "bottom courses, of the +Y wing); eventual placement "
                     "transform is (0,0,3500). Visible decorated face is the "
                     "west (-X) face at the REQUIRED replacement extent x=-461; "
                     "relief proud toward -X. x=-300 is only the defective void edge."),
            "wall_extents_uu": {"x": list(spec.WALL_X), "y": list(spec.WALL_Y),
                                "z": list(spec.WALL_Z)},
            "door_clear_y_uu": list(spec.DOOR_CLEAR_Y),
            "prototype_cell_world_uu": {
                "x": [spec.EXPECTED_MIN[0], spec.BACKING_X],
                "y": list(spec.CELL_Y),
                "z": [spec.WALL_Z[0], spec.WALL_Z[0] + spec.PLINTH_H + spec.MODULE_H],
            },
        },
        "candidate_module_rationale": (
            "146 x 225 uu (1.46 x 2.25 m): within the 1960s architectural "
            "precast range (Mo-Sai / storey-band units ~1.2-1.5 m). 146 divides "
            "the 876 uu wing width exactly 6x and 225 divides the 675 uu precast "
            "field exactly 3x, so panels close on both the door jamb and the "
            "wall-end stop lines with no part-panels. Plinth is a separate "
            "1.5 m board-marked in-situ pour."),
        "triangle_counts_by_category": cat,
        "triangle_counts_grouped": {
            "fixed_base_massing": {m: cat.get(m, 0)
                                   for m in sorted(spec.FIXED_MASSING_MATERIALS)},
            "repeated_decorative_detail": {m: cat.get(m, 0)
                                           for m in sorted(spec.REPEATED_DETAIL_MATERIALS)},
            "sparse_decorative_detail": {m: cat.get(m, 0)
                                         for m in sorted(spec.SPARSE_DETAIL_MATERIALS)},
        },
        "total_prototype_triangles": sum(len(face.corners) - 2 for face in cleaned.faces),
        "mesh_hygiene": hygiene,
        "local_bounds_uu": {
            "min": [min(v[i] for v in cleaned.vertices) for i in range(3)],
            "max": [max(v[i] for v in cleaned.vertices) for i in range(3)],
        },
        "expected_world_face_x_uu": spec.FACE_X,
        "aggregate_geometry": {
            "count": spec.AGGREGATE_COUNT,
            "radius_range_uu": list(spec.AGGREGATE_RADIUS_RANGE),
            "distribution": "deterministic non-grid; varied 5/6/7-sided irregular closed bipyramids",
            "triangle_cost": cat.get(spec.MAT_AGGREGATE, 0),
        },
        "projection": project(cat),
        "collision_note": (
            "Render mesh only. Do NOT accept Unreal's import-generated convex "
            "hull and do NOT use convex decomposition -- either bridges the "
            "adjacent doorway. At integration, author explicit segmented Unreal "
            "box collision primitives; no primitive may cross the clear doorway "
            "at x -509..112, y +/-424, z 3500..3892."),
        "banned_language": ("No rivets, plate seams, welds, or steel-plate: "
                            "1960s institutional precast, not fabricated metal."),
    }
    metrics_path = QA / f"{spec.OBJ_NAME}_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    preview_path = write_preview(metrics)
    report_path = write_report(metrics)

    print(json.dumps({
        "obj": str(obj_path.relative_to(ROOT)),
        "mtl": str(mtl_path.relative_to(ROOT)),
        "metrics": str(metrics_path.relative_to(ROOT)),
        "preview": str(preview_path.relative_to(ROOT)),
        "report": str(report_path.relative_to(ROOT)),
        "total_prototype_triangles": metrics["total_prototype_triangles"],
        "triangle_counts_by_category": cat,
        "modules_represented": 1,
        "projected_full_wall_total": metrics["projection"]["projected_full_wall"]["total_projected_triangles"],
    }, indent=2))


if __name__ == "__main__":
    main()

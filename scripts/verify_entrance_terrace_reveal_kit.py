#!/usr/bin/env python3
"""Verify the Rootstead entrance-terrace reveal kit (slice 1).

Fails on: broken one-object/no-group/mtllib contract, out-of-range dimensions,
missing indexed UVs, degenerate face regions, wrong material slots, wrong
foliage vertex colours, sealed (non-open) planters, or missing visual outputs.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "SourceMesh" / "entrance_terrace_reveal"
CUTOUTS = ROOT / "cutouts" / "entrance_terrace_reveal"
QA = ROOT / "qa" / "entrance_terrace_reveal"
MTL = "VD_EntranceTerraceReveal.mtl"

EXPECTED = {
    "VD_SpecimenPlanter_Concrete": {"M_ConcretePlanter_Cast", "M_ConcretePlanter_Rim", "M_Planter_DressedSoil"},
    "VD_SpecimenPlanter_Ceramic": {"M_CeramicPlanter_Glaze", "M_CeramicPlanter_Rim", "M_Planter_DressedSoil"},
    "VD_DatePalm_Hero": {"M_DatePalm_Trunk", "M_DatePalm_Rachis", "M_DatePalm_Leaflet"},
    "VD_SoilDressing_Mound": {"M_SoilDressing_Mound"},
    "VD_SoilDressing_Litter": {"M_SoilDressing_Litter"},
    "VD_SoilDressing_Stones": {"M_SoilDressing_Stone"},
    "VD_Aloe_Specimen": {"M_Aloe_Leaf", "M_Aloe_Base"},
    "VD_Philodendron_Specimen": {"M_Philodendron_Crown", "M_Philodendron_Petiole", "M_Philodendron_Leaf"},
    "VD_Coleus_Specimen": {"M_Coleus_Base", "M_Coleus_Stem", "M_Coleus_Leaf"},
}
PLANTERS = {"VD_SpecimenPlanter_Concrete": "M_Planter_DressedSoil",
            "VD_SpecimenPlanter_Ceramic": "M_Planter_DressedSoil"}
FOLIAGE = {"VD_DatePalm_Hero", "VD_Aloe_Specimen", "VD_Philodendron_Specimen", "VD_Coleus_Specimen"}
COLORS = {
    "M_ConcretePlanter_Cast": (150, 150, 138, 255),
    "M_ConcretePlanter_Rim": (176, 172, 158, 255),
    "M_CeramicPlanter_Glaze": (36, 108, 104, 255),
    "M_CeramicPlanter_Rim": (48, 126, 120, 255),
    "M_Planter_DressedSoil": (46, 33, 21, 255),
    "M_DatePalm_Trunk": (110, 84, 52, 255),
    "M_DatePalm_Rachis": (104, 116, 56, 255),
    "M_DatePalm_Leaflet": (58, 118, 52, 255),
    "M_SoilDressing_Mound": (52, 37, 22, 255),
    "M_SoilDressing_Litter": (150, 104, 56, 255),
    "M_SoilDressing_Stone": (126, 126, 122, 255),
    "M_Aloe_Leaf": (70, 120, 64, 255),
    "M_Aloe_Base": (60, 48, 30, 255),
    "M_Philodendron_Crown": (54, 42, 27, 255),
    "M_Philodendron_Petiole": (92, 108, 54, 255),
    "M_Philodendron_Leaf": (34, 96, 46, 255),
    "M_Coleus_Base": (54, 40, 24, 255),
    "M_Coleus_Stem": (104, 86, 60, 255),
    "M_Coleus_Leaf": (130, 58, 74, 255),
}
TEXTURES = {
    "date_palm_leaflet": "date_palm_leaflet_ribbon_rgba_1024.png",
    "leaf_bark_litter": "leaf_bark_litter_rgba_1024.png",
    "philodendron_leaf": "philodendron_lobed_leaf_rgba_1024.png",
    "coleus_leaf": "coleus_leaf_rgba_1024.png",
}
VISUAL_OUTPUTS = [
    "entrance_terrace_reveal_preview.png",
    "entrance_terrace_reveal_hero_preview.png",
    "entrance_terrace_reveal_alpha_sheets_preview.png",
    "entrance_terrace_reveal_supporting_species_preview.png",
]
Vec3 = tuple[float, float, float]


@dataclass
class Obj:
    name: str
    vertices: list[Vec3]
    wind_colours: list[tuple[float, float, float] | None]
    texcoords: list[tuple[float, float]]
    faces: list[tuple[str, tuple[int, ...], tuple[int, ...]]]
    objects: list[str]
    groups: int
    mtllib: str | None


def parse(path: Path) -> Obj:
    vertices, wind_colours, texcoords, faces, objects = [], [], [], [], []
    groups = 0
    material = ""
    mtllib = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if not parts:
            continue
        if parts[0] == "v":
            vertices.append(tuple(map(float, parts[1:4])))
            wind_colours.append(tuple(map(float, parts[4:7])) if len(parts) >= 7 else None)
        elif parts[0] == "vt":
            texcoords.append(tuple(map(float, parts[1:3])))
        elif parts[0] == "o":
            objects.append(parts[1])
        elif parts[0] == "g":
            groups += 1
        elif parts[0] == "mtllib":
            mtllib = parts[1]
        elif parts[0] == "usemtl":
            material = parts[1]
        elif parts[0] == "f":
            corners = [token.split("/") for token in parts[1:]]
            faces.append((material,
                          tuple(int(c[0]) - 1 for c in corners),
                          tuple(int(c[1]) - 1 if len(c) > 1 and c[1] else -1 for c in corners)))
    return Obj(path.stem, vertices, wind_colours, texcoords, faces, objects, groups, mtllib)


def triangle_area(a: Vec3, b: Vec3, c: Vec3) -> float:
    ab = tuple(b[i] - a[i] for i in range(3))
    ac = tuple(c[i] - a[i] for i in range(3))
    cr = (ab[1] * ac[2] - ab[2] * ac[1],
          ab[2] * ac[0] - ab[0] * ac[2],
          ab[0] * ac[1] - ab[1] * ac[0])
    return 0.5 * math.sqrt(sum(value * value for value in cr))


def validate(mesh: Obj) -> dict[str, object]:
    failures: list[str] = []
    if mesh.objects != [mesh.name]:
        failures.append(f"one-object contract failed: {mesh.objects}")
    if mesh.groups:
        failures.append(f"contains {mesh.groups} forbidden g records")
    if mesh.mtllib != MTL:
        failures.append(f"mtllib is {mesh.mtllib!r}, expected {MTL!r}")
    if not mesh.vertices or not mesh.texcoords or not mesh.faces:
        failures.append("empty vertices, UVs, or faces")
    materials = {material for material, _, _ in mesh.faces}
    if materials != EXPECTED[mesh.name]:
        failures.append(f"material slots {sorted(materials)} != {sorted(EXPECTED[mesh.name])}")

    degenerate = 0
    invalid_uv_corners = 0
    for _, face, uv_indices in mesh.faces:
        if len(face) < 3 or any(index < 0 or index >= len(mesh.vertices) for index in face):
            failures.append("invalid face vertex index")
            continue
        invalid_uv_corners += sum(index < 0 or index >= len(mesh.texcoords) for index in uv_indices)
        if len(uv_indices) != len(face):
            failures.append("face corner without an indexed UV")
        for index in range(1, len(face) - 1):
            if triangle_area(mesh.vertices[face[0]], mesh.vertices[face[index]],
                             mesh.vertices[face[index + 1]]) < 1e-5:
                degenerate += 1
    if invalid_uv_corners:
        failures.append(f"{invalid_uv_corners} face corners lack valid indexed UVs")
    if degenerate:
        failures.append(f"{degenerate} degenerate triangulated face regions")

    mins = tuple(min(point[i] for point in mesh.vertices) for i in range(3))
    maxs = tuple(max(point[i] for point in mesh.vertices) for i in range(3))
    size = tuple(maxs[i] - mins[i] for i in range(3))
    if abs(mins[2]) > 0.001:
        failures.append(f"base is not on Z=0 (minZ={mins[2]:.4f})")
    if abs((mins[0] + maxs[0]) * 0.5) > 0.001 or abs((mins[1] + maxs[1]) * 0.5) > 0.001:
        failures.append("XY bounds are not centred on the origin")

    if mesh.name in PLANTERS:
        if not 180.0 <= size[0] <= 240.0 or not 180.0 <= size[1] <= 240.0:
            failures.append(f"planter diameter {size[0]:.1f}x{size[1]:.1f} cm outside 180-240")
        if not 90.0 <= size[2] <= 120.0:
            failures.append(f"planter height {size[2]:.1f} cm outside 90-120")
        soil = PLANTERS[mesh.name]
        soil_ids = {i for material, face, _ in mesh.faces if material == soil for i in face}
        if not soil_ids:
            failures.append("no dressed-soil surface present")
        else:
            soil_top = max(mesh.vertices[i][2] for i in soil_ids)
            soil_bottom = min(mesh.vertices[i][2] for i in soil_ids)
            if soil_top > size[2] - 5.0:
                failures.append(f"soil at {soil_top:.1f} cm is not recessed below the {size[2]:.1f} cm rim")
            if soil_top - soil_bottom < 5.0:
                failures.append(f"dressed soil relief is only {soil_top - soil_bottom:.1f} cm; reads as a flat lid")
    if mesh.name == "VD_DatePalm_Hero" and not 300.0 <= size[2] <= 500.0:
        failures.append(f"date palm height {size[2]:.1f} cm outside 300-500 (3-5 m)")
    if mesh.name == "VD_SoilDressing_Mound" and (size[2] > 40.0 or max(size[0], size[1]) > 160.0):
        failures.append(f"soil mound bounds {size} out of a dressing-scatter range")
    if mesh.name == "VD_Aloe_Specimen" and not 70.0 <= size[2] <= 110.0:
        failures.append(f"aloe height {size[2]:.1f} cm outside 70-110")
    if mesh.name == "VD_Philodendron_Specimen" and not 110.0 <= size[2] <= 170.0:
        failures.append(f"philodendron height {size[2]:.1f} cm outside 110-170")
    if mesh.name == "VD_Coleus_Specimen":
        if not 45.0 <= size[2] <= 75.0:
            failures.append(f"coleus height {size[2]:.1f} cm outside 45-75")
        if max(size[0], size[1]) < size[2] * 0.9:
            failures.append(f"coleus footprint {max(size[0], size[1]):.1f} cm does not read as a low mound")

    wind_values = [colour[0] for colour in mesh.wind_colours if colour is not None]
    is_foliage = mesh.name in FOLIAGE
    if is_foliage:
        if len(wind_values) != len(mesh.vertices):
            failures.append("not every foliage vertex carries RGB wind stiffness")
        elif any(abs(c[0] - c[1]) > 1e-6 or abs(c[1] - c[2]) > 1e-6 or not 0 <= c[0] <= 1
                 for c in mesh.wind_colours if c is not None):
            failures.append("wind vertex colours are not grayscale values in [0,1]")
        elif min(wind_values) > 0.001 or max(wind_values) < 0.80:
            failures.append(f"wind range {min(wind_values):.3f}-{max(wind_values):.3f} lacks rigid roots or free tips")
    elif wind_values:
        failures.append("rigid mesh unexpectedly carries wind vertex colours")

    material_faces = {material: sum(1 for m, _, _ in mesh.faces if m == material)
                      for material in sorted(materials)}
    if mesh.name == "VD_DatePalm_Hero":
        cards = material_faces.get("M_DatePalm_Leaflet", 0) // 2
        if cards < 400:
            failures.append(f"palm has only {cards} leaflet cards; sparse pinnate canopy")
        if material_faces.get("M_DatePalm_Rachis", 0) < 200:
            failures.append("palm frond rachis geometry is missing or too sparse")
        # Trunk bridge is 14x12=168 + 1 base cap fan; anything well above that means
        # the diamond leaf-base bosses were authored.
        if material_faces.get("M_DatePalm_Trunk", 0) < 300:
            failures.append("trunk lacks the raised diamond leaf-base lattice")
    if mesh.name == "VD_Aloe_Specimen":
        # ~32 lofted blades (each 8 segments x 4 diamond quads + teeth + tip fan).
        if material_faces.get("M_Aloe_Leaf", 0) < 900:
            failures.append(f"aloe has only {material_faces.get('M_Aloe_Leaf', 0)} leaf faces; sparse rosette")
        if material_faces.get("M_Aloe_Base", 0) < 16:
            failures.append("aloe basal crown geometry is missing")
    if mesh.name == "VD_Philodendron_Specimen":
        leaf_cards = material_faces.get("M_Philodendron_Leaf", 0) // 24
        if leaf_cards < 8:
            failures.append(f"philodendron has only {leaf_cards} leaf sheets; sparse canopy")
        if material_faces.get("M_Philodendron_Petiole", 0) < 250:
            failures.append("philodendron petiole geometry is missing or too sparse")
    if mesh.name == "VD_Coleus_Specimen":
        leaf_cards = material_faces.get("M_Coleus_Leaf", 0) // 6
        if leaf_cards < 36:
            failures.append(f"coleus has only {leaf_cards} leaves; not a dense mound")
        if material_faces.get("M_Coleus_Stem", 0) < 120:
            failures.append("coleus stem geometry is missing or too sparse")

    return {"pass": not failures, "failures": failures,
            "vertices": len(mesh.vertices), "texture_coordinates": len(mesh.texcoords),
            "faces": len(mesh.faces), "triangles": sum(len(face) - 2 for _, face, _ in mesh.faces),
            "object_names": mesh.objects, "group_records": mesh.groups,
            "material_slots": sorted(materials), "material_face_counts": material_faces,
            "wind_stiffness": ({"encoding": "vertex RGB grayscale", "min": min(wind_values),
                                "max": max(wind_values), "vertex_count": len(wind_values)}
                               if wind_values else None),
            "bounds_cm": {"min": mins, "max": maxs, "size": size},
            "invalid_uv_corners": invalid_uv_corners, "degenerate_regions": degenerate}


def norm(v: Vec3) -> Vec3:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return tuple(x / n for x in v)  # type: ignore[return-value]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a: Vec3, b: Vec3) -> float:
    return sum(a[i] * b[i] for i in range(3))


def render_panel(image: Image.Image, box: tuple[int, int, int, int], meshes: list[Obj],
                 offsets: list[Vec3], camera: Vec3, label: str) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    verts: list[Vec3] = []
    polys_src: list[tuple[str, list[int]]] = []
    for mesh, offset in zip(meshes, offsets):
        base = len(verts)
        verts.extend((p[0] + offset[0], p[1] + offset[1], p[2] + offset[2]) for p in mesh.vertices)
        for material, face, _ in mesh.faces:
            polys_src.append((material, [i + base for i in face]))
    target: Vec3 = tuple((min(p[i] for p in verts) + max(p[i] for p in verts)) * 0.5 for i in range(3))  # type: ignore[assignment]
    delta: Vec3 = (camera[0] - target[0], camera[1] - target[1], camera[2] - target[2])
    view = norm(delta)
    right = norm(cross((0, 0, 1), view))
    up = cross(view, right)
    projected = []
    for p in verts:
        rel: Vec3 = (p[0] - target[0], p[1] - target[1], p[2] - target[2])
        projected.append((dot(rel, right), dot(rel, up), dot(rel, view)))
    x0, y0, x1, y1 = box
    px = [p[0] for p in projected]
    py = [p[1] for p in projected]
    span_x = max(max(px) - min(px), 1)
    span_y = max(max(py) - min(py), 1)
    scale = min((x1 - x0 - 40) / span_x, (y1 - y0 - 58) / span_y)
    cx, cy = (min(px) + max(px)) / 2, (min(py) + max(py)) / 2
    sx, sy = (x0 + x1) / 2, (y0 + y1) / 2 + 10
    polygons = []
    for material, face in polys_src:
        pts = [projected[index] for index in face]
        screen = [(sx + (p[0] - cx) * scale, sy - (p[1] - cy) * scale) for p in pts]
        polygons.append((sum(p[2] for p in pts) / len(pts), material, screen))
    for _, material, polygon in sorted(polygons):
        draw.polygon(polygon, fill=COLORS[material], outline=(15, 21, 18, 110))
    draw.rectangle(box, outline=(74, 87, 77, 255), width=2)
    draw.text((x0 + 12, y0 + 10), label, fill=(232, 226, 202, 255), font=ImageFont.load_default())


def render_preview(meshes: dict[str, Obj]) -> None:
    image = Image.new("RGB", (2400, 1500), (19, 24, 21))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((45, 22), "ENTRANCE-TERRACE REVEAL KIT / SLICE 1", fill=(238, 226, 190), font=font)
    draw.text((45, 45), "Round specimen planters · date-palm hero · scatterable soil dressing · base-centred Unreal cm",
              fill=(150, 173, 157), font=font)
    panels = [
        ("VD_SpecimenPlanter_Concrete", (40, 80, 800, 620), (620, -640, 300), "CONCRETE PLANTER / 2.24 m x 0.98 m"),
        ("VD_SpecimenPlanter_Ceramic", (820, 80, 1580, 620), (560, -580, 320), "GLAZED CERAMIC PLANTER / 1.88 m x 1.16 m"),
        ("VD_DatePalm_Hero", (1600, 80, 2360, 1440), (760, -900, 520), "DATE PALM HERO / ~4.1 m"),
        ("VD_SoilDressing_Mound", (40, 660, 570, 1010), (150, -170, 120), "SOIL MOUND"),
        ("VD_SoilDressing_Litter", (600, 660, 1130, 1010), (150, -170, 150), "LEAF / BARK LITTER"),
        ("VD_SoilDressing_Stones", (1160, 660, 1580, 1010), (150, -170, 110), "STONE CLUSTER"),
    ]
    for name, box, camera, label in panels:
        render_panel(image, box, [meshes[name]], [(0, 0, 0)], camera, label)
    notes = ["Planters are open urns: visible dressed soil recessed below the rim; interior stays hollow.",
             "Author planter collision as a segmented ring + base disc, never one auto convex hull.",
             "Palm vertex RGB = wind stiffness (trunk 0, free frond tips 1); trunk carries diamond leaf-base bosses.",
             "Soil-dressing meshes are base-centred at Z=0 and drop into these and the existing terrace planters."]
    for i, note in enumerate(notes):
        draw.text((45, 1050 + i * 34), note, fill=(189, 200, 184), font=font)
    image.save(QA / "entrance_terrace_reveal_preview.png")


def render_hero(meshes: dict[str, Obj]) -> None:
    """The look-right shot: palm planted in the concrete planter, soil dressing at the base."""
    image = Image.new("RGB", (2000, 1600), (19, 24, 21))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((45, 22), "REVEAL COMPOSITION / DATE PALM IN CONCRETE SPECIMEN PLANTER", fill=(238, 226, 190), font=font)
    planter = meshes["VD_SpecimenPlanter_Concrete"]
    palm = meshes["VD_DatePalm_Hero"]
    mound = meshes["VD_SoilDressing_Mound"]
    litter = meshes["VD_SoilDressing_Litter"]
    stones = meshes["VD_SoilDressing_Stones"]
    soil_top = 80.0  # concrete planter soil disc height (~height - soil_depth)
    stack = [planter, palm, mound, litter, stones]
    offsets: list[Vec3] = [(0, 0, 0), (0, 0, soil_top - 4), (34, 20, soil_top),
                           (-30, -26, soil_top), (26, -30, soil_top)]
    render_panel(image, (40, 70, 1960, 1560), stack, offsets, (900, -1150, 620),
                 "HERO ELEVATION / palm anchored in dressed soil, litter + stones scattered on the surface")
    image.save(QA / "entrance_terrace_reveal_hero_preview.png")


def render_supporting(meshes: dict[str, Obj]) -> None:
    """Supporting-species elevation: aloe, philodendron, coleus, each base-centred."""
    image = Image.new("RGB", (2200, 1300), (19, 24, 21))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((45, 22), "ENTRANCE-TERRACE REVEAL KIT / SLICE 2 — SUPPORTING SPECIES", fill=(238, 226, 190), font=font)
    draw.text((45, 45), "Aloe rosette · philodendron · coleus mound · base-centred Unreal cm · vertex-colour wind stiffness",
              fill=(150, 173, 157), font=font)
    panels = [
        ("VD_Aloe_Specimen", (40, 80, 780, 1120), (200, -230, 150), "ALOE ROSETTE / ~0.86 m, thick 3-D succulent leaves"),
        ("VD_Philodendron_Specimen", (800, 80, 1440, 1200), (330, -400, 260), "PHILODENDRON / ~1.43 m, lobed alpha-cut leaves + petioles"),
        ("VD_Coleus_Specimen", (1460, 80, 2160, 1120), (170, -200, 150), "COLEUS MOUND / ~0.62 m, patterned alpha-cut leaves + stems"),
    ]
    for name, box, camera, label in panels:
        render_panel(image, box, [meshes[name]], [(0, 0, 0)], camera, label)
    notes = ["Aloe: genuinely 3-D lofted diamond-section blades with serrated margins; no alpha card, no leaf collision.",
             "Philodendron: real curved petiole tubes carry lobed RGBA leaf sheets; overlap-only, optional crown capsule.",
             "Coleus: branching real stems with opposite decussate patterned RGBA leaves forming a low mound wider than tall.",
             "All three carry vertex-colour wind stiffness: stems/petioles/attachments 0, free leaf tips toward 1."]
    for i, note in enumerate(notes):
        draw.text((45, 1140 + i * 34), note, fill=(189, 200, 184), font=font)
    image.save(QA / "entrance_terrace_reveal_supporting_species_preview.png")


def verify_textures() -> dict[str, dict[str, object]]:
    results: dict[str, dict[str, object]] = {}
    mtl_text = (SOURCE / MTL).read_text(encoding="utf-8")
    checker = Image.new("RGB", (1660, 960), (36, 40, 36))
    draw = ImageDraw.Draw(checker)
    for key, (species, filename) in enumerate(TEXTURES.items()):
        path = CUTOUTS / filename
        failures: list[str] = []
        if not path.exists():
            results[species] = {"pass": False, "failures": ["missing texture"]}
            continue
        image = Image.open(path)
        if image.size != (1024, 1024):
            failures.append(f"size is {image.size}, expected 1024x1024")
        if image.mode != "RGBA":
            failures.append(f"mode is {image.mode}, expected RGBA")
        rgba = image.convert("RGBA")
        alpha = rgba.getchannel("A")
        extrema = alpha.getextrema()
        histogram = alpha.histogram()
        opaque_fraction = sum(histogram[128:]) / (1024 * 1024)
        if extrema != (0, 255):
            failures.append(f"alpha extrema are {extrema}, expected (0,255)")
        if not 0.03 <= opaque_fraction <= 0.65:
            failures.append(f"opaque coverage {opaque_fraction:.3f} outside 0.03-0.65")
        corners = [alpha.getpixel(point) for point in ((0, 0), (1023, 0), (0, 1023), (1023, 1023))]
        if any(corners):
            failures.append(f"transparent padding failed at corners: {corners}")
        if mtl_text.count(filename) < 2:
            failures.append("MTL does not reference the RGBA sheet for both base colour and opacity")
        results[species] = {"pass": not failures, "failures": failures,
                            "path": str(path.relative_to(ROOT)), "size": image.size,
                            "mode": image.mode, "alpha_extrema": extrema,
                            "opaque_fraction": round(opaque_fraction, 4)}
        x0 = 35 + key * 810
        tile = 56
        for yy in range(35, 803, tile):
            for xx in range(x0, x0 + 720, tile):
                shade = 86 if ((xx - x0) // tile + (yy - 35) // tile) % 2 else 134
                draw.rectangle((xx, yy, min(xx + tile, x0 + 720), min(yy + tile, 803)), fill=(shade,) * 3)
        preview = rgba.resize((720, 720), Image.Resampling.LANCZOS)
        checker.paste(preview, (x0, 55), preview)
        draw.text((x0, 815), f"{species.upper()} / {filename}", fill=(232, 226, 202))
    checker.save(QA / "entrance_terrace_reveal_alpha_sheets_preview.png")
    return results


def main() -> None:
    QA.mkdir(parents=True, exist_ok=True)
    actual = {path.stem for path in SOURCE.glob("*.obj")}
    missing, extra = sorted(set(EXPECTED) - actual), sorted(actual - set(EXPECTED))
    meshes = {name: parse(SOURCE / f"{name}.obj") for name in EXPECTED if name in actual}
    results = {name: validate(mesh) for name, mesh in meshes.items()}
    texture_results = verify_textures()
    if meshes:
        render_preview(meshes)
        render_hero(meshes)
        if all(name in meshes for name in ("VD_Aloe_Specimen", "VD_Philodendron_Specimen", "VD_Coleus_Specimen")):
            render_supporting(meshes)
    visual = {name: (QA / name).exists() and (QA / name).stat().st_size > 1024 for name in VISUAL_OUTPUTS}
    report = {"pass": (not missing and not extra
                       and all(r["pass"] for r in results.values())
                       and all(r["pass"] for r in texture_results.values())
                       and all(visual.values())),
              "missing": missing, "extra": extra, "mesh_count": len(meshes),
              "meshes": results, "textures": texture_results,
              "visual_outputs": {name: str((QA / name).relative_to(ROOT)) if ok else "MISSING"
                                 for name, ok in visual.items()}}
    (QA / "entrance_terrace_reveal_verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()

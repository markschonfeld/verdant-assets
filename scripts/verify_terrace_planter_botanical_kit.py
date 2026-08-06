#!/usr/bin/env python3
"""Verify contract, dimensions, materials, and visual silhouettes for terrace kit."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "SourceMesh" / "terrace_botanical"
CUTOUTS = ROOT / "cutouts" / "terrace_botanical"
QA = ROOT / "qa" / "terrace_planter_botanical"
MTL = "VD_TerraceBotanical.mtl"
EXPECTED = {
    "VD_TerracePlanter": {"M_Planter_AgedConcrete", "M_Planter_CastRepair", "M_Planter_Soil"},
    "VD_TerracePlanter_EndCap": {"M_Planter_AgedConcrete", "M_Planter_CastRepair"},
    "VD_Dracaena_A": {"M_Dracaena_Cane", "M_Dracaena_Leaf"},
    "VD_Dracaena_B": {"M_Dracaena_Cane", "M_Dracaena_Leaf"},
    "VD_Dracaena_C": {"M_Dracaena_Cane", "M_Dracaena_Leaf"},
    "VD_ZZPlant_A": {"M_ZZ_Stem", "M_ZZ_Leaf"},
    "VD_ZZPlant_B": {"M_ZZ_Stem", "M_ZZ_Leaf"},
    "VD_ZZPlant_C": {"M_ZZ_Stem", "M_ZZ_Leaf"},
    "VD_DwarfMorningGlory_A": {"M_MorningGlory_Stem", "M_MorningGlory_Leaf", "M_MorningGlory_Flower"},
    "VD_DwarfMorningGlory_B": {"M_MorningGlory_Stem", "M_MorningGlory_Leaf", "M_MorningGlory_Flower"},
    "VD_DwarfMorningGlory_C": {"M_MorningGlory_Stem", "M_MorningGlory_Leaf", "M_MorningGlory_Flower"},
}
COLORS = {
    "M_Planter_AgedConcrete": (91, 95, 84, 255),
    "M_Planter_CastRepair": (126, 114, 85, 255),
    "M_Planter_Soil": (38, 27, 16, 255),
    "M_Dracaena_Cane": (106, 78, 45, 255),

    "M_Dracaena_Leaf": (53, 105, 48, 255),
    "M_ZZ_Stem": (75, 126, 51, 255),
    "M_ZZ_Leaf": (36, 101, 43, 255),
    "M_MorningGlory_Stem": (66, 120, 49, 255),
    "M_MorningGlory_Leaf": (72, 145, 67, 255),
    "M_MorningGlory_Flower": (89, 111, 219, 255),
}
TEXTURES = {
    "dracaena": "dracaena_marginata_leaf_rgba_1024.png",
    "zz": "zz_leaflet_pair_rgba_1024.png",
    "morning_glory": "morning_glory_leaf_flower_rgba_1024.png",
}
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
    cross = (ab[1] * ac[2] - ab[2] * ac[1],
             ab[2] * ac[0] - ab[0] * ac[2],
             ab[0] * ac[1] - ab[1] * ac[0])
    return 0.5 * math.sqrt(sum(value * value for value in cross))


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
        for index in range(1, len(face) - 1):
            if triangle_area(mesh.vertices[face[0]], mesh.vertices[face[index]], mesh.vertices[face[index + 1]]) < 1e-5:
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
    if mesh.name == "VD_TerracePlanter" and any(abs(a - b) > 0.01 for a, b in zip(size, (126, 245, 110))):
        failures.append(f"planter dimensions are {size}, expected (126,245,110)")
    if mesh.name.startswith("VD_Dracaena") and not (150 <= size[2] <= 220):
        failures.append(f"dracaena height {size[2]:.1f} cm outside 150-220 cm")
    if mesh.name.startswith("VD_ZZPlant") and not (60 <= size[2] <= 95):
        failures.append(f"ZZ height {size[2]:.1f} cm outside 60-95 cm")
    if mesh.name.startswith("VD_DwarfMorningGlory") and size[2] < 80:
        failures.append(f"morning-glory curtain is too short at {size[2]:.1f} cm")

    wind_values = [colour[0] for colour in mesh.wind_colours if colour is not None]
    is_foliage = mesh.name.startswith(("VD_Dracaena", "VD_ZZPlant", "VD_DwarfMorningGlory"))
    if is_foliage:
        if len(wind_values) != len(mesh.vertices):
            failures.append("not every foliage vertex carries RGB wind stiffness")
        elif any(abs(colour[0] - colour[1]) > 1e-6 or
                 abs(colour[1] - colour[2]) > 1e-6 or not 0 <= colour[0] <= 1
                 for colour in mesh.wind_colours if colour is not None):
            failures.append("wind vertex colours are not grayscale values in [0,1]")
        elif min(wind_values) > 0.001 or max(wind_values) < 0.90:
            failures.append(f"wind range {min(wind_values):.3f}-{max(wind_values):.3f} lacks rigid roots or free tips")
    elif wind_values:
        failures.append("rigid planter mesh unexpectedly carries wind vertex colours")

    material_faces = {material: sum(1 for m, _, _ in mesh.faces if m == material)
                      for material in sorted(materials)}
    dracaena_contract = {
        "VD_Dracaena_A": (2, 52), "VD_Dracaena_B": (3, 58), "VD_Dracaena_C": (3, 64)}
    zz_contract = {"VD_ZZPlant_A": 7, "VD_ZZPlant_B": 9, "VD_ZZPlant_C": 11}
    morning_contract = {
        "VD_DwarfMorningGlory_A": 6, "VD_DwarfMorningGlory_B": 8,
        "VD_DwarfMorningGlory_C": 10}
    if mesh.name in dracaena_contract:
        heads, leaves = dracaena_contract[mesh.name]
        authored = material_faces.get("M_Dracaena_Leaf", 0) // 3
        if authored != heads * leaves:
            failures.append(f"dracaena cards {authored} != {heads} heads x {leaves} leaves")
    if mesh.name in zz_contract:
        fronds = zz_contract[mesh.name]
        leaflets = material_faces.get("M_ZZ_Leaf", 0)
        if not fronds * 10 <= leaflets <= fronds * 16:
            failures.append(f"ZZ leaflet count {leaflets} outside {fronds} fronds x 10-16")
    if mesh.name in morning_contract:
        strands = morning_contract[mesh.name]
        leaves = material_faces.get("M_MorningGlory_Leaf", 0) // 6
        flowers = material_faces.get("M_MorningGlory_Flower", 0) // 8
        if not strands * 7 <= leaves <= strands * 9:
            failures.append(f"morning-glory leaf count {leaves} outside {strands} strands x 7-9")
        if not strands * 2 <= flowers <= strands * 4:
            failures.append(f"morning-glory flower count {flowers} outside {strands} strands x 2-4")
    return {"pass": not failures, "failures": failures,
            "vertices": len(mesh.vertices), "texture_coordinates": len(mesh.texcoords),
            "faces": len(mesh.faces), "triangles": sum(len(face) - 2 for _, face, _ in mesh.faces),
            "object_names": mesh.objects, "group_records": mesh.groups,
            "material_slots": sorted(materials),
            "material_face_counts": material_faces,
            "wind_stiffness": ({"encoding": "vertex RGB grayscale", "min": min(wind_values),
                                  "max": max(wind_values), "vertex_count": len(wind_values)}
                                 if wind_values else None),
            "bounds_cm": {"min": mins, "max": maxs, "size": size},
            "invalid_uv_corners": invalid_uv_corners, "degenerate_regions": degenerate}


def norm(v: Vec3) -> Vec3:
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v)  # type: ignore[return-value]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a: Vec3, b: Vec3) -> float:
    return sum(a[i] * b[i] for i in range(3))


def render_panel(image: Image.Image, box: tuple[int, int, int, int], mesh: Obj,
                 camera: Vec3, label: str) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    target: Vec3 = tuple((min(p[i] for p in mesh.vertices) + max(p[i] for p in mesh.vertices)) * 0.5 for i in range(3))  # type: ignore[assignment]
    delta: Vec3 = (camera[0] - target[0], camera[1] - target[1], camera[2] - target[2])
    view = norm(delta)
    right = norm(cross((0, 0, 1), view))
    up = cross(view, right)
    projected = []
    for p in mesh.vertices:
        relative: Vec3 = (p[0] - target[0], p[1] - target[1], p[2] - target[2])
        projected.append((dot(relative, right), dot(relative, up), dot(relative, view)))
    x0, y0, x1, y1 = box
    px = [p[0] for p in projected]; py = [p[1] for p in projected]
    span_x = max(max(px) - min(px), 1); span_y = max(max(py) - min(py), 1)
    scale = min((x1 - x0 - 40) / span_x, (y1 - y0 - 58) / span_y)
    cx, cy = (min(px) + max(px)) / 2, (min(py) + max(py)) / 2
    sx, sy = (x0 + x1) / 2, (y0 + y1) / 2 + 10
    polygons = []
    for material, face, _ in mesh.faces:
        points = [projected[index] for index in face]
        screen = [(sx + (p[0] - cx) * scale, sy - (p[1] - cy) * scale) for p in points]
        polygons.append((sum(p[2] for p in points) / len(points), material, screen))
    for _, material, polygon in sorted(polygons):
        draw.polygon(polygon, fill=COLORS[material], outline=(15, 21, 18, 115))
    draw.rectangle(box, outline=(74, 87, 77, 255), width=2)
    draw.text((x0 + 12, y0 + 10), label, fill=(232, 226, 202, 255), font=ImageFont.load_default())


def compose_scene(meshes: dict[str, Obj], instances: Iterable[tuple[str, float, float, float, float]]) -> Obj:
    vertices: list[Vec3] = []
    texcoords: list[tuple[float, float]] = []
    faces: list[tuple[str, tuple[int, ...], tuple[int, ...]]] = []
    for name, x, y, z, yaw_degrees in instances:
        source = meshes[name]
        angle = math.radians(yaw_degrees)
        cosine, sine = math.cos(angle), math.sin(angle)
        vertex_offset, uv_offset = len(vertices), len(texcoords)
        vertices.extend((x + p[0] * cosine - p[1] * sine,
                         y + p[0] * sine + p[1] * cosine,
                         z + p[2]) for p in source.vertices)
        texcoords.extend(source.texcoords)
        faces.extend((material,
                      tuple(index + vertex_offset for index in face),
                      tuple(index + uv_offset for index in uv_indices))
                     for material, face, uv_indices in source.faces)
    return Obj("TerracePlantingAssembly", vertices, [None] * len(vertices), texcoords, faces,
               ["TerracePlantingAssembly"], 0, MTL)


def render_assembly(meshes: dict[str, Obj]) -> None:
    instances: list[tuple[str, float, float, float, float]] = []
    for y in (-245.0, 0.0, 245.0):
        instances.append(("VD_TerracePlanter", 0, y, 0, 0))
    instances.extend((("VD_TerracePlanter_EndCap", 0, -367.5, 0, 0),
                      ("VD_TerracePlanter_EndCap", 0, 367.5, 0, 180)))
    # Mixed display planting: high points alternate, ZZ fills the base, and
    # morning-glory curtains overlap along the visitor-facing west wall.
    instances.extend((("VD_Dracaena_B", 0, -232, 93, 18),
                      ("VD_Dracaena_C", 0, 18, 93, -12),
                      ("VD_Dracaena_A", 0, 248, 93, 31)))
    for name, y, yaw in (("VD_ZZPlant_A", -322, -12), ("VD_ZZPlant_C", -120, 24),
                         ("VD_ZZPlant_B", 102, -20), ("VD_ZZPlant_A", 330, 16)):
        instances.append((name, 5, y, 93, yaw))
    for name, y in (("VD_DwarfMorningGlory_A", -310),
                    ("VD_DwarfMorningGlory_B", -190),
                    ("VD_DwarfMorningGlory_C", -65),
                    ("VD_DwarfMorningGlory_A", 65),
                    ("VD_DwarfMorningGlory_B", 190),
                    ("VD_DwarfMorningGlory_C", 310)):
        instances.append((name, -63, y, 0, 0))
    scene = compose_scene(meshes, instances)
    image = Image.new("RGB", (2400, 1400), (19, 24, 21))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((45, 22), "ENTRANCE TERRACE / THREE-BAY ASSEMBLY STUDY", fill=(238, 226, 190), font=font)
    draw.text((45, 46), "Planter centres at Y -245 / 0 / +245 cm; terminal caps at +/-367.5 cm", fill=(150, 173, 157), font=font)
    render_panel(image, (40, 80, 2360, 900), scene, (-950, -1250, 650), "VISITOR-SIDE HERO / MORNING GLORY SOFTENS BARRIER FACE")
    render_panel(image, (40, 930, 2360, 1355), scene, (1100, 0, 330), "END ELEVATION / 1.26 m DEPTH + MIXED CANOPY")
    image.save(QA / "terrace_planter_botanical_assembly_preview.png")


def render_preview(meshes: dict[str, Obj]) -> None:
    image = Image.new("RGB", (2400, 1800), (19, 24, 21))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((45, 22), "ENTRANCE TERRACE / MODULAR PLANTER + BOTANICAL KIT", fill=(238, 226, 190), font=font)
    draw.text((45, 45), "245 cm bay cadence · 126 cm deep · 110 cm high · base-centred Unreal centimetres", fill=(150, 173, 157), font=font)
    panels = [
        ("VD_TerracePlanter", (40, 80, 2360, 520), (650, -900, 520), "TILEABLE MID MODULE / OPEN ENDS + SOIL"),
        ("VD_TerracePlanter_EndCap", (40, 550, 570, 900), (520, -520, 310), "BOLTED END CAP"),
        ("VD_Dracaena_A", (600, 550, 1160, 1160), (520, -700, 330), "DRACAENA A / 1.67 m"),
        ("VD_Dracaena_B", (1190, 550, 1750, 1160), (520, -700, 360), "DRACAENA B / 1.93 m"),
        ("VD_Dracaena_C", (1780, 550, 2360, 1160), (520, -700, 400), "DRACAENA C / 2.08 m"),
        ("VD_ZZPlant_A", (40, 1190, 570, 1480), (310, -420, 170), "ZZ A / 0.61 m"),
        ("VD_ZZPlant_B", (600, 1190, 1130, 1480), (310, -420, 190), "ZZ B / 0.73 m"),
        ("VD_ZZPlant_C", (1160, 1190, 1690, 1480), (310, -420, 210), "ZZ C / 0.82 m"),
        ("VD_DwarfMorningGlory_B", (1720, 1190, 2360, 1745), (380, -500, 220), "DWARF MORNING GLORY / RIM-TO-DECK DRAPE"),
    ]
    for name, box, camera, label in panels:
        render_panel(image, box, meshes[name], camera, label)
    notes = ["Separate instancing meshes: 3 Dracaena, 3 ZZ, 3 morning-glory variants.",
             "Leaves are low-poly alpha cards/ribbons; canes and stems remain real geometry.",
             "Vertex RGB is wind stiffness: black at root/attachment, white at free foliage tips.",
             "Morning-glory origin is curtain bottom; flowers face visitor-side X-." ]
    for i, note in enumerate(notes):
        draw.text((45, 1515 + i * 35), note, fill=(189, 200, 184), font=font)
    image.save(QA / "terrace_planter_botanical_preview.png")


def verify_textures() -> dict[str, dict[str, object]]:
    results: dict[str, dict[str, object]] = {}
    mtl_text = (SOURCE / MTL).read_text(encoding="utf-8")
    checker = Image.new("RGB", (2400, 900), (36, 40, 36))
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
        alpha_values: list[int] = list(alpha.get_flattened_data())  # type: ignore[arg-type]
        opaque_fraction = sum(1 for value in alpha_values if value >= 128) / (1024 * 1024)
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

        x0 = 35 + key * 790
        tile = 56
        for yy in range(35, 803, tile):
            for xx in range(x0, x0 + 720, tile):
                shade = 86 if ((xx - x0) // tile + (yy - 35) // tile) % 2 else 134
                draw.rectangle((xx, yy, min(xx + tile, x0 + 720), min(yy + tile, 803)), fill=(shade,) * 3)
        preview = rgba.resize((720, 720), Image.Resampling.LANCZOS)
        checker.paste(preview, (x0, 55), preview)
        draw.text((x0, 815), f"{species.upper()} / {filename}", fill=(232, 226, 202))
    checker.save(QA / "terrace_botanical_alpha_sheets_preview.png")
    return results


def main() -> None:
    QA.mkdir(parents=True, exist_ok=True)
    actual = {path.stem for path in SOURCE.glob("*.obj")}
    missing, extra = sorted(set(EXPECTED) - actual), sorted(actual - set(EXPECTED))
    meshes = {name: parse(SOURCE / f"{name}.obj") for name in EXPECTED if name in actual}
    results = {name: validate(mesh) for name, mesh in meshes.items()}
    texture_results = verify_textures()
    report = {"pass": (not missing and not extra and all(r["pass"] for r in results.values())
                        and all(r["pass"] for r in texture_results.values())),
              "missing": missing, "extra": extra, "mesh_count": len(meshes), "meshes": results,
              "textures": texture_results,
              "tiling": {"axis": "Y", "module_length_cm": 245.0,
                         "end_planes_cm": [-122.5, 122.5],
                         "continuous_components": ["front wall", "back wall", "rim rails", "soil surface"],
                         "separate_end_cap": True}}
    (QA / "terrace_planter_botanical_verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if meshes:
        render_preview(meshes)
        render_assembly(meshes)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()

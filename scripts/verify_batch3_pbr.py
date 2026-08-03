#!/usr/bin/env python3
"""Mechanical and visual-artifact QA for VERDANT Batch 3 PBR sets."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from generate_batch3_pbr import normal_dx

ROOT = Path(__file__).resolve().parents[1]
PBR = ROOT / "textures" / "pbr"
QA = ROOT / "qa" / "batch3_pbr"
QA.mkdir(parents=True, exist_ok=True)
MATERIALS = ["soil_terrace", "steel_rusted_beam", "concrete_formed", "glass_dome_grime"]
MAPS = ["basecolor", "normal", "roughness", "ao"]
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 19)
SMALL = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)


def stats(a: np.ndarray) -> dict[str, float]:
    return {
        "min": int(a.min()),
        "max": int(a.max()),
        "mean": round(float(a.mean()), 3),
        "stddev": round(float(a.std()), 3),
        "p05": round(float(np.percentile(a, 5)), 3),
        "p95": round(float(np.percentile(a, 95)), 3),
    }


def exact_seams(a: np.ndarray) -> tuple[bool, bool]:
    return bool(np.array_equal(a[:, 0], a[:, -1])), bool(np.array_equal(a[0], a[-1]))


def quadrant_spread(lum: np.ndarray) -> float:
    h, w = lum.shape
    q = [lum[:h//2, :w//2].mean(), lum[:h//2, w//2:].mean(), lum[h//2:, :w//2].mean(), lum[h//2:, w//2:].mean()]
    return round(float(max(q) - min(q)), 3)


def tile_preview(im: Image.Image, out: Path) -> None:
    thumb = im.resize((384, 384), Image.Resampling.LANCZOS)
    canvas = Image.new(im.mode, (768, 768))
    for x in (0, 384):
        for y in (0, 384):
            canvas.paste(thumb, (x, y))
    canvas.save(out, optimize=True)


def lit_preview(base: np.ndarray, normal: np.ndarray, rough: np.ndarray, ao: np.ndarray) -> Image.Image:
    b = base.astype(np.float32) / 255
    n = normal.astype(np.float32) / 255 * 2 - 1
    # Fixed frontal/upper-left test light. This is QA only, never baked into base color.
    light = np.array([-.38, -.42, .82], np.float32)
    light /= np.linalg.norm(light)
    ndotl = np.clip((n * light).sum(axis=-1), 0, 1)
    r = rough.astype(np.float32) / 255
    ambient = .27
    diffuse = ambient + .82 * ndotl
    spec = np.power(np.clip(ndotl, 0, 1), 5 + 70 * r) * (1 - r) * .75
    shaded = b * diffuse[..., None] * (ao[..., None] / 255) + spec[..., None]
    return Image.fromarray(np.clip(shaded * 255, 0, 255).astype(np.uint8), "RGB")


report: dict = {
    "spec": {
        "dimensions": [2048, 2048],
        "format": "PNG",
        "normal_convention": "DirectX tangent-space; green channel down (+image-Y slope => +G)",
        "roughness_encoding": "black=smooth/mirror, white=rough",
        "ao_encoding": "white=open, dark=crevice",
        "opacity_encoding": "white=clear glass, dark=heavy grime",
        "basecolor_policy": "material pigment/color only; no height, normal, AO, lighting, shadow, or vignette multiplication",
    },
    "materials": {},
}

# Convention unit check: a height ramp increasing down the image must produce
# green > 127 in DirectX convention, and the opposite slope green < 127.
ramp_y = np.sin(np.arange(2048, dtype=np.float32) * 2 * np.pi / 2048)
ramp = np.repeat(ramp_y[:, None], 2048, axis=1)
ramp_normal = normal_dx(ramp, 18)
g_down = int(ramp_normal[0, 1024, 1])
g_up = int(ramp_normal[1024, 1024, 1])
report["directx_convention_unit_check"] = {
    "positive_image_y_slope_green": g_down,
    "negative_image_y_slope_green": g_up,
    "pass": bool(g_down > 127 and g_up < 127),
}

for material in MATERIALS:
    rec: dict = {"maps": {}}
    loaded: dict[str, np.ndarray] = {}
    passes = []
    for map_name in MAPS + (["opacity"] if material == "glass_dome_grime" else []):
        path = PBR / f"{material}_{map_name}.png"
        raw = Image.open(path)
        expected_mode = "RGB" if map_name in ("basecolor", "normal") else "L"
        im = raw.convert(expected_mode)
        a = np.asarray(im)
        loaded[map_name] = a
        lr, tb = exact_seams(a)
        lum = (.2126*a[..., 0] + .7152*a[..., 1] + .0722*a[..., 2]) if a.ndim == 3 else a.astype(np.float32)
        s: dict[str, Any] = stats(lum)
        map_pass = raw.format == "PNG" and im.size == (2048, 2048) and raw.mode == expected_mode and lr and tb
        if map_name == "basecolor":
            s["quadrant_luminance_spread"] = quadrant_spread(lum)
            map_pass = map_pass and s["quadrant_luminance_spread"] < 28
        elif map_name == "normal":
            channels = [stats(a[..., i]) for i in range(3)]
            s["channels_rgb"] = channels
            # Blue-positive tangent normals, with meaningful X/Y relief.
            map_pass = map_pass and channels[2]["mean"] > 175 and channels[0]["stddev"] > 3 and channels[1]["stddev"] > 3
        elif map_name == "roughness":
            # Explicit guard against the costly near-flat-grey failure mode.
            s["p95_minus_p05"] = round(s["p95"] - s["p05"], 3)
            map_pass = map_pass and s["stddev"] >= 18 and s["p95_minus_p05"] >= 55
        elif map_name == "ao":
            s["p95_minus_p05"] = round(s["p95"] - s["p05"], 3)
            map_pass = map_pass and s["p95_minus_p05"] >= 28 and s["p95"] >= 245
        elif map_name == "opacity":
            s["p95_minus_p05"] = round(s["p95"] - s["p05"], 3)
            map_pass = map_pass and s["p95_minus_p05"] >= 35 and s["p95"] >= 230
        rec["maps"][map_name] = {
            "path": str(path.relative_to(ROOT)), "size": list(im.size), "mode": raw.mode,
            "format": raw.format, "exact_left_right": lr, "exact_top_bottom": tb,
            "bytes": path.stat().st_size, "statistics": s, "pass": bool(map_pass),
        }
        passes.append(bool(map_pass))
    # All maps stack exactly by dimensions, and all have byte-identical seam endpoints.
    rec["alignment_pass"] = len({a.shape[:2] for a in loaded.values()}) == 1
    base = loaded["basecolor"]
    normal = loaded["normal"]
    rough = loaded["roughness"]
    ao = loaded["ao"]
    tile_preview(Image.fromarray(base, "RGB"), QA / f"{material}_basecolor_2x2.png")
    lit_preview(base, normal, rough, ao).resize((768, 768), Image.Resampling.LANCZOS).save(QA / f"{material}_lit_preview.png", optimize=True)
    rec["pass"] = bool(all(passes) and rec["alignment_pass"])
    report["materials"][material] = rec

# Contact sheet: base / normal / roughness / AO / QA-only lit result (+ opacity inset on glass).
cell = 280
sheet = Image.new("RGB", (cell * 5, 4 * (cell + 48)), (21, 27, 25))
d = ImageDraw.Draw(sheet)
headers = ["BASE COLOR", "NORMAL (DX)", "ROUGHNESS", "AO", "QA-ONLY LIT"]
for c, label in enumerate(headers):
    d.text((c * cell + 9, 8), label, font=SMALL, fill=(229, 220, 196))
for row, material in enumerate(MATERIALS):
    y = row * (cell + 48) + 30
    base = Image.open(PBR / f"{material}_basecolor.png").convert("RGB")
    normal = Image.open(PBR / f"{material}_normal.png").convert("RGB")
    rough = Image.open(PBR / f"{material}_roughness.png").convert("L")
    ao = Image.open(PBR / f"{material}_ao.png").convert("L")
    lit = Image.open(QA / f"{material}_lit_preview.png").convert("RGB")
    ims = [base, normal, rough.convert("RGB"), ao.convert("RGB"), lit]
    for c, im in enumerate(ims):
        sheet.paste(im.resize((cell, cell), Image.Resampling.LANCZOS), (c * cell, y))
    d.text((10, y + cell + 7), material.replace("_", " ").upper(), font=FONT, fill=(236, 220, 177))
    if material == "glass_dome_grime":
        opacity = Image.open(PBR / f"{material}_opacity.png").convert("L").resize((90, 90), Image.Resampling.LANCZOS)
        sheet.paste(opacity.convert("RGB"), (cell * 4 - 98, y + 8))
        d.text((cell * 4 - 96, y + 101), "OPACITY", font=SMALL, fill=(229, 220, 196))
sheet.save(QA / "batch3_pbr_contact_sheet.png", optimize=True)

report["pass"] = bool(report["directx_convention_unit_check"]["pass"] and all(r["pass"] for r in report["materials"].values()))
(QA / "batch3_pbr_report.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
raise SystemExit(0 if report["pass"] else 1)

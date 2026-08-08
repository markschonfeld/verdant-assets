#!/usr/bin/env python3
"""Mechanical and visual QA for VERDANT institutional surface PBR maps."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from generate_batch3_pbr import normal_dx

ROOT = Path(__file__).resolve().parents[1]
PBR = ROOT / "textures" / "pbr"
QA = ROOT / "qa" / "institutional_surface_pbr"
QA.mkdir(parents=True, exist_ok=True)
NAME = "precast_exposed_aggregate"
MAPS = ("basecolor", "normal", "roughness", "ao")


def stats(a: np.ndarray) -> dict[str, float]:
    return {
        "min": int(a.min()), "max": int(a.max()),
        "mean": round(float(a.mean()), 3), "stddev": round(float(a.std()), 3),
        "p05": round(float(np.percentile(a, 5)), 3),
        "p95": round(float(np.percentile(a, 95)), 3),
    }


def exact_seams(a: np.ndarray) -> tuple[bool, bool]:
    return bool(np.array_equal(a[:, 0], a[:, -1])), bool(np.array_equal(a[0], a[-1]))


def lit_preview(base: np.ndarray, normal: np.ndarray, rough: np.ndarray, ao: np.ndarray) -> Image.Image:
    b = base.astype(np.float32) / 255
    n = normal.astype(np.float32) / 255 * 2 - 1
    light = np.array([-.38, -.42, .82], np.float32)
    light /= np.linalg.norm(light)
    ndotl = np.clip((n * light).sum(-1), 0, 1)
    r = rough.astype(np.float32) / 255
    shaded = b * (.27 + .82 * ndotl)[..., None] * (ao[..., None] / 255)
    shaded += (np.power(ndotl, 5 + 70 * r) * (1 - r) * .55)[..., None]
    return Image.fromarray(np.clip(shaded * 255, 0, 255).astype(np.uint8), "RGB")


manifest = json.loads((PBR / "material_scale_manifest.json").read_text())
expected_scales = {
    NAME: (146.0, 146.0),
    "concrete_formed": (225.0, 225.0),
    "alu_oxidised": (200.0, 200.0),
}
report: dict = {
    "spec": {
        "dimensions": [2048, 2048],
        "format": "PNG",
        "normal_convention": "DirectX tangent-space; green-down",
        "new_material_tile_cm": [146.0, 146.0],
        "basecolor_policy": "pigment/material identity only; no baked lighting, AO or height shading",
    },
    "scale_manifest": {}, "maps": {},
}
passes: list[bool] = []
for material, expected in expected_scales.items():
    rec = manifest["materials"][material]
    actual = (float(rec["tile_width_cm"]), float(rec["tile_height_cm"]))
    ok = actual == expected and "application" in rec and "intended_use" in rec
    report["scale_manifest"][material] = {"actual_cm": list(actual), "expected_cm": list(expected), "pass": ok}
    passes.append(ok)

loaded: dict[str, np.ndarray] = {}
for map_name in MAPS:
    path = PBR / f"{NAME}_{map_name}.png"
    raw = Image.open(path)
    mode = "RGB" if map_name in ("basecolor", "normal") else "L"
    arr = np.asarray(raw.convert(mode))
    loaded[map_name] = arr
    lr, tb = exact_seams(arr)
    lum = (.2126 * arr[..., 0] + .7152 * arr[..., 1] + .0722 * arr[..., 2]) if arr.ndim == 3 else arr.astype(np.float32)
    s: dict[str, Any] = stats(lum)
    ok = raw.format == "PNG" and raw.mode == mode and raw.size == (2048, 2048) and lr and tb
    if map_name == "basecolor":
        quadrants = [lum[:1024, :1024].mean(), lum[:1024, 1024:].mean(), lum[1024:, :1024].mean(), lum[1024:, 1024:].mean()]
        s["quadrant_luminance_spread"] = round(float(max(quadrants) - min(quadrants)), 3)
        ok = ok and s["stddev"] >= 12 and s["quadrant_luminance_spread"] < 18
    elif map_name == "normal":
        channels = [stats(arr[..., i]) for i in range(3)]
        s["channels_rgb"] = channels
        ok = ok and channels[2]["mean"] > 175 and channels[0]["stddev"] > 3 and channels[1]["stddev"] > 3
    elif map_name == "roughness":
        s["p95_minus_p05"] = round(s["p95"] - s["p05"], 3)
        ok = ok and s["stddev"] >= 15 and s["p95_minus_p05"] >= 45
    elif map_name == "ao":
        s["p95_minus_p05"] = round(s["p95"] - s["p05"], 3)
        ok = ok and s["p95"] >= 245 and s["p95_minus_p05"] >= 35
    report["maps"][map_name] = {
        "path": str(path.relative_to(ROOT)), "mode": raw.mode, "format": raw.format,
        "size": list(raw.size), "exact_left_right": lr, "exact_top_bottom": tb,
        "bytes": path.stat().st_size, "statistics": s, "pass": bool(ok),
    }
    passes.append(bool(ok))

base, normal, rough, ao = (loaded[m] for m in MAPS)
base_lum = .2126 * base[..., 0] + .7152 * base[..., 1] + .0722 * base[..., 2]
report["base_ao_abs_correlation"] = round(abs(float(np.corrcoef(base_lum.ravel(), ao.ravel())[0, 1])), 4)
report["base_ao_independence_pass"] = report["base_ao_abs_correlation"] < .60
passes.append(report["base_ao_independence_pass"])

# Unit-test DirectX sign convention independently of the delivered texture.
ramp_y = np.sin(np.arange(2048, dtype=np.float32) * 2 * np.pi / 2048)
ramp = np.repeat(ramp_y[:, None], 2048, axis=1)
rn = normal_dx(ramp, 18)
report["directx_convention_unit_check"] = {
    "positive_image_y_slope_green": int(rn[0, 1024, 1]),
    "negative_image_y_slope_green": int(rn[1024, 1024, 1]),
    "pass": bool(rn[0, 1024, 1] > 127 and rn[1024, 1024, 1] < 127),
}
passes.append(report["directx_convention_unit_check"]["pass"])

# Visual artifacts: 2x2 base-color tiling, QA-only lit render, and map contact sheet.
thumb = Image.fromarray(base, "RGB").resize((512, 512), Image.Resampling.LANCZOS)
tiled = Image.new("RGB", (1024, 1024))
for x in (0, 512):
    for y in (0, 512):
        tiled.paste(thumb, (x, y))
tiled.save(QA / f"{NAME}_basecolor_2x2.png", optimize=True)
lit = lit_preview(base, normal, rough, ao)
lit.resize((1024, 1024), Image.Resampling.LANCZOS).save(QA / f"{NAME}_lit_preview.png", optimize=True)

font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
cell = 390
sheet = Image.new("RGB", (cell * 5, cell + 92), (21, 27, 25))
d = ImageDraw.Draw(sheet)
images = [Image.fromarray(base, "RGB"), Image.fromarray(normal, "RGB"), Image.fromarray(rough, "L").convert("RGB"), Image.fromarray(ao, "L").convert("RGB"), lit]
for i, (im, label) in enumerate(zip(images, ("BASE COLOR", "NORMAL DX", "ROUGHNESS", "AO", "QA-ONLY LIT"))):
    sheet.paste(im.resize((cell, cell), Image.Resampling.LANCZOS), (i * cell, 36))
    d.text((i * cell + 10, 9), label, font=font, fill=(232, 221, 195))
d.text((12, cell + 52), "EXPOSED-AGGREGATE PRECAST — 146 x 146 CM TILE — DIELECTRIC", font=font, fill=(238, 218, 174))
sheet.save(QA / f"{NAME}_contact_sheet.png", optimize=True)

report["pass"] = bool(all(passes))
(QA / f"{NAME}_report.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
raise SystemExit(0 if report["pass"] else 1)

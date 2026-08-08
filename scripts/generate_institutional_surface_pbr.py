#!/usr/bin/env python3
"""Generate VERDANT's exposed-aggregate architectural precast PBR set.

The 2048 px square represents 146 x 146 cm: one Rootstead precast bay wide.
Aggregate, matrix pores, pigment, roughness and AO share deterministic masks.
Panel joints, runoff, spalls and edge wear are deliberately not baked into this
repeatable face material; they must follow panel geometry or local masks.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

from generate_batch3_pbr import N, ao_from_height, normal_dx, periodic_noise, seal

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "textures" / "pbr"
QA = ROOT / "qa" / "institutional_surface_pbr"
NAME = "precast_exposed_aggregate"
TILE_CM = 146.0
SEED = 1964
OUT.mkdir(parents=True, exist_ok=True)
QA.mkdir(parents=True, exist_ok=True)


def add_wrapped_stone(
    field: np.ndarray, cx: int, cy: int, radius: float, value: float,
    aspect: float, angle: float, phase: float, scale: float = 1.0,
) -> None:
    """Max-composite an irregular rotated gravel grain into a toroidal field."""
    r = int(np.ceil(radius * max(aspect, 1.0 / aspect) * 1.25)) + 1
    xs = np.arange(cx - r, cx + r + 1)
    ys = np.arange(cy - r, cy + r + 1)
    xx, yy = np.meshgrid(xs, ys)
    dx, dy = xx - cx, yy - cy
    ca, sa = np.cos(angle), np.sin(angle)
    xr, yr = ca * dx + sa * dy, -sa * dx + ca * dy
    theta = np.arctan2(yr, xr)
    dist = np.sqrt((xr / aspect) ** 2 + (yr * aspect) ** 2) / (radius * scale)
    dist *= 1.0 + .16 * np.sin(3 * theta + phase) + .09 * np.sin(5 * theta - phase * .7)
    dome = np.sqrt(np.clip(1.0 - dist * dist, 0.0, 1.0)) * value
    np.maximum.at(field, (yy.ravel() % N, xx.ravel() % N), dome.ravel())


def aggregate_fields() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(SEED)
    relief = np.zeros((N, N), np.float32)
    identity = np.zeros((N, N), np.float32)
    family = np.zeros((N, N), np.float32)

    # 4,400 irregular 7-25 mm stones across a 1.46 m tile. Pixel radius is
    # derived from the explicit 2048/146 px-per-cm conversion.
    px_per_cm = N / TILE_CM
    for i in range(4400):
        cx, cy = int(rng.integers(0, N)), int(rng.integers(0, N))
        diameter_cm = float(np.clip(rng.lognormal(mean=np.log(1.30), sigma=.34), .70, 2.50))
        radius = diameter_cm * px_per_cm * .5
        proud = float(rng.uniform(.70, 1.0))
        aspect = float(rng.uniform(.72, 1.38))
        angle = float(rng.uniform(0, np.pi))
        phase = float(rng.uniform(0, 2 * np.pi))
        add_wrapped_stone(relief, cx, cy, radius, proud, aspect, angle, phase)
        add_wrapped_stone(identity, cx, cy, radius, float(rng.uniform(.55, 1.0)), aspect, angle, phase, .90)
        add_wrapped_stone(family, cx, cy, radius, float(rng.choice((.18, .42, .68, .94))), aspect, angle, phase, .84)
    return relief, identity, family


def save_rgb(suffix: str, array: np.ndarray) -> None:
    Image.fromarray(seal(np.clip(array, 0, 255).astype(np.uint8)), "RGB").save(
        OUT / f"{NAME}_{suffix}.png", optimize=True
    )


def save_l(suffix: str, array: np.ndarray) -> None:
    Image.fromarray(seal(np.clip(array, 0, 255).astype(np.uint8)), "L").save(
        OUT / f"{NAME}_{suffix}.png", optimize=True
    )


def generate() -> None:
    relief, identity, family = aggregate_fields()
    macro = periodic_noise(196401, ((31, .40), (83, .36), (221, .24)))
    fine = periodic_noise(196402, ((2, .22), (5, .34), (13, .29), (37, .15)))
    pores = np.clip((periodic_noise(196403, ((1, .44), (3, .36), (8, .20))) - .72) * 3.8, 0, 1)
    stone = relief > .06

    # Pigment only: matrix variation and lithology identity, never height shading.
    base = np.empty((N, N, 3), np.float32)
    base[:] = np.array((151, 145, 131), np.float32)
    base += (macro - .5)[..., None] * np.array((18, 16, 13), np.float32)
    base += (fine - .5)[..., None] * np.array((8, 7, 6), np.float32)
    base -= pores[..., None] * np.array((22, 21, 18), np.float32)

    # Restrained Mo-Sai-like warm gravel mix: limestone/cream, grey, umber and
    # occasional charcoal. It must read as architectural precast, not terrazzo.
    palettes = np.array([
        (181, 170, 145),
        (157, 151, 137),
        (130, 123, 108),
        (101, 98, 91),
        (77, 75, 70),
    ], np.float32)
    bins = np.digitize(family, (.28, .52, .76, .90))
    stone_color = palettes[bins]
    stone_color += (identity - .70)[..., None] * np.array((22, 19, 15), np.float32)
    base[stone] = stone_color[stone]

    # Aggregate sits proud of a sand/cement matrix. Pores recess; broad variation
    # is intentionally shallow so no directional lighting leaks into base color.
    height = .43 + .035 * (macro - .5) + .024 * (fine - .5) - .16 * pores
    height += .20 * relief
    height += .025 * relief * (fine - .5)

    matrix_rough = 184 + 35 * fine + 18 * macro + 30 * pores
    stone_rough = 122 + 38 * (1 - identity) + 22 * fine
    rough = np.where(stone, stone_rough, matrix_rough)
    ao = ao_from_height(height, .44)

    save_rgb("basecolor", base)
    save_rgb("normal", normal_dx(height, 13.0))
    save_l("roughness", rough)
    save_l("ao", ao)

    manifest = {
        "schema": 1,
        "units": "centimetres",
        "materials": {
            NAME: {
                "tile_width_cm": 146.0,
                "tile_height_cm": 146.0,
                "resolution": [2048, 2048],
                "normal_convention": "DirectX tangent-space, green-down",
                "metallic": 0,
                "intended_use": "architectural precast face; one Rootstead facade bay wide",
                "application": "WorldAlignedTexture/WorldAlignedNormal TextureSize=146 cm, or UV density 2048 px per 146 cm",
                "panel_note": "A 146 x 225 cm panel uses U=1.0 tile and V=1.541096 tiles. Keep joints/runoff/spalls in geometry, decals or local masks.",
                "aggregate_diameter_cm": [0.7, 2.5],
            },
            "concrete_formed": {
                "tile_width_cm": 225.0,
                "tile_height_cm": 225.0,
                "resolution": [2048, 2048],
                "normal_convention": "DirectX tangent-space, green-down",
                "metallic": 0,
                "intended_use": "board-marked in-situ plinth and construction junction",
                "application": "WorldAlignedTexture/WorldAlignedNormal TextureSize=225 cm",
                "authored_feature_scale": "board courses ~26.8 cm high; tie pattern ~63.3 x 53.6 cm",
            },
            "alu_oxidised": {
                "tile_width_cm": 200.0,
                "tile_height_cm": 200.0,
                "resolution": [2048, 2048],
                "normal_convention": "DirectX tangent-space, green-down",
                "metallic": 1,
                "intended_use": "weathered anodised aluminium vault tubes and nodes",
                "application": "WorldAlignedTexture/WorldAlignedNormal TextureSize=200 cm; ~20 cm tube width spans ~205 px",
                "wear_note": "Handled-edge bright wear is a local mask/decal, not uniformly baked into the tile.",
            },
        },
    }
    (OUT / "material_scale_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Generated {NAME} PBR at {TILE_CM:.0f} x {TILE_CM:.0f} cm per tile")


if __name__ == "__main__":
    generate()

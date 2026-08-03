#!/usr/bin/env python3
"""Generate aligned, seamless 2K PBR materials for VERDANT Batch 3.

Every material is built from shared periodic masks/height data. Base color is
material color only (never shaded from height/AO). Normals are tangent-space
DirectX convention: +image-Y slope is encoded as +green (green-down).
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "textures" / "pbr"
QA = ROOT / "qa" / "batch3_pbr"
OUT.mkdir(parents=True, exist_ok=True)
QA.mkdir(parents=True, exist_ok=True)
N = 2048
TAU = 2 * math.pi


def seal(a: np.ndarray) -> np.ndarray:
    """Duplicate first row/column at the far edges for exact PNG seams."""
    a[-1, ...] = a[0, ...]
    a[:, -1, ...] = a[:, 0, ...]
    return a


def norm01(a: np.ndarray, lo: float = 1.0, hi: float = 99.0) -> np.ndarray:
    q0, q1 = np.percentile(a, (lo, hi))
    return np.clip((a - q0) / max(float(q1 - q0), 1e-6), 0, 1).astype(np.float32)


def periodic_noise(seed: int, layers=((7, .35), (21, .30), (53, .22), (127, .13))) -> np.ndarray:
    """Rich periodic noise from wrapped Gaussian fields at specified scales."""
    rng = np.random.default_rng(seed)
    z = np.zeros((N, N), np.float32)
    for sigma, weight in layers:
        raw = rng.standard_normal((N, N), dtype=np.float32)
        layer = gaussian_filter(raw, sigma=sigma, mode="wrap")
        layer -= layer.mean()
        layer /= max(float(layer.std()), 1e-6)
        z += layer * weight
    return norm01(z)


def impulses(seed: int, count: int, sigma: float, amplitude: tuple[float, float] = (.5, 1.0)) -> np.ndarray:
    rng = np.random.default_rng(seed)
    a = np.zeros((N, N), np.float32)
    ys = rng.integers(0, N, count)
    xs = rng.integers(0, N, count)
    vals = rng.uniform(low=amplitude[0], high=amplitude[1], size=count).astype(np.float32)
    np.add.at(a, (ys, xs), vals)
    a = gaussian_filter(a, sigma=sigma, mode="wrap")
    return norm01(a, 0, 99.8)


def wrapped_lines(seed: int, count: int, horizontal=False, width=(2, 7), length=(70, 420)) -> np.ndarray:
    """Draw wandering crevice/streak lines on a torus."""
    rng = random.Random(seed)
    im = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(im)
    for _ in range(count):
        x, y = rng.randrange(N), rng.randrange(N)
        total = rng.randint(*length)
        pts: list[tuple[float, float]] = [(float(x), float(y))]
        steps = rng.randint(3, 8)
        for j in range(1, steps + 1):
            t = total * j / steps
            if horizontal:
                px, py = x + t, y + rng.uniform(-22, 22) + 8 * math.sin(j * 1.7)
            else:
                px, py = x + rng.uniform(-18, 18) + 7 * math.sin(j * 1.3), y + t
            pts.append((px, py))
        w = rng.randint(*width)
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                d.line([(px + ox, py + oy) for px, py in pts], fill=255, width=w, joint="curve")
    return np.asarray(im, dtype=np.float32) / 255.0


def circles_grid(spacing_x: int, spacing_y: int, radius: float, offset=(0, 0), wobble=0.0) -> tuple[np.ndarray, np.ndarray]:
    """Return dome-shaped circles and ring masks on a seamless grid."""
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    dome = np.zeros((N, N), np.float32)
    ring = np.zeros_like(dome)
    rows = range(-1, N // spacing_y + 2)
    cols = range(-1, N // spacing_x + 2)
    for row in rows:
        for col in cols:
            cx = col * spacing_x + offset[0] + wobble * math.sin(row * 1.91 + col)
            cy = row * spacing_y + offset[1] + wobble * math.sin(col * 1.37)
            dx = np.minimum(np.abs(xx - cx), N - np.abs(xx - cx))
            dy = np.minimum(np.abs(yy - cy), N - np.abs(yy - cy))
            r = np.sqrt(dx * dx + dy * dy)
            dome = np.maximum(dome, np.sqrt(np.clip(1 - (r / radius) ** 2, 0, 1)))
            ring = np.maximum(ring, np.exp(-((r - radius * 1.35) / (radius * .20)) ** 2))
    return dome, ring


def colorize(base: tuple[float, float, float], terms: list[tuple[np.ndarray, tuple[float, float, float]]]) -> np.ndarray:
    arr = np.empty((N, N, 3), np.float32)
    arr[:] = np.array(base, np.float32)
    for mask, delta in terms:
        arr += mask[..., None] * np.array(delta, np.float32)
    return np.clip(arr, 0, 255).astype(np.uint8)


def normal_dx(height: np.ndarray, strength: float) -> np.ndarray:
    """Tangent normal, DirectX green-down: n = (-dH/dx, +dH/dy, 1)."""
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * strength
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * strength
    nx, ny, nz = -dx, dy, np.ones_like(height)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    rgb = np.stack(((nx * inv * .5 + .5), (ny * inv * .5 + .5), (nz * inv * .5 + .5)), axis=-1)
    return np.clip(rgb * 255, 0, 255).astype(np.uint8)


def ao_from_height(height: np.ndarray, amount=.75) -> np.ndarray:
    small = gaussian_filter(height, 7, mode="wrap")
    broad = gaussian_filter(height, 28, mode="wrap")
    cavity = np.maximum(small - height, 0) + .65 * np.maximum(broad - height, 0)
    cavity = norm01(cavity, 10, 99.5)
    return np.clip(255 * (1 - amount * cavity), 0, 255).astype(np.uint8)


def save_rgb(name: str, suffix: str, a: np.ndarray) -> None:
    Image.fromarray(seal(a.copy()), "RGB").save(OUT / f"{name}_{suffix}.png", optimize=True)


def save_l(name: str, suffix: str, a: np.ndarray) -> None:
    Image.fromarray(seal(a.copy()), "L").save(OUT / f"{name}_{suffix}.png", optimize=True)


def save_set(name: str, base: np.ndarray, height: np.ndarray, rough: np.ndarray, ao_amount=.75, normal_strength=18.0, opacity: np.ndarray | None = None) -> None:
    save_rgb(name, "basecolor", base)
    save_rgb(name, "normal", normal_dx(height, normal_strength))
    save_l(name, "roughness", np.clip(rough, 0, 255).astype(np.uint8))
    save_l(name, "ao", ao_from_height(height, ao_amount))
    if opacity is not None:
        save_l(name, "opacity", np.clip(opacity, 0, 255).astype(np.uint8))


def soil_terrace() -> None:
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    macro = periodic_noise(3101, ((19, .38), (51, .34), (131, .28)))
    crumb = periodic_noise(3102, ((2, .25), (5, .32), (12, .28), (29, .15)))
    warp = 14 * np.sin(TAU * yy / N * 3 + .4) + 7 * np.sin(TAU * yy / N * 7 + 1.6) + (macro - .5) * 14
    phase = TAU * (xx + warp) / 188
    ridge = ((1 + np.cos(phase)) * .5) ** 1.35
    trough = 1 - ridge
    clod = np.clip((crumb - .47) * 2.2, 0, 1) * (.35 + .65 * ridge)
    pebbles = impulses(3103, 900, 3.2) ** 2
    height = .10 + .64 * ridge + .26 * clod + .10 * pebbles + .05 * (macro - .5)
    # Natural pigment/moisture variation only; no height-derived lighting.
    damp = np.clip(.58 * macro + .42 * periodic_noise(3104, ((11, .4), (43, .35), (103, .25))), 0, 1)
    base = colorize((35, 25, 19), [
        (damp - .5, (20, 14, 9)),
        (crumb - .5, (14, 10, 7)),
        (trough * (.3 + .7 * damp), (-8, -6, -4)),
        (pebbles, (9, 7, 5)),
    ])
    # Sparse sprouts share alignment without affecting soil shading.
    sprout_pts = np.zeros((N, N), np.float32)
    rng = np.random.default_rng(3105)
    sprout_pts[rng.integers(0, N, 36), rng.integers(0, N, 36)] = 1
    sprouts = gaussian_filter(sprout_pts, (3, 10), mode="wrap")
    sprouts = norm01(sprouts, 0, 99.98)
    green = sprouts > .20
    base[green] = np.stack((48 + 30 * sprouts[green], 76 + 44 * sprouts[green], 35 + 24 * sprouts[green]), axis=-1).astype(np.uint8)
    height += sprouts * .08
    rough = 102 + 78 * clod + 35 * crumb + 18 * (1 - damp) - 28 * trough * damp + 22 * pebbles
    save_set("soil_terrace", base, height, rough, ao_amount=.82, normal_strength=25)


def steel_rusted_beam() -> None:
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    macro = periodic_noise(3201, ((17, .34), (47, .35), (113, .31)))
    fine = periodic_noise(3202, ((2, .18), (6, .34), (15, .31), (37, .17)))
    blooms = impulses(3203, 145, 48)
    flakes = np.clip(norm01(.62 * macro + .38 * fine, 18, 86) - .46, 0, 1) * 1.85
    streak_seed = impulses(3204, 95, 13)
    streaks = np.zeros_like(streak_seed)
    for shift in range(0, 390, 13):
        streaks += np.roll(streak_seed, shift, axis=0) * math.exp(-shift / 170)
    streaks = norm01(streaks, 15, 99.5)
    rust = np.clip(.72 * blooms + .58 * flakes + .65 * streaks - .24, 0, 1)
    pitting = np.clip((fine - .60) * 2.8, 0, 1) * rust
    rivets, rust_rings = circles_grid(512, 286, 27, offset=(126, 94), wobble=8)
    seam = np.exp(-((np.mod(xx + 32, 512) - 256) / 8) ** 2)
    chalk = np.clip((fine - .35) * (1 - rust), 0, 1)
    # Desaturated Eden-Prime turquoise paint; hue/masks only, no relief shading.
    base = colorize((89, 126, 121), [
        (macro - .5, (18, 17, 14)),
        (chalk, (34, 35, 29)),
        (rust, (105, -68, -84)),
        (rust * blooms, (39, 2, -7)),
        (pitting, (-45, -25, -17)),
        (rust_rings * (.15 + .85 * rust), (78, -39, -54)),
        (rivets * (1 - rust), (-6, -3, -1)),
    ])
    height = .50 + .055 * (fine - .5) + .10 * (1 - rust) * flakes - .18 * pitting - .08 * seam + .44 * rivets
    rough = 105 + 58 * chalk + 102 * rust + 55 * pitting - 76 * rivets + 32 * fine + 27 * streaks
    save_set("steel_rusted_beam", base, height, rough, ao_amount=.70, normal_strength=30)


def concrete_formed() -> None:
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    broad = periodic_noise(3301, ((29, .45), (79, .35), (181, .20)))
    grain = periodic_noise(3302, ((3, .18), (9, .31), (25, .32), (61, .19)))
    board_h = 244
    local_y = np.mod(yy + 27, board_h)
    seam = np.exp(-((local_y - 3) / 5) ** 2) + .55 * np.exp(-((local_y - board_h + 5) / 7) ** 2)
    wood = .5 + .5 * np.sin(TAU * xx / 215 + 1.8 * np.sin(TAU * xx / 611) + (yy // board_h) * 1.7)
    wood *= .35 + .65 * grain
    holes, hole_rings = circles_grid(576, 488, 21, offset=(178, 120), wobble=10)
    cracks = gaussian_filter(wrapped_lines(3303, 37, horizontal=False, width=(1, 3), length=(100, 520)), .8, mode="wrap")
    water_sources = impulses(3304, 55, 20)
    water = np.zeros_like(water_sources)
    for shift in range(0, 560, 20):
        water += np.roll(water_sources, shift, axis=0) * math.exp(-shift / 260)
    water = norm01(water, 30, 99.6)
    moss = np.clip(.75 * seam + .45 * periodic_noise(3305, ((6, .3), (19, .4), (53, .3))) - .57, 0, 1)
    base = colorize((143, 141, 129), [
        (broad - .5, (23, 22, 18)),
        (grain - .5, (11, 10, 8)),
        (water, (-34, -28, -23)),
        (moss, (-53, -17, -48)),
        (cracks, (-34, -32, -28)),
        (holes, (-43, -42, -37)),
        (hole_rings, (12, 8, 3)),
    ])
    board_steps = ((yy // board_h) % 3).astype(np.float32) / 3
    height = .50 + .035 * (broad - .5) + .045 * (wood - .5) + .025 * (board_steps - .5) - .25 * seam - .38 * holes - .22 * cracks + .035 * moss
    rough = 145 + 72 * grain + 84 * moss - 82 * water + 58 * seam + 38 * broad
    save_set("concrete_formed", base, height, rough, ao_amount=.76, normal_strength=27)


def glass_dome_grime() -> None:
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    fine = periodic_noise(3401, ((3, .18), (11, .34), (31, .31), (83, .17)))
    haze = periodic_noise(3402, ((25, .36), (73, .38), (167, .26)))
    # Distance to periodically repeated panel corners; seamlessly tiles corner blooms.
    dx = np.minimum(xx, N - xx)
    dy = np.minimum(yy, N - yy)
    corner = np.exp(-((np.sqrt(dx * dx + dy * dy)) / 310) ** 1.6)
    algae = np.clip(corner * (.62 + .72 * haze) + .24 * impulses(3403, 90, 34) - .30, 0, 1)
    run_sources = impulses(3404, 80, 10)
    runs = np.zeros_like(run_sources)
    for shift in range(0, 720, 12):
        runs += np.roll(run_sources, shift, axis=0) * math.exp(-shift / 330)
    runs = norm01(runs, 55, 99.7)
    minerals = np.clip((fine - .58) * 2.8, 0, 1) * (.35 + .65 * runs)
    dust = np.clip(.58 * haze + .42 * fine - .48, 0, 1)
    grime = np.clip(.58 * algae + .34 * runs + .30 * minerals + .22 * dust, 0, 1)
    base = colorize((207, 224, 211), [
        (haze - .5, (8, 9, 5)),
        (algae, (-81, -56, -69)),
        (runs, (-22, -17, -18)),
        (minerals, (26, 20, 4)),
        (dust, (-18, -13, -9)),
    ])
    # Glass remains almost flat; deposits provide subtle actual relief.
    height = .50 + .030 * dust + .065 * algae + .045 * minerals + .018 * runs
    rough = 32 + 126 * grime + 70 * minerals + 34 * dust + 18 * fine
    opacity = 255 - 205 * np.clip(grime ** .82, 0, 1)  # white clear, dark heavy grime per brief
    save_set("glass_dome_grime", base, height, rough, ao_amount=.34, normal_strength=32, opacity=opacity)


def main() -> None:
    soil_terrace()
    steel_rusted_beam()
    concrete_formed()
    glass_dome_grime()
    print(f"Generated 17 aligned PBR maps in {OUT}")


if __name__ == "__main__":
    main()

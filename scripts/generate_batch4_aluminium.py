#!/usr/bin/env python3
"""Generate the seamless 2K aluminium PBR set for VERDANT Batch 4.

WHY THIS SET EXISTS
    Eden Prime's envelope is a 466 m triangulated lamella vault whose frame is
    ALUMINIUM. Batch 3 shipped concrete, glass grime, soil and `steel_rusted_beam`
    — none of which is correct for it. Putting the rusted-steel set on the vault
    would be the single most wrong material choice available, because the whole
    point of the frame is that it does NOT rust.

    Reference: HABS MO-1135-L photographs 6 and 7 (Climatron: aluminium tubes in
    compression, rods in tension, circular nodes, separately suspended glazing),
    and Hermes' sheet 04 decay logic:

        "Aluminium oxidizes dull grey-white rather than orange; reserve rust for
         dissimilar-steel screws, brackets, and contaminated runoff."

WHAT ALUMINIUM ACTUALLY DOES, AND WHAT THAT MEANS FOR THE MAPS
    It self-passivates. A thin oxide forms immediately and then essentially stops,
    so sixty years of neglect gives chalky bloom and pitting rather than the
    progressive scale-and-flake of steel. Consequences:

    basecolor  Near-neutral, high value, LOW contrast. Aluminium's colour range is
               narrow — the interest is in roughness, not hue. Any strong colour
               variation here will read as painted metal, which is wrong.
    roughness  This is where the material identity lives. Chalked oxide is rough;
               the flanks of extrusions and anywhere hands or weather have
               polished it are smoother. Deliberately wide range, not a flat grey.
    normal     Mostly ISOTROPIC pitting, with only a hint of extrusion die lines.
               Real extruded tube does show strong die lines, but the meshes are
               unwrapped with smart UV projection, so island orientation is
               arbitrary — a strongly directional texture would run along the tube
               on some faces and around it on others. Physical accuracy loses to
               UV reality here, deliberately.
    ao         From height only, gentle — there are no deep crevices in a tube.

FASTENER RUST IS NOT IN THIS SET, ON PURPOSE
    Orange belongs only where dissimilar steel touches the aluminium, and a tiling
    texture cannot know where the bolts are. Doing it here would smear rust
    uniformly over surfaces that should stay clean. It needs either a second
    material slot on the fastener geometry or decals placed at the joints.

Conventions follow batch 3: built from wrapped periodic fields on a torus, edges
sealed for exact PNG seams, normals tangent-space DirectX (green-down).
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "textures" / "pbr"
QA = ROOT / "qa" / "batch4_aluminium"
OUT.mkdir(parents=True, exist_ok=True)
QA.mkdir(parents=True, exist_ok=True)
N = 2048


def seal(a: np.ndarray) -> np.ndarray:
    a[-1, ...] = a[0, ...]
    a[:, -1, ...] = a[:, 0, ...]
    return a


def norm01(a: np.ndarray, lo: float = 1.0, hi: float = 99.0) -> np.ndarray:
    q0, q1 = np.percentile(a, (lo, hi))
    return np.clip((a - q0) / max(float(q1 - q0), 1e-6), 0, 1).astype(np.float32)


def periodic_noise(seed: int, layers) -> np.ndarray:
    rng = np.random.default_rng(seed)
    z = np.zeros((N, N), np.float32)
    for sigma, weight in layers:
        raw = rng.standard_normal((N, N), dtype=np.float32)
        layer = gaussian_filter(raw, sigma=sigma, mode="wrap")
        layer -= layer.mean()
        layer /= max(float(layer.std()), 1e-6)
        z += layer * weight
    return norm01(z)


def pits(seed: int, count: int, sigma: float) -> np.ndarray:
    """Corrosion pitting — small, sharp, isotropic, sparse."""
    rng = np.random.default_rng(seed)
    a = np.zeros((N, N), np.float32)
    ys = rng.integers(0, N, count)
    xs = rng.integers(0, N, count)
    np.add.at(a, (ys, xs), rng.uniform(0.55, 1.0, count).astype(np.float32))
    return norm01(gaussian_filter(a, sigma=sigma, mode="wrap"), 0, 99.7)


def die_lines(seed: int, frequency: int, jitter: float) -> np.ndarray:
    """Longitudinal extrusion die lines: fine, parallel, slightly irregular.

    Anisotropic on purpose — an extruded tube is drawn through a die, so its
    surface has direction. Isotropic noise alone reads as cast, not extruded.
    """
    rng = np.random.default_rng(seed)
    xx = np.mgrid[0:N, 0:N][1].astype(np.float32)
    wander = gaussian_filter(rng.standard_normal((N, N), dtype=np.float32),
                             sigma=(90, 6), mode="wrap")
    wander = wander / max(float(wander.std()), 1e-6)
    phase = xx / N * frequency * 2 * math.pi + wander * jitter
    lines = 0.5 + 0.5 * np.sin(phase)
    strength = norm01(gaussian_filter(
        rng.standard_normal((N, N), dtype=np.float32), sigma=(70, 25), mode="wrap"))
    return norm01(lines * (0.35 + 0.65 * strength))


def normal_dx(height: np.ndarray, strength: float) -> np.ndarray:
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * strength
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * strength
    nx, ny, nz = -dx, dy, np.ones_like(height)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    rgb = np.stack(((nx * inv * .5 + .5), (ny * inv * .5 + .5), (nz * inv * .5 + .5)), -1)
    return np.clip(rgb * 255, 0, 255).astype(np.uint8)


def ao_from_height(height: np.ndarray, amount: float) -> np.ndarray:
    small = gaussian_filter(height, 7, mode="wrap")
    broad = gaussian_filter(height, 28, mode="wrap")
    cavity = np.maximum(small - height, 0) + .65 * np.maximum(broad - height, 0)
    return np.clip(255 * (1 - amount * norm01(cavity, 10, 99.5)), 0, 255).astype(np.uint8)


def save_rgb(name, suffix, a):
    Image.fromarray(seal(a.copy()), "RGB").save(OUT / f"{name}_{suffix}.png", optimize=True)


def save_l(name, suffix, a):
    Image.fromarray(seal(a.copy()), "L").save(OUT / f"{name}_{suffix}.png", optimize=True)


def aluminium_oxidised() -> None:
    """v7 — Hermes' texture design, calibrated against the actual level.

    TWO SETS COLLIDED HERE. Hermes built this file to a brief while I was
    iterating my own version of the same maps in engine; we both pushed to
    alu_oxidised_*. Rather than pick a winner, this keeps what each side had
    evidence for.

    KEPT FROM HERMES, because his texture design is better than mine was:
      * pits(count=620) instead of my 4,500. Real pitting is a scatter of
        isolated corrosion events, not an all-over aggregate. His note that a
        dense field "read as cast stone at arm's length" is the same diagnosis I
        reached from the other direction, and his fix is the cleaner one.
      * the `polish` field — broad smooth flanks (sigma 95/260) interrupting the
        chalk bloom. I chased the same effect by stretching the triplanar
        projection from 2 m to 5.2 m, which coarsens the pit scale as a side
        effect. Doing it inside the texture is strictly better; the projection
        can go back to a sane physical scale later if we want.
      * `broad` low-frequency variation, the shallow height amplitudes, and the
        much stronger AO (0.45 vs my 0.07). Sparse pits that read dark at their
        centres are what sells corrosion up close, and my AO was too timid.

    CHANGED, because these three were tuned in the level and Hermes never saw it
    there — all three are the direct cause of a "frosted ice" read that Mark
    rejected on 5 Aug:

      1. ROUGHNESS FLOOR 62 -> 105 (0.24 -> 0.41). Under a glass roof the sky is
         the dominant light, so any patch below about 0.4 turns into a mirror for
         it and the whole frame goes pale blue. My own v4 sat at 0.17 and failed
         exactly this way. The SHAPE of Hermes' roughness is kept — chalk up,
         polish down, pits roughest — only the band is lifted.
      2. BASE COLOUR was 167/170/171, i.e. faintly COOL (B > R). For a metal this
         is F0, and it is the one thing that can counteract a blue environment.
         Now 190/188/185, warm-neutral, lifting to ~208 under chalk. Oxidised
         aluminium's F0 is about 205 sRGB (245 bare); cool-and-dark compounds the
         sky instead of resisting it.
      3. METALLIC 235 -> 255. The passivation layer is nanometres thick and does
         not make aluminium a dielectric. I already made the mistake of dropping
         metallic to compensate for a gloss problem and got matte white ceramic
         for it.

    Verified in engine at PyTools/vshot.py preset frame_close before shipping.
    """
    name = "alu_oxidised"

    lines = die_lines(41, frequency=150, jitter=.55)
    # Pits are isolated corrosion events, not an all-over aggregate.  The prior
    # placeholder used 34,000 impulses and read as cast stone at arm's length.
    pit = pits(42, count=620, sigma=2.35)
    bloom = periodic_noise(43, ((18, .30), (48, .34), (110, .24), (260, .12)))
    broad = periodic_noise(44, ((150, .58), (360, .42)))
    polish = periodic_noise(46, ((95, .62), (260, .38)))

    # ---- height: die lines are shallow, pits are the real relief
    height = (0.018 * (lines - .5) + 0.045 * (bloom - .5)
              + 0.020 * (broad - .5)) - 0.24 * pit

    # ---- base colour: narrow, near-neutral. Chalk lifts value and desaturates;
    # pitting darkens slightly and goes very faintly warm-grey, never orange.
    base = np.empty((N, N, 3), np.float32)
    # v7: was (167, 170, 171) — faintly cool, which compounds the blue sky in a
    # glass building. Warm-neutral and brighter; this is F0, not diffuse albedo.
    base[:] = np.array((190.0, 188.0, 185.0), np.float32)
    chalk = norm01(bloom * 0.7 + broad * 0.3)
    base += chalk[..., None] * np.array((18.0, 18.0, 17.0), np.float32)
    base += (lines - 0.5)[..., None] * np.array((1.2, 1.2, 1.3), np.float32)
    base -= pit[..., None] * np.array((8.0, 8.0, 7.0), np.float32)
    base = np.clip(base, 0, 255).astype(np.uint8)

    # ---- roughness: the load-bearing map. Chalked oxide rough, polished flanks
    # smooth, pits roughest of all. Wide range on purpose.
    # Broad polished flanks interrupt chalk bloom.  Even the matte end stays
    # below fully rough so grazing highlights still identify bare metal.
    # v7: same shape, band lifted off the glossy end. A floor of 62 (0.24) is a
    # semi-polished finish and mirrors the sky dome; 105 (0.41) is chalked oxide.
    rough = 122.0 + 92.0 * chalk - 34.0 * polish - 9.0 * (lines - .5) + 24.0 * pit
    rough += 13.0 * (periodic_noise(45, ((34, .58), (105, .42))) - 0.5)
    rough = np.clip(rough, 105, 214)

    save_rgb(name, "basecolor", base)
    save_rgb(name, "normal", normal_dx(height, 8.0))
    save_l(name, "roughness", rough.astype(np.uint8))
    save_l(name, "ao", ao_from_height(height, 0.45))

    # metallic is uniform for bare metal, but shipped so the material graph can
    # bind a texture rather than a constant and stay consistent with other sets.
    # v7: 235 -> 255. Aluminium is a metal; the oxide film does not change that.
    save_l(name, "metallic", np.full((N, N), 255, np.uint8))

    # ---- QA: 2x2 tile so seams are visible at a glance
    tile = Image.fromarray(seal(base.copy()), "RGB")
    sheet = Image.new("RGB", (N, N))
    half = tile.resize((N // 2, N // 2), Image.LANCZOS)
    for ox in (0, N // 2):
        for oy in (0, N // 2):
            sheet.paste(half, (ox, oy))
    sheet.save(QA / f"{name}_2x2_preview.png", optimize=True)

    r = np.asarray(Image.open(OUT / f"{name}_roughness.png"), np.float32)
    print("%s: roughness min/mean/max = %.0f / %.0f / %.0f (want a WIDE range)"
          % (name, r.min(), r.mean(), r.max()))
    b = np.asarray(Image.open(OUT / f"{name}_basecolor.png"), np.float32)
    print("%s: basecolor per-channel spread = %.1f (want NARROW, this is bare metal)"
          % (name, float(b.reshape(-1, 3).std(axis=0).mean())))
    for suffix in ("basecolor", "normal", "roughness", "ao", "metallic"):
        a = np.asarray(Image.open(OUT / f"{name}_{suffix}.png"))
        lr = int(np.abs(a[:, 0].astype(int) - a[:, -1].astype(int)).max())
        tb = int(np.abs(a[0, :].astype(int) - a[-1, :].astype(int)).max())
        print("  %-10s %s  seam L/R=%d  T/B=%d" % (suffix, a.shape, lr, tb))


if __name__ == "__main__":
    aluminium_oxidised()
    print("done ->", OUT)

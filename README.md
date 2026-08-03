# VERDANT Assets

Source-controlled 2D art and texture assets for **VERDANT**, a first-person
narrative game set in the decaying atomic-age greenhouse city of Eden Prime.

## Batch 1

### Seamless base-color textures

All texture exports are 2048×2048 RGB PNGs, top-down/orthographic in visual
language, and contain no baked directional light, highlights, shadows,
vignettes, text, or logos.

- `textures/soil_terrace_2048.png`
- `textures/concrete_formed_2048.png`
- `textures/steel_pastel_turquoise_2048.png`
- `textures/stucco_cream_2048.png`
- `textures/overgrowth_vine_2048.png`

### Cultivation propaganda posters

All poster exports are 1024×1536 RGB PNGs with programmatically typeset slogan
text (not diffusion-generated lettering).

- `posters/garden_loved_1024x1536.png`
- `posters/wild_branch_1024x1536.png`
- `posters/pruning_direction_1024x1536.png`

## Reproduction and QA

```bash
python3 scripts/generate_batch1.py
python3 scripts/verify_batch1.py
```

The texture recipe builds every stochastic field from periodic Fourier
functions on a torus and draws edge-crossing details on wrapped neighbor
copies. Export then makes opposite boundary pixels exactly equal. QA verifies:

- exact 2048×2048 / 1024×1536 dimensions;
- RGB PNG mode;
- pixel-identical left/right and top/bottom texture boundaries;
- near-edge derivative continuity metrics;
- broad quadrant-luminance spread as a directional-lighting guard;
- 2×2 tiled previews under `qa/` for visual seam inspection.

`qa/batch1_report.json` is the machine-readable verification report.

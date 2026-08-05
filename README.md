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

## Batch 2

### Corrected and new seamless base-color textures

All texture exports are 2048×2048 RGB PNGs. They are generated on a torus,
export with pixel-identical opposite edges, and use flat chromatic material
variation rather than baked directional highlights or shadows.

- `textures/soil_terrace_2048.png` (corrected dark, wet worked earth)
- `textures/rust_corrugated_2048.png`
- `textures/terrazzo_institutional_2048.png`
- `textures/dome_glass_dirty_2048.png`
- `textures/concrete_rubble_2048.png`

### Alpha-cutout foliage cards

All cutouts are 1024×1024 RGBA PNGs with real transparent alpha, centered
silhouettes, clean padding, and alpha-correct downsampling to avoid white or
dark edge halos.

- `cutouts/vine_hanging_1024.png`
- `cutouts/vine_wall_patch_1024.png`
- `cutouts/weed_clump_1024.png`
- `cutouts/leaf_debris_1024.png`

Batch 2 reproduction and QA:

```bash
python3 scripts/generate_batch2.py
python3 scripts/verify_batch2.py
```

`qa/batch2_report.json` records seam, lighting-spread, alpha-range, transparent
RGB, content-padding, and format checks. The `batch2_*_contact_sheet.png` files
and individual 2×2/checkerboard previews support visual review.

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

## Structural modelling references

Lore-independent close studies for rebuilding the 1950s greenhouse envelope.
These are design-intent reference sheets rather than fabrication drawings; each
uses an evenly lit three-quarter view, numbered construction notes, and explicit
material/surface callouts.

- `references/structure/dome_frame_joinery_reference_2400x1800.png`
- `references/structure/greenhouse_glazing_detail_reference_2400x1800.png`

Regenerate both sheets with:

```bash
python3 scripts/generate_structure_reference_sheets.py
```

## Atomic-research references

Source-grounded concept sheets for Eden Prime’s reconciled research-station canon:

- `references/atomic_research/gamma_garden_damage_gradient_wide_2400x1600.png`
- `references/atomic_research/climatron_hex_glazing_decay_reference_2400x1600.png`
- `references/atomic_research/SOURCES.md` (verified history versus VERDANT interpretation)

Regenerate both images with:

```bash
python3 scripts/generate_atomic_research_references.py
```

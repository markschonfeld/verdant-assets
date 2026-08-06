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

## Vault materials and engineered growth

The vault-frame and glazing PBR maps are 2048×2048, aligned, and exact-edge
seamless for triplanar/world-aligned projection. Normals use Unreal's DirectX
(green-down) convention. Base color contains no baked lighting or AO.

- `textures/pbr/alu_oxidised_{basecolor,normal,roughness,ao}.png`
- `textures/pbr/glaze_acrylic_original_{basecolor,normal,roughness,ao,opacity}.png`
- `textures/pbr/glaze_glass_repair_{basecolor,normal,roughness,ao,opacity}.png`

Glazing opacity follows the existing `glass_dome_grime` convention: white is
clear pane and dark values mark heavier grime. The two eras are intentionally
distinct: warm/cloudy/crazed original acrylic versus clearer, sharper,
green-edged laminated repairs.

The replacement growth cards are 1024×1024 RGBA PNGs. They follow structure or
a directional stimulus instead of hanging like generic ivy:

- `cutouts/growth_tube_cling_1024.png`
- `cutouts/growth_joint_mass_1024.png`
- `cutouts/growth_creeping_mat_1024.png`
- `cutouts/growth_reaching_1024.png`

Regenerate and verify this delivery with:

```bash
python3 scripts/generate_batch4_aluminium.py
python3 scripts/generate_vault_glazing_growth.py
python3 scripts/verify_vault_materials_growth.py
```

The machine report and visual contact sheets are under
`qa/vault_materials_growth/`; the focused aluminium sheet remains under
`qa/batch4_aluminium/`.

## Authored prop geometry

Source OBJ meshes use Unreal centimetres at 1:1, Z-up, and bottom-centre pivots.
Generators are committed beside their outputs; imported actors must remain at
uniform scale `1.0`.

The first prop family replaces the two Engine cylinders used for the Eden Prime
landmark with a 13.10 m atomic-age environmental-research pylon:

- `SourceMesh/props/VD_Spire.obj`
- `SourceMesh/props/VD_SpireBase.obj`
- `references/props/SPIRE_LANDMARK_HANDOFF.md`

Regenerate and verify with:

```bash
python3 scripts/generate_spire_landmark.py
python3 scripts/verify_spire_landmark.py
```

Machine topology/bounds reports and the dimensioned orthographic preview are
under `qa/spire_landmark/`.

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

- `references/structure/sealed_steel_infrastructure_joint_reference_2400x1800.png`
  (tunnel, blast-door, and freight-lock steel; not the aluminium vault)
- `references/structure/greenhouse_glazing_detail_reference_2400x1800.png`

Regenerate both sheets with:

```bash
python3 scripts/generate_structure_reference_sheets.py
```

## Climber modelling references

Species-specific design-intent sheets for the three-sided blast-door trellis.
Each sheet shows trellis grip, bearing thickening, one-bay bridging, the combined
corner knot/hanging skirt, a fixed production helix, and the story-directed
transition toward doorway warmth.

- `references/botanical/solandra_maxima_trellis_reference_2400x1800.png`
- `references/botanical/aristolochia_dutchmans_pipe_trellis_reference_2400x1800.png`
- `references/botanical/climber_stem_bark_surface_reference_2400x1800.png`
  (young-to-mature stem progression, relative bearing diameters, node/bud
  treatment, compressed contact faces, bark grain, and surface response)
- `references/botanical/climber_branching_architecture_reference_2400x1800.png`
  (axillary branching, primary/secondary/tertiary hierarchy, parallel and
  crossing runs, multiple leaders, mature two-species canopy, and flower-density
  distinction)
- `references/botanical/CLIMBER_BRANCHING_PHOTO_REFERENCE.md`
  (linked, attributed whole-habit photographs plus a procedural brief; external
  photographs are not copied into this repository)
- `references/botanical/vine_weight_wind_bloom_reference_2400x1800.png`
  (support-state curves, branch-order sag, coherent wind weights, doorway
  clearance, and production bloom targets)
- `references/botanical/VINE_GROWTH_DYNAMICS_CORRECTION_BRIEF.md`
  (screenshot diagnosis, gravity/support algorithm, wind hierarchy, flower
  placement, implementation gates, and next-pass acceptance test)
- `references/botanical/climber_flower_scale_reference_2400x1800.png`
- `references/botanical/CLIMBER_FLOWER_SCALE_REFERENCE.md`
  (source-grounded flower-body dimensions, same-scale leaf comparison, and exact
  Unreal transforms for the committed alpha cards)
- `references/botanical/SOURCES.md` (public botanical facts vs VERDANT interpretation)

Flat-on alpha assets are 1024×1024 RGBA PNGs with true transparent alpha and
premultiplied-alpha downsampling:

- `cutouts/solandra_maxima_leaf_flat_1024.png`
- `cutouts/aristolochia_leaf_flat_1024.png`
- `cutouts/aristolochia_pipe_flower_1024.png`
- `cutouts/solandra_maxima_flower_open_1024.png`
- `cutouts/solandra_maxima_flower_bud_1024.png`

Regenerate and verify with:

```bash
python3 scripts/generate_climber_reference_sheets.py
python3 scripts/generate_climber_branching_reference.py
python3 scripts/generate_vine_dynamics_reference.py
python3 scripts/generate_climber_flower_scale_reference.py
python3 scripts/annotate_vine_growth_review.py
python3 scripts/verify_climber_reference_sheets.py
```

QA output is under `qa/climber_references/` and
`qa/vine_growth_review_2026-08-06/`.

### Mature stem bark PBR

The two mature-bark materials remain separate because their relief language is
structurally different: heavier ropey Solandra cork versus finer, shallow-split
Aristolochia bark. Each set contains aligned, seamless 2048×2048 base color,
DirectX normal, roughness, and AO maps:

- `textures/pbr/bark_solandra_mature_{basecolor,normal,roughness,ao}.png`
- `textures/pbr/bark_aristolochia_mature_{basecolor,normal,roughness,ao}.png`

Image Y/V follows the stem axis; X/U wraps the circumference. Bark is dielectric
(`Metallic = 0`). Bearing flattening and contact polish are intentionally absent
from the repeating textures and should come from mesh shape plus a local material
mask. Base color contains pigment variation only, without baked lighting or AO.

Regenerate and verify with:

```bash
python3 scripts/generate_climber_bark_pbr.py
python3 scripts/verify_climber_bark_pbr.py
```

QA maps, 2×2 seam previews, lit previews, the contact sheet, and the machine
report are under `qa/climber_bark_pbr/`.

### Improvised seal-plate sheet PBR

`seal_plate_sheet_*` is a separate unpainted mill/light-galvanised material for
later sheets fixed over failed gable panes. It deliberately shares no pigment or
wear field with the painted blast door or trellis:

- `textures/pbr/seal_plate_sheet_basecolor.png`
- `textures/pbr/seal_plate_sheet_normal.png`
- `textures/pbr/seal_plate_sheet_roughness.png`
- `textures/pbr/seal_plate_sheet_ao.png`

The set is seamless 2048×2048, uses DirectX tangent normals (green-down), and
expects `Metallic = 1`. Edge dimple rows require pane-local 0–1 UVs. Under
world/triplanar projection, use the bulk sheet maps but place edge fasteners from
pane barycentrics or geometry instead.

```bash
python3 scripts/generate_seal_plate_sheet_pbr.py
python3 scripts/verify_seal_plate_sheet_pbr.py
```

QA previews and the machine report are under `qa/seal_plate_sheet/`.

## Environment concept references

The west blast-door reveal fixes the first eastward view down Eden Prime's
466 m aluminium lamella vault: dirty mixed-era glazing, stepped terraces, pier
colonnade, structure-following growth, and deliberate quarantine decay.

- `references/environment/greenhouse_vault_reveal_west_2560x1440.png`

Regenerate it with:

```bash
python3 scripts/generate_greenhouse_vault_reveal.py
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

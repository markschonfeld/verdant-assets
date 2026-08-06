# Entrance Terrace Planter + Botanical Kit Handoff

## Delivery

`SourceMesh/terrace_botanical/` contains 11 Unreal-centimetre, Z-up OBJs plus one
material-slot library:

- `VD_TerracePlanter.obj` — tileable 245 cm mid module, 126 × 245 × 110 cm
- `VD_TerracePlanter_EndCap.obj` — reversible 13 cm terminal cap
- `VD_Dracaena_{A,B,C}.obj` — 1.67, 1.93, and 2.08 m overall
- `VD_ZZPlant_{A,B,C}.obj` — 0.61, 0.73, and 0.82 m overall
- `VD_DwarfMorningGlory_{A,B,C}.obj` — 0.98–1.02 m rim-to-deck drapes
- `VD_TerraceBotanical.mtl` — import-time slot names and neutral preview values

Every OBJ has exactly one `o` object, zero `g` records, a valid UV index on every
face corner, and XY-centred bounds with minimum Z at zero. Dracaena canes are
closed, smooth 10-sided tapered geometry with no raised bamboo-like rings. Leaves
and flowers are two-sided masked ribbons/cards rather than solid modelled blades.

The foliage density contract is species-specific:

- Dracaena: 52/58/64 leaves **per head**, 42–68 cm long, on three-quad curved
  ribbons. The outer rows arch up and finish below their attachment point.
- ZZ: 7/9/11 arching fronds per crown, each with 5–8 paired sections (10–16
  glossy leaflets) held near horizontal.
- Morning glory: 6/8/10 draping strands with 7–9 heart leaves each and flowers
  biased to the visitor-facing outer X- face.

Three 1024×1024 RGBA sheets provide base colour and the opacity mask in alpha:

- `cutouts/terrace_botanical/dracaena_marginata_leaf_rgba_1024.png`
- `cutouts/terrace_botanical/zz_leaflet_pair_rgba_1024.png`
- `cutouts/terrace_botanical/morning_glory_leaf_flower_rgba_1024.png`

## Why 245 cm

The module follows the existing `BALUS_*` bay cadence in
`level/rootstead_manifest.json`: adjacent bay locations differ by 245 cm. That
keeps the new barrier rhythm aligned with the terrace kit rather than introducing
an unrelated 2.4–3.0 m interval.

The module has deliberately open Y ends. Its front wall, back wall, rim rails,
and soil slab terminate exactly at Y ±122.5 cm, so adjacent instances meet as
continuous sections without doubled end walls. Use `VD_TerracePlanter_EndCap`
only at the exposed ends of a run; rotate the opposite cap 180° around Z.

## Rootstead placement state

The former west run at X **-350 cm** has been removed from the level because it
sat outside the glazed envelope. Do not recreate it. The only retained run is
the inboard run at X **700 cm**, currently 316 instances and correctly inside the
space. This handoff does not bake or overwrite those world transforms.

## Plant placement

The planter soil surface is Z **93 cm** in local space.

- Scatter Dracaena and ZZ with their local Z=0 at planter-local Z=93.
- Use roughly one Dracaena per bay, alternating variants and yaw; avoid a strict
  size sequence over long runs.
- Use one or two ZZ clusters per bay and vary yaw/offset while keeping crowns
  inside the ±46.5 cm soil width.
- Morning-glory origins are at the bottom of the hanging curtain, not the root
  crown: place local Z=0 at deck level and local X near the visitor-facing rim
  (assembly preview uses X=-63). The authored stem bends outward from the rim.
- For a softened barrier face, use about two overlapping morning-glory instances
  per planter bay, alternating A/B/C rather than repeating one silhouette.

`qa/terrace_planter_botanical/terrace_planter_botanical_assembly_preview.png`
shows a three-bay mixed planting study. It is a density/composition example, not
a preassembled export.

## Material intent

Material slots are semantic. Replace the MTL preview values with project master
materials or instances:

- `M_Planter_AgedConcrete` — use the formed-concrete PBR family; broad damp and
  mineral staining belongs in the material, not baked vertex lighting
- `M_Planter_CastRepair` — warmer repaired rim/scupper/end-cap hardware; a corten
  or ferrous retrofit variant can be substituted without changing the mesh
- `M_Planter_Soil` — dark worked terrace soil
- Dracaena — matte smooth cane with faint diamond scars in the material, no
  raised rings; restrained green strap leaves with a narrow burgundy margin
- ZZ — glossy leaf material, rougher green stems
- Morning glory — medium-gloss heart leaves and blue-violet flowers

Use **Masked** blend mode and the RGBA alpha channel as the opacity mask; enable
two-sided shading for all three foliage leaf/flower materials. Canes, stems,
vessel components, and end-cap hardware are closed or radial geometry.

## Wind encoding

Foliage OBJs carry grayscale RGB vertex colours: **0** (black) at cane/stem roots
and card attachment edges, ramping to **1** (white) at free leaf tips. Import with
vertex colours set to **Replace**, not Ignore. In the eventual World Position
Offset material, multiply bend displacement by the red channel. The vessels do
not carry wind colours. This pass only bakes the data; it does not add a WPO
material or claim in-engine wind behaviour.

## Collision and import

The OBJ contract does not carry Unreal simple-collision metadata. The barrier is
gameplay-critical, so do not leave collision at `NoCollision`:

1. Import each OBJ as one StaticMesh; do not combine meshes.
2. Keep scale at 1.0 (centimetres).
3. Import foliage vertex colours with `Vertex Color Import Option = Replace`.
4. Generate a simple box collision for `VD_TerracePlanter` covering its
   126 × 245 × 110 cm envelope, or use an equivalent authored blocking volume.
5. Give the end cap simple box collision only where the cap itself is exposed.
6. Foliage can remain `NoCollision` unless local interaction requires it.
7. After placement, walk the retained inboard run in PIE and test the jamb and outer-end
   transitions specifically; the visual mesh alone is not proof of a sealed path.

## Regeneration and QA

```bash
python3 scripts/generate_terrace_planter_botanical_kit.py
python3 scripts/verify_terrace_planter_botanical_kit.py
```

The verifier checks object/group records, MTL reference, exact material-slot
sets, indexed UV coverage, degenerate geometry, base-centred origins, species
height envelopes, planter dimensions, and expected file inventory. Outputs:

- `qa/terrace_planter_botanical/terrace_planter_botanical_verification.json`
- `qa/terrace_planter_botanical/terrace_planter_botanical_preview.png`
- `qa/terrace_planter_botanical/terrace_planter_botanical_assembly_preview.png`
- `qa/terrace_planter_botanical/terrace_botanical_alpha_sheets_preview.png`

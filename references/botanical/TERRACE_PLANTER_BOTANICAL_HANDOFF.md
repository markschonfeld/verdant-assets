# Entrance Terrace Planter + Botanical Kit Handoff

## Delivery

`SourceMesh/terrace_botanical/` contains 11 Unreal-centimetre, Z-up OBJs plus one
material-slot library:

- `VD_TerracePlanter.obj` — tileable 245 cm mid module, 126 × 245 × 110 cm
- `VD_TerracePlanter_EndCap.obj` — reversible 13 cm terminal cap
- `VD_Dracaena_{A,B,C}.obj` — 1.51, 1.65, and 1.97 m overall
- `VD_ZZPlant_{A,B,C}.obj` — 0.65, 0.82, and 0.92 m overall
- `VD_DwarfMorningGlory_{A,B,C}.obj` — 0.98–1.02 m rim-to-deck drapes
- `VD_TerraceBotanical.mtl` — import-time slot names and neutral preview values

Every OBJ has exactly one `o` object, zero `g` records, a valid UV index on every
face corner, and XY-centred bounds with minimum Z at zero. The foliage is mesh
geometry rather than camera-facing billboards. Dracaena canes are closed 10-sided
tapered geometry; its strappy leaves use curved, V-folded ribbons.

## Why 245 cm

The module follows the existing `BALUS_*` bay cadence in
`level/rootstead_manifest.json`: adjacent bay locations differ by 245 cm. That
keeps the new barrier rhythm aligned with the terrace kit rather than introducing
an unrelated 2.4–3.0 m interval.

The module has deliberately open Y ends. Its front wall, back wall, rim rails,
and soil slab terminate exactly at Y ±122.5 cm, so adjacent instances meet as
continuous sections without doubled end walls. Use `VD_TerracePlanter_EndCap`
only at the exposed ends of a run; rotate the opposite cap 180° around Z.

## Rootstead placement study

The following is a placement recommendation, not baked world transform data:

- planter centre X: **-350 cm**
- planter base Z: **3500 cm** (`ENT_Deck` top)
- planter west face: X **-413 cm**, leaving 7 cm inside the deck's west edge
- vestibule outer jamb/cap plane: Y **±972 cm**
- first module centres: Y **±1094.5 cm**
- continue outward at 245 cm intervals
- 26 modules per side place last centres at Y **±7219.5 cm**
- module ends reach Y **±7342 cm**; outer cap edges reach **±7348.5 cm**
- this leaves 1.5 cm inside the ±7350 cm deck/balustrade line

This produces two independent 63.70 m runs flanking the vestibule and closes the
measured walk-out path without narrowing the 9.2 m entrance clearance.

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
- Dracaena — matte cane, dark scar bands, restrained green strap leaves
- ZZ — glossy leaf material, rougher green stems
- Morning glory — medium-gloss heart leaves and blue-violet flowers

Enable two-sided shading for all three foliage leaf/flower materials. Canes,
stems, vessel components, and end-cap hardware are closed or radial geometry.

## Collision and import

The OBJ contract does not carry Unreal simple-collision metadata. The barrier is
gameplay-critical, so do not leave collision at `NoCollision`:

1. Import each OBJ as one StaticMesh; do not combine meshes.
2. Keep scale at 1.0 (centimetres).
3. Generate a simple box collision for `VD_TerracePlanter` covering its
   126 × 245 × 110 cm envelope, or use an equivalent authored blocking volume.
4. Give the end cap simple box collision only where the cap itself is exposed.
5. Foliage can remain `NoCollision` unless local interaction requires it.
6. After placement, walk the full two runs in PIE and test the jamb and outer-end
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

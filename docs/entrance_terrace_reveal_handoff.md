# Entrance-Terrace Reveal Kit — Handoff (Slice 1 base + Slice 2 supporting species + Slice 3 furniture + Slice 4 banners)

Source: `scripts/generate_entrance_terrace_reveal_kit.py`
Verify: `scripts/verify_entrance_terrace_reveal_kit.py`
Units: Unreal centimetres, Z-up. Every OBJ is one object, no `g` records,
named `usemtl` slots, indexed UVs on every corner, Z=0 / base-centred origin.
Foliage vertex RGB encodes wind stiffness (0 = rigid root, 1 = free tip).

Slice 2 adds three supporting display specimens: an aloe rosette, a
philodendron, and a coleus mound. Each is a composed specimen, not a hedge
module.

Slice 3 adds public visitor furniture: a pair of 1960s municipal park benches
(one intact, one subtly sagged/damaged), a freestanding period brochure/
leaflet stand, and one dry, non-functioning octagonal public-garden fountain.
All four are rigid props and carry **no vertex colour** -- the damaged bench
shows its damage through bowed beam geometry and a distinct weathered
material, never through paint-by-vertex.

Slice 4 adds three tattered 1960s Institute promotional banners: an
intact-but-faded vertical hanging banner, a torn/partially-detached banner
with asymmetric sag, and a narrow wayfinding/promotional pennant. Every
banner is a subdivided cloth grid (multi-wave attachment sag plus fine
wrinkle creases baked into the geometry, not a flat quad); the torn banner
uses alpha-cut ragged punctures and droops one lost top corner for a visibly
asymmetric drape. All three carry **no vertex colour**
-- this is rigid baked cloth for now, with wind physics deferred to a later
runtime pass. Each banner is single-material, double-sided (front + a
reversed-winding back face on the same vertices), and has its own 2048 RGBA
graphic sheet with alpha-cut torn/frayed edges, fading/stains, and
programmatically typeset Institute copy (PIL `ImageFont` on DejaVu Sans Bold/
Regular and Liberation Sans Bold -- no diffusion-generated lettering).

MTL: `SourceMesh/entrance_terrace_reveal/VD_EntranceTerraceReveal.mtl`
RGBA cutouts: `cutouts/entrance_terrace_reveal/` — four 1024 alpha sheets
(date-palm leaflet, leaf/bark litter, philodendron lobed leaf, coleus
patterned leaf) plus three Slice 4 2048 banner graphic sheets (Institute
faded, Institute torn, Botanical Terrace pennant), each referenced by both
`map_Kd` and `map_d`. Slice 3 reuses the leaf/bark litter sheet for the
fountain's collected leaf debris rather than adding a fifth sheet.

## Import steps (Unreal)
1. Import each OBJ as its own Static Mesh; keep "Combine Meshes" OFF (one object
   per file already).
2. Import the RGBA sheets as textures; connect RGB -> Base Color and A ->
   Opacity Mask on every masked leaf/leaflet/litter/banner material.
3. On every foliage mesh (date palm, aloe, philodendron, coleus) enable "Vertex
   Colors" import and drive a wind/pivot-sway node from vertex-colour luminance
   (0 anchored/rigid, 1 free tip). Trunks, stems, petioles and leaf attachments
   are 0; free leaf tips approach 1. The Slice 3 furniture (benches, brochure
   stand, fountain) and the Slice 4 banners/pennant import with no vertex
   colour at all -- do not wire a wind node to any of them yet.
4. Author collision per the notes below; do NOT let Unreal auto-generate a
   single convex hull on the planters or the fountain — it seals the open
   mouth / basin. Foliage leaves generally take NO collision. The Slice 4
   banners/pennant take **NO COLLISION** at all (decorative cloth only) --
   do not auto-hull them either; a hull across baked sag/tears would be both
   wrong-shaped and pointless for a walk-through decorative prop.

## Assets

### VD_SpecimenPlanter_Concrete
**Round specimen planter — aged cast concrete**

- Dimensions: 224 cm outer diameter x 98 cm tall; wall ~10 cm; soil disc ~18 cm below rim.
- Material slots: M_ConcretePlanter_Cast (body + inner wall + base), M_ConcretePlanter_Rim (top lip), M_Planter_DressedSoil (visible soil).
- Collision: Segmented ring collision: 8-16 convex wall segments + a base disc, leaving the mouth open. NEVER a single auto convex hull (it fills the bowl and blocks planting).

### VD_SpecimenPlanter_Ceramic
**Round specimen planter — period glazed ceramic**

- Dimensions: 188 cm outer diameter x 116 cm tall; wall ~8.5 cm; soil disc ~21 cm below rim.
- Material slots: M_CeramicPlanter_Glaze (glazed body + inner wall + base), M_CeramicPlanter_Rim (glazed lip), M_Planter_DressedSoil (visible soil).
- Collision: Same as the concrete planter: ring/segmented convex primitives around the wall + base disc; keep the opening clear. No single convex hull.

### VD_DatePalm_Hero
**Phoenix/date-palm hero specimen**

- Dimensions: ~4.1 m tall overall; trunk ~2.7 m with a raised diamond leaf-base lattice; 16 arching pinnate fronds.
- Material slots: M_DatePalm_Trunk (trunk + diamond bosses, rigid), M_DatePalm_Rachis (frond midribs), M_DatePalm_Leaflet (alpha-cut pinnate leaflet ribbons).
- Collision: Trunk-only vertical capsule or 8-sided cylinder collision (~0.5 m radius). Fronds/leaflets: NO collision (overlap-only), so visitors and camera pass through the canopy.

### VD_SoilDressing_Mound
**Scatter — uneven dressed soil mound**

- Dimensions: ~110 cm diameter x ~15 cm tall irregular dome.
- Material slots: M_SoilDressing_Mound.
- Collision: Single simple convex hull or a low box is fine (it is a solid mass).

### VD_SoilDressing_Litter
**Scatter — leaf / bark litter cards**

- Dimensions: ~85 cm spread of 15 near-flat alpha cards, a few cm thick.
- Material slots: M_SoilDressing_Litter (alpha-cut leaf/bark/twig atlas).
- Collision: No collision (decorative overlay).

### VD_SoilDressing_Stones
**Scatter — small stone cluster**

- Dimensions: ~80 cm spread of 6 faceted stones, ~10-16 cm each.
- Material slots: M_SoilDressing_Stone.
- Collision: Per-stone simple convex collision, or none if purely decorative. Do not wrap the whole cluster in one hull across the gaps.

### VD_Aloe_Specimen
**Supporting specimen — aloe rosette**

- Dimensions: ~80 cm tall x ~1.2 m spread; 32 thick 3-D succulent leaves in four tiers with serrated margins.
- Material slots: M_Aloe_Leaf (thick lofted diamond-section blades, no alpha), M_Aloe_Base (basal crown).
- Collision: No leaf collision. If a physical blocker is wanted, one short vertical capsule (~10 cm radius x ~20 cm) over the basal crown only; never hull the spreading leaves.

### VD_Philodendron_Specimen
**Supporting specimen — philodendron**

- Dimensions: ~1.1-1.7 m tall; 11 large lobed alpha-cut leaf sheets on real curved petioles rising from a crown clump.
- Material slots: M_Philodendron_Crown (rootball clump), M_Philodendron_Petiole (real petiole tubes), M_Philodendron_Leaf (lobed alpha-cut leaf sheets).
- Collision: No leaf/petiole collision (overlap-only). If needed, a single small capsule (~12 cm radius) over the crown clump so visitors do not walk through the base; leaves stay non-colliding.

### VD_Coleus_Specimen
**Supporting specimen — coleus mound**

- Dimensions: ~45-75 cm tall low dense mound, wider than tall; branching real stems with 60 opposite decussate patterned alpha-cut leaves (burgundy centre, chartreuse margin).
- Material slots: M_Coleus_Base (soil crown), M_Coleus_Stem (real branching stems), M_Coleus_Leaf (patterned alpha-cut leaves).
- Collision: No leaf collision. Optionally one low box/capsule (~12 cm radius x ~12 cm) over the base crown; do not hull the mound of leaves.

### VD_Bench_Municipal_Intact
**Public visitor furniture — 1960s municipal park bench (intact)**

- Dimensions: 196 cm long x ~46 cm deep x ~78 cm tall (to back top); ~44 cm seat height; tubular welded/cast-steel end frames, 6 seat slats + 4 back slats, flat and true.
- Material slots: M_Bench_CastFrame_Intact (tubular end frames + stretchers), M_Bench_SeatSlat_Intact (6 real timber seat boards), M_Bench_BackSlat_Intact (4 real timber back boards). No vertex colour.
- Collision: Two simple boxes (seat slab + back slab) plus a capsule or box per end frame, OR complex-as-simple on the tube frame silhouette. Do not collide individual slats separately.

### VD_Bench_Municipal_Damaged
**Public visitor furniture — 1960s municipal park bench (damaged/sagged)**

- Dimensions: Same 196 cm x ~46 cm footprint as the intact bench so the pair reads as one row; seat boards bow down to ~5 cm mid-span sag, the back frame leans further (~74 cm back top), one seat stretcher has dropped.
- Material slots: M_Bench_CastFrame_Damaged (leaning/corroded frame), M_Bench_SeatSlat_Damaged (weathered, sagging boards), M_Bench_BackSlat_Damaged (weathered back boards). No vertex colour -- damage is geometric + a distinct weathered material only.
- Collision: Same collision approach as the intact bench (simple boxes/capsules per frame end + seat/back slabs, or complex-as-simple); size the seat-slab box to the sagged mid-span, not the flat rest height.

### VD_BrochureStand_Institutional
**Public visitor furniture — freestanding brochure/leaflet stand**

- Dimensions: ~148 cm tall; ~45 cm footprint on a splayed 3-leg tripod foot; 5 shallow angled sheet-metal pockets climbing the post, each still holding one warped paper leaflet card.
- Material slots: M_BrochureStand_Frame (post + tripod legs), M_BrochureStand_Pocket (5 angled pocket trays), M_BrochureStand_Paper (5 warped leaflet cards). No vertex colour.
- Collision: One simple box or vertical capsule around the post + tripod footprint. Paper cards get NO collision (overlap-only).

### VD_Fountain_DryBasin
**Public visitor furniture — dry, non-functioning octagonal public-garden fountain**

- Dimensions: ~380 cm across x 112 cm tall; octagonal basin, dry recessed floor at 46 cm (well below the rim), stained central pedestal/nozzle stub to ~86 cm, 10 leaf-litter cards collected on the floor. No water material.
- Material slots: M_Fountain_BasinWall (outer wall + rim lip + inner drop), M_Fountain_BasinFloor (dry floor annulus), M_Fountain_Pedestal (stained pedestal/nozzle stub), M_Fountain_LeafLitter (collected leaf-litter cards, reuses the Slice 1 leaf/bark litter sheet). No vertex colour.
- Collision: Segmented ring collision: 8 convex wall segments (one per octagon face) + a separate floor-annulus disc + a short cylinder/capsule for the pedestal. NEVER one convex hull across the whole prop -- that seals the dry basin and hides/blocks the recessed floor.

### VD_Banner_Institute_Faded
**Slice 4 — intact-but-faded vertical hanging Institute banner**

- Dimensions: ~1.70 m wide x ~3.20 m tall; 16x24 subdivided cloth grid, multi-wave attachment sag + fine wrinkle creases baked in, front + reversed-winding back faces, no vertex colour.
- Material slots: M_Banner_Institute_Faded (single 2048 RGBA graphic sheet: 'EDEN PRIME / A GARDEN FOR THE ATOMIC AGE', sun-bleached, alpha-cut frayed hem).
- Collision: NO COLLISION -- decorative cloth only; do not auto-hull.

### VD_Banner_Institute_Torn
**Slice 4 — torn/partially-detached Institute banner, asymmetric sag**

- Dimensions: ~1.60 m wide x ~3.00 m tall; a denser 24x36 cloth grid with a lost top-right corner (droops + pulls inward), restrained alpha-cut ragged punctures, and a tattered lower hem.
- Material slots: M_Banner_Institute_Torn (single 2048 RGBA graphic sheet: 'THE INSTITUTE / SCIENCE IN SERVICE OF ABUNDANCE', heavy stains and alpha-cut ragged punctures).
- Collision: NO COLLISION -- decorative cloth only; do not auto-hull.

### VD_Pennant_BotanicalTerrace
**Slice 4 — narrow wayfinding/promotional pennant**

- Dimensions: ~1.30 m wide at the header tapering to ~0.10 m at the foot x ~2.80 m tall; 10x22 subdivided cloth grid, lighter sag/creases, no torn geometry.
- Material slots: M_Pennant_BotanicalTerrace (single 2048 RGBA graphic sheet: 'BOTANICAL TERRACE / PUBLIC EXHIBITION' with a wayfinding chevron mark, light fading + minor pinholes).
- Collision: NO COLLISION -- decorative cloth only; do not auto-hull.

## Scatter usage
The three `VD_SoilDressing_*` meshes are base-centred at Z=0 and sized to drop
into both these planters and the existing `SourceMesh/terrace_botanical`
planters. Scatter/rotate freely around Z; they carry no wind colour.

## Slice 3 furniture usage
`VD_Bench_Municipal_Intact` and `VD_Bench_Municipal_Damaged` share the same
196 cm footprint and frame layout so they place cleanly in pairs (e.g. flanking
a walkway) without visually mismatching in scale. Mix them freely; the damaged
variant reads as a single neglected bench in an otherwise-maintained row, not
a different bench type. `VD_BrochureStand_Institutional` and
`VD_Fountain_DryBasin` are each single freestanding props.

## Slice 4 banner usage
`VD_Banner_Institute_Faded`, `VD_Banner_Institute_Torn`, and
`VD_Pennant_BotanicalTerrace` are each single freestanding decorative cloth
props, base-centred at Z=0 like every other mesh in this kit; mounting them
against a wall, truss, or frame is left to the level/placement pass (out of
scope here). Mix the faded and torn banners freely along the same hanging
line for a maintained-vs-neglected read, the way the two benches pair up in
Slice 3. The pennant is narrower and tapers toward its foot, reads at a
smaller wayfinding scale, and is not meant to hang alongside the two full
banners.

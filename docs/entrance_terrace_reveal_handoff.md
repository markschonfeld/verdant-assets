# Entrance-Terrace Reveal Kit — Handoff (Slice 1 base + Slice 2 supporting species)

Source: `scripts/generate_entrance_terrace_reveal_kit.py`
Verify: `scripts/verify_entrance_terrace_reveal_kit.py`
Units: Unreal centimetres, Z-up. Every OBJ is one object, no `g` records,
named `usemtl` slots, indexed UVs on every corner, Z=0 / base-centred origin.
Foliage vertex RGB encodes wind stiffness (0 = rigid root, 1 = free tip).

Slice 2 adds three supporting display specimens: an aloe rosette, a
philodendron, and a coleus mound. Each is a composed specimen, not a hedge
module.

MTL: `SourceMesh/entrance_terrace_reveal/VD_EntranceTerraceReveal.mtl`
RGBA cutouts: `cutouts/entrance_terrace_reveal/` — four alpha sheets (date-palm
leaflet, leaf/bark litter, philodendron lobed leaf, coleus patterned leaf),
each referenced by both `map_Kd` and `map_d`.

## Import steps (Unreal)
1. Import each OBJ as its own Static Mesh; keep "Combine Meshes" OFF (one object
   per file already).
2. Import the RGBA sheets as textures; connect RGB -> Base Color and A ->
   Opacity Mask on every masked leaf/leaflet/litter material.
3. On every foliage mesh (date palm, aloe, philodendron, coleus) enable "Vertex
   Colors" import and drive a wind/pivot-sway node from vertex-colour luminance
   (0 anchored/rigid, 1 free tip). Trunks, stems, petioles and leaf attachments
   are 0; free leaf tips approach 1.
4. Author collision per the notes below; do NOT let Unreal auto-generate a
   single convex hull on the planters — it seals the open mouth. Foliage leaves
   generally take NO collision.

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

## Scatter usage
The three `VD_SoilDressing_*` meshes are base-centred at Z=0 and sized to drop
into both these planters and the existing `SourceMesh/terrace_botanical`
planters. Scatter/rotate freely around Z; they carry no wind colour.

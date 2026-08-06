# Entrance-Terrace Reveal Kit — Handoff (Slice 1)

Source: `scripts/generate_entrance_terrace_reveal_kit.py`
Verify: `scripts/verify_entrance_terrace_reveal_kit.py`
Units: Unreal centimetres, Z-up. Every OBJ is one object, no `g` records,
named `usemtl` slots, indexed UVs on every corner, Z=0 / base-centred origin.
Foliage vertex RGB encodes wind stiffness (0 = rigid root, 1 = free tip).

MTL: `SourceMesh/entrance_terrace_reveal/VD_EntranceTerraceReveal.mtl`
RGBA cutouts: `cutouts/entrance_terrace_reveal/` (referenced by both `map_Kd`
and `map_d`).

## Import steps (Unreal)
1. Import each OBJ as its own Static Mesh; keep "Combine Meshes" OFF (one object
   per file already).
2. Import the two RGBA sheets as textures; connect RGB -> Base Color and A ->
   Opacity Mask on the leaflet/litter masked materials.
3. On the date palm, enable "Vertex Colors" import and drive a wind/pivot-sway
   node from vertex-colour luminance (0 anchored, 1 free). Trunk vertices are 0.
4. Author collision per the notes below; do NOT let Unreal auto-generate a
   single convex hull on the planters — it seals the open mouth.

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

## Scatter usage
The three `VD_SoilDressing_*` meshes are base-centred at Z=0 and sized to drop
into both these planters and the existing `SourceMesh/terrace_botanical`
planters. Scatter/rotate freely around Z; they carry no wind colour.

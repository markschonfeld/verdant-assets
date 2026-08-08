# Exhaust-stack / signal-mast landmark handoff

## Canonical function

The landmark is a **working Eden Prime research exhaust stack later adapted by the settlement for signals and observation**. The original smoke plume is functional evidence; the oversized flag yard records later reuse. It is not a rocket, flare stack, religious icon, or purpose-built communications tower.

This pass replaces the `/Engine/BasicShapes/Cylinder` placeholders named `SPIRE` and `SPIRE_BASE`. It does not claim any architectural, door/bulkhead, railing, or 300 uu envelope-dependent family.

## Measured source state versus authored decision

### Measured from the live level

- Old `SPIRE`: centre `(60000, 0)`, 30 m diameter, 250 m high.
- Old `SPIRE_BASE`: same centre, 60 m diameter, 30 m high.
- Original plume origin: `Z=24700` (247 m).
- Original flag yard: approximately `Z=12500` (125 m), 45 m yard with 42 m cloth.
- Entrance terrace: 586 m from the stack; 99% of the placeholder was visible.
- Tram approach: 170 m from the stack; 100% visible, including the base.
- Entrance angular thresholds supplied by the live sightline audit:
  - 115.8 m: visually peers with the vault crown.
  - 156.2 m: approximately 1.5× the crown angle.
  - 197.7 m: approximately 2× the crown angle.

### Locked design decision

Mark selected **180 m total height**: dominant from the entrance without preserving the excessive 250 m placeholder. The old 60 m × 30 m base and 45 m flag yard are treated as stretched placeholders, not canon.

## Scale and origins

All coordinates are **Unreal centimetres at 1:1** (`1 OBJ unit = 1 uu = 1 cm`), with `+Z` up. Import every mesh at uniform scale **1.0**.

All three meshes share a **ground-centre assembly origin**. Place them at the same world transform, centred on the existing `(60000, 0, 0)` landmark origin. Do not offset the stack above the base; the base encloses its lower section.

| Asset | Authored bounds | Geometry role | Pivot/origin |
|---|---:|---|---|
| `VD_Spire.obj` | `22 × 22 × 180 m` maximum hardware span | opaque tapered exhaust stack, platforms, ladder, pods, collars, signal yard | shared ground centre `(0,0,0)` |
| `VD_SpireBase.obj` | `24 × 24 × 12 m` | opaque process/service enclosure, doors, ducts, flanges | shared ground centre `(0,0,0)` |
| `VD_SpireLights.obj` | `13.2 × 13.2 m` XY span; lenses from 59.8–177.7 m Z | translucent/emissive aircraft-warning lenses | shared ground centre `(0,0,0)` |

Primary stack dimensions:

- Lower shell: 16 m diameter.
- Upper rim: 6.6 m diameter.
- Full height: 180 m.
- Settlement signal yard: 18 m long at 90 m elevation.
- Warning-light bands: 60 m, 120 m, and 177.5 m.
- Human-detail priority band: ground through 40 m.

## Source artifacts

- Generator: `scripts/generate_spire_landmark.py`
- Verifier/preview: `scripts/verify_spire_landmark.py`
- Meshes:
  - `SourceMesh/props/VD_Spire.obj`
  - `SourceMesh/props/VD_SpireBase.obj`
  - `SourceMesh/props/VD_SpireLights.obj`
- Material-slot library: `SourceMesh/props/VD_Spire_Landmark.mtl`
- QA: `qa/spire_landmark/`

Regenerate and verify from the repository root:

```bash
python3 scripts/generate_spire_landmark.py
python3 scripts/verify_spire_landmark.py
```

## Geometry and detail strategy

### Ground–40 m: tram-approach detail band

The tram view is only 170 m away and sees the base near eye level. This band therefore carries the human-scale geometry:

- 2.5 m service/plant doors;
- 3 m process ducts with separate flange collars;
- fixed-width ladder with 35 cm rung spacing, following the shell taper;
- ladder stand-off brackets;
- two fully posted maintenance platforms with 1.1 m guardrails;
- braced environmental-instrument arms and pods;
- real door, collar, and structural fasteners.

### Above 40 m: far-band structure

The entrance view is 586 m away. Detail decreases sharply above the lower band while retaining skyline-readable construction:

- four staged taper sections;
- simplified but physically supported maintenance decks;
- structural collars;
- 18 m settlement signal yard and braces at 90 m;
- three aircraft-warning bands;
- heavy exhaust rim and soot-dark mouth.

Fasteners, rails, and emitters remain human-scale throughout; no detail was enlarged in proportion to the total height.

## Material intent

| Slot | Intended surface | Projection / import |
|---|---|---|
| `M_Spire_Concrete` | dark cast foundation concrete | world/triplanar; opaque |
| `M_Spire_StackConcrete` | weathered pale reinforced stack shell | world/triplanar; opaque |
| `M_Spire_PaintedSteel` | aged Institute teal/green service enclosure | world/triplanar; opaque |
| `M_Spire_BareMetal` | galvanized/aluminium platforms, ducts, collars | world/triplanar; opaque |
| `M_Spire_ServicePanel` | oxidized orange-brown doors, pods, pulley housings | world/triplanar; opaque |
| `M_Spire_Fastener` | dark steel rails, bolts, ladder, brackets | world/triplanar; opaque |
| `M_Spire_Soot` | matte black exhaust-mouth recess | world/triplanar; opaque |
| `M_Spire_WarningLens` | red translucent/emissive aviation lens | separate non-Nanite mesh |

There is never an invisible warning light: `VD_SpireLights` supplies visible lens/emitter geometry. Runtime point/spot lights may supplement those lenses but must not replace them.

## Nanite and collision

- `VD_Spire`: **Nanite ON**, opaque, **NoCollision** unless a specific reachable lower-shell blocker is needed.
- `VD_SpireBase`: **Nanite ON**, opaque, simple octagonal/box collision around the 24 m service enclosure. Do not use per-poly navigation collision.
- `VD_SpireLights`: **Nanite OFF**, translucent/emissive, **NoCollision**.

The OBJ solids are closed and manifold. Interpenetrating generated sub-solids are intentional and keep rails, fasteners, platforms, and brackets reproducible.

## Required live-level integration changes

1. Import all three OBJ files at uniform scale `1.0` with unit conversion disabled.
2. Place all three at the old landmark ground-centre transform `(60000, 0, 0)`.
3. Move/rebuild the smoke plume so its source sits at the new exhaust mouth near `Z=18000`; the old `Z=24700` plume would float 67 m above the stack.
4. Do **not** reuse or scale the old 42 m flag cloth. The new yard is 18 m at `Z=9000`; author a separate appropriately sized dynamic flag/halyard asset if the settlement flag remains.
5. Apply collision as described above and confirm the 24 m base footprint leaves the tram path clear.
6. Check the entrance terrace and tram approach in Play mode, including nighttime visibility of all three warning-light bands.
7. Only after visual/navigation acceptance, hide or delete the two Engine cylinders.

## Verification contract

The verifier checks:

- exact authored bounds and shared-origin placement;
- material assignment and MTL linkage;
- one named object per OBJ, no `g` group records, and `usemtl`-driven slots;
- a valid UV0 texture-coordinate index on every face corner;
- valid face indices and non-degenerate faces;
- closed two-face edge incidence for every generated solid;
- separate translucent warning-light geometry;
- reproducible full-height and lower-40 m visual QA preview.

Do not solve fit issues with non-uniform actor scaling. Change generator dimensions and regenerate the OBJ/QA package together.

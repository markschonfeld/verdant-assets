# Rootstead Blast-Door Surround Handoff

## Delivery

`SourceMesh/architecture/` contains:

- `VD_BlastDoorSurround.obj` — one opaque cast-concrete and bolted-steel portal
- `VD_BlastDoorSurround.mtl` — six semantic import-time material slots

The door leaves are deliberately **not** included. Keep the existing left/right
leaf meshes and their animation/Blueprint ownership separate.

The OBJ has exactly one `o VD_BlastDoorSurround` record, zero `g` records, one
valid UV0 index on every face corner, and named `usemtl` assignments. Units are
Unreal centimetres, Z-up.

## Origin and placement

- Local origin: **opening base-centre** `(0, 0, 0)`
- World placement: **`(-380, 0, 3500)`**
- Rotation: `(0, 0, 0)`
- Scale: `1.0`
- Overall local bounds: `X -132…54`, `Y -520…520`, `Z -48…470` cm
- Overall world bounds: `X -512…-326`, `Y -520…520`, `Z 3452…3970` cm

The local negative-Z extent is only the thin water-stain apron below the sill.
The pivot remains at the opening base as requested.

## Architectural route closure

The structural portal follows the measured end-wall and jamb planes:

- wall west face: world `X -509` / local `X -129`
- jamb line: world `X -350` / local `X 30`
- doorway: world/local `Y -400…400`
- structural return bands: world/local `Y -520…-400` and `400…520`

Each side has a continuous cast-concrete return from local `X -129` to `12`,
plus a bolted steel jacket from `12` to `30`. The inner reveal face therefore
runs the full **159 cm** from world X `-509` through the jamb line at `-350`.
The player can no longer step sideways from the doorway onto the wall top; the
route is closed by visible architecture rather than an invisible blocker.

The threshold plate spans local `X -129…30`, `Y -400…400`, `Z 0…8`. Its five
low tread bars rise only to local Z `11`. The central player volume remains clear
through local `Y ±380` and local Z `12…340`; track/trolley hardware occupies the
head zone above that.

## Design and material intent

The surround is intentionally older, heavier, and cruder than the glazed
vestibule:

- deep cast-concrete portal core and side returns
- broad bolted steel face jacket rather than light greenhouse sections
- dark reveal liners and continuous overhead track casing
- three oversized guide/hinge shoes per jamb, trolley housings, pins, and gussets
- asymmetric replaceable rub plates at hand height
- threshold plate and tread bars
- mineral/water-stain slots on the cast face and below the sill datum

Material slots are semantic and should be replaced with project masters or
instances:

- `M_BlastSurround_CastConcrete` — old coarse formed concrete, aggregate and chips
- `M_BlastSurround_AgedSteel` — dark oxidized structural plate, restrained paint remnants
- `M_BlastSurround_ShadowSteel` — near-black reveal liner and track recess
- `M_BlastSurround_HandWear` — polished/scraped rub plates and threshold
- `M_BlastSurround_WaterStain` — dark mineral runoff and damp apron
- `M_BlastSurround_BoltSteel` — exposed pins, bolt heads, and trolley axles

UV0 uses dominant-axis planar projection at one UV unit per metre. Use the slots
for authored steel/concrete PBR families; do not flatten the material contrast
into one generic rust material.

## Existing actor replacement scope

After importing and placing the surround, the obvious west-portal primitive
surround actors it supersedes are:

- `DOOR_Head`
- `DOOR_JambL`
- `DOOR_JambR`
- `DOOR_Sill`
- `DOOR_Track`
- `DOOR_ShoeHeadL`
- `DOOR_ShoeHeadR`

Keep `DOOR_LeafL` and `DOOR_LeafR` separate. Preserve the west door Blueprint,
buttons, readers, and panels until their interaction ownership is confirmed in
Play mode. Do not bulk-delete the whole `DOOR_*` family: the manifest also
contains the unrelated east blast door.

## Collision — required import setting

**Do not accept Unreal's default auto-generated convex hull.** One convex hull
around this portal fills the doorway and creates an invisible wall, exactly as
happened with the vestibule frame.

Recommended for this static 810-face surround:

1. import as one StaticMesh, scale `1.0`, preserving material slots;
2. set collision complexity to **`CTF_USE_COMPLEX_AS_SIMPLE`**;
3. keep collision enabled as `QueryAndPhysics`;
4. test the full threshold, both inner jambs, and both side-return transitions in PIE.

Alternative: author separate simple boxes for the two returns, head, and
threshold. Those primitives must leave `Y -400…400` open above the threshold.
Never use one auto convex hull for the whole portal.

## Regeneration and QA

```bash
python3 scripts/generate_blast_door_surround.py
python3 scripts/verify_blast_door_surround.py
```

The verifier checks the one-object/no-group contract, exact MTL and material
slots, indexed UV coverage, non-degenerate closed geometry, bounds, the 159 cm
side-return faces, full threshold/head spans, and the central clear volume.
Outputs:

- `qa/blast_door_surround/blast_door_surround_verification.json`
- `qa/blast_door_surround/blast_door_surround_preview.png`

The preview includes a hero view, east elevation, and a plan cut explicitly
showing the solid returns and bounded doorway axis.

# Rootstead west-entry assets — Unreal handoff

This delivery is **additive**. It does not remove, trim, regenerate, or otherwise
modify `ENDWALL_W`. The existing west-gable lattice remains complete from the
springing row upward.

## Assets

### `VD_RootsteadEntryPortal`

- Source: `SourceMesh/architecture/VD_RootsteadEntryPortal.obj`
- Material library: `SourceMesh/architecture/VD_RootsteadEntryPortal.mtl`
- Place at world location **(0, 0, 3500)**, rotation zero, scale 1.
- Local/world dimensions at that placement:
  - overall coverage: Y `-1450..1450`, Z `3500..4700`;
  - facade slab and trim: X `0..128` only;
  - vestibule-clear face opening: Y `-1000..1000`, Z `3500..4420`;
  - deep reveal runs west to the measured blast-door envelope;
  - frosted leaves: X `-397..-353`, Y `-416..416`, Z `3508..3892`.
- The two broad side bands and head occlude the walkable-centre gable members.
  The existing vestibule occupies the deliberate central opening.
- The side-band rails are the rigid climbing support that replaces/absorbs
  `TRELLIS_WestDoor`; no foliage cards are included in this rigid asset.
- Existing `VINE_WestDoor` foliage may be reattached to the integrated support or
  replaced separately. Do not assign `MX_Foliage` to the rigid portal.
- Frosted glazing has its own semantic material slot:
  `M_EntryPortal_FrostedGlass`.

Material slots:

1. `M_EntryPortal_FormedConcrete`
2. `M_EntryPortal_OxidisedAluminium`
3. `M_EntryPortal_RevealSteel`
4. `M_EntryPortal_TrellisSteel`
5. `M_EntryPortal_FrostedGlass`
6. `M_EntryPortal_WaterStain`
7. `M_EntryPortal_BoltSteel`

The OBJ contains one `o` object, no `g` records, indexed UVs at every face
corner, and no vertex-colour data. It is a rigid architectural mesh.

#### Portal collision — mandatory

**Never keep Unreal's import-generated single convex hull.** It spans the
walk-through opening and creates an invisible wall.

1. Remove import-generated collision immediately after import.
2. Set the BodySetup trace flag to `CTF_USE_COMPLEX_AS_SIMPLE`, **or** author
   aperture-safe segmented primitives for the left pier, right pier, head, side
   reveal panels, and threshold.
3. If the frosted leaves remain closed/static, their surface can block passage.
   If the existing leaves animate or are retained as separate actors, remove the
   included leaf faces during the Unreal integration step or use a no-collision
   duplicate for the portal and keep leaf collision on the existing actors.
4. Re-enter PIE and walk the complete centreline from west of X `-445` through
   the reveal and vestibule. Do not accept visual inspection alone.

### `VD_VaultFootShoe`

- Source: `SourceMesh/architecture/VD_VaultFootShoe.obj`
- Material library: `SourceMesh/architecture/VD_VaultFootShoe.mtl`
- One instance per actual `NodeHero` foot beyond `|Y| = 1450`.
- Place the base-centred pivot at the node XY and deck-top Z. Rotate around Z if
  the node orientation requires it; do not scale.
- Overall bounds: X `-91..91`, Y `-94..94`, Z `0..72`.
- Base plate: nominal `180 x 188 cm`.
- Explicit open socket: `112 x 116 cm`, providing 11.9 cm and 12.1 cm total
  diametral clearance around the measured `100.1 x 103.9 cm` node stock.
- The 72 cm collar covers the node junction that begins 10 cm below deck top.
- Four visible anchor studs and separate water-stain slots provide the intended
  cast retrofit/fixing read.

Material slots:

1. `M_VaultFootShoe_CastIron`
2. `M_VaultFootShoe_BoltSteel`
3. `M_VaultFootShoe_WaterStain`

The OBJ contains one `o` object, no `g` records, indexed UVs at every face
corner, and no vertex-colour data.

#### Foot-shoe collision

Recommended setting is **NoCollision** because these instances sit in the
non-walkable planting beds. If collision is required, use complex-as-simple or
explicit segmented primitives. The collar is an authored rectangular ring;
do not rely on convex decomposition to preserve its socket opening.

## Regeneration and QA

```bash
python3 scripts/generate_rootstead_west_entry_assets.py
python3 scripts/verify_rootstead_west_entry_assets.py
```

QA artifacts:

- `qa/rootstead_west_entry/rootstead_west_entry_verification.json`
- `qa/rootstead_west_entry/rootstead_west_entry_preview.png`

The verifier checks the one-object/no-group/UV/no-vertex-colour contract,
manifold closed components, exact bounds, facade depth, vestibule clearance,
walkable reveal clearance, frosted-leaf envelope, and foot-shoe socket fit.

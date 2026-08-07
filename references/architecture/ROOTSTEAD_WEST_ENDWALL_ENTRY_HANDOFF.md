# Rootstead west endwall + entrance — Unreal handoff

This delivery is a **REPLACEMENT** for the whole west gable, not the additive
occlusion pattern shipped on `origin/feat/rootstead-west-entry-assets`
(`VD_RootsteadEntryPortal` + `VD_VaultFootShoe`). That delivery never rebuilt
the gable lattice — it only added a facade box in front of the existing
`ENDWALL_W` — and it baked static "frosted leaf" glass into the *same* rigid
object that fills the animated door-leaf sweep volume, so the doorway would
always read as shut no matter what `DOOR_LeafL`/`DOOR_LeafR` did. Neither
mistake is repeated here: `VD_RootsteadWestEndwallEntry` *is* the gable — a
full triangular lattice from the ENDGLAZE_W transfer junction to the crown,
with the entrance cut through by topology — and the frosted leaves ship as a
separate, explicitly optional mesh that never enters the leaf sweep volume.

## Assets

### `VD_RootsteadWestEndwallEntry` (required, replaces `ENDWALL_W` above z=3500)

- Source: `SourceMesh/architecture/VD_RootsteadWestEndwallEntry.obj`
- Material library: `SourceMesh/architecture/VD_RootsteadWestEndwallEntry.mtl`
- Place at world **(0, 0, 3485.94)**, rotation zero, scale 1. (Local Z=0 is the
  authored base datum — the lowest point of the joint collars sitting on the
  z=3500 transfer row, which dip slightly below the row's nominal Z since a
  collar has finite radius. Regenerating with different tube-radius constants
  will change this offset; always take the exact value from
  `qa/rootstead_west_endwall_entry/rootstead_west_endwall_entry_lattice_graph.json`
  → `world_placement`, not the number above, if you've touched the generator.)
- Local bounds: X `-509 .. 112`, Y `±7512.5`, Z `0 .. 6205` (i.e. world Z up to
  `9691`, comfortably covering the crown at `9675`).
- Does **not** rebuild `ENDDADO_W` (z 0..900) or the existing `ENDGLAZE_W`
  glazing (z 900..3500) — those stay as they are. This asset starts exactly
  where they stop.

Material slots:

1. `M_WestEndwall_OxidisedAluminium` — lattice tubes, joint collars, and the
   ENDGLAZE transfer/sill cap band.
2. `M_WestEndwall_GlazeAcrylic` — original-era lattice panes (~80%).
3. `M_WestEndwall_GlazeRepair` — later repair-era lattice panes (~20%,
   pseudo-randomly distributed by node id, mirroring the mixed-era glazing
   used elsewhere in Rootstead).
4. `M_WestEndwall_EntranceReveal` — entrance jamb/head/sill structure and the
   facade piers/head band.
5. `M_WestEndwall_TrellisSteel` — rigid climbing trellis (side bands + head
   band).
6. `M_WestEndwall_SealShadowGap` — thin recessed groove strips at the
   jamb/head step lines.
7. `M_WestEndwall_FrostedTransom` — fixed transom light above the head return.
   This is architecturally useful fixed glazing, not a substitute for the
   leaves: it sits at world Z `3974..4040`, strictly above the leaf envelope's
   top (`3892`) and the head return, and is verified never to overlap either.

The OBJ contains one `o` object, zero `g` records, indexed UVs on every face
corner, no vertex-colour data, and every solid component (tubes, joint
collars, panes, entrance structure, trellis, transfer cap) is a closed manifold
(edge incidence exactly 2 everywhere — verified globally).

#### Lattice / entrance topology

- 957 lattice nodes, 2735 tube members, 1778 panes — a 300 uu equilateral
  triangular grid boundary-snapped to the true circular arch (centre y=0,
  z=2035.2, radius 7639.8) and, separately, to the entrance-hole rectangle
  (`±560` Y, world Z `3500..4070`). Boundary nodes are *repositioned* onto the
  true boundary curves, not deleted and patched — this is what makes the
  aperture "integrated by topology" rather than arbitrary member deletion:
  every remaining node still has its full triangulated connectivity, just at
  a boundary-conforming position.
- z4000..6000 members measure ~5.5 cm radius versus ~9.0 cm below and ~10.5 cm
  above (measured from the actual OBJ ring geometry, not just declared) — a
  deliberately slender aluminium band with restrained, compact joint collars
  (no flange plates), not a HERO_BAND-style heavy structural read.
- The ENDGLAZE transfer/sill cap (`M_WestEndwall_OxidisedAluminium`, world X
  `-509..-431`, Z `3500..3560`) is continuous across the full wall width
  except for the entrance gap (`±560` Y) — there is no unsupported gap at the
  ENDGLAZE contact line.

#### Entrance aperture — the animated door leaves

- **The door-leaf envelope stays completely empty in this mesh**: world X
  `-397..-353`, Y `±416`, Z `3508..3892`. Verified by testing every face's
  bounding box against that volume — zero intrusions. The existing
  `DOOR_LeafL`/`DOOR_LeafR` actors keep animating in this space exactly as
  before; nothing in `VD_RootsteadWestEndwallEntry` will ever visually read as
  a shut door regardless of leaf animation state.
- The reveal/jamb/head/sill around that envelope is authored with real depth:
  stepped jamb returns with a shadow-gap groove, a head return with a soffit
  drip lip, and a sill with a nosing lip — not a handful of scaled cubes.
- Jamb solids stop at Y `±424` (a 4 uu safety buffer beyond the leaf's `416`)
  and the sill's top surface is at world Z `3506` (2 uu below the leaf's
  bottom, `3508`) specifically so the static reveal never laps into the leaf
  sweep the way the *existing* `DOOR_JambL/R` boxes do (their y 400..462
  band overlaps the leaf's y≤416 — a normal rebate detail on an *animated*
  actor, but not safe to reproduce on this static mesh).

#### Trellis — proud of the facade, within the hard limit

PR #17's trellis bug: rails centred at x=120 with radius 7 against a slab face
also at x=120 — zero clearance, embedded in the wall. Fixed here with an
explicit stand-off: facade pier/head-band face is at world X=85, rail
centreline at X=104 with 8 cm radius, giving the near rail surface a **measured
11 cm positive clearance** (verified from actual geometry, not just declared),
and the far rail surface at X=112 stays 16 cm inside the VEST_Frame hard east
limit (X=128). Both side bands and a head band are present, matching the
brief's "side/head facade bands." No trellis geometry carries a foliage
material — this is rigid support steel only; existing `VINE_WestDoor` foliage
can be reattached to it.

### `VD_RootsteadWestEndwallEntry_Leaves` (optional, replaces `DOOR_LeafL`/`DOOR_LeafR` meshes)

- Source: `SourceMesh/architecture/VD_RootsteadWestEndwallEntry_Leaves.obj`
- Material library: `SourceMesh/architecture/VD_RootsteadWestEndwallEntry_Leaves.mtl`
- **This is explicitly a replacement for the existing `DOOR_LeafL` and
  `DOOR_LeafR` static mesh assignments — it is not additive.** Import it only
  if you intend to re-skin those two animated actors with a frosted-glass
  look; do not spawn it as new geometry alongside them, and do not import it
  at all if the existing leaf meshes are being kept.
- One object, two disconnected leaf components (left/right), matching this
  repo's "single object, two disconnected components acceptable" convention
  for door leaf replacements — verified as exactly 2 connected components.
- Bounds match the measured envelope exactly: X `-397..-353`, Y `±416`,
  Z-span `384` (world `3508..3892`). Place each half at the corresponding
  `DOOR_LeafL`/`DOOR_LeafR` actor's existing pivot and re-hook the existing
  animation blueprint to the new mesh — this delivery does not change the
  animation, only the leaf geometry/material.
- Material slots: `M_WestEndwallLeaf_FrostedGlass` (required, the two
  X-normal glazed faces) and `M_WestEndwallLeaf_AluminiumFrame` (the thin
  perimeter). No vertex colours.

## Collision — mandatory, read before importing

**Do not accept Unreal's import-generated single convex hull.** On a 150 m-wide
asset with a door aperture punched through it, that hull bridges the aperture
and seals the only way through — this is the same class of bug that sealed the
vestibule doorway on an earlier delivery (see
`docs/VERDANT_PROJECT_BRIEF.md` §4). **Do not use convex decomposition** either
— it does not reliably segment a shape this large and complex; expect it to
collapse to one or two hulls that still bridge the aperture, the same failure
mode recorded for the planter rings. **Do not set complex-as-simple for the
whole asset** — at 48k faces spanning 150 m, that is both expensive and
pointless on a mesh that is mostly non-walkable glazing and high lattice.

Recommended setup:

1. Set the render mesh's collision to **NoCollision** immediately after
   import.
2. Author explicit segmented Unreal **box** collision primitives by hand for:
   - the left and right entrance piers (`PIER_L`/`PIER_R`, world X `0..85`),
   - the head band (world X `0..85`, Z `4200..4260`),
   - the jamb/reveal returns flanking the door (world Y outside `±424`),
   - the head return/soffit (world Z `3892..3974`),
   - the sill **only** where it is actually walked on (world Z `3500..3514`,
     kept clear of the door aperture footprint itself),
   - any broad lower structural zones you add during in-engine dressing.
3. **No primitive may bridge the door aperture.** Every box above does not bridge
   the aperture—each stops at the aperture's Y `±560`/Z `4070` boundary; do not
   extend one across it to "simplify" collision.
4. Leave the lattice, panes, and trellis at **NoCollision** — they are glazing
   and high climbing structure, not walked surfaces.
5. If the optional leaf replacement mesh is imported, it inherits whatever
   collision setup the existing `DOOR_LeafL`/`DOOR_LeafR` actors already use
   for their animation blueprint; do not add new collision primitives for it.

### PIE walk-through acceptance test

Stop PIE before making any changes (per `docs/VERDANT_PROJECT_BRIEF.md` §3).
After importing and setting up collision:

1. Enter PIE. Walk the complete centreline from west of world X `-560`
   (outside the transfer cap / trellis piers) through the entrance aperture
   to world X `128` (the `VEST_Frame` threshold), at both `DOOR_LeafL`/
   `DOOR_LeafR` open **and** closed.
2. Confirm you cannot walk through the transfer cap, the jamb returns, the
   head soffit, or the trellis piers anywhere off the centreline — the
   segmented primitives should block those without blocking the doorway.
3. Confirm the sill collision (if added) does not create a step/catch at the
   threshold.
4. Do not accept a visual-only inspection — actually walk it. This is the
   acceptance gate; regenerating the OBJ and re-running the verifier is not a
   substitute for a PIE pass with real collision applied.

## Regeneration and QA

```bash
python3 scripts/generate_rootstead_west_endwall_entry.py
python3 scripts/verify_rootstead_west_endwall_entry.py
```

Both scripts import `scripts/rootstead_west_endwall_entry_spec.py`, the single
shared source of truth for every world-geometry constant in this delivery —
change a dimension there, not independently in each script.

QA artifacts:

- `qa/rootstead_west_endwall_entry/rootstead_west_endwall_entry_verification.json`
  — every measured claim above, with a `pass`/`failures` breakdown per
  section (contract, lattice, transfer cap, leaf-envelope emptiness, trellis
  clearance, leaf-replacement contract, handoff-doc content).
- `qa/rootstead_west_endwall_entry/rootstead_west_endwall_entry_preview.png`
  — full front elevation of the gable plus a detailed entrance inset (front
  and side).
- `qa/rootstead_west_endwall_entry/rootstead_west_endwall_entry_lattice_graph.json`
  — the full node/edge/pane design graph, with vertex-index references into
  the OBJ so the verifier's claims are checked against actual geometry, not
  just the graph's own bookkeeping.

The verifier does not just report counts — it independently recomputes the
arch/hole envelope from `rootstead_west_endwall_entry_spec.py`'s constants,
cross-checks every node/edge/pane's declared position against the vertex data
the generator actually wrote into the OBJ, measures tube/collar radii from
ring geometry rather than trusting the declared values, and integrates pane
area against the analytic arch-minus-hole area to catch gaps or overlaps in
the field.

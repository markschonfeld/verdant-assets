# PR #18 rework — the lattice joints must match the vault kit

**Status:** PR #18 (`feat/rootstead-west-endwall-entry`, `0c1155f`) is imported and
structurally correct. Placement, bounds, the door envelope, the trellis stand-off,
collision and material slots all verified in-engine. **Do not redo any of that.**

One thing needs rebuilding: the lattice **joints**. Mark's review, on seeing it
in the level next to the existing roof:

> "The frame junctions are a mismatch to the design used on the rest of the
> greenhouse roof. However, if that gets redone, the rest seems good."

## Root cause — a spec decision, not a modelling error

`ROOTSTEAD_WEST_ENDWALL_ENTRY_HANDOFF.md` set the intent as:

> "deliberately slender aluminium band with restrained, compact joint collars
> (no flange plates), not a HERO_BAND-style heavy structural read"

That was the wrong call for this building. Rootstead's vault is *built out of*
heavy hub joints — they are the visual signature of the whole envelope, repeated
across 150 m of roof directly above this gable. A gable that suppresses them
reads as a different structure bolted onto the same building.

The generator did exactly what the spec told it to. Change the spec.

## The target, measured from the actual kit meshes

Measured from `Verdant 5.8/SourceMesh/*.obj` — the meshes the rest of the
envelope is instanced from — not from screenshots and not from the handoff.

### `VD_VaultNode.obj` — the hub, and the thing that is missing

```
radial extent (xy)      14.31 .. 52.66 uu     bore 14.31, hub 52.66
axial thickness (z)     40.40 uu              (z -20.20 .. +20.20)
```

A disc hub of **radius 52.7 and thickness 40.4**, with a **14.3 bore** the tubes
plug into. One sits at every lattice node across the vault.

### `VD_VaultTube.obj` — the member

```
plain barrel radius      9.4 .. 10.5 uu       (vertices cluster at the ends;
end collar hardware      out to 14.26 uu       the mid-span is unsubdivided)
length                   262.0 uu             on the 300 uu structural PITCH
```

### Against the current spec (`rootstead_west_endwall_entry_spec.py`)

| quantity | vault kit | PR #18 | action |
|---|---|---|---|
| tube radius, z < 4000 | 9.4–10.5 | `TUBE_RADIUS_LOWER = 9.0` | keep |
| tube radius, 4000–6000 | 9.4–10.5 | `TUBE_RADIUS_MID = 5.5` | **raise to ~10.0** |
| tube radius, z >= 6000 | 9.4–10.5 | `TUBE_RADIUS_UPPER = 10.5` | keep |
| joint hub radius | **52.66** | `1.6 x r` = 8.8–16.8 | **replace with a real hub** |
| joint axial length | **40.40** | `2 x 11.0` = 22.0 | **40.4** |
| joint bore | 14.31 | n/a | tubes seat into the hub |

## What to change

1. **Add a hub at every lattice node.** Radius **52.66**, axial thickness
   **40.40**, bore **14.31**, axis along the node normal. This is the change
   that actually answers the review — the collar factor is not the fix, the
   absent hub is.
2. **`TUBE_RADIUS_MID` 5.5 -> ~10.0.** The three-band variation was there to
   keep the mid-height band slender; the vault has no such variation, so a
   uniform ~9.5–10.5 across all three bands is the truer match. Keeping the
   banding is acceptable if the *spread* narrows to within the kit's own
   9.4–10.5 range.
3. **Retire `JOINT_COLLAR_RADIUS_FACTOR` / `JOINT_COLLAR_HALF_LENGTH`** or
   re-derive them from the hub above, so there is one source of truth.
4. **Sanity-check the triangle budget.** A 52.7-radius hub at ~1,000 nodes is a
   large step up from a thin collar. `VD_VaultNode` is 12,464 tris and the
   project already ships `VD_VaultNode_Far` at 672 tris (18.5x) for exactly this
   reason — see `PyTools/import_far_variants.py`. Match that decimation strategy
   rather than inventing one, and if the hub count makes a single mesh
   impractical, say so before building rather than shipping a heavy one.

## Explicitly NOT changing

Everything else passed. Do not touch, and do not let a regenerate silently move:

- world placement `(0, 0, 3485.94)`; local bounds X `-509..112`, Y `+/-7512.5`, Z `0..6205`
- the door-leaf envelope staying empty: X `-397..-353`, Y `+/-416`, Z `3508..3892`
- jamb solids stopping at Y `+/-424`; sill top at Z `3506`
- trellis stand-off: facade face X `85`, rail centreline X `104`, r `8`,
  measured 11 cm clearance, far surface X `112` inside the `VEST_Frame` limit `128`
- the 7 material slot names (all are bound in-engine already; renaming one
  silently unbinds it)
- single `o`, no `g`, UVs present, base at local Z 0

## Verification to add

`verify_rootstead_west_endwall_entry.py` should gain a joint check that fails if
the hub radius is not within tolerance of **52.66** and the axial length not
within tolerance of **40.40**. The current verifier passed this delivery
completely, because nothing in it ever compared the joints to the vault kit.
That gap is why this reached the level before anyone noticed.

## Known follow-ups on the Unreal side — not Hermes' scope

Handled in-engine after the rework lands:

- the old door-area walls clip through the new doorway and come out
- the interact button needs repositioning
- `VINE_WestDoor` re-drapes onto the new trellis; it currently attaches oddly
  and the new pier reads bare

# Rootstead flank dado — replace the base course on both long elevations

**Ask:** a modular dado/base-course asset for the vault's two long flanks, to
replace scaled engine cubes.

**This is NOT urgent geometry** — the hole it was leaving is closed. It is a
quality job on the longest continuous surface in the level.

## What is there now

Every one of these is `/Engine/BasicShapes/Cube`, scaled:

```
VW_L / VW_R           x   -570..46070  y +/-7475..7525  z    0..900   MI_Terrace
WDADO_FLOOR_N / _S    x  27000..45000  y +/-7410..7500  z    0..340   MI_Retain
WDADO_TERR_A_N / _S   x   6000..10000  y +/-7410..7500  z 2600..2940  MI_Retain
WDADO_TERR_B_N / _S   x  13000..17000  y +/-7410..7500  z 1700..2040  MI_Retain
WDADO_TERR_C_N / _S   x  20000..24000  y +/-7410..7500  z  800..1140  MI_Retain
```

`VW_L` and `WDADO_FLOOR_S` were missing entirely until 2026-08-07 and have just
been mirrored in-engine from their north twins. The asymmetry is fixed; the
crudeness is not.

## Where it sits in the wall build-up

```
PLINTH_S / _N      y +/-7265..7735   z  -600 ..   40     below
>>> THE DADO       y +/-7410..7525   z     0 ..  900     this asset
WGLAZE_VW_L / _R   y +/-7461..7539   z   900 .. 3500     glazing above
```

The dado is the base course the glazing sits on. That junction at **z 900** is
the important line: a glasshouse of this date does not glaze to the ground, it
sits its glazing on a solid base, and the sill detail where the two meet is the
part worth modelling properly.

## Length — read this before choosing an approach

**466 m per flank, 932 m total.** Do not deliver this as one mesh. It must be a
**modular bay** that the engine instances, on a held module, the way the vault
lattice and planter kit already work. Report:

- triangles per bay,
- the module length you chose and why,
- projected total at the real bay count.

A bay that looks right at 400 tri is unusable at this length if it needs 12,000
instances; a bay that tiles at a coarse module reads as repetition on a 466 m
run. That tension is the actual design problem here, and it is yours to solve —
not something to discover after replication.

## Period and material — same building as the bulkhead

Follow `ROOTSTEAD_ENTRANCE_BULKHEAD_SPEC.md`. Same date, same institution, same
construction logic: **exposed-aggregate architectural precast**, recessed joints
with perished sealant, board-marked in-situ where the construction junction is
real, and **weather streaking that obeys the panel layout**.

Two things specific to this element:

- **It is at the bottom of the building**, so it takes splash-back, salt, moss
  and ground staining that the entrance bulkhead does not. Dirt should be
  heaviest at the base and fade upward — the inverse of a wall that streaks
  downward from its joints. Both readings should be present.
- **The terrace steps are real construction events.** `WDADO_TERR_A/B/C` sit at
  z 2600 / 1700 / 800 as the interior floor descends eastward. Where the dado
  steps, that is a junction with a visible detail, not a texture change.

## Obstructions the run must accommodate — all verified occupied

The dado cannot run blindly. In the band, on one or both flanks:

```
SUP_TERR_A/B/C_*_shaft   terrace support columns, ~152 wide, at
                         x 6074/7924/9774, 13074/14924/16774, 20074/21924/23774
GANT_Col                 x 21975..22025
CAFE* / CAFECAB*         cafe run, x 32996..39002
CH0/1/2_*                chambers, x 43600..45600
SO_*                     x 41975..44025
RAILPOST_* / RAIL_*      floor and terrace rails at various x
ENDDADO_post_W / _E      x -570..-370 and 45970..46170 — the run's two ends
```

Where a column lands in the run, the dado should **return into it** rather than
clip through — that is how a base course meets a structural member.

## Contract

- one object, no `g` groups, UVs present
- semantic material slot names (`M_FlankDado_PrecastPanel`, `_BoardFormed`,
  `_SealantJoint`, `_GroundStain`, …)
- report placement, local bounds and the module length
- **collision:** hand-authored boxes, no import hull, no convex decomposition.
  This one is simple — it is a straight wall — but the rule stands.
- verify against the obstruction table by testing face bounds, and report the
  intrusion count as zero

## Related

- `references/architecture/ROOTSTEAD_ENTRANCE_BULKHEAD_SPEC.md`
- `reference-kit/rootstead-vault/` — the envelope kit, for material continuity

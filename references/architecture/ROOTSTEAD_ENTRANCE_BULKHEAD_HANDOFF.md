# Rootstead entrance bulkhead — production handoff

`VD_RootsteadEntranceBulkhead` is the production replacement for
`CLAD_Bulkhead`: two solid, fully closed architectural wall wings with explicit
jamb/head/track notches, not a panel-box prototype and not a containment wall.
The accepted 1960s exposed-aggregate precast detail is retained on both west
faces, both outer returns, and both doorway returns.

## Import and placement

- Import `SourceMesh/architecture/VD_RootsteadEntranceBulkhead.obj` with its
  semantic MTL and place at world **(0, 0, 3500)**, zero rotation, unit scale.
- Local axes are world-aligned. Exact parsed bounds: X `-465.2..112`, Y
  `-1300..1300`, local Z `0..825` (world Z `3500..4325`). Structural bounds are
  X `-461..112`, Y `-1300..1300`. West relief reaches the accepted X=-465.2;
  outer-return matrix, joints, plinth, streaks, and stone backs recess into the
  wing so their face/tips stop exactly at Y=±1300 and never exceed it.
- One OBJ object, no groups, indexed UV on every corner, ten semantic slots.
  Every one of 1,970 disconnected structural/detail components is closed and
  manifold. The east X=112 face is undecorated and abuts WEND_Entry.
- Parsed production count: **23,776 triangles**. This is slightly below the
  approved 24,284 projection while preserving all 14 proud aggregate stones on
  every one of the 72 modules (1,008 stones); no return-face reduction was used.

The west grid remains six 146 uu bays per 876 uu wing and three 225 uu courses
above the distinct 150 uu board-formed plinth. Returns use three closure bays
at X `-461,-281,-101,112` (180/180/213). This intentional departure from equal
191 uu bays prevents the otherwise unavoidable joint at X=-79 from crossing
the device mounts.

All 1,008 aggregate stones remain present (14 on each of 72 modules), but the
production generator now varies each module deterministically by normalized
position jitter, dihedral transform/permutation, azimuth, size, and projection.
Independent parsed-centroid signatures are unique for 36/36 west, 18/18 outer
return, and 18/18 doorway-return modules. Weather runs likewise vary lateral
offset, width, 2–4 segment runout, length, and joint/fixing origin dominance;
parsed run profiles are unique for every module while remaining vertical.

Finished sealant joints are **3.2 uu (32 mm) wide**, with a closed reveal floor
recessed **12 uu** and a 1.2 uu arris chamfer. The verifier derives width from
parsed OBJ geometry and rejects anything outside 2.5–4.0 uu or above 4 uu.
Exactly 14 closed five-sided corner-loss spalls are distributed across
west/outer-return/door-return **6/4/4**. Parsed topology reports 13 distinct
footprint signatures, all four panel-corner orientations, zero rectangular-box
components, and 14/14 locally associated oxidized rebar lugs. Fracture concrete
uses restrained gray-tan evidence color; only exposed rebar remains brown.

Door-return geometry is clipped around the actual jamb/head/track occupancy.
All doorway-return relief recesses into its own wing; proud aggregate terminates
at Y=±424. The parsed result has zero vertices strictly inside |Y|<424 and zero
faces crossing it. Every parsed face AABB reports zero intrusions against the
door leaf, clear passage, jambs, head, sill, and track. WEND_Entry's broad AABB
is intentionally treated only as the X<=112 plane limit.

## Mounting faces

Cast, flat pads occupy X `-90..-10`, local Z `120..330`, flush to Y=±424 and
thicken only into their respective wings. They cover:

- `DOOR_PanelIn`: Y=-424, outward normal +Y; X `-84..-16`, world Z `3628..3722`.
- positive beacon: Y=424, outward normal -Y; X `-75..-49`, world Z `3775..3825`.
- negative beacon: Y=-424, outward normal +Y; same X/Z footprint.

Each verifier grid is 81/81 covered with zero joint/recess hits. Minimum pad-edge
clearance is 6 uu for the call button and 5 uu for either beacon.

## Collision — mandatory

Disable collision on the render mesh immediately after import. Do not accept an
import-generated hull, convex decomposition, or complex-as-simple collision.
Create the eight explicit box primitives in
`qa/rootstead_entrance_bulkhead/rootstead_entrance_bulkhead_collision_boxes.json`.
The manifest gives exact world centers, half extents, and min/max bounds suitable
for Unreal box primitives. They reproduce the notched structural mass, never
bridge |Y|<424, and independently verify at zero intrusions for every real
occupied exclusion.

Mark's final acceptance gate remains a PIE walk test after import: test the open
and closed door, the centreline through the threshold, both jamb edges, and the
plinth/return edges. The offline verifier cannot substitute for that engine test.

## QA and regeneration

```bash
python3 scripts/generate_rootstead_entrance_bulkhead.py
python3 scripts/verify_rootstead_entrance_bulkhead.py
```

Evidence lives in `qa/rootstead_entrance_bulkhead/`: exact metrics JSON,
collision manifest JSON, a 2600×1700 RGB production render re-parsed from the
written OBJ and rasterized from its actual 23,776 triangles/material slots with
a deterministic two-sided NumPy z-buffer, and the independent verification
JSON. Its four measured views are full west elevation, a high-resolution
three-bay west fracture detail, doorway return from the passage, and outer
return from outside. The orthographic detail was chosen because this compact
software renderer has axis-aligned cameras; the two return views expose the
recess direction while the enlarged west crop resolves fracture silhouettes.
Viewport coverage, semantic-color counts, and structural-color fractions are recorded
in metrics and independently thresholded. The accepted prototype and its gate
evidence remain unchanged under the existing `_Proto` paths.

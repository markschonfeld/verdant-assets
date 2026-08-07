# Rootstead entrance bulkhead — replace `CLAD_Bulkhead`

**Ask:** one detailed rigid mesh replacing the west entrance block's cladding.
It must be **solid** — the current build leaves a walkable void that exits the
building envelope.

## What is there now, and why it is going

```
CLAD_Bulkhead    BP_PanelClad_C
                 one ISM "Panels" — VD_WallPanel x 56 instances
                 world x -461..128   y -1300..1300   z -128..4325
```

56 repeats of a single wall panel. Mark's read: "mostly boxes arranged into a
shape instead of a proper mesh that would give us the detail and realism we
want." It also reads as riveted painted steel plate, which is a decade or two
off the building's period (see **Period** below).

### The void — the actual defect

Measured in-engine by line trace, sampled at y 200 / 700 / 1100 / 1290 and at
both z 3560 and z 3900:

```
slot width   300 uu, parallel-sided at every sample
west face    x -300    (BULK_L / BULK_R east face)
east face    x    0    (collision; the gable's visible glazing is at x ~-40)
floor        z 3500    (ENT_Deck)
open span    y +/-424 (door jambs) out to y +/-1300 (where CLAD_Bulkhead ends)
```

A 3 m wide, ~8.8 m long, 4 m tall void either side of the doorway, inside the
entrance block's 621 uu depth, open at both ends.

**The replacement must fill this solid.** No cavity, no service alley, no
walkable pocket. A sealed 3 m void is a void with extra steps.

### Why — this is an ARCHITECTURAL fix, not a containment fix

An earlier revision of this document said the player could walk out of the
building through this void. **That is no longer true and must not drive the
design.** PR #18's gable collision already closes it: wall boxes span x 0..85
for |y| 560..7513 and jamb boxes block x -509..0 at |y| 424..560, so the only
route — through the doorway then sideways — is stopped. Confirmed in play.

The reason to fill it is that **a real building does not have a 3 m gap between
its cladding and its glazing.** Mark: "we want to close it for realism and
architectural accuracy."

So do not add mass, depth or collision to make it harder to breach, and do not
treat this as a containment problem. Build the wall a 1960s institution would
actually have built, at the thickness that construction implies. Correctness is
the requirement; containment is solved elsewhere and is not this asset's job.

## Extents to build

```
close solid      x -461 .. 112      (through to the gable plane, not to -300)
                 y -1300 .. 1300
                 z  3500 .. 4325    above deck; below 3500 is understructure
```

Stop at y +/-1300 as the current one does. The remaining length either side is
an in-engine job (deck-edge balustrade), not part of this delivery.

## Must stay clear — verified occupied, do not intrude

```
door leaf envelope   x -397..-353   y +/-416    z 3508..3892   (animated)
clear doorway        x -509..112    y +/-424    z 3500..3892
DOOR_JambL/R         x -412..-350   |y| 400..462  z 3500..3950
DOOR_Head            x -412..-350   y +/-462    z 3892..3950
DOOR_Sill            x -445..-305   y +/-400    z 3500..3508
DOOR_Track           x -410..-352   y +/-462    z 3866..3892
WEND_Entry gable     x -509..112    y +/-7513   z 3486..9691
```

`WEND_Entry` is the merged endwall+entrance from PR #18. The bulkhead abuts its
inner face; it must not push east of **x 112** or it fouls the `VEST_Frame`
threshold at x 128.

## Mountings the new mesh must provide

These are currently fixed to the old cladding and the door jambs, and will be
re-seated onto the new mesh in-engine. Give them flat, plumb mounting faces at
these positions — a panel joint or a recess running through them makes them
impossible to sit cleanly:

```
DOOR_PanelIn (call button)   x -84..-16   y -424..-408   z 3628..3722
BEACON_Body_6 / _7           x -75..-49   |y| 370..400   z 3775..3825
```

## Period — this is the part that matters

Rootstead is a **1960s institutional botanical glasshouse**. Two real
contemporaries, both worth looking at:

- **Climatron**, Missouri Botanical Garden, 1960 (Murphy & Mackey). Triangulated
  steel framing, ~2,500 panels, the first geodesic dome clad in **rigid acrylic
  rather than glass**. This is already Rootstead's envelope language.
- **Mitchell Park Domes**, Milwaukee, 1959–67 (Donald Grieb). A **precast
  concrete frame** carrying **aluminium-framed wire glass**. The solid parts of
  a glasshouse of this date are concrete, not fabricated plate.

**Architectural precast came into wide use in exactly this decade**, and the
dominant decorative system was **Mo-Sai exposed-aggregate** panelling (Earley
Studio / Dextone / Falco lineage). Deep solid precast sections were specified
for institutional buildings needing thickness — which is what a wall beside a
freight lock in a research facility would be.

### So: exposed-aggregate architectural precast, not steel plate

Detail worth carrying, all of it period-justified and all of it giving the
"gone to seed" read for free:

- **Panel module** with recessed joints and chamfered arrises. Pick a module and
  hold it — repetition is correct here, it is a precast system.
- **Perished joint sealant** — shrunken, split, fallen out in places.
- **Exposed aggregate** face: the coarse aggregate proud of the matrix.
- **Board-marked in-situ plinth** at the base, distinct from the precast above —
  a real construction junction, not a texture change.
- **Weather streaking that obeys the geometry.** Exposed aggregate streaks
  *predictably*: vertical runs below every joint, sill and fixing. Streaks that
  ignore the panel layout are the tell that it was painted on.
- **Spalling at panel corners** exposing rebar or fixing lugs, sparingly.

Avoid: rivets, plate seams, welds, painted steel. Those read industrial/wartime
and are wrong for the date.

## Collision — the same rule as PR #18

Do not accept an import-generated hull, and do not use convex decomposition.
This mesh sits directly beside a doorway that must stay traversable; a hull will
bridge it. Segmented **box** primitives, authored by hand, and **no primitive may
cross the clear doorway** at `x -509..112, y +/-424, z 3500..3892`. See
`references/architecture/ROOTSTEAD_WEST_ENDWALL_ENTRY_HANDOFF.md` for the full
rationale — this is the third asset where it has mattered.

## Contract

- single object, no `g` groups, UVs present
- named material slots, semantic (e.g. `M_EntranceBulkhead_PrecastPanel`,
  `_BoardFormedPlinth`, `_SealantJoint`, `_SpallReveal`)
- report the placement transform and local bounds; state the triangle count
  before scaling any repeated detail across the whole wall
- verify against the "must stay clear" table above **by testing face bounding
  boxes against those volumes**, and report the intrusion count as zero

## Related

- `references/architecture/ROOTSTEAD_WEST_ENDWALL_ENTRY_HANDOFF.md`
- `references/architecture/WEST_ENDWALL_ENTRY_JOINT_REWORK.md`
- `reference-kit/rootstead-vault/` — the envelope kit, for material continuity

# Rootstead entrance doors — replace `DOOR_LeafL` / `DOOR_LeafR`

**Ask:** the two sliding leaves of the west entrance, as hero assets. This is
the door the player walks through on the reveal, at arm's length, more than
once. It is currently 322 triangles each.

Mark: *"the doors look terrible and the glass doesn't look real — we want it
smudgy and aged from people touching it."*

## The hard constraint: these are ANIMATED, and the pivot cannot move

`SEQ_BlastDoor` drives them with **absolute world Location.Y keys**. Move the
pivot relative to the geometry and the doors will animate to the wrong place —
silently, and only when the door is used.

```
DOOR_LeafL   pivot (-375, -200, 3700)   Location.Y keys  -200 -> -600
DOOR_LeafR   pivot (-375,  200, 3700)   Location.Y keys   200 ->  600
```

So each mesh's **local origin must sit exactly where that pivot sits** in the
geometry. For the left leaf, the origin is 216 uu from its outer edge and
212 uu from its meeting edge. Get this wrong and nothing looks wrong until the
door opens.

## Envelope — measured, and it is a KEEP-OUT in another asset

```
DOOR_LeafL   x -397..-353   y -416.. 12   z 3508..3892
DOOR_LeafR   x -397..-353   y  -12..416   z 3508..3892
```

`WEND_Entry` (PR #18) was built with **this exact volume deliberately empty**
so the leaves keep animating in it. **Do not exceed it in any axis.** X is only
**44 uu** — that is the whole door thickness, frame included.

Two details in those numbers that must survive:

- **The 24 uu meeting-stile overlap.** Left runs to y +12, right starts at
  y −12. Closed, they overlap at the centre. That is what stops a shut door
  showing a light line down the middle.
- **Open, leaf L reaches y −816.** It retracts into the pocket behind the new
  mesh's jamb. Nothing may stick out that would foul the reveal at |y| 424..560.

## Integrate the hazard tape

`DOOR_ChevL` / `DOOR_ChevR` are currently separate 4 uu engine cubes stuck on
the front face at x −401..−397, z 3508..3598, carrying `M_Chevron`. They animate
on their own sequence bindings with identical keys.

**Fold them into the leaf mesh as their own material slot.** Applied hazard tape
is part of the door, not an object floating in front of it, and at 4 uu proud it
currently reads as a slab. Give it real thickness, a lifting edge, and a lower
margin where it has been scuffed off. The existing actors and their sequence
bindings will be retired in-engine once the new leaves land — that is my job,
not yours.

## The glass — this is the point of the whole request

The leaves are obscured/frosted glazing in an aluminium frame, which is right
for the date: **Mitchell Park Domes (1959–67) glazed in aluminium-framed wire
glass**, and this is the same class of building. The failure now is that the
glass reads as a flat lit panel, not as a surface people have touched for sixty
years.

What "smudgy and aged" means, concretely, and all of it should follow the
geometry rather than be scattered:

- **Hand grease at push height.** The heaviest soiling is a band around
  **z 3650..3750** — hand height above the sill at 3508. Palm smears, finger
  drag marks, a darker patch where the push plate is or was. This is the single
  most important detail; it is what makes glass read as *used*.
- **Cleaning swirls.** Arcs from a cloth, brighter than the surrounding film,
  concentrated in the middle of each pane and never reaching the corners.
- **Corner and edge grime** where the cloth never went, heaviest along the
  bottom rail and in the frame rebate.
- **Etch wear.** Obscured glass loses its frosting where it is touched most —
  the push band should be slightly *clearer* than the rest, not just dirtier.
- **Frame:** anodised aluminium, chalked and pitted, with the anodising worn
  through to bright metal on the leading stile where hands and trolleys hit it.
- **Kick damage** at the bottom rail: scuffs, a dented kick plate, scratches
  that run horizontally rather than randomly.

Avoid a uniform noise overlay. Every mark above has a cause and a place; that is
what separates this from a dirt texture.

## Contract

- **two meshes**, `_L` and `_R` — they are separate actors with separate pivots
- semantic slots: `M_EntranceLeaf_ObscuredGlass`, `_AluminiumFrame`,
  `_HazardTape`, `_KickPlate`
- one object each, no `g` groups, UVs present
- **report the pivot position relative to the geometry** and confirm it matches
  the table above — state it explicitly, do not leave it implied
- triangle budget: these are two hero assets seen at arm's length. Several
  thousand each is fine. Report the count; do not optimise them down to the
  current 322.
- collision: **none needed** — the leaves inherit the animation setup and the
  doorway collision is authored on `WEND_Entry`. Do not add primitives.

## Note on the existing leaf replacement

PR #18 shipped an optional `VD_RootsteadWestEndwallEntry_Leaves.obj` for these
two actors. It was never imported. It is 2 KB and carries only a frosted-glass
and a frame slot, so it does not meet this brief — supersede it rather than
extend it, but its envelope numbers were correct and match the table above.

## Related

- `references/architecture/ROOTSTEAD_WEST_ENDWALL_ENTRY_HANDOFF.md` — the leaf
  envelope as a keep-out
- `references/architecture/ROOTSTEAD_ENTRANCE_BULKHEAD_SPEC.md` — same building,
  same date, material continuity

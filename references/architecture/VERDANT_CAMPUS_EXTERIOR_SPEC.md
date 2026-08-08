# Verdant Institute — agricultural research campus exterior

**Ask:** the buildings visible outside the Rootstead greenhouse. Background
massing, not playable architecture.

## The fiction

The **Verdant Institute of Technology** has its main campus in the nearby city.
This is its **agricultural research station**: isolated, rural-suburban, its own
grounds. The player drives out to it after an SOS.

Real-world analogue: the University of Minnesota's agricultural and arboretum
facilities out at Chaska, well separated from the main Minneapolis campus.

On site: the **greenhouse** (built — this is Rootstead), **smaller laboratory
buildings**, an **office block with classrooms**, a **lecture hall**, and
**graduate residence halls**. Same institution, same period as the greenhouse:
**1960s, exposed-aggregate precast**, per
`ROOTSTEAD_ENTRANCE_BULKHEAD_SPEC.md`.

## What is actually visible — this governs everything

The greenhouse is glass, but it has an **opaque dado from z 0 to z 900** along
both flanks. That base course is what the player sees over, and it sets a hard
sightline. Ground is at **z -1050**.

Measured from the built geometry:

```
viewpoint          eye z    nearest visible GROUND
west deck           3670     ~150 m
terrace A           2770     ~153 m
terrace B           1870     ~225 m
terrace C            970    ~2160 m
east floor           170     never — dado top is 730 above eye level
```

**Minimum height for a building to break the dado line and be seen at all:**

```
from terrace C (eye 970)      at 200 m out:  18.3 m tall
                              at 400 m out:  16.5 m tall
from east floor (eye 170)     at 200 m out:  32 m tall
                              at 400 m out:  51 m tall
```

Two consequences:

1. **Ground within ~150 m is not visible from inside; ground beyond it very
   much is.** Only the near band can be skipped. Mark, correcting an earlier
   draft of this document: *"Roadway and grass etc would be visible. Just on the
   N and S sides more than E and W."* The long flanks are 466 m of glass each,
   so the ground they look at is the largest single surface in view. **Ground
   treatment is required on all four sides** — deprioritise the first 150 m, not
   the whole thing.
2. **From the east half, nothing shorter than ~30 m breaks the sightline.** So
   the east reads as horizon rather than campus, and low buildings there would
   be invisible.

## Bound the view — the ground currently runs to the horizon

`GROUND_Plane` is a single flat sheet spanning 40 km. Whatever else happens, the
view needs closing off at a credible distance, or the campus reads as a few
buildings adrift on an infinite plain.

Mark's call: **hills or low mountains ringing the campus**, far enough out to
sit beyond everything built, close enough to stop the eye. That also removes any
need to model ground past the ring.

## The campus is CANONICAL GEOGRAPHY, not backdrop

This is the change that most affects how these are built. Mark intends the
player to **move between these buildings as separate levels**, so their
positions, footprints and entrances have to stay consistent from level to level.

Consequences for this delivery:

- Placement is a **shared fact**, not a dressing decision. Once a building sits
  somewhere it stays there, and the interior level built later must match the
  exterior the player saw.
- Give each building a **plausible entrance and footprint** even though no
  interior exists yet — a door that later has to move is a continuity break.
- Silhouette work is still the priority for *this* level, but do not model
  anything that would have to be contradicted later.

## Layout — cluster west, leave the east as horizon

Put the campus in an arc **west and south-west of the greenhouse, 150–400 m
out**. That is where the entrance, the freight tunnel and the skyway already
are, it is the highest vantage in the level, and it is the only place with real
ground visibility.

**Leave the east end with nothing but treeline and horizon.** The player walks
466 m *away* from every sign of other people, and the building runs out into
empty country. That is the geography doing the storytelling for a game where
nobody answered the SOS.

## Scope — the whole set is wanted

Mark: *"skyway first but we want them all."* This is not a pick-the-visible-ones
exercise. Every item below is in scope; the order is about sequencing, not
about which ones survive a budget cut.

**Already placed, compose around it:** `STACK_Spire` sits at `(-25000, -14000)`,
282 m west-south-west, inside this arc. It is the microwave relay that sent the
SOS (`references/props/SPIRE_SIGNAL_MAST_REWORK.md`) and at 180 m it is the
tallest thing on site by a wide margin. It is context for the layout, not a
delivery step here.

## Delivery order

1. **The skyway.** First, by Mark's call. The freight tunnel runs west from the
   greenhouse to about x -8000 and currently dead-ends at a blocking volume.
   Turning it into an elevated enclosed walkway arriving at the office block
   fixes that dead end and delivers the structure the player meets first, on
   the way in. Exterior form only; the interior is a separate job.
2. **The office/classroom block** — the skyway's destination, and the primary
   built silhouette after the mast.
3. **The lecture hall.**
4. **Laboratory buildings** — note the *smaller* lab has moved out of this spec
   and attaches to the mast base instead; these are the remaining ones.
5. **Graduate residence halls** — furthest out, low massing, reads as a cluster.
6. **Ground treatment** beyond ~150 m, all four sides, N and S first.
7. **The bounding hills.**

Items 6 and 7 are as much a part of "all" as the buildings are — a campus of
good massing on a flat infinite plain will still read as unfinished.

## What these assets are, and are not

They are seen at **150–400 m, through dirty acrylic, in fog**. So:

- **Silhouette and roofline carry everything.** Plant rooms, tanks, vents,
  stair overruns, parapet steps. A flat-topped box reads as a placeholder at any
  distance.
- **Window grids matter**, façade micro-detail does not. Panel joints will not
  resolve; a rhythm of openings will.
- **No interiors, no door furniture, no reachable detail.**
- Nanite-friendly, and report triangle counts. These are background — if any
  single building costs more than the entrance bulkhead's 23,720, something is
  wrong.

## Deliberately not in this spec

- **Ground treatment inside 150 m only.** Beyond that it is required — see the
  visibility section. The near band is the only part that can be skipped.
- **Time of day.** The sun is `pitch -42, yaw -60` and stays there. It produces
  the god rays the interior depends on. Build to that light.

## Related

- `references/architecture/ROOTSTEAD_ENTRANCE_BULKHEAD_SPEC.md` — period and material
- `references/architecture/ROOTSTEAD_FLANK_DADO_SPEC.md` — the dado that sets the sightline
- `references/lore/PLANT_ANIMAL_HYBRID_SCIENCE_BRIEF.md`

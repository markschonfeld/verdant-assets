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

Two consequences, and both are scope decisions:

1. **Ground detail near the building is invisible.** Roadway, kerbs, grass and
   paths within 150 m of the greenhouse will never be seen from inside it. Do
   not build them for this level.
2. **From the east half, nothing on the campus is visible** unless it is over
   30 m tall — ten storeys, which this campus does not have. So the east is
   empty by geometry, not by omission.

## Layout — cluster west, leave the east empty

Put the campus in an arc **west and south-west of the greenhouse, 150–400 m
out**. That is where the entrance, the freight tunnel and the skyway already
are, it is the highest vantage in the level, and it is the only place with real
ground visibility.

**Leave the east end with nothing but treeline and horizon.** The player walks
466 m *away* from every sign of other people, and the building runs out into
empty country. That is the geography doing the storytelling for a game where
nobody answered the SOS.

## Delivery order

1. **The skyway.** The freight tunnel runs west from the greenhouse to about
   x -8000 and currently stops at a blocking volume. It should become an
   elevated enclosed walkway that arrives at the office block — which fixes a
   dead end and delivers the most visible structure at the same time. Interior
   is a separate job; this is the exterior form.
2. **The office/classroom block** — the skyway's destination. The tallest thing
   on site and the primary silhouette.
3. **Lecture hall and laboratory buildings** — the mid-distance arc.
4. **Graduate residence halls** — furthest out, low massing, read as a cluster.

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

- **Ground treatment** (asphalt, grass, kerbs) — invisible inside 150 m; will
  be specced separately if the arrival sequence ever needs it.
- **Time of day.** The sun is `pitch -42, yaw -60` and stays there. It produces
  the god rays the interior depends on. Build to that light.

## Related

- `references/architecture/ROOTSTEAD_ENTRANCE_BULKHEAD_SPEC.md` — period and material
- `references/architecture/ROOTSTEAD_FLANK_DADO_SPEC.md` — the dado that sets the sightline
- `references/lore/PLANT_ANIMAL_HYBRID_SCIENCE_BRIEF.md`

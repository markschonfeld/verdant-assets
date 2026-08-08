# Spire rework — the microwave relay mast that sent the SOS

**Status:** revision of the PR #11 landmark (`VD_Spire`, `VD_SpireBase`,
`VD_SpireLights`), already imported and placed as `STACK_Spire` at
`(60000, 0)`, 180 m tall. **Do not start from scratch** — the placement, the
lights-separated-for-Nanite split, and the height all stay.

## What changes, and why

PR #11 built it as a *research exhaust stack later adapted as a signal mast*.
That was a reasonable guess when the object had no story. It now has one:

> **This is the mast that sent the SOS.** It is a microwave relay linking the
> isolated research station back to the Verdant Institute's main campus in the
> city. It is the reason anyone knows Eden Prime called for help.

So it stops being a chimney with an aerial on top and becomes a
**telecommunications tower** — which is a different silhouette, not a reskin.

## Form reference

Mark's chosen silhouette is the **Helpterberg radio tower** (Woldegk, Germany;
170.3 m; reinforced concrete): a tapered concrete shaft, circular galleries at
intervals, antenna arrays, and an upper steel lattice mast in red/white
aviation banding, with a **long low building attached at the base**.

**But build the period from AT&T Long Lines, not from Helpterberg.**
Helpterberg is 1981 — two decades after this facility. The correct
contemporaries are the Bell System's Long Lines microwave relay sites of the
1950s–60s, which share the same form and are the right date.

### The period signature: KS-15676 horn-reflector antennas

These, not modern parabolic dishes, are what belongs on a 1960s relay tower.
A pyramidal horn feeding an integrated paraboloidal reflector — the
"sugar-scoop" profile. They were the defining feature of Long Lines towers
after the TD-2 rollout, replacing the older KS-5759 delay-lens antennas around
1960. Getting this one detail right will date the whole object correctly;
getting it wrong (round dishes) will date it to the 1990s.

### Other period detail worth carrying

Long Lines sites were **semi-hardened** — built to keep working through
nuclear fallout:

- **blast shields over ventilation intakes** at the base building
- heavy concrete rather than lattice for the lower structure
- a generator house or fuel tank, for the standby diesel
- **waveguide runs** climbing the shaft in a bundled tray, elbowing out to
  each horn — the single most legible "this is a radio tower" detail
- caged access ladder, gallery handrails, conduit
- aircraft warning lenses (already separated into `VD_SpireLights`)

This hardening is not decoration here: the greenhouse has blast doors and a
freight lock. Same institution, same decade, same anxieties.

## The attached building — new

Mark: *"we'll make the smaller laboratory building attached the same way
there's a building attached in the photo."*

So the **smaller laboratory** from `VERDANT_CAMPUS_EXTERIOR_SPEC.md` is no
longer a separate free-standing block — it attaches to the tower base, as the
equipment building does at Helpterberg and at every Long Lines site.

- single storey, long and low, hard against the shaft
- reads as **equipment hall plus laboratory** — this is where the relay gear
  lived and where the station's smaller lab work happened
- blast-shielded vents, few windows, a service door and a roller shutter
- same **1960s exposed-aggregate precast** as the entrance bulkhead and flank
  dado, so it belongs to the same institution

## Constraints

```
height        ~180 m — keep it; Helpterberg is 170.3 m, close enough
placement     currently (60000, 0). MAY MOVE — do not bake world position
              into the geometry. Origin at the base centre, z 0.
lights        keep VD_SpireLights separate: translucent geometry stays
              non-Nanite while the shaft and base remain Nanite-capable.
              That split was right and has since been vindicated project-wide.
```

**This is the most visible object in the level.** It clears the sightline
threshold by ~10x from terrace C and ~5.6x from the east floor, and the player
spends the entire level walking toward it down 466 m of hall. Silhouette
quality matters more here than on anything else in the campus spec.

## Budget

Report triangle counts before scaling repeated detail. Unlike the campus
background buildings, this one earns more — it is large, close, and always in
frame. But the horns and galleries are the parts worth spending on; the shaft
is a tapered cylinder and should cost almost nothing.

## Related

- `references/props/SPIRE_LANDMARK_HANDOFF.md` — the PR #11 delivery this revises
- `references/architecture/VERDANT_CAMPUS_EXTERIOR_SPEC.md` — the smaller lab
  moves out of that spec and into this one
- `references/architecture/ROOTSTEAD_ENTRANCE_BULKHEAD_SPEC.md` — precast direction

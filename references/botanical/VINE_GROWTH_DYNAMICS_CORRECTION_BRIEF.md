# Vine growth dynamics correction brief

**Audience:** Claude / procedural-geometry implementation

**Review source:** Mark's exterior and interior Play-mode screenshots, 2026-08-06

**Verdict:** **Not visually shippable yet.** Branch count has improved, but the result still reads as procedural wire because support state, gravity, wind hierarchy, foliage mass, flower state, and player clearance are not yet coupled.

This brief governs the mature combined growth of **Solandra maxima** and **Aristolochia macrophylla** around the west blast-door trellis. It supplements:

- `climber_branching_architecture_reference_2400x1800.png`
- `vine_weight_wind_bloom_reference_2400x1800.png`
- `CLIMBER_BRANCHING_PHOTO_REFERENCE.md`
- the two species trellis sheets and stem/bark sheet

## What the screenshots show

### Exterior / greenhouse side

See `qa/vine_growth_review_2026-08-06/annotated_exterior.png`.

1. **The silhouette is a rectangular wire hedge.** The top and jambs have nearly even line density, so the growth follows the frame as a procedural border rather than accumulating as a living canopy. The head needs irregular supported knots and weighted lobes; the two corners should be denser than the middle.
2. **Long secondary and tertiary stems leave support as straight spears.** Several project upward or sideways for metres. A young distal tip can search upward for a short distance; the parent run cannot remain rigid once unsupported.
3. **The inner helix is legible as a generated coil.** Twining is valid only around an actual support or another stem. A helix must stop at detachment and should normally be obscured by foliage in a mature canopy.
4. **There is line density but little canopy mass.** Tiny, uniformly scattered cards read as confetti around dark curves. Three to five overlapping foliage layers means real occlusion: most tertiary topology should be hidden from the hero view.
5. **There is no bloom system.** This much mature, warm greenhouse growth should carry many Solandra cups and buds. Pipe flowers remain predominantly concealed, except for the intentional warmth-biased VERDANT mutation near the door.
6. **The growth intrudes into the entrance without weight.** Intrusion is desirable, but it needs to drape from the header and jambs. Woody stems should not lance into the central player corridor.

### Interior / looking out

See `qa/vine_growth_review_2026-08-06/annotated_interior.png`.

1. **Long free stems are gravity-invariant.** They stay straight at arbitrary diagonals or descend like rods. Their tangent should relax downward as unsupported length increases.
2. **The left side contains an eye-level lance.** Replace it with a weighted arc attached at the jamb, or prune it to flexible leaves and tips at the edge.
3. **Several center and right stems approach the floor as straight lines.** Hanging shoots need curved shoulders, taper, leaf weight, and varied termination heights.
4. **The canopy reads as a coil/grid.** Repeated loops and radial crossings expose procedural phase. Break phase, delete free-space helices, and occlude most thin stems with foliage.
5. **The opening has no large focal flowers.** Placement must be driven by branch order and bloom state, not by sparse random node decoration.
6. **The passage lacks a soft clearance envelope.** Leaves, flowers, and a few thin tips may brush the edges; load-bearing stems must stay out of the traversable center.

## Required generator change: support state before curve shape

Do **not** generate a spline and then decorate it. Each run must first be classified:

```text
BOUND      both the run and its tangent conform to a trellis member or host stem
BRIDGE     both endpoints are attached; the free span sags between them
FREE       one endpoint is attached; inherited tangent relaxes downward
SEARCHING  only the distal 0.35–0.60 m may turn upward/toward warmth
```

Each branch node may independently carry a leaf, an activated lateral, a flower/bud state, or nothing. The branch itself comes from the axillary bud; the leaf does not become the branch.

### Bound/twining runs

- Construct a helix around the **actual support centerline**.
- Radius equals support radius + stem radius + contact clearance.
- Stop the helix at the exact support-detachment point.
- Never continue a mathematically convenient helix through open space.
- Break visible periodicity with changing pitch, interrupted wraps, node swelling, contact flattening, and foliage occlusion.
- The production handedness convention remains ascending-clockwise for a given plant; it is an art convention, not a universal botanical claim.

### Two-anchor bridge

Use a sagged curve rather than a straight chord. A sufficient art-directed bridge model is:

```text
P(t) = lerp(P0, P1) - Up * 4 * sag * t * (1 - t) + lateral_noise(t)
```

- Noise must be zero at both anchors.
- Sag increases with chord length and flexibility.
- A mature primary may hold a shallow one-bay arc.
- Secondary and tertiary spans sag much more visibly.
- Any bridge longer than the permitted support interval should seek another support or become a hanging run.

### One-anchor free run

Use a cubic curve whose first control point inherits the parent tangent and whose second control point is pulled downward:

```text
P0 = attachment
P1 = P0 + inherited_tangent * 0.20–0.30 * length
P2 = P1 + lateral_bias - Up * gravity_drop
P3 = P2 + tip_bias - Up * terminal_drop
```

Production gates:

- Beyond **0.75 m** unsupported, droop must be visually obvious.
- Beyond **1.5 m**, a run cannot remain a horizontal or upward straight rod.
- Only the terminal **0.35–0.60 m** may rise as a searching tip.
- Vary end heights and curvature. Do not let hanging runs terminate on one shared horizontal line.
- Thick old primaries bend least; secondaries, tertiaries, and new tips bend progressively more.

Suggested relative flexibility values, to be tuned in Play mode:

| Branch class | Relative flexibility |
| --- | ---: |
| old structural primary | 0.15 |
| young primary | 0.30 |
| secondary | 0.55 |
| tertiary | 0.80 |
| searching tip | 1.00 |

These are production heuristics, not measured elastic moduli.

## Doorway clearance and silhouette

Use a central **woody-stem exclusion envelope approximately 1.5 m wide × 2.2 m high** through the opening.

- Load-bearing primaries and secondaries: outside the envelope.
- Leaves, flowers, and a few soft tertiary tips: may intrude **0.10–0.25 m** at its edges.
- At the head, allow weighted drapes but preserve a readable central passage.
- At the jamb-to-head corners, retain the dense knot plus hanging skirt.
- Keep the exterior silhouette asymmetric: one corner may be heavier, but both must remain structurally attached.
- Remove straight stems that terminate at eye or throat height in the central corridor.

## Replace line density with canopy density

The current build has too many visible curves and too little foliage. For the next pass:

- Reduce visible secondary/tertiary line count by roughly **25–40%**.
- Increase leaf-bearing tertiary shoots and species-scale leaves until the hero views contain **three to five overlapping foliage layers**.
- The branch hierarchy should be sensed through occasional gaps, not exposed like a diagram.
- Cluster leaves on live subordinate growth; do not scatter cards uniformly through a volume.
- Use larger overlapping cordate Aristolochia leaves as the curtain.
- Use broader, leathery Solandra leaves around its heavier framework and flowers.
- Preserve deliberate holes around the door and at a few trellis bays so the mass does not become a solid green wall.
- Do not solve density by adding more long splines. Solve it with short foliated laterals, overlap, scale, and occlusion.

## Bloom system

The following counts are **hero-shot art targets**, not botanical measurements.

### Solandra maxima

Across the complete jamb–head–jamb trellis at peak greenhouse bloom:

- **20–35 open cups**
- **30–50 buds or aging flowers**
- roughly **60%** of the strongest bloom mass around head corners and warmth-facing interior growth

Placement rules:

- Attach cups and buds to short tertiary/terminal flowering shoots.
- Do not put one flower on every node.
- The flower and its supporting shoot should bend under the cup's weight.
- Mix outward, downward, three-quarter, occluded, and back-facing orientations.
- Avoid evenly spaced marquee-light distribution.
- Use open, bud, and aging states so the canopy does not look duplicated.

The new cards are:

- `cutouts/solandra_maxima_flower_open_1024.png`
- `cutouts/solandra_maxima_flower_bud_1024.png`

They are appropriate for mid-distance cards/LODs and as colour/silhouette guides. Hero flowers near the doorway should still use a shallow three-dimensional cup so the rim and throat survive close viewing.

### Aristolochia macrophylla

- **12–20 total flowers** across the full frame
- conceal roughly **70%** beneath or behind the leaf curtain
- deliberately visible mutation-biased examples should concentrate near the doorway warmth gradient

Pipe flowers arise from leaf axils and hang beneath foliage. The existing `aristolochia_pipe_flower_1024.png` card should not be distributed as an exposed floral carpet.

## Wind and secondary motion

Gravity belongs in generated geometry. Wind belongs mainly in controlled runtime deformation.

Recommended vertex-colour or UV-channel wind weights:

| Element | Weight |
| --- | ---: |
| old primary | 0.00–0.05 |
| secondary | 0.05–0.15 |
| tertiary | 0.20–0.45 |
| searching tip | 0.40–0.70 |
| leaf/flower extremity | 0.40–1.00 |

Runtime behavior:

- Use one low-frequency phase per connected branch family, not one random phase per spline or leaf.
- Suggested indoor greenhouse base motion: **0.08–0.25 Hz**.
- Thick stems should appear nearly anchored.
- Thin tips may move approximately **1–3 cm** in normal air movement; leaves and flower rims may move **3–8 cm** at their outer edges.
- Add occasional slow gust envelopes, not constant rapid oscillation.
- Motion amplitude increases continuously from branch base to tip.
- Avoid synchronous global swaying and independent high-frequency leaf jitter.
- Collisions and clearance must be correct in the rest pose; WPO is secondary motion, not a way to hide bad spline paths.

## Materials and scale

- Use the merged Solandra and Aristolochia bark PBR sets; do not retain brown-tinted `concrete_cast`.
- Bark grain axis is texture **V/image Y**; circumference is **U/image X**. Swap the mesh UV axes as already noted if arc length currently advances along U.
- Normal maps are DirectX tangent-space, green-down.
- Use two-sided foliage shading with restrained subsurface/transmission. The current cyan cast should not flatten both species into one material.
- Vary leaf roughness and orientation by species; do not use brightness variation as a substitute for morphology.
- Use branch taper. Tertiary tips should not share the same wire diameter as secondary runs.

## Acceptance test for the next screenshots

The pass is acceptable when all are true:

1. No unsupported stem longer than 1.5 m remains straight, horizontal, or upward-pointing.
2. No helix is visible continuing through free space.
3. Hanging runs have curved shoulders, taper, and varied terminal heights.
4. The central 1.5 m × 2.2 m passage contains no woody stems; only soft edge intrusion remains.
5. Exterior and interior hero views show three to five foliage layers, while most tertiary stems are occluded.
6. Solandra bloom is immediately visible at hero distance, with open/bud/aging variation and weighted attachments.
7. Aristolochia flowers remain mostly concealed except for the warmth-biased mutation zone.
8. Wind motion is coherent by branch family and increases toward leaves/tips; thick bearing wood remains stable.
9. From the exterior, the silhouette reads as asymmetric, weighted growth rather than a rectangular wire frame.
10. From the interior, no line reads as an eye-level spear or a rigid rod reaching toward the floor.

Do not tune flower count, wind, or material polish until the support-state and gravity pass is correct. The curve architecture is the load-bearing fix.
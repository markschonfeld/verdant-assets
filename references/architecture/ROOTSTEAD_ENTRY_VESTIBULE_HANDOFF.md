# Rootstead west-entry vestibule handoff

## Design intent

This kit replaces the engine-primitive entrance enclosure with a later **glazed
steel greenhouse porch** bolted to the Rootstead west concrete end wall. It is
light, repairable, and visibly younger than the bunker fabric: narrow painted
steel sections, rubber glazing seats, shallow pitched roof, gutters, wall shoes,
selective laminated replacement panes, and a few bare-steel repairs.

The existing 15.9 m wide × 7.8 m tall trellis and its vines remain inside the
porch. The kit does not include, replace, or modify that trellis, the blast door,
or any interactive door leaf.

## Coordinates, origin, and placement

- Units: **1 OBJ unit = 1 Unreal uu = 1 cm**.
- Axis: `+Z` up; `+X` projects east into the greenhouse; `+/-Y` spans the doorway.
- Shared pivot: porch **back-bottom-centre** `(0, 0, 0)`.
- Place both meshes at world **`(128, 0, 3500)`**, rotation `(0, 0, 0)`, uniform scale `1.0`.
- Overall opaque-frame bounds: `X 0…370`, `Y -972…972`, `Z 0…908.97` cm.
- Glazing bounds: `X 12…361`, `Y -941…941`, `Z 78…898.98` cm.
- Internal trellis clearance: **18.4 m wide × 8.1 m at the eave**.
- East walk-through: **9.2 m clear width × 5.2 m clear height**.

The 19.44 m maximum width is at the back-wall shoe plates. The primary porch
frame is narrower; do not non-uniformly scale it to remove those attachment
plates.

## Meshes

| OBJ | Role | Unreal settings |
|---|---|---|
| `VD_RootsteadEntryVestibule_Frame.obj` | opaque painted/bare steel frame, seals, kickplates, gutters, fasteners | Opaque; Nanite may be enabled; simple collision only if needed |
| `VD_RootsteadEntryVestibule_Glazing.obj` | aged original panes and clearer laminated repairs | **Translucent; Nanite OFF; NoCollision** |
| `VD_RootsteadEntryVestibule.mtl` | named material-slot declarations | retain `usemtl` assignments on import |

Each OBJ contains exactly one `o` object, **no `g` group records**, one UV0
texture-coordinate index on every face corner, and `usemtl` records for named
Unreal material slots. Do not ask the importer to combine these two OBJ files;
they must remain separate because of translucency.

The glazing is authored as single-surface panes. Use a two-sided translucent
material unless the final Unreal import is explicitly given thickness.

## Material slots

### Opaque frame

- `M_Vestibule_PaintedSteel`: distressed Institute blue-green paint over steel.
- `M_Vestibule_BareSteel`: galvanized/bare repairs, wall shoes, gutters, fasteners.
- `M_Vestibule_RubberSeal`: dark glazing gaskets and shadow lines.
- `M_Vestibule_Kickplate`: dull sacrificial lower steel skirt.

### Glazing

- `M_Vestibule_GlassAged`: older green-grey panes with grime, mineral streaks,
  scratches, and restrained clouding.
- `M_Vestibule_GlassRepair`: clearer, slightly cooler laminated replacement panes.

Use UV-dependent dirt/streak breakup or the existing world-space materials; both
paths are supported. The UV0 density is one UV unit per metre under dominant-axis
planar projection. Unreal may generate its own non-overlapping lightmap channel
for the opaque frame if baked lighting requires one.

## Collision and gameplay

- Keep `VD_RootsteadEntryVestibule_Glazing` at `NoCollision`.
- Prefer simple authored blocking volumes for the side walls/frame rather than
  complex-as-simple collision.
- The east face is intentionally empty inside `Y -460…460`, `Z 0…520`; no mesh
  face intrudes into that opening.
- Confirm the trellis, vine cards, and blast-door interaction remain reachable in
  Play mode before deleting the placeholder boxes.

## Reproduction and QA

From the repository root:

```bash
python3 scripts/generate_rootstead_entry_vestibule.py
python3 scripts/verify_rootstead_entry_vestibule.py
```

The verifier checks the one-object/no-group OBJ contract, UV completeness,
material separation, bounds, non-degenerate faces, closed opaque sub-solids, and
the east walk-through volume. Outputs are under
`qa/rootstead_entry_vestibule/`, including the machine reports and three-view
preview.

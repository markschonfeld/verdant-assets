# Rootstead vault kit — the ground truth for lattice joints

These are the **actual meshes the Rootstead envelope is instanced from**, copied
out of the private Unreal project (`Verdant 5.8/SourceMesh/`). Every joint and
member across 150 m of vault roof and both end gables is one of these, placed by
`PyTools/build_vault.py` and `PyTools/build_endwall.py`.

They are here because a PR was twice asked to "match the roof junctions" and
twice missed — once too slender, once as a solid disc. Both attempts were
working from *descriptions* of the geometry. **Match against the mesh, not
against a description of it, including the one below.**

| file | tris | role |
|---|---|---|
| `VD_VaultNode.obj` | 12,464 | the joint, hero LOD |
| `VD_VaultNode_Far.obj` | 672 | the joint, far LOD (18.5x decimation) |
| `VD_VaultTube.obj` | 3,516 | the member, hero LOD |
| `VD_VaultTube_Far.obj` | 252 | the member, far LOD (14x) |

No `.mtl` — the kit is assigned `M_Aluminium` in-engine, and the west endwall
asset already binds its own `M_WestEndwall_OxidisedAluminium` slot.

## What the joint actually is, and what it is not

`VD_VaultNode` is **not a disc, torus or annulus**. Measured from the file:

```
connected pieces                        117
outer-shell azimuth bins occupied        12 of 24
outer-shell z span                    -16.5 .. 16.5
radial extent (xy)                     14.31 .. 52.66
```

117 separate pieces, and the outer shell occupies only **half** the azimuth bins
— material clumps into discrete directions with gaps between. It is a **cluster
of short cylindrical collars radiating from a compact centre**, each terminating
in a sleeve with a small flange ring: pipe-fitting hardware, in the idiom of a
1960s institutional space frame.

A solid disc would fill all 24 bins and be one connected piece.

### The specific error to avoid

An earlier revision spec quoted "hub radius 52.66, axial thickness 40.40, bore
14.31" and asked for a bored disc hub at every node. Those numbers are real but
they are **bounding measurements of the spoked cluster** — 52.66 is how far the
collar tips reach, 14.31 is a collar bore, 40.40 is the overall depth. Building a
solid annulus to those dimensions produces a smooth doughnut at every junction,
which is a completely different design language from the surrounding roof.

Radial extent is not form. Read the geometry.

## Related

- `references/architecture/WEST_ENDWALL_ENTRY_JOINT_REWORK.md` — the review this
  reference exists to settle
- `PyTools/import_far_variants.py` (private project) — the far-LOD decimation
  strategy already in use, worth matching rather than reinventing

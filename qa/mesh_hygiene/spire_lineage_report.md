# Spire source-lineage finding

## Decision

The 942-triangle mesh reported by the Unreal geometry audit is **not a separate
942-triangle source artifact in this repository**. It is an engine-side derived
representation of the 180 m PR #11 spire lineage.

The authoritative *existing* source is PR #11's 13,780-triangle OBJ. The
architectural authority for the next import is now
`references/props/SPIRE_SIGNAL_MAST_REWORK.md`, which replaces the exhaust-stack
form with the microwave relay mast. Therefore **do not reimport the cleaned
12,776-triangle exhaust-stack OBJ solely for this hygiene PR**. Carry the hygiene
gate into the signal-mast rework and import that replacement when it is ready.

## Evidence

Every unique `VD_Spire.obj` artifact in Git history was enumerated:

| Revision | Triangles | Bounds | Meaning |
|---|---:|---:|---|
| `4876628` | 1,544 | 3.6 × 3.6 × 12 m | Initial authored landmark; not the level mesh |
| `ddd8b21` | 13,780 | 22 × 22 × 180 m | Redesigned 180 m exhaust stack |
| `a966d63` | 13,780 | 22 × 22 × 180 m | Same geometry with indexed UVs; merged through PR #11 |

There is no committed 942-triangle OBJ and no committed decimated export.

The current level manifest identifies `STACK_Spire` as a 22 × 22 × 180 m asset
using the five material slots from the 13,780-triangle PR #11 source. Its local
height is 18,000 cm. That excludes the 12 m / 1,544-triangle `4876628` artifact.

The two largest in-engine stacked regions were reported near local Z 12,612 and
16,612 cm. Those positions match the platform calls introduced by `ddd8b21` at
Z 12,600 and 16,600 cm. The initial `4876628` generator has neither platform.
This independently ties the level asset to the 180 m source lineage.

The 942-triangle count is now confirmed as Unreal's **Nanite fallback mesh**,
not source topology: `get_num_triangles(0)` returned the fallback representation
for this Nanite asset. The original in-engine Spire duplicate counts therefore
measured the wrong representation and must be disregarded. The Z 12,600 / 16,600
platform match remains the independent evidence tying the placed asset to the
PR #11 source. Future in-engine audits must explicitly inspect the intended
source/render representation rather than assuming LOD 0 is source topology.

## Hygiene status

For source hygiene and reproducibility, this branch cleans the existing PR #11
source from 13,780 to 12,776 import triangles and reduces its 162 exact/1 cm
stacked polygon pairs to zero. This is a safe repository baseline, not an
instruction to replace the level mesh before the mast rework.

# Rootstead entrance bulkhead prototype gate

**Candidate decision:** HOLD. The 146 × 225 uu west-face module and 191 × 225 uu return module are viable candidates, but aggregate/detail replication is not authorized until art/tech review accepts this measured projection.

- Measured prototype: **452 triangles**, including **14** closed proud aggregate stones (166 triangles).
- Projection: 72 repeated module instances; 14 sparse-spall instances; 480 fixed structural/base triangles + 23804 repeated-detail triangles = **24284 triangles**.
- Placement/bounds: transform `(0, 0, 3500)`; parsed local bounds are recorded in metrics. The visible west face is world `x=-461`, not the defective `x=-300` void edge.
- Surfaces: both west wing faces, outer returns at `y=±1300`, and doorway returns at `y=±424`; east `x=112` abuts WEND_Entry and is undecorated.
- Collision: render prototype only. Integration must use hand-authored segmented boxes; no primitive may cross `x=-509..112, y=±424, z=3500..3892`. No generated hull or convex decomposition.
- Limitations: no full wall is authored; material/shader fidelity, LODs, Unreal import, lightmap UVs, and face-volume clearance tests belong to the production asset gate.

Commands: `python3 scripts/generate_rootstead_entrance_bulkhead_proto.py`; `python3 scripts/verify_rootstead_entrance_bulkhead_proto.py`.

## STOP before scaling

Do not replicate aggregate, streak, sealant, spall, or module geometry across the full wall until this candidate count and visual density are explicitly accepted.

# SPIRE landmark asset handoff

## Scope and design intent

This pass replaces the two scaled Engine cylinders named `SPIRE` and `SPIRE_BASE` with a self-contained atomic-age horticultural/research landmark. It does **not** claim or alter any architectural family, door/bulkhead component, railing, or 300 uu envelope module.

The silhouette is intentionally readable before texture detail: a faceted tapered mast, short lower buttresses, four staggered environmental-instrument arms and pods, three structural collars, exposed collar bolts, a stepped octagonal service base, four access plates, and real plate fasteners. The object is industrial/civic wayfinding rather than a rocket, weapon, or religious icon.

## Scale lock (not an estimate hidden in transforms)

All source coordinates are **Unreal centimetres at 1:1** (`1 OBJ unit = 1 uu = 1 cm`). Import at uniform scale **1.0**.

| Asset | Real-world target | Bounds | Pivot | Up axis |
|---|---:|---:|---|---|
| `VD_SpireBase.obj` | 3.60 m wide × 3.60 m deep × 1.10 m high | `360 × 360 × 110 cm` | bottom centre, `Z=0` | `+Z` |
| `VD_Spire.obj` | 3.60 m instrument span × 12.00 m high | `360 × 360 × 1200 cm` | bottom centre, `Z=0` | `+Z` |
| assembled | **13.10 m high** | base + mast, mast translated `+110 cm Z` | base pivot | `+Z` |

The 13.10 m assembly is an authored first-pass size chosen for a landmark under the 61.9 m vault; no level measurement was supplied for the two old cylinders. Claude/Mark should check this against the live actors before replacement. If the old silhouette materially differs, revise the generator dimensions and regenerate—**do not non-uniformly scale the imported mesh**.

## Source artifacts

- Generator: `scripts/generate_spire_landmark.py`
- Verifier/orthographic preview: `scripts/verify_spire_landmark.py`
- Meshes: `SourceMesh/props/VD_Spire.obj`, `SourceMesh/props/VD_SpireBase.obj`
- Material-slot library: `SourceMesh/props/VD_Spire_Landmark.mtl`
- QA report and preview: `qa/spire_landmark/`

Regenerate and verify from the repository root:

```bash
python3 scripts/generate_spire_landmark.py
python3 scripts/verify_spire_landmark.py
```

## Import and placement

### `VD_SpireBase`

- Import OBJ with unit conversion disabled and uniform scale `1.0`.
- Place the bottom-centre pivot on the existing base actor's ground plane.
- Intended collision: a simple octagonal/cylindrical blocking hull around the 3.6 m plinth. Do not use per-poly collision for routine navigation.
- Nanite: **ON** (all material slots are opaque).

### `VD_Spire`

- Import at uniform scale `1.0`.
- Place at the same XY as the base and translate its pivot to the base top (`+110 cm Z`).
- Intended collision: **NoCollision** if inaccessible/decorative, consistent with VERDANT's unreachable-decoration rule. If players can reach the mast, use one simple cylindrical blocker around the lower shaft; do not collide against fins and bolts.
- Nanite: **ON** (all material slots are opaque).

## Material intent

The OBJ uses material groups; Unreal materials remain project-owned.

| Slot | Intended surface | Projection |
|---|---|---|
| `M_Spire_Concrete` | dark cast foundation concrete | world/triplanar |
| `M_Spire_PaintedSteel` | aged Institute teal/green painted steel | world/triplanar |
| `M_Spire_BareMetal` | worn aluminium/galvanized collar metal | world/triplanar |
| `M_Spire_ServicePanel` | oxidized orange-brown service plate | world/triplanar |
| `M_Spire_Fin` | painted structural fins with edge wear | world/triplanar |
| `M_Spire_Fastener` | dark steel bolts and lightning tip | world/triplanar |

There is no translucent slot and no light in this pass. If a beacon is added later, its lens/emitter should be a separate non-Nanite mesh with visible emitting geometry—not an invisible point light attached to this opaque asset.

## Collision, UV, and topology notes

- Geometry is composed of closed manifold solids. Interpenetrating authored sub-solids are intentional for Nanite import and preserve clean generator logic.
- Tiling surfaces intentionally have no 1:1 texture UV dependency; use triplanar/world projection.
- Real collar and service-plate fasteners are geometry, not normal-map fakery.
- The source meshes require no non-uniform actor scale.
- The verifier checks face indices, degenerate faces, edge incidence, exact bounds, pivots, material assignment, and MTL linkage.

## Live-level acceptance check

Before deleting/replacing the cylinders:

1. Record old `SPIRE` and `SPIRE_BASE` world bounds and pivot locations.
2. Import both meshes at `1.0` and place the mast `110 cm` above the base pivot.
3. Compare from the established player-first-view and distant landmark views.
4. Confirm the 3.6 m footprint does not obstruct navigation.
5. If the assembly needs dimensional revision, change constants in the generator; do not stretch the mesh in-editor.
6. Only after visual and navigation acceptance, replace or hide the old cylinders.

# VERDANT — Project Brief

**Purpose:** everything a new agent needs to pick up this project cold. Written
06 Aug 2026. If a session dies, start here.

---

## 1. The game

**VERDANT** (in-world: **Eden Prime**) — first-person narrative horror RPG.
Unreal Engine **5.8**. Project at `G:\UnrealProjects\Verdant 5.8`.
Primary level: `/Game/Maps/Rootstead` (World Partition).

The first level is a **1960s institutional botanical glasshouse gone to seed**,
explicitly **BioShock Infinite inspired**. The entrance terrace is *the reveal*:
the player expects a ruin and finds something that was once magnificent and
public. Lower levels get crops and experiments; this level is beauty and unease.

The player will see part of the next level from inside this one, and on the last
level will see the glasshouse through a window — a cohesive continuous world in
the manner of The Last of Us. Background areas outside the glasshouse will
eventually be filled in for that reason.

### Standing art direction — do not relitigate these

- **Quality bar is Fallout 76, not photorealism** — reachable "with enough
  varied textures and attention to detail".
- **"Everything in this game should be researched thoroughly for realism as that
  adds to why it's scary to players."** This is the single most load-bearing
  instruction. Period-correct detail beats invention.
- **Priority order for assets: look right → logical placement → wind.** Wind
  animation comes last. Bake vertex-colour stiffness, do not wire it yet.
- **Cinematic is a goal.** Colour grading is cyan/orange split toning (applied,
  see §6). Cyan/magenta is a written alternative.
- The building has repeatedly read **too teal**. The cause was never grading —
  it was too few textures doing too many jobs, plus one actual bug in the steel
  albedo. Prefer warm counterweights; be suspicious of anything that adds cyan.
- **"Adding walls is not a solution"** to the player walking off the map. Block
  access architecturally.

---

## 2. Repositories and paths

| What | Where |
|---|---|
| Unreal project | `G:\UnrealProjects\Verdant 5.8` |
| Python tooling | `G:\UnrealProjects\Verdant 5.8\PyTools` |
| Shared asset repo | `G:\UnrealProjects\verdant-assets` → `github.com/markschonfeld/verdant-assets` |
| Source meshes (project) | `G:\UnrealProjects\Verdant 5.8\SourceMesh` |
| Reports | `Saved\vreports\<name>_NNN.txt` |
| Renders | `Saved\vshots\` |

**`Content/` and `Saved/` are gitignored. The level is NOT in version control.**
Actor deletion is therefore irreversible — always print transforms, meshes and
materials to a report BEFORE destroying anything. That printout is the only undo.

---

## 3. How to run code in the editor

A file-drop relay bridges to the running editor:

- Write `{"kind":"python","code":"..."}` to `Saved\mcpbridge\in\<id>.json`
- Result appears at `Saved\mcpbridge\out\res_<id>.json`
- `PyTools/mcp_relay.py` runs it **on the game thread**, one snippet per tick,
  with a 120 s watchdog. **Never sleep or poll inside a snippet.**

The bridge returns `result`, **not stdout**. Scripts write findings to a report
file in a `finally:` block; the driver reads that file. Report index = max+1.

### Security — non-negotiable

The Unreal MCP server has **no authentication of any kind** and exposes
arbitrary Python execution in the editor. **Never bind it to `0.0.0.0`, never
port-forward it, never tunnel it to a public URL.**

### Always

- **Stop PIE before running anything.** Work against the PIE world is discarded.
  `get_all_level_actors()` returns an **empty list** during PIE and does not
  raise — three probes once read zero and nearly caused a false "everything was
  deleted" report. Guard on `get_game_world() is not None`.
- **Never delete-and-recreate a material.** Use
  `MEL.delete_all_material_expressions()` on the existing asset. With the level
  loaded, `create_asset` on an existing referenced material raises a modal that
  blocks the game thread. **If that dialog appears: Cancel, never Overwrite.**

---

## 4. Hard-won gotchas — read before writing engine code

These all cost real time. Every one produced a report that looked successful.

**Silent-failure API calls**

- `set_editor_property` / `set_material` **re-register the component and
  invalidate the list you are iterating.** Gather first, then set, then verify
  on a *fresh* list. This has bitten at least four times, most severely when
  setting properties inside a placement loop caused 24,779 `add_instance` calls
  to land on orphaned components — the builder reported a perfect run and **the
  vault ended up with zero panes**.
- `MaterialEditingLibrary.set_material_default_scalar_parameter_value` **does
  not exist.** A master's defaults cannot be set from Python. Use instances.
- `set_material_instance_*_parameter_value` does **not** raise on an unknown
  parameter name — it silently does nothing. Validate names against the parent.
- `connect_material_expressions` and `connect_material_property` **return False**
  on a bad pin name and do not raise. Check the return value.
- `set_custom_data_value` does nothing if the array is undersized. Set
  `num_custom_data_floats` **on the blueprint template**, not the spawned
  component.
- `set_editor_property('visible', False)` is accepted then **silently reverted**
  on an ISM. Use `set_visibility()`.
- `save_dirty_packages` returns `True` and writes nothing for World Partition
  actor moves. Use explicit `save_packages(list, False)`.
- `is_temporarily_hidden_in_editor` is a setter, and is **transient by design** —
  it can never survive a restart.
- `StaticMesh` has no `build()` and no `collision_complexity` in 5.8. Collision
  trace flag lives on the **BodySetup** as `collision_trace_flag`.

**Type traps**

- `unreal.Rotator` is `(roll, pitch, yaw)` **positionally**. Always use keywords.
- `bloom_tint` wants `unreal.Color` (8-bit); `fog_albedo` wants
  `unreal.LinearColor`. Passing the wrong one raises rather than converting.
- `DitherTemporalAA` is a material **function**, not an expression class. Its
  input pin is `'Alpha Threshold'` — with a space.

**Collision**

- Unreal **auto-generates a single convex hull on OBJ import**. On a hollow
  vessel that hull *fills the cavity*. This sealed the vestibule doorway (Mark
  walked into an invisible wall twice) and would have sealed both planters and
  the fountain basin. Always `remove_collisions()` first.
- Convex **decomposition does not reliably segment a smooth vessel** — asked for
  16 hulls it returned 1 and 2 on the two planters, i.e. sealed. For rings,
  author explicit tangential box primitives instead.
- Apertures need `CTF_USE_COMPLEX_AS_SIMPLE` on **both** frame and glazing.
- `set_collision_enabled` does **not** change `collision_profile_name`, and the
  profile wins on reload.

**Measurement discipline**

- **Never mask by colour when measuring colour.** A colour-threshold pixel mask
  is a function of the thing being measured and produced an impossible reading.
  Use fixed geometric masks.
- **SceneCapture2D does not run the same post-process chain as the viewport.**
  Exposure, bloom, light shafts and grading cannot be judged from a capture.
  Measure geometry, counts, parameters and flags from script; judge *look* with
  Mark's eyes. Acting on capture metrics for post-process effects has produced
  wrong calls twice.
- A directional light's forward vector **travels toward** its yaw, so the sun is
  **opposite**. With sun yaw −60, look toward yaw **+120** to see it. Several
  "toward the sun" captures pointed down the beam and showed nothing.
- Report counts that omit a component are worse than no counts — an endwall
  report said 1,038 panes for a wall holding 1,675 and read as "the dial did
  nothing".

---

## 5. Level structure — Rootstead

Measured extents (uu; **1 uu = 1 cm**):

```
hall              x   -350 .. 45950   y ±7530   crown z 9694
ENT_Deck          x   -420 ..  1600   y ±7350   top z 3500     entrance terrace
TERR_A/B/C        x   6000 .. 24000   y ±7500   z 2600/1700/800  descending
FLOOR             x  27000 .. 45000                    z 0      far hall floor
blast door        x   -375            y ±416    z 3508..3892
vestibule         x    128 ..   498   y ±972    z 3500..4409
OVK walkway       x      0 ..  1606   y ±770                    keep clear
ground plane      40 km                        z −1050
```

**Glazing** (`build_glazing.py`, `build_endwall.py`): one triangular pane per
structural opening, 300 uu pitch. Vault = 16 `GLAZE_Sec` actors; ends =
`ENDWALL_W` / `ENDWALL_E`. Components `PaneAcrylic` / `PaneRepair` /
`PaneBlocked` / `PanePlate`.

- ~28,162 **visible** translucent panes (two glazing eras: 1960s acrylic and
  later repair glass).
- 12,390 **invisible shadow twins** on `PaneBlocked`: `visible=False`,
  `cast_hidden_shadow=True`. These block sunlight and are never drawn. This
  separation exists because making panes *opaque* to get occlusion made the roof
  read as **"glass replaced with metal sheets"** — Mark called it three times.
  Turning `GRIME_COVERAGE` up can no longer bring panels back.
- Grime is a **continuum**, not binary: each pane's rank in the grime
  distribution is written to **custom data slot 1** and added into the `grime`
  node before it branches, so base colour, roughness and opacity all pick it up.
  Slot 0 is a per-pane decorrelation seed. `num_custom_data_floats = 2`.

**Spire, ground plane, balustrade, vestibule** are built by their own scripts in
`PyTools`. Each script's docstring records why it is the way it is — read it
before changing anything.

---

## 6. Current lighting / atmosphere state

```
SUN_New   pitch −42, yaw −60 (≈2 pm), intensity 20
          volumetric_scattering_intensity 5.0, cast_volumetric_shadow True
          enable_light_shaft_occlusion True, occlusion_mask_darkness 0.15
          bloom_scale 0.90, bloom_max_brightness 30, bloom_threshold 0.30
SKY_New   intensity 4.0, min_occlusion 0.5      ← the interior-lighting fix, keep
FOG_New   fog_density 0.005, extinction 1.2, distance 30000, distribution 0.55
LFOG_Hall ×8  LocalFogVolume, radial_fog_extinction 0.010,
              height_fog_extinction 0.006, fog_phase_g 0.88
PPV_Rootstead  unbound. Split tone cyan/orange, GRADE_STRENGTH 0.70,
               ranges 0.18 / 0.55. EXPOSURE_CONTROL is OFF.
```

### God rays — what was learned

A **global** `ExponentialHeightFog` cannot produce shafts in this building: it is
world-wide, so density enough for interior beams also hazes the sky and the
exterior, which you see through 28,000 panes from nearly everywhere. Measured:

```
density   0.006    0.020    0.045
luma      175.7    212.7    232.3      p99/p50 collapses to 1.08 = milk
```

The fix is **bounded** fog (`LocalFogVolume`, §6 above) plus **invisible**
shadow-casting occluders, plus the sun's own **light-shaft occlusion**, which is
screen-space and does not care about voxel resolution. `fog_phase_g` (forward
scattering) matters more than density — it is what makes a beam read as a beam.

Local fog has a **cliff** between 0.020 and 0.008: above it the hall stops
existing. 0.010 sits just below.

Light shafts only render with the sun in or near frame — accepted trade.

### ⚠ Exposure

`EXPOSURE_CONTROL = False` in `setup_post_process.py` and should stay off unless
someone is watching the viewport. **`AEM_MANUAL` ignores
`auto_exposure_min/max_brightness`** and takes exposure from camera
shutter/ISO/aperture, which this scene has never been configured for — setting it
turned the level **pitch black**. If pinning exposure, use `AEM_HISTOGRAM` with
min == max.

The interior sits near ~200 luma with no exposure control, which is the real
ceiling on both the grade and the ray strength. Fixing it is the highest-value
outstanding lighting task.

---

## 7. Asset pipeline — working with Hermes

**Hermes** is a separate agent (Slack `#agent-team`, channel `C0BJFCX1SPM`) who
authors procedural OBJ assets in `verdant-assets` and opens PRs. Mark relays
briefs. Division of labour:

- Hermes: geometry, alpha sheets, generator + verifier scripts, handoff docs.
- This agent: Unreal import, materials, collision, placement, in-engine QA.
  **The Unreal integration IS the acceptance gate** — Hermes deliberately does
  not merge before it passes.

**Asset contract** (every OBJ): one object per file, `usemtl` slots, indexed UVs
on every corner, **no `g` records**, base-centred origin at Z = 0, vertex-colour
wind stiffness on foliage (0 = rigid root, 1 = free tip), and a **collision note
in every handoff**.

> Historical bug: an importer once stripped `usemtl` as well as `g `, collapsing
> 8 material slots into 1. Only `g ` is the problem. Always read material slot
> counts back after import.

### PR state at time of writing

| PR | Branch | State |
|---|---|---|
| #12 | `feat/rootstead-entry-vestibule` | open, **not merged**. Vestibule frame revision (free-standing posts removed). The OBJ was pulled locally and imported, so the level is correct; the branch is still outstanding. |
| #13 | `feat/terrace-planter-botanical-kit` | open. Remote head still at the old Dracaena fix. **Must land before #16.** |
| #16 | `hermes/botanical-foliage-rework` → base #13 | open, clean, mergeable. The entrance-terrace reveal kit. **Imported and integrated.** |

**#16 is stacked on #13.** Its branch already contains #13's ancestry, so assets
can be fetched and imported **without any merge**. Do not merge #16 directly —
it would merge into #13's branch, not `main`.

---

## 8. Entrance-terrace reveal kit — integrated 06 Aug

16 meshes, 35 material instances, from PR #16 at `9ad9437`.

- Meshes → `/Game/Meshes/Reveal`, textures → `/Game/Textures/Reveal`.
- Materials `MI_Rev*` — **no new masters**; all instanced off existing
  `MX_Foliage` / `MX_Bark` / `MX_Soil` / `MX_ConcreteCast` / `MX_SteelPainted` /
  `MX_Plaster` / `MX_Concrete`.
- RGBA cutouts must be `TC_DEFAULT` + sRGB with alpha preserved. `TC_MASKS`
  discards colour; `compression_no_alpha` discards the mask. Either produces
  leaves with no cutout.
- **`WindAmplitude` is pinned to 0 on every instance.** `MX_Foliage` drives wind
  from vertex colour, and a mesh with *no* vertex colour reads as white — the
  free-tip value. Benches, brochure stand, fountain and all three banners are
  authored without vertex colour and would flap at full amplitude the moment
  wind is enabled. **They must stay at 0 even after wind is switched on.**
- Banners use `MX_Foliage` (masked + two-sided is right for alpha-cut cloth) with
  **pure white tint** — the 2048 sheets carry typeset 1960s Institute copy and
  tinting would corrupt authored graphics.

### Terrace composition (`place_reveal_terrace.py`)

The old `PLANTERS_Terrace` run — a continuous 147 m line 7 m in front of the door
— was recorded and removed. The deck is 20 m deep × 147 m wide, so a line along
the long axis reads as a fence.

Mark's direction: **formal, axial, and the player only walks the middle.** The
outer wings stay empty on purpose, to be filled later with trees and dense beds
"just like a true botanical garden greenhouse would have".

33 `REV_*` actors: gate pair of concrete planters with date palms flanking the
walkway, outer ceramic planters with philodendron, dry fountain **on the
centreline** (formal gardens put the basin on axis; at 1.12 m you see over it),
benches facing the axis, brochure stand by the vestibule, soil dressing in every
planter, banners hung from the trellis.

Specimens sit on the **soil surface**, not the deck: concrete +80, ceramic +95.

---

## 9. Open items

1. **Exposure control** — off; the ceiling on grade and ray strength. Highest
   value, needs someone watching the viewport.
2. **PR #13 → then #16** — merge order matters.
3. **PR #12** — vestibule branch still unmerged.
4. **Side beds** — trees and dense planting either side of the terrace corridor.
5. **Walk-out route** beside the blast door still open. Mark has said he will
   demonstrate his preferred approach; **do not build walls**.
6. **~95 boxy engine cubes** — `ENT_`, `DOOR_`, `RH_` prefixes.
7. **Wind** — stiffness baked, nothing wired. Comes after placement.
8. **NPC animation** — Mark and Hermes have begun planning; not started here.
9. **Translucency sort instability** (16.32%) unresolved. Masked+dither was
   tried and **rejected** — at 28,000 panes a few pixels across, TAA has nothing
   coherent to accumulate and it read as television static.

---

## 10. Working style that has worked

- Small measured changes, one variable at a time, reported honestly.
- Every script writes a report in a `finally:` block and **verifies its own work
  on a fresh read** — this project's signature bug is the successful-looking
  report over a no-op or a destroyed asset.
- State what was falsified, not just what worked. Several dead ends are recorded
  in script docstrings precisely so they are not retried.
- When a conclusion rests on a capture of a post-process effect, say so and hand
  the judgement to Mark.

"""Shared numeric contract for the Rootstead entrance-bulkhead TRIANGLE-BUDGET
PROTOTYPE.

Both `generate_rootstead_entrance_bulkhead_proto.py` and
`verify_rootstead_entrance_bulkhead_proto.py` import this module so the generator
and the independent verifier can never drift apart. Units are Unreal centimetres
(1 uu = 1 cm), Z-up, +X east into the building, +Y north -- the same frame as
`docs/VERDANT_PROJECT_BRIEF.md` and
`references/architecture/ROOTSTEAD_ENTRANCE_BULKHEAD_SPEC.md`.

WHAT THIS IS (and is NOT)
-------------------------
This is a *prototype gate*, not the deliverable wall. It authors ONE
representative held precast module -- an exposed-aggregate architectural precast
panel with chamfered arrises, a recessed/perished sealant joint, the board-marked
in-situ plinth construction junction beneath it, a sparse corner spall exposing a
rebar/fixing lug, and geometry-obedient weather streaks below joint/fixing
origins -- at TRUE SCALE, so per-module triangle cost can be measured and the
full-wall detail count projected from an explicit layout.

It deliberately does NOT replicate the module across the wall's x/y/z extents.
The module is authored in WORLD-ALIGNED LOCAL COORDINATES (local axes parallel to
world; local X == world X, local Y == world Y, local Z == world Z - PLACE_Z so
the base sits at local Z=0 per this repo's base-centred-origin convention). Its
intended eventual placement is documented in PLACEMENT below and echoed into the
metrics JSON.

Period justification for every detail lives in the spec doc (1960s institutional
architectural precast -- Mo-Sai exposed aggregate, board-formed in-situ plinths,
predictable weather streaking, sparse corner spalling). Absolutely no rivets,
plate seams, welds, or painted-steel language: those read industrial/wartime and
are wrong for the date. The verifier enforces that ban on material names.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Full-wall extents to fill (references/architecture/ROOTSTEAD_ENTRANCE_BULKHEAD_SPEC.md
# "Extents to build"). Used ONLY for the projection; no geometry is authored
# across these.
# ---------------------------------------------------------------------------
WALL_X = (-461.0, 112.0)   # depth, through to the gable plane
WALL_Y = (-1300.0, 1300.0)  # width, matching the current cladding run
WALL_Z = (3500.0, 4325.0)  # above ENT_Deck; below 3500 is understructure

# Clear doorway that must stay empty (spec "Must stay clear"). The wall is two
# wings either side of this.
DOOR_CLEAR_Y = (-424.0, 424.0)

# ---------------------------------------------------------------------------
# Placement datum. Base of authored geometry (world z 3500 = top of ENT_Deck)
# maps to local Z = 0. The prototype is authored at the representative cell (the
# first column, bottom courses, of the +Y wing) using real world X and Y, so the
# eventual placement transform is simply (0, 0, PLACE_Z).
# ---------------------------------------------------------------------------
PLACE_Z = 3500.0
WORLD_PLACEMENT = (0.0, 0.0, PLACE_Z)


def world_z(local_z_value: float) -> float:
    return local_z_value + PLACE_Z


def local_z(world_z_value: float) -> float:
    return world_z_value - PLACE_Z


# ---------------------------------------------------------------------------
# Candidate module dimensions + rationale (echoed into metrics JSON).
# ---------------------------------------------------------------------------
# The visible decorated face is the WEST (-X) face of the wall; panels tile
# across width (Y, columns) and height (Z, rows), with relief proud toward -X.
#
# Module 146 (wide, Y) x 225 (tall, Z):
#   - 1.46 m x 2.25 m sits squarely in the 1960s architectural-precast range
#     (Mo-Sai / storey-band units ran ~1.2-1.5 m wide, storey/band height).
#   - 146 divides each 876 uu wing width exactly 6 times (no part-panels at the
#     door jamb or the wall end) -- a real precast setter-out picks a module that
#     closes on both stop lines.
#   - 225 divides the 675 uu precast field height exactly 3 times.
MODULE_W = 146.0   # along Y
MODULE_H = 225.0   # along Z (precast field course height)

# Board-marked in-situ plinth band at the base, distinct pour from the precast
# above -> a real construction junction, not a texture change.
PLINTH_H = 150.0   # 1.5 m board-formed base, world z 3500..3650
PLINTH_BOARD_COUNT = 6  # horizontal board-form impressions in the plinth face

# Precast field sits above the plinth.
FIELD_Z = (world_z(PLINTH_H), WALL_Z[1])  # world 3650..4325, height 675

# Relief depths (X). Proud pad face is most negative X (toward the viewer);
# recesses cut back toward +X.
FACE_X = -461.0            # required replacement west extent (NOT defective void edge -300)
JOINT_RECESS_DEPTH = 12.0  # recessed joint floor at FACE_X + 12
CHAMFER = 5.0              # 45 deg chamfered arris bevel at the pad edge
SEALANT_INSET = 8.0        # perished bead face sits recessed 8 uu behind the pad face
BACKING_X = -391.0         # back plane of the authored base-massing SAMPLE slab
JOINT_WIDTH = 18.0         # full recessed joint width between adjacent pads (half owned per module)
STREAK_PROUD = 0.6         # weather-streak ribs stand this proud of the pad face

# The representative cell occupies the first column of the +Y wing.
CELL_Y = (DOOR_CLEAR_Y[1], DOOR_CLEAR_Y[1] + MODULE_W)  # world y 424..570

# ---------------------------------------------------------------------------
# Full-wall projected layout (explicit; drives the projection in the generator).
# ---------------------------------------------------------------------------
WING_WIDTH = DOOR_CLEAR_Y[0] - WALL_Y[0]              # 876 uu (== WALL_Y[1]-424)
COLUMNS_PER_WING = int(round(WING_WIDTH / MODULE_W))  # 6
ROWS = int(round((FIELD_Z[1] - FIELD_Z[0]) / MODULE_H))  # 3
WINGS = 2
RETURN_BAY_W = 191.0       # 573 uu x-depth / 3 exact bays
RETURN_BAYS = 3
WEST_MODULES = WINGS * COLUMNS_PER_WING * ROWS             # 36
OUTER_RETURN_MODULES = 2 * RETURN_BAYS * ROWS              # 18
DOOR_RETURN_MODULES = 2 * RETURN_BAYS * ROWS               # 18
MODULE_COUNT_FULL_WALL = WEST_MODULES + OUTER_RETURN_MODULES + DOOR_RETURN_MODULES  # 72

# Spalling is authored "sparingly" (spec). Projected onto a fraction of modules.
SPALL_FRACTION = 0.20  # ~1 module in 5 shows a corner spall/rebar reveal

# ---------------------------------------------------------------------------
# Semantic material slots (== detail categories). Names are period-safe: no
# rivet/plate/weld/seam/steel-plate language anywhere. "RebarLug" is cast-in
# reinforcement / fixing hardware, legitimate precast, not fabricated cladding.
# ---------------------------------------------------------------------------
MAT_BASE_MASSING = "M_EntranceBulkhead_BaseMassing"      # solid backing (fixed massing)
MAT_BOARD_PLINTH = "M_EntranceBulkhead_BoardFormedPlinth"  # board-marked in-situ plinth
MAT_PRECAST = "M_EntranceBulkhead_PrecastAggregate"       # exposed-aggregate precast face/body
MAT_AGGREGATE = "M_EntranceBulkhead_ProudCoarseAggregate" # real proud coarse aggregate stones
MAT_CHAMFER = "M_EntranceBulkhead_ChamferArris"           # chamfered arrises
MAT_JOINT = "M_EntranceBulkhead_JointReveal"              # recessed joint reveal returns
MAT_SEALANT = "M_EntranceBulkhead_SealantJoint"           # recessed/perished sealant bead
MAT_SPALL = "M_EntranceBulkhead_SpallReveal"              # corner spall fracture faces
MAT_REBAR = "M_EntranceBulkhead_RebarLug"                 # exposed rebar / fixing lug
MAT_STREAK = "M_EntranceBulkhead_WeatherStreak"           # geometry-obedient weather streaks

ALLOWED_MATERIALS = {
    MAT_BASE_MASSING, MAT_BOARD_PLINTH, MAT_PRECAST, MAT_CHAMFER, MAT_JOINT,
    MAT_SEALANT, MAT_SPALL, MAT_REBAR, MAT_STREAK, MAT_AGGREGATE,
}

# Categories that are FIXED base massing (do not multiply per module -- they
# scale roughly with wall area/length) versus REPEATED decorative detail (scale
# linearly with module count). This split is the whole point of the gate:
# scaling risk lives entirely in the repeated set.
FIXED_MASSING_MATERIALS = {MAT_BASE_MASSING, MAT_BOARD_PLINTH}
REPEATED_DETAIL_MATERIALS = {
    MAT_PRECAST, MAT_AGGREGATE, MAT_CHAMFER, MAT_JOINT, MAT_SEALANT, MAT_STREAK,
}
# Sparse repeated detail: multiplies by (SPALL_FRACTION * module_count).
SPARSE_DETAIL_MATERIALS = {MAT_SPALL, MAT_REBAR}

# Preview swatch colours (RGB 0..255) per material, for the Pillow legend.
PREVIEW_COLORS = {
    MAT_BASE_MASSING: (120, 116, 108),
    MAT_BOARD_PLINTH: (150, 140, 122),
    MAT_PRECAST: (196, 188, 168),
    MAT_CHAMFER: (176, 168, 150),
    MAT_JOINT: (96, 92, 86),
    MAT_SEALANT: (60, 56, 52),
    MAT_SPALL: (166, 120, 96),
    MAT_REBAR: (150, 96, 70),
    MAT_STREAK: (128, 128, 120),
    MAT_AGGREGATE: (112, 104, 86),
}

# ---------------------------------------------------------------------------
# Banned material-name substrings. Any occurrence in an MTL/OBJ material name is
# a hard verifier failure (period discipline: no fabricated-metal cladding read).
# ---------------------------------------------------------------------------
BANNED_NAME_SUBSTRINGS = (
    "rivet", "plate", "weld", "seam", "steelplate", "steel_plate", "plating",
    "bolt", "flange",
)

# ---------------------------------------------------------------------------
# Asset names / paths.
# ---------------------------------------------------------------------------
OBJ_NAME = "VD_RootsteadEntranceBulkhead_Proto"

# ---------------------------------------------------------------------------
# Expected local bounds (world-aligned; Z rebased so base == 0). The verifier
# checks the parsed OBJ against these, it does not trust the generator.
# ---------------------------------------------------------------------------
AGGREGATE_COUNT = 14
AGGREGATE_RADIUS_RANGE = (2.7, 5.2)
EXPECTED_MIN = (FACE_X - 4.2, CELL_Y[0], 0.0)  # largest stone projection is proudest
EXPECTED_MAX = (BACKING_X, CELL_Y[1], PLINTH_H + MODULE_H)  # local z 0..375

# ---------------------------------------------------------------------------
# Tolerances.
# ---------------------------------------------------------------------------
TOL_BOUNDS = 1.0
DEGENERATE_AREA_EPS = 1e-4

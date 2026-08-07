"""Shared numeric contract for the Rootstead west-endwall-entry replacement asset.

Both the generator and the verifier import this module so the two can never
drift apart. Every constant here traces to either `docs/VERDANT_PROJECT_BRIEF.md`,
the brief for this delivery, or `level/rootstead_manifest.json` (the measured,
read-only snapshot of the actual Rootstead level). Units are Unreal centimetres,
Z-up, +X east into the hall, +Y north.

This is a REPLACEMENT delivery, not the additive occlusion pattern shipped on
`origin/feat/rootstead-west-entry-assets` (PR #17 / `VD_RootsteadEntryPortal`):
that asset never touched the gable lattice (it only added a box facade in front
of it) and it baked static "frosted leaf" glass boxes into the same rigid object
that fills the animated door-leaf sweep volume, so the doorway reads as
permanently shut regardless of what the real DOOR_LeafL/R actors do. Neither
mistake is repeated here: the lattice is rebuilt through the entrance by
topology, and the frosted leaves ship as a separate, explicitly-optional
replacement mesh with its own object.
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Vault/gable arch (docs/VERDANT_PROJECT_BRIEF.md + brief for this asset)
# ---------------------------------------------------------------------------
ARCH_CENTER_Y = 0.0
ARCH_CENTER_Z = 2035.2
ARCH_RADIUS = 7639.8
SPRINGING_Z = 3490.0
CROWN_Z = 9675.0
HALF_SPAN_Y = 7500.0
GABLE_PITCH = 300.0

# The new lattice field starts where it meets the existing lower glazing/dado,
# not at grade -- ENDDADO_W (z 0..900) and ENDGLAZE_W (z 900..3500) are
# existing, retained geometry. z=3500 sits above SPRINGING_Z (3490.0), so the
# entire authored domain is bounded purely by the circular arch, not the
# straight vault side walls.
FIELD_BASE_Z_WORLD = 3500.0
assert FIELD_BASE_Z_WORLD > SPRINGING_Z

# Local-to-world Z offset: local Z = 0 is the base of the authored geometry
# (the transfer/sill datum), matching this repo's base-centred-origin
# convention and the placement pattern used by prior Rootstead deliveries
# (place the OBJ at world (0, 0, FIELD_BASE_Z_WORLD)).
def world_z(local_z: float) -> float:
    return local_z + FIELD_BASE_Z_WORLD


def local_z(world_z_value: float) -> float:
    return world_z_value - FIELD_BASE_Z_WORLD


def arch_half_width_at_z(world_z_value: float) -> float:
    """Half-width (|y| extent) of the circular arch at a given world Z."""
    dz = world_z_value - ARCH_CENTER_Z
    inside = ARCH_RADIUS * ARCH_RADIUS - dz * dz
    return math.sqrt(inside) if inside > 0.0 else 0.0


# ---------------------------------------------------------------------------
# ENDGLAZE_W contact / transfer junction (level/rootstead_manifest.json family
# ENDGLAZE: ENDGLAZE_W_0..4, x -509..-431 world, z 900..3500)
# ---------------------------------------------------------------------------
ENDGLAZE_X_FAR = -509.0
ENDGLAZE_X_NEAR = -431.0
ENDGLAZE_Z_TOP = 3500.0

TRANSFER_CAP_Z_HEIGHT = 60.0  # local 0..60, world 3500..3560

# ---------------------------------------------------------------------------
# Gable field member planes (X depth). Inboard of the ENDGLAZE contact zone.
# ---------------------------------------------------------------------------
TUBE_X = -40.0
PANE_X = -58.0

# ---------------------------------------------------------------------------
# Structural member sizing by Z band. The z4000..6000 band must read as
# slender architectural aluminium, not PR17's heavy tube/flange language, and
# must be measurably slimmer than the "roof structure" band above z6000.
# ---------------------------------------------------------------------------
BAND_LOWER_Z_WORLD = 4000.0
BAND_UPPER_Z_WORLD = 6000.0

TUBE_RADIUS_LOWER = 9.0   # z < 4000 (transfer zone, near springing)
TUBE_RADIUS_MID = 5.5     # 4000 <= z < 6000 (slender band, no HERO_BAND)
TUBE_RADIUS_UPPER = 10.5  # z >= 6000 (upper lattice reads as roof structure)

JOINT_COLLAR_RADIUS_FACTOR = 1.6
JOINT_COLLAR_HALF_LENGTH = 11.0  # collar cylinder runs TUBE_X +/- this

def tube_radius_for_z(world_z_value: float) -> float:
    if world_z_value < BAND_LOWER_Z_WORLD:
        return TUBE_RADIUS_LOWER
    if world_z_value < BAND_UPPER_Z_WORLD:
        return TUBE_RADIUS_MID
    return TUBE_RADIUS_UPPER


# ---------------------------------------------------------------------------
# Entrance envelope (level/rootstead_manifest.json families DOOR, VEST, BULK;
# cross-checked against the brief).
# ---------------------------------------------------------------------------
# Existing animated leaf actors (DOOR_LeafL/R) -- this volume must stay
# completely empty of static geometry in the main OBJ, always.
LEAF_ENVELOPE_X = (-397.0, -353.0)
LEAF_ENVELOPE_Y = (-416.0, 416.0)
LEAF_ENVELOPE_Z_WORLD = (3508.0, 3892.0)

# Existing engine-cube references, kept for grounding/documentation only --
# this delivery authors real reveal/jamb/head/sill geometry, not a rebuild of
# these exact boxes. A 4 uu safety buffer is added beyond the leaf's y=416 so
# the new jamb solids never lap into the leaf envelope (the old DOOR_JambL/R
# at y 400..462 do lap over the leaf's y<=416, which is a normal door-rebate
# detail on the *existing* animated actors, but is not safe to reproduce on a
# static mesh that must guarantee leaf-envelope emptiness).
EXISTING_HEAD_X = (-412.0, -350.0)
EXISTING_HEAD_Y = (-462.0, 462.0)
EXISTING_HEAD_Z_WORLD = (3892.0, 3950.0)
EXISTING_JAMB_Y = (-462.0, -400.0)  # magnitude band; mirrored on +Y
EXISTING_SILL_X = (-445.0, -305.0)
EXISTING_SILL_Y = (-400.0, 400.0)
EXISTING_SILL_Z_WORLD = (3500.0, 3508.0)
OLD_PORTAL_FREIGHTLOCK_X = (-555.0, -195.0)
OLD_PORTAL_FREIGHTLOCK_Y = (-1300.0, 1300.0)
BULKHEAD_PLANE_X = (-451.0, -299.0)
VEST_FRAME_X_HARD_LIMIT = 128.0
VEST_FRAME_Y = (-972.0, 972.0)
VEST_FRAME_Z_WORLD = (3500.0, 4409.0)

# Authored entrance geometry (this delivery).
JAMB_Y_INNER = 424.0   # >= LEAF_ENVELOPE_Y[1] + 4 uu safety buffer, by construction below
JAMB_Y_OUTER = 480.0
JAMB_X_OUTER = -430.0
JAMB_X_INNER = -350.0
assert JAMB_Y_INNER >= LEAF_ENVELOPE_Y[1] + 4.0

HEAD_Y = (-480.0, 480.0)
HEAD_Z_WORLD = (3892.0, 3950.0)
HEAD_RETURN_Z_WORLD = (3950.0, 3974.0)  # soffit/drip return above the head face

SILL_X = (-430.0, -300.0)
SILL_Y = (-480.0, 480.0)
SILL_Z_WORLD = (3500.0, 3514.0)
SILL_NOSING_Z_WORLD = (3500.0, 3508.0)  # angled drip lip at the west edge

SHADOW_GAP_X = (-322.0, -316.0)  # thin recessed seal strip, reveal-to-facade
SHADOW_GAP_Y = (-480.0, 480.0)
SHADOW_GAP_Z_WORLD = (3500.0, 3974.0)

FROSTED_TRANSOM_X = (-390.0, -360.0)
FROSTED_TRANSOM_Y = (-450.0, 450.0)
FROSTED_TRANSOM_Z_WORLD = (3974.0, 4040.0)  # strictly above HEAD_RETURN_Z_WORLD, no interpenetration
assert FROSTED_TRANSOM_Z_WORLD[0] >= HEAD_RETURN_Z_WORLD[1]
assert FROSTED_TRANSOM_Z_WORLD[0] > LEAF_ENVELOPE_Z_WORLD[1]

# Entrance hole cut into the lattice field (topology-integrated aperture).
ENTRANCE_HOLE_HALF_Y = 560.0
ENTRANCE_HOLE_TOP_Z_WORLD = 4070.0
assert ENTRANCE_HOLE_HALF_Y > JAMB_Y_OUTER
assert ENTRANCE_HOLE_TOP_Z_WORLD > HEAD_RETURN_Z_WORLD[1]
assert ENTRANCE_HOLE_TOP_Z_WORLD > FROSTED_TRANSOM_Z_WORLD[1]

# ---------------------------------------------------------------------------
# Facade piers + trellis (side AND head bands). PR17's bug: rails centred at
# x=120 with radius 7 against a slab face also at x=120 -- zero/negative
# clearance. Fixed here with an explicit positive stand-off, and the whole
# assembly stays within the VEST_Frame hard east limit (x=128).
# ---------------------------------------------------------------------------
PIER_X = (0.0, 85.0)
PIER_Y_INNER = 560.0  # matches ENTRANCE_HOLE_HALF_Y so the pier starts right at the hole edge
PIER_Y_OUTER = 1300.0  # matches scale of the superseded PORTAL_FreightLock envelope
PIER_Z_WORLD = (3500.0, 4200.0)

HEAD_BAND_X = (0.0, 85.0)
HEAD_BAND_Y = (-560.0, 560.0)
HEAD_BAND_Z_WORLD = (4200.0, 4260.0)

TRELLIS_FACADE_FACE_X = 85.0  # = PIER_X[1] = HEAD_BAND_X[1]
TRELLIS_RAIL_X_CENTER = 104.0
TRELLIS_RAIL_RADIUS = 8.0
TRELLIS_TIE_RADIUS = 6.0
assert TRELLIS_RAIL_X_CENTER - TRELLIS_RAIL_RADIUS > TRELLIS_FACADE_FACE_X
assert TRELLIS_RAIL_X_CENTER + TRELLIS_RAIL_RADIUS < VEST_FRAME_X_HARD_LIMIT

# ---------------------------------------------------------------------------
# Material slot names.
# ---------------------------------------------------------------------------
MAT_ALUMINIUM = "M_WestEndwall_OxidisedAluminium"
MAT_GLAZE_ACRYLIC = "M_WestEndwall_GlazeAcrylic"
MAT_GLAZE_REPAIR = "M_WestEndwall_GlazeRepair"
MAT_ENTRANCE_REVEAL = "M_WestEndwall_EntranceReveal"
MAT_TRELLIS_STEEL = "M_WestEndwall_TrellisSteel"
MAT_SEAL_SHADOW_GAP = "M_WestEndwall_SealShadowGap"
MAT_FROSTED_TRANSOM = "M_WestEndwall_FrostedTransom"

MAIN_MATERIALS = {
    MAT_ALUMINIUM,
    MAT_GLAZE_ACRYLIC,
    MAT_GLAZE_REPAIR,
    MAT_ENTRANCE_REVEAL,
    MAT_TRELLIS_STEEL,
    MAT_SEAL_SHADOW_GAP,
    MAT_FROSTED_TRANSOM,
}

LEAF_MAT_FROSTED = "M_WestEndwallLeaf_FrostedGlass"
LEAF_MAT_FRAME = "M_WestEndwallLeaf_AluminiumFrame"
LEAF_MATERIALS = {LEAF_MAT_FROSTED, LEAF_MAT_FRAME}

# ---------------------------------------------------------------------------
# Asset names / paths.
# ---------------------------------------------------------------------------
MAIN_OBJ_NAME = "VD_RootsteadWestEndwallEntry"
LEAF_OBJ_NAME = "VD_RootsteadWestEndwallEntry_Leaves"

WORLD_PLACEMENT = (0.0, 0.0, FIELD_BASE_Z_WORLD)

# ---------------------------------------------------------------------------
# Tolerances used by the verifier.
# ---------------------------------------------------------------------------
TOL_BOUNDS = 1.0
TOL_ARCH_NODE = 2.0
TOL_HOLE_NODE = 2.0
TOL_NODE_TO_VERTEX = 0.05
DEGENERATE_AREA_EPS = 1e-4

"""Production contract for the Rootstead entrance bulkhead (Unreal cm)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "VD_RootsteadEntranceBulkhead"
PLACEMENT = (0.0, 0.0, 3500.0)
WALL_X = (-461.0, 112.0)
WALL_Y = (-1300.0, 1300.0)
WALL_Z_LOCAL = (0.0, 825.0)
DOOR_Y = 424.0
PLINTH_H = 150.0
COURSE_H = 225.0
WEST_BOUNDS = (-1300.0, -1154.0, -1008.0, -862.0, -716.0, -570.0, -424.0,
               424.0, 570.0, 716.0, 862.0, 1008.0, 1154.0, 1300.0)
# Deliberately unequal closure bays. Equal 191 bays put a joint at x=-79,
# through the call-button/beacon mounting range.
RETURN_BOUNDS = (-461.0, -281.0, -101.0, 112.0)
COURSE_BOUNDS = (150.0, 375.0, 600.0, 825.0)
FACE_X = -461.0
RELIEF_PROUD = 4.2
RECESS = 12.0
JOINT = 3.2
CHAMFER = 1.2
AGGREGATES_PER_MODULE = 14
SPALL_MODULES = 14
# Deterministic global module selections: 6 west, 4 outer-return, 4 door-return.
SPALL_INDICES = (0, 7, 14, 21, 28, 35, 36, 44, 54, 62, 45, 53, 63, 71)

MAT_STRUCTURE = "M_EntranceBulkhead_StructuralConcrete"
MAT_PLINTH = "M_EntranceBulkhead_BoardFormedPlinth"
MAT_PRECAST = "M_EntranceBulkhead_PrecastAggregate"
MAT_AGG = "M_EntranceBulkhead_ProudCoarseAggregate"
MAT_CHAMFER = "M_EntranceBulkhead_ChamferArris"
MAT_JOINT = "M_EntranceBulkhead_JointReveal"
MAT_SEAL = "M_EntranceBulkhead_SealantJoint"
MAT_SPALL = "M_EntranceBulkhead_SpallReveal"
MAT_REBAR = "M_EntranceBulkhead_RebarLug"
MAT_STREAK = "M_EntranceBulkhead_WeatherStreak"
MATERIALS = {MAT_STRUCTURE, MAT_PLINTH, MAT_PRECAST, MAT_AGG, MAT_CHAMFER,
             MAT_JOINT, MAT_SEAL, MAT_SPALL, MAT_REBAR, MAT_STREAK}
BANNED = ("rivet", "weld", "plate_seam", "steelplate", "steel_plate", "plating")

# AABBs are world X/Y and local Z. Strict/open y is handled by the verifier.
EXCLUSIONS = {
 "door_leaf": ((-397.,-353.),(-416.,416.),(8.,392.)),
 "clear_doorway": ((-509.,112.),(-424.,424.),(0.,392.)),
 "jamb_positive": ((-412.,-350.),(400.,462.),(0.,450.)),
 "jamb_negative": ((-412.,-350.),(-462.,-400.),(0.,450.)),
 "head": ((-412.,-350.),(-462.,462.),(392.,450.)),
 "sill": ((-445.,-305.),(-400.,400.),(0.,8.)),
 "track": ((-410.,-352.),(-462.,462.),(366.,392.)),
}
MOUNTS = {
 "DOOR_PanelIn": {"x":(-84.,-16.), "y":-424., "z":(128.,222.), "normal":(0.,1.,0.)},
 "BEACON_positive": {"x":(-75.,-49.), "y":424., "z":(275.,325.), "normal":(0.,-1.,0.)},
 "BEACON_negative": {"x":(-75.,-49.), "y":-424., "z":(275.,325.), "normal":(0.,1.,0.)},
}

# Explicit collision boxes: broad outer wing plus notched inner strip pieces.
# Centers/extents are produced from these exact min/max world bounds.
COLLISION_BOXES = []
for sign in (-1, 1):
    ya,yb = ((-1300.,-462.) if sign < 0 else (462.,1300.))
    COLLISION_BOXES.append((f"wing_{'neg' if sign<0 else 'pos'}_outer", (-461.,112.), (ya,yb), (3500.,4325.)))
    ya,yb = ((-462.,-424.) if sign < 0 else (424.,462.))
    for label,xa,xb,za,zb in (("west",-461.,-412.,3500.,4325.),
                              ("east",-350.,112.,3500.,4325.),
                              ("above",-412.,-350.,3950.,4325.)):
        COLLISION_BOXES.append((f"wing_{'neg' if sign<0 else 'pos'}_inner_{label}", (xa,xb), (ya,yb), (za,zb)))

# RIDING + ROWING bodies.
#   mount(rider_rig, rider_root, seat)  - a rider sits ASTRIDE the horse (Session E's horse + tack: the 'rider_seat'
#                                         empty follows the horse's spine, so the rider moves with trot / gallop)
#   rowing(rig, start, end, period_s)   - a rower's stroke on a trireme bench, looped in time with the oars:
#                                         reach forward (catch) -> drive the legs + lean back + pull the arms (finish)
#                                         -> recover. Thranite / zygite / thalamite rowers all use this stroke.
# Rider details from the period: Greek and Persian riders sat bareback or on a saddle cloth, with NO stirrups, so the
# thighs grip the horse's sides, the lower legs hang, the toes point down (Parthenon frieze, Attic vases).
import math

import bpy
from mathutils import Vector

from lib import pose

pose.POSES.setdefault('ride', {
    # thighs forward and spread round the horse's barrel, lower legs hanging, toes down; hands forward on the reins
    "upperleg01.L": (0.35, -0.75, -0.55), "upperleg01.R": (-0.35, -0.75, -0.55),
    "lowerleg01.L": (0.12, 0.25, -1.0), "lowerleg01.R": (-0.12, 0.25, -1.0),
    "foot.L": (0.05, -0.2, -1.0), "foot.R": (-0.05, -0.2, -1.0),
    "upperarm01.L": (0.15, -0.6, -0.75), "upperarm01.R": (-0.15, -0.6, -0.75),
    "lowerarm01.L": (-0.05, -1.0, -0.1), "lowerarm01.R": (0.05, -1.0, -0.1),
    "_fingers": 0.85,
})
pose.POSES.setdefault('row_catch', {      # reach: arms long and forward, torso leaning forward over the knees
    "spine05": (0.0, -0.45, 1.0), "upperarm01.L": (0.12, -0.85, -0.45), "upperarm01.R": (-0.12, -0.85, -0.45),
    "lowerarm01.L": (0.05, -1.0, -0.05), "lowerarm01.R": (-0.05, -1.0, -0.05),
    "upperleg01.L": (0.1, -0.95, 0.25), "upperleg01.R": (-0.1, -0.95, 0.25),
    "lowerleg01.L": (0.05, -0.3, -1.0), "lowerleg01.R": (-0.05, -0.3, -1.0), "_fingers": 0.95,
})
pose.POSES.setdefault('row_finish', {     # finish: legs pushed long, torso leaning back, hands pulled to the chest
    "spine05": (0.0, 0.3, 1.0), "upperarm01.L": (0.25, 0.25, -0.95), "upperarm01.R": (-0.25, 0.25, -0.95),
    "lowerarm01.L": (0.1, -1.0, 0.3), "lowerarm01.R": (-0.1, -1.0, 0.3),
    "upperleg01.L": (0.1, -1.0, -0.05), "upperleg01.R": (-0.1, -1.0, -0.05),
    "lowerleg01.L": (0.05, -0.85, -0.55), "lowerleg01.R": (-0.05, -0.85, -0.55), "_fingers": 0.95,
})


def mount(rig, root, seat, frame=1, heading_deg=0.0):
    """Sit the rider (built at the origin, facing -Y) on the horse: astride pose, pelvis on the seat marker, then
    parented to the seat so every step of the horse's gait carries him (the bounce of a real trot)."""
    pose.apply_pose(rig, 'ride')
    pose.keyframe_pose(rig, frame, pose.pose_bones('ride'))
    bpy.context.view_layer.update()
    pelvis = rig.matrix_world @ rig.pose.bones['root'].head
    root.rotation_euler.z = math.radians(heading_deg)             # face where the horse faces (test per model)
    bpy.context.view_layer.update()
    pelvis = rig.matrix_world @ rig.pose.bones['root'].head
    root.location = root.location + (seat.matrix_world.translation - pelvis) + Vector((0, 0, 0.04))
    bpy.context.view_layer.update()
    w = root.matrix_world.copy()
    root.parent = seat; root.matrix_world = w
    return root


def rowing(rig, start, end, period_s=34 / 24, phase_s=0.0, fps=24):
    """Loop the rowing stroke from `start` to `end`: catch at 0, finish at 45 % of the period (the drive is quicker
    than the recovery), back to catch. `period_s` should equal the oars' stroke period (Session E's trireme_v2)."""
    p = period_s * fps
    f = start - (phase_s * fps) % p
    while f < end:
        for name, t in (('row_catch', 0.0), ('row_finish', 0.45)):
            fr = int(round(f + t * p))
            if start <= fr <= end:
                bpy.context.scene.frame_set(fr)
                pose.apply_pose(rig, name)
                pose.keyframe_pose(rig, fr, pose.pose_bones(name))
        f += p

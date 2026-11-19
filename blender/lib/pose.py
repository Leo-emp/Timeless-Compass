# POSES: set a character's skeleton by pointing bones in directions (easy to read and write), plus
# keyframing so cloth can be simulated while the body moves from the rest A-pose into the final pose.
# Directions are in world space: character faces -Y, up is +Z, his RIGHT side is -X.
import math

import bpy
from mathutils import Matrix, Vector


def aim(rig, name, direction):
    """Rotate a bone so it points along `direction`, keeping its head (joint) where it is.
    `direction` is in the CHARACTER's own frame (facing -Y, up +Z), so a pose means the same thing however the
    character is turned or wherever it stands (pose bones live in armature space, which turns with the rig)."""
    bpy.context.view_layer.update()
    pb = rig.pose.bones[name]
    h = pb.head.copy()
    q = (pb.tail - pb.head).rotation_difference(Vector(direction).normalized())
    pb.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ pb.matrix
    bpy.context.view_layer.update()


def curl_fingers(rig, side, amount=1.0):
    """amount 0 = open hand, 1 = fist."""
    for f in range(1, 6):
        for j in range(1, 4):
            pb = rig.pose.bones.get(f'finger{f}-{j}.{side}')
            if pb:
                pb.rotation_mode = 'XYZ'
                pb.rotation_euler = (math.radians((55 if f > 1 else 25) * amount), 0, 0)


POSES = {
    # standing, arms relaxed by the sides, weight slightly on one leg
    "stand_relaxed": {"upperarm01.R": (-0.12, 0.02, -1), "lowerarm01.R": (-0.05, -0.12, -1),
                      "upperarm01.L": (0.12, 0.02, -1), "lowerarm01.L": (0.05, -0.12, -1),
                      "upperleg01.L": (0.05, -0.04, -1), "upperleg01.R": (-0.03, 0.02, -1),
                      "lowerleg01.L": (0.02, 0.03, -1), "lowerleg01.R": (-0.02, 0.0, -1),
                      "_fingers": 0.35},
    # hoplite at the ready: spear upright in the right hand, shield arm across the front
    "hoplite_ready": {"upperarm01.R": (-0.25, -0.2, -1), "lowerarm01.R": (-0.05, -1.0, 0.55),
                      "upperarm01.L": (0.32, -0.25, -1), "lowerarm01.L": (-0.8, -0.55, 0.3),
                      "upperleg01.L": (0.07, -0.12, -1), "upperleg01.R": (-0.06, 0.08, -1),
                      "lowerleg01.L": (0.03, 0.04, -1), "lowerleg01.R": (-0.03, 0.02, -1),
                      "_fingers": 0.9},
    # receiving something with both hands, a slight respectful bow of the head
    "receive": {"upperarm01.R": (-0.12, -0.5, -0.85), "lowerarm01.R": (0.2, -1.0, 0.3),
                "upperarm01.L": (0.12, -0.5, -0.85), "lowerarm01.L": (-0.2, -1.0, 0.3),
                "neck01": (0, -0.25, 1), "head": (0, -0.35, 1),
                "upperleg01.L": (0.04, 0.03, -1), "upperleg01.R": (-0.04, -0.06, -1),
                "lowerleg01.L": (0.02, 0.0, -1), "lowerleg01.R": (-0.02, 0.03, -1),
                "_fingers": 0.4},
    # the same without the head bow (used while cloth simulates; the bow is added after)
    "receive_body": {"upperarm01.R": (-0.12, -0.5, -0.85), "lowerarm01.R": (0.2, -1.0, 0.3),
                     "upperarm01.L": (0.12, -0.5, -0.85), "lowerarm01.L": (-0.2, -1.0, 0.3),
                     "upperleg01.L": (0.04, 0.03, -1), "upperleg01.R": (-0.04, -0.06, -1),
                     "lowerleg01.L": (0.02, 0.0, -1), "lowerleg01.R": (-0.02, 0.03, -1),
                     "_fingers": 0.4},
    # handing something over with the right hand (Themistocles giving the message)
    "hand_over": {"upperarm01.R": (-0.12, -0.78, -0.6), "lowerarm01.R": (-0.08, -1.0, 0.06),   # reach well forward
                  "upperarm01.L": (0.12, 0.02, -1), "lowerarm01.L": (0.05, -0.12, -1),
                  "upperleg01.L": (0.05, -0.08, -1), "upperleg01.R": (-0.03, 0.05, -1),
                  "lowerleg01.L": (0.02, 0.03, -1), "lowerleg01.R": (-0.02, 0.0, -1),
                  "_fingers": 0.5},
}


def apply_pose(rig, pose_name):
    p = POSES[pose_name]
    for bone, d in p.items():
        if not bone.startswith('_'):
            aim(rig, bone, d)
    for side in ('L', 'R'):
        curl_fingers(rig, side, p.get('_fingers', 0.3))
    bpy.context.view_layer.update()


def pose_bones(pose_name):
    """Bones a named pose drives (its aimed bones + all finger bones); everything else stays free for the life
    layer (breathing, eyes, blinks) and facial expressions."""
    names = {b for b in POSES[pose_name] if not b.startswith('_')}
    names |= {f'finger{f}-{j}.{s}' for f in range(1, 6) for j in range(1, 4) for s in 'LR'}
    return names


def keyframe_pose(rig, frame, only=None):
    """Store the current pose at `frame`: every bone, or only the bones named in `only`."""
    for pb in rig.pose.bones:
        if only is not None and pb.name not in only:
            continue
        pb.keyframe_insert('rotation_quaternion' if pb.rotation_mode == 'QUATERNION' else 'rotation_euler', frame=frame)
        pb.keyframe_insert('location', frame=frame)


def blend_into_pose(rig, pose_name, start=1, end=15):
    """Rest pose at `start`, the named pose at `end` (cloth simulates while the body moves into place)."""
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    keyframe_pose(rig, start)
    apply_pose(rig, pose_name)
    # aim() writes pb.matrix; convert every bone back to quaternion channels before keying
    keyframe_pose(rig, end)


def walk_cycle(rig, start=1, end=96, stride_s=1.0, step_deg=24.0, arm_deg=16.0, forward_m_per_s=1.25, fps=24):
    """A procedural walk (placeholder for motion capture), layered ON TOP of the current pose (e.g. stand_relaxed
    at frame `start`): thighs swing +-step_deg, knees bend in the swing phase, arms swing opposite to the legs,
    and the whole rig moves forward (-Y) at walking speed."""
    import math as m
    from mathutils import Quaternion
    bpy.context.scene.frame_set(start); bpy.context.view_layer.update()
    names = [f'{b}.{s}' for b in ('upperleg01', 'lowerleg01', 'upperarm01', 'lowerarm01') for s in ('L', 'R')]
    base = {n: rig.pose.bones[n].rotation_quaternion.copy() for n in names if n in rig.pose.bones}
    base_y = rig.location.y
    for f in range(start, end + 1, 2):
        ph = 2 * m.pi * ((f - start) / fps) / stride_s
        for side, sgn in (('L', 1), ('R', -1)):
            swing = m.sin(ph) * sgn
            rot = {f'upperleg01.{side}': m.radians(step_deg) * swing,
                   f'lowerleg01.{side}': -max(0.0, -m.cos(ph) * sgn) * m.radians(35),
                   f'upperarm01.{side}': -m.radians(arm_deg) * swing,
                   f'lowerarm01.{side}': m.radians(8)}
            for n, ang in rot.items():
                if n in base:
                    pb = rig.pose.bones[n]
                    pb.rotation_quaternion = base[n] @ Quaternion((1, 0, 0), ang)      # swing about the bone's own X axis
                    pb.keyframe_insert('rotation_quaternion', frame=f)
        rig.location.y = base_y - forward_m_per_s * (f - start) / fps
        rig.keyframe_insert('location', index=1, frame=f)


def gesture(rig, pose_name, start, end, hold_from=None):
    """Move from whatever pose the body is in at `start` into `pose_name` by `end` (eased), keying only that pose's
    bones. Call in time order: each gesture starts from where the previous one ended."""
    only = pose_bones(pose_name)
    bpy.context.scene.frame_set(start); bpy.context.view_layer.update()
    keyframe_pose(rig, start, only)
    apply_pose(rig, pose_name)
    keyframe_pose(rig, end, only)
    if hold_from is not None:
        keyframe_pose(rig, hold_from, only)


def reach(rig, side, target_world, pole=(0.0, 0.4, -1.0), wrist_bend=True):
    """Two-bone REACH (analytic IK): put the hand of arm `side` ('L'/'R') on a point in the world, with the elbow
    bending naturally toward `pole` (character space: +Y back, -Z down = elbows hang down and slightly back).
    Used for real contacts: handing an object over, taking it, touching a shoulder, gripping a spear."""
    bpy.context.view_layer.update()
    inv = rig.matrix_world.inverted()
    T = inv @ Vector(target_world)                               # target in armature space
    up = rig.pose.bones[f'upperarm01.{side}']
    lo = rig.pose.bones[f'lowerarm01.{side}']
    wr = rig.pose.bones[f'wrist.{side}']
    S = up.head.copy()
    a = (rig.pose.bones[f'upperarm02.{side}'].tail - up.head).length      # shoulder -> elbow (both twist bones)
    b = (rig.pose.bones[f'lowerarm02.{side}'].tail - lo.head).length      # elbow -> wrist
    d = min((T - S).length, (a + b) * 0.995)                     # can't reach further than the arm is long
    fwd = (T - S).normalized()
    x = (a * a - b * b + d * d) / (2 * d)                        # law of cosines: elbow position along shoulder->target
    h = math.sqrt(max(a * a - x * x, 0.0))
    p = Vector(pole); p = (p - fwd * p.dot(fwd)).normalized()    # bend direction, perpendicular to the reach line
    E = S + fwd * x + p * h
    aim(rig, f'upperarm01.{side}', E - S)
    aim(rig, f'upperarm02.{side}', E - S)
    aim(rig, f'lowerarm01.{side}', (S + fwd * d) - E)
    aim(rig, f'lowerarm02.{side}', (S + fwd * d) - E)
    if wrist_bend:                                               # hand continues the forearm, palm slightly in
        aim(rig, f'wrist.{side}', ((S + fwd * d) - E).normalized() + Vector((0, 0, -0.15)))
    bpy.context.view_layer.update()


def key_arm(rig, side, frame):
    """Keyframe one arm (after reach()) so it can be animated between reaches."""
    for n in ('upperarm01', 'upperarm02', 'lowerarm01', 'lowerarm02', 'wrist'):
        pb = rig.pose.bones[f'{n}.{side}']
        pb.keyframe_insert('rotation_quaternion' if pb.rotation_mode == 'QUATERNION' else 'rotation_euler', frame=frame)

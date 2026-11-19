# MOTION CAPTURE: real human movement from the free CMU Graphics Lab Motion Capture Database
# (BVH files, mirror: github.com/sfd158/cmu-mocap; "free for all uses", credit: mocap.cs.cmu.edu).
# MPFB's "cmu_mb" rig uses the same bone names as these files. We copy each bone's roll from the BVH
# skeleton onto ours (so rotations mean the same thing), then copy rotations frame by frame, and scale the hip
# travel to our character's leg length.
import math
import os

import bpy
from mathutils import Matrix, Vector

from bl_ext.blender_org.mpfb.services.humanservice import HumanService
from bl_ext.blender_org.mpfb.services.objectservice import ObjectService

MOCAP_DIR = os.environ.get('TC_MOCAP', 'C:/Users/User/tools/mocap')
# default-rig bone -> cmu_mb bone, for things pinned to a bone (hair, helmet, shield, spear)
TO_CMU = {'head': 'Head', 'neck01': 'Neck', 'wrist.R': 'RightHand', 'wrist.L': 'LeftHand',
          'lowerarm01.L': 'LeftForeArm', 'lowerarm01.R': 'RightForeArm', 'lowerarm02.R': 'RightForeArm',
          'lowerarm02.L': 'LeftForeArm', 'spine01': 'Spine1', 'spine03': 'Spine', 'pelvis': 'Hips'}


def swap_to_mocap_rig(human, old_rig):
    """Characters are first built with MPFB's detailed 'default' rig (its face/body weight groups define where the
    beard and hair grow). For motion capture, replace it with the 'cmu_mb' rig and re-attach hair to 'Head'."""
    # everything pinned to the old head bone: hair, beard, eyes, brows, lashes, teeth (see cast.build_human)
    hair = [o for o in bpy.data.objects if o.parent is old_rig and o.parent_type == 'BONE']
    keep = {o: o.matrix_world.copy() for o in hair}
    old_bone = {o: o.parent_bone for o in hair}
    for m in list(human.modifiers):
        if m.type == 'ARMATURE':
            human.modifiers.remove(m)
    w = human.matrix_world.copy(); human.parent = None; human.matrix_world = w
    bpy.data.objects.remove(old_rig, do_unlink=True)
    HumanService.add_builtin_rig(human, 'cmu_mb', import_weights=True)
    rig = ObjectService.find_object_of_type_amongst_nearest_relatives(human, 'Skeleton')
    bpy.context.view_layer.update()
    for o, mw in keep.items():
        o.parent = rig; o.parent_type = 'BONE'; o.parent_bone = TO_CMU.get(old_bone[o], 'Head')
        bpy.context.view_layer.update(); o.matrix_world = mw
    return rig


def _rest_align(src_b, dst_b, src_w, dst_w):
    """Rotation (world) that turns our bone's rest direction onto the BVH bone's rest direction.
    Needed because CMU files are recorded from a T-pose (arms straight out) and MPFB rigs rest in a different pose."""
    s_dir = (src_w @ (src_b.tail_local - src_b.head_local)).normalized()
    d_dir = (dst_w @ (dst_b.tail_local - dst_b.head_local)).normalized()
    return d_dir.rotation_difference(s_dir).to_matrix()


def _after_tpose(src, f0, f1):
    """First frame where both upper arms hang down (not held out sideways), plus a few frames of margin."""
    sc = bpy.context.scene
    for f in range(f0, f1):
        sc.frame_set(f)
        down = True
        for n in ('LeftArm', 'RightArm'):
            pb = src.pose.bones[n]
            d = (src.matrix_world @ pb.tail) - (src.matrix_world @ pb.head)
            down &= d.normalized().z < -0.6
        if down:
            return min(f + 4, f1)
    return f0


# CMU bone -> MPFB 'default' rig bone (the full rig with face bones: eyes, lids, jaw, lips, brows).
# Bones in between (spine04, spine02, neck02, shoulder01, twist bones upperarm02/lowerarm02) are NOT driven:
# they follow their parent, and stay free for the life layer (breathing, head drift) to add small motions.
DEFAULT_RIG_MAP = {
    'Hips': 'root', 'LowerBack': 'spine05', 'Spine': 'spine03', 'Spine1': 'spine01',
    'Neck': 'neck01', 'Neck1': 'neck03', 'Head': 'head',
    'LeftShoulder': 'clavicle.L', 'LeftArm': 'upperarm01.L', 'LeftForeArm': 'lowerarm01.L', 'LeftHand': 'wrist.L',
    'RightShoulder': 'clavicle.R', 'RightArm': 'upperarm01.R', 'RightForeArm': 'lowerarm01.R', 'RightHand': 'wrist.R',
    'LeftUpLeg': 'upperleg01.L', 'LeftLeg': 'lowerleg01.L', 'LeftFoot': 'foot.L',
    'RightUpLeg': 'upperleg01.R', 'RightLeg': 'lowerleg01.R', 'RightFoot': 'foot.R',
}
# limbs are re-aimed from the actor's T-pose onto our rest pose; the trunk keeps OUR natural posture and only
# receives the actor's change of rotation (otherwise every character would inherit the actor's slouch)
_ALIGN = ('clavicle', 'upperarm', 'lowerarm', 'wrist', 'upperleg', 'lowerleg', 'foot',
          'Arm', 'Leg', 'Foot', 'Hand', 'Shoulder')


# Mixamo (FBX, bones named 'mixamorig:<name>') -> MPFB default rig. Mixamo's spine is split Spine/Spine1/Spine2.
MIXAMO_MAP = {
    'Hips': 'root', 'Spine': 'spine05', 'Spine1': 'spine03', 'Spine2': 'spine01', 'Neck': 'neck01', 'Head': 'head',
    'LeftShoulder': 'clavicle.L', 'LeftArm': 'upperarm01.L', 'LeftForeArm': 'lowerarm01.L', 'LeftHand': 'wrist.L',
    'RightShoulder': 'clavicle.R', 'RightArm': 'upperarm01.R', 'RightForeArm': 'lowerarm01.R', 'RightHand': 'wrist.R',
    'LeftUpLeg': 'upperleg01.L', 'LeftLeg': 'lowerleg01.L', 'LeftFoot': 'foot.L',
    'RightUpLeg': 'upperleg01.R', 'RightLeg': 'lowerleg01.R', 'RightFoot': 'foot.R',
}


def bone_map_for(rig):
    """cmu_mb rigs use the CMU names themselves; the default rig needs DEFAULT_RIG_MAP."""
    return {k: k for k in DEFAULT_RIG_MAP} if 'Hips' in rig.data.bones else DEFAULT_RIG_MAP


def _floor_z(rig):
    toes = [b for b in rig.data.bones if 'toe' in b.name.lower()]
    feet = toes or [b for b in rig.data.bones if 'foot' in b.name.lower()]
    return min((rig.matrix_world @ b.tail_local).z for b in feet)


def ground_feet(rig, first, last, root='root', floor=None):
    """GROUNDING: keep the feet on the floor. For every frame, find the lowest point of either foot and move the whole
    body (root bone) up or down by the difference, so the lowest foot touches the ground (motion clips retargeted onto
    a body with different proportions float or sink otherwise: measured up to 1.6 m on some Mixamo clips)."""
    sc = bpy.context.scene
    feet = [b for b in ('foot.L', 'foot.R', 'toe1-1.L', 'toe1-1.R') if b in rig.pose.bones]
    if floor is None:
        floor = _floor_z(rig)
    pb = rig.pose.bones[root]
    rest_inv = rig.data.bones[root].matrix_local.to_3x3().inverted()
    for f in range(first, last + 1):
        sc.frame_set(f)
        low = min(min((rig.matrix_world @ rig.pose.bones[n].head).z, (rig.matrix_world @ rig.pose.bones[n].tail).z) for n in feet)
        dz = floor - low
        if abs(dz) < 0.004:
            continue
        loc = pb.location.copy()
        pb.location = loc + rest_inv @ (rig.matrix_world.to_3x3().inverted() @ Vector((0, 0, dz)))
        pb.keyframe_insert('location', frame=f)


def apply_bvh(rig, clip, start=1, hold=0, max_frames=None, fps=24, travel=True, skip='auto', bone_map=None, ground=True):
    """Play BVH `clip` (e.g. '16_15') on `rig` from frame start+hold. Frames start..start+hold blend from our rest
    pose into the first mocap pose (cloth pre-roll). Returns the last frame written.

    Retargeting is done in WORLD space, so it does not care how either skeleton's bones are rolled:
        delta  = (BVH bone now) x (BVH bone at rest)^-1     how far the real actor's bone has turned
        target = delta x align x (our bone at rest)         align = our rest direction -> BVH rest direction (limbs)
    then converted back into each bone's own local rotation, parents first (undriven bones follow their parent)."""
    if os.path.exists(clip):
        path = clip
    elif os.path.exists(os.path.join(MOCAP_DIR, 'mixamo', clip + '.fbx')):
        path = os.path.join(MOCAP_DIR, 'mixamo', clip + '.fbx')           # e.g. 'breathing_idle'
    else:
        path = os.path.join(MOCAP_DIR, clip + '.bvh')                     # e.g. CMU '16_15'
    sc = bpy.context.scene; sc.render.fps = fps
    before = set(bpy.data.objects)
    if path.lower().endswith('.fbx'):                                     # Mixamo: FBX importer handles Y-up + cm
        bpy.ops.import_scene.fbx(filepath=path, use_anim=True, ignore_leaf_bones=True, automatic_bone_orientation=False)
        src = next(o for o in set(bpy.data.objects) - before if o.type == 'ARMATURE')
        for o in set(bpy.data.objects) - before:
            if o is not src:
                bpy.data.objects.remove(o, do_unlink=True)
        if skip == 'auto':
            skip = 0                                                      # Mixamo clips have no calibration pose
    else:
        # CMU BVH is Y-up: Blender's importer converts to Z-up with these (its defaults)
        bpy.ops.import_anim.bvh(filepath=path, axis_forward='-Z', axis_up='Y', rotate_mode='NATIVE',
                                use_fps_scale=True, update_scene_fps=False, update_scene_duration=False)
        src = bpy.context.object
    act = src.animation_data.action
    f0, f1 = (int(x) for x in act.frame_range)
    if skip == 'auto':                             # many CMU takes open with a calibration T-pose: start after it
        f0 = _after_tpose(src, f0, f1)
    else:
        f0 += int(skip)
    prefix = next((b.name.split(':')[0] + ':' for b in src.data.bones if ':' in b.name), '')
    if bone_map is None and prefix:
        bone_map = MIXAMO_MAP
    bmap = bone_map or bone_map_for(rig)
    S = lambda n: prefix + n                       # source bone name (Mixamo bones carry 'mixamorig:')
    to_src = {d: S(s) for s, d in bmap.items() if S(s) in src.data.bones and d in rig.data.bones}
    root_dst = bmap['Hips']
    sw, dw = src.matrix_world.to_3x3(), rig.matrix_world.to_3x3()
    dw_inv = dw.inverted()
    rest_s_inv, target_rest = {}, {}
    for d, s_name in to_src.items():
        sb, db = src.data.bones[s_name], rig.data.bones[d]
        rest_s_inv[d] = (sw @ sb.matrix_local.to_3x3()).inverted()
        align = _rest_align(sb, db, sw, dw) if any(t in d for t in _ALIGN) else Matrix.Identity(3)
        target_rest[d] = align @ dw @ db.matrix_local.to_3x3()
    # hip travel scaled by leg length (hip height above the feet, measured in the first frame)
    sc.frame_set(f0)
    src_hip0 = src.matrix_world @ src.pose.bones[S('Hips')].head
    src_floor = min((src.matrix_world @ src.pose.bones[S(n)].tail).z for n in ('LeftToeBase', 'RightToeBase') if S(n) in src.pose.bones)
    our_hip = rig.matrix_world @ rig.data.bones[root_dst].head_local
    our_floor = _floor_z(rig)
    k = (our_hip.z - our_floor) / max(src_hip0.z - src_floor, 1e-6)
    for d in to_src:
        rig.pose.bones[d].rotation_mode = 'QUATERNION'
    n = f1 - f0 if max_frames is None else min(f1 - f0, max_frames)
    if hold:                                       # rest pose at `start`, blending into the first mocap pose
        for d in to_src:                           # (garments are built at rest; the cloth settles while it moves)
            pb = rig.pose.bones[d]
            pb.rotation_quaternion = (1, 0, 0, 0); pb.keyframe_insert('rotation_quaternion', frame=start)
        rig.pose.bones[root_dst].location = (0, 0, 0)
        rig.pose.bones[root_dst].keyframe_insert('location', frame=start)
    root_b = rig.data.bones[root_dst]
    order = list(rig.data.bones)                   # parents first
    for i in range(n + 1):
        sc.frame_set(f0 + i)
        frame = start + hold + i
        arm = {}                                   # armature-space rotation of each of our bones this frame
        for b in order:
            rest_local = b.matrix_local.to_3x3()
            parent_arm = None
            if b.parent is not None:
                parent_arm = arm[b.parent.name] @ (b.parent.matrix_local.to_3x3().inverted() @ rest_local)
            if b.name not in to_src:               # undriven: follows its parent at its rest offset
                arm[b.name] = parent_arm if parent_arm is not None else rest_local
                continue
            s_now = sw @ src.pose.bones[to_src[b.name]].matrix.to_3x3()
            arm[b.name] = dw_inv @ ((s_now @ rest_s_inv[b.name]) @ target_rest[b.name])
            base = parent_arm if parent_arm is not None else rest_local
            pb = rig.pose.bones[b.name]
            pb.rotation_quaternion = (base.inverted() @ arm[b.name]).to_quaternion()
            pb.keyframe_insert('rotation_quaternion', frame=frame)
        # root travel: BVH hip movement since frame 0 (world), scaled, expressed in the root bone's rest axes
        move = (src.matrix_world @ src.pose.bones[S('Hips')].head) - src_hip0
        if not travel:
            move.x = move.y = 0.0
        d_arm = dw_inv @ (move * k)
        d_arm.z += (src_hip0.z - src_floor) * k - (our_hip.z - our_floor)   # ~0: keeps the feet on the floor
        rig.pose.bones[root_dst].location = root_b.matrix_local.to_3x3().inverted() @ d_arm
        rig.pose.bones[root_dst].keyframe_insert('location', frame=frame)
    bpy.data.objects.remove(src, do_unlink=True)
    if ground:                                     # feet on the floor every frame (see ground_feet)
        ground_feet(rig, start + hold, start + hold + n, root=root_dst, floor=our_floor)
    sc.frame_set(start)
    return start + hold + n

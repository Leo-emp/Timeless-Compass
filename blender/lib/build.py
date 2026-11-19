# BUILD FROM MANIFESTS: turns names in a shot recipe (written by `tc assemble`) into library calls.
# A character is built at the ORIGIN facing -Y (what the garment builders expect), dressed, and then carried to its
# stage mark by one root empty. Two motion paths:
#   pose  -> default MPFB rig, named pose, cloth simulated then frozen (cheapest, best for still moments)
#   clip  -> rig swapped to cmu_mb, motion capture applied, cloth FOLLOWS the skeleton and is baked over a pre-roll
import json
import math
import os

import bpy
from mathutils import Vector

from lib import cast, motion, pose, sets, wardrobe

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
PREROLL = 30
CMU_ALIASES = {'upperarm01.L': 'LeftArm', 'upperarm01.R': 'RightArm', 'upperleg01.L': 'LeftUpLeg',
               'upperleg01.R': 'RightUpLeg', 'lowerleg01.L': 'LeftLeg', 'lowerleg01.R': 'RightLeg', 'neck01': 'Neck'}


def manifest(kind, name):
    return json.load(open(os.path.join(ROOT, 'library', kind, name + '.json'), encoding='utf-8'))


def _materials(wardrobe_name):
    """Era-correct dyes per wardrobe (see library/wardrobe/*.json)."""
    if wardrobe_name == 'greek_civilian_480bc':
        return {'chiton': wardrobe.border_material('linen_border', (0.80, 0.75, 0.64), (0.08, 0.12, 0.30), width=0.035),
                'himation': wardrobe.border_material('wool_madder', (0.22, 0.035, 0.03), (0.05, 0.04, 0.03), edge=1, width=0.025)}
    raise KeyError(f'no builder for wardrobe {wardrobe_name!r} yet')


def character(name, wardrobe_name, motion_spec, mark=(0, 0, 0), turn_deg=0.0, frames=96, spec=None):
    """Build, dress and animate one character on the FULL face rig (motion capture works on it directly).
    Garments drape while the body stands still, then FOLLOW the skeleton (wardrobe.settle_then_follow), so they
    move with any motion. motion_spec: {'clip': '16_15' | 'breathing_idle' (Mixamo)} or {'pose': 'hand_over'}.
    `spec` = a full cast dict (e.g. from tc crowd) instead of library/cast/<name>.json.
    Returns (rig, human, root, first_shot_frame, last_frame)."""
    before = set(bpy.data.objects)
    spec = spec or manifest('cast', name)
    human, rig = cast.build_human(spec)
    bpy.context.view_layer.update()
    cast.groom(human, rig, spec)
    try:
        mats = _materials(wardrobe_name) if wardrobe_name else {}
    except KeyError:                                     # not a live-cloth chiton outfit: full era costume (WS3)
        mats = {}
        from lib import costume
        made = costume.dress(human, rig, cast.rest_surface(human)[0], wardrobe_name, dye=spec.get('dye'), seed=hash(name) % 1000)
        if (wardrobe_name or '').endswith('hoplite_480bc'):        # named hoplites (Leonidas...) get the full bronze kit
            from lib import crowd as C
            ch = next((o for o in made if o.name.startswith('chiton')), None)
            if ch is not None:
                C.arm_hoplite(dict(spec, shield=spec.get('shield') or {'emblem': 'lambda', 'wear': 0.4}), human, rig, ch)
    pos, _, _ = cast.rest_surface(human)
    wardrobe.add_collision(human)
    garments = []
    if 'chiton' in mats:
        ch = wardrobe.chiton(human, rig, pos, mats['chiton'])
        wardrobe.settle_then_follow(ch, human, rig, frames=45, soft=0.25, air=1.0)
        ch.modifiers.new('collision', 'COLLISION'); ch.collision.thickness_outer = 0.012; ch.collision.use_culling = False
        garments.append(ch)
        if 'himation' in mats:
            hm = wardrobe.himation(human, rig, pos, mats['himation'], side='L', over=ch)
            wardrobe.settle_then_follow(hm, human, rig, frames=60, soft=0.35, mass=0.45, air=0.5)
            garments.append(hm)
    first = PREROLL + 1
    if motion_spec and 'clip' in motion_spec:
        last = motion.apply_bvh(rig, motion_spec['clip'], start=1, hold=PREROLL, max_frames=frames - 1)
    else:
        pose.blend_into_pose(rig, (motion_spec or {}).get('pose', 'stand_relaxed'), start=1, end=PREROLL)
        last = first + frames - 1
    for g in garments:
        for m in g.modifiers:
            if m.type == 'CLOTH':
                m.point_cache.frame_start, m.point_cache.frame_end = 1, last
    human.modifiers.new('smooth', 'SUBSURF').levels = 1
    root = bpy.data.objects.new(f'{name}_root', None); bpy.context.scene.collection.objects.link(root)
    for o in set(bpy.data.objects) - before:
        if o.parent is None and o is not root:
            o.parent = root
    root.location = mark; root.rotation_euler.z = math.radians(turn_deg)
    bpy.context.view_layer.update()
    return rig, human, root, first, last


def build_set(builder):
    """'sets.salamis_dusk' -> sets.salamis_dusk()."""
    mod, fn = builder.split('.')
    return getattr({'sets': sets}[mod], fn)()


def head_point(rig, bone):
    """frame -> world position of a bone (for cameras that follow a character)."""
    def at(frame):
        bpy.context.scene.frame_set(frame)
        return rig.matrix_world @ rig.pose.bones[bone].head
    return at

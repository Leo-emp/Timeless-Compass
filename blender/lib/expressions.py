# FACIAL EXPRESSIONS for a serious historical drama: resolve, anger, fear, grief, contempt, cunning, awe, pain...
# Two tools together:
#   1. MakeHuman EXPRESSION UNITS (34 sculpted muscle shapes shipped with MPFB, CC0) for mouth, nose, cheeks, neck
#      -> shape keys on the body mesh, e.g. 'mouth-corner-puller' (smile), 'mouth-depression' (frown)
#   2. FACE BONES for brows, jaw (+ eyelids via life.py) because brow hairs, lashes and teeth follow bones
# Bone directions measured in spike/lib_stills/lid2 + mouth sheets:
#   oculi02.* X + = brows pull down and in (frown);  brow raise = oculi02.R Z +, oculi02.L Z -  (mirrored)
#   jaw X + = mouth opens
import math
import os

import bpy
from mathutils import Euler

from bl_ext.blender_org.mpfb.services.targetservice import TargetService

import bl_ext.blender_org.mpfb as _mpfb

# every expression: shape units (0..1), brow (deg: + frown, - raise), jaw (deg open), lids (deg: + wide, - heavy)
EXPRESSIONS = {
    'neutral':  {'units': {}, 'brow': 0, 'raise': 0, 'jaw': 0, 'lids': 0},
    'resolve':  {'units': {'mouth-compression': 0.45, 'neck-platysma': 0.1}, 'brow': 6, 'raise': 0, 'jaw': 0, 'lids': -4},
    'anger':    {'units': {'mouth-compression': 0.6, 'nose-left-elevation': 0.35, 'nose-right-elevation': 0.35,
                           'neck-platysma': 0.35}, 'brow': 14, 'raise': 0, 'jaw': 0, 'lids': -6},
    'rage':     {'units': {'mouth-retraction': 0.5, 'nose-left-elevation': 0.6, 'nose-right-elevation': 0.6,
                           'neck-platysma': 0.7}, 'brow': 17, 'raise': 0, 'jaw': 7, 'lids': 4},
    'fear':     {'units': {'mouth-retraction': 0.45, 'neck-platysma': 0.55}, 'brow': -3, 'raise': 12, 'jaw': 4, 'lids': 12},
    'grief':    {'units': {'mouth-depression': 0.6, 'mouth-compression': 0.2}, 'brow': 2, 'raise': 9, 'jaw': 0, 'lids': -10},
    'contempt': {'units': {'nose-left-elevation': 0.3, 'mouth-depression': 0.2}, 'brow': 4, 'raise': 0, 'jaw': 0, 'lids': -9},
    'cunning':  {'units': {'mouth-corner-puller': 0.35, 'mouth-compression': 0.15}, 'brow': 4, 'raise': 0, 'jaw': 0, 'lids': -5},
    'awe':      {'units': {}, 'brow': -2, 'raise': 6, 'jaw': 2, 'lids': 5},
    'pain':     {'units': {'mouth-retraction': 0.6, 'neck-platysma': 0.6, 'nose-left-elevation': 0.3,
                           'nose-right-elevation': 0.3}, 'brow': 12, 'raise': 6, 'jaw': 3, 'lids': -14},
    'smile':    {'units': {'mouth-corner-puller': 0.6, 'mouth-elevation': 0.15}, 'brow': 0, 'raise': 2, 'jaw': 1, 'lids': -6},
}
UNITS = sorted({u for e in EXPRESSIONS.values() for u in e['units']})


def _units_dir(race='caucasian'):
    # shipped inside the MPFB extension itself (not in the separate CC0 asset pack)
    return os.path.join(os.path.dirname(_mpfb.__file__), 'data', 'targets', 'expression', 'units', race)


def load_units(human, race='caucasian'):
    """Load every unit the library uses as a shape key (value 0) named 'ex-<unit>'."""
    for u in UNITS:
        name = 'ex-' + u
        if human.data.shape_keys and human.data.shape_keys.key_blocks.get(name):
            continue
        TargetService.load_target(human, os.path.join(_units_dir(race), u + '.target.gz'), weight=0.0, name=name)


def _bone(rig, name, frame, deg):
    pb = rig.pose.bones[name]
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = Euler(tuple(math.radians(d) for d in deg))
    pb.keyframe_insert('rotation_euler', frame=frame)


def key_expression(human, rig, name, frame, strength=1.0):
    """Key the whole face into expression `name` at `frame` (strength 0..1 mixes with neutral).
    Returns the eyelid offset (deg) so life.blinks() can keep the same lids between blinks."""
    e = EXPRESSIONS[name]
    kb = human.data.shape_keys.key_blocks
    for u in UNITS:
        k = kb.get('ex-' + u)
        if k is not None:
            k.value = e['units'].get(u, 0.0) * strength
            k.keyframe_insert('value', frame=frame)
    b, r = e['brow'] * strength, e['raise'] * strength
    _bone(rig, 'oculi02.L', frame, (b, 0, -r))
    _bone(rig, 'oculi02.R', frame, (b, 0, r))
    _bone(rig, 'jaw', frame, (e['jaw'] * strength, 0, 0))
    return e['lids'] * strength


def perform(human, rig, beats, ease_frames=8):
    """beats = [(frame, expression, strength), ...] in time order. Each change takes `ease_frames` to arrive, like a
    real face (expressions build over ~1/3 s). Returns [(frame, lid offset)] for the life layer."""
    load_units(human)
    lids = []
    prev = None
    for frame, name, strength in beats:
        if prev is not None:                                   # hold the previous face until this change begins
            key_expression(human, rig, prev[1], max(frame - ease_frames, prev[0]), prev[2])
        lids.append((frame, key_expression(human, rig, name, frame, strength)))
        prev = (frame, name, strength)
    return lids

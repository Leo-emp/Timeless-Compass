# TALKING FACES: mouths that move like real speech.
#   lip_sync(human, rig, cues, start)  - from Rhubarb Lip Sync output (free, open source): a list of
#                                         (seconds, shape) with Rhubarb's 9 standard mouth shapes A-H + X
#   silent_talk(human, rig, start, end) - a character SHOWN talking while the narrator speaks (no audio):
#                                         natural syllable rhythm, phrases and pauses, stressed beats
#   listen(rig, start, end)            - the other person: small nods, attentive stillness
# A mouth is never just a hinge: every shape combines the JAW bone with MakeHuman's lip/cheek shape units
# (the same ones expressions.py uses), and every change is eased (real lips anticipate the next sound).
# Head and brows move with speech emphasis, which is most of what makes talking look alive.
# Order in a scene: expressions.perform() first, then talk (talk overrides the MOUTH units while speaking; the
# expression's brows, lids and smile units stay), then life.bring_to_life() (blinks, eyes, breathing).
import math
import random

from mathutils import Euler

from lib import expressions

FPS = 24

# Rhubarb shapes (Preston Blair set) -> jaw opening (deg) + shape units (0..1)
#   A closed lips (M, B, P)   B slightly open, teeth (K, S, T, EE)   C open (EH, AE)   D wide open (AA)
#   E rounded (AO, ER)        F puckered (UW, OW, W)                 G upper teeth on lip (F, V)
#   H tongue up, open (L)     X rest / silence
SHAPES = {
    'A': {'jaw': 0.0,  'units': {'mouth-compression': 0.55}},
    'B': {'jaw': 3.0,  'units': {'mouth-retraction': 0.25}},
    'C': {'jaw': 7.0,  'units': {'mouth-retraction': 0.15, 'mouth-open': 0.25}},
    'D': {'jaw': 12.0, 'units': {'mouth-open': 0.55}},
    'E': {'jaw': 7.0,  'units': {'mouth-protusion': 0.6, 'mouth-pursing': 0.3, 'mouth-open': 0.15}},
    'F': {'jaw': 3.0,  'units': {'mouth-pursing': 0.9, 'mouth-protusion': 0.6}},
    'G': {'jaw': 2.5,  'units': {'mouth-depression-retraction': 0.35, 'mouth-compression': 0.15}},
    'H': {'jaw': 8.0,  'units': {'mouth-open': 0.3}},
    'X': {'jaw': 0.5,  'units': {}},
}
UNITS = sorted({u for s in SHAPES.values() for u in s['units']})


def _load(human):
    """Make sure every unit the mouth shapes use exists as a shape key ('ex-<unit>', value 0)."""
    import os
    from bl_ext.blender_org.mpfb.services.targetservice import TargetService
    d = expressions._units_dir()
    for u in UNITS:
        if not (human.data.shape_keys and human.data.shape_keys.key_blocks.get('ex-' + u)):
            TargetService.load_target(human, os.path.join(d, u + '.target.gz'), weight=0.0, name='ex-' + u)


def _key_shape(human, rig, shape, frame, strength=1.0, base_jaw=0.0):
    s = SHAPES[shape]
    kb = human.data.shape_keys.key_blocks
    for u in UNITS:
        k = kb.get('ex-' + u)
        if k is not None:
            k.value = s['units'].get(u, 0.0) * strength
            k.keyframe_insert('value', frame=frame)
    pb = rig.pose.bones['jaw']; pb.rotation_mode = 'XYZ'
    pb.rotation_euler = Euler((math.radians(base_jaw + s['jaw'] * strength), 0, 0))
    pb.keyframe_insert('rotation_euler', frame=frame)


def lip_sync(human, rig, cues, start, strength=1.0, lead_frames=1):
    """cues: [(seconds, 'A'..'X'), ...] as Rhubarb writes them (its TSV/JSON). Each shape is keyed `lead_frames`
    early, because lips arrive at a sound slightly before we hear it."""
    _load(human)
    for t, shape in cues:
        _key_shape(human, rig, shape if shape in SHAPES else 'X', start + max(0, round(t * FPS) - lead_frames), strength)


def _nod(rig, frame, deg, bone='neck03'):          # neck02 belongs to the life layer (breathing + drift)
    pb = rig.pose.bones[bone]; pb.rotation_mode = 'XYZ'
    pb.rotation_euler = Euler((math.radians(deg), 0, 0)); pb.keyframe_insert('rotation_euler', frame=frame)


def silent_talk(human, rig, start, end, seed=0, energy=0.7, syllables_per_s=4.5):
    """Speech-like mouth motion without audio: phrases of 4-14 syllables, short breaths between them, one stressed
    syllable per phrase with a head nod + brow lift. `energy` 0.3 (calm) .. 1 (arguing, commanding)."""
    _load(human)
    rnd = random.Random(seed)
    vowels = ['C', 'D', 'E', 'C', 'B', 'H']                   # open-ish shapes carry most syllables
    consonants = ['A', 'B', 'G', 'F', 'B', 'A']
    f = start
    while f < end - 6:
        n = rnd.randint(4, 14)                                 # one phrase
        stress = rnd.randrange(n)
        for i in range(n):
            if f >= end - 4:
                break
            step = max(3, round(FPS / (syllables_per_s * rnd.uniform(0.8, 1.25))))
            loud = energy * (1.25 if i == stress else rnd.uniform(0.7, 1.0))
            _key_shape(human, rig, rnd.choice(consonants), f, min(1.0, loud))
            _key_shape(human, rig, rnd.choice(vowels), f + step // 2, min(1.0, loud))
            if i == stress:                                    # emphasis: small nod + brow lift on the beat
                _nod(rig, f - 2, 0.0); _nod(rig, f + 2, 2.5 * energy); _nod(rig, f + 9, 0.0)
                for side, sgn in (('L', -1), ('R', 1)):
                    pb = rig.pose.bones[f'oculi02.{side}']; pb.rotation_mode = 'XYZ'
                    frown = pb.rotation_euler.x                # keep the expression's frown, only LIFT on the beat
                    pb.rotation_euler = Euler((frown, 0, 0)); pb.keyframe_insert('rotation_euler', frame=f - 3)
                    pb.rotation_euler = Euler((frown, 0, math.radians(sgn * 5 * energy))); pb.keyframe_insert('rotation_euler', frame=f + 2)
                    pb.rotation_euler = Euler((frown, 0, 0)); pb.keyframe_insert('rotation_euler', frame=f + 12)
            f += step
        _key_shape(human, rig, 'X', f, 1.0)                    # breath between phrases
        f += round(FPS * rnd.uniform(0.25, 0.7))


def listen(rig, start, end, seed=0):
    """The listener: still and attentive, an occasional small nod of agreement."""
    rnd = random.Random(seed + 99)
    f = start + round(FPS * rnd.uniform(0.6, 1.8))
    while f < end - 12:
        _nod(rig, f, 0.0); _nod(rig, f + 5, rnd.uniform(2.0, 4.0)); _nod(rig, f + 12, 0.0)
        f += round(FPS * rnd.uniform(1.8, 4.5))

# LIFE LAYER: the small involuntary motions that stop a character looking like a statue.
# Real people are never still: they breathe, their head drifts, their eyes jump between points (saccades) and
# they blink every few seconds; standing people shift their weight. This layer keys ONLY bones that motion capture
# and named poses leave free (spine02, neck02, eyes, eyelids, brows, and the root sway for standing shots), so it
# adds on top of any body motion without fighting it.
#
# Face-bone directions on the MPFB default rig (measured in spike/lib_stills/lid2/sheet.png):
#   orbicularis03.* (upper lid)  X -30 deg = closed          orbicularis04.* (lower lid)  X + = rises (squint)
#   eye.*                        X + = look up, Z + = look to the character's left
#   oculi01.* (brow)             X + = lower (frown), X - = raise
import math
import random

from mathutils import Euler

FPS = 24


def _rad(*deg):
    return Euler(tuple(math.radians(d) for d in deg))


def _key(rig, bone, frame, rot=None, loc=None):
    pb = rig.pose.bones[bone]
    if rot is not None:
        pb.rotation_mode = 'XYZ'; pb.rotation_euler = rot; pb.keyframe_insert('rotation_euler', frame=frame)
    if loc is not None:
        pb.location = loc; pb.keyframe_insert('location', frame=frame)


def breathe_and_drift(rig, start, end, period_s=4.2, deg=1.1, drift_deg=1.3, seed=0):
    """Chest rises and falls (spine02); the neck (neck02) counters the breath so the head stays level, plus a slow
    never-repeating head drift (two slow sines per axis)."""
    rnd = random.Random(seed)
    phase = rnd.random() * 2 * math.pi
    p = [rnd.random() * 6.28 for _ in range(4)]
    for f in range(start, end + 1, 2):
        t = f / FPS
        b = math.sin(2 * math.pi * t / period_s + phase)
        yaw = drift_deg * (0.7 * math.sin(t * 0.37 + p[0]) + 0.3 * math.sin(t * 0.91 + p[1]))
        tilt = drift_deg * 0.6 * (0.6 * math.sin(t * 0.29 + p[2]) + 0.4 * math.sin(t * 0.77 + p[3]))
        _key(rig, 'spine02', f, rot=_rad(-deg * b, 0, 0))
        _key(rig, 'neck02', f, rot=_rad(deg * 0.5 * b + tilt, 0, yaw))


def _driven(rig):
    """Bones already animated by motion capture (they have rotation_quaternion curves)."""
    ad = rig.animation_data
    if not ad or not ad.action:
        return set()
    names = set()
    for fc in _fcurves(ad.action):
        if 'rotation_quaternion' in fc.data_path:
            names.add(fc.data_path.split('"')[1])
    return names


def _fcurves(action):
    if hasattr(action, 'fcurves'):
        return list(action.fcurves)
    out = []
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                out += list(bag.fcurves)
    return out


def blinks(rig, start, end, every_s=(2.0, 5.5), seed=0, lid_open=0.0):
    """Blink: lids close in 2 frames, stay 1, open in 3 (a real blink is ~150 ms). `lid_open` (deg) sets the upper
    lid between blinks: + = wider (fear, awe), - = heavier (grief, contempt, suspicion); expressions.perform gives it."""
    rnd = random.Random(seed + 23)
    rest = _rad(lid_open, 0, 0)
    for s in 'LR':
        _key(rig, f'orbicularis03.{s}', start, rot=rest)
    f = start + int(rnd.uniform(0.3, 2.0) * FPS)
    while f + 6 < end:
        for s in 'LR':
            up, lo = f'orbicularis03.{s}', f'orbicularis04.{s}'
            _key(rig, up, f, rot=rest)
            _key(rig, up, f + 2, rot=_rad(-31, 0, 0)); _key(rig, lo, f + 2, rot=_rad(4, 0, 0))
            _key(rig, up, f + 3, rot=_rad(-31, 0, 0))
            _key(rig, up, f + 6, rot=rest); _key(rig, lo, f + 6, rot=_rad(0, 0, 0))
        f += int(rnd.uniform(*every_s) * FPS)


def saccades(rig, start, end, look=(0.0, 0.0), spread=(6.0, 3.0), hold_s=(0.4, 2.2), seed=0):
    """Eyes fixate a point, then jump (in 2 frames) to a nearby one. `look` = (yaw, pitch) deg of the main gaze
    (yaw + = to the character's left, pitch + = up), e.g. toward the person he is talking to."""
    rnd = random.Random(seed + 41)
    f = start
    while f <= end:
        yaw = look[0] + rnd.gauss(0, spread[0] / 2); pitch = look[1] + rnd.gauss(0, spread[1] / 2)
        for s in 'LR':
            _key(rig, f'eye.{s}', f, rot=_rad(pitch, 0, yaw))
        hold = int(rnd.uniform(*hold_s) * FPS)
        if f + hold <= end:                                    # stay, then the next jump starts 2 frames later
            for s in 'LR':
                _key(rig, f'eye.{s}', f + hold, rot=_rad(pitch, 0, yaw))
        f += hold + 2


def weight_shift(rig, start, end, period_s=7.0, deg=1.2, seed=0):
    """Standing people shift their weight from foot to foot: a slow side-lean of the lower spine (spine05), so the
    feet stay planted. Skipped when motion capture already drives that bone."""
    if 'spine05' in _driven(rig):
        return
    rnd = random.Random(seed + 57); phase = rnd.random() * 6.28
    for f in range(start, end + 1, 3):
        _key(rig, 'spine05', f, rot=_rad(0, deg * math.sin(2 * math.pi * (f / FPS) / period_s + phase), 0))


def bring_to_life(rig, start, end, seed=0, look=(0.0, 0.0), lid_open=0.0, standing=True):
    """Everything above, with one seed per character so a crowd never moves in sync."""
    breathe_and_drift(rig, start, end, seed=seed)
    blinks(rig, start, end, seed=seed, lid_open=lid_open)
    saccades(rig, start, end, look=look, seed=seed)
    if standing:
        weight_shift(rig, start, end, seed=seed)

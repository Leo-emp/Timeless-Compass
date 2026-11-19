# FILM CAMERA VOCABULARY: the camera moves a shot list may ask for (same names as tc/shots.py CAMERA_MOVES).
# Every move is keyframed with eased (slow-in / slow-out) curves, like a real dolly or crane, never linear.
#   subject  = a callable frame -> world point the camera looks at (follows a walking character), or a Vector
#   start    = where the camera stands at the first frame, as an angle around the subject:
#              'front' (facing the person, who faces -Y), 'side', 'three_quarter', 'back', 'low', 'high'
import math
import random

import bpy
from mathutils import Vector

from lib.common import look_at

ANGLES = {                     # (azimuth degrees from the subject's front, camera height above the look point)
    'front': (0, 0.0), 'three_quarter': (35, 0.05), 'side': (90, 0.0), 'back': (180, 0.1),
    'low': (25, -0.7), 'high': (20, 1.6),
}


def _point(subject, frame):
    if callable(subject):
        return subject(frame)
    return Vector(subject)


def _place(cam, target, az_deg, dist, height):
    a = math.radians(az_deg)
    cam.location = target + Vector((math.sin(a) * dist, -math.cos(a) * dist, height))
    look_at(cam, target)


def _ease(cam):
    ad = cam.animation_data
    act = ad.action if ad else None
    curves = []
    if act is not None:
        if hasattr(act, 'fcurves'):
            curves = list(act.fcurves)
        else:                                  # Blender 5 layered actions: curves live in channelbags
            for layer in act.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        curves += list(bag.fcurves)
    for fc in curves:
        for k in fc.keyframe_points:
            k.interpolation = 'BEZIER'; k.easing = 'EASE_IN_OUT'


def apply_move(cam, move, subject, start=1, end=96, frm='three_quarter', dist=4.0, step=4, seed=1, facing=0.0):
    """Keyframe `cam` for `move` between frames start..end. `facing` = the character's turn in degrees (0 = facing -Y),
    so 'three_quarter' etc. are measured from where the character looks. Returns the camera."""
    az, h = ANGLES.get(frm, ANGLES['three_quarter'])
    az += facing
    rnd = random.Random(seed)
    n = max(end - start, 1)
    for f in list(range(start, end + 1, step)) + ([end] if (end - start) % step else []):
        t = (f - start) / n                                    # 0 -> 1 over the shot
        s = t * t * (3 - 2 * t)                                # smoothstep: eased even between keys
        target = _point(subject, f)
        a, d, hh, look = az, dist, h, target.copy()
        if move == 'push_in':
            d = dist * (1.0 - 0.35 * s)
        elif move == 'pull_out':
            d = dist * (0.65 + 0.35 * s)
        elif move in ('pan_left', 'pan_right'):               # camera stays, view turns across the scene
            target0 = _point(subject, start)
            sgn = -1 if move == 'pan_left' else 1
            _place(cam, target0, az, dist, h)
            right = (cam.matrix_world.to_3x3() @ Vector((1, 0, 0)))
            look = target0 + right * sgn * (s - 0.5) * dist * 0.5
            cam.location = cam.location.copy(); look_at(cam, look)
            cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)
            continue
        elif move in ('tilt_up', 'tilt_down'):
            sgn = 1 if move == 'tilt_up' else -1
            look = target + Vector((0, 0, sgn * (s - 0.5) * 1.2))
        elif move == 'orbit':
            a = az + 40 * s
        elif move == 'crane_up':
            hh = h - 0.6 + 1.8 * s
        elif move == 'crane_down':
            hh = h + 1.2 - 1.8 * s
        elif move == 'handheld':                               # small human drift, not shake
            look = target + Vector((rnd.gauss(0, 0.012), rnd.gauss(0, 0.012), rnd.gauss(0, 0.01)))
        # 'static' and 'track' need nothing extra: static keeps the first frame, track follows the subject
        if move == 'static':
            target = _point(subject, start); look = target
        a_rad = math.radians(a)
        cam.location = target + Vector((math.sin(a_rad) * d, -math.cos(a_rad) * d, hh))
        look_at(cam, look)
        cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)
    _ease(cam)
    return cam

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


# ======================================================================================================
# CAMERA GRAMMAR v2 (WS8, Session D): what real camera crews add on top of the basic moves above.
#   lens kit       a real prime set per shot type (focal length, aperture, distance) + 180-degree motion blur
#   rack_focus     pull focus from one person/thing to another on a beat (the eye follows the focus)
#   dolly_zoom     'Vertigo' effect: the camera pulls back while the lens zooms in - the subject stays the same size,
#                  the world behind stretches away (revelation, dread)
#   handheld_v2    layered noise like a real operator: slow breathing drift + body sway + tiny jitter, on top of
#                  any move (F-curve noise modifiers, so it never repeats)
#   impact_shake   a sharp jolt that dies away (a ram hits a hull, a door slams, an explosion)
#   whip_pan       a very fast pan that smears with motion blur: a transition between two shots
# All of these ADD to whatever keys the camera already has, so they combine with apply_move().
# ======================================================================================================

LENS_KIT = {    # shot type -> (focal mm, f-stop, typical camera distance m): a cinema prime set
    'extreme_close': (100, 2.0, 0.6), 'close': (85, 2.0, 1.1), 'medium_close': (65, 2.8, 1.6),
    'medium': (50, 2.8, 2.4), 'cowboy': (40, 4.0, 3.4), 'full': (35, 4.0, 4.6), 'wide': (28, 5.6, 9.0),
    'establishing': (24, 8.0, 40.0), 'aerial': (24, 11.0, 150.0),
}


def apply_lens(cam, shot_type='medium', focus=None, motion_blur=True):
    """Real-camera settings for a shot type: focal length, aperture (depth of field), Super-35 sensor, focus on
    `focus` (object or point), and motion blur with a 180-degree shutter (half the frame time, like film at 24 fps:
    the single cue the eye misses most in CG). Returns the typical camera distance for the shot type."""
    mm, fstop, dist = LENS_KIT.get(shot_type, LENS_KIT['medium'])
    d = cam.data
    d.lens = mm; d.sensor_fit = 'HORIZONTAL'; d.sensor_width = 24.89          # Super 35
    d.dof.use_dof = True; d.dof.aperture_fstop = fstop
    if focus is not None:
        if hasattr(focus, 'matrix_world'):
            d.dof.focus_object = focus
        else:
            d.dof.focus_distance = (Vector(focus) - cam.location).length
    sc = bpy.context.scene
    if motion_blur:
        sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5      # 180 degrees
    return dist


def _ease_curve(fc):
    for k in fc.keyframe_points:
        k.interpolation = 'BEZIER'; k.easing = 'EASE_IN_OUT'


def _curves(id_data, path):
    ad = id_data.animation_data
    act = ad.action if ad else None
    out = []
    if act is None:
        return out
    if hasattr(act, 'fcurves'):
        out = [fc for fc in act.fcurves if fc.data_path == path]
    else:                                                          # Blender 5 layered actions
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out += [fc for fc in bag.fcurves if fc.data_path == path]
    return out


def rack_focus(cam, a, b, frame, pull_frames=18, hold_from=None):
    """Focus on `a` until `frame`, then pull to `b` over `pull_frames` (eased, like a focus puller's hand).
    a/b = objects or world points. Wide apertures (f/2-2.8, apply_lens 'close'/'medium') make it read."""
    d = cam.data
    d.dof.use_dof = True; d.dof.focus_object = None
    def dist(x, f):
        bpy.context.scene.frame_set(f)
        p = x.matrix_world.translation if hasattr(x, 'matrix_world') else Vector(x)
        return (p - cam.matrix_world.translation).length
    f0 = hold_from if hold_from is not None else bpy.context.scene.frame_start
    for f, x in ((f0, a), (frame, a), (frame + pull_frames, b)):
        d.dof.focus_distance = dist(x, f)
        d.dof.keyframe_insert('focus_distance', frame=f)
    for fc in _curves(d, 'dof.focus_distance'):
        _ease_curve(fc)
    return cam


def dolly_zoom(cam, subject, start, end, pull=0.6):
    """The dolly zoom: between start and end the camera travels BACK along its view line by `pull` x its distance
    while the focal length grows in proportion, so the subject keeps its size and the background stretches away.
    Keys location + lens (eased). subject = point or object."""
    sc = bpy.context.scene
    p = subject.matrix_world.translation.copy() if hasattr(subject, 'matrix_world') else Vector(subject)
    sc.frame_set(start)
    c0 = cam.matrix_world.translation.copy(); d0 = (c0 - p).length; f0 = cam.data.lens
    away = (c0 - p).normalized()
    for f, k in ((start, 0.0), (end, 1.0)):
        d = d0 * (1 + pull * k)
        cam.location = p + away * d
        cam.data.lens = f0 * d / d0
        cam.keyframe_insert('location', frame=f); cam.data.keyframe_insert('lens', frame=f)
    for fc in _curves(cam, 'location') + _curves(cam.data, 'lens'):
        _ease_curve(fc)
    return cam


def handheld_v2(cam, strength=1.0, seed=0):
    """A real operator's handheld: three noise layers on the camera's rotation (and a little location) -
    breathing (slow, ~3 s), body sway (~0.8 s), and fine jitter (~0.15 s) - as F-curve NOISE modifiers, so it
    lives on top of any move and never repeats. strength 1 = calm documentary; 2 = tense; 4 = running/battle."""
    if not _curves(cam, 'rotation_euler'):
        cam.keyframe_insert('rotation_euler', frame=bpy.context.scene.frame_start)
    if not _curves(cam, 'location'):
        cam.keyframe_insert('location', frame=bpy.context.scene.frame_start)
    layers = [(72, 0.006), (19, 0.003), (3.5, 0.0009)]              # (period in frames, radians)
    for fc in _curves(cam, 'rotation_euler'):
        for i, (scale, amp) in enumerate(layers):
            m = fc.modifiers.new('NOISE'); m.scale = scale; m.strength = amp * strength * (0.6 if fc.array_index == 1 else 1.0)
            m.phase = seed * 13.7 + fc.array_index * 5.1 + i * 2.3; m.blend_in = 0; m.blend_out = 0
    for fc in _curves(cam, 'location'):
        m = fc.modifiers.new('NOISE'); m.scale = 60; m.strength = 0.01 * strength; m.phase = seed * 7.1 + fc.array_index * 3.3
    return cam


def impact_shake(cam, frame, strength=1.0, decay=14, seed=0):
    """A jolt at `frame` that rings down over `decay` frames (ram strike, slam, blast): rotation keys of a decaying
    oscillation ADDED to the camera's current rotation at those frames."""
    rnd = random.Random(seed)
    sc = bpy.context.scene
    base = {}
    for f in range(frame - 1, frame + decay + 2):
        sc.frame_set(f); base[f] = cam.rotation_euler.copy()
    for i, f in enumerate(range(frame, frame + decay + 1)):
        k = strength * 0.03 * math.exp(-4.0 * i / decay)
        r = base[f]
        cam.rotation_euler = (r.x + k * math.sin(i * 2.1 + rnd.random()), r.y + 0.5 * k * math.sin(i * 1.7 + 1),
                              r.z + k * math.cos(i * 2.6 + rnd.random()))
        cam.keyframe_insert('rotation_euler', frame=f)
    cam.rotation_euler = base[frame + decay + 1]; cam.keyframe_insert('rotation_euler', frame=frame + decay + 1)
    return cam


def whip_pan(cam, frame, frames=6, degrees=75.0, direction=1):
    """A whip pan: the camera snaps round `degrees` in `frames` frames (motion blur smears it into a streak), used
    to cut between two shots: end shot A with a whip out, start shot B with a whip in."""
    sc = bpy.context.scene
    sc.frame_set(frame); r0 = cam.rotation_euler.copy()
    cam.keyframe_insert('rotation_euler', frame=frame)
    cam.rotation_euler = (r0.x, r0.y, r0.z + math.radians(degrees) * direction)
    cam.keyframe_insert('rotation_euler', frame=frame + frames)
    for fc in _curves(cam, 'rotation_euler'):
        for k in fc.keyframe_points:
            if frame <= k.co.x <= frame + frames:
                k.interpolation = 'BEZIER'; k.easing = 'EASE_IN'
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    return cam

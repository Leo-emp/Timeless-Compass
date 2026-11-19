# FIGHTS in Blender: plays a tc.fight choreography on two rigged fighters standing face to face.
#   place_pair(a_root, b_root, centre, heading_deg, weapon)   puts them at sword / spear reach, facing each other
#   duel(a, b, beats, end_frame)    a/b = (rig, root); beats from tc.fight.choreograph()
#     - in any long gap a fighter holds a guard stance (sword_and_shield_idle)
#     - each beat = one Mixamo clip from its start frame; clips sit BLEND frames apart so Blender eases between them
#     - blocked blows throw a short burst of bronze sparks + a clang light at the contact point (the impact frame)
#   impact_frames(rig, first, last)  measures when the weapon hand moves fastest = the real impact frame of a clip
#   slow_motion(scene, speed)        renders REAL in-between frames (tc.slowmo) for the big moments
import math
import os
import random
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from lib import motion  # noqa: E402
from tc import fight as plan, slowmo  # noqa: E402

GAP = {'sword': 1.25, 'spear': 2.1}      # metres between the two men (sword reach vs spear reach)


def place_pair(a_root, b_root, centre, heading_deg, weapon='sword'):
    """A at centre - gap/2 facing B, B at centre + gap/2 facing A, along the heading (0 deg = +X)."""
    g = GAP.get(weapon, 1.3) / 2
    h = math.radians(heading_deg)
    d = Vector((math.cos(h), math.sin(h), 0))
    c = Vector(centre)
    a_root.location = c - d * g
    b_root.location = c + d * g
    # our characters face -Y at 0 deg: turn A toward +d, B toward -d
    a_root.rotation_euler.z = math.atan2(d.x, -d.y)
    b_root.rotation_euler.z = math.atan2(-d.x, d.y)


def _spark_material():
    m = bpy.data.materials.get('spark')
    if m:
        return m
    m = bpy.data.materials.new('spark')
    nt = m.node_tree
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (1.0, 0.6, 0.25, 1)
    em.inputs['Strength'].default_value = 40
    nt.links.new(em.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    return m


def sparks(loc, frame, n=24, seed=0, name='clash'):
    """Bronze on bronze: a 3-frame light pop + hot specks flying out and falling under gravity."""
    rnd = random.Random(seed)
    bpy.ops.object.light_add(type='POINT', location=loc)
    lt = bpy.context.object
    lt.name = name + '_light'
    lt.data.color = (1.0, 0.75, 0.45)
    for f, e in ((frame - 1, 0), (frame, 900), (frame + 2, 200), (frame + 4, 0)):
        lt.data.energy = e
        lt.data.keyframe_insert('energy', frame=f)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.004, location=(0, 0, -500))
    src = bpy.context.object
    src.data.materials.append(_spark_material())
    src.hide_render = True
    for i in range(n):
        s = bpy.data.objects.new(f'{name}_{i}', src.data)
        bpy.context.scene.collection.objects.link(s)
        v = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.uniform(0.2, 1.2))).normalized() * rnd.uniform(1.5, 4.0)
        s.hide_render = True
        s.keyframe_insert('hide_render', frame=frame - 1)
        s.hide_render = False
        s.keyframe_insert('hide_render', frame=frame)
        for k in range(7):
            t = k / 24
            s.location = Vector(loc) + v * t + Vector((0, 0, -4.9 * t * t))
            s.keyframe_insert('location', frame=frame + k)
        s.hide_render = True
        s.keyframe_insert('hide_render', frame=frame + 7)
    return lt


def duel(a, b, beats, end_frame, guard='sword_and_shield_idle', seed=0, clash=True):
    """Play the beats on a = (rig, root) and b = (rig, root). Returns the impact frames."""
    rigs = {'A': a[0], 'B': b[0]}
    for who in 'AB':
        mine = sorted([x for x in beats if x['fighter'] == who], key=lambda x: x['start'])
        t = 1
        for bt in mine:
            if bt['start'] - t > 2 * plan.BLEND:             # hold a guard stance in the gap
                motion.apply_bvh(rigs[who], guard, start=t, hold=0, max_frames=bt['start'] - plan.BLEND - t,
                                 travel=False, skip=(seed + t) % 30)
            motion.apply_bvh(rigs[who], bt['clip'], start=bt['start'], hold=0,
                             max_frames=plan.CLIPS[bt['clip']]['length'], travel=False)
            t = bt['start'] + plan.CLIPS[bt['clip']]['length'] + plan.BLEND
            if bt['kind'] == 'death':
                t = end_frame + 1                            # he stays down
        if t < end_frame:
            motion.apply_bvh(rigs[who], guard, start=t, hold=0, max_frames=end_frame - t, travel=False)
    impacts = []
    for bt in beats:
        if bt['kind'] != 'attack':
            continue
        impacts.append(bt['impact'])
        if clash and bt['answer']['kind'] == 'block':
            mid = (a[1].location + b[1].location) / 2 + Vector((0, 0, 1.35))
            sparks(mid, bt['impact'], seed=seed + bt['impact'], name=f"clash_{bt['impact']}")
    return impacts


def impact_frames(rig, first, last, bone='wrist.R'):
    """The frame where `bone` moves fastest in world space: the true impact frame of an attack clip."""
    sc = bpy.context.scene
    name = bone if bone in rig.pose.bones else 'lowerarm02.R'
    prev, best, best_f = None, -1.0, first
    for f in range(first, last + 1):
        sc.frame_set(f)
        p = rig.matrix_world @ rig.pose.bones[name].tail
        if prev is not None and (p - prev).length > best:
            best, best_f = (p - prev).length, f
        prev = p
    return best_f


def slow_motion(scene, speed):
    """Render this shot at `speed` (0.25 = 4x slower) with real in-between frames + film motion blur."""
    m = slowmo.frame_map(speed)
    scene.render.frame_map_old, scene.render.frame_map_new = m['old'], m['new']
    scene.frame_end = int(round(scene.frame_end * m['new'] / m['old']))
    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = 0.5

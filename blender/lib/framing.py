# DEPTH LAYERS (Session D): what makes a CG frame read like a photographed film frame - the frame is built in
# THREE PLANES, the way cinematographers stage a shot:
#   foreground : something out of focus very close to the lens, partly covering one edge of the frame (a spear
#                shaft, a shield rim, an olive branch, a cloth or sail edge, a column, a rope). It gives scale, depth
#                and the feeling that the camera is IN the world, peeking past things.
#   subject    : sharp, in the focus plane.
#   background : falls off into haze and soft focus (sets.haze + shallow depth of field).
# Everything here is placed RELATIVE TO THE CAMERA: given a camera and the distance to the subject, framers are
# put 0.4-1.5 m from the lens, on the side you choose, sized so they cover 10-30% of the frame edge, and turned to
# face the camera. Called after the camera is set (works with apply_lens: shallow f-stops blur them beautifully).
# Era-correct props only (Greek/Persian 480 BC): reed/ash spear shafts with bronze butts, painted shield rims,
# olive branches, linen/wool cloth edges, Doric column edges, hemp rope, a ship's sail edge.
import math
import random

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

from lib.common import link, principled

KINDS = ('spear', 'shield_rim', 'olive_branch', 'cloth_edge', 'column_edge', 'rope', 'grass', 'sail_edge')


def _m(name, color, rough=0.6, metal=0.0, bump=0.1, bump_scale=120, sss=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = principled(name, color, metal=metal, rough=rough, bump=bump, bump_scale=bump_scale, sss=sss); m.use_fake_user = True
    return m


def _cam_frame(cam):
    """Camera position, forward, right and up unit vectors (world) at the current frame."""
    bpy.context.view_layer.update()                  # a fresh / constrained camera's matrix is stale until updated
    mw = cam.matrix_world
    pos = mw.translation.copy()
    fwd = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
    right = (mw.to_3x3() @ Vector((1, 0, 0))).normalized()
    up = (mw.to_3x3() @ Vector((0, 0, 1))).normalized()
    return pos, fwd, right, up


def _view_half_size(cam, dist):
    """Half width / half height of the camera's view at `dist` metres in front of the lens."""
    sc = bpy.context.scene
    aspect = sc.render.resolution_x / sc.render.resolution_y
    hw = dist * (cam.data.sensor_width / 2) / cam.data.lens
    return hw, hw / aspect


def _tube(name, pts, r, mat, r_end=None):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (*map(float, p), 1.0)
        sp.points[i].radius = 1.0 if r_end is None else 1.0 + (r_end / r - 1.0) * i / max(1, len(pts) - 1)
    cu.bevel_depth = r; cu.bevel_resolution = 3
    tmp = link(bpy.data.objects.new(name + '_c', cu))
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg)); bpy.data.objects.remove(tmp)
    o = link(bpy.data.objects.new(name, me)); o.data.materials.clear(); o.data.materials.append(mat)
    for pg in o.data.polygons:
        pg.use_smooth = True
    return o


def _leaf_cluster(bm, base, d, n, rnd, length=0.07, width=0.016):
    """Olive leaves: narrow lance-shaped leaves along a twig, silver-green (two faces per leaf for a slight fold)."""
    for i in range(n):
        t = i / max(1, n - 1)
        p = base + d * t
        a = rnd.uniform(0, 2 * math.pi)
        side = Vector((math.cos(a), math.sin(a), rnd.uniform(-0.4, 0.4))).normalized()
        tip = p + (side * 0.8 + d.normalized() * 0.6).normalized() * length
        mid = (p + tip) / 2
        perp = side.cross(d).normalized() * width / 2
        v = [bm.verts.new(p), bm.verts.new(mid + perp), bm.verts.new(tip), bm.verts.new(mid - perp + side * 0.003)]
        bm.faces.new(v)


def framer(cam, kind='spear', side='left', depth=0.8, cover=0.18, seed=0, name=None):
    """One out-of-focus FOREGROUND element in front of `cam`.
      kind   : one of KINDS
      side   : 'left' | 'right' | 'bottom' | 'top' | 'bottom_left' | 'bottom_right'  - which frame edge it intrudes from
      depth  : metres from the lens (0.4-1.5; closer = bigger + blurrier)
      cover  : how much of the frame width/height it covers from that edge (0.1-0.35)
    Returns the object (parented to the camera, so it stays in place through camera moves)."""
    rnd = random.Random(seed)
    name = name or f'fg_{kind}_{side}_{seed}'
    pos, fwd, right, up = _cam_frame(cam)
    hw, hh = _view_half_size(cam, depth)
    centre = pos + fwd * depth
    sx = {'left': -1, 'right': 1, 'bottom_left': -1, 'bottom_right': 1}.get(side, 0)
    sy = {'bottom': -1, 'top': 1, 'bottom_left': -1, 'bottom_right': -1}.get(side, 0)
    # anchor: just inside the chosen edge
    anchor = centre + right * sx * hw * (1 - cover) + up * sy * hh * (1 - cover)
    objs = []
    if kind == 'spear':                                               # a near-vertical spear shaft, bronze butt-spike
        tilt = rnd.uniform(-0.12, 0.12)
        a = anchor - up * hh * 1.4 + right * tilt * hh; b = anchor + up * hh * 1.4 - right * tilt * hh
        objs.append(_tube(name, [a, b], max(0.012, hw * cover * 0.22), _m('fg_ash_wood', (0.22, 0.14, 0.07), 0.6, bump=0.3)))
        objs.append(_tube(name + '_butt', [a, a + (b - a).normalized() * hh * 0.25], max(0.014, hw * cover * 0.24),
                          _m('fg_bronze', (0.5, 0.33, 0.14), 0.3, metal=1.0), r_end=max(0.008, hw * cover * 0.15)))
    elif kind == 'shield_rim':                                        # the curve of a painted bronze shield rim
        R = hh * 1.6
        cpos = anchor + right * sx * R * 0.85 + up * sy * R * 0.4
        pts = [cpos + (right * math.cos(t) + up * math.sin(t)) * R for t in np.linspace(0, 2 * math.pi, 64)]
        objs.append(_tube(name, pts, max(0.02, hw * cover * 0.12), _m('fg_shield_bronze', (0.45, 0.3, 0.13), 0.35, metal=1.0, bump=0.2)))
        bpy.ops.mesh.primitive_circle_add(vertices=64, radius=R, fill_type='NGON', location=cpos)
        face = bpy.context.object; face.name = name + '_face'
        face.rotation_euler = fwd.to_track_quat('Z', 'Y').to_euler()
        face.data.materials.append(_m('fg_shield_paint', rnd.choice([(0.25, 0.04, 0.03), (0.04, 0.04, 0.04), (0.5, 0.4, 0.25)]), 0.55))
        objs.append(face)
    elif kind == 'olive_branch':                                      # a sprig of olive hanging into the frame
        bm = bmesh.new()
        base = anchor + right * sx * hw * cover + up * hh * 0.9
        twig_pts = [base + (-right * sx * hw * cover * 1.6 * t) + (-up * hh * 0.5 * t * t) for t in np.linspace(0, 1, 6)]
        for a, b in zip(twig_pts[:-1], twig_pts[1:]):
            _leaf_cluster(bm, a, b - a, 4, rnd, length=hh * 0.18, width=hh * 0.04)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        lv = link(bpy.data.objects.new(name, me)); lv.data.materials.append(_m('fg_olive_leaf', (0.13, 0.17, 0.09), 0.5, sss=0.15))
        objs += [lv, _tube(name + '_twig', twig_pts, hh * 0.012, _m('fg_twig', (0.15, 0.11, 0.07), 0.8))]
    elif kind in ('cloth_edge', 'sail_edge'):                         # a hanging edge of cloth / a sail, with folds
        nx, ny = 10, 16
        W, H = hw * cover * 2.2, hh * 2.6
        bm = bmesh.new()
        vs = [[bm.verts.new(anchor + right * sx * (i / (nx - 1)) * W - right * sx * W * 0.1 + up * (H / 2 - j / (ny - 1) * H)
                            + fwd * 0.02 * math.sin(i * 1.3 + j * 0.2)) for i in range(nx)] for j in range(ny)]
        for j in range(ny - 1):
            for i in range(nx - 1):
                bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        cl = link(bpy.data.objects.new(name, me))
        col = (0.55, 0.5, 0.42) if kind == 'sail_edge' else rnd.choice([(0.3, 0.05, 0.035), (0.07, 0.1, 0.26), (0.45, 0.3, 0.1)])
        cl.data.materials.append(_m(f'fg_{kind}_{col}', col, 0.85, sss=0.1 if kind == 'sail_edge' else 0.0))
        for pg in cl.data.polygons:
            pg.use_smooth = True
        objs.append(cl)
    elif kind == 'column_edge':                                       # the fluted edge of a column or door jamb
        bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=hw * cover * 1.2, depth=hh * 3,
                                            location=anchor + right * sx * hw * cover * 0.9)
        c = bpy.context.object; c.name = name
        c.rotation_euler = up.to_track_quat('Z', 'Y').to_euler()
        c.data.materials.append(_m('fg_marble', (0.62, 0.58, 0.52), 0.45, bump=0.3, bump_scale=40))
        objs.append(c)
    elif kind == 'rope':                                              # a ship's rope sagging across a corner
        a = anchor - right * sx * hw * 0.3 + up * hh * 0.7; b = anchor + right * sx * hw * 0.6 - up * hh * 0.9
        pts = [a + (b - a) * t - up * hh * 0.25 * math.sin(math.pi * t) for t in np.linspace(0, 1, 12)]
        objs.append(_tube(name, pts, max(0.008, hh * 0.025), _m('fg_rope', (0.4, 0.31, 0.19), 0.9, bump=0.8, bump_scale=300)))
    elif kind == 'grass':                                             # dry grass / wheat heads along the bottom edge
        bm = bmesh.new()
        for i in range(70):
            x = rnd.uniform(-1, 1) * hw; base = centre + right * x - up * hh * 1.05
            top = base + up * hh * rnd.uniform(0.25, 0.6) + right * rnd.uniform(-0.05, 0.05) * hw
            perp = right * hh * 0.006
            bm.faces.new([bm.verts.new(base - perp), bm.verts.new(base + perp), bm.verts.new(top)])
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        gr = link(bpy.data.objects.new(name, me)); gr.data.materials.append(_m('fg_dry_grass', (0.5, 0.38, 0.17), 0.7, sss=0.1))
        objs.append(gr)
    else:
        raise KeyError(kind)
    root = link(bpy.data.objects.new(name + '_root', None))
    for o in objs:
        w = o.matrix_world.copy(); o.parent = root; o.matrix_world = w
    # follow the camera through its move: parent to the camera, keeping the current placement
    w = root.matrix_world.copy(); root.parent = cam; root.matrix_parent_inverse = cam.matrix_world.inverted(); root.matrix_world = w
    for o in objs:                                                    # foreground props never cast shadows on the set
        o.visible_shadow = False
    return root


SETTING_FRAMERS = {    # what plausibly stands between a camera and the action, per kind of place
    'battle': ('spear', 'shield_rim', 'spear'), 'ship': ('rope', 'sail_edge', 'rope'),
    'palace': ('column_edge', 'cloth_edge'), 'temple': ('column_edge',), 'countryside': ('olive_branch', 'grass'),
    'market': ('cloth_edge', 'olive_branch'), 'harbour': ('rope', 'sail_edge'), 'house': ('cloth_edge', 'column_edge'),
}


def auto_frame(cam, setting='countryside', seed=0, count=1):
    """Pick and place era-right foreground framers for a kind of place (SETTING_FRAMERS), on alternating sides."""
    rnd = random.Random(seed)
    kinds = SETTING_FRAMERS.get(setting, ('cloth_edge',))
    out = []
    for i in range(count):
        k = kinds[(seed + i) % len(kinds)]
        side = ('grass' == k and 'bottom') or rnd.choice(['left', 'right', 'bottom_left', 'bottom_right'] if k != 'olive_branch' else ['top', 'left', 'right'])
        out.append(framer(cam, k, side=side if k != 'olive_branch' else 'left', depth=rnd.uniform(0.55, 1.1),
                          cover=rnd.uniform(0.12, 0.25), seed=seed + i))
    return out

# PROPS: objects built from code. First: the Athenian TRIREME (c. 480 BC).
# Design source (facts, not copied art): Morrison & Coates' reconstruction and the full-size replica Olympias:
#   ~37 m long, ~5.5 m wide over the outriggers, 170 rowers in three banks per side
#   (thranites 31 through the outrigger, zygites 27, thalamites 27 near the waterline),
#   bronze waterline ram, painted eyes on the bow, stern curling up into the aphlaston, black pitched hull.
import math

import bpy
import numpy as np
from mathutils import Vector, Matrix

from lib.common import link, mesh_obj, principled, aged_bronze


def _hull_mesh(L=34.0, beam=2.3, top=2.1, keel=-0.85, sections=90, around=28):
    """Lofted hull: U-shaped cross-sections along the length (x: 0 = stern .. L = bow)."""
    verts, faces = [], []
    for i in range(sections + 1):
        t = i / sections
        b = beam * (math.sin(math.pi * t) ** 0.55) * (0.88 if t > 0.5 else 1.0) + 0.03     # half-width
        stern_rise = 1.4 * max(0.0, 0.18 - t) / 0.18                                         # keel sweeps up at the stern
        bow_rise = 0.5 * max(0.0, t - 0.9) / 0.1
        k = keel * (math.sin(math.pi * min(1, t * 1.05)) ** 0.35) + stern_rise + bow_rise
        tp = top + 0.9 * max(0.0, 0.12 - t) / 0.12 + 0.35 * max(0.0, t - 0.92) / 0.08         # sheer line rises at both ends
        for j in range(around + 1):
            s = -1 + 2 * j / around
            y = b * s
            z = k + (tp - k) * (abs(s) ** 2.4)
            verts.append((t * L, y, z))
    for i in range(sections):
        for j in range(around):
            a = i * (around + 1) + j
            faces.append((a, a + 1, a + around + 2, a + around + 1))
    return verts, faces


def trireme(loc=(0, 0, 0), heading_deg=0.0, oars_down=True, name='trireme'):
    pitch = principled('pitch_black', (0.012, 0.011, 0.01), rough=0.45, bump=0.25, bump_scale=8)
    ochre = principled('hull_red_band', (0.32, 0.05, 0.03), rough=0.6)
    wood = principled('deck_wood', (0.30, 0.20, 0.12), rough=0.75, bump=0.3, bump_scale=40)
    oarwood = principled('oar_wood', (0.38, 0.27, 0.16), rough=0.7)
    bronze = bpy.data.materials.get('bronze') or aged_bronze('bronze')
    white = principled('eye_white', (0.85, 0.82, 0.74), rough=0.5)
    parts = []
    L = 34.0
    v, f = _hull_mesh(L=L)
    hull = mesh_obj(name + '_hull', v, f, pitch); parts.append(hull)
    hull.modifiers.new('thick', 'SOLIDIFY').thickness = 0.06
    hull.modifiers.new('smooth', 'SUBSURF').levels = 1
    bpy.context.view_layer.objects.active = hull; bpy.ops.object.shade_smooth()
    # red band along the top strakes (wale)
    for sgn in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(L * 0.52, sgn * 2.05, 1.75))
        w = bpy.context.object; w.scale = (L * 0.78, 0.07, 0.22); w.data.materials.append(ochre); parts.append(w)
    # outrigger box for the top bank (parexeiresia)
    for sgn in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(L * 0.52, sgn * 2.45, 2.0))
        o = bpy.context.object; o.scale = (L * 0.62, 0.55, 0.32); o.data.materials.append(pitch); parts.append(o)
        bv = o.modifiers.new('b', 'BEVEL'); bv.width = 0.04
    # deck for the marines and archers
    bpy.ops.mesh.primitive_cube_add(size=1, location=(L * 0.5, 0, 2.38))
    d = bpy.context.object; d.scale = (L * 0.72, 3.4, 0.08); d.data.materials.append(wood); parts.append(d)
    # bronze ram at the waterline: a three-finned blade projecting from the bow
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.45, depth=2.4, location=(L + 0.9, 0, 0.05), rotation=(0, math.radians(90), 0))
    ram = bpy.context.object; ram.scale = (0.6, 1.0, 1.0); ram.data.materials.append(bronze); parts.append(ram)
    for dz in (-0.18, 0.0, 0.18):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(L + 1.4, 0, 0.05 + dz))
        fin = bpy.context.object; fin.scale = (1.0, 0.5, 0.04); fin.data.materials.append(bronze); parts.append(fin)
    # stern ornament (aphlaston): a tapering curve sweeping up and forward
    cu = bpy.data.curves.new('aphlaston', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.16; cu.bevel_resolution = 3
    sp = cu.splines.new('BEZIER'); pts = [(0.6, 0, 2.9), (-1.0, 0, 4.0), (-0.6, 0, 5.4), (0.6, 0, 5.6)]
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    sp.bezier_points[-1].radius = 0.25
    aph = link(bpy.data.objects.new(name + '_aphlaston', cu)); aph.data.materials.append(pitch); parts.append(aph)
    # painted eyes on the bow (to "see" the way)
    for sgn in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.32, depth=0.02, location=(L - 1.7, sgn * 0.95, 1.2), rotation=(math.radians(90), 0, 0))
        e = bpy.context.object; e.scale = (1.5, 1, 1); e.data.materials.append(white); parts.append(e)
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.15, depth=0.03, location=(L - 1.6, sgn * 0.97, 1.2), rotation=(math.radians(90), 0, 0))
        e2 = bpy.context.object; e2.data.materials.append(pitch); parts.append(e2)
    # oars: three banks per side (31 / 27 / 27)
    def oar(x, y_lock, z_lock, sgn, length, dip):
        out = Vector((0, sgn, 0)); down = Vector((0, 0, -1))
        dirv = (out * 1.0 + down * dip).normalized()
        mid = Vector((x, y_lock, z_lock)) + dirv * (length * 0.35)
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.045, depth=length, location=mid)
        o = bpy.context.object
        o.rotation_euler = dirv.to_track_quat('Z', 'Y').to_euler()
        o.data.materials.append(oarwood)
        blade_c = Vector((x, y_lock, z_lock)) + dirv * (length * 0.82)
        bpy.ops.mesh.primitive_cube_add(size=1, location=blade_c)
        bl = bpy.context.object; bl.scale = (0.08, 0.02, 0.55); bl.rotation_euler = o.rotation_euler; bl.data.materials.append(oarwood)
        return [o, bl]
    banks = [(31, 2.7, 2.0, 4.4, 0.55), (27, 2.15, 1.55, 4.0, 0.7), (27, 2.05, 1.05, 3.6, 0.85)]   # count, lock y, lock z, length, dip
    for sgn in (-1, 1):
        for count, ly, lz, ln, dip in banks:
            for k in range(count):
                x = L * 0.22 + (L * 0.6) * k / (count - 1)
                parts += oar(x, sgn * ly, lz, sgn, ln, dip if oars_down else 0.1)
    # mast with the main sail furled on its yard (sails were left ashore or furled for battle)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.14, depth=9.0, location=(L * 0.55, 0, 6.6))
    m = bpy.context.object; m.data.materials.append(wood); parts.append(m)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.22, depth=10.0, location=(L * 0.55, 0, 10.6), rotation=(math.radians(90), 0, 0))
    yd = bpy.context.object; yd.data.materials.append(principled('furled_sail', (0.62, 0.55, 0.45), rough=0.95, bump=0.4, bump_scale=30)); parts.append(yd)
    # put the whole ship where it belongs
    root = bpy.data.objects.new(name, None); link(root)
    for p in parts:
        p.parent = root
    root.location = loc; root.rotation_euler.z = math.radians(heading_deg)
    return root


def terracotta(name='terracotta', seed=0):
    """Fired clay: warm red-orange body with darker fire clouds and paler dust, matte."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = principled(name, (0.48, 0.22, 0.12), rough=0.75, bump=0.15, bump_scale=120)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 3.0; n.inputs['Detail'].default_value = 6
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.20, 0.08, 0.04, 1)     # fire cloud
    ramp.color_ramp.elements[1].color = (0.42, 0.20, 0.11, 1)     # dusty pale clay
    nt.links.new(n.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    return m


def amphora(loc, height=0.72, lean=0.0, seed=0, name='amphora'):
    """Greek transport amphora (c. 500-450 BC): pointed toe, swelling body, sloping shoulder, narrow neck, thick rim,
    two vertical handles from neck to shoulder. Lathe-turned profile (radius at each height, metres)."""
    rng = np.random.default_rng(seed)
    prof = [(0.0, 0.012), (0.04, 0.03), (0.10, 0.07), (0.22, 0.135), (0.36, 0.165), (0.48, 0.16), (0.56, 0.13),
            (0.62, 0.07), (0.66, 0.045), (0.75, 0.042), (0.79, 0.05), (0.81, 0.052), (0.83, 0.043)]
    k = height / 0.83
    seg = 40
    verts, faces = [], []
    for z, r in prof:
        r = r * k * (1 + rng.normal(0, 0.01))
        for i in range(seg):
            a = 2 * math.pi * i / seg
            verts.append((r * math.cos(a), r * math.sin(a), z * k))
    rows = len(prof)
    for j in range(rows - 1):
        for i in range(seg):
            a, b = j * seg + i, j * seg + (i + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    o = mesh_obj(name, verts, faces, terracotta())
    o.modifiers.new('thick', 'SOLIDIFY').thickness = 0.008
    o.modifiers.new('smooth', 'SUBSURF').levels = 2
    for p in o.data.polygons:
        p.use_smooth = True
    # handles: bent tubes from the neck down to the shoulder
    for side in (1, -1):
        pts = [(side * 0.045 * k, 0, 0.76 * k), (side * 0.11 * k, 0, 0.74 * k), (side * 0.12 * k, 0, 0.66 * k), (side * 0.10 * k, 0, 0.58 * k)]
        cu = bpy.data.curves.new(f'{name}_h', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.011 * k; cu.bevel_resolution = 3
        sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
        for bp, p in zip(sp.bezier_points, pts):
            bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
        h = link(bpy.data.objects.new(f'{name}_handle', cu)); cu.materials.append(terracotta())
        h.parent = o
    o.location = loc; o.rotation_euler = (lean, rng.normal(0, 0.03), rng.uniform(0, 6.28))
    return o



def gold(name='royal_gold'):
    m = bpy.data.materials.get(name)
    if m:
        return m
    return principled(name, (0.83, 0.62, 0.26), metal=1.0, rough=0.28, bump=0.08, bump_scale=200)


def throne(loc, heading_deg=0.0, name='xerxes_throne'):
    """Achaemenid throne after the Persepolis Treasury relief (the king enthroned): a high straight back, turned legs
    on cone feet, a cushion, and a separate FOOTSTOOL - gold over wood."""
    root = bpy.data.objects.new(name, None); link(root)
    g = gold(); cushion = principled(f'{name}_cushion', (0.25, 0.03, 0.1), rough=0.8, bump=0.2)
    parts = []

    def box(nm, c, sz, m):
        bpy.ops.mesh.primitive_cube_add(size=1, location=c); o = bpy.context.object; o.name = nm; o.scale = sz
        bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = 0.008; bv.segments = 2
        o.data.materials.append(m); parts.append(o)
    for x in (-0.28, 0.28):
        for y in (-0.25, 0.25):
            bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.035, depth=0.5, location=(x, y, 0.28))
            leg = bpy.context.object; leg.data.materials.append(g); parts.append(leg)
            bpy.ops.mesh.primitive_cone_add(vertices=20, radius1=0.055, radius2=0.03, depth=0.06, location=(x, y, 0.03))
            ft = bpy.context.object; ft.data.materials.append(g); parts.append(ft)
    box(f'{name}_seat', (0, 0, 0.55), (0.66, 0.6, 0.06), g)
    box(f'{name}_cushion', (0, 0, 0.6), (0.6, 0.55, 0.05), cushion)
    box(f'{name}_back', (0, 0.28, 1.05), (0.62, 0.05, 1.0), g)
    for x in (-0.31, 0.31):
        bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.03, depth=1.05, location=(x, 0.28, 1.05))
        p = bpy.context.object; p.data.materials.append(g); parts.append(p)
    box(f'{name}_footstool', (0, -0.48, 0.12), (0.5, 0.3, 0.12), g)
    for p in parts:
        p.parent = root
    root.location = loc; root.rotation_euler.z = math.radians(heading_deg)
    return root


def pavilion(loc, w=6.0, d=5.0, h=3.4, heading_deg=0.0, cloth=(0.35, 0.05, 0.08), trim=(0.8, 0.6, 0.2), name='royal_pavilion'):
    """Royal field canopy: gilded poles, a fabric roof with a deep valance (the king's canopy and parasol appear on
    the Persepolis reliefs)."""
    root = bpy.data.objects.new(name, None); link(root)
    g = gold(f'{name}_gold'); fab = principled(f'{name}_cloth', cloth, rough=0.85, bump=0.15, bump_scale=300)
    tr = principled(f'{name}_trim', trim, rough=0.6)
    parts = []
    for x in (-w / 2, w / 2):
        for y in (-d / 2, d / 2):
            bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.05, depth=h, location=(x, y, h / 2))
            p = bpy.context.object; p.data.materials.append(g); parts.append(p)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, h + 0.25)); roof = bpy.context.object
    roof.scale = (w + 0.3, d + 0.3, 1); roof.data.materials.append(fab); parts.append(roof)
    for (c, sz) in [((0, -d / 2 - 0.15, h - 0.05), (w + 0.3, 0.02, 0.5)), ((0, d / 2 + 0.15, h - 0.05), (w + 0.3, 0.02, 0.5)),
                    ((-w / 2 - 0.15, 0, h - 0.05), (0.02, d + 0.3, 0.5)), ((w / 2 + 0.15, 0, h - 0.05), (0.02, d + 0.3, 0.5))]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=c); v = bpy.context.object; v.scale = sz
        v.data.materials.append(fab); parts.append(v)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(c[0], c[1], c[2] - 0.26)); t = bpy.context.object
        t.scale = (sz[0], sz[1] * 1.5, 0.04); t.data.materials.append(tr); parts.append(t)      # gold fringe band
    for p in parts:
        p.parent = root
    root.location = loc; root.rotation_euler.z = math.radians(heading_deg)
    return root


def tent(loc, r=2.2, h=2.6, heading_deg=0.0, color=(0.55, 0.47, 0.36), name='tent'):
    """Army tent (round, centre pole): rough undyed canvas / leather."""
    root = bpy.data.objects.new(name, None); link(root)
    m = principled(f'{name}_canvas', tuple(color), rough=0.9, bump=0.3, bump_scale=120)
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=r, radius2=0.08, depth=h, location=(0, 0, h / 2))
    c = bpy.context.object; c.data.materials.append(m); c.parent = root
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.04, depth=h + 0.4, location=(0, 0, (h + 0.4) / 2))
    pole = bpy.context.object; pole.data.materials.append(principled(f'{name}_pole', (0.2, 0.13, 0.07), rough=0.8))
    pole.parent = root
    root.location = loc; root.rotation_euler.z = math.radians(heading_deg)
    return root


def banner(loc, color=(0.45, 0.05, 0.05), height=4.0, name='banner'):
    """A standard: pole + square cloth (cloth-simulated flags are a later upgrade)."""
    root = bpy.data.objects.new(name, None); link(root)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.03, depth=height, location=(0, 0, height / 2))
    pole = bpy.context.object; pole.data.materials.append(gold(f'{name}_gold')); pole.parent = root
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0.42, 0, height - 0.45), rotation=(math.radians(90), 0, 0))
    f = bpy.context.object; f.scale = (0.8, 0.8, 1); f.data.materials.append(principled(f'{name}_cloth', tuple(color), rough=0.8))
    f.parent = root
    root.location = loc
    return root


# =====================================================================================================================
# WS7 (Session E, 2026-11-19): FURNITURE, LAMPS, FIRE, CONTAINERS, ROPE, SHIPS v2, HORSE TACK
# Everything below is ADDED; the functions above stay exactly as they were.
# Design sources (facts only, rule r9 - we never copy another production):
#   furniture  - Gisela Richter, "The Furniture of the Greeks, Etruscans and Romans" (1966): klismos, kline, trapeza,
#                kibotos chests, all drawn from Attic vase paintings and grave reliefs of c. 500-450 BC
#   lamps      - Attic black-glazed wheel-made lamps, Athenian Agora excavations (Howland types 21-23, c. 500-450 BC)
#   braziers   - bronze tripod braziers and clay portable braziers (escharai) from Olympia / Agora finds
#   ships      - Herodotus 3.37 (Phoenician "pataikoi" figures on the prow), 3.58 (ships painted red with miltos),
#                Plutarch Themistocles 14 (the Persian-side ships high-decked and heavy); the Assyrian relief of
#                Phoenician galleys from Sidon (Nineveh, c. 700 BC: shields hung along the upper rail);
#                Olympias replica trials (stroke rate ~36-44 per minute, all oars in unison to the aulos piper)
#   horses     - Parthenon frieze and Attic vases: Greek riders mostly bareback or on a cloth; Persian riders on a
#                saddle cloth; NO saddle tree and NO stirrups anywhere before the late Roman / Avar era
# =====================================================================================================================
import random as _random

from lib.common import fabric                          # woven-cloth material (wool/linen) for cushions, sails, tack


# ------------------------------------------------------------------ small building blocks (used by all the props)
def _fcurves(obj_or_id):
    """All F-curves of an object's action. Blender 5 keeps them inside 'channelbags' (layered actions);
    older Blender had action.fcurves. Works with both (same trick as camera_moves.py / life.py)."""
    ad = getattr(obj_or_id, 'animation_data', None)
    act = ad.action if ad else None
    if act is None:
        return []
    if hasattr(act, 'fcurves'):
        try:
            return list(act.fcurves)
        except Exception:
            pass
    out = []
    for layer in getattr(act, 'layers', []):
        for strip in layer.strips:
            for bag in strip.channelbags:
                out += list(bag.fcurves)
    return out


def _loop(obj_or_id):
    """Make every keyframed channel repeat forever (a 'Cycles' modifier on each F-curve): one oar stroke
    becomes an endless loop without thousands of keyframes."""
    for fc in _fcurves(obj_or_id):
        if not any(m.type == 'CYCLES' for m in fc.modifiers):
            fc.modifiers.new('CYCLES')


def _box(name, c, size, mat, bevel=0.006, parent=None):
    """A bevelled box: centre c, full size (x, y, z). Real furniture never has razor-sharp edges, so every box gets
    a tiny bevel that catches a line of light."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=c)
    o = bpy.context.object; o.name = name; o.scale = size
    if bevel:
        b = o.modifiers.new('bevel', 'BEVEL'); b.width = bevel; b.segments = 2
    o.data.materials.append(mat)
    if parent:
        o.parent = parent
    return o


def _cyl(name, c, r, depth, mat, rot=(0, 0, 0), verts=20, parent=None, r2=None):
    """Cylinder (or a cone when r2 is given) centred on c."""
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=c, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=depth, location=c, rotation=rot)
    o = bpy.context.object; o.name = name
    o.data.materials.append(mat)
    if parent:
        o.parent = parent
    return o


def _tube(name, pts, radius, mat, parent=None, poly=False, res=3, taper_end=None):
    """A round bar along a list of points (a curve with a round bevel): chair legs, handles, straps, rope.
    poly=True keeps straight segments between the points (needed for long finely-sampled paths like rope strands)."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = radius; cu.bevel_resolution = res; cu.use_fill_caps = True
    if poly:
        sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
        for p, q in zip(sp.points, pts):
            p.co = (*q, 1)
    else:
        sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
        for bp, p in zip(sp.bezier_points, pts):
            bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
        if taper_end is not None:                     # thicker/thinner at the end (e.g. a flared foot)
            sp.bezier_points[-1].radius = taper_end
    o = link(bpy.data.objects.new(name, cu)); cu.materials.append(mat)
    if parent:
        o.parent = parent
    return o


def _lathe(name, prof, mat, seg=40, parent=None, smooth=2, thick=0.0):
    """Turn a profile [(height, radius), ...] around the vertical axis, like a potter's wheel or a wood lathe."""
    verts, faces = [], []
    for z, r in prof:
        for i in range(seg):
            a = 2 * math.pi * i / seg
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for j in range(len(prof) - 1):
        for i in range(seg):
            a, b = j * seg + i, j * seg + (i + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    o = mesh_obj(name, verts, faces, mat)
    if thick:
        o.modifiers.new('thick', 'SOLIDIFY').thickness = thick
    if smooth:
        o.modifiers.new('smooth', 'SUBSURF').levels = smooth
    for p in o.data.polygons:
        p.use_smooth = True
    if parent:
        o.parent = parent
    return o


def _root(name):
    """Every prop = one EMPTY 'root' with all its parts as children: move/turn the root, the whole prop follows.
    Parts are built around the origin in the prop's own coordinates; _place() then puts the root in the world."""
    r = bpy.data.objects.new(name, None); link(r)
    r['ws7_prop'] = name
    return r


def _place(root, loc, heading_deg):
    root.location = loc; root.rotation_euler.z = math.radians(heading_deg)
    return root


# ------------------------------------------------------------------ materials for the props
def old_wood(name='old_wood', color=(0.26, 0.15, 0.08), grain=1.0):
    """Hand-worked wood: long grain streaks (noise stretched along X) + fine bump, satin from years of handling.
    Greek furniture was mostly olive, maple, boxwood or imported ebony; oiled, sometimes painted."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = principled(name, color, rough=0.62)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (2.0, 40.0 * grain, 40.0 * grain)
    L(tc.outputs['Object'], mp.inputs['Vector'])
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 3.0; n.inputs['Detail'].default_value = 8
    n.inputs['Distortion'].default_value = 1.5
    L(mp.outputs['Vector'], n.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (color[0] * 0.55, color[1] * 0.5, color[2] * 0.45, 1)       # dark late-wood
    ramp.color_ramp.elements[1].color = (min(1, color[0] * 1.35), min(1, color[1] * 1.3), min(1, color[2] * 1.2), 1)
    L(n.outputs['Fac'], ramp.inputs['Fac']); L(ramp.outputs['Color'], b.inputs['Base Color'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.12
    L(n.outputs['Fac'], bp.inputs['Height']); L(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def black_gloss(name='black_gloss'):
    """Attic black 'glaze' (really an iron-rich slip fired black): deep black with a soft sheen."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = principled(name, (0.010, 0.009, 0.008), rough=0.42, bump=0.04, bump_scale=300)   # rough 0.28 read as silver
    m.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = 0.3
    return m


def wicker(name='wicker', color=(0.42, 0.30, 0.16)):
    """Woven reed / willow: a basket weave (brick pattern) as colour + bump."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = principled(name, color, rough=0.85)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    br = nt.nodes.new('ShaderNodeTexBrick'); br.inputs['Scale'].default_value = 60.0
    br.inputs['Mortar Size'].default_value = 0.02; br.offset = 0.5
    br.inputs['Color1'].default_value = (*color, 1)
    br.inputs['Color2'].default_value = (color[0] * 0.75, color[1] * 0.7, color[2] * 0.6, 1)
    br.inputs['Mortar'].default_value = (color[0] * 0.3, color[1] * 0.25, color[2] * 0.2, 1)
    L(br.outputs['Color'], b.inputs['Base Color'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.35
    L(br.outputs['Fac'], bp.inputs['Height']); L(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def rope_fibre(name='rope_fibre', color=(0.45, 0.36, 0.22)):
    """Twisted hemp / esparto / papyrus rope (Herodotus 7.25 + 7.36: Xerxes' bridge cables of white flax and papyrus)."""
    return bpy.data.materials.get(name) or principled(name, color, rough=0.92, bump=0.5, bump_scale=180)


def ember_glow(name='ember_glow', strength=6.0, temp=1250.0):
    """Glowing charcoal: black crust with orange-red light coming through the cracks (noise mask x blackbody)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    b.inputs['Base Color'].default_value = (0.02, 0.018, 0.016, 1); b.inputs['Roughness'].default_value = 0.9
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 45.0; n.inputs['Detail'].default_value = 6
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.45; mr.inputs['From Max'].default_value = 0.7
    L(n.outputs['Fac'], mr.inputs['Value'])
    bb = nt.nodes.new('ShaderNodeBlackbody'); bb.inputs['Temperature'].default_value = temp
    L(bb.outputs['Color'], b.inputs['Emission Color'])
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = strength
    L(mr.outputs['Result'], mul.inputs[0]); L(mul.outputs['Value'], b.inputs['Emission Strength'])
    return m


def flame_glow(name='lamp_flame', strength=30.0, temp=1800.0):
    """A small oil-lamp flame: pure blackbody emission (olive oil burns ~1800 K = warm yellow-orange)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = strength
    bb = nt.nodes.new('ShaderNodeBlackbody'); bb.inputs['Temperature'].default_value = temp
    nt.links.new(bb.outputs['Color'], em.inputs['Color'])
    nt.links.new(em.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    return m


def _flicker_light(loc, power, parent, name, frames=(1, 240), seed=0, radius=0.04, color=(1.0, 0.72, 0.48)):
    # colour: firelight is warm but NOT orange paint - film firelight stays near 2700 K so faces keep their colour (r10)
    """Point light that flickers (random brightness every 2-3 frames), like fx.fire_light but parented to a prop."""
    l = bpy.data.lights.new(name, 'POINT'); l.energy = power; l.color = color; l.shadow_soft_size = radius
    o = link(bpy.data.objects.new(name, l)); o.location = loc; o.parent = parent
    rnd = _random.Random(seed); f = frames[0]
    while f <= frames[1]:
        l.energy = power * rnd.uniform(0.75, 1.25); l.keyframe_insert('energy', frame=f)
        f += rnd.choice((2, 3))
    return o


# ------------------------------------------------------------------ FURNITURE
def klismos(loc=(0, 0, 0), heading_deg=0.0, wood=None, cushion=(0.45, 0.12, 0.08), name='klismos'):
    """KLISMOS chair (c. 500-450 BC; Attic vases of women at home, later the Hegeso stele): four SABRE legs curving
    out (front legs forward, back legs back), the back legs sweep up into the uprights, a broad CONCAVE back board at
    shoulder height, a seat of woven cord, a loose cushion. The sitter faces -Y."""
    root = _root(name)
    w = wood or old_wood('klismos_wood', (0.30, 0.17, 0.08))
    cord = wicker('seat_cord', (0.55, 0.45, 0.30))
    sh, sw, sd = 0.45, 0.48, 0.44             # seat height, width, depth (m) - a little lower than a modern chair
    for sx in (-1, 1):
        # front legs: from the seat corner, bending forward and out (the sabre curve)
        _tube(f'{name}_legF', [(sx * sw / 2, -sd / 2, sh), (sx * sw / 2 * 1.04, -sd / 2 - 0.06, sh * 0.5),
                               (sx * sw / 2 * 1.08, -sd / 2 - 0.17, 0.012)], 0.019, w, root, taper_end=0.7)
        # back legs: down and back to the floor and UP into the backrest uprights - one continuous curve
        _tube(f'{name}_legB', [(sx * sw / 2 * 1.08, sd / 2 + 0.18, 0.012), (sx * sw / 2 * 1.04, sd / 2 + 0.06, sh * 0.5),
                               (sx * sw / 2, sd / 2, sh), (sx * sw / 2 * 0.98, sd / 2 + 0.07, 0.72),
                               (sx * sw / 2 * 0.96, sd / 2 + 0.14, 0.86)], 0.019, w, root)
    # seat frame (four rails) + the woven cord seat between them
    for (c, s) in [((0, -sd / 2, sh), (sw + 0.03, 0.035, 0.035)), ((0, sd / 2, sh), (sw + 0.03, 0.035, 0.035)),
                   ((-sw / 2, 0, sh), (0.035, sd, 0.035)), ((sw / 2, 0, sh), (0.035, sd, 0.035))]:
        _box(f'{name}_rail', c, s, w, parent=root)
    _box(f'{name}_cordseat', (0, 0, sh + 0.004), (sw - 0.01, sd - 0.01, 0.012), cord, bevel=0.002, parent=root)
    # the concave back board: a bent plank (an arc of short boxes) across the tops of the uprights
    n = 9
    for i in range(n):
        t = -1 + 2 * i / (n - 1)
        x = t * sw / 2 * 1.02
        y = sd / 2 + 0.14 + 0.06 * (1 - t * t)       # curves back in the middle: it hugs the sitter's shoulders
        o = _box(f'{name}_back', (x, y, 0.86), (sw / (n - 1) * 1.08, 0.022, 0.13), w, bevel=0.003, parent=root)
        o.rotation_euler.z = -math.atan(0.24 * t / max(sw / 2, 0.01))   # each piece turned along the arc
    if cushion:
        cm = principled(f'{name}_cushion', tuple(cushion), rough=0.9, bump=0.15, bump_scale=400)
        c = _box(f'{name}_cushion', (0, -0.01, sh + 0.035), (sw * 0.92, sd * 0.9, 0.05), cm, bevel=0.02, parent=root)
        c.modifiers['bevel'].segments = 4
    return _place(root, loc, heading_deg)


def kline(loc=(0, 0, 0), heading_deg=0.0, wood=None, mattress=(0.36, 0.10, 0.07), blanket=(0.30, 0.20, 0.10),
          name='kline'):
    """KLINE (dining couch of the symposion, c. 500-450 BC): a high rectangular frame on four flat legs whose tops are
    cut into VOLUTES and a palmette (the 'Ionic' leg of Attic vases), a raised HEAD-END for the elbow, a thick
    mattress, two folded cushions and a blanket hanging over the side. Head end at +X. ~1.95 x 0.85 m, top ~0.68 m."""
    root = _root(name)
    w = wood or old_wood('kline_wood', (0.22, 0.12, 0.06))
    L, W, H = 1.95, 0.85, 0.62
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (L / 2 - 0.05), sy * (W / 2 - 0.04)
            _box(f'{name}_leg', (x, y, (H - 0.06) / 2), (0.075, 0.05, H - 0.06), w, parent=root)   # flat plank leg
            # leg capital: a pair of volute scrolls (tori) + a small palmette block
            for vx in (-1, 1):
                bpy.ops.mesh.primitive_torus_add(major_radius=0.026, minor_radius=0.009, location=(x + vx * 0.03, y, H - 0.09),
                                                 rotation=(math.radians(90), 0, 0))
                t = bpy.context.object; t.name = f'{name}_volute'; t.data.materials.append(w); t.parent = root
            _box(f'{name}_palmette', (x, y, H - 0.15), (0.05, 0.055, 0.06), w, bevel=0.004, parent=root)
    # the frame (the mattress lies on cord lacing stretched inside it)
    for (c, s) in [((0, -W / 2 + 0.04, H - 0.03), (L, 0.05, 0.08)), ((0, W / 2 - 0.04, H - 0.03), (L, 0.05, 0.08)),
                   ((-L / 2 + 0.05, 0, H - 0.03), (0.06, W, 0.08)), ((L / 2 - 0.05, 0, H - 0.03), (0.06, W, 0.08))]:
        _box(f'{name}_frame', c, s, w, parent=root)
    # raised head-end at +X: two curved side bars + a board
    for sy in (-1, 1):
        _tube(f'{name}_headrest', [(L / 2 - 0.06, sy * (W / 2 - 0.05), H + 0.02), (L / 2 - 0.03, sy * (W / 2 - 0.05), H + 0.2),
                                   (L / 2 - 0.12, sy * (W / 2 - 0.05), H + 0.3)], 0.02, w, root)
    _box(f'{name}_headboard', (L / 2 - 0.05, 0, H + 0.14), (0.03, W - 0.08, 0.24), w, parent=root)
    # mattress (wool) + two cushions propped against the head end
    mt = fabric(f'{name}_mattress', tuple(mattress))
    m = _box(f'{name}_mattress', (0, 0, H + 0.07), (L - 0.12, W - 0.06, 0.12), mt, bevel=0.04, parent=root)
    m.modifiers['bevel'].segments = 5
    cu = fabric(f'{name}_cushion', (0.55, 0.38, 0.18))
    for k, dy in enumerate((-0.18, 0.18)):
        c = _box(f'{name}_cushion{k}', (L / 2 - 0.22, dy, H + 0.2), (0.14, 0.34, 0.22), cu, bevel=0.05, parent=root)
        c.modifiers['bevel'].segments = 5; c.rotation_euler.y = math.radians(-18)
    # blanket: lies over the mattress and hangs down the -Y front with soft folds (cloth sim is WS3's job)
    bl = fabric(f'{name}_blanket', tuple(blanket), weave_scale=260.0)   # coarse wool: a fine weave flickers (aliasing)
    verts, faces = [], []
    nx, ny = 24, 14
    for i in range(nx + 1):
        for j in range(ny + 1):
            u, v = i / nx, j / ny
            x = -L / 2 + 0.25 + u * (L * 0.6)
            if v < 0.55:                        # lying on top of the mattress
                y = W / 2 - 0.05 - v / 0.55 * (W * 0.88); z = H + 0.135 + 0.01 * math.sin(u * 12)
            else:                               # hanging down the -Y front edge, with soft vertical folds
                y = -W / 2 + 0.005 - 0.03 * math.sin(u * math.pi * 7) ** 2; z = H + 0.13 - (v - 0.55) / 0.45 * 0.32
            verts.append((x, y, z))
    for i in range(nx):
        for j in range(ny):
            a = i * (ny + 1) + j
            faces.append((a, a + ny + 1, a + ny + 2, a + 1))
    b = mesh_obj(f'{name}_blanket', verts, faces, bl); b.parent = root
    b.modifiers.new('thick', 'SOLIDIFY').thickness = 0.008
    b.modifiers.new('smooth', 'SUBSURF').levels = 1
    for p in b.data.polygons:
        p.use_smooth = True
    return _place(root, loc, heading_deg)


def trapeza(loc=(0, 0, 0), heading_deg=0.0, wood=None, name='trapeza'):
    """TRAPEZA: the small low table pushed under the kline at a symposion (c. 500-450 BC vases): rectangular top on
    THREE legs (two at one end, one at the other), stretchers, slightly wider feet. ~0.72 x 0.42 m, 0.5 m high."""
    root = _root(name)
    w = wood or old_wood('trapeza_wood', (0.28, 0.16, 0.08))
    TL, TW, H = 0.72, 0.42, 0.50
    _box(f'{name}_top', (0, 0, H - 0.015), (TL, TW, 0.03), w, parent=root)
    for (x, y) in [(-TL / 2 + 0.06, -TW / 2 + 0.05), (-TL / 2 + 0.06, TW / 2 - 0.05), (TL / 2 - 0.06, 0)]:
        _box(f'{name}_leg', (x, y, (H - 0.03) / 2), (0.04, 0.035, H - 0.03), w, parent=root)
        _box(f'{name}_foot', (x, y, 0.02), (0.06, 0.05, 0.04), w, parent=root)
    _box(f'{name}_stretcher', (0, 0, 0.12), (TL - 0.1, 0.025, 0.025), w, parent=root)
    _box(f'{name}_stretcher2', (-TL / 2 + 0.06, 0, 0.12), (0.025, TW - 0.08, 0.025), w, parent=root)
    return _place(root, loc, heading_deg)


def footstool(loc=(0, 0, 0), heading_deg=0.0, wood=None, name='thranion'):
    """Low footstool (thranion): to climb onto the high kline, and under a seated woman's feet on grave reliefs."""
    root = _root(name)
    w = wood or old_wood('stool_wood', (0.25, 0.14, 0.07))
    _box(f'{name}_top', (0, 0, 0.14), (0.5, 0.28, 0.03), w, parent=root)
    for sx in (-1, 1):
        _box(f'{name}_side', (sx * 0.22, 0, 0.065), (0.035, 0.26, 0.13), w, parent=root)
    return _place(root, loc, heading_deg)


def chest(loc=(0, 0, 0), heading_deg=0.0, size=(0.9, 0.5, 0.48), paint=(0.42, 0.10, 0.06), lid='flat', name='kibotos'):
    """KIBOTOS / LARNAX wooden chest (Danae's chest on Attic vases, c. 490-470 BC; household chests for clothes and
    documents): panels set between corner posts, the posts run down as short FEET, a flat or low-gabled lid, a
    painted band, two bronze ring handles. size = (length, depth, height of the box)."""
    root = _root(name)
    L, D, H = size
    w = old_wood(f'{name}_wood', (0.24, 0.14, 0.07))
    pm = principled(f'{name}_paint', tuple(paint), rough=0.7, bump=0.1, bump_scale=200)     # mineral paint, chalky
    br = bpy.data.materials.get('bronze') or aged_bronze('bronze')
    foot = 0.07
    for sx in (-1, 1):
        for sy in (-1, 1):
            _box(f'{name}_post', (sx * (L / 2 - 0.025), sy * (D / 2 - 0.025), (H + foot) / 2), (0.05, 0.05, H + foot), w, parent=root)
    # panels sit a little inside the posts: that shadow line is what reads as "panelled"
    _box(f'{name}_front', (0, -D / 2 + 0.03, foot + H / 2), (L - 0.08, 0.02, H - 0.02), w, parent=root)
    _box(f'{name}_backp', (0, D / 2 - 0.03, foot + H / 2), (L - 0.08, 0.02, H - 0.02), w, parent=root)
    _box(f'{name}_end1', (-L / 2 + 0.03, 0, foot + H / 2), (0.02, D - 0.08, H - 0.02), w, parent=root)
    _box(f'{name}_end2', (L / 2 - 0.03, 0, foot + H / 2), (0.02, D - 0.08, H - 0.02), w, parent=root)
    _box(f'{name}_bottom', (0, 0, foot + 0.01), (L - 0.06, D - 0.06, 0.02), w, parent=root)
    for sy in (-1, 1):            # painted band along the top of the front and back
        _box(f'{name}_band', (0, sy * (D / 2 - 0.018), foot + H - 0.06), (L - 0.09, 0.006, 0.07), pm, bevel=0.001, parent=root)
    _box(f'{name}_lid', (0, 0, foot + H + 0.02), (L + 0.03, D + 0.03, 0.04), w, parent=root)
    if lid == 'gable':            # some chests on vases have a low pitched lid
        for sy in (-1, 1):
            o = _box(f'{name}_roof', (0, sy * D * 0.24, foot + H + 0.07), (L + 0.03, D * 0.52, 0.025), w, parent=root)
            o.rotation_euler.x = math.radians(-14 * sy)
    for sx in (-1, 1):            # bronze ring handles on the ends
        bpy.ops.mesh.primitive_torus_add(major_radius=0.035, minor_radius=0.006, location=(sx * (L / 2 + 0.006), 0, foot + H * 0.62),
                                         rotation=(0, math.radians(90), 0))
        t = bpy.context.object; t.name = f'{name}_ring'; t.data.materials.append(br); t.parent = root
    return _place(root, loc, heading_deg)


# ------------------------------------------------------------------ LIGHT + FIRE
def oil_lamp(loc=(0, 0, 0), heading_deg=0.0, lit=True, power=6.0, frames=(1, 240), seed=0, name='lamp'):
    """Attic black-glazed oil lamp (Agora Howland type 21/22, c. 500-450 BC): wheel-made round body ~8 cm across with
    an incurved rim around the filling hole, a long nozzle for the wick, a small loop handle. Burns olive oil:
    one small flame + a flickering light (~6 W in Cycles = the soft glow of one wick)."""
    root = _root(name)
    bg = black_gloss()
    _lathe(f'{name}_body', [(0.0, 0.0), (0.001, 0.025), (0.006, 0.037), (0.018, 0.041), (0.027, 0.036),
                            (0.031, 0.022), (0.029, 0.014), (0.022, 0.012)], bg, seg=32, parent=root, thick=0.002)
    noz = _cyl(f'{name}_nozzle', (0.055, 0, 0.016), 0.011, 0.05, bg, rot=(0, math.radians(90), 0), verts=16, parent=root)
    noz.scale = (0.8, 1.0, 1.0)
    _box(f'{name}_wickhole', (0.079, 0, 0.022), (0.012, 0.012, 0.004), principled('soot', (0.01, 0.01, 0.01), rough=0.95),
         bevel=0.002, parent=root)
    _tube(f'{name}_handle', [(-0.035, -0.012, 0.022), (-0.055, 0, 0.026), (-0.035, 0.012, 0.022)], 0.004, bg, root)
    if lit:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.006, location=(0.079, 0, 0.034))
        f = bpy.context.object; f.name = f'{name}_flame'; f.scale = (0.75, 0.75, 2.4)    # a teardrop flame ~3 cm tall
        f.data.materials.append(flame_glow()); f.parent = root
        f.visible_shadow = False
        _flicker_light((0.079, 0, 0.05), power, root, f'{name}_light', frames, seed, radius=0.01)
    return _place(root, loc, heading_deg)


def lamp_stand(loc=(0, 0, 0), heading_deg=0.0, height=1.25, lit=True, power=8.0, frames=(1, 240), seed=0, name='lampstand'):
    """Bronze lamp stand (kandelabron): a slim shaft on three splayed feet, a dish on top carrying an oil lamp - how
    rich houses and sanctuaries lit a room at head height (finds from Olympia and Etruria, 5th c. BC)."""
    root = _root(name)
    br = bpy.data.materials.get('bronze') or aged_bronze('bronze')
    for k in range(3):
        a = 2 * math.pi * k / 3
        _tube(f'{name}_leg', [(0, 0, 0.16), (0.11 * math.cos(a), 0.11 * math.sin(a), 0.07),
                              (0.17 * math.cos(a), 0.17 * math.sin(a), 0.015)], 0.012, br, root, taper_end=1.4)
    _cyl(f'{name}_shaft', (0, 0, (height + 0.16) / 2), 0.012, height - 0.16, br, verts=12, parent=root, r2=0.009)
    _lathe(f'{name}_dish', [(height, 0.0), (height, 0.06), (height + 0.012, 0.075), (height + 0.016, 0.07)], br,
           seg=32, parent=root, thick=0.003, smooth=1)
    lamp = oil_lamp((0, 0, 0), 0, lit, power, frames, seed, name=f'{name}_lamp')
    lamp.parent = root; lamp.location = (0, 0, height + 0.004)
    return _place(root, loc, heading_deg)


def brazier(loc=(0, 0, 0), heading_deg=0.0, kind='bronze', lit=True, power=180.0, flames=True, frames=(1, 240), seed=0,
            name='brazier'):
    """BRAZIER for warmth, cooking and the altar. kind='bronze': a wide bronze bowl (~0.57 m) on a tripod (~0.8 m
    tall, sanctuary finds); kind='clay': a portable clay brazier (eschara: a pan with two handles on three stubby
    legs, ~0.3 m, Agora finds). Lit: a heap of glowing charcoal, a low flame volume (fx.flames) and a flickering
    orange light that dances on nearby faces and walls (WS8's 'firelit' mood)."""
    root = _root(name)
    rnd = _random.Random(seed)
    if kind == 'bronze':
        mat = bpy.data.materials.get('bronze') or aged_bronze('bronze')
        top = 0.78
        for k in range(3):
            a = 2 * math.pi * k / 3
            _tube(f'{name}_leg', [(0.2 * math.cos(a), 0.2 * math.sin(a), top - 0.08), (0.27 * math.cos(a), 0.27 * math.sin(a), 0.35),
                                  (0.3 * math.cos(a), 0.3 * math.sin(a), 0.02)], 0.016, mat, root, taper_end=1.6)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.265, minor_radius=0.009, location=(0, 0, 0.36))   # ring tying the legs
        t = bpy.context.object; t.name = f'{name}_tie'; t.data.materials.append(mat); t.parent = root
        bowl_prof = [(top - 0.12, 0.0), (top - 0.11, 0.12), (top - 0.07, 0.22), (top, 0.27), (top + 0.01, 0.285)]
        coal_z, coal_r = top - 0.05, 0.2
    else:
        mat = terracotta('brazier_clay')
        top = 0.28
        for k in range(3):
            a = 2 * math.pi * k / 3 + 0.5
            _cyl(f'{name}_leg', (0.13 * math.cos(a), 0.13 * math.sin(a), 0.05), 0.03, 0.1, mat, verts=12, parent=root, r2=0.022)
        bowl_prof = [(0.09, 0.0), (0.1, 0.12), (0.16, 0.18), (top, 0.2), (top + 0.01, 0.215)]
        for sx in (-1, 1):
            _tube(f'{name}_handle', [(sx * 0.2, -0.04, top - 0.03), (sx * 0.26, 0, top - 0.01), (sx * 0.2, 0.04, top - 0.03)], 0.012, mat, root)
        coal_z, coal_r = top - 0.04, 0.16
    _lathe(f'{name}_bowl', bowl_prof, mat, seg=40, parent=root, thick=0.006, smooth=1)
    if lit:
        coal = ember_glow()
        for i in range(55):                                  # a heap of charcoal lumps, higher in the middle
            rr = coal_r * math.sqrt(rnd.random()); a = rnd.uniform(0, 2 * math.pi)
            z = coal_z + 0.05 * (1 - rr / coal_r) + rnd.uniform(-0.01, 0.01)
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=rnd.uniform(0.018, 0.035),
                                                  location=(rr * math.cos(a), rr * math.sin(a), z))
            c = bpy.context.object; c.name = f'{name}_coal'
            c.scale = (rnd.uniform(0.7, 1.3), rnd.uniform(0.7, 1.3), rnd.uniform(0.5, 0.9))
            c.rotation_euler = (rnd.random() * 3, rnd.random() * 3, rnd.random() * 3)
            c.data.materials.append(coal); c.parent = root
        if flames:
            from lib import fx                                # the shared FX library (glowing volume flames)
            fl = fx.flames((0, 0, 0), height=coal_r * 2.2, width=coal_r * 1.3, intensity=45.0, frames=frames,
                           name=f'{name}_flames')
            fl.parent = root; fl.location = (0, 0, coal_z + 0.02 + coal_r * 1.1)
        _flicker_light((0, 0, coal_z + 0.25), power, root, f'{name}_light', frames, seed, radius=0.12,
                       color=(1.0, 0.66, 0.4))
    return _place(root, loc, heading_deg)


# ------------------------------------------------------------------ CONTAINERS + ROPE
def basket(loc=(0, 0, 0), heading_deg=0.0, kind='kalathos', scale=1.0, color=(0.46, 0.33, 0.18), fill=None, name='basket'):
    """Woven baskets of everyday Greek life: kind='kalathos' = the tall wool basket that FLARES toward the rim
    (beside every spinning woman on the vases, ~0.35 m); 'carry' = a round market/fish basket with two loop
    handles; 'flat' = a shallow bread / winnowing tray. fill=(r,g,b) puts a heap (wool, grain, fish) inside."""
    root = _root(name)
    m = wicker(f'{name}_wicker', color)
    k = scale
    if kind == 'kalathos':
        prof = [(0, 0.0), (0, 0.07 * k), (0.12 * k, 0.1 * k), (0.25 * k, 0.14 * k), (0.34 * k, 0.17 * k), (0.35 * k, 0.175 * k)]
        rim_z, rim_r = 0.35 * k, 0.175 * k
    elif kind == 'carry':
        prof = [(0, 0.0), (0, 0.15 * k), (0.06 * k, 0.2 * k), (0.18 * k, 0.22 * k), (0.25 * k, 0.215 * k)]
        rim_z, rim_r = 0.25 * k, 0.215 * k
        for sx in (-1, 1):
            _tube(f'{name}_handle', [(sx * rim_r * 0.85, -0.05 * k, rim_z), (sx * rim_r * 1.05, 0, rim_z + 0.07 * k),
                                     (sx * rim_r * 0.85, 0.05 * k, rim_z)], 0.009 * k, m, root)
    else:
        prof = [(0, 0.0), (0, 0.25 * k), (0.04 * k, 0.3 * k), (0.06 * k, 0.32 * k)]
        rim_z, rim_r = 0.06 * k, 0.32 * k
    _lathe(f'{name}_body', prof, m, seg=36, parent=root, thick=0.008 * k, smooth=1)
    bpy.ops.mesh.primitive_torus_add(major_radius=rim_r, minor_radius=0.01 * k, location=(0, 0, rim_z))
    t = bpy.context.object; t.name = f'{name}_rim'; t.data.materials.append(m); t.parent = root
    if fill:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=rim_r * 0.92, location=(0, 0, rim_z - rim_r * 0.35))
        f = bpy.context.object; f.name = f'{name}_fill'; f.scale = (1, 1, 0.5)
        f.data.materials.append(principled(f'{name}_fill', tuple(fill), rough=0.95, bump=0.5, bump_scale=60)); f.parent = root
    return _place(root, loc, heading_deg)


def rope_coil(loc=(0, 0, 0), heading_deg=0.0, radius=0.32, rope_r=0.014, turns=5, layers=2, strands=True,
              color=(0.45, 0.36, 0.22), name='rope'):
    """A coiled ship's rope lying on deck or quay: a flat spiral, `layers` deep, with a loose end. strands=True
    twists three strands around the path (laid rope: Greek hawsers were 3-strand flax / papyrus / esparto)."""
    root = _root(name)
    m = rope_fibre(f'{name}_fibre', color)
    path = []
    r_in = radius * 0.35
    for layer in range(layers):
        n = int(turns * 40)
        for i in range(n):
            t = i / n
            a = 2 * math.pi * turns * t
            r = r_in + (radius - r_in) * (t if layer % 2 == 0 else 1 - t)   # out on one layer, back in on the next
            path.append(Vector((r * math.cos(a), r * math.sin(a), rope_r * (1 + 1.9 * layer) + 0.002 * math.sin(a * 3))))
    end = path[-1]
    for k in range(1, 12):                                   # the loose end trailing over the deck
        path.append(Vector((end.x + 0.05 * k, end.y - 0.02 * k, rope_r)))
    if not strands:
        _tube(f'{name}_rope', [tuple(p) for p in path], rope_r, m, root, poly=True)
        return _place(root, loc, heading_deg)
    # resample the path finely, then wind three strands around it (one twist every ~8 rope diameters)
    pitch = rope_r * 8
    dist = [0.0]
    for a, b in zip(path, path[1:]):
        dist.append(dist[-1] + (b - a).length)
    fine, j, d, step = [], 0, 0.0, pitch / 10
    while d < dist[-1]:
        while j < len(path) - 2 and dist[j + 1] < d:
            j += 1
        u = (d - dist[j]) / max(dist[j + 1] - dist[j], 1e-9)
        fine.append((path[j].lerp(path[j + 1], u), (path[j + 1] - path[j]).normalized(), d)); d += step
    for s in range(3):
        pts = []
        for p, tng, dd in fine:
            side = tng.cross(Vector((0, 0, 1)))
            side = side.normalized() if side.length > 1e-6 else Vector((1, 0, 0))
            up = side.cross(tng).normalized()
            a = 2 * math.pi * (dd / pitch + s / 3)
            pts.append(tuple(p + (side * math.cos(a) + up * math.sin(a)) * rope_r * 0.55))
        _tube(f'{name}_strand{s}', pts, rope_r * 0.55, m, root, poly=True, res=2)
    return _place(root, loc, heading_deg)


def stone_anchor(loc=(0, 0, 0), heading_deg=0.0, name='anchor_stone'):
    """Stone anchor: a flat stone with a rope hole - the anchor of Archaic/Classical small craft (big ships also
    carried wooden anchors with lead stocks)."""
    root = _root(name)
    bpy.ops.mesh.primitive_cylinder_add(vertices=7, radius=0.2, depth=0.09, location=(0, 0, 0.045))
    s = bpy.context.object; s.name = f'{name}_stone'; s.scale = (1.0, 0.75, 1.0); s.parent = root
    s.data.materials.append(bpy.data.materials.get('anchor_stone') or principled('anchor_stone', (0.30, 0.28, 0.25), rough=0.95, bump=0.6, bump_scale=25))
    b = s.modifiers.new('bevel', 'BEVEL'); b.width = 0.03; b.segments = 3
    bpy.ops.mesh.primitive_torus_add(major_radius=0.04, minor_radius=0.012, location=(0.11, 0, 0.095))   # rope through the hole
    r = bpy.context.object; r.name = f'{name}_rope'; r.data.materials.append(rope_fibre()); r.parent = root
    return _place(root, loc, heading_deg)


# ------------------------------------------------------------------ SHIPS
_TRI_L = 34.0                                                     # hull length used by trireme() above
_TRI_BANKS = [  # name, oars per side, oarlock y, oarlock z, oar length (m) - same layout as trireme() above
    ('thranite', 31, 2.7, 2.0, 4.4), ('zygite', 27, 2.15, 1.55, 4.0), ('thalamite', 27, 2.05, 1.05, 3.6)]


def _children_using(root, prefix):
    """Child objects whose first material name starts with `prefix` (how we find trireme() parts again: the old
    function does not name its oars/fins, but their materials have fixed names)."""
    out = []
    for o in root.children:
        ms = [s.material for s in getattr(o, 'material_slots', []) if s.material]
        if not ms and o.type == 'CURVE':
            ms = [m for m in o.data.materials if m]
        if ms and ms[0].name.startswith(prefix):
            out.append(o)
    return out


def _remove(objs):
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)


def trireme_phoenician(loc=(0, 0, 0), heading_deg=0.0, oars_down=True, hull=(0.15, 0.045, 0.03), shields=True,
                       admiral=False, seed=0, name='phoenician'):
    """PHOENICIAN trireme of Xerxes' fleet (Sidon / Tyre, 480 BC), built on the Athenian hull but changed where the
    sources say the ships differed:
      - HIGHER deck with a bulwark (Plutarch: the Persian-side ships were high-decked and heavy) carrying a row of
        ROUND SHIELDS hung along the rail (Assyrian relief of Sidonian galleys) - and 30 marines, not 14 (Hdt 7.184)
      - dark red-brown hull (red ochre, 'miltos': Herodotus 3.58) instead of the Athenian black pitch
      - a POINTED conical ram (Sidonian coin galleys) instead of the three-finned Athenian ram
      - a small 'pataikos' figure on the prow (Herodotus 3.37: the Phoenicians' dwarf-shaped prow gods)
      - admiral=True adds a stern standard (a commander's ship)."""
    root = trireme((0, 0, 0), 0.0, oars_down, name)
    bpy.context.view_layer.update()               # so every part's .dimensions are real before we test them
    L = _TRI_L
    rnd = _random.Random(seed)
    red = principled(f'{name}_ochre_hull', tuple(hull), rough=0.5, bump=0.25, bump_scale=8)
    hull_obj = next(o for o in root.children if o.name.startswith(name + '_hull'))
    black = hull_obj.data.materials[0]
    for o in root.children:                       # recolour hull, outriggers, stern curl (not the small eye pupils)
        mats = o.data.materials if hasattr(o.data, 'materials') else []
        if len(mats) and mats[0] == black and max(o.dimensions) > 1.0:
            mats[0] = red
    _remove([o for o in _children_using(root, 'bronze') if o.location.x > L - 0.5])   # the Athenian 3-fin ram
    bronze = bpy.data.materials.get('bronze') or aged_bronze('bronze')
    _cyl(f'{name}_ram', (L + 1.0, 0, 0.08), 0.36, 2.4, bronze, rot=(0, math.radians(90), 0), verts=16, parent=root, r2=0.02)
    wood = bpy.data.materials.get('deck_wood') or principled('deck_wood', (0.30, 0.20, 0.12), rough=0.75)
    x0, x1 = L * 0.16, L * 0.86
    _box(f'{name}_highdeck', ((x0 + x1) / 2, 0, 2.95), (x1 - x0, 3.5, 0.08), wood, bevel=0.02, parent=root)
    for sgn in (-1, 1):                           # bulwark screens + the rail the shields hang on
        _box(f'{name}_bulwark', ((x0 + x1) / 2, sgn * 1.76, 2.7), (x1 - x0, 0.06, 0.6), red, bevel=0.01, parent=root)
        _box(f'{name}_rail', ((x0 + x1) / 2, sgn * 1.76, 3.42), (x1 - x0, 0.1, 0.06), wood, bevel=0.01, parent=root)
        for k in range(4):                        # stanchions holding the rail
            x = x0 + (x1 - x0) * (k + 0.5) / 4
            _box(f'{name}_post', (x, sgn * 1.76, 3.18), (0.07, 0.07, 0.48), wood, parent=root)
    if shields:
        cols = [(0.55, 0.38, 0.12), (0.32, 0.06, 0.04), (0.65, 0.58, 0.45), (0.12, 0.10, 0.08)]   # bronze, red, hide, dark
        smats = [principled(f'{name}_shield{i}', c, metal=0.6 if i == 0 else 0.0, rough=0.45 if i == 0 else 0.7) for i, c in enumerate(cols)]
        n = int((x1 - x0) / 0.95)
        for sgn in (-1, 1):
            for k in range(n):
                x = x0 + 0.5 + k * 0.95
                s = _cyl(f'{name}_shield', (x, sgn * 1.83, 3.12), 0.42, 0.05, smats[(k + (sgn > 0)) % 4],
                         rot=(math.radians(90), 0, 0), verts=24, parent=root)
                s.rotation_euler.y = rnd.uniform(-0.2, 0.2)      # hung by hand: not perfectly aligned
                bv = s.modifiers.new('bevel', 'BEVEL'); bv.width = 0.02; bv.segments = 2
    # pataikos: a squat little figure on the prow
    pk = principled(f'{name}_pataikos', (0.42, 0.28, 0.12), metal=0.3, rough=0.6)
    _cyl(f'{name}_pataikos_body', (L - 0.45, 0, 2.72), 0.13, 0.4, pk, verts=12, parent=root, r2=0.09)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.1, location=(L - 0.45, 0, 3.0))
    h = bpy.context.object; h.name = f'{name}_pataikos_head'; h.data.materials.append(pk); h.parent = root
    if admiral:
        st = banner((0, 0, 0), color=(0.5, 0.06, 0.05), height=4.5, name=f'{name}_standard')
        st.parent = root; st.location = (1.2, 0, 3.0)
    return _place(root, loc, heading_deg)


def _small_hull(L=6.6, B=0.95, D=0.42, T=0.55, sections=40, around=20):
    """Lofted hull of a small open boat: U-sections, pointed at both ends, sheer rising toward bow and stern.
    x: 0 = stern .. L = bow; z = 0 is the waterline."""
    verts, faces = [], []
    for i in range(sections + 1):
        t = i / sections
        b = B * (math.sin(math.pi * t) ** 0.6) + 0.015
        k = -D * (math.sin(math.pi * min(1.0, t)) ** 0.35)
        top = T + 0.32 * max(0.0, 0.15 - t) / 0.15 + 0.22 * max(0.0, t - 0.85) / 0.15
        for j in range(around + 1):
            s = -1 + 2 * j / around
            verts.append((t * L, b * s, k + (top - k) * (abs(s) ** 2.2)))
    for i in range(sections):
        for j in range(around):
            a = i * (around + 1) + j
            faces.append((a, a + 1, a + around + 2, a + around + 1))
    return verts, faces


def _small_hull_point(t, z, sgn, L=6.6, B=0.95, D=0.42, T=0.55):
    """Point on the outside of _small_hull() at length fraction t (0 stern .. 1 bow) and height z, side sgn (+1/-1).
    Inverts the section formula z = keel + (top - keel) * |s|^2.2 so fittings sit exactly ON the planks."""
    b = B * (math.sin(math.pi * t) ** 0.6) + 0.015
    k = -D * (math.sin(math.pi * min(1.0, t)) ** 0.35)
    top = T + 0.32 * max(0.0, 0.15 - t) / 0.15 + 0.22 * max(0.0, t - 0.85) / 0.15
    z = min(max(z, k), top)
    s_abs = ((z - k) / max(top - k, 1e-6)) ** (1 / 2.2)
    return Vector((t * L, sgn * b * s_abs, z)), top


def fishing_boat(loc=(0, 0, 0), heading_deg=0.0, L=6.6, oars='rest', mast=True, nets=True, cargo=True,
                 hull_color=(0.05, 0.04, 0.035), band=(0.30, 0.07, 0.04), seed=0, name='fishing_boat'):
    """Small fishing boat of the Aegean (vase paintings of fishermen and Herakles/Odysseus boats; the Kyrenia and
    Ma'agan Mikhael wrecks for construction): ~6-7 m, pitched dark hull with a coloured band, an upturned stem post
    at the bow and a curling stern post, painted eyes, three thwarts, 2 pairs of oars on thole pins, a stubby mast
    with a furled square sail, nets heaped in the stern, baskets of catch, a coiled rope and a stone anchor.
    oars: 'rest' (blades just above the water), 'down' (in the water), 'in' (lying in the boat)."""
    root = _root(name)
    rnd = _random.Random(seed)
    pitch = principled(f'{name}_pitch', tuple(hull_color), rough=0.5, bump=0.3, bump_scale=10)
    bandm = principled(f'{name}_band', tuple(band), rough=0.65)
    wood = old_wood('boat_wood_old', (0.30, 0.20, 0.11))
    v, f = _small_hull(L=L)
    h = mesh_obj(f'{name}_hull', v, f, pitch); h.parent = root
    h.modifiers.new('thick', 'SOLIDIFY').thickness = 0.035
    h.modifiers.new('smooth', 'SUBSURF').levels = 1
    for p in h.data.polygons:
        p.use_smooth = True
    for sgn in (-1, 1):                           # coloured band (wale) just under the sheer line, ON the hull
        pts = []
        for i in range(13):
            t = 0.06 + 0.88 * i / 12
            top = _small_hull_point(t, 10.0, sgn, L)[1]
            p, _ = _small_hull_point(t, top - 0.06, sgn, L)
            pts.append(tuple(p + Vector((0, sgn * 0.02, 0))))
        _tube(f'{name}_wale', pts, 0.028, bandm, root, poly=True)
    _tube(f'{name}_stem', [(L - 0.05, 0, 0.6), (L + 0.12, 0, 0.95), (L + 0.08, 0, 1.25)], 0.05, pitch, root, taper_end=0.6)
    _tube(f'{name}_sternpost', [(0.05, 0, 0.75), (-0.2, 0, 1.15), (-0.05, 0, 1.45), (0.15, 0, 1.5)], 0.05, pitch, root, taper_end=0.5)
    eye_w = principled('eye_white', (0.85, 0.82, 0.74), rough=0.5)
    for sgn in (-1, 1):                           # painted eyes near the bow, lying on the planks
        t = 1 - 0.75 / L
        p, _ = _small_hull_point(t, 0.42, sgn, L)
        p2, _ = _small_hull_point(t + 0.02, 0.42, sgn, L)
        ang = math.atan2(p2.y - p.y, p2.x - p.x)  # the hull side turns in toward the bow: turn the eye with it
        e = _cyl(f'{name}_eye', tuple(p + Vector((0, sgn * 0.006, 0))), 0.075, 0.008, eye_w, rot=(math.radians(90), 0, ang),
                 verts=20, parent=root)
        e.scale = (1.5, 1.0, 1.0)
        _cyl(f'{name}_pupil', tuple(p + Vector((0, sgn * 0.012, 0))), 0.038, 0.008, pitch, rot=(math.radians(90), 0, ang),
             verts=16, parent=root)
    for x in (L * 0.3, L * 0.5, L * 0.7):          # thwarts (benches)
        _box(f'{name}_thwart', (x, 0, 0.36), (0.2, 1.55 * math.sin(math.pi * x / L) ** 0.6, 0.04), wood, parent=root)
    _box(f'{name}_floor', (L / 2, 0, -0.08), (L * 0.7, 0.9, 0.03), wood, parent=root)
    # oars on thole pins at the two middle thwarts
    oarw = old_wood('oar_wood_old', (0.40, 0.29, 0.17))
    for k, x in enumerate((L * 0.4, L * 0.62)):
        for sgn in (-1, 1):
            top = _small_hull_point(x / L, 10.0, sgn, L)[1]
            T, _ = _small_hull_point(x / L, top, sgn, L)          # thole pin on the gunwale
            _cyl(f'{name}_thole', tuple(T + Vector((0, 0, 0.06))), 0.015, 0.12, wood, verts=8, parent=root)
            if oars == 'in':                                         # lying fore-and-aft on the thwarts
                a, b = Vector((x - 1.3, sgn * 0.3, 0.42)), Vector((x + 1.5, sgn * 0.22, 0.42))
                _tube(f'{name}_oar', [tuple(a), tuple(b)], 0.022, oarw, root, poly=True)
                bl = _box(f'{name}_blade', tuple(b - Vector((0.25, 0, 0))), (0.5, 0.12, 0.025), oarw, bevel=0.004, parent=root)
                continue
            drop = 0.9 if oars == 'down' else 0.55                   # how far the tip is below the pin over 2.4 m
            d = Vector((-0.25, sgn * 1.0, -drop / 2.4)).normalized()  # out, a little aft, and down
            pivot = T + Vector((0, 0, 0.08))
            hand, tip = pivot - d * 0.9, pivot + d * 2.4
            _tube(f'{name}_oar', [tuple(hand), tuple(tip)], 0.022, oarw, root, poly=True)
            bl = _box(f'{name}_blade', tuple(pivot + d * 2.12), (0.025, 0.55, 0.13), oarw, bevel=0.004, parent=root)
            bl.rotation_mode = 'QUATERNION'; bl.rotation_quaternion = d.to_track_quat('Y', 'Z')   # box length along the oar
    if mast:
        _cyl(f'{name}_mast', (L * 0.58, 0, 2.0), 0.06, 3.4, wood, verts=12, parent=root, r2=0.045)
        sail = fabric(f'{name}_sail', (0.70, 0.62, 0.48))
        _cyl(f'{name}_yard', (L * 0.58, 0, 3.55), 0.07, 3.0, sail, rot=(math.radians(90), 0, 0), verts=12, parent=root)
        _tube(f'{name}_stay', [(L * 0.58, 0, 3.6), (L + 0.05, 0, 1.2)], 0.006, rope_fibre(), root, poly=True)
        _tube(f'{name}_stay2', [(L * 0.58, 0, 3.6), (0.1, 0, 1.4)], 0.006, rope_fibre(), root, poly=True)
    if nets:                                      # a heaped net in the stern: a lumpy mesh with knotted-net bump
        bpy.ops.mesh.primitive_cube_add(size=1, location=(L * 0.16, 0, 0.12))
        n = bpy.context.object; n.name = f'{name}_nets'; n.scale = (0.9, 0.9, 0.35); n.parent = root
        n.modifiers.new('sub', 'SUBSURF').levels = 3
        tex = bpy.data.textures.new(f'{name}_netlumps', 'CLOUDS'); tex.noise_scale = 0.25
        d = n.modifiers.new('lumps', 'DISPLACE'); d.texture = tex; d.strength = 0.18
        nm = principled(f'{name}_netmat', (0.33, 0.27, 0.18), rough=0.95)
        nt = nm.node_tree; vb = nt.nodes.new('ShaderNodeTexVoronoi'); vb.inputs['Scale'].default_value = 90.0
        vb.feature = 'DISTANCE_TO_EDGE'
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.8
        nt.links.new(vb.outputs['Distance'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], nt.nodes['Principled BSDF'].inputs['Normal'])
        n.data.materials.append(nm)
        for p in n.data.polygons:
            p.use_smooth = True
    if cargo:
        b = basket((0, 0, 0), 0, kind='carry', scale=0.8, fill=(0.55, 0.58, 0.6), name=f'{name}_catch')   # silvery fish
        b.parent = root; b.location = (L * 0.8, -0.2, -0.06)
        rc = rope_coil((0, 0, 0), 0, radius=0.2, rope_r=0.01, turns=4, strands=False, name=f'{name}_rope')
        rc.parent = root; rc.location = (L * 0.86, 0.15, -0.05)
        an = stone_anchor((0, 0, 0), 0, name=f'{name}_anchor')
        an.parent = root; an.location = (L * 0.9, -0.05, -0.05); an.scale = (0.7, 0.7, 0.7)
    return _place(root, loc, heading_deg)


def _oar_mesh(name, inboard, outboard, r=0.045, blade=(0.025, 0.62, 0.15)):
    """One oar as a mesh whose ORIGIN IS THE OARLOCK (thole pin), lying along +Y: the loom runs `inboard` metres
    inside, the shaft `outboard` metres outside and ends in a flat blade. Rotating the object then swings the
    oar about the pin exactly like a real stroke. One mesh is shared by every oar of a bank (memory!)."""
    me = bpy.data.meshes.get(name)
    if me:
        return me
    seg = 8
    verts, faces = [], []
    y_blade = outboard - blade[1]
    rings = [(-inboard, r * 1.1), (0.0, r), (y_blade, r * 0.75)]
    for y, rr in rings:
        for i in range(seg):
            a = 2 * math.pi * i / seg
            verts.append((rr * math.cos(a), y, rr * math.sin(a)))
    for j in range(len(rings) - 1):
        for i in range(seg):
            a, b = j * seg + i, j * seg + (i + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    faces.append(tuple(range(seg))[::-1]); faces.append(tuple(range(2 * seg, 3 * seg)))
    # blade: a thin box (thin along X = the direction it pushes water, tall along Z)
    bx, by, bz = blade[0] / 2, blade[1], blade[2] / 2
    o = len(verts)
    for (x, y, z) in [(-bx, y_blade, -bz), (bx, y_blade, -bz), (bx, y_blade + by, -bz), (-bx, y_blade + by, -bz),
                      (-bx, y_blade, bz), (bx, y_blade, bz), (bx, y_blade + by, bz), (-bx, y_blade + by, bz)]:
        verts.append((x, y, z))
    faces += [(o, o + 1, o + 2, o + 3), (o + 4, o + 7, o + 6, o + 5), (o, o + 4, o + 5, o + 1),
              (o + 1, o + 5, o + 6, o + 2), (o + 2, o + 6, o + 7, o + 3), (o + 3, o + 7, o + 4, o)]
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    return me


def _person_proxy(name, role, parent, loc, face_deg, mats, rnd):
    """A low-poly stand-in person for WIDE shots only (a ship 50+ m away: crew read as small silhouettes).
    Close shots replace these with real cast/crowd characters at the same marker (WS1/WS2)."""
    h = rnd.uniform(1.62, 1.76)
    body = _cyl(f'{name}_body', (0, 0, h * 0.42), 0.17, h * 0.84, mats['cloth' if role not in ('marine', 'archer') else role],
                verts=10, r2=0.12)
    head = None
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.11, location=(0, 0, h - 0.1))
    head = bpy.context.object; head.name = f'{name}_head'; head.data.materials.append(mats['skin' if role != 'marine' else 'bronze'])
    grp = bpy.data.objects.new(name, None); link(grp)
    body.parent = grp; head.parent = grp
    if role == 'marine':                           # crest + shield + spear make a hoplite read even at 100 m
        _box(f'{name}_crest', (0, 0, h + 0.05), (0.04, 0.3, 0.12), mats['crest'], bevel=0.0, parent=grp)
        _cyl(f'{name}_aspis', (0.18, 0, h * 0.5), 0.45, 0.06, mats['bronze'], rot=(0, math.radians(90), 0), verts=16, parent=grp)
        _cyl(f'{name}_dory', (-0.18, 0, h * 0.8), 0.015, 2.4, mats['wood'], verts=6, parent=grp)
    elif role == 'archer':
        _tube(f'{name}_bow', [(0.2, 0, h * 0.4), (0.3, 0, h * 0.6), (0.2, 0, h * 0.85)], 0.012, mats['wood'], grp)
    grp.parent = parent; grp.location = loc; grp.rotation_euler.z = math.radians(face_deg)
    return grp


def _crew_mats():
    # muted, sun-faded dyes: at 50+ m bright red/white proxies read as toy soldiers
    return {'cloth': fabric('crew_cloth', (0.26, 0.22, 0.17)), 'marine': fabric('crew_marine', (0.22, 0.07, 0.05)),
            'archer': fabric('crew_archer', (0.18, 0.15, 0.11)), 'skin': principled('crew_skin', (0.30, 0.18, 0.11), rough=0.6),
            'bronze': bpy.data.materials.get('bronze') or aged_bronze('bronze'),
            'crest': principled('crew_crest', (0.35, 0.05, 0.04), rough=0.8),
            'wood': bpy.data.materials.get('oar_wood_old') or old_wood('oar_wood_old', (0.40, 0.29, 0.17))}


def trireme_v2(loc=(0, 0, 0), heading_deg=0.0, oars='row', stroke_frames=34, frame_start=1, frame_end=240,
               sail=None, crew='markers', marines=14, speed_mps=0.0, bob=True, phoenician=False, seed=0, name='trireme2'):
    """TRIREME v2: the Athenian ship (or phoenician=True) with
      oars:  'row'  - all 170 oars ROWING in unison, a looping stroke (catch -> drive -> finish -> recovery);
                      stroke_frames=34 at 24 fps = ~42 strokes/min, the Olympias' battle rate
             'rest' - oars held level, blades just above the water (drifting, waiting, before a battle)
             None   - no oars (shipped inside: under sail or beached)
      sail:  'set'  - the square linen sail set on its yard, bellied by the wind, brail lines sewn on (cruising;
                      before a battle the main sail was left on shore, Xenophon Hell. 6.2.27)
             'furled' or None - the old furled yard / bare mast (trireme() default)
      crew:  'markers' - named empties where people stand/sit (role in a custom property): helmsman, rowing master,
                         bow officer, piper, marines, archers, deckhands, and every rower seat (for close shots)
             'proxies' - markers + low-poly stand-in people on deck (wide shots only)
      speed_mps: ship moves forward along its heading (battle speed ~4.5 m/s, cruising ~3 m/s); bob: gentle
                 heave / pitch / roll on the swell. Two steering oars at the stern quarters, as on every trireme."""
    root = trireme_phoenician((0, 0, 0), 0.0, True, name=name, seed=seed) if phoenician else trireme((0, 0, 0), 0.0, True, name=name)
    L = _TRI_L
    rnd = _random.Random(seed)
    _remove(_children_using(root, 'oar_wood'))                  # the old static oars of trireme()
    if sail == 'set':
        _remove(_children_using(root, 'furled_sail'))
    oarm = bpy.data.materials.get('oar_wood_v2') or principled('oar_wood_v2', (0.38, 0.27, 0.16), rough=0.7, bump=0.15, bump_scale=60)
    # ---- oars: one pivot per oar, mirrored for the port side by a parent with scale y = -1
    if oars:
        for sgn in (1, -1):
            side = bpy.data.objects.new(f'{name}_oars_{"stbd" if sgn > 0 else "port"}', None); link(side)
            side.parent = root; side.scale = (1, sgn, 1)
            for bank, count, ly, lz, ln in _TRI_BANKS:
                inb, outb = ln * 0.3, ln * 0.85
                me = _oar_mesh(f'oar_{bank}', inb, outb)
                if not me.materials:
                    me.materials.append(oarm)
                reach = outb - 0.31                               # pin -> middle of the blade
                dip_in = math.asin(min(0.95, (lz + 0.22) / reach))   # blade buried ~0.2 m in the water
                dip_air = math.asin(max(0.02, (lz - 0.4) / reach))   # blade ~0.4 m clear of the water
                for k in range(count):
                    x = L * 0.22 + (L * 0.6) * k / (count - 1)
                    o = bpy.data.objects.new(f'{name}_{bank}_{"s" if sgn > 0 else "p"}{k:02d}', me); link(o)
                    o.parent = side; o.location = (x, ly, lz); o.rotation_mode = 'XYZ'
                    if oars == 'rest':
                        o.rotation_euler = (-dip_air * 0.8, 0, math.radians(rnd.uniform(-3, 3)))
                        continue
                    # the stroke: keys at 4 moments; X rotation = blade down/up, Z rotation = sweep fore/aft
                    T = stroke_frames
                    f0 = frame_start + rnd.uniform(-0.8, 0.8)      # rowers are never perfectly together
                    keys = [(0.00, -dip_in, -26), (0.45, -dip_in, 20), (0.56, -dip_air, 22), (0.93, -dip_air, -25),
                            (1.00, -dip_in, -26)]
                    for ph, dx, sz in keys:
                        o.rotation_euler = (dx, 0, math.radians(sz))
                        o.keyframe_insert('rotation_euler', index=0, frame=f0 + ph * T)
                        o.keyframe_insert('rotation_euler', index=2, frame=f0 + ph * T)
                    _loop(o)
    # ---- steering oars (pedalia): two big paddles at the stern quarters, angled down and aft into the water
    for sgn in (-1, 1):
        _tube(f'{name}_rudder_shaft', [(L * 0.1, sgn * 2.05, 2.6), (L * 0.1 - 1.9, sgn * 2.35, -0.4)], 0.07, oarm, root, poly=True)
        bl = _box(f'{name}_rudder_blade', (L * 0.1 - 2.05, sgn * 2.37, -0.65), (0.6, 0.05, 1.1), oarm, bevel=0.01, parent=root)
        bl.rotation_euler.y = math.radians(-33)
    # ---- sail
    if sail == 'set':
        mast_x = L * 0.55
        linen = principled(f'{name}_sail_linen', (0.72, 0.64, 0.50), rough=0.9, bump=0.2, bump_scale=500)
        nt = linen.node_tree; b = nt.nodes['Principled BSDF']
        b.inputs['Subsurface Weight'].default_value = 0.0
        # brails + seams: vertical lines every ~0.75 m and horizontal strips (the grid of a sewn Greek sail)
        tcn = nt.nodes.new('ShaderNodeTexCoord')
        for axis, scale in ((0, 1 / 0.75), (2, 1 / 0.9)):
            sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tcn.outputs['Object'], sep.inputs['Vector'])
            mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = scale
            nt.links.new(sep.outputs[axis], mul.inputs[0])
            fr = nt.nodes.new('ShaderNodeMath'); fr.operation = 'PINGPONG'; fr.inputs[1].default_value = 0.5
            nt.links.new(mul.outputs[0], fr.inputs[0])
            lt = nt.nodes.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = 0.035
            nt.links.new(fr.outputs[0], lt.inputs[0])
            mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
            src = b.inputs['Base Color'].links[0].from_socket if b.inputs['Base Color'].is_linked else None
            if src:
                nt.links.new(src, mix.inputs['A'])
            else:
                mix.inputs['A'].default_value = b.inputs['Base Color'].default_value
            mix.inputs['B'].default_value = (0.32, 0.25, 0.16, 1)     # darker rope / seam
            nt.links.new(lt.outputs[0], mix.inputs['Factor']); nt.links.new(mix.outputs['Result'], b.inputs['Base Color'])
        W, Ht, nu, nv = 9.6, 6.8, 26, 20
        verts, faces = [], []
        for i in range(nu + 1):
            for j in range(nv + 1):
                u, v = i / nu, j / nv
                y = (u - 0.5) * W
                z = 10.45 - v * Ht
                belly = 0.95 * math.sin(math.pi * u) * (math.sin(math.pi * (0.15 + 0.85 * v)) ** 0.8)   # wind from astern
                verts.append((mast_x + 0.3 + belly, y, z))
        for i in range(nu):
            for j in range(nv):
                a = i * (nv + 1) + j
                faces.append((a, a + 1, a + nv + 2, a + nv + 1))
        s = mesh_obj(f'{name}_sail', verts, faces, linen); s.parent = root
        s.modifiers.new('thick', 'SOLIDIFY').thickness = 0.01
        s.modifiers.new('smooth', 'SUBSURF').levels = 1
        for p in s.data.polygons:
            p.use_smooth = True
        wood = bpy.data.materials.get('deck_wood') or principled('deck_wood', (0.30, 0.20, 0.12), rough=0.75)
        _cyl(f'{name}_yard', (mast_x + 0.25, 0, 10.55), 0.13, W + 0.6, wood, rot=(math.radians(90), 0, 0), verts=12, parent=root)
        rf = rope_fibre()
        for sgn in (-1, 1):                       # sheets down to the stern quarters, braces to the yard arms
            _tube(f'{name}_sheet', [(mast_x + 0.3, sgn * W / 2, 10.45 - Ht), (L * 0.2, sgn * 1.9, 2.5)], 0.012, rf, root, poly=True)
        _tube(f'{name}_forestay', [(mast_x, 0, 11.0), (L - 0.4, 0, 2.6)], 0.014, rf, root, poly=True)
        _tube(f'{name}_backstay', [(mast_x, 0, 11.0), (L * 0.08, 0, 3.0)], 0.014, rf, root, poly=True)
    # ---- crew markers (+ optional stand-in people)
    if crew:
        deck_z = 2.99 if phoenician else 2.42
        spots = [('helmsman', (L * 0.13, 0, deck_z), 0), ('rowing_master', (L * 0.5, 0, deck_z), 180),
                 ('bow_officer', (L * 0.86, 0, deck_z), 0), ('piper', (L * 0.47, 0.6, deck_z), 180)]
        n_mar = 30 if phoenician and marines == 14 else marines          # Hdt 7.184: 30 marines on Xerxes' ships
        n_arch = 4
        for i in range(n_mar):
            x = L * 0.62 + (i // 2) * 0.9 if i < 20 else L * 0.25 + ((i - 20) // 2) * 0.9
            spots.append(('marine', (x, (-0.7 if i % 2 else 0.7), deck_z), 0))
        for i in range(n_arch):
            spots.append(('archer', (L * 0.3 + i * 0.8, (1.0 if i % 2 else -1.0), deck_z), 0))
        for i in range(6):
            spots.append(('deckhand', (L * 0.2 + i * 3.5, (1.3 if i % 2 else -1.3), deck_z), 90))
        mats = _crew_mats() if crew == 'proxies' else None
        for k, (role, p, face) in enumerate(spots):
            mk = bpy.data.objects.new(f'{name}_crew_{role}_{k:02d}', None); link(mk)
            mk.parent = root; mk.location = p; mk.rotation_euler.z = math.radians(face)
            mk['role'] = role; mk.empty_display_size = 0.3
            if crew == 'proxies':
                _person_proxy(f'{name}_p{k:02d}', role, root, p, face + rnd.uniform(-25, 25), mats, rnd)
        for bank, count, ly, lz, ln in _TRI_BANKS:          # every rower's seat (inside the hull, for close shots)
            for sgn in (-1, 1):
                for k in range(count):
                    x = L * 0.22 + (L * 0.6) * k / (count - 1)
                    mk = bpy.data.objects.new(f'{name}_seat_{bank}_{"s" if sgn > 0 else "p"}{k:02d}', None); link(mk)
                    mk.parent = root; mk.location = (x - 0.4, sgn * (ly - 1.0), lz - 0.25)
                    mk.rotation_euler.z = math.radians(180)          # rowers face the stern
                    mk['role'] = f'rower_{bank}'; mk.empty_display_size = 0.15
    # ---- movement: forward along the heading + swell
    _place(root, loc, heading_deg)
    if speed_mps or bob:
        fps = bpy.context.scene.render.fps or 24
        h = math.radians(heading_deg)
        if speed_mps:
            dist = speed_mps * (frame_end - frame_start) / fps
            for f, d in ((frame_start, 0.0), (frame_end, dist)):
                root.location = (loc[0] + d * math.cos(h), loc[1] + d * math.sin(h), loc[2])
                root.keyframe_insert('location', index=0, frame=f); root.keyframe_insert('location', index=1, frame=f)
            for fc in _fcurves(root):
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
                fc.extrapolation = 'LINEAR'
        if bob:                                   # heave 6 cm / pitch 0.5 deg / roll 0.7 deg over a ~4 s swell
            P = 4.0 * fps
            for i in range(5):
                f = frame_start + i * P / 4
                root.location.z = loc[2] + 0.06 * math.sin(i * math.pi / 2)
                root.rotation_euler = (math.radians(0.7) * math.sin(i * math.pi / 2 + 1.0),
                                       math.radians(0.5) * math.cos(i * math.pi / 2), h)
                root.keyframe_insert('location', index=2, frame=f)
                root.keyframe_insert('rotation_euler', index=0, frame=f); root.keyframe_insert('rotation_euler', index=1, frame=f)
            for fc in _fcurves(root):
                if (fc.data_path == 'location' and fc.array_index == 2) or (fc.data_path == 'rotation_euler' and fc.array_index in (0, 1)):
                    if not any(m.type == 'CYCLES' for m in fc.modifiers):
                        fc.modifiers.new('CYCLES')
    return root


# ------------------------------------------------------------------ HORSE TACK (480 BC: cloth + bridle, NO saddle, NO stirrups)
# How it stays on a moving horse: every strap and the cloth is built in the horse's REST pose by shooting rays at
# its body (so it lies on the skin), then each vertex copies the skin weights of the nearest horse vertex and gets
# the same Armature modifier as the horse. When the horse trots, the bones bend the tack exactly like the skin.
def _bone_pos(rig, prefix, tail=False):
    b = next(b for b in rig.data.bones if b.name.startswith(prefix))
    return rig.matrix_world @ (b.tail_local if tail else b.head_local)


def _rest_body(rig):
    """The horse's body mesh in REST pose, in world space: (object, list of world vertices, BVH tree for rays)."""
    from mathutils.bvhtree import BVHTree
    body = max((o for o in rig.children if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg); me = ev.to_mesh()
    verts = [body.matrix_world @ v.co for v in me.vertices]
    tree = BVHTree.FromPolygons(verts, [tuple(p.vertices) for p in me.polygons])
    ev.to_mesh_clear()
    return body, verts, tree


def _surface(tree, centre, direction, offset, reach=0.9):
    """Shoot a ray from INSIDE the body (centre) outward along `direction`; the first hit is the nearest skin. Return
    that point pushed out by `offset` along the skin normal (so the strap sits ON the hair, not inside it).
    (Rays shot from far OUTSIDE back toward the centre were wrong: below the poll they hit the neck/chest first and
    made a bridle strap jump a metre down to the chest.)"""
    hit, nrm, _, _ = tree.ray_cast(centre, direction, reach)
    if hit is None:
        return None
    if nrm.dot(direction) < 0:
        nrm = -nrm
    return hit + nrm * offset


def _ring(tree, centre, axis, offset, step_deg=10, start_deg=0, end_deg=360, up=Vector((0, 0, 1))):
    """Points around the body/head in the plane at `centre` perpendicular to `axis` (a strap that goes all the way
    round, like a girth or a noseband). Angles are measured from 'up' (0 = top)."""
    axis = axis.normalized()
    U = (up - axis * up.dot(axis)).normalized()                # 'up' inside the plane
    V = axis.cross(U)
    pts = []
    a = start_deg
    while a <= end_deg + 1e-6:
        r = math.radians(a)
        p = _surface(tree, centre, U * math.cos(r) + V * math.sin(r), offset)
        if p is not None:
            pts.append(p)
        a += step_deg
    return pts


def _band(name, pts, width_dir, width, thick, mat, closed=False):
    """A flat leather strap through `pts`: a strip `width` wide along `width_dir` (or across the path when None)."""
    verts, faces = [], []
    n = len(pts)
    for i, p in enumerate(pts):
        if width_dir is not None:
            w = width_dir.normalized()
        else:
            t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
            w = t.cross(Vector((0, 0, 1))).normalized() if abs(t.z) < 0.95 else t.cross(Vector((1, 0, 0))).normalized()
        verts += [tuple(p - w * width / 2), tuple(p + w * width / 2)]
    for i in range(n - 1 + (1 if closed else 0)):
        a, b = 2 * i, 2 * ((i + 1) % n)
        faces.append((a, b, b + 1, a + 1))
    o = mesh_obj(name, verts, faces, mat)
    o.modifiers.new('thick', 'SOLIDIFY').thickness = thick
    return o


# which horse bones each piece of tack may follow (a strap must NOT copy a LEG bone's weight just because it passes
# near the elbow - in the first test the girth and reins were dragged to the ground by the swinging forelegs)
TACK_BONES = {
    'body': ('DEF-spine', 'DEF-pelvis', 'DEF-belly'),          # not DEF-girth: those helper bones follow the elbows
    'reins': ('DEF-head', 'DEF-neck', 'DEF-spine_03'),
    'head': ('DEF-head', 'DEF-jaw', 'DEF-muzzle', 'DEF-cheek', 'DEF-chin'),
}


def _bind(objs, rig, body, body_verts, allow):
    """Make tack deform with the horse: copy each vertex's skin weights from the nearest horse vertex that is driven
    by the ALLOWED bones (prefixes), keep only those bones' weights (re-normalised), then add the horse's Armature
    modifier and parent to the rig (world position kept)."""
    from mathutils.kdtree import KDTree
    names = {g.index: g.name for g in body.vertex_groups}
    ok = {i for i, n in names.items() if n.startswith(allow)}
    bverts = body.data.vertices
    cand = [i for i, v in enumerate(bverts) if sum(g.weight for g in v.groups if g.group in ok) > 0.5]
    kd = KDTree(len(cand))
    for k, i in enumerate(cand):
        kd.insert(body_verts[i], i)
    kd.balance()
    for o in objs:
        if o.type == 'CURVE':                                  # curves (round tubes) become meshes first
            bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.convert(target='MESH')
            o = bpy.context.view_layer.objects.active
        mw = o.matrix_world.copy()
        groups = {}                                            # body group index -> this object's vertex group
        for v in o.data.vertices:
            _, idx, _ = kd.find(mw @ v.co)
            ws = [(g.group, g.weight) for g in bverts[idx].groups if g.group in ok and g.weight > 0.01]
            tot = sum(w for _, w in ws) or 1.0
            for gi, w in ws:
                vg = groups.get(gi) or o.vertex_groups.new(name=names[gi])
                groups[gi] = vg
                vg.add([v.index], w / tot, 'REPLACE')
        o.parent = rig; o.matrix_parent_inverse = rig.matrix_world.inverted()   # stays exactly where it was built
        am = o.modifiers.new('horse_rig', 'ARMATURE'); am.object = rig
        bpy.ops.object.select_all(action='DESELECT')


def _cloth_material(name, style):
    """Saddle cloth wool. 'greek': plain undyed or madder-red wool with a dark woven border (Attic vases);
    'persian': dark blue wool with a checked red/ochre border and a deep fringe (Achaemenid cavalry, Persepolis
    tribute reliefs and later the Alexander sarcophagus)."""
    if style == 'persian':
        base, border, edge = (0.05, 0.07, 0.20), (0.45, 0.07, 0.04), (0.65, 0.45, 0.12)
    else:
        base, border, edge = (0.40, 0.10, 0.06), (0.08, 0.06, 0.05), (0.62, 0.55, 0.42)
    m = fabric(name, base)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    uv = nt.nodes.new('ShaderNodeUVMap')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(uv.outputs['UV'], sep.inputs['Vector'])
    # distance to the nearest edge of the cloth (0 at the edge, 0.5 in the middle)
    def edge_dist(sock):
        inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
        L(sock, inv.inputs[1])
        mn = nt.nodes.new('ShaderNodeMath'); mn.operation = 'MINIMUM'; L(sock, mn.inputs[0]); L(inv.outputs[0], mn.inputs[1])
        return mn.outputs[0]
    mn = nt.nodes.new('ShaderNodeMath'); mn.operation = 'MINIMUM'
    L(edge_dist(sep.outputs['X']), mn.inputs[0]); L(edge_dist(sep.outputs['Y']), mn.inputs[1])
    band = nt.nodes.new('ShaderNodeMath'); band.operation = 'LESS_THAN'; band.inputs[1].default_value = 0.09
    L(mn.outputs[0], band.inputs[0])
    line = nt.nodes.new('ShaderNodeMath'); line.operation = 'LESS_THAN'; line.inputs[1].default_value = 0.02
    L(mn.outputs[0], line.inputs[0])
    col_b = nt.nodes.new('ShaderNodeRGB'); col_b.outputs[0].default_value = (*border, 1)
    if style == 'persian':                                    # checked border (woven pattern)
        ck = nt.nodes.new('ShaderNodeTexChecker'); ck.inputs['Scale'].default_value = 40.0
        ck.inputs['Color1'].default_value = (*border, 1); ck.inputs['Color2'].default_value = (*edge, 1)
        L(uv.outputs['UV'], ck.inputs['Vector']); bsock = ck.outputs['Color']
    else:
        bsock = col_b.outputs[0]
    m1 = nt.nodes.new('ShaderNodeMix'); m1.data_type = 'RGBA'
    src = b.inputs['Base Color'].default_value
    m1.inputs['A'].default_value = src; L(bsock, m1.inputs['B']); L(band.outputs[0], m1.inputs['Factor'])
    m2 = nt.nodes.new('ShaderNodeMix'); m2.data_type = 'RGBA'
    L(m1.outputs['Result'], m2.inputs['A']); m2.inputs['B'].default_value = (*edge, 1); L(line.outputs[0], m2.inputs['Factor'])
    L(m2.outputs['Result'], b.inputs['Base Color'])
    return m


def horse_tack(horse_root, cloth='greek', bridle=True, reins=True, girth=True, name=None):
    """Dress a rigged horse scan (scans_glb.load_glb('horse_akhalteke')) for 480 BC:
      - SADDLE CLOTH ('greek' plain wool with a dark border, 'persian' blue checked + fringe, None = bareback, which
        is how most Greek riders on the Parthenon frieze ride) held by a GIRTH strap
      - BRIDLE: crownpiece behind the ears, browband, cheekpieces, noseband; a bronze snaffle BIT with rings at the
        mouth corners (Greek bits are known from finds and from Xenophon's 'On Horsemanship')
      - REINS lying on the neck from the bit to the withers
      - a 'rider_seat' marker (empty on the back, follows the spine) for WS5's rider
    NO saddle (no tree) and NO stirrups: neither existed in 480 BC.
    Works on the horse's own bone names (DEF-head, DEF-spine_0x, DEF-scapula, ...). Returns the list of tack objects."""
    from lib import scans_glb
    rig = scans_glb.rig_of(horse_root)
    name = name or horse_root.name + '_tack'
    rig.data.pose_position = 'REST'                     # build on the horse as modelled (bones straight)
    bpy.context.view_layer.update()
    body, bverts, tree = _rest_body(rig)
    s = horse_root.scale.x                              # metres per model unit - offsets below are real metres
    leather = principled(f'{name}_leather', (0.10, 0.055, 0.03), rough=0.55, bump=0.2, bump_scale=300)
    bronze = bpy.data.materials.get('bronze') or aged_bronze('bronze')
    made = []
    # ----- landmarks from the skeleton
    scap = (_bone_pos(rig, 'DEF-scapula.L') + _bone_pos(rig, 'DEF-scapula.R')) / 2      # top of the shoulders
    sp2 = _bone_pos(rig, 'DEF-spine_02'); pelvis = _bone_pos(rig, 'DEF-pelvis')
    fwd = (scap - pelvis); fwd.z = 0; fwd.normalize()   # the direction the horse faces
    side = fwd.cross(Vector((0, 0, 1))).normalized()
    centre_x = scap.x
    # ----- saddle cloth
    if cloth:
        y_front = scap - fwd * 0.06
        y_back = sp2 + (pelvis - sp2) * 0.3
        n_st, n_ang = 16, 19
        grid = []
        for i in range(n_st):
            t = i / (n_st - 1)
            c = y_front.lerp(y_back, t); c.x = centre_x; c.z = c.z - 0.32
            row = []
            for j in range(n_ang):
                a = math.radians(-78 + 156 * j / (n_ang - 1))
                d = Vector((0, 0, 1)) * math.cos(a) + side * math.sin(a)
                p = _surface(tree, c, d, 0.012)
                row.append(p if p is not None else c + d * 0.3)
            # the bottom edges hang a little loose from the belly instead of hugging it
            for j in (0, n_ang - 1):
                row[j] = row[j] + Vector((0, 0, -0.03))
            grid.append(row)
        verts, faces, uvs = [], [], []
        for i, row in enumerate(grid):
            for j, p in enumerate(row):
                verts.append(tuple(p))
        for i in range(n_st - 1):
            for j in range(n_ang - 1):
                a = i * n_ang + j
                faces.append((a, a + 1, a + n_ang + 1, a + n_ang))
        cm = _cloth_material(f'{name}_cloth', cloth)
        co = mesh_obj(f'{name}_saddlecloth', verts, faces, cm)
        uvl = co.data.uv_layers.new(name='UVMap')
        for poly in co.data.polygons:
            for li, vi in zip(poly.loop_indices, poly.vertices):
                i, j = divmod(vi, n_ang)
                uvl.data[li].uv = (j / (n_ang - 1), i / (n_st - 1))
        co.modifiers.new('thick', 'SOLIDIFY').thickness = 0.008
        for p in co.data.polygons:
            p.use_smooth = True
        made.append(co)
        if cloth == 'persian':                         # fringe: short tassels along both lower edges
            fr = principled(f'{name}_fringe', (0.6, 0.42, 0.12), rough=0.9)
            for i in range(0, n_st, 1):
                for j in (0, n_ang - 1):
                    p = grid[i][j]
                    made.append(_tube(f'{name}_tassel', [tuple(p), tuple(p + Vector((0, 0, -0.07)))], 0.006, fr, poly=True, res=1))
    # ----- girth: a strap round the barrel just behind the elbows, holding the cloth
    if girth:
        gc = scap - fwd * 0.2; gc.x = centre_x; gc.z -= 0.3
        ring = _ring(tree, gc, fwd, 0.02 if cloth else 0.008, step_deg=10)
        made.append(_band(f'{name}_girth', ring, fwd, 0.05, 0.006, leather, closed=True))
    # ----- bridle
    if bridle:
        E = (_bone_pos(rig, 'DEF-eye.L') + _bone_pos(rig, 'DEF-eye.R')) / 2
        M = _bone_pos(rig, 'DEF-muzzle')
        ears = (_bone_pos(rig, 'DEF-ear_01.L') + _bone_pos(rig, 'DEF-ear_01.R')) / 2
        A = (M - ears).normalized()                       # the line of the face, poll -> nose
        hside = (_bone_pos(rig, 'DEF-eye.L') - _bone_pos(rig, 'DEF-eye.R')).normalized()
        hup = hside.cross(A).normalized()
        if hup.z < 0:
            hup = -hup
        head_c = E - hup * 0.05                           # a point inside the head, on its centre line
        P_crown = ears - A * 0.04 - hup * 0.08            # behind the ears, inside the head
        P_nose = E + (M - E) * 0.55 - hup * 0.03
        crown = _ring(tree, P_crown, A, 0.006, step_deg=12, up=hup)
        nose = _ring(tree, P_nose, A, 0.006, step_deg=12, up=hup)
        made.append(_band(f'{name}_crownpiece', crown, A, 0.025, 0.004, leather, closed=True))
        made.append(_band(f'{name}_noseband', nose, A, 0.025, 0.004, leather, closed=True))
        brow = _ring(tree, ears + A * 0.06 - hup * 0.06, A, 0.006, step_deg=12, start_deg=-60, end_deg=60, up=hup)
        if len(brow) > 2:
            made.append(_band(f'{name}_browband', brow, A, 0.02, 0.004, leather))
        for sg in (1, -1):                                # cheekpieces: down each side of the face, crown -> noseband
            pts = []
            for k in range(9):
                t = k / 8
                c = P_crown.lerp(P_nose, t)
                p = _surface(tree, c, (hside * sg * 0.9 + hup * 0.2).normalized(), 0.006)
                if p is not None:
                    pts.append(p)
            if len(pts) > 2:
                made.append(_band(f'{name}_cheek', pts, None, 0.022, 0.004, leather))
        # bit: a bronze bar through the mouth corners with a ring at each end
        lcL, lcR = _bone_pos(rig, 'DEF-lip_corner.L'), _bone_pos(rig, 'DEF-lip_corner.R')
        mid = (lcL + lcR) / 2; half = (lcL - lcR) / 2
        bitL, bitR = mid + half * 1.35, mid - half * 1.35
        made.append(_tube(f'{name}_bit', [tuple(bitL), tuple(bitR)], 0.006, bronze, poly=True))
        for p in (bitL, bitR):
            bpy.ops.mesh.primitive_torus_add(major_radius=0.025, minor_radius=0.004, location=p)
            t = bpy.context.object; t.name = f'{name}_bitring'; t.data.materials.append(bronze)
            t.rotation_euler = hside.to_track_quat('Z', 'Y').to_euler()
            made.append(t)
        # reins: from each bit ring along the side of the neck to the withers, joined over the neck
        if reins:
            chain = [_bone_pos(rig, p) for p in ('DEF-head', 'DEF-neck_05', 'DEF-neck_04', 'DEF-neck_03',
                                                 'DEF-neck_02', 'DEF-neck_01')]
            for sg, bit in ((1, bitL), (-1, bitR)):
                pts = [bit]
                for k, c in enumerate(chain[1:]):
                    ang = math.radians(70 - 40 * k / (len(chain) - 2))          # from the side up toward the crest
                    d = (Vector((0, 0, 1)) * math.cos(ang) + side * sg * math.sin(ang)).normalized()
                    p = _surface(tree, c, d, 0.03)
                    if p is not None:
                        pts.append(p)
                top = scap + Vector((0, 0, 0.09)) + fwd * 0.12
                pts.append(top + side * sg * 0.03)
                made.append(_tube(f'{name}_rein', [tuple(p) for p in pts], 0.006, leather))
    # ----- rider seat marker: on top of the back where a rider sits (just behind the withers)
    seat = bpy.data.objects.new(f'{name}_rider_seat', None); link(seat)
    seat.empty_display_size = 0.2; seat['role'] = 'rider_seat'
    sp = scap - fwd * 0.3
    top = _surface(tree, Vector((centre_x, sp.y, sp.z - 0.3)), Vector((0, 0, 1)), 0.03)
    seat.location = top if top is not None else sp
    seat.rotation_euler.z = math.atan2(fwd.y, fwd.x)
    def kind(o):                                       # which bones may move this piece (see TACK_BONES)
        n = o.name
        return 'reins' if '_rein' in n else 'body' if any(k in n for k in ('saddlecloth', 'tassel', 'girth')) else 'head'
    for k in ('body', 'reins', 'head'):
        _bind([o for o in made if kind(o) == k], rig, body, bverts, TACK_BONES[k])
    mw = seat.matrix_world.copy()
    seat.parent = rig; seat.parent_type = 'BONE'; seat.parent_bone = next(b.name for b in rig.data.bones if b.name.startswith('DEF-spine_02'))
    seat.matrix_world = mw
    rig.data.pose_position = 'POSE'
    bpy.context.view_layer.update()
    return made + [seat]


def folded_drape(name, width, height, folds=18, depth=0.05, material=None, seg=160, rows=12):
    """A hanging cloth panel with real vertical FOLDS (sine pleats that deepen toward the hem) - for valances,
    curtains, banners; reads like cloth without a simulation."""
    verts, faces = [], []
    for j in range(rows + 1):
        z = -height * j / rows
        k = 0.4 + 0.6 * (j / rows)                                   # folds deepen toward the bottom
        for i in range(seg + 1):
            x = -width / 2 + width * i / seg
            verts.append((x, depth * k * math.sin(2 * math.pi * folds * i / seg), z))
    for j in range(rows):
        for i in range(seg):
            a = j * (seg + 1) + i
            faces.append((a, a + 1, a + seg + 2, a + seg + 1))
    o = mesh_obj(name, verts, faces, material)
    for p in o.data.polygons:
        p.use_smooth = True
    o.modifiers.new('thick', 'SOLIDIFY').thickness = 0.006
    return o


def royal_dress_up(throne_root, pavilion_root, w=6.0, d=5.0, h=3.4):
    """Upgrade the pavilion + throne: folded valances on all four sides, gilded lion-paw feet and finials on the
    throne (Persepolis Treasury relief), a patterned carpet under it."""
    cloth = bpy.data.materials.get('royal_pavilion_cloth') or principled('royal_pavilion_cloth', (0.35, 0.05, 0.08), rough=0.85)
    trim = bpy.data.materials.get('royal_pavilion_trim') or principled('royal_pavilion_trim', (0.8, 0.6, 0.2), rough=0.6)
    for k, (x, y, rot) in enumerate([(0, -d / 2 - 0.16, 0), (0, d / 2 + 0.16, math.pi), (-w / 2 - 0.16, 0, math.pi / 2), (w / 2 + 0.16, 0, -math.pi / 2)]):
        width = w + 0.3 if k < 2 else d + 0.3
        v = folded_drape(f'valance_{k}', width, 0.55, folds=int(width * 4), material=cloth)
        v.location = (x, y, h + 0.2); v.rotation_euler.z = rot; v.parent = pavilion_root
        t = folded_drape(f'valance_trim_{k}', width, 0.06, folds=int(width * 4), material=trim)
        t.location = (x, y, h - 0.33); t.rotation_euler.z = rot; t.parent = pavilion_root
    g = gold()
    for x in (-0.28, 0.28):                                          # lion-paw feet: pad + three toes
        for y in (-0.25, 0.25):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.06, location=(x, y, 0.05))
            pad = bpy.context.object; pad.scale = (1.0, 1.25, 0.6); pad.data.materials.append(g); pad.parent = throne_root
            for k in (-1, 0, 1):
                bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.022, location=(x + k * 0.03, y - 0.065, 0.025))
                toe = bpy.context.object; toe.data.materials.append(g); toe.parent = throne_root
    for x in (-0.31, 0.31):                                          # finials on the back posts
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.05, location=(x, 0.28, 1.62))
        f = bpy.context.object; f.data.materials.append(g); f.parent = throne_root
        bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=0.035, depth=0.09, location=(x, 0.28, 1.71))
        c = bpy.context.object; c.data.materials.append(g); c.parent = throne_root
    rug = principled('royal_carpet', (0.3, 0.05, 0.05), rough=0.95, bump=0.3, bump_scale=200)
    nt = rug.node_tree; b = nt.nodes['Principled BSDF']
    chk = nt.nodes.new('ShaderNodeTexChecker'); chk.inputs['Scale'].default_value = 12
    chk.inputs['Color1'].default_value = (0.3, 0.05, 0.05, 1); chk.inputs['Color2'].default_value = (0.55, 0.38, 0.1, 1)
    nt.links.new(chk.outputs['Color'], b.inputs['Base Color'])
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0.005)); r = bpy.context.object
    r.scale = (2.6, 3.2, 1); r.data.materials.append(rug); r.parent = throne_root

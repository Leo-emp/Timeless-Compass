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

from lib.common import fabric                          # (kept for other sessions' code; WS7 uses the scanned wool())


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
    o = bpy.context.object; o.name = name
    # the size goes INTO the mesh (object scale stays 1): scanned textures then keep their real size in metres on
    # every face instead of stretching along the long side of a plank, and the bevel is a true bevel in metres
    o.data.transform(Matrix.Diagonal((*size, 1.0)))
    if bevel:
        b = o.modifiers.new('bevel', 'BEVEL'); b.width = min(bevel, 0.45 * min(size)); b.segments = 2
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
# Real photographed surfaces (Poly Haven CC0 scans in library/scans/) look far more real than noise patterns.
# We use the scan's DETAIL (grain, weave, creases, wear: its brightness + normal + roughness maps) and choose the
# COLOUR ourselves, so one wood scan can be olive, maple or ebony, and the (blue-dyed) linen scan any wool colour.
# Mapping: object coordinates in metres, box projection, `tile` = metres per texture repeat.
_SCAN_LUM = {'brown_planks_04': 0.175, 'rough_linen': 0.39, 'fabric_leather_02': 0.10, 'hessian_230': 0.20,
             'wicker_basket_01': 0.049}          # average brightness of each scan (measured), to normalise the detail
_SCAN_AVG = {'brown_planks_04': (0.221, 0.168, 0.138)}   # average linear colour (for keep_hue)


def _scan_files(scan):
    import os
    from lib.common import SCANS
    d = os.path.join(SCANS, scan)
    files = []
    for root, _, fs in os.walk(d):
        files += [os.path.join(root, f) for f in fs]
    pick = lambda *keys: next((f for f in files if any(k in os.path.basename(f) for k in keys)), None)
    return pick('_diff_', '_albedo_'), pick('_rough_'), pick('_nor_gl_')


def _age(m, src_socket, edge=0.25, grime=0.4, radius=0.03):
    """AGE a material like a used object: worn, paler, polished EDGES (AO 'inside' finds convex corners) and dark
    GRIME in corners and crevices (normal AO). Returns the new colour socket to feed into Base Color."""
    nt = m.node_tree; L = nt.links.new
    ao_e = nt.nodes.new('ShaderNodeAmbientOcclusion'); ao_e.inside = True; ao_e.only_local = True
    ao_e.inputs['Distance'].default_value = radius
    wear = nt.nodes.new('ShaderNodeMapRange'); wear.inputs['From Min'].default_value = 0.75; wear.inputs['From Max'].default_value = 0.98
    wear.inputs['To Min'].default_value = edge; wear.inputs['To Max'].default_value = 0.0      # low AO inside = edge
    L(ao_e.outputs['AO'], wear.inputs['Value'])
    lighter = nt.nodes.new('ShaderNodeMix'); lighter.data_type = 'RGBA'; lighter.blend_type = 'SCREEN'
    L(wear.outputs['Result'], lighter.inputs['Factor']); L(src_socket, lighter.inputs['A'])
    lighter.inputs['B'].default_value = (0.55, 0.5, 0.42, 1)
    ao_g = nt.nodes.new('ShaderNodeAmbientOcclusion'); ao_g.only_local = True; ao_g.inputs['Distance'].default_value = radius * 3
    dirt = nt.nodes.new('ShaderNodeMapRange'); dirt.inputs['From Min'].default_value = 0.4; dirt.inputs['From Max'].default_value = 1.0
    dirt.inputs['To Min'].default_value = grime; dirt.inputs['To Max'].default_value = 0.0
    L(ao_g.outputs['AO'], dirt.inputs['Value'])
    dark = nt.nodes.new('ShaderNodeMix'); dark.data_type = 'RGBA'; dark.blend_type = 'MULTIPLY'
    L(dirt.outputs['Result'], dark.inputs['Factor']); L(lighter.outputs['Result'], dark.inputs['A'])
    dark.inputs['B'].default_value = (0.25, 0.2, 0.15, 1)
    return dark.outputs['Result']


def scan_surface(name, scan, color, tile=0.6, rough=(0.5, 0.9), normal=1.0, keep_hue=False, metal=0.0, age=None):
    """age=(edge, grime) adds worn edges + crevice dirt (see _age); None = new/clean."""
    """Material from a scanned texture set: colour = `color` x the scan's brightness detail (keep_hue=True keeps the
    scan's own colour variation, rescaled to `color`). Falls back to a plain material if the scan is missing."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    diff, rgh, nor = _scan_files(scan)
    m = principled(name, color, metal=metal, rough=sum(rough) / 2)
    if diff is None:
        return m
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / tile,) * 3
    L(tc.outputs['Object'], mp.inputs['Vector'])

    def tex(path, data):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path, check_existing=True)
        if data:
            t.image.colorspace_settings.name = 'Non-Color'
        t.projection = 'BOX'; t.projection_blend = 0.3
        L(mp.outputs['Vector'], t.inputs['Vector'])
        return t
    td = tex(diff, False)
    lum = _SCAN_LUM.get(scan, 0.2)
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
    mix.inputs['Factor'].default_value = 1.0; mix.name = 'tint'                 # 'tint' B input = the colour
    mix.inputs['B'].default_value = (*color, 1)
    if keep_hue:                                           # scan colour x (wanted colour / scan's average colour)
        avg = _SCAN_AVG.get(scan, (lum,) * 3)
        mix.inputs['B'].default_value = (*[min(4.0, c / a) for c, a in zip(color, avg)], 1)
        L(td.outputs['Color'], mix.inputs['A'])
    else:
        bw = nt.nodes.new('ShaderNodeRGBToBW'); L(td.outputs['Color'], bw.inputs['Color'])
        dv = nt.nodes.new('ShaderNodeMath'); dv.operation = 'DIVIDE'; dv.inputs[1].default_value = lum
        L(bw.outputs['Val'], dv.inputs[0]); L(dv.outputs[0], mix.inputs['A'])
    L(_age(m, mix.outputs['Result'], *age) if age else mix.outputs['Result'], b.inputs['Base Color'])
    if rgh:
        mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = rough[0]; mr.inputs['To Max'].default_value = rough[1]
        L(tex(rgh, True).outputs['Color'], mr.inputs['Value']); L(mr.outputs['Result'], b.inputs['Roughness'])
    if nor and normal:
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = normal
        L(tex(nor, True).outputs['Color'], nm.inputs['Color']); L(nm.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Specular IOR Level'].default_value = 0.4
    return m


def meander_image(name='meander_key3', px=12):
    """The running MEANDER (Greek key), drawn in code into an image: a baseline + a square spiral per repeat, with
    a top border line - the ornament on furniture, textiles and vase rims of the period. One repeat = 5 x 6 units."""
    import numpy as np
    im = bpy.data.images.get(name)
    if im:
        return im
    W, H = 5 * px, 6 * px
    a = np.zeros((H, W), dtype=np.float32)

    lw = max(2, px // 3)                                 # painted line = 1/3 of a grid step (thin line, wide gap)
    off = (px - lw) // 2

    def line(x0, y0, x1, y1):
        for x in range(min(x0, x1) * px + off, max(x0, x1) * px + off + lw):
            for y in range(min(y0, y1) * px + off, max(y0, y1) * px + off + lw):
                a[min(y, H - 1), min(x, W - 1)] = 1.0
    path = [(0, 0), (5, 0)]                              # baseline, running on into the next repeat
    spiral = [(0, 0), (0, 4), (3, 4), (3, 1), (1, 1), (1, 3), (2, 3), (2, 2)]
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        line(x0, y0, x1, y1)
    for (x0, y0), (x1, y1) in zip(spiral, spiral[1:]):
        line(x0, y0, x1, y1)
    line(0, 5, 5, 5)                                     # top border, continuous
    rgba = np.stack([a, a, a, np.ones_like(a)], axis=-1)
    im = bpy.data.images.new(name, W, H, alpha=False)
    im.pixels.foreach_set(rgba.ravel()); im.update(); im.pack()
    im.colorspace_settings.name = 'Non-Color'
    return im


def painted_band(name, height, bg=(0.40, 0.09, 0.05), fg=(0.02, 0.018, 0.015), repeat=None):
    """Mineral paint band with a black meander on red (or any pair): mapped by object coordinates, so put it on a
    band object whose origin is its centre and whose height (m) is `height`. repeat = metres per key (default ~h)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    rep = repeat or height * 0.85
    m = principled(name, bg, rough=0.75, bump=0.08, bump_scale=300)
    nt = m.node_tree; L = nt.links.new; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / rep, 1 / rep, 1 / height)
    mp.inputs['Location'].default_value = (0.0, 0.0, 0.5)
    L(tc.outputs['Object'], mp.inputs['Vector'])
    sw = nt.nodes.new('ShaderNodeSeparateXYZ'); L(mp.outputs['Vector'], sw.inputs['Vector'])
    cm = nt.nodes.new('ShaderNodeCombineXYZ')
    ad = nt.nodes.new('ShaderNodeMath'); ad.operation = 'ADD'           # x and y both run along the band
    L(sw.outputs['X'], ad.inputs[0]); L(sw.outputs['Y'], ad.inputs[1]); L(ad.outputs[0], cm.inputs['X'])
    zz = nt.nodes.new('ShaderNodeMath'); zz.operation = 'ADD'; zz.inputs[1].default_value = 0.0
    L(sw.outputs['Z'], zz.inputs[0]); L(zz.outputs[0], cm.inputs['Y'])
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = meander_image(); t.interpolation = 'Linear'
    L(cm.outputs['Vector'], t.inputs['Vector'])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    mx.inputs['A'].default_value = (*bg, 1); mx.inputs['B'].default_value = (*fg, 1)
    L(t.outputs['Color'], mx.inputs['Factor']); L(mx.outputs['Result'], b.inputs['Base Color'])
    return m


def old_wood(name='old_wood', color=(0.26, 0.15, 0.08), grain=1.0):
    """Hand-worked wood (olive, maple, boxwood; imported ebony for the rich): the scanned plank texture gives real
    grain, knots and wear; satin from years of handling. Grain repeats every ~0.5 m (grain=2 -> finer)."""
    # tile 2.4 m: one board of the scan is ~0.45 m wide, so a leg or a table top shows grain, not plank seams
    return scan_surface(name, 'brown_planks_04', color, tile=2.4 / grain, rough=(0.45, 0.8), normal=0.6, keep_hue=True,
                        age=(0.22, 0.45))


def wool(name, color, tile=0.25):
    """Woven wool / linen cloth: the scanned rough-linen weave + creases, in any dye colour."""
    return scan_surface(name, 'rough_linen', color, tile=tile, rough=(0.75, 0.95), normal=0.8)


def leather(name='tack_leather', color=(0.10, 0.055, 0.03)):
    """Oiled leather straps (bridles, girths, sandals): scanned leather grain."""
    return scan_surface(name, 'fabric_leather_02', color, tile=0.15, rough=(0.4, 0.7), normal=0.7, age=(0.15, 0.3))


def black_gloss(name='black_gloss'):
    """Attic black 'glaze' (really an iron-rich slip fired black): deep black with a soft sheen."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = principled(name, (0.010, 0.009, 0.008), rough=0.42, bump=0.04, bump_scale=300)   # rough 0.28 read as silver
    m.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = 0.3
    return m


def wicker(name='wicker', color=(0.42, 0.30, 0.16)):
    """Woven reed / willow: the scanned wicker basket weave."""
    return scan_surface(name, 'wicker_basket_01', color, tile=0.18, rough=(0.6, 0.9), normal=1.0, age=(0.1, 0.4))


def rope_fibre(name='rope_fibre', color=(0.45, 0.36, 0.22)):
    """Twisted hemp / esparto / papyrus rope (Herodotus 7.25 + 7.36: Xerxes' bridge cables of white flax and papyrus):
    scanned hessian fibres at a small scale."""
    return scan_surface(name, 'hessian_230', color, tile=0.08, rough=(0.8, 0.98), normal=1.0)


def ember_glow(name='ember_glow', strength=6.0, temp=1250.0, cracks=0.45):
    """Glowing charcoal: black crust with orange-red light coming through the cracks (noise mask x blackbody)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    b.inputs['Base Color'].default_value = (0.02, 0.018, 0.016, 1); b.inputs['Roughness'].default_value = 0.9
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 45.0; n.inputs['Detail'].default_value = 6
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = cracks; mr.inputs['From Max'].default_value = cracks + 0.25
    L(n.outputs['Fac'], mr.inputs['Value'])
    # explicit ember colour (deep orange-red); a physical blackbody colour washes to salmon-pink under the film curve
    b.inputs['Emission Color'].default_value = (1.0, 0.22, 0.03, 1) if temp < 1150 else (1.0, 0.38, 0.06, 1)
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


def tongue_flame_material(name='flame_tongue4', strength=3.2):
    """Flame like a real wood/oil flame: hottest (yellow-white, ~1900 K) at the root, cooling to red (~1200 K) toward
    the tip, and fading to nothing at the top and edges (a flame has no hard outline). Uses each tongue's own
    0..1 'Generated' height, so it works at any size."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF']); L = nt.links.new
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(tc.outputs['Generated'], sep.inputs['Vector'])
    noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 4.0; noise.inputs['Detail'].default_value = 3
    L(tc.outputs['Generated'], noise.inputs['Vector'])
    zt = nt.nodes.new('ShaderNodeMath'); zt.operation = 'MULTIPLY_ADD'               # height + a little noise: ragged
    zt.inputs[1].default_value = 0.35; L(noise.outputs['Fac'], zt.inputs[0]); L(sep.outputs['Z'], zt.inputs[2])
    temp = nt.nodes.new('ShaderNodeMapRange'); temp.inputs['From Min'].default_value = 0.15; temp.inputs['From Max'].default_value = 1.2
    temp.inputs['To Min'].default_value = 1650.0; temp.inputs['To Max'].default_value = 1000.0   # orange root -> deep red tip
    L(zt.outputs['Value'], temp.inputs['Value'])
    # fire colour by height: an explicit ramp (the physical blackbody colour washed to pink under the film curve)
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    L(zt.outputs['Value'], ramp.inputs['Fac'])
    els = ramp.color_ramp.elements
    els[0].position = 0.1; els[0].color = (1.0, 0.62, 0.16, 1)            # root: yellow-orange
    els[1].position = 0.95; els[1].color = (0.35, 0.04, 0.01, 1)          # tip: dark red
    mid = els.new(0.5); mid.color = (0.95, 0.28, 0.04, 1)                 # body: orange-red
    bb = ramp                                                           # (keeps the code below unchanged)
    fade = nt.nodes.new('ShaderNodeMapRange'); fade.inputs['From Min'].default_value = 0.35; fade.inputs['From Max'].default_value = 1.25
    fade.inputs['To Min'].default_value = 1.0; fade.inputs['To Max'].default_value = 0.0
    L(zt.outputs['Value'], fade.inputs['Value'])
    root_f = nt.nodes.new('ShaderNodeMapRange'); root_f.inputs['From Min'].default_value = 0.0; root_f.inputs['From Max'].default_value = 0.22
    L(sep.outputs['Z'], root_f.inputs['Value'])          # the root fades in too: tongues merge, no round 'drop' bottoms
    both = nt.nodes.new('ShaderNodeMath'); both.operation = 'MULTIPLY'
    L(fade.outputs['Result'], both.inputs[0]); L(root_f.outputs['Result'], both.inputs[1])
    alpha = both.outputs[0]                                # how visible the flame is at each point
    em = nt.nodes.new('ShaderNodeEmission'); L(ramp.outputs['Color'], em.inputs['Color'])
    st = nt.nodes.new('ShaderNodeMath'); st.operation = 'MULTIPLY'; st.inputs[1].default_value = strength
    L(alpha, st.inputs[0]); L(st.outputs[0], em.inputs['Strength'])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader'); L(alpha, mix.inputs['Fac'])
    L(tr.outputs[0], mix.inputs[1]); L(em.outputs[0], mix.inputs[2])
    L(mix.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    return m


def flame_tongues(parent, loc, height=0.4, width=0.25, n=6, frames=(1, 240), seed=0, name='flame', strength=3.2):
    """A small fire as several teardrop 'tongues' of glowing gas that flicker and sway (keyframed scale + lean every
    2-3 frames). Light-weight and readable at any distance - no volume simulation. Returns the tongue objects."""
    rnd = _random.Random(seed)
    mat = tongue_flame_material(f'flame_tongue4_{round(strength, 1)}', strength)   # shared per brightness
    tex = bpy.data.textures.get('flame_ragged') or bpy.data.textures.new('flame_ragged', 'CLOUDS')
    tex.noise_scale = 0.12; tex.noise_depth = 3
    n = n * 2                                       # twice as many, thinner tongues: a fire, not a candle
    out = []
    for i in range(n):
        w = width * (0.18 + 0.3 * rnd.random()) if i else width * 0.4
        h = height * (0.35 + 0.65 * rnd.random()) if i else height
        bpy.ops.mesh.primitive_uv_sphere_add(segments=14, ring_count=10, radius=0.5)
        o = bpy.context.object; o.name = f'{name}_tongue'
        for v in o.data.vertices:                      # teardrop: round bottom, pointed top
            z = v.co.z + 0.5                          # 0..1
            k = 1.0 if z < 0.35 else max(0.02, (1 - (z - 0.35) / 0.65)) ** 1.4
            v.co.x *= k; v.co.y *= k; v.co.z = z
        o.data.transform(Matrix.Diagonal((w, w, h, 1.0)))
        for p_ in o.data.polygons:
            p_.use_smooth = True
        o.data.materials.append(mat)
        sub = o.modifiers.new('sub', 'SUBSURF'); sub.levels = 1
        dsp = o.modifiers.new('ragged', 'DISPLACE'); dsp.texture = tex; dsp.strength = w * 0.6   # torn, licking edges
        dsp.texture_coords = 'GLOBAL'
        o.visible_shadow = False                      # glowing gas casts no shadow
        o.parent = parent
        r = width * 0.3 * math.sqrt(rnd.random()); a = rnd.uniform(0, 2 * math.pi)
        o.location = (loc[0] + r * math.cos(a), loc[1] + r * math.sin(a), loc[2])
        f = frames[0]
        while f <= frames[1]:                          # flicker: height pulses, the tongue leans and turns
            o.scale = (rnd.uniform(0.85, 1.1), rnd.uniform(0.85, 1.1), rnd.uniform(0.7, 1.25))
            o.rotation_euler = (rnd.uniform(-0.18, 0.18), rnd.uniform(-0.18, 0.18), rnd.uniform(0, 6.28))
            o.keyframe_insert('scale', frame=f); o.keyframe_insert('rotation_euler', frame=f)
            f += rnd.choice((2, 3))
        out.append(o)
    return out


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


def kline(loc=(0, 0, 0), heading_deg=0.0, wood=None, mattress=(0.36, 0.10, 0.07), blanket=(0.16, 0.035, 0.03),
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
    kb = painted_band(f'{name}_meander', 0.05, bg=(0.36, 0.08, 0.04))
    for sy in (-1, 1):            # painted meander along the outside of the long rails (Attic symposion vases)
        _box(f'{name}_band', (0, sy * (W / 2 - 0.012), H - 0.03), (L - 0.12, 0.004, 0.05), kb, bevel=0.0, parent=root)
    # raised head-end at +X: two curved side bars + a board
    for sy in (-1, 1):
        _tube(f'{name}_headrest', [(L / 2 - 0.06, sy * (W / 2 - 0.05), H + 0.02), (L / 2 - 0.03, sy * (W / 2 - 0.05), H + 0.2),
                                   (L / 2 - 0.12, sy * (W / 2 - 0.05), H + 0.3)], 0.02, w, root)
    _box(f'{name}_headboard', (L / 2 - 0.05, 0, H + 0.14), (0.03, W - 0.08, 0.24), w, parent=root)
    # mattress (wool) + two cushions propped against the head end
    mt = wool(f'{name}_mattress', tuple(mattress))
    m = _box(f'{name}_mattress', (0, 0, H + 0.07), (L - 0.12, W - 0.06, 0.12), mt, bevel=0.04, parent=root)
    m.modifiers['bevel'].segments = 5
    cu = wool(f'{name}_cushion', (0.55, 0.38, 0.18))
    for k, dy in enumerate((-0.18, 0.18)):
        c = _box(f'{name}_cushion{k}', (L / 2 - 0.22, dy, H + 0.2), (0.14, 0.34, 0.22), cu, bevel=0.05, parent=root)
        c.modifiers['bevel'].segments = 5; c.rotation_euler.y = math.radians(-18)
    # blanket: lies over the mattress and hangs down the -Y front with soft folds (cloth sim is WS3's job)
    bl = wool(f'{name}_blanket', tuple(blanket), tile=0.35)             # scanned weave (procedural one flickered)
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
    band = painted_band(f'{name}_meander', 0.07, bg=tuple(paint))
    for sy in (-1, 1):            # painted meander band along the top of the front and back (vase-painting chests)
        _box(f'{name}_band', (0, sy * (D / 2 - 0.018), foot + H - 0.06), (L - 0.09, 0.006, 0.07), band, bevel=0.001, parent=root)
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
        flame_tongues(root, (0.079, 0, 0.024), height=0.032, width=0.011, n=1, frames=frames, seed=seed,
                      name=f'{name}_flame', strength=2.5)
        _flicker_light((0.079, 0, 0.075), power, root, f'{name}_light', frames, seed, radius=0.012)   # above the flame: lights the room, not just the lamp
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
        if flames:                                    # flame tongues licking up from the coals
            flame_tongues(root, (0, 0, coal_z + 0.02), height=coal_r * 2.0, width=coal_r * 0.9, n=7, frames=frames,
                          seed=seed, name=f'{name}_flame')
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


# ------------------------------------------------------------------ DRESSING KITS: fill a set with one call
# Real places are full of objects (the reference films' interiors are dense). Each kit lays out era-correct props by
# simple rules (around the walls, along a quay edge), with random turns so nothing repeats. loc = the kit's centre on
# the floor, heading_deg turns the whole layout. Museum scans come from scans_glb (credits in library/props/*.json).
def _kit_root(name, loc, heading_deg):
    r = _root(name)
    return r


def _put(child, root, local, turn_deg=0.0):
    child.parent = root; child.location = local; child.rotation_euler.z = math.radians(turn_deg)
    return child


def dress_symposion(loc=(0, 0, 0), heading_deg=0.0, couches=3, lit=True, seed=0, frames=(1, 240), name='symposion'):
    """An andron set for a symposion (c. 480 BC): `couches` klinai along three walls of a ~5 x 5 m room, a trapeza
    in front of each with a kylix and a lamp, the wine jars by the door, a brazier and lamp stands for light,
    a wool basket. A big neck-amphora of wine stands in the middle (our only krater scan is Lucanian 430-410 BC,
    too late - see library/props/krater_bell_met.json)."""
    from lib import scans_glb
    rnd = _random.Random(seed)
    root = _kit_root(name, loc, heading_deg)
    # (x, y), turn: a kline faces its local -Y, so the back-wall couch turns 0, the left wall +90, the right -90
    spots = [((0.0, 2.0), 0), ((-2.0, 0.2), 90), ((2.0, 0.2), -90), ((-1.0, 2.0), 0), ((1.0, 2.0), 0)][:couches]
    for i, ((x, y), turn) in enumerate(spots):
        k = _put(kline((0, 0, 0), 0, name=f'{name}_kline{i}'), root, (x, y, 0), turn)
        h = math.radians(turn)
        tx, ty = x + 0.75 * math.sin(h), y - 0.75 * math.cos(h)          # the table stands in front of the couch
        _put(trapeza((0, 0, 0), 0, name=f'{name}_table{i}'), root, (tx, ty, 0), turn)
        cup = scans_glb.load_glb('kylix_cleveland'); _put(cup, root, (tx + rnd.uniform(-0.15, 0.1), ty, 0.5), rnd.uniform(0, 360))
        _put(oil_lamp((0, 0, 0), 0, lit=lit, frames=frames, seed=seed + i, name=f'{name}_lamp{i}'), root,
             (tx + 0.22, ty + rnd.uniform(-0.1, 0.1), 0.5), rnd.uniform(0, 360))
    krater = scans_glb.load_glb('amphora_neck_cleveland'); _put(krater, root, (0.0, 0.0, 0.0), rnd.uniform(0, 360))
    for j in range(3):                                   # wine and water jars by the door
        a = scans_glb.load_glb(('amphora_terracotta_met', 'amphora_blackfigure_cleveland')[j % 2])
        _put(a, root, (-1.8 + j * 0.45, -2.1, 0), rnd.uniform(0, 360))
    _put(brazier((0, 0, 0), 0, kind='bronze', lit=lit, frames=frames, seed=seed + 7, name=f'{name}_brazier'), root, (1.7, -1.6, 0))
    for j, (x, y) in enumerate(((-2.2, 2.2), (2.2, 2.2))):
        _put(lamp_stand((0, 0, 0), 0, lit=lit, frames=frames, seed=seed + 20 + j, name=f'{name}_stand{j}'), root, (x, y, 0))
    _put(basket((0, 0, 0), 0, kind='kalathos', fill=(0.82, 0.78, 0.7), name=f'{name}_wool'), root, (-2.3, -1.5, 0))
    return _place(root, loc, heading_deg)


def dress_storeroom(loc=(0, 0, 0), heading_deg=0.0, rows=2, per_row=6, seed=0, name='storeroom'):
    """A household storeroom: rows of amphorae (museum scans, leaning on each other as in excavated storerooms),
    two chests, baskets, a coiled rope."""
    from lib import scans_glb
    rnd = _random.Random(seed)
    root = _kit_root(name, loc, heading_deg)
    jars = ['amphora_terracotta_met', 'amphora_blackfigure_cleveland', 'amphora_neck_cleveland']
    for r in range(rows):
        for c in range(per_row):
            a = scans_glb.load_glb(rnd.choice(jars))
            a.rotation_euler.x = rnd.uniform(-0.05, 0.05)
            _put(a, root, (c * 0.42 - per_row * 0.21 + rnd.uniform(-0.03, 0.03), 1.5 - r * 0.5, 0), rnd.uniform(0, 360))
    _put(chest((0, 0, 0), 0, lid='gable', name=f'{name}_chest0'), root, (-1.8, 0.1, 0), 90)
    _put(chest((0, 0, 0), 0, size=(0.7, 0.45, 0.42), paint=(0.15, 0.12, 0.1), name=f'{name}_chest1'), root, (-1.8, -0.8, 0), 80)
    _put(basket((0, 0, 0), 0, kind='carry', fill=(0.55, 0.45, 0.25), name=f'{name}_grain'), root, (1.6, -0.4, 0))
    _put(basket((0, 0, 0), 0, kind='flat', name=f'{name}_tray'), root, (1.2, -0.9, 0))
    _put(rope_coil((0, 0, 0), 0, radius=0.25, strands=False, name=f'{name}_rope'), root, (0.6, -0.9, 0))
    return _place(root, loc, heading_deg)


def dress_quay(loc=(0, 0, 0), heading_deg=0.0, length=20.0, boats=2, seed=0, name='quay'):
    """A harbour quay (the Piraeus / Salamis shore): stacks of amphorae, rope coils, stone anchors, baskets of
    catch, nets, and fishing boats drawn up or moored along the edge (the water is on the -Y side)."""
    from lib import scans_glb
    rnd = _random.Random(seed)
    root = _kit_root(name, loc, heading_deg)
    x = -length / 2
    while x < length / 2:
        kind = rnd.random()
        if kind < 0.35:                                   # a cluster of transport amphorae
            for j in range(rnd.randint(3, 7)):
                a = scans_glb.load_glb('amphora_terracotta_met')
                a.rotation_euler.x = rnd.uniform(-0.08, 0.08)
                _put(a, root, (x + rnd.uniform(-0.6, 0.6), rnd.uniform(0.6, 1.8), 0), rnd.uniform(0, 360))
        elif kind < 0.55:
            _put(rope_coil((0, 0, 0), 0, radius=rnd.uniform(0.2, 0.35), name=f'{name}_rope'), root, (x, rnd.uniform(-0.2, 0.6), 0), rnd.uniform(0, 360))
        elif kind < 0.7:
            _put(stone_anchor((0, 0, 0), 0, name=f'{name}_anchor'), root, (x, rnd.uniform(-0.1, 0.5), 0), rnd.uniform(0, 360))
        else:
            _put(basket((0, 0, 0), 0, kind='carry', fill=(0.55, 0.58, 0.6) if rnd.random() < 0.6 else None,
                        name=f'{name}_basket'), root, (x, rnd.uniform(0.2, 1.4), 0), rnd.uniform(0, 360))
        x += rnd.uniform(1.0, 2.6)
    for b in range(boats):
        bx = -length / 2 + (b + 0.5) * length / max(boats, 1)
        _put(fishing_boat((0, 0, 0), 0, oars='in', seed=seed + b, name=f'{name}_boat{b}'), root, (bx - 3.3, -2.6, -1.0),
             rnd.uniform(-8, 8))                         # moored: the water is ~1 m below the quay top
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
        sail = wool(f'{name}_sail', (0.70, 0.62, 0.48))
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


def _proxy_mesh(role, mats):
    """ONE low-poly person mesh per role (shared by every crew member of that role = cheap): legs, tunic, torso with
    shoulders, arms, neck, head; marines add a bronze helmet + crest, a round aspis on the left arm and a spear;
    archers a bow. 1.7 m tall, feet at z = 0, facing +X. For WIDE shots only; close shots put real cast/crowd
    characters on the same markers (WS1/WS2)."""
    import bmesh
    key = f'crew_proxy_{role}'
    me = bpy.data.meshes.get(key)
    if me:
        return me
    cloth = {'marine': 'marine', 'archer': 'archer'}.get(role, 'cloth')
    order = [cloth, 'skin', 'bronze', 'crest', 'wood']
    bm = bmesh.new()

    def part(kind, mi, mat4, **kw):
        if kind == 'cone':
            r = bmesh.ops.create_cone(bm, cap_ends=True, segments=kw.get('seg', 8), radius1=kw['r1'], radius2=kw['r2'],
                                      depth=kw['d'], matrix=mat4)
        elif kind == 'sphere':
            r = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=kw['r'], matrix=mat4)
        else:
            r = bmesh.ops.create_cube(bm, size=1.0, matrix=mat4 @ Matrix.Diagonal((*kw['s'], 1.0)))
        for f in {f for v in r['verts'] for f in v.link_faces}:
            f.material_index = mi
    T = Matrix.Translation
    R = lambda deg, ax: Matrix.Rotation(math.radians(deg), 4, ax)
    for sy in (-1, 1):
        part('cone', 1, T((0, sy * 0.09, 0.42)), r1=0.045, r2=0.07, d=0.84)                 # legs (bare: tunic is short)
        part('cone', 0, T((0.02, sy * 0.25, 1.22)) @ R(8 * sy, 'X'), r1=0.04, r2=0.055, d=0.6)   # arms in sleeves
        part('sphere', 1, T((0.03, sy * 0.27, 0.9)), r=0.045)                                 # hands
    part('cone', 0, T((0, 0, 0.92)), r1=0.25, r2=0.17, d=0.36, seg=10)                         # tunic skirt (flared)
    part('cone', 0, T((0, 0, 1.3)), r1=0.16, r2=0.21, d=0.5, seg=10)                           # torso -> shoulders
    part('cone', 1, T((0, 0, 1.58)), r1=0.05, r2=0.05, d=0.1)                                  # neck
    part('sphere', 1, T((0.01, 0, 1.68)), r=0.105)                                             # head
    if role == 'marine':
        part('sphere', 2, T((0, 0, 1.71)) @ Matrix.Diagonal((1.12, 1.05, 1.08, 1)), r=0.115)   # Corinthian helmet
        part('box', 3, T((-0.02, 0, 1.86)), s=(0.32, 0.04, 0.1))                               # horsehair crest
        part('cone', 2, T((0.12, -0.32, 1.12)) @ R(90, 'X') @ R(12, 'Y'), r1=0.45, r2=0.45, d=0.05, seg=20)   # aspis
        part('cone', 4, T((0.15, 0.3, 1.25)), r1=0.014, r2=0.012, d=2.4, seg=6)                 # dory (spear)
    elif role == 'archer':
        part('cone', 4, T((0.12, -0.3, 1.2)) @ R(-10, 'X'), r1=0.012, r2=0.012, d=1.3, seg=6)   # bow stave
        part('cone', 0, T((-0.14, 0.12, 1.32)) @ R(20, 'X'), r1=0.05, r2=0.05, d=0.5, seg=8)   # quiver on the back
    me = bpy.data.meshes.new(key); bm.to_mesh(me); bm.free()
    for nm in order:
        me.materials.append(mats[nm])
    for p_ in me.polygons:
        p_.use_smooth = True
    return me


def _rower_mesh(mats):
    """Seated rower stand-in (shared mesh): hips on the bench at z = 0, torso, head, both arms reaching forward
    (+X) to the oar handle. The object pivots at the hips, so rotating it about Y = leaning into the stroke."""
    import bmesh
    me = bpy.data.meshes.get('crew_proxy_rower')
    if me:
        return me
    bm = bmesh.new()

    def part(kind, mi, mat4, **kw):
        if kind == 'cone':
            r = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=kw['r1'], radius2=kw['r2'], depth=kw['d'], matrix=mat4)
        else:
            r = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=kw['r'], matrix=mat4)
        for f in {f for v in r['verts'] for f in v.link_faces}:
            f.material_index = mi
    T = Matrix.Translation; R = lambda deg, ax: Matrix.Rotation(math.radians(deg), 4, ax)
    part('cone', 0, T((0, 0, 0.3)), r1=0.17, r2=0.2, d=0.6)                   # torso (bare or in an exomis)
    part('sphere', 1, T((0.02, 0, 0.7)), r=0.1)                              # head
    for sy in (-1, 1):
        part('cone', 1, T((0.25, sy * 0.17, 0.45)) @ R(90, 'Y'), r1=0.04, r2=0.045, d=0.5)   # arms to the handle
        part('cone', 1, T((0.25, sy * 0.1, -0.05)) @ R(80, 'Y'), r1=0.05, r2=0.07, d=0.5)    # thighs
    me = bpy.data.meshes.new('crew_proxy_rower'); bm.to_mesh(me); bm.free()
    me.materials.append(mats['cloth']); me.materials.append(mats['skin'])
    for p_ in me.polygons:
        p_.use_smooth = True
    return me


def _person_proxy(name, role, parent, loc, face_deg, mats, rnd):
    """Place one stand-in person (a cheap object sharing its role's mesh), a little bigger or smaller each time."""
    o = bpy.data.objects.new(name, _proxy_mesh(role, mats)); link(o)
    k = rnd.uniform(0.95, 1.04)
    o.parent = parent; o.location = loc; o.scale = (k, k, k)
    o.rotation_euler.z = math.radians(face_deg)
    return o


def _crew_mats():
    # muted, sun-faded dyes: at 50+ m bright red/white proxies read as toy soldiers
    return {'cloth': wool('crew_cloth', (0.26, 0.22, 0.17)), 'marine': wool('crew_marine', (0.22, 0.07, 0.05)),
            'archer': wool('crew_archer', (0.18, 0.15, 0.11)), 'skin': principled('crew_skin', (0.30, 0.18, 0.11), rough=0.6),
            'bronze': bpy.data.materials.get('bronze') or aged_bronze('bronze'),
            'crest': principled('crew_crest', (0.35, 0.05, 0.04), rough=0.8),
            'wood': bpy.data.materials.get('oar_wood_old') or old_wood('oar_wood_old', (0.40, 0.29, 0.17))}


def foam_material(name='sea_foam', density=0.55, scale=6.0, fade=False):
    """White water: bright, slightly translucent foam broken into patches by noise (alpha), so it never looks like
    a solid white plastic shape. Object coordinates, so it moves with the ship. fade=True also fades it out along
    the mesh's own X (0 -> 1), for a wake that dies away behind the ship."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    b.inputs['Base Color'].default_value = (0.82, 0.86, 0.88, 1); b.inputs['Roughness'].default_value = 0.45
    if 'Subsurface Weight' in b.inputs:
        b.inputs['Subsurface Weight'].default_value = 0.3
    tc = nt.nodes.new('ShaderNodeTexCoord')
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = 8
    L(tc.outputs['Object'], n.inputs['Vector'])
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 1 - density
    mr.inputs['From Max'].default_value = 1 - density + 0.12
    L(n.outputs['Fac'], mr.inputs['Value'])
    alpha = mr.outputs['Result']
    if fade:
        sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(tc.outputs['Generated'], sep.inputs['Vector'])
        inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
        L(sep.outputs['X'], inv.inputs[1])
        mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; L(alpha, mul.inputs[0]); L(inv.outputs[0], mul.inputs[1])
        alpha = mul.outputs[0]
    L(alpha, b.inputs['Alpha'])
    return m


def _splash_mesh(name='oar_splash'):
    """A splash = a small cluster of foam blobs (~0.5 m across), shared by every oar."""
    import bmesh
    me = bpy.data.meshes.get(name)
    if me:
        return me
    rnd = _random.Random(7)
    bm = bmesh.new()
    for i in range(7):
        r = rnd.uniform(0.06, 0.16)
        c = Vector((rnd.uniform(-0.2, 0.2), rnd.uniform(-0.12, 0.12), rnd.uniform(0.0, 0.12)))
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r, matrix=Matrix.Translation(c) @ Matrix.Diagonal((1.4, 1, 0.7, 1)))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(foam_material('splash_foam', density=0.75, scale=14.0))
    for p_ in me.polygons:
        p_.use_smooth = True
    return me


def _ship_oars(root, name, oars, oarm, rnd, stroke_frames=34, frame_start=1, L=_TRI_L, splash=False, rowers=False):
    """All 170 trireme oars as pivoting objects (shared meshes) under two side empties; 'row' = looping stroke,
    'rest' = held level just above the water. splash=True: a burst of white water where each blade bites in (the
    catch), timed to that oar's own stroke. Used by trireme_v2 and trireme_v3."""
    # one pivot per oar, mirrored for the port side by a parent with scale y = -1
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
                    if splash:                     # white water where the blade enters, only around the catch
                        R = Matrix.Rotation(math.radians(-24), 3, 'Z') @ Matrix.Rotation(-dip_in, 3, 'X')
                        tip = Vector((x, ly, lz)) + R @ Vector((0, reach, 0))
                        sp = bpy.data.objects.new(o.name + '_splash', _splash_mesh()); link(sp)
                        sp.parent = side; sp.location = (tip.x, tip.y, 0.0)
                        sp.rotation_euler.z = rnd.uniform(0, 6.28)
                        for ph, k in ((0.0, 0.05), (0.06, 1.0), (0.3, 0.55), (0.5, 0.0), (1.0, 0.05)):
                            sp.scale = (k, k, k * 0.8)
                            sp.keyframe_insert('scale', frame=f0 + ph * T)
                        _loop(sp)
                    if rowers and bank == 'thranite':   # the top-bank rower, seen through the open outrigger
                        rw = bpy.data.objects.new(o.name + '_rower', _rower_mesh(_crew_mats())); link(rw)
                        # rowers face the STERN: he sits on the bow side of his oar handle (handle ~0.3*length inboard)
                        rw.parent = side; rw.location = (x + 0.55, ly - inb, lz - 0.45)
                        rw.rotation_euler.z = math.pi
                        for ph, lean in ((0.0, 22), (0.45, -18), (0.56, -16), (0.93, 20), (1.0, 22)):
                            rw.rotation_euler.y = math.radians(lean)  # reach forward at the catch, lie back at the finish
                            rw.keyframe_insert('rotation_euler', index=1, frame=f0 + ph * T)
                        _loop(rw)


def _ship_crew(root, name, crew, rnd, L=_TRI_L, deck_z=2.42, phoenician=False, marines=14):
    """Crew markers (role in a custom property) + optional low-poly stand-ins, and all 170 rower seats."""
    if crew:
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


def _ship_motion(root, loc, heading_deg, speed_mps, bob, frame_start, frame_end):
    """Place the ship, then keyframe forward travel along the heading and a looping swell (heave/pitch/roll)."""
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
    _ship_oars(root, name, oars, oarm, rnd, stroke_frames, frame_start, L)
    # ---- steering oars (pedalia): two big paddles at the stern quarters, angled down and aft into the water
    for sgn in (-1, 1):
        _tube(f'{name}_rudder_shaft', [(L * 0.1, sgn * 2.05, 2.6), (L * 0.1 - 1.9, sgn * 2.35, -0.4)], 0.07, oarm, root, poly=True)
        bl = _box(f'{name}_rudder_blade', (L * 0.1 - 2.05, sgn * 2.37, -0.65), (0.6, 0.05, 1.1), oarm, bevel=0.01, parent=root)
        bl.rotation_euler.y = math.radians(-33)
    # ---- sail
    if sail == 'set':
        mast_x = L * 0.55
        linen = wool(f'{name}_sail_linen', (0.72, 0.64, 0.50), tile=1.2)
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
    _ship_crew(root, name, crew, rnd, L, 2.99 if phoenician else 2.42, phoenician, marines)
    _ship_motion(root, loc, heading_deg, speed_mps, bob, frame_start, frame_end)
    return root


# ------------------------------------------------------------------ TRIREME v3: detailed hull + FAST instanced fleets
# Why v3: (1) close shots need the detail of a real ship: plank seams under the pitch, rub-rails, an open outrigger
# with thole pins, leather oar-port sleeves, catheads, rigging as thick laid rope; (2) a fleet scene needs DOZENS of
# ships, and v1/v2 take ~2 minutes and 400 objects each. v3 builds the static ship ONCE per variant into a hidden
# 'kit' collection (pure bmesh, no slow bpy.ops), and every ship after that is one cheap INSTANCE of the kit plus
# whatever must move on its own (oars, sail, crew).
# Extra design sources: Thucydides 7.34 + 7.36 (epotides = catheads, strengthened for ramming); the askomata, leather
# sleeves sealing the lowest oar ports (Aristophanes, Acharnians 97); Olympias reconstruction for the open outrigger.
def _bm_tube(bm, pts, radius, mi, seg=8, caps=True):
    """A round tube through `pts` (radius = number or one per point) straight into a bmesh. The ring frame is carried
    along the path (parallel transport) so the tube never twists."""
    pts = [Vector(p) for p in pts]
    rad = radius if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    n = len(pts)
    t0 = (pts[1] - pts[0]).normalized()
    a = t0.orthogonal().normalized()
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        a = (a - t * a.dot(t)).normalized()
        b = t.cross(a)
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / seg) + b * math.sin(2 * math.pi * k / seg)) * rad[i])
                      for k in range(seg)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(seg):
            f = bm.faces.new((r0[k], r0[(k + 1) % seg], r1[(k + 1) % seg], r1[k])); f.material_index = mi; f.smooth = True
    if caps:
        for r in (rings[0], rings[-1][::-1]):
            f = bm.faces.new(r[::-1]); f.material_index = mi


def _bm_box(bm, centre, size, mi, rot=None):
    import bmesh
    M = Matrix.Translation(centre) @ (rot.to_4x4() if rot is not None else Matrix.Identity(4)) @ Matrix.Diagonal((*size, 1.0))
    r = bmesh.ops.create_cube(bm, size=1.0, matrix=M)
    for f in {f for v in r['verts'] for f in v.link_faces}:
        f.material_index = mi


def _bm_cyl(bm, centre, r1, r2, depth, mi, rot=None, seg=12):
    import bmesh
    M = Matrix.Translation(centre) @ (rot.to_4x4() if rot is not None else Matrix.Identity(4))
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=depth, matrix=M)
    for f in {f for v in r['verts'] for f in v.link_faces}:
        f.material_index = mi
        f.smooth = True


def _tri_hull_pt(t, z, sgn, L=_TRI_L, beam=2.3, top=2.1, keel=-0.85):
    """Outside point of the trireme hull (the _hull_mesh loft above) at length fraction t, height z, side sgn."""
    b = beam * (math.sin(math.pi * t) ** 0.55) * (0.88 if t > 0.5 else 1.0) + 0.03
    stern_rise = 1.4 * max(0.0, 0.18 - t) / 0.18
    bow_rise = 0.5 * max(0.0, t - 0.9) / 0.1
    k = keel * (math.sin(math.pi * min(1, t * 1.05)) ** 0.35) + stern_rise + bow_rise
    tp = top + 0.9 * max(0.0, 0.12 - t) / 0.12 + 0.35 * max(0.0, t - 0.92) / 0.08
    z = min(max(z, k), tp)
    s = ((z - k) / max(tp - k, 1e-6)) ** (1 / 2.4)
    return Vector((t * L, sgn * b * s, z)), tp


def _weather_pitch(m):
    """Sea-worn pitch: pale SALT STREAKS running down the hull from the wales (noise stretched vertically) and a
    duller, crazed finish higher up where the sun bakes it. Added on top of the plank-scan colour."""
    nt = m.node_tree; L = nt.links.new; b = nt.nodes['Principled BSDF']
    src = b.inputs['Base Color'].links[0].from_socket
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (3.0, 3.0, 0.25)   # long vertical runs
    L(tc.outputs['Object'], mp.inputs['Vector'])
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 4.0; n.inputs['Detail'].default_value = 6
    L(mp.outputs['Vector'], n.inputs['Vector'])
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.58; mr.inputs['From Max'].default_value = 0.75
    mr.inputs['To Max'].default_value = 0.35
    L(n.outputs['Fac'], mr.inputs['Value'])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    L(mr.outputs['Result'], mix.inputs['Factor']); L(src, mix.inputs['A']); mix.inputs['B'].default_value = (0.32, 0.3, 0.27, 1)
    L(mix.outputs['Result'], b.inputs['Base Color'])
    return m


def _tri_mats(phoenician):
    hull_col = (0.05, 0.016, 0.01) if phoenician else (0.016, 0.014, 0.012)     # red-ochre pitch / black pitch
    pname = 'tri4_pitch_red' if phoenician else 'tri4_pitch'
    pitch = bpy.data.materials.get(pname) or _weather_pitch(
        scan_surface(pname, 'brown_planks_04', hull_col, tile=1.5, rough=(0.3, 0.65), normal=1.3, keep_hue=True))
    return [
        pitch,                                                                 # 0 planked hull under glossy pitch
        principled('tri3_ochre', (0.30, 0.06, 0.03), rough=0.6, bump=0.15, bump_scale=60),   # 1 red top strake
        old_wood('tri3_deck', (0.30, 0.21, 0.13)),                                           # 2 deck + frames
        bpy.data.materials.get('bronze') or aged_bronze('bronze'),                           # 3 ram, fittings
        principled('eye_white', (0.85, 0.82, 0.74), rough=0.5),                              # 4 painted eye
        rope_fibre('tri3_rope', (0.42, 0.34, 0.22)),                                         # 5 rigging
        old_wood('tri3_oarwood', (0.40, 0.29, 0.17)),                                        # 6 steering oars, mast
        leather('tri3_askoma', (0.09, 0.05, 0.03)),                                          # 7 leather sleeves
        wool('tri3_furled', (0.62, 0.55, 0.43), tile=0.6),                                   # 8 furled sail
        principled('tri3_shield_a', (0.55, 0.38, 0.12), metal=0.6, rough=0.45),              # 9 shields (Phoen.)
        principled('tri3_shield_b', (0.32, 0.06, 0.04), rough=0.7),                          # 10
        principled('tri3_shield_c', (0.60, 0.52, 0.40), rough=0.7),                          # 11
        principled('eye_marble', (0.78, 0.75, 0.68), rough=0.35),                            # 12 marble eye plate
        principled('eye_iris', (0.32, 0.07, 0.04), rough=0.4),                               # 13 painted iris
        principled('eye_pupil', (0.01, 0.01, 0.01), rough=0.3),                              # 14 pupil
        painted_band('tri4_outrigger_meander', 0.16, bg=(0.33, 0.07, 0.04), fg=(0.82, 0.78, 0.68), repeat=0.16),  # 15
        wool('tri4_pennant', (0.42, 0.06, 0.05), tile=0.4),                                  # 16 pennants
        wool('tri4_screens', (0.32, 0.26, 0.18), tile=0.5),                                  # 17 rolled side screens
        terracotta('tri4_jar_clay'),                                                         # 18 water jars
    ]


def _trireme_kit(phoenician=False, furled=True):
    """Build (once) the hidden collection with the static ship: hull + every fitting + rigging. Cached by variant."""
    import bmesh
    key = f'kit_trireme4_{"phoen" if phoenician else "athen"}_{"furled" if furled else "set"}'
    col = bpy.data.collections.get(key)
    if col:
        return col
    col = bpy.data.collections.new(key)
    mats = _tri_mats(phoenician)
    L = _TRI_L
    # ---- hull: the v1 loft, finer, with plank-scan pitch
    v, f = _hull_mesh(L=L, sections=120, around=32)
    me = bpy.data.meshes.new(key + '_hull'); me.from_pydata(v, [], f); me.update()
    me.materials.append(mats[0])
    wet = bpy.data.materials.get('tri3_waterline') or principled('tri3_waterline', (0.012, 0.016, 0.01), rough=0.22,
                                                                   bump=0.3, bump_scale=30)   # wet pitch + a little weed
    me.materials.append(wet)
    for p_ in me.polygons:
        p_.use_smooth = True
        if p_.center.z < 0.18:                       # everything at and just above the waterline stays wet
            p_.material_index = 1
    hull = bpy.data.objects.new(key + '_hull', me); col.objects.link(hull)
    hull.modifiers.new('thick', 'SOLIDIFY').thickness = 0.07
    hull.modifiers.new('smooth', 'SUBSURF').levels = 1
    # ---- fittings: one bmesh, many parts, material by index
    bm = bmesh.new()
    ts = [0.05 + 0.9 * i / 40 for i in range(41)]
    for sgn in (-1, 1):
        # rub-rails (wales): three thick strakes following the hull, the top one painted red ochre
        for z, r, mi in ((0.55, 0.05, 0), (1.25, 0.055, 0), (1.85, 0.065, 0), (2.02, 0.07, 1)):
            pts = []
            for t in ts:
                p, tp = _tri_hull_pt(t, z + (0.0 if z < 1.9 else 0.0), sgn)
                if z > 1.9:
                    p, _ = _tri_hull_pt(t, tp - 0.08, sgn)
                pts.append(p + Vector((0, sgn * r * 0.6, 0)))
            _bm_tube(bm, pts, r, mi, seg=8)
        # open outrigger: top rail + thole rail, brackets back to the hull every ~1.4 m, a thole pin per thranite
        x0, x1 = L * 0.2, L * 0.83
        _bm_tube(bm, [(x0, sgn * 2.78, 2.22), (x1, sgn * 2.78, 2.22)], 0.07, 2, seg=8)
        _bm_tube(bm, [(x0, sgn * 2.72, 1.98), (x1, sgn * 2.72, 1.98)], 0.06, 2, seg=8)
        nb = int((x1 - x0) / 1.4)
        for k in range(nb + 1):
            x = x0 + (x1 - x0) * k / nb
            hp, _ = _tri_hull_pt(x / L, 1.9, sgn)
            _bm_tube(bm, [hp, (x, sgn * 2.75, 2.2)], 0.055, 2, seg=6)
            _bm_tube(bm, [(x, sgn * 2.75, 2.22), (x, sgn * 2.2, 2.42)], 0.045, 2, seg=6)   # knee up to the deck edge
        for k in range(31):
            x = L * 0.22 + (L * 0.6) * k / 30
            _bm_cyl(bm, (x, sgn * 2.72, 2.08), 0.022, 0.018, 0.2, 2, seg=6)
        # oar ports: leather askomata on the lowest bank, dark ports on the middle bank
        for bank, count, ly, lz, ln in _TRI_BANKS[1:]:
            for k in range(count):
                x = L * 0.22 + (L * 0.6) * k / (count - 1)
                p, _ = _tri_hull_pt(x / L, lz, sgn)
                rot = Matrix.Rotation(math.radians(90), 3, 'X')
                if bank == 'thalamite':
                    _bm_cyl(bm, p + Vector((0, sgn * 0.02, 0)), 0.13, 0.08, 0.06, 7, rot=rot, seg=10)
                else:
                    _bm_cyl(bm, p + Vector((0, sgn * 0.01, 0)), 0.085, 0.085, 0.02, 0, rot=rot, seg=10)
        # painted eye on the bow
        p, _ = _tri_hull_pt(0.95, 1.25, sgn)
        rot = Matrix.Rotation(math.radians(90), 3, 'X') @ Matrix.Rotation(0, 3, 'Z')
        _bm_cyl(bm, p + Vector((0, sgn * 0.03, 0)), 0.32, 0.32, 0.02, 4, rot=Matrix.Rotation(math.radians(-sgn * 20), 3, 'Z') @ rot, seg=24)
        _bm_cyl(bm, p + Vector((0.08, sgn * 0.05, 0)), 0.15, 0.15, 0.02, 0, rot=Matrix.Rotation(math.radians(-sgn * 20), 3, 'Z') @ rot, seg=16)
        # catheads (epotides): heavy beams sticking out either side of the bow
        _bm_box(bm, (L * 0.9, sgn * 1.55, 2.35), (0.3, 1.5, 0.28), 2)
        _bm_box(bm, (L * 0.9, sgn * 2.33, 2.35), (0.34, 0.08, 0.32), 3)          # bronze cap
        # deck stanchions + a light rail
        for k in range(13):
            x = L * 0.16 + (L * 0.7) * k / 12
            _bm_box(bm, (x, sgn * 1.68, 2.72), (0.08, 0.08, 0.62), 2)
        _bm_tube(bm, [(L * 0.16, sgn * 1.68, 3.03), (L * 0.86, sgn * 1.68, 3.03)], 0.04, 2, seg=6)
        # steering oars with tillers at the stern quarters
        _bm_tube(bm, [(L * 0.1 + 0.6, sgn * 1.7, 3.1), (L * 0.1, sgn * 2.1, 2.6), (L * 0.1 - 1.9, sgn * 2.4, -0.4)], 0.075, 6, seg=8)
        _bm_box(bm, (L * 0.1 - 2.06, sgn * 2.42, -0.66), (0.62, 0.06, 1.15), 6, rot=Matrix.Rotation(math.radians(-33), 3, 'Y'))
    # deck (planked), helmsman's bench, mast step
    _bm_box(bm, (L * 0.5, 0, 2.4), (L * 0.72, 3.4, 0.07), 2)
    _bm_box(bm, (L * 0.12, 0, 2.62), (0.5, 1.6, 0.12), 2)
    # bronze 3-fin ram (Athenian) or pointed ram (Phoenician) + small upper ram (proembolion)
    if phoenician:
        _bm_cyl(bm, (L + 1.0, 0, 0.08), 0.36, 0.02, 2.4, 3, rot=Matrix.Rotation(math.radians(90), 3, 'Y'), seg=16)
    else:
        _bm_cyl(bm, (L + 0.9, 0, 0.05), 0.42, 0.06, 2.4, 3, rot=Matrix.Rotation(math.radians(90), 3, 'Y'), seg=4)
        for dz in (-0.18, 0.0, 0.18):
            _bm_box(bm, (L + 1.4, 0, 0.05 + dz), (1.0, 0.5, 0.04), 3)
    _bm_cyl(bm, (L + 0.35, 0, 1.45), 0.14, 0.03, 0.8, 3, rot=Matrix.Rotation(math.radians(90), 3, 'Y'), seg=8)
    # (the stern aphlaston is built in the HERO DETAIL block below: a five-tipped fan)
    # stem post at the bow
    _bm_tube(bm, [(L - 0.2, 0, 2.3), (L + 0.1, 0, 2.7), (L + 0.05, 0, 3.0)], [0.14, 0.1, 0.06], 0, seg=8)
    # mast + yard (+ furled sail bundled on the yard) + rigging in thick laid rope
    mx = L * 0.55
    _bm_cyl(bm, (mx, 0, 6.7), 0.16, 0.11, 8.6, 6, seg=14)
    _bm_cyl(bm, (mx + 0.25, 0, 10.55), 0.13, 0.13, 10.2, 6, rot=Matrix.Rotation(math.radians(90), 3, 'X'), seg=12)
    if furled:
        _bm_cyl(bm, (mx + 0.25, 0, 10.32), 0.28, 0.28, 9.4, 8, rot=Matrix.Rotation(math.radians(90), 3, 'X'), seg=14)
    top = Vector((mx, 0, 11.0))
    rig = [[top, (L - 0.3, 0, 2.7)], [top, (L * 0.08, 0, 3.4)]]                  # forestay, backstay
    for sgn in (-1, 1):
        arm = Vector((mx + 0.25, sgn * 5.0, 10.55))
        rig += [[top, arm], [arm, (L * 0.18, sgn * 1.7, 3.0)], [top + Vector((0, 0, -0.4)), (mx - 0.8, sgn * 1.6, 2.5)]]
    for a_, b_ in rig:                                   # each rope sags a little between its ends
        a_, b_ = Vector(a_), Vector(b_)
        mid = a_.lerp(b_, 0.5) + Vector((0, 0, -0.02 * (b_ - a_).length))
        _bm_tube(bm, [a_, a_.lerp(mid, 0.5), mid, mid.lerp(b_, 0.5), b_], 0.022, 5, seg=6, caps=False)
    # ======== HERO DETAIL (owner 2026-11-20: build the ships majestically) ========
    for sgn in (-1, 1):
        # marble EYE PLATES on the bow (almond plates like the marble ophthalmoi found at Piraeus), painted iris
        p, _ = _tri_hull_pt(0.955, 1.2, sgn)
        R = Matrix.Rotation(math.radians(-sgn * 18), 3, 'Z') @ Matrix.Rotation(math.radians(90), 3, 'X')
        for r, d, mi, sc in ((0.36, 0.05, 12, (1.9, 1.0)), (0.17, 0.065, 13, (1.0, 1.0)), (0.08, 0.075, 14, (1.0, 1.0))):
            M = Matrix.Translation(p + Vector((0.05, sgn * d, 0))) @ R.to_4x4() @ Matrix.Diagonal((sc[0], sc[1], 1, 1))
            import bmesh as _bmesh
            res = _bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=r, radius2=r, depth=0.03, matrix=M)
            for f in {f for v in res['verts'] for f in v.link_faces}:
                f.material_index = mi
        # painted outrigger panel: a board under the top rail carrying a meander band (red / bone white)
        _bm_box(bm, (L * 0.515, sgn * 2.8, 2.08), (L * 0.63, 0.03, 0.16), 15)
        # rolled leather/canvas battle side-screens lashed along the deck rail
        _bm_tube(bm, [(L * 0.18, sgn * 1.72, 3.12), (L * 0.84, sgn * 1.72, 3.12)], 0.09, 17, seg=10)
        for k in range(9):                               # lashings round the roll
            x = L * 0.2 + (L * 0.62) * k / 8
            _bm_tube(bm, [(x, sgn * 1.62, 3.12), (x, sgn * 1.72, 3.22), (x, sgn * 1.82, 3.12)], 0.012, 5, seg=5, caps=False)
    # a taller, sweeping stern: five-tipped aphlaston fan rising to ~6.5 m
    for dy in (-0.34, -0.17, 0.0, 0.17, 0.34):
        pts = [(0.4, dy * 0.2, 2.9), (-0.9, dy * 0.45, 3.9), (-1.35, dy * 0.8, 5.0), (-1.0, dy * 1.15, 6.1), (-0.2, dy * 1.4, 6.55),
               (0.3, dy * 1.5, 6.3)]
        _bm_tube(bm, pts, [0.16, 0.14, 0.11, 0.08, 0.05, 0.03], 0, seg=8)
    # stolos: the stem rising and curving back above the ram (Athenian bows on the vase paintings)
    _bm_tube(bm, [(L - 0.1, 0, 2.4), (L + 0.25, 0, 3.0), (L + 0.2, 0, 3.6), (L - 0.15, 0, 3.95)], [0.16, 0.13, 0.09, 0.05], 0, seg=10)
    # stylis: the stern standard pole with its cross-bar (vase paintings / coins); pennants are separate objects
    _bm_cyl(bm, (L * 0.06, 0, 4.2), 0.035, 0.03, 2.6, 6, seg=8)
    _bm_cyl(bm, (L * 0.06, 0, 5.3), 0.025, 0.025, 1.0, 6, rot=Matrix.Rotation(math.radians(90), 3, 'X'), seg=6)
    # spare oars racked along the gangway + water jars by the mast
    for k in range(6):
        _bm_tube(bm, [(L * 0.3, -0.5 + k * 0.08, 2.5), (L * 0.3 + 4.2, -0.5 + k * 0.08, 2.5)], 0.04, 6, seg=6)
    for k in range(4):
        _bm_cyl(bm, (L * 0.58 + 0.45 * k, 0.9, 2.75), 0.17, 0.05, 0.7, 18, seg=14)
    # extra rigging: halyard + 10 brails over the yard and down to the deck, wooden blocks at the masthead
    _bm_cyl(bm, (mx, 0.18, 10.85), 0.07, 0.07, 0.06, 2, rot=Matrix.Rotation(math.radians(90), 3, 'X'), seg=10)
    _bm_cyl(bm, (mx, -0.18, 10.85), 0.07, 0.07, 0.06, 2, rot=Matrix.Rotation(math.radians(90), 3, 'X'), seg=10)
    _bm_tube(bm, [(mx, 0.18, 10.9), (mx + 0.2, 0.3, 10.6), (mx - 0.3, 0.4, 2.6)], 0.018, 5, seg=5, caps=False)
    if not furled:
        for k in range(10):
            yy = -4.3 + 8.6 * k / 9
            _bm_tube(bm, [(mx + 0.4, yy, 10.5), (mx + 0.8 + 1.1 * math.sin(math.pi * (k + 0.5) / 10), yy, 6.8),
                          (mx + 0.55, yy, 3.7), (mx - 0.3, yy * 0.25, 2.6)], 0.012, 5, seg=4, caps=False)
    if phoenician:                                       # high deck, bulwark and a rail of round shields
        x0, x1 = L * 0.16, L * 0.86
        _bm_box(bm, ((x0 + x1) / 2, 0, 2.95), (x1 - x0, 3.5, 0.08), 2)
        for sgn in (-1, 1):
            _bm_box(bm, ((x0 + x1) / 2, sgn * 1.76, 2.7), (x1 - x0, 0.06, 0.6), 0)
            _bm_box(bm, ((x0 + x1) / 2, sgn * 1.76, 3.42), (x1 - x0, 0.1, 0.06), 2)
            n = int((x1 - x0) / 0.95)
            for k in range(n):
                _bm_cyl(bm, (x0 + 0.5 + k * 0.95, sgn * 1.83, 3.12), 0.42, 0.42, 0.05, 9 + (k + (sgn > 0)) % 3,
                        rot=Matrix.Rotation(math.radians(90), 3, 'X'), seg=20)
        _bm_cyl(bm, (L - 0.45, 0, 2.72), 0.13, 0.09, 0.4, 3, seg=10)                 # pataikos
        _bm_cyl(bm, (L - 0.45, 0, 3.0), 0.1, 0.1, 0.2, 3, seg=10)
    fm = bpy.data.meshes.new(key + '_fittings'); bm.to_mesh(fm); bm.free()
    for m in mats:
        fm.materials.append(m)
    fit = bpy.data.objects.new(key + '_fittings', fm); col.objects.link(fit)
    bv = fit.modifiers.new('bevel', 'BEVEL'); bv.width = 0.015; bv.segments = 1; bv.limit_method = 'ANGLE'
    # pennants: a long streamer from the masthead and two ribbons from the stylis, rippling in the wind
    for nm, base, ln, wd in (('streamer', Vector((mx, 0, 11.25)), 4.5, 0.45), ('stylis_a', Vector((L * 0.06, 0.45, 5.3)), 1.6, 0.22),
                             ('stylis_b', Vector((L * 0.06, -0.45, 5.3)), 1.6, 0.22)):
        verts, faces = [], []
        n = 24
        for i in range(n + 1):
            t = i / n
            w = wd * (1 - 0.75 * t)                       # tapers to a swallow-tail point
            verts += [(base.x - t * ln, base.y, base.z - 0.15 * t), (base.x - t * ln, base.y, base.z - w - 0.15 * t)]
        for i in range(n):
            a = 2 * i
            faces.append((a, a + 2, a + 3, a + 1))
        pm = bpy.data.meshes.new(f'{key}_{nm}'); pm.from_pydata(verts, [], faces); pm.update(); pm.materials.append(mats[16])
        po = bpy.data.objects.new(f'{key}_{nm}', pm); col.objects.link(po)
        sub = po.modifiers.new('sub', 'SUBSURF'); sub.levels = 1
        w_ = po.modifiers.new('wind', 'WAVE'); w_.use_normal = False; w_.use_x = False; w_.use_y = True
        w_.height = 0.12; w_.width = 0.9; w_.speed = 0.12; w_.start_position_x = base.x; w_.start_position_y = base.y
        po.modifiers.new('thick', 'SOLIDIFY').thickness = 0.006
    return col


def trireme_sail_mesh(name='tri4_sail', W=10.2, Ht=7.0, belly=1.45, folds=10):
    """The set square sail as real cloth shape: bellied by a following wind, the foot sagging between the sheets,
    and soft vertical FOLDS between the brail lines (the ropes that gather a Greek sail up like a blind)."""
    me = bpy.data.meshes.get(name)
    if me:
        return me
    nu, nv = 48, 30
    verts, faces = [], []
    for i in range(nu + 1):
        for j in range(nv + 1):
            u, v = i / nu, j / nv
            y = (u - 0.5) * W
            z = -v * Ht + 0.35 * math.sin(math.pi * u) * v ** 3            # the foot sags in the middle
            x = belly * math.sin(math.pi * u) * math.sin(math.pi * (0.12 + 0.88 * v)) ** 0.8
            x += 0.09 * math.sin(u * math.pi * 2 * folds) * (0.25 + 0.75 * v)  # folds between the brails, deeper below
            x += 0.03 * math.sin(v * math.pi * 9 + u * 3)                     # slight horizontal ripples from the seams
            verts.append((x, y, z))
    for i in range(nu):
        for j in range(nv):
            a = i * (nv + 1) + j
            faces.append((a, a + 1, a + nv + 2, a + nv + 1))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    for p_ in me.polygons:
        p_.use_smooth = True
    uv = me.uv_layers.new(name='UVMap')
    for p_ in me.polygons:
        for li, vi in zip(p_.loop_indices, p_.vertices):
            i, j = divmod(vi, nv + 1)
            uv.data[li].uv = (i / nu, 1 - j / nv)
    return me


def trireme_sail_cloth(name='tri5_sail_cloth', W=10.2, Ht=7.0, frames=45, wind=9.0, res=(44, 32)):
    """The SET SAIL as REAL CLOTH: a Blender cloth simulation, run once and frozen (cached per Blender session).
      - pinned along the whole top edge (laced to the yard) and at the two bottom corners (the sheets);
      - the sewn reinforcing strips and brail lines (the grid on Greek sails in vase paintings) are STIFFER than
        the linen between them, so each panel puffs out on its own - that is what gives a sail real volume;
      - a wind force from astern (+X) fills it; gravity makes the foot sag.
    Mesh coordinates match trireme_sail_mesh(): x forward (belly), y across, z from 0 (yard) down to -Ht."""
    me = bpy.data.meshes.get(name)
    if me:
        return me
    nu, nv = res
    verts, faces = [], []
    for i in range(nu + 1):
        for j in range(nv + 1):
            u, v = i / nu, j / nv
            # start slightly bellied so the solver settles faster and never folds backwards
            verts.append((0.25 * math.sin(math.pi * u) * math.sin(math.pi * v), (u - 0.5) * W, -v * Ht))
    for i in range(nu):
        for j in range(nv):
            a = i * (nv + 1) + j
            faces.append((a, a + 1, a + nv + 2, a + nv + 1))
    tmp_me = bpy.data.meshes.new(name + '_sim'); tmp_me.from_pydata(verts, [], faces); tmp_me.update()
    ob = bpy.data.objects.new(name + '_sim', tmp_me); bpy.context.scene.collection.objects.link(ob)
    pin = ob.vertex_groups.new(name='pin')
    seams = ob.vertex_groups.new(name='seams')
    for i in range(nu + 1):
        for j in range(nv + 1):
            idx = i * (nv + 1) + j
            if j == 0 or (j == nv and i in (0, nu)):
                pin.add([idx], 1.0, 'REPLACE')                   # yard + sheet corners
            if i % (nu // 11) == 0 or j % (nv // 8) == 0:
                seams.add([idx], 1.0, 'REPLACE')                 # brail lines + sewn strips
    cl = ob.modifiers.new('cloth', 'CLOTH'); st = cl.settings
    st.quality = 6; st.mass = 0.25; st.air_damping = 0.6
    st.tension_stiffness = 25; st.compression_stiffness = 25; st.shear_stiffness = 8; st.bending_stiffness = 0.3
    st.vertex_group_mass = 'pin'
    try:                                                          # stiffer seams (Blender 2.9+ 'shrink'/'structural' groups)
        st.vertex_group_structural_stiffness = 'seams'; st.tension_stiffness_max = 80; st.compression_stiffness_max = 80
        st.vertex_group_bending = 'seams'; st.bending_stiffness_max = 4.0
    except Exception:
        pass
    cl.point_cache.frame_start = 1; cl.point_cache.frame_end = frames
    # the wind: a force field from astern with a little turbulence
    bpy.ops.object.effector_add(type='WIND', location=(-6.0, 0, -Ht / 2), rotation=(0, math.radians(90), 0))
    wf = bpy.context.object; wf.name = name + '_wind'
    wf.field.strength = wind; wf.field.noise = 0.6; wf.field.flow = 0.3
    sc = bpy.context.scene
    keep = sc.frame_current
    for f in range(1, frames + 1):                                # step the solver frame by frame
        sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))   # freeze the settled shape
    me.name = name
    for p_ in me.polygons:
        p_.use_smooth = True
    uv = me.uv_layers.new(name='UVMap')
    for p_ in me.polygons:
        for li, vi in zip(p_.loop_indices, p_.vertices):
            i, j = divmod(vi, nv + 1)
            uv.data[li].uv = (i / nu, 1 - j / nv)
    sc.frame_set(keep)
    bpy.data.objects.remove(wf, do_unlink=True); bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(tmp_me)
    return me


def _sail_material(name='tri4_sail_linen'):
    """Undyed linen sail with sewn horizontal strips and vertical brail lines (vase paintings show this grid)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = wool(name, (0.74, 0.66, 0.52), tile=1.0)
    nt = m.node_tree; L = nt.links.new
    tint = nt.nodes['tint']
    uvn = nt.nodes.new('ShaderNodeUVMap'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(uvn.outputs['UV'], sep.inputs['Vector'])
    out = None
    for axis, count, width in ((0, 13, 0.06), (1, 8, 0.05)):            # 13 brail lines, 8 seams
        mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = count
        L(sep.outputs[axis], mul.inputs[0])
        fr = nt.nodes.new('ShaderNodeMath'); fr.operation = 'FRACT'; L(mul.outputs[0], fr.inputs[0])
        lt = nt.nodes.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = width
        L(fr.outputs[0], lt.inputs[0])
        if out is None:
            out = lt
        else:
            mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'; L(out.outputs[0], mx.inputs[0]); L(lt.outputs[0], mx.inputs[1]); out = mx
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    mix.inputs['A'].default_value = (0.70, 0.63, 0.50, 1); mix.inputs['B'].default_value = (0.36, 0.28, 0.18, 1)
    L(out.outputs[0], mix.inputs['Factor']); L(mix.outputs['Result'], tint.inputs['B'])
    b = nt.nodes['Principled BSDF']
    if 'Subsurface Weight' in b.inputs:                # thin linen lets a little sun through (backlit sails glow)
        b.inputs['Subsurface Weight'].default_value = 0.15
    return m


def _ship_foam(root, name, speed_mps, L=_TRI_L):
    """Bow wave (foam strips peeling off the bow along the hull) + the wake (a widening, fading foam path behind
    the stern, longer at higher speed). Flat meshes lying on the water (z ~ 0.03), moving with the ship."""
    foam = foam_material('ship_foam', density=0.5, scale=3.0)
    k = min(1.5, speed_mps / 4.0)
    for sgn in (-1, 1):                              # bow wave: hugs the hull from the bow back ~40 %
        verts, faces = [], []
        n = 20
        for i in range(n + 1):
            t = 1.0 - 0.4 * i / n
            p, _ = _tri_hull_pt(t, 0.0, sgn)
            w = (0.15 + 1.4 * (i / n)) * k
            verts += [(p.x, p.y + sgn * 0.02, 0.03), (p.x - 0.3 * i / n, p.y + sgn * (0.02 + w), 0.03)]
        for i in range(n):
            a = 2 * i
            faces.append((a, a + 2, a + 3, a + 1) if sgn > 0 else (a, a + 1, a + 3, a + 2))
        o = mesh_obj(f'{name}_bowwave', verts, faces, foam); o.parent = root
    verts, faces = [], []                            # wake: from the stern (x = 0) backward, widening
    n = 30; ln = 40.0 * k
    for i in range(n + 1):
        t = i / n
        w = 1.6 + 7.0 * t * k
        verts += [(t * ln, -w, 0.025), (t * ln, w, 0.025)]   # built along +X so Generated X = 0 at the stern
    for i in range(n):
        a = 2 * i
        faces.append((a, a + 1, a + 3, a + 2))
    me = bpy.data.meshes.new(f'{name}_wake'); me.from_pydata(verts, [], faces); me.update()
    me.materials.append(foam_material('wake_foam', density=0.4, scale=1.5, fade=True))
    o = bpy.data.objects.new(f'{name}_wake', me); link(o); o.parent = root
    o.rotation_euler.z = math.pi                     # ...then turned to trail behind the stern (-X)


def trireme_v3(loc=(0, 0, 0), heading_deg=0.0, oars='row', stroke_frames=34, frame_start=1, frame_end=240,
               sail=None, crew='markers', marines=14, speed_mps=0.0, bob=True, phoenician=False, seed=0,
               wind=True, cloth=True, name='trireme3'):
    """TRIREME v3 - same options as trireme_v2 (oars 'row' | 'rest' | None, sail 'set' | None, crew 'markers' |
    'proxies' | None, speed_mps, bob, phoenician) but with the DETAILED hull and fittings, and FAST: the static ship is
    an instance of a cached kit, so the 2nd..100th ship costs seconds. wind=True ripples the set sail (Wave modifier)."""
    rnd = _random.Random(seed)
    kit = _trireme_kit(phoenician, furled=(sail != 'set'))
    root = bpy.data.objects.new(name, None); link(root)
    root['ws7_prop'] = 'trireme_v3'
    inst = bpy.data.objects.new(name + '_ship', None); link(inst)
    inst.instance_type = 'COLLECTION'; inst.instance_collection = kit; inst.parent = root
    oarm = old_wood('tri3_oarwood', (0.40, 0.29, 0.17))
    _ship_oars(root, name, oars, oarm, rnd, stroke_frames, frame_start, _TRI_L, splash=(oars == 'row'),
               rowers=(oars == 'row' and crew == 'proxies'))
    if speed_mps > 0.5:                              # under way: bow wave + a wake trailing behind, fading out
        _ship_foam(root, name, speed_mps)
    if sail == 'set':
        sail_me = trireme_sail_cloth() if cloth else trireme_sail_mesh()     # cloth=True: real simulated linen
        s = bpy.data.objects.new(name + '_sail', sail_me); link(s)
        if not s.data.materials:
            s.data.materials.append(_sail_material())
        s.parent = root; s.location = (_TRI_L * 0.55 + 0.35, 0, 10.45)
        if wind:                                      # the cloth breathes: slow ripples running across the sail
            w = s.modifiers.new('wind', 'WAVE'); w.use_normal = True; w.use_x = w.use_y = False
            w.height = 0.06; w.width = 2.2; w.narrowness = 1.0; w.speed = 0.04; w.time_offset = rnd.uniform(0, 40)
        s.modifiers.new('thick', 'SOLIDIFY').thickness = 0.008
    _ship_crew(root, name, crew, rnd, _TRI_L, 2.99 if phoenician else 2.42, phoenician, marines)
    _ship_motion(root, loc, heading_deg, speed_mps, bob, frame_start, frame_end)
    return root


def fleet(centre, count=12, spread=(220.0, 120.0), heading_deg=0.0, phoenician_share=0.0, oars='rest', sail=None,
          speed_mps=0.0, seed=0, far=150.0, camera=None, name='fleet'):
    """A FLEET of v3 triremes in loose lines (ancient fleets sailed in column and deployed in line abreast,
    Herodotus 8.83-86). Ships farther than `far` metres from `camera` get NO separate oars or crew (the kit only:
    one object each), so 100+ ships stay light. phoenician_share = fraction of Phoenician ships (Xerxes' fleet)."""
    rnd = _random.Random(seed)
    out = []
    rows = max(1, int(math.sqrt(count * spread[1] / max(spread[0], 1))))
    per = math.ceil(count / rows)
    h = math.radians(heading_deg)
    fwd, side = Vector((math.cos(h), math.sin(h), 0)), Vector((-math.sin(h), math.cos(h), 0))
    for i in range(count):
        r, c = divmod(i, per)
        off = side * ((c - (per - 1) / 2) * spread[0] / max(per, 1) + rnd.uniform(-6, 6)) \
            + fwd * (-(r * spread[1] / max(rows, 1)) + rnd.uniform(-10, 10))
        p = Vector(centre) + off
        near = camera is None or (Vector(camera) - p).length < far
        ph = rnd.random() < phoenician_share
        out.append(trireme_v3(tuple(p), heading_deg + rnd.uniform(-6, 6), oars=oars if near else None,
                              sail=sail, crew='proxies' if near else None, speed_mps=speed_mps, phoenician=ph,
                              seed=seed * 100 + i, frame_start=1 + rnd.randint(0, 8), name=f'{name}_{i:03d}'))
    return out


# ------------------------------------------------------------------ STORY PROPS (the 5 Salamis Shorts)
def sea_bronze(name='sea_bronze'):
    """Bronze after 2,000 years under the sea: dark brown metal under mottled green-blue corrosion, a few rubbed
    golden highlights on the edges (how the Athlit ram looks in the Haifa museum)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = principled(name, (0.25, 0.16, 0.08), metal=0.85, rough=0.45)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 22.0; n.inputs['Detail'].default_value = 12
    n.inputs['Roughness'].default_value = 0.7       # fine pitting, not big camouflage blotches
    mk = nt.nodes.new('ShaderNodeMapRange'); mk.inputs['From Min'].default_value = 0.38; mk.inputs['From Max'].default_value = 0.78
    L(n.outputs['Fac'], mk.inputs['Value'])
    col = nt.nodes.new('ShaderNodeMix'); col.data_type = 'RGBA'
    col.inputs['A'].default_value = (0.16, 0.09, 0.045, 1); col.inputs['B'].default_value = (0.05, 0.1, 0.08, 1)   # dark bronze / deep verdigris  # bronze / verdigris
    L(mk.outputs['Result'], col.inputs['Factor']); L(_age(m, col.outputs['Result'], 0.12, 0.5, 0.05), b.inputs['Base Color'])
    inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 0.85
    L(mk.outputs['Result'], inv.inputs[1]); L(inv.outputs[0], b.inputs['Metallic'])                         # corrosion is not metal
    rr = nt.nodes.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = 0.35; rr.inputs['To Max'].default_value = 0.85
    L(mk.outputs['Result'], rr.inputs['Value']); L(rr.outputs['Result'], b.inputs['Roughness'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.4
    L(n.outputs['Fac'], bp.inputs['Height']); L(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def ram_athlit(loc=(0, 0, 0), heading_deg=0.0, plinth=True, corroded=True, name='athlit_ram'):
    """The ATHLIT RAM (found off Athlit, Israel, 1980; Hellenistic, c. 200 BC; Haifa Maritime Museum): ONE casting of
    bronze, 465 kg, 2.26 m long, 0.95 m high, 0.76 m wide. A hollow sheath fitted over the bow timbers: a trough-like
    body that narrows forward, a raised cowl on top, flaring side wings, and at the front the 'driving centre' with
    THREE horizontal fins and a vertical plate that split enemy planks. (Its relief emblems - helmets, eagle,
    thunderbolt - are left out on purpose: the Short shows its shape and size.) Tip points to +X.
    corroded=True: as it came out of the sea; False: freshly cast golden bronze (how Salamis rams looked)."""
    import bmesh
    root = _root(name)
    mat = sea_bronze() if corroded else (bpy.data.materials.get('bronze') or aged_bronze('bronze'))
    bm = bmesh.new()
    Lr = 2.26
    secs = 24
    ring_n = 28
    rings = []
    for i in range(secs + 1):
        t = i / secs                                     # 0 = rear opening .. 1 = front of the body
        x = -Lr + 0.55 + t * (Lr - 0.55)                 # body from x = -1.71 (rear) to 0 (base of the fins)
        w = 0.38 * (1 - 0.3 * t ** 1.2)                  # half-width: 0.38 at the back -> ~0.27 at the front
        h = 0.95 * (1 - 0.45 * t ** 1.1)                 # height: 0.95 m at the back -> ~0.52 m at the front
        cowl = 0.12 * (1 - t) ** 0.7                     # raised ridge on top
        pts = []
        for k in range(ring_n):                          # section: a ROUNDED RECTANGLE (flat sides + flat bottom, the
            a = 2 * math.pi * k / ring_n                 # sheath of the bow timbers) with the cowl ridge on top
            ca, sa = math.cos(a), math.sin(a)
            yy = math.copysign(abs(sa) ** 0.35, sa)      # superellipse: |.|^0.35 squares the circle off
            zz = -math.copysign(abs(ca) ** 0.35, ca)
            z = (zz * 0.5 + 0.5) * h + cowl * max(0.0, zz) ** 8
            pts.append(bm.verts.new((x, yy * w, z - h * 0.3)))
        rings.append(pts)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(ring_n):
            f = bm.faces.new((r0[k], r0[(k + 1) % ring_n], r1[(k + 1) % ring_n], r1[k])); f.smooth = True
    bm.faces.new(rings[-1][::-1])                        # the front face (the fins grow out of it)
    # the driving centre: three horizontal fins + a vertical plate, ~0.55 m forward of the body
    zc = rings[-1][0].co.z + 0.95 * 0.35 * 0.5
    for f in bm.faces:                                   # the body is smooth-shaded; the blades below stay flat + crisp
        f.smooth = True
    for dz in (-0.17, 0.0, 0.17):                        # three horizontal blades, as wide as the front of the body
        _bm_box(bm, (0.28, 0, zc + dz), (0.6, 0.56 - abs(dz) * 0.4, 0.05), 0)
    _bm_box(bm, (0.25, 0, zc), (0.55, 0.06, 0.46), 0)    # the vertical plate tying them together
    for sgn in (-1, 1):                                  # the long side wings (fluted flanges) sweeping back
        _bm_tube(bm, [(0.05, sgn * 0.12, zc + 0.08), (-0.6, sgn * 0.3, zc + 0.18), (-1.6, sgn * 0.42, zc + 0.32)],
                 [0.03, 0.04, 0.05], 0, seg=8)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name + '_bronze', me); link(o); o.parent = root
    o.modifiers.new('thick', 'SOLIDIFY').thickness = 0.03          # a 3 cm thick hollow casting
    bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = 0.012; bv.segments = 2; bv.limit_method = 'ANGLE'   # crisp blades
    zmin = min(v.co.z for v in me.vertices)
    o.location.z = -zmin + (0.45 if plinth else 0.0)
    if plinth:                                           # museum display plinth (dark stone)
        _box(f'{name}_plinth', (-0.75, 0, 0.22), (2.0, 0.95, 0.44), principled(f'{name}_stone', (0.05, 0.05, 0.055), rough=0.7),
             bevel=0.02, parent=root)
    return _place(root, loc, heading_deg)


def wreck_debris(centre=(0, 0, 0), radius=12.0, count=40, frames=(1, 240), seed=0, name='debris'):
    """After a ramming: smashed planks, snapped oars, floating shields, a broken spar, rope and an amphora, spread on
    the water and bobbing on the swell (keyframed, looping). z = 0 is the sea surface."""
    rnd = _random.Random(seed)
    root = _root(name)
    root.location = (centre[0], centre[1], centre[2] + 0.12)   # ride ON the swell (waves are ~±0.1 m), not under it
    wood = old_wood('debris_wood', (0.22, 0.15, 0.09))
    pitch = scan_surface('tri3_pitch', 'brown_planks_04', (0.016, 0.014, 0.012), tile=1.5, rough=(0.3, 0.65), normal=0.9, keep_hue=True)
    oarw = old_wood('tri3_oarwood', (0.40, 0.29, 0.17))
    smats = [bpy.data.materials.get('bronze') or aged_bronze('bronze'), principled('debris_shield_red', (0.3, 0.06, 0.04), rough=0.7)]
    for i in range(count):
        a = rnd.uniform(0, 2 * math.pi); r = radius * math.sqrt(rnd.random())
        p = (r * math.cos(a), r * math.sin(a), 0.0)
        kind = rnd.random()
        if kind < 0.45:                                  # hull planks, black outside, raw wood where they broke
            o = _box(f'{name}_plank', p, (rnd.uniform(0.8, 3.0), rnd.uniform(0.18, 0.35), 0.08), rnd.choice((pitch, wood)), parent=root)
        elif kind < 0.75:                                # snapped oar
            ln = rnd.uniform(1.0, 3.5)
            o = _cyl(f'{name}_oar', p, 0.04, ln, oarw, rot=(0, math.radians(90), 0), verts=8, parent=root)
        elif kind < 0.88:                                # a hoplite shield floating face-down
            o = _cyl(f'{name}_shield', p, 0.45, 0.06, rnd.choice(smats), verts=24, parent=root)
        elif kind < 0.95:
            o = _cyl(f'{name}_spar', p, 0.1, rnd.uniform(3, 6), wood, rot=(0, math.radians(90), 0), verts=10, parent=root)
        else:
            o = _tube(f'{name}_rope', [(p[0] + 0.4 * math.cos(k), p[1] + 0.4 * math.sin(k * 1.3), 0.02) for k in range(8)],
                      0.015, rope_fibre(), root)
        o.rotation_euler.z = rnd.uniform(0, 6.28)
        if o.type == 'MESH':                             # bob and roll a little on the swell, each with its own rhythm
            per = rnd.uniform(60, 110); ph = rnd.uniform(0, per)
            for k in range(5):
                f = frames[0] + ph + k * per / 4
                o.location.z = 0.03 * math.sin(k * math.pi / 2)
                o.rotation_euler.x = 0.06 * math.cos(k * math.pi / 2)
                o.keyframe_insert('location', index=2, frame=f); o.keyframe_insert('rotation_euler', index=0, frame=f)
            _loop(o)
    return root


def tripod_cauldron(loc=(0, 0, 0), heading_deg=0.0, height=1.6, seat=False, name='tripod'):
    """Bronze TRIPOD-CAULDRON (lebes on three tall legs with two ring handles on the rim): the great offering of the
    Greek sanctuaries (Delphi, Olympia), and the seat of the Pythia when seat=True (a lid she sits on, as on the
    Kodros Painter cup, c. 440 BC)."""
    root = _root(name)
    br = bpy.data.materials.get('bronze') or aged_bronze('bronze')
    rim = height * 0.72
    for k in range(3):
        a = 2 * math.pi * k / 3
        _tube(f'{name}_leg', [(0.33 * math.cos(a), 0.33 * math.sin(a), rim - 0.05), (0.36 * math.cos(a), 0.36 * math.sin(a), rim * 0.5),
                              (0.42 * math.cos(a), 0.42 * math.sin(a), 0.04)], 0.028, br, root, taper_end=1.5)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.05, location=(0.42 * math.cos(a), 0.42 * math.sin(a), 0.04))
        ft = bpy.context.object; ft.name = f'{name}_foot'; ft.scale = (1, 1, 0.6); ft.data.materials.append(br); ft.parent = root
    _lathe(f'{name}_lebes', [(rim - 0.32, 0.0), (rim - 0.3, 0.18), (rim - 0.18, 0.33), (rim - 0.05, 0.37), (rim, 0.36)], br,
           seg=48, parent=root, thick=0.008, smooth=2)
    for sgn in (-1, 1):                                  # two big ring handles standing on the rim
        bpy.ops.mesh.primitive_torus_add(major_radius=0.17, minor_radius=0.018, location=(0, sgn * 0.33, rim + 0.17),
                                         rotation=(0, 0, 0))
        t = bpy.context.object; t.name = f'{name}_handle'; t.rotation_euler = (math.radians(90), 0, 0)   # ring plane along the rim
        t.data.materials.append(br); t.parent = root
    if seat:
        _cyl(f'{name}_lid', (0, 0, rim + 0.01), 0.36, 0.03, br, verts=40, parent=root)
    return _place(root, loc, heading_deg)


def omphalos(loc=(0, 0, 0), heading_deg=0.0, height=1.0, name='omphalos'):
    """The OMPHALOS of Delphi, the 'navel of the world': an egg-shaped stone wrapped in a net of woollen fillets
    (the agrenon), carved in relief on the marble copy in the Delphi museum."""
    root = _root(name)
    m = principled(f'{name}_stone', (0.34, 0.31, 0.26), rough=0.7)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    tc = nt.nodes.new('ShaderNodeTexCoord')
    net = None
    for rot in (0.75, -0.75):                            # two crossing sets of diagonal bands = the knotted net
        mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, rot, 0)
        L(tc.outputs['Object'], mp.inputs['Vector'])
        w = nt.nodes.new('ShaderNodeTexWave'); w.inputs['Scale'].default_value = 3.0 / height; w.wave_profile = 'SIN'
        L(mp.outputs['Vector'], w.inputs['Vector'])
        if net is None:
            net = w
        else:
            mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'; L(net.outputs['Fac'], mx.inputs[0]); L(w.outputs['Fac'], mx.inputs[1])
            net = mx
    sock = net.outputs[0]
    sharp = nt.nodes.new('ShaderNodeMapRange'); sharp.inputs['From Min'].default_value = 0.8; sharp.inputs['From Max'].default_value = 0.95
    L(sock, sharp.inputs['Value'])                       # thin raised cords where the bands cross the stone
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 1.0; bp.inputs['Distance'].default_value = 0.02
    L(sharp.outputs['Result'], bp.inputs['Height']); L(bp.outputs['Normal'], b.inputs['Normal'])
    col = nt.nodes.new('ShaderNodeMix'); col.data_type = 'RGBA'
    col.inputs['A'].default_value = (0.34, 0.31, 0.26, 1); col.inputs['B'].default_value = (0.62, 0.58, 0.5, 1)
    L(sharp.outputs['Result'], col.inputs['Factor']); L(col.outputs['Result'], b.inputs['Base Color'])
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=0.5)
    o = bpy.context.object; o.name = f'{name}_stone'
    for v in o.data.vertices:                            # egg: flat base, fuller below, rounded dome above
        z = v.co.z
        if z < -0.3:
            v.co.z = -0.3
        v.co.x *= 1 - 0.12 * max(0.0, z) ; v.co.y *= 1 - 0.12 * max(0.0, z)
    o.data.transform(Matrix.Diagonal((height * 0.85, height * 0.85, height * 1.25, 1.0)))
    o.location.z = 0.3 * height * 1.25
    o.data.materials.append(m); o.parent = root
    for p_ in o.data.polygons:
        p_.use_smooth = True
    return _place(root, loc, heading_deg)


def suppliant_branch(loc=(0, 0, 0), heading_deg=0.0, length=0.8, leaves=55, seed=0, name='hiketeria'):
    """Suppliant's OLIVE BRANCH wound with white wool fillets (hiketeria) - what the Athenian envoys carried when they
    went back to Delphi (Herodotus 7.141). Narrow olive leaves, dark green above, silver below. Hold it at +Z."""
    import bmesh
    rnd = _random.Random(seed)
    root = _root(name)
    bark = old_wood('olive_bark', (0.18, 0.14, 0.1), grain=3)
    leaf = principled('olive_leaf', (0.10, 0.13, 0.06), rough=0.55, sss=0.1)
    leaf_b = principled('olive_leaf_under', (0.42, 0.45, 0.38), rough=0.6)
    wool_m = wool('fillet_wool', (0.82, 0.79, 0.72), tile=0.05)
    stem = [(0, 0, 0), (0.02, 0.0, length * 0.35), (-0.03, 0.01, length * 0.7), (0.0, 0.03, length)]
    _tube(f'{name}_stem', stem, 0.008, bark, root, taper_end=0.3)
    bm = bmesh.new()
    for i in range(leaves):
        t = 0.25 + 0.75 * rnd.random()
        base = Vector((0.0, 0.0, t * length)) + Vector((rnd.uniform(-0.02, 0.02), rnd.uniform(-0.02, 0.02), 0))
        a = rnd.uniform(0, 2 * math.pi); up = rnd.uniform(0.3, 0.9)
        d = Vector((math.cos(a), math.sin(a), up)).normalized()
        side = d.cross(Vector((0, 0, 1))).normalized() * 0.006
        ln = rnd.uniform(0.04, 0.07)                       # olive leaves: 4-7 cm long, ~1 cm wide
        v = [bm.verts.new(base), bm.verts.new(base + d * ln * 0.5 + side), bm.verts.new(base + d * ln),
             bm.verts.new(base + d * ln * 0.5 - side)]
        f = bm.faces.new(v); f.material_index = 0 if rnd.random() < 0.6 else 1
    me = bpy.data.meshes.new(f'{name}_leaves'); bm.to_mesh(me); bm.free()
    me.materials.append(leaf); me.materials.append(leaf_b)
    lv = bpy.data.objects.new(f'{name}_leaves', me); link(lv); lv.parent = root
    lv.modifiers.new('thick', 'SOLIDIFY').thickness = 0.0008
    for k in range(3):                                   # wool fillets tied round the branch, ends hanging
        z = length * (0.2 + 0.12 * k)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.014, minor_radius=0.006, location=(0, 0, z))
        t = bpy.context.object; t.name = f'{name}_fillet'; t.data.materials.append(wool_m); t.parent = root
        _tube(f'{name}_fillet_end', [(0.012, 0, z), (0.03, 0.01, z - 0.08), (0.025, 0.02, z - 0.16)], 0.004, wool_m, root)
    return _place(root, loc, heading_deg)


def timber_barricade(loc=(0, 0, 0), heading_deg=0.0, length=12.0, height=2.2, burning=False, frames=(1, 240), seed=0,
                     name='wooden_wall'):
    """The Acropolis barricade of 480 BC: 'a wall of planks and timber' (Herodotus 8.51-52) that temple stewards and
    poor men built at the entrance, believing it was the oracle's wooden wall. Rough posts dug in at an angle,
    planks and doors nailed across them at different heights, beams propping it from behind, gaps.
    burning=True: flame tongues along it and a flickering fire light (the Persians shot burning arrows into it)."""
    rnd = _random.Random(seed)
    root = _root(name)
    wood = scan_surface('barricade_wood', 'brown_planks_04', (0.25, 0.18, 0.12), tile=1.6, rough=(0.6, 0.95), normal=1.0,
                        keep_hue=True, age=(0.25, 0.6))
    charred = principled('charred_wood', (0.015, 0.012, 0.01), rough=0.95, bump=0.6, bump_scale=40)
    x = -length / 2
    while x <= length / 2:                               # posts every ~1.2 m, leaning a little
        h = height * rnd.uniform(0.9, 1.15)
        p = _box(f'{name}_post', (x, 0, h / 2 - 0.2), (0.16, 0.16, h), wood, bevel=0.01, parent=root)
        p.rotation_euler = (rnd.uniform(-0.06, 0.06), rnd.uniform(-0.05, 0.05), rnd.uniform(-0.1, 0.1))
        _box(f'{name}_prop', (x, 0.7, h * 0.35), (0.12, 0.12, h * 0.9), wood, bevel=0.01, parent=root).rotation_euler.x = math.radians(-38)
        x += rnd.uniform(1.0, 1.4)
    z = 0.15
    while z < height:                                    # planks and old doors across, uneven, some gaps
        x = -length / 2
        while x < length / 2:
            ln = rnd.uniform(1.2, 3.2); hh = rnd.uniform(0.18, 0.32)
            if rnd.random() > 0.12:
                pl = _box(f'{name}_plank', (x + ln / 2, -0.11, z + hh / 2), (ln, 0.05, hh * 0.95),
                          charred if burning and rnd.random() < 0.35 else wood, bevel=0.006, parent=root)
                pl.rotation_euler.y = rnd.uniform(-0.05, 0.05)
            x += ln + rnd.uniform(-0.1, 0.05)
        z += rnd.uniform(0.2, 0.34)
    if burning:
        for i in range(int(length / 0.7)):          # overlapping fires every ~0.7 m: the whole wall is alight
            fx_ = -length / 2 + (i + rnd.random()) * 0.7
            for layer in range(2):                   # low fire along the planks + taller tongues climbing above
                z0 = rnd.uniform(0.0, height * 0.5) if layer == 0 else rnd.uniform(height * 0.4, height * 0.9)
                flame_tongues(root, (fx_, -0.18, z0), height=rnd.uniform(1.0, 2.2) * (1.3 if layer else 1.0),
                              width=rnd.uniform(0.6, 1.0), n=6, frames=frames, seed=seed + i * 7 + layer,
                              name=f'{name}_fire{i}_{layer}', strength=3.5)
        ember = ember_glow('barricade_embers', strength=1.2, temp=1050.0, cracks=0.62)   # glow only deep in the cracks
        for o in root.children:                      # charred planks glow in their cracks
            if o.type == 'MESH' and o.data.materials and o.data.materials[0] == charred:
                o.data.materials[0] = ember
        from lib import fx
        sm = fx.smoke_column((0, 0, 0), height=40.0, width=length * 0.6, density=0.05, frames=frames, name=f'{name}_smoke')
        sm.parent = root; sm.location = (0, 1.0, height + 20.0)
        for k, xk in enumerate((-length / 3, 0, length / 3)):
            _flicker_light((xk, -1.2, height * 0.7), 1500.0, root, f'{name}_firelight{k}', frames, seed + k, radius=1.5,
                           color=(1.0, 0.55, 0.25))
    return _place(root, loc, heading_deg)


def scribe_kit(loc=(0, 0, 0), heading_deg=0.0, persian=True, name='scribe_kit'):
    """What the king's secretaries wrote with (Plutarch: Xerxes had secretaries beside him at Salamis; Herodotus 8.90:
    they wrote down the captains' names). Achaemenid scribes wrote Aramaic in ink on LEATHER scrolls (the Arsames
    letters) - persian=True: a leather scroll half unrolled with lines of ink, a stone ink pot, reed pens.
    persian=False: the Greek WAX TABLET (a hinged wooden diptych with black wax, writing scratched with a bronze
    stylus) - the kind Demaratus used to send his hidden warning (Herodotus 7.239)."""
    root = _root(name)
    ink = principled('scribe_ink', (0.01, 0.01, 0.012), rough=0.3)
    if persian:
        hide = principled('scroll_leather', (0.55, 0.42, 0.28), rough=0.8, bump=0.2, bump_scale=200)
        nt = hide.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
        tc = nt.nodes.new('ShaderNodeTexCoord')
        # 'writing': rows ~9 mm apart (fract of y), each row broken into letter-sized marks by fine noise
        sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(tc.outputs['Object'], sep.inputs['Vector'])
        ry = nt.nodes.new('ShaderNodeMath'); ry.operation = 'MULTIPLY'; ry.inputs[1].default_value = 110.0; L(sep.outputs['Y'], ry.inputs[0])
        fr = nt.nodes.new('ShaderNodeMath'); fr.operation = 'FRACT'; L(ry.outputs[0], fr.inputs[0])
        row = nt.nodes.new('ShaderNodeMath'); row.operation = 'LESS_THAN'; row.inputs[1].default_value = 0.32; L(fr.outputs[0], row.inputs[0])
        nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 420.0; nz.inputs['Detail'].default_value = 1
        L(tc.outputs['Object'], nz.inputs['Vector'])
        ch = nt.nodes.new('ShaderNodeMath'); ch.operation = 'GREATER_THAN'; ch.inputs[1].default_value = 0.5; L(nz.outputs['Fac'], ch.inputs[0])
        th = nt.nodes.new('ShaderNodeMath'); th.operation = 'MULTIPLY'; L(row.outputs[0], th.inputs[0]); L(ch.outputs[0], th.inputs[1])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
        mx.inputs['A'].default_value = (0.55, 0.42, 0.28, 1); mx.inputs['B'].default_value = (0.04, 0.03, 0.03, 1)  # lines of ink
        L(th.outputs[0], mx.inputs['Factor']); L(mx.outputs['Result'], b.inputs['Base Color'])
        _box(f'{name}_sheet', (0.18, 0, 0.002), (0.36, 0.24, 0.002), hide, bevel=0.0, parent=root)        # the unrolled part
        plain = principled('scroll_leather_plain', (0.5, 0.38, 0.25), rough=0.8, bump=0.25, bump_scale=200)
        _cyl(f'{name}_roll', (-0.02, 0, 0.025), 0.025, 0.25, plain, rot=(math.radians(90), 0, 0), verts=24, parent=root)
        pot = _lathe(f'{name}_inkpot', [(0, 0), (0.0, 0.04), (0.018, 0.046), (0.032, 0.038), (0.038, 0.02), (0.042, 0.022)],
                     black_gloss(), seg=28, parent=root, smooth=1, thick=0.003)
        pot.location = (0.42, 0.12, 0.0)                     # squat black-glazed ink pot, wide so it cannot tip
        _cyl(f'{name}_ink', (0.42, 0.12, 0.03), 0.017, 0.002, ink, verts=16, parent=root)   # ink surface inside the mouth
        reed = principled('reed_pen', (0.55, 0.47, 0.30), rough=0.6)
        for k in range(2):
            _cyl(f'{name}_pen', (0.32 + k * 0.03, -0.15, 0.006), 0.004, 0.22, reed, rot=(0, math.radians(90), math.radians(10 + 15 * k)), verts=8, parent=root)
    else:
        w = old_wood('tablet_wood', (0.32, 0.22, 0.12), grain=4)
        wax = principled('tablet_wax', (0.02, 0.018, 0.015), rough=0.35, bump=0.3, bump_scale=120)
        for k, (x, rz) in enumerate(((-0.075, 0.0), (0.075, 0.0))):         # two leaves, open like a book
            _box(f'{name}_leaf{k}', (x, 0, 0.006), (0.14, 0.19, 0.012), w, bevel=0.002, parent=root)
            _box(f'{name}_wax{k}', (x, 0, 0.0125), (0.11, 0.16, 0.002), wax, bevel=0.0, parent=root)
        for k in range(2):                                                   # cord hinges
            bpy.ops.mesh.primitive_torus_add(major_radius=0.008, minor_radius=0.002, location=(0, (k - 0.5) * 0.1, 0.01))
            t = bpy.context.object; t.name = f'{name}_hinge'; t.rotation_euler.x = math.radians(90)
            t.data.materials.append(rope_fibre()); t.parent = root
        _cyl(f'{name}_stylus', (0.05, -0.13, 0.004), 0.003, 0.13, bpy.data.materials.get('bronze') or aged_bronze('bronze'),
             rot=(0, math.radians(90), 0.3), verts=8, parent=root)
    return _place(root, loc, heading_deg)


def royal_parasol(loc=(0, 0, 0), heading_deg=0.0, height=2.6, tilt_deg=12.0, name='royal_parasol'):
    """The ROYAL PARASOL held over the Great King by an attendant (Persepolis reliefs, Palace of Darius doorways):
    a tall staff, a shallow dome of ribs covered in cloth with a deep fringe, a finial. Tilted as if carried."""
    root = _root(name)
    g = bpy.data.materials.get('royal_gold') or gold()
    cloth = wool(f'{name}_cloth', (0.32, 0.06, 0.12), tile=0.3)
    _cyl(f'{name}_staff', (0, 0, height / 2), 0.022, height, g, verts=12, parent=root)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=12, radius=0.75, location=(0, 0, height))
    d = bpy.context.object; d.name = f'{name}_dome'
    for v in d.data.vertices:
        if v.co.z < 0:
            v.co.z = 0
    d.scale = (1, 1, 0.35); d.data.materials.append(cloth); d.parent = root
    for k in range(16):                                  # fringe tassels round the edge
        a = 2 * math.pi * k / 16
        _cyl(f'{name}_tassel', (0.74 * math.cos(a), 0.74 * math.sin(a), height - 0.09), 0.02, 0.18, g, verts=6, parent=root)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.05, location=(0, 0, height + 0.3))
    f = bpy.context.object; f.name = f'{name}_finial'; f.data.materials.append(g); f.parent = root
    root.rotation_euler.x = math.radians(tilt_deg)
    return _place(root, loc, heading_deg)


def carpet(loc=(0, 0, 0), heading_deg=0.0, size=(3.0, 2.0), field=(0.30, 0.05, 0.04), border=(0.08, 0.10, 0.22),
           trim=(0.62, 0.48, 0.18), name='carpet'):
    """Knotted wool CARPET of the Persian court: a red field of small squares (rosettes), wide borders of a second
    colour, a thin ochre trim - the scheme of the Pazyryk carpet (c. 400 BC, the oldest one known, with Achaemenid
    motifs). A thin slab lying on the floor; size = (length, width) in metres."""
    root = _root(name)
    m = wool(f'{name}_wool', field, tile=0.08)
    nt = m.node_tree; L = nt.links.new
    tint = nt.nodes['tint']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(tc.outputs['Object'], sep.inputs['Vector'])

    def edge(axis, half):                              # distance from the nearest edge along one axis (metres)
        ab = nt.nodes.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; L(sep.outputs[axis], ab.inputs[0])
        d = nt.nodes.new('ShaderNodeMath'); d.operation = 'SUBTRACT'; d.inputs[0].default_value = half; L(ab.outputs[0], d.inputs[1])
        return d.outputs[0]
    mn = nt.nodes.new('ShaderNodeMath'); mn.operation = 'MINIMUM'
    L(edge('X', size[0] / 2), mn.inputs[0]); L(edge('Y', size[1] / 2), mn.inputs[1])
    bw = min(size) * 0.14                              # border width
    inb = nt.nodes.new('ShaderNodeMath'); inb.operation = 'LESS_THAN'; inb.inputs[1].default_value = bw; L(mn.outputs[0], inb.inputs[0])
    trm = nt.nodes.new('ShaderNodeMath'); trm.operation = 'LESS_THAN'; trm.inputs[1].default_value = 0.025; L(mn.outputs[0], trm.inputs[0])
    trm2 = nt.nodes.new('ShaderNodeMath'); trm2.operation = 'COMPARE'; trm2.inputs[1].default_value = bw; trm2.inputs[2].default_value = 0.012
    L(mn.outputs[0], trm2.inputs[0])
    ck = nt.nodes.new('ShaderNodeTexChecker'); ck.inputs['Scale'].default_value = 1.0
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / 0.11, 1 / 0.11, 1)   # 11 cm squares
    L(tc.outputs['Object'], mp.inputs['Vector']); L(mp.outputs['Vector'], ck.inputs['Vector'])
    ck.inputs['Color1'].default_value = (*field, 1)
    ck.inputs['Color2'].default_value = (field[0] * 0.6, field[1] * 0.8 + 0.03, field[2] + 0.04, 1)
    c1 = nt.nodes.new('ShaderNodeMix'); c1.data_type = 'RGBA'; L(inb.outputs[0], c1.inputs['Factor'])
    L(ck.outputs['Color'], c1.inputs['A']); c1.inputs['B'].default_value = (*border, 1)
    tmax = nt.nodes.new('ShaderNodeMath'); tmax.operation = 'MAXIMUM'; L(trm.outputs[0], tmax.inputs[0]); L(trm2.outputs[0], tmax.inputs[1])
    c2 = nt.nodes.new('ShaderNodeMix'); c2.data_type = 'RGBA'; L(tmax.outputs[0], c2.inputs['Factor'])
    L(c1.outputs['Result'], c2.inputs['A']); c2.inputs['B'].default_value = (*trim, 1)
    L(c2.outputs['Result'], tint.inputs['B'])
    o = _box(f'{name}_rug', (0, 0, 0.006), (size[0], size[1], 0.012), m, bevel=0.004, parent=root)
    return _place(root, loc, heading_deg)


def incense_burner(loc=(0, 0, 0), heading_deg=0.0, height=1.25, smoke=True, frames=(1, 240), name='incense_burner'):
    """Achaemenid INCENSE BURNER: on the Persepolis Treasury relief two of these tall stands smoke in front of the
    enthroned king. A stepped foot, a slim fluted shaft, a bowl and a tall stepped conical lid with a bird finial;
    smoke=True lets a thin thread of incense smoke rise (fx.smoke_column, very low density)."""
    root = _root(name)
    g = bpy.data.materials.get('royal_gold') or gold()
    br = bpy.data.materials.get('bronze') or aged_bronze('bronze')
    _lathe(f'{name}_foot', [(0, 0), (0.0, 0.22), (0.05, 0.22), (0.06, 0.15), (0.11, 0.15), (0.12, 0.07), (0.16, 0.05)],
           br, seg=36, parent=root, smooth=1)
    _cyl(f'{name}_shaft', (0, 0, 0.16 + (height - 0.55) / 2), 0.035, height - 0.55, br, verts=16, parent=root, r2=0.03)
    top = height - 0.39
    _lathe(f'{name}_bowl', [(top, 0.0), (top, 0.05), (top + 0.06, 0.14), (top + 0.1, 0.16)], g, seg=36, parent=root, smooth=1, thick=0.004)
    _lathe(f'{name}_lid', [(top + 0.1, 0.16), (top + 0.12, 0.15), (top + 0.12, 0.11), (top + 0.18, 0.1), (top + 0.19, 0.07),
                           (top + 0.27, 0.05), (top + 0.28, 0.03), (top + 0.36, 0.0)], g, seg=36, parent=root, smooth=1)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.025, location=(0, 0, top + 0.39))
    b = bpy.context.object; b.name = f'{name}_finial'; b.scale = (1.6, 0.8, 1.0); b.data.materials.append(g); b.parent = root
    if smoke:
        from lib import fx
        sm = fx.smoke_column((0, 0, 0), height=1.4, width=0.06, density=0.6, color=(0.55, 0.55, 0.58), frames=frames,
                             name=f'{name}_smoke')
        sm.parent = root; sm.location = (0, 0, top + 0.4 + 0.7)
    return _place(root, loc, heading_deg)


def phiale(loc=(0, 0, 0), heading_deg=0.0, metal='gold', lobes=24, name='phiale'):
    """PHIALE: a shallow libation bowl with a raised centre boss (omphalos) and radiating LOBES - gold and silver ones
    are known from Achaemenid court treasure and Greek sanctuaries alike. ~18 cm across."""
    import bmesh
    root = _root(name)
    m = (bpy.data.materials.get('royal_gold') or gold()) if metal == 'gold' else principled('silver', (0.8, 0.8, 0.82), metal=1.0, rough=0.25)
    seg, rings = lobes * 6, 14
    bm = bmesh.new()
    grid = []
    for j in range(rings + 1):
        v = j / rings
        r = 0.09 * v
        z = 0.035 * v ** 2 + (0.012 * math.exp(-(v / 0.18) ** 2))       # shallow bowl + central boss
        row = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            lobe = 1.0 + 0.06 * max(0.0, math.cos(a * lobes)) * math.sin(math.pi * min(1, v * 1.2)) if v > 0.25 else 1.0
            row.append(bm.verts.new((r * lobe * math.cos(a), r * lobe * math.sin(a), z)))
        grid.append(row)
    for r0, r1 in zip(grid, grid[1:]):
        for i in range(seg):
            f = bm.faces.new((r0[i], r0[(i + 1) % seg], r1[(i + 1) % seg], r1[i])); f.smooth = True
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(m)
    o = bpy.data.objects.new(name + '_bowl', me); link(o); o.parent = root
    o.modifiers.new('thick', 'SOLIDIFY').thickness = 0.002
    return _place(root, loc, heading_deg)


def rhyton(loc=(0, 0, 0), heading_deg=0.0, name='rhyton'):
    """Achaemenid gold RHYTON: a fluted drinking horn whose lower end turns into the forepart of an animal (here a
    simple winged-lion / ibex head block: the famous Hamadan rhyta are 5th c. BC). Lies on its side as on a table."""
    root = _root(name)
    g = bpy.data.materials.get('royal_gold') or gold()
    pts = [(0.0, 0, 0.05), (0.08, 0, 0.06), (0.16, 0, 0.09), (0.22, 0, 0.14)]
    _tube(f'{name}_horn', pts, 0.045, g, root, taper_end=0.0)
    cu = root.children[-1].data
    sp = cu.splines[0]
    for k, bp in enumerate(sp.bezier_points):           # the horn widens toward the mouth
        bp.radius = 0.5 + 0.5 * (len(sp.bezier_points) - 1 - k) / (len(sp.bezier_points) - 1)
    rim = _lathe(f'{name}_rim', [(0, 0.045), (0.012, 0.05), (0.02, 0.047)], g, seg=32, parent=root, smooth=1)
    rim.rotation_euler.y = math.radians(-90); rim.location = (0.0, 0, 0.05)      # lip round the mouth of the horn
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.04, location=(0.25, 0, 0.15))
    h = bpy.context.object; h.name = f'{name}_protome'; h.scale = (1.4, 0.8, 1.0); h.data.materials.append(g); h.parent = root
    for sgn in (-1, 1):                                  # horns / ears of the animal head
        _tube(f'{name}_ear', [(0.24, sgn * 0.02, 0.18), (0.22, sgn * 0.04, 0.22), (0.19, sgn * 0.05, 0.24)], 0.006, g, root)
    return _place(root, loc, heading_deg)


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
    m = wool(name, base)
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
    m1.inputs['A'].default_value = (*base, 1); L(bsock, m1.inputs['B']); L(band.outputs[0], m1.inputs['Factor'])
    m2 = nt.nodes.new('ShaderNodeMix'); m2.data_type = 'RGBA'
    L(m1.outputs['Result'], m2.inputs['A']); m2.inputs['B'].default_value = (*edge, 1); L(line.outputs[0], m2.inputs['Factor'])
    tint = nt.nodes.get('tint')                              # the scanned weave multiplies our pattern
    L(m2.outputs['Result'], tint.inputs['B'] if tint else b.inputs['Base Color'])
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
    leather = globals()['leather'](f'{name}_leather')    # scanned leather grain (name clash: local var)
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

# MODERN-ERA PROPS (WS17, Session F) - 1940s-1960s secret government projects, built by code from period photos and
# museum pieces. Every function builds at the origin (or `loc`), returns the root empty, and accepts heading_deg.
# Sources (shapes + sizes):
#   office      - US government office furniture of the 1940s-50s: steel tanker desks, Globe-Wernicke / Steelcase
#                 4-drawer filing cabinets (~1.33 m tall), venetian blinds (National Archives photos, OSS / Pentagon)
#   typewriter  - Underwood No. 5 / Remington Standard (Smithsonian NMAH collection): 4 rows of round keys, platen,
#                 carriage-return lever, ribbon spools under a curved top
#   rotary phone- Western Electric model 302 (1937) / 500 (1949), black Bakelite, finger-wheel dial (10 holes)
#   reel-to-reel- Ampex 300 / 350 studio recorders (1949-), the CIA/FBI wiretap and interrogation recorder of the era
#   folders     - manila folders + red/black classification stamps: SECRET, TOP SECRET (Executive Order 10290, 1951;
#                 example covers in the CIA Reading Room and National Archives declassified documents)
#   geiger      - Victoreen / Nuclear-Chicago survey meters (1940s-50s): box + round meter + probe on a cable
#   projector   - 16 mm Bell & Howell Filmo / Victor Animatograph (two reel arms, side lens)
#   vehicles    - Willys MB jeep (1941-45), GMC CCKW "deuce and a half" truck, 1940s US sedan (fastback, separate
#                 fenders), 1950s Ford sedan (slab sides) - National WWII Museum, NHTSA photos
#   aircraft    - Boeing B-29 Superfortress (tube fuselage, glazed nose, 4 radial engines - Enola Gay, NASM), a
#                 swept-wing 1950s jet; shapes only (no markings)
#   rockets     - V-2 / A-4 (14 m, 4 fins), Redstone + Mercury capsule (Mercury-Redstone, 25 m), R-7 / Vostok (4
#                 strap-on boosters with conical tops) - NASA history office, RSC Energia photos
import math
import random

import bpy
import numpy as np
from mathutils import Vector

from lib.common import link, mesh_obj, principled


# ------------------------------------------------------------------ helpers
def mat(name, color, metal=0.0, rough=0.5, bump=0.0, bump_scale=200.0):
    return bpy.data.materials.get(name) or principled(name, color, metal=metal, rough=rough, bump=bump, bump_scale=bump_scale)


def worn_paint(name, color, metal=0.25, wear=0.35, rough=0.45):
    """Painted steel that has lived in an office/army: base paint, grime in a noise pattern, bare metal showing on
    worn spots (scratched edges are approximated by high-frequency noise)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = principled(name, color, metal=metal, rough=rough)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    n1 = nt.nodes.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 7; n1.inputs['Detail'].default_value = 8
    n2 = nt.nodes.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 90; n2.inputs['Detail'].default_value = 4
    g = nt.nodes.new('ShaderNodeMix'); g.data_type = 'RGBA'; g.inputs['A'].default_value = (*color, 1)
    g.inputs['B'].default_value = (color[0] * 0.55, color[1] * 0.52, color[2] * 0.48, 1)
    gm = nt.nodes.new('ShaderNodeMapRange'); gm.inputs['From Min'].default_value = 0.45; gm.inputs['From Max'].default_value = 0.75
    L(n1.outputs['Fac'], gm.inputs['Value']); L(gm.outputs['Result'], g.inputs['Factor'])
    bare = nt.nodes.new('ShaderNodeMix'); bare.data_type = 'RGBA'; L(g.outputs['Result'], bare.inputs['A'])
    bare.inputs['B'].default_value = (0.45, 0.44, 0.42, 1)
    bm = nt.nodes.new('ShaderNodeMapRange'); bm.inputs['From Min'].default_value = 1.0 - wear * 0.25; bm.inputs['From Max'].default_value = 1.0
    L(n2.outputs['Fac'], bm.inputs['Value']); L(bm.outputs['Result'], bare.inputs['Factor'])
    L(bare.outputs['Result'], b.inputs['Base Color'])
    rr = nt.nodes.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = rough; rr.inputs['To Max'].default_value = rough + 0.3
    L(n1.outputs['Fac'], rr.inputs['Value']); L(rr.outputs['Result'], b.inputs['Roughness'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.05
    L(n2.outputs['Fac'], bp.inputs['Height']); L(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def bakelite(name='bakelite'):
    return mat(name, (0.012, 0.011, 0.01), rough=0.18)


def chrome(name='chrome'):
    return mat(name, (0.8, 0.8, 0.8), metal=1.0, rough=0.12)


def rubber(name='rubber'):
    return mat(name, (0.02, 0.02, 0.02), rough=0.85, bump=0.1, bump_scale=400)


def glass(name='window_glass', tint=(0.9, 0.95, 0.95)):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = principled(name, tint, rough=0.03)
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Transmission Weight'].default_value = 1.0; b.inputs['IOR'].default_value = 1.5
    return m


def emit(name, color, strength=5.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_fake_user = True; nt = m.node_tree
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs['Color'].default_value = (*color, 1); e.inputs['Strength'].default_value = strength
    nt.links.new(e.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    return m


def box(name, c, sz, m, bevel=0.004, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=c); o = bpy.context.object; o.name = name; o.scale = sz
    if bevel:
        bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = bevel; bv.segments = 2
    o.data.materials.append(m)
    if parent is not None:
        o.parent = parent
    return o


def cyl(name, c, r, depth, m, rot=(0, 0, 0), verts=32, parent=None, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=c, rotation=rot)
    o = bpy.context.object; o.name = name; o.data.materials.append(m)
    for f in o.data.polygons:
        f.use_smooth = True
    if bevel:
        bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = bevel; bv.segments = 2; bv.limit_method = 'ANGLE'
    if parent is not None:
        o.parent = parent
    return o


def sphere(name, c, r, m, parent=None, scale=(1, 1, 1), seg=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=r, location=c)
    o = bpy.context.object; o.name = name; o.scale = scale; o.data.materials.append(m)
    for f in o.data.polygons:
        f.use_smooth = True
    if parent is not None:
        o.parent = parent
    return o


def root_empty(name, loc=(0, 0, 0), heading_deg=0.0):
    r = bpy.data.objects.new(name, None); link(r)
    r.location = loc; r.rotation_euler.z = math.radians(heading_deg)
    return r


def _adopt(root, before):
    for o in set(bpy.data.objects) - before:
        if o.parent is None and o is not root:
            o.parent = root
    return root


def text(name, body, loc, size, m, rot=(math.pi / 2, 0, 0), extrude=0.0, align='CENTER', parent=None, bold=True):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.size = size; cu.extrude = extrude
    cu.align_x = align; cu.align_y = 'CENTER'
    o = bpy.data.objects.new(name, cu); link(o); o.location = loc; o.rotation_euler = rot
    o.data.materials.append(m)
    if parent is not None:
        o.parent = parent
    return o


def lathe(name, profile, m, segs=48, parent=None):
    """Surface of revolution around Z from a profile [(radius, z), ...] (rockets, lamp shades, reels)."""
    verts, faces = [], []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        verts += [(r * math.cos(a), r * math.sin(a), z) for r, z in profile]
    n = len(profile)
    for k in range(segs):
        k2 = (k + 1) % segs
        for i in range(n - 1):
            faces.append([k * n + i, k2 * n + i, k2 * n + i + 1, k * n + i + 1])
    o = mesh_obj(name, verts, faces, m)
    for f in o.data.polygons:
        f.use_smooth = True
    if parent is not None:
        o.parent = parent
    return o


# ------------------------------------------------------------------ office
def desk(loc=(0, 0, 0), heading_deg=0.0, name='desk', w=1.52, d=0.76, steel=True, seed=0):
    """A government 'tanker' desk (steel, rounded edges, linoleum top) or an oak pedestal desk. Front = -Y."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    body = worn_paint(f'{name}_paint', (0.28, 0.3, 0.27)) if steel else mat(f'{name}_oak', (0.22, 0.12, 0.05), rough=0.45, bump=0.03)
    top = mat('desk_lino', (0.11, 0.14, 0.12), rough=0.4) if steel else body
    h = 0.76
    box(name + '_top', (0, 0, h - 0.02), (w, d, 0.04), top, 0.01)
    for sx in (-1, 1):                                               # two drawer pedestals
        x = sx * (w / 2 - 0.22)
        box(f'{name}_ped{sx}', (x, 0.02, (h - 0.04) / 2), (0.42, d - 0.06, h - 0.04), body, 0.01)
        for k in range(3):                                           # drawers: fronts, recessed seams, pulls
            z = 0.14 + k * 0.215
            box(f'{name}_dr{sx}{k}', (x, -d / 2 + 0.025, z + 0.06), (0.39, 0.01, 0.2), body, 0.004)
            box(f'{name}_pull{sx}{k}', (x, -d / 2 + 0.017, z + 0.12), (0.11, 0.012, 0.014), chrome(), 0.003)
    box(name + '_modesty', (0, d / 2 - 0.03, 0.45), (w - 0.86, 0.02, 0.6), body, 0.004)
    return _adopt(r, before)


def office_chair(loc=(0, 0, 0), heading_deg=0.0, name='chair'):
    """1940s wooden swivel office chair (bentwood back, five-star cast base) - front = -Y."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    wood = mat('chair_oak', (0.2, 0.1, 0.04), rough=0.42, bump=0.03)
    iron = mat('cast_iron', (0.04, 0.04, 0.04), metal=0.7, rough=0.5)
    for k in range(5):
        a = k * 2 * math.pi / 5
        o = box(f'{name}_leg{k}', (0.17 * math.cos(a), 0.17 * math.sin(a), 0.06), (0.34, 0.035, 0.03), iron, 0.006)
        o.rotation_euler.z = a
        cyl(f'{name}_caster{k}', (0.33 * math.cos(a), 0.33 * math.sin(a), 0.025), 0.025, 0.02, rubber(), rot=(math.pi / 2, 0, a))
    cyl(name + '_post', (0, 0, 0.26), 0.025, 0.36, iron)
    cyl(name + '_seat', (0, 0, 0.47), 0.23, 0.045, wood, bevel=0.01)
    box(name + '_back', (0, 0.2, 0.75), (0.42, 0.03, 0.2), wood, 0.012)
    for sx in (-1, 1):
        box(f'{name}_spindle{sx}', (sx * 0.15, 0.2, 0.6), (0.025, 0.025, 0.25), wood, 0.005)
    return _adopt(r, before)


def filing_cabinet(loc=(0, 0, 0), heading_deg=0.0, name='file', drawers=4, color=(0.32, 0.34, 0.3), seed=0, open_drawer=None):
    """Steel 4-drawer filing cabinet (~1.33 m): drawer fronts with chrome pulls + card label holders. Front = -Y.
    open_drawer = index of a drawer pulled out (with folders inside) for a search scene."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    paint = worn_paint(f'file_paint_{color}', color)
    H, W, D = 0.33 * drawers + 0.03, 0.4, 0.66
    box(name + '_body', (0, 0, H / 2), (W, D, H), paint, 0.006)
    card = mat('label_card', (0.75, 0.72, 0.6), rough=0.8)
    manila = mat('manila', (0.72, 0.58, 0.33), rough=0.85)
    for k in range(drawers):
        z = 0.03 + k * 0.33 + 0.16
        y = -D / 2 - 0.006 - (0.45 if open_drawer == k else 0.0)
        box(f'{name}_front{k}', (0, y, z), (W - 0.02, 0.012, 0.3), paint, 0.004)
        box(f'{name}_pull{k}', (0, y - 0.015, z + 0.02), (0.12, 0.02, 0.022), chrome(), 0.004)
        box(f'{name}_label{k}', (0, y - 0.007, z + 0.08), (0.08, 0.004, 0.035), card, 0.001)
        if open_drawer == k:
            box(f'{name}_tray{k}', (0, y + 0.24, z - 0.02), (W - 0.04, 0.46, 0.22), paint, 0.003)
            rnd = random.Random(seed)
            for f in range(18):
                o = box(f'{name}_fold{k}_{f}', (rnd.uniform(-0.005, 0.005), y + 0.04 + f * 0.022, z + 0.03 + rnd.uniform(0, 0.02)),
                        (W - 0.08, 0.003, 0.24), manila, 0.001)
                o.rotation_euler.x = rnd.uniform(-0.12, 0.12)
    return _adopt(r, before)


def venetian_blinds(loc, width=1.4, height=1.6, heading_deg=0.0, tilt_deg=35.0, name='blinds', color=(0.72, 0.68, 0.58)):
    """Window blinds: thin painted slats every 5 cm on ladder tapes, tilted so sunlight falls through in BARS (the
    classic film-noir light). The window itself is the caller's; this hangs in front of it (front = -Y)."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    slat = mat(f'{name}_slat', color, rough=0.45)
    tape = mat('blind_tape', (0.6, 0.57, 0.5), rough=0.9)
    me = bpy.data.meshes.new(name + '_slat'); verts = []; faces = []
    n = int(height / 0.05)
    for k in range(n):                                               # all slats in ONE mesh (cheap)
        z = height / 2 - k * 0.05
        t = math.radians(tilt_deg); dy, dz = 0.022 * math.cos(t), 0.022 * math.sin(t)
        b = len(verts)
        verts += [(-width / 2, -dy, z - dz), (width / 2, -dy, z - dz), (width / 2, dy, z + dz), (-width / 2, dy, z + dz)]
        faces.append([b, b + 1, b + 2, b + 3])
    me.from_pydata(verts, [], faces); me.update()
    o = link(bpy.data.objects.new(name + '_slats', me)); o.data.materials.append(slat); o.parent = r
    o.modifiers.new('t', 'SOLIDIFY').thickness = 0.002
    for sx in (-0.3, 0.3):
        box(f'{name}_tape{sx}', (sx * width, 0.0, 0), (0.012, 0.046, height), tape, 0).parent = r
    box(name + '_head', (0, 0, height / 2 + 0.04), (width + 0.04, 0.06, 0.05), slat, 0.004).parent = r
    return _adopt(r, before)


def wall_clock(loc, heading_deg=0.0, name='clock', hour=5, minute=29):
    """Round office clock (Seth Thomas / Simplex style), steel bezel, hands at hour:minute. Face = -Y."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    rim = mat('clock_rim', (0.1, 0.1, 0.1), metal=0.8, rough=0.35)
    cyl(name + '_rim', (0, 0, 0), 0.2, 0.05, rim, rot=(math.pi / 2, 0, 0), bevel=0.01)
    cyl(name + '_face', (0, -0.026, 0), 0.18, 0.004, mat('clock_face', (0.85, 0.84, 0.78), rough=0.5), rot=(math.pi / 2, 0, 0))
    black = mat('ink_black', (0.01, 0.01, 0.01), rough=0.5)
    for k in range(12):
        a = k * math.pi / 6
        o = box(f'{name}_tick{k}', (0.155 * math.sin(a), -0.03, 0.155 * math.cos(a)), (0.007, 0.002, 0.028 if k % 3 == 0 else 0.016), black, 0)
        o.rotation_euler.y = a
    for nm, ang, ln, wd in (('hour', (hour % 12 + minute / 60) * math.pi / 6, 0.09, 0.012), ('min', minute * math.pi / 30, 0.14, 0.008)):
        o = box(f'{name}_{nm}', (ln / 2 * math.sin(ang), -0.034, ln / 2 * math.cos(ang)), (wd, 0.002, ln), black, 0)
        o.rotation_euler.y = ang
    cyl(name + '_glass', (0, -0.04, 0), 0.185, 0.006, glass(), rot=(math.pi / 2, 0, 0))
    return _adopt(r, before)


def desk_lamp(loc, heading_deg=0.0, name='lamp', on=True, power=25.0):
    """Banker's / gooseneck desk lamp: green enamel shade, brass stem, warm bulb (tungsten ~2700 K)."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    brass = mat('brass', (0.65, 0.45, 0.2), metal=1.0, rough=0.3)
    shade = mat('lamp_green', (0.02, 0.18, 0.08), rough=0.2)
    cyl(name + '_base', (0, 0, 0.012), 0.08, 0.024, brass, bevel=0.006)
    cyl(name + '_stem', (0, 0.02, 0.2), 0.008, 0.38, brass)
    s = lathe(name + '_shade', [(0.0, 0.0), (0.05, 0.0), (0.12, -0.08), (0.125, -0.09)], shade)
    s.location = (0, -0.06, 0.4); s.rotation_euler.x = math.radians(18)
    if on:
        sphere(name + '_bulb', (0, -0.07, 0.35), 0.025, emit('bulb_warm', (1.0, 0.78, 0.5), 30))
        bpy.ops.object.light_add(type='SPOT', location=(0, -0.07, 0.36)); lt = bpy.context.object; lt.name = name + '_light'
        lt.data.energy = power; lt.data.color = (1.0, 0.8, 0.55); lt.data.spot_size = math.radians(110); lt.data.shadow_soft_size = 0.03
        lt.rotation_euler.x = math.radians(-12)
    return _adopt(r, before)


# ------------------------------------------------------------------ desk equipment
def typewriter(loc=(0, 0, 0), heading_deg=0.0, name='typewriter', paper=True):
    """Underwood No. 5-style typewriter (~0.3 x 0.32 x 0.25 m), black enamel + gold decals, front = -Y:
    stepped body, 4 rows of round glass-topped keys on wire stalks, space bar, curved type-bar basket, platen roller
    with knobs, carriage-return lever, two ribbon spools, a sheet of paper in the carriage."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    enamel = mat('typewriter_enamel', (0.015, 0.014, 0.013), rough=0.22)
    keytop = mat('key_top', (0.85, 0.83, 0.76), rough=0.25)
    ring = chrome('key_ring')
    box(name + '_base', (0, 0.02, 0.03), (0.32, 0.3, 0.06), enamel, 0.01)
    box(name + '_body', (0, 0.07, 0.11), (0.3, 0.2, 0.12), enamel, 0.025)
    box(name + '_hood', (0, 0.02, 0.15), (0.24, 0.1, 0.05), enamel, 0.02).rotation_euler.x = math.radians(-35)
    for row in range(4):                                             # the keyboard, stepped like stairs
        n = 11 if row < 3 else 10
        for k in range(n):
            x = -0.115 + k * 0.023 + row * 0.006
            y = -0.13 + row * 0.022; z = 0.045 + row * 0.014
            cyl(f'{name}_stalk{row}_{k}', (x, y + 0.006, z - 0.012), 0.0015, 0.026, ring, verts=6)
            cyl(f'{name}_ring{row}_{k}', (x, y, z), 0.0085, 0.004, ring, verts=16)
            cyl(f'{name}_key{row}_{k}', (x, y, z + 0.0025), 0.0072, 0.002, keytop, verts=16)
    box(name + '_space', (0, -0.152, 0.036), (0.18, 0.012, 0.006), enamel, 0.002)
    # carriage: platen roller + knobs + paper + return lever
    cyl(name + '_platen', (0, 0.13, 0.2), 0.022, 0.34, rubber('platen'), rot=(0, math.pi / 2, 0), verts=24)
    box(name + '_carriage', (0, 0.15, 0.18), (0.4, 0.05, 0.02), ring, 0.003)
    for sx in (-1, 1):
        cyl(f'{name}_knob{sx}', (sx * 0.19, 0.13, 0.2), 0.016, 0.03, enamel, rot=(0, math.pi / 2, 0))
    lever = box(name + '_lever', (-0.2, 0.08, 0.215), (0.012, 0.09, 0.006), ring, 0.002); lever.rotation_euler.z = math.radians(20)
    for sx in (-1, 1):                                               # ribbon spools under round covers
        cyl(f'{name}_spool{sx}', (sx * 0.1, 0.1, 0.175), 0.03, 0.01, enamel)
    if paper:
        pm = mat('paper_white', (0.82, 0.8, 0.74), rough=0.9)
        o = box(name + '_paper', (0, 0.155, 0.29), (0.216, 0.001, 0.2), pm, 0); o.rotation_euler.x = math.radians(-12)
    return _adopt(r, before)


def rotary_phone(loc=(0, 0, 0), heading_deg=0.0, name='phone', color=None):
    """Western Electric model 302/500: domed black Bakelite body, handset on the cradle, finger-wheel dial with 10
    holes on a white number card, coiled-look cord. Front = -Y."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    bk = bakelite(f'bakelite_{color}') if color is None else mat(f'phone_{color}', color, rough=0.2)
    lathe(name + '_body', [(0.0, 0.0), (0.11, 0.0), (0.105, 0.04), (0.085, 0.085), (0.04, 0.105), (0.0, 0.108)], bk).scale = (1.0, 0.85, 1.0)
    for sx in (-1, 1):                                               # cradle prongs
        box(f'{name}_prong{sx}', (sx * 0.06, 0.0, 0.112), (0.025, 0.05, 0.03), bk, 0.008)
    # handset: two cups joined by a curved grip, lying across the cradle
    box(name + '_grip', (0, 0.0, 0.135), (0.2, 0.04, 0.03), bk, 0.012)
    for sx in (-1, 1):
        cyl(f'{name}_cup{sx}', (sx * 0.1, 0.0, 0.125), 0.032, 0.04, bk, verts=24, bevel=0.008)
    # dial on the sloped front face
    card = mat('dial_card', (0.85, 0.84, 0.8), rough=0.5)
    dial = bpy.data.objects.new(name + '_dial', None); link(dial); dial.location = (0, -0.075, 0.07); dial.rotation_euler.x = math.radians(55)
    cyl(name + '_card', (0, 0, 0), 0.042, 0.004, card, rot=(math.pi / 2, 0, 0), parent=dial)
    cyl(name + '_wheel', (0, -0.004, 0), 0.046, 0.004, chrome('dial_chrome'), rot=(math.pi / 2, 0, 0), parent=dial)
    for k in range(10):                                              # finger holes (dark discs on the wheel)
        a = math.radians(-60 + k * 30)
        cyl(f'{name}_hole{k}', (0.032 * math.cos(a), -0.0065, 0.032 * math.sin(a)), 0.0075, 0.002, bk, rot=(math.pi / 2, 0, 0), parent=dial, verts=16)
    cyl(name + '_cord', (0.02, 0.1, 0.02), 0.005, 0.25, bk, rot=(math.pi / 2, 0, 0.3), verts=8)
    return _adopt(r, before)


def reel_to_reel(loc=(0, 0, 0), heading_deg=0.0, name='recorder', spin=True, frames=(1, 240)):
    """Ampex 350-style tape recorder: grey case, two 10.5" reels (aluminium flanges with three cut-outs), tape path
    over the head block, VU meter, knobs. The reels TURN if spin (keyframed). Front face = -Y (tilted up 15 deg)."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    case = worn_paint('ampex_grey', (0.33, 0.34, 0.33), metal=0.4, wear=0.15)
    panel = mat('ampex_panel', (0.1, 0.1, 0.1), metal=0.5, rough=0.4)
    alu = mat('reel_alu', (0.7, 0.7, 0.68), metal=1.0, rough=0.28)
    tape = mat('tape_brown', (0.12, 0.06, 0.03), rough=0.35)
    box(name + '_case', (0, 0, 0.12), (0.48, 0.36, 0.24), case, 0.012)
    face = bpy.data.objects.new(name + '_face', None); link(face); face.location = (0, 0, 0.245); face.rotation_euler.x = math.radians(-15)
    box(name + '_panel', (0, 0, 0), (0.46, 0.34, 0.006), panel, 0.003, parent=face)
    for sx in (-1, 1):
        reel = bpy.data.objects.new(f'{name}_reel{sx}', None); link(reel); reel.parent = face; reel.location = (sx * 0.12, 0.04, 0.02)
        cyl(f'{name}_pack{sx}', (0, 0, 0), 0.075 if sx < 0 else 0.055, 0.012, tape, parent=reel, verts=40)
        for zz in (-0.008, 0.008):
            fl = cyl(f'{name}_flange{sx}{zz}', (0, 0, zz), 0.13, 0.002, alu, parent=reel, verts=48)
        for k in range(3):                                           # flange cut-outs read as dark windows
            a = k * 2 * math.pi / 3
            cyl(f'{name}_cut{sx}{k}', (0.07 * math.cos(a), 0.07 * math.sin(a), 0.0095), 0.03, 0.001, panel, parent=reel, verts=20)
        cyl(f'{name}_hub{sx}', (0, 0, 0.01), 0.02, 0.012, alu, parent=reel)
        if spin:
            reel.rotation_euler.z = 0; reel.keyframe_insert('rotation_euler', index=2, frame=frames[0])
            reel.rotation_euler.z = -sx * 2 * math.pi * (frames[1] - frames[0]) / 24 * 0.6
            reel.keyframe_insert('rotation_euler', index=2, frame=frames[1])
            for fc in (reel.animation_data.action.fcurves if hasattr(reel.animation_data.action, 'fcurves') else []):
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
    box(name + '_heads', (0, -0.11, 0.015), (0.1, 0.03, 0.025), alu, 0.004, parent=face)
    box(name + '_tape_path', (0, -0.095, 0.022), (0.3, 0.001, 0.006), tape, 0, parent=face)
    box(name + '_vu', (0.16, -0.13, 0.008), (0.06, 0.035, 0.006), emit('vu_glow', (1.0, 0.85, 0.55), 1.5), 0.002, parent=face)
    for k in range(4):
        cyl(f'{name}_knob{k}', (-0.18 + k * 0.05, -0.135, 0.012), 0.011, 0.014, bakelite(), parent=face, verts=16)
    return _adopt(r, before)


def folder(loc=(0, 0, 0), heading_deg=0.0, name='folder', stamp='TOP SECRET', color=(0.72, 0.58, 0.33), open_=False,
           seed=0, label=None):
    """Manila file folder lying flat, with the classification STAMPED in red ink across the front (a rubber stamp:
    letters slightly uneven, ink a little faded), a typed tab label, sheets inside. stamp=None = unmarked."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    rnd = random.Random(seed)
    manila = mat(f'manila_{color}', color, rough=0.85, bump=0.02, bump_scale=600)
    paper = mat('paper_white', (0.82, 0.8, 0.74), rough=0.9)
    box(name + '_back', (0, 0, 0.001), (0.235, 0.305, 0.0015), manila, 0)
    box(name + '_tab', (0.06, 0.16, 0.001), (0.08, 0.02, 0.0015), manila, 0)
    for k in range(rnd.randint(4, 12)):
        o = box(f'{name}_sheet{k}', (rnd.uniform(-0.003, 0.003), rnd.uniform(-0.004, 0.0), 0.002 + k * 0.0003), (0.216, 0.279, 0.0002), paper, 0)
        o.rotation_euler.z = rnd.uniform(-0.02, 0.02)
    cover = box(name + '_cover', (0, 0, 0.0055), (0.235, 0.3, 0.0015), manila, 0)
    if open_:
        cover.location = (-0.235, 0, 0.001)
    if stamp:
        ink = mat('stamp_red', (0.5, 0.03, 0.03), rough=0.7)
        cx = cover.location.x
        t = text(name + '_stamp', stamp, (cx, 0.02, 0.0066), 0.034 if len(stamp) > 7 else 0.042, ink, rot=(0, 0, math.radians(rnd.uniform(-6, 6))))
        box(name + '_stampbox', (cx, 0.02, 0.0064), (0.034 * 0.62 * len(stamp) + 0.02, 0.05, 0.0002), ink, 0).hide_render = True
        frame = mat('stamp_red', (0.5, 0.03, 0.03), rough=0.7)
        for dy in (-0.028, 0.028):                                   # the stamp's ruled border
            b = box(f'{name}_rule{dy}', (cx, 0.02 + dy, 0.0066), (0.034 * 0.6 * len(stamp) + 0.02, 0.003, 0.0002), frame, 0)
            b.rotation_euler.z = t.rotation_euler.z
    if label:
        text(name + '_label', label, (0.06, 0.16, 0.0025), 0.008, mat('ink_black', (0.01, 0.01, 0.01), rough=0.5), rot=(0, 0, 0))
    return _adopt(r, before)


def folder_stack(loc=(0, 0, 0), heading_deg=0.0, n=5, name='folders', seed=0):
    """A messy pile of classified folders (mixed SECRET / TOP SECRET / unmarked)."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    rnd = random.Random(seed)
    for k in range(n):
        f = folder((rnd.uniform(-0.02, 0.02), rnd.uniform(-0.02, 0.02), k * 0.007), rnd.uniform(-12, 12), f'{name}_{k}',
                   stamp=rnd.choice(['TOP SECRET', 'SECRET', 'TOP SECRET', None]), seed=seed * 10 + k)
        f.parent = r
    return _adopt(r, before)


def geiger_counter(loc=(0, 0, 0), heading_deg=0.0, name='geiger', needle=0.6):
    """1940s-50s radiation survey meter: grey steel box with carry handle, round meter (needle at `needle` of full
    scale), range knob, and the probe tube on a coiled cable."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    paint = worn_paint('survey_grey', (0.25, 0.27, 0.27), wear=0.4)
    box(name + '_box', (0, 0, 0.08), (0.24, 0.12, 0.16), paint, 0.01)
    box(name + '_handle', (0, 0, 0.19), (0.18, 0.02, 0.02), mat('handle_leather', (0.12, 0.07, 0.04), rough=0.7), 0.006)
    cyl(name + '_meter', (-0.04, -0.061, 0.1), 0.045, 0.004, mat('meter_face', (0.88, 0.86, 0.78), rough=0.4), rot=(math.pi / 2, 0, 0))
    a = math.radians(-50 + 100 * needle)
    o = box(name + '_needle', (-0.04 + 0.018 * math.sin(a), -0.064, 0.085 + 0.018 * math.cos(a)), (0.002, 0.001, 0.04), mat('ink_black', (0.01, 0.01, 0.01)), 0)
    o.rotation_euler.y = a
    cyl(name + '_knob', (0.07, -0.062, 0.1), 0.014, 0.016, bakelite(), rot=(math.pi / 2, 0, 0))
    probe = cyl(name + '_probe', (0.22, -0.05, 0.02), 0.014, 0.22, chrome('probe_chrome'), rot=(0, math.pi / 2, 0.4))
    cyl(name + '_cable', (0.13, 0.0, 0.03), 0.004, 0.2, rubber(), rot=(0, math.pi / 2, -0.2), verts=8)
    return _adopt(r, before)


def film_projector(loc=(0, 0, 0), heading_deg=0.0, name='projector', on=False, frames=(1, 240)):
    """16 mm projector (Bell & Howell / Victor): grey crinkle body, two reel arms (front supply, back take-up),
    lens on the side facing -Y... the beam goes to -Y. on=True adds the beam (spot light + dusty volume cone)."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    body_m = worn_paint('projector_grey', (0.22, 0.22, 0.2), wear=0.25)
    alu = mat('reel_alu', (0.7, 0.7, 0.68), metal=1.0, rough=0.28)
    box(name + '_body', (0, 0, 0.14), (0.16, 0.34, 0.24), body_m, 0.02)
    cyl(name + '_lens', (0, -0.21, 0.16), 0.03, 0.1, mat('lens_black', (0.02, 0.02, 0.02), metal=0.5, rough=0.3), rot=(math.pi / 2, 0, 0))
    cyl(name + '_glass', (0, -0.262, 0.16), 0.026, 0.004, glass('lens_glass', (0.6, 0.7, 0.75)), rot=(math.pi / 2, 0, 0))
    for k, (y, z) in enumerate(((-0.1, 0.46), (0.14, 0.42))):
        arm = box(f'{name}_arm{k}', (0, y * 0.6, (z + 0.26) / 2), (0.02, 0.02, z - 0.24), body_m, 0.004)
        arm.rotation_euler.x = math.radians(15 if k == 0 else -15)
        reel = bpy.data.objects.new(f'{name}_reel{k}', None); link(reel); reel.location = (0.02, y, z)
        cyl(f'{name}_flange{k}', (0, 0, 0), 0.12, 0.004, alu, rot=(0, math.pi / 2, 0), parent=reel, verts=40)
        cyl(f'{name}_film{k}', (0.01, 0, 0), 0.07 if k == 0 else 0.05, 0.016, mat('film_base', (0.06, 0.04, 0.03), rough=0.3), rot=(0, math.pi / 2, 0), parent=reel)
        reel.rotation_euler.x = 0; reel.keyframe_insert('rotation_euler', index=0, frame=frames[0])
        reel.rotation_euler.x = 2 * math.pi * (frames[1] - frames[0]) / 24 * 0.4; reel.keyframe_insert('rotation_euler', index=0, frame=frames[1])
    if on:
        bpy.ops.object.light_add(type='SPOT', location=(0, -0.27, 0.16)); lt = bpy.context.object; lt.name = name + '_beam'
        lt.data.energy = 300; lt.data.spot_size = math.radians(14); lt.data.color = (1.0, 0.95, 0.85); lt.data.shadow_soft_size = 0.01
        lt.rotation_euler = (math.radians(90), 0, 0)
    return _adopt(r, before)


# ------------------------------------------------------------------ vehicles
def _wheel(name, c, radius, width, tyre_m, hub_m, parent, axis='X', spokes=0):
    rot = (0, math.pi / 2, 0) if axis == 'X' else (math.pi / 2, 0, 0)
    t = bpy.ops.mesh.primitive_torus_add(major_radius=radius - width * 0.35, minor_radius=width * 0.42, location=c, rotation=rot,
                                         major_segments=32, minor_segments=12)
    tyre = bpy.context.object; tyre.name = name + '_tyre'; tyre.data.materials.append(tyre_m); tyre.scale = (1, 1, 1)
    for f in tyre.data.polygons:
        f.use_smooth = True
    tyre.parent = parent
    cyl(name + '_hub', c, radius * 0.55, width * 0.7, hub_m, rot=rot, parent=parent, verts=24)
    return tyre


def jeep(loc=(0, 0, 0), heading_deg=0.0, name='jeep', color=(0.16, 0.17, 0.09), seed=0, star=True):
    """Willys MB (1941-45): 3.36 x 1.58 m, flat olive-drab body, flat hood with the slotted steel grille, round
    headlamps, fold-down windscreen, spare wheel + jerrycan on the back, white star on the hood. Front = -Y."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    od = worn_paint(f'od_{color}', color, metal=0.2, wear=0.4, rough=0.6)
    tyre, hub = rubber('tyre'), worn_paint(f'od_hub_{color}', color, wear=0.5)
    L, W = 3.36, 1.58
    box(name + '_tub', (0, 0.25, 0.75), (1.45, 1.7, 0.5), od, 0.03)               # body tub (rear)
    box(name + '_hood', (0, -0.95, 0.85), (1.15, 1.0, 0.3), od, 0.03)              # flat hood
    box(name + '_grille', (0, -1.47, 0.72), (1.1, 0.05, 0.5), od, 0.01)
    dark = mat('grille_dark', (0.01, 0.01, 0.01), rough=0.6)
    for k in range(9):                                                             # the 9 vertical grille slots
        box(f'{name}_slot{k}', (-0.32 + k * 0.08, -1.5, 0.74), (0.03, 0.01, 0.34), dark, 0)
    for sx in (-1, 1):
        cyl(f'{name}_lamp{sx}', (sx * 0.42, -1.5, 0.82), 0.075, 0.04, chrome('lamp_rim'), rot=(math.pi / 2, 0, 0))
        cyl(f'{name}_lens{sx}', (sx * 0.42, -1.52, 0.82), 0.065, 0.005, glass('headlamp', (0.9, 0.9, 0.8)), rot=(math.pi / 2, 0, 0))
        box(f'{name}_fender{sx}', (sx * 0.68, -1.0, 0.82), (0.32, 1.05, 0.04), od, 0.01)   # flat front fenders
    for x, y in ((-0.68, -1.05), (0.68, -1.05), (-0.68, 1.0), (0.68, 1.0)):
        _wheel(f'{name}_w{x}{y}', (x, y, 0.36), 0.36, 0.2, tyre, hub, r)
    ws = bpy.data.objects.new(name + '_windscreen', None); link(ws); ws.location = (0, -0.45, 1.0); ws.parent = r
    box(name + '_wsframe', (0, 0, 0.22), (1.35, 0.04, 0.44), od, 0.01, parent=ws)
    box(name + '_wsglass', (0, -0.005, 0.22), (1.22, 0.01, 0.34), glass(), 0, parent=ws)
    ws.rotation_euler.x = math.radians(-8)
    seat = mat('seat_canvas', (0.15, 0.14, 0.08), rough=0.95, bump=0.05, bump_scale=300)
    for sx in (-1, 1):
        box(f'{name}_seat{sx}', (sx * 0.33, 0.0, 0.95), (0.42, 0.42, 0.1), seat, 0.03)
        box(f'{name}_seatback{sx}', (sx * 0.33, 0.2, 1.15), (0.42, 0.08, 0.35), seat, 0.03)
    cyl(name + '_wheel_steer', (-0.33, -0.3, 1.2), 0.18, 0.02, bakelite(), rot=(math.radians(60), 0, 0), verts=32)
    _wheel(name + '_spare', (0, 1.13, 0.85), 0.36, 0.2, tyre, hub, r, axis='Y')
    if star:                                                                       # Allied white star on the hood
        from lib.modern_dress import _star
        s = _star(name + '_star', (0, -0.95, 1.003), 0.22, mat('star_white', (0.75, 0.74, 0.68), rough=0.7))
        s.rotation_euler.x = math.radians(-90); s.location = (0, -0.95, 1.002)
    return _adopt(r, before)


def army_truck(loc=(0, 0, 0), heading_deg=0.0, name='truck', color=(0.16, 0.17, 0.09), canvas=True):
    """GMC CCKW 2.5-ton 'deuce and a half': long hood + flat-fronted cab, three axles (dual rear), cargo bed under a
    canvas tilt on bows. ~6.8 m long. Front = -Y."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    od = worn_paint(f'od_{color}', color, metal=0.2, wear=0.4, rough=0.6)
    tyre, hub = rubber('tyre'), worn_paint(f'od_hub_{color}', color, wear=0.5)
    box(name + '_chassis', (0, 0.4, 0.75), (1.0, 6.2, 0.2), mat('chassis_black', (0.03, 0.03, 0.03), metal=0.6, rough=0.6), 0.01)
    box(name + '_hood', (0, -2.35, 1.35), (1.0, 1.3, 0.75), od, 0.04)
    box(name + '_grille', (0, -3.02, 1.25), (0.95, 0.05, 0.8), mat('grille_dark', (0.01, 0.01, 0.01), rough=0.6), 0.01)
    for sx in (-1, 1):
        box(f'{name}_fender{sx}', (sx * 0.85, -2.3, 1.05), (0.5, 1.5, 0.06), od, 0.02)
        cyl(f'{name}_lamp{sx}', (sx * 0.6, -3.0, 1.35), 0.11, 0.08, chrome('lamp_rim'), rot=(math.pi / 2, 0, 0))
    box(name + '_cab', (0, -1.25, 1.65), (2.0, 1.0, 1.35), od, 0.04)
    box(name + '_screen', (0, -1.76, 1.95), (1.7, 0.02, 0.5), glass(), 0)
    box(name + '_bed', (0, 1.6, 1.25), (2.2, 4.2, 0.7), od, 0.02)
    if canvas:
        cv = mat('canvas_tilt', (0.2, 0.2, 0.12), rough=0.95, bump=0.15, bump_scale=60)
        prof = [(1.1, 0.0), (1.1, 0.9), (0.95, 1.25), (0.0, 1.38)]          # tilt cross-section (half)
        verts = []; faces = []
        for i, y in enumerate(np.linspace(-0.5, 3.7, 6)):
            sec = [(-x, y, 1.6 + z) for x, z in prof] + [(x, y, 1.6 + z) for x, z in reversed(prof)]
            verts += sec
        n = len(prof) * 2
        for i in range(5):
            for k in range(n - 1):
                a = i * n + k; faces.append([a, a + 1, a + 1 + n, a + n])
        o = mesh_obj(name + '_tilt', verts, faces, cv); o.parent = r
        for f in o.data.polygons:
            f.use_smooth = True
        o.modifiers.new('t', 'SOLIDIFY').thickness = 0.01
    for y in (-2.35, 0.9, 2.3):
        for sx in (-1, 1):
            _wheel(f'{name}_w{y}{sx}', (sx * 0.85, y, 0.48), 0.48, 0.26, tyre, hub, r)
            if y > 0:
                _wheel(f'{name}_wd{y}{sx}', (sx * 0.58, y, 0.48), 0.48, 0.24, tyre, hub, r)
    return _adopt(r, before)


def sedan(loc=(0, 0, 0), heading_deg=0.0, name='sedan', color=(0.02, 0.02, 0.025), style='1940s'):
    """A US government sedan (black, of course): '1940s' = rounded fastback with separate swelling fenders and a tall
    vertical grille (Ford/Chevrolet 1941-48); '1950s' = slab-sided 'three-box' (Ford 1955). ~5.0 m. Front = -Y."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    paint = mat(f'car_paint_{color}', color, metal=0.6, rough=0.18)
    tyre, hubc = rubber('tyre'), chrome('hubcap')
    # body as a loft of rounded sections along Y: (y, half width, bottom z, top z)
    if style == '1940s':
        secs = [(-2.45, 0.55, 0.45, 0.85), (-2.2, 0.7, 0.4, 1.0), (-1.2, 0.78, 0.38, 1.05), (-0.6, 0.8, 0.38, 1.15),
                (-0.3, 0.8, 0.38, 1.6), (0.6, 0.8, 0.38, 1.62), (1.3, 0.79, 0.38, 1.45), (2.0, 0.75, 0.4, 1.05), (2.45, 0.6, 0.45, 0.85)]
    else:
        secs = [(-2.55, 0.85, 0.4, 0.88), (-1.0, 0.9, 0.36, 0.95), (-0.55, 0.9, 0.36, 1.0), (-0.3, 0.88, 0.36, 1.48),
                (0.9, 0.88, 0.36, 1.48), (1.25, 0.9, 0.36, 1.0), (2.55, 0.86, 0.4, 0.95)]
    verts, faces, n = [], [], 16
    for (y, hw, zb, zt) in secs:
        for k in range(n):
            a = 2 * math.pi * k / n
            c, s = math.cos(a), math.sin(a)
            ex = 4.0 if style == '1950s' else 2.6
            x = hw * math.copysign(abs(c) ** (2 / ex), c)
            z = (zb + zt) / 2 + (zt - zb) / 2 * math.copysign(abs(s) ** (2 / ex), s)
            if s > 0.3 and zt > 1.3:                                 # cabin: narrower at the roof (tumblehome)
                x *= 0.85
            verts.append((x, y, z))
    for i in range(len(secs) - 1):
        for k in range(n):
            a, b = i * n + k, i * n + (k + 1) % n
            faces.append([a, b, b + n, a + n])
    faces.append(list(range(n))[::-1]); faces.append([len(secs) * n - n + k for k in range(n)])
    body = mesh_obj(name + '_body', verts, faces, paint); body.parent = r
    for f in body.data.polygons:
        f.use_smooth = True
    sub = body.modifiers.new('s', 'SUBSURF'); sub.levels = 2; sub.render_levels = 2
    win = mat('car_glass', (0.05, 0.06, 0.07), metal=0.0, rough=0.05)
    for sx in (-1, 1):                                               # side windows (dark glass strips)
        box(f'{name}_win{sx}', (sx * 0.71, 0.15, 1.38), (0.02, 1.4, 0.32), win, 0.02).parent = r
    box(name + '_wscreen', (0, -0.42, 1.38), (1.3, 0.02, 0.36), win, 0.02).rotation_euler.x = math.radians(-35)
    if style == '1940s':
        for sx in (-1, 1):                                           # swelling separate fenders
            for y in (-1.55, 1.5):
                f = sphere(f'{name}_fender{sx}{y}', (sx * 0.75, y, 0.72), 0.5, paint, parent=r, scale=(0.5, 1.45, 0.62))
        box(name + '_grille', (0, -2.47, 0.72), (0.4, 0.03, 0.35), chrome('grille_chrome'), 0.02).parent = r
    else:
        box(name + '_grille', (0, -2.56, 0.7), (1.5, 0.03, 0.22), chrome('grille_chrome'), 0.01).parent = r
    for sx in (-1, 1):
        cyl(f'{name}_lamp{sx}', (sx * 0.62, -2.42, 0.88), 0.09, 0.05, chrome('lamp_rim'), rot=(math.pi / 2, 0, 0)).parent = r
        cyl(f'{name}_lens{sx}', (sx * 0.62, -2.45, 0.88), 0.08, 0.005, glass('headlamp', (0.9, 0.9, 0.8)), rot=(math.pi / 2, 0, 0)).parent = r
    box(name + '_bumperF', (0, -2.58, 0.48), (1.7, 0.08, 0.12), chrome('bumper_chrome'), 0.03).parent = r
    box(name + '_bumperR', (0, 2.58, 0.48), (1.7, 0.08, 0.12), chrome('bumper_chrome'), 0.03).parent = r
    for x, y in ((-0.76, -1.55), (0.76, -1.55), (-0.76, 1.5), (0.76, 1.5)):
        _wheel(f'{name}_w{x}{y}', (x, y, 0.36), 0.36, 0.2, tyre, hubc, r)
    return _adopt(r, before)


# ------------------------------------------------------------------ aircraft (shapes only, no markings)
def bomber(loc=(0, 0, 0), heading_deg=0.0, name='bomber', metal=True, gear=True):
    """B-29 Superfortress shape: 30.2 m tube fuselage with a fully glazed rounded nose, 43 m straight high-aspect
    wing at mid-fuselage, 4 radial engines in cowlings with 4-blade props, tall fin. Bare aluminium. Nose = -Y."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    alu = mat('aircraft_alu', (0.72, 0.73, 0.74), metal=1.0, rough=0.32, bump=0.01, bump_scale=40) if metal else mat('aircraft_od', (0.16, 0.17, 0.09), rough=0.6)
    gl = mat('cockpit_glass', (0.1, 0.12, 0.13), rough=0.04)
    R, Lf = 1.45, 30.2
    fus = lathe(name + '_fuselage', [(0.0, 0.0), (0.9, 0.5), (1.3, 1.6), (R, 3.5), (R, 22.0), (1.0, 27.0), (0.4, 30.0), (0.0, 30.2)], alu)
    fus.rotation_euler.x = math.radians(90); fus.location = (0, -Lf / 2, 3.2); fus.parent = r
    nose = sphere(name + '_nose', (0, -Lf / 2 + 1.3, 3.2), 1.32, gl, parent=r, scale=(1, 1.05, 1))
    for k in range(6):                                               # glazing frames on the nose
        a = k * math.pi / 6
        o = bpy.ops.mesh.primitive_torus_add(major_radius=1.33, minor_radius=0.02, location=(0, -Lf / 2 + 1.3, 3.2), rotation=(0, math.pi / 2, a))
        bpy.context.object.data.materials.append(alu); bpy.context.object.parent = r
    # wing (tapered, thin), engines, tail
    span, root_c, tip_c = 43.0, 5.0, 1.8
    wv = [(-span / 2, -tip_c / 2 + 1.0, 3.0), (-0.5, -root_c / 2, 3.0), (0.5, -root_c / 2, 3.0), (span / 2, -tip_c / 2 + 1.0, 3.0),
          (span / 2, tip_c / 2 + 1.0, 3.0), (0.5, root_c / 2, 3.0), (-0.5, root_c / 2, 3.0), (-span / 2, tip_c / 2 + 1.0, 3.0)]
    w = mesh_obj(name + '_wing', wv, [[0, 1, 6, 7], [1, 2, 5, 6], [2, 3, 4, 5]], alu); w.parent = r
    w.modifiers.new('t', 'SOLIDIFY').thickness = 0.45; w.modifiers.new('b', 'BEVEL').width = 0.15
    for x in (-11.5, -5.6, 5.6, 11.5):
        cow = lathe(f'{name}_cowl{x}', [(0.0, 0.0), (0.75, 0.1), (0.85, 0.6), (0.8, 4.0), (0.3, 5.5)], alu)
        cow.rotation_euler.x = math.radians(90); cow.location = (x, -3.4, 2.9); cow.parent = r
        hub = cyl(f'{name}_spinner{x}', (x, -3.5, 2.9), 0.25, 0.4, alu, rot=(math.pi / 2, 0, 0), parent=r)
        blade = mat('prop_black', (0.02, 0.02, 0.02), rough=0.5)
        for k in range(4):
            a = k * math.pi / 2 + 0.3
            o = box(f'{name}_blade{x}{k}', (x + 1.1 * math.cos(a), -3.6, 2.9 + 1.1 * math.sin(a)), (2.1, 0.06, 0.3), blade, 0.03)
            o.rotation_euler.y = -a; o.parent = r
    fin = mesh_obj(name + '_fin', [(0, 11.0, 4.3), (0, 15.0, 4.3), (0, 15.0, 11.5), (0, 13.2, 11.5)], [[0, 1, 2, 3]], alu)
    fin.modifiers.new('t', 'SOLIDIFY').thickness = 0.3; fin.parent = r
    tp = mesh_obj(name + '_tailplane', [(-7.0, 13.0, 3.6), (7.0, 13.0, 3.6), (7.0, 14.8, 3.6), (-7.0, 14.8, 3.6)], [[0, 1, 2, 3]], alu)
    tp.modifiers.new('t', 'SOLIDIFY').thickness = 0.25; tp.parent = r
    if gear:
        tyre = rubber('tyre')
        for x in (-5.6, 5.6):
            cyl(f'{name}_strut{x}', (x, -2.0, 1.6), 0.12, 2.4, alu, parent=r)
            for dx in (-0.3, 0.3):
                _wheel(f'{name}_mw{x}{dx}', (x + dx, -2.0, 0.7), 0.7, 0.4, tyre, alu, r)
        cyl(name + '_nosestrut', (0, -12.0, 1.4), 0.08, 2.0, alu, parent=r)
        _wheel(name + '_nw', (0, -12.0, 0.45), 0.45, 0.25, tyre, alu, r)
    return _adopt(r, before)


def jet(loc=(0, 0, 0), heading_deg=0.0, name='jet', color=(0.7, 0.71, 0.72)):
    """1950s swept-wing jet (F-86 / MiG-15 class shape): nose intake, bubble canopy, 35-deg swept wings + tail."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    alu = mat(f'jet_{color}', color, metal=1.0, rough=0.3)
    fus = lathe(name + '_fus', [(0.45, 0.0), (0.6, 0.6), (0.68, 3.0), (0.6, 8.0), (0.42, 11.2), (0.38, 11.4)], alu)
    fus.rotation_euler.x = math.radians(90); fus.location = (0, -5.7, 1.6); fus.parent = r
    cyl(name + '_intake', (0, -5.72, 1.6), 0.4, 0.04, mat('intake_dark', (0.01, 0.01, 0.01)), rot=(math.pi / 2, 0, 0), parent=r)
    sphere(name + '_canopy', (0, -3.2, 2.15), 0.42, mat('cockpit_glass', (0.1, 0.12, 0.13), rough=0.04), parent=r, scale=(0.9, 2.0, 0.8))
    sw = math.tan(math.radians(35))
    wv = [(0, -1.5, 1.4), (5.7, -1.5 + 5.7 * sw, 1.4), (5.7, -0.3 + 5.7 * sw, 1.4), (0, 1.4, 1.4)]
    for sx in (-1, 1):
        o = mesh_obj(f'{name}_wing{sx}', [(sx * x, y, z) for x, y, z in wv], [[0, 1, 2, 3]], alu)
        o.modifiers.new('t', 'SOLIDIFY').thickness = 0.14; o.parent = r
        o = mesh_obj(f'{name}_tp{sx}', [(sx * x * 0.4, y * 0.4 + 4.6, 2.1) for x, y, z in wv], [[0, 1, 2, 3]], alu)
        o.modifiers.new('t', 'SOLIDIFY').thickness = 0.08; o.parent = r
    fin = mesh_obj(name + '_fin', [(0, 3.4, 2.0), (0, 5.6, 2.0), (0, 6.4, 3.9), (0, 5.4, 3.9)], [[0, 1, 2, 3]], alu)
    fin.modifiers.new('t', 'SOLIDIFY').thickness = 0.1; fin.parent = r
    return _adopt(r, before)


# ------------------------------------------------------------------ rockets
def _fins(name, n, root_z, h, span, chord, m, parent, r0, sweep=0.6, offset=0.0):
    for k in range(n):
        a = k * 2 * math.pi / n + offset
        v = [(r0, 0, root_z), (r0, 0, root_z + chord), (r0 + span, 0, root_z + chord * (1 - sweep)), (r0 + span, 0, root_z - h * 0.1)]
        o = mesh_obj(f'{name}_fin{k}', v, [[0, 1, 2, 3]], m); o.rotation_euler.z = a; o.parent = parent
        o.modifiers.new('t', 'SOLIDIFY').thickness = 0.06


def rocket(kind='v2', loc=(0, 0, 0), heading_deg=0.0, name=None):
    """kind: 'v2' (A-4, 14 m, black/white roll pattern, 4 big fins), 'redstone' (Mercury-Redstone, white body, black
    Mercury capsule + red escape tower, 25 m), 'r7' (Vostok: core stage + 4 conical strap-on boosters, ~31 m, grey-green).
    Origin = base of the rocket (nozzle exit plane at z=0)."""
    name = name or f'rocket_{kind}'
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    white = mat('rocket_white', (0.8, 0.79, 0.75), rough=0.45)
    black = mat('rocket_black', (0.02, 0.02, 0.02), rough=0.45)
    if kind == 'v2':
        prof = [(0.5, 0.0), (0.82, 1.0), (0.83, 6.5), (0.75, 9.0), (0.5, 11.8), (0.2, 13.6), (0.0, 14.0)]
        body = lathe(name + '_body', prof, white, parent=r)
        # the famous black-and-white quartered roll pattern (so film could see it spin): black panels by angle
        # a slightly bigger black skin over the body, then keep only the panels of a checker: quadrant (x>0 xor
        # y>0) flipped every 2.2 m of height
        q = lathe(name + '_quarters', [(p[0] + 0.005, p[1]) for p in prof[1:5]], black, segs=48, parent=r)
        bm_keep = [f.index for f in q.data.polygons if ((f.center.x > 0) ^ (f.center.y > 0)) ^ (int(f.center.z / 2.2) % 2 == 0)]
        import bmesh
        bm = bmesh.new(); bm.from_mesh(q.data); bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.faces[i] for i in range(len(bm.faces)) if i not in set(bm_keep)], context='FACES')
        bm.to_mesh(q.data); bm.free()
        _fins(name, 4, 0.1, 3.5, 1.0, 3.2, black, r, 0.6, sweep=0.55, offset=math.radians(45))
        cyl(name + '_nozzle', (0, 0, 0.2), 0.42, 0.4, mat('nozzle', (0.08, 0.07, 0.06), metal=0.8, rough=0.5), parent=r)
    elif kind == 'redstone':
        body = lathe(name + '_body', [(0.89, 0.0), (0.89, 17.8), (0.85, 18.3)], white, parent=r)
        black_band = lathe(name + '_band', [(0.9, 16.5), (0.9, 17.3)], black, parent=r)
        cap = lathe(name + '_capsule', [(0.85, 18.3), (0.95, 18.4), (0.55, 20.3), (0.4, 20.6), (0.4, 21.4)], black, parent=r)
        red = mat('tower_red', (0.55, 0.06, 0.04), rough=0.5)
        for k in range(3):                                         # escape tower lattice (3 legs + rocket)
            a = k * 2 * math.pi / 3
            o = cyl(f'{name}_tower{k}', (0.25 * math.cos(a), 0.25 * math.sin(a), 22.6), 0.025, 2.4, red, parent=r, verts=6)
            o.rotation_euler = (0.08 * math.sin(a), -0.08 * math.cos(a), 0)
        lathe(name + '_escape', [(0.0, 23.7), (0.15, 23.8), (0.15, 25.0), (0.0, 25.4)], red, parent=r)
        _fins(name, 4, 0.0, 1.5, 0.9, 1.6, black, r, 0.89, sweep=0.2, offset=math.radians(45))
    elif kind == 'r7':
        grey = mat('r7_grey', (0.42, 0.45, 0.4), rough=0.55)
        lathe(name + '_core', [(0.6, 0.0), (1.3, 4.0), (1.48, 19.0), (1.3, 20.5), (1.35, 23.0), (1.3, 27.5), (1.2, 28.5), (0.6, 30.5), (0.0, 31.0)], grey, parent=r)
        for k in range(4):                                         # the strap-on boosters: long cones (iconic Vostok look)
            a = k * math.pi / 2
            b = lathe(f'{name}_booster{k}', [(0.0, 0.0), (1.35, 0.3), (1.35, 3.0), (0.9, 12.0), (0.35, 19.0), (0.0, 19.6)], grey, parent=r)
            b.location = (2.0 * math.cos(a), 2.0 * math.sin(a), 0.0)
            v = mesh_obj(f'{name}_vane{k}', [(1.3, 0, 0.2), (1.3, 0, 2.2), (2.1, 0, 1.6), (2.1, 0, 0.4)], [[0, 1, 2, 3]], grey)
            v.location = b.location; v.rotation_euler.z = a; v.parent = r; v.modifiers.new('t', 'SOLIDIFY').thickness = 0.05
    return _adopt(r, before)


def launch_tower(loc=(0, 0, 0), height=30.0, heading_deg=0.0, name='gantry'):
    """Steel umbilical/service tower beside a pad: 4 legs, horizontal girders every 3 m, X-bracing, swing arms."""
    before = set(bpy.data.objects); r = root_empty(name, loc, heading_deg)
    steel = worn_paint('gantry_red', (0.35, 0.08, 0.05), metal=0.5, wear=0.3)
    s = 2.4
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(f'{name}_leg{sx}{sy}', (sx * s / 2, sy * s / 2, height / 2), 0.09, height, steel, verts=8, parent=r)
    for k in range(int(height / 3) + 1):
        z = k * 3.0
        for (cx, cy, lx, ly) in ((0, s / 2, s, 0.12), (0, -s / 2, s, 0.12), (s / 2, 0, 0.12, s), (-s / 2, 0, 0.12, s)):
            box(f'{name}_g{k}{cx}{cy}', (cx, cy, z), (lx, ly, 0.12), steel, 0, parent=r)
        if k < int(height / 3):
            for (cx, cy, rotz) in ((0, s / 2, 0), (0, -s / 2, 0), (s / 2, 0, math.pi / 2), (-s / 2, 0, math.pi / 2)):
                for sgn in (-1, 1):
                    o = box(f'{name}_x{k}{cx}{cy}{sgn}', (cx, cy, z + 1.5), (math.hypot(s, 3.0), 0.06, 0.06), steel, 0, parent=r)
                    o.rotation_euler = (0, sgn * math.atan2(3.0, s), rotz)
    for z in (height * 0.55, height * 0.8):
        box(f'{name}_arm{z}', (-s / 2 - 2.0, 0, z), (4.0, 0.5, 0.3), steel, 0, parent=r)
    return _adopt(r, before)

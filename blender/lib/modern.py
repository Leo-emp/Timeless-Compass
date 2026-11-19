# MODERN ERA SETS (1940s-60s secret government projects: Manhattan Project, Cold War labs, MKUltra, Area 51...).
# Built by code from period photographs (Los Alamos, Oak Ridge, Hanford control rooms, government offices):
#   painted plaster walls (institutional green/cream), worn linoleum or concrete floors, fluorescent tube panels,
#   steel workbenches, control panels with round dials and toggle switches, chalkboards, steel filing cabinets,
#   wall clocks, desk lamps, metal chairs. Moody: hard overhead light pools + dark corners (rule r10).
import math
import random

import bpy
from mathutils import Vector

from lib.common import link, principled


def _scan(name, scan, tint, tiles, rough=(0.5, 0.9)):
    try:
        from lib import scatter
        return scatter.scan_material(name, scan, tint=tint, tiles=tiles, rough=rough)
    except Exception:
        return principled(name, tint, rough=0.8)


def _box(name, c, sz, m, bevel=0.01):
    bpy.ops.mesh.primitive_cube_add(size=1, location=c); o = bpy.context.object; o.name = name; o.scale = sz
    if bevel:
        bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = bevel; bv.segments = 2
    o.data.materials.append(m)
    return o


def steel(name='painted_steel', color=(0.18, 0.22, 0.2)):
    m = bpy.data.materials.get(name)
    return m or principled(name, color, metal=0.6, rough=0.45, bump=0.05, bump_scale=300)


def fluorescent(loc, length=1.2, name='tube', power=60.0, flicker=False, frames=(1, 240), seed=0):
    """A ceiling fixture: steel housing + glowing tube + an area light pointing down (+ optional flicker)."""
    housing = _box(name + '_housing', loc, (length, 0.22, 0.08), steel(), 0.005)
    tube_m = bpy.data.materials.new(name + '_glow'); nt = tube_m.node_tree
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (0.9, 0.97, 1.0, 1); em.inputs['Strength'].default_value = 25
    nt.links.new(em.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    _box(name + '_tube', (loc[0], loc[1], loc[2] - 0.045), (length * 0.95, 0.06, 0.02), tube_m, 0)
    bpy.ops.object.light_add(type='AREA', location=(loc[0], loc[1], loc[2] - 0.07))
    lt = bpy.context.object; lt.name = name + '_light'; lt.data.shape = 'RECTANGLE'
    lt.data.size, lt.data.size_y = length, 0.2; lt.data.energy = power; lt.data.color = (0.88, 0.95, 1.0)
    if flicker:                                                 # one tired tube flickers (classic tension beat)
        rnd = random.Random(seed); f = frames[0]
        while f < frames[1]:
            on = rnd.random() > 0.12
            lt.data.energy = power * (1 if on else 0.15); lt.data.keyframe_insert('energy', frame=f)
            em.inputs['Strength'].default_value = 25 if on else 2; em.inputs['Strength'].keyframe_insert('default_value', frame=f)
            f += rnd.choice((2, 3, 5, 9, 14))
    return housing


def control_panel(loc, width=3.0, height=1.9, heading_deg=0.0, seed=0, name='panel'):
    """Wall of instruments: steel cabinet, rows of round dial gauges (white faces, black needles at random angles),
    toggle switches, a few glowing indicator lamps."""
    rnd = random.Random(seed)
    root = bpy.data.objects.new(name, None); link(root)
    parts = [_box(name + '_cab', (0, 0, height / 2), (width, 0.45, height), steel(f'{name}_steel', (0.2, 0.25, 0.22)))]
    face = principled(f'{name}_dialface', (0.85, 0.83, 0.76), rough=0.4)
    black = principled(f'{name}_black', (0.02, 0.02, 0.02), rough=0.4)
    lamp_m = []
    for c in ((1.0, 0.2, 0.1), (1.0, 0.75, 0.2), (0.3, 1.0, 0.4)):
        m = bpy.data.materials.new(f'{name}_lamp_{c}'); nt = m.node_tree
        e = nt.nodes.new('ShaderNodeEmission'); e.inputs['Color'].default_value = (*c, 1); e.inputs['Strength'].default_value = 8
        nt.links.new(e.outputs[0], nt.nodes['Material Output'].inputs['Surface']); lamp_m.append(m)
    cols = int(width / 0.32)
    for row, z in enumerate((height * 0.8, height * 0.62)):
        for k in range(cols):
            x = -width / 2 + 0.2 + k * (width - 0.4) / max(cols - 1, 1)
            bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.1, depth=0.03, location=(x, -0.235, z), rotation=(math.pi / 2, 0, 0))
            d = bpy.context.object; d.data.materials.append(face); parts.append(d)
            a = rnd.uniform(-2.2, 0.6)
            n = _box(f'{name}_needle_{row}_{k}', (x + 0.04 * math.cos(a), -0.252, z + 0.04 * math.sin(a)), (0.09, 0.004, 0.006), black, 0)
            n.rotation_euler = (0, -a, 0); parts.append(n)
    for k in range(cols * 2):                                    # toggle switches + lamps on the sloped desk part
        x = -width / 2 + 0.15 + k * (width - 0.3) / max(cols * 2 - 1, 1)
        s = _box(f'{name}_sw{k}', (x, -0.24, height * 0.42), (0.02, 0.05, 0.02), black, 0); s.rotation_euler = (rnd.choice((0.4, -0.4)), 0, 0)
        parts.append(s)
        if rnd.random() < 0.3:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=0.018, location=(x, -0.235, height * 0.5))
            l = bpy.context.object; l.data.materials.append(rnd.choice(lamp_m)); parts.append(l)
    for p in parts:
        p.parent = root
    root.location = loc; root.rotation_euler.z = math.radians(heading_deg)
    return root


def chalkboard(loc, w=3.2, h=1.3, heading_deg=0.0, name='chalkboard'):
    """Black slate board in a wooden frame, smudged with chalk (equations are drawn in shots that need them)."""
    root = bpy.data.objects.new(name, None); link(root)
    slate = principled(f'{name}_slate', (0.04, 0.045, 0.045), rough=0.85, bump=0.05)
    nt = slate.node_tree; b = nt.nodes['Principled BSDF']
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 4
    r = nt.nodes.new('ShaderNodeMapRange'); r.inputs['From Min'].default_value = 0.55; r.inputs['From Max'].default_value = 0.8
    r.inputs['To Max'].default_value = 0.25; nt.links.new(n.outputs['Fac'], r.inputs['Value'])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['A'].default_value = (0.04, 0.045, 0.045, 1)
    mx.inputs['B'].default_value = (0.5, 0.5, 0.48, 1); nt.links.new(r.outputs['Result'], mx.inputs['Factor'])
    nt.links.new(mx.outputs['Result'], b.inputs['Base Color'])                   # chalk dust smudges
    wood = principled(f'{name}_frame', (0.25, 0.15, 0.08), rough=0.7)
    parts = [_box(name + '_slate', (0, 0, 0), (w, 0.03, h), slate, 0), _box(name + '_frame_t', (0, -0.01, h / 2 + 0.03), (w + 0.1, 0.05, 0.06), wood),
             _box(name + '_frame_b', (0, -0.03, -h / 2 - 0.05), (w + 0.1, 0.1, 0.06), wood)]
    for p in parts:
        p.parent = root
    root.location = loc; root.rotation_euler.z = math.radians(heading_deg)
    return root


def lab_1950s(w=14.0, d=10.0, h=3.4, name='lab', flicker=True):
    """A classified laboratory c. 1945-1960: green-and-cream painted plaster walls, worn linoleum, fluorescent tubes
    (one flickering), a wall of control panels, workbenches with equipment, a chalkboard, filing cabinets, a clock.
    Origin = floor centre; the panels are on the north wall (+Y), the chalkboard on the west wall (-X)."""
    root = bpy.data.objects.new(name, None); link(root)
    floor_m = _scan(f'{name}_floor', 'linoleum_brown', (0.85, 0.8, 0.72), 2.0, (0.35, 0.7))
    wall_m = _scan(f'{name}_wall', 'grey_plaster_02', (0.62, 0.72, 0.6), 2.5)                 # institutional green
    upper_m = _scan(f'{name}_wall_up', 'grey_plaster_02', (0.9, 0.88, 0.78), 2.5)             # cream above
    ceil_m = principled(f'{name}_ceiling', (0.75, 0.74, 0.7), rough=0.9)
    parts = [_box(name + '_floor', (0, 0, -0.05), (w, d, 0.1), floor_m, 0), _box(name + '_ceiling', (0, 0, h + 0.05), (w, d, 0.1), ceil_m, 0)]
    for (x, y, sw, sd) in ((0, d / 2, w, 0.2), (0, -d / 2, w, 0.2), (w / 2, 0, 0.2, d), (-w / 2, 0, 0.2, d)):
        parts.append(_box(f'{name}_wall_{x}_{y}', (x, y, 0.75), (sw, sd, 1.5), wall_m, 0))         # green dado
        parts.append(_box(f'{name}_wallup_{x}_{y}', (x, y, 1.5 + (h - 1.5) / 2), (sw, sd, h - 1.5), upper_m, 0))
    for i, x in enumerate((-4.5, 0.0, 4.5)):
        for j, y in enumerate((-2.5, 2.5)):
            fluorescent((x, y, h - 0.05), name=f'{name}_tube_{i}{j}', flicker=flicker and i == 2 and j == 0, seed=i * 3 + j)
    control_panel((0, d / 2 - 0.35, 0), width=6.0, heading_deg=0, name=f'{name}_panel')
    chalkboard((-w / 2 + 0.12, 0, 1.6), heading_deg=90, name=f'{name}_board')
    bench_m = steel(f'{name}_bench', (0.3, 0.3, 0.28))
    top_m = principled(f'{name}_benchtop', (0.08, 0.08, 0.08), rough=0.5)
    for k, x in enumerate((-3.0, 2.5)):
        parts.append(_box(f'{name}_bench{k}', (x, -0.5, 0.45), (3.0, 0.9, 0.9), bench_m))
        parts.append(_box(f'{name}_benchtop{k}', (x, -0.5, 0.92), (3.1, 0.95, 0.04), top_m))
        for e in range(3):                                         # boxes of equipment on the benches
            parts.append(_box(f'{name}_equip{k}{e}', (x - 1.0 + e, -0.6, 1.1), (0.45, 0.35, 0.32), steel(f'{name}_eq{e}', (0.25, 0.27, 0.3))))
    for k in range(4):                                             # steel filing cabinets
        parts.append(_box(f'{name}_cabinet{k}', (w / 2 - 0.4, -3.5 + k * 0.55, 0.7), (0.6, 0.5, 1.4), steel(f'{name}_file', (0.35, 0.36, 0.32))))
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.18, depth=0.04, location=(w / 2 - 0.12, 2.0, 2.6), rotation=(0, math.pi / 2, 0))
    clock = bpy.context.object; clock.data.materials.append(principled(f'{name}_clock', (0.9, 0.9, 0.86), rough=0.4)); parts.append(clock)
    for p in parts:
        if p.parent is None:
            p.parent = root
    return root

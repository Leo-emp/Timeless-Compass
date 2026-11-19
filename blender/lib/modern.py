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


# =====================================================================================================================
# WS17 (Session F): the modern-era SET LIBRARY. Every set: origin = floor centre, returns its root empty, built from
# period photographs (sources in each docstring). Props come from lib/modern_props.py. Light is the caller's
# (lighting.film_lights) EXCEPT practical lights that belong to the set (fluorescent tubes, bulbs, screens).
# =====================================================================================================================
def _room(name, w, d, h, floor_m, wall_m, upper_m=None, ceil_m=None, dado=1.2, open_sides=(), wall_t=0.2):
    """Four walls (two-tone if upper_m: painted dado below, lighter paint above), floor, ceiling. open_sides: any of
    'N','S','E','W' left out so a camera can sit outside the room."""
    parts = [_box(name + '_floor', (0, 0, -0.05), (w, d, 0.1), floor_m, 0)]
    if ceil_m is not None:
        parts.append(_box(name + '_ceiling', (0, 0, h + 0.05), (w, d, 0.1), ceil_m, 0))
    for side, (x, y, sw, sd) in {'N': (0, d / 2, w, wall_t), 'S': (0, -d / 2, w, wall_t), 'E': (w / 2, 0, wall_t, d),
                                 'W': (-w / 2, 0, wall_t, d)}.items():
        if side in open_sides:
            continue
        if upper_m is None:
            parts.append(_box(f'{name}_wall{side}', (x, y, h / 2), (sw, sd, h), wall_m, 0))
        else:
            parts.append(_box(f'{name}_wall{side}', (x, y, dado / 2), (sw, sd, dado), wall_m, 0))
            parts.append(_box(f'{name}_wallup{side}', (x, y, dado + (h - dado) / 2), (sw, sd, h - dado), upper_m, 0))
    return parts


def _parent(root, before):
    for o in set(bpy.data.objects) - before:
        if o.parent is None and o is not root:
            o.parent = root
    return root


def government_office(w=7.0, d=5.5, h=3.2, name='gov_office', sun=True, blinds_tilt=38.0):
    """A US government office c. 1945-60 (OSS / War Department / early CIA, Washington): dark oak wainscot below a
    cream-painted wall, worn linoleum, a wall of tall windows behind VENETIAN BLINDS (sunlight falls through in bars,
    with dust in the air), two steel desks with typewriter / rotary phone / folder stacks / desk lamps, a row of
    filing cabinets (one drawer open), wall clock, coat rack, hanging globe lights.
    Sources: National Archives photos of War Department + OSS offices (RG 165, RG 226), CIA "Our First Headquarters"
    (E Street complex, CIA.gov history). Windows on the north wall (+Y); door side = -Y (open for the camera)."""
    from lib import modern_props as P
    before = set(bpy.data.objects); root = bpy.data.objects.new(name, None); link(root)
    floor_m = _scan(f'{name}_floor', 'linoleum_brown', (0.7, 0.62, 0.5), 1.6, (0.3, 0.6))
    wood_m = principled(f'{name}_wainscot', (0.12, 0.065, 0.03), rough=0.4, bump=0.02, bump_scale=300)
    paint_m = _scan(f'{name}_wall', 'plastered_wall_02', (0.86, 0.8, 0.66), 2.0)
    ceil_m = principled(f'{name}_ceiling', (0.8, 0.78, 0.72), rough=0.9)
    _room(name, w, d, h, floor_m, wood_m, paint_m, ceil_m, dado=1.05, open_sides=('S', 'N'))
    # north wall with 3 tall windows (wall pieces between them), glass, blinds
    win_w, win_h, sill = 1.25, 1.9, 0.85
    xs = (-2.3, 0.0, 2.3)
    edges = [-w / 2] + [v for x in xs for v in (x - win_w / 2, x + win_w / 2)] + [w / 2]
    for k in range(0, len(edges), 2):                                 # wall panels between windows
        a, b = edges[k], edges[k + 1]
        _box(f'{name}_pier{k}', ((a + b) / 2, d / 2, h / 2), (b - a, 0.25, h), paint_m, 0)
    for x in xs:
        _box(f'{name}_under{x}', (x, d / 2, sill / 2), (win_w, 0.25, sill), wood_m, 0)
        _box(f'{name}_over{x}', (x, d / 2, (sill + win_h + h) / 2), (win_w, 0.25, h - sill - win_h), paint_m, 0)
        _box(f'{name}_glass{x}', (x, d / 2 + 0.05, sill + win_h / 2), (win_w, 0.01, win_h), P.glass(), 0)
        _box(f'{name}_mullion{x}', (x, d / 2 - 0.02, sill + win_h / 2), (0.04, 0.05, win_h), wood_m, 0)
        P.venetian_blinds((x, d / 2 - 0.12, sill + win_h / 2), width=win_w - 0.05, height=win_h - 0.05, heading_deg=0,
                          tilt_deg=blinds_tilt, name=f'{name}_blinds{x}')
    if sun:                                                           # hard low sun through the blinds -> light bars
        s = bpy.data.lights.new(name + '_sun', 'SUN'); s.energy = 6.0; s.color = (1.0, 0.88, 0.7); s.angle = math.radians(0.6)
        so = bpy.data.objects.new(name + '_sun', s); link(so); so.rotation_euler = (math.radians(-62), 0, math.radians(160))
        # dusty air so the bars of light show as SHAFTS (volume scatter in a box filling the room)
        haze = bpy.data.materials.new(name + '_haze'); nt = haze.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
        vs = nt.nodes.new('ShaderNodeVolumeScatter'); vs.inputs['Density'].default_value = 0.035; vs.inputs['Anisotropy'].default_value = 0.6
        nt.links.new(vs.outputs[0], nt.nodes['Material Output'].inputs['Volume'])
        _box(name + '_haze', (0, 0, h / 2), (w - 0.1, d - 0.1, h - 0.05), haze, 0).visible_shadow = False
    # furniture + desk dressing
    for k, (x, y, hd) in enumerate(((-1.6, 0.6, 180), (1.7, 0.2, 165))):
        P.desk((x, y, 0), hd, f'{name}_desk{k}', seed=k)
        P.office_chair((x, y + 0.75, 0), hd, f'{name}_chair{k}')
        top = 0.76
        c, sn = math.cos(math.radians(hd)), math.sin(math.radians(hd))
        def on(dx, dy):                                               # point on the desk top in the desk's frame
            return (x + dx * c - dy * sn, y + dx * sn + dy * c, top)
        P.typewriter(on(-0.1, 0.05), hd, f'{name}_tw{k}')
        P.rotary_phone(on(0.55, -0.15), hd + 15, f'{name}_phone{k}')
        P.folder_stack(on(-0.55, -0.12), hd - 10, n=4 + k, name=f'{name}_files{k}', seed=k + 3)
        P.desk_lamp(on(0.55, 0.2), hd + 200, f'{name}_lamp{k}', on=True)
        P.folder(on(0.15, -0.28), hd + 8, f'{name}_open{k}', stamp='TOP SECRET', open_=True, seed=9 + k)
    for k in range(4):
        P.filing_cabinet((-w / 2 + 0.45, -1.2 + k * 0.45, 0), 90, f'{name}_file{k}', open_drawer=1 if k == 2 else None, seed=k)
    P.wall_clock((w / 2 - 0.12, 0.5, 2.35), -90, f'{name}_clock', hour=11, minute=40)
    for k, x in enumerate((-1.6, 1.7)):                               # schoolhouse globe pendant lights
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.17, location=(x, 0.4, h - 0.55)); g = bpy.context.object
        g.data.materials.append(P.emit('globe_glow', (1.0, 0.86, 0.62), 6.0)); g.name = f'{name}_globe{k}'
        _box(f'{name}_rod{k}', (x, 0.4, h - 0.22), (0.015, 0.015, 0.45), P.chrome(), 0)
        bpy.ops.object.light_add(type='POINT', location=(x, 0.4, h - 0.6)); L_ = bpy.context.object
        L_.data.energy = 60; L_.data.color = (1.0, 0.8, 0.55); L_.data.shadow_soft_size = 0.17; L_.name = f'{name}_globe_light{k}'
    rack = P.cyl(f'{name}_rack', (w / 2 - 0.4, -d / 2 + 0.6, 0.9), 0.02, 1.8, wood_m)
    return _parent(root, before)


def bunker_command(w=12.0, d=9.0, h=3.6, name='bunker'):
    """Underground Cold War command room (SAC / NORAD-style, c. 1955-62): raw board-formed concrete walls under a
    shallow BARREL VAULT, steel blast door with wheel, a big illuminated wall MAP BOARD (status lights over a world
    map grid), a long plotting table under hard pools of light, consoles with dials, red alert lamps, cable trays,
    pipes. Moody: almost no fill. Sources: SAC underground command post, Offutt AFB (1957, USAF photos), Greenbrier
    "Project Greek Island" bunker (1958-61), NORAD Cheyenne Mountain design drawings (1961)."""
    from lib import modern_props as P
    before = set(bpy.data.objects); root = bpy.data.objects.new(name, None); link(root)
    conc = _scan(f'{name}_concrete', 'concrete_floor_worn_001', (0.55, 0.55, 0.53), 3.0, (0.6, 0.95))
    floor_m = _scan(f'{name}_floor', 'concrete_floor_worn_001', (0.38, 0.38, 0.37), 2.0, (0.5, 0.85))
    _room(name, w, d, h * 0.7, floor_m, conc, open_sides=('S',), wall_t=0.5)
    # barrel vault: half-cylinder shell along X
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=d / 2, depth=w, location=(0, 0, h * 0.7), rotation=(0, math.pi / 2, 0))
    v = bpy.context.object; v.name = name + '_vault'; v.data.materials.append(conc); v.scale = (1, 1, 0.38)
    v.modifiers.new('shell', 'SOLIDIFY').thickness = 0.4
    for k in range(-4, 5):                                            # concrete ribs every 1.3 m
        bpy.ops.mesh.primitive_torus_add(major_radius=d / 2 - 0.05, minor_radius=0.12, location=(k * 1.3, 0, h * 0.7), rotation=(0, math.pi / 2, 0))
        r = bpy.context.object; r.scale = (1, 1, 0.38); r.data.materials.append(conc); r.name = f'{name}_rib{k}'
    # MAP BOARD on the north wall: dark board, a grid, glowing status lights
    board = principled(f'{name}_mapboard', (0.04, 0.07, 0.09), rough=0.6)
    _box(name + '_board', (0, d / 2 - 0.3, 2.1), (7.5, 0.08, 2.6), board, 0.01)
    gridm = P.emit('map_grid', (0.25, 0.55, 0.6), 0.6)
    for k in range(13):
        _box(f'{name}_gx{k}', (-3.6 + k * 0.6, d / 2 - 0.35, 2.1), (0.01, 0.01, 2.5), gridm, 0)
    for k in range(5):
        _box(f'{name}_gz{k}', (0, d / 2 - 0.35, 1.0 + k * 0.55), (7.4, 0.01, 0.01), gridm, 0)
    rnd = random.Random(4)
    lamps = [P.emit('lamp_red', (1.0, 0.12, 0.05), 25), P.emit('lamp_amber', (1.0, 0.6, 0.12), 18), P.emit('lamp_green', (0.3, 1.0, 0.4), 12)]
    for k in range(70):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4, radius=0.028, location=(rnd.uniform(-3.5, 3.5), d / 2 - 0.36, rnd.uniform(1.0, 3.2)))
        o = bpy.context.object; o.data.materials.append(rnd.choice(lamps)); o.name = f'{name}_status{k}'
    # plotting table + consoles
    _box(name + '_table', (0, 0.2, 0.85), (4.0, 1.6, 0.08), principled(f'{name}_tabletop', (0.08, 0.12, 0.1), rough=0.5), 0.01)
    _box(name + '_tablebase', (0, 0.2, 0.42), (3.6, 1.2, 0.8), P.worn_paint('bunker_grey', (0.2, 0.22, 0.21)), 0.01)
    control_panel((-4.0, d / 2 - 0.6, 0), width=3.0, heading_deg=0, seed=2, name=f'{name}_panelW')
    control_panel((4.0, d / 2 - 0.6, 0), width=3.0, heading_deg=0, seed=3, name=f'{name}_panelE')
    for k, x in enumerate((-3.0, 0.0, 3.0)):                          # caged ceiling lamps: hard pools of light
        bpy.ops.object.light_add(type='SPOT', location=(x, 0.2, h * 0.7 + 0.9)); s = bpy.context.object; s.name = f'{name}_pool{k}'
        s.data.energy = 900; s.data.spot_size = math.radians(55); s.data.spot_blend = 0.3; s.data.color = (1.0, 0.92, 0.78); s.data.shadow_soft_size = 0.08
        bpy.ops.mesh.primitive_cone_add(radius1=0.25, radius2=0.08, depth=0.2, location=(x, 0.2, h * 0.7 + 1.0)); c = bpy.context.object
        c.data.materials.append(P.worn_paint('lamp_shade_green', (0.06, 0.12, 0.08))); c.name = f'{name}_shade{k}'
    for k, x in enumerate((-5.5, 5.5)):                               # red rotating alert lamps
        P.sphere(f'{name}_alert{k}', (x, d / 2 - 0.3, 3.0), 0.1, P.emit('alert_red', (1.0, 0.05, 0.02), 40))
        bpy.ops.object.light_add(type='POINT', location=(x, d / 2 - 0.5, 3.0)); a = bpy.context.object
        a.data.energy = 120; a.data.color = (1.0, 0.08, 0.03); a.name = f'{name}_alert_light{k}'
    # blast door (west wall): thick round-cornered steel slab + locking wheel
    door_m = P.worn_paint('blast_door', (0.32, 0.33, 0.3), metal=0.6, wear=0.5)
    _box(name + '_door', (-w / 2 + 0.3, -1.5, 1.2), (0.35, 2.0, 2.3), door_m, 0.05)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.35, minor_radius=0.03, location=(-w / 2 + 0.52, -1.5, 1.2), rotation=(0, math.pi / 2, 0))
    bpy.context.object.data.materials.append(P.chrome()); bpy.context.object.name = name + '_wheel'
    pipe = P.worn_paint('pipe_paint', (0.25, 0.2, 0.12), wear=0.4)
    for k, z in enumerate((2.3, 2.45)):                               # pipes + cable tray along the east wall
        P.cyl(f'{name}_pipe{k}', (w / 2 - 0.35, 0, z), 0.06 + 0.02 * k, d - 0.6, pipe, rot=(math.pi / 2, 0, 0))
    return _parent(root, before)


def hangar(w=46.0, d=60.0, h=16.0, name='hangar', plane=True, doors_open=True):
    """A WWII-era steel arch hangar (Wendover Field / Tinian B-29 hangars, Area 51's 1955 hangars at Groom Lake):
    corrugated steel shell on lattice arches, worn concrete apron with oil stains + painted guide lines, the big door
    end open to bright desert light, a B-29-shaped bomber inside, jeeps and a truck, work lights.
    Sources: USAAF photos of the 509th Composite Group at Wendover + North Field, Tinian (1945, National Archives
    RG 342); CIA history "The CIA and the U-2 Program" (1998) for the Groom Lake hangars."""
    from lib import modern_props as P
    before = set(bpy.data.objects); root = bpy.data.objects.new(name, None); link(root)
    floor_m = _scan(f'{name}_floor', 'concrete_floor_worn_001', (0.62, 0.6, 0.56), 8.0, (0.45, 0.85))
    _box(name + '_floor', (0, 0, -0.05), (w + 30, d + 60, 0.1), floor_m, 0)
    shell = P.worn_paint('hangar_corrugated', (0.42, 0.42, 0.4), metal=0.7, wear=0.3, rough=0.55)
    nt = shell.node_tree; b = nt.nodes['Principled BSDF']           # corrugation: wave bump across the sheets
    wv = nt.nodes.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Y'; wv.inputs['Scale'].default_value = 300
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.6
    nt.links.new(wv.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=w / 2, depth=d, location=(0, 0, 0), rotation=(math.pi / 2, 0, 0))
    arc = bpy.context.object; arc.name = name + '_shell'; arc.data.materials.append(shell); arc.scale = (1, 1, 1)
    arc.scale = (1.0, h / (w / 2), 1.0)                               # squash the circle to the hangar's height
    arc.modifiers.new('shell', 'SOLIDIFY').thickness = 0.15
    bis = arc.modifiers.new('cut', 'BOOLEAN')                         # keep only the upper half (above the floor)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -w / 2)); cutter = bpy.context.object; cutter.scale = (w * 2, d * 2, w)
    cutter.hide_render = True; cutter.display_type = 'WIRE'; bis.object = cutter; bis.operation = 'DIFFERENCE'
    steel = P.worn_paint('arch_steel', (0.28, 0.29, 0.28), metal=0.7, wear=0.3)
    for k in range(9):                                                # lattice arch ribs
        y = -d / 2 + 2 + k * (d - 4) / 8
        bpy.ops.mesh.primitive_torus_add(major_radius=w / 2 - 0.5, minor_radius=0.25, location=(0, y, 0), rotation=(math.pi / 2, 0, 0),
                                         major_segments=64, minor_segments=6)
        r = bpy.context.object; r.scale = (1.0, h / (w / 2), 1.0); r.data.materials.append(steel); r.name = f'{name}_arch{k}'
        r.modifiers.new('cut', 'BOOLEAN').object = cutter
    # back wall (closed end); the front (-Y) end stays open to the light
    _box(name + '_endwall', (0, d / 2, h / 2), (w, 0.3, h), shell, 0)
    stain = principled(f'{name}_oil', (0.05, 0.045, 0.04), rough=0.25)
    rnd = random.Random(2)
    for k in range(14):                                               # oil stains on the concrete
        bpy.ops.mesh.primitive_circle_add(vertices=24, radius=rnd.uniform(0.3, 1.4), fill_type='NGON', location=(rnd.uniform(-12, 12), rnd.uniform(-20, 20), 0.005))
        o = bpy.context.object; o.data.materials.append(stain); o.scale = (1, rnd.uniform(0.5, 1.5), 1); o.name = f'{name}_stain{k}'
    line = principled(f'{name}_paintline', (0.6, 0.5, 0.12), rough=0.6)
    _box(name + '_guide', (0, -5, 0.004), (0.25, d * 0.85, 0.005), line, 0)
    if plane:
        P.bomber((0, 2.0, 0), 180, name + '_b29')
    P.jeep((-10, -14, 0), 25, name + '_jeep')
    P.army_truck((12, -6, 0), -10, name + '_truck')
    for k, (x, y) in enumerate(((-14, 10), (14, 12), (-6, 22), (8, -20))):   # work lights: hard pools under the arches
        bpy.ops.object.light_add(type='SPOT', location=(x, y, h - 2)); s = bpy.context.object; s.name = f'{name}_work{k}'
        s.data.energy = 15000; s.data.spot_size = math.radians(70); s.data.color = (1.0, 0.9, 0.75); s.data.shadow_soft_size = 0.3
    return _parent(root, before)


def desert_test_site(name='trinity_site', size=6000.0, tower=True, bunkers=True, mountains=True):
    """Trinity Site, Jornada del Muerto, New Mexico, 16 July 1945: flat creosote-bush desert; at ground zero the
    100-ft (30.5 m) steel TOWER with the corrugated-steel shot cab on top (the 'Gadget'); wooden instrument
    poles + cable lines; the observation bunkers N-10000, W-10000, S-10000 (10,000 yards = 9.1 km: timber + concrete
    shelters heaped with earth, a slit facing ground zero) - this set puts the SOUTH bunker + an observers' TRENCH
    near origin for the camera, ground zero 9 km to the north (+Y), the Oscura Mountains beyond.
    Sources: LANL "Trinity Site" history; National Park Service Manhattan Project NHP; US Army White Sands Missile
    Range Trinity Site fact sheet; Bainbridge, "Trinity" (LA-6300-H, 1976) for the tower, bunkers and distances.
    Returns the root; root['ground_zero'] = (x, y, z) of the tower base for fx.atomic_test."""
    from lib import modern_props as P
    before = set(bpy.data.objects); root = bpy.data.objects.new(name, None); link(root)
    gz = (0.0, 9100.0, 0.0)
    sand = _scan(f'{name}_sand', 'brown_mud_dry', (0.85, 0.72, 0.56), 4.0, (0.75, 1.0))
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=200, y_subdivisions=200, size=size * 2.6, location=(0, gz[1] * 0.5, 0))
    g = bpy.context.object; g.name = name + '_ground'; g.data.materials.append(sand)
    tex = bpy.data.textures.new(name + '_undulate', 'CLOUDS'); tex.noise_scale = 0.9
    dsp = g.modifiers.new('undulate', 'DISPLACE'); dsp.texture = tex; dsp.strength = 3.0; dsp.mid_level = 0.5
    dsp.texture_coords = 'GLOBAL'
    tex.noise_scale = 400.0
    # creosote bushes: thousands of small dark-green clumps (instanced) - the desert's only cover
    bush_m = principled(f'{name}_creosote', (0.07, 0.09, 0.04), rough=0.9)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.5, location=(0, 0, -100)); bush = bpy.context.object
    bush.name = name + '_bush'; bush.data.materials.append(bush_m); bush.scale = (1, 1, 0.6)
    tex2 = bpy.data.textures.new(name + '_bushnoise', 'CLOUDS'); tex2.noise_scale = 0.3
    d2 = bush.modifiers.new('lumpy', 'DISPLACE'); d2.texture = tex2; d2.strength = 0.35
    ps = g.modifiers.new('bushes', 'PARTICLE_SYSTEM'); st = ps.particle_system.settings
    st.type = 'HAIR'; st.count = 60000; st.use_advanced_hair = True; st.render_type = 'OBJECT'; st.instance_object = bush
    st.particle_size = 1.0; st.size_random = 0.7; st.use_rotation_instance = True; st.hair_length = 1.0
    st.use_emit_random = True
    if tower:                                                         # the 100-ft shot tower at ground zero
        tw = bpy.data.objects.new(name + '_tower', None); link(tw); tw.location = gz
        steel = P.worn_paint('tower_steel', (0.3, 0.3, 0.28), metal=0.6, wear=0.3)
        H, base, top = 30.5, 6.0, 3.0
        for sx in (-1, 1):
            for sy in (-1, 1):
                a, b_ = Vector((sx * base / 2, sy * base / 2, 0)), Vector((sx * top / 2, sy * top / 2, H))
                o = P.cyl(f'{name}_leg{sx}{sy}', tuple((a + b_) / 2), 0.15, (b_ - a).length, steel, verts=8, parent=tw)
                o.rotation_euler = (b_ - a).to_track_quat('Z', 'Y').to_euler()
        for k in range(1, 9):                                         # girders + X braces
            z = k * H / 9; s = base + (top - base) * z / H
            for (cx, cy, lx, ly) in ((0, s / 2, s, 0.1), (0, -s / 2, s, 0.1), (s / 2, 0, 0.1, s), (-s / 2, 0, 0.1, s)):
                _box(f'{name}_tg{k}{cx}{cy}', (cx + gz[0], cy + gz[1], z), (lx, ly, 0.1), steel, 0).parent = None
        cab_m = P.worn_paint('shot_cab', (0.55, 0.55, 0.52), metal=0.6, wear=0.2)
        _box(name + '_cab', (gz[0], gz[1], H + 1.5), (3.4, 3.4, 3.0), cab_m, 0.02)
        _box(name + '_platform', (gz[0], gz[1], H), (4.0, 4.0, 0.25), steel, 0)
    for k in range(20):                                               # instrument poles + cable line to the bunker
        y = 400 + k * 430
        P.cyl(f'{name}_pole{k}', (6.0, y, 4.0), 0.12, 8.0, principled('pole_wood', (0.2, 0.14, 0.08), rough=0.9))
    if bunkers:                                                       # S-10000 shelter: earth-banked timber + concrete
        conc = _scan(f'{name}_bunker_conc', 'concrete_floor_worn_001', (0.62, 0.58, 0.52), 4.0)
        timber = principled(f'{name}_timber', (0.22, 0.16, 0.1), rough=0.85, bump=0.1, bump_scale=80)
        _box(name + '_bunker', (0, 30, 1.4), (9.0, 6.0, 2.8), conc, 0.05)
        _box(name + '_slit', (0, 26.95, 1.9), (3.0, 0.2, 0.35), principled('slit_dark', (0.01, 0.01, 0.01)), 0)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 31, 1.0)); mound = bpy.context.object
        mound.scale = (9.0, 7.5, 3.4); mound.data.materials.append(sand); mound.name = name + '_earth'
        for k in range(10):                                           # timber roof beams poking out of the earth
            _box(f'{name}_beam{k}', (-4.5 + k, 27.0, 2.9), (0.25, 1.2, 0.25), timber, 0.01)
        # observers' trench (Compania Hill observers + base camp watched from trenches, lying face-down)
        _box(name + '_trench_floor', (0, 12, -0.9), (24.0, 1.4, 0.1), sand, 0)
        for sy in (-1, 1):
            o = _box(f'{name}_spoil{sy}', (0, 12 + sy * 1.4, 0.25), (24.0, 1.2, 0.6), sand, 0.2)
    if mountains:                                                     # Oscura Mountains behind ground zero
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=300, y_subdivisions=40, size=1, location=(0, gz[1] + 14000, 0))
        mt = bpy.context.object; mt.name = name + '_oscura'; mt.scale = (40000, 6000, 1)
        mt.data.materials.append(_scan(f'{name}_rock', 'rock_boulder_dry', (0.6, 0.5, 0.42), 0.0015))
        tx = bpy.data.textures.new(name + '_ridge', 'MUSGRAVE') if hasattr(bpy.types, 'MusgraveTexture') else bpy.data.textures.new(name + '_ridge', 'CLOUDS')
        tx.noise_scale = 0.25
        dm = mt.modifiers.new('ridge', 'DISPLACE'); dm.texture = tx; dm.strength = 1400; dm.texture_coords = 'LOCAL'
    root['ground_zero'] = gz
    return _parent(root, before)


def interrogation_room(w=4.0, d=4.5, h=2.7, name='interrogation'):
    """A 1950s interrogation room (Cold War military intelligence / FBI field office): bare painted cinder-block walls,
    stained concrete floor with a drain, one steel table + two chairs, a single bare bulb in a green enamel shade
    hanging low over the table (the only light), a one-way mirror window on one wall, an Ampex reel-to-reel on a side
    table recording, an ashtray, a folder. Sources: US Army Counter Intelligence Corps manuals + photos (NARA RG 319),
    CIA "KUBARK Counterintelligence Interrogation" manual (1963, CIA Reading Room) on the room ("bare", "one light",
    "hidden observers"). Camera side (-Y) open."""
    from lib import modern_props as P
    before = set(bpy.data.objects); root = bpy.data.objects.new(name, None); link(root)
    block = _scan(f'{name}_block', 'grey_plaster_02', (0.55, 0.6, 0.55), 3.0, (0.7, 0.95))
    nt = block.node_tree; b = nt.nodes['Principled BSDF']             # cinder-block courses: brick texture as bump
    br = nt.nodes.new('ShaderNodeTexBrick'); br.inputs['Scale'].default_value = 2.5; br.inputs['Mortar Size'].default_value = 0.012
    br.inputs['Brick Width'].default_value = 0.4; br.inputs['Row Height'].default_value = 0.2
    tcn = nt.nodes.new('ShaderNodeTexCoord'); nt.links.new(tcn.outputs['Object'], br.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.35; nt.links.new(br.outputs['Fac'], bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    floor_m = _scan(f'{name}_floor', 'concrete_floor_worn_001', (0.42, 0.4, 0.38), 1.5, (0.5, 0.9))
    ceil_m = principled(f'{name}_ceil', (0.5, 0.5, 0.48), rough=0.95)
    _room(name, w, d, h, floor_m, block, None, ceil_m, open_sides=('S',))
    P.cyl(name + '_drain', (0.6, -0.4, 0.003), 0.08, 0.004, P.mat('drain_iron', (0.05, 0.05, 0.05), metal=0.8, rough=0.6))
    steel = P.worn_paint('table_steel', (0.3, 0.31, 0.3), wear=0.5)
    _box(name + '_tabletop', (0, 0.3, 0.74), (1.2, 0.75, 0.04), steel, 0.005)
    for sx in (-1, 1):
        for sy in (-1, 1):
            _box(f'{name}_tleg{sx}{sy}', (sx * 0.55, 0.3 + sy * 0.33, 0.37), (0.04, 0.04, 0.74), steel, 0.003)
    for k, (y, hd) in enumerate(((0.95, 180), (-0.35, 0))):           # two steel chairs facing each other
        _box(f'{name}_seat{k}', (0, y, 0.45), (0.42, 0.42, 0.03), steel, 0.004)
        for sx in (-1, 1):
            for sy in (-1, 1):
                _box(f'{name}_cleg{k}{sx}{sy}', (sx * 0.19, y + sy * 0.19, 0.225), (0.025, 0.025, 0.45), steel, 0.002)
        _box(f'{name}_cback{k}', (0, y + (0.2 if hd == 180 else -0.2), 0.7), (0.42, 0.03, 0.4), steel, 0.004)
    # the single bulb: green enamel shade, bulb, hard spot down onto the table
    shade = P.lathe(name + '_shade', [(0.0, 0.0), (0.04, 0.0), (0.22, -0.13), (0.23, -0.14)], P.mat('shade_green', (0.02, 0.15, 0.07), rough=0.25))
    shade.location = (0, 0.3, 1.75)
    _box(name + '_cord', (0, 0.3, 1.75 + (h - 1.75) / 2), (0.008, 0.008, h - 1.75), P.bakelite(), 0)
    P.sphere(name + '_bulb', (0, 0.3, 1.66), 0.04, P.emit('bulb_bare', (1.0, 0.85, 0.6), 60))
    bpy.ops.object.light_add(type='SPOT', location=(0, 0.3, 1.67)); s = bpy.context.object; s.name = name + '_bulb_light'
    s.data.energy = 180; s.data.spot_size = math.radians(115); s.data.spot_blend = 0.4; s.data.color = (1.0, 0.82, 0.58)
    s.data.shadow_soft_size = 0.03; s.rotation_euler = (0, 0, 0)
    # one-way mirror (east wall): dark reflective pane in a steel frame
    mirror = principled(f'{name}_mirror', (0.03, 0.035, 0.035), metal=1.0, rough=0.04)
    _box(name + '_mirror', (w / 2 - 0.11, 0.2, 1.45), (0.02, 1.6, 0.9), mirror, 0)
    _box(name + '_mframe', (w / 2 - 0.1, 0.2, 1.45), (0.03, 1.7, 1.0), steel, 0.005)
    _box(name + '_side', (-w / 2 + 0.45, 1.3, 0.35), (0.6, 0.5, 0.7), steel, 0.005)
    P.reel_to_reel((-w / 2 + 0.45, 1.3, 0.7), 90, name + '_recorder', spin=True)
    P.folder((0.25, 0.25, 0.76), 12, name + '_file', stamp='SECRET', seed=4)
    P.cyl(name + '_ashtray', (-0.35, 0.45, 0.775), 0.06, 0.02, P.glass('ash_glass', (0.7, 0.75, 0.72)))
    return _parent(root, before)


def psych_ward(w=8.0, d=14.0, h=3.3, beds=6, name='ward'):
    """A 1950s psychiatric hospital ward (the MKUltra subprojects ran in hospitals: Allan Memorial Institute,
    Montreal; the Addiction Research Center, Lexington KY): glazed white tile to shoulder height, institutional
    green paint above, terrazzo floor, a row of white-enamelled iron-frame beds with grey blankets, privacy curtains
    on ceiling rails, an IV stand, a wheeled cart with an ELECTROSHOCK machine (box with dials + electrodes, like
    the Page-Russell modified machine Cameron used), tall barred windows, a fluorescent tube that flickers.
    Sources: Senate hearing "Project MKULTRA, the CIA's Program of Research in Behavioral Modification" (1977);
    CIA Reading Room MKULTRA subproject files; period hospital photos (Library and Archives Canada)."""
    from lib import modern_props as P
    before = set(bpy.data.objects); root = bpy.data.objects.new(name, None); link(root)
    tile = principled(f'{name}_tile', (0.78, 0.8, 0.76), rough=0.12)
    nt = tile.node_tree; b = nt.nodes['Principled BSDF']
    br = nt.nodes.new('ShaderNodeTexBrick'); br.offset = 0.0; br.inputs['Scale'].default_value = 6.5
    br.inputs['Mortar Size'].default_value = 0.01; br.inputs['Brick Width'].default_value = 0.5; br.inputs['Row Height'].default_value = 0.5
    tcn = nt.nodes.new('ShaderNodeTexCoord'); nt.links.new(tcn.outputs['Object'], br.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.3; bp.invert = True
    nt.links.new(br.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    green = _scan(f'{name}_paint', 'plastered_wall_02', (0.55, 0.68, 0.55), 2.5)
    floor_m = _scan(f'{name}_terrazzo', 'marble_01', (0.62, 0.6, 0.55), 3.0, (0.25, 0.5))
    ceil_m = principled(f'{name}_ceil', (0.82, 0.82, 0.78), rough=0.9)
    _room(name, w, d, h, floor_m, tile, green, ceil_m, dado=1.5, open_sides=('S',))
    enamel = P.mat('bed_enamel', (0.75, 0.75, 0.72), metal=0.3, rough=0.35)
    blanket = principled(f'{name}_blanket', (0.3, 0.31, 0.3), rough=0.95, bump=0.15, bump_scale=200)
    sheet = principled(f'{name}_sheet', (0.8, 0.8, 0.77), rough=0.85)
    for k in range(beds):                                             # beds along the west wall, heads to the wall
        y = -d / 2 + 2.0 + k * (d - 3.0) / max(beds - 1, 1)
        x0 = -w / 2 + 1.15
        for (dx, hh) in ((-0.95, 1.05), (0.95, 0.75)):               # iron head + foot frames
            for sy in (-1, 1):
                P.cyl(f'{name}_post{k}{dx}{sy}', (x0 + dx, y + sy * 0.45, hh / 2), 0.018, hh, enamel, verts=12)
            P.cyl(f'{name}_rail{k}{dx}', (x0 + dx, y, hh - 0.03), 0.015, 0.9, enamel, rot=(math.pi / 2, 0, 0), verts=12)
            for j in range(5):
                P.cyl(f'{name}_bar{k}{dx}{j}', (x0 + dx, y - 0.36 + j * 0.18, hh * 0.72), 0.008, hh * 0.45, enamel, verts=8)
        _box(f'{name}_mattress{k}', (x0, y, 0.55), (1.9, 0.88, 0.16), sheet, 0.04)
        bl = _box(f'{name}_blanket{k}', (x0 + 0.2, y, 0.64), (1.45, 0.95, 0.04), blanket, 0.02)
        _box(f'{name}_pillow{k}', (x0 - 0.78, y, 0.67), (0.3, 0.6, 0.1), sheet, 0.04)
        if k % 2 == 0:                                                # curtain rail + half-drawn curtain
            _box(f'{name}_crail{k}', (x0, y + 0.75, h - 0.3), (2.4, 0.02, 0.02), P.chrome(), 0)
            cur = principled(f'{name}_curtain', (0.62, 0.66, 0.6), rough=0.9)
            bpy.ops.mesh.primitive_plane_add(size=1, location=(x0 - 0.3, y + 0.75, h - 1.3), rotation=(math.pi / 2, 0, 0))
            c = bpy.context.object; c.scale = (1.4, 2.0, 1); c.data.materials.append(cur); c.name = f'{name}_curtain{k}'
            wav = c.modifiers.new('folds', 'WAVE'); wav.use_normal = True; wav.height = 0.04; wav.width = 0.12; wav.narrowness = 1.0
            c.modifiers.new('t', 'SOLIDIFY').thickness = 0.003
    for k in range(3):                                                # tall barred windows (east wall)
        y = -d / 2 + 3 + k * 4
        _box(f'{name}_window{k}', (w / 2 - 0.11, y, 1.9), (0.02, 1.0, 1.6), P.emit('window_day', (0.85, 0.9, 1.0), 2.5), 0)
        for j in range(6):
            P.cyl(f'{name}_wbar{k}{j}', (w / 2 - 0.15, y - 0.42 + j * 0.17, 1.9), 0.012, 1.6, P.mat('bar_iron', (0.05, 0.05, 0.05), metal=0.8))
        bpy.ops.object.light_add(type='AREA', location=(w / 2 - 0.3, y, 1.9)); a = bpy.context.object; a.name = f'{name}_daylight{k}'
        a.data.size = 1.0; a.data.size_y = 1.6; a.data.shape = 'RECTANGLE'; a.data.energy = 220; a.data.color = (0.85, 0.9, 1.0)
        a.rotation_euler = (0, math.radians(-90), 0)
    # ECT machine on a cart
    cart = P.worn_paint('cart_white', (0.72, 0.72, 0.7), wear=0.3)
    _box(name + '_cart', (1.2, 1.5, 0.75), (0.6, 0.45, 0.03), cart, 0.005)
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.cyl(f'{name}_cartleg{sx}{sy}', (1.2 + sx * 0.27, 1.5 + sy * 0.2, 0.38), 0.012, 0.74, P.chrome(), verts=8)
    ect = P.mat('ect_wood', (0.18, 0.1, 0.05), rough=0.4)
    _box(name + '_ect', (1.2, 1.5, 0.88), (0.42, 0.3, 0.22), ect, 0.01)
    _box(name + '_ect_panel', (1.2, 1.36, 0.92), (0.38, 0.01, 0.15), P.bakelite(), 0.003)
    for j in range(3):
        P.cyl(f'{name}_ect_dial{j}', (1.08 + j * 0.12, 1.35, 0.94), 0.025, 0.01, P.mat('meter_face', (0.88, 0.86, 0.78)), rot=(math.pi / 2, 0, 0))
    P.cyl(name + '_iv', (-w / 2 + 2.4, -d / 2 + 2.6, 0.9), 0.012, 1.8, P.chrome(), verts=8)
    P.sphere(name + '_ivbottle', (-w / 2 + 2.4, -d / 2 + 2.6, 1.75), 0.07, P.glass('iv_glass', (0.85, 0.9, 0.9)), scale=(1, 1, 1.6))
    for k, y in enumerate((-4.0, 0.0, 4.0)):
        fluorescent((0, y, h - 0.05), length=1.2, name=f'{name}_tube{k}', power=70, flicker=(k == 1), seed=k)
    return _parent(root, before)


def mission_control(w=18.0, d=14.0, h=4.5, rows=3, name='mission_control'):
    """Mercury Control Center, Cape Canaveral (1961-63): tiered rows of grey-green consoles with small round CRT
    screens and banks of push-button lamps; facing them a huge WORLD MAP wall with the tracking stations and the
    capsule's orbit track, plot boards on either side; low ceiling, dim room lit mostly by the consoles and the
    map. Sources: NASA "Mercury Control Center" photos (KSC history office, 1961-63), Kranz "Failure Is Not an
    Option" descriptions; NASA SP-4201 "This New Ocean" ch. on the control center."""
    from lib import modern_props as P
    before = set(bpy.data.objects); root = bpy.data.objects.new(name, None); link(root)
    floor_m = principled(f'{name}_carpet', (0.09, 0.1, 0.11), rough=0.95, bump=0.1, bump_scale=600)
    wall_m = principled(f'{name}_wall', (0.32, 0.34, 0.33), rough=0.8)
    ceil_m = principled(f'{name}_ceil', (0.2, 0.2, 0.2), rough=0.9)
    _room(name, w, d, h, floor_m, wall_m, None, ceil_m, open_sides=('S',))
    console = P.worn_paint('console_greygreen', (0.3, 0.36, 0.33), metal=0.3, wear=0.1)
    crt = P.emit('crt_green', (0.35, 1.0, 0.55), 2.0)
    btn = [P.emit('btn_white', (1.0, 0.95, 0.85), 3.0), P.emit('btn_amber', (1.0, 0.6, 0.15), 3.0), P.emit('btn_red', (1.0, 0.1, 0.05), 3.0),
           P.emit('btn_green', (0.3, 1.0, 0.35), 2.5)]
    rnd = random.Random(1)
    for r in range(rows):                                             # tiered rows (each row a step higher, further back)
        y = -1.5 - r * 2.6; z = r * 0.35
        if r:
            _box(f'{name}_tier{r}', (0, y - 0.3, z / 2), (w - 1, 2.6, z), floor_m, 0)
        n = 6 - r
        for k in range(n):
            x = (k - (n - 1) / 2) * 2.2
            _box(f'{name}_desk{r}{k}', (x, y, z + 0.38), (2.0, 0.8, 0.76), console, 0.01)
            hood = _box(f'{name}_hood{r}{k}', (x, y + 0.25, z + 0.98), (2.0, 0.35, 0.5), console, 0.02)
            hood.rotation_euler.x = math.radians(-20)
            for j in range(2):                                        # round CRTs
                P.cyl(f'{name}_crt{r}{k}{j}', (x - 0.45 + j * 0.9, y + 0.06, z + 1.0), 0.13, 0.01, crt, rot=(math.radians(70), 0, 0))
            for j in range(14):                                       # push-button lamp banks
                bpy.ops.mesh.primitive_cube_add(size=0.035, location=(x - 0.85 + (j % 7) * 0.28, y - 0.3, z + 0.78 + (j // 7) * 0.05))
                bpy.context.object.data.materials.append(rnd.choice(btn)); bpy.context.object.name = f'{name}_btn{r}{k}{j}'
            if k % 2 == 0:
                bpy.ops.object.light_add(type='AREA', location=(x, y + 0.05, z + 1.0)); a = bpy.context.object
                a.data.size = 1.2; a.data.energy = 18; a.data.color = (0.4, 1.0, 0.6); a.rotation_euler = (math.radians(-70), 0, 0)
                a.name = f'{name}_crtglow{r}{k}'
    # WORLD MAP wall (north): dark-blue board, pale continents (procedural blotches), glowing orbit sine track +
    # tracking-station lamps
    mapm = bpy.data.materials.new(name + '_worldmap'); nt = mapm.node_tree; b = nt.nodes['Principled BSDF']
    em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(em.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    tcn = nt.nodes.new('ShaderNodeTexCoord'); nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 5
    nt.links.new(tcn.outputs['Generated'], nz.inputs['Vector'])
    land = nt.nodes.new('ShaderNodeMapRange'); land.inputs['From Min'].default_value = 0.52; land.inputs['From Max'].default_value = 0.54
    nt.links.new(nz.outputs['Fac'], land.inputs['Value'])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['A'].default_value = (0.02, 0.06, 0.14, 1); mx.inputs['B'].default_value = (0.35, 0.42, 0.38, 1)
    nt.links.new(land.outputs['Result'], mx.inputs['Factor']); nt.links.new(mx.outputs['Result'], em.inputs['Color']); em.inputs['Strength'].default_value = 0.8
    _box(name + '_map', (0, d / 2 - 0.2, 2.5), (12.0, 0.05, 3.2), mapm, 0)
    track = P.emit('orbit_track', (1.0, 0.85, 0.3), 6.0)
    pts = 80
    for k in range(pts):                                              # orbit ground track (sine on a flat map)
        x = -5.8 + 11.6 * k / (pts - 1); z = 2.5 + 1.0 * math.sin(2 * math.pi * k / (pts - 1) * 1.5)
        bpy.ops.mesh.primitive_cube_add(size=0.05, location=(x, d / 2 - 0.25, z)); bpy.context.object.data.materials.append(track)
        bpy.context.object.name = f'{name}_trk{k}'
    for k in range(18):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4, radius=0.05, location=(rnd.uniform(-5.5, 5.5), d / 2 - 0.26, rnd.uniform(1.2, 3.8)))
        bpy.context.object.data.materials.append(btn[2]); bpy.context.object.name = f'{name}_station{k}'
    for sx in (-1, 1):                                                # plot boards
        _box(f'{name}_plot{sx}', (sx * 7.5, d / 2 - 0.2, 2.5), (2.5, 0.05, 3.0), P.emit('plot_board', (0.12, 0.2, 0.18), 0.6), 0)
    bpy.ops.object.light_add(type='AREA', location=(0, d / 2 - 2.0, 2.5)); a = bpy.context.object; a.name = name + '_mapglow'
    a.data.size = 10.0; a.data.size_y = 3.0; a.data.shape = 'RECTANGLE'; a.data.energy = 300; a.data.color = (0.5, 0.65, 1.0)
    a.rotation_euler = (math.radians(90), 0, 0)
    return _parent(root, before)


def los_alamos_huts(name='tech_area', rows=3, per_row=4):
    """Los Alamos Technical Area, 1943-45 ('the Hill'): hastily built two-storey wooden Army buildings - drop-siding
    painted Army green, pitched tar-paper roofs, rows of small-paned sash windows, outside wooden stairs - on bare
    dusty mesa ground with dirt roads, ponderosa pines, a chain-link + barbed-wire security fence with a guard
    tower, jeeps; the Jemez Mountains behind.
    Sources: LANL Historical photos (Tech Area, Fuller Lodge, T-buildings), Los Alamos Historical Museum; Hawkins,
    "Manhattan District History, Project Y" (LAMS-2532, 1961)."""
    from lib import modern_props as P
    before = set(bpy.data.objects); root = bpy.data.objects.new(name, None); link(root)
    dirt = _scan(f'{name}_dirt', 'brown_mud_dry', (0.72, 0.6, 0.48), 40.0, (0.7, 1.0))
    _box(name + '_ground', (0, 0, -0.05), (600, 600, 0.1), dirt, 0)
    siding = principled(f'{name}_siding', (0.16, 0.2, 0.13), rough=0.8)
    nt = siding.node_tree; b = nt.nodes['Principled BSDF']
    wv = nt.nodes.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Z'; wv.inputs['Scale'].default_value = 25
    wv.wave_profile = 'SAW'; tcn = nt.nodes.new('ShaderNodeTexCoord'); nt.links.new(tcn.outputs['Object'], wv.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.5
    nt.links.new(wv.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    roof = principled(f'{name}_tarpaper', (0.06, 0.06, 0.06), rough=0.85, bump=0.1, bump_scale=150)
    trim = principled(f'{name}_trim', (0.75, 0.72, 0.62), rough=0.7)
    win = P.mat('hut_window', (0.03, 0.035, 0.04), rough=0.05)
    rnd = random.Random(5)
    for r in range(rows):
        for k in range(per_row):
            x = -45 + k * 30 + rnd.uniform(-2, 2); y = 20 + r * 26
            L_, W_, H_ = 24.0, 9.0, 6.5
            _box(f'{name}_hut{r}{k}', (x, y, H_ / 2), (L_, W_, H_), siding, 0.02)
            for sy in (-1, 1):                                        # pitched roof planes
                o = _box(f'{name}_roof{r}{k}{sy}', (x, y + sy * W_ / 4, H_ + 0.9), (L_ + 0.6, W_ / 2 + 0.6, 0.1), roof, 0)
                o.rotation_euler.x = sy * math.radians(-20)
            for fl in (1.5, 4.6):                                     # two rows of windows
                for j in range(8):
                    wx = x - L_ / 2 + 1.5 + j * (L_ - 3) / 7
                    _box(f'{name}_w{r}{k}{fl}{j}', (wx, y - W_ / 2 - 0.02, fl), (0.9, 0.04, 1.1), win, 0)
                    _box(f'{name}_wt{r}{k}{fl}{j}', (wx, y - W_ / 2 - 0.05, fl), (1.0, 0.03, 1.2), trim, 0)
            stair = principled('stair_wood', (0.32, 0.25, 0.17), rough=0.9)
            for s in range(10):                                       # outside stair to the upper floor
                _box(f'{name}_st{r}{k}{s}', (x + L_ / 2 + 0.6, y - 2.5 + s * 0.4, 0.3 + s * 0.33), (1.0, 0.3, 0.05), stair, 0)
    pine = principled(f'{name}_pine', (0.04, 0.08, 0.035), rough=0.9)
    bark = principled(f'{name}_bark', (0.15, 0.1, 0.07), rough=0.95)
    for k in range(40):                                               # ponderosa pines: trunk + stacked cones
        x, y = rnd.uniform(-150, 150), rnd.uniform(110, 260)
        if rnd.random() < 0.3:
            x, y = rnd.uniform(-90, 90), rnd.uniform(-80, -20)
        hgt = rnd.uniform(14, 24)
        P.cyl(f'{name}_trunk{k}', (x, y, hgt * 0.35), 0.3, hgt * 0.7, bark, verts=10)
        for j in range(3):
            bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=hgt * (0.22 - j * 0.05), depth=hgt * 0.35, location=(x, y, hgt * (0.45 + j * 0.2)))
            c = bpy.context.object; c.data.materials.append(pine); c.name = f'{name}_crown{k}{j}'
    fence = P.mat('fence_steel', (0.4, 0.4, 0.38), metal=0.8, rough=0.5)
    for k in range(40):                                               # security fence along the front (y = 5)
        x = -100 + k * 5
        P.cyl(f'{name}_fpost{k}', (x, 5, 1.2), 0.04, 2.4, fence, verts=8)
    mesh_m = bpy.data.materials.new(f'{name}_chainlink'); mm = mesh_m.node_tree; bsdf = mm.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (0.5, 0.5, 0.48, 1); bsdf.inputs['Metallic'].default_value = 0.8
    chk = mm.nodes.new('ShaderNodeTexBrick'); chk.inputs['Scale'].default_value = 40; chk.inputs['Mortar Size'].default_value = 0.08
    mm.nodes['Material Output']; mix = mm.nodes.new('ShaderNodeMixShader'); tr = mm.nodes.new('ShaderNodeBsdfTransparent')
    mm.links.new(chk.outputs['Fac'], mix.inputs['Fac']); mm.links.new(bsdf.outputs[0], mix.inputs[1]); mm.links.new(tr.outputs[0], mix.inputs[2])
    mm.links.new(mix.outputs[0], mm.nodes['Material Output'].inputs['Surface'])
    _box(name + '_chainlink', (-2.5, 5, 1.1), (195, 0.01, 2.1), mesh_m, 0)
    gt = P.worn_paint('tower_wood', (0.3, 0.26, 0.2), wear=0.2)
    for sx in (-1, 1):                                                # guard tower at the gate
        for sy in (-1, 1):
            P.cyl(f'{name}_gtleg{sx}{sy}', (12 + sx * 1.2, 3 + sy * 1.2, 3.5), 0.1, 7.0, gt, verts=8)
    _box(name + '_gtcab', (12, 3, 7.8), (3.0, 3.0, 1.8), gt, 0.02)
    _box(name + '_gtroof', (12, 3, 8.9), (3.6, 3.6, 0.15), roof, 0)
    P.jeep((4, -6, 0), 70, name + '_jeep')
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=200, y_subdivisions=30, size=1, location=(0, 2500, 0))
    mt = bpy.context.object; mt.name = name + '_jemez'; mt.scale = (9000, 1800, 1)
    mt.data.materials.append(principled(f'{name}_far_hills', (0.12, 0.16, 0.12), rough=0.95))
    tx = bpy.data.textures.new(name + '_hills', 'CLOUDS'); tx.noise_scale = 0.3
    dm = mt.modifiers.new('hills', 'DISPLACE'); dm.texture = tx; dm.strength = 650; dm.texture_coords = 'LOCAL'
    return _parent(root, before)

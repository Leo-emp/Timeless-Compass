# CANNONS by era (built by code from museum pieces and period drawings), each with a film-style firing:
#   'bombard' c. 1450   wrought-iron hooped siege gun on a timber bed, no wheels (Orban's guns at Constantinople, 1453;
#                       Mons Meg, Edinburgh Castle, 1449)
#   'naval'   c. 1650-1850  cast-iron ship's gun on a 4-truck carriage (HMS Victory's 32-pounders, 1805)
#   'field'   c. 1800-1865  bronze 12-pounder "Napoleon" on two big spoked wheels + trail (Napoleonic wars, US Civil War)
# fire(cannon, frame, target) = the moment in the movies: white-hot flash, a tongue of flame from the muzzle, the gun
# KICKS back (carriage rolls / slides), a thick cloud of white-grey powder smoke rolls out, the ball flies its arc and
# (optionally) a shell bursts at the target. Black powder smoke is WHITE-grey and huge - the battlefields vanished in it.
import math
import random

import bpy
import bmesh
from mathutils import Vector

from lib.common import link, principled

ERA = {'bombard': (1400, 1530), 'naval': (1600, 1860), 'field': (1790, 1870)}


def _weathered(name, base, metal, rough, grime, pits=0.25):
    """Metal that has lived outdoors: base colour broken by soot/grime blotches and rough patches, fine pitting."""
    m = principled(name, base, metal=metal, rough=rough, bump=pits, bump_scale=160)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6; nz.inputs['Detail'].default_value = 10
    L(tc.outputs['Object'], nz.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.45; ramp.color_ramp.elements[0].color = (*base, 1)
    ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = (*grime, 1)
    L(nz.outputs['Fac'], ramp.inputs['Fac']); L(ramp.outputs['Color'], b.inputs['Base Color'])
    rr = nt.nodes.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = rough * 0.8; rr.inputs['To Max'].default_value = min(1.0, rough * 1.5)
    L(nz.outputs['Fac'], rr.inputs['Value']); L(rr.outputs['Result'], b.inputs['Roughness'])
    return m


def _mats():
    iron = bpy.data.materials.get('gun_iron') or _weathered('gun_iron', (0.07, 0.068, 0.07), 0.85, 0.5, (0.11, 0.07, 0.045))   # rust-brown blotches
    bronze = bpy.data.materials.get('gun_bronze') or _weathered('gun_bronze', (0.45, 0.32, 0.15), 1.0, 0.35, (0.2, 0.22, 0.14), 0.12)  # dull patina
    wood = bpy.data.materials.get('gun_wood')
    if wood is None:                                   # scanned planks (Poly Haven CC0), else a plain fallback
        try:
            from lib import scatter
            wood = scatter.scan_material('gun_wood', 'brown_planks_04', tint=(0.75, 0.6, 0.5), tiles=3.0)
        except Exception:
            wood = principled('gun_wood', (0.22, 0.13, 0.07), rough=0.75, bump=0.3, bump_scale=60)
    red = bpy.data.materials.get('gun_red') or principled('gun_red', (0.3, 0.05, 0.03), rough=0.7)    # naval carriages
    olive = bpy.data.materials.get('gun_olive') or principled('gun_olive', (0.16, 0.17, 0.1), rough=0.65)  # field carriages
    return iron, bronze, wood, red, olive


def lathe(name, profile, material, seg=48):
    """A turned shape (gun barrel, wheel hub, ball): `profile` = [(radius, x)] along +X (muzzle toward +X)."""
    bm = bmesh.new()
    rings = []
    for r, x in profile:
        ring = [bm.verts.new((x, r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg))) for k in range(seg)]
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(seg):
            bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); link(o)
    o.data.materials.append(material)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def _box(name, c, s, m, parent):
    bpy.ops.mesh.primitive_cube_add(size=1, location=c); o = bpy.context.object; o.name = name; o.scale = s
    bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = 0.012; bv.segments = 2
    o.data.materials.append(m); o.parent = parent
    return o


def _wheel(name, radius, width, spokes, wood, iron, parent, loc):
    """Spoked wooden wheel with an iron tyre, axle along Y."""
    w = bpy.data.objects.new(name, None); link(w); w.parent = parent; w.location = loc
    bpy.ops.mesh.primitive_torus_add(major_radius=radius - 0.03, minor_radius=0.035, major_segments=64, location=(0, 0, 0),
                                     rotation=(math.pi / 2, 0, 0))
    rim = bpy.context.object; rim.scale = (1, 1, width / 0.07); rim.data.materials.append(wood); rim.parent = w
    bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=0.012, major_segments=64, rotation=(math.pi / 2, 0, 0))
    tyre = bpy.context.object; tyre.scale = (1, 1, width / 0.024); tyre.data.materials.append(iron); tyre.parent = w
    hub = lathe(name + '_hub', [(0.06, -0.12), (0.11, -0.08), (0.11, 0.08), (0.06, 0.12)], wood, 24)
    hub.rotation_euler.z = math.pi / 2; hub.parent = w
    for k in range(spokes):
        a = 2 * math.pi * k / spokes
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.022, depth=radius - 0.1,
                                            location=(math.cos(a) * radius / 2, 0, math.sin(a) * radius / 2),
                                            rotation=(0, math.pi / 2 - a, 0))
        s = bpy.context.object; s.data.materials.append(wood); s.parent = w
    return w


def build(kind='field', loc=(0, 0, 0), heading_deg=0.0, elevation_deg=3.0, name=None):
    """Build one cannon. Origin on the ground under the axle; the muzzle points along the heading (0 = +X).
    Returns the root empty (custom props: kind, muzzle_len, barrel = the barrel object for recoil / aiming)."""
    iron, bronze, wood, red, olive = _mats()
    name = name or f'cannon_{kind}'
    root = bpy.data.objects.new(name, None); link(root)
    root['kind'] = kind
    if kind == 'bombard':              # ~4 m wrought-iron tube of welded staves held by hoops, huge bore, on a timber bed
        prof = [(0.25, -1.4), (0.36, -1.35), (0.36, -0.4), (0.5, -0.35), (0.5, 2.4), (0.46, 2.45)]
        barrel = lathe(name + '_barrel', prof, iron)
        for k in range(12):                                            # the hoops
            x = -0.3 + k * 0.23
            h = lathe(f'{name}_hoop{k}', [(0.5, x), (0.535, x + 0.02), (0.535, x + 0.09), (0.5, x + 0.11)], iron)
            h.parent = barrel
        bore = lathe(name + '_bore', [(0.001, 2.2), (0.33, 2.21), (0.33, 2.46)], principled('bore_dark', (0.01, 0.01, 0.01), rough=0.9))
        bore.parent = barrel
        barrel.location = (0, 0, 0.75)
        for y in (-0.45, 0.45):
            _box(f'{name}_bed{y}', (0.5, y, 0.25), (4.5, 0.3, 0.5), wood, root)
        _box(f'{name}_bedx', (-1.0, 0, 0.25), (0.4, 1.2, 0.5), wood, root)
        muzzle = 2.45
    elif kind == 'naval':              # 32-pounder: ~2.9 m cast iron, cascabel knob, on a red-painted truck carriage
        prof = [(0.03, -1.6), (0.09, -1.58), (0.06, -1.5), (0.22, -1.45), (0.3, -1.3), (0.31, -0.6), (0.28, -0.55),
                (0.25, 0.5), (0.22, 1.1), (0.21, 1.25), (0.25, 1.3), (0.25, 1.38)]
        barrel = lathe(name + '_barrel', prof, iron)
        bore = lathe(name + '_bore', [(0.001, 1.2), (0.085, 1.21), (0.085, 1.39)], principled('bore_dark', (0.01, 0.01, 0.01), rough=0.9))
        bore.parent = barrel
        barrel.location = (0, 0, 0.78)
        for y in (-0.33, 0.33):                                        # stepped cheeks
            _box(f'{name}_cheek{y}', (-0.35, y, 0.45), (1.5, 0.12, 0.55), red, root)
            _box(f'{name}_step{y}', (-0.9, y, 0.32), (0.7, 0.12, 0.35), red, root)
        _box(f'{name}_axlef', (0.2, 0, 0.2), (0.16, 0.9, 0.14), wood, root)
        _box(f'{name}_axleb', (-0.9, 0, 0.2), (0.16, 0.9, 0.14), wood, root)
        for x in (0.2, -0.9):
            for y in (-0.42, 0.42):                                    # the four solid "trucks"
                t = lathe(f'{name}_truck{x}{y}', [(0.001, -0.06), (0.2, -0.06), (0.2, 0.06), (0.001, 0.06)], wood, 32)
                t.rotation_euler.z = math.pi / 2; t.location = (x, y, 0.2); t.parent = root
        muzzle = 1.38
    else:                              # 'field': bronze 12-pdr Napoleon (1.68 m, smooth taper, muzzle swell), 1.45 m wheels
        prof = [(0.03, -0.95), (0.075, -0.92), (0.05, -0.85), (0.15, -0.8), (0.19, -0.7), (0.19, -0.2),
                (0.15, 0.5), (0.13, 0.62), (0.15, 0.7), (0.16, 0.76)]
        barrel = lathe(name + '_barrel', prof, bronze)
        bore = lathe(name + '_bore', [(0.001, 0.6), (0.06, 0.61), (0.06, 0.77)], principled('bore_dark', (0.01, 0.01, 0.01), rough=0.9))
        bore.parent = barrel
        barrel.location = (0, 0, 1.18)
        for y in (-0.62, 0.62):
            _wheel(f'{name}_wheel{y}', 0.72, 0.08, 14, wood, iron, root, (0, y, 0.72))
        _box(f'{name}_axle', (0, 0, 0.72), (0.14, 1.2, 0.12), olive, root)
        for y in (-0.16, 0.16):                                        # cheeks + trail to the ground behind
            _box(f'{name}_cheek{y}', (-0.25, y, 0.95), (0.9, 0.08, 0.3), olive, root)
        trail = _box(f'{name}_trail', (-1.5, 0, 0.45), (2.6, 0.26, 0.18), olive, root)
        trail.rotation_euler.y = -math.atan2(0.62, 2.6)
        muzzle = 0.77
    barrel.parent = root
    barrel.rotation_euler.y = -math.radians(elevation_deg)
    root['muzzle_len'] = muzzle
    root['barrel'] = barrel.name
    root.location = loc; root.rotation_euler.z = math.radians(heading_deg)
    return root


def muzzle_point(cannon):
    b = bpy.data.objects[cannon['barrel']]
    bpy.context.view_layer.update()
    return b.matrix_world @ Vector((cannon['muzzle_len'] + 0.05, 0, 0)), (b.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()



def _puff_material(name, density=1.8, color=(0.9, 0.88, 0.85)):     # bright, high-albedo: powder smoke is white-grey
    """Soft billowing powder smoke inside a sphere: density = noise x (1 - r/R)^1.5 - dense core, wispy edge."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    L = nt.links.new
    v = nt.nodes.new('ShaderNodeVolumePrincipled')
    v.inputs['Color'].default_value = (*color, 1)
    v.inputs['Anisotropy'].default_value = 0.3
    tc = nt.nodes.new('ShaderNodeTexCoord')
    ln = nt.nodes.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; L(tc.outputs['Object'], ln.inputs[0])
    fall = nt.nodes.new('ShaderNodeMapRange'); fall.inputs['From Min'].default_value = 1.0; fall.inputs['From Max'].default_value = 0.2
    L(ln.outputs['Value'], fall.inputs['Value'])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.2; nz.inputs['Detail'].default_value = 8
    nz.inputs['Roughness'].default_value = 0.65; L(tc.outputs['Object'], nz.inputs['Vector'])
    cr = nt.nodes.new('ShaderNodeMapRange'); cr.inputs['From Min'].default_value = 0.35; cr.inputs['From Max'].default_value = 0.75
    L(nz.outputs['Fac'], cr.inputs['Value'])
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; L(fall.outputs['Result'], mul.inputs[0]); L(cr.outputs['Result'], mul.inputs[1])
    d = nt.nodes.new('ShaderNodeMath'); d.operation = 'MULTIPLY'; d.inputs[1].default_value = density; L(mul.outputs[0], d.inputs[0])
    L(d.outputs[0], v.inputs['Density'])
    L(v.outputs[0], nt.nodes['Material Output'].inputs['Volume'])
    return m


def powder_smoke(tip, fwd, frame, n=7, seed=0, name='powder'):
    """The black-powder cloud: puffs blasted out of the muzzle along the barrel line, each one growing, slowing and
    drifting up; the cloud then hangs over the gun (period accounts: gun lines vanished in their own smoke)."""
    rnd = random.Random(seed)
    mat = _puff_material('powder_smoke')
    cy = bpy.context.scene.cycles                  # light must scatter INSIDE the cloud, or dense smoke renders black
    cy.volume_bounces = max(cy.volume_bounces, 3)
    out = []
    for i in range(n):
        dist = 0.6 + i * rnd.uniform(0.9, 1.4)
        r_end = 0.9 + i * 0.35 + rnd.uniform(-0.2, 0.3)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0, location=tip)
        p = bpy.context.object; p.name = f'{name}_{i}'; p.data.materials.append(mat)
        side = Vector((rnd.gauss(0, 0.25), rnd.gauss(0, 0.25), rnd.uniform(0.0, 0.3)))
        for f, k, s in ((frame - 1, 0.0, 0.01), (frame + 1 + i // 2, 0.55, 0.45), (frame + 8 + i, 0.9, 0.85), (frame + 90, 1.0, 1.05)):
            p.location = tip + (fwd * dist + side * dist) * k + Vector((0, 0, 0.6 * max(0, f - frame) / 90))
            p.scale = (r_end * s,) * 3
            p.keyframe_insert('location', frame=f); p.keyframe_insert('scale', frame=f)
        out.append(p)
    return out

def fire(cannon, frame, target=None, shell=False, seed=0):
    """Fire at `frame`: flash + flame tongue + recoil + powder smoke + flying ball (+ a shell burst at the target)."""
    from lib import fx
    rnd = random.Random(seed)
    kind = cannon['kind']
    tip, fwd = muzzle_point(cannon)
    # 1) FLASH: a light spike for 2-3 frames (lights the crew and the smoke from inside)
    bpy.ops.object.light_add(type='POINT', location=tip + fwd * 0.4)
    fl = bpy.context.object; fl.name = cannon.name + '_flash'; fl.data.color = (1.0, 0.72, 0.4); fl.data.shadow_soft_size = 0.6
    for f, e in ((frame - 1, 0), (frame, 12000), (frame + 1, 6000), (frame + 3, 1200), (frame + 6, 0)):
        fl.data.energy = e; fl.data.keyframe_insert('energy', frame=f)
    # 2) FLAME: a hot glowing VOLUME (blackbody fire) bursting from the muzzle for 4 frames - not a solid shape
    fire = fx.flames(tuple(tip + fwd * 0.6 - Vector((0, 0, 0.35))), height=0.7, width=0.7, intensity=60.0, temp=2300.0,
                     frames=(frame, frame + 6), name=cannon.name + '_flame')
    fire.rotation_mode = 'QUATERNION'; fire.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(fwd)
    base = fire.scale.copy()
    for f, k in ((frame - 1, 0.01), (frame, 1.0), (frame + 2, 1.6), (frame + 4, 0.01)):
        fire.scale = base * k; fire.keyframe_insert('scale', frame=f)
    # 3) RECOIL: the whole gun kicks back (field guns roll ~1.5 m, ship guns ~2.5 m until the breeching rope stops them)
    back = {'field': 1.4, 'naval': 2.2, 'bombard': 0.25}[kind]
    start = cannon.location.copy()
    hd = Vector((math.cos(cannon.rotation_euler.z), math.sin(cannon.rotation_euler.z), 0))
    cannon.keyframe_insert('location', frame=frame)
    cannon.location = start - hd * back * 0.7; cannon.keyframe_insert('location', frame=frame + 3)
    cannon.location = start - hd * back; cannon.keyframe_insert('location', frame=frame + 14)
    cannon.location = start
    if kind == 'field':                                                  # the wheels turn as it rolls back
        for w in [c for c in cannon.children if 'wheel' in c.name]:
            w.keyframe_insert('rotation_euler', frame=frame)
            w.rotation_euler.y = -back / 0.72; w.keyframe_insert('rotation_euler', frame=frame + 14)
    # 4) POWDER SMOKE: soft rolling puffs blasted along the barrel line, then hanging over the gun
    powder_smoke(tip, fwd, frame, seed=seed, name=cannon.name + '_smoke')
    # 5) THE BALL on a ballistic arc to the target (with motion blur it reads as a dark streak)
    if target is not None:
        p1 = Vector(target)
        T = max(0.6, (p1 - tip).length / 300.0)                         # ~300 m/s round shot
        v = (p1 - tip) / T + Vector((0, 0, 4.9 * T))
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.08, location=tip)
        ball = bpy.context.object; ball.name = cannon.name + '_ball'; ball.data.materials.append(_mats()[0])
        ball.hide_render = True; ball.keyframe_insert('hide_render', frame=frame - 1)
        ball.hide_render = False; ball.keyframe_insert('hide_render', frame=frame)
        steps = max(3, int(T * 24))
        for k in range(steps + 1):
            t = T * k / steps
            ball.location = tip + v * t + Vector((0, 0, -4.9 * t * t)); ball.keyframe_insert('location', frame=frame + k)
        if shell:                                                        # an exploding shell (1800s: common shell)
            fx.explosion(tuple(p1), size=3.0, frame=frame + steps, seed=seed + 1, name=cannon.name + '_burst')
        else:                                                            # round shot: a spray of earth where it strikes
            fx.explosion(tuple(p1), size=1.2, frame=frame + steps, debris=40, seed=seed + 1, name=cannon.name + '_strike')
    return fl

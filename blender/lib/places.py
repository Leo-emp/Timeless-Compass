# PLACES the Salamis Shorts need that no set builder covered yet (main session, WS6). Rooms and places are built here;
# the props inside them are Session E's (props.py, read-only use).
#   delphi_adyton()      the Pythia's inner sanctum in Apollo's temple at Delphi, 480 BC
#   tent_interior(kind)  a commander's tent on Salamis: 'themistocles' (his own) or 'council' (the generals' meeting)
# Each returns a dict of marks (where people stand / sit, where the camera can go) for tc assemble.
import math
import random

import bpy
from mathutils import Vector

from lib import common, props
from lib.common import link, principled


def _scan(name, scan, tint=(1, 1, 1), tiles=2.0, rough=(0.6, 0.95)):
    try:
        from lib import scatter
        return scatter.scan_material(name, scan, tint=tint, tiles=tiles, rough=rough)
    except Exception:
        return principled(name, tint, rough=0.85)


def _box(name, c, size, mat, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=c)
    o = bpy.context.object
    o.name = name
    o.scale = size
    o.data.materials.append(mat)
    if parent is not None:
        o.parent = parent
    return o


def room_haze(center, size, density=0.02, color=(1.0, 0.92, 0.82), name='room_haze'):
    """A thin volume filling a room: makes shafts of light from doors and lamps visible (incense, dust, smoke)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    o = bpy.context.object
    o.name = name
    o.scale = size
    m = bpy.data.materials.new(name + '_mat')
    nt = m.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    v = nt.nodes.new('ShaderNodeVolumePrincipled')
    v.inputs['Color'].default_value = (*color, 1)
    v.inputs['Density'].default_value = density
    v.inputs['Anisotropy'].default_value = 0.5            # forward scattering: beams glow toward the camera
    nt.links.new(v.outputs[0], nt.nodes['Material Output'].inputs['Volume'])
    o.data.materials.append(m)
    o.visible_shadow = False
    return o


# ------------------------------------------------------------------ DELPHI
def delphi_adyton(frames=(1, 240), seed=0):
    """The adyton of the Temple of Apollo at Delphi as it stood in 480 BC (the Alcmaeonid temple, c. 510 BC): a small
    rectangular chamber at the back of the cella, its floor sunk below the temple floor, entered down a few steps.
    Inside (Pausanias 10.24; Plutarch, De defectu oraculorum; Aeschylus, Eumenides): the omphalos wrapped in its woollen
    net, the bronze tripod on which the Pythia sat, laurel, the smoke of burnt laurel and barley, lamps. A narrow
    shaft of daylight falls from the door; the rest is dark - the god's room, not a hall.
    Origin = room floor centre; the door is in the +Y wall (camera looking in from the steps = from +Y)."""
    W, D, H = 6.0, 4.6, 4.8
    root = bpy.data.objects.new('delphi_adyton', None)
    link(root)
    stone = _scan('adyton_stone', 'old_sandstone_02', tint=(0.82, 0.74, 0.62), tiles=3.0)
    floor = _scan('adyton_floor', 'sandstone_cracks', tint=(0.62, 0.55, 0.46), tiles=2.5)
    _box('adyton_floor', (0, 0, -0.05), (W, D, 0.1), floor, root)
    _box('adyton_ceiling', (0, 0, H + 0.05), (W, D, 0.1), principled('adyton_timber', (0.12, 0.08, 0.05), rough=0.8), root)
    _box('adyton_wall_back', (0, -D / 2, H / 2), (W, 0.4, H), stone, root)
    _box('adyton_wall_L', (-W / 2, 0, H / 2), (0.4, D, H), stone, root)
    _box('adyton_wall_R', (W / 2, 0, H / 2), (0.4, D, H), stone, root)
    door_w, door_h = 1.6, 3.2                               # the front wall with the doorway (+Y)
    side = (W - door_w) / 2
    _box('adyton_wall_front_L', (-(door_w / 2 + side / 2), D / 2, H / 2), (side, 0.4, H), stone, root)
    _box('adyton_wall_front_R', ((door_w / 2 + side / 2), D / 2, H / 2), (side, 0.4, H), stone, root)
    _box('adyton_lintel', (0, D / 2, door_h + (H - door_h) / 2), (door_w, 0.4, H - door_h), stone, root)
    for k in range(3):                                      # steps up to the temple floor outside the door
        _box(f'adyton_step{k}', (0, D / 2 + 0.45 + k * 0.4, 0.12 + k * 0.24), (door_w + 0.6, 0.4, 0.24 + k * 0.48), floor, root)
    # the chasm: a dark fissure in the floor under the tripod (ancient tradition; vapours rise from it)
    _box('adyton_cleft', (-0.9, -0.6, 0.002), (0.9, 0.16, 0.01), principled('cleft_dark', (0.01, 0.01, 0.01), rough=1.0), root)
    tri = props.tripod_cauldron(loc=(-0.9, -0.6, 0), heading_deg=20, height=1.6, seat=True, name='pythia_tripod')
    omph = props.omphalos(loc=(1.3, -1.2, 0), heading_deg=-15, height=1.0, name='omphalos')
    for o in (tri, omph):
        if o is not None:
            o.parent = root
    lamps = [props.lamp_stand(loc=(x, y, 0), heading_deg=0, height=1.25, lit=True, power=10.0, frames=frames, seed=seed + i,
                              name=f'adyton_lamp{i}') for i, (x, y) in enumerate(((-2.4, -1.7), (2.4, -1.7)))]
    br = props.brazier(loc=(0.3, -1.6, 0), kind='bronze', lit=True, power=120.0, flames=True, frames=frames, seed=seed,
                       name='laurel_brazier')
    # a thin rising wisp of laurel smoke from the brazier and from the cleft
    try:
        from lib import fx
        fx.smoke_column((0.3, -1.6, 0.9), height=3.6, width=0.35, density=0.6, color=(0.55, 0.52, 0.48), frames=frames,
                        name='laurel_smoke', wind=0.05)
        fx.smoke_column((-0.9, -0.6, 0.05), height=2.4, width=0.3, density=0.35, color=(0.62, 0.6, 0.56), frames=frames,
                        name='cleft_vapour', wind=0.03)
    except Exception as e:
        print('adyton smoke skipped', e)
    # DAYLIGHT through the door: a hard warm beam falling down the steps and across the floor, made visible by haze
    bpy.ops.object.light_add(type='SPOT', location=(0.4, D / 2 + 4.0, 4.6))
    sun = bpy.context.object
    sun.name = 'adyton_daybeam'
    sun.data.energy = 9000
    sun.data.spot_size = math.radians(22)
    sun.data.spot_blend = 0.15
    sun.data.shadow_soft_size = 0.15
    sun.data.color = (1.0, 0.88, 0.7)
    sun.rotation_euler = (Vector((0.2, -0.8, 0.0)) - sun.location).to_track_quat('-Z', 'Y').to_euler()
    room_haze((0, 0, H / 2), (W - 0.4, D - 0.4, H - 0.1), density=0.03, color=(0.95, 0.88, 0.78), name='adyton_smoke_haze')
    # a little cool bounce so the shadows are not pure black (film fill)
    common.area_light('adyton_fill', 40, (0.75, 0.82, 1.0), Vector((2.0, 1.6, 2.2)), Vector((-0.9, -0.6, 1.2)), 2.5)
    return {'root': root, 'pythia_seat': Vector((-0.9, -0.6, 1.6)), 'omphalos': Vector((1.3, -1.2, 0)),
            'envoys': [Vector((0.2, 1.4, 0)), Vector((0.9, 1.6, 0))], 'door': Vector((0, D / 2, 0)),
            'cam_from_door': Vector((0.6, D / 2 + 0.9, 1.7)), 'cam_low_tripod': Vector((-2.2, 0.6, 0.6))}


# ------------------------------------------------------------------ TENTS
def tent_interior(kind='themistocles', frames=(1, 240), seed=0):
    """A commander's field tent on Salamis, 480 BC: a ridge tent of leather and coarse canvas on wooden poles, guy
    ropes taut, the flap open to the camp. 'themistocles': his own tent - a camp table with a wax tablet and a lamp,
    a klismos, his arms on a stand (helmet, shield, spear), a chest. 'council': bigger, stools round a table for the
    generals' debate (Herodotus 8.56-64, 8.74-78: the commanders argued for days whether to stay at Salamis).
    Origin = floor centre; the open flap is at +Y. Lamplit night by default (the councils ran late)."""
    rnd = random.Random(seed)
    big = kind == 'council'
    W, D, H = (6.0, 8.0, 3.4) if big else (4.0, 5.0, 3.0)
    root = bpy.data.objects.new(f'tent_{kind}', None)
    link(root)
    leather = _scan(f'tent_leather_{kind}', 'brown_leather', tint=(0.85, 0.72, 0.58), tiles=6.0)
    canvas = _scan(f'tent_canvas_{kind}', 'hessian_230', tint=(0.78, 0.68, 0.52), tiles=22.0)   # fine weave, not bricks
    ground = _scan(f'tent_ground_{kind}', 'brown_mud_dry', tint=(0.7, 0.6, 0.48), tiles=2.0)
    _box(f'tent_floor_{kind}', (0, 0, -0.05), (W + 2, D + 2, 0.1), ground, root)
    # the roof: two sloping panels to a ridge pole (thin boxes, a little sag from a simple subdivision + noise)
    slope = math.atan2(H - 1.4, W / 2)
    panel_w = math.hypot(W / 2, H - 1.4)
    for sgn in (-1, 1):
        p = _box(f'tent_roof_{kind}_{sgn}', (sgn * W / 4, 0, 1.4 + (H - 1.4) / 2), (panel_w, D, 0.02), canvas if sgn < 0 else leather, root)
        p.rotation_euler.y = sgn * slope
        sub = p.modifiers.new('sag', 'SUBSURF'); sub.levels = 3; sub.subdivision_type = 'SIMPLE'
        tex = bpy.data.textures.new(f'sag_{kind}_{sgn}', 'CLOUDS'); tex.noise_scale = 1.2
        dsp = p.modifiers.new('sagdisp', 'DISPLACE'); dsp.texture = tex; dsp.strength = 0.06
    for sgn in (-1, 1):                                     # low side walls
        _box(f'tent_wall_{kind}_{sgn}', (sgn * W / 2, 0, 0.7), (0.02, D, 1.4), leather, root)
    _box(f'tent_back_{kind}', (0, -D / 2, H / 2), (W, 0.02, H), canvas, root)
    wood = principled('tent_pole', (0.28, 0.18, 0.1), rough=0.75)
    for y in (-D / 2 + 0.1, 0, D / 2 - 0.1):                # upright poles + ridge
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.045, depth=H, location=(0, y, H / 2))
        pole = bpy.context.object; pole.data.materials.append(wood); pole.parent = root
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.04, depth=D, location=(0, 0, H), rotation=(math.pi / 2, 0, 0))
    ridge = bpy.context.object; ridge.data.materials.append(wood); ridge.parent = root
    marks = {'root': root}
    if big:                                                 # the council: a long table, stools all round
        props.trapeza(loc=(0, -0.5, 0), heading_deg=90, name='council_table_a')
        props.trapeza(loc=(0, 0.6, 0), heading_deg=90, name='council_table_b')
        seats = []
        for i in range(8):
            side = -1 if i % 2 == 0 else 1
            y = -1.6 + (i // 2) * 0.95
            props.footstool(loc=(side * 1.05, y, 0), heading_deg=90 * side, name=f'council_stool{i}')
            seats.append(Vector((side * 1.05, y, 0)))
        marks['seats'] = seats
        marks['speaker'] = Vector((0, -2.6, 0))
        for i, (x, y) in enumerate(((-1.8, -2.8), (1.8, -2.8), (-1.8, 2.6), (1.8, 2.6))):
            props.lamp_stand(loc=(x, y, 0), height=1.25, lit=True, power=22.0, frames=frames, seed=seed + i, name=f'council_lamp{i}')
    else:                                                   # Themistocles' own tent
        props.trapeza(loc=(0.6, -1.0, 0), heading_deg=0, name='them_table')
        props.klismos(loc=(0.6, -1.65, 0), heading_deg=0, name='them_chair')
        props.oil_lamp(loc=(0.85, -1.0, 0.74), lit=True, power=18.0, frames=frames, seed=seed, name='them_lamp')
        props.kline(loc=(-1.3, -1.3, 0), heading_deg=90, name='them_couch')
        try:                                                # his arms on a stand: helmet, shield, spear (armour kit)
            bronze = bpy.data.materials.get('aged_bronze') or common.aged_bronze()
            bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.03, depth=1.5, location=(1.6, -2.0, 0.75))
            st = bpy.context.object; st.data.materials.append(wood); st.parent = root
            bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.45, location=(1.75, -2.15, 0.5))
            sh = bpy.context.object; sh.scale = (1.0, 0.12, 1.0); sh.rotation_euler.z = math.radians(30)
            sh.data.materials.append(bronze); sh.parent = root
        except Exception as e:
            print('arms stand skipped', e)
        marks['seat'] = Vector((0.6, -1.65, 0))
        marks['visitor'] = Vector((0.2, 0.8, 0))
    # the open flap at +Y shows the camp at night: a few far fires
    for i in range(4):
        x, y = rnd.uniform(-8, 8), D / 2 + rnd.uniform(8, 25)
        bpy.ops.object.light_add(type='POINT', location=(x, y, 0.5))
        f = bpy.context.object; f.data.energy = 300; f.data.color = (1.0, 0.55, 0.25); f.data.shadow_soft_size = 0.4
    room_haze((0, 0, H / 2), (W - 0.1, D - 0.1, H - 0.1), density=0.012, color=(1.0, 0.85, 0.65), name=f'tent_haze_{kind}')
    common.area_light(f'tent_fill_{kind}', 60, (0.7, 0.78, 1.0), Vector((0, D / 2 + 1.0, 2.0)), Vector((0, 0, 1.0)), 2.0)
    marks['cam_flap'] = Vector((0.3, D / 2 + 0.6, 1.6))
    return marks


# ------------------------------------------------------------------ ATHENS: the Pnyx
def pnyx_assembly(citizens=60, frames=(1, 240), seed=0):
    """The Pnyx in 480 BC (Phase I, before the 400s rebuilding): a natural rocky slope west of the Acropolis where the
    Assembly met - citizens sitting and standing on the bare hillside, a speaker on the rock-cut bema at the foot of
    the slope, the Acropolis rock in view to the east. Herodotus 7.143: here Themistocles argued that the 'wooden
    walls' meant the fleet. Origin = the bema; the audience slope rises toward -Y; the Acropolis lies to +X."""
    from lib import sets, scatter
    root = bpy.data.objects.new('pnyx', None)
    link(root)
    # the slope must stay BELOW the bema (v1 buried it: land() noise put metres of hill over the origin) - a gentle
    # bowl rising away from the speaker, built from one formula so marks and camera heights are predictable
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=120, y_subdivisions=120, size=140, location=(0, -30, 0))
    hill = bpy.context.object
    hill.name = 'pnyx_hill'
    for v in hill.data.vertices:
        y = v.co.y - 30.0                                    # world y (grid centred at -30)
        r = math.hypot(v.co.x, y)
        v.co.z = max(0.0, (-(y) - 3.0)) * 0.16 + 0.0015 * r * r * (1 if y < 0 else 0.3) - 0.05
    hill.data.update()
    hill.data.materials.append(_scan('pnyx_ground', 'coast_land_rocks_01', tint=(0.92, 0.85, 0.72), tiles=4.0))
    rock = _scan('pnyx_rock', 'rock_wall_08', tint=(0.85, 0.8, 0.72), tiles=1.5)
    _box('bema_base', (0, 0, 0.45), (3.4, 2.4, 0.9), rock, root)               # the speaker's platform, cut from rock
    for k in range(3):
        _box(f'bema_step{k}', (0, -1.45 - k * 0.35, 0.15 * (3 - k)), (2.2, 0.35, 0.3 * (3 - k)), rock, root)
    sets.mesa('acropolis_far', (420, 40, 0), size=(300, 140), height=70, seed=seed + 3)
    try:
        scatter.scatter(hill, ['grass_medium_01', 'dry_branches_medium_01'], 900, (-60, 60, -80, 20), seed=seed + 11,
                        size=(0.8, 1.4), clusters=50, cluster_r=4.0, min_z=-5, keep_clear=[(0, 0, 4), (0, -14, 14)],
                        collection_name='pnyx_grass', lod=1)
    except Exception as e:
        print('pnyx grass skipped', e)
    marks = {'root': root, 'speaker': Vector((0, 0, 0.9)), 'acropolis': Vector((420, 40, 60))}
    rnd = random.Random(seed)                                # audience marks in arcs up the slope (crowd extras go here)
    aud = []
    for i in range(citizens):
        r = 5.0 + (i // 12) * 1.6 + rnd.uniform(-0.3, 0.3)
        a = math.radians(-60 + (i % 12) * 10 + rnd.uniform(-3, 3))
        x, y = math.sin(a) * r, -math.cos(a) * r
        z = max(0.0, (-y - 3.0)) * 0.16 + 0.0015 * (x * x + y * y) * (1 if y < 0 else 0.3) - 0.05   # on the slope
        aud.append(Vector((x, y, z)))
    marks['audience'] = aud
    marks['cam_behind_speaker'] = Vector((1.2, 3.5, 2.2))
    marks['cam_crowd_low'] = Vector((-4.0, -7.0, 1.2 + 0.16 * 4.0 + 0.0015 * 65))
    common.hdri_world('kloofendal_48d_partly_cloudy_puresky', strength=1.0)
    common.sun_light('pnyx_sun', 3.2, (1.0, 0.92, 0.8), 38, 140)
    return marks


# ------------------------------------------------------------------ ATHLIT: the ram, found 1980, and in the museum
def _water_volume(name, size, loc, density=0.07):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    w = bpy.context.object
    w.name = name
    w.scale = size
    m = bpy.data.materials.new(name + '_mat')
    nt = m.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    v = nt.nodes.new('ShaderNodeVolumePrincipled')
    v.inputs['Color'].default_value = (0.25, 0.6, 0.62, 1)
    v.inputs['Density'].default_value = density
    v.inputs['Absorption Color'].default_value = (0.1, 0.45, 0.5, 1)
    v.inputs['Anisotropy'].default_value = 0.6
    nt.links.new(v.outputs[0], nt.nodes['Material Output'].inputs['Volume'])
    w.data.materials.append(m)
    w.visible_shadow = False
    return w


def athlit_seabed_1980(frames=(1, 240), seed=0):
    """Athlit, Israel, November 1980: the bronze ram found on the seabed just off the coast (a few metres deep), half
    buried in sand, a diver's lamp on it. Underwater look: blue-green volume, sun shafts from the surface, ripples."""
    root = bpy.data.objects.new('athlit_seabed', None)
    link(root)
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    sand = bpy.context.object
    sand.name = 'seabed_sand'
    sub = sand.modifiers.new('sub', 'SUBSURF')
    sub.levels = 5
    sub.subdivision_type = 'SIMPLE'
    tex = bpy.data.textures.new('ripples', 'WOOD')
    tex.wood_type = 'BANDNOISE'
    tex.noise_scale = 0.6
    tex.turbulence = 4
    dsp = sand.modifiers.new('ripples', 'DISPLACE')
    dsp.texture = tex
    dsp.strength = 0.04
    sand.data.materials.append(_scan('seabed_mat', 'coast_sand_rocks_02', tint=(0.8, 0.85, 0.8), tiles=8.0))
    ram = props.ram_athlit(loc=(0, 0, -0.25), heading_deg=25, plinth=False, corroded=True, name='athlit_ram_found')
    if ram is not None:
        ram.rotation_euler.x = math.radians(6)                     # tilted, half in the sand
    _water_volume('sea_volume', (60, 60, 4.0), (0, 0, 2.0))
    common.sun_light('surface_sun', 6.0, (0.85, 0.97, 1.0), 70, 160)
    bpy.ops.object.light_add(type='SPOT', location=(1.6, 1.4, 1.2))   # the diver's lamp
    lamp = bpy.context.object
    lamp.data.energy = 600
    lamp.data.spot_size = math.radians(35)
    lamp.data.color = (1.0, 0.95, 0.85)
    lamp.rotation_euler = (Vector((0, 0, 0)) - lamp.location).to_track_quat('-Z', 'Y').to_euler()
    return {'root': root, 'ram': Vector((0, 0, 0)), 'diver': Vector((1.8, 1.6, 0.6)), 'cam_low': Vector((2.6, -2.2, 0.5))}


def athlit_ram_display(frames=(1, 240), seed=0):
    """The Athlit ram today: National Maritime Museum, Haifa - the corroded bronze ram on a low plinth in a dark
    gallery, a warm spotlight from above, a plain wall behind (documentary 'now' shot)."""
    root = bpy.data.objects.new('athlit_gallery', None)
    link(root)
    _box('gallery_floor', (0, 0, -0.05), (10, 10, 0.1), principled('gallery_floor', (0.06, 0.06, 0.065), rough=0.35), root)
    _box('gallery_wall', (0, -3.0, 2.5), (10, 0.2, 5), _scan('gallery_wall', 'grey_plaster_02', tint=(0.35, 0.36, 0.38), tiles=3.0), root)
    props.ram_athlit(loc=(0, 0, 0), heading_deg=30, plinth=True, corroded=True, name='athlit_ram_museum')
    bpy.ops.object.light_add(type='SPOT', location=(0.8, 1.2, 4.2))
    key = bpy.context.object
    key.data.energy = 2500
    key.data.spot_size = math.radians(28)
    key.data.spot_blend = 0.4
    key.data.color = (1.0, 0.86, 0.68)
    key.rotation_euler = (Vector((0, 0, 0.6)) - key.location).to_track_quat('-Z', 'Y').to_euler()
    common.area_light('gallery_rim', 120, (0.7, 0.8, 1.0), Vector((-2.2, -2.0, 2.0)), Vector((0, 0, 0.6)), 1.5)
    return {'root': root, 'ram': Vector((0, 0, 0.6)), 'cam_three_quarter': Vector((2.4, 2.6, 1.3)),
            'cam_close': Vector((0.9, 1.1, 0.8))}

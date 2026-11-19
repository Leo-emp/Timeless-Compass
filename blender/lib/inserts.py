# DETAIL INSERTS (Session D): the close-up 'insert' shots a narrated documentary lives on - the letter, the coin,
# the shard with a name on it - each a cheap, beautiful shot that matches a line of narration. Objects of the
# Salamis world (480 BC) + insert_set(): a surface, one hard RAKING key light (texture, long shadows), a soft rim,
# dark falloff, and a macro camera (100 mm, f/2.8) - the classic look of a film insert.
#   wax_tablet  wooden writing tablet (deltos) with a wax face and a bronze stylus - Demaratus hid his warning to
#               Sparta under the wax of such a tablet (Herodotus 7.239)
#   ostrakon    potsherd with a name scratched in: 'ΘΕΜΙΣΘΟΚΛΕΣ ΝΕΟΚΛΕΟΣ' (ostraka with Themistocles' name survive
#               in the Athenian Agora; he was ostracised c. 471 BC)
#   scroll      rolled papyrus tied with cord and a clay sealing (bulla) stamped with a seal
#   aryballos   small round oil flask (athletes, bathers), astragaloi = knucklebones (children's / gaming pieces)
#   + market.owl_coins, props.oil_lamp, the wardrobe pins and jewellery, armour pieces, etc.
import math
import os
import random

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

from lib.common import link, principled

GREEK_FONTS = ["C:/Windows/Fonts/times.ttf", "C:/Windows/Fonts/georgia.ttf", "C:/Windows/Fonts/constan.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "/usr/share/fonts/dejavu/DejaVuSerif.ttf"]


def _m(name, color, rough=0.6, metal=0.0, bump=0.1, bump_scale=150, sss=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = principled(name, color, metal=metal, rough=rough, bump=bump, bump_scale=bump_scale, sss=sss); m.use_fake_user = True
    return m


def _root(name, loc, rot_z=0.0):
    r = link(bpy.data.objects.new(name, None)); r.location = loc; r.rotation_euler = (0, 0, rot_z)
    return r


def _box(name, c, size, mat, parent, bevel=0.002):
    bpy.ops.mesh.primitive_cube_add(size=1, location=c); o = bpy.context.object; o.name = name
    o.scale = size; bpy.ops.object.transform_apply(scale=True)
    if bevel:
        b = o.modifiers.new('bevel', 'BEVEL'); b.width = bevel; b.segments = 2
    o.data.materials.append(mat); o.parent = parent
    return o


def _text(name, text, size, mat, parent, loc, rot=(0, 0, 0), depth=0.0003):
    """Letters as thin geometry lying on a surface (incised / painted look)."""
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = text; cu.size = size; cu.extrude = depth; cu.align_x = 'CENTER'
    f = next((p for p in GREEK_FONTS if os.path.exists(p)), None)
    if f:
        cu.font = bpy.data.fonts.load(f, check_existing=True)
    o = link(bpy.data.objects.new(name, cu)); o.data.materials.append(mat)
    o.location = loc; o.rotation_euler = rot; o.parent = parent
    return o


def wax_tablet(loc=(0, 0, 0), rot_z=0.0, open_deg=150.0, seed=0, name='wax_tablet'):
    """A two-leaf wooden writing tablet: raised frames, dark beeswax filling (scratched letters catch the light),
    hinged with cord, a bronze stylus (pointed end to write, flat end to smooth the wax) lying beside it."""
    root = _root(name, loc, rot_z)
    wood = _m('tablet_box', (0.3, 0.18, 0.08), 0.55, bump=0.3, bump_scale=60)
    wax = _m('tablet_wax', (0.045, 0.03, 0.014), 0.55, bump=0.35, bump_scale=900)     # dark, soft-sheen beeswax
    W, D, T = 0.16, 0.12, 0.012
    for k, ang in ((0, 0.0), (1, math.radians(180 - open_deg))):
        leaf = link(bpy.data.objects.new(f'{name}_leaf{k}', None)); leaf.parent = root
        leaf.location = (0, 0, T / 2); leaf.rotation_euler = (0, 0, 0)
        x0 = (k * 2 - 1) * W / 2
        _box(f'{name}_frame{k}', (x0, 0, 0), (W, D, T), wood, leaf)
        _box(f'{name}_wax{k}', (x0, 0, T / 2 + 0.0005), (W - 0.022, D - 0.022, 0.0015), wax, leaf, bevel=0)
        if k:
            leaf.rotation_euler = (0, -ang * 0.0, 0)                  # (kept flat-open: reads best in an insert)
    # scratched lines of writing on one leaf (lighter where the stylus cut through the wax)
    scratch = _m('wax_scratch', (0.35, 0.26, 0.14), 0.5)
    rnd = random.Random(seed)
    for row in range(5):
        y = 0.035 - row * 0.016
        x = -W + 0.02
        while x < -0.02:
            ln = rnd.uniform(0.004, 0.014)
            _box(f'{name}_mark{row}_{x:.3f}', (x + ln / 2, y, T + 0.0016), (ln, 0.0012, 0.0004), scratch, root, bevel=0)
            x += ln + rnd.uniform(0.002, 0.005)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.003, depth=0.13, location=(0.05, -0.085, 0.004), rotation=(0, math.pi / 2, 0.3))
    st = bpy.context.object; st.name = name + '_stylus'; st.data.materials.append(_m('stylus_bronze', (0.5, 0.33, 0.14), 0.3, metal=1.0)); st.parent = root
    return root


def ostrakon(loc=(0, 0, 0), rot_z=0.0, text='ΘΕΜΙΣΘΟΚΛΕΣ\nΝΕΟΚΛΕΟΣ', seed=0, name='ostrakon'):
    """A broken potsherd (curved, black-glazed outside, red clay inside and at the broken edges) with a name
    scratched into its face - a vote to exile a man for ten years."""
    rnd = random.Random(seed)
    root = _root(name, loc, rot_z)
    bm = bmesh.new()
    n = 14
    outline = [(0.07 * (1 + rnd.uniform(-0.25, 0.25)) * math.cos(2 * math.pi * i / n),
                0.05 * (1 + rnd.uniform(-0.25, 0.25)) * math.sin(2 * math.pi * i / n)) for i in range(n)]
    top = [bm.verts.new(Vector((x, y, 0.006 + 0.02 * (x * x + y * y) ** 0.5 * -0.3))) for x, y in outline]
    bot = [bm.verts.new(Vector((x, y, 0.0 + 0.02 * (x * x + y * y) ** 0.5 * -0.3))) for x, y in outline]
    bm.faces.new(top); bm.faces.new(list(reversed(bot)))
    for i in range(n):
        bm.faces.new((top[i], top[(i + 1) % n], bot[(i + 1) % n], bot[i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name + '_sherd', me)); o.parent = root
    o.data.materials.append(_m('sherd_glaze', (0.03, 0.025, 0.02), 0.25, bump=0.15, bump_scale=300))
    sub = o.modifiers.new('round', 'SUBSURF'); sub.levels = 1
    _text(name + '_name', text, 0.011, _m('sherd_incised', (0.45, 0.2, 0.1), 0.8), root, (0, 0.004, 0.0075), (0, 0, rnd.uniform(-0.1, 0.1)))
    return root


def scroll(loc=(0, 0, 0), rot_z=0.0, sealed=True, name='scroll'):
    """A rolled papyrus, tied with cord, the knot covered by a clay sealing stamped with a seal (bulla)."""
    root = _root(name, loc, rot_z)
    pap = _m('papyrus', (0.62, 0.52, 0.34), 0.7, bump=0.4, bump_scale=200, sss=0.1)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.018, depth=0.24, location=(0, 0, 0.018), rotation=(0, math.pi / 2, 0))
    r = bpy.context.object; r.name = name + '_roll'; r.data.materials.append(pap); r.parent = root
    bpy.ops.mesh.primitive_torus_add(major_radius=0.0185, minor_radius=0.0015, location=(0, 0, 0.018), rotation=(0, math.pi / 2, 0))
    c = bpy.context.object; c.name = name + '_cord'; c.data.materials.append(_m('cord', (0.35, 0.28, 0.18), 0.9)); c.parent = root
    if sealed:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.011, location=(0, -0.012, 0.03))
        b = bpy.context.object; b.name = name + '_bulla'; b.scale = (1, 0.5, 1)
        b.data.materials.append(_m('clay_seal', (0.32, 0.14, 0.07), 0.6, bump=0.8, bump_scale=900)); b.parent = root
    return root


def aryballos(loc=(0, 0, 0), name='aryballos'):
    """Small round oil flask (Corinthian/Attic aryballos), glossy black with a red band."""
    root = _root(name, loc)
    bm = bmesh.new()
    prof = [(0.001, 0.0), (0.02, 0.003), (0.034, 0.025), (0.035, 0.045), (0.025, 0.065), (0.009, 0.075), (0.008, 0.085), (0.018, 0.09), (0.004, 0.092)]
    rings = []
    for r, z in prof:
        rings.append([bm.verts.new(Vector((r * math.cos(2 * math.pi * k / 24), r * math.sin(2 * math.pi * k / 24), z))) for k in range(24)])
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(24):
            bm.faces.new((a[k], a[(k + 1) % 24], b[(k + 1) % 24], b[k]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name + '_body', me)); o.data.materials.append(_m('black_gloss_pot', (0.02, 0.018, 0.016), 0.12)); o.parent = root
    for pg in o.data.polygons:
        pg.use_smooth = True
    return root


def astragaloi(loc=(0, 0, 0), n=5, seed=0, name='astragaloi'):
    """Knucklebones (sheep ankle bones): children's game pieces and dice, scattered (on vases and grave reliefs)."""
    rnd = random.Random(seed)
    root = _root(name, loc)
    bone = _m('knucklebone', (0.72, 0.65, 0.52), 0.55, bump=0.3, bump_scale=200, sss=0.2)
    for i in range(n):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(rnd.uniform(-0.06, 0.06), rnd.uniform(-0.04, 0.04), 0.008))
        b = bpy.context.object; b.name = f'{name}_{i}'; b.scale = (0.022, 0.014, 0.012); b.rotation_euler = (0, 0, rnd.uniform(0, 3))
        s = b.modifiers.new('round', 'SUBSURF'); s.levels = 2
        d = b.modifiers.new('waist', 'SIMPLE_DEFORM'); d.deform_method = 'TAPER'; d.factor = 0.5
        b.data.materials.append(bone); b.parent = root
    return root


def insert_set(target=(0, 0, 0), surface='wood', mood='warm', cam_dist=0.55, lens=60, fstop=5.6, height_deg=32.0,
               azimuth_deg=-25.0, res=(1280, 544), samples=48):
    """The insert shot: a surface under the objects, a hard RAKING key (low, from the side: every scratch and grain
    casts a shadow), a soft cool rim from behind, darkness around (deep shadows, rule r10), and a macro camera
    looking down at `height_deg`. surface: 'wood' (scanned planks) | 'stone' | 'cloth' (linen). mood: 'warm'
    (lamp/sun) | 'cold' (moonlight) | 'fire'. Returns the camera."""
    from lib import common, camera_moves
    t = Vector(target)
    bpy.ops.mesh.primitive_plane_add(size=3, location=t + Vector((0, 0, -0.0005))); s = bpy.context.object; s.name = 'insert_surface'
    try:
        from lib import scatter
        scan, tint, tiles = {'wood': ('brown_planks_04', (1.0, 0.85, 0.7), 0.6), 'stone': ('marble_01', (0.85, 0.8, 0.72), 0.5),
                             'cloth': ('rough_linen', (0.6, 0.5, 0.38), 0.25)}[surface]
        s.data.materials.append(scatter.scan_material('insert_' + surface, scan, tint=tint, tiles=tiles))
    except Exception:
        s.data.materials.append(_m('insert_' + surface, (0.25, 0.16, 0.09), 0.6))
    key_col = {'warm': (1.0, 0.72, 0.45), 'cold': (0.6, 0.72, 1.0), 'fire': (1.0, 0.55, 0.25)}[mood]
    a = math.radians(azimuth_deg + 100)
    # KEY: a low, narrow SPOT raking across the surface - a pool of light on the objects, falling off to darkness
    # around them (the insert look); small source = crisp texture shadows
    bpy.ops.object.light_add(type='SPOT', location=t + Vector((math.cos(a) * 0.9, math.sin(a) * 0.9, 0.28)))
    key = bpy.context.object; key.name = 'insert_key'
    key.data.energy = 40 if mood != 'cold' else 18; key.data.color = key_col
    key.data.spot_size = math.radians(28); key.data.spot_blend = 0.6; key.data.shadow_soft_size = 0.03
    common.look_at(key, t)
    # RIM: a faint cool edge from behind, so dark objects separate from the dark surface
    common.area_light('insert_rim', 2.5, (0.55, 0.65, 1.0) if mood != 'cold' else (0.8, 0.85, 1.0),
                      t + Vector((-math.cos(a) * 0.5, -math.sin(a) * 0.5 + 0.6, 0.35)), t, 0.25)
    w = bpy.context.scene.world or bpy.data.worlds.new('insert_world'); bpy.context.scene.world = w
    w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.02
    h, az = math.radians(height_deg), math.radians(azimuth_deg)
    loc = t + Vector((math.sin(az) * math.cos(h), -math.cos(az) * math.cos(h), math.sin(h))) * cam_dist
    cam = common.camera('insert_cam', loc, t, lens=lens, fstop=fstop, focus=t)
    camera_moves.apply_lens(cam, 'extreme_close', focus=None)
    cam.data.lens = lens; cam.data.dof.aperture_fstop = fstop; cam.data.dof.focus_distance = (t - loc).length
    common.render_settings(res=res, samples=samples)
    bpy.context.scene.view_settings.look = 'AgX - High Contrast'
    return cam

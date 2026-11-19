# TOOLS OF WORKING LIFE (WS16), c. 480 BC, built by code, plus hold() to put one in a person's hand.
#   farm      ard plough + yoke (Hesiod, Works and Days 427-436, tells how to build one), sickle, two-pronged
#             mattock (dikella), winnowing shovel, pruning hook
#   herding   shepherd's crook (kalaurops: the throwing club/crook of Greek herdsmen on vases)
#   fishing   wicker fish trap, trident, rod and line (fishermen on Attic cups; Oppian, later, lists the same gear)
#   hauling   carrying pole with two baskets, a two-wheeled farm cart with cross-bar wheels (Attic vases)
# Iron for blades, olive/oak wood, wicker, cord. All origins at the hand-grip (or the ground for big things).
import math
import random

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

from lib.common import link, principled


def _m(name, color, rough=0.6, metal=0.0, bump=0.1, bump_scale=150):
    m = bpy.data.materials.get(name)
    if m is None:
        m = principled(name, color, metal=metal, rough=rough, bump=bump, bump_scale=bump_scale); m.use_fake_user = True
    return m


def wood_mat():
    return _m('tool_wood', (0.24, 0.15, 0.08), rough=0.7, bump=0.25, bump_scale=60)


def iron_mat():
    return _m('tool_iron', (0.2, 0.19, 0.18), rough=0.45, metal=0.9, bump=0.35, bump_scale=300)


def wicker_mat():
    return _m('tool_wicker', (0.42, 0.31, 0.17), rough=0.85, bump=0.6, bump_scale=90)


def _tube(name, pts, r, mat, parent=None, r_end=None):
    """Round wooden/metal shaft along points (curve -> mesh), optionally tapering to r_end."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (*map(float, p), 1.0)
        sp.points[i].radius = 1.0 if r_end is None else 1.0 + (r_end / r - 1.0) * i / (len(pts) - 1)
    cu.bevel_depth = r; cu.bevel_resolution = 2
    tmp = link(bpy.data.objects.new(name + '_c', cu))
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg)); bpy.data.objects.remove(tmp)
    o = link(bpy.data.objects.new(name, me)); o.data.materials.clear(); o.data.materials.append(mat)
    for pg in o.data.polygons:
        pg.use_smooth = True
    if parent:
        o.parent = parent
    return o


def _blade(name, outline, thick, mat, parent=None):
    """A flat blade from a 2-D outline (x, z) in the XZ plane, `thick` m thick."""
    bm = bmesh.new()
    front = [bm.verts.new(Vector((x, -thick / 2, z))) for x, z in outline]
    back = [bm.verts.new(Vector((x, thick / 2, z))) for x, z in outline]
    bm.faces.new(front); bm.faces.new(list(reversed(back)))
    n = len(outline)
    for i in range(n):
        bm.faces.new((front[i], front[(i + 1) % n], back[(i + 1) % n], back[i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.data.materials.append(mat)
    if parent:
        o.parent = parent
    return o


def _root(name):
    return link(bpy.data.objects.new(name, None))


# ------------------------------------------------------------------ hand tools (origin = the grip)
def sickle(name='sickle'):
    """Iron sickle (drepanon): a short wooden handle and a deeply curved toothed blade (harvest scenes on vases)."""
    r = _root(name)
    _tube(name + '_handle', [Vector((0, 0, -0.06)), Vector((0, 0, 0.07))], 0.016, wood_mat(), r)
    out, inner = [], []
    for t in np.linspace(0, 1, 16):                                    # crescent: outer + inner arcs
        a = math.radians(-10 + 200 * t)
        out.append((0.16 * math.cos(a) - 0.13 + 0.13, 0.08 + 0.16 * math.sin(a)))
        ai = math.radians(-5 + 190 * t)
        inner.append((0.135 * math.cos(ai) + 0.005, 0.085 + 0.13 * math.sin(ai)))
    outline = [(x - 0.16, z) for x, z in out] + [(x - 0.16, z) for x, z in reversed(inner)]
    b = _blade(name + '_blade', outline, 0.002, iron_mat(), r); b.location = (0.16, 0, 0.0)
    return r


def mattock(name='mattock'):
    """Two-pronged mattock (dikella): long ash handle, iron head with two prongs (vineyard and field digging)."""
    r = _root(name)
    _tube(name + '_handle', [Vector((0, 0, -0.35)), Vector((0, 0, 0.55))], 0.017, wood_mat(), r)
    for dx in (-0.025, 0.025):
        _tube(name + f'_prong{dx}', [Vector((dx * 0.4, 0, 0.55)), Vector((dx, -0.12, 0.5)), Vector((dx * 1.2, -0.24, 0.38))],
              0.009, iron_mat(), r, r_end=0.004)
    return r


def winnowing_shovel(name='winnow'):
    """Winnowing shovel (ptyon): a long handle and a broad wooden blade, to throw threshed grain into the wind."""
    r = _root(name)
    _tube(name + '_handle', [Vector((0, 0, -0.5)), Vector((0, 0, 0.6))], 0.016, wood_mat(), r)
    b = _blade(name + '_blade', [(-0.13, 0.6), (0.13, 0.6), (0.11, 0.95), (0.0, 0.99), (-0.11, 0.95)], 0.012, wood_mat(), r)
    return r


def pruning_hook(name='pruning_hook'):
    """Pruning hook (drepane for vines): a short knife with a hooked tip."""
    r = _root(name)
    _tube(name + '_handle', [Vector((0, 0, -0.05)), Vector((0, 0, 0.06))], 0.014, wood_mat(), r)
    _blade(name + '_blade', [(-0.01, 0.06), (0.012, 0.06), (0.016, 0.2), (0.05, 0.24), (0.03, 0.26), (-0.005, 0.22)], 0.0025, iron_mat(), r)
    return r


def crook(name='crook'):
    """Shepherd's crook / staff (kalaurops): a long rough stick with a hooked top (herdsmen on vases and reliefs)."""
    r = _root(name)
    pts = [Vector((0.01 * math.sin(z * 6), 0, z)) for z in np.linspace(-0.8, 0.75, 9)]
    for t in np.linspace(0, 1, 7)[1:]:                                 # the hook
        a = math.pi * t
        pts.append(Vector((0.07 - 0.07 * math.cos(a), 0, 0.75 + 0.07 * math.sin(a))))
    _tube(name + '_staff', pts, 0.014, wood_mat(), r, r_end=0.011)
    return r


def trident(name='trident'):
    """Fisherman's trident (for spearing fish and octopus by torchlight): long shaft, three barbed iron prongs."""
    r = _root(name)
    _tube(name + '_shaft', [Vector((0, 0, -0.9)), Vector((0, 0, 1.2))], 0.014, wood_mat(), r)
    for dx in (-0.045, 0.0, 0.045):
        _tube(name + f'_prong{dx}', [Vector((dx * 0.3, 0, 1.2)), Vector((dx, 0, 1.28)), Vector((dx, 0, 1.42))], 0.004, iron_mat(), r, r_end=0.0015)
    _tube(name + '_bar', [Vector((-0.05, 0, 1.24)), Vector((0.05, 0, 1.24))], 0.005, iron_mat(), r)
    return r


def fishing_rod(name='rod'):
    """A reed fishing rod with a horsehair line and a bronze hook hanging from it."""
    r = _root(name)
    _tube(name + '_rod', [Vector((0, 0, -0.3)), Vector((0, -0.6, 1.3)), Vector((0, -1.4, 2.3))], 0.012, _m('reed', (0.45, 0.38, 0.2), 0.6), r, r_end=0.003)
    _tube(name + '_line', [Vector((0, -1.4, 2.3)), Vector((0, -1.5, 0.6))], 0.0006, _m('line', (0.6, 0.55, 0.45), 0.8), r)
    return r


def fish_trap(loc=(0, 0, 0), name='fish_trap'):
    """A wicker fish trap (kyrtos): a bottle-shaped basket with a funnel mouth, weighted with a stone."""
    r = _root(name); r.location = loc
    bm = bmesh.new()
    prof = [(0.12, 0.0), (0.2, 0.08), (0.24, 0.3), (0.2, 0.55), (0.1, 0.68), (0.06, 0.72)]
    seg = 20; rings = []
    for rad, z in prof:
        rings.append([bm.verts.new(Vector((rad * math.cos(2 * math.pi * k / seg), rad * math.sin(2 * math.pi * k / seg), z))) for k in range(seg)])
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(seg):
            bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name + '_body', me)); o.data.materials.append(wicker_mat()); o.parent = r
    o.rotation_euler = (0, math.pi / 2, 0); o.location = (0, 0, 0.24)
    wf = o.modifiers.new('weave', 'WIREFRAME'); wf.thickness = 0.008                  # open wickerwork
    return r


def carrying_pole(name='carrying_pole', fill=(0.45, 0.48, 0.5)):
    """A shoulder pole with a basket hanging from each end (fish sellers and water carriers on vases)."""
    from lib import props
    r = _root(name)
    _tube(name + '_pole', [Vector((-0.75, 0, 0)), Vector((0, 0, 0.03)), Vector((0.75, 0, 0))], 0.018, wood_mat(), r)
    for sx in (-1, 1):
        _tube(f'{name}_cord{sx}', [Vector((sx * 0.7, 0, 0)), Vector((sx * 0.7, 0, -0.55))], 0.003, _m('cord', (0.35, 0.28, 0.18), 0.9), r)
        b = props.basket((sx * 0.7, 0, -0.85), kind='carry', fill=fill, name=f'{name}_basket{sx}')
        w = b.matrix_world.copy(); b.parent = r; b.matrix_world = w
    return r


# ------------------------------------------------------------------ big things (origin on the ground)
def ard_plough(loc=(0, 0, 0), heading_deg=0.0, name='ard'):
    """The Greek ard (arotron) as Hesiod describes it (Works and Days 427-436): a curved wooden share-beam (the
    'gyes', ideally a naturally bent oak), a pole (histoboeus) of laurel or elm to the yoke, a handle (echetle)
    for the ploughman, an iron-tipped share that scratches the furrow. With the yoke for two oxen."""
    r = _root(name); r.location = loc; r.rotation_euler = (0, 0, math.radians(heading_deg))
    W = wood_mat()
    _tube(name + '_share_beam', [Vector((0, 0.0, 0.02)), Vector((0, 0.45, 0.0)), Vector((0, 0.9, 0.25)), Vector((0, 1.0, 0.7))], 0.05, W, r, r_end=0.035)
    _tube(name + '_pole', [Vector((0, 0.9, 0.35)), Vector((0, -1.0, 0.75)), Vector((0, -2.6, 0.95))], 0.04, W, r, r_end=0.03)
    _tube(name + '_handle', [Vector((0, 1.0, 0.7)), Vector((0, 1.25, 1.05)), Vector((0.12, 1.3, 1.08))], 0.025, W, r)
    _tube(name + '_share', [Vector((0, -0.05, 0.02)), Vector((0, -0.32, -0.02))], 0.025, iron_mat(), r, r_end=0.006)
    # the yoke across the oxen's necks, lashed to the pole end
    _tube(name + '_yoke', [Vector((-0.75, -2.65, 1.25)), Vector((-0.35, -2.65, 1.05)), Vector((0, -2.62, 1.0)),
                           Vector((0.35, -2.65, 1.05)), Vector((0.75, -2.65, 1.25))], 0.045, W, r)
    for sx in (-1, 1):                                                  # the neck bows (straps) of the yoke
        pts = [Vector((sx * 0.55 + 0.18 * math.cos(a), -2.65, 1.12 - 0.3 * math.sin(a))) for a in np.linspace(0, math.pi, 9)]
        _tube(f'{name}_bow{sx}', pts, 0.015, _m('tack_leather', (0.1, 0.055, 0.03), 0.7), r)
    return r


def ox_team(loc=(0, 0, 0), heading_deg=0.0, seed=0, name='ox_team'):
    """Two oxen yoked to the ard (the main session's CC-BY cow scan, library/scans/animal_cow, as the ox), plus
    the plough itself. Returns the root."""
    from lib import scatter
    r = _root(name); r.location = loc; r.rotation_euler = (0, 0, math.radians(heading_deg))
    ard = ard_plough(name=name + '_ard'); ard.parent = r
    try:                                                                # Session G's animals.py: real-size ox
        from lib import animals
        for i, sx in enumerate((-1, 1)):
            ox = animals.load('ox', (sx * 0.55, -3.6, 0), heading_deg=0.0, name=f'{name}_ox{i}')   # heading 0 = -Y
            w = ox.matrix_world.copy(); ox.parent = r; ox.matrix_world = r.matrix_world @ w
    except Exception as e:
        print('ox_team: animals.py unavailable, trying the raw cow scan -', e)
        try:
            vs = scatter.load_scan('animal_cow')
            for i, sx in enumerate((-1, 1)):
                inst = bpy.data.objects.new(f'{name}_ox{i}', None); link(inst)
                inst.instance_type = 'COLLECTION'; inst.instance_collection = vs[0]
                inst.location = (sx * 0.55, -3.6, 0); inst.rotation_euler = (0, 0, math.pi); inst.parent = r
        except Exception as e2:                                         # scan not downloaded on this machine
            print('ox_team: no cow scan here -', e2)
    return r


def cart(loc=(0, 0, 0), heading_deg=0.0, load='amphorae', seed=0, name='cart'):
    """A two-wheeled farm cart (hamaxa) with CROSS-BAR wheels (a plank disc braced by a bar, typical on Archaic and
    Classical Greek vases), a slatted bed and a pole for a mule or oxen. load: 'amphorae' | 'sacks' | 'hay' | None."""
    from lib import props, market
    rnd = random.Random(seed)
    r = _root(name); r.location = loc; r.rotation_euler = (0, 0, math.radians(heading_deg))
    W = wood_mat()
    props._box(name + '_bed', (0, 0, 0.8), (1.3, 2.0, 0.06), W, parent=r)
    for sx in (-1, 1):
        props._box(f'{name}_side{sx}', (sx * 0.62, 0, 1.0), (0.05, 2.0, 0.35), W, parent=r)
    _tube(name + '_pole', [Vector((0, -1.0, 0.82)), Vector((0, -3.0, 0.95))], 0.045, W, r)
    for sx in (-1, 1):                                                  # cross-bar wheels on one axle
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=28, radius1=0.48, radius2=0.48, depth=0.07)
        me = bpy.data.meshes.new(f'{name}_wheel{sx}'); bm.to_mesh(me); bm.free()
        w = link(bpy.data.objects.new(f'{name}_wheel{sx}', me)); w.data.materials.append(W); w.parent = r
        w.location = (sx * 0.78, 0.1, 0.48); w.rotation_euler = (0, math.pi / 2, 0)
        props._box(f'{name}_bar{sx}', (sx * 0.82, 0.1, 0.48), (0.03, 0.9, 0.09), W, parent=r)
    _tube(name + '_axle', [Vector((-0.85, 0.1, 0.48)), Vector((0.85, 0.1, 0.48))], 0.035, W, r)
    if load == 'amphorae':
        for i in range(6):
            a = props.amphora(((i % 3 - 1) * 0.35, (i // 3 - 0.5) * 0.6, 0.83), height=0.62, lean=rnd.uniform(-0.15, 0.15),
                              seed=seed + i, name=f'{name}_amph{i}')
            w = a.matrix_world.copy(); a.parent = r; a.matrix_world = r.matrix_world @ w
    elif load == 'sacks':
        for i in range(5):
            market.grain_sack(Vector(((i % 3 - 1) * 0.38, (i // 3 - 0.5) * 0.6, 0.83)), parent=r, seed=seed + i, name=f'{name}_sack{i}')
    elif load == 'hay':
        # the harvest load: BOUND SHEAVES of wheat stacked on the bed, ears outward, in three courses narrowing to
        # the top (how a sheaf cart is loaded so it rides without spilling) - real stalks and ears, not a mound
        from lib import countryside
        countryside.sheaf_heap((0, 0, -50), n=0, seed=seed, name=f'{name}_sheaf')   # builds the sheaf prototype only
        col = bpy.data.collections[f'{name}_sheaf_src']
        rnd = random.Random(seed)
        k = 0
        for layer, (xs, z) in enumerate((((-0.42, 0.0, 0.42), 0.95), ((-0.24, 0.24), 1.16), ((0.0,), 1.36))):
            for x in xs:
                for sy in (-1, 1):
                    inst = bpy.data.objects.new(f'{name}_sheaf{k}', None); link(inst); k += 1
                    inst.instance_type = 'COLLECTION'; inst.instance_collection = col; inst.parent = r
                    # lying along the cart, butts in the middle, ears out over front and back
                    inst.location = (x + rnd.uniform(-0.04, 0.04), sy * 0.08 + rnd.uniform(-0.05, 0.05), z + rnd.uniform(-0.02, 0.03))
                    inst.rotation_euler = (math.radians(-90 * sy + rnd.uniform(-8, 8)), math.radians(rnd.uniform(-6, 6)), rnd.uniform(-0.1, 0.1))   # ears point out (+-y)
    return r


# ------------------------------------------------------------------ put a tool in a hand
def hold(tool_root, rig, side='R', offset=(0, 0, 0), rot_deg=(0, 0, 0), bone=None):
    """Put a tool (origin = its grip) in a person's hand: snapped to the wrist bone's position + `offset` (in the
    bone's frame), turned by rot_deg, and parented to the bone so it follows every gesture. Pose the arm first."""
    from lib import cast
    b = bone or f'wrist.{side}'
    pb = rig.pose.bones[b]
    m = rig.matrix_world @ pb.matrix
    # the palm is a little beyond the wrist along the bone, the grip crosses the hand
    grip = m @ Vector((0.0, 0.06, 0.0)) + m.to_3x3() @ Vector(offset)
    tool_root.matrix_world = Matrix.Translation(grip) @ (m.to_3x3() @ Matrix.Rotation(math.pi / 2, 3, 'X')).to_4x4() \
        @ (Matrix.Rotation(math.radians(rot_deg[0]), 4, 'X') @ Matrix.Rotation(math.radians(rot_deg[1]), 4, 'Y')
           @ Matrix.Rotation(math.radians(rot_deg[2]), 4, 'Z'))
    cast.parent_to_bone(tool_root, rig, b)
    return tool_root


TRADE_TOOLS = {        # role (tc/crowd.py) -> which tool the person carries (dress(..., tools=True))
    'farmer': ('mattock', 'sickle'), 'shepherd': ('crook',), 'fisherman': ('trident', 'fishing_rod'),
    'rower': (), 'potter': (), 'smith': (), 'trader': (), 'villager': ('carrying_pole',),
}
BUILDERS = {'sickle': sickle, 'mattock': mattock, 'winnowing_shovel': winnowing_shovel, 'pruning_hook': pruning_hook,
            'crook': crook, 'trident': trident, 'fishing_rod': fishing_rod, 'carrying_pole': carrying_pole}


def tool_for(role, seed=0):
    """The tool a person of this trade carries (or None), built and returned (not yet in a hand)."""
    opts = TRADE_TOOLS.get(role) or ()
    if not opts:
        return None
    k = opts[seed % len(opts)]
    return BUILDERS[k](f'{k}_{seed}')

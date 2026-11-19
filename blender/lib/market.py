# MARKET & DAILY LIFE (WS16): trading scenes, goods, villages and fishing beaches of c. 480 BC, built by code.
#   goods      fish, bread loaves, figs, olives, grain sacks, wool bales, stacked pots, oil/wine amphorae,
#              silver 'owl' coins, a merchant's balance (weighing scenes: the Arkesilas cup, c. 560 BC)
#   stalls     trestle tables under linen awnings, one per trade (fish, bread, produce, pottery, oil, cloth)
#   villages   farmhouses (architecture.house, main session's kit) along crooked lanes, field walls, a well,
#              a domed bread oven, a threshing floor (countryside)
#   fishing    boats pulled up on the beach (props.fishing_boat, Session E's kit), nets drying on poles, fish
#              baskets, a drying rack for split fish
# Sources: Aristophanes (Knights, Wasps, Acharnians: agora sellers of fish, bread, figs, garlic, pots); Athenian
# Agora excavations (stoa shops, weights and measures, the 'owl' tetradrachm, struck from Laurion silver - the
# silver that paid for the fleet of Salamis, Herodotus 7.144); Attic vases of fishermen, potters, merchants
# weighing goods. Rule r9: our own designs from these sources.
import math
import random

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

from lib.common import link, principled


def _mat(name, color, rough=0.6, metal=0.0, bump=0.1, bump_scale=200, sss=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = principled(name, color, metal=metal, rough=rough, bump=bump, bump_scale=bump_scale, sss=sss)
        m.use_fake_user = True
    return m


def _root(name, loc, heading_deg=0.0):
    r = link(bpy.data.objects.new(name, None))
    r.location = loc; r.rotation_euler = (0, 0, math.radians(heading_deg))
    return r


def _obj(name, bm, mat, parent=None, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons:
            p.use_smooth = True
    if parent:
        o.parent = parent
    return o


def _lathe(bm, profile, seg=24, matrix=Matrix.Identity(4)):
    """Spin a (radius, z) profile round Z into bm (pots, loaves, coins, figs)."""
    rings = []
    for r, z in profile:
        ring = [bm.verts.new(matrix @ Vector((r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg), z)))
                for k in range(seg)]
        rings.append(ring)
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(seg):
            bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    return rings


# ------------------------------------------------------------------ goods
def fish_material(kind='silver'):
    """Wet fish skin: silver-blue back fading to a white belly, fine scales (Voronoi bump), glossy."""
    name = f'fish_{kind}'
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; L = nt.links.new; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(tc.outputs['Object'], sep.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    back, belly = {'silver': ((0.1, 0.16, 0.2), (0.75, 0.75, 0.72)), 'red': ((0.5, 0.12, 0.08), (0.8, 0.6, 0.5)),
                   'tuna': ((0.04, 0.06, 0.12), (0.6, 0.62, 0.62))}[kind]
    ramp.color_ramp.elements[0].color = (*belly, 1); ramp.color_ramp.elements[1].color = (*back, 1)
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -0.02; mr.inputs['From Max'].default_value = 0.03
    L(sep.outputs['Z'], mr.inputs['Value']); L(mr.outputs['Result'], ramp.inputs['Fac'])
    L(ramp.outputs['Color'], b.inputs['Base Color'])
    vor = nt.nodes.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 260; L(tc.outputs['Object'], vor.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.25; L(vor.outputs['Distance'], bp.inputs['Height'])
    L(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.18; b.inputs['Metallic'].default_value = 0.35 if kind == 'silver' else 0.1
    return m


def fish(loc, length=0.3, kind='silver', heading_deg=0.0, parent=None, seed=0, name='fish'):
    """A whole fish lying on its side (sea bream, mullet, mackerel: the agora's most argued-over food, Aristophanes):
    a lofted spindle body, a forked tail, a dorsal fin ridge, a dark eye."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    L = length; seg = 12
    rings = []
    for i, t in enumerate(np.linspace(0, 1, 14)):
        h = L * 0.13 * math.sin(math.pi * min(1.0, t * 1.05)) ** 0.8 + 0.002     # body depth
        w = h * 0.45
        x = -L / 2 + L * t * 0.86
        ring = [bm.verts.new(Vector((x, w * math.cos(2 * math.pi * k / seg), h * math.sin(2 * math.pi * k / seg) + 0.6 * h)))
                for k in range(seg)]
        rings.append(ring)
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(seg):
            bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    tx = -L / 2 + L * 0.86                                              # forked tail
    tail = [bm.verts.new(Vector((tx, 0, 0.6 * 0.004))), bm.verts.new(Vector((tx + L * 0.16, 0.001, L * 0.11))),
            bm.verts.new(Vector((tx + L * 0.1, 0, 0.0))), bm.verts.new(Vector((tx + L * 0.16, 0.001, -L * 0.09)))]
    bm.faces.new(tail)
    dorsal = [bm.verts.new(Vector((-L * 0.15, 0, L * 0.2))), bm.verts.new(Vector((L * 0.15, 0, L * 0.16))),
              bm.verts.new(Vector((L * 0.1, 0, L * 0.2))), bm.verts.new(Vector((-L * 0.1, 0, L * 0.26)))]
    bm.faces.new(dorsal)
    o = _obj(name, bm, fish_material(kind), parent)
    # lying on its side on the table
    o.location = loc; o.rotation_euler = (math.pi / 2, 0, math.radians(heading_deg) + rnd.uniform(-0.3, 0.3))
    bmesh_eye = bmesh.new()
    bmesh.ops.create_uvsphere(bmesh_eye, u_segments=8, v_segments=6, radius=L * 0.018,
                              matrix=Matrix.Translation(Vector((L * 0.38, L * 0.04, L * 0.085))))
    eye = _obj(name + '_eye', bmesh_eye, _mat('fish_eye', (0.01, 0.01, 0.01), rough=0.05), o)
    return o


def loaf(loc, r=0.1, parent=None, seed=0, name='loaf'):
    """A round Greek loaf (artos), domed, its top scored into four (as on terracotta models of bread from Boeotia)."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    prof = [(0.001, 0.0), (r * 0.9, 0.0), (r, r * 0.12), (r * 0.95, r * 0.35), (r * 0.7, r * 0.55), (r * 0.35, r * 0.66), (0.001, r * 0.68)]
    _lathe(bm, prof, seg=24)
    for v in bm.verts:                                                  # four scored grooves on top
        a = math.atan2(v.co.y, v.co.x)
        if v.co.z > r * 0.3:
            v.co.z -= r * 0.06 * max(0.0, math.cos(2 * a)) ** 30
        v.co.x *= 1 + rnd.uniform(-0.04, 0.04)
    o = _obj(name, bm, _mat('bread_crust', (0.42, 0.22, 0.08), rough=0.7, bump=0.3, bump_scale=120), parent)
    o.location = loc
    return o


def heap(loc, kind='figs', radius=0.14, n=40, parent=None, seed=0, name='heap'):
    """A heap of small produce (figs, olives, garlic bulbs, onions), built as one mesh of many little shapes."""
    rnd = random.Random(seed)
    size, color = {'figs': (0.022, (0.18, 0.06, 0.1)), 'olives': (0.009, (0.05, 0.06, 0.02)),
                   'garlic': (0.02, (0.75, 0.7, 0.6)), 'onions': (0.03, (0.45, 0.22, 0.08)),
                   'grain': (0.004, (0.6, 0.45, 0.18))}[kind]
    bm = bmesh.new()
    for i in range(n):
        a = rnd.uniform(0, 2 * math.pi); rr = radius * math.sqrt(rnd.random())
        z = (radius - rr) * 0.6 + size
        bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=size * rnd.uniform(0.85, 1.15),
                                  matrix=Matrix.Translation(Vector((rr * math.cos(a), rr * math.sin(a), z)))
                                  @ Matrix.Scale(1.25 if kind == 'figs' else 1.0, 4, Vector((0, 0, 1))))
    o = _obj(name, bm, _mat(f'produce_{kind}', color, rough=0.4 if kind == 'olives' else 0.6, sss=0.1), parent)
    o.location = loc
    return o


def grain_sack(loc, h=0.55, parent=None, seed=0, open_top=False, name='sack'):
    """A full sack (grain, beans, salt): plump body, gathered neck tied with cord, or rolled open to show grain."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    r = h * 0.36
    # a full sack SLUMPS: widest low down, flattened where it sits, the top gathered into a tied neck that flops
    prof = [(0.001, 0.0), (r * 1.05, 0.0), (r * 1.18, h * 0.12), (r * 1.1, h * 0.35), (r * 0.95, h * 0.62), (r * 0.7, h * 0.8)]
    prof += [(r * 0.78, h * 0.84), (r * 0.82, h * 0.86)] if open_top else [(r * 0.22, h * 0.9), (r * 0.18, h * 0.98), (r * 0.32, h * 1.08)]
    _lathe(bm, prof, seg=28)
    for v in bm.verts:                                                  # lumpy grain inside, cloth creases
        a = math.atan2(v.co.y, v.co.x)
        k = 1 + 0.06 * math.sin(3 * a + seed) + 0.03 * math.sin(7 * a + v.co.z * 20 + seed)
        v.co.x *= k; v.co.y *= k * 0.88
        v.co.x += 0.006 * math.sin(v.co.z * 40 + seed); v.co.y += 0.006 * math.cos(v.co.z * 33 + seed)
        if v.co.z > h * 0.9:                                            # the neck flops to one side
            v.co.x += (v.co.z - h * 0.9) * 0.8
    from lib import wardrobe
    mat = bpy.data.materials.get('sack_hessian') or wardrobe.scan_cloth('sack_hessian', 'hessian_230', (0.42, 0.34, 0.22),
                                                                       tiles=(5, 3), grime=0.2, sheen=0.05)
    o = _obj(name, bm, mat, parent)
    uv = o.data.uv_layers.new(name='UVMap')
    for poly in o.data.polygons:
        for li in poly.loop_indices:
            co = o.data.vertices[o.data.loops[li].vertex_index].co
            uv.data[li].uv = ((math.atan2(co.y, co.x) / (2 * math.pi)) % 1.0, co.z / h)
    o.location = loc; o.rotation_euler = (0, 0, rnd.uniform(0, 6.3))
    if open_top:
        heap(Vector((0, 0, h * 0.82)), 'grain', radius=r * 0.8, n=120, parent=o, seed=seed, name=name + '_grain')
    return o


def wool_bale(loc, size=(0.7, 0.5, 0.45), parent=None, seed=0, name='wool_bale'):
    """A bale of raw fleece (Miletus and Attic wool) bound with cords: a soft lumpy block, fibrous, off-white."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=4, use_grid_fill=True)
    rnd = random.Random(seed)
    for v in bm.verts:
        p = v.co
        k = 1 + rnd.uniform(-0.04, 0.04)
        v.co = Vector((p.x * size[0] * k, p.y * size[1] * k, (p.z + 0.5) * size[2] * k))
    o = _obj(name, bm, _mat('raw_wool', (0.62, 0.57, 0.47), rough=0.95, bump=0.6, bump_scale=60, sss=0.05), parent)
    o.modifiers.new('soft', 'SUBSURF').levels = 2
    o.location = loc
    return o


def owl_coins(loc, n=12, parent=None, seed=0, name='owls'):
    """Athenian silver tetradrachms ('owls', c. 24 mm, Athena's head / the owl): a little spilled stack.
    Struck from Laurion silver - Themistocles had the new silver strike of 483 BC spent on 200 triremes."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    for i in range(n):
        stacked = i < n * 0.6
        x, y = (rnd.gauss(0, 0.002), rnd.gauss(0, 0.002)) if stacked else (rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05))
        z = (i * 0.0032 if stacked else 0.0)
        m = Matrix.Translation(Vector((x, y, z))) @ Matrix.Rotation(rnd.uniform(-0.08, 0.08), 4, 'X')
        _lathe(bm, [(0.001, 0), (0.0115, 0.0), (0.012, 0.0015), (0.011, 0.003), (0.001, 0.0032)], seg=20, matrix=m)
    o = _obj(name, bm, _mat('silver_coin', (0.8, 0.8, 0.78), metal=1.0, rough=0.3, bump=0.2, bump_scale=900), parent)
    o.location = loc
    return o


def balance(loc, parent=None, heading_deg=0.0, name='balance'):
    """A merchant's equal-arm balance: a bronze beam on a hand-held loop, two shallow pans on three cords each
    (weighing scenes on Archaic vases; official bronze pans and lead weights found in the Athenian Agora)."""
    from lib import props
    bronze = _mat('balance_bronze', (0.5, 0.33, 0.14), metal=1.0, rough=0.35)
    root = _root(name, loc, heading_deg)
    if parent:
        root.parent = parent
    props._cyl(name + '_beam', (0, 0, 0.42), 0.004, 0.46, bronze, rot=(0, math.pi / 2, 0), parent=root)
    props._cyl(name + '_post', (0, 0, 0.47), 0.003, 0.1, bronze, parent=root)
    for sx in (-1, 1):
        bm = bmesh.new()
        _lathe(bm, [(0.001, 0.0), (0.06, 0.006), (0.075, 0.02)], seg=24)
        pan = _obj(f'{name}_pan{sx}', bm, bronze, root); pan.location = (sx * 0.22, 0, 0.18)
        for k in range(3):
            a = 2 * math.pi * k / 3
            p0 = Vector((sx * 0.22 + 0.07 * math.cos(a), 0.07 * math.sin(a), 0.2)); p1 = Vector((sx * 0.22, 0, 0.42))
            props._tube(f'{name}_cord{sx}{k}', [p0, p1], 0.0008, _mat('cord', (0.35, 0.28, 0.18), rough=0.9), parent=root, poly=True)
    return root


# ------------------------------------------------------------------ stalls
def stall(loc=(0, 0, 0), heading_deg=0.0, trade='fish', seed=0, awning=None, name=None):
    """A market stall (the agora had wooden trestle tables and wicker booths, Demosthenes 18.169 'the booths'):
    a trestle table, a linen awning on four poles, and the goods of one TRADE laid out:
      fish | bread | produce (figs, olives, garlic, onions) | pottery | oil (amphorae) | wool | grain
    Every stall carries a balance and a few owls (coins) for the trading moment."""
    from lib import props, wardrobe
    rnd = random.Random(seed)
    name = name or f'stall_{trade}_{seed}'
    root = _root(name, loc, heading_deg)
    wood = bpy.data.materials.get('old_wood') or props.old_wood()
    W, D, H = 2.0, 0.8, 0.78
    props._box(name + '_top', (0, 0, H), (W, D, 0.05), wood, parent=root)
    for sx in (-1, 1):                                                  # trestles
        for sy in (-1, 1):
            props._box(name + f'_leg{sx}{sy}', (sx * (W / 2 - 0.15), sy * (D / 2 - 0.08), H / 2), (0.06, 0.06, H), wood, parent=root)
    for sx in (-1, 1):                                                  # awning poles + cloth
        for sy in (-1, 1):
            props._box(name + f'_pole{sx}{sy}', (sx * (W / 2 + 0.1), sy * (D / 2 + 0.25), 1.15), (0.05, 0.05, 2.3), wood, parent=root)
    cloth = awning or rnd.choice([(0.52, 0.47, 0.37), (0.45, 0.3, 0.1), (0.3, 0.06, 0.04), (0.42, 0.38, 0.3)])
    am = wardrobe.patterned_cloth(name + '_awning', 'rough_linen', cloth, band=rnd.choice([(0.07, 0.1, 0.26), (0.3, 0.05, 0.035), None]) or None,
                                  border=rnd.choice(['lines', 'zigzag', None]), tiles=(4, 4), width=0.08, grime=0.35, sheen=0.1)
    bm = bmesh.new()                                                    # a sagging cloth roof, sloping to the front
    nx, ny = 24, 12
    vs = [[bm.verts.new(Vector(((i / (nx - 1) - 0.5) * (W + 0.35), (j / (ny - 1) - 0.5) * (D + 0.7),
                                 2.28 - 0.25 * (1 - j / (ny - 1)) - 0.08 * math.sin(math.pi * i / (nx - 1)) * math.sin(math.pi * j / (ny - 1)))))
           for i in range(nx)] for j in range(ny)]
    for j in range(ny - 1):
        for i in range(nx - 1):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    aw = _obj(name + '_awning', bm, am, root)
    uv = aw.data.uv_layers.new(name='UVMap')
    for poly in aw.data.polygons:
        for li in poly.loop_indices:
            co = aw.data.vertices[aw.data.loops[li].vertex_index].co
            uv.data[li].uv = (co.x / (W + 0.35) + 0.5, co.y / (D + 0.7) + 0.5)
    aw.modifiers.new('thick', 'SOLIDIFY').thickness = 0.003
    top = H + 0.025
    if trade == 'fish':
        for k in range(rnd.randint(16, 22)):                           # a full slab: big and small fish, overlapping
            fish(Vector((rnd.uniform(-0.85, 0.85), rnd.uniform(-0.28, 0.28), top + 0.03 + 0.02 * (k % 3))), length=rnd.uniform(0.28, 0.55),
                 kind=rnd.choice(['silver', 'silver', 'red']), heading_deg=rnd.uniform(-20, 20), parent=root, seed=seed + k, name=f'{name}_fish{k}')
        props.basket((0.9, 0.9, 0.0), kind='carry', fill=(0.45, 0.48, 0.5), name=f'{name}_fishbasket')
    elif trade == 'bread':
        for k in range(rnd.randint(22, 30)):                           # loaves piled two deep
            loaf(Vector((rnd.uniform(-0.88, 0.88), rnd.uniform(-0.3, 0.3), top + (0.08 if k > 16 else 0.0))), r=rnd.uniform(0.09, 0.13),
                 parent=root, seed=seed + k, name=f'{name}_loaf{k}')
        props.basket((-0.9, -0.8, 0.0), kind='flat', fill=(0.42, 0.22, 0.08), name=f'{name}_breadtray')
    elif trade == 'produce':
        for k, kind in enumerate(['figs', 'olives', 'garlic', 'onions', 'figs']):
            heap(Vector((-0.8 + k * 0.4, rnd.uniform(-0.1, 0.1), top)), kind, radius=0.2, n=140 if kind != 'olives' else 500,
                 parent=root, seed=seed + k, name=f'{name}_{kind}{k}')
        for k in range(3):                                              # more in baskets on the ground
            props.basket((-0.7 + k * 0.7, -0.8, 0.0), kind='carry', fill=[(0.18, 0.06, 0.1), (0.05, 0.06, 0.02), (0.45, 0.22, 0.08)][k],
                         name=f'{name}_prodbasket{k}')
    elif trade == 'pottery':
        for k in range(7):
            props.amphora((rnd.uniform(-0.8, 0.8), rnd.uniform(-0.2, 0.2), top), height=rnd.uniform(0.25, 0.4), seed=seed + k,
                          name=f'{name}_pot{k}')
    elif trade == 'oil':
        for k in range(6):
            a = props.amphora(((k - 2.5) * 0.36, -0.75, 0.0), height=0.72, lean=rnd.uniform(-0.1, 0.1), seed=seed + k, name=f'{name}_amph{k}')
    elif trade == 'wool':
        for k in range(3):
            wool_bale(Vector((-0.6 + k * 0.6, 0, top)), parent=root, seed=seed + k, name=f'{name}_wool{k}')
    elif trade == 'grain':
        for k in range(5):
            grain_sack(Vector((-0.9 + k * 0.45, -0.85, 0.0)), open_top=(k % 2 == 0), parent=root, seed=seed + k, name=f'{name}_sack{k}')
    balance(Vector((0.75, 0.25, top)), parent=root, name=f'{name}_balance')
    owl_coins(Vector((0.55, 0.3, top)), parent=root, seed=seed, name=f'{name}_owls')
    # loose props (baskets, amphorae) were placed in world space: move them with the stall
    for o in list(bpy.data.objects):
        if o.parent is None and o.name.startswith(name + '_') and o is not root:
            w = o.matrix_world.copy(); o.parent = root; o.matrix_world = root.matrix_world @ w
    return root


def market(loc=(0, 0, 0), heading_deg=0.0, rows=2, per_row=4, seed=0, name='market'):
    """An agora market: rows of stalls of mixed trades facing a lane (people go in the lane: crowd/WS2 +
    wardrobe.dress). Returns the root empty."""
    rnd = random.Random(seed)
    root = _root(name, loc, heading_deg)
    trades = ['fish', 'bread', 'produce', 'pottery', 'oil', 'wool', 'grain']
    for r in range(rows):
        for i in range(per_row):
            x = (i - (per_row - 1) / 2) * 3.0 + rnd.uniform(-0.3, 0.3)
            y = (r - (rows - 1) / 2) * 6.0
            st = stall((x, y, 0), 180 if r % 2 else 0, rnd.choice(trades), seed=seed * 50 + r * 10 + i, name=f'{name}_s{r}{i}')
            st.parent = root
    return root


# ------------------------------------------------------------------ villages + fishing beaches
def well(loc, parent=None, name='well'):
    """A village well: a round stone kerb (well-head) with a wooden beam frame and a rope + bucket."""
    from lib import props, countryside
    root = _root(name, loc)
    if parent:
        root.parent = parent
    stone = countryside.stone_material()
    bm = bmesh.new()
    _lathe(bm, [(0.45, 0.0), (0.5, 0.05), (0.5, 0.65), (0.42, 0.7), (0.38, 0.68), (0.38, 0.0)], seg=32)
    _obj(name + '_kerb', bm, stone, root)
    wood = bpy.data.materials.get('old_wood') or props.old_wood()
    for sx in (-1, 1):
        props._box(f'{name}_post{sx}', (sx * 0.6, 0, 1.0), (0.08, 0.08, 2.0), wood, parent=root)
    props._box(f'{name}_beam', (0, 0, 1.95), (1.35, 0.08, 0.08), wood, parent=root)
    props._tube(f'{name}_rope', [Vector((0, 0, 1.9)), Vector((0, 0, 0.9))], 0.006, _mat('cord', (0.35, 0.28, 0.18), rough=0.9), parent=root, poly=True)
    props._cyl(f'{name}_bucket', (0, 0, 0.8), 0.1, 0.18, props.terracotta(), parent=root)
    return root


def bread_oven(loc, heading_deg=0.0, parent=None, name='oven'):
    """A domed clay bread oven (kribanos / ipnos) on a stone base, its mouth blackened by smoke."""
    from lib import props
    root = _root(name, loc, heading_deg)
    if parent:
        root.parent = parent
    clay = _mat('oven_clay', (0.46, 0.33, 0.22), rough=0.9, bump=0.5, bump_scale=40)
    bm = bmesh.new()
    _lathe(bm, [(0.75, 0.0), (0.75, 0.15), (0.72, 0.4), (0.6, 0.7), (0.35, 0.92), (0.001, 0.98)], seg=32,
           matrix=Matrix.Translation((0, 0, 0.5)))
    _obj(name + '_dome', bm, clay, root)
    props._box(name + '_base', (0, 0, 0.25), (1.7, 1.7, 0.5), bpy.data.materials.get('fieldstone') or clay, parent=root)
    props._box(name + '_mouth', (0, -0.72, 0.75), (0.4, 0.1, 0.3), _mat('soot', (0.01, 0.008, 0.006), rough=0.95), parent=root)
    return root


def village(loc=(0, 0, 0), n=9, seed=0, spread=34.0, name='village'):
    """A Greek village (kome) of the countryside: farmhouses (architecture.house) facing crooked lanes, each with a
    walled yard; a well in the little square, a bread oven, a threshing floor at the edge, field walls going out
    into the fields. Returns the dict of parts."""
    from lib import architecture, countryside
    rnd = random.Random(seed)
    root = _root(name, loc)
    parts = {'houses': [], 'walls': []}
    placed = []
    tries = 0
    while len(placed) < n and tries < n * 30:
        tries += 1
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(7.0, spread)
        x, y = loc[0] + r * math.cos(a), loc[1] + r * math.sin(a)
        if any(math.hypot(x - px, y - py) < 13.0 for px, py in placed):
            continue
        w, d = rnd.uniform(6.5, 10.0), rnd.uniform(7.5, 12.0)
        heading = math.degrees(math.atan2(loc[1] - y, loc[0] - x)) + rnd.uniform(-25, 25) + 90   # face the square
        h = architecture.house((x, y, loc[2]), w=w, d=d, h=rnd.uniform(2.9, 3.4), heading_deg=heading, seed=seed + len(placed),
                               name=f'{name}_house{len(placed)}')
        parts['houses'].append(h); placed.append((x, y))
        # a walled yard behind the house
        hr = math.radians(heading)
        bx, by = x - math.sin(hr) * (d / 2 + 4), y + math.cos(hr) * (d / 2 + 4)
        c = [(bx + dx * math.cos(hr) - dy * math.sin(hr), by + dx * math.sin(hr) + dy * math.cos(hr))
             for dx, dy in ((-w / 2, -4), (-w / 2, 3.5), (w / 2, 3.5), (w / 2, -4))]
        parts['walls'].append(countryside.dry_stone_wall(c, height=1.3, seed=seed + 100 + len(placed), name=f'{name}_yard{len(placed)}', ruined=0.1))
    parts['well'] = well((loc[0] + 1.5, loc[1] - 1.0, loc[2]), name=name + '_well')
    parts['oven'] = bread_oven((loc[0] - 4.0, loc[1] + 3.0, loc[2]), heading_deg=rnd.uniform(0, 360), name=name + '_oven')
    a = rnd.uniform(0, 2 * math.pi)
    parts['threshing_floor'] = countryside.threshing_floor((loc[0] + (spread + 10) * math.cos(a), loc[1] + (spread + 10) * math.sin(a), loc[2]),
                                                           seed=seed + 7, name=name + '_halos')
    return parts


def net(loc, size=(3.0, 1.6), heading_deg=0.0, sag=0.35, mesh=0.04, name='net'):
    """A fishing net hung up to dry between two poles: a sagging grid turned into knotted cord by a wireframe."""
    from lib import props
    root = _root(name, loc, heading_deg)
    wood = bpy.data.materials.get('old_wood') or props.old_wood()
    W, H = size
    for sx in (-1, 1):
        props._cyl(f'{name}_pole{sx}', (sx * W / 2, 0, (H + 0.4) / 2), 0.03, H + 0.4, wood, parent=root)
    nx, ny = int(W / mesh), int(H / mesh)
    bm = bmesh.new()
    vs = [[bm.verts.new(Vector(((i / nx - 0.5) * W, 0.04 * math.sin(i * 0.7) * math.sin(j * 0.5),
                                 H + 0.3 - (j / ny) * H - sag * math.sin(math.pi * i / nx) * (1 - 0.5 * j / ny))))
           for i in range(nx + 1)] for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    n = _obj(name + '_mesh', bm, _mat('net_cord', (0.3, 0.24, 0.16), rough=0.9), root, smooth=False)
    wf = n.modifiers.new('cord', 'WIREFRAME'); wf.thickness = 0.003; wf.use_even_offset = True
    return root


def fishing_beach(loc=(0, 0, 0), heading_deg=0.0, boats=3, seed=0, name='fishing_beach'):
    """A fishermen's beach: boats pulled up on the sand bow-first (props.fishing_boat, Session E's kit), nets drying
    on poles, baskets of fish, a rack of split fish drying in the sun. Put fishermen (wardrobe.dress with role
    'fisherman') among them."""
    from lib import props
    rnd = random.Random(seed)
    a = math.radians(heading_deg)
    def at(dx, dy):
        return (loc[0] + dx * math.cos(a) - dy * math.sin(a), loc[1] + dx * math.sin(a) + dy * math.cos(a), loc[2])
    parts = {'boats': [], 'nets': [], 'baskets': []}
    for i in range(boats):
        parts['boats'].append(props.fishing_boat(at((i - (boats - 1) / 2) * 4.2, rnd.uniform(-1, 1)), heading_deg=heading_deg + 90 + rnd.uniform(-12, 12),
                                                 oars='rest', seed=seed + i, name=f'{name}_boat{i}'))
    for i in range(2):
        parts['nets'].append(net(at(-6 + i * 4, 7 + rnd.uniform(-1, 1)), heading_deg=heading_deg + rnd.uniform(-10, 10), name=f'{name}_net{i}'))
    for i in range(4):
        parts['baskets'].append(props.basket(at(rnd.uniform(-6, 6), rnd.uniform(2, 5)), kind='carry', fill=(0.45, 0.48, 0.5),
                                             name=f'{name}_basket{i}'))
    rack = _root(name + '_rack', at(5, 6), heading_deg)                 # drying rack of split fish
    wood = bpy.data.materials.get('old_wood') or props.old_wood()
    from lib import props as P
    for sx in (-1, 1):
        P._box(f'{name}_rack_post{sx}', (sx * 1.0, 0, 0.7), (0.05, 0.05, 1.4), wood, parent=rack)
    P._box(f'{name}_rack_bar', (0, 0, 1.38), (2.1, 0.04, 0.04), wood, parent=rack)
    for k in range(9):
        f = fish(Vector((-0.85 + k * 0.21, 0.02, 1.15)), length=0.32, kind='silver', parent=rack, seed=seed + k, name=f'{name}_dry{k}')
        f.rotation_euler = (0, math.pi / 2, 0)                          # hanging by the tail
    parts['rack'] = rack
    return parts


def caravan(loc=(0, 0, 0), heading_deg=0.0, n=5, spacing=3.4, back_h=1.95, seed=0, name='caravan'):
    """A trade caravan on the road: camels in single file (the main session's CC-BY camel scan,
    library/scans/animal_camels), each loaded with wool bales, grain sacks or amphorae slung on both flanks over a
    saddle cloth, lead ropes from one to the next. Persian royal roads (Herodotus 5.52-54, Sardis to Susa) and
    Arabian/Phoenician trade: camels carried the army's baggage in 480 BC too (Herodotus 7.86-87, the Arabian camel
    corps). back_h = height of the hump/saddle (adjust to the scan's scale)."""
    from lib import scatter, wardrobe
    rnd = random.Random(seed)
    root = _root(name, loc, heading_deg)
    try:
        vs = scatter.load_scan('animal_camels')
    except Exception as e:
        print('caravan: camel scan missing -', e)
        vs = []
    cloth = wardrobe.patterned_cloth(name + '_saddlecloth', 'caban', (0.3, 0.06, 0.04), band=(0.5, 0.34, 0.1),
                                     border='zigzag', border_color=(0.04, 0.03, 0.025), tiles=(3, 3), width=0.12, grime=0.3)
    for i in range(n):
        y = -i * spacing
        if vs:
            inst = bpy.data.objects.new(f'{name}_camel{i}', None); link(inst)
            inst.instance_type = 'COLLECTION'; inst.instance_collection = vs[i % len(vs)]
            inst.location = (rnd.uniform(-0.15, 0.15), y, 0); inst.rotation_euler = (0, 0, rnd.uniform(-0.08, 0.08))
            inst.parent = root
        props_bm = bmesh.new()                                          # saddle cloth over the back
        bmesh.ops.create_cube(props_bm, size=1.0)
        for v in props_bm.verts:
            v.co = Vector((v.co.x * 0.9, v.co.y * 0.75, v.co.z * 0.04))
        sc = _obj(f'{name}_cloth{i}', props_bm, cloth, root, smooth=False)
        sc.location = (0, y + 0.1, back_h)
        kind = rnd.choice(['wool', 'sacks', 'amphorae'])
        for sx in (-1, 1):                                              # a load slung on each flank
            p = Vector((sx * 0.55, y + 0.1, back_h - 0.35))
            if kind == 'wool':
                b = wool_bale(p - Vector((0, 0, 0.2)), size=(0.4, 0.6, 0.45), parent=root, seed=seed + i * 2 + sx, name=f'{name}_bale{i}{sx}')
            elif kind == 'sacks':
                grain_sack(p - Vector((0, 0, 0.3)), h=0.6, parent=root, seed=seed + i * 2 + sx, name=f'{name}_sack{i}{sx}')
            else:
                from lib import props
                a = props.amphora((0, 0, 0), height=0.62, seed=seed + i * 2 + sx, name=f'{name}_amph{i}{sx}')
                a.parent = root; a.location = p - Vector((0, 0, 0.35)); a.rotation_euler = (0, sx * 0.25, 0)
        if i > 0:                                                       # lead rope to the camel in front
            from lib import props
            props._tube(f'{name}_rope{i}', [Vector((0, y + 1.4, 1.75)), Vector((0, y + spacing - 1.2, 1.3)),
                                            Vector((0, y + spacing - 0.6, back_h - 0.1))], 0.008,
                        _mat('cord', (0.35, 0.28, 0.18), rough=0.9), parent=root, poly=True)
    return root


def _scan(name, scan, tint, tiles=1.0):
    """A real scanned surface (world-mapped, no repeats) - plaster, mud brick, stone - or None if missing."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    try:
        from lib import scatter
        return scatter.scan_material(name, scan, tint=tint, tiles=tiles)
    except Exception:
        return None


def roof_tiles(name='terracotta_tiles'):
    """Fired-clay roof tiles: rows of overlapping pan tiles (a wave across, steps down the slope), weathered."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; L = nt.links.new; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(tc.outputs['Object'], sep.inputs[0])
    across = nt.nodes.new('ShaderNodeMath'); across.operation = 'SINE'
    k = nt.nodes.new('ShaderNodeMath'); k.operation = 'MULTIPLY'; k.inputs[1].default_value = 2 * 3.14159 / 0.3   # 30 cm tiles
    L(sep.outputs['X'], k.inputs[0]); L(k.outputs[0], across.inputs[0])
    down = nt.nodes.new('ShaderNodeMath'); down.operation = 'FRACT'
    kd = nt.nodes.new('ShaderNodeMath'); kd.operation = 'MULTIPLY'; kd.inputs[1].default_value = 1 / 0.42        # 42 cm courses
    L(sep.outputs['Y'], kd.inputs[0]); L(kd.outputs[0], down.inputs[0])
    h = nt.nodes.new('ShaderNodeMath'); h.operation = 'ADD'; L(across.outputs[0], h.inputs[0]); L(down.outputs[0], h.inputs[1])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.8; bp.inputs['Distance'].default_value = 0.04
    L(h.outputs[0], bp.inputs['Height']); L(bp.outputs['Normal'], b.inputs['Normal'])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; L(tc.outputs['Object'], nz.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.2, 0.07, 0.035, 1); ramp.color_ramp.elements[1].color = (0.42, 0.18, 0.09, 1)
    L(nz.outputs['Fac'], ramp.inputs['Fac']); L(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.85
    return m


def workshop_shed(loc=(0, 0, 0), heading_deg=0.0, w=7.0, d=4.0, h=3.0, parent=None, name='shed'):
    """A lean-to workshop shed: a plastered mud-brick back wall on a stone socle, two side walls, timber posts at
    the open front, a single-pitch tiled roof sloping to the front (workshops along the Kerameikos streets)."""
    from lib import props, countryside
    root = _root(name, loc, heading_deg)
    if parent:
        root.parent = parent
    plaster = _scan('mudbrick_plaster', 'clay_plaster', (1.0, 0.86, 0.68), 1.2) or _mat('mud_plaster', (0.45, 0.35, 0.25), rough=0.9)
    stone = countryside.stone_material()
    wood = bpy.data.materials.get('old_wood') or props.old_wood()
    props._box(name + '_socle', (0, d / 2, 0.3), (w, 0.55, 0.6), stone, parent=root)
    props._box(name + '_back', (0, d / 2, 0.6 + (h - 0.6) / 2), (w, 0.45, h - 0.6), plaster, parent=root)
    for sx in (-1, 1):
        props._box(f'{name}_side{sx}', (sx * w / 2, d / 4, h / 2), (0.4, d / 2, h), plaster, parent=root)
        props._box(f'{name}_post{sx}', (sx * (w / 2 - 0.2), -d / 2, (h - 0.5) / 2), (0.16, 0.16, h - 0.5), wood, parent=root)
    props._box(name + '_lintel', (0, -d / 2, h - 0.5), (w, 0.2, 0.2), wood, parent=root)
    bm = bmesh.new()                                                   # single-pitch roof, front lower
    v = [bm.verts.new(Vector(p)) for p in ((-w / 2 - 0.3, -d / 2 - 0.6, h - 0.45), (w / 2 + 0.3, -d / 2 - 0.6, h - 0.45),
                                           (w / 2 + 0.3, d / 2 + 0.3, h + 0.25), (-w / 2 - 0.3, d / 2 + 0.3, h + 0.25))]
    bm.faces.new(v)
    roof = _obj(name + '_roof', bm, roof_tiles(), root, smooth=False)
    roof.modifiers.new('thick', 'SOLIDIFY').thickness = 0.08
    return root


def stoa(loc=(0, 0, 0), heading_deg=0.0, columns=12, spacing=3.2, depth=7.0, height=5.5, name='stoa'):
    """A STOA: the long colonnaded hall that framed a Greek agora - a row of Doric columns (architecture.column)
    in front, a plastered back wall, a tiled single-pitch roof (the Royal Stoa / Stoa Basileios in the Athenian
    agora, c. 500 BC; the Painted Stoa, c. 460 BC). Shopkeepers, officials and talkers gathered in its shade."""
    from lib import architecture, props
    root = _root(name, loc, heading_deg)
    marble = architecture.stone()
    L = (columns - 1) * spacing
    props._box(name + '_steps', (0, 0, 0.18), (L + 2.4, depth + 1.6, 0.36), marble, parent=root)
    plaster = _scan('stoa_plaster', 'plastered_wall_02', (1.0, 0.95, 0.88), 1.5) or marble
    props._box(name + '_back', (0, depth / 2, 0.36 + height / 2), (L + 1.2, 0.6, height), plaster, parent=root)
    for sx in (-1, 1):
        props._box(f'{name}_end{sx}', (sx * (L / 2 + 0.6), 0.5, 0.36 + height / 2), (0.6, depth - 0.4, height), plaster, parent=root)
    for i in range(columns):
        c = architecture.column((0, 0, 0), D=0.75, H=height - 0.7, name=f'{name}_col{i}')
        c.parent = root; c.location = (-L / 2 + i * spacing, -depth / 2 + 0.6, 0.36)
    props._box(name + '_entablature', (0, -depth / 2 + 0.6, 0.36 + height - 0.35), (L + 1.4, 1.0, 0.7), marble, parent=root)
    bm = bmesh.new()
    v = [bm.verts.new(Vector(p)) for p in ((-L / 2 - 0.9, -depth / 2 - 0.2, height + 0.36), (L / 2 + 0.9, -depth / 2 - 0.2, height + 0.36),
                                           (L / 2 + 0.9, depth / 2 + 0.4, height + 1.6), (-L / 2 - 0.9, depth / 2 + 0.4, height + 1.6))]
    bm.faces.new(v)
    roof = _obj(name + '_roof', bm, roof_tiles(), root, smooth=False); roof.modifiers.new('thick', 'SOLIDIFY').thickness = 0.12
    return root


# ------------------------------------------------------------------ workshops (Kerameikos potters, smiths)
def potter_workshop(loc=(0, 0, 0), heading_deg=0.0, seed=0, name='potters'):
    """A potter's yard in the Kerameikos (Athens' potters' quarter; red-figure at its height c. 480 BC). After vase
    scenes of potters at work (the Caputi hydria, c. 470 BC; Corinthian pinakes of kilns): a low wheel turned by an
    apprentice, a pot rising on it, a domed UPDRAUGHT kiln with its stoking mouth, a heap of wet clay, shelves of
    pots drying before the firing."""
    from lib import props, countryside
    rnd = random.Random(seed)
    root = _root(name, loc, heading_deg)
    clay = _mat('wet_clay', (0.36, 0.2, 0.11), rough=0.45, bump=0.3, bump_scale=60)
    dry = props.terracotta(name + '_fired', seed=seed)
    wood = bpy.data.materials.get('old_wood') or props.old_wood()
    # the wheel: a heavy wooden disc on a low pivot, a pot being thrown on it
    props._cyl(name + '_wheel', (0, 0, 0.3), 0.42, 0.06, wood, parent=root)
    props._cyl(name + '_pivot', (0, 0, 0.14), 0.06, 0.28, wood, parent=root)
    bm = bmesh.new()
    _lathe(bm, [(0.001, 0.0), (0.09, 0.0), (0.12, 0.08), (0.13, 0.18), (0.09, 0.26), (0.07, 0.3), (0.08, 0.32), (0.06, 0.32)], seg=28)
    p = _obj(name + '_thrown', bm, clay, root); p.location = (0, 0, 0.33)
    # the kiln: a domed chamber over a firebox, the stoking channel in front
    bm = bmesh.new()
    _lathe(bm, [(1.0, 0.0), (1.0, 0.9), (0.9, 1.4), (0.6, 1.85), (0.25, 2.05), (0.18, 2.1)], seg=36)
    kiln_mat = _scan('kiln_clay_scan', 'clay_plaster', (0.95, 0.72, 0.55), 0.7) or _mat('kiln_clay', (0.42, 0.29, 0.19), rough=0.9)
    for v in bm.verts:                                                  # hand-built: lumpy, not a perfect dome
        v.co.x *= 1 + 0.03 * math.sin(v.co.z * 9 + v.co.y * 4); v.co.y *= 1 + 0.03 * math.cos(v.co.z * 7 + v.co.x * 5)
    k = _obj(name + '_kiln', bm, kiln_mat, root)
    k.location = (3.2, 1.5, 0)
    # the stoking mouth: an ARCHED opening set into the kiln's base, sooty inside, glowing a little
    bm = bmesh.new()
    arch = [(-0.3, 0.0), (0.3, 0.0)] + [(0.3 * math.cos(a), 0.45 + 0.3 * math.sin(a)) for a in np.linspace(0, math.pi, 9)]
    vs = [bm.verts.new(Vector((x, 0.0, z))) for x, z in arch]      # bottom edge, then the arch over the top
    bm.faces.new(vs)
    mouth = _obj(name + '_mouth', bm, _mat('soot_glow', (0.02, 0.008, 0.004), rough=0.9), root, smooth=False)
    mouth.location = (3.2, 1.5 - 1.005, 0.02)
    workshop_shed((0.2, 2.4, 0), w=7.5, d=4.0, h=3.0, parent=root, name=name + '_shed')
    # clay heap
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * 0.7, v.co.y * 0.6, max(0.0, v.co.z) * 0.35))
    _obj(name + '_clayheap', bm, clay, root).location = (-1.6, 1.2, 0)
    # drying shelves with pots (unfired: pale; some fired: orange)
    for s in range(2):
        props._box(f'{name}_shelf{s}', (-2.5, -1.2 + s * 0.0, 0.5 + s * 0.6), (2.2, 0.4, 0.04), wood, parent=root)
        for j in range(5):
            a = props.amphora((0, 0, 0), height=rnd.uniform(0.22, 0.35), seed=seed + s * 10 + j, name=f'{name}_pot{s}{j}')
            a.parent = root; a.location = (-3.4 + j * 0.45, -1.2, 0.52 + s * 0.6)
            if s == 0:
                a.data.materials.clear(); a.data.materials.append(_mat('greenware', (0.55, 0.42, 0.3), rough=0.8))
    for sx in (-1, 1):
        for sh in (0, 1):
            props._box(f'{name}_shelfleg{sx}{sh}', (-2.5 + sx * 1.05, -1.2, 0.55), (0.05, 0.05, 1.1), wood, parent=root)
    return root


def smithy(loc=(0, 0, 0), heading_deg=0.0, lit=True, seed=0, name='smithy'):
    """A smith's workshop (Hephaistos' trade on vases: the Foundry Painter's cup, c. 490-480 BC): a raised forge hearth
    with glowing charcoal, a pair of skin bellows, a stone-and-wood anvil block, a water tub for quenching, tongs and
    blades on a rack. lit=True: the coals glow and light the scene (props.ember_glow)."""
    from lib import props, tools
    root = _root(name, loc, heading_deg)
    from lib import countryside
    stone = countryside.stone_material()
    props._box(name + '_hearth', (0, 0, 0.4), (1.2, 0.9, 0.8), stone, parent=root)
    workshop_shed((0.3, 1.6, 0), w=5.0, d=3.6, h=2.9, parent=root, name=name + '_shed')
    coals = props.ember_glow(name + '_coals', strength=8.0) if lit else _mat('charcoal', (0.02, 0.02, 0.02), rough=0.9)
    bm = bmesh.new()
    rnd = random.Random(seed)
    for i in range(70):
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rnd.uniform(0.02, 0.04),
                                   matrix=Matrix.Translation(Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.2, 0.2), 0.82 + rnd.uniform(0, 0.06)))))
    _obj(name + '_coals', bm, coals, root, smooth=False)
    if lit:
        bpy.ops.object.light_add(type='POINT', location=(0, 0, 1.1)); l = bpy.context.object
        l.data.energy = 220; l.data.color = (1.0, 0.5, 0.2); l.data.shadow_soft_size = 0.2; l.parent = root
    leather = props.leather()
    for sx in (-1, 1):                                                  # skin bellows behind the hearth
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        for v in bm.verts:
            v.co = Vector((v.co.x * 0.18, v.co.y * 0.3, v.co.z * 0.12))
        b = _obj(f'{name}_bellows{sx}', bm, leather, root); b.location = (sx * 0.22, 0.75, 0.55)
    anv = props._box(name + '_anvil_block', (1.3, -0.3, 0.3), (0.45, 0.45, 0.6), _mat('log', (0.2, 0.13, 0.07), rough=0.8, bump=0.6, bump_scale=40), parent=root)
    props._box(name + '_anvil', (1.3, -0.3, 0.66), (0.22, 0.14, 0.12), tools.iron_mat(), parent=root)
    bm = bmesh.new()
    _lathe(bm, [(0.001, 0.0), (0.32, 0.0), (0.35, 0.45), (0.32, 0.45), (0.29, 0.03)], seg=28)
    _obj(name + '_tub', bm, _mat('tub_wood', (0.22, 0.14, 0.07), rough=0.7), root).location = (-1.2, -0.4, 0)
    props._cyl(name + '_water', (-1.2, -0.4, 0.38), 0.3, 0.01, _mat('dark_water', (0.02, 0.03, 0.03), rough=0.05), parent=root)
    rack = props._box(name + '_rack', (0, 1.4, 1.2), (1.6, 0.06, 0.06), bpy.data.materials.get('old_wood') or props.old_wood(), parent=root)
    for i, maker in enumerate((tools.sickle, tools.pruning_hook, tools.sickle)):
        t = maker(f'{name}_tool{i}'); t.parent = root; t.location = (-0.5 + i * 0.5, 1.37, 1.0)
    return root


# ------------------------------------------------------------------ women's work: loom, water, wool
def hydria(loc=(0, 0, 0), height=0.45, parent=None, seed=0, name='hydria'):
    """The HYDRIA, the water jar: broad shoulder, narrow neck, two horizontal handles for lifting and one vertical
    handle for pouring (the jar women carry on their heads at the fountain)."""
    from lib import props, tools
    k = height / 0.45
    bm = bmesh.new()
    prof = [(0.001, 0.0), (0.08, 0.0), (0.09, 0.02), (0.13, 0.12), (0.17, 0.24), (0.16, 0.3), (0.1, 0.35),
            (0.05, 0.37), (0.045, 0.42), (0.065, 0.45), (0.05, 0.45)]
    _lathe(bm, [(r * k, z * k) for r, z in prof], seg=32)
    clay = props.terracotta(name + '_clay', seed=seed)
    o = _obj(name, bm, clay, parent); o.location = loc
    for sx in (-1, 1):                                                  # horizontal lifting handles
        pts = [Vector((sx * (0.16 + 0.03 * math.sin(a)) * k, 0.04 * math.cos(a) * k, 0.24 * k)) for a in np.linspace(0, math.pi, 7)]
        tools._tube(f'{name}_handle{sx}', pts, 0.008 * k, clay, o)
    pts = [Vector((0, (0.05 + 0.1 * math.sin(a)) * k, (0.42 - 0.12 * a / math.pi) * k)) for a in np.linspace(0, math.pi, 8)]
    tools._tube(name + '_pour', pts, 0.009 * k, clay, o)
    return o


def loom(loc=(0, 0, 0), heading_deg=0.0, cloth_color=(0.45, 0.3, 0.1), border='meander', seed=0, name='loom'):
    """The WARP-WEIGHTED LOOM of every Greek house (Penelope's loom; the Amasis Painter's lekythos of women weaving,
    c. 550 BC): two uprights leaning against the wall, a top beam, the woven part hanging from it, then the bare
    WARP threads running down to rows of clay LOOM WEIGHTS that keep them taut; a shed rod across. The woven cloth
    carries a pattern border (wardrobe.patterned_cloth)."""
    from lib import props, tools, wardrobe
    rnd = random.Random(seed)
    root = _root(name, loc, heading_deg)
    W, H, lean = 1.5, 2.0, 0.25
    wood = bpy.data.materials.get('old_wood') or props.old_wood()
    for sx in (-1, 1):
        tools._tube(f'{name}_upright{sx}', [Vector((sx * W / 2, 0, 0)), Vector((sx * W / 2, lean, H))], 0.03, wood, root)
    tools._tube(name + '_beam', [Vector((-W / 2 - 0.1, lean, H - 0.08)), Vector((W / 2 + 0.1, lean, H - 0.08))], 0.045, wood, root)
    tools._tube(name + '_shed', [Vector((-W / 2, lean * 0.45, H * 0.45)), Vector((W / 2, lean * 0.45, H * 0.45))], 0.015, wood, root)
    cm = wardrobe.patterned_cloth(name + '_web', 'rough_linen', cloth_color, band=(0.04, 0.03, 0.025), border=border,
                                  border_color=(0.52, 0.47, 0.37), border_repeat=10, width=0.12, tiles=(4, 4), grime=0.05)
    bm = bmesh.new()
    nx, ny = 20, 10
    top_z, bot_z = H - 0.12, H * 0.55
    vs = [[bm.verts.new(Vector(((i / (nx - 1) - 0.5) * (W - 0.1), lean * (top_z - (top_z - bot_z) * j / (ny - 1)) / H,
                                 top_z - (top_z - bot_z) * j / (ny - 1)))) for i in range(nx)] for j in range(ny)]
    for j in range(ny - 1):
        for i in range(nx - 1):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    web = _obj(name + '_web', bm, cm, root, smooth=False)
    uv = web.data.uv_layers.new(name='UVMap')
    for poly in web.data.polygons:
        for li in poly.loop_indices:
            co = web.data.vertices[web.data.loops[li].vertex_index].co
            uv.data[li].uv = (co.x / (W - 0.1) + 0.5, 1 - (top_z - co.z) / (top_z - bot_z))
    thread = _mat('warp_thread', (0.52, 0.47, 0.37), rough=0.9)
    clay = props.terracotta(name + '_weights', seed=seed)
    wb = bmesh.new()
    nb = 22
    for i in range(nb):
        x = (i / (nb - 1) - 0.5) * (W - 0.15)
        for row, dy in ((0, 0.0), (1, 0.07)):                           # front and back warp
            zt = bot_z; zw = 0.35 + 0.05 * rnd.random() + row * 0.08
            yt = lean * zt / H + dy * 0.3; yw = lean * zw / H + dy
            tools._tube(f'{name}_warp{i}{row}', [Vector((x, yt, zt)), Vector((x, yw, zw + 0.06))], 0.004, thread, root)
            bmesh.ops.create_cone(wb, cap_ends=True, segments=4, radius1=0.035, radius2=0.015, depth=0.09,
                                  matrix=Matrix.Translation(Vector((x, yw, zw))))   # pyramidal clay weight
    _obj(name + '_loomweights', wb, clay, root, smooth=False)
    return root


def spindle(name='spindle'):
    """Drop spindle with a clay whorl and spun yarn (women spinning on vases, the wool basket at their feet)."""
    from lib import tools, props
    r = _root(name, (0, 0, 0))
    tools._tube(name + '_shaft', [Vector((0, 0, -0.32)), Vector((0, 0, 0.0))], 0.004, tools.wood_mat(), r)
    props._cyl(name + '_whorl', (0, 0, -0.27), 0.022, 0.012, props.terracotta(), parent=r)
    tools._tube(name + '_yarn', [Vector((0, 0, -0.1)), Vector((0, 0, -0.2))], 0.009, _mat('spun_wool', (0.62, 0.57, 0.47), rough=0.95), r)
    return r


def fountain_house(loc=(0, 0, 0), heading_deg=0.0, spouts=3, seed=0, name='fountain'):
    """A public fountain house (krene), as painted on Athenian hydriai c. 520-480 BC (women filling jars under lion-
    head spouts): a Doric porch (architecture.column), a back wall with LION-HEAD SPOUTS pouring water into a long
    basin, hydriai waiting on the step. The water streams are glassy and fall in thin arcs."""
    from lib import architecture, props, tools
    rnd = random.Random(seed)
    root = _root(name, loc, heading_deg)
    marble = architecture.stone()
    W, D, H = 6.0, 3.2, 3.6
    props._box(name + '_step', (0, 0, 0.1), (W + 0.6, D + 0.6, 0.2), marble, parent=root)
    props._box(name + '_backwall', (0, D / 2, H / 2 + 0.2), (W, 0.4, H), marble, parent=root)
    props._box(name + '_roof', (0, 0, H + 0.45), (W + 0.4, D + 0.6, 0.4), marble, parent=root)
    for i in range(4):                                                  # porch columns
        x = (i / 3 - 0.5) * (W - 0.6)
        c = architecture.column((0, 0, 0), D=0.42, H=H - 0.05, name=f'{name}_col{i}')
        c.parent = root; c.location = (x, -D / 2 + 0.3, 0.2)
    props._box(name + '_basin', (0, D / 2 - 0.55, 0.55), (W - 0.6, 0.7, 0.7), marble, parent=root)
    water = bpy.data.materials.get('fountain_water')
    if water is None:
        water = bpy.data.materials.new('fountain_water'); water.use_fake_user = True
        b = water.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (0.8, 0.9, 0.95, 1); b.inputs['Roughness'].default_value = 0.02
        b.inputs['Transmission Weight'].default_value = 1.0; b.inputs['IOR'].default_value = 1.33
    props._box(name + '_pool', (0, D / 2 - 0.55, 0.86), (W - 0.7, 0.6, 0.02), water, parent=root)
    bronze = _mat('spout_bronze', (0.4, 0.3, 0.14), metal=1.0, rough=0.35)
    for i in range(spouts):
        x = (i - (spouts - 1) / 2) * 1.5
        bm = bmesh.new()                                                # a lion's head: maned disc + muzzle
        _lathe(bm, [(0.001, 0.0), (0.16, 0.0), (0.18, 0.03), (0.12, 0.08), (0.07, 0.14), (0.04, 0.16)], seg=20,
               matrix=Matrix.Rotation(-math.pi / 2, 4, 'X'))
        lion = _obj(f'{name}_lion{i}', bm, bronze, root); lion.location = (x, D / 2 - 0.2, 1.55)
        pts = [Vector((x, D / 2 - 0.36 - 0.25 * t, 1.55 - 0.68 * t * t)) for t in np.linspace(0, 1, 8)]   # water arc
        tools._tube(f'{name}_stream{i}', pts, 0.018, water, root, r_end=0.012)
    for i in range(3):
        hydria((rnd.uniform(-2.2, 2.2), -D / 2 + 0.1, 0.2), height=0.45, parent=root, seed=seed + i, name=f'{name}_hydria{i}')
    return root

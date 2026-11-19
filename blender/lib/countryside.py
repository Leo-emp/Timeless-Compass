# COUNTRYSIDE (WS16): the farmed Greek landscape of c. 480 BC between the mountains and the sea, built by code.
#   grain fields   emmer wheat / hulled barley, ripe (gold) or green, cut stubble, ploughed furrows, fallow
#   olive groves   real scanned olive trees (WS6's CC0 scan) planted in wide rows, as in Attica
#   dry-stone walls field boundaries and hillside TERRACE walls of unmortared fieldstones
#   threshing floor the round paved 'halos' where oxen trod out the grain (Xenophon, Oeconomicus 18)
#   beehives       horizontal terracotta hive tubes on stands (found at Classical Attic farms, e.g. the Vari house)
#   farmstead      composes them round architecture.courtyard_house (the main session's house kit)
# Design sources: Hesiod, Works and Days (ploughing, sowing, harvest, threshing); Xenophon, Oeconomicus 16-19
# (fallow, ploughing, harvest, threshing, vines and olives); Attic vase scenes of ploughing (Nikosthenes cup) and
# olive harvesting (Antimenes Painter amphora, c. 520 BC); excavated Attic farmsteads (Dema house c. 420 BC, Vari
# house); Attic field walls and terraces. Never copied from other productions (rule r9).
# WIND: standing crops (and vineyards) move - gust waves roll across the field with the scene clock (wind_scatter).
#
# How the big fields stay cheap: a grain field is ONE ground mesh plus a geometry-node setup that places INSTANCES of a
# few small code-built "clumps" (a dozen stalks each). Thousands of instances share the clump mesh, so a 40 x 30 m
# field of ~1.5 million stalks costs about as much memory as a few hundred.
import math
import random

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

from lib.common import link, principled, SCANS


# ------------------------------------------------------------------ materials
def _plant_material(name, ripe=1.0, seed=0):
    """Grain stalks / leaves / ears. ripe 0 = fresh spring green, 1 = harvest gold (late May / June in Attica).
    Every instance gets its own shade (Object Info > Random), and light shines THROUGH the thin leaves
    (translucency), which is what makes a field glow against a low sun."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; L = nt.links.new
    b = nt.nodes['Principled BSDF']
    green, gold = np.array((0.11, 0.2, 0.04)), np.array((0.62, 0.46, 0.17))
    base = green * (1 - ripe) + gold * ripe
    info = nt.nodes.new('ShaderNodeObjectInfo')
    ramp = nt.nodes.new('ShaderNodeValToRGB')                         # shade variety between plants
    ramp.color_ramp.elements[0].color = (*(base * 0.7), 1)
    ramp.color_ramp.elements[1].color = (*np.minimum(base * 1.25, 1), 1)
    L(info.outputs['Random'], ramp.inputs['Fac'])
    # a little greener toward the base of the stalk even when ripe (the lower leaves dry last)
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); tc = nt.nodes.new('ShaderNodeTexCoord')
    L(tc.outputs['Object'], sep.inputs[0])
    low = nt.nodes.new('ShaderNodeMapRange'); low.inputs['From Min'].default_value = 0.0; low.inputs['From Max'].default_value = 0.45
    low.inputs['To Min'].default_value = 0.6 * ripe; low.inputs['To Max'].default_value = 0.0
    L(sep.outputs['Z'], low.inputs['Value'])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    mx.inputs['B'].default_value = (*(green * 0.9 + gold * 0.1), 1)
    L(low.outputs['Result'], mx.inputs['Factor']); L(ramp.outputs['Color'], mx.inputs['A'])
    L(mx.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.55
    b.inputs['Specular IOR Level'].default_value = 0.35
    if 'Subsurface Weight' in b.inputs:                              # light through thin leaves
        b.inputs['Subsurface Weight'].default_value = 0.0
    if 'Transmission Weight' in b.inputs:
        b.inputs['Transmission Weight'].default_value = 0.0
    # translucent glow: mix with a Translucent BSDF of the same colour
    tr = nt.nodes.new('ShaderNodeBsdfTranslucent'); L(mx.outputs['Result'], tr.inputs['Color'])
    ms = nt.nodes.new('ShaderNodeMixShader'); ms.inputs['Fac'].default_value = 0.3
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    L(b.outputs[0], ms.inputs[1]); L(tr.outputs[0], ms.inputs[2]); L(ms.outputs[0], out.inputs['Surface'])
    return m


def soil_material(name='field_soil', scan='brown_mud_dry', tint=(1.0, 0.95, 0.88), tiles=1.2):
    """Dry ploughed Attic soil from a real scan (world-mapped, no visible repeats: scatter.scan_material)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    from lib import scatter
    return scatter.scan_material(name, scan, tint=tint, tiles=tiles)


def stone_material(name='fieldstone', scan='rock_wall_08', tint=(1.0, 0.97, 0.92), tiles=1.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    from lib import scatter
    return scatter.scan_material(name, scan, tint=tint, tiles=tiles)


# ------------------------------------------------------------------ grain clumps (the instanced plants)
def _ribbon(bm, pts, width, twist=0.0):
    """A thin flat ribbon (leaf / stalk) along points, narrowing to the tip. Returns nothing (adds to bm)."""
    prev = None
    n = len(pts)
    for i, p in enumerate(pts):
        t = i / (n - 1)
        d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]); d.normalize()
        side = d.cross(Vector((math.cos(twist + t), math.sin(twist + t), 0))).normalized()
        w = width * (1 - 0.85 * t)
        a = bm.verts.new(p + side * w / 2); b = bm.verts.new(p - side * w / 2)
        if prev:
            bm.faces.new((prev[0], prev[1], b, a))
        prev = (a, b)


def grain_clump(name='grain_clump', crop='wheat', height=0.95, stalks=12, ripe=1.0, seed=0, cut=False, hair_axis=True):
    """One clump of grain plants (one seed's tillers): `stalks` stems around a small circle, each with 2 long
    leaves and, unless `cut`, an EAR on top. crop 'wheat' (emmer: plump ear, short awns) or 'barley' (slender
    ear with long awns that catch the light). cut=True = harvest stubble (short stems, no ears, no leaves).
    Origin at the ground; Z up. Kept low-poly: the field shows thousands of these."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    for s in range(stalks):
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0.0, 0.05)
        base = Vector((r * math.cos(a), r * math.sin(a), 0))
        h = (0.12 + rnd.uniform(-0.03, 0.03)) if cut else height * rnd.uniform(0.8, 1.08)
        lean = Vector((math.cos(a), math.sin(a), 0)) * rnd.uniform(0.02, 0.12) * h
        bend = rnd.uniform(0.0, 0.08) * h                              # heavy ears nod over
        pts = [base + lean * (t ** 1.5) + Vector((0, 0, h * t)) + Vector((bend * t ** 3, 0, -bend * t ** 4))
               for t in np.linspace(0, 1, 7)]
        _ribbon(bm, pts, 0.004, twist=a)
        if cut:
            continue
        for lf in range(2):                                            # two leaves curving out from the stem
            t0 = rnd.uniform(0.15, 0.5); la = a + rnd.uniform(-1.5, 1.5)
            p0 = pts[0].lerp(pts[-1], t0)
            out = Vector((math.cos(la), math.sin(la), 0))
            lp = [p0 + out * (0.22 * h * u) + Vector((0, 0, 0.2 * h * u - 0.18 * h * u * u * (1.4 if ripe > 0.6 else 0.8)))
                  for u in np.linspace(0, 1, 6)]
            _ribbon(bm, lp, 0.011, twist=la)
        # the ear: stacked spikelets = a narrow spindle of alternating small flat scales
        top = pts[-1]; d = (pts[-1] - pts[-2]).normalized()
        ear_len = 0.075 if crop == 'wheat' else 0.065
        nsp = 9
        for k in range(nsp):
            t = k / (nsp - 1)
            c = top + d * (ear_len * t)
            w = (0.011 if crop == 'wheat' else 0.007) * math.sin(math.pi * (0.15 + 0.85 * t)) + 0.002
            ang = a + (k % 2) * math.pi
            side = Vector((math.cos(ang), math.sin(ang), 0))
            q = [bm.verts.new(c + side * 0.002), bm.verts.new(c + side * w + d * 0.008),
                 bm.verts.new(c + d * 0.014), bm.verts.new(c - side * 0.0 + d * 0.004 + side.cross(d) * w * 0.6)]
            bm.faces.new(q)
            awn = 0.02 if crop == 'wheat' else 0.07                     # barley's long awns
            tip = c + side * w * 0.5 + (d * 1.0 + side * 0.25).normalized() * awn
            v0, v1, v2 = bm.verts.new(c + side * w * 0.4), bm.verts.new(c + side * w * 0.6), bm.verts.new(tip)
            bm.faces.new((v0, v1, v2))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if hair_axis:
        _to_hair_axis(me)
    o = bpy.data.objects.new(name, me)
    o.data.materials.append(_plant_material(f'grain_{crop}_{int(ripe * 10)}', ripe))
    return o


def _hidden_collection(name):
    """A collection that is NOT linked into the scene: its objects never render themselves, only as instances
    (particle systems and collection instances can use collections that live outside the scene)."""
    return bpy.data.collections.get(name) or bpy.data.collections.new(name)


def _to_hair_axis(me):
    """Particle-hair instancing stands an object along its +X axis (X follows the ground normal). Our plants
    are built Z-up, so turn the mesh: +Z -> +X (a 90 degree turn about Y). Flat-lying straw built in XY then
    lies flat on the ground the same way."""
    for v in me.vertices:
        v.co = (v.co.z, v.co.y, -v.co.x)
    me.update()


# ------------------------------------------------------------------ ground
def field_ground(name, size=(40.0, 30.0), loc=(0, 0, 0), heading_deg=0.0, furrow=0.32, depth=0.06, step=0.08,
                 slope=(0.0, 0.0), seed=0, material=None):
    """A field's soil: a grid with PLOUGH FURROWS (ridges every `furrow` m along the field's length, the way an
    ard scratches the ground - shallow, uneven, not a modern tractor's perfect lines), clods, and an optional
    tilt `slope` = (dz/dx, dz/dy). heading_deg turns the furrow direction."""
    rnd = np.random.default_rng(seed)
    nx, ny = int(size[0] / step) + 1, int(size[1] / step) + 1
    xs = np.linspace(-size[0] / 2, size[0] / 2, nx); ys = np.linspace(-size[1] / 2, size[1] / 2, ny)
    X, Y = np.meshgrid(xs, ys)
    wobble = 0.08 * np.sin(Y * 0.35 + seed) + 0.05 * np.sin(Y * 1.3 + 2 * seed)        # furrows wander a little
    Z = depth * 0.5 * np.cos(2 * np.pi * (X + wobble) / furrow) ** 2
    Z += rnd.normal(0, depth * 0.18, Z.shape)                                       # clods
    Z += slope[0] * X + slope[1] * Y
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(ny - 1) for i in range(nx - 1)]
    me = bpy.data.meshes.new(name); me.from_pydata(verts.tolist(), [], faces); me.update()
    o = link(bpy.data.objects.new(name, me))
    o.location = loc; o.rotation_euler = (0, 0, math.radians(heading_deg))
    uv = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            uv.data[li].uv = ((verts[vi, 0] + size[0] / 2) / size[0], (verts[vi, 1] + size[1] / 2) / size[1])
    for p in me.polygons:
        p.use_smooth = True
    o.data.materials.append(material or soil_material())
    return o


def grain_field(name='field', size=(40.0, 30.0), loc=(0, 0, 0), heading_deg=0.0, crop='wheat', state='ripe',
                density=26.0, height=0.95, seed=0, slope=(0.0, 0.0), edge_thin=1.5, max_count=60000,
                wind_deg=30.0, gust=None):
    """A whole field. state: 'ripe' (gold, standing), 'green' (spring), 'stubble' (after the sickle, with loose
    straw), 'ploughed' (bare furrows, autumn/sowing time), 'fallow' (resting year: weeds and dry grass tufts).
    density = clumps per m2 (each clump ~12 stalks). The edges thin out (`edge_thin` m) the way a hand-sown field
    does. The standing crop MOVES IN THE WIND (wind_scatter: gust waves rolling across + flutter; wind_deg = the
    direction the wind blows to, gust = bend in radians, None = by crop: ripe heavy ears bend most).
    Returns the ground object (the plants are geometry-node instances on it)."""
    ground = field_ground(name, size, loc, heading_deg, seed=seed, slope=slope)
    if state == 'ploughed':
        return ground
    ripe = {'ripe': 1.0, 'green': 0.0, 'stubble': 0.9, 'fallow': 0.75}[state]
    col = _hidden_collection(f'{name}_clumps')
    variants = []
    for v in range(4):                                                 # a few different clumps: no repeats visible
        if state == 'fallow':
            c = grain_clump(f'{name}_tuft{v}', 'barley', height=0.35, stalks=8, ripe=ripe, seed=seed * 10 + v,
                            hair_axis=False)
        else:
            c = grain_clump(f'{name}_clump{v}', crop, height=height, stalks=12, ripe=ripe, seed=seed * 10 + v,
                            cut=(state == 'stubble'), hair_axis=False)
        col.objects.link(c); variants.append(c)
    # density map: thinner near the edges (vertex group drives the particle density)
    vg = ground.vertex_groups.new(name='density')
    hx, hy = size[0] / 2, size[1] / 2
    for vtx in ground.data.vertices:
        e = min(hx - abs(vtx.co.x), hy - abs(vtx.co.y))
        w = min(1.0, max(0.0, e / edge_thin)) ** 0.7
        if state == 'fallow':                                           # weeds grow in patches
            w *= 0.4 + 0.6 * (0.5 + 0.5 * math.sin(vtx.co.x * 0.7 + seed) * math.sin(vtx.co.y * 0.9))
        vg.add([vtx.index], w, 'REPLACE')
    area = size[0] * size[1]
    dens = min(max_count / area, density * (0.35 if state == 'fallow' else 1.0))
    if gust is None:                                                    # how much each crop bends in a gust
        gust = {'ripe': 0.34, 'green': 0.26, 'stubble': 0.0, 'fallow': 0.2}[state]
    local_wind = wind_deg - heading_deg                                 # wind in the field's own frame
    wind_scatter(ground, col, dens, seed=seed, wind_deg=local_wind, gust=gust,
                 flutter=0.0 if state == 'stubble' else 0.06, name=f'{name}_wind')
    if state == 'stubble':                                              # loose straw left lying after the harvest
        scol = _hidden_collection(f'{name}_straw')
        scol.objects.link(_straw_scatter(f'{name}_strawbits', 0.95, seed, hair_axis=False))
        wind_scatter(ground, scol, 6.0, seed=seed + 5, gust=0.0, flutter=0.0, scale=(0.6, 1.3), name=f'{name}_straw')
    return ground


def _straw_scatter(name, ripe, seed, hair_axis=True):
    """A few loose straws lying flat (dropped behind the reapers)."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    for _ in range(6):
        a = rnd.uniform(0, 2 * math.pi); ln = rnd.uniform(0.2, 0.5)
        d = Vector((math.cos(a), math.sin(a), 0)); c = Vector((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), 0.005))
        _ribbon(bm, [c + d * ln * t + Vector((0, 0, 0.01 * math.sin(math.pi * t))) for t in np.linspace(0, 1, 5)], 0.004, a)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if hair_axis:                                                       # for particle hair (threshing floor)
        _to_hair_axis(me)
    o = bpy.data.objects.new(name, me); o.data.materials.append(_plant_material(f'straw_{seed}', 0.95))
    return o


# ------------------------------------------------------------------ olive groves
def olive_grove(ground, area, spacing=9.0, jitter=1.6, seed=0, size=(0.75, 1.15), skip=0.08, name='olive_grove'):
    """Olive trees planted in wide, slightly irregular rows (Attic groves were spaced widely, grain or vines grew
    between them). Uses the CC0 scanned olive tree (library/scans/tree_olive_zakynthos, via scatter.load_scan),
    placed ON `ground` by ray cast. area = (xmin, xmax, ymin, ymax). Some gaps (`skip`) where old trees died."""
    from lib import scatter
    try:
        vs = scatter.load_scan('tree_olive_zakynthos')
    except Exception as e:                                             # e.g. a cloud runner without Sketchfab scans
        print('olive_grove: olive scan not available here -', e)
        return None
    rnd = random.Random(seed)
    dg = bpy.context.evaluated_depsgraph_get()
    from mathutils.bvhtree import BVHTree
    tree = BVHTree.FromObject(ground, dg)
    mw = ground.matrix_world; inv = mw.inverted()
    out = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if out.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(out)
    x0, x1, y0, y1 = area
    n = 0; pts = []
    y = y0 + spacing / 2
    row = 0
    while y < y1:
        x = x0 + spacing / 2 + (spacing / 2 if row % 2 else 0)          # quincunx: alternate rows offset
        while x < x1:
            if rnd.random() > skip:
                px, py = x + rnd.gauss(0, jitter / 2), y + rnd.gauss(0, jitter / 2)
                o_l = inv @ Vector((px, py, 1000.0)); d_l = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
                hit = tree.ray_cast(o_l, d_l)
                if hit[0] is not None:
                    pts.append(mw @ hit[0] + Vector((0, 0, -0.05))); n += 1
            x += spacing
        y += spacing * 0.92; row += 1
    # one wind-moved instancer for the whole grove: old olive trees barely bend, their crowns sway and shimmer
    allv = _hidden_collection(f'{name}_variants')
    for c in vs:
        if c.name not in allv.children:
            allv.children.link(c)
    return wind_scatter(None, allv, 0, seed=seed, points=pts, gust=0.025, gust_size=20.0, gust_speed=2.5,
                        flutter=0.01, flutter_hz=0.8, scale=size, name=name)


# ------------------------------------------------------------------ stones, walls, terraces
def _stone_bm(bm, center, size, rnd, rot=0.0, subdiv=2):
    """One irregular fieldstone: a low-poly sphere squashed to `size`, its corners pushed in/out at random
    (no two alike), flattened top and bottom like a stone picked from a field and laid in a wall."""
    m = Matrix.Translation(center) @ Matrix.Rotation(rot, 4, 'Z')
    res = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=0.5, matrix=Matrix.Identity(4))
    for v in res['verts']:
        p = v.co.copy()
        k = 1.0 + rnd.uniform(-0.18, 0.18)
        p *= k
        p.z = max(-0.38, min(0.38, p.z))                               # flat-ish beds
        p = Vector((p.x * size[0], p.y * size[1], p.z * size[2]))
        v.co = m @ p


def dry_stone_wall(points, height=1.1, width=0.55, seed=0, name='field_wall', material=None, ground=None,
                   ruined=0.0, faces=2, stone_scale=1.0, subdiv=2):
    """A dry-stone field wall along a polyline (list of (x, y) or (x, y, z)): courses of unmortared fieldstones,
    bigger stones low, smaller on top, a few capstones; the two faces lean in a little (battered). If `ground` is
    given, the wall sits on it (ray cast). ruined 0..1 = gaps and tumbled stones at the foot (old boundary walls).
    faces=1: only the -side face is built (a TERRACE retaining wall: its back is buried in soil); stone_scale > 1
    = bigger stones (fewer of them: long terrace walls stay fast); subdiv 1 = simpler stones for distant walls."""
    rnd = random.Random(seed)
    tree = None
    if ground is not None:
        from mathutils.bvhtree import BVHTree
        dg = bpy.context.evaluated_depsgraph_get(); tree = BVHTree.FromObject(ground, dg)
        gmw, ginv = ground.matrix_world, ground.matrix_world.inverted()
    def ground_z(x, y, z0):
        if tree is None:
            return z0
        hit = tree.ray_cast(ginv @ Vector((x, y, 1000.0)), (ginv.to_3x3() @ Vector((0, 0, -1))).normalized())
        return (gmw @ hit[0]).z if hit[0] is not None else z0
    pts = [Vector((p[0], p[1], p[2] if len(p) > 2 else 0.0)) for p in points]
    bm = bmesh.new()
    for a, b in zip(pts[:-1], pts[1:]):
        seg = b - a; L = seg.length; d = seg.normalized(); side = Vector((-d.y, d.x, 0))
        heading = math.atan2(d.y, d.x)
        s = 0.0
        while s < L:
            base = a + d * s
            gz = ground_z(base.x, base.y, base.z)
            h_here = height * (1 - ruined * max(0.0, math.sin(s * 0.9 + seed)) * rnd.random())
            z = gz
            course = 0
            while z < gz + h_here - 0.05:
                big = (1.0 - 0.45 * (z - gz) / height) * stone_scale    # bigger stones low in the wall
                ln = rnd.uniform(0.25, 0.5) * big; hh = rnd.uniform(0.13, 0.24) * big
                for face in ((-1, 1) if faces == 2 else (-1,)):           # two faces, rubble core between
                    batter = (z - gz) / height * 0.08
                    c = base + d * (ln / 2 + rnd.uniform(-0.03, 0.03)) + side * face * (width / 2 - 0.12 - batter) \
                        + Vector((0, 0, z - base.z + hh / 2))
                    _stone_bm(bm, c, (ln, rnd.uniform(0.2, 0.3) * stone_scale ** 0.5, hh), rnd, heading + rnd.uniform(-0.15, 0.15), subdiv)
                z += hh * 0.92; course += 1
            if rnd.random() < 0.35:                                     # capstone across the top
                c = base + d * 0.2 + Vector((0, 0, z - base.z + 0.06))
                _stone_bm(bm, c, (rnd.uniform(0.3, 0.45), width * 0.9, 0.12), rnd, heading)
            if ruined and rnd.random() < ruined * 0.4:                  # a tumbled stone at the foot
                c = base + side * rnd.choice((-1, 1)) * (width * 0.9 + rnd.uniform(0, 0.4)) + Vector((0, 0, gz - base.z + 0.08))
                _stone_bm(bm, c, (0.3, 0.22, 0.16), rnd, rnd.uniform(0, 3))
            s += rnd.uniform(0.28, 0.45) * stone_scale
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me))
    for p in o.data.polygons:
        p.use_smooth = True
    o.data.materials.append(material or stone_material())
    return o


def terraced_hill(name='terraces', loc=(0, 0, 0), size=(60.0, 40.0), rise=18.0, steps=7, seed=0, wall_h=1.2):
    """A hillside cut into level TERRACES held up by dry-stone walls (how Greeks farmed steep land for vines,
    olives and grain). The slope rises along +Y by `rise` m over `size[1]`; each step = a flat strip + a wall.
    Returns (ground, [walls]). Plant the strips with grain_field / olive_grove afterwards."""
    rnd = random.Random(seed)
    step = 0.25
    nx, ny = int(size[0] / step) + 1, int(size[1] / step) + 1
    strip = size[1] / steps
    xs = np.linspace(-size[0] / 2, size[0] / 2, nx); ys = np.linspace(0, size[1], ny)
    X, Y = np.meshgrid(xs, ys)
    wiggle = 1.2 * np.sin(X * 0.08 + seed) + 0.6 * np.sin(X * 0.21 + 2 * seed)       # walls follow the contours
    k = np.floor((Y + wiggle) / strip)
    frac = (Y + wiggle) / strip - k
    Z = (k + np.clip((frac - 0.92) / 0.08, 0, 1)) * (rise / steps)                    # flat, then the wall face
    Z += 0.04 * np.sin(X * 1.7) * np.sin(Y * 1.3)
    verts = np.stack([X.ravel() + loc[0], Y.ravel() + loc[1], Z.ravel() + loc[2]], 1)
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(ny - 1) for i in range(nx - 1)]
    me = bpy.data.meshes.new(name); me.from_pydata(verts.tolist(), [], faces); me.update()
    g = link(bpy.data.objects.new(name, me))
    for p in me.polygons:
        p.use_smooth = True
    g.data.materials.append(soil_material('terrace_soil', tint=(1.0, 0.92, 0.82)))
    walls = []
    for s in range(1, steps):
        line = []
        for x in np.linspace(-size[0] / 2 + 0.5, size[0] / 2 - 0.5, 40):
            w = 1.2 * math.sin(x * 0.08 + seed) + 0.6 * math.sin(x * 0.21 + 2 * seed)
            y = s * strip - w - 0.04 * strip
            line.append((x + loc[0], y + loc[1], loc[2] + (s - 1) * rise / steps))
        walls.append(dry_stone_wall(line, height=rise / steps + 0.25, width=0.6, seed=seed + s, name=f'{name}_wall{s}',
                                    ruined=0.05 * rnd.random(), faces=1, stone_scale=1.7, subdiv=1))
    return g, walls


def threshing_floor(loc=(0, 0, 0), radius=6.5, seed=0, name='threshing_floor', with_grain=True):
    """The round threshing floor (halos / aloni): a level circle paved with flat stones, edged by a kerb of upright
    slabs, on a windy rise (the wind carried the chaff away at winnowing). With grain: a heap of sheaves and
    trodden straw over the floor (Xenophon, Oeconomicus 18: oxen and mules tread the grain, the chaff is thrown up
    into the wind). Era: in use in Greece from the Bronze Age to the 20th century."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    c0 = Vector(loc)
    # flagstones: rings of slabs from the centre out
    r = 0.0
    while r < radius - 0.3:
        ring_r = r + 0.35
        n = max(1, int(2 * math.pi * ring_r / 0.6))
        for i in range(n):
            a = 2 * math.pi * (i + rnd.random() * 0.3) / n
            c = c0 + Vector((ring_r * math.cos(a), ring_r * math.sin(a), 0.03))
            _stone_bm(bm, c, (rnd.uniform(0.45, 0.62), rnd.uniform(0.4, 0.55), 0.07), rnd, a + rnd.uniform(-0.3, 0.3))
        r += 0.55
    for i in range(int(2 * math.pi * radius / 0.5)):                   # kerb of upright slabs
        a = 2 * math.pi * i / int(2 * math.pi * radius / 0.5)
        c = c0 + Vector((radius * math.cos(a), radius * math.sin(a), 0.14))
        _stone_bm(bm, c, (0.12, 0.5, 0.32), rnd, a)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.data.materials.append(stone_material('threshing_stone', tint=(1.05, 1.0, 0.92)))
    for p in o.data.polygons:
        p.use_smooth = True
    parts = [o]
    if with_grain:
        # trodden straw over the floor + a heap of sheaves at one side
        bpy.ops.mesh.primitive_circle_add(vertices=48, radius=radius - 0.4, fill_type='NGON', location=c0 + Vector((0, 0, 0.075)))
        disc = bpy.context.object; disc.name = name + '_straw'
        disc.modifiers.new('sub', 'SUBSURF').levels = 3
        ps = disc.modifiers.new('straw', 'PARTICLE_SYSTEM'); st = ps.particle_system.settings
        straw = _straw_scatter(name + '_straw_bits', 0.95, seed)
        col = _hidden_collection(name + '_bits'); col.objects.link(straw)
        st.type = 'HAIR'; st.count = int(math.pi * radius * radius * 40); st.hair_length = 1.0; st.emit_from = 'FACE'
        st.render_type = 'OBJECT'; st.instance_object = straw; st.use_advanced_hair = True; st.use_rotations = True
        st.rotation_mode = 'NOR'; st.phase_factor_random = 2.0; st.size_random = 0.5
        disc.data.materials.append(_plant_material('chaff', 0.9))
        disc.show_instancer_for_render = False
        parts.append(disc)
        heap = sheaf_heap(c0 + Vector((radius * 0.45, radius * 0.3, 0.07)), seed=seed)
        parts.append(heap)
    return parts


def sheaf_heap(loc, n=26, seed=0, name='sheaves'):
    """A heap of bound sheaves waiting to be threshed: each sheaf = a bundle of stalks tied in the middle."""
    rnd = random.Random(seed)
    col = _hidden_collection(name + '_src')
    sheaf = grain_clump(name + '_sheaf', 'wheat', height=0.9, stalks=30, ripe=1.0, seed=seed + 99, hair_axis=False)
    # squeeze the clump into a bundle (tied in the middle)
    for v in sheaf.data.vertices:
        z = v.co.z
        pinch = 0.35 + 0.65 * abs(z - 0.4) / 0.5
        v.co.x *= pinch; v.co.y *= pinch
    col.objects.link(sheaf)
    root = link(bpy.data.objects.new(name, None)); root.location = loc
    for i in range(n):
        inst = bpy.data.objects.new(f'{name}_{i}', None)
        inst.instance_type = 'COLLECTION'; inst.instance_collection = col
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0, 1.2)
        inst.location = Vector(loc) + Vector((r * math.cos(a), r * math.sin(a), 0.15 + (1.2 - r) * 0.45 * rnd.random()))
        inst.rotation_euler = (math.radians(rnd.uniform(60, 95)), 0, rnd.uniform(0, 2 * math.pi))   # lying down
        link(inst)
    return root


# ------------------------------------------------------------------ farm life
def beehives(loc=(0, 0, 0), heading_deg=0.0, n=5, seed=0, name='beehives'):
    """Horizontal terracotta beehives (long clay tubes with a lid at one end), laid side by side on a low stone
    bench. Fragments of such hives are excavated at Classical Attic farms (Vari house; Aristotle, History of
    Animals 9.40, on bee-keeping). Mount Hymettos honey was famous."""
    from lib import props
    rnd = random.Random(seed)
    clay = props.terracotta(name + '_clay', seed=seed)
    root = link(bpy.data.objects.new(name, None)); root.location = loc; root.rotation_euler = (0, 0, math.radians(heading_deg))
    bench = dry_stone_wall([(-n * 0.22 - 0.2, 0), (n * 0.22 + 0.2, 0)], height=0.45, width=0.7, seed=seed, name=name + '_bench')
    bench.parent = root
    for i in range(n):
        x = (i - (n - 1) / 2) * 0.44
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.16, depth=0.75, location=(x, 0, 0.62), rotation=(math.pi / 2, 0, 0))
        h = bpy.context.object; h.name = f'{name}_hive{i}'
        bm = bmesh.new(); bm.from_mesh(h.data)
        for v in bm.verts:                                              # slightly tapered, hand-made
            k = 1 - 0.12 * (v.co.z + 0.375) / 0.75 + rnd.uniform(-0.01, 0.01)
            v.co.x *= k; v.co.y *= k
        bm.to_mesh(h.data); bm.free()
        h.modifiers.new('ribs', 'SOLIDIFY').thickness = 0.015
        h.data.materials.append(clay); h.parent = root
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.17, depth=0.02, location=(x, -0.38, 0.62), rotation=(math.pi / 2, 0, 0))
        lid = bpy.context.object; lid.name = f'{name}_lid{i}'; lid.data.materials.append(clay); lid.parent = root
    return root


def farmstead(loc=(0, 0, 0), heading_deg=0.0, seed=0, name='farmstead'):
    """A small Attic farm (after the excavated Dema house, c. 420 BC, and the Vari house): the courtyard house
    (architecture.courtyard_house, main session's kit), a threshing floor on the windy side, beehives against the
    south wall, and a stone-walled yard."""
    from lib import architecture
    house = architecture.courtyard_house(loc=loc, seed=seed, name=name + '_house')
    a = math.radians(heading_deg)
    def at(dx, dy):
        return (loc[0] + dx * math.cos(a) - dy * math.sin(a), loc[1] + dx * math.sin(a) + dy * math.cos(a), loc[2])
    floor = threshing_floor(at(18, 6), seed=seed + 1, name=name + '_halos')
    hives = beehives(at(-4, -9), heading_deg=heading_deg, seed=seed + 2, name=name + '_hives')
    yard = dry_stone_wall([at(-12, -14), at(14, -14), at(14, 12)], height=1.0, seed=seed + 3, name=name + '_yardwall',
                          ruined=0.1)
    return {'house': house, 'threshing_floor': floor, 'beehives': hives, 'yard_wall': yard}


def _sock(sockets, name):
    """The ENABLED socket called `name` (Blender 5.x shows only the sockets of a node's current data type; older
    versions keep hidden duplicates with the same name, one per type)."""
    for sk in sockets:
        if sk.name == name and getattr(sk, 'enabled', True):
            return sk
    raise KeyError(name)


def _out(node):
    """The node's first enabled output."""
    return next(o for o in node.outputs if getattr(o, 'enabled', True))


# ------------------------------------------------------------------ WIND: fields that move like in the movies
def wind_scatter(ground, collection, density, seed=0, density_attr='density', wind_deg=30.0, gust=0.32,
                 gust_size=9.0, gust_speed=3.2, flutter=0.06, flutter_hz=1.6, scale=(0.75, 1.25), name='wind_scatter',
                 points=None, random_turn=True):
    """Scatter the objects of `collection` over `ground` with GEOMETRY NODES and make them MOVE IN THE WIND.
      density      instances per m2 (times the 0..1 vertex group / attribute `density_attr`, if present)
      wind_deg     where the wind blows TO (0 = +X), in degrees
      gust         how far a plant bends in a strong gust (radians, ~0.3 = 17 degrees)
      gust_size    size of the gust patches (m); gust_speed = how fast they sweep across (m/s)
      flutter      small quick sway of every plant (radians) at `flutter_hz`
    How it works: a big soft NOISE pattern is laid over the field and slides along the wind direction with the
    scene clock (Scene Time). Where it is high, a gust is passing: those plants lean away from the wind, so waves of
    bending roll across the field (the 'wind running through the wheat' look). A second, small fast noise adds the
    constant flutter. Each plant rotates about its own base. Nothing is baked: it animates in every frame/shot.
    Plants must be built Z-up with the origin at the ground.
    points = a list of world positions: instead of scattering over `ground`, put ONE instance on each point (rows
    of vines, the trees of a grove) - a small point-cloud object carries the modifier and is returned's owner.
    `collection` may hold objects or child collections (one scanned tree variant = one child collection)."""
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N = ng.nodes; L = ng.links.new
    gin = N.new('NodeGroupInput'); gout = N.new('NodeGroupOutput')
    if points is not None:                                               # one instance per given point
        me = bpy.data.meshes.new(name + '_pts'); me.from_pydata([tuple(map(float, p)) for p in points], [], []); me.update()
        ground = link(bpy.data.objects.new(name + '_pts', me))
        dist = N.new('GeometryNodeMeshToPoints'); L(gin.outputs[0], dist.inputs['Mesh'])
    else:
        dist = N.new('GeometryNodeDistributePointsOnFaces'); dist.distribute_method = 'RANDOM'
        L(gin.outputs[0], dist.inputs['Mesh'])
        dist.inputs['Density'].default_value = density; dist.inputs['Seed'].default_value = seed
    if points is None and density_attr and density_attr in ground.vertex_groups:
        # density map (0..1 vertex group) x density -> the node's Density input (Blender 5.3 RANDOM mode has no
        # separate 'Density Factor' socket)
        na = N.new('GeometryNodeInputNamedAttribute'); na.data_type = 'FLOAT'; na.inputs['Name'].default_value = density_attr
        dm = N.new('ShaderNodeMath'); dm.operation = 'MULTIPLY'; dm.inputs[1].default_value = density
        L(na.outputs['Attribute'], dm.inputs[0]); L(dm.outputs[0], dist.inputs['Density'])
    ci = N.new('GeometryNodeCollectionInfo'); ci.inputs['Collection'].default_value = collection
    ci.inputs['Separate Children'].default_value = True; ci.inputs['Reset Children'].default_value = True
    ci.transform_space = 'ORIGINAL'
    iop = N.new('GeometryNodeInstanceOnPoints')
    L(dist.outputs['Points'], iop.inputs['Points']); L(ci.outputs[0], iop.inputs['Instance'])
    n_items = len(collection.children) or len(collection.objects)
    iop.inputs['Pick Instance'].default_value = True
    ridx = N.new('FunctionNodeRandomValue'); ridx.data_type = 'INT'
    _sock(ridx.inputs, 'Min').default_value = 0; _sock(ridx.inputs, 'Max').default_value = max(0, n_items - 1)
    _sock(ridx.inputs, 'Seed').default_value = seed + 1
    L(_out(ridx), iop.inputs['Instance Index'])
    rz = N.new('FunctionNodeRandomValue'); rz.data_type = 'FLOAT'
    _sock(rz.inputs, 'Min').default_value = 0.0; _sock(rz.inputs, 'Max').default_value = 2 * math.pi
    _sock(rz.inputs, 'Seed').default_value = seed + 2
    comb = N.new('ShaderNodeCombineXYZ'); L(_out(rz), comb.inputs['Z'])
    L(comb.outputs[0], iop.inputs['Rotation'])
    rs = N.new('FunctionNodeRandomValue'); rs.data_type = 'FLOAT'
    _sock(rs.inputs, 'Min').default_value = scale[0]; _sock(rs.inputs, 'Max').default_value = scale[1]
    _sock(rs.inputs, 'Seed').default_value = seed + 3
    L(_out(rs), iop.inputs['Scale'])
    # --- wind: gust waves sliding along the wind, + flutter
    t = N.new('GeometryNodeInputSceneTime')
    pos = N.new('GeometryNodeInputPosition')
    wd = Vector((math.cos(math.radians(wind_deg)), math.sin(math.radians(wind_deg)), 0.0))
    def noise_at(size, speed, detail, w_seed):
        shift = N.new('ShaderNodeVectorMath'); shift.operation = 'SCALE'
        dirv = N.new('ShaderNodeCombineXYZ'); dirv.inputs['X'].default_value = wd.x * speed; dirv.inputs['Y'].default_value = wd.y * speed
        L(dirv.outputs[0], shift.inputs[0]); L(t.outputs['Seconds'], shift.inputs['Scale'])
        sub = N.new('ShaderNodeVectorMath'); sub.operation = 'SUBTRACT'
        L(pos.outputs[0], sub.inputs[0]); L(shift.outputs[0], sub.inputs[1])     # the pattern moves WITH the wind
        off = N.new('ShaderNodeVectorMath'); off.operation = 'ADD'; off.inputs[1].default_value = (w_seed * 17.3, w_seed * 5.1, 0)
        L(sub.outputs[0], off.inputs[0])
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.0 / size; nz.inputs['Detail'].default_value = detail
        L(off.outputs[0], nz.inputs['Vector'])
        return nz.outputs['Fac']
    g = noise_at(gust_size, gust_speed, 1.5, seed)
    shape = N.new('ShaderNodeMapRange'); shape.inputs['From Min'].default_value = 0.42; shape.inputs['From Max'].default_value = 0.68
    shape.inputs['To Min'].default_value = gust * 0.12; shape.inputs['To Max'].default_value = gust   # always a little lean
    L(g, shape.inputs['Value'])
    fl = noise_at(0.7, flutter_hz * 0.7, 2.0, seed + 7)
    flm = N.new('ShaderNodeMapRange'); flm.inputs['To Min'].default_value = -flutter; flm.inputs['To Max'].default_value = flutter
    L(fl, flm.inputs['Value'])
    ang = N.new('ShaderNodeMath'); ang.operation = 'ADD'; L(shape.outputs['Result'], ang.inputs[0]); L(flm.outputs['Result'], ang.inputs[1])
    # lean AWAY from the wind = rotate about the axis perpendicular to it (Z x wind)
    axis = Vector((0, 0, 1)).cross(wd).normalized()
    rx = N.new('ShaderNodeMath'); rx.operation = 'MULTIPLY'; rx.inputs[1].default_value = axis.x
    ry = N.new('ShaderNodeMath'); ry.operation = 'MULTIPLY'; ry.inputs[1].default_value = axis.y
    L(ang.outputs[0], rx.inputs[0]); L(ang.outputs[0], ry.inputs[0])
    # rotation vector (x, y) = angle * axis, so a gust tips each plant over toward the wind direction
    rot = N.new('ShaderNodeCombineXYZ'); L(rx.outputs[0], rot.inputs['X']); L(ry.outputs[0], rot.inputs['Y'])
    ri = N.new('GeometryNodeRotateInstances'); L(iop.outputs[0], ri.inputs['Instances']); L(rot.outputs[0], ri.inputs['Rotation'])
    ri.inputs['Local Space'].default_value = False
    join = N.new('GeometryNodeJoinGeometry')
    if points is None:
        L(gin.outputs[0], join.inputs[0])                                # keep the ground itself
    L(ri.outputs[0], join.inputs[0])
    L(join.outputs[0], gout.inputs[0])
    if not random_turn:
        iop.inputs['Rotation'].default_value = (0, 0, 0)
        for lk in list(iop.inputs['Rotation'].links):
            ng.links.remove(lk)
    mod = ground.modifiers.new(name, 'NODES'); mod.node_group = ng
    return mod


# ------------------------------------------------------------------ vineyards
def _vine_leaf_shape(n=15):
    """Outline of a grape-vine leaf (5 pointed lobes with deep notches), unit size, in the XY plane."""
    pts = []
    for i in range(n * 5):
        t = i / (n * 5) * 2 * math.pi
        lobe = 0.55 + 0.45 * abs(math.cos(2.5 * t)) ** 0.6              # 5 lobes
        notch = 1.0 - 0.25 * max(0.0, math.cos(t - math.pi / 2)) ** 8     # the stalk notch at the base
        r = lobe * notch
        pts.append((r * math.cos(t), r * math.sin(t) + 0.3))
    return pts


def _bark_material(name='vine_bark'):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = principled(name, (0.11, 0.075, 0.05), rough=0.85, bump=0.6, bump_scale=90)
    m.use_fake_user = True
    return m


def _leaf_material(name='vine_leaf', autumn=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; L = nt.links.new; b = nt.nodes['Principled BSDF']
    green, red = np.array((0.08, 0.17, 0.03)), np.array((0.35, 0.1, 0.03))
    base = green * (1 - autumn) + red * autumn
    info = nt.nodes.new('ShaderNodeObjectInfo')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*(base * 0.75), 1); ramp.color_ramp.elements[1].color = (*np.minimum(base * 1.3 + 0.02, 1), 1)
    L(info.outputs['Random'], ramp.inputs['Fac'])
    tr = nt.nodes.new('ShaderNodeBsdfTranslucent'); L(ramp.outputs['Color'], tr.inputs['Color'])
    L(ramp.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.5
    ms = nt.nodes.new('ShaderNodeMixShader'); ms.inputs['Fac'].default_value = 0.35
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    L(b.outputs[0], ms.inputs[1]); L(tr.outputs[0], ms.inputs[2]); L(ms.outputs[0], out.inputs['Surface'])
    return m


def vine(name='vine', seed=0, height=0.75, staked=False, grapes='black', autumn=0.0):
    """One old grape vine as Greeks grew it: a short, thick, twisting trunk (pruned hard every winter, so it is
    gnarled), 3-5 arms, a dense head of 5-lobed leaves and hanging bunches (black or white grapes; Hesiod tells to
    gather them when Arcturus rises, Works and Days 609). staked=True: tied to one wooden prop (a common Greek way).
    Returns an object (mesh) with the origin at the ground; instanced by vineyard()."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    parts = []
    # trunk + arms as bevelled curves (converted to mesh)
    def branch(pts, r0, r1):
        cu = bpy.data.curves.new(name + '_br', 'CURVE'); cu.dimensions = '3D'
        sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
        for i, p in enumerate(pts):
            bp = sp.bezier_points[i]; bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
            bp.radius = r0 + (r1 - r0) * i / (len(pts) - 1)
        cu.bevel_depth = 1.0; cu.bevel_resolution = 2; cu.resolution_u = 6
        o = link(bpy.data.objects.new(name + '_br', cu))
        dg = bpy.context.evaluated_depsgraph_get(); dg.update()
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg)); bpy.data.objects.remove(o)
        bm.from_mesh(me); bpy.data.meshes.remove(me)
    trunk = [Vector((rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), z)) +
             Vector((0.05 * math.sin(z * 9 + seed), 0.05 * math.cos(z * 7 + seed), 0)) for z in np.linspace(0, height, 5)]
    branch(trunk, 0.045, 0.03)
    tips = []
    for k in range(rnd.randint(3, 5)):
        a = 2 * math.pi * k / 5 + rnd.uniform(-0.4, 0.4)
        d = Vector((math.cos(a), math.sin(a), 0))
        arm = [trunk[-1] + d * (0.12 * t) + Vector((0, 0, 0.18 * t + 0.05 * math.sin(t * 3))) for t in np.linspace(0, 1, 4)]
        branch(arm, 0.025, 0.012)
        tips.append(arm[-1])
    me_wood = bpy.data.meshes.new(name + '_wood'); bm.to_mesh(me_wood); bm.free()
    wood = bpy.data.objects.new(name, me_wood); wood.data.materials.append(_bark_material())
    # leaves: a head of leaves around the arm tips (cards with the lobed outline), facing up/out to the light
    shape = _vine_leaf_shape()
    lb = bmesh.new()
    for tip in tips:
        for _ in range(rnd.randint(26, 40)):
            c = tip + Vector((rnd.gauss(0, 0.17), rnd.gauss(0, 0.17), rnd.gauss(0.1, 0.12)))
            s = rnd.uniform(0.07, 0.12)
            rot = Matrix.Rotation(rnd.uniform(0, 2 * math.pi), 3, 'Z') @ Matrix.Rotation(rnd.uniform(0.3, 1.1), 3, 'X')
            vs = [lb.verts.new(c + rot @ Vector((x * s, y * s, 0.02 * s * math.sin(x * 3)))) for x, y in shape]
            lb.faces.new(vs)
    me_leaf = bpy.data.meshes.new(name + '_leaves'); lb.to_mesh(me_leaf); lb.free()
    leaves = bpy.data.objects.new(name + '_leaves', me_leaf); leaves.data.materials.append(_leaf_material(autumn=autumn))
    leaves.parent = wood
    parts.append(leaves)
    # grape bunches: cones of small spheres hanging under the leaves
    gb = bmesh.new()
    for tip in tips:
        if rnd.random() < 0.8:
            top = tip + Vector((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), -0.05))
            for j in range(rnd.randint(30, 45)):
                t = rnd.random()
                rr = 0.045 * (1 - t) + 0.008
                p = top + Vector((rnd.gauss(0, rr), rnd.gauss(0, rr), -0.16 * t))
                bmesh.ops.create_uvsphere(gb, u_segments=6, v_segments=4, radius=rnd.uniform(0.007, 0.009),
                                          matrix=Matrix.Translation(p))
    me_g = bpy.data.meshes.new(name + '_grapes'); gb.to_mesh(me_g); gb.free()
    gcol = (0.05, 0.015, 0.04) if grapes == 'black' else (0.4, 0.42, 0.12)
    gm = bpy.data.materials.get('grapes_' + grapes) or principled('grapes_' + grapes, gcol, rough=0.35, sss=0.2)
    gm.use_fake_user = True
    gr = bpy.data.objects.new(name + '_grapes', me_g); gr.data.materials.append(gm); gr.parent = wood
    parts.append(gr)
    if staked:
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.018, depth=height + 0.45, location=(0.06, 0.0, (height + 0.45) / 2 - 0.1))
        st = bpy.context.object; st.name = name + '_stake'; st.data.materials.append(_bark_material('stake_wood'))
        bpy.context.scene.collection.objects.unlink(st); st.parent = wood; parts.append(st)
    for p in [wood] + parts:
        for poly in p.data.polygons:
            poly.use_smooth = True
    return wood, parts


def vineyard(ground, area, row=1.9, spacing=1.4, seed=0, staked=0.5, grapes='black', autumn=0.0, name='vineyard'):
    """Rows of low vines over `ground` (area = xmin, xmax, ymin, ymax). Six vine variants are built once and
    instanced (whole hillsides stay cheap). staked = share of vines tied to a single prop."""
    rnd = random.Random(seed)
    variants = []
    for v in range(6):
        col = _hidden_collection(f'{name}_v{v}')
        wood, parts = vine(f'{name}_vine{v}', seed=seed * 10 + v, staked=(v / 6 < staked), grapes=grapes, autumn=autumn)
        for o in [wood] + parts:
            col.objects.link(o)
        variants.append(col)
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get(); tree = BVHTree.FromObject(ground, dg)
    mw, inv = ground.matrix_world, ground.matrix_world.inverted()
    out = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if out.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(out)
    x0, x1, y0, y1 = area
    n = 0; pts = []
    y = y0 + row / 2
    while y < y1:
        x = x0 + spacing / 2 + rnd.uniform(0, 0.3)
        while x < x1:
            if rnd.random() > 0.05:                                       # a few missing vines
                hit = tree.ray_cast(inv @ Vector((x + rnd.gauss(0, 0.08), y + rnd.gauss(0, 0.08), 1000.0)),
                                    (inv.to_3x3() @ Vector((0, 0, -1))).normalized())
                if hit[0] is not None:
                    pts.append(mw @ hit[0]); n += 1
            x += spacing
        y += row
    # all vines in one wind-moved instancer: leaves and canes sway in the gusts (less than grain: woody plants)
    allv = _hidden_collection(f'{name}_variants')
    for c in variants:
        if c.name not in allv.children:
            allv.children.link(c)
    return wind_scatter(None, allv, 0, seed=seed, points=pts, gust=0.07, gust_size=12.0, flutter=0.025,
                        flutter_hz=1.2, scale=(0.85, 1.15), name=name)


# ------------------------------------------------------------------ herds
def flock(ground, center, n=24, kind='sheep', radius=9.0, seed=0, dog=True, name=None):
    """A grazing flock: sheep or goats (the main session's CC-BY scans, library/scans/animal_sheep|animal_goat) in a
    loose group that thins toward its edge, most heads down grazing (random turn), a few strays further out, and
    a herd dog at the side. Placed ON `ground` by ray cast. Pair with a shepherd (crowd role 'shepherd' + crook).
    Goats were the hill animal of Attica, sheep the lowland one (wool!)."""
    from lib import scatter
    from mathutils.bvhtree import BVHTree
    name = name or f'flock_{kind}_{seed}'
    rnd = random.Random(seed)
    try:
        vs = scatter.load_scan(f'animal_{kind}')
    except Exception as e:
        print('flock: scan missing -', e)
        return None
    dg = bpy.context.evaluated_depsgraph_get(); tree = BVHTree.FromObject(ground, dg)
    mw, inv = ground.matrix_world, ground.matrix_world.inverted()
    out = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if out.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(out)
    def drop(x, y):
        hit = tree.ray_cast(inv @ Vector((x, y, 1000.0)), (inv.to_3x3() @ Vector((0, 0, -1))).normalized())
        return (mw @ hit[0]) if hit[0] is not None else None
    heading = rnd.uniform(0, 2 * math.pi)                               # the flock drifts one way while grazing
    for i in range(n):
        r = radius * (rnd.random() ** 0.6) * (1.8 if rnd.random() < 0.1 else 1.0)
        a = rnd.uniform(0, 2 * math.pi)
        p = drop(center[0] + r * math.cos(a), center[1] + r * math.sin(a))
        if p is None:
            continue
        inst = bpy.data.objects.new(f'{name}_{i}', None)
        inst.instance_type = 'COLLECTION'; inst.instance_collection = rnd.choice(vs)
        inst.location = p; inst.rotation_euler = (0, 0, heading + rnd.gauss(0, 0.9))
        sc = rnd.uniform(0.85, 1.1); inst.scale = (sc, sc, sc)
        out.objects.link(inst)
    if dog:
        try:
            dv = scatter.load_scan('animal_dog')
            p = drop(center[0] + radius * 1.3 * math.cos(heading + 1.6), center[1] + radius * 1.3 * math.sin(heading + 1.6))
            if p is not None:
                d = bpy.data.objects.new(f'{name}_dog', None); d.instance_type = 'COLLECTION'; d.instance_collection = dv[0]
                d.location = p; d.rotation_euler = (0, 0, heading + math.pi); out.objects.link(d)
        except Exception as e:
            print('flock: no dog scan -', e)
    return out


# ------------------------------------------------------------------ Persian royal garden
def persian_garden(loc=(0, 0, 0), size=(80.0, 60.0), seed=0, name='paradeisos'):
    """The Persian royal garden-park (paradeisos, origin of 'paradise'), after Pasargadae (c. 530 BC): long channels
    of cut limestone carrying water in straight lines, square basins at intervals, framing planted beds; rows of
    tall cypress along the walks, date palms and fruit trees in the beds (Xenophon, Oeconomicus 4.20-25: Cyrus'
    park at Sardis 'planted in straight rows, every angle beautiful'). Trees are the main session's CC0/CC-BY
    scans (tree_cypress, tree_date_palm, tree_olive_zakynthos), moving gently in the wind. Returns parts."""
    from lib import scatter, sets
    rnd = random.Random(seed)
    W, D = size
    x0, y0 = loc[0] - W / 2, loc[1] - D / 2
    bpy.ops.mesh.primitive_plane_add(size=1, location=(loc[0], loc[1], loc[2]))
    g = bpy.context.object; g.name = name + '_ground'; g.scale = (W + 20, D + 20, 1)
    bpy.ops.object.transform_apply(scale=True)
    # irrigated, green ground (the whole point of a paradeisos) and PALE cut limestone kerbs
    g.data.materials.append(soil_material('garden_turf', scan='coast_sand_rocks_02', tint=(0.42, 0.55, 0.24), tiles=1.2))
    lime = stone_material('channel_limestone', scan='marble_01', tint=(0.92, 0.9, 0.84), tiles=0.8)
    water = sets.water_material()
    bm = bmesh.new()
    wbm = bmesh.new()
    def channel(a, b, w=0.5, d=0.25):
        """Stone channel from a to b: two kerbs and a floor; water fills it to just below the rim."""
        d_ = (Vector(b) - Vector(a)); L = d_.length; u = d_.normalized(); side = Vector((-u.y, u.x, 0))
        mid = (Vector(a) + Vector(b)) / 2
        for sgn in (-1, 1):
            c = mid + side * sgn * (w / 2 + 0.12) + Vector((0, 0, 0.08))
            m = Matrix.Translation(c) @ Matrix.Rotation(math.atan2(u.y, u.x), 4, 'Z') @ Matrix.Diagonal((L, 0.24, 0.24, 1))
            bmesh.ops.create_cube(bm, size=1.0, matrix=m)
        m = Matrix.Translation(mid + Vector((0, 0, -d))) @ Matrix.Rotation(math.atan2(u.y, u.x), 4, 'Z') @ Matrix.Diagonal((L, w + 0.48, 0.1, 1))
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)
        m = Matrix.Translation(mid + Vector((0, 0, 0.12))) @ Matrix.Rotation(math.atan2(u.y, u.x), 4, 'Z') @ Matrix.Diagonal((L, w, 1, 1))
        bmesh.ops.create_grid(wbm, x_segments=1, y_segments=1, size=0.5, matrix=m)
    def basin(c, s=1.6):
        for k in range(4):
            a = k * math.pi / 2
            p = Vector(c) + Vector((math.cos(a), math.sin(a), 0)) * (s / 2) + Vector((0, 0, 0.1))
            m = Matrix.Translation(p) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Diagonal((0.3, s + 0.3, 0.3, 1))
            bmesh.ops.create_cube(bm, size=1.0, matrix=m)
        bmesh.ops.create_grid(wbm, x_segments=1, y_segments=1, size=s / 2, matrix=Matrix.Translation(Vector(c) + Vector((0, 0, 0.14))))
    cx, cy = loc[0], loc[1]
    # a cross of channels with a basin at the crossing and every ~14 m along them (chahar bagh-like layout)
    channel((x0, cy, loc[2]), (x0 + W, cy, loc[2])); channel((cx, y0, loc[2]), (cx, y0 + D, loc[2]))
    for t in np.arange(-W / 2 + 7, W / 2, 14.0):
        basin((cx + t, cy, loc[2]))
    for t in np.arange(-D / 2 + 7, D / 2, 14.0):
        basin((cx, cy + t, loc[2]))
    me = bpy.data.meshes.new(name + '_channels'); bm.to_mesh(me); bm.free()
    ch = link(bpy.data.objects.new(name + '_channels', me)); ch.data.materials.append(lime)
    me = bpy.data.meshes.new(name + '_water'); wbm.to_mesh(me); wbm.free()
    wa = link(bpy.data.objects.new(name + '_water', me)); wa.data.materials.append(water)
    # trees: cypress rows along the channels, date palms + olives in the four beds, all in straight rows
    pts = {'tree_cypress': [], 'tree_date_palm': [], 'tree_olive_zakynthos': []}
    # an AIRY royal park: cypresses in stately rows set back from the walks (light reaches the water and the paths),
    # fruit trees and palms spaced wide in the four beds
    for t in np.arange(-W / 2 + 4, W / 2, 9.0):
        for sgn in (-1, 1):
            pts['tree_cypress'].append(Vector((cx + t, cy + sgn * 5.5, loc[2])))
    for t in np.arange(-D / 2 + 4, D / 2, 9.0):
        for sgn in (-1, 1):
            if abs(t) > 7:
                pts['tree_cypress'].append(Vector((cx + sgn * 5.5, cy + t, loc[2])))
    for qx in (-1, 1):
        for qy in (-1, 1):
            for i, x in enumerate(np.arange(13, W / 2 - 3, 12.0)):
                for j, y in enumerate(np.arange(13, D / 2 - 3, 12.0)):
                    kind = 'tree_date_palm' if (i + j) % 2 == 0 else 'tree_olive_zakynthos'
                    pts[kind].append(Vector((cx + qx * x, cy + qy * y, loc[2])))
    parts = {'ground': g, 'channels': ch, 'water': wa, 'trees': []}
    for kind, P in pts.items():
        if not P:
            continue
        try:
            vs = scatter.load_scan(kind)
        except Exception as e:
            print('persian_garden: scan missing', kind, e); continue
        allv = _hidden_collection(f'{name}_{kind}_v')
        for c in vs:
            if c.name not in allv.children:
                allv.children.link(c)
        sway = 0.012 if kind == 'tree_cypress' else 0.03
        sc = {'tree_cypress': (0.75, 0.95), 'tree_date_palm': (0.6, 0.8)}.get(kind, (0.7, 0.9))
        parts['trees'].append(wind_scatter(None, allv, 0, seed=seed + len(parts['trees']), points=P, gust=sway,
                                           gust_size=18.0, gust_speed=2.5, flutter=sway * 0.5, flutter_hz=0.9,
                                           scale=sc, name=f'{name}_{kind}'))
    return parts

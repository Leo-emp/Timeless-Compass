# SET DRESSING (Session D): make every frame RICH, like a film set dressed by an art department - ground
# detail, everyday clutter, background life and atmosphere - placed only where the CAMERA SEES.
#   dress_view(cam, ground, setting, amount)   the one call a shot needs after its set, actors and camera exist
# How it works:
#   1. points are sampled INSIDE THE CAMERA'S VIEW (rays through random spots of the frame hit the ground), denser
#      near the lens and thinning with distance (what is close reads in detail, the distance reads as 'busy'),
#      never inside keep-clear zones (where the actors stand and move)
#   2. each point gets something from the SETTING'S KIT (village, market, harbour, countryside, persian_camp,
#      battlefield): era-correct pieces from our libraries - jars, baskets, sacks, firewood, stones, shrubs, rope,
#      anchors, tents, broken spears, fallen shields - each built ONCE and placed as cheap instances
#   3. LIFE: background people (low-poly stand-ins, only far enough away to read as people, never in close-up),
#      birds overhead, and ATMOSPHERE: smoke from ovens/fires, haze
# Everything is seeded: the same shot dresses the same way every render (and every shard of a cloud render).
import math
import random

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from lib.common import link, principled


# ------------------------------------------------------------------ where the camera looks
def visible_points(cam, ground, n, near=1.5, far=80.0, keep_clear=(), seed=0, margin=0.15, near_bias=6.0):
    """Up to n ground points seen by `cam`: random rays through the frame (a little beyond its edges, so things
    enter the frame from outside too) hitting `ground` between `near` and `far` metres. Points closer than
    `near_bias` m are always kept; farther ones are kept with probability near_bias/d (density falls with
    distance, like a real set: detailed near, busy far). keep_clear = [(x, y, r)] free circles (actors)."""
    rnd = random.Random(seed)
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(ground, dg)
    gi = ground.matrix_world.inverted(); gm = ground.matrix_world
    mw = cam.matrix_world
    pos = mw.translation.copy()
    fwd = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
    right = (mw.to_3x3() @ Vector((1, 0, 0))).normalized()
    up = (mw.to_3x3() @ Vector((0, 0, 1))).normalized()
    aspect = sc.render.resolution_x / sc.render.resolution_y
    hw = (cam.data.sensor_width / 2) / cam.data.lens; hh = hw / aspect
    out = []
    tries = 0
    while len(out) < n and tries < n * 30:
        tries += 1
        u, v = rnd.uniform(-1 - margin, 1 + margin), rnd.uniform(-1 - margin, 0.6)   # mostly the lower frame (ground)
        d = (fwd + right * u * hw + up * v * hh).normalized()
        hit = tree.ray_cast(gi @ pos, (gi.to_3x3() @ d).normalized(), far)
        if hit[0] is None:
            continue
        p = gm @ hit[0]
        dist = (p - pos).length
        if dist < near or (dist > near_bias and rnd.random() > near_bias / dist):
            continue
        if any((p.x - x) ** 2 + (p.y - y) ** 2 < r * r for x, y, r in keep_clear):
            continue
        out.append((p, dist))
    return out


# ------------------------------------------------------------------ small era pieces that only set dressing needs
def _m(name, color, rough=0.7, metal=0.0, bump=0.3, bump_scale=80):
    m = bpy.data.materials.get(name)
    if m is None:
        m = principled(name, color, metal=metal, rough=rough, bump=bump, bump_scale=bump_scale); m.use_fake_user = True
    return m


def firewood(loc=(0, 0, 0), seed=0, name='firewood'):
    """A stack of split olive/oak logs for the oven or the hearth."""
    rnd = random.Random(seed)
    root = link(bpy.data.objects.new(name, None)); root.location = loc
    wood = _m('firewood_bark', (0.2, 0.14, 0.09), 0.85, bump=0.8)
    for i in range(rnd.randint(7, 12)):
        row = i // 4
        bpy.ops.mesh.primitive_cylinder_add(vertices=7, radius=rnd.uniform(0.04, 0.07), depth=rnd.uniform(0.5, 0.8),
                                            location=(rnd.uniform(-0.05, 0.05), (i % 4 - 1.5) * 0.12 + row * 0.06, 0.06 + row * 0.1),
                                            rotation=(0, math.pi / 2, rnd.uniform(-0.15, 0.15)))
        o = bpy.context.object; o.name = f'{name}_{i}'; o.data.materials.append(wood); o.parent = root
    return root


def stone_pile(loc=(0, 0, 0), seed=0, name='stone_pile'):
    """A heap of fieldstones cleared from a field / ready for a wall (countryside._stone_bm)."""
    from lib import countryside
    rnd = random.Random(seed)
    bm = bmesh.new()
    for i in range(rnd.randint(8, 16)):
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0, 0.5)
        countryside._stone_bm(bm, Vector((r * math.cos(a), r * math.sin(a), 0.1 + (0.5 - r) * 0.3 * rnd.random())),
                              (rnd.uniform(0.18, 0.35), rnd.uniform(0.15, 0.3), rnd.uniform(0.1, 0.2)), rnd, rnd.uniform(0, 3))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.location = loc; o.data.materials.append(countryside.stone_material())
    for pg in o.data.polygons:
        pg.use_smooth = True
    return o


def broken_spear(loc=(0, 0, 0), seed=0, name='broken_spear'):
    """A spear shaft snapped in two, lying, or stuck slanting in the ground (after a fight)."""
    from lib import tools
    rnd = random.Random(seed)
    root = link(bpy.data.objects.new(name, None)); root.location = loc
    if rnd.random() < 0.5:                                            # stuck in the ground at a slant
        a = rnd.uniform(0, 2 * math.pi); tilt = rnd.uniform(0.3, 0.8)
        top = Vector((math.cos(a) * math.sin(tilt), math.sin(a) * math.sin(tilt), math.cos(tilt))) * rnd.uniform(1.0, 1.8)
        tools._tube(name + '_shaft', [Vector((0, 0, -0.1)), top], 0.014, tools.wood_mat(), root)
    else:                                                             # broken, lying
        for k in range(2):
            a = rnd.uniform(0, 3.1); ln = rnd.uniform(0.6, 1.2)
            d = Vector((math.cos(a), math.sin(a), 0))
            p0 = Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 0.015))
            tools._tube(f'{name}_piece{k}', [p0, p0 + d * ln], 0.014, tools.wood_mat(), root)
    return root


def fallen_shield(loc=(0, 0, 0), seed=0, name='fallen_shield'):
    """A round hoplite shield (aspis) lying face up or down: bronze-faced, painted, dented."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    prof = [(0.001, 0.09), (0.3, 0.085), (0.42, 0.05), (0.45, 0.02), (0.47, 0.03), (0.47, 0.0)]   # dished + rim
    rings = []
    for r, z in prof:
        rings.append([bm.verts.new(Vector((r * math.cos(2 * math.pi * k / 36), r * math.sin(2 * math.pi * k / 36), z))) for k in range(36)])
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(36):
            bm.faces.new((a[k], a[(k + 1) % 36], b[(k + 1) % 36], b[k]))
    for v in bm.verts:                                                # dents
        v.co.z += 0.01 * math.sin(v.co.x * 9 + seed) * math.sin(v.co.y * 7)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.location = loc
    o.rotation_euler = (rnd.choice([0, math.pi]) + rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), rnd.uniform(0, 6.3))
    o.data.materials.append(_m(f'shield_paint_{seed % 3}', [(0.3, 0.05, 0.03), (0.05, 0.04, 0.03), (0.45, 0.32, 0.12)][seed % 3], 0.5,
                               metal=0.3, bump=0.3))
    for pg in o.data.polygons:
        pg.use_smooth = True
    return o


# ------------------------------------------------------------------ kits
def _builders():
    from lib import props, market, tools, countryside
    def scan(sid):
        def f(loc, seed, name):
            from lib import scatter
            vs = scatter.load_scan(sid)
            inst = link(bpy.data.objects.new(name, None)); inst.instance_type = 'COLLECTION'
            inst.instance_collection = vs[seed % len(vs)]; inst.location = loc
            return inst
        return f
    return {
        'amphora': lambda loc, seed, name: props.amphora(loc, height=random.Random(seed).uniform(0.55, 0.75),
                                                          lean=random.Random(seed).uniform(-0.2, 0.2), seed=seed, name=name),
        'basket': lambda loc, seed, name: props.basket(loc, kind=random.Random(seed).choice(['kalathos', 'carry', 'flat']),
                                                        fill=random.Random(seed).choice([None, (0.6, 0.45, 0.18), (0.18, 0.06, 0.1)]), name=name),
        'fish_basket': lambda loc, seed, name: props.basket(loc, kind='carry', fill=(0.45, 0.48, 0.5), name=name),
        'sack': lambda loc, seed, name: market.grain_sack(Vector(loc), seed=seed, open_top=seed % 3 == 0, name=name),
        'wool_bale': lambda loc, seed, name: market.wool_bale(Vector(loc), seed=seed, name=name),
        'hydria': lambda loc, seed, name: market.hydria(loc, seed=seed, name=name),
        'firewood': lambda loc, seed, name: firewood(loc, seed, name),
        'stone_pile': lambda loc, seed, name: stone_pile(loc, seed, name),
        'rope_coil': lambda loc, seed, name: props.rope_coil(loc, name=name),
        'anchor': lambda loc, seed, name: props.stone_anchor(loc, name=name),
        'cart': lambda loc, seed, name: tools.cart(loc, load=random.Random(seed).choice(['amphorae', 'sacks', 'hay', None]), seed=seed, name=name),
        'tent': lambda loc, seed, name: props.tent(loc, name=name),
        'broken_spear': lambda loc, seed, name: broken_spear(loc, seed, name),
        'fallen_shield': lambda loc, seed, name: fallen_shield(loc, seed, name),
        'shrub': scan('shrub_01'), 'shrub2': scan('shrub_03'), 'grass': scan('grass_medium_01'),
        'rocks': scan('coast_land_rocks_02'), 'boulder': scan('boulder_01'), 'branches': scan('dry_branches_medium_01'),
        'mastic': scan('searsia_lucida'),
    }


KITS = {   # setting -> [(piece, weight, min distance m)]   (people/birds/smoke are added separately)
    'village': [('amphora', 3, 1.5), ('basket', 3, 1.5), ('sack', 2, 1.5), ('firewood', 3, 2), ('stone_pile', 2, 2),
                ('hydria', 1, 1.5), ('shrub', 3, 3), ('grass', 6, 1.5), ('mastic', 2, 4), ('cart', 0.4, 6)],
    'market': [('amphora', 5, 1.5), ('basket', 5, 1.5), ('sack', 4, 1.5), ('wool_bale', 2, 2), ('hydria', 2, 1.5),
               ('fish_basket', 2, 1.5), ('cart', 0.5, 6), ('grass', 1, 2)],
    'harbour': [('rope_coil', 3, 1.5), ('anchor', 2, 2), ('amphora', 4, 1.5), ('fish_basket', 3, 1.5), ('basket', 2, 1.5),
                ('sack', 2, 2), ('rocks', 2, 3), ('grass', 2, 2)],
    'countryside': [('grass', 8, 1.2), ('shrub', 4, 3), ('shrub2', 3, 3), ('mastic', 3, 4), ('rocks', 2, 3), ('boulder', 1, 5),
                    ('branches', 2, 2), ('stone_pile', 1, 4), ('basket', 0.5, 2)],
    'persian_camp': [('tent', 1.5, 8), ('sack', 4, 1.5), ('amphora', 3, 1.5), ('firewood', 3, 2), ('basket', 2, 1.5),
                     ('cart', 0.6, 6), ('grass', 3, 1.5), ('rocks', 1, 3)],
    'battlefield': [('broken_spear', 6, 1.2), ('fallen_shield', 3, 1.5), ('rocks', 3, 2), ('grass', 3, 1.5), ('branches', 2, 2)],
}
LIFE = {    # setting -> (people per 100 points, birds, smoke columns)
    'village': (6, 10, 2), 'market': (14, 6, 1), 'harbour': (6, 18, 0), 'countryside': (2, 14, 0),
    'persian_camp': (10, 8, 3), 'battlefield': (0, 20, 4),
}


def _prototype(kind, builder, variant, cache):
    """Build one piece at the origin ONCE, move everything it created into a hidden collection, and return that
    collection: every placement is then a light collection instance."""
    key = (kind, variant)
    if key in cache:
        return cache[key]
    before = set(bpy.data.objects)
    try:
        builder((0, 0, 0), variant, f'proto_{kind}_{variant}')
    except Exception as e:                                            # a scan missing on this machine: skip the kind
        print(f'dressing: {kind} unavailable here - {e}')
        cache[key] = None
        return None
    new = [o for o in bpy.data.objects if o not in before]
    col = bpy.data.collections.new(f'dress_{kind}_{variant}')         # NOT linked to the scene: only instances render
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    cache[key] = col
    return col


def _people(points, rnd, out):
    """Background people: low-poly stand-ins (props._proxy_mesh) in sun-faded dyes, only at 12 m and beyond
    (they read as people at that distance; close shots use real dressed characters - WS2/WS3)."""
    from lib import props
    mats = props._crew_mats()
    for i, (p, d) in enumerate(points):
        o = bpy.data.objects.new(f'dress_person_{i}', props._proxy_mesh(rnd.choice(['cloth', 'cloth', 'archer']), mats))
        out.objects.link(o)
        k = rnd.uniform(0.92, 1.05); o.location = p; o.scale = (k, k, k); o.rotation_euler.z = rnd.uniform(0, 2 * math.pi)


def dress_view(cam, ground, setting='village', amount=120, keep_clear=(), seed=0, people=True, birds=True, smoke=True,
               far=90.0):
    """Dress what `cam` sees with about `amount` pieces of the setting's kit, plus background people, birds and
    smoke. keep_clear = [(x, y, r)] around actors and their paths. Returns the collection holding the instances."""
    rnd = random.Random(seed)
    kit = KITS.get(setting, KITS['village'])
    B = _builders()
    out = bpy.data.collections.get(f'dressing_{setting}') or bpy.data.collections.new(f'dressing_{setting}')
    if out.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(out)
    pts = visible_points(cam, ground, amount, far=far, keep_clear=keep_clear, seed=seed)
    cache = {}
    total = sum(w for _, w, _ in kit)
    for i, (p, d) in enumerate(pts):
        r = rnd.uniform(0, total)
        for kind, w, dmin in kit:
            r -= w
            if r <= 0:
                break
        if d < dmin:
            continue
        col = _prototype(kind, B[kind], rnd.randint(0, 2), cache)
        if col is None:
            continue
        inst = bpy.data.objects.new(f'dress_{kind}_{i}', None)
        inst.instance_type = 'COLLECTION'; inst.instance_collection = col
        inst.location = p; inst.rotation_euler.z = rnd.uniform(0, 2 * math.pi)
        s = rnd.uniform(0.85, 1.15); inst.scale = (s, s, s)
        out.objects.link(inst)
    n_people, n_birds, n_smoke = LIFE.get(setting, (4, 8, 0))
    if people and n_people:
        far_pts = [pd for pd in visible_points(cam, ground, int(amount * n_people / 100) + 2, near=12.0, far=far,
                                               keep_clear=keep_clear, seed=seed + 1, near_bias=12.0)]
        _people(far_pts, rnd, out)
    mw = cam.matrix_world; pos = mw.translation; fwd = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
    if birds and n_birds:
        from lib import fx
        try:
            fx.bird_flock(pos + Vector((fwd.x, fwd.y, 0)).normalized() * 60, count=n_birds, radius=30, height=(15, 40), seed=seed)
        except Exception as e:
            print('dressing: birds skipped -', e)
    if smoke and n_smoke:
        from lib import fx
        for k in range(n_smoke):                                      # thin smoke from ovens / camp fires, far off
            far_p = visible_points(cam, ground, 1, near=25.0, far=far, keep_clear=keep_clear, seed=seed + 50 + k, near_bias=40.0)
            if far_p:
                try:
                    fx.smoke_column(far_p[0][0], height=rnd.uniform(18, 35), width=rnd.uniform(1.5, 3.0), density=0.06,
                                    color=(0.35, 0.33, 0.3), name=f'dress_smoke_{k}')
                except Exception as e:
                    print('dressing: smoke skipped -', e)
    return out

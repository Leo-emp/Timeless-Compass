# SCATTER: dress a set with REAL scanned plants and rocks (Poly Haven CC0 models in library/scans/<id>/).
# Each scan is appended once and kept hidden; the set gets lightweight INSTANCES of it (collection instances share
# the mesh, so 2,000 shrubs cost about as much memory as one). Placement is by code:
#   - only on ground that faces up (no shrubs on cliffs), above the waterline, outside keep-clear zones
#   - clustered like real maquis (plants grow in patches), random turn + size so nothing repeats
#   - denser and bigger near the camera (foreground depth), sparse far away
import math
import os
import random

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from lib.common import SCANS


def load_scan(asset_id, lod=1):
    """Append a scanned model and split it into its VARIANTS (Poly Haven files hold e.g. bush a, b, c, each in
    4 levels of detail LOD0..LOD3 stacked in place). Returns a list of hidden collections, one per variant, at
    level `lod` (or the nearest available). Each collection's origin = the bottom centre of that variant, so an
    instance placed at a ground point stands ON it. Cached per (asset, lod)."""
    import re
    key = f'scan_{asset_id}_L{lod}'
    found = [c for c in bpy.data.collections if c.name.startswith(key + '_')]
    if found:
        return found
    d = os.path.join(SCANS, asset_id)
    blend = next((f for f in os.listdir(d) if f.endswith('.blend')), None)
    if blend is None:                                          # Sketchfab scan (.glb): one variant, scaled to real size
        return [_load_glb_variant(asset_id, d, key)]
    with bpy.data.libraries.load(os.path.join(d, blend), link=False) as (src, dst):
        dst.objects = list(src.objects)
    groups = {}
    has_lods = any(o is not None and '_LOD' in o.name for o in dst.objects)
    for o in dst.objects:
        if o is None:
            continue
        # helper objects in some scan files are not plants (UV templates, geometry-node scatter rigs): skip them
        helper = any(t in o.name.lower() for t in ('geometry_nodes', 'geonodes_setup', 'leaf_uv', '_uv'))
        if o.type != 'MESH' or helper or (has_lods and '_LOD' not in o.name):
            bpy.data.objects.remove(o); continue
        m = re.match(r'(.*?)_LOD(\d+)$', o.name.split('.')[0])
        stem, level = (m.group(1), int(m.group(2))) if m else (o.name.split('.')[0], 0)
        groups.setdefault(stem, {})[level] = o
    # parts that belong together (e.g. tree branches + leaves of the same letter) stay one variant
    variants = {}
    for stem, levels in groups.items():
        v = re.sub(r'_(leaves|branches|trunk)', '', stem)
        variants.setdefault(v, []).append(levels)
    out = []
    for i, (v, parts) in enumerate(sorted(variants.items())):
        col = bpy.data.collections.new(f'{key}_{i}')
        chosen = []
        for levels in parts:
            pick = min(levels, key=lambda L: (abs(L - lod), L))
            chosen.append(levels[pick])
            for L, o in levels.items():
                if L != pick and o.users_collection == ():
                    bpy.data.objects.remove(o)
        for o in chosen:
            col.objects.link(o)
        pts = [o.matrix_world @ Vector(c) for o in chosen for c in o.bound_box]
        col.instance_offset = (sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts), min(p.z for p in pts))
        out.append(col)
    return out


# real-world heights (m) for Sketchfab scans, whose files come at arbitrary scale
REAL_HEIGHT = {'tree_olive_zakynthos': 6.0, 'tree_cypress': 13.0, 'tree_date_palm': 12.0, 'horse_akhalteke': 1.6,
               'horse_realistic': 1.6, 'animal_camels': 2.0, 'animal_cow': 1.4, 'animal_goat': 0.75, 'animal_sheep': 0.8,
               'animal_dog': 0.55, 'animal_seagull': 0.3, 'animal_raven_cc0': 0.35}


def _load_glb_variant(asset_id, d, key):
    """Import a .glb into a hidden collection, scaled so it stands REAL_HEIGHT[asset_id] metres tall."""
    import glob
    f = os.path.join(d, 'model.glb')
    if not os.path.exists(f):
        f = (glob.glob(os.path.join(d, '**', '*.gltf'), recursive=True) or glob.glob(os.path.join(d, '**', '*.glb'), recursive=True))[0]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f)
    new = list(set(bpy.data.objects) - before)
    col = bpy.data.collections.new(f'{key}_0')
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    bpy.context.view_layer.update()
    meshes = [o for o in new if o.type == 'MESH']
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    zmin, zmax = min(p.z for p in pts), max(p.z for p in pts)
    k = REAL_HEIGHT.get(asset_id, 1.0) / max(zmax - zmin, 1e-6)
    roots = [o for o in new if o.parent is None]
    for o in roots:
        o.scale = tuple(v * k for v in o.scale); o.location = o.location * k
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    col.instance_offset = (sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts), min(p.z for p in pts))
    return col


def _ground_tree(ground):
    dg = bpy.context.evaluated_depsgraph_get()
    return BVHTree.FromObject(ground, dg), ground.evaluated_get(dg)


def scatter(ground, scans, count, area, seed=0, size=(0.7, 1.3), min_z=0.3, max_slope_deg=35,
            clusters=40, cluster_r=6.0, keep_clear=(), near=None, near_boost=2.5, collection_name='scatter', lod=1):
    """Place `count` instances of the scans (list of asset ids, or (id, weight) pairs) on `ground`.
    area = (xmin, xmax, ymin, ymax) in world metres. keep_clear = [(x, y, radius)] (paths, stage marks, camera).
    near = (x, y): the camera position; plants get denser and a little bigger toward it."""
    rnd = random.Random(seed)
    items = [(s, 1.0) if isinstance(s, str) else s for s in scans]
    cols = []
    for sid, w in items:                                       # every variant of every scan, sharing the weight
        if not os.path.isdir(os.path.join(SCANS, sid)):        # e.g. a cloud runner without the Sketchfab token
            print(f'scatter: scan {sid} not downloaded here - skipped')
            continue
        vs = load_scan(sid, lod)
        cols += [(c, w / len(vs)) for c in vs]
    if not cols:
        return bpy.data.collections.get(collection_name) or bpy.data.collections.new(collection_name)
    total_w = sum(w for _, w in cols)
    tree, _ = _ground_tree(ground)
    out = bpy.data.collections.get(collection_name) or bpy.data.collections.new(collection_name)
    if out.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(out)
    x0, x1, y0, y1 = area
    centres = [(rnd.uniform(x0, x1), rnd.uniform(y0, y1)) for _ in range(clusters)]
    cos_max = math.cos(math.radians(max_slope_deg))
    placed, tries = 0, 0
    while placed < count and tries < count * 20:
        tries += 1
        cx, cy = rnd.choice(centres)
        x, y = cx + rnd.gauss(0, cluster_r), cy + rnd.gauss(0, cluster_r)
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            continue
        if any((x - kx) ** 2 + (y - ky) ** 2 < kr ** 2 for kx, ky, kr in keep_clear):
            continue
        k = 1.0
        if near is not None:                                   # thin out far away, keep it rich near the camera
            dist = math.hypot(x - near[0], y - near[1])
            k = near_boost / (1.0 + dist / 25.0)
            if rnd.random() > min(1.0, k):
                continue
        hit = tree.ray_cast(Vector((x, y, 5000.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        loc, normal = hit[0], hit[1]
        if loc.z < min_z or normal.z < cos_max:
            continue
        r = rnd.uniform(0, total_w)
        for col, w in cols:
            r -= w
            if r <= 0:
                break
        inst = bpy.data.objects.new(f'{col.name}_{placed}', None)
        inst.instance_type = 'COLLECTION'; inst.instance_collection = col
        inst.location = loc
        inst.rotation_euler = (normal.y * -0.4, normal.x * 0.4, rnd.uniform(0, 2 * math.pi))   # lean with the slope a little
        sc = rnd.uniform(*size) * (1.0 + 0.15 * min(k, 2.0))
        inst.scale = (sc, sc, sc * rnd.uniform(0.85, 1.15))
        out.objects.link(inst)
        placed += 1
    return out


def scan_material(name, scan, tint=(1, 1, 1), tiles=20.0, disp=0.0, rough=(0.6, 0.95), break_tiling=True):
    """Ground / rock / wall material from a scanned texture set (colour, normal, roughness, optional height),
    mapped by world-space coordinates so it never stretches on big terrain."""
    d = os.path.join(SCANS, scan)
    def img(suffix, color=True):
        f = next((x for x in os.listdir(d) if f'_{suffix}_' in x), None)
        if f is None:
            return None
        im = bpy.data.images.load(os.path.join(d, f), check_existing=True)
        if not color:
            im.colorspace_settings.name = 'Non-Color'
        return im
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; L = nt.links.new
    b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / tiles, 1 / tiles, 1 / tiles)
    L(tc.outputs['Object'], mp.inputs['Vector'])
    # TILING BREAK: on big surfaces a repeating scan shows as wallpaper. Sample every map twice - at the normal scale
    # and at a second scale + rotation - and blend the two with a big soft noise mask, so no repeat can be seen.
    mp2 = nt.nodes.new('ShaderNodeMapping'); mp2.inputs['Scale'].default_value = (0.43 / tiles,) * 3
    mp2.inputs['Rotation'].default_value = (0.0, 0.0, 0.65); mp2.inputs['Location'].default_value = (13.7, 5.3, 0.0)
    L(tc.outputs['Object'], mp2.inputs['Vector'])
    mask = nt.nodes.new('ShaderNodeTexNoise'); mask.inputs['Scale'].default_value = 1.0 / max(tiles * 4.0, 1.0)
    mask.inputs['Detail'].default_value = 3.0
    L(tc.outputs['Object'], mask.inputs['Vector'])
    soft = nt.nodes.new('ShaderNodeMapRange'); soft.inputs['From Min'].default_value = 0.38; soft.inputs['From Max'].default_value = 0.62
    L(mask.outputs['Fac'], soft.inputs['Value'])
    class _Out:                                               # mimics an image node's outputs (so the code below is unchanged)
        def __init__(self, sock): self.outputs = {'Color': sock}
    def tex(image):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = image; t.projection = 'BOX'; t.projection_blend = 0.25
        L(mp.outputs['Vector'], t.inputs['Vector'])
        if not break_tiling:
            return t
        t2 = nt.nodes.new('ShaderNodeTexImage'); t2.image = image; t2.projection = 'BOX'; t2.projection_blend = 0.25
        L(mp2.outputs['Vector'], t2.inputs['Vector'])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
        L(soft.outputs['Result'], mx.inputs['Factor']); L(t.outputs['Color'], mx.inputs['A']); L(t2.outputs['Color'], mx.inputs['B'])
        return _Out(mx.outputs['Result'])
    diff = tex(img('diff'))
    tint_n = nt.nodes.new('ShaderNodeMix'); tint_n.data_type = 'RGBA'; tint_n.blend_type = 'MULTIPLY'
    tint_n.inputs['Factor'].default_value = 1.0; tint_n.inputs['B'].default_value = (*tint, 1)
    L(diff.outputs['Color'], tint_n.inputs['A']); L(tint_n.outputs['Result'], b.inputs['Base Color'])
    r_im = img('rough', False)
    if r_im:
        rr = nt.nodes.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = rough[0]; rr.inputs['To Max'].default_value = rough[1]
        L(tex(r_im).outputs['Color'], rr.inputs['Value']); L(rr.outputs['Result'], b.inputs['Roughness'])
    n_im = img('nor_gl', False)
    if n_im:
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 1.0
        L(tex(n_im).outputs['Color'], nm.inputs['Color']); L(nm.outputs['Normal'], b.inputs['Normal'])
    h_im = img('disp', False)
    if h_im and disp:                                           # real relief (Cycles displacement + bump)
        m.displacement_method = 'BOTH'
        dn = nt.nodes.new('ShaderNodeDisplacement'); dn.inputs['Scale'].default_value = disp; dn.inputs['Midlevel'].default_value = 0.5
        L(tex(h_im).outputs['Color'], dn.inputs['Height'])
        L(dn.outputs['Displacement'], nt.nodes['Material Output'].inputs['Displacement'])
    b.inputs['Specular IOR Level'].default_value = 0.35
    return m

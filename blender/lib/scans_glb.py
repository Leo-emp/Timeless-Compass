# SCANS_GLB: load the Sketchfab museum scans (library/scans/<id>/model.glb) into a scene at REAL size.
#
# Why this file exists (the owner is learning, so here is the whole story):
#   Sketchfab gives every model as one .glb file (binary glTF: meshes + textures + bones + animations in one file).
#   Three things are wrong with them straight out of the box:
#     1. SIZE. Each uploader uses their own units. The Cleveland neck amphora arrives ~29 m tall (centimetres read as
#        metres, then scaled by 1/60), the Met krater ~1 m. A 40 cm vase must be 0.40 m in our scene, or it will look
#        like a toy or a building next to a 1.75 m human.  -> we measure the model and scale it to the MUSEUM size.
#     2. PLACEMENT. The pivot (origin) is somewhere in the middle of the pot, so placing it "at" a ground point sinks
#        half of it into the ground.  -> we move the geometry so the origin is the BOTTOM CENTRE (stands on a point).
#     3. MATERIALS. Museum scans use the old "specular-glossiness" glTF material or no roughness map at all, which in
#        Cycles comes out as plastic-shiny or chrome-like.  -> we re-tune every material by what the object is made
#        of (fired clay with glossy black slip, bronze, horse hide...).
#
# The museum sizes and dates below come from the museums' own open-access records (Cleveland Museum of Art open
# access API, The Met collection API), looked up 2026-11-19. They are facts about the real objects, so they are safe
# to use (rule r9: we design from museum pieces).
#
# Usage inside a Blender scene script:
#   from lib import scans_glb
#   pot = scans_glb.load_glb('amphora_neck_cleveland')             # real size from KNOWN, one object
#   pot.location = (1.0, 2.0, 0.0)                                 # stands ON that point
#   cup = scans_glb.load_glb('kylix_cleveland', width_m=0.296)     # or give a size yourself
#   horse = scans_glb.load_glb('horse_akhalteke')                  # rigged: returns the root empty of the rig
import json
import math
import os

import bpy
from mathutils import Matrix, Vector

from lib.common import SCANS

# ------------------------------------------------------------------ real sizes + what each scan is made of
# 'size': which measurement the museum gives ('height' = overall height, 'width' = widest diameter, e.g. a cup).
# 'kind': picks the material fix in _fix_material().
# 'rot': extra rotation (degrees, x/y/z) when the uploader left the object lying on its side.
KNOWN = {
    # Attic black-figure amphora (type B), men and horses, c. 540 BC. Cleveland 1923.645. Overall 40.6 cm.
    'amphora_blackfigure_cleveland': {'size': ('height', 0.406), 'kind': 'ceramic'},
    # Attic black-figure neck-amphora, Painter of Berlin 1899, 515-510 BC. Cleveland 1970.16. H 39.8 cm, D 29 cm.
    'amphora_neck_cleveland': {'size': ('height', 0.398), 'kind': 'ceramic'},
    # Attic red-figure kylix (drinking cup) by Douris, c. 480 BC. Cleveland 1915.718. Diameter 29.6 cm (with handles).
    'kylix_cleveland': {'size': ('width', 0.296), 'kind': 'ceramic'},
    # Attic amphora type A, Rycroft Painter, c. 510 BC. Met 247236. H 51.1 cm.
    'amphora_terracotta_met': {'size': ('height', 0.511), 'kind': 'ceramic'},
    # South Italian (Lucanian) bell-krater, Pisticci Painter, c. 430-410 BC. Met 246575. H 31.3 cm.
    # NOTE: 50 years too late and from Italy -> not for 480 BC Greece (see library/props/krater_bell_met.json).
    'krater_bell_met': {'size': ('height', 0.313), 'kind': 'ceramic'},
    # Corinthian helmet, Greece, 500-475 BC (museum says "or modern"). Cleveland 1926.54. Overall 21.5 cm.
    'helmet_corinthian_cleveland': {'size': ('height', 0.215), 'kind': 'bronze'},
    # Akhal-Teke stallion (CC-BY, Animal Animator). Ancient Greek/Persian horses were SMALL: about 1.35-1.45 m at
    # the withers (horse skeletons from Greek sites, Parthenon frieze proportions), so we scale it to 1.42 m at the
    # withers ('withers' = the top of the shoulders, measured on the spine bone + the skin above it, in rest pose).
    'horse_akhalteke': {'size': ('withers', 1.42), 'kind': 'organic', 'withers_bone': 'DEF-spine_03', 'skin': 0.07},
}

# Cache: one hidden "master" object per scan. Every further load_glb() of the same scan returns a cheap copy that
# SHARES the mesh + materials (like scatter.py's instances) - 30 amphorae cost the memory of one.
_MASTERS = {}


def asset_info(asset_id):
    """The scan's asset.json (licence + credit line). Every prop manifest copies the credit from here."""
    with open(os.path.join(SCANS, asset_id, 'asset.json'), encoding='utf-8') as f:
        return json.load(f)


def credit(asset_id):
    return asset_info(asset_id).get('credit', '')


# ------------------------------------------------------------------ import helpers
def _import(path):
    """Run Blender's glTF importer and return the NEW objects it made (everything that wasn't there before)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path, import_shading='NORMALS', bone_heuristic='TEMPERANCE',
                              import_select_created_objects=True)
    return [o for o in bpy.data.objects if o not in before]


def _world_bbox(objs):
    """Corners of all meshes in WORLD space (after parents, scales, rotations, and bones' rest pose)."""
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in objs:
        if o.type != 'MESH':
            continue
        e = o.evaluated_get(dg)
        pts += [e.matrix_world @ Vector(c) for c in e.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def _scale_factor(lo, hi, height_m, width_m):
    dims = hi - lo
    if height_m:
        return height_m / dims.z
    if width_m:
        return width_m / max(dims.x, dims.y)
    return 1.0


# ------------------------------------------------------------------ materials
def _principled_nodes(mat):
    return [n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'] if mat and mat.use_nodes else []


def _remap(nt, bsdf, socket_name, lo, hi):
    """Squeeze whatever feeds a socket (a texture or a fixed number) into the range lo..hi.
    Used on Roughness: scans often say 0 (mirror) because of the old glossiness maps."""
    sock = bsdf.inputs[socket_name]
    if sock.is_linked:
        src = sock.links[0].from_socket
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['To Min'].default_value = lo; mr.inputs['To Max'].default_value = hi
        nt.links.new(src, mr.inputs['Value']); nt.links.new(mr.outputs['Result'], sock)
    else:
        sock.default_value = min(max(sock.default_value, lo), hi)


def _set_colorspaces(nt):
    """Colour photos are sRGB; normal/roughness/metal maps are DATA (Non-Color). A wrong colour space makes
    normal maps bend the light the wrong way and roughness maps too strong."""
    for n in nt.nodes:
        if n.type != 'TEX_IMAGE' or not n.image:
            continue
        data = False
        for l in n.outputs['Color'].links:
            to = l.to_node
            if to.type == 'NORMAL_MAP' or (to.type == 'BSDF_PRINCIPLED' and l.to_socket.name in ('Roughness', 'Metallic')) \
                    or to.type in ('SEPARATE_COLOR', 'SEPRGB', 'MAP_RANGE', 'MATH', 'INVERT'):
                data = True
        n.image.colorspace_settings.name = 'Non-Color' if data else 'sRGB'


def _fix_material(mat, kind):
    """Make a scanned material render like the real substance in Cycles."""
    nt = mat.node_tree
    _set_colorspaces(nt)
    for b in _principled_nodes(mat):
        # The specular-glossiness importer sets IOR = 1000 (to fake "specular colour = 1"): that turns the surface
        # into a MIRROR - the pots rendered white/silver from reflecting the room. Real glaze/clay/patina ~ 1.5.
        if b.inputs['IOR'].default_value > 3.0:
            b.inputs['IOR'].default_value = 1.5
        if kind == 'ceramic':
            # Fired clay + black "gloss" slip: never metal, satin sheen (the slip shines a little, the clay is matte).
            b.inputs['Metallic'].default_value = 0.0
            if b.inputs['Metallic'].is_linked:
                nt.links.remove(b.inputs['Metallic'].links[0])
            _remap(nt, b, 'Roughness', 0.38, 0.72)
            b.inputs['Specular IOR Level'].default_value = 0.45
            # The specular-glossiness import sets a white Specular Tint -> a plastic look. Neutral = no tint.
            if not b.inputs['Specular Tint'].is_linked:
                b.inputs['Specular Tint'].default_value = (1, 1, 1, 1)
            else:
                nt.links.remove(b.inputs['Specular Tint'].links[0]); b.inputs['Specular Tint'].default_value = (1, 1, 1, 1)
        elif kind == 'bronze':
            # The photo texture already shows the green-brown patina, so only part metal: patina is not shiny metal.
            if b.inputs['Metallic'].is_linked:
                nt.links.remove(b.inputs['Metallic'].links[0])
            b.inputs['Metallic'].default_value = 0.55
            _remap(nt, b, 'Roughness', 0.35, 0.65)
            if b.inputs['Specular Tint'].is_linked:
                nt.links.remove(b.inputs['Specular Tint'].links[0])
            b.inputs['Specular Tint'].default_value = (1, 1, 1, 1)
        elif kind == 'organic':
            # Hide/hair/eyes: keep the artist's material, only stop mirror-like roughness on the coat.
            if 'eye' not in mat.name.lower():
                _remap(nt, b, 'Roughness', 0.35, 0.9)
    # Alpha-masked cards (the horse's mane/tail) must cut out in Cycles too: it reads the Alpha socket directly,
    # so nothing to do there; for Eevee previews use hashed transparency.
    if hasattr(mat, 'surface_render_method'):
        mat.surface_render_method = 'DITHERED'
    mat.use_fake_user = True                # MakeHuman's loader purges "unused" materials (see blender/README.md)


# ------------------------------------------------------------------ the loader
def _bake_static(asset_id, new, s, rot):
    """Static scan: bake every transform into the vertices, join all meshes into ONE object, origin = bottom centre.
    (Scale in vertex coordinates, not object scale - lesson in blender/README.md.)"""
    meshes = [o for o in new if o.type == 'MESH']
    R = Matrix.Identity(4)
    if rot:
        R = (Matrix.Rotation(math.radians(rot[2]), 4, 'Z') @ Matrix.Rotation(math.radians(rot[1]), 4, 'Y')
             @ Matrix.Rotation(math.radians(rot[0]), 4, 'X'))
    for o in meshes:
        o.data = o.data.copy() if o.data.users > 1 else o.data
        o.data.transform(R @ o.matrix_world)      # world shape straight into the mesh
        o.parent = None
        o.matrix_world = Matrix.Identity(4)
    for o in new:                                  # the Sketchfab helper empties are no longer needed
        if o.type != 'MESH':
            bpy.data.objects.remove(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = f'scan_{asset_id}'
    lo, hi = _world_bbox([ob])
    s = s(lo, hi) if callable(s) else s
    base = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    ob.data.transform(Matrix.Scale(s, 4) @ Matrix.Translation(-base))   # bottom centre -> origin, then real size
    ob.data.update()
    return ob


def _master(asset_id, height_m, width_m, rot):
    key = (asset_id, height_m, width_m)
    if key in _MASTERS and _MASTERS[key].name in bpy.data.objects:
        return _MASTERS[key]
    info = KNOWN.get(asset_id, {})
    if height_m is None and width_m is None and 'size' in info:
        which, val = info['size']
        height_m, width_m = (val, None) if which in ('height', 'withers') else (None, val)
    rot = rot if rot is not None else info.get('rot')
    new = _import(os.path.join(SCANS, asset_id, 'model.glb'))
    for o in new:
        for slot in getattr(o, 'material_slots', []):
            if slot.material:
                _fix_material(slot.material, info.get('kind', 'ceramic'))
    rig = next((o for o in new if o.type == 'ARMATURE'), None)
    if rig is None:
        ob = _bake_static(asset_id, new, lambda lo, hi: _scale_factor(lo, hi, height_m, width_m), rot)
    else:
        ob = _rigged_root(asset_id, new, height_m, width_m, info)
    _MASTERS[key] = ob
    return ob


def _rigged_root(asset_id, new, height_m, width_m, info=None):
    """Rigged + animated scan (the horse): bones and animations must keep working, so we DON'T bake. Instead we put
    one new empty on top of the whole hierarchy and scale/move only that empty."""
    tops = [o for o in new if o.parent is None]
    root = bpy.data.objects.new(f'scan_{asset_id}', None)
    bpy.context.scene.collection.objects.link(root)
    for o in tops:
        o.parent = root
    # measure in REST pose (bones straight, as modelled) - the first animation frame may have the head down
    rig = next(o for o in new if o.type == 'ARMATURE')
    rig.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    lo, hi = _world_bbox(new)
    info = info or {}
    if info.get('size', ('',))[0] == 'withers' and height_m:
        b = next(b for b in rig.data.bones if b.name.startswith(info['withers_bone']))
        top = (rig.matrix_world @ b.head_local).z - lo.z + info.get('skin', 0.0)
        s = height_m / top                            # scale so the withers stand at the wanted height
    else:
        s = _scale_factor(lo, hi, height_m, width_m)
    rig.data.pose_position = 'POSE'
    base = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    for o in tops:                                   # shift the children so the hooves stand on the root's origin
        o.location -= base
    root.scale = (s, s, s)
    root['scan_id'] = asset_id
    return root


def load_glb(asset_id, height_m=None, width_m=None, loc=(0, 0, 0), rot_z_deg=0.0, rot=None, copy=True):
    """Load a Sketchfab scan at real size, standing on `loc`, turned rot_z_deg around the vertical.
    Static scans -> ONE mesh object (origin = bottom centre). The first load is the hidden master; with copy=True
    (default) you get a copy that shares the mesh (cheap). Rigged scans (horse) -> the root EMPTY of the rig
    (not copied: every horse gets its own rig so it can run its own animation)."""
    m = _master(asset_id, height_m, width_m, rot)
    if m.type == 'EMPTY':                            # rigged: hand out the master itself the first time
        if m.get('_handed_out'):
            _MASTERS.pop((asset_id, height_m, width_m), None)
            m = _master(asset_id, height_m, width_m, rot)
        m['_handed_out'] = True
        m.location = loc; m.rotation_euler.z = math.radians(rot_z_deg)
        return m
    if not copy:
        m.location = loc; m.rotation_euler.z = math.radians(rot_z_deg)
        return m
    m.hide_render = True; m.hide_viewport = True     # the master stays hidden; copies go in the shot
    ob = m.copy()                                    # .copy() shares m.data (the mesh) - no extra memory
    ob.hide_render = False; ob.hide_viewport = False
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc; ob.rotation_euler = (0, 0, math.radians(rot_z_deg))
    return ob


# ------------------------------------------------------------------ animations of rigged scans
def rig_of(root):
    return next((o for o in root.children_recursive if o.type == 'ARMATURE'), None)


def clips(root):
    """Names of the animations that came with the scan (horse: 'Chewing', 'Run_Gallop', 'Trot')."""
    rig = rig_of(root)
    names = set()
    ad = rig.animation_data if rig else None
    if ad:
        if ad.action:
            names.add(ad.action.name)
        for tr in ad.nla_tracks:
            for st in tr.strips:
                if st.action:
                    names.add(st.action.name)
    return sorted(names)


def play(root, clip, frame_start=1, speed=1.0, repeat=10):
    """Play one of the scan's own animations on its rig, looping `repeat` times from frame_start.
    The glTF importer stores each animation as an Action (often as muted NLA strips); we mute everything and lay one
    looping NLA strip of the wanted action. Blender 4.4+ actions have 'slots' - the strip picks the right one."""
    rig = rig_of(root)
    act = next((a for a in bpy.data.actions if a.name == clip or a.name.startswith(clip + '_') or clip in a.name), None)
    if rig is None or act is None:
        raise ValueError(f'no clip {clip!r}; have {clips(root)}')
    ad = rig.animation_data or rig.animation_data_create()
    ad.action = None
    for tr in list(ad.nla_tracks):
        ad.nla_tracks.remove(tr)
    tr = ad.nla_tracks.new(); tr.name = clip
    st = tr.strips.new(clip, int(frame_start), act)
    st.repeat = repeat
    st.scale = 1.0 / max(speed, 1e-3)
    if hasattr(st, 'action_slot') and getattr(act, 'slots', None) and len(act.slots):
        try:
            st.action_slot = act.slots[0]
        except Exception:
            pass
    return st

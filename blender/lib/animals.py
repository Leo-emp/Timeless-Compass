# ANIMALS: every farm, market and war animal at its REAL size, facing the same way, playing its own clips, moving
# along paths without foot-sliding, plus herd / flock scatter helpers (Session G, WS18).
#
# How it works (the owner is learning, so here is the whole story):
#   1. CATALOGUE below says, per animal: which Sketchfab scan (library/scans/<id>, credits in its asset.json and in
#      library/animals.json), its real size (with the source), and which of the scan's own animations is its
#      walk / trot / idle / eat ... clip.
#   2. load(kind) imports the scan and puts TWO empties on top of it:
#         root  - where the animal stands + which way it faces (you move / turn / animate THIS one)
#         fix   - the scan's own correction: turned so the HEAD points to -Y (every uploader faces a different way),
#                 scaled so the WITHERS (top of the shoulders) are at the real height, feet on the ground.
#      Same convention as the horse scan and tools.cart: heading 0 = facing -Y.
#   3. play(root, 'walk') lays a looping NLA strip of that clip on the rig (phase + speed per animal, so a herd is
#      never in step).
#   4. walk_path(root, points, speed) moves the root along the ground and plays the gait at the RIGHT playback speed:
#      clip_speed() measures how fast the clip's feet push backwards while they're on the ground (= how fast the
#      animal would really travel), so playback = wanted speed / clip speed -> no ice-skating hooves.
#   5. herd() / flock_move() / poultry() build a few unique ACTORS (own rig, own phase) and scatter cheap
#      INSTANCES of them (collection instances: 40 sheep cost the memory of 4).
#
# Real sizes (withers height unless noted) - sources:
#   donkey 1.05 m  - ancient Mediterranean donkeys ~1.0-1.1 m (bone measurements, e.g. Tell es-Safi/Gath donkeys;
#                    Greek vase donkeys are small next to their drivers); mule 1.35 m (Roman mules 1.3-1.45 m)
#   ox 1.2 m       - Iron Age / Classical cattle were small: ~1.1-1.25 m (faunal studies of Greek sanctuaries);
#                    zebu-type humped cattle in Egypt (New Kingdom tomb paintings), Mesopotamia, Persia, India
#   goat 0.7, sheep 0.65, dog 0.55 (Laconian / Molossian hounds on vases ~ knee-to-thigh high), pig 0.7 (ancient
#                    pigs were small, dark, bristly and boar-like - Attic vases, Roman reliefs - so the boar scan IS
#                    the right look), chicken 0.42 tall (hen), pigeon 0.21 tall, cat 0.30 tall (to the ears)
#   dromedary 1.9 m at the shoulder (hump ~2.1 m)
#   elephant: North African forest elephant (Carthage, Ptolemies) ~2.5 m - Polybius 5.84: they were SMALLER than the
#             Indian ones; Indian (Seleucid, Pyrrhus) ~2.8-3.0 m. Our scan is an African savanna bull: the big ears
#             fit Carthage / Ptolemaic coins; for Seleucid Indian elephants it is only a stand-in (ears too big).
#   horse: Session E's horse_akhalteke at 1.42 m (scans_glb) - use cavalry.py / scans_glb for horses.
import json
import math
import os
import random

import bpy
from mathutils import Matrix, Vector

from lib import scans_glb
from lib.common import SCANS, link

FPS = 24

# ------------------------------------------------------------------ the catalogue
# scan      library/scans/<id>
# size      ('withers', m, shoulder_bone)  or  ('height', m)   (measured in the scan's rest pose)
# head      bone whose position tells which way the animal faces (None + 'front' for unrigged scans)
# front     for unrigged scans: the axis the head points along in the file ('+X', '-Y', ...)
# clips     our names -> the scan's action names
# foot      a foot bone for clip_speed(); speeds = fallback travel speed (m/s at playback 1.0) per gait
# drop      object-name prefixes to delete after import (props, duplicate meshes, the roasted chicken...)
# era       where/when it fits (for the agent picking animals for a scene)
CATALOGUE = {
    'donkey': {
        'scan': 'animal_donkey', 'size': ('withers', 1.05, 'L_Clavicle_016'), 'head': 'Head_023',
        'clips': {'idle': 'H_Idle_01', 'look': 'H_Idle03_Look', 'shake': 'H_Idle_02_HeadShake', 'walk': 'H_Walk',
                  'trot': 'H_Trot', 'canter': 'H_Canter', 'gallop': 'H_Gallop', 'eat': 'H_Eat', 'drink': 'H_Drink',
                  'bray': 'H_Neigh', 'sleep': 'H_Sleep_Loop'},
        'foot': 'L_Foot_06', 'speeds': {'walk': 1.2, 'trot': 2.6, 'canter': 4.5, 'gallop': 8.0},
        'drop_mats': ('Saddle',),                       # a modern leather riding saddle: wrong for every era we film
        'era': 'all (Egypt 3000 BC onward, Greece, Rome, medieval)'},
    'mule': {
        'scan': 'animal_donkey', 'size': ('withers', 1.35, 'L_Clavicle_016'), 'head': 'Head_023', 'same_as': 'donkey',
        'era': 'Greece, Rome (army baggage: ~1 mule per 8 legionaries), medieval'},
    'ox': {
        'scan': 'animal_zebu_bull', 'size': ('withers', 1.2, 'Quadruped_Skeleton_LShoulder_022'), 'head': 'Head',
        'clips': {'idle': 'Base Layer.001', 'idle2': 'Base Layer.002', 'walk': 'Base Layer.003', 'eat': 'Base Layer.004'},
        'foot': 'LFootBone1', 'speeds': {'walk': 0.9},
        'era': 'humped zebu: Egypt, Mesopotamia, Persia, India; Greek/Roman oxen were humpless (stand-in)'},
    'goat': {
        'scan': 'animal_goat', 'size': ('withers', 0.7, 'spine_03.x'), 'head': 'head.x',
        'clips': {'idle': 'rigAction'}, 'speeds': {'walk': 0.8}, 'era': 'all'},
    'sheep': {
        'scan': 'animal_sheep', 'size': ('height', 0.95), 'head': None, 'front': '+X',
        'clips': {'idle': 'GltfAnimation 0'}, 'speeds': {'walk': 0.7}, 'era': 'all'},
    'dog': {
        # realistic Labrador-type body (ItsKrish7/kenchoo scans are the only realistic rigged dogs on Sketchfab under
        # CC-BY); its one clip is an idle (sniff, look round). Ancient hounds were this size and build (Laconian /
        # Molossian dogs on Attic vases, the Jennings Dog = Roman copy of a Molossian). TROT is procedural (gait()).
        'scan': 'animal_dog_run', 'size': ('withers', 0.55, 'FrontShoulder.L'), 'head': 'Head',
        'clips': {'idle': 'Animation'}, 'speeds': {},
        'legs': {'FL': ('FrontUpperLeg.L', 'FrontLowerLeg.L'), 'FR': ('FrontUpperLeg.R', 'FrontLowerLeg.R'),
                 'BL': ('BackUpperLeg.L', 'BackLowerLeg.L'), 'BR': ('BackUpperLeg.R', 'BackLowerLeg.R')},
        'leg_len': 0.42, 'era': 'all'},
    'dog_static': {
        'scan': 'animal_dog', 'size': ('height', 0.72), 'head': None, 'front': '-Y', 'clips': {}, 'era': 'all'},
    'hound': {
        'scan': 'animal_hound', 'size': ('withers', 0.6, 'shoulder.L'), 'head': 'nose',
        'clips': {'idle': 'IDLE', 'eat': 'eating', 'growl': 'RRAR', 'sleep': 'SLEEP'}, 'speeds': {},
        'era': 'all - wolf-like hound (Laconian / Molossian type on Greek vases)'},
    'pig': {
        'scan': 'animal_boar', 'size': ('withers', 0.7, 'BOAR__L_Clavicle_014'), 'head': 'BOAR__Head_019',
        'clips': {'idle': 'idle', 'run': 'run', 'walk': 'run'}, 'foot': 'BOAR__L_Foot_08', 'speeds': {'run': 4.0, 'walk': 4.0},
        'era': 'all - dark bristly ancient pig'},
    'chicken': {
        'scan': 'animal_chicken', 'size': ('height', 0.42), 'head': 'head', 'drop': ('chicken_roasted', 'GLTF_created_1'),
        'clips': {'idle': 'idle01', 'peck': 'peck_idle2', 'walk': 'walk01', 'run': 'run01', 'flap': 'run01flap',
                  'scared': 'chicken_scared01', 'sit': 'chicken_squat_cycle01'},
        'foot': 'foot_L', 'speeds': {'walk': 0.45, 'run': 2.5},
        'era': 'Persia + Greece from c. 600 BC ("the Persian bird"), Rome, medieval; NOT New Kingdom Egypt farms'},
    'pigeon': {
        'scan': 'animal_pigeon', 'size': ('height', 0.21), 'head': 'Chicken_Head_JawSHJnt',
        'clips': {'idle': 'Animation', 'walk': 'Animation'}, 'speeds': {'walk': 0.3}, 'era': 'all (rock dove)'},
    'cat': {
        'scan': 'animal_cat', 'size': ('height', 0.30), 'head': None, 'front': '+X', 'clips': {},
        'era': 'Egypt (sacred, everywhere), Greece/Rome from c. 500 BC (rarer)'},
    'camel': {
        'scan': 'animal_camel_saddled', 'size': ('withers', 1.9, 'Sholder_L'), 'head': 'Head_018',
        'clips': {'idle': 'Armature|Idle_01', 'idle2': 'Armature|Idle_02', 'walk': 'Armature|WalkCycle'},
        'foot': 'FrontFoot_L', 'speeds': {'walk': 1.3},
        'era': 'Persia (Cyrus at Sardis, Hdt. 1.80), Arabia, Roman East, caravans; NOT Pharaonic Egypt'},
    'elephant': {
        'scan': 'animal_elephant_african', 'size': ('withers', 2.5, 'DEF-shoulder.L'), 'head': 'DEF-head',
        'clips': {'idle': '01_Idle', 'walk': '02_Walk', 'run': '03_Run', 'eat': '04_Eating', 'attack': '05_Attack'},
        'foot': 'DEF-f_foot.L', 'speeds': {'walk': 1.5, 'run': 5.0},
        'era': 'Carthage (Hannibal 218 BC), Ptolemies, Hellenistic kingdoms (Indian ones bigger: size 2.9)'},
    'horse': {
        # Session E's horse (scans_glb KNOWN: 1.42 m withers, Akhal-Teke by Animal Animator, CC-BY). Loaded through
        # cavalry.horse() so props.horse_tack works on it; listed here so play() / clip_speed() / walk_path() work.
        'scan': 'horse_akhalteke', 'size': ('withers', 1.42, 'DEF-scapula.L'), 'head': 'DEF-head',
        'clips': {'idle': 'Chewing', 'trot': 'Trot', 'gallop': 'Run_Gallop'}, 'foot': 'AUTO',
        'speeds': {'trot': 3.6, 'gallop': 11.0}, 'era': 'all'},
    'raven': {
        'scan': 'animal_raven_cc0', 'size': ('height', 0.28), 'head': None, 'front': '-Y', 'clips': {},
        'era': 'battlefields, all eras'},
}


def spec(kind):
    s = dict(CATALOGUE[kind])
    if 'same_as' in s:
        base = dict(CATALOGUE[s['same_as']]); base.update({k: v for k, v in s.items() if k != 'same_as'}); s = base
    return s


def credits(kinds):
    """CC-BY credit lines for every animal used in a video (goes into the YouTube description)."""
    out = []
    for k in kinds:
        c = scans_glb.credit(spec(k)['scan'])
        if c and c not in out:
            out.append(c)
    return out


# ------------------------------------------------------------------ loading
def _bone(rig, name):
    """Find a bone by name or prefix (the glTF importer appends _NN numbers: 'Head_023', 'DEF-head_56')."""
    if rig is None or not name:
        return None
    for b in rig.data.bones:
        if b.name == name:
            return b
    for b in rig.data.bones:
        if b.name.startswith(name) or name in b.name:
            return b
    return None


def _eval_points(meshes, step=1):
    """World positions of the DEFORMED vertices (after the rig poses the mesh) - bound boxes can lag behind bones."""
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for m in meshes:
        e = m.evaluated_get(dg); me = e.to_mesh(); mw = e.matrix_world
        vs = me.vertices; pts += [mw @ vs[i].co for i in range(0, len(vs), step)]
        e.to_mesh_clear()
    return pts


def _mesh_bbox(meshes):
    pts = _eval_points(meshes, step=3)
    if not pts:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


_AXIS = {'+X': Vector((1, 0, 0)), '-X': Vector((-1, 0, 0)), '+Y': Vector((0, 1, 0)), '-Y': Vector((0, -1, 0))}


def load(kind, loc=(0, 0, 0), heading_deg=0.0, name=None):
    """Import one animal at real size, standing on `loc`, facing heading_deg (0 = -Y). Returns the ROOT empty
    (custom props: kind, rig = armature name, fix = correction empty). Missing scan -> a placeholder empty."""
    s = spec(kind)
    path = os.path.join(SCANS, s['scan'], 'model.glb')
    name = name or kind
    root = link(bpy.data.objects.new(name, None))
    root['kind'] = kind
    if not os.path.exists(path):
        print(f'WARNING animals: {s["scan"]} not on this machine - placeholder used for {kind}')
        root.location = loc; root.rotation_euler.z = math.radians(heading_deg)
        return root
    acts_before = set(a.name for a in bpy.data.actions)
    new = scans_glb._import(path)
    own_actions = [a.name for a in bpy.data.actions if a.name not in acts_before]
    # remove junk the uploaders left in (a second model, helper boxes, the roasted chicken)
    junk = set()
    for o in new:
        mats = [m.name for m in getattr(getattr(o, 'data', None), 'materials', [])] if o.type == 'MESH' else []
        if any(o.name.startswith(p) for p in s.get('drop', ())) or o.name.startswith('Cube_Box') or                 any(m.startswith(dm) for m in mats for dm in s.get('drop_mats', ())):
            junk.add(o.name); junk.update(c.name for c in o.children_recursive)
    keep = [o.name for o in new if o.name not in junk]
    for n in junk:
        if n in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[n])
    new = [bpy.data.objects[n] for n in keep]
    for o in new:
        for slot in getattr(o, 'material_slots', []):
            if slot.material:
                scans_glb._fix_material(slot.material, 'organic')
    rigs = [o for o in new if o.type == 'ARMATURE']
    rig = rigs[0] if rigs else None
    slot_id = ''
    if rig:
        # remember WHICH action slot the importer gave this rig: glTF actions hold one slot per animated node
        # (the rig AND helper empties); giving the rig a helper's slot tips the animal over / makes it float
        ad = rig.animation_data
        if ad:
            sl = getattr(ad, 'action_slot', None)
            if sl is None:
                for tr in ad.nla_tracks:
                    for st in tr.strips:
                        if getattr(st, 'action_slot', None) is not None:
                            sl = st.action_slot; break
                    if sl is not None:
                        break
            slot_id = sl.identifier if sl is not None else ''
        slot_id = slot_id or ('OB' + rig.name)
        if rig.animation_data:
            for tr in list(rig.animation_data.nla_tracks):
                rig.animation_data.nla_tracks.remove(tr)
            rig.animation_data.action = None
        # MEASURE IN THE STANDING POSE: many scans' rest (bind) pose is not how the animal stands - the clips move
        # the root bone (lying T-poses, other axes). So we pose it in the first frame of its idle clip.
        tmp = {'kind': kind, 'actions': own_actions}
        idle = None
        for c in ('idle', 'walk'):
            idle = _action(tmp, c) if c in s.get('clips', {}) else None
            if idle:
                break
        if idle is not None:
            ad = rig.animation_data_create(); ad.action = idle
            sl = _slot_for(idle, 'OBJECT', slot_id)
            if sl is not None:
                try:
                    ad.action_slot = sl
                except Exception:
                    pass
            bpy.context.scene.frame_set(int(idle.frame_range[0]))
        else:
            rig.data.pose_position = 'REST'
    fix = link(bpy.data.objects.new(name + '_fix', None))
    for o in new:
        if o.parent is None:
            o.parent = fix
    bpy.context.view_layer.update()
    meshes = [o for o in new if o.type == 'MESH']
    # 1. which way does it face? head bone (or the catalogue axis) relative to the body centre
    lo, hi = _mesh_bbox(meshes); centre = (lo + hi) / 2
    hb = _bone(rig, s.get('head'))
    if hb is not None:
        d = (rig.matrix_world @ rig.pose.bones[hb.name].head) - centre
    else:
        d = _AXIS[s.get('front', '-Y')].copy()
    d.z = 0
    if d.length < 1e-9:
        d = Vector((0, -1, 0))
    # snap to the nearest axis (scans are modelled axis-aligned; the head bone can sit a bit off-centre)
    ang = math.atan2(d.x, -d.y)                           # 0 when facing -Y
    ang = round(ang / (math.pi / 2)) * (math.pi / 2)
    R = Matrix.Rotation(-ang, 4, 'Z')
    fix.matrix_world = R
    bpy.context.view_layer.update()
    lo, hi = _mesh_bbox(meshes)
    # 2. real size
    kind_size = s['size']
    if kind_size[0] == 'withers' and rig is not None and _bone(rig, kind_size[2]) is not None:
        sb = _bone(rig, kind_size[2])
        sp = rig.matrix_world @ rig.pose.bones[sb.name].head
        L = hi.y - lo.y; W = hi.x - lo.x
        # top of the back at the shoulder: highest skin point in a thin slab across the body just behind the bone
        top = None
        for p in _eval_points(meshes):
            if abs(p.y - (sp.y + 0.04 * L)) < 0.035 * L and abs(p.x - (lo.x + hi.x) / 2) < 0.2 * W:
                top = p.z if top is None else max(top, p.z)
        h_now = (top if top is not None else sp.z) - lo.z
    else:
        h_now = hi.z - lo.z
    k = kind_size[1] / max(h_now, 1e-9)
    base = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    fix.matrix_world = Matrix.Scale(k, 4) @ Matrix.Translation(-base) @ R
    fix.parent = root
    if rig:
        rig.data.pose_position = 'POSE'
        if rig.animation_data:
            rig.animation_data.action = None
    root.location = loc; root.rotation_euler.z = math.radians(heading_deg)
    root['fix'] = fix.name
    root['rig'] = rig.name if rig else ''
    root['slot'] = slot_id
    root['actions'] = own_actions                     # ONLY these clips belong to this animal (not another import's)
    root['scale'] = k
    root['mesh_names'] = [m.name for m in meshes]
    # shape-key animated scans (the sheep) keep their morph action on the mesh
    return root


def rig_of(root):
    n = root.get('rig')
    return bpy.data.objects.get(n) if n else None


def objects_of(root):
    return [root] + list(root.children_recursive)


# ------------------------------------------------------------------ clips
def _action(who, clip):
    """The action for catalogue clip name `clip`. `who` = an animal root (searches only ITS own imported clips -
    another import of the same scan has its own copies with other slots) or a kind name (any import)."""
    kind = who['kind'] if not isinstance(who, str) else who
    s = spec(kind)
    want = s.get('clips', {}).get(clip)
    if want is None:
        return None                                       # this animal has no such clip (static scan) -> stands
    if not isinstance(who, str) and who.get('actions') is not None:
        acts = [bpy.data.actions[n] for n in who['actions'] if n in bpy.data.actions]
    else:
        acts = list(bpy.data.actions)
    for a in acts:
        if a.name == want:
            return a
    for a in acts:                                         # importer adds .001 on re-import; 'Armature|...' prefixes
        base = a.name.split('|')[-1]
        if a.name.startswith(want + '.') or a.name.endswith(want) or base == want or base.split('.')[0] == want:
            return a
    for a in acts:
        if want in a.name:
            return a
    return None


def _slot_for(act, idtype='OBJECT', want=''):
    slots = getattr(act, 'slots', None)
    if not slots:
        return None
    if want:
        for sl in slots:
            if sl.identifier == want:
                return sl
        base = want.split('.')[0]
        for sl in slots:                                 # same node, other import (.001 names)
            if sl.identifier.split('.')[0] == base:
                return sl
    for sl in slots:
        if getattr(sl, 'target_id_type', idtype) == idtype:
            return sl
    return slots[0]


def _target(root):
    """What the clip animates: the armature, or (sheep) the mesh's shape keys."""
    rig = rig_of(root)
    if rig is not None:
        return rig, 'OBJECT'
    for n in root.get('mesh_names', []):
        m = bpy.data.objects.get(n)
        if m and m.data.shape_keys:
            return m.data.shape_keys, 'KEY'
    return None, None


def play(root, clip, start=1, end=None, phase_s=0.0, speed=1.0, track=None, blend=0, influence=None):
    """Loop clip `clip` (catalogue name, e.g. 'walk', or the scan's action name) from frame `start` to `end`.
    phase_s shifts it in time (seconds) so neighbours are out of step; speed = playback rate. `track` = name of a
    new NLA track (default: replaces everything); blend = frames of blend-in (for gait changes on a second track).
    Returns the NLA strip (None if the animal has no such clip - then it just stands)."""
    tgt, idtype = _target(root)
    act = _action(root, clip)
    if tgt is None or act is None:
        return None
    sc = bpy.context.scene
    end = end or sc.frame_end
    ad = tgt.animation_data or tgt.animation_data_create()
    ad.action = None
    if track is None:
        for tr in list(ad.nla_tracks):
            ad.nla_tracks.remove(tr)
    tr = ad.nla_tracks.new(); tr.name = track or clip
    a0, a1 = act.frame_range
    length = max(a1 - a0, 1.0) / max(speed, 1e-3)
    off = (phase_s * FPS * speed) % max(a1 - a0, 1.0)
    st = tr.strips.new(f'{clip}', int(start), act)
    st.action_frame_start = a0; st.action_frame_end = a1
    st.scale = 1.0 / max(speed, 1e-3)
    st.repeat = max(1.0, (end - start) / length + 2)
    # phase: start the loop part-way through by trimming the first cycle (move the strip earlier)
    st.frame_start = start - off / max(speed, 1e-3)
    st.frame_end = st.frame_start + st.repeat * length
    sl = _slot_for(act, idtype, root.get('slot', '') if idtype == 'OBJECT' else '')
    if sl is not None:
        try:
            st.action_slot = sl
        except Exception:
            pass
    st.extrapolation = 'HOLD'
    if blend:
        st.blend_in = blend
    if influence is not None:
        st.use_animated_influence = True
    return st


def clip_speed(root, clip):
    """How fast (m/s, real metres) the animal would travel playing `clip` at speed 1.0: the foot bone's backward
    slide while it is on the ground. Falls back to the catalogue's speeds table."""
    s = spec(root['kind'])
    fallback = s.get('speeds', {}).get(clip, 1.0)
    rig = rig_of(root)
    fb = _bone(rig, s.get('foot')) if rig and s.get('foot') != 'AUTO' else None
    if rig is not None and s.get('foot') == 'AUTO':        # the lowest bone on the left side = a hoof
        left = [b for b in rig.data.bones if '.L' in b.name or b.name.startswith('L_')]
        fb = min(left, key=lambda b: (rig.matrix_world @ b.head_local).z) if left else None
    act = _action(root, clip)
    if fb is None or act is None:
        return fallback
    sc = bpy.context.scene
    keep = sc.frame_current
    ad = rig.animation_data or rig.animation_data_create()
    saved = [(tr, tr.mute) for tr in ad.nla_tracks]
    for tr, _ in saved:
        tr.mute = True
    ad.action = act
    sl = _slot_for(act, 'OBJECT', root.get('slot', ''))
    if sl is not None:
        try:
            ad.action_slot = sl
        except Exception:
            pass
    a0, a1 = (int(x) for x in act.frame_range)
    pts = []
    for f in range(a0, a1 + 1):
        sc.frame_set(f)
        pts.append((rig.matrix_world @ rig.pose.bones[fb.name].head).copy())
    ad.action = None
    for tr, m in saved:
        tr.mute = m
    sc.frame_set(keep)
    zs = [p.z for p in pts]; zmin, zmax = min(zs), max(zs)
    fwd = root.matrix_world.to_3x3() @ Vector((0, -1, 0)); fwd.z = 0; fwd.normalize()
    slide, n = 0.0, 0
    for i in range(1, len(pts)):
        if pts[i].z < zmin + 0.15 * (zmax - zmin) and pts[i - 1].z < zmin + 0.15 * (zmax - zmin):
            slide += -(pts[i] - pts[i - 1]).dot(fwd); n += 1
    if n < 2 or slide <= 0:
        return fallback
    v = slide / n * FPS                                   # metres per frame on the ground -> m/s
    return v if 0.1 < v < 25 else fallback


# ------------------------------------------------------------------ moving along the ground
def heading_of(dx, dy):
    """Heading (deg) that makes a -Y-facing animal look along (dx, dy)."""
    return math.degrees(math.atan2(dx, -dy))


def walk_path(root, points, speed, start=1, gait='walk', z_fn=None, turn_smooth=6, phase_s=0.0, play_clip=True,
              stop_clip='idle'):
    """Move `root` along the polyline `points` [(x, y), ...] at `speed` m/s from frame `start`, facing the way it
    goes, and play `gait` at the playback rate that matches the speed (no sliding). When the path ends the animal
    stops and plays `stop_clip`. z_fn(x, y) -> ground height (default 0). Returns the last frame of travel."""
    pts = [Vector((p[0], p[1], 0.0)) for p in points]
    seg = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]
    total = sum(seg)
    dur = total / max(speed, 1e-3) * FPS
    end = int(start + dur)
    step = 4                                              # a key every 4 frames is plenty for smooth travel
    prev_h = None
    for f in list(range(int(start), end, step)) + [end]:
        dist = (f - start) / FPS * speed
        i, acc = 0, 0.0
        while i < len(seg) - 1 and acc + seg[i] < dist:
            acc += seg[i]; i += 1
        t = min(1.0, (dist - acc) / max(seg[i], 1e-6))
        p = pts[i].lerp(pts[i + 1], t)
        d = pts[i + 1] - pts[i]
        h = math.radians(heading_of(d.x, d.y))
        if prev_h is not None:                            # unwrap so a turn never spins the long way round
            while h - prev_h > math.pi:
                h -= 2 * math.pi
            while h - prev_h < -math.pi:
                h += 2 * math.pi
        prev_h = h
        root.location = (p.x, p.y, z_fn(p.x, p.y) if z_fn else 0.0)
        root.rotation_euler = (0, 0, h)
        root.keyframe_insert('location', frame=f); root.keyframe_insert('rotation_euler', index=2, frame=f)
    if play_clip:
        native = clip_speed(root, gait)
        rate = max(0.5, min(1.8, speed / max(native, 1e-3)))
        play(root, gait, start=start - 10, end=end, phase_s=phase_s, speed=rate)
        if stop_clip and _action(root, stop_clip) is not None and end < bpy.context.scene.frame_end:
            st = play(root, stop_clip, start=end, phase_s=phase_s, track='stop', blend=8)
            if st:
                st.extrapolation = 'HOLD_FORWARD'          # only AFTER the stop - never override the walk before it
    return end


# ------------------------------------------------------------------ cheap copies
_SOURCES = {}


def _hidden_collection(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    lc = bpy.context.view_layer.layer_collection.children.get(c.name)
    if lc:
        lc.exclude = False
        lc.hide_viewport = True
    c.hide_render = True
    return c


def actor(kind, clip='idle', phase_s=0.0, speed=1.0, frames=None, name=None):
    """One unique animal kept as an instancing SOURCE (own rig + own clip phase), parked in a hidden collection at
    the origin. Returns the collection to instance (instance(...))."""
    name = name or f'src_{kind}_{clip}_{int(phase_s * 100)}'
    if name in _SOURCES and _SOURCES[name].name in bpy.data.collections:
        return _SOURCES[name]
    r = load(kind, (0, 0, 0), 0.0, name=name + '_root')
    if clip:
        play(r, clip, start=(frames or (1, 0))[0], end=(frames or (1, None))[1], phase_s=phase_s, speed=speed)
    col = bpy.data.collections.new(name)
    holder = _hidden_collection('animal_sources')
    holder.children.link(col)
    for o in objects_of(r):
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    col.hide_render = False
    _SOURCES[name] = col
    return col


def instance(col, loc=(0, 0, 0), heading_deg=0.0, scale=1.0, name='animal_inst'):
    """A cheap copy of an actor() collection, standing on `loc`. Animate its location/rotation like a root."""
    e = link(bpy.data.objects.new(name, None))
    e.instance_type = 'COLLECTION'; e.instance_collection = col
    e.location = loc; e.rotation_euler = (0, 0, math.radians(heading_deg)); e.scale = (scale,) * 3
    return e


def _scatter_points(center, radius, count, min_dist, seed, ellipse=(1.0, 1.0)):
    """Blue-noise points in a disc / ellipse (no two animals inside each other)."""
    rnd = random.Random(seed)
    out, tries = [], 0
    while len(out) < count and tries < count * 400:
        tries += 1
        a = rnd.uniform(0, 2 * math.pi); r = radius * math.sqrt(rnd.random())
        p = Vector((center[0] + math.cos(a) * r * ellipse[0], center[1] + math.sin(a) * r * ellipse[1]))
        if all((p - q).length >= min_dist for q in out):
            out.append(p)
    return out


def herd(kind, center, count=12, radius=8.0, heading_deg=0.0, spread_deg=70.0, clips=('eat', 'idle'), variants=4,
         seed=0, z_fn=None, min_dist=None, name=None, size_jitter=0.06):
    """A grazing / resting herd: `variants` unique actors (different clips + phases) scattered as instances over a
    disc, all roughly facing heading_deg +- spread (animals graze into the wind / along the slope).
    size_jitter: +-6 % size (no two animals identical). Returns the list of instance empties."""
    rnd = random.Random(seed)
    s = spec(kind)
    body = s['size'][1] * (1.6 if s['size'][0] == 'withers' else 1.3)
    min_dist = min_dist or body * 1.1
    srcs = []
    for v in range(variants):
        clip = clips[v % len(clips)]
        if _action_exists(kind, clip) is False:
            clip = 'idle'
        srcs.append(actor(kind, clip, phase_s=rnd.uniform(0, 6), speed=rnd.uniform(0.85, 1.1),
                          name=f'src_{name or kind}_{seed}_{v}'))
    out = []
    for i, p in enumerate(_scatter_points(center, radius, count, min_dist, seed)):
        h = heading_deg + rnd.uniform(-spread_deg, spread_deg)
        z = z_fn(p.x, p.y) if z_fn else 0.0
        out.append(instance(srcs[i % variants], (p.x, p.y, z), h, rnd.uniform(1 - size_jitter, 1 + size_jitter),
                            name=f'{name or kind}_{i}'))
    return out


def _action_exists(kind, clip):
    s = spec(kind)
    if clip not in s.get('clips', {}):
        return False
    return True


def flock_move(kind, path, count=20, speed=0.8, start=1, spread=4.0, depth=6.0, variants=4, seed=0, z_fn=None,
               gait='walk', name=None):
    """A flock / herd DRIVEN along a path (a shepherd moving his sheep, a drover with cattle): every animal follows
    the path with its own sideways offset (within +-spread/2), its own lag (up to `depth` m behind the leader),
    a slow weave and +-12 % speed. Uses walking actors; instance roots carry the travel."""
    rnd = random.Random(seed)
    pts = [Vector((p[0], p[1])) for p in path]
    srcs = []
    for v in range(variants):
        srcs.append(actor(kind, gait if _action_exists(kind, gait) else 'idle', phase_s=rnd.uniform(0, 4),
                          speed=1.0, name=f'src_{name or kind}_move_{seed}_{v}'))
    out = []
    for i in range(count):
        lat = rnd.uniform(-spread / 2, spread / 2); lag = rnd.uniform(0, depth)
        spd = speed * rnd.uniform(0.9, 1.1)
        e = instance(srcs[i % variants], (0, 0, 0), 0.0, rnd.uniform(0.94, 1.06), name=f'{name or kind}_m{i}')
        # offset path: shift every point sideways by lat (perpendicular), start `lag` metres behind
        off = []
        for j, p in enumerate(pts):
            d = (pts[min(j + 1, len(pts) - 1)] - pts[max(j - 1, 0)])
            d = d.normalized() if d.length > 1e-6 else Vector((0, 1))
            side = Vector((-d.y, d.x))
            wob = math.sin(j * 1.3 + i) * 0.3
            off.append(p + side * (lat + wob))
        d0 = (off[1] - off[0]).normalized()
        off.insert(0, off[0] - d0 * lag)
        walk_path(e, [tuple(p) for p in off], spd, start=start, z_fn=z_fn, play_clip=False)
        out.append(e)
    return out


def poultry(kind, center, count=10, radius=3.0, frames=(1, 240), seed=0, z_fn=None, name=None):
    """Chickens (or pigeons) in a yard: each one PECKS, then takes a few quick steps somewhere new, then pecks again.
    Built as unique actors (cheap: ~5k faces each) so every bird keeps its own rhythm."""
    rnd = random.Random(seed)
    out = []
    pts = _scatter_points(center, radius, count, 0.35, seed)
    for i, p in enumerate(pts):
        r = load(kind, (p.x, p.y, z_fn(p.x, p.y) if z_fn else 0.0), rnd.uniform(0, 360), name=f'{name or kind}_{i}')
        f = frames[0] - rnd.randint(0, 40)
        pos = Vector((p.x, p.y)); h = r.rotation_euler.z
        segments = []
        while f < frames[1]:
            peck = rnd.randint(40, 110)
            segments.append(('peck', f, f + peck)); f += peck
            dist = rnd.uniform(0.3, 1.2)
            dur = int(dist / spec(kind).get('speeds', {}).get('walk', 0.45) * FPS)
            a = h + math.radians(rnd.uniform(-100, 100))
            new = pos + Vector((math.sin(a), -math.cos(a))) * dist
            if (new - Vector(center)).length > radius:
                new = pos + (Vector(center) - pos).normalized() * dist
                a = math.radians(heading_of(*(new - pos)))
            segments.append(('walk', f, f + dur, pos.copy(), new.copy(), a)); f += dur
            pos, h = new, a
        # keys: hold still while pecking, glide during walks
        tgt, _ = _target(r)
        ad = tgt.animation_data_create() if tgt else None
        if ad:
            for tr in list(ad.nla_tracks):
                ad.nla_tracks.remove(tr)
        for sgm in segments:
            if sgm[0] == 'walk':
                _, f0, f1, a_, b_, hh = sgm
                for ff, pp in ((f0, a_), (f1, b_)):
                    r.location = (pp.x, pp.y, z_fn(pp.x, pp.y) if z_fn else 0.0); r.rotation_euler.z = hh
                    r.keyframe_insert('location', frame=ff); r.keyframe_insert('rotation_euler', index=2, frame=ff)
            if ad:
                act = _action(r, sgm[0])
                if act:
                    tr = ad.nla_tracks.new(); tr.name = f'{sgm[0]}{sgm[1]}'
                    st = tr.strips.new(sgm[0], int(sgm[1]), act)
                    a0, a1 = act.frame_range
                    st.repeat = max(1.0, (sgm[2] - sgm[1]) / max(a1 - a0, 1))
                    st.extrapolation = 'NOTHING'            # each segment only plays in its own time window
                    sl = _slot_for(act, 'OBJECT', r.get('slot', ''))
                    if sl is not None:
                        try:
                            st.action_slot = sl
                        except Exception:
                            pass
        out.append(r)
    return out


# ------------------------------------------------------------------ procedural gait (for rigs without a trot clip)
def gait(root, start, end, speed=2.6, kind='trot', period_s=None, bob=0.025, phase_s=0.0):
    """Procedural quadruped gait on the catalogue's 'legs' bones: every leg swings about the animal's sideways axis,
    the lower leg folds while the foot travels forward (swing) and stays straight while it pushes (stance).
      trot : diagonal pairs together (front-left + back-right, then front-right + back-left) - dogs, trotting horses
      walk : four-beat, each leg a quarter cycle apart (LH, LF, RH, RF)
    The swing angle comes from the speed: in stance the foot is planted while the body moves speed * period / 2,
    so 2 * leg * sin(angle) = speed * period / 2  ->  no sliding paws. Body bobs twice per cycle (trot).
    Removes the rig's clips for that time (call play(...) again after `end` for an idle)."""
    s = spec(root['kind'])
    rig = rig_of(root); legs = s.get('legs')
    if rig is None or not legs:
        return
    L = s.get('leg_len', 0.45)
    p = period_s or (0.34 if kind == 'trot' else 0.9)
    th = math.asin(max(-0.95, min(0.95, speed * p / (4 * L))))
    phases = {'trot': {'FL': 0.0, 'BR': 0.0, 'FR': 0.5, 'BL': 0.5},
              'walk': {'BL': 0.0, 'FL': 0.25, 'BR': 0.5, 'FR': 0.75}}[kind]
    duty = 0.5 if kind == 'trot' else 0.65                 # fraction of the cycle each foot is on the ground
    ad = rig.animation_data_create(); ad.action = None
    for tr in list(ad.nla_tracks):
        ad.nla_tracks.remove(tr)
    bpy.context.view_layer.update()
    # the animal's sideways axis, expressed in armature space
    side_w = (root.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()
    side_a = (rig.matrix_world.to_3x3().inverted() @ side_w).normalized()
    from mathutils import Quaternion
    bones = {}
    for leg, (up, low) in legs.items():
        bu, bl = _bone(rig, up), _bone(rig, low)
        if bu is None or bl is None:
            continue
        # axis in each bone's own rest frame (pose rotations are applied there)
        au = (bu.matrix_local.to_3x3().inverted() @ side_a).normalized()
        al = (bl.matrix_local.to_3x3().inverted() @ side_a).normalized()
        front = leg.startswith('F')
        bones[leg] = (rig.pose.bones[bu.name], rig.pose.bones[bl.name], au, al, front)
        for pb in (rig.pose.bones[bu.name], rig.pose.bones[bl.name]):
            pb.rotation_mode = 'QUATERNION'
    fix = bpy.data.objects.get(root.get('fix', ''))
    z0 = fix.location.z if fix else 0.0
    for f in range(int(start), int(end) + 1, 2):
        t = ((f - start) / FPS + phase_s) / p
        for leg, (pu, pl, au, al, front) in bones.items():
            c = (t + phases[leg]) % 1.0
            if c < duty:                                   # stance: foot planted, leg sweeps from front to back
                u = c / duty
                ang = th * (1 - 2 * u); fold = 0.0
            else:                                          # swing: lift + carry the foot forward again
                u = (c - duty) / (1 - duty)
                ang = -th + 2 * th * (0.5 - 0.5 * math.cos(math.pi * u))
                fold = math.sin(math.pi * u) * (0.9 if front else 0.6)
            sign = -1.0                                    # rotating +X swings a hanging foot BACK (+Y)
            pu.rotation_quaternion = Quaternion(au, sign * ang)
            # lifting the paw: the lower leg folds back (+X turn) - more at the front (carpus) than behind (hock)
            pl.rotation_quaternion = Quaternion(al, fold)
            pu.keyframe_insert('rotation_quaternion', frame=f); pl.keyframe_insert('rotation_quaternion', frame=f)
        if fix and bob:
            fix.location.z = z0 + bob * (0.5 + 0.5 * math.cos(4 * math.pi * t)) * (1 if kind == 'trot' else 0.4)
            fix.keyframe_insert('location', index=2, frame=f)

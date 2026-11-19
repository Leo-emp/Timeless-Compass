# CAST: build a named character from a spec: MakeHuman (MPFB, CC0) body + face, skin, eyes, brows,
# a skeleton, and REAL STRAND HAIR + BEARD (Blender hair curves) grown on the scalp and jaw.
# Hair is grown at rest pose and parented to the head bone, so it follows head turns.
import math
import os
import random

import bpy
import numpy as np
from mathutils import Vector, Matrix

from bl_ext.blender_org.mpfb.services.humanservice import HumanService
from bl_ext.blender_org.mpfb.services.objectservice import ObjectService

from lib.common import mpfb_asset, hair_material, link


def build_human(spec: dict):
    """spec keys: macro (dict), skin (MPFB skin folder), eyes_color (MPFB eye material), brows, tan (0..1)."""
    human = HumanService.create_human(macro_detail_dict=spec['macro'])
    if spec.get('face'):
        sculpt(human, spec['face'])          # before eyes/brows/rig are fitted, so they fit the sculpted face
    if spec.get('asymmetry', 1.0) > 0:       # FACE STANDARD 1: subtle, natural asymmetry (never mirror-perfect)
        sculpt(human, asymmetry(spec.get('seed', abs(hash(spec.get('name', 'x'))) % 10000), spec.get('asymmetry', 1.0)))
    skin = spec.get('skin', 'middleage_caucasian_male')
    HumanService.set_character_skin(mpfb_asset('skins', skin, skin + '.mhmat'), human)
    for typ, parts in [('Eyes', ('eyes', 'high-poly', 'high-poly.mhclo')),
                       ('Eyebrows', ('eyebrows', spec.get('brows', 'eyebrow001'), spec.get('brows', 'eyebrow001') + '.mhclo')),
                       ('Eyelashes', ('eyelashes', 'eyelashes01', 'eyelashes01.mhclo')),
                       ('Teeth', ('teeth', 'teeth_base', 'teeth_base.mhclo'))]:
        HumanService.add_mhclo_asset(mpfb_asset(*parts), human, asset_type=typ, material_type='MAKESKIN')
    # MODERN clothes from the MakeHuman asset pack (suits, work suit, fedora, shoes...), e.g. for 1950s secret projects:
    # spec "mpfb_clothes": [["male_elegantsuit01", [0.08, 0.08, 0.09]], ["fedora01", null], "shoes02"]  (name, tint)
    for item in spec.get('mpfb_clothes', []):
        name, tint = (item, None) if isinstance(item, str) else (item[0], item[1])
        HumanService.add_mhclo_asset(mpfb_asset('clothes', name, name + '.mhclo'), human, asset_type='Clothes',
                                     material_type='MAKESKIN')
        if tint:
            o = next((c for c in human.children if name in c.name), None)
            if o is not None:
                _tint_object(o, tint)
    HumanService.add_builtin_rig(human, 'default', import_weights=True)
    rig = ObjectService.find_object_of_type_amongst_nearest_relatives(human, 'Skeleton')
    # eyes, brows, lashes and teeth were added before the rig, so MPFB left them as plain children of the body
    # mesh (they would neither follow the head nor act). Skin each one to the face bones so the face can perform.
    for o in [c for c in human.children if c.type == 'MESH']:
        rig_face_part(o, human, rig)
    if spec.get('tan'):
        tan_skin(human, spec['tan'], spec.get('tan_color', (0.78, 0.56, 0.42)))
    skin_detail(human)
    skin_v2(human, rig, stubble=spec.get('stubble', 0.0))
    if spec.get('age_lines'):
        age_face(human, rig, spec['age_lines'])
    face_materials(rig, hair_melanin=(spec.get('hair') or {}).get('melanin', 0.9))
    if spec.get('brow_strands', bool(spec.get('grooming'))):   # real brow hairs: on for every named character
        h = spec.get('hair') or {}
        brow_strands(human, rig, density=spec.get('brow_density', 1400), melanin=spec.get('brow_melanin', h.get('melanin', 0.9)),
                     grey=h.get('grey', 0.0) * 0.6)
    return human, rig


ASYM_PAIRS = [('eye-trans-up', 'eye-trans-down', 0.10), ('eye-height2-incr', 'eye-height2-decr', 0.12),
              ('eye-scale-incr', 'eye-scale-decr', 0.06), ('eye-corner1-up', 'eye-corner1-down', 0.12),
              ('eye-bag-incr', 'eye-bag-decr', 0.15), ('eye-eyefold-down', 'eye-eyefold-up', 0.12),
              ('cheek-bones-incr', 'cheek-bones-decr', 0.12), ('cheek-volume-incr', 'cheek-volume-decr', 0.12),
              ('cheek-trans-up', 'cheek-trans-down', 0.08)]


def asymmetry(seed, amount=1.0):
    """Per-person one-sided shape weights (MakeHuman l-/r- targets): each trait drifts on ONE side only, by a
    small seeded amount - below what reads as a deformity, enough that the face is no longer a mirror image."""
    import random as _r
    rnd = _r.Random(seed)
    out = {}
    for up, down, mx in ASYM_PAIRS:
        side = rnd.choice('lr')
        w = rnd.uniform(0.3, 1.0) * mx * amount
        out[f'{side}-{up if rnd.random() < 0.5 else down}'] = round(w, 3)
    return out


def sculpt(human, face: dict):
    """Give a character its OWN face (from its historical portrait) with MakeHuman's sculpt targets, e.g.
    {"head-square": 0.5, "nose-hump-incr": 0.3, "cheek-bones-incr": 0.3}. A name without l-/r- that exists only
    per side is applied to both sides. Weights 0..1."""
    import bl_ext.blender_org.mpfb as mpfb
    from bl_ext.blender_org.mpfb.services.targetservice import TargetService
    root = os.path.join(os.path.dirname(mpfb.__file__), 'data', 'targets')
    index = {}
    for cat in os.listdir(root):
        d = os.path.join(root, cat)
        if os.path.isdir(d) and cat not in ('expression', 'macrodetails', '_images'):
            for f in os.listdir(d):
                if f.endswith('.target.gz'):
                    index[f[:-10]] = os.path.join(d, f)
    for name, w in face.items():
        names = [name] if name in index else [f'l-{name}', f'r-{name}']
        for n in names:
            if n not in index:
                raise KeyError(f'no MakeHuman target {name!r}')
            TargetService.load_target(human, index[n], weight=float(w), name='face-' + n)


def _tint_object(o, rgb):
    """Recolour a MakeHuman clothing proxy: multiply its texture by a dye colour (charcoal suit, khaki uniform...)."""
    for slot in o.material_slots:
        m = slot.material
        if not m or not m.node_tree:
            continue
        b = next((x for x in m.node_tree.nodes if x.type == 'BSDF_PRINCIPLED'), None)
        if b is None:
            continue
        nt = m.node_tree
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
        mx.inputs['Factor'].default_value = 1.0; mx.inputs['B'].default_value = (*rgb, 1)
        if b.inputs['Base Color'].is_linked:
            nt.links.new(b.inputs['Base Color'].links[0].from_socket, mx.inputs['A'])
        else:
            mx.inputs['A'].default_value = b.inputs['Base Color'].default_value
        nt.links.new(mx.outputs['Result'], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = max(b.inputs['Roughness'].default_value, 0.6)


def rig_face_part(o, human, rig):
    """Bind an eye / brow / lash / teeth mesh to the skeleton so it performs with the face:
       eyebrows + eyelashes -> copy the skin's own face-bone weights (they ride on brows and eyelids)
       eyeballs            -> each half fully weighted to its eye bone (eye.L is on +X), so the eyes can look around
       teeth               -> upper row on the head, lower row on the jaw (the mouth can open)"""
    w = o.matrix_world.copy()
    o.parent = rig; o.parent_type = 'OBJECT'; o.matrix_world = w
    for m in list(o.modifiers):
        if m.type == 'ARMATURE':
            o.modifiers.remove(m)
    for g in list(o.vertex_groups):
        o.vertex_groups.remove(g)
    name = o.name.lower()
    face_part = any(k in name for k in ('eyebrow', 'eyelash', 'teeth', 'high-poly', 'eyes', 'tongue'))
    if 'eyebrow' in name or 'eyelash' in name or not face_part:        # brows, lashes AND clothes copy body weights
        dt = o.modifiers.new('weights', 'DATA_TRANSFER')
        dt.object = human; dt.use_vert_data = True; dt.data_types_verts = {'VGROUP_WEIGHTS'}
        dt.vert_mapping = 'POLYINTERP_NEAREST'
        dt.layers_vgroup_select_src = 'ALL'; dt.layers_vgroup_select_dst = 'NAME'
        with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
            bpy.ops.object.datalayout_transfer(modifier=dt.name)
            bpy.ops.object.modifier_apply(modifier=dt.name)
    else:
        xs = [v.co.x for v in o.data.vertices]; zs = [v.co.z for v in o.data.vertices]
        if 'teeth' in name:
            # split at the BITE LINE = the biggest empty height gap between the two rows (the middle of the height
            # range can cut through the upper teeth + gums, which then swing down with the jaw like fangs)
            zz = sorted(set(round(z, 5) for z in zs))
            lo_i, hi_i = int(len(zz) * 0.25), int(len(zz) * 0.75)
            gaps = [(zz[i + 1] - zz[i], i) for i in range(lo_i, max(lo_i + 1, hi_i))]
            g, i = max(gaps) if gaps else (0, len(zz) // 2)
            mid = (zz[i] + zz[i + 1]) / 2 if i + 1 < len(zz) else (min(zs) + max(zs)) / 2
            split = [('head', [v.index for v in o.data.vertices if v.co.z >= mid]),
                     ('jaw', [v.index for v in o.data.vertices if v.co.z < mid])]
        else:                                                   # eyes (MPFB names the eye mesh "high-poly")
            split = [('eye.L', [v.index for v in o.data.vertices if v.co.x > 0]),
                     ('eye.R', [v.index for v in o.data.vertices if v.co.x <= 0])]
        for bone, idx in split:
            o.vertex_groups.new(name=bone).add(idx, 1.0, 'REPLACE')
    arm = o.modifiers.new('skeleton', 'ARMATURE'); arm.object = rig
    # armature first, then any subdivision (MPFB adds a SUBSURF to these proxies)
    while o.modifiers.find(arm.name) > 0:
        with bpy.context.temp_override(object=o, active_object=o):
            bpy.ops.object.modifier_move_up(modifier=arm.name)


def skin_detail(human, pores=0.2, sheen=0.45):
    """Real skin is not plastic: add micro pores (fine bump on top of the skin's normal map), break up the
    shine with a roughness pattern, and set a natural skin specular. Done inside MakeHuman's shared skin group."""
    done = set()
    for slot in human.material_slots:
        m = slot.material
        if not m or not m.node_tree:
            continue
        for g in [n for n in m.node_tree.nodes if n.type == 'GROUP' and n.node_tree]:
            nt = g.node_tree
            if nt.name in done:
                continue
            done.add(nt.name)
            b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if b is None:
                continue
            L = nt.links.new
            pore = nt.nodes.new('ShaderNodeTexVoronoi'); pore.inputs['Scale'].default_value = 900
            fine = nt.nodes.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value = 400; fine.inputs['Detail'].default_value = 8
            mix = nt.nodes.new('ShaderNodeMath'); mix.operation = 'ADD'
            L(pore.outputs['Distance'], mix.inputs[0]); L(fine.outputs['Fac'], mix.inputs[1])
            bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = pores; bump.inputs['Distance'].default_value = 0.0005
            # pores are deeper and more visible on the nose and T-zone: scale by the 'oil' channel of skin_regions
            reg = nt.nodes.new('ShaderNodeAttribute'); reg.attribute_name = 'skin_regions'
            sepr = nt.nodes.new('ShaderNodeSeparateColor'); L(reg.outputs['Color'], sepr.inputs['Color'])
            boost = nt.nodes.new('ShaderNodeMath'); boost.operation = 'MULTIPLY_ADD'; boost.inputs[1].default_value = 1.0
            boost.inputs[2].default_value = 1.0; L(sepr.outputs['Blue'], boost.inputs[0])         # 1x .. 2x
            deep = nt.nodes.new('ShaderNodeMath'); deep.operation = 'MULTIPLY'
            L(mix.outputs[0], deep.inputs[0]); L(boost.outputs[0], deep.inputs[1])
            L(deep.outputs[0], bump.inputs['Height'])
            if b.inputs['Normal'].is_linked:                       # keep MakeHuman's own normal map underneath
                L(b.inputs['Normal'].links[0].from_socket, bump.inputs['Normal'])
            L(bump.outputs['Normal'], b.inputs['Normal'])
            rough = nt.nodes.new('ShaderNodeMapRange'); rough.inputs['To Min'].default_value = 0.42; rough.inputs['To Max'].default_value = 0.66
            L(fine.outputs['Fac'], rough.inputs['Value']); L(rough.outputs['Result'], b.inputs['Roughness'])
            b.inputs['Specular IOR Level'].default_value = sheen


def _blob(pos, center, radius):
    d = np.linalg.norm(pos - np.asarray(center, dtype=np.float32), axis=1)
    return np.exp(-(d / radius) ** 2)


def skin_v2(human, rig, stubble=0.0):
    """Skin that reads as LIVING skin, not a mannequin (MakeHuman skins are one flat 2K colour image):
      R = blood: redness on nose, cheeks, ears, lips (thin skin, many vessels)
      G = stubble shadow: the blue-grey of shaved beard roots on jaw / upper lip (`stubble` 0..1)
      B = oil: shinier T-zone (forehead + nose), matte cheeks
    stored per vertex as the colour attribute 'skin_regions', read inside MakeHuman's shared skin group.
    Also: real subsurface scattering (light glows red through ears / nostrils), thin oily coat, richer pores."""
    pos, nor, _ = rest_surface(human)
    lm = landmarks(human, rig, pos)
    head, nose, chin = (np.asarray(lm[k], dtype=np.float32) for k in ('head', 'nose', 'chin'))
    mouth_z = float(lm['mouth_top'])
    eye_l = np.asarray(rig.matrix_world @ rig.data.bones['eye.L'].head_local, dtype=np.float32)
    eye_r = np.asarray(rig.matrix_world @ rig.data.bones['eye.R'].head_local, dtype=np.float32)
    eye_z = (eye_l[2] + eye_r[2]) / 2
    lips = group_weights(human, 'lips')
    cheek_l = eye_l + np.array([0.012, -0.012, -0.04], dtype=np.float32)
    cheek_r = eye_r + np.array([-0.012, -0.012, -0.04], dtype=np.float32)
    rel = pos - head
    ear = (np.abs(rel[:, 0]) > 0.062) & (np.abs(pos[:, 2] - eye_z) < 0.05) & (rel[:, 1] > -0.04)
    red = np.clip(0.9 * _blob(pos, nose, 0.022) + 0.55 * _blob(pos, cheek_l, 0.03) + 0.55 * _blob(pos, cheek_r, 0.03)
                  + 0.6 * ear + 0.3 * lips, 0, 1)
    front = rel[:, 1] < -0.02
    jaw_zone = front & (pos[:, 2] < mouth_z + 0.018) & (pos[:, 2] > chin[2] - 0.035) & (np.abs(rel[:, 0]) < 0.07)
    stub = np.clip(jaw_zone * (1 - lips) * stubble, 0, 1)
    scalp_w = group_weights(human, 'scalp')[:len(pos)]                 # hair spec A: roots seen through the hair
    stub = np.maximum(stub, np.clip(scalp_w, 0, 1) * 0.55)
    forehead = front & (pos[:, 2] > eye_z + 0.03) & (pos[:, 2] < eye_z + 0.085) & (np.abs(rel[:, 0]) < 0.05)
    oil = np.clip(forehead * 0.8 + 0.9 * _blob(pos, nose, 0.03), 0, 1)
    wet = np.zeros(len(pos), dtype=np.float32)          # FACE STANDARD 3: moist lower-lid margin + inner corner
    for e in (eye_l, eye_r):
        d = np.linalg.norm(pos - e, axis=1)
        band = (d > 0.0118) & (d < 0.0158) & (pos[:, 2] < e[2] - 0.002) & ((pos[:, 1] - e[1]) < -0.004)
        inner = np.linalg.norm(pos - (e + np.array([-np.sign(e[0] - head[0]) * 0.012, -0.006, -0.001], dtype=np.float32)), axis=1) < 0.004
        wet = np.maximum(wet, (band | inner).astype(np.float32))
    me = human.data
    attr = me.color_attributes.get('skin_regions') or me.color_attributes.new('skin_regions', 'FLOAT_COLOR', 'POINT')
    cols = np.ones((len(me.vertices), 4), dtype=np.float32)
    n = min(len(me.vertices), len(pos))
    cols[:n, 0], cols[:n, 1], cols[:n, 2], cols[:n, 3] = red[:n], stub[:n], oil[:n], 1.0 - wet[:n]
    attr.data.foreach_set('color', cols.ravel())
    done = set()
    for slot in human.material_slots:
        m = slot.material
        if not m or not m.node_tree:
            continue
        for g in [nd for nd in m.node_tree.nodes if nd.type == 'GROUP' and nd.node_tree]:
            if 'Clearcoat' in g.inputs:                               # thin oily layer over the skin
                g.inputs['Clearcoat'].default_value = 0.03
            if 'Clearcoat Roughness' in g.inputs:
                g.inputs['Clearcoat Roughness'].default_value = 0.45
            nt = g.node_tree
            if nt.name in done:
                continue
            done.add(nt.name)
            b = next((x for x in nt.nodes if x.type == 'BSDF_PRINCIPLED'), None)
            if b is None or not b.inputs['Base Color'].is_linked:
                continue
            L = nt.links.new
            at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'skin_regions'
            sep = nt.nodes.new('ShaderNodeSeparateColor'); L(at.outputs['Color'], sep.inputs['Color'])
            col = b.inputs['Base Color'].links[0].from_socket
            blood = nt.nodes.new('ShaderNodeMix'); blood.data_type = 'RGBA'; blood.blend_type = 'MULTIPLY'
            blood.inputs['B'].default_value = (1.0, 0.62, 0.58, 1)
            fac = nt.nodes.new('ShaderNodeMath'); fac.operation = 'MULTIPLY'; fac.inputs[1].default_value = 0.32
            L(sep.outputs['Red'], fac.inputs[0]); L(fac.outputs[0], blood.inputs['Factor'])
            mott = nt.nodes.new('ShaderNodeTexNoise'); mott.inputs['Scale'].default_value = 30; mott.inputs['Detail'].default_value = 3
            tc_ = nt.nodes.new('ShaderNodeTexCoord'); L(tc_.outputs['Object'], mott.inputs['Vector'])
            mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.35; mr.inputs['From Max'].default_value = 0.7
            mr.inputs['To Max'].default_value = 0.14; L(mott.outputs['Fac'], mr.inputs['Value'])
            tone = nt.nodes.new('ShaderNodeMix'); tone.data_type = 'RGBA'; tone.blend_type = 'MULTIPLY'
            tone.inputs['B'].default_value = (0.92, 0.8, 0.76, 1); L(mr.outputs['Result'], tone.inputs['Factor'])
            L(col, tone.inputs['A']); col = tone.outputs['Result']
            L(col, blood.inputs['A'])
            shadow = nt.nodes.new('ShaderNodeMix'); shadow.data_type = 'RGBA'; shadow.blend_type = 'MULTIPLY'
            shadow.inputs['B'].default_value = (0.62, 0.64, 0.72, 1)
            L(sep.outputs['Green'], shadow.inputs['Factor'])
            L(blood.outputs['Result'], shadow.inputs['A'])
            L(shadow.outputs['Result'], b.inputs['Base Color'])
            if b.inputs['Roughness'].is_linked:                       # T-zone shine: rough * (1 - 0.3 * oil)
                r_src = b.inputs['Roughness'].links[0].from_socket
                k = nt.nodes.new('ShaderNodeMath'); k.operation = 'MULTIPLY_ADD'
                L(sep.outputs['Blue'], k.inputs[0]); k.inputs[1].default_value = -0.3; k.inputs[2].default_value = 1.0
                r = nt.nodes.new('ShaderNodeMath'); r.operation = 'MULTIPLY'
                L(r_src, r.inputs[0]); L(k.outputs[0], r.inputs[1])
                wetmix = nt.nodes.new('ShaderNodeMapRange')            # wet lid band: roughness -> 0.06 (tear film)
                L(at.outputs['Alpha'], wetmix.inputs['Value']); wetmix.inputs['To Min'].default_value = 0.06
                wr = nt.nodes.new('ShaderNodeMix'); wr.data_type = 'FLOAT'
                L(at.outputs['Alpha'], wr.inputs['Factor']); wr.inputs['A'].default_value = 0.06
                L(r.outputs[0], wr.inputs['B']); L(wr.outputs['Result'], b.inputs['Roughness'])
            # subsurface: red light travels further than green/blue in skin (mm scale; MakeHuman sets 0.005 m)
            b.subsurface_method = 'RANDOM_WALK_SKIN'
            b.inputs['Subsurface Scale'].default_value = 0.0045   # ~4.5 mm: deeper reads as wax
            for nd in nt.nodes:
                if nd.name == 'SSSStrength' and hasattr(nd, 'outputs') and nd.type == 'VALUE':
                    nd.outputs[0].default_value = max(nd.outputs[0].default_value, 0.6)


def _segment_dist(p, a, b):
    """Distance from points p (N,3) to segment a-b, and position t (0..1) along it."""
    ab = b - a
    t = np.clip(((p - a) @ ab) / (ab @ ab + 1e-12), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1), t


def age_face(human, rig, age=0.6, seed=0):
    """A lived-in face (age 0 = smooth young skin, 1 = deeply lined old man), as real geometry (shape key 'tc-age'):
      nasolabial folds (nose wing -> mouth corner), frown furrows between the brows, soft bags under the eyes;
    plus a 'skin_age' attribute (R = forehead lines, G = crow's feet) that the skin shader turns into fine lines."""
    pos, nor, _ = rest_surface(human)
    lm = landmarks(human, rig, pos)
    nose = np.asarray(lm['nose'], dtype=np.float32)
    mouth_z = float(lm['mouth_top']); mouth_bot = float(lm['mouth_bot'])
    lips = lm['lips']
    lip_pts = pos[lips]
    eye_l = np.asarray(rig.matrix_world @ rig.data.bones['eye.L'].head_local, dtype=np.float32)
    eye_r = np.asarray(rig.matrix_world @ rig.data.bones['eye.R'].head_local, dtype=np.float32)
    eye_z = (eye_l[2] + eye_r[2]) / 2
    head = np.asarray(lm['head'], dtype=np.float32)
    front = (pos[:, 1] - head[1]) < -0.02
    disp = np.zeros(len(pos), dtype=np.float32)               # + = outward along the normal, metres
    for sgn, eye in ((1, eye_l), (-1, eye_r)):
        wing = nose + np.array([sgn * 0.017, 0.012, 0.004], dtype=np.float32)              # side of the nostril
        side = lip_pts[(np.sign(lip_pts[:, 0]) == sgn)]
        corner = side[np.argmax(np.abs(side[:, 0]))] + np.array([sgn * 0.006, 0.0, -0.004], dtype=np.float32)
        d, t = _segment_dist(pos, wing, corner)
        groove = np.exp(-(d / 0.0035) ** 2) * (0.6 + 0.4 * np.sin(np.pi * t))
        cheek = np.exp(-((d - 0.007) / 0.005) ** 2) * (pos[:, 0] * sgn > (wing[0] * sgn)) * 0.5
        disp += front * (-0.0016 * groove + 0.0009 * cheek) * age
        bag_c = eye + np.array([0.0, -0.006, -0.016], dtype=np.float32)                    # under the lower lid
        bag = np.exp(-(((pos - bag_c) / np.array([0.014, 0.01, 0.005])) ** 2).sum(1))
        crease = np.exp(-(((pos - (bag_c + np.array([0, 0, -0.006]))) / np.array([0.013, 0.01, 0.0018])) ** 2).sum(1))
        disp += front * (0.0007 * bag - 0.0006 * crease) * age
    brow_mid = np.array([0.0, nose[1] + 0.012, eye_z + 0.014], dtype=np.float32)          # glabella
    for x in (-0.006, 0.006):
        a = brow_mid + np.array([x, 0, -0.006]); b = brow_mid + np.array([x * 1.3, 0, 0.012])
        d, _ = _segment_dist(pos, a.astype(np.float32), b.astype(np.float32))
        disp += front * -0.0006 * np.exp(-(d / 0.0015) ** 2) * age
    sk = human.data.shape_keys
    basis = human.shape_key_add(name='Basis', from_mix=False) if sk is None else None
    key = human.shape_key_add(name='tc-age', from_mix=False)
    co = np.zeros(len(key.data) * 3, dtype=np.float32); key.data.foreach_get('co', co); co = co.reshape(-1, 3)
    n = min(len(co), len(pos))
    co[:n] += nor[:n] * disp[:n, None]
    key.data.foreach_set('co', co.ravel()); key.value = 1.0
    # fine lines for the shader
    forehead = front & (pos[:, 2] > eye_z + 0.028) & (pos[:, 2] < eye_z + 0.075) & (np.abs(pos[:, 0]) < 0.055)
    crows = np.zeros(len(pos), dtype=np.float32)
    for sgn, eye in ((1, eye_l), (-1, eye_r)):
        c = eye + np.array([sgn * 0.022, 0.006, 0.0], dtype=np.float32)
        crows = np.maximum(crows, np.exp(-(((pos - c) / np.array([0.008, 0.012, 0.011])) ** 2).sum(1)))
    me = human.data
    attr = me.color_attributes.get('skin_age') or me.color_attributes.new('skin_age', 'FLOAT_COLOR', 'POINT')
    cols = np.zeros((len(me.vertices), 4), dtype=np.float32); cols[:, 3] = 1
    cols[:n, 0] = forehead[:n] * age; cols[:n, 1] = crows[:n] * age
    attr.data.foreach_set('color', cols.ravel())
    _age_lines_shader(human)


def _age_lines_shader(human, strength=0.35):
    """Forehead lines (horizontal bands) and crow's feet (diagonal bands at the eye corners), masked by 'skin_age',
    added into the skin's bump chain inside MakeHuman's shared skin group."""
    done = set()
    for slot in human.material_slots:
        m = slot.material
        if not m or not m.node_tree:
            continue
        for g in [nd for nd in m.node_tree.nodes if nd.type == 'GROUP' and nd.node_tree]:
            nt = g.node_tree
            if nt.name in done:
                continue
            done.add(nt.name)
            b = next((x for x in nt.nodes if x.type == 'BSDF_PRINCIPLED'), None)
            if b is None:
                continue
            L = nt.links.new
            at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'skin_age'
            sep = nt.nodes.new('ShaderNodeSeparateColor'); L(at.outputs['Color'], sep.inputs['Color'])
            tc = nt.nodes.new('ShaderNodeTexCoord')
            def bands(direction, scale, mask_out):
                w = nt.nodes.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = direction
                w.inputs['Scale'].default_value = scale; w.inputs['Distortion'].default_value = 2.0
                w.inputs['Detail'].default_value = 2.0; w.inputs['Detail Scale'].default_value = 1.5
                L(tc.outputs['Object'], w.inputs['Vector'])
                inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'POWER'; inv.inputs[1].default_value = 6.0
                L(w.outputs['Fac'], inv.inputs[0])                    # thin sharp creases, not soft stripes
                mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
                L(inv.outputs[0], mul.inputs[0]); L(mask_out, mul.inputs[1])
                return mul.outputs[0]
            fh = bands('Z', 60.0, sep.outputs['Red'])                # Blender bands: period = 2*pi/(10*scale) -> ~1 cm
            cf = bands('DIAGONAL', 150.0, sep.outputs['Green'])       # ~4 mm crow's feet
            add = nt.nodes.new('ShaderNodeMath'); add.operation = 'ADD'
            L(fh, add.inputs[0]); L(cf, add.inputs[1])
            neg = nt.nodes.new('ShaderNodeMath'); neg.operation = 'MULTIPLY'; neg.inputs[1].default_value = -1.0
            L(add.outputs[0], neg.inputs[0])                          # creases go IN
            bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = strength
            bump.inputs['Distance'].default_value = 0.0006
            L(neg.outputs[0], bump.inputs['Height'])
            if b.inputs['Normal'].is_linked:
                L(b.inputs['Normal'].links[0].from_socket, bump.inputs['Normal'])
            L(bump.outputs['Normal'], b.inputs['Normal'])


def _face_mat(o, fn):
    for s in o.material_slots:
        m = s.material
        if m and m.node_tree:
            b = next((x for x in m.node_tree.nodes if x.type == 'BSDF_PRINCIPLED'), None)
            if b is not None:
                fn(m.node_tree, b)


def face_materials(rig, hair_melanin=0.9):
    """Eyes, teeth, brows and lashes (MakeHuman leaves them all matte, roughness 0.7):
      eyes   -> wet: a glossy clear coat like the cornea + tear film (gives the catchlight that makes eyes alive)
      teeth  -> enamel: warm ivory, semi-glossy, slight translucency
      brows / lashes -> darkened to the character's hair colour"""
    dark = max(0.05, 1.0 - hair_melanin)
    for o in [c for c in rig.children if c.type == 'MESH']:
        name = o.name.lower()
        if 'high-poly' in name or name.endswith('eyes'):
            def eye(nt, b):
                b.inputs['Roughness'].default_value = 0.12
                b.inputs['Coat Weight'].default_value = 0.0; b.inputs['Coat Roughness'].default_value = 0.02   # the clear cornea reflects; iris stays matte
                b.inputs['Coat IOR'].default_value = 1.376
                b.inputs['Subsurface Weight'].default_value = 0.0     # subsurface turned brown irises blue-grey
                if b.inputs['Base Color'].is_linked:                # calm the pink sclera veins
                    src = b.inputs['Base Color'].links[0].from_socket
                    hs = nt.nodes.new('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = 0.85
                    hs.inputs['Value'].default_value = 1.0
                    nt.links.new(src, hs.inputs['Color']); nt.links.new(hs.outputs['Color'], b.inputs['Base Color'])
                # CORNEA: MakeHuman maps the clear lens over the iris to the blue disc in the texture's corner
                # (u 0.934, v 0.066). Rendered opaque it puts a lavender cap on the iris; make it a clear wet lens.
                out = next(x for x in nt.nodes if x.type == 'OUTPUT_MATERIAL')
                uv = nt.nodes.new('ShaderNodeUVMap')
                d = nt.nodes.new('ShaderNodeVectorMath'); d.operation = 'DISTANCE'
                d.inputs[1].default_value = (0.934, 0.066, 0.0)
                nt.links.new(uv.outputs['UV'], d.inputs[0])
                mask = nt.nodes.new('ShaderNodeMath'); mask.operation = 'LESS_THAN'; mask.inputs[1].default_value = 0.075
                nt.links.new(d.outputs['Value'], mask.inputs[0])
                clear = nt.nodes.new('ShaderNodeBsdfTransparent')
                gloss = nt.nodes.new('ShaderNodeBsdfGlossy'); gloss.inputs['Roughness'].default_value = 0.0
                fres = nt.nodes.new('ShaderNodeFresnel'); fres.inputs['IOR'].default_value = 1.376
                lens = nt.nodes.new('ShaderNodeMixShader')
                nt.links.new(fres.outputs['Fac'], lens.inputs['Fac'])
                nt.links.new(clear.outputs[0], lens.inputs[1]); nt.links.new(gloss.outputs[0], lens.inputs[2])
                mix = nt.nodes.new('ShaderNodeMixShader')
                nt.links.new(mask.outputs[0], mix.inputs['Fac'])
                nt.links.new(b.outputs[0], mix.inputs[1]); nt.links.new(lens.outputs[0], mix.inputs[2])
                nt.links.new(mix.outputs[0], out.inputs['Surface'])
            _face_mat(o, eye)
        elif 'teeth' in name:
            def teeth(nt, b):
                b.inputs['Roughness'].default_value = 0.28
                b.inputs['Subsurface Weight'].default_value = 0.3
                if b.inputs['Base Color'].is_linked:
                    src = b.inputs['Base Color'].links[0].from_socket
                    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
                    mx.inputs['Factor'].default_value = 1.0; mx.inputs['B'].default_value = (0.92, 0.86, 0.74, 1)
                    nt.links.new(src, mx.inputs['A']); nt.links.new(mx.outputs['Result'], b.inputs['Base Color'])
            _face_mat(o, teeth)
        elif 'eyebrow' in name or 'eyelash' in name:
            def hairy(nt, b):
                if b.inputs['Base Color'].is_linked:
                    src = b.inputs['Base Color'].links[0].from_socket
                    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
                    mx.inputs['Factor'].default_value = 1.0; mx.inputs['B'].default_value = (dark, dark * 0.8, dark * 0.65, 1)
                    nt.links.new(src, mx.inputs['A']); nt.links.new(mx.outputs['Result'], b.inputs['Base Color'])
            _face_mat(o, hairy)


def tan_skin(human, amount, color):
    """Sun-darkened Mediterranean skin. MakeHuman's skin is a node GROUP ("Human.body") shared by every body
    material, so we tint inside that group: every diffuse image texture's colour goes through a MULTIPLY."""
    done = set()
    for slot in human.material_slots:
        m = slot.material
        if not m or not m.node_tree:
            continue
        for g in [n for n in m.node_tree.nodes if n.type == 'GROUP' and n.node_tree]:
            nt = g.node_tree
            if nt.name in done:
                continue
            done.add(nt.name)
            # tint the FINAL colour going into the shader (earlier steps in the group re-blend the texture)
            bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf is None or not bsdf.inputs['Base Color'].is_linked:
                continue
            src = bsdf.inputs['Base Color'].links[0].from_socket
            mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
            mix.inputs['Factor'].default_value = amount; mix.inputs['B'].default_value = (*color, 1)
            nt.links.new(src, mix.inputs['A']); nt.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])


# ------------------------------------------------------------------ geometry at rest pose
def rest_surface(human):
    """Evaluated body at rest (shape keys applied) WITHOUT the helper-mask, so vertex indices match the
    original mesh and its vertex groups. Returns (positions Nx3, normals Nx3, triangles Mx3)."""
    mods = [m for m in human.modifiers if m.type in ('MASK', 'SUBSURF')]
    for m in mods:
        m.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    ev = human.evaluated_get(dg); me = ev.to_mesh()
    me.calc_loop_triangles()
    n = len(me.vertices)
    pos = np.zeros(n * 3, dtype=np.float32); me.vertices.foreach_get('co', pos); pos = pos.reshape(-1, 3)
    nor = np.zeros(n * 3, dtype=np.float32); me.vertices.foreach_get('normal', nor); nor = nor.reshape(-1, 3)
    tris = np.zeros(len(me.loop_triangles) * 3, dtype=np.int32); me.loop_triangles.foreach_get('vertices', tris)
    ev.to_mesh_clear()
    for m in mods:
        m.show_viewport = True
    mw = np.array(human.matrix_world)
    pos = pos @ mw[:3, :3].T + mw[:3, 3]
    return pos, nor @ mw[:3, :3].T, tris.reshape(-1, 3)


def group_weights(human, name):
    """Per-vertex weight (0..1) of one vertex group."""
    w = np.zeros(len(human.data.vertices), dtype=np.float32)
    if name not in human.vertex_groups:
        return w
    gi = human.vertex_groups[name].index
    for v in human.data.vertices:
        for g in v.groups:
            if g.group == gi:
                w[v.index] = g.weight
    return w


def sample_on(tris, pos, nor, vert_mask, count, rng):
    """Area-weighted random points on the triangles whose 3 corners are all inside vert_mask."""
    keep = vert_mask[tris].all(axis=1)
    t = tris[keep]
    a, b, c = pos[t[:, 0]], pos[t[:, 1]], pos[t[:, 2]]
    area = np.linalg.norm(np.cross(b - a, c - a), axis=1) / 2
    if len(t) == 0:
        return np.zeros((0, 3)), np.zeros((0, 3)), np.zeros((0, 3), dtype=int)
    pick = rng.choice(len(t), size=count, p=area / area.sum())
    u, v = rng.random(count), rng.random(count)
    flip = u + v > 1; u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
    p = a[pick] + (b[pick] - a[pick]) * u[:, None] + (c[pick] - a[pick]) * v[:, None]
    nn = nor[t[pick, 0]] * (1 - u - v)[:, None] + nor[t[pick, 1]] * u[:, None] + nor[t[pick, 2]] * v[:, None]
    nn /= np.linalg.norm(nn, axis=1)[:, None] + 1e-9
    return p, nn, t[pick]


def grow(name, roots, normals, lengths, rng, pts=8, flow=(0, 0, -1), flow_amt=0.5, curl_r=0.0, curl_turns=0.0,
         root_r=0.00022, tip_r=0.00005, frizz=0.0015, material=None, lift=0.35, clumps=0, clump_amt=0.0,
         lock_curls=False, flyaway=0.02, thick_var=0.25):
    """Grow one strand per root. Real hair LIES ALONG the skin: the start direction is the flow direction
    projected onto the skin surface, lifted off it by `lift` (0 = flat on the skin, 1 = straight out).
    Optional helix curl, frizz, and CLUMPING: strands are pulled toward the nearest of `clumps` guide strands
    by `clump_amt` toward the tip, which makes locks/curls instead of uniform fur."""
    n = len(roots)
    c = bpy.data.hair_curves.new(name)
    c.add_curves([pts] * n)
    flow = np.array(flow, dtype=np.float32); flow /= np.linalg.norm(flow) + 1e-9
    tangent = flow[None, :] - normals * (normals @ flow)[:, None]                  # flow projected onto the skin
    tangent /= np.linalg.norm(tangent, axis=1)[:, None] + 1e-9
    start_dir = tangent * (1 - lift) + normals * lift
    start_dir /= np.linalg.norm(start_dir, axis=1)[:, None] + 1e-9
    P = np.zeros((n, pts, 3), dtype=np.float32)
    gi = near = None
    if clumps and clump_amt:                                  # which lock (guide strand) every strand belongs to
        gi = rng.choice(n, size=min(clumps, n), replace=False)
        d2 = ((roots[:, None, :] - roots[gi][None, :, :]) ** 2).sum(-1)
        near = d2.argmin(axis=1)
    phase = rng.random(n) * 2 * math.pi
    if lock_curls and near is not None:                       # a lock spirals TOGETHER: shared phase + tiny jitter
        lock_phase = rng.random(len(gi)) * 2 * math.pi
        phase = lock_phase[near] + rng.normal(0, 0.35, n)
    for i in range(pts):
        t = i / (pts - 1)
        d = start_dir * (1 - flow_amt * t) + flow * (flow_amt * t)               # droop toward the flow
        d /= np.linalg.norm(d, axis=1)[:, None] + 1e-9
        base = roots + d * (lengths * t)[:, None]
        if curl_r:
            # curl around the strand direction: two axes perpendicular to d
            ax1 = np.cross(d, np.array([0, 0, 1.0])); ax1 /= np.linalg.norm(ax1, axis=1)[:, None] + 1e-9
            ax2 = np.cross(d, ax1)
            ang = phase + t * curl_turns * 2 * math.pi
            r = curl_r * min(1.0, t * 3)                                         # straight at the root
            base = base + ax1 * (np.cos(ang) * r)[:, None] + ax2 * (np.sin(ang) * r)[:, None]
        if frizz:
            base = base + rng.normal(0, frizz * t, (n, 3))
        P[:, i] = base
    if flyaway:
        # FLYAWAYS (hair spec A): a few % of strands escape their lock - lifted off the surface, wandering at the tip,
        # a little longer. Gives the fine broken silhouette of real hair instead of a solid, sculpted outline.
        fa = rng.random(n) < flyaway
        if fa.any():
            k = int(fa.sum())
            t = np.linspace(0, 1, pts)[None, :, None]
            drift = (normals[fa] * rng.uniform(0.15, 0.5, (k, 1)) + rng.normal(0, 0.6, (k, 3)))[:, None, :]
            P[fa] = P[fa] + drift * (lengths[fa][:, None, None] * 0.35) * t ** 2
    if near is not None:
        # each strand joins its nearest guide strand toward the tip (guides = a random subset of strands)
        G = P[gi]                                                                  # guides: (clumps, pts, 3)
        w = (np.linspace(0, 1, pts) ** 1.5 * clump_amt)[None, :, None]
        offset = (roots - roots[gi][near])[:, None, :]                             # keep each root where it is
        w = np.broadcast_to(w, P.shape).copy()
        if flyaway:
            w[fa] *= 0.25                                                          # flyaways stay out of the lock
        P = P * (1 - w) + (G[near] + offset * (1 - np.linspace(0, 1, pts)[None, :, None])) * w
    c.attributes['position'].data.foreach_set('vector', P.reshape(-1))
    rad = c.attributes.new('radius', 'FLOAT', 'POINT')
    # every strand its own thickness (hair spec A: natural variation, never perfectly uniform strands)
    k = np.exp(rng.normal(0, thick_var, n))[:, None] if thick_var else np.ones((n, 1))
    rad.data.foreach_set('value', (np.linspace(root_r, tip_r, pts)[None, :] * k).astype(np.float32).ravel())
    o = link(bpy.data.objects.new(name, c))
    if material:
        c.materials.append(material)
    return o


def parent_to_bone(obj, rig, bone):
    """Keep obj where it is, but make it follow `bone` from now on."""
    world = obj.matrix_world.copy()
    obj.parent = rig; obj.parent_type = 'BONE'; obj.parent_bone = bone
    bpy.context.view_layer.update()
    obj.matrix_world = world


# ------------------------------------------------------------------ hair styles
def landmarks(human, rig, pos):
    """Face landmarks at rest: head bone base, nose tip (front-most point), mouth (lips group), chin."""
    hb = rig.matrix_world @ rig.data.bones['head'].head_local
    lips = group_weights(human, 'lips') > 0.5
    head_zone = (pos[:, 2] > hb.z - 0.14) & (pos[:, 2] < hb.z + 0.25) & (np.abs(pos[:, 0]) < 0.12)
    front = head_zone & (np.abs(pos[:, 0]) < 0.012)
    nose_i = np.where(front)[0][np.argmin(pos[front][:, 1])]
    lip_z = pos[lips][:, 2]
    chin_zone = front & (pos[:, 2] < lip_z.min())
    chin_i = np.where(chin_zone)[0][np.argmin(pos[chin_zone][:, 1])]      # front-most point below the lips = chin
    return {"head": np.array(hb), "nose": pos[nose_i], "mouth_top": lip_z.max(), "mouth_bot": lip_z.min(),
            "chin": pos[chin_i], "lips": lips}


def edge_fade(pos, inside, roots, width=0.012):
    """0 at the edge of the growing area -> 1 deeper than `width` m inside (real beards and hairlines thin out
    gradually; a hard edge looks painted on)."""
    from mathutils.kdtree import KDTree
    out_pts = pos[~inside]
    if len(out_pts) == 0:
        return np.ones(len(roots))
    kd = KDTree(len(out_pts))
    for i, p in enumerate(out_pts):
        kd.insert(p, i)
    kd.balance()
    d = np.array([kd.find(r)[2] for r in roots])
    return np.clip(d / width, 0, 1)


def _thin(roots, norms, fade, rng, power=0.8):
    keep = rng.random(len(roots)) < (0.15 + 0.85 * fade ** power)
    return roots[keep], norms[keep], fade[keep]


def beard(human, rig, style: dict, seed=1):
    """style: density (strands), length (m at chin), color (melanin), grey, curl."""
    rng = np.random.default_rng(seed)
    pos, nor, tris = rest_surface(human)
    hb = np.array(rig.matrix_world @ rig.data.bones['head'].head_local)
    rel = pos - hb                                    # face coordinates relative to the head bone base
    # The beard area, from MakeHuman's own face regions (measured): jaw + chin + mouth corners + upper lip,
    # plus the cheeks up to the sideburns and a little under the jaw. Never the lips or the nose.
    face_groups = ['jaw', 'risorius03.L', 'risorius03.R', 'levator05.L', 'levator05.R', 'oris07.L', 'oris07.R',
                   'oris01', 'oris03.L', 'oris03.R', 'oris05', 'special04']
    m = np.zeros(len(pos), dtype=bool)
    for g in face_groups:
        m |= group_weights(human, g) > 0.2
    head_w = group_weights(human, 'head') > 0.2
    cheeks = head_w & (rel[:, 2] > -0.075) & (rel[:, 2] < -0.012 + 0.02 * (np.abs(rel[:, 0]) > 0.06)) & (rel[:, 1] < -0.02) & (np.abs(rel[:, 0]) > 0.035) & (np.abs(rel[:, 0]) < 0.075)
    under_jaw = (group_weights(human, 'neck02') > 0.2) & (rel[:, 1] < -0.04) & (rel[:, 2] > -0.125)
    lips = group_weights(human, 'lips') > 0.25
    nose = (rel[:, 2] > -0.011) & (np.abs(rel[:, 0]) < 0.026)                      # keep the nose and nostrils bare (upper lip = moustache)
    inside = (m | cheeks | under_jaw) & ~lips & ~nose & (rel[:, 2] < 0.012)
    roots, norms, _ = sample_on(tris, pos, nor, inside, int(style.get('density', 26000) * 1.6), rng)
    if style.get('moustache') is False:              # Spartan custom: the upper lip is shaved, the beard kept
        lm = landmarks(human, rig, pos)
        rr = roots - np.asarray(lm['nose'])
        lip = (roots[:, 2] > float(lm['mouth_top']) - 0.004) & (np.abs(rr[:, 0]) < 0.032)
        roots, norms = roots[~lip], norms[~lip]
    edge = edge_fade(pos, inside, roots, width=style.get('edge', 0.014))
    roots, norms, edge = _thin(roots, norms, edge, rng)
    r = roots - hb
    # soft upper edge on the cheeks: thin the strands out toward the top instead of a hard line
    cheek_top = np.abs(r[:, 0]) > 0.03
    fade = np.clip((r[:, 2] + 0.045) / 0.035, 0, 1) * cheek_top                   # 0 low on the cheek -> 1 at the top edge
    keep = rng.random(len(roots)) > fade * 0.85
    roots, norms, r, edge = roots[keep], norms[keep], r[keep], edge[keep]
    # length: full on the chin and jaw, shorter on the upper cheeks and moustache
    down = np.clip((0.012 - r[:, 2]) / 0.11, 0, 1)
    length = style.get('length', 0.03) * (0.45 + 0.55 * down) * (0.35 + 0.65 * edge) * rng.uniform(0.75, 1.1, len(roots))
    persian = style.get('style') == 'persian'
    if persian:
        # Achaemenid royal beard (Persepolis reliefs): falls straight down and is CUT SQUARE - every strand ends on
        # one level line `length` below the chin, so length = distance from its root down to that line
        chin_z = float(np.min(roots[:, 2]))
        bottom = chin_z - style.get('length', 0.1)
        side = np.clip(np.abs(roots[:, 0] - float(np.mean(roots[:, 0]))) / 0.06, 0, 1)
        length = np.clip(roots[:, 2] - bottom, 0.01, None) * rng.uniform(0.88, 1.04, len(roots)) * (1 - 0.18 * side ** 2)
    mat = hair_material('beard_mat', melanin=style.get('melanin', 0.9), grey=style.get('grey', 0.0),
                        redness=style.get('redness', 0.08))
    # strands rooted on the jaw move with the jaw (the mouth can open under the beard); the rest ride the head
    jaw_w = group_weights(human, 'jaw')
    from mathutils.kdtree import KDTree
    kd = KDTree(len(pos))
    for i, p in enumerate(pos):
        kd.insert(p, i)
    kd.balance()
    on_jaw = np.array([jaw_w[kd.find(rt)[1]] > 0.5 for rt in roots])
    parts = []
    for bone, sel in (('jaw', on_jaw), ('head', ~on_jaw)):
        if not sel.any():
            continue
        if persian:                                   # straight down, tight corkscrew curls in many small locks
            o = grow('beard_' + bone, roots[sel], norms[sel], length[sel], rng, pts=18, flow=(0, -0.12, -1), flow_amt=0.85,
                     lift=0.12, curl_r=style.get('curl', 0.0035) * 1.1, curl_turns=style.get('turns', 5.0) * 0.8, root_r=0.0001,
                     tip_r=0.00003, frizz=0.0001, material=mat, clumps=int(sel.sum() / 22), clump_amt=0.75, lock_curls=True)   # combed locks, soft curls
            parent_to_bone(o, rig, bone); parts.append(o)
            continue
        o = grow('beard_' + bone, roots[sel], norms[sel], length[sel], rng, pts=12, flow=(0, -0.25, -1), flow_amt=0.72,
                 lift=0.14, curl_r=min(style.get('curl', 0.0016), 0.0018), curl_turns=min(style.get('turns', 1.2), 1.4),
                 root_r=0.00008, tip_r=0.00002, frizz=0.00015, material=mat, clumps=int(sel.sum() / 30), clump_amt=0.3,
                 lock_curls=False)   # groomed: lies along the jaw, soft waves (was lift 0.3 + tight clumps = bushy wool)
        parent_to_bone(o, rig, bone)
        parts.append(o)
    return parts[-1]


def scalp_hair(human, rig, style: dict, seed=2):
    """Short curly Greek hair (or long for gods/old men): grown on MakeHuman's 'scalp' area."""
    rng = np.random.default_rng(seed)
    pos, nor, tris = rest_surface(human)
    scalp = group_weights(human, 'scalp') > 0.3
    roots, norms, _ = sample_on(tris, pos, nor, scalp, int(style.get('density', 30000) * 1.4), rng)
    fade = edge_fade(pos, scalp, roots, width=style.get('edge', 0.012))                   # soft hairline
    roots, norms, fade = _thin(roots, norms, fade, rng)
    length = style.get('length', 0.035) * (0.4 + 0.6 * fade) * rng.uniform(0.75, 1.15, len(roots))
    mat = hair_material('hair_mat', melanin=style.get('melanin', 0.9), grey=style.get('grey', 0.0),
                        redness=style.get('redness', 0.08))
    long_hair = style.get('length', 0.035) > 0.07
    if not long_hair:
        # NATURAL, NOT BUSHY (owner 2026-11-20): strands lie close to the head (lift 0.12, was 0.3 = fur standing up),
        # soft WAVES (small radius, ~1 turn) instead of tight ringlets, little frizz, broad soft locks (fewer, looser
        # clumps). Per-character style values still win, but are scaled into the natural range.
        o = grow('hair', roots, norms, length, rng, pts=12, flow=style.get('flow', (0, 0.6, -1)), flow_amt=style.get('flow_amt', 0.55),
                 curl_r=min(style.get('curl', 0.0022), 0.0026) * 0.8, curl_turns=min(style.get('turns', 1.2), 1.4), root_r=0.00011,
                 tip_r=0.00003, frizz=0.00012, material=mat, lift=min(style.get('lift', 0.12), 0.15),
                 clumps=style.get('clumps', int(len(roots) / 40)), clump_amt=min(style.get('clump_amt', 0.28), 0.3), lock_curls=False)
        parent_to_bone(o, rig, 'head')
        return o
    # LONG hair (Spartans, gods, old men) is COMBED BACK: strands on the front half of the scalp first run back over
    # the crown, then fall down the back and behind the ears; it never hangs over the face (v1 did: one flow for all).
    hb = np.array(rig.matrix_world @ rig.data.bones['head'].head_local)
    rel = roots - hb
    front = rel[:, 1] < 0.02                                             # -Y = the face side
    parts = []
    for tag, sel, flow, amt, lift in (('front', front, (0, 1.0, -0.35), 0.6, 0.05), ('back', ~front, (0, 0.3, -1.0), 0.7, 0.08)):   # lie flat
        if not sel.any():
            continue
        o = grow(f'hair_{tag}', roots[sel], norms[sel], length[sel] * (1.15 if tag == 'front' else 1.0), rng, pts=16,
                 flow=flow, flow_amt=amt, curl_r=style.get('curl', 0.004), curl_turns=style.get('turns', 3.0), root_r=0.00012,
                 tip_r=0.00003, frizz=0.00012, material=mat, lift=lift, clumps=int(sel.sum() / 30), clump_amt=0.85, lock_curls=True)
        parent_to_bone(o, rig, 'head'); parts.append(o)
    return parts[-1]


# ------------------------------------------------------------------ women's hair (gathered up, c. 480 BC)
def _fit_sphere(pts):
    """Least-squares sphere through points (the skull under the scalp): returns centre, radius."""
    A = np.c_[2 * pts, np.ones(len(pts))]
    b = (pts ** 2).sum(1)
    c, *_ = np.linalg.lstsq(A, b, rcond=None)
    centre = c[:3]
    return centre, float(np.sqrt(c[3] + (centre ** 2).sum()))


def hair_bun(human, rig, style: dict, seed=3):
    """Long hair drawn back over the skull into a bun at the back of the head (krobylos), as on Attic vases and
    the Peplos Kore. Each strand: from its root it follows the skull (a great-circle path just above the scalp)
    to the bun, then coils around the bun's centre. style: density, melanin, grey, bun_size (m), lift (m off skull),
    ribbon (rgb or None). Parented to the head bone."""
    from mathutils.bvhtree import BVHTree
    rng = np.random.default_rng(seed)
    pos, nor, tris = rest_surface(human)
    scalp = group_weights(human, 'scalp') > 0.3
    centre, R = _fit_sphere(pos[scalp])
    tree = BVHTree.FromPolygons([tuple(p) for p in pos], [tuple(t) for t in tris])
    roots, norms, _ = sample_on(tris, pos, nor, scalp, style.get('density', 26000), rng)
    lift = style.get('lift', 0.006)
    bun_r = style.get('bun_size', 0.045)
    back = np.array([0.0, 1.0, -0.25]); back /= np.linalg.norm(back)               # +Y = back of the head
    bun_c = centre + back * (R + bun_r * 0.6)
    pts = 14
    n = len(roots)
    P = np.zeros((n, pts, 3), dtype=np.float32)
    for k in range(n):
        u0 = (roots[k] - centre) / np.linalg.norm(roots[k] - centre)
        ang = math.acos(float(np.clip(u0 @ back, -1, 1)))
        axis = np.cross(u0, back); axis /= np.linalg.norm(axis) + 1e-9
        phase = rng.uniform(0, 2 * math.pi)
        for i in range(pts):
            t = i / (pts - 1)
            if t < 0.7:                                           # over the skull toward the bun (slerp)
                s = t / 0.7
                a = ang * s
                u = u0 * math.cos(a) + np.cross(axis, u0) * math.sin(a) + axis * (axis @ u0) * (1 - math.cos(a))
                q = centre + u * (R + 0.03)
                loc, nrm, _, _ = tree.find_nearest(Vector(q))           # sit ON the real skull, not a fitted sphere
                P[k, i] = (np.array(loc) + np.array(nrm) * (lift + 0.003 * math.sin(math.pi * s))) if loc is not None else q
            else:                                                 # coil around the bun
                s = (t - 0.7) / 0.3
                a = phase + s * 2.6 * math.pi
                side = np.cross(back, [0, 0, 1.0]); side /= np.linalg.norm(side)
                up = np.cross(side, back)
                rr = bun_r * (1 - 0.55 * s) * (0.75 + 0.25 * math.cos(phase * 3))      # a round 3D knot, not a disk
                P[k, i] = bun_c + side * rr * math.cos(a) + up * rr * math.sin(a) + back * (bun_r * 0.9 * math.sin(math.pi * s) * math.sin(a * 0.5 + phase))
    wave = np.sin(np.linspace(0, 1, pts)[None, :] * 9 * math.pi + rng.uniform(0, 6.28, (n, 1)))[..., None] * 0.0018
    P += (wave * np.array([1.0, 0.0, 0.6])).astype(np.float32)       # gentle waves: real hair is never a smooth cap
    c = bpy.data.hair_curves.new('hair_bun')
    c.add_curves([pts] * n)
    c.attributes['position'].data.foreach_set('vector', P.reshape(-1))
    rad = c.attributes.new('radius', 'FLOAT', 'POINT')
    rad.data.foreach_set('value', np.tile(np.linspace(0.00012, 0.00006, pts), n).astype(np.float32))
    o = link(bpy.data.objects.new('hair_bun', c))
    c.materials.append(hair_material('hair_bun_mat', melanin=style.get('melanin', 0.9), grey=style.get('grey', 0.0),
                                     redness=style.get('redness', 0.2), rough=0.5))      # matte, not a shiny cap
    parent_to_bone(o, rig, 'head')
    if style.get('ribbon') and style.get('ribbon_ok'):            # ribbon placement needs a fitted path (v2): off
        bpy.ops.mesh.primitive_torus_add(major_radius=R * 1.02, minor_radius=0.004, location=tuple(centre))
        band = bpy.context.object; band.name = 'hair_ribbon'
        band.rotation_euler = (math.radians(75), 0, 0)
        from lib.common import principled
        band.data.materials.append(principled('ribbon', tuple(style['ribbon']), rough=0.6))
        parent_to_bone(band, rig, 'head')
    return o


def brow_strands(human, rig, density=1400, length=0.007, melanin=0.95, grey=0.0, seed=5):
    """Real eyebrow HAIRS instead of MakeHuman's painted brow card (which looks flat in close-ups).
    Roots are taken where the brow card sits (projected onto the skin); hairs lie flat on the skin, growing UP near
    the nose and sweeping OUTWARD toward the temple, as real brows do. Each side rides its brow bone (oculi02.*),
    so frowns and raised brows still move them. The card is then hidden from renders."""
    from mathutils.bvhtree import BVHTree
    card = next((o for o in rig.children if 'eyebrow' in o.name.lower()), None)
    if card is None:
        return []
    rng = np.random.default_rng(seed)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = card.evaluated_get(dg)
    cpts = np.array([ev.matrix_world @ v.co for v in ev.data.vertices])
    body = human.evaluated_get(dg)
    tree = BVHTree.FromObject(body, dg)
    out = []
    mat = hair_material('brow_mat', melanin=melanin, grey=grey, redness=0.15)
    mid_x = 0.0
    for side, sgn in (('L', 1), ('R', -1)):
        pts = cpts[(cpts[:, 0] - mid_x) * sgn > 0.004]
        if len(pts) == 0:
            continue
        inner, outer = np.abs(pts[:, 0]).min(), np.abs(pts[:, 0]).max()
        roots, norms, lens, t_all = [], [], [], []
        for _ in range(density):
            p = pts[rng.integers(len(pts))] + rng.normal(0, 0.0018, 3)      # spread over the whole brow
            loc, nrm, _, _ = tree.find_nearest(Vector(p))
            if loc is None:
                continue
            t = (abs(loc.x) - inner) / max(outer - inner, 1e-6)          # 0 = by the nose, 1 = at the temple
            roots.append(np.array(loc)); norms.append(np.array(nrm)); t_all.append(t)
            lens.append(length * (0.75 + 0.5 * (1 - abs(t - 0.35))) * rng.uniform(0.8, 1.15))
        roots, norms, lens, t_all = map(np.array, (roots, norms, lens, t_all))
        for part, sel, flow in (('in', t_all < 0.3, (sgn * 0.35, 0.0, 1.0)),             # inner hairs grow up
                                ('out', t_all >= 0.3, (sgn * 1.0, 0.0, 0.15))):         # outer hairs sweep out
            if not sel.any():
                continue
            # real brow hairs are VERY fine and lie almost flat on the skin (v1 was thick + lifted = black dashes)
            o = grow(f'brow_{side}_{part}', roots[sel], norms[sel], lens[sel], rng, pts=6, flow=flow, flow_amt=0.25,
                     lift=0.04, root_r=0.00003, tip_r=0.00001, frizz=0.0001, material=mat, clumps=int(sel.sum() / 25),
                     clump_amt=0.12)
            parent_to_bone(o, rig, f'oculi02.{side}')
            out.append(o)
    card.hide_render = True
    return out


def groom(human, rig, spec, seed=0):
    """All hair for a cast spec in one call: scalp hair by style ('bun' = women's gathered hair, default = loose /
    curly hair grown by scalp_hair, whose length/flow handle short Athenian curls and long Spartan hair), plus the
    beard if the spec has one."""
    h = spec.get('hair')
    if h:
        if spec.get('hair_style') == 'bun':
            hair_bun(human, rig, h, seed=seed + 3)
        else:
            scalp_hair(human, rig, h, seed=seed + 2)
    if spec.get('beard'):
        beard(human, rig, spec['beard'], seed=seed + 1)

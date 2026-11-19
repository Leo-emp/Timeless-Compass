# MODERN-ERA DRESS (WS17, Session F): the garments MakeHuman's asset pack doesn't have, built BY CODE over the
# MakeHuman suits, plus a builder for modern extras.
#   lab_coat       - knee-length white cotton coat (scientists, doctors): torso + sleeves grown from the body surface,
#                    a skirt lofted around BOTH legs (a coat hangs as one tube, it isn't trousers), placket + buttons
#   hospital_gown  - short-sleeved, knee-length, washed pale blue-grey cotton with a small print (MKUltra / 1945
#                    hospital test subjects)
#   caps           - cap_garrison (US side cap, WWII), cap_peaked (US officer service cap), cap_peaked_soviet
#                    (furazhka: khaki crown, red band, star), cap_pilotka (Soviet side cap + star), cap_patrol (US OG-107
#                    patrol cap, 1950s-60s), cap_flat (workman's cloth cap), nurse_cap
#   medal_ribbons  - a ribbon bar on a general's left breast
# Sources: US Army Center of Military History (uniform of WWII + Army Green 1954), Manhattan Project photos
# (DOE photo archive / National Archives RG 434: white knee-length lab coats over shirt + tie), Soviet uniform
# regulations of 1958 (side cap with star, officers' peaked cap with coloured band) as seen in period photos.
#
# Every garment is built at REST on a human standing at the origin, then skinned to the skeleton (coats) or riding
# the head bone (caps), so it follows any motion clip. build_modern_person() = the modern-era version of
# blender/lib/crowd.build_person (that one drapes a Greek chiton when a person has no ancient wardrobe).
import math
import random

import bpy
import numpy as np

from lib import cast, life, motion, pose, wardrobe
from lib.common import fabric, link, mesh_obj, principled

# ------------------------------------------------------------------ body measurements (at rest)
_HAND = ('wrist', 'hand', 'finger', 'thumb', 'index', 'middle', 'ring', 'pinky', 'metacarpal')
_HEAD = ('head', 'neck', 'jaw', 'eye', 'tongue', 'teeth', 'special', 'levator', 'oris', 'orbicularis', 'temporalis',
         'risorius', 'mandible', 'nose', 'cheek', 'lip')
_ARM = ('upperarm', 'lowerarm', 'shoulder', 'clavicle')
_LEG = ('upperleg', 'lowerleg', 'foot', 'toe')


def _group_sums(human):
    """For every vertex: summed weight of the hand, head, arm and leg vertex groups (one pass over the mesh)."""
    names = {g.index: g.name.lower() for g in human.vertex_groups}
    kinds = {'hand': _HAND, 'head': _HEAD, 'arm': _ARM, 'leg': _LEG}
    gi_kind = {}
    for gi, nm in names.items():
        for k, pref in kinds.items():
            if any(nm.startswith(p) for p in pref):
                gi_kind[gi] = k; break
    out = {k: np.zeros(len(human.data.vertices), dtype=np.float32) for k in kinds}
    for v in human.data.vertices:
        for g in v.groups:
            k = gi_kind.get(g.group)
            if k:
                out[k][v.index] += g.weight
    return out


def _bone_z(rig, bone, end='head'):
    b = rig.data.bones.get(bone)
    if b is None:
        return None
    return (rig.matrix_world @ (b.head_local if end == 'head' else b.tail_local)).z


def measure(human, rig):
    """Rest-pose landmarks used to cut garments: shoulder, hip, knee heights; head top + size; masks."""
    pos, nor, tris = cast.rest_surface(human)
    g = _group_sums(human)
    head = g['head'] > 0.5
    hz = pos[head, 2]
    m = {'pos': pos, 'nor': nor, 'tris': tris, 'groups': g,
         'neck_z': _bone_z(rig, 'neck01') or float(np.percentile(hz, 2)),
         'hip_z': _bone_z(rig, 'spine05') or float(pos[:, 2].max() * 0.53),
         'knee_z': _bone_z(rig, 'lowerleg01.L') or float(pos[:, 2].max() * 0.28),
         'top': float(hz.max()), 'height': float(pos[:, 2].max())}
    top = pos[head & (pos[:, 2] > m['top'] - 0.06)]                 # the crown: top 6 cm of the head
    m['crown_xy'] = (float(top[:, 0].mean()), float(top[:, 1].mean()))
    hb = pos[head & (pos[:, 2] > m['top'] - 0.14)]                   # head width/depth at brow height
    m['head_w'] = float(np.ptp(hb[:, 0])); m['head_d'] = float(np.ptp(hb[:, 1]))
    return m


# ------------------------------------------------------------------ materials
def cotton(name, color, print_color=None, grime=0.15):
    """Washed cotton twill: fine weave bump, soft sheen, a little grime toward the hem (Z gradient), optional small
    printed pattern (hospital gowns)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = fabric(name, color, rough=0.88, weave_scale=1400)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(tc.outputs['Generated'], sep.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeMapRange'); ramp.inputs['From Min'].default_value = 0.0; ramp.inputs['From Max'].default_value = 0.35
    ramp.inputs['To Min'].default_value = grime; ramp.inputs['To Max'].default_value = 0.0; L(sep.outputs['Z'], ramp.inputs['Value'])
    noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 30
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; L(ramp.outputs['Result'], mul.inputs[0]); L(noise.outputs['Fac'], mul.inputs[1])
    base = nt.nodes.new('ShaderNodeMix'); base.data_type = 'RGBA'; base.inputs['A'].default_value = (*color, 1)
    if print_color:                                                   # tiny repeating diamonds/dots print
        v = nt.nodes.new('ShaderNodeTexVoronoi'); v.inputs['Scale'].default_value = 260; L(tc.outputs['Object'], v.inputs['Vector'])
        dots = nt.nodes.new('ShaderNodeMath'); dots.operation = 'LESS_THAN'; dots.inputs[1].default_value = 0.18
        L(v.outputs['Distance'], dots.inputs[0])
        pm = nt.nodes.new('ShaderNodeMix'); pm.data_type = 'RGBA'; pm.inputs['A'].default_value = (*color, 1)
        pm.inputs['B'].default_value = (*print_color, 1); L(dots.outputs[0], pm.inputs['Factor'])
        L(pm.outputs['Result'], base.inputs['A'])
    base.inputs['B'].default_value = (0.25, 0.22, 0.18, 1); L(mul.outputs[0], base.inputs['Factor'])
    L(base.outputs['Result'], b.inputs['Base Color'])
    return m


def felt(name, color, rough=0.8):
    """Wool felt / gabardine for caps: very fine noise bump, almost no sheen."""
    return bpy.data.materials.get(name) or principled(name, color, rough=rough, bump=0.04, bump_scale=900)


# ------------------------------------------------------------------ coats (lab coat, hospital gown)
def _ring(cx, cy, rx, ry, z, n=48, ex=2.6):
    """Superellipse ring (between an ellipse and a rounded rectangle: the shape of a hanging coat in section)."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        c, s = math.cos(a), math.sin(a)
        pts.append((cx + rx * math.copysign(abs(c) ** (2 / ex), c), cy + ry * math.copysign(abs(s) ** (2 / ex), s), z))
    return pts


def _coat(human, rig, m, name, mat, sleeve='wrist', hem='knee', offset=0.024, flare=0.22):
    """Upper part: the body surface between hip and neck (and the arms down to `sleeve`) pushed out by `offset`.
    Lower part: a skirt lofted from just above the hip to the hem, each ring fitted around BOTH legs at its height
    (and never narrower than the ring above: cloth hangs, it doesn't hug the thighs)."""
    pos, nor, tris, g = m['pos'], m['nor'], m['tris'], m['groups']
    hip, neck = m['hip_z'], m['neck_z']
    keep = (g['head'] < 0.3) & (g['hand'] < 0.3) & (g['leg'] < 0.5) & (pos[:, 2] > hip - 0.02) & (pos[:, 2] < neck + 0.01)
    if sleeve == 'short':                                             # short sleeves: drop everything below the elbow
        elbow = _bone_z(rig, 'lowerarm01.L') or (neck - 0.3)
        keep &= ~((g['arm'] > 0.5) & (pos[:, 2] < elbow + 0.04))
    sel = keep[tris].all(axis=1)
    ft = tris[sel]
    used = np.unique(ft)
    remap = -np.ones(len(pos), dtype=np.int64); remap[used] = np.arange(len(used))
    verts = (pos[used] + nor[used] * offset).tolist()
    faces = remap[ft].tolist()
    # skirt
    hem_z = {'knee': m['knee_z'] - 0.04, 'shin': m['knee_z'] - 0.14}.get(hem, m['knee_z'] + 0.12)
    body_only = (g['arm'] < 0.3) & (g['hand'] < 0.3)
    rings, prev = [], None
    zs = np.linspace(hip + 0.03, hem_z, 12)
    for i, z in enumerate(zs):
        band = pos[body_only & (np.abs(pos[:, 2] - z) < 0.025)]
        if len(band) < 8:
            band = pos[body_only & (np.abs(pos[:, 2] - z) < 0.06)]
        t = i / (len(zs) - 1)
        cx, cy = float(band[:, 0].mean()), float(band[:, 1].mean())
        rx = float(np.ptp(band[:, 0])) / 2 + offset + 0.012 + flare * 0.25 * t
        ry = float(np.ptp(band[:, 1])) / 2 + offset + 0.02 + flare * 0.18 * t
        if prev:                                                      # hanging cloth: never pulls in below the hips
            rx, ry = max(rx, prev[2]), max(ry, prev[3])
        prev = (cx, cy, rx, ry); rings.append(_ring(cx, cy, rx, ry, float(z)))
    base = len(verts); n = len(rings[0])
    for r in rings:
        verts += [list(p) for p in r]
    for i in range(len(rings) - 1):
        for k in range(n):
            a, b = base + i * n + k, base + i * n + (k + 1) % n
            faces.append([a, b, b + n, a + n])
    o = mesh_obj(name, verts, faces, mat)
    for f in o.data.polygons:
        f.use_smooth = True
    # cotton drapes over the body, it doesn't shrink-wrap every muscle: relax the surface (Laplacian-ish smooth,
    # stronger on the torso than at the edges) so the coat reads as one smooth garment, not a quilted shell
    # one clean garment shell: thicken the open surface, VOXEL-REMESH it (closes the source mesh's slits and gives
    # even topology), then relax it so the cotton drapes over the body instead of hugging every muscle/breast;
    # baked (applied) before the bone weights are copied
    so = o.modifiers.new('thickness', 'SOLIDIFY'); so.thickness = 0.008; so.offset = 0.0
    rm = o.modifiers.new('remesh', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.009; rm.use_smooth_shade = True
    sm = o.modifiers.new('drape', 'SMOOTH'); sm.factor = 0.8; sm.iterations = 25
    with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
        for md in list(o.modifiers):
            bpy.ops.object.modifier_apply(modifier=md.name)
    return o


def _placket(coat_m, m, name, mat_btn, n=5, sleeve_top=None):
    """Front edge of a buttoned coat: a slightly darker strip down the centre front + `n` buttons."""
    pos, g = m['pos'], m['groups']
    front_y = float(pos[(g['arm'] < 0.3) & (np.abs(pos[:, 0]) < 0.03) & (pos[:, 2] > m['hip_z']) & (pos[:, 2] < m['neck_z'] - 0.08), 1].min())
    parts = []
    for k in range(n):
        z = m['neck_z'] - 0.14 - k * (m['neck_z'] - m['hip_z'] - 0.05) / max(n - 1, 1) * 1.05
        yb = float(pos[(np.abs(pos[:, 0]) < 0.04) & (np.abs(pos[:, 2] - z) < 0.02) & (g['arm'] < 0.3), 1].min()) - 0.03 \
            if ((np.abs(pos[:, 0]) < 0.04) & (np.abs(pos[:, 2] - z) < 0.02)).any() else front_y - 0.03
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.007, depth=0.004, location=(0.012, yb, z), rotation=(math.pi / 2, 0, 0))
        b = bpy.context.object; b.name = f'{name}_btn{k}'; b.data.materials.append(mat_btn); parts.append(b)
    return parts


def bind(garment, human, rig):
    """wardrobe.bind_to_skeleton with the body's MASK modifiers OFF while the weights are copied (with them on, a
    garment vertex over hidden skin takes the weights of the nearest VISIBLE skin - the hands - and tears)."""
    masks = [m for m in human.modifiers if m.type == 'MASK' and m.show_viewport]
    for m in masks:
        m.show_viewport = False
    bpy.context.view_layer.update()
    try:
        return wardrobe.bind_to_skeleton(garment, human, rig)
    finally:
        for m in masks:
            m.show_viewport = True


def _image_mean_lum(img, n=6000):
    px = np.empty(len(img.pixels), dtype=np.float32); img.pixels.foreach_get(px)
    px = px.reshape(-1, 4)
    idx = np.linspace(0, len(px) - 1, min(n, len(px))).astype(int)
    p = px[idx]; a = p[:, 3] > 0.5
    p = p[a] if a.any() else p
    return float(max(0.02, (0.2126 * p[:, 0] + 0.7152 * p[:, 1] + 0.0722 * p[:, 2]).mean()))


def redye(o):
    """Turn cast._tint_object's MULTIPLY tint into a real DYE: the garment takes the tint colour ON AVERAGE, and the
    texture only adds its light/dark detail (folds, seams, weave), normalised by its own mean brightness. Multiply
    alone makes a black suit + olive = black, so no uniform could ever read olive drab."""
    for slot in o.material_slots:
        m = slot.material
        if not m or not m.node_tree:
            continue
        nt = m.node_tree
        for mx in [n for n in nt.nodes if n.type == 'MIX' and getattr(n, 'blend_type', '') == 'MULTIPLY' and n.data_type == 'RGBA']:
            if not mx.inputs['A'].is_linked:
                continue
            src = mx.inputs['A'].links[0].from_socket
            img = getattr(src.node, 'image', None)
            mean = _image_mean_lum(img) if img is not None else 0.25
            bw = nt.nodes.new('ShaderNodeRGBToBW'); nt.links.new(src, bw.inputs['Color'])
            dv = nt.nodes.new('ShaderNodeMath'); dv.operation = 'DIVIDE'; dv.inputs[1].default_value = mean
            nt.links.new(bw.outputs['Val'], dv.inputs[0])
            cl = nt.nodes.new('ShaderNodeMapRange'); cl.inputs['From Min'].default_value = 0.0; cl.inputs['From Max'].default_value = 2.0
            cl.inputs['To Min'].default_value = 0.35; cl.inputs['To Max'].default_value = 1.6; cl.clamp = True
            nt.links.new(dv.outputs[0], cl.inputs['Value'])
            nt.links.new(cl.outputs['Result'], mx.inputs['A'])


def dye_uniforms(p, human, rig):
    """Re-dye the tinted MakeHuman garments of a modern spec (uniforms, coloured suits)."""
    names = [c[0] for c in p.get('mpfb_clothes', []) if isinstance(c, (list, tuple)) and c[1]]
    for o in [c for c in set(rig.children) | set(human.children) if c.type == 'MESH']:
        if any(n in o.name for n in names):
            redye(o)


def lab_coat(human, rig, m, seed=0):
    """Knee-length white lab coat (slightly warm white: cotton is never pure #fff, and pure white blows out)."""
    rnd = random.Random(seed)
    white = cotton(f'labcoat_{seed}', (0.78 + rnd.uniform(-0.03, 0.02), 0.77, 0.73 + rnd.uniform(-0.02, 0.02)), grime=0.18)
    o = _coat(human, rig, m, f'labcoat_{seed}', white, sleeve='wrist', hem='knee', offset=0.034, flare=0.2)
    btn = bpy.data.materials.get('coat_button') or principled('coat_button', (0.6, 0.6, 0.58), rough=0.3)
    parts = [o] + _placket(o, m, f'labcoat_{seed}', btn)
    for p in parts:
        bind(p, human, rig) if p is o else cast.parent_to_bone(p, rig, 'spine03')
    return o


def hospital_gown(human, rig, m, seed=0):
    """Pale washed blue-grey gown with a tiny print, short sleeves, to the knee."""
    mat = cotton(f'gown_{seed}', (0.48, 0.55, 0.6), print_color=(0.3, 0.36, 0.45), grime=0.12)
    o = _coat(human, rig, m, f'gown_{seed}', mat, sleeve='short', hem='shin', offset=0.03, flare=0.28)
    bind(o, human, rig)
    return o


# ------------------------------------------------------------------ caps (ride the head bone)
def _loft(name, sections, mat, cap_top=True):
    """Mesh through a list of rings (each ring = list of (x, y, z)), closed on top with a fan."""
    n = len(sections[0]); verts = [p for r in sections for p in r]; faces = []
    for i in range(len(sections) - 1):
        for k in range(n):
            a, b = i * n + k, i * n + (k + 1) % n
            faces.append([a, b, b + n, a + n])
    if cap_top:
        top = sections[-1]
        c = (sum(p[0] for p in top) / n, sum(p[1] for p in top) / n, sum(p[2] for p in top) / n)
        verts.append(c); ci = len(verts) - 1; s = (len(sections) - 1) * n
        faces += [[s + k, s + (k + 1) % n, ci] for k in range(n)]
    o = mesh_obj(name, verts, faces, mat)
    for f in o.data.polygons:
        f.use_smooth = True
    return o


def _head_fit(m):
    """Cap band ellipse: a touch bigger than the head at brow height (hair is short in these eras)."""
    return m['crown_xy'][0], m['crown_xy'][1], m['head_w'] / 2 + 0.012, m['head_d'] / 2 + 0.012


def _visor(name, cx, cy, rx, ry, z, reach, drop, m, n=18):
    """Cap visor/brim: quads between the band's front half-ellipse and an outer arc pushed forward by `reach`*sin."""
    inner, outer = [], []
    for a in np.linspace(0, math.pi, n):
        c, s = math.cos(a), math.sin(a)
        inner.append((cx + rx * c, cy - ry * s, z))
        outer.append((cx + (rx + 0.004) * c, cy - (ry + reach * s) * s if s > 0 else cy, z - drop * s * s))
    o = mesh_obj(name, inner + outer, [[k, k + 1, n + k + 1, n + k] for k in range(n - 1)], m)
    for f in o.data.polygons:
        f.use_smooth = True
    o.modifiers.new('t', 'SOLIDIFY').thickness = 0.003
    return o


def _peaked(name, m, crown_m, band_m, visor_m, badge_m, soviet=False):
    cx, cy, rx, ry = _head_fit(m); z0 = m['top'] - 0.07
    band = [_ring(cx, cy, rx, ry, z0 + dz, n=40, ex=2.0) for dz in (0.0, 0.045)]
    b = _loft(name + '_band', band, band_m, cap_top=False)
    # crown: flares out to a wide, flat oval top that rises at the front (the "saddle" of a service cap)
    sec = []
    for dz, s in ((0.045, 1.0), (0.065, 1.18), (0.08, 1.28 if soviet else 1.22)):
        sec.append([(x, y, z + (0.012 if y < cy - ry * 0.5 and dz > 0.07 else 0.0))
                    for (x, y, z) in _ring(cx, cy - 0.006, rx * s, ry * s * 1.05, z0 + dz, n=40, ex=2.0)])
    c = _loft(name + '_crown', sec, crown_m)
    # visor: a half-annulus in front; inner edge = the band's front arc, outer edge 5.5 cm further out at the centre
    # (0 at the sides), sloping down ~25 deg
    vis = _visor(name + '_visor', cx, cy, rx, ry, z0 - 0.002, 0.055, 0.025, visor_m)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.011, depth=0.004, location=(cx, cy - ry - 0.004, z0 + 0.03),
                                        rotation=(math.pi / 2, 0, 0))
    bd = bpy.context.object; bd.name = name + '_badge'; bd.data.materials.append(badge_m)
    return [b, c, vis, bd]


def _side_cap(name, m, mat, tilt_deg=8.0):
    """Garrison cap / pilotka: a folded boat shape along the head (front to back), sitting tilted to the right."""
    cx, cy, rx, ry = _head_fit(m); z0 = m['top'] - 0.045
    secs = []
    for t in np.linspace(-1, 1, 14):                                  # along the head, front (-1) to back (+1)
        y = cy + t * ry * 1.05
        half = rx * 0.82 * math.sqrt(max(0.05, 1 - (t * 0.85) ** 2))
        hgt = 0.06 * (0.75 + 0.25 * (1 - abs(t)))
        secs.append([(cx - half, y, z0), (cx - half * 0.45, y, z0 + hgt * 0.95), (cx, y, z0 + hgt),
                     (cx + half * 0.45, y, z0 + hgt * 0.95), (cx + half, y, z0)])
    verts = [p for s in secs for p in s]; faces = []
    for i in range(len(secs) - 1):
        for k in range(4):
            a = i * 5 + k; faces.append([a, a + 1, a + 6, a + 5])
    o = mesh_obj(name, verts, faces, mat)
    for f in o.data.polygons:
        f.use_smooth = True
    o.modifiers.new('t', 'SOLIDIFY').thickness = 0.004
    # tilt around the front-back axis through the crown (worn over the right side)
    o.data.transform(__import__('mathutils').Matrix.Translation((-cx, 0, -z0)))
    o.data.transform(__import__('mathutils').Matrix.Rotation(math.radians(-tilt_deg), 4, 'Y'))
    o.data.transform(__import__('mathutils').Matrix.Translation((cx + 0.01, 0, z0)))
    return o


def _star(name, loc, r, mat):
    pts = [(loc[0] + (r if k % 2 == 0 else r * 0.42) * math.sin(k * math.pi / 5), loc[1], loc[2] + (r if k % 2 == 0 else r * 0.42) * math.cos(k * math.pi / 5))
           for k in range(10)]
    o = mesh_obj(name, [loc] + pts, [[0, 1 + k, 1 + (k + 1) % 10] for k in range(10)], mat)
    o.modifiers.new('t', 'SOLIDIFY').thickness = 0.002
    return o


def cap(kind, human, rig, m, tint=(0.2, 0.19, 0.1), seed=0):
    """One cap of `kind` fitted to this head and parented to the head bone."""
    name = f'{kind}_{seed}'
    gold = bpy.data.materials.get('cap_gold') or principled('cap_gold', (0.8, 0.6, 0.25), metal=1.0, rough=0.3)
    red = bpy.data.materials.get('cap_red_star') or principled('cap_red_star', (0.55, 0.03, 0.02), rough=0.35)
    leather = bpy.data.materials.get('cap_visor') or principled('cap_visor', (0.015, 0.012, 0.01), rough=0.18)
    cloth = felt(f'cap_cloth_{seed}', tint)
    cx, cy, rx, ry = _head_fit(m)
    parts = []
    if kind == 'cap_peaked':
        parts = _peaked(name, m, cloth, felt('cap_band_dark', (0.03, 0.025, 0.02)), leather, gold)
    elif kind == 'cap_peaked_soviet':
        parts = _peaked(name, m, cloth, felt('cap_band_red', (0.4, 0.02, 0.02), rough=0.7), leather, red, soviet=True)
    elif kind in ('cap_garrison', 'cap_pilotka'):
        parts = [_side_cap(name, m, cloth)]
        if kind == 'cap_pilotka':
            parts.append(_star(name + '_star', (cx - 0.005, cy - ry * 1.02, m['top'] - 0.015), 0.011, red))
    elif kind == 'cap_patrol':                                        # straight-sided flat-top + short visor
        z0 = m['top'] - 0.07
        sec = [_ring(cx, cy - 0.004, rx * s, ry * s, z0 + dz, n=40, ex=2.4) for dz, s in ((0, 1.0), (0.06, 1.02), (0.085, 1.0))]
        parts = [_loft(name + '_crown', sec, cloth)]
        parts.append(_visor(name + '_visor', cx, cy - 0.004, rx, ry, z0 + 0.002, 0.045, 0.015, cloth))
    elif kind == 'cap_flat':                                          # worker's cloth cap: soft top pulled forward
        z0 = m['top'] - 0.05; tweed = felt(f'cap_tweed_{seed}', (0.16, 0.14, 0.11), rough=0.95)
        sec = [_ring(cx, cy - 0.01 * s, rx * s, ry * s * 1.08, z0 + dz, n=40, ex=2.0) for dz, s in ((0, 1.0), (0.025, 1.12), (0.04, 1.08))]
        parts = [_loft(name + '_crown', sec, tweed)]
        parts.append(_visor(name + '_brim', cx, cy - 0.01, rx, ry * 1.08, z0, 0.05, 0.012, tweed))
    elif kind == 'nurse_cap':                                         # small white folded cap on the back of the crown
        bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy + ry * 0.25, m['top'] + 0.012))
        o = bpy.context.object; o.name = name; o.scale = (rx * 1.5, ry * 0.7, 0.035); o.rotation_euler.x = math.radians(-25)
        o.modifiers.new('b', 'BEVEL').width = 0.006
        o.data.materials.append(cotton('nurse_white', (0.82, 0.82, 0.8), grime=0.05)); parts = [o]
    for p in parts:
        cast.parent_to_bone(p, rig, 'head')
    return parts


def medal_ribbons(human, rig, m, rows=3, seed=0):
    """A general's ribbon bar on the left breast: rows of small striped ribbons (colours of WWII US campaign
    ribbons: yellow/red/blue/green stripes)."""
    rnd = random.Random(seed); pos, g = m['pos'], m['groups']
    z0 = m['neck_z'] - 0.17
    chest = pos[(g['arm'] < 0.3) & (np.abs(pos[:, 2] - z0) < 0.02) & (pos[:, 0] > 0.04) & (pos[:, 0] < 0.12)]
    y = float(chest[:, 1].min()) - 0.03 if len(chest) else -0.15
    cols = [(0.7, 0.55, 0.1), (0.5, 0.05, 0.05), (0.05, 0.1, 0.4), (0.1, 0.3, 0.1), (0.8, 0.8, 0.75)]
    parts = []
    for r in range(rows):
        for k in range(3):
            c = rnd.choice(cols)
            mat = bpy.data.materials.get(f'ribbon_{c}') or principled(f'ribbon_{c}', c, rough=0.5)
            bpy.ops.mesh.primitive_cube_add(size=1, location=(0.06 + k * 0.034, y, z0 + r * 0.011))
            o = bpy.context.object; o.name = f'ribbon_{seed}_{r}_{k}'; o.scale = (0.033, 0.004, 0.0095); o.data.materials.append(mat)
            parts.append(o)
    for p in parts:
        cast.parent_to_bone(p, rig, 'spine02')
    return parts


def dress_overlays(p, human, rig, m=None):
    """Add every overlay garment the crowd spec lists (tc/crowd.py WS17 eras -> p['overlays'])."""
    ov = p.get('overlays') or []
    if not ov:
        return []
    m = m or measure(human, rig)
    tint = next((c[1] for c in p.get('mpfb_clothes', []) if 'suit' in c[0] and c[1]), (0.2, 0.19, 0.1))
    out = []
    for name in ov:
        if name == 'lab_coat':
            out.append(lab_coat(human, rig, m, seed=p['seed']))
        elif name == 'hospital_gown':
            out.append(hospital_gown(human, rig, m, seed=p['seed']))
        elif name.startswith('cap_') or name == 'nurse_cap':
            out += cap(name, human, rig, m, tint=tuple(t * 0.9 for t in tint), seed=p['seed'])
        elif name == 'medal_ribbons':
            out += medal_ribbons(human, rig, m, seed=p['seed'])
        # 'tie': MakeHuman's elegant suit already has shirt + tie; nothing to add
    return out


# ------------------------------------------------------------------ the modern extra
def rebind_mpfb_clothes(human, rig):
    """MakeHuman suits added BEFORE the rig get bone weights that tear apart as soon as the arms come down (sleeves
    fold into the crotch, trouser legs cross - verified in spike/lib_stills/modern/debug_agent.png). Fix: throw the
    garment's weights away and copy the BODY's weights onto every garment vertex (nearest point of the body
    surface), at rest pose, then make sure an Armature modifier drives it."""
    # The body's MASK modifier deletes the skin under the clothes - with it on, trouser vertices find the nearest
    # VISIBLE skin, which in the A-pose is the HANDS, and the trousers swing out with the arms. So: mask off.
    masks = [m for m in human.modifiers if m.type == 'MASK' and m.show_viewport]
    for m in masks:
        m.show_viewport = False
    bpy.context.view_layer.update()
    for o in [c for c in set(rig.children) | set(human.children) if c.type == 'MESH' and c is not human]:
        low = o.name.lower()
        if not any(k in low for k in ('suit', 'shoes', 'fedora')):
            continue
        o.vertex_groups.clear()
        dt = o.modifiers.new('weights', 'DATA_TRANSFER')
        dt.object = human; dt.use_vert_data = True; dt.data_types_verts = {'VGROUP_WEIGHTS'}
        dt.vert_mapping = 'POLYINTERP_NEAREST'
        dt.layers_vgroup_select_src = 'ALL'; dt.layers_vgroup_select_dst = 'NAME'
        with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
            bpy.ops.object.modifier_move_to_index(modifier=dt.name, index=0)
            bpy.ops.object.datalayout_transfer(modifier=dt.name)
            bpy.ops.object.modifier_apply(modifier=dt.name)
        if not any(m.type == 'ARMATURE' for m in o.modifiers):
            a = o.modifiers.new('skeleton', 'ARMATURE'); a.object = rig
            with bpy.context.temp_override(object=o, active_object=o):
                bpy.ops.object.modifier_move_to_index(modifier=a.name, index=0)
    for m in masks:
        m.show_viewport = True


def build_modern_person(p, mark=(0, 0, 0), turn_deg=0.0, frames=96, clip=True):
    """One modern-era person from a tc/crowd.py spec: MakeHuman body + suit/uniform (tinted), short hair, overlays
    (lab coat, caps, gown, ribbons), own motion clip with its own offset, life layer. Returns the root empty."""
    before = set(bpy.data.objects)
    human, rig = cast.build_human(p)
    rebind_mpfb_clothes(human, rig)
    dye_uniforms(p, human, rig)
    cast.groom(human, rig, p, seed=p['seed'])
    dress_overlays(p, human, rig)
    mo = p.get('motion') or {}
    name = mo.get('clip') if clip else None
    if name:
        try:
            motion.apply_bvh(rig, name, start=1, hold=0, max_frames=frames, skip=int(mo.get('offset_s', 0) * 24), travel=False)
        except Exception:
            pose.apply_pose(rig, 'stand_relaxed')
    else:
        pose.apply_pose(rig, 'stand_relaxed')
    life.bring_to_life(rig, 1, frames, seed=mo.get('life_seed', p['seed']), standing=not name)
    root = bpy.data.objects.new(f"modern_{p['role']}_{p['seed']}", None); link(root)
    for o in set(bpy.data.objects) - before:
        if o.parent is None and o is not root:
            o.parent = root
    root.location = mark; root.rotation_euler.z = math.radians(turn_deg)
    return root


def modern_crowd(people, marks, frames=96, face_toward=None, clip=True):
    roots, rnd = [], random.Random(len(people))
    for p, mk in zip(people, marks):
        turn = rnd.uniform(-180, 180)
        if face_toward is not None:
            dx, dy = face_toward[0] - mk[0], face_toward[1] - mk[1]
            turn = math.degrees(math.atan2(dx, -dy)) + rnd.gauss(0, 10)
        roots.append(build_modern_person(p, mk, turn, frames, clip=clip))
    return roots

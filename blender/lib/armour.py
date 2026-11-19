# ARMOUR: Greek hoplite kit, c. 480 BC, built from CLEAN shapes fitted to a SMOOTHED copy of the body.
# (The first attempt copied the body surface itself, so the helmet "melted" into the nose and brows.
#  Now: smooth body proxy -> shrinkwrap a clean primitive onto it -> cut openings -> aged bronze.)
# Design sources (not copied art): Corinthian helmets (e.g. Olympia finds, early 5th c. BC), bronze muscle
# cuirasses, greaves and aspis shields known from museum pieces and Attic vase painting.
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib.common import link, mesh_obj, principled, aged_bronze
from lib import cast


# ------------------------------------------------------------------ helpers
def proxy_from(human, mask, name, smooth_factor=1.0, smooth_repeat=20, subdivide=0):
    """A smoothed copy of part of the (posed) body: the triangles whose corners are all in `mask`."""
    pos, nor, tris = cast.rest_surface(human)
    keep = mask[tris].all(axis=1)
    t = tris[keep]
    used = np.unique(t)
    remap = -np.ones(len(pos), dtype=int); remap[used] = np.arange(len(used))
    o = mesh_obj(name, [tuple(p) for p in pos[used]], [tuple(f) for f in remap[t]])
    if subdivide:
        sd = o.modifiers.new('dense', 'SUBSURF'); sd.levels = subdivide          # more points -> no facets after fitting
    sm = o.modifiers.new('smooth', 'SMOOTH'); sm.factor = smooth_factor; sm.iterations = smooth_repeat
    apply_all(o)
    o.hide_render = True; o.hide_viewport = True
    return o


def apply_all(o):
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def shrink_onto(o, target, offset, method='NEAREST_SURFACEPOINT'):
    sw = o.modifiers.new('fit', 'SHRINKWRAP'); sw.target = target; sw.offset = offset; sw.wrap_method = method
    apply_all(o)


def delete_verts(o, test):
    """Delete vertices where test(world_co) is True."""
    import bmesh
    bm = bmesh.new(); bm.from_mesh(o.data)
    mw = o.matrix_world
    dead = [v for v in bm.verts if test(mw @ v.co)]
    bmesh.ops.delete(bm, geom=dead, context='VERTS'); bm.to_mesh(o.data); bm.free()


def boolean_cut(o, cutter):
    b = o.modifiers.new('cut', 'BOOLEAN'); b.operation = 'DIFFERENCE'; b.object = cutter; b.solver = 'EXACT'
    apply_all(o)
    bpy.data.objects.remove(cutter)


def parent_keep(o, rig, bone):
    cast.parent_to_bone(o, rig, bone)


def bone_head(rig, name):
    return rig.matrix_world @ rig.pose.bones[name].head


def bone_tail(rig, name):
    return rig.matrix_world @ rig.pose.bones[name].tail


# ------------------------------------------------------------------ Corinthian helmet
def corinthian_helmet(human, rig, bronze, crest_color=(0.16, 0.008, 0.006)):
    """Whole-face bronze helmet: T opening (two almond eye holes + nose guard + mouth slot), cheek pieces to
    the jaw, flared neck guard, and a horsehair crest grown as real strands. crest_color = (melanin, redness)."""
    pos, nor, tris = cast.rest_surface(human)
    hb = np.array(bone_head(rig, 'head'))
    head_w = cast.group_weights(human, 'head') > 0.25
    for g in ('jaw', 'ears', 'scalp'):
        head_w |= cast.group_weights(human, g) > 0.25
    proxy = proxy_from(human, head_w, 'head_proxy', smooth_factor=1.0, smooth_repeat=80, subdivide=2)
    # clean sphere around the head, fitted onto the smooth proxy
    lo, hi = pos[head_w].min(axis=0), pos[head_w].max(axis=0)
    c = (lo + hi) / 2
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=64, radius=1, location=tuple(c))
    helm = bpy.context.object; helm.name = 'corinthian_helmet'
    helm.scale = tuple((hi - lo) / 2 * 1.25); bpy.ops.object.transform_apply(scale=True)
    shrink_onto(helm, proxy, 0.016)
    sm = helm.modifiers.new('relax', 'SMOOTH'); sm.factor = 0.9; sm.iterations = 15; apply_all(helm)
    # open bottom: down to the jaw at the front, the nape at the back (neck guard)
    fy = lo[1]                                                         # front of the face (min y)
    delete_verts(helm, lambda p: p.z < hb[2] - 0.115 + 0.06 * np.clip((p.y - fy) / 0.2, 0, 1))
    # flare the neck guard and cheek-piece tips a little outward
    for v in helm.data.vertices:
        p = helm.matrix_world @ v.co
        low = np.clip((hb[2] - 0.03 - p.z) / 0.08, 0, 1)
        out = Vector((p.x - c[0], p.y - c[1], 0)).normalized()
        v.co += out * (0.012 * low)
    # sculpt the Corinthian features into the shell (before cutting): a raised nose guard down the middle,
    # embossed brow arches over the eyes, and a soft crease where the skull meets the face plate
    eye_z = hb[2] + 0.062
    for v in helm.data.vertices:
        p = helm.matrix_world @ v.co
        if p.y > fy + 0.06:                                            # only the face side
            continue
        n = Vector((0, -1, 0))
        if abs(p.x) < 0.014 and eye_z - 0.07 < p.z < eye_z + 0.02:     # nose guard
            v.co += n * 0.007 * (1 - abs(p.x) / 0.014)
        dz = p.z - (eye_z + 0.03 - 0.25 * p.x * p.x / 0.004)           # brow arch follows a curve over each eye
        if abs(dz) < 0.008 and 0.008 < abs(p.x) < 0.07:
            v.co += n * 0.004 * (1 - abs(dz) / 0.008)
        if eye_z + 0.05 < p.z < eye_z + 0.06:                          # skull / face plate crease
            v.co -= n * 0.002
    # T opening: two almond eye holes with a nose guard between, and the vertical mouth slot
    cutters = []
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1, depth=0.25, location=(sx * 0.03, fy - 0.02, eye_z),
                                            rotation=(math.pi / 2, 0, 0))
        e = bpy.context.object; e.scale = (0.024, 0.0125, 1); e.rotation_euler[1] = sx * math.radians(-8)
        cutters.append(e)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, fy - 0.02, hb[2] - 0.045))
    slot = bpy.context.object; slot.scale = (0.03, 0.25, 0.085)
    for v in slot.data.vertices:                                       # wider at the mouth, narrow under the nose guard
        if v.co.z < 0:
            v.co.x *= 1.5
    cutters.append(slot)
    for cu in cutters:
        bpy.context.view_layer.objects.active = cu; bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        boolean_cut(helm, cu)
    sol = helm.modifiers.new('thick', 'SOLIDIFY'); sol.thickness = 0.004
    sol.material_offset = 1                                            # inner shell = felt lining (dark eye holes)
    bv = helm.modifiers.new('edge', 'BEVEL'); bv.width = 0.0015; bv.segments = 2
    helm.modifiers.new('smooth', 'SUBSURF').levels = 1
    helm.data.materials.clear(); helm.data.materials.append(bronze)      # booleans can leave an empty slot
    helm.data.materials.append(principled('felt_lining', (0.03, 0.022, 0.018), rough=1.0))
    for poly in helm.data.polygons:
        poly.material_index = 0
    bpy.context.view_layer.objects.active = helm; bpy.ops.object.shade_smooth()
    parent_keep(helm, rig, 'head')
    # crest: a box of red horsehair on top, front to back, made of strands
    rng = np.random.default_rng(7)
    n = 42000
    tt = rng.random(n)                                                  # 0 = front (brow) .. 1 = back (nape)
    ang = math.radians(-55) + tt * math.radians(150)
    top = hi[2] + 0.018
    ry = (hi[1] - lo[1]) / 2 + 0.018
    roots = np.stack([rng.normal(0, 0.006, n), c[1] + np.sin(ang) * ry, c[2] + np.cos(ang) * (top - c[2])], axis=1)
    normals = np.stack([np.zeros(n), np.sin(ang) * 0.4, np.cos(ang) * 0.6 + 0.6], axis=1)
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    length = 0.17 * np.sin(np.pi * (0.08 + 0.85 * tt)) + 0.04
    from lib.common import dyed_hair_material
    crest = cast.grow('crest', roots, normals, length, rng, pts=8, flow=(0, 1.0, -0.9), flow_amt=0.55, lift=1.0,
                      root_r=0.00022, tip_r=0.0001, frizz=0.0025,
                      material=dyed_hair_material('crest_mat', crest_color))
    parent_keep(crest, rig, 'head')
    return helm, crest


# ------------------------------------------------------------------ body armour
def _tube(name, center, rx, ry, z0, z1, seg=96, ring=0.01):
    rings = max(2, int((z1 - z0) / ring) + 1)
    verts, faces = [], []
    for r in range(rings):
        z = z0 + (z1 - z0) * r / (rings - 1)
        for k in range(seg):
            a = 2 * math.pi * k / seg
            verts.append((center[0] + rx * math.cos(a), center[1] + ry * math.sin(a), z))
    for r in range(rings - 1):
        for k in range(seg):
            a, b = r * seg + k, r * seg + (k + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    return mesh_obj(name, verts, faces)


def muscle_cuirass(human, rig, bronze):
    """Bronze muscle cuirass: a clean tube shrink-fitted to a lightly smoothed torso (keeps chest and abdomen
    forms), cut under the arms and at the neck."""
    pos, _, _ = cast.rest_surface(human)
    torso = np.zeros(len(pos), dtype=bool)
    for g in ('spine01', 'spine02', 'spine03', 'spine04', 'spine05', 'breast.L', 'breast.R', 'clavicle.L', 'clavicle.R', 'pelvis.L', 'pelvis.R'):
        torso |= cast.group_weights(human, g) > 0.3
    proxy = proxy_from(human, torso, 'torso_proxy', smooth_factor=0.6, smooth_repeat=8)
    sh_z = (bone_head(rig, 'upperarm01.L').z + bone_head(rig, 'upperarm01.R').z) / 2
    hip_z = (bone_head(rig, 'upperleg01.L').z + bone_head(rig, 'upperleg01.R').z) / 2
    cy = float(pos[torso][:, 1].mean())
    cu = _tube('muscle_cuirass', (0, cy), 0.25, 0.2, hip_z + 0.07, sh_z + 0.07)
    shrink_onto(cu, proxy, 0.016)
    armpit = sh_z - 0.075
    delete_verts(cu, lambda p: p.z > armpit and abs(p.x) > 0.115)                       # arm holes
    delete_verts(cu, lambda p: p.z > sh_z + 0.02 and abs(p.x) < 0.075)                   # neck opening
    cu.modifiers.new('thick', 'SOLIDIFY').thickness = 0.003
    bv = cu.modifiers.new('edge', 'BEVEL'); bv.width = 0.0015; bv.segments = 2
    cu.modifiers.new('smooth', 'SUBSURF').levels = 1
    cu.data.materials.append(bronze)
    bpy.context.view_layer.objects.active = cu; bpy.ops.object.shade_smooth()
    return cu, hip_z + 0.07, cy


def pteruges(hem_z, cy, rx, ry, material, count=26):
    """Leather/linen strips hanging from the cuirass hem (protect the hips)."""
    objs = []
    for k in range(count):
        a = 2 * math.pi * k / count
        x, y = rx * math.cos(a), cy + ry * math.sin(a)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x * 1.04, y, hem_z - 0.1))
        s = bpy.context.object; s.scale = (0.022, 0.004, 0.1)
        s.rotation_euler = (0, 0, a + math.pi / 2)
        tilt = Vector((math.cos(a), math.sin(a), 0)) * 0.06
        s.location += tilt * 0.3
        s.data.materials.append(material)
        objs.append(s)
    return objs


def greaves(human, rig, bronze):
    """Bronze shin guards fitted to each lower leg, open at the back of the calf."""
    pos, _, _ = cast.rest_surface(human)
    out = []
    for side in ('L', 'R'):
        leg = np.zeros(len(pos), dtype=bool)
        for g in (f'lowerleg01.{side}', f'lowerleg02.{side}'):
            leg |= cast.group_weights(human, g) > 0.3
        proxy = proxy_from(human, leg, f'shin_proxy_{side}', smooth_factor=0.8, smooth_repeat=10)
        knee = bone_head(rig, f'lowerleg01.{side}'); ankle = bone_tail(rig, f'lowerleg02.{side}')
        g = _tube(f'greave_{side}', (knee.x, (knee.y + ankle.y) / 2), 0.07, 0.07, ankle.z + 0.06, knee.z + 0.05, seg=64)
        shrink_onto(g, proxy, 0.007)
        sm = g.modifiers.new('relax', 'SMOOTH'); sm.factor = 0.8; sm.iterations = 6; apply_all(g)
        cyl = (knee.y + ankle.y) / 2
        delete_verts(g, lambda p, cyl=cyl, kx=knee.x: (p.y - cyl) > 0.035 and abs(p.x - kx) < 0.025)   # open at the back
        g.modifiers.new('thick', 'SOLIDIFY').thickness = 0.0025
        g.modifiers.new('smooth', 'SUBSURF').levels = 2
        g.data.materials.append(bronze)
        bpy.context.view_layer.objects.active = g; bpy.ops.object.shade_smooth()
        out.append(g)
    return out


# ------------------------------------------------------------------ shield + spear
def emblem_face(name, image_path, wear=0.4):
    """Shield-face material from a painted emblem texture (tc/emblems.py): projected flat from the front (local X/Z,
    as a painter would lay it out), slightly worn - scratches lighten the paint, edges show through."""
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; L = nt.links.new; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(tc.outputs['Object'], sep.inputs[0])
    ux = nt.nodes.new('ShaderNodeMath'); ux.operation = 'MULTIPLY_ADD'; ux.inputs[1].default_value = 1 / 0.92; ux.inputs[2].default_value = 0.5
    uz = nt.nodes.new('ShaderNodeMath'); uz.operation = 'MULTIPLY_ADD'; uz.inputs[1].default_value = 1 / 0.92; uz.inputs[2].default_value = 0.5
    L(sep.outputs['X'], ux.inputs[0]); L(sep.outputs['Z'], uz.inputs[0])
    uv = nt.nodes.new('ShaderNodeCombineXYZ'); L(ux.outputs[0], uv.inputs['X']); L(uz.outputs[0], uv.inputs['Y'])
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(str(image_path), check_existing=True)
    t.extension = 'CLIP'; L(uv.outputs['Vector'], t.inputs['Vector'])
    scratch = nt.nodes.new('ShaderNodeTexNoise'); scratch.inputs['Scale'].default_value = 90; scratch.inputs['Detail'].default_value = 8
    L(tc.outputs['Object'], scratch.inputs['Vector'])
    sc = nt.nodes.new('ShaderNodeMapRange'); sc.inputs['From Min'].default_value = 0.62; sc.inputs['From Max'].default_value = 0.7
    sc.inputs['To Max'].default_value = wear; L(scratch.outputs['Fac'], sc.inputs['Value'])
    worn = nt.nodes.new('ShaderNodeMix'); worn.data_type = 'RGBA'; worn.blend_type = 'SCREEN'
    worn.inputs['B'].default_value = (0.6, 0.5, 0.35, 1); L(sc.outputs['Result'], worn.inputs['Factor'])
    L(t.outputs['Color'], worn.inputs['A']); L(worn.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.6
    return m


def aspis(rig, bronze, emblem_paint=(0.02, 0.02, 0.02), facing_deg=-20.0, emblem_image=None):
    """Round, deeply dished hoplite shield (~0.9 m) on the left forearm, bronze rim. Face: either a painted emblem
    texture from tc/emblems.py (`emblem_image`, every soldier his own) or the default trident on bronze (Athens'
    navy fought under Poseidon)."""
    fa = (bone_head(rig, 'lowerarm01.L') + bone_tail(rig, 'lowerarm01.L')) / 2
    loc = fa + Vector((0.06, -0.17, 0.02))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=1, location=loc)
    sh = bpy.context.object; sh.name = 'aspis'
    for v in sh.data.vertices:                                       # dished: keep the front half, shallow dome
        if v.co.y > 0:
            v.co.y = 0
    sh.scale = (0.46, 0.11, 0.46); bpy.ops.object.transform_apply(scale=True)
    sh.modifiers.new('thick', 'SOLIDIFY').thickness = 0.012
    sh.data.materials.append(emblem_face(f'aspis_face_{rig.name}', emblem_image) if emblem_image else bronze)
    bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_torus_add(major_radius=0.455, minor_radius=0.025, major_segments=96, location=loc,
                                     rotation=(math.pi / 2, 0, 0))
    rim = bpy.context.object; rim.data.materials.append(bronze); bpy.ops.object.shade_smooth()
    # trident emblem: shaft + three prongs, painted (slightly in front of the dome surface) - only without an image
    paint = principled('shield_paint', emblem_paint, rough=0.55)
    parts = []
    if emblem_image:
        group = [sh, rim]
        rot = Matrix.Rotation(math.radians(facing_deg), 4, 'Z')
        for o in group:
            o.matrix_world = Matrix.Translation(loc) @ rot @ Matrix.Translation(-loc) @ o.matrix_world
            cast.parent_to_bone(o, rig, 'lowerarm01.L')
        return group
    def bar(x, z, w, h):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(loc.x + x, loc.y - 0.111, loc.z + z))
        b = bpy.context.object; b.scale = (w, 0.004, h); b.data.materials.append(paint); parts.append(b)
    bar(0, -0.06, 0.018, 0.25)
    bar(0, 0.12, 0.17, 0.016)
    for x in (-0.085, 0, 0.085):
        bar(x, 0.2, 0.016, 0.09)
    group = [sh, rim] + parts
    rot = Matrix.Rotation(math.radians(facing_deg), 4, 'Z')
    for o in group:
        o.matrix_world = Matrix.Translation(loc) @ rot @ Matrix.Translation(-loc) @ o.matrix_world
        cast.parent_to_bone(o, rig, 'lowerarm01.L')
    return group


def dory(rig, bronze, wood):
    """2.5 m ash spear held upright in the right hand, bronze leaf blade, bronze butt-spike (sauroter)."""
    hand = bone_tail(rig, 'wrist.R') if 'wrist.R' in rig.pose.bones else bone_tail(rig, 'lowerarm02.R')
    # the butt spike rests just above the ground; the hand grips the shaft about a third of the way up
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.014, depth=2.4, location=(hand.x, hand.y - 0.01, 1.32))
    shaft = bpy.context.object; shaft.data.materials.append(wood)
    bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=0.03, depth=0.3, location=shaft.location + Vector((0, 0, 1.35)))
    tip = bpy.context.object; tip.scale = (1, 0.25, 1); tip.data.materials.append(bronze)
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=0.016, depth=0.18, location=shaft.location + Vector((0, 0, -1.29)),
                                    rotation=(math.pi, 0, 0))
    butt = bpy.context.object; butt.data.materials.append(bronze)
    for o in (shaft, tip, butt):
        cast.parent_to_bone(o, rig, 'wrist.R' if 'wrist.R' in rig.pose.bones else 'lowerarm02.R')
    return shaft, tip, butt


# ------------------------------------------------------------------ Persian royal regalia
def persian_crown(rig, gold, height=0.2):
    """The Persian king's tall crenellated crown (as on the Persepolis reliefs): a slightly flaring fluted cylinder
    with stepped merlons on top and a jewelled band."""
    head_top = rig.matrix_world @ rig.pose.bones['head'].tail
    hb = rig.matrix_world @ rig.pose.bones['head'].head
    base_z = hb.z + 0.085                                               # sits low on the brow, over the hair
    r0, r1 = 0.108, 0.122
    verts, faces = [], []
    seg = 48
    for ring in range(2):
        z = base_z + ring * height; r = r0 if ring == 0 else r1
        for k in range(seg):
            a = 2 * math.pi * k / seg
            rr = r * (1 + 0.025 * math.cos(a * 16))                       # vertical fluting
            verts.append((hb.x + rr * math.cos(a), hb.y + 0.005 + rr * math.sin(a), z))
    for k in range(seg):
        faces.append((k, (k + 1) % seg, seg + (k + 1) % seg, seg + k))
    crown = mesh_obj('persian_crown', verts, faces, gold)
    crown.modifiers.new('thick', 'SOLIDIFY').thickness = 0.006
    parts = [crown]
    for k in range(12):                                                   # stepped merlons
        a = 2 * math.pi * k / 12
        bpy.ops.mesh.primitive_cube_add(size=1, location=(hb.x + r1 * math.cos(a), hb.y + 0.005 + r1 * math.sin(a), base_z + height + 0.025))
        mm = bpy.context.object; mm.scale = (0.028, 0.008, 0.05); mm.rotation_euler.z = a + math.pi / 2
        mm.data.materials.append(gold); parts.append(mm)
    bpy.ops.mesh.primitive_torus_add(major_radius=r0 + 0.006, minor_radius=0.008, location=(hb.x, hb.y + 0.005, base_z + 0.03))
    band = bpy.context.object; band.data.materials.append(principled('lapis', (0.04, 0.08, 0.3), rough=0.3)); parts.append(band)
    for o in parts:
        cast.parent_to_bone(o, rig, 'head')
    return parts


def follow_body(rig, cuirass=None, pteruges_objs=(), greaves_objs=()):
    """Make the hoplite kit MOVE with the body (marching, fighting): bronze does not bend, so each piece rides
    rigidly on the bone under it - cuirass on the chest (spine02), each greave on its shin, the leather pteruges on
    the hips. The shrink-wrap fits are BAKED first (a live shrinkwrap would pull the armour back to the static body)."""
    if cuirass is not None:
        sw = [m for m in cuirass.modifiers if m.type == 'SHRINKWRAP']
        for m in sw:
            with bpy.context.temp_override(object=cuirass, active_object=cuirass):
                bpy.ops.object.modifier_apply(modifier=m.name)
        cast.parent_to_bone(cuirass, rig, 'spine02')
    for s in pteruges_objs:
        cast.parent_to_bone(s, rig, 'spine05')
    for g in greaves_objs:
        side = 'L' if g.name.endswith('_L') or '_L.' in g.name else 'R'
        cast.parent_to_bone(g, rig, f'lowerleg01.{side}')


# ------------------------------------------------------------------ Persian infantry, 480 BC
def wicker(name='spara_wicker'):
    """Woven wicker (osier) with a leather facing: procedural weave (two crossed wave textures) for the spara."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = principled(name, (0.42, 0.32, 0.18), rough=0.85)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    tc = nt.nodes.new('ShaderNodeTexCoord')
    w1 = nt.nodes.new('ShaderNodeTexWave'); w1.wave_type = 'BANDS'; w1.bands_direction = 'X'; w1.inputs['Scale'].default_value = 60
    w2 = nt.nodes.new('ShaderNodeTexWave'); w2.wave_type = 'BANDS'; w2.bands_direction = 'Z'; w2.inputs['Scale'].default_value = 60
    L(tc.outputs['Object'], w1.inputs['Vector']); L(tc.outputs['Object'], w2.inputs['Vector'])
    mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'; L(w1.outputs['Fac'], mx.inputs[0]); L(w2.outputs['Fac'], mx.inputs[1])
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.6; L(mx.outputs[0], bump.inputs['Height'])
    L(bump.outputs['Normal'], b.inputs['Normal'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.25, 0.18, 0.09, 1); ramp.color_ramp.elements[1].color = (0.55, 0.43, 0.25, 1)
    L(mx.outputs[0], ramp.inputs['Fac']); L(ramp.outputs['Color'], b.inputs['Base Color'])
    return m


def spara(rig, facing_deg=-15.0, w=0.75, h=1.3):
    """The sparabara's big rectangular wicker shield (Herodotus 7.61 'wicker shields'), held on the left forearm,
    slightly curved, its foot near the ground."""
    fa = (bone_head(rig, 'lowerarm01.L') + bone_tail(rig, 'lowerarm01.L')) / 2
    loc = fa + Vector((0.08, -0.2, -0.2))
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=(math.pi / 2, 0, math.radians(facing_deg)))
    s = bpy.context.object; s.name = 'spara'; s.scale = (w, h, 1)
    bpy.ops.object.transform_apply(scale=True)
    sub = s.modifiers.new('sub', 'SUBSURF'); sub.levels = 3; sub.subdivision_type = 'SIMPLE'
    bend = s.modifiers.new('curve', 'SIMPLE_DEFORM'); bend.deform_method = 'BEND'; bend.angle = math.radians(35); bend.deform_axis = 'Z'
    s.modifiers.new('thick', 'SOLIDIFY').thickness = 0.02
    s.data.materials.append(wicker())
    cast.parent_to_bone(s, rig, 'lowerarm01.L')
    return s


def immortal_kit(rig, gold, wood, leather):
    """Persepolis guard / Immortal (Herodotus 7.83): spear with a pomegranate-shaped butt (gold for the 1,000 royal
    guards, silver for the rest), a recurved bow over the left shoulder, a quiver on the back."""
    hand = bone_tail(rig, 'wrist.R') if 'wrist.R' in rig.pose.bones else bone_tail(rig, 'lowerarm02.R')
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.013, depth=2.1, location=(hand.x, hand.y - 0.01, 1.12))
    shaft = bpy.context.object; shaft.data.materials.append(wood)
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=0.025, depth=0.22, location=shaft.location + Vector((0, 0, 1.15)))
    tip = bpy.context.object; tip.data.materials.append(bpy.data.materials.get('aged_bronze') or gold)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.05, location=shaft.location - Vector((0, 0, 1.08)))
    pom = bpy.context.object; pom.scale = (1.0, 1.0, 0.85); pom.data.materials.append(gold)       # the pomegranate
    parts = [shaft, tip, pom]
    for o in parts:
        cast.parent_to_bone(o, rig, 'wrist.R' if 'wrist.R' in rig.pose.bones else 'lowerarm02.R')
    back = bone_head(rig, 'spine01') + Vector((0.06, 0.16, 0.05))
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.06, depth=0.7, location=back, rotation=(0.15, 0.35, 0))
    q = bpy.context.object; q.name = 'quiver'; q.data.materials.append(leather)
    for k in range(6):                                                   # arrow shafts + fletching sticking out
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.004, depth=0.25, location=back + Vector((0.01 * k - 0.025, 0.0, 0.42)),
                                            rotation=(0.15, 0.35, 0))
        a = bpy.context.object; a.data.materials.append(wood); cast.parent_to_bone(a, rig, 'spine01')
    cast.parent_to_bone(q, rig, 'spine01')
    # the bow: a recurved arc slung over the left shoulder
    sh = bone_head(rig, 'clavicle.L')
    cu = bpy.data.curves.new('bow', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.008; cu.bevel_resolution = 2
    sp = cu.splines.new('BEZIER'); pts = [(-0.05, 0.12, -0.45), (0.12, 0.18, 0.0), (-0.05, 0.12, 0.45)]
    sp.bezier_points.add(len(pts) - 1)
    for bp, pnt in zip(sp.bezier_points, pts):
        bp.co = pnt; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    bow = bpy.data.objects.new('bow', cu); bpy.context.scene.collection.objects.link(bow)
    bow.location = sh + Vector((0.05, 0.0, -0.1)); cu.materials.append(wood)
    cast.parent_to_bone(bow, rig, 'spine01')
    return parts + [q, bow]


# ------------------------------------------------------------------ swords + bows
def xiphos(rig, bronze, wood, drawn=True):
    """The hoplite's short sword (~0.6 m leaf-shaped iron blade, cross-guard, wooden grip) - the weapon of the last
    stand at Thermopylae once the spears broke (Herodotus 7.224). Drawn = in the right hand, blade forward."""
    iron = bpy.data.materials.get('blade_iron') or principled('blade_iron', (0.42, 0.42, 0.42), metal=1.0, rough=0.35)
    hand = bone_tail(rig, 'wrist.R') if 'wrist.R' in rig.pose.bones else bone_tail(rig, 'lowerarm02.R')
    bpy.ops.mesh.primitive_cube_add(size=1, location=hand + Vector((0, -0.34, 0)))
    blade = bpy.context.object; blade.name = 'xiphos_blade'; blade.scale = (0.045, 0.6, 0.008)
    bpy.ops.object.transform_apply(scale=True)
    for v in blade.data.vertices:                                     # leaf shape: wide near the tip, point at the end
        t = (hand.y - 0.04 - (blade.matrix_world @ v.co).y) / 0.6     # 0 at the guard -> 1 at the tip
        v.co.x *= 1.0 + 0.35 * math.sin(math.pi * min(max(t, 0), 1) * 0.8) - (0.95 if t > 0.97 else 0)
    blade.data.materials.append(iron)
    bpy.ops.mesh.primitive_cube_add(size=1, location=hand + Vector((0, -0.035, 0)))
    guard = bpy.context.object; guard.scale = (0.12, 0.02, 0.02); guard.data.materials.append(bronze)
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.016, depth=0.1, location=hand + Vector((0, 0.02, 0)),
                                        rotation=(math.pi / 2, 0, 0))
    grip = bpy.context.object; grip.data.materials.append(wood)
    parts = [blade, guard, grip]
    bone = 'wrist.R' if 'wrist.R' in rig.pose.bones else 'lowerarm02.R'
    for o in parts:
        cast.parent_to_bone(o, rig, bone)
    return parts


def toxon(rig, wood, leather, side='L'):
    """A Greek / Scythian-style composite bow held in the bow hand, with a quiver (gorytos) at the hip. Athenian
    archers fought at Plataea in 479 BC (Herodotus 9.22, 9.60); Cretan archers were famous mercenaries."""
    hand = bone_tail(rig, f'wrist.{side}') if f'wrist.{side}' in rig.pose.bones else bone_tail(rig, f'lowerarm02.{side}')
    cu = bpy.data.curves.new('toxon', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.009; cu.bevel_resolution = 2
    sp = cu.splines.new('BEZIER')
    pts = [(0, 0.06, 0.55), (0, -0.05, 0.3), (0, 0.02, 0.0), (0, -0.05, -0.3), (0, 0.06, -0.55)]   # recurved tips
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    bow = bpy.data.objects.new('toxon', cu); bpy.context.scene.collection.objects.link(bow)
    bow.location = hand; cu.materials.append(wood)
    string = bpy.data.curves.new('bowstring', 'CURVE'); string.dimensions = '3D'; string.bevel_depth = 0.0015
    s = string.splines.new('POLY'); s.points.add(1)
    s.points[0].co = (0, 0.06, 0.55, 1); s.points[1].co = (0, 0.06, -0.55, 1)
    st = bpy.data.objects.new('bowstring', string); bpy.context.scene.collection.objects.link(st)
    st.location = hand; string.materials.append(bpy.data.materials.get('sinew') or principled('sinew', (0.6, 0.55, 0.45), rough=0.6))
    hip = bone_head(rig, 'pelvis.R') if 'pelvis.R' in rig.pose.bones else bone_head(rig, 'spine05')
    bpy.ops.mesh.primitive_cube_add(size=1, location=hip + Vector((0.12, 0.05, -0.05)))
    q = bpy.context.object; q.name = 'gorytos'; q.scale = (0.05, 0.16, 0.36); q.rotation_euler = (0.25, 0, 0.2)
    q.data.materials.append(leather)
    bone = f'wrist.{side}' if f'wrist.{side}' in rig.pose.bones else f'lowerarm02.{side}'
    for o in (bow, st):
        cast.parent_to_bone(o, rig, bone)
    cast.parent_to_bone(q, rig, 'spine05' if 'spine05' in rig.pose.bones else 'root')
    return bow, st, q


def tuck_hair_under(helm, hair_objects, margin=0.004):
    """Hair under a closed helmet: every strand point that would stick OUT through the bronze shell (above its
    open bottom edge) is collapsed to zero radius, so the strand ends inside the helmet. Hair that falls below the
    rim (a Spartan's long hair down the back) stays. Uses a BVH of the helmet shell + the inside/outside test from
    the closest surface normal."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(helm, dg)
    zs = [(helm.matrix_world @ v.co).z for v in helm.data.vertices]
    rim = min(zs)
    inv = helm.matrix_world.inverted()
    for h in hair_objects:
        if h.type != 'CURVES':
            continue
        c = h.data
        pos = c.attributes['position'].data
        rad = c.attributes.get('radius')
        if rad is None:
            continue
        hidden = 0
        for ci, curve in enumerate(c.curves):
            start, n = curve.first_point_index, curve.points_length
            cut = None
            for k in range(n):
                pw = h.matrix_world @ Vector(pos[start + k].vector)
                if pw.z < rim:
                    break                                  # below the helmet: free hair
                loc, nrm, _, dist = bvh.find_nearest(inv @ pw)
                if loc is not None and (inv @ pw - loc).dot(nrm) > -margin:   # on / outside the shell
                    cut = k
                    break
            if cut is not None:
                for k in range(cut, n):
                    rad.data[start + k].value = 0.0
                hidden += 1
        print(f'tuck_hair_under: {hidden} strands of {h.name} end inside the helmet')


def helmet_up(rig, parts, angle_deg=-38.0, lift=0.075):
    """Wear the Corinthian helmet PUSHED UP on top of the head, face open - how Greek vase painters show hoplites
    off the battle line, talking, resting, pouring libations. Tilts the shell back about a pivot behind the crown."""
    from mathutils import Matrix
    hb = bone_head(rig, 'head')
    pivot = Vector((hb.x, hb.y + 0.07, hb.z + 0.13))
    M = Matrix.Translation(pivot + Vector((0, 0.01, lift))) @ Matrix.Rotation(math.radians(angle_deg), 4, 'X') @ Matrix.Translation(-pivot)
    for o in parts:
        o.matrix_world = M @ o.matrix_world
    bpy.context.view_layer.update()

# Spike (throwaway): a Greek hoplite, 480 BC, built from a free MakeHuman (CC0) body in Blender.
# Armour is GROWN FROM THE BODY: we copy body regions (torso, shins, head), push them outward and
# make them bronze -> muscle cuirass, greaves, Corinthian helmet that fit him exactly and move with his skeleton.
# Run:  blender -b --python hoplite.py -- <out.png> [samples]
import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix
from bl_ext.blender_org.mpfb.services.humanservice import HumanService
from bl_ext.blender_org.mpfb.services.objectservice import ObjectService

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else os.path.join(os.path.dirname(__file__), 'hoplite.png')
SAMPLES = int(argv[1]) if len(argv) > 1 else 64
SHOT = argv[2] if len(argv) > 2 else 'med'      # 'med' = knees up, 'head' = helmet close-up
DATA = os.path.join(os.environ['APPDATA'], 'Blender Foundation', 'Blender', '5.3', 'extensions', '.user', 'blender_org', 'mpfb', 'data')
A = lambda *p: os.path.join(DATA, *p)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# =============================== MATERIALS ===============================
def mat(name, color, metal=0.0, rough=0.5, bump=0.0, scale=60.0, emit=None):
    # fake user: MakeHuman purges unused materials
    m = bpy.data.materials.new(name); m.use_fake_user = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Metallic'].default_value = metal; b.inputs['Roughness'].default_value = rough
    if bump:   # hammered / woven surface
        n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump
        nt.links.new(n.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    if emit: b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = 3
    return m
BRONZE = mat('bronze', (0.78, 0.48, 0.22), metal=1, rough=0.32, bump=0.15, scale=80)
CREST = mat('crest', (0.42, 0.04, 0.03), rough=0.8, bump=0.6, scale=400)
CLOAK = mat('cloak', (0.38, 0.04, 0.03), rough=0.85, bump=0.2, scale=200)
LINEN = mat('linen', (0.80, 0.74, 0.62), rough=0.9, bump=0.2, scale=300)
LEATHER = mat('leather', (0.25, 0.13, 0.06), rough=0.7, bump=0.2)
WOOD = mat('wood', (0.30, 0.18, 0.09), rough=0.6)
BEARD = mat('beard', (0.035, 0.022, 0.015), rough=0.9, bump=0.8, scale=500)

# =============================== THE MAN ===============================
macro = {"gender": 1.0, "age": 0.6, "muscle": 0.9, "weight": 0.55, "proportions": 0.75, "height": 0.6,
         "cupsize": 0.5, "firmness": 0.5, "race": {"asian": 0.05, "caucasian": 0.8, "african": 0.15}}
human = HumanService.create_human(macro_detail_dict=macro)
HumanService.set_character_skin(A('skins', 'middleage_caucasian_male', 'middleage_caucasian_male.mhmat'), human)
for typ, f in [('Eyes', ('eyes', 'high-poly', 'high-poly.mhclo')), ('Eyebrows', ('eyebrows', 'eyebrow001', 'eyebrow001.mhclo')),
               ('Eyelashes', ('eyelashes', 'eyelashes01', 'eyelashes01.mhclo')), ('Teeth', ('teeth', 'teeth_base', 'teeth_base.mhclo'))]:
    HumanService.add_mhclo_asset(A(*f), human, asset_type=typ, material_type='MAKESKIN')
HumanService.add_builtin_rig(human, 'default', import_weights=True)
rig = ObjectService.find_object_of_type_amongst_nearest_relatives(human, 'Skeleton')

# sun-tanned skin: multiply the skin colour
for slot in human.material_slots:
    m = slot.material
    if not m or not m.node_tree: continue
    b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b and b.inputs['Base Color'].is_linked:
        src = b.inputs['Base Color'].links[0].from_socket
        mix = m.node_tree.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 0.75; mix.inputs['B'].default_value = (0.78, 0.55, 0.4, 1)
        m.node_tree.links.new(src, mix.inputs['A']); m.node_tree.links.new(mix.outputs['Result'], b.inputs['Base Color'])

# =============================== POSE ===============================
def aim(name, direction):
    """Rotate a bone so it points along `direction` (armature space), keeping its head where it is."""
    bpy.context.view_layer.update()
    pb = rig.pose.bones[name]; h = pb.head.copy()
    q = (pb.tail - pb.head).rotation_difference(Vector(direction).normalized())
    pb.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ pb.matrix
    bpy.context.view_layer.update()
# character faces -Y; his right side is -X
aim('upperarm01.R', (-0.18, -0.12, -1)); aim('lowerarm01.R', (-0.05, -1.0, 0.25))      # spear hand forward at the waist
aim('upperarm01.L', (0.25, -0.35, -1)); aim('lowerarm01.L', (-0.35, -1.0, 0.15))        # shield arm across the front
aim('upperleg01.L', (0.06, -0.12, -1)); aim('upperleg01.R', (-0.05, 0.08, -1))          # one foot forward
aim('lowerleg01.L', (0.04, 0.02, -1)); aim('lowerleg01.R', (-0.04, 0.10, -1))
# fists: curl every finger joint (gripping spear + shield handle)
for side in ('L', 'R'):
    for f in range(1, 6):
        for j in range(1, 4):
            pb = rig.pose.bones.get(f'finger{f}-{j}.{side}')
            if pb: pb.rotation_mode = 'XYZ'; pb.rotation_euler = (math.radians(55 if f > 1 else 25), 0, 0)
bpy.context.view_layer.update()

# =============================== ARMOUR GROWN FROM THE BODY ===============================
def shell(name, groups, material, push, thick, keep=None, extra_groups_min=0.45):
    """Copy the body where these bone-groups dominate, push it outward, give it thickness."""
    o = human.copy(); o.data = human.data.copy(); o.name = name
    scene.collection.objects.link(o)
    for md in list(o.modifiers):
        if md.type != 'ARMATURE': o.modifiers.remove(md)
    idx = {o.vertex_groups[g].index for g in groups if g in o.vertex_groups}
    bm = bmesh.new(); bm.from_mesh(o.data); dl = bm.verts.layers.deform.active
    # rest-pose bounds, for "keep" filters
    dead = []
    for v in bm.verts:
        w = sum(v[dl].get(i, 0) for i in idx)
        if w < extra_groups_min or (keep and not keep(co[v.index])): dead.append(v)
    bmesh.ops.delete(bm, geom=dead, context='VERTS'); bm.to_mesh(o.data); bm.free()
    o.data.materials.clear(); o.data.materials.append(material)
    d = o.modifiers.new('push', 'DISPLACE'); d.strength = push; d.mid_level = 0
    s = o.modifiers.new('thick', 'SOLIDIFY'); s.thickness = thick; s.offset = 1
    o.modifiers.new('smooth', 'SUBSURF').levels = 2
    return o

# rest-pose landmarks. The body shape lives in SHAPE KEYS, so mix them to get the real rest coordinates.
def keyed_coords(o):
    me = o.data; kb = me.shape_keys.key_blocks if me.shape_keys else None
    if not kb: return [o.matrix_world @ v.co for v in me.vertices]
    base = kb[0].data; out = [Vector(base[i].co) for i in range(len(me.vertices))]
    for k in kb[1:]:
        if k.value == 0 or k.mute: continue
        for i in range(len(out)): out[i] += (k.data[i].co - base[i].co) * k.value
    return [o.matrix_world @ c for c in out]
co = keyed_coords(human)
TOP = max(c.z for c in co)
headb = rig.data.bones['head']; HEADZ = (rig.matrix_world @ headb.head_local).z
NECKZ = (rig.matrix_world @ rig.data.bones['neck01'].head_local).z
print('top', TOP, 'head', HEADZ, 'neck', NECKZ)

shell('cuirass', ['spine01', 'spine02', 'spine03', 'spine04', 'spine05', 'breast.L', 'breast.R', 'clavicle.L', 'clavicle.R'],
      BRONZE, 0.022, 0.006, keep=lambda c: c.z < NECKZ - 0.02)
shell('chiton_skirt', ['pelvis.L', 'pelvis.R', 'upperleg01.L', 'upperleg01.R'], LINEN, 0.03, 0.004,
      keep=lambda c: c.z > TOP * 0.43)
shell('greaves', ['lowerleg01.L', 'lowerleg01.R', 'lowerleg02.L', 'lowerleg02.R'], BRONZE, 0.012, 0.004,
      keep=lambda c: c.z > 0.09)

# Corinthian helmet: the head shell, minus the T-shaped opening (eye band + vertical slot for nose/mouth)
def helmet_keep(c):
    front = c.y < -0.06                                     # the face side
    eye_band = HEADZ + 0.045 < c.z < HEADZ + 0.085 and abs(c.x) < 0.07
    slot = c.z < HEADZ + 0.085 and abs(c.x) < 0.025
    below_jaw = c.z < HEADZ - 0.075
    return not (front and (eye_band or slot)) and not below_jaw
helm = shell('helmet', ['head', 'jaw', 'neck03'] + [b.name for b in rig.data.bones if b.name.startswith(('oris', 'levator', 'oculi', 'orbicularis', 'risorius', 'temporalis', 'special'))],
             BRONZE, 0.03, 0.007, keep=helmet_keep, extra_groups_min=0.3)

# beard: lower face shell, visible through the helmet slot
shell('beard', ['jaw', 'head'] + [b.name for b in rig.data.bones if b.name.startswith(('oris', 'risorius', 'levator'))], BEARD, 0.012, 0.01,
      keep=lambda c: c.z < HEADZ + 0.015 and c.y < 0.0 and c.z > HEADZ - 0.09, extra_groups_min=0.3)

# ---- crest: a tall horsehair ridge from brow to nape, attached to the head bone ----
def attach(o, bone):
    o.parent = rig; o.parent_type = 'BONE'; o.parent_bone = bone
    o.matrix_parent_inverse = (rig.matrix_world @ Matrix.Translation(rig.pose.bones[bone].tail)).inverted()
def mesh_obj(name, verts, faces, material):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o); o.data.materials.append(material); return o
hz = (rig.matrix_world @ rig.pose.bones['head'].head).z
hy = (rig.matrix_world @ rig.pose.bones['head'].head).y
pts = []
for i in range(17):            # arc over the top of the helmet (front -> back)
    a = math.radians(-70 + i * 140 / 16)
    pts.append(Vector((0, hy + math.sin(a) * 0.125, hz + 0.07 + math.cos(a) * 0.13)))
verts, faces = [], []
for i, p in enumerate(pts):
    h = 0.12 * math.sin(math.pi * (0.15 + 0.85 * i / 16)) + 0.03
    up = (p - Vector((0, hy, hz + 0.05))).normalized()
    for w in (-0.022, 0.022):
        verts += [p + Vector((w, 0, 0)), p + up * h + Vector((w * 0.6, 0, 0))]
for i in range(16):
    for s in range(2):
        a = i * 4 + s * 2; b = a + 4
        faces.append((a, b, b + 1, a + 1))
    faces.append((i * 4 + 1, i * 4 + 5, i * 4 + 7, i * 4 + 3))
crest = mesh_obj('crest', verts, faces, CREST); crest.modifiers.new('s', 'SUBSURF').levels = 1
attach(crest, 'head')

# ---- aspis: big round bronze-faced shield on the left forearm ----
la = rig.pose.bones['lowerarm01.L']; c = rig.matrix_world @ ((la.head + la.tail) / 2)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.44, location=c + Vector((0.16, -0.10, 0.0)), segments=48, ring_count=24)
sh = bpy.context.object; sh.name = 'aspis'; sh.scale = (1, 0.18, 1); sh.rotation_euler = (0, 0, math.radians(-35)); sh.data.materials.append(BRONZE)
bpy.ops.object.shade_smooth()
bpy.ops.mesh.primitive_torus_add(major_radius=0.44, minor_radius=0.022, location=sh.location, rotation=(math.pi / 2, 0, math.radians(-35)))
rim = bpy.context.object; rim.data.materials.append(BRONZE); bpy.ops.object.shade_smooth()
# lambda (Λ) for Lacedaemon painted on the shield face
lam = mesh_obj('lambda', [(-0.2, 0, -0.22), (-0.13, 0, -0.22), (0, 0, 0.16), (0.13, 0, -0.22), (0.2, 0, -0.22), (0.035, 0, 0.26), (-0.035, 0, 0.26)],
               [(0, 1, 2, 6), (2, 3, 4, 5), (2, 5, 6)], mat('paint', (0.35, 0.03, 0.02), rough=0.6))
lam.location = sh.location + Matrix.Rotation(math.radians(-35), 3, 'Z') @ Vector((0, -0.083, 0)); lam.rotation_euler = (0, 0, math.radians(-35))

# ---- dory: 2.4 m spear held upright in the right hand ----
wr = rig.matrix_world @ rig.pose.bones['wrist.R'].head
bpy.ops.mesh.primitive_cylinder_add(radius=0.016, depth=2.5, location=wr + Vector((0, -0.05, 0.55)))
shaft = bpy.context.object; shaft.data.materials.append(WOOD)
bpy.ops.mesh.primitive_cone_add(radius1=0.035, depth=0.28, location=shaft.location + Vector((0, 0, 1.38)))
tip = bpy.context.object; tip.scale = (1, 0.3, 1); tip.data.materials.append(BRONZE)

# ---- red cloak hanging from the shoulders down the back ----
sp = rig.matrix_world @ rig.pose.bones['spine05'].tail
cv, cf = [], []
for r in range(8):
    for c2 in range(9):
        t = c2 / 8 - 0.5; z = sp.z + 0.02 - r * 0.2; spread = 0.24 + r * 0.035
        cv.append((t * spread * 2, sp.y + 0.13 + r * 0.03 + 0.04 * math.cos(t * math.pi) + 0.02 * math.sin(r * 1.3 + c2), z))
for r in range(7):
    for c2 in range(8):
        a = r * 9 + c2; cf.append((a, a + 1, a + 10, a + 9))
cloak = mesh_obj('cloak', cv, cf, CLOAK)
cloak.modifiers.new('t', 'SOLIDIFY').thickness = 0.008; cloak.modifiers.new('s', 'SUBSURF').levels = 2

for o in [human]: o.modifiers.new('smooth', 'SUBSURF').levels = 1

# =============================== THE WORLD: Thermopylae at sunset ===============================
world = bpy.data.worlds.new('sky'); scene.world = world
nt = world.node_tree; bgn = nt.nodes['Background']
sky = nt.nodes.new('ShaderNodeTexSky')
try: sky.sky_type = 'NISHITA'
except Exception: pass
for attr, val in [('sun_elevation', math.radians(3)), ('sun_rotation', math.radians(200)), ('air_density', 2.0), ('dust_density', 4.0)]:
    if hasattr(sky, attr): setattr(sky, attr, val)
nt.links.new(sky.outputs['Color'], bgn.inputs['Color']); bgn.inputs['Strength'].default_value = 0.35
# low sun behind him (rim light) + cool sky fill
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); scene.collection.objects.link(sun)
sun.data.energy = 6; sun.data.color = (1.0, 0.55, 0.28); sun.data.angle = math.radians(2)
sun.rotation_euler = (math.radians(84), 0, math.radians(200))
fill = bpy.data.objects.new('fill', bpy.data.lights.new('fill', 'AREA')); scene.collection.objects.link(fill)
fill.data.energy = 260; fill.data.size = 3; fill.data.color = (1.0, 0.72, 0.5)
fill.location = (1.8, -3.2, 1.9); fill.rotation_euler = (Vector((0, 0, 1.3)) - fill.location).to_track_quat('-Z', 'Y').to_euler()
# rocky ground and the cliffs of the pass
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0)); g = bpy.context.object
g.data.materials.append(mat('rock', (0.32, 0.24, 0.18), rough=0.95, bump=0.5, scale=8))
sd = g.modifiers.new('sub', 'SUBSURF'); sd.subdivision_type = 'SIMPLE'; sd.levels = 6
tex = bpy.data.textures.new('n', 'CLOUDS'); tex.noise_scale = 1.5
dp = g.modifiers.new('d', 'DISPLACE'); dp.texture = tex; dp.strength = 0.25
ROCK = mat('mtn', (0.20, 0.15, 0.14), rough=1, bump=1.0, scale=2)
for (x, y, r, h) in [(-40, 70, 30, 18), (10, 90, 40, 26), (55, 75, 28, 15), (-80, 95, 45, 30)]:
    bpy.ops.mesh.primitive_ico_sphere_add(radius=1, subdivisions=4, location=(x, y, 0)); m2 = bpy.context.object
    m2.scale = (r, r * 0.5, h); m2.data.materials.append(ROCK)
    d2 = m2.modifiers.new('d', 'DISPLACE'); t3 = bpy.data.textures.new('m', 'CLOUDS'); t3.noise_scale = 0.4; d2.texture = t3; d2.strength = 0.25
# =============================== CAMERA: heroic low angle, knees up ===============================
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scene.collection.objects.link(cam); scene.camera = cam
cam.data.lens = 50
if SHOT == 'full':
    cam.data.lens = 40; cam.location = Vector((-2.6, -5.2, 1.1)); target = Vector((0.1, 0, 0.95))
elif SHOT == 'head':
    cam.data.lens = 85; cam.location = Vector((-0.75, -1.45, 1.78)); target = Vector((0.0, 0, 1.72))
else:
    cam.location = Vector((-1.7, -3.6, 1.05)); target = Vector((0.1, 0, 1.15))
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.dof.use_dof = True; cam.data.dof.focus_distance = (target - cam.location).length; cam.data.dof.aperture_fstop = 2.2

ENGINE = os.environ.get('ENGINE', 'CYCLES')
if ENGINE == 'EEVEE':
    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = 16
else:
    scene.render.engine = 'CYCLES'; scene.cycles.samples = SAMPLES; scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = 'AgX - Punchy'
scene.render.filepath = OUT
import time
t0 = time.time(); bpy.ops.render.render(write_still=True); print('RENDER1', round(time.time() - t0, 1))
t0 = time.time(); bpy.ops.render.render(write_still=True); print('RENDER2', round(time.time() - t0, 1))
print('saved', OUT)

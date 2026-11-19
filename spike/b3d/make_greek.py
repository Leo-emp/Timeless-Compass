# Spike (throwaway) - Blender + MPFB (MakeHuman, CC0): build a Greek man, dress him, render a still.
# Run:  blender -b --python make_greek.py -- <variant> <out.png>
#   variant: "face" (portrait test), "hoplite", "zeus"
import bpy, sys, os, math
from mathutils import Vector
from bl_ext.blender_org.mpfb.services.humanservice import HumanService
from bl_ext.blender_org.mpfb.services.objectservice import ObjectService

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
VARIANT = argv[0] if argv else 'face'
OUT = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(__file__), f'{VARIANT}.png')
DATA = os.path.join(os.environ['APPDATA'], 'Blender Foundation', 'Blender', '5.3', 'extensions', '.user', 'blender_org', 'mpfb', 'data')
A = lambda *p: os.path.join(DATA, *p)

# ---------- empty scene ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ---------- the man: body shape from MakeHuman "macro" sliders ----------
old = VARIANT == 'zeus'
macro = {"gender": 1.0, "age": 0.88 if old else 0.62, "muscle": 0.8 if not old else 0.7, "weight": 0.55,
         "proportions": 0.7, "height": 0.6, "cupsize": 0.5, "firmness": 0.5,
         "race": {"asian": 0.05, "caucasian": 0.85, "african": 0.10}}       # Mediterranean look
human = HumanService.create_human(macro_detail_dict=macro)
skin = 'old_caucasian_male' if old else 'middleage_caucasian_male'
HumanService.set_character_skin(A('skins', skin, skin + '.mhmat'), human)
HumanService.add_mhclo_asset(A('eyes', 'high-poly', 'high-poly.mhclo'), human, asset_type='Eyes', material_type='MAKESKIN')
HumanService.add_mhclo_asset(A('eyebrows', 'eyebrow001', 'eyebrow001.mhclo'), human, asset_type='Eyebrows', material_type='MAKESKIN')
HumanService.add_mhclo_asset(A('eyelashes', 'eyelashes01', 'eyelashes01.mhclo'), human, asset_type='Eyelashes', material_type='MAKESKIN')
HumanService.add_mhclo_asset(A('teeth', 'teeth_base', 'teeth_base.mhclo'), human, asset_type='Teeth', material_type='MAKESKIN')
hair = 'long01' if old else 'short02'
HumanService.add_mhclo_asset(A('hair', hair, hair + '.mhclo'), human, asset_type='Hair', material_type='MAKESKIN')

# smooth the body (MakeHuman base mesh is low-poly)
for o in bpy.data.objects:
    if o.type == 'MESH' and not any(m.type == 'SUBSURF' for m in o.modifiers):
        o.modifiers.new('smooth', 'SUBSURF').levels = 1

# ---------- head position (to aim the camera) ----------
dg = bpy.context.evaluated_depsgraph_get()
ev = human.evaluated_get(dg)
zs = [ (ev.matrix_world @ v.co).z for v in ev.data.vertices ]
top = max(zs)
head = Vector((0, 0, top - 0.12))
print('human height', round(top, 3))

# ---------- world + light: dusk, warm rim from behind, soft key from the front-left ----------
world = bpy.data.worlds.new('dusk'); scene.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.05, 0.035, 0.09, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8
def light(name, kind, energy, color, loc, size=1.0):
    l = bpy.data.lights.new(name, kind); l.energy = energy; l.color = color
    if kind == 'AREA': l.size = size
    o = bpy.data.objects.new(name, l); o.location = loc; scene.collection.objects.link(o)
    o.rotation_euler = (Vector((0, 0, head.z)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o
light('key', 'AREA', 220, (1.0, 0.78, 0.6), (1.6, -2.2, head.z + 0.6), 1.5)
light('rim', 'AREA', 600, (1.0, 0.55, 0.25), (-1.4, 2.0, head.z + 0.4), 1.2)
light('fill', 'AREA', 60, (0.5, 0.55, 1.0), (-2.0, -1.5, head.z), 2.0)

# ---------- camera: portrait, 3/4 view ----------
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scene.collection.objects.link(cam); scene.camera = cam
cam.data.lens = 85
cam.location = head + Vector((0.55, -1.25, 0.02))
cam.rotation_euler = (head - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.dof.use_dof = True; cam.data.dof.focus_distance = (head - cam.location).length; cam.data.dof.aperture_fstop = 2.8

# ---------- render settings ----------
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64; scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = 'AgX - Punchy'
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print('saved', OUT)

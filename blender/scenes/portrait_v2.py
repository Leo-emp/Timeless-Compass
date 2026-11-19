# FACE QUALITY TEST v2: a character from library/cast with skin v2, wet eyes, an expression, lit by a REAL
# photographed dusk sky (Poly Haven HDRI) plus a warm film key and a hot rim.
# Run: blender -b --python blender/scenes/portrait_v2.py -- <out.png> [samples] [expression] [cast] [hdri]
import json, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Euler, Vector
from lib import common, cast, expressions

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'portrait_v2.png'
SAMPLES = int(argv[1]) if len(argv) > 1 else 96
EXPR = argv[2] if len(argv) > 2 else 'resolve'
CAST = argv[3] if len(argv) > 3 else 'themistocles'
HDRI = argv[4] if len(argv) > 4 else 'qwantani_dusk_2_puresky'
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')

common.reset_scene()
spec = json.load(open(os.path.join(ROOT, 'library', 'cast', CAST + '.json'), encoding='utf-8'))
human, rig = cast.build_human(spec)
if spec.get('hair'):
    cast.scalp_hair(human, rig, spec['hair'])
if spec.get('beard'):
    cast.beard(human, rig, spec['beard'])
human.modifiers.new('smooth', 'SUBSURF').levels = 1
expressions.load_units(human)
lid = expressions.key_expression(human, rig, EXPR, 1, 1.0)
for s in 'LR':
    pb = rig.pose.bones[f'orbicularis03.{s}']; pb.rotation_mode = 'XYZ'; pb.rotation_euler = Euler((math.radians(lid), 0, 0))
    pb = rig.pose.bones[f'eye.{s}']; pb.rotation_mode = 'XYZ'; pb.rotation_euler = Euler((math.radians(-2), 0, math.radians(-6)))
bpy.context.scene.frame_set(1)

head = rig.matrix_world @ rig.data.bones['head'].head_local + Vector((0, 0, 0.05))
common.hdri_world(HDRI, strength=0.6, rotate_deg=140)
common.area_light('key', 55, (1.0, 0.72, 0.5), head + Vector((1.1, -1.5, 0.45)), head, 1.0)      # warm low sun side
common.area_light('rim', 300, (1.0, 0.58, 0.32), head + Vector((-1.0, 1.3, 0.35)), head, 0.6)    # hot back rim
common.area_light('eye', 3, (1.0, 0.95, 0.9), head + Vector((0.25, -1.2, 0.05)), head, 0.15)     # small catchlight
eyes = rig.matrix_world @ ((rig.data.bones['eye.L'].head_local + rig.data.bones['eye.R'].head_local) / 2)
common.camera('cam', head + Vector((0.40, -1.02, -0.01)), head + Vector((0, 0, -0.01)), lens=85, fstop=2.8, focus=eyes)
common.render_settings(res=(1280, 720), samples=SAMPLES, path=OUT)
bpy.context.scene.view_settings.look = 'AgX - Medium High Contrast'
common.render()

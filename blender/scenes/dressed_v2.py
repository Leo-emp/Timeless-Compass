# CHARACTER QUALITY TEST v2: sculpted face, groomed hair + beard, skin v2, wet eyes, SCANNED linen chiton and wool
# himation, scanned limestone ground, real photographed dusk sky + film key. Medium (waist-up) or full shot.
# Run: blender -b --python blender/scenes/dressed_v2.py -- <out.png> [samples] [med|full] [expression]
import json, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Euler, Vector
from lib import common, cast, expressions, pose, wardrobe

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'dressed_v2.png'
SAMPLES = int(argv[1]) if len(argv) > 1 else 64
SHOT = argv[2] if len(argv) > 2 else 'med'
EXPR = argv[3] if len(argv) > 3 else 'resolve'
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')

common.reset_scene()
spec = json.load(open(os.path.join(ROOT, 'library', 'cast', 'themistocles.json'), encoding='utf-8'))
human, rig = cast.build_human(spec)
cast.scalp_hair(human, rig, spec['hair'])
cast.beard(human, rig, spec['beard'])
pos, _, _ = cast.rest_surface(human)

# undyed linen with a woad-blue hem band; madder-red wool with a dark woven border (dyes known for 5th c. BC Greece)
LINEN = wardrobe.scan_cloth('linen_v2', 'rough_linen', (0.52, 0.47, 0.37), band=(0.07, 0.10, 0.26), tiles=(7, 5), width=0.035, sheen=0.15)
WOOL = wardrobe.scan_cloth('wool_v2', 'caban', (0.30, 0.05, 0.035), band=(0.05, 0.035, 0.025), tiles=(4, 12), edge=1,
                           width=0.025, grime=0.25, sheen=0.15)
wardrobe.add_collision(human)
pose.blend_into_pose(rig, 'stand_relaxed', start=1, end=15)
ch = wardrobe.chiton(human, rig, pos, LINEN)
wardrobe.simulate(45); wardrobe.freeze(ch)
rig.animation_data_clear(); pose.apply_pose(rig, 'stand_relaxed')
wardrobe.himation(human, rig, pos, WOOL, side='L', over=ch)
wardrobe.simulate(60)
human.modifiers.new('smooth', 'SUBSURF').levels = 1
expressions.load_units(human)
lid = expressions.key_expression(human, rig, EXPR, bpy.context.scene.frame_current, 1.0)
for s in 'LR':
    pb = rig.pose.bones[f'orbicularis03.{s}']; pb.rotation_mode = 'XYZ'; pb.rotation_euler = Euler((math.radians(lid), 0, 0))
    pb = rig.pose.bones[f'eye.{s}']; pb.rotation_mode = 'XYZ'; pb.rotation_euler = Euler((math.radians(-1), 0, math.radians(8)))

# ground: scanned dry coastal earth with stones
bpy.ops.mesh.primitive_plane_add(size=30); g = bpy.context.object
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.uv.reset(); bpy.ops.object.mode_set(mode='OBJECT')
g.data.materials.append(wardrobe.scan_cloth('ground', 'coast_sand_rocks_02', (0.62, 0.55, 0.46), tiles=(15, 15), grime=0.0, sheen=0.0))

common.hdri_world('qwantani_sunset_puresky', strength=0.55, rotate_deg=140)
head = rig.matrix_world @ rig.data.bones['head'].head_local
eyes = rig.matrix_world @ ((rig.data.bones['eye.L'].head_local + rig.data.bones['eye.R'].head_local) / 2)
common.sun_light('sun', 3.0, (1.0, 0.6, 0.34), 10, 215)                                           # low golden sun
common.area_light('key', 90, (1.0, 0.76, 0.55), head + Vector((1.6, -2.2, 0.3)), head, 1.6)
common.area_light('rim', 260, (1.0, 0.6, 0.35), head + Vector((-1.3, 1.6, 0.25)), head, 0.8)
if SHOT == 'med':
    common.camera('cam', head + Vector((0.75, -1.95, -0.12)), head + Vector((0.05, 0, -0.18)), lens=55, fstop=2.8, focus=eyes)
else:
    common.camera('cam', Vector((1.4, -4.6, 1.1)), Vector((0, 0, 0.95)), lens=45, fstop=4, focus=eyes)
common.render_settings(res=(1280, 720), samples=SAMPLES, path=OUT)
bpy.context.scene.view_settings.look = 'AgX - Medium High Contrast'
common.render()

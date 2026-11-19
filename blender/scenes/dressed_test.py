# TEST STILL: Themistocles full body in chiton + himation (cloth simulated), standing at sunset.
# Run: blender -b --python blender/scenes/dressed_test.py -- <out.png> [samples] [shot: full|med]
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, cast, pose, wardrobe

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'dressed.png'
SAMPLES = int(argv[1]) if len(argv) > 1 else 64
SHOT = argv[2] if len(argv) > 2 else 'full'
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')

common.reset_scene()
spec = json.load(open(os.path.join(ROOT, 'library', 'cast', 'themistocles.json'), encoding='utf-8'))
human, rig = cast.build_human(spec)
cast.scalp_hair(human, rig, spec['hair'])
cast.beard(human, rig, spec['beard'])
pos, _, _ = cast.rest_surface(human)

LINEN = wardrobe.border_material('linen_border', (0.80, 0.75, 0.64), (0.08, 0.12, 0.30), width=0.035)   # blue hem band
WOOL = wardrobe.border_material('wool_madder', (0.22, 0.035, 0.03), (0.05, 0.04, 0.03), edge=1, width=0.025)   # madder-red wool, dark border
wardrobe.add_collision(human)
pose.blend_into_pose(rig, 'stand_relaxed', start=1, end=15)
# pass 1: the tunic settles on the moving body, then is frozen as a collider
ch = wardrobe.chiton(human, rig, pos, LINEN)
wardrobe.simulate(45)
wardrobe.freeze(ch)
# pass 2: the mantle drapes over body + frozen tunic (body already in its final pose)
bpy.context.scene.frame_set(45)
for pb in rig.pose.bones:
    if pb.id_data.animation_data: pass
rig.animation_data_clear()
pose.apply_pose(rig, 'stand_relaxed')
wardrobe.himation(human, rig, pos, WOOL, side='L', over=ch)
wardrobe.simulate(60)
human.modifiers.new('smooth', 'SUBSURF').levels = 1

# ground + sunset world
bpy.ops.mesh.primitive_plane_add(size=40); g = bpy.context.object
g.data.materials.append(common.principled('stone', (0.35, 0.3, 0.26), rough=0.9, bump=0.3, bump_scale=6))
common.sky_world(sun_elev_deg=6, sun_rot_deg=200, strength=0.18)
common.sun_light('sun', 3.5, (1.0, 0.62, 0.36), 8, 200)
head = rig.matrix_world @ rig.data.bones['head'].head_local
common.area_light('key', 110, (1.0, 0.78, 0.58), Vector((1.8, -2.6, 1.9)), Vector((0, 0, 1.2)), 2.0)
common.area_light('fill', 60, (0.55, 0.6, 1.0), Vector((-2.4, -1.6, 1.4)), Vector((0, 0, 1.0)), 3.0)
if SHOT == 'med':
    common.camera('cam', Vector((0.9, -2.3, 1.62)), Vector((0.05, 0, 1.52)), lens=55, fstop=2.8)
else:
    common.camera('cam', Vector((1.4, -4.6, 1.1)), Vector((0, 0, 0.95)), lens=45, fstop=4)
common.render_settings(samples=SAMPLES, path=OUT)
common.render()

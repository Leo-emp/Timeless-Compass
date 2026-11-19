# TALK TEST: the 9 Rhubarb mouth shapes on a character (contact sheet), to check each one reads correctly.
# Run: blender -b --python blender/scenes/talk_test.py -- <out_dir> [cast] [samples]
import json, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import cast, common, talk

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'talk_test'
CAST = argv[1] if len(argv) > 1 else 'themistocles'
SAMPLES = int(argv[2]) if len(argv) > 2 else 16
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')

common.reset_scene()
spec = json.load(open(os.path.join(ROOT, 'library', 'cast', CAST + '.json'), encoding='utf-8'))
spec = dict(spec, beard=None)                      # bare chin for the test: we judge the lips themselves
human, rig = cast.build_human(spec)
human.modifiers.new('smooth', 'SUBSURF').levels = 1
talk._load(human)
mouth = rig.matrix_world @ rig.data.bones['jaw'].head_local + Vector((0, -0.09, -0.02))
common.hdri_world('qwantani_sunset_puresky', strength=0.5, rotate_deg=140)
common.area_light('key', 40, (1, 0.85, 0.72), mouth + Vector((0.5, -0.8, 0.3)), mouth, 0.8)
common.camera('cam', mouth + Vector((0.12, -0.45, 0.03)), mouth, lens=85, fstop=4, focus=mouth)
common.render_settings(res=(320, 260), samples=SAMPLES)
os.makedirs(OUT, exist_ok=True)
for i, shape in enumerate(talk.SHAPES):
    talk._key_shape(human, rig, shape, i + 1)
for i, shape in enumerate(talk.SHAPES):
    bpy.context.scene.frame_set(i + 1)
    common.render(os.path.join(OUT, f'{i}_{shape}.png'))
print('TALK DONE')

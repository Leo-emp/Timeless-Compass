# SET TEST: a classified 1950s laboratory (secret-project era), with two 1950s extras from tc.crowd.
# Run: blender -b --python blender/scenes/lab_test.py -- <out_dir> [samples] [people 0|1]
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy
from mathutils import Vector
from lib import common, modern

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'lab_test'
SAMPLES = int(argv[1]) if len(argv) > 1 else 24
PEOPLE = len(argv) > 2 and argv[2] == '1'

common.reset_scene()
modern.lab_1950s()
w = bpy.data.worlds.new('dark'); bpy.context.scene.world = w; w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0
if PEOPLE:
    from lib import crowd as C
    from tc import crowd
    ppl = crowd.cast(1, 'scientist', 'usa_1950s', seed=3) + crowd.cast(1, 'official', 'usa_1950s', seed=4)
    C.mid_crowd(ppl, [(-1.0, 1.5, 0.0), (1.2, 2.2, 0.0)], frames=24, face_toward=(0.0, 5.0))
common.render_settings(res=(1280, 544), samples=SAMPLES)
sc = bpy.context.scene; sc.view_settings.look = 'AgX - High Contrast'
os.makedirs(OUT, exist_ok=True)
for name, loc, tgt, lens in [('room', Vector((5.5, -4.5, 1.7)), Vector((-1.0, 3.0, 1.2)), 24),
                             ('panel', Vector((1.0, 1.5, 1.5)), Vector((0.0, 4.6, 1.3)), 35)]:
    sc.camera = common.camera('cam_' + name, loc, tgt, lens=lens)
    common.render(os.path.join(OUT, name + '.png'))
print('LAB DONE')

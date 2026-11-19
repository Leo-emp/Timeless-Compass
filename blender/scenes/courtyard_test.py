# SET TEST: inside an Athenian house courtyard c. 480 BC (portico, altar of Zeus Herkeios, well, amphorae, tree).
# Run: blender -b --python blender/scenes/courtyard_test.py -- <out_dir> [samples]
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import architecture as A, common

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'courtyard_test'
SAMPLES = int(argv[1]) if len(argv) > 1 else 20
common.reset_scene()
A.courtyard_house()
common.hdri_sky('qwantani_sunset_puresky', background=0.8, lighting=0.4, rotate_deg=120)
common.sun_light('sun', 4.0, (1.0, 0.7, 0.45), 16, 250)          # low sun over the west wall: half the court in shade
common.render_settings(res=(1280, 544), samples=SAMPLES)
sc = bpy.context.scene; sc.view_settings.look = 'AgX - High Contrast'; sc.view_settings.exposure = -0.2
os.makedirs(OUT, exist_ok=True)
for name, loc, tgt, lens in [('court', Vector((5.5, -5.0, 1.7)), Vector((-2.0, 3.5, 1.4)), 24),
                             ('portico', Vector((-1.0, 1.0, 1.6)), Vector((2.0, 6.0, 1.5)), 32)]:
    sc.camera = common.camera('cam_' + name, loc, tgt, lens=lens)
    common.render(os.path.join(OUT, name + '.png'))
print('COURTYARD DONE')

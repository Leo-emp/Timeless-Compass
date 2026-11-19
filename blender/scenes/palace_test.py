# SET TEST: inside the Persian audience hall (Persepolis apadana style) with the golden throne on the dais.
# Run: blender -b --python blender/scenes/palace_test.py -- <out_dir> [samples]
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, props, sets

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'palace_test'
SAMPLES = int(argv[1]) if len(argv) > 1 else 24

common.reset_scene()
sets.persian_palace_interior()
props.throne((-31.0, 0.0, 0.9), heading_deg=-90)              # on the dais, facing down the hall (+X)
common.render_settings(res=(1280, 544), samples=SAMPLES)
sc = bpy.context.scene
sc.view_settings.look = 'AgX - High Contrast'; sc.view_settings.exposure = 0.3
os.makedirs(OUT, exist_ok=True)
views = {'down_hall': (Vector((28.0, -6.0, 1.7)), Vector((-31.0, 0.0, 2.0)), 28),
         'throne':    (Vector((-22.0, 4.0, 1.6)), Vector((-31.0, 0.0, 1.6)), 35),
         'columns_up': (Vector((5.0, -3.0, 1.2)), Vector((0.0, 0.0, 13.0)), 20)}
for name, (loc, tgt, lens) in views.items():
    cam = common.camera('cam_' + name, loc, tgt, lens=lens)
    sc.camera = cam
    common.render(os.path.join(OUT, name + '.png'))
print('PALACE DONE')

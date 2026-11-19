# SET TEST: Athens 480 BC (lower city + Acropolis with the Old Temple of Athena). Optional: burning (Persian sack).
# Run: blender -b --python blender/scenes/athens_test.py -- <out_dir> [samples] [density] [burning 0|1]
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, sets

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'athens_test'
SAMPLES = int(argv[1]) if len(argv) > 1 else 24
DENSITY = float(argv[2]) if len(argv) > 2 else 0.5
BURNING = len(argv) > 3 and argv[3] == '1'

common.reset_scene()
sets.athens_480bc(density=DENSITY, burning=BURNING)
common.render_settings(res=(1280, 544), samples=SAMPLES)
bpy.context.scene.view_settings.look = 'AgX - High Contrast'
bpy.context.scene.view_settings.exposure = -0.6
os.makedirs(OUT, exist_ok=True)
views = {
    'street':   (Vector((6.0, -30.0, 2.6)), Vector((-10.0, 180.0, 62.0)), 32),     # from a lane up to the temple
    'wide':     (Vector((-160.0, -170.0, 60.0)), Vector((0.0, 100.0, 40.0)), 35),
    'temple':   (Vector((22.0, 140.0, 72.0)), Vector((-20.0, 182.0, 76.0)), 28),   # on the rock, near the temple
}
for name, (loc, target, lens) in views.items():
    cam = common.camera('cam_' + name, loc, target, lens=lens)
    bpy.context.scene.camera = cam
    common.render(os.path.join(OUT, ('burning_' if BURNING else '') + name + '.png'))
print('ATHENS DONE')

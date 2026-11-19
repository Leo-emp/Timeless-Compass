# SET TEST: Thermopylae 480 BC - the coastal pass, the cliffs of Kallidromos, the Phocian wall, the Malian Gulf.
# Run: blender -b --python blender/scenes/thermopylae_test.py -- <out_dir> [samples] [density] [dawn 0|1]
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, sets

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'thermopylae_test'
SAMPLES = int(argv[1]) if len(argv) > 1 else 24
DENSITY = float(argv[2]) if len(argv) > 2 else 0.5
DAWN = len(argv) > 3 and argv[3] == '1'

common.reset_scene()
sets.thermopylae_480bc(density=DENSITY, dawn=DAWN)
common.render_settings(res=(1280, 544), samples=SAMPLES)
bpy.context.scene.view_settings.look = 'AgX - High Contrast'
bpy.context.scene.view_settings.exposure = -0.5
os.makedirs(OUT, exist_ok=True)
ground = lambda y: max(-1.5, min(2.5, 0.08 * (y + 12)))      # the pass shelf height (same formula as the set)
views = {
    'greek_line': (Vector((-25.0, 18.0, ground(18) + 1.7)), Vector((40.0, 25.0, ground(25) + 1.4)), 35),   # behind the wall
    'pass_wide':  (Vector((-160.0, -40.0, 30.0)), Vector((60.0, 40.0, 10.0)), 30),                         # strip between cliff + sea
    'low_hero':   (Vector((8.0, 10.0, ground(10) + 0.5)), Vector((-2.0, 24.0, ground(24) + 2.4)), 24),     # low, up at the wall
}
for name, (loc, target, lens) in views.items():
    cam = common.camera('cam_' + name, loc, target, lens=lens)
    bpy.context.scene.camera = cam
    common.render(os.path.join(OUT, ('dawn_' if DAWN else '') + name + '.png'))
print('THERMOPYLAE DONE')

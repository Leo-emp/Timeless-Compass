# SET TEST: Salamis strait v2 (scanned cove, real plants and rocks), three camera views, no characters.
# Run: blender -b --python blender/scenes/salamis_v2_test.py -- <out_dir> [samples] [density]
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, sets

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'salamis_v2'
SAMPLES = int(argv[1]) if len(argv) > 1 else 32
DENSITY = float(argv[2]) if len(argv) > 2 else 1.0

common.reset_scene()
sets.salamis_dusk_v2(density=DENSITY)
sets.salamis_film_light()
common.render_settings(res=(1280, 544), samples=SAMPLES)
bpy.context.scene.view_settings.look = 'AgX - High Contrast'
bpy.context.scene.view_settings.exposure = 0.4
os.makedirs(OUT, exist_ok=True)
views = {
    'hero':    (Vector((2.1, -10.0, 2.05)), Vector((0.0, -6.0, 2.05)), 40),     # the hero shot's camera
    'cove':    (Vector((-6.0, -16.0, 4.5)), Vector((6.0, 10.0, 0.5)), 28),      # wider: cove arms framing the sea
    'reverse': (Vector((3.0, 6.0, 2.2)), Vector((-2.0, -14.0, 2.5)), 32),       # from the water back onto the shore
}
for name, (loc, target, lens) in views.items():
    cam = common.camera('cam_' + name, loc, target, lens=lens)
    bpy.context.scene.camera = cam
    common.render(os.path.join(OUT, name + '.png'))
print('SET DONE')

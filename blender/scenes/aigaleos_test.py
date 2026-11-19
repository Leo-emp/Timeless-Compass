# SET TEST: Xerxes' golden throne at the foot of Mount Aigaleos above the strait of Salamis (Herodotus 8.90).
# Run: blender -b --python blender/scenes/aigaleos_test.py -- <out_dir> [samples] [density]
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, sets

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'aigaleos_test'
SAMPLES = int(argv[1]) if len(argv) > 1 else 16
DENSITY = float(argv[2]) if len(argv) > 2 else 0.5

common.reset_scene()
plat = sets.xerxes_throne_aigaleos(density=DENSITY)
z = plat.location.z
common.render_settings(res=(1280, 544), samples=SAMPLES)
bpy.context.scene.view_settings.look = 'AgX - High Contrast'
bpy.context.scene.view_settings.exposure = -1.3
os.makedirs(OUT, exist_ok=True)
views = {
    'behind_king': (Vector((2.5, -47.0, z + 3.2)), Vector((0.0, 200.0, 0.0)), 28),     # over the throne to the strait
    'throne':      (Vector((3.5, -35.0, z + 1.6)), Vector((0.0, -40.5, z + 1.0)), 40),   # the throne under the canopy
    'camp':        (Vector((40.0, -20.0, z + 12.0)), Vector((0.0, -60.0, z)), 30),       # pavilion + camp from the side
}
for name, (loc, target, lens) in views.items():
    cam = common.camera('cam_' + name, loc, target, lens=lens)
    bpy.context.scene.camera = cam
    common.render(os.path.join(OUT, name + '.png'))
print('AIGALEOS DONE')

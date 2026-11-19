# SET TEST: Thebes c. 1250 BC - temple pylon + obelisks facing the Nile, date palms. Run: ... -- <out_dir> [samples] [density]
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, sets
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'thebes_test'
SAMPLES = int(argv[1]) if len(argv) > 1 else 16
DENSITY = float(argv[2]) if len(argv) > 2 else 0.5
common.reset_scene()
sets.thebes_1250bc(density=DENSITY)
common.render_settings(res=(1280, 544), samples=SAMPLES)
sc = bpy.context.scene; sc.view_settings.look = 'AgX - High Contrast'; sc.view_settings.exposure = -0.8
os.makedirs(OUT, exist_ok=True)
for name, loc, tgt, lens in [('approach', Vector((12.0, -40.0, 2.0)), Vector((0.0, 40.0, 12.0)), 28),
                             ('obelisk', Vector((-14.0, 14.0, 1.6)), Vector((-8.0, 24.0, 16.0)), 24),
                             ('river', Vector((-60.0, -70.0, 6.0)), Vector((0.0, 30.0, 8.0)), 35)]:
    sc.camera = common.camera('cam_' + name, loc, tgt, lens=lens)
    common.render(os.path.join(OUT, name + '.png'))
print('THEBES DONE')

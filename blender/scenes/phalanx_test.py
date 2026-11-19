# BATTLE TEST: a Greek phalanx at Thermopylae - unique hoplites (own face, crest, shield emblem) in close ranks at the
# Phocian wall, facing the Persian side (+X), plus far instances behind. Run: ... -- <out_dir> [samples] [front_count]
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy
from mathutils import Vector
from lib import common, crowd as C, sets
from tc import crowd

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'phalanx_test'
SAMPLES = int(argv[1]) if len(argv) > 1 else 16
N = int(argv[2]) if len(argv) > 2 else 8

common.reset_scene()
sets.thermopylae_480bc(density=0.4)
ground = lambda y: max(-1.5, min(2.5, 0.08 * (y + 12)))
men = crowd.cast(N, 'hoplite', 'greece_480bc', seed=21)
marks = [(-3.0 - 1.1 * (i // 4), 14.0 + 1.0 * (i % 4), ground(14.0 + 1.0 * (i % 4))) for i in range(N)]   # close order
mids = C.mid_crowd(men, marks, frames=24, face_toward=(60.0, 18.0))
C.far_crowd(mids, (-30, -8, 8, 30), 60, z_fn=lambda x, y: ground(y), seed=4, face_toward=(60.0, 18.0))
common.render_settings(res=(1280, 544), samples=SAMPLES)
sc = bpy.context.scene; sc.view_settings.look = 'AgX - High Contrast'; sc.view_settings.exposure = -0.4
sc.frame_set(12)
os.makedirs(OUT, exist_ok=True)
for name, loc, tgt, lens in [('front', Vector((4.0, 13.0, ground(13) + 1.5)), Vector((-4.0, 16.0, ground(16) + 1.4)), 30),
                             ('shields', Vector((0.5, 15.0, ground(15) + 1.2)), Vector((-3.0, 15.5, ground(15.5) + 1.1)), 50)]:
    sc.camera = common.camera('cam_' + name, loc, tgt, lens=lens)
    common.render(os.path.join(OUT, name + '.png'))
print('PHALANX DONE')

# BATTLE TEST: Thermopylae, August 480 BC - a Spartan line (crimson cloaks, long hair, bronze, personal shield
# emblems) at the Phocian wall facing Persian Immortals + sparabara (wicker shields) across the narrow pass.
# Run: blender -b --python blender/scenes/thermopylae_battle_test.py -- <out_dir> [samples] [per_side]
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy
from mathutils import Vector
from lib import common, crowd as C, sets
from tc import crowd

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'battle_test'
SAMPLES = int(argv[1]) if len(argv) > 1 else 16
N = int(argv[2]) if len(argv) > 2 else 6

common.reset_scene()
sets.thermopylae_480bc(density=0.4)
ground = lambda y: max(-1.5, min(2.5, 0.08 * (y + 12)))
sp = crowd.cast(N, 'spartan', 'greece_480bc', seed=31)
pe = crowd.cast(N // 2, 'immortal', 'persia_480bc', seed=32) + crowd.cast(N - N // 2, 'soldier', 'persia_480bc', seed=33)
sp_marks = [(4.0 - 1.1 * (i // 3), 15.0 + 1.0 * (i % 3), ground(15.0 + 1.0 * (i % 3))) for i in range(len(sp))]
pe_marks = [(14.0 + 1.2 * (i // 3), 15.0 + 1.0 * (i % 3), ground(15.0 + 1.0 * (i % 3))) for i in range(len(pe))]
greeks = C.mid_crowd(sp, sp_marks, frames=24, face_toward=(40.0, 16.0))
persians = C.mid_crowd(pe, pe_marks, frames=24, face_toward=(-20.0, 16.0))
C.far_crowd(greeks, (-14, 1, 10, 26), 30, z_fn=lambda x, y: ground(y), seed=5, face_toward=(40.0, 16.0))
C.far_crowd(persians, (18, 60, 4, 40), 120, z_fn=lambda x, y: ground(y), seed=6, face_toward=(-20.0, 16.0))
common.render_settings(res=(1280, 544), samples=SAMPLES)
sc = bpy.context.scene; sc.view_settings.look = 'AgX - High Contrast'; sc.view_settings.exposure = -0.4
sc.frame_set(12)
os.makedirs(OUT, exist_ok=True)
for name, loc, tgt, lens in [('side', Vector((9.0, 4.0, ground(4) + 1.7)), Vector((9.0, 16.0, ground(16) + 1.3)), 28),
                             ('greek_backs', Vector((-4.0, 15.5, ground(15.5) + 1.8)), Vector((14.0, 16.0, ground(16) + 1.4)), 35),
                             ('persian_view', Vector((22.0, 16.5, ground(16.5) + 1.7)), Vector((3.0, 16.0, ground(16) + 1.4)), 40)]:
    sc.camera = common.camera('cam_' + name, loc, tgt, lens=lens)
    common.render(os.path.join(OUT, name + '.png'))
print('BATTLE DONE')

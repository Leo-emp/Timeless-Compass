# CROWD TEST: an Athenian assembly - 8 unique mid-ground people (citizens, a servant, a noble, an elder) built from
# tc.crowd specs, plus 80 far instances behind them, all facing a speaker's spot. Checks: no two look alike, nobody
# moves in sync, rank shows in clothing.
# Run: blender -b --python blender/scenes/crowd_test.py -- <out_dir> [samples] [mid_count]
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(HERE, '..', '..'))            # repo root: the tc package (pure Python)
import bpy
from mathutils import Vector
from lib import common, crowd as C
from tc import crowd

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'crowd_test'
SAMPLES = int(argv[1]) if len(argv) > 1 else 16
N = int(argv[2]) if len(argv) > 2 else 8

common.reset_scene()
people = (crowd.cast(max(N - 3, 1), 'citizen', 'greece_480bc', seed=11) + crowd.cast(1, 'servant', 'greece_480bc', seed=12)
          + crowd.cast(1, 'noble', 'greece_480bc', seed=13) + [crowd.person(5, 'citizen', 'greece_480bc', age=0.92)])[:N]
marks = [(-3.0 + 1.1 * (i % 5) + 0.3 * (i // 5), -1.0 - 1.3 * (i // 5), 0.0) for i in range(len(people))]
mids = C.mid_crowd(people, marks, frames=48, face_toward=(0.0, 8.0))
C.far_crowd(mids, (-14, 14, -16, -5), 80, seed=3, face_toward=(0.0, 8.0))
bpy.ops.mesh.primitive_plane_add(size=80); g = bpy.context.object
from lib import scatter
g.data.materials.append(scatter.scan_material('pnyx_ground', 'brown_mud_dry', tint=(1.0, 0.92, 0.8), tiles=3.0))
common.hdri_world('qwantani_sunset_puresky', strength=0.6, rotate_deg=200)
common.sun_light('sun', 3.0, (1.0, 0.72, 0.5), 16, 20)
common.render_settings(res=(1280, 544), samples=SAMPLES)
bpy.context.scene.view_settings.look = 'AgX - High Contrast'
bpy.context.scene.frame_set(36)
os.makedirs(OUT, exist_ok=True)
for name, loc, tgt, lens in [('from_speaker', Vector((0.5, 7.5, 2.0)), Vector((0, -3, 1.4)), 35),
                             ('side', Vector((9.0, -2.0, 1.8)), Vector((-2, -3, 1.4)), 40)]:
    cam = common.camera('cam_' + name, loc, tgt, lens=lens)
    bpy.context.scene.camera = cam
    common.render(os.path.join(OUT, name + '.png'))
print('CROWD DONE')

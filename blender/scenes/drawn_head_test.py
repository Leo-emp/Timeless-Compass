# QUICK CHECK: one hoplite, helmet pushed up, head-and-shoulders in the drawn look (fast, laptop-sized).
# Run: blender -b --python blender/scenes/drawn_head_test.py -- <out_dir> [name] [samples]
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from lib import build, common, drawn  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else 'spike/style2d')
NAME = argv[1] if len(argv) > 1 else 'leonidas'
SAMPLES = int(argv[2]) if len(argv) > 2 else 16
os.makedirs(OUT, exist_ok=True)
t0 = time.time()
common.reset_scene()
spec = build.manifest('cast', NAME)
spec['helmet'] = dict(spec.get('helmet') or {'crest': 'red'}, worn='up')
spec['shield'] = {'emblem': 'lambda', 'wear': 0.4}
spec.pop('cloak', None)                                    # no cloth sim: this check is about the head
rig, human, root, first, last = build.character(NAME, spec['wardrobe'], {'pose': 'stand_relaxed'}, frames=12, spec=spec)
print(f'BUILT {time.time() - t0:.0f}s', flush=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, last
if any(m.type == 'CLOTH' for o in bpy.data.objects for m in o.modifiers):
    bpy.ops.ptcache.bake_all(bake=True)
sc.frame_set(first + 4)
head = rig.matrix_world @ rig.pose.bones['head'].head + Vector((0, 0, 0.08))
common.hdri_sky('kloofendal_48d_partly_cloudy_puresky', background=1.0, lighting=0.12, rotate_deg=60)
common.sun_light('sun', 1.0, (1.0, 0.95, 0.86), 38, -42)
common.render_settings(res=(720, 720), samples=SAMPLES)
for tag, off in (('front', (0.25, -1.3, -0.12)), ('side', (1.15, -0.65, -0.05))):
    common.camera('cam_' + tag, head + Vector(off), head + Vector((0, 0, 0.02)), lens=55)
    if tag == 'front':
        drawn.apply_cycles(lines=2.4, brush=5, samples=SAMPLES)
    common.render(os.path.join(OUT, f'{NAME}_head_{tag}.png'))
    print(f'RENDERED {tag} {time.time() - t0:.0f}s', flush=True)
print('HEAD DONE')

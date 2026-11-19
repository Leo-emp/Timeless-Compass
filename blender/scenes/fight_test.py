# FIGHT TEST: two hoplites duel with drawn swords (xiphos + aspis): guard, exchanges, blocks with sparks, the last blow
# kills. Prints the MEASURED impact frame of every attack (to correct tc/fight.py's timing table).
# Laptop only (Mixamo clips are not in the cloud).
# Run: blender -b --python blender/scenes/fight_test.py -- <out_dir> [samples] [slowmo_speed]
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from lib import common, crowd as C, fight  # noqa: E402
from tc import crowd, fight as plan  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'fight_test'
SAMPLES = int(argv[1]) if len(argv) > 1 else 16
SPEED = float(argv[2]) if len(argv) > 2 else 1.0
END = 200

common.reset_scene()
pa, pb = crowd.cast(2, 'hoplite', 'greece_480bc', seed=77)
for p in (pa, pb):
    p['weapon'] = 'sword'
    p['motion'] = {}
A = C.build_person(pa, (0, 0, 0), 0, frames=END)
B = C.build_person(pb, (0, 0, 0), 0, frames=END)


def rig_of(root):
    return next(o for o in root.children_recursive if o.type == 'ARMATURE')


fight.place_pair(A, B, (0, 0, 0), 0.0, 'sword')
beats = plan.choreograph(seed=11, exchanges=4, winner='A')
for b in beats:
    print('BEAT', b['fighter'], b['kind'], b['clip'], b['start'], b.get('impact', ''))
fight.duel((rig_of(A), A), (rig_of(B), B), beats, END, seed=3)
for b in beats:
    if b['kind'] == 'attack':
        r = rig_of(A) if b['fighter'] == 'A' else rig_of(B)
        measured = fight.impact_frames(r, b['start'], b['start'] + plan.CLIPS[b['clip']]['length']) - b['start']
        print('IMPACT', b['clip'], 'planned', b['impact'] - b['start'], 'measured', measured)

bpy.ops.mesh.primitive_plane_add(size=80)
bpy.context.object.data.materials.append(common.principled('earth', (0.3, 0.25, 0.18), rough=0.95))
common.hdri_world('qwantani_sunset_puresky', strength=0.7)
common.sun_light('sun', 3.5, (1.0, 0.78, 0.55), 18, 200)
common.render_settings(res=(960, 540), samples=SAMPLES)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, END
sc.render.use_motion_blur = True
sc.camera = common.camera('cam', Vector((0.5, -4.8, 1.5)), Vector((0, 0, 1.2)), lens=35)
os.makedirs(OUT, exist_ok=True)
hits = [b['impact'] for b in beats if b['kind'] == 'attack']
for f in [hits[0] - 8, hits[0], hits[1], hits[-1] - 4, hits[-1] + 30]:
    sc.frame_set(f)
    common.render(os.path.join(OUT, f'f{f:03d}.png'))
if SPEED < 1.0:                       # a slow-motion strip around the killing blow
    fight.slow_motion(sc, SPEED)
    k = int(round(hits[-1] / SPEED))
    for f in range(k - 8, k + 9, 4):
        sc.frame_set(f)
        common.render(os.path.join(OUT, f'slow_{f:04d}.png'))
print('FIGHT DONE')

# DRAWN-LOOK TEST SHOT: two hoplites, helmets pushed up, half-body against a cloudy sky with the army's spears
# behind - framed like the owner's Heroes of Bronze reference frame - rendered with lib/drawn.py.
# Run: blender -b --python blender/scenes/drawn_test.py -- <out_dir> [res_scale%] [samples]
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from lib import build, common, drawn  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'spike/style2d'
SCALE = int(argv[1]) if len(argv) > 1 else 100
SAMPLES = int(argv[2]) if len(argv) > 2 else 32
os.makedirs(OUT, exist_ok=True)

common.reset_scene()
CAST = [('leonidas', (-0.48, 0.0, 0.0), -12.0), ('eurybiades', (0.62, 0.35, 0.0), 14.0)]
rigs, lasts = [], []
for name, mark, turn in CAST:
    spec = build.manifest('cast', name)
    spec['helmet'] = dict(spec.get('helmet') or {'crest': 'red'}, worn='up')
    if name == 'leonidas':
        spec['shield'] = {'emblem': 'lambda', 'wear': 0.4}
    rig, human, root, first, last = build.character(name, spec['wardrobe'], {'pose': 'stand_relaxed'},
                                                    mark=mark, turn_deg=turn, frames=24, spec=spec)
    rigs.append(rig); lasts.append((first, last))
sc = bpy.context.scene
first = max(f for f, _ in lasts); last = max(l for _, l in lasts)
sc.frame_start, sc.frame_end = 1, last

# ---- the army behind them: real Spartans (helmets down, facing the camera), more as instances further back
from lib import crowd as C  # noqa: E402
from tc import crowd as TC  # noqa: E402
men = TC.cast(6, 'spartan', 'greece_480bc', seed=4801)
for m in men:                       # background men: no cloak cloth (6 cloth sims made the cloud job crawl)
    m.pop('cloak', None)
marks = [(-2.6, 5.2, 0), (-0.9, 6.0, 0), (1.0, 5.6, 0), (2.7, 6.3, 0), (-1.8, 8.0, 0), (1.9, 8.4, 0)]
roots = C.mid_crowd(men, marks, frames=24, face_toward=(0.0, -20.0))
C.far_crowd(roots, (-14, 14, 10, 34), 60, seed=11, face_toward=(0.0, -40.0))
bpy.ops.mesh.primitive_plane_add(size=400); g = bpy.context.object
g.data.materials.append(common.principled('drawn_ground', (0.52, 0.44, 0.24), rough=1.0))
if any(m.type == 'CLOTH' for o in bpy.data.objects for m in o.modifiers):
    bpy.ops.ptcache.bake_all(bake=True)
sc.frame_set(first + 6)

# ---- GRIP CHECK (owner rule): every spear must pass through the hand that holds it
bad = 0
for s in [o for o in bpy.data.objects if o.name.startswith('dory_shaft')]:
    rig = s.constraints[0].target
    hand = rig.matrix_world @ rig.pose.bones[s['grip_bone']].tail
    a = s.matrix_world @ Vector((0, 0, -1.0)); b = s.matrix_world @ Vector((0, 0, 1.0))
    ab = b - a; t = (hand - a).dot(ab) / ab.length_squared
    d = (a + ab * t - hand).length
    up = (b - a).normalized().z
    ok = d < 0.03 and up > 0.97
    bad += not ok
    print(f'GRIP CHECK {s.name}: {d * 100:.1f} cm from the hand, upright {up:.3f} -> {"OK" if ok else "FAIL"}')
print('GRIP CHECK SUMMARY', 'ALL OK' if not bad else f'{bad} FAIL')
print('MATERIALS', sorted(m.name for m in bpy.data.materials if m.users)[:80])

# ---- light: warm sun from camera-left, high; the cloud photo is the painted sky (gentle on the scene)
common.hdri_sky('kloofendal_48d_partly_cloudy_puresky', background=1.0, lighting=0.12, rotate_deg=60)
common.sun_light('sun', 1.0, (1.0, 0.95, 0.86), 38, -42)

# ---- camera: low, slightly looking up at the two men, waist-up (as in the reference frame)
common.render_settings(res=(1920 * SCALE // 100, 1080 * SCALE // 100), samples=SAMPLES)
cam = common.camera('cam', Vector((0.15, -3.3, 1.12)), Vector((0.1, 0.2, 1.52)), lens=38)
drawn.apply_cycles(lines=2.0 * SCALE / 100 + 0.3, brush=max(3, 8 * SCALE // 100), samples=SAMPLES)
common.render(os.path.join(OUT, 'drawn_hoplites.png'))
print('DRAWN DONE')

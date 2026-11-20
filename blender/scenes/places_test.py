# PLACES TEST: Delphi's adyton and the commanders' tents (blender/lib/places.py), two views each.
# Run: blender -b --python blender/scenes/places_test.py -- <out_dir> [samples] [place]  place = adyton | tent | council | all
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from lib import common, places  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'places_test'
SAMPLES = int(argv[1]) if len(argv) > 1 else 24
WHICH = argv[2] if len(argv) > 2 else 'all'
os.makedirs(OUT, exist_ok=True)


def shoot(name, views):
    sc = bpy.context.scene
    common.render_settings(res=(1280, 544), samples=SAMPLES)
    sc.view_settings.look = 'AgX - High Contrast'
    sc.frame_set(12)
    for tag, (loc, tgt, lens) in views.items():
        sc.camera = common.camera(f'cam_{name}_{tag}', loc, tgt, lens=lens)
        common.render(os.path.join(OUT, f'{name}_{tag}.png'))


if WHICH in ('adyton', 'all'):
    common.reset_scene()
    m = places.delphi_adyton()
    bpy.context.scene.world = bpy.data.worlds.new('dark') if not bpy.context.scene.world else bpy.context.scene.world
    bpy.context.scene.view_settings.exposure = 0.0
    shoot('adyton', {'from_door': (m['cam_from_door'], Vector((-0.6, -1.0, 1.0)), 24),
                     'low_tripod': (m['cam_low_tripod'], Vector((-0.9, -0.6, 1.4)), 30)})
for kind in ('themistocles', 'council'):
    if WHICH in (kind, 'tent' if kind == 'themistocles' else 'council', 'all'):
        common.reset_scene()
        m = places.tent_interior(kind)
        shoot(f'tent_{kind}', {'flap': (m['cam_flap'], Vector((0, -1.0, 1.0)), 24),
                               'inside': (Vector((-1.2, 1.0, 1.5)), Vector((0.6, -1.6, 0.9)), 28)})
if WHICH in ('pnyx', 'all2', 'pnyx_crowd'):
    common.reset_scene()
    m = places.pnyx_assembly()
    if WHICH == 'pnyx_crowd':                       # the Assembly alive: citizens on the slope facing the bema
        from lib import crowd as C
        from tc import crowd
        near = crowd.cast(16, 'citizen', 'greece_480bc', seed=480)
        roots = C.mid_crowd(near, [tuple(p) for p in m['audience'][:16]], frames=24, face_toward=(0.0, 0.0))
        far_z = lambda x, y: max(0.0, (-y - 3.0)) * 0.16 + 0.0015 * (x * x + y * y) - 0.05
        C.far_crowd(roots, (-22, 22, -34, -10), 260, z_fn=far_z, seed=7, face_toward=(0.0, 0.0))
        speaker = crowd.cast(1, 'noble', 'greece_480bc', seed=481)
        C.mid_crowd(speaker, [tuple(m['speaker'])], frames=24, face_toward=(0.0, -20.0))
    shoot('pnyx', {'behind_speaker': (m['cam_behind_speaker'], Vector((0, -10, 2.0)), 28),
                   'crowd_low': (m['cam_crowd_low'], Vector((0, 0, 1.2)), 35)})
if WHICH in ('athlit', 'all2'):
    common.reset_scene()
    m = places.athlit_seabed_1980()
    shoot('athlit_seabed', {'low': (m['cam_low'], m['ram'], 30)})
    common.reset_scene()
    m = places.athlit_ram_display()
    shoot('athlit_museum', {'three_quarter': (m['cam_three_quarter'], m['ram'], 40),
                            'close': (m['cam_close'], m['ram'], 50)})
print('PLACES DONE')

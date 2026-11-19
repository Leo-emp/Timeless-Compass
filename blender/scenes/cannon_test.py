# CANNON TEST: the three era guns side by side (bombard c.1450, naval 32-pdr c.1805, field 12-pdr c.1860), then the
# field gun firing: frames just before / at / after the shot. Cloud-safe (needs only Poly Haven CC0 skies).
# Run: blender -b --python blender/scenes/cannon_test.py -- <out_dir> [samples]
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from lib import cannon, common  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'cannon_test'
SAMPLES = int(argv[1]) if len(argv) > 1 else 16

common.reset_scene()
bpy.ops.mesh.primitive_plane_add(size=400)
bpy.context.object.data.materials.append(common.principled('field', (0.25, 0.27, 0.15), rough=0.95))
common.hdri_world('kloofendal_48d_partly_cloudy_puresky', strength=0.9)
common.sun_light('sun', 3.0, (1, 0.9, 0.78), 35, 210)
common.render_settings(res=(1280, 544), samples=SAMPLES)
sc = bpy.context.scene
sc.render.use_motion_blur = True
os.makedirs(OUT, exist_ok=True)
guns = [cannon.build('bombard', (-7, 0, 0), 0, 2), cannon.build('naval', (0, 0, 0), 0, 0),
        cannon.build('field', (6, 0, 0), 0, 4)]
sc.frame_set(1)
sc.camera = common.camera('cam_line', Vector((1.0, -11.0, 2.2)), Vector((0, 0, 0.8)), lens=30)
common.render(os.path.join(OUT, 'lineup.png'))
for g in guns[:2]:
    for o in [g] + list(g.children_recursive):
        o.hide_render = True
cannon.fire(guns[2], 20, target=(140, 10, 0), shell=False)
sc.frame_start, sc.frame_end = 1, 80
sc.camera = common.camera('cam_fire', Vector((2.0, -6.5, 1.6)), Vector((8.5, 0, 1.0)), lens=32)
for f in (18, 20, 22, 30, 60):
    sc.frame_set(f)
    common.render(os.path.join(OUT, f'fire_{f:03d}.png'))
print('CANNON DONE')

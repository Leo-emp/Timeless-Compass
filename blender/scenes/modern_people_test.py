# WS17 PEOPLE TEST (Session F): modern-era extras from tc/crowd.py (usa_1945 / usa_1960 / ussr_1960) dressed with
# MakeHuman suits + uniforms and the code-built overlays (lab coat, hospital gown, caps, ribbons) from
# blender/lib/modern_dress.py. A row of people against a grey studio wall, soft key light.
# Run: blender -b --python blender/scenes/modern_people_test.py -- <out_dir> [samples] [clips 0|1] [engine]
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, ROOT)
import bpy
from mathutils import Vector
from lib import common, modern_dress
from tc import crowd

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else os.path.abspath('modern_people')
SAMPLES = int(argv[1]) if len(argv) > 1 else 32
CLIPS = len(argv) > 2 and argv[2] == '1'
ENGINE = argv[3] if len(argv) > 3 else 'CYCLES'

LINEUP = [('scientist', 'usa_1945', 11), ('general', 'usa_1945', 4), ('soldier', 'usa_1945', 2), ('agent', 'usa_1960', 5),
          ('test_subject', 'usa_1960', 3), ('soldier', 'ussr_1960', 2), ('general', 'ussr_1960', 6), ('worker', 'ussr_1960', 1)]
common.reset_scene()
people = []
for role, era, seed in LINEUP:
    p = crowd.person(seed, role, era)
    if role == 'scientist':
        p['overlays'] = ['lab_coat']                     # the test must show the coat
    people.append(p)
    print('PERSON', role, era, p.get('overlays'), [c[0] for c in p['mpfb_clothes']], flush=True)
marks = [(-4.2 + i * 1.2, 0.0, 0.0) for i in range(len(people))]
modern_dress.modern_crowd(people, marks, frames=24, face_toward=None, clip=CLIPS)
for r in [o for o in bpy.data.objects if o.name.startswith('modern_')]:
    r.rotation_euler.z = 0.0                             # everyone faces the camera (-Y)
mat = common.principled('studio', (0.32, 0.32, 0.31), rough=0.9)
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0)); bpy.context.object.data.materials.append(mat)
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 3, 0), rotation=(1.5708, 0, 0)); bpy.context.object.data.materials.append(mat)
common.area_light('key', 900, (1.0, 0.95, 0.88), (-3, -5, 4), (0, 0, 1.2), size=3)
common.area_light('fill', 220, (0.85, 0.9, 1.0), (5, -4, 2), (0, 0, 1.2), size=3)
common.area_light('rim', 400, (1, 1, 1), (0, 2.5, 3.5), (0, 0, 1.4), size=2)
w = bpy.data.worlds.new('w'); bpy.context.scene.world = w; w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.05
common.render_settings(res=(1600, 640), samples=SAMPLES, engine=ENGINE)
bpy.context.scene.frame_set(12 if CLIPS else 1)
os.makedirs(OUT, exist_ok=True)
common.camera('cam_row', Vector((0, -9.5, 1.3)), Vector((0, 0, 0.95)), lens=40)
common.render(os.path.join(OUT, 'lineup.png'))
common.render_settings(res=(1280, 720), samples=SAMPLES, engine=ENGINE)
common.camera('cam_close', Vector((-3.6, -2.6, 1.6)), Vector((-3.6, 0, 1.45)), lens=50)
common.render(os.path.join(OUT, 'close_sci_general.png'))
print('MODERN PEOPLE DONE')

# WS18 ANIMAL LINEUP: every catalogue animal side by side at REAL size (blender/lib/animals.py), all facing -Y
# (heads to the LEFT of the frame), next to a 1.7 m man and a 1 m scale pole, playing its idle clip.
# Checks: size right? facing right? feet on the ground? materials not plastic? clip plays?
# Laptop only (Sketchfab scans).  Run: blender -b --python blender/scenes/animals_lineup_test.py -- <out_dir> [frame] [kinds,...]
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy
from mathutils import Vector
from lib import animals, common, scatter

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'animals_lineup'
FRAME = int(argv[1]) if len(argv) > 1 else 20
KINDS = argv[2].split(',') if len(argv) > 2 else ['elephant', 'camel', 'mule', 'donkey', 'ox', 'goat', 'sheep',
                                                  'pig', 'hound', 'dog', 'cat', 'chicken', 'pigeon', 'raven']
common.reset_scene()
sc = bpy.context.scene; sc.frame_start, sc.frame_end = 1, 120
y = 0.0
for k in KINDS:
    r = animals.load(k, (0, 0, 0), 0.0, name=k)
    st = animals.play(r, 'idle', start=1, end=120)
    a = animals._action(k, 'idle')
    print('SLOT', k, 'want', r.get('slot'), 'have', [sl.identifier for sl in getattr(a, 'slots', [])] if a else None,
          'used', getattr(st, 'action_slot', None) and st.action_slot.identifier)
    bpy.context.view_layer.update()
    meshes = [bpy.data.objects[n] for n in r.get('mesh_names', []) if n in bpy.data.objects]
    if meshes:
        lo, hi = animals._mesh_bbox(meshes)
        r.location.y = y - lo.y + 0.4
        y += (hi.y - lo.y) + 0.8
        print('LINEUP', k, 'len', round(hi.y - lo.y, 2), 'h', round(hi.z - lo.z, 2), 'scale', round(r['scale'], 5),
              'rig', r.get('rig'))
    else:
        print('LINEUP', k, 'MISSING')
# scale references: a 1 m pole with 10 cm bands, and a 1.7 m pole (a man's height)
for (yy, h, nm) in ((-1.2, 1.0, 'pole1m'), (-1.8, 1.7, 'pole17')):
    for i in range(int(h * 10)):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.1, location=(0, yy, i * 0.1 + 0.05))
        bpy.context.object.data.materials.append(common.principled(f'{nm}{i % 2}', (0.8, 0.05, 0.03) if i % 2 else (0.9, 0.9, 0.85)))
gm = scatter.scan_material('lineup_ground', 'brown_mud_dry', tint=(0.85, 0.8, 0.72), tiles=3.0)
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, y / 2, 0)); bpy.context.object.data.materials.append(gm)
common.hdri_world('kloofendal_48d_partly_cloudy_puresky', strength=0.9)
common.sun_light('sun', 3.2, (1.0, 0.92, 0.82), 40, 120)
common.render_settings(res=(2400, 700), samples=24)
mid = (y - 2) / 2
sc.frame_set(FRAME)
os.makedirs(OUT, exist_ok=True)
# side view (heads should all point LEFT), long lens from far = little perspective distortion
common.camera('cam_side', Vector((y * 1.25, mid, 1.4)), Vector((0, mid, 0.9)), lens=50)
sc.camera = bpy.data.objects['cam_side']
common.render(os.path.join(OUT, f'lineup_side_f{FRAME}.png'))
print('LINEUP DONE')

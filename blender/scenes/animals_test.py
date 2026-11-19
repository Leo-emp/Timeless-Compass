# ANIMAL LINEUP: every downloaded animal scan side by side at real-world height (shoulder / standing height), to
# judge quality, scale and era fit before use. Run: blender -b --python blender/scenes/animals_test.py -- <out_dir>
import glob, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common

OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'animals_test'
SCANS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'library', 'scans')
HEIGHT = {'horse_akhalteke': 1.6, 'horse_realistic': 1.6, 'animal_camels': 2.0, 'animal_cow': 1.4, 'animal_goat': 0.75,
          'animal_sheep': 0.8, 'animal_dog': 0.55, 'animal_seagull': 0.3, 'animal_raven_cc0': 0.35}
common.reset_scene()
x = 0.0
for aid, h in HEIGHT.items():
    glb = os.path.join(SCANS, aid, 'model.glb')
    if not os.path.exists(glb):
        gl = glob.glob(os.path.join(SCANS, aid, '**', '*.gltf'), recursive=True)
        if not gl:
            print('MISSING', aid); continue
        glb = gl[0]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=glb)
    new = [o for o in set(bpy.data.objects) - before]
    meshes = [o for o in new if o.type == 'MESH']
    if not meshes:
        print('NO MESH', aid); continue
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    zmin = min(p.z for p in pts); zmax = max(p.z for p in pts)
    cx = sum(p.x for p in pts) / len(pts); cy = sum(p.y for p in pts) / len(pts)
    k = h / max(zmax - zmin, 1e-6)
    root = bpy.data.objects.new(aid + '_root', None); bpy.context.scene.collection.objects.link(root)
    for o in new:
        if o.parent is None:
            o.parent = root
    root.scale = (k, k, k); root.location = (x - cx * k, -cy * k, -zmin * k)
    width = max(p.x for p in pts) - min(p.x for p in pts)
    x += max(width * k, h) + 0.8
    print('ANIMAL', aid, 'height', h, 'scale', round(k, 4))
bpy.ops.mesh.primitive_plane_add(size=200); g = bpy.context.object
g.data.materials.append(common.principled('ground', (0.35, 0.3, 0.25), rough=0.9))
common.hdri_world('kloofendal_48d_partly_cloudy_puresky', strength=0.8)
common.sun_light('sun', 3.0, (1.0, 0.9, 0.8), 35, 210)
common.render_settings(res=(1600, 500), samples=16)
mid = x / 2
bpy.context.scene.camera = common.camera('cam', Vector((mid, -x * 0.75, 2.2)), Vector((mid, 0, 0.7)), lens=40)
os.makedirs(OUT, exist_ok=True)
common.render(os.path.join(OUT, 'lineup.png'))
print('ANIMALS DONE')

# RIDING TEST: a Greek horseman astride the trotting Akhal-Teke (Session E's horse + tack), side + front views at two
# moments of the trot, for each rider heading - pick the heading that matches the horse. Laptop only (Sketchfab scan).
# Run: blender -b --python blender/scenes/riding_test.py -- <out_dir> [heading_deg]
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy
from mathutils import Vector
from lib import cast, common, props, riding, scans_glb
from tc import crowd

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'riding_test'
HEAD = float(argv[1]) if len(argv) > 1 else 0.0
common.reset_scene()
horse = scans_glb.load_glb('horse_akhalteke', loc=(0, 0, 0), rot_z_deg=0)
clip = next((c for c in scans_glb.clips(horse) if 'trot' in c.lower()), None) if hasattr(scans_glb, 'clips') else None
if clip:
    scans_glb.play(horse, clip, frame_start=1)
tack = props.horse_tack(horse, cloth='greek')
seat = next(o for o in bpy.data.objects if o.get('role') == 'rider_seat')
p = crowd.person(7, 'noble', 'greece_480bc')
before = set(bpy.data.objects)
human, rig = cast.build_human(p); cast.groom(human, rig, p)
root = bpy.data.objects.new('rider_root', None); bpy.context.scene.collection.objects.link(root)
for o in set(bpy.data.objects) - before:
    if o.parent is None and o is not root:
        o.parent = root
riding.mount(rig, root, seat, heading_deg=HEAD)
bpy.ops.mesh.primitive_plane_add(size=60); bpy.context.object.data.materials.append(common.principled('g', (0.35, 0.3, 0.24), rough=0.9))
common.hdri_world('kloofendal_48d_partly_cloudy_puresky', strength=0.8); common.sun_light('sun', 3.0, (1, 0.9, 0.8), 35, 210)
common.render_settings(res=(800, 600), samples=12)
sc = bpy.context.scene
os.makedirs(OUT, exist_ok=True)
for f in (1, 9):
    sc.frame_set(f)
    for name, loc in (('side', Vector((4.5, 0.0, 1.6))), ('front', Vector((0.0, -5.0, 1.8)))):
        sc.camera = common.camera('cam_' + name, loc, Vector((0, 0, 1.3)), lens=35)
        common.render(os.path.join(OUT, f'h{int(HEAD)}_{name}_f{f}.png'))
print('RIDING DONE')

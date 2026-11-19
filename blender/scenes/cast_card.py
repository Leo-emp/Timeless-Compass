# CHARACTER CARD: one image per library character for review - front, three-quarter and profile portraits plus a
# full-body view in costume, under neutral film light (real dusk sky + soft key + rim).
# Run: blender -b --python blender/scenes/cast_card.py -- <name> [out_dir] [samples]
#   then: ffmpeg tiles the 4 views into <out_dir>/<name>_card.jpg (done at the end of this script)
import json, os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import build, common

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
NAME = argv[0] if argv else 'themistocles'
OUT = argv[1] if len(argv) > 1 else os.path.join('spike', 'cards')
SAMPLES = int(argv[2]) if len(argv) > 2 else 24

common.reset_scene()
spec = build.manifest('cast', NAME)
wardrobe = spec.get('wardrobe')
# every wardrobe now has a costume (live chiton/himation or a WS3 outfit via lib/costume.py)
rig, human, root, first, last = build.character(NAME, wardrobe, {'pose': 'stand_relaxed'}, frames=24, spec=spec)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, last
if any(m.type == 'CLOTH' for o in bpy.data.objects for m in o.modifiers):
    bpy.ops.ptcache.bake_all(bake=True)
sc.frame_set(first + 6)

head = rig.matrix_world @ rig.pose.bones['head'].head + Vector((0, 0, 0.06))
eyes = rig.matrix_world @ ((rig.pose.bones['eye.L'].head + rig.pose.bones['eye.R'].head) / 2)
common.hdri_world('qwantani_sunset_puresky', strength=0.45, rotate_deg=140)
common.area_light('key', 70, (1.0, 0.8, 0.62), head + Vector((1.3, -1.8, 0.5)), head, 1.2)
common.area_light('rim', 260, (1.0, 0.62, 0.38), head + Vector((-1.2, 1.5, 0.4)), head, 0.7)
bpy.ops.mesh.primitive_plane_add(size=20); floor = bpy.context.object
floor.data.materials.append(common.principled('card_floor', (0.18, 0.16, 0.14), rough=0.9))
common.render_settings(res=(640, 720), samples=SAMPLES)
sc.view_settings.look = 'AgX - Medium High Contrast'
os.makedirs(OUT, exist_ok=True)
views = [('front', (0.0, -1.05, 0.0), 85), ('three_quarter', (0.62, -0.85, 0.02), 85), ('profile', (1.05, 0.0, 0.0), 85)]
files = []
for tag, off, lens in views:
    cam = common.camera('cam_' + tag, head + Vector(off), head, lens=lens, fstop=2.8, focus=eyes)
    sc.camera = cam
    f = os.path.join(OUT, f'{NAME}_{tag}.png'); common.render(f); files.append(f)
feet = rig.matrix_world @ rig.pose.bones['root'].head
body_c = Vector((feet.x, feet.y, head.z * 0.5))
cam = common.camera('cam_body', body_c + Vector((1.2, -3.6, 0.15)), body_c, lens=50, fstop=5.6)
sc.camera = cam
f = os.path.join(OUT, f'{NAME}_body.png'); common.render(f); files.append(f)
card = os.path.join(OUT, f'{NAME}_card.jpg')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error'] + sum([['-i', x] for x in files], []) +
               ['-filter_complex', 'hstack=4', card])
print('CARD DONE', card)

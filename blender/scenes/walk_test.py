# TEST ANIMATION: Themistocles walks along the harbour wall in chiton + himation that FOLLOW the body (cloth sim
# with skeleton-bound pins). Run: blender -b --python blender/scenes/walk_test.py -- <out_dir> [samples] [frames]
import json, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, cast, pose, wardrobe

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT_DIR = argv[0] if argv else 'walk_frames'
SAMPLES = int(argv[1]) if len(argv) > 1 else 16
FRAMES = int(argv[2]) if len(argv) > 2 else 72
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')

common.reset_scene()
spec = json.load(open(os.path.join(ROOT, 'library', 'cast', 'themistocles.json'), encoding='utf-8'))
human, rig = cast.build_human(spec)
cast.scalp_hair(human, rig, spec['hair']); cast.beard(human, rig, spec['beard'])
pos, _, _ = cast.rest_surface(human)
LINEN = wardrobe.border_material('linen_border', (0.80, 0.75, 0.64), (0.08, 0.12, 0.30), width=0.035)
WOOL = wardrobe.border_material('wool_madder', (0.22, 0.035, 0.03), (0.05, 0.04, 0.03), edge=1, width=0.025)
wardrobe.add_collision(human)
ch = wardrobe.chiton(human, rig, pos, LINEN, follow=True)
# the tunic is cloth AND a collider (modifier after the cloth), so the mantle drapes over it while both move
col = ch.modifiers.new('collision', 'COLLISION'); ch.collision.thickness_outer = 0.012; ch.collision.use_culling = False
hm = wardrobe.himation(human, rig, pos, WOOL, side='L', over=ch, follow=True)
for m in hm.modifiers:
    if m.type == 'CLOTH':
        m.collision_settings.distance_min = 0.01
# settle into a standing pose (frames 1-20), then walk (20 -> end); cloth simulates the whole time
pose.blend_into_pose(rig, 'stand_relaxed', start=1, end=20)
pose.walk_cycle(rig, start=21, end=FRAMES)
for o in (ch, hm):
    for m in o.modifiers:
        if m.type == 'CLOTH':
            m.point_cache.frame_end = FRAMES
human.modifiers.new('smooth', 'SUBSURF').levels = 1
bpy.ops.mesh.primitive_plane_add(size=60); bpy.context.object.data.materials.append(common.principled('ground', (0.3, 0.26, 0.22), rough=0.9))
common.sky_world(sun_elev_deg=12, sun_rot_deg=140, strength=0.3)
common.sun_light('sun', 4.0, (1.0, 0.62, 0.36), 12, 118)
cam = common.camera('cam', Vector((3.2, -3.0, 1.4)), Vector((0, -1.0, 1.1)), lens=35)
sc = bpy.context.scene; sc.frame_start, sc.frame_end = 1, FRAMES
# the camera tracks alongside him (same walking speed), like a dolly shot
walked = 1.25 * (FRAMES - 21) / 24
cam.keyframe_insert('location', frame=21)
cam.location.y -= walked; cam.keyframe_insert('location', frame=FRAMES)
common.render_settings(res=(960, 408), samples=SAMPLES)
os.makedirs(OUT_DIR, exist_ok=True)
sc.render.filepath = os.path.join(OUT_DIR, 'f'); sc.render.use_persistent_data = True
bpy.ops.render.render(animation=True)
print('frames done ->', OUT_DIR)

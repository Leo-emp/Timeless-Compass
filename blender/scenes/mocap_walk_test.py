# TEST ANIMATION: Themistocles WALKS with real motion capture (CMU 16_15 "walk"), chiton + himation following
# (cloth with skeleton-bound pins), camera tracking him. Frames 1-30 = cloth pre-roll (not part of the shot).
# Run: blender -b --python blender/scenes/mocap_walk_test.py -- <out_dir> [samples] [mocap frames] [clip]
import json, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, cast, wardrobe, motion

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT_DIR = argv[0] if argv else 'mocap_frames'
SAMPLES = int(argv[1]) if len(argv) > 1 else 16
NMOCAP = int(argv[2]) if len(argv) > 2 else 72
CLIP = argv[3] if len(argv) > 3 else '16_15'
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
PREROLL = 30

common.reset_scene()
spec = json.load(open(os.path.join(ROOT, 'library', 'cast', 'themistocles.json'), encoding='utf-8'))
human, rig = cast.build_human(spec)
cast.scalp_hair(human, rig, spec['hair']); cast.beard(human, rig, spec['beard'])
rig = motion.swap_to_mocap_rig(human, rig)
pos, _, _ = cast.rest_surface(human)
LINEN = wardrobe.border_material('linen_border', (0.80, 0.75, 0.64), (0.08, 0.12, 0.30), width=0.035)
WOOL = wardrobe.border_material('wool_madder', (0.22, 0.035, 0.03), (0.05, 0.04, 0.03), edge=1, width=0.025)
wardrobe.add_collision(human)
# body_measure() asks for default-rig bone names; give it the cmu_mb equivalents
wardrobe.BONE_ALIASES = {'upperarm01.L': 'LeftArm', 'upperarm01.R': 'RightArm', 'upperleg01.L': 'LeftUpLeg',
                         'upperleg01.R': 'RightUpLeg', 'lowerleg01.L': 'LeftLeg', 'lowerleg01.R': 'RightLeg', 'neck01': 'Neck'}
# drape each garment standing still first, then let it follow the motion (see wardrobe.settle_then_follow)
ch = wardrobe.chiton(human, rig, pos, LINEN)
wardrobe.settle_then_follow(ch, human, rig, frames=45, soft=0.25, air=1.0)
ch.modifiers.new('collision', 'COLLISION'); ch.collision.thickness_outer = 0.012; ch.collision.use_culling = False
hm = wardrobe.himation(human, rig, pos, WOOL, side='L', over=ch)
wardrobe.settle_then_follow(hm, human, rig, frames=60, soft=0.35, mass=0.45, air=0.5)
last = motion.apply_bvh(rig, CLIP, start=1, hold=PREROLL, max_frames=NMOCAP)
for o in (ch, hm):
    for m in o.modifiers:
        if m.type == 'CLOTH':
            m.point_cache.frame_end = last
human.modifiers.new('smooth', 'SUBSURF').levels = 1
bpy.ops.mesh.primitive_plane_add(size=80); bpy.context.object.data.materials.append(common.principled('ground', (0.3, 0.26, 0.22), rough=0.9))
common.sky_world(sun_elev_deg=12, sun_rot_deg=140, strength=0.3)
common.sun_light('sun', 4.0, (1.0, 0.62, 0.36), 12, 118)
cam = common.camera('cam', Vector((3.5, -3.0, 1.5)), Vector((0, 0, 1.1)), lens=35)
# camera tracks the hips: keep a fixed offset from where he is on each frame
sc = bpy.context.scene
for f in range(PREROLL, last + 1, 3):
    sc.frame_set(f)
    hips = rig.matrix_world @ rig.pose.bones['Hips'].head
    cam.location = hips + Vector((3.2, -2.6, 0.45)); common.look_at(cam, hips + Vector((0, 0, 0.35)))
    cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)
sc.frame_start, sc.frame_end = 1, last
common.render_settings(res=(960, 408), samples=SAMPLES)
os.makedirs(OUT_DIR, exist_ok=True)
sc.render.filepath = os.path.join(OUT_DIR, 'f')
# cloth must simulate from frame 1: bake it all first, then render only the shot (frames after the pre-roll)
sc.frame_start = 1
bpy.ops.ptcache.bake_all(bake=True)
sc.frame_start = PREROLL + 1
bpy.ops.render.render(animation=True)
print('frames done ->', OUT_DIR, 'shot frames from', PREROLL)

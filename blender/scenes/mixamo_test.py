# MOTION TEST: every Mixamo clip in tools/mocap/mixamo retargeted onto our character (no hair/cloth: fast Workbench
# preview), 3 moments per clip -> contact sheet. Catches clips that retarget badly (twisted limbs, floating, sliding).
# Run: blender -b --python blender/scenes/mixamo_test.py -- <out_dir>
import glob, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import cast, common, motion

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'mixamo_test'
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
clips = sorted(os.path.splitext(os.path.basename(f))[0] for f in glob.glob(os.path.join(motion.MOCAP_DIR, 'mixamo', '*.fbx')))
os.makedirs(OUT, exist_ok=True)
spec = json.load(open(os.path.join(ROOT, 'library', 'cast', 'themistocles.json'), encoding='utf-8'))
spec = {k: v for k, v in spec.items() if k not in ('hair', 'beard', 'brow_strands')}
report = []
for clip in clips:
    common.reset_scene()
    human, rig = cast.build_human(spec)
    try:
        last = motion.apply_bvh(rig, clip, start=1, hold=0, max_frames=72)
    except Exception as e:
        report.append(f'{clip}: FAILED {e}'); print('CLIP FAIL', clip, e); continue
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.resolution_x, sc.render.resolution_y = 300, 360
    bpy.ops.mesh.primitive_plane_add(size=30)
    for k, f in enumerate((1, max(2, last // 2), last)):
        sc.frame_set(f)
        hips = rig.matrix_world @ rig.pose.bones['root'].head
        cam = common.camera('cam', hips + Vector((2.2, -3.4, 0.4)), hips + Vector((0, 0, -0.1)), lens=35)
        sc.camera = cam
        sc.render.filepath = os.path.join(OUT, f'{clip}_{k}.png')
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam, do_unlink=True)
    feet = min((rig.matrix_world @ rig.pose.bones[b].tail).z for b in ('foot.L', 'foot.R'))
    report.append(f'{clip}: ok, {last} frames, lowest foot z {feet:.2f}')
open(os.path.join(OUT, 'report.txt'), 'w').write('\n'.join(report))
print('MIXAMO DONE', len(clips))

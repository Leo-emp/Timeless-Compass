# HELMET-UP SWEEP: build one hoplite once, then render the pushed-up Corinthian helmet at several tilt / lift /
# pivot settings (side + three-quarter) so the right one is chosen by EYE, then frozen into armour.helmet_up.
# Run: blender -b --python blender/scenes/helmet_up_sweep.py -- <out_dir>
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from lib import armour, build, common  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else 'spike/style2d/sweep')
os.makedirs(OUT, exist_ok=True)
common.reset_scene()
spec = build.manifest('cast', 'leonidas')
spec['helmet'] = dict(spec.get('helmet') or {'crest': 'red'}, worn='down')
spec.pop('cloak', None)
rig, human, root, first, last = build.character('leonidas', spec['wardrobe'], {'pose': 'stand_relaxed'}, frames=6, spec=spec)
sc = bpy.context.scene
sc.frame_set(first)
helm = next(o for o in bpy.data.objects if o.name.startswith('corinthian_helmet'))
crest = next(o for o in bpy.data.objects if o.name.startswith('crest') and o.parent is rig)
parts = [helm, crest]
base = [o.matrix_world.copy() for o in parts]
hb = armour.bone_head(rig, 'head')
head = rig.matrix_world @ rig.pose.bones['head'].head + Vector((0, 0, 0.08))
common.hdri_world('kloofendal_48d_partly_cloudy_puresky', strength=0.6)
common.sun_light('sun', 3.0, (1.0, 0.95, 0.86), 38, -42)
common.render_settings(res=(360, 360), samples=8)
cams = {'side': common.camera('c_side', head + Vector((1.1, -0.1, 0.0)), head, lens=55),
        'tq': common.camera('c_tq', head + Vector((0.6, -0.95, -0.05)), head, lens=55)}
# (tilt deg, pivot (dy, dz) from the head bone, extra lift): pivot near the back of the crown = how a helmet
# pushed back actually rests (its rear rim on the occiput, the bowl on the crown)
SETS = [(-40, (0.06, 0.15), 0.00), (-50, (0.06, 0.15), 0.00), (-60, (0.06, 0.15), 0.00),
        (-45, (0.08, 0.12), 0.01), (-55, (0.08, 0.12), 0.01), (-50, (0.04, 0.18), 0.0)]
files = []
for i, (tilt, (py, pz), lift) in enumerate(SETS):
    piv = Vector((hb.x, hb.y + py, hb.z + pz))
    M = Matrix.Translation(piv + Vector((0, 0, lift))) @ Matrix.Rotation(__import__('math').radians(tilt), 4, 'X') @ Matrix.Translation(-piv)
    for o, m0 in zip(parts, base):
        o.matrix_world = M @ m0
    bpy.context.view_layer.update()
    for tag, cam in cams.items():
        sc.camera = cam
        f = os.path.join(OUT, f'{i}_{tag}.png'); common.render(f); files.append(f)
    print(f'SET {i}: tilt {tilt} pivot dy {py} dz {pz} lift {lift}', flush=True)
args = []
for f in files:
    args += ['-i', f]
n = len(files)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *args, '-filter_complex',
                ''.join(f'[{k}:v]' for k in range(n)) + f'xstack=inputs={n}:layout=' +
                '|'.join(f'{(k % 4) * 360}_{(k // 4) * 360}' for k in range(n)) + '[o]', '-map', '[o]',
                os.path.join(OUT, 'sweep.jpg')])
print('SWEEP DONE')

# WS18 CAVALRY TEST: a squadron of era horsemen (blender/lib/cavalry.py) in formation, CHARGING toward the camera:
# trot -> gallop speed ramp with clip cross-fade, riders astride with spears/javelins levelled, hoof dust
# (fx.hoof_dust: trailing cloud + puffs). Stills at 4 moments of the charge (rule r13).
# Laptop only (horse scan + MakeHuman).
# Run: blender -b --python blender/scenes/cavalry_test.py -- <out_dir> [era] [n] [unique] [formation] [samples]
#   era = greece_480bc | persia_480bc | rome_100bc | medieval    formation = line | column | wedge | rhombus
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy
from mathutils import Vector
from lib import animals, cavalry, common, fx, scatter

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'cavalry_test'
ERA = argv[1] if len(argv) > 1 else 'persia_480bc'
N = int(argv[2]) if len(argv) > 2 else 8
UNIQUE = int(argv[3]) if len(argv) > 3 else 3
FORM = argv[4] if len(argv) > 4 else 'line'
SAMPLES = int(argv[5]) if len(argv) > 5 else 24
FRAMES = (1, 120)
common.reset_scene()
sc = bpy.context.scene; sc.frame_start, sc.frame_end = FRAMES

gm = scatter.scan_material('cav_ground', 'brown_mud_dry', tint=(0.85, 0.75, 0.58), tiles=4.0)
bpy.ops.mesh.primitive_plane_add(size=600); bpy.context.object.data.materials.append(gm)
common.hdri_world('kloofendal_48d_partly_cloudy_puresky', strength=0.6)
common.sun_light('sun', 4.0, (1.0, 0.85, 0.65), 18, 200)            # low sun behind-left: dust glows

# the squadron starts 60 m away and charges toward -Y (the camera)
movers = cavalry.squadron(ERA, n=N, formation=FORM, center=(0, 60), heading_deg=0.0, unique=UNIQUE, gait='trot',
                          frames=FRAMES, seed=7, charge=True)
units = [o for o in bpy.data.objects if o.get('kind') == 'horse' and o.get('rider')]
end = cavalry.charge(movers, [(0.0, 3.6), (1.5, 6.5), (3.0, 11.0)], start=FRAMES[0], seed=7, units=units)
fx.hoof_dust(movers, frames=FRAMES, length=18, height=4.0, density=0.35, seed=7)

common.render_settings(res=(1280, 720), samples=SAMPLES)
os.makedirs(OUT, exist_ok=True)
# camera low at the ground in the path of the charge, slightly to the side (the classic charge shot)
sc.camera = common.camera('cam_low', Vector((6.0, -4.0, 1.0)), Vector((0, 40, 1.6)), lens=40)
for f in (1, 36, 72, 100):
    sc.frame_set(f)
    common.render(os.path.join(OUT, f'{ERA}_{FORM}_f{f:03d}.png'))
# a side view of one unit at the gallop to judge the rider's seat + weapon + clip
sc.camera = common.camera('cam_side', Vector((14, 20, 1.8)), Vector((0, 20, 1.4)), lens=50)
for f in (60, 64):
    sc.frame_set(f)
    common.render(os.path.join(OUT, f'{ERA}_side_f{f:03d}.png'))
print('CAVALRY DONE')

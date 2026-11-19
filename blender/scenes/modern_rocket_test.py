# WS17 SET TEST (Session F): rocket launch: Mercury-Redstone + gantry at the pad, engine start and lift-off
# Run: blender -b --python blender/scenes/modern_rocket_test.py -- <out_dir> [samples] [people 0|1] [res_scale]
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modern_shot as S
import bpy
from lib import common, lighting, modern
OUT, SAMPLES, PEOPLE, SCALE = S.args()

from lib import fx, modern_props as P
FRAMES = {'ignition': 40, 'liftoff': 90, 'climb': 170}
def build():
    common.sky_world(sun_elev_deg=24, sun_rot_deg=120, strength=0.7, dust=1.5)
    common.sun_light('sun', 4.0, (1.0, 0.95, 0.88), 24, 120)
    g = P.mat('pad_concrete', (0.45, 0.44, 0.42), rough=0.85, bump=0.1, bump_scale=30)
    bpy.ops.mesh.primitive_plane_add(size=3000, location=(0, 0, 0)); bpy.context.object.data.materials.append(g)
    P.launch_tower((-4.2, 0, 0), 30.0)
    fx.rocket_launch('redstone', (0, 0, 0), ignite=30, frames=(1, 200))
import os
which = os.environ.get('TC_ROCKET', 'ignition,liftoff,climb').split(',')
for k in which:
    S.run(build, [('rocket_' + k, (60.0, -140.0, 6.0), (0.0, 0.0, 22.0 if k != 'climb' else 60.0), 50)], OUT, SAMPLES, SCALE, frame=FRAMES[k])

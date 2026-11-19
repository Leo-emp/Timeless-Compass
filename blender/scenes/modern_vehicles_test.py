# WS17 SET TEST (Session F): vehicle + aircraft + rocket shapes (jeep, truck, sedans, B-29, jet, V-2, Redstone, R-7)
# Run: blender -b --python blender/scenes/modern_vehicles_test.py -- <out_dir> [samples] [people 0|1] [res_scale]
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modern_shot as S
import bpy
from lib import common, lighting, modern
OUT, SAMPLES, PEOPLE, SCALE = S.args()

from lib import modern_props as P
def build():
    common.sky_world(sun_elev_deg=30, sun_rot_deg=210, strength=0.7)
    common.sun_light('sun', 4.5, (1.0, 0.95, 0.85), 30, 210)
    g = P.mat('tarmac', (0.25, 0.24, 0.22), rough=0.9, bump=0.1, bump_scale=40)
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0)); bpy.context.object.data.materials.append(g)
    P.jeep((-14, -6, 0), 30); P.army_truck((-6, -4, 0), 20); P.sedan((2, -6, 0), 25, 'sedan40'); P.sedan((8, -6, 0), 25, 'sedan50', style='1950s')
    P.bomber((0, 32, 0), 150); P.jet((-24, 12, 0), 120)
    P.rocket('v2', (20, 8, 0)); P.rocket('redstone', (28, 10, 0)); P.rocket('r7', (40, 14, 0)); P.launch_tower((31.5, 10, 0), 28.0)
S.run(build, [('ground', (0.0, -26.0, 2.0), (2.0, 0.0, 2.0), 28), ('air', (-30.0, -40.0, 22.0), (10.0, 15.0, 6.0), 30),
              ('rockets', (30.0, -22.0, 6.0), (30.0, 10.0, 12.0), 35)], OUT, SAMPLES, SCALE)

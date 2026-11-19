# WS17 SET TEST (Session F): Los Alamos Technical Area 1944: green wooden T-buildings, dirt roads, pines, fence + guard tower
# Run: blender -b --python blender/scenes/modern_huts_test.py -- <out_dir> [samples] [people 0|1] [res_scale]
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modern_shot as S
import bpy
from lib import common, lighting, modern
OUT, SAMPLES, PEOPLE, SCALE = S.args()

def build():
    modern.los_alamos_huts()
    common.sky_world(sun_elev_deg=28, sun_rot_deg=230, strength=0.6, dust=1.2)
    common.sun_light('sun', 5.0, (1.0, 0.93, 0.82), 28, 230)
def people():
    S.place_people([('soldier', 'usa_1945', 2), ('scientist', 'usa_1945', 1)], [(10.0, 0.0, 0.0), (7.0, -2.0, 0.0)], face_toward=(0.0, -20.0))
S.run(build, [('gate', (-18.0, -24.0, 1.7), (5.0, 30.0, 4.0), 32), ('street', (20.0, 8.0, 1.7), (-20.0, 30.0, 4.0), 28)],
      OUT, SAMPLES, SCALE, people=people if PEOPLE else None)

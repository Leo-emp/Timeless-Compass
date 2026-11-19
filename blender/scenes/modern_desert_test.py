# WS17 SET TEST (Session F): Trinity Site at dawn: shot tower 9.1 km north, S-10000 bunker, observers trench, Oscura Mountains
# Run: blender -b --python blender/scenes/modern_desert_test.py -- <out_dir> [samples] [people 0|1] [res_scale]
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modern_shot as S
import bpy
from lib import common, lighting, modern
OUT, SAMPLES, PEOPLE, SCALE = S.args()

def build():
    site = modern.desert_test_site()
    common.sky_world(sun_elev_deg=-1.5, sun_rot_deg=95, strength=0.9, dust=2.0)   # 05:29 - just before sunrise
    common.sun_light('dawn', 0.6, (0.8, 0.85, 1.0), 4, 100)
def people():
    S.place_people([('scientist', 'usa_1945', 1), ('soldier', 'usa_1945', 2), ('scientist', 'usa_1945', 4)],
                   [(-1.5, 12.0, -0.85), (0.5, 12.2, -0.85), (2.2, 11.8, -0.85)], face_toward=(0.0, 9100.0))
S.run(build, [('trench', (1.2, 9.5, 1.0), (0.0, 9100.0, 120.0), 35), ('tower', (45.0, 9040.0, 2.0), (0.0, 9100.0, 18.0), 24),
              ('bunker', (14.0, 15.0, 2.2), (0.0, 30.0, 1.5), 28)], OUT, SAMPLES, SCALE, exposure=0.6, people=people if PEOPLE else None)

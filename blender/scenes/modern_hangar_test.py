# WS17 SET TEST (Session F): steel arch aircraft hangar with a B-29-shaped bomber, jeep and truck
# Run: blender -b --python blender/scenes/modern_hangar_test.py -- <out_dir> [samples] [people 0|1] [res_scale]
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modern_shot as S
import bpy
from lib import common, lighting, modern
OUT, SAMPLES, PEOPLE, SCALE = S.args()

def build():
    modern.hangar()
    common.sky_world(sun_elev_deg=35, sun_rot_deg=200, strength=0.6, dust=1.5)
    common.sun_light('sun', 5.0, (1.0, 0.95, 0.85), 35, 200)
def people():
    S.place_people([('soldier', 'usa_1945', 2), ('worker', 'usa_1945', 3), ('general', 'usa_1945', 4)],
                   [(-6.0, -14.0, 0.0), (-4.5, -12.5, 0.0), (3.5, -16.0, 0.0)], face_toward=(0.0, 0.0))
S.run(build, [('outside', (6.0, -52.0, 2.2), (0.0, 0.0, 6.0), 28), ('inside', (-14.0, -14.0, 1.6), (0.0, 4.0, 3.5), 24)],
      OUT, SAMPLES, SCALE, people=people if PEOPLE else None)

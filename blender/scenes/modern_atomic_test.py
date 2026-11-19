# WS17 SET TEST (Session F): atomic test (Trinity-style): flash, fireball, mushroom cloud, base surge, seen from 9 km
# Run: blender -b --python blender/scenes/modern_atomic_test.py -- <out_dir> [samples] [people 0|1] [res_scale]
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modern_shot as S
import bpy
from lib import common, lighting, modern
OUT, SAMPLES, PEOPLE, SCALE = S.args()

from lib import fx
FRAMES = {'flash': 26, 'fireball': 40, 'rise': 120, 'mushroom': 330}
def build():
    modern.desert_test_site(tower=False, bunkers=True)
    common.sky_world(sun_elev_deg=-1.5, sun_rot_deg=95, strength=0.9, dust=2.0)
    common.sun_light('dawn', 0.6, (0.8, 0.85, 1.0), 4, 100)
    fx.atomic_test((0.0, 9100.0, 30.5), radius=150.0, frame=24, frames=(1, 480))
import os
which = os.environ.get('TC_ATOMIC', 'flash,fireball,rise,mushroom').split(',')
for k in which:
    S.run(build, [('atomic_' + k, (0.0, 0.0, 6.0), (0.0, 9100.0, 900.0), 40)], OUT, SAMPLES, SCALE, frame=FRAMES[k], exposure=-1.0 if k in ('flash', 'fireball') else 0.3)

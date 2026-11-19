# WS17 SET TEST (Session F): 1950s psychiatric ward (MKUltra era): tile + green paint, iron beds, curtains, ECT machine
# Run: blender -b --python blender/scenes/modern_ward_test.py -- <out_dir> [samples] [people 0|1] [res_scale]
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modern_shot as S
import bpy
from lib import common, lighting, modern
OUT, SAMPLES, PEOPLE, SCALE = S.args()

def build():
    modern.psych_ward()
    S.dark_world(0.03, (0.8, 0.9, 1.0))
def people():
    S.place_people([('test_subject', 'usa_1960', 3), ('doctor', 'usa_1960', 2), ('nurse', 'usa_1960', 1)],
                   [(-2.6, 0.4, 0.0), (0.9, 1.0, 0.0), (0.2, 2.1, 0.0)], face_toward=(-2.8, 0.6))
S.run(build, [('wide', (2.4, -6.6, 1.7), (-1.5, 2.5, 1.0), 24), ('ect', (2.2, 0.2, 1.3), (1.2, 1.5, 0.9), 40, 2.8)],
      OUT, SAMPLES, SCALE, people=people if PEOPLE else None)

# WS17 SET TEST (Session F): 1950s interrogation room (one bare bulb, steel table, one-way mirror, reel-to-reel)
# Run: blender -b --python blender/scenes/modern_interrogation_test.py -- <out_dir> [samples] [people 0|1] [res_scale]
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modern_shot as S
import bpy
from lib import common, lighting, modern
OUT, SAMPLES, PEOPLE, SCALE = S.args()

def build():
    modern.interrogation_room()
    S.dark_world(0.005)
def people():
    S.place_people([('test_subject', 'usa_1960', 3), ('agent', 'usa_1960', 9)], [(0.0, 1.05, 0.0), (0.4, -0.5, 0.0)], turns=[0, 180])
S.run(build, [('wide', (-0.9, -2.15, 1.55), (0.1, 0.5, 0.95), 26), ('mirror', (-1.4, 1.7, 1.4), (1.9, 0.2, 1.4), 30)],
      OUT, SAMPLES, SCALE, people=people if PEOPLE else None)

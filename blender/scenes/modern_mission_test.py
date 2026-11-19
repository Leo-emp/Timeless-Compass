# WS17 SET TEST (Session F): Mercury Control Center 1961: tiered consoles, CRTs, world map with orbit track
# Run: blender -b --python blender/scenes/modern_mission_test.py -- <out_dir> [samples] [people 0|1] [res_scale]
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modern_shot as S
import bpy
from lib import common, lighting, modern
OUT, SAMPLES, PEOPLE, SCALE = S.args()

def build():
    modern.mission_control()
    S.dark_world(0.01)
def people():
    S.place_people([('scientist', 'usa_1960', 1), ('scientist', 'usa_1960', 2), ('agent', 'usa_1960', 4)],
                   [(-2.2, -0.8, 0.0), (2.2, -0.8, 0.0), (0.0, -3.3, 0.35)], face_toward=(0.0, 7.0))
S.run(build, [('back', (4.5, -6.6, 2.6), (-0.5, 6.0, 2.0), 24), ('console', (-1.5, -2.4, 1.6), (-0.8, -1.2, 1.0), 35, 2.8)],
      OUT, SAMPLES, SCALE, people=people if PEOPLE else None)

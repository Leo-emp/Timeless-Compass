# WS17 SET TEST (Session F): underground Cold War command room (barrel vault, map board, plotting table, blast door)
# Run: blender -b --python blender/scenes/modern_bunker_test.py -- <out_dir> [samples] [people 0|1] [res_scale]
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modern_shot as S
import bpy
from lib import common, lighting, modern
OUT, SAMPLES, PEOPLE, SCALE = S.args()

def build():
    modern.bunker_command()
    S.dark_world(0.01)
def people():
    S.place_people([('general', 'usa_1960', 4), ('soldier', 'usa_1960', 6), ('agent', 'usa_1960', 8)],
                   [(0.6, -0.8, 0.0), (-1.4, 1.2, 0.0), (2.4, 1.3, 0.0)], face_toward=(0.0, 4.5))
S.run(build, [('wide', (0.0, -4.2, 1.7), (0.0, 4.0, 1.9), 20), ('map', (-2.2, 1.2, 1.5), (0.0, 4.5, 2.2), 32)],
      OUT, SAMPLES, SCALE, people=people if PEOPLE else None)

# WS17 SET TEST (Session F): US government office, 1945-60 (venetian-blind light bars, desks, typewriters, classified folders)
# Run: blender -b --python blender/scenes/modern_office_test.py -- <out_dir> [samples] [people 0|1] [res_scale]
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modern_shot as S
import bpy
from lib import common, lighting, modern
OUT, SAMPLES, PEOPLE, SCALE = S.args()

def build():
    modern.government_office()
    S.dark_world(0.25, (0.75, 0.8, 0.9))
def people():
    S.place_people([('agent', 'usa_1960', 5), ('secretary', 'usa_1960', 3)], [(-1.6, 1.25, 0.0), (-2.6, -0.9, 0.0)], turns=[180, 70])
S.run(build, [('wide', (0.4, -3.1, 1.65), (-0.6, 1.8, 1.05), 24), ('desk', (-0.75, -0.35, 1.2), (-1.55, 0.6, 0.78), 40, 2.8),
              ('blinds', (1.5, -1.0, 1.3), (0.0, 2.75, 1.8), 30)], OUT, SAMPLES, SCALE, people=people if PEOPLE else None)

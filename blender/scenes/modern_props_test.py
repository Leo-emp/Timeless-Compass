# WS17 SET TEST (Session F): prop sheet: desk equipment (typewriter, phone, reel-to-reel, folders, Geiger counter, projector)
# Run: blender -b --python blender/scenes/modern_props_test.py -- <out_dir> [samples] [people 0|1] [res_scale]
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modern_shot as S
import bpy
from lib import common, lighting, modern
OUT, SAMPLES, PEOPLE, SCALE = S.args()

from lib import modern_props as P
def build():
    S.dark_world(0.05)
    tbl = P.mat('sheet_table', (0.15, 0.09, 0.05), rough=0.45)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -0.02)); bpy.context.object.scale = (3.0, 1.4, 0.04)
    bpy.context.object.data.materials.append(tbl)
    P.typewriter((-1.0, 0.1, 0.0), 10); P.rotary_phone((-0.45, -0.15, 0.0), -10); P.reel_to_reel((0.15, 0.15, 0.0), 0)
    P.folder_stack((0.75, -0.2, 0.0), 8, n=4, seed=2); P.folder((0.75, 0.25, 0.0), -6, 'f_top', stamp='TOP SECRET', seed=5)
    P.geiger_counter((1.2, 0.1, 0.0), -20); P.film_projector((-1.3, -0.45, 0.0), 30)
    P.desk_lamp((-0.1, -0.45, 0.0), 160)
    lighting.film_lights((0.0, 0.0, 0.15), (0.0, -2.2, 1.1), mood='interior', dist=2.0)
S.run(build, [('sheet', (0.0, -2.0, 1.05), (0.0, 0.0, 0.08), 35), ('close', (-0.75, -0.55, 0.35), (-0.75, 0.1, 0.08), 50, 2.8)],
      OUT, SAMPLES, SCALE)

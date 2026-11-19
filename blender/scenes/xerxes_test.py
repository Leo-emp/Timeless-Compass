# TEST STILL: Xerxes, King of Kings, in royal robes and crown (design source: Persepolis reliefs).
# Run: blender -b --python blender/scenes/xerxes_test.py -- <out.png> [samples] [shot: med|full]
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, cast, pose, wardrobe, armour

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'xerxes.png'
SAMPLES = int(argv[1]) if len(argv) > 1 else 64
SHOT = argv[2] if len(argv) > 2 else 'med'

common.reset_scene()
XERXES = {"macro": {"gender": 1.0, "age": 0.6, "muscle": 0.55, "weight": 0.6, "proportions": 0.7, "height": 0.62,
                    "cupsize": 0.5, "firmness": 0.5, "race": {"asian": 0.25, "caucasian": 0.6, "african": 0.15}},
          "skin": "middleage_caucasian_male", "tan": 0.9, "tan_color": (0.7, 0.5, 0.36), "brows": "eyebrow001",
          # the long, carefully curled royal beard of the Persepolis reliefs
          "beard": {"density": 42000, "length": 0.11, "curl": 0.004, "melanin": 0.99}}
human, rig = cast.build_human(XERXES)
cast.beard(human, rig, XERXES['beard'])
cast.scalp_hair(human, rig, {"density": 34000, "length": 0.07, "curl": 0.005, "melanin": 0.99, "flow": (0, 0.4, -1), "flow_amt": 0.7})
pos, _, _ = cast.rest_surface(human)
ROBE = wardrobe.border_material('royal_purple', (0.14, 0.03, 0.16), (0.55, 0.38, 0.08), width=0.05)     # Tyrian purple + gold hem
MANTLE = wardrobe.border_material('royal_mantle', (0.30, 0.05, 0.06), (0.55, 0.38, 0.08), edge=1, width=0.03)
GOLD = common.principled('gold', (0.95, 0.68, 0.25), metal=1.0, rough=0.22, bump=0.05, bump_scale=200)
wardrobe.add_collision(human)
pose.blend_into_pose(rig, 'stand_relaxed', start=1, end=15)
robe = wardrobe.chiton(human, rig, pos, ROBE, length='ankle')
wardrobe.simulate(45); wardrobe.freeze(robe)
rig.animation_data_clear(); pose.apply_pose(rig, 'stand_relaxed')
mantle = wardrobe.himation(human, rig, pos, MANTLE, side='L', over=robe)
wardrobe.simulate(60); wardrobe.freeze(mantle)
armour.persian_crown(rig, GOLD)
human.modifiers.new('smooth', 'SUBSURF').levels = 1

bpy.ops.mesh.primitive_plane_add(size=40); g = bpy.context.object
g.data.materials.append(common.principled('palace_floor', (0.32, 0.27, 0.22), rough=0.55, bump=0.2, bump_scale=4))
common.sky_world(sun_elev_deg=14, sun_rot_deg=140, strength=0.25)
common.sun_light('sun', 3.2, (1.0, 0.62, 0.36), 14, 118)
common.area_light('fill', 40, (0.5, 0.58, 1.0), Vector((2.5, -3.0, 1.8)), Vector((0, 0, 1.4)), 3.0)
if SHOT == 'full':
    common.camera('cam', Vector((1.4, -5.0, 1.2)), Vector((0, 0, 1.0)), lens=45, fstop=4)
else:
    common.camera('cam', Vector((0.9, -2.4, 1.72)), Vector((0.03, 0, 1.6)), lens=55, fstop=2.8)
common.render_settings(samples=SAMPLES, path=OUT)
bpy.context.scene.view_settings.look = 'AgX - High Contrast'
bpy.context.scene.view_settings.exposure = -0.6
common.render()

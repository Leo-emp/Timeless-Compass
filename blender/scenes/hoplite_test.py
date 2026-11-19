# TEST STILL: an Athenian hoplite (marine at Salamis, 480 BC) in full kit, at sunset.
# Run: blender -b --python blender/scenes/hoplite_test.py -- <out.png> [samples] [shot: med|head|full]
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, cast, pose, wardrobe, armour

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'hoplite.png'
SAMPLES = int(argv[1]) if len(argv) > 1 else 64
SHOT = argv[2] if len(argv) > 2 else 'med'

common.reset_scene()
HOPLITE = {"macro": {"gender": 1.0, "age": 0.55, "muscle": 0.9, "weight": 0.55, "proportions": 0.75, "height": 0.62,
                     "cupsize": 0.5, "firmness": 0.5, "race": {"asian": 0.04, "caucasian": 0.8, "african": 0.16}},
           "skin": "middleage_caucasian_male", "tan": 1.0, "tan_color": (0.68, 0.47, 0.33), "brows": "eyebrow003",
           "beard": {"density": 30000, "length": 0.028, "curl": 0.0025, "melanin": 0.98, "grey": 0.0}}
human, rig = cast.build_human(HOPLITE)
cast.beard(human, rig, HOPLITE['beard'])
pos, _, _ = cast.rest_surface(human)

# short linen chiton under the armour (cloth), frozen, then only the skirt part is kept
LINEN = wardrobe.border_material('linen_border', (0.76, 0.70, 0.58), (0.35, 0.05, 0.04), width=0.05)
wardrobe.add_collision(human)
pose.blend_into_pose(rig, 'hoplite_ready', start=1, end=15)
ch = wardrobe.chiton(human, rig, pos, LINEN)
wardrobe.simulate(45)
wardrobe.freeze(ch)
rig.animation_data_clear(); pose.apply_pose(rig, 'hoplite_ready')

BRONZE = common.aged_bronze('bronze')
LEATHER = common.principled('leather', (0.16, 0.08, 0.04), rough=0.6, bump=0.3, bump_scale=120)
WOOD = common.principled('ash_wood', (0.33, 0.22, 0.12), rough=0.6, bump=0.1, bump_scale=300)
helm, crest = armour.corinthian_helmet(human, rig, BRONZE)
cu, hem_z, cy = armour.muscle_cuirass(human, rig, BRONZE)
armour.delete_verts(ch, lambda p: p.z > hem_z - 0.02)               # the tunic shows only below the cuirass
armour.pteruges(hem_z, cy, 0.205, 0.165, LEATHER)
armour.greaves(human, rig, BRONZE)
armour.aspis(rig, BRONZE)
armour.dory(rig, BRONZE, WOOD)
human.modifiers.new('smooth', 'SUBSURF').levels = 1

# rocky shore at sunset
bpy.ops.mesh.primitive_plane_add(size=60); g = bpy.context.object
g.data.materials.append(common.principled('rock', (0.30, 0.25, 0.21), rough=0.95, bump=0.6, bump_scale=5))
common.sky_world(sun_elev_deg=5, sun_rot_deg=160, strength=0.2)
common.sun_light('sun', 4.0, (1.0, 0.6, 0.33), 7, 160)
common.area_light('key', 120, (1.0, 0.78, 0.58), Vector((1.8, -2.6, 2.0)), Vector((0, 0, 1.3)), 2.0)
common.area_light('rim', 300, (1.0, 0.55, 0.3), Vector((-1.6, 2.2, 2.2)), Vector((0, 0, 1.5)), 1.2)
common.area_light('fill', 50, (0.55, 0.6, 1.0), Vector((-2.4, -1.6, 1.4)), Vector((0, 0, 1.0)), 3.0)
head = rig.matrix_world @ rig.pose.bones['head'].head
if SHOT == 'head':
    common.camera('cam', head + Vector((0.45, -1.2, 0.08)), head + Vector((0, 0, 0.06)), lens=85, fstop=2.8)
elif SHOT == 'full':
    common.camera('cam', Vector((1.6, -5.0, 1.15)), Vector((0, 0, 1.0)), lens=45, fstop=4)
else:
    common.camera('cam', Vector((1.0, -2.8, 1.5)), Vector((0.05, 0, 1.25)), lens=45, fstop=3.2)
common.render_settings(samples=SAMPLES, path=OUT)
common.render()

# TEST STILL: a Greek man's portrait (Themistocles look) to judge face + strand hair + beard quality.
# Run: blender -b --python blender/scenes/portrait_test.py -- <out.png> [samples]
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, cast

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'portrait.png'
SAMPLES = int(argv[1]) if len(argv) > 1 else 96

common.reset_scene()
THEMISTOCLES = {
    "macro": {"gender": 1.0, "age": 0.68, "muscle": 0.7, "weight": 0.55, "proportions": 0.7, "height": 0.6,
              "cupsize": 0.5, "firmness": 0.5, "race": {"asian": 0.05, "caucasian": 0.82, "african": 0.13}},
    "skin": "middleage_caucasian_male", "tan": 1.0, "tan_color": (0.72, 0.5, 0.36), "brows": "eyebrow001",
    "hair": {"density": 38000, "length": 0.03, "curl": 0.0035, "melanin": 0.98, "grey": 0.0},
    "beard": {"density": 34000, "length": 0.034, "curl": 0.0022, "melanin": 0.97, "grey": 0.08},
}
human, rig = cast.build_human(THEMISTOCLES)
cast.scalp_hair(human, rig, THEMISTOCLES['hair'])
cast.beard(human, rig, THEMISTOCLES['beard'])
human.modifiers.new('smooth', 'SUBSURF').levels = 1

head = rig.matrix_world @ rig.data.bones['head'].head_local + Vector((0, 0, 0.035))
common.sky_world(sun_elev_deg=5, sun_rot_deg=150, strength=0.25)
common.area_light('key', 70, (1.0, 0.74, 0.52), head + Vector((1.2, -1.6, 0.5)), head, 1.2)     # warm sunset key
common.area_light('rim', 420, (1.0, 0.55, 0.28), head + Vector((-1.1, 1.4, 0.4)), head, 0.8)    # hot rim from behind
common.area_light('fill', 35, (0.55, 0.6, 1.0), head + Vector((-1.6, -1.2, 0.1)), head, 2.0)    # cool sky fill
common.camera('cam', head + Vector((0.42, -1.05, 0.02)), head, lens=85, fstop=2.8)
common.render_settings(samples=SAMPLES, path=OUT)
common.render()

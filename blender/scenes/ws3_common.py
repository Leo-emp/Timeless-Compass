# Shared set-up for the WS3 (wardrobe) test stills: test characters, the dusk set (scanned ground, real sky,
# golden key + strong rim + low fill, as rule r10 asks), cameras and small test-render settings.
# Imported by blender/scenes/ws3_wardrobe.py and blender/scenes/xerxes_v2.py (not run on its own).
import math

import bpy
from mathutils import Vector

from lib import common, cast, wardrobe

# --- test characters (MakeHuman macro settings; real people are never face copies, rule r6) ----------------
# Greek women on vases are painted pale (they spent more time indoors): less sun-tan than the men.
WOMAN = {"macro": {"gender": 0.0, "age": 0.42, "muscle": 0.4, "weight": 0.45, "proportions": 0.6, "height": 0.42,
                   "cupsize": 0.5, "firmness": 0.55, "race": {"caucasian": 0.84, "african": 0.1, "asian": 0.06}},
         "skin": "young_caucasian_female", "tan": 0.45, "tan_color": (0.8, 0.6, 0.46), "brows": "eyebrow010",
         "face": {"head-oval": 0.4, "cheek-bones-incr": 0.2},
         # hair drawn back from the face (it goes under the veil; long braided styles are WS1's job)
         "hair": {"density": 36000, "length": 0.06, "curl": 0.003, "melanin": 0.97, "flow": (0, 1, -0.3),
                  "flow_amt": 0.6, "lift": 0.12}}
PRIESTESS = {**WOMAN, "macro": {**WOMAN["macro"], "age": 0.58, "weight": 0.5}, "skin": "middleage_caucasian_female",
             "age_lines": 0.3}
SERVANT = {"macro": {"gender": 1.0, "age": 0.45, "muscle": 0.78, "weight": 0.4, "proportions": 0.55, "height": 0.45,
                     "cupsize": 0.5, "firmness": 0.5, "race": {"caucasian": 0.7, "african": 0.22, "asian": 0.08}},
           "skin": "middleage_caucasian_male", "tan": 1.0, "tan_color": (0.66, 0.46, 0.32), "brows": "eyebrow001",
           "stubble": 0.6, "age_lines": 0.4, "face": {"nose-hump-incr": 0.25, "chin-width-incr": 0.2},
           "hair": {"density": 32000, "length": 0.022, "curl": 0.004, "melanin": 0.98},
           "beard": {"density": 26000, "length": 0.014, "curl": 0.0018, "melanin": 0.97}}
CHILD = {"macro": {"gender": 1.0, "age": 0.13, "muscle": 0.3, "weight": 0.45, "proportions": 0.5, "height": 0.2,
                   "cupsize": 0.5, "firmness": 0.5, "race": {"caucasian": 0.85, "african": 0.1, "asian": 0.05}},
         "skin": "young_caucasian_male", "tan": 0.8, "tan_color": (0.74, 0.54, 0.4), "brows": "eyebrow010",
         "hair": {"density": 34000, "length": 0.035, "curl": 0.004, "melanin": 0.96}}
PRIEST = {"macro": {"gender": 1.0, "age": 0.82, "muscle": 0.45, "weight": 0.55, "proportions": 0.6, "height": 0.5,
                    "cupsize": 0.5, "firmness": 0.5, "race": {"caucasian": 0.85, "african": 0.1, "asian": 0.05}},
          "skin": "old_caucasian_male", "tan": 0.7, "tan_color": (0.72, 0.52, 0.4), "brows": "eyebrow001",
          "age_lines": 0.8, "face": {"head-oval": 0.3, "nose-hump-incr": 0.3},
          "hair": {"density": 30000, "length": 0.045, "curl": 0.004, "melanin": 0.8, "grey": 0.7},
          "beard": {"density": 34000, "length": 0.07, "curl": 0.0028, "melanin": 0.8, "grey": 0.75}}


def make_person(spec):
    """Build body + face + strand hair/beard; returns (human, rig, rest positions)."""
    human, rig = cast.build_human(spec)
    if spec.get('hair'):
        cast.scalp_hair(human, rig, spec['hair'])
    if spec.get('beard'):
        cast.beard(human, rig, spec['beard'])
    pos, _, _ = cast.rest_surface(human)
    wardrobe.add_collision(human)
    return human, rig, pos


def metals():
    """Bronze for pins, gold for jewellery, leather for sandals and straps (code materials, no textures)."""
    bronze = common.principled('pin_bronze', (0.55, 0.36, 0.16), metal=1.0, rough=0.35, bump=0.03, bump_scale=300)
    gold = common.principled('jewel_gold', (0.92, 0.66, 0.26), metal=1.0, rough=0.22, bump=0.02, bump_scale=400)
    leather = common.principled('sandal_leather', (0.16, 0.08, 0.04), rough=0.6, bump=0.15, bump_scale=120)
    for m in (bronze, gold, leather):
        m.use_fake_user = True
    return bronze, gold, leather


def dusk_set(rig, shot='full', target_z=None, cam_dist=1.0, res=(960, 540), samples=20, out='out.png'):
    """Ground + sky + film light (golden key, strong warm rim, low cool fill) + camera + render settings.
    shot: 'full' (whole figure), 'med' (waist-up), 'head' (head and shoulders)."""
    bpy.ops.mesh.primitive_plane_add(size=30); g = bpy.context.object
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.uv.reset(); bpy.ops.object.mode_set(mode='OBJECT')
    g.data.materials.append(wardrobe.scan_cloth('ground', 'coast_sand_rocks_02', (0.55, 0.49, 0.41), tiles=(15, 15),
                                                grime=0.0, sheen=0.0))
    common.hdri_world('qwantani_sunset_puresky', strength=0.45, rotate_deg=140)
    head = rig.matrix_world @ rig.pose.bones['head'].head
    eyes = rig.matrix_world @ ((rig.pose.bones['eye.L'].head + rig.pose.bones['eye.R'].head) / 2)
    common.sun_light('sun', 2.6, (1.0, 0.6, 0.34), 10, 215)                           # low golden sun
    common.area_light('key', 80, (1.0, 0.76, 0.55), head + Vector((1.6, -2.2, 0.3)), head, 1.6)
    common.area_light('rim', 260, (1.0, 0.6, 0.35), head + Vector((-1.3, 1.6, 0.25)), head, 0.8)
    common.area_light('fill', 6, (0.55, 0.65, 1.0), head + Vector((-2.5, -2.0, -0.4)), head, 2.5)
    H = head.z
    if shot == 'med':
        common.camera('cam', head + Vector((0.75, -1.95, -0.12)) * cam_dist, head + Vector((0.05, 0, -0.2)), lens=55,
                      fstop=2.8, focus=eyes)
    elif shot == 'head':
        common.camera('cam', head + Vector((0.45, -1.15, -0.02)), head + Vector((0.0, 0, -0.04)), lens=70, fstop=2.8,
                      focus=eyes)
    else:
        tz = target_z if target_z is not None else H * 0.56
        d = (H + 0.25) / 1.9 * 4.8 * cam_dist                       # back off for taller figures
        common.camera('cam', Vector((0.3 * d, -d, tz + 0.15)), Vector((0, 0, tz)), lens=45, fstop=5.6, focus=eyes)
    common.render_settings(res=res, samples=samples, path=out)
    bpy.context.scene.view_settings.look = 'AgX - Medium High Contrast'
    bpy.context.scene.view_settings.exposure = -0.6               # tc look: first stills were too bright (0.60 > 0.51)

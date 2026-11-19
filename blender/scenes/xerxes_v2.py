# XERXES v2 + Persian court dress, 480 BC (replaces the weak v1 robe in xerxes_test.py, which was a Greek chiton +
# himation in purple). Design sources: the Persepolis reliefs (Apadana stairs, Treasury audience relief, palace
# door jambs: king and nobles in the pleated "Persian robe" with wide hanging sleeves; guards and ushers in the
# "Median" belted tunic, trousers and rounded cap), Xenophon Cyropaedia 8.3.13 (the king's purple robe, crimson
# trousers, upright tiara), Herodotus 7.61 (Persian dress: tiara, sleeved tunic, trousers). Never copied from films.
# Run: blender -b --python blender/scenes/xerxes_v2.py -- <out.png> [samples] [outfit: king|median] [shot: full|med|head]
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from lib import common, pose, wardrobe
import ws3_common as W

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'xerxes_v2.png'
SAMPLES = int(argv[1]) if len(argv) > 1 else 20
OUTFIT = argv[2] if len(argv) > 2 else 'king'
SHOT = argv[3] if len(argv) > 3 else 'full'
POSE = argv[4] if len(argv) > 4 else None       # e.g. 'stand_open': test the robe with the arms hanging (card pose)

# The audience pose of the reliefs: upper arms a little away from the body (so the robe and sleeves have room),
# both forearms raised forward (on the reliefs the king holds a long sceptre in the right hand and a lotus
# blossom in the left). Added at run time (pose.py belongs to WS5).
pose.POSES['royal_audience'] = {
    "upperarm01.R": (-0.5, -0.22, -1), "lowerarm01.R": (-0.12, -1, 0.3),
    "upperarm01.L": (0.5, -0.22, -1), "lowerarm01.L": (0.12, -1, 0.12),
    "upperleg01.L": (0.05, -0.04, -1), "upperleg01.R": (-0.03, 0.02, -1),
    "lowerleg01.L": (0.02, 0.03, -1), "lowerleg01.R": (-0.02, 0.0, -1),
    "_fingers": 0.6}

XERXES = {"macro": {"gender": 1.0, "age": 0.6, "muscle": 0.55, "weight": 0.6, "proportions": 0.7, "height": 0.62,
                    "cupsize": 0.5, "firmness": 0.5, "race": {"asian": 0.25, "caucasian": 0.6, "african": 0.15}},
          "skin": "middleage_caucasian_male", "tan": 0.6, "tan_color": (0.7, 0.5, 0.36), "brows": "eyebrow001",
          "age_lines": 0.4,
          # long, curled royal beard (the squared, row-curled relief beard is a WS1 beard-style task)
          "beard": {"density": 42000, "length": 0.11, "curl": 0.004, "melanin": 0.99},
          "hair": {"density": 34000, "length": 0.07, "curl": 0.005, "melanin": 0.99, "flow": (0, 0.4, -1), "flow_amt": 0.7}}
MEDE = {**XERXES, "macro": {**XERXES["macro"], "age": 0.45, "weight": 0.45, "height": 0.55},
        "beard": {"density": 34000, "length": 0.06, "curl": 0.0035, "melanin": 0.98},
        "hair": {"density": 34000, "length": 0.05, "curl": 0.005, "melanin": 0.98, "flow": (0, 0.4, -1), "flow_amt": 0.7}}

common.reset_scene()
bronze, gold, leather = W.metals()
spec = XERXES if OUTFIT == 'king' else MEDE              # noble + median: the younger court face
human, rig, pos = W.make_person(spec)
# POSED garments: the body takes its final pose first and stays still while each layer of cloth falls
if POSE and POSE not in pose.POSES:
    from lib import wardrobe as _w
    _w._ensure_poses()
pose.apply_pose(rig, POSE or 'royal_audience')


def cloth(name, scan, dye, band=None, tiles=(7, 5), grime=0.06, width=0.04, sheen=0.2):
    return wardrobe.scan_cloth(name, scan, dye, band=band, tiles=tiles, width=width, grime=grime, sheen=sheen)


if OUTFIT == 'king':
    # Xenophon: purple robe, crimson trousers; gold-embroidered borders (gold garment plaques are real finds)
    PURPLE, CRIMSON, GOLD_THREAD = (0.16, 0.025, 0.12), (0.32, 0.03, 0.035), (0.55, 0.38, 0.08)
    wardrobe.trousers(human, rig, cloth('royal_trousers', 'caban', CRIMSON, tiles=(4, 12), sheen=0.15))
    robe_mat = cloth('royal_robe', 'rough_linen', PURPLE, band=GOLD_THREAD)
    robe = wardrobe.candys(human, rig, pos, robe_mat)
    sleeves = wardrobe.wide_sleeves(human, rig, cloth('royal_sleeves', 'rough_linen', PURPLE, band=GOLD_THREAD))
    wardrobe.belt(rig, robe, gold, kind='strap', knot=False)
    felt = cloth('royal_felt', 'caban', (0.12, 0.02, 0.09), tiles=(3, 3), sheen=0.1)
    wardrobe.persian_cap(human, rig, felt, band=gold, kind='royal')
    wardrobe.earrings(human, rig, gold)
elif OUTFIT == 'noble':
    # a Persian noble / Immortal officer in court dress: robe + sleeves like the king's (no royal purple,
    # no upright tiara) and the fluted, flaring headdress of the reliefs
    BLUE, SAFFRON = (0.06, 0.09, 0.24), (0.5, 0.34, 0.09)
    wardrobe.trousers(human, rig, cloth('noble_trousers', 'caban', (0.28, 0.24, 0.18), tiles=(4, 12), sheen=0.15))
    robe = wardrobe.candys(human, rig, pos, cloth('noble_robe', 'rough_linen', BLUE, band=SAFFRON))
    wardrobe.wide_sleeves(human, rig, cloth('noble_sleeves', 'rough_linen', BLUE, band=SAFFRON))
    wardrobe.belt(rig, robe, leather, kind='strap', knot=False)
    wardrobe.persian_cap(human, rig, cloth('noble_felt', 'caban', (0.42, 0.36, 0.26), tiles=(3, 3), sheen=0.1),
                         band=gold, kind='fluted')
    wardrobe.earrings(human, rig, gold)
else:
    # a Median noble / usher: ochre tunic, patterned-red trousers, felt cap (Persepolis Apadana delegations)
    wardrobe.trousers(human, rig, cloth('mede_trousers', 'caban', (0.3, 0.06, 0.04), tiles=(4, 12), sheen=0.15))
    tunic = wardrobe.median_tunic(human, rig, pos, cloth('mede_tunic', 'rough_linen', (0.45, 0.3, 0.1), band=(0.07, 0.1, 0.26)))
    wardrobe.tight_sleeves(human, rig, cloth('mede_sleeves', 'rough_linen', (0.45, 0.3, 0.1), band=(0.07, 0.1, 0.26)))
    wardrobe.belt(rig, tunic, leather, kind='strap', knot=False)
    wardrobe.persian_cap(human, rig, cloth('mede_felt', 'caban', (0.4, 0.33, 0.24), tiles=(3, 3), sheen=0.1), kind='median')
    wardrobe.earrings(human, rig, gold)

human.modifiers.new('smooth', 'SUBSURF').levels = 1
W.dusk_set(rig, SHOT, samples=SAMPLES, out=OUT)
common.render()

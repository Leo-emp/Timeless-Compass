# CROWD + CAST GENERATOR: every extra is a UNIQUE, era-correct person, made from a seed number.
#   role   (king, queen, prince, child, servant, soldier, commander, priest, citizen, ...) sets gender, age range,
#          rank (what dyes / cleanliness / jewellery they can afford), wardrobe and motion style
#   era    (greece_480bc, persia_480bc, ...) sets ancestry mix, skins, hair and beard customs, palette, wardrobes
#   seed   makes everything else vary: body, ~14 face sculpt targets, hair, beard, dye shade, wear, motion clip,
#          start offset, life-layer seed, shield emblem
# cast() builds a group with no lookalikes (distance check) and skips seeds used in earlier videos
# (library/cast_history.json), so the background people of one video never reappear in the next.
# Output dicts are the same shape as library/cast/*.json specs, so blender/lib/cast.build_human() builds them.
import json
import random
from pathlib import Path

from tc.paths import LIBRARY

HISTORY = LIBRARY / "cast_history.json"
MIN_DISTANCE = 0.12

# --- dyes by rank (linear RGB): what each class could afford in the 5th c. BC -------------------------------
DYES = {   # (linear RGB) - real dyes of the period: madder (red), kermes (crimson), woad/indigo (blue), weld + saffron
           # (yellow), murex (purple, royal only), walnut + oak gall (browns, blacks), and undyed linen / wool
    "royal": [(0.20, 0.02, 0.12), (0.30, 0.03, 0.05), (0.05, 0.06, 0.22), (0.55, 0.38, 0.08), (0.42, 0.04, 0.06),
              (0.68, 0.64, 0.55)],                                                        # purple, crimson, indigo, gold, scarlet, white
    "rich":  [(0.30, 0.05, 0.035), (0.07, 0.10, 0.26), (0.62, 0.58, 0.48), (0.45, 0.30, 0.10), (0.06, 0.16, 0.10),
              (0.50, 0.12, 0.06), (0.12, 0.20, 0.35), (0.55, 0.44, 0.12)],               # madder, woad, white linen, ochre, green...
    "common": [(0.55, 0.50, 0.40), (0.40, 0.30, 0.18), (0.36, 0.13, 0.07), (0.28, 0.28, 0.24), (0.18, 0.22, 0.30),
               (0.48, 0.38, 0.16), (0.62, 0.58, 0.50), (0.25, 0.18, 0.12), (0.40, 0.20, 0.12)],   # linen, browns, faded red/blue...
    "poor":  [(0.40, 0.34, 0.26), (0.33, 0.28, 0.21), (0.30, 0.27, 0.22), (0.46, 0.42, 0.34), (0.24, 0.20, 0.15)],  # undyed wool / hemp
}
GRIME = {"royal": 0.05, "rich": 0.15, "common": 0.3, "poor": 0.5}
EMBLEMS = ["lambda", "gorgon", "owl", "trident", "scorpion", "bull", "lion", "boar", "eagle", "serpent", "pegasus",
           "crab", "dolphin", "wheel", "tripod", "club", "triskeles", "cock", "horse", "star", "crescent", "eye"]
FACE_TARGETS = ["head-square", "head-oval", "head-round", "chin-width-incr", "chin-prominent-incr", "nose-hump-incr",
                "nose-scale-horiz-incr", "nose-point-width-incr", "nose-volume-incr", "cheek-bones-incr",
                "eyebrows-trans-down", "forehead-trans-forward", "mouth-scale-horiz-incr", "ear-scale-incr"]

ERAS = {
    "greece_480bc": {
        "race": {"caucasian": (0.65, 0.9), "african": (0.05, 0.2), "asian": (0.0, 0.1)},
        "skins": {"male": ["middleage_caucasian_male", "young_caucasian_male", "old_caucasian_male"],
                  "female": ["middleage_caucasian_female", "young_caucasian_female", "old_caucasian_female"]},
        "tan": (0.6, 1.0), "hair_melanin": (0.85, 0.99), "beard_customs": {"adult_men": (0.012, 0.04)},
        "height": (0.35, 0.6),                          # ancient people averaged shorter than today
        "roles": {
            "king": ("male", (0.45, 0.85), "royal", "greek_civilian_480bc", "stately"),
            "queen": ("female", (0.3, 0.7), "royal", "greek_woman_480bc", "stately"),
            "prince": ("male", (0.12, 0.35), "royal", "greek_civilian_480bc", "restless"),
            "princess": ("female", (0.12, 0.35), "royal", "greek_woman_480bc", "restless"),
            "child": ("any", (0.05, 0.25), "common", "greek_child_480bc", "restless"),
            "servant": ("any", (0.2, 0.8), "poor", "greek_servant_480bc", "humble"),
            "citizen": ("any", (0.2, 0.95), "common", None, "everyday"),
            "noble": ("any", (0.3, 0.9), "rich", None, "stately"),
            "priest": ("male", (0.5, 0.95), "rich", "greek_priest_480bc", "solemn"),
            "priestess": ("female", (0.3, 0.9), "rich", "greek_priestess_480bc", "solemn"),
            "hoplite": ("male", (0.25, 0.6), "common", "greek_hoplite_480bc", "soldier"),
            "commander": ("male", (0.45, 0.8), "rich", "greek_hoplite_480bc", "commanding"),
            "rower": ("male", (0.2, 0.6), "poor", "greek_servant_480bc", "labour"),
            "fisherman": ("male", (0.25, 0.9), "poor", "greek_servant_480bc", "labour"),
        },
    },
    "persia_480bc": {
        "race": {"caucasian": (0.45, 0.7), "asian": (0.15, 0.4), "african": (0.05, 0.15)},
        "skins": {"male": ["middleage_caucasian_male", "young_caucasian_male", "middleage_asian_male", "old_caucasian_male"],
                  "female": ["middleage_caucasian_female", "young_caucasian_female", "middleage_asian_female"]},
        "tan": (0.6, 1.0), "hair_melanin": (0.92, 1.0), "beard_customs": {"adult_men": (0.03, 0.08)},   # long curled beards
        "height": (0.35, 0.6),
        "roles": {
            "king": ("male", (0.4, 0.8), "royal", "persian_king_480bc", "stately"),
            "queen": ("female", (0.3, 0.7), "royal", "persian_woman_480bc", "stately"),
            "prince": ("male", (0.12, 0.35), "royal", "persian_court_480bc", "restless"),
            "child": ("any", (0.05, 0.25), "common", "persian_court_480bc", "restless"),
            "servant": ("any", (0.2, 0.8), "poor", "persian_servant_480bc", "humble"),
            "courtier": ("male", (0.3, 0.8), "rich", "persian_court_480bc", "stately"),
            "soldier": ("male", (0.25, 0.6), "common", "persian_soldier_480bc", "soldier"),
            "immortal": ("male", (0.25, 0.55), "rich", "persian_immortal_480bc", "soldier"),
            "commander": ("male", (0.45, 0.8), "rich", "persian_court_480bc", "commanding"),
            "archer": ("male", (0.2, 0.55), "common", "persian_soldier_480bc", "soldier"),
        },
    },
}

# 1950s eras (secret government projects): MakeHuman's modern clothes, tinted to period colours. "clothes" per role =
# options of [mhclo name, tint]; "beard_chance" small (men were almost all clean-shaven), short hair.
_SUIT = [["male_elegantsuit01", (0.07, 0.07, 0.08)], ["male_elegantsuit01", (0.1, 0.09, 0.08)], ["male_casualsuit03", (0.16, 0.14, 0.12)]]
_MODERN_ROLES = {
    "scientist": ("male", (0.3, 0.85), "rich", "modern", "everyday", [_SUIT, [["fedora01", (0.12, 0.11, 0.1)], None], [["shoes02", None]]]),
    "official": ("male", (0.4, 0.85), "rich", "modern", "stately", [_SUIT, [["fedora01", (0.08, 0.08, 0.08)], ["fedora_cocked", (0.1, 0.09, 0.08)]], [["shoes01", None]]]),
    "general": ("male", (0.5, 0.85), "rich", "modern", "commanding", [[["male_worksuit01", (0.3, 0.32, 0.22)]], [["shoes02", None]]]),
    "soldier": ("male", (0.18, 0.4), "common", "modern", "soldier", [[["male_worksuit01", (0.33, 0.35, 0.24)]], [["shoes03", None]]]),
    "guard": ("male", (0.2, 0.5), "common", "modern", "soldier", [[["male_worksuit01", (0.15, 0.17, 0.2)]], [["shoes03", None]]]),
    "worker": ("male", (0.2, 0.7), "poor", "modern", "labour", [[["male_worksuit01", (0.2, 0.25, 0.35)], ["male_casualsuit05", (0.3, 0.27, 0.22)]], [["shoes04", None]]]),
    "journalist": ("any", (0.25, 0.6), "common", "modern", "everyday", [[["male_casualsuit02", (0.25, 0.22, 0.18)]], [["fedora01", (0.2, 0.17, 0.13)], None], [["shoes01", None]]]),
    "secretary": ("female", (0.2, 0.55), "common", "modern", "everyday", [[["female_elegantsuit01", (0.15, 0.17, 0.25)], ["female_casualsuit01", (0.35, 0.3, 0.28)]], [["shoes05", None]]]),
}
for _era, _race in (("usa_1950s", {"caucasian": (0.75, 0.95), "african": (0.03, 0.2), "asian": (0.0, 0.08)}),
                    ("ussr_1950s", {"caucasian": (0.85, 1.0), "asian": (0.0, 0.12), "african": (0.0, 0.03)})):
    ERAS[_era] = {"race": _race, "modern": True, "beard_chance": 0.06,
                  "skins": {"male": ["middleage_caucasian_male", "young_caucasian_male", "old_caucasian_male"],
                            "female": ["middleage_caucasian_female", "young_caucasian_female", "old_caucasian_female"]},
                  "tan": (0.0, 0.25), "hair_melanin": (0.3, 0.95), "beard_customs": {"adult_men": (0.004, 0.012)},
                  "height": (0.45, 0.75), "roles": {r: v[:5] for r, v in _MODERN_ROLES.items()},
                  "clothes": {r: v[5] for r, v in _MODERN_ROLES.items()}}

# ROME (Republic, c. 100 BC): men clean-shaven, short hair (beards were for mourning / philosophers); toga & tunic
ERAS["rome_100bc"] = {
    "race": {"caucasian": (0.75, 0.92), "african": (0.04, 0.15), "asian": (0.0, 0.08)}, "clean_shaven": True,
    "skins": ERAS["greece_480bc"]["skins"], "tan": (0.4, 0.9), "hair_melanin": (0.75, 0.99),
    "beard_customs": {"adult_men": (0.0, 0.0)}, "height": (0.38, 0.6),
    "roles": {"senator": ("male", (0.5, 0.9), "rich", "roman_toga_100bc", "stately"),
              "consul": ("male", (0.5, 0.85), "royal", "roman_toga_100bc", "commanding"),
              "legionary": ("male", (0.2, 0.45), "common", "roman_legionary_100bc", "soldier"),
              "centurion": ("male", (0.35, 0.6), "rich", "roman_legionary_100bc", "commanding"),
              "citizen": ("any", (0.2, 0.9), "common", "roman_tunic_100bc", "everyday"),
              "matron": ("female", (0.3, 0.8), "rich", "roman_stola_100bc", "stately"),
              "slave": ("any", (0.15, 0.7), "poor", "roman_tunic_100bc", "humble"),
              "child": ("any", (0.05, 0.25), "common", "roman_tunic_100bc", "restless")}}
# EGYPT (New Kingdom, c. 1250 BC, Ramesses II): Nile-valley ancestry, men shaved or wigged, priests fully shaved,
# white linen, kohl-lined eyes
ERAS["egypt_1250bc"] = {
    "race": {"african": (0.3, 0.55), "caucasian": (0.4, 0.65), "asian": (0.0, 0.08)}, "clean_shaven": True,
    "skins": {"male": ["middleage_african_male", "young_african_male", "middleage_caucasian_male", "old_african_male"],
              "female": ["middleage_african_female", "young_african_female", "middleage_caucasian_female"]},
    "tan": (0.7, 1.0), "hair_melanin": (0.95, 1.0), "beard_customs": {"adult_men": (0.0, 0.0)}, "height": (0.35, 0.58),
    "shaved_roles": ("priest", "scribe"),
    "roles": {"pharaoh": ("male", (0.3, 0.8), "royal", "egypt_royal_1250bc", "stately"),
              "queen": ("female", (0.25, 0.6), "royal", "egypt_royal_1250bc", "stately"),
              "priest": ("male", (0.35, 0.9), "rich", "egypt_priest_1250bc", "solemn"),
              "scribe": ("male", (0.2, 0.7), "rich", "egypt_linen_1250bc", "everyday"),
              "soldier": ("male", (0.2, 0.45), "common", "egypt_soldier_1250bc", "soldier"),
              "worker": ("any", (0.15, 0.7), "poor", "egypt_linen_1250bc", "labour"),
              "noblewoman": ("female", (0.2, 0.6), "rich", "egypt_linen_1250bc", "stately"),
              "child": ("any", (0.05, 0.25), "common", "egypt_linen_1250bc", "restless")}}

MOTIONS = {      # Mixamo / CMU clips per style (blender/lib/motion.apply_bvh finds them by name)
    "stately": ["breathing_idle", "looking_around", "thoughtful_head_shake"],
    "restless": ["looking_around", "breathing_idle", "cheering"],
    "humble": ["sad_idle", "breathing_idle", "kneeling_idle"],
    "everyday": ["breathing_idle", "talking", "looking_around", "arguing", "pointing"],
    "solemn": ["breathing_idle", "sad_idle"],
    "soldier": ["sword_and_shield_idle", "breathing_idle", "looking_around"],
    "commanding": ["pointing", "talking", "sword_and_shield_idle", "arguing"],
    "labour": ["breathing_idle", "looking_around", "kneeling_idle"],
}


def _u(r, lo_hi):
    return r.uniform(*lo_hi)


def person(seed: int, role: str, era: str, age: float | None = None) -> dict:
    """One unique person. `age` (0 child .. 1 very old) overrides the role's random age."""
    E = ERAS[era]
    gender_rule, age_range, rank, wardrobe, style = E["roles"][role]          # KeyError = role not in this era
    r = random.Random(f"{era}:{role}:{seed}")
    gender = r.choice(["male", "female"]) if gender_rule == "any" else gender_rule
    a = age if age is not None else _u(r, age_range)
    race = {k: _u(r, v) for k, v in E["race"].items()}
    tot = sum(race.values()); race = {k: round(v / tot, 3) for k, v in race.items()}
    child = a < 0.3
    macro = {"gender": 1.0 if gender == "male" else 0.0, "age": round(a, 3),
             "muscle": round(_u(r, (0.3, 0.75)) if not child else 0.3, 3),
             "weight": round(_u(r, (0.3, 0.7) if rank != "royal" else (0.45, 0.8)), 3),
             "height": round(_u(r, E["height"]) if not child else a * 1.6, 3),
             "proportions": round(_u(r, (0.4, 0.75)), 3), "cupsize": 0.5, "firmness": 0.5, "race": race}
    skins = E["skins"][gender]
    skin = skins[min(len(skins) - 1, 0 if 0.35 <= a < 0.75 else (1 if a < 0.35 else len(skins) - 1))] \
        if r.random() < 0.7 else r.choice(skins)
    face = {t: round(r.uniform(0.0, 0.45), 3) for t in r.sample(FACE_TARGETS, 6)}
    grey = max(0.0, min(1.0, (a - 0.55) * 2.2 + r.gauss(0, 0.12)))
    hair_len = _u(r, (0.015, 0.04)) if gender == "male" else _u(r, (0.12, 0.35))
    p = {"seed": seed, "role": role, "era": era, "rank": rank, "macro": macro, "skin": skin, "face": face,
         "tan": round(_u(r, E["tan"]) * (0.6 if rank == "royal" else 1.0), 3), "age_lines": round(max(0.0, a - 0.35) * 1.4, 3),
         "stubble": round(r.uniform(0.3, 0.9), 3) if gender == "male" and not child else 0.0,
         "hair": {"density": r.randint(26000, 40000), "length": round(hair_len, 4), "curl": round(_u(r, (0.0015, 0.0045)), 4),
                  "melanin": round(_u(r, E["hair_melanin"]), 3), "grey": round(grey, 3), "bald": round(max(0.0, (a - 0.6) * r.uniform(0, 2.5)), 3)
                  if gender == "male" else 0.0},
         "hair_style": "bun" if (gender == "female" and not E.get("modern") and not child) else None,   # gathered up
         "wardrobe": wardrobe or ("greek_woman_480bc" if gender == "female" and era == "greece_480bc" else
                                  "greek_civilian_480bc" if era == "greece_480bc" else "persian_court_480bc"),
         "dye": {"rank": rank, "main": r.choice(DYES[rank]), "band": r.choice(DYES["rich"]),
                 "grime": round(GRIME[rank] + r.uniform(0, 0.15), 3), "patched": rank == "poor" and r.random() < 0.5},
         "motion": {"clip": r.choice(MOTIONS[style]), "offset_s": round(r.uniform(0, 4), 2),
                    "speed": round(r.uniform(0.9, 1.1), 3), "life_seed": r.randint(0, 10 ** 6)}}
    if E.get("clean_shaven"):                                     # Romans, Egyptians: no beards
        if role in E.get("shaved_roles", ()):
            p["hair"]["length"] = 0.001; p["hair"]["density"] = 6000      # shaved head (stubble only)
        return p
    if E.get("modern"):
        p["hair"]["length"] = round(_u(r, (0.008, 0.02)) if gender == "male" else _u(r, (0.08, 0.2)), 4)
        p["hair"]["curl"] = round(_u(r, (0.0, 0.0015)), 4)
        p["mpfb_clothes"] = [x for x in (r.choice(opts) for opts in E["clothes"][role]) if x]
        p["wardrobe"] = None
        moustache = random.Random(f"beard:{era}:{role}:{seed}").random() < E.get("beard_chance", 0.0)   # own draw
        if not (gender == "male" and a >= 0.3 and moustache):
            return p                                             # clean-shaven (no beard block below)
    if gender == "male" and a >= 0.3:
        lo, hi = E["beard_customs"]["adult_men"]
        p["beard"] = {"density": r.randint(18000, 36000), "length": round(_u(r, (lo, hi)), 4),
                      "curl": round(_u(r, (0.001, 0.003)), 4), "melanin": p["hair"]["melanin"], "grey": round(min(1.0, grey * 1.1), 3)}
    elif gender == "male" and a >= 0.26 and role != "child":                 # late teens: first fuzz
        p["beard"] = {"density": 9000, "length": 0.004, "curl": 0.001, "melanin": p["hair"]["melanin"], "grey": 0.0}   # first fuzz
    if (p["wardrobe"] or "").endswith("hoplite_480bc"):
        p["shield"] = {"emblem": r.choice(EMBLEMS), "rim": r.choice(["bronze", "painted"]), "wear": round(r.uniform(0.2, 0.9), 2)}
        p["helmet"] = {"type": r.choice(["corinthian", "corinthian", "chalcidian", "pilos"]),
                       "crest": r.choice(["red", "black", "white", "none"]) if role != "commander" else "tall_" + r.choice(["red", "white"])}
    return p


def distance(a: dict, b: dict) -> float:
    """How different two people look (0 = identical). Face, body, hair, beard and clothing colour, roughly weighted
    by how much each shows on screen."""
    d = 0.0
    keys = set(a["face"]) | set(b["face"])
    d += 0.35 * sum(abs(a["face"].get(k, 0) - b["face"].get(k, 0)) for k in keys) / max(len(keys), 1) * 4
    for k, w in (("age", 0.5), ("weight", 0.2), ("height", 0.2), ("muscle", 0.1), ("gender", 1.0)):
        d += w * abs(a["macro"][k] - b["macro"][k])
    d += 0.15 * (a["skin"] != b["skin"])
    d += 0.1 * abs(a["hair"]["grey"] - b["hair"]["grey"]) + 3.0 * abs(a["hair"]["length"] - b["hair"]["length"])
    d += 0.15 * sum(abs(x - y) for x, y in zip(a["dye"]["main"], b["dye"]["main"]))
    d += 2.0 * abs((a.get("beard") or {}).get("length", 0) - (b.get("beard") or {}).get("length", 0))
    return d


def cast(n: int, role: str, era: str, seed: int = 0, used_seeds: set | None = None, tries: int = 4000) -> list[dict]:
    """n people of one role, all different from each other and from seeds already used (earlier videos)."""
    used = set(used_seeds or ())
    out, s, k = [], seed * 100003, 0
    while len(out) < n and k < tries:
        s += 1; k += 1
        if s in used:
            continue
        p = person(s, role, era)
        if all(distance(p, q) >= MIN_DISTANCE for q in out):
            out.append(p)
    return out


def load_history() -> set:
    return set(json.loads(HISTORY.read_text(encoding="utf-8"))) if HISTORY.exists() else set()


def save_history(people: list[dict]) -> None:
    HISTORY.write_text(json.dumps(sorted(load_history() | {p["seed"] for p in people})), encoding="utf-8")

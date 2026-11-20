# Shot assembler (Plan 2, task 9): turn every timed shot into a BUILD RECIPE for Blender.
#   shots.timed.json  +  library/ manifests   ->   jobs/<id>/recipes/<shot>.json  +  gaps.json
# A recipe names which library assets to build (characters + their default wardrobe, the set), which motion
# drives the bodies (a motion-capture clip or one of our named poses), the camera move and the frame count.
# Anything the library does not have yet is listed as a GAP (e.g. "cast:xerxes") instead of crashing, so the
# agent knows exactly which assets to build before rendering.
import json
from pathlib import Path

from tc import jobs
from tc.cli import register
from tc.paths import LIBRARY

FPS = 24
KINDS = ("cast", "wardrobe", "sets", "props")

# action words in a shot -> how the body moves. Checked in order; first match wins.
#   clip = CMU motion-capture file in blender's mocap folder; pose = blender/lib/pose.py POSES entry
ACTIONS = [
    # Mixamo acting clips first (real performed motion), then our named poses, then CMU walking
    (("argues", "arguing", "debates", "quarrels"), {"clip": "arguing"}),
    (("points", "pointing", "shows the way"), {"clip": "pointing"}),
    (("kneels", "kneeling", "begs"), {"clip": "kneeling_idle"}),
    (("sits", "seated", "sitting"), {"clip": "sitting_idle"}),
    (("bows", "bowing"), {"clip": "quick_formal_bow"}),
    (("talks", "speaks", "tells", "explains", "says"), {"clip": "talking"}),
    (("slashes", "strikes", "fights", "attacks"), {"clip": "sword_and_shield_slash"}),
    (("blocks", "defends"), {"clip": "sword_and_shield_block"}),
    (("stabs", "thrusts"), {"clip": "stabbing"}),
    (("runs", "charges", "flees"), {"clip": "run_forward"}),
    (("falls", "dies", "is killed"), {"clip": "falling_back_death"}),
    (("cheers", "celebrates"), {"clip": "cheering"}),
    (("mourns", "grieves", "weeps"), {"clip": "sad_idle"}),
    (("hands", "hand over", "gives", "passes"), {"pose": "hand_over"}),
    (("receives", "takes the", "accepts"), {"pose": "receive"}),
    (("walks", "walking", "strides", "paces", "steps"), {"clip": "16_15"}),
    (("stands", "waits", "watches", "looks", "listens", "thinks"), {"pose": "stand_relaxed"}),
    (("readies", "braces", "guards", "spear", "shield"), {"pose": "hoplite_ready"}),
]


def load_library(root: Path = LIBRARY) -> dict:
    """{kind: {name: manifest}} for every JSON manifest under library/<kind>/."""
    root = Path(root)
    lib = {k: {} for k in KINDS}
    for kind in KINDS:
        for f in sorted((root / kind).glob("*.json")) if (root / kind).is_dir() else []:
            m = json.loads(f.read_text(encoding="utf-8"))
            lib[kind][m.get("name", f.stem)] = m
    return lib


def _find_set(where: str, sets: dict):
    w = (where or "").strip().lower()
    for name, m in sets.items():
        if w == name.lower() or w in [a.lower() for a in m.get("aliases", [])]:
            return name, m
    return None, None


def _motion(action: str):
    a = (action or "").lower()
    for words, motion in ACTIONS:
        if any(word in a for word in words):
            return dict(motion)
    return None


def recipe_for(shot: dict, lib: dict) -> dict:
    if shot.get("map"):                                       # WS19: a parchment-map shot (blender/lib/maps.py)
        return {"shot": shot["id"], "fps": FPS, "frames": round((shot.get("dur") or 0) * FPS), "at": shot.get("at"),
                "era": shot.get("era"), "kind": "map", "map": shot["map"], "camera": shot.get("camera") or {},
                "cast": [], "crowd": [], "set": None, "motion": None, "expression": {}, "action": "", "missing": []}
    missing = []
    cast = []
    crowds = []
    for who in shot.get("who") or []:
        if who.startswith("crowd:"):                          # crowd:<role>:<count> -> generated extras (tc/crowd.py)
            _, role, count = (who.split(":") + ["1"])[:3]
            crowds.append({"role": role, "count": int(count), "era": shot.get("era") or "greece_480bc"})
            continue
        m = lib["cast"].get(who)
        if m is None:
            missing.append(f"cast:{who}")
            continue
        if shot.get("era") and m.get("era") and m["era"] != shot["era"]:
            missing.append(f"era:{who} is {m['era']}, shot is {shot['era']}")
        wardrobe = m.get("wardrobe")
        if wardrobe and wardrobe not in lib["wardrobe"]:
            missing.append(f"wardrobe:{wardrobe}")
        cast.append({"name": who, "wardrobe": wardrobe})
    set_name, set_m = _find_set(shot.get("where"), lib["sets"])
    if set_m is None:
        missing.append(f"set:{shot.get('where')}")
    motion = None
    if shot.get("who"):
        motion = _motion(shot.get("action"))
        if motion is None:
            missing.append(f"motion:{shot.get('action')}")
    return {"shot": shot["id"], "fps": FPS, "frames": round((shot.get("dur") or 0) * FPS),
            "at": shot.get("at"), "era": shot.get("era"), "action": shot.get("action") or "", "cast": cast,
            "set": {"name": set_name, "builder": set_m.get("builder")} if set_m else None,
            "motion": motion, "camera": shot.get("camera") or {}, "expression": shot.get("expression") or {},
            "crowd": crowds, "missing": missing}


def assemble(shots: list[dict], lib: dict, used_seeds: set | None = None) -> tuple[list[dict], list[str]]:
    """Recipes for every shot. Crowd requests are filled with UNIQUE generated people: never two alike in a video and
    never a seed from an earlier video (used_seeds, default = library/cast_history.json)."""
    from tc import crowd
    used = set(crowd.load_history() if used_seeds is None else used_seeds)
    recipes = [recipe_for(s, lib) for s in shots]
    for r in recipes:
        r["extras"] = []
        for i, c in enumerate(r.get("crowd", [])):
            try:
                people = crowd.cast(c["count"], c["role"], c["era"], seed=len(used) + i + 1, used_seeds=used)
            except KeyError:
                r["missing"].append(f"crowd role:{c['role']} in {c['era']}")
                continue
            used |= {p["seed"] for p in people}
            r["extras"] += people
    gaps = []
    for r in recipes:
        for g in r["missing"]:
            if g not in gaps:
                gaps.append(g)
    return recipes, gaps


@register("assemble", "build a Blender recipe per shot from the library; list library gaps", lambda p: p.add_argument("job"))
def _cmd_assemble(args) -> int:
    d = jobs.job_dir(args.job)
    f = d / "shots.timed.json"
    if not f.exists():
        print("No shots.timed.json yet: run  tc shots <id>  first")
        return 2
    recipes, gaps = assemble(json.loads(f.read_text(encoding="utf-8"))["shots"], load_library())
    from tc import crowd
    crowd.save_history([p for r in recipes for p in r.get("extras", [])])   # never reuse these faces in later videos
    out = d / "recipes"
    out.mkdir(exist_ok=True)
    for r in recipes:
        (out / f"{r['shot']}.json").write_text(json.dumps(r, indent=2), encoding="utf-8")
    (d / "gaps.json").write_text(json.dumps(gaps, indent=2), encoding="utf-8")
    print(f"{len(recipes)} recipes written; {len(gaps)} library gaps")
    for g in gaps:
        print("-", g)
    return 1 if gaps else 0

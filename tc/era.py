# ERA LOCK (`tc era <job>`, owner rules r4 + r32): clothing, armour, weapons, buildings, ships, plants, animals and
# landscapes must all match the exact time and place of the video.
# jobs/<id>/era.json is written in the research stage:
#   {"era": "Classical Greece", "place": "Salamis", "years": "480 BC",
#    "items": [{"id": "trireme", "kind": "ship", "name": "...", "source": "museum piece / excavation / period art", "notes": ""}],
#    "dont":  ["no stirrups", "no Roman armour on Greeks", ...]}
# Every shot in shots.json lists the sheet items it shows ("era_items": [...]); this checks both.
import json

from tc import jobs
from tc.cli import register

ERA_KINDS = {"clothing", "armour", "weapon", "hair", "building", "furniture", "ship", "tool", "plant", "animal",
             "landscape", "colour", "vehicle", "object"}
MIN_DONTS = 3


def era_problems(sheet: dict) -> list[str]:
    probs = []
    for k in ("era", "place", "years"):
        if not str(sheet.get(k, "")).strip():
            probs.append(f"era sheet needs '{k}'")
    items = sheet.get("items", [])
    if not items:
        probs.append("era sheet has no items")
    seen = set()
    for it in items:
        iid = it.get("id", "?")
        if iid in seen:
            probs.append(f"duplicate item id {iid!r}")
        seen.add(iid)
        if it.get("kind") not in ERA_KINDS:
            probs.append(f"item {iid}: kind must be one of {sorted(ERA_KINDS)}")
        if not str(it.get("source", "")).strip():
            probs.append(f"item {iid}: needs a source (museum piece, excavation, period art)")
        if not str(it.get("name", "")).strip():
            probs.append(f"item {iid}: needs a name")
    if len(sheet.get("dont", [])) < MIN_DONTS:
        probs.append(f"list at least {MIN_DONTS} don't-anachronisms (e.g. 'no stirrups')")
    return probs


def shots_era_problems(shots: list[dict], sheet: dict) -> list[str]:
    known = {it.get("id") for it in sheet.get("items", [])}
    probs = []
    for s in shots:
        ids = s.get("era_items")
        if not ids:
            probs.append(f"shot {s.get('id')}: list the era sheet items it shows (era_items)")
            continue
        for i in ids:
            if i not in known:
                probs.append(f"shot {s.get('id')}: {i!r} is not on the era sheet")
    return probs


@register("era", "check jobs/<id>/era.json (and shots.json era_items if present)", lambda p: p.add_argument("job"))
def _cmd_era(args) -> int:
    d = jobs.job_dir(args.job)
    f = d / "era.json"
    if not f.exists():
        print(f"write {f} in the research stage (docs/ART_BIBLE.md section 5)")
        return 1
    sheet = json.loads(f.read_text(encoding="utf-8"))
    probs = era_problems(sheet)
    if (d / "shots.json").exists():
        shots = json.loads((d / "shots.json").read_text(encoding="utf-8"))
        probs += shots_era_problems(shots.get("shots", shots) if isinstance(shots, dict) else shots, sheet)
    for p in probs:
        print("problem:", p)
    print("era:", "OK" if not probs else f"{len(probs)} problem(s)")
    return 1 if probs else 0

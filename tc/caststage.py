# THE CAST STAGE (`tc cast <job>`, rules r19 + r26): before anything is drawn, every character the video needs
# must exist in the registry, pass its sheet check, and have its own voice (no two speakers share one).
# jobs/<id>/cast.json = {"characters": ["themistocles", "xerxes"], "extras": ["messenger"]}
#   characters: registered named characters (library/characters/<id>)
#   extras:     unnamed speaking roles that use a generic voice key from library/voices.json (a messenger, a guard)
import json
import re

from tc import characters, jobs
from tc.cli import register
from tc.dialogue import load_voices
from tc.script import parse_script


def cast_problems(cast: dict, voices: dict, speakers: list[str]) -> list[str]:
    probs, used = [], {}
    chars = voices.get("characters", {})
    known = set(characters.all_ids())
    for cid in cast.get("characters", []):
        if cid not in known:
            probs.append(f"{cid} is not registered (create library/characters/{cid} first)")
            continue
        s = characters.load_sheet(cid)
        probs += [f"{cid}: {p}" for p in characters.sheet_problems(s, voices)]
        ref = chars.get(s.get("voice"), {}).get("reference_id")
        if ref:
            if ref in used:
                probs.append(f"{cid} and {used[ref]} share a voice ({s.get('voice')}); every character needs its own")
            used[ref] = cid
    for e in cast.get("extras", []):
        if e not in chars:
            probs.append(f"extra {e!r} has no voice in library/voices.json")
    names = {re.sub(r"[^a-z0-9]+", "_", n.lower()) for n in cast.get("extras", [])}
    for sp in speakers:
        cid = characters.resolve(sp)
        if cid in cast.get("characters", []) or re.sub(r"[^a-z0-9]+", "_", sp.lower()).strip("_") in names:
            continue
        probs.append(f"{sp} speaks in the script but is not in cast.json (add the character or an extra)")
    return probs


@register("cast", "check jobs/<id>/cast.json: registered characters, sheets pass, one voice each", lambda p: p.add_argument("job"))
def _cmd_cast(args) -> int:
    job = jobs.load_job(args.job)
    d = jobs.job_dir(job.id)
    if not (d / "cast.json").exists():
        print(f"write {d / 'cast.json'} first: {{\"characters\": [...], \"extras\": [...]}}")
        return 1
    cast = json.loads((d / "cast.json").read_text(encoding="utf-8"))
    speakers = []
    if (d / "script.md").exists():
        speakers = sorted({l.speaker for l in parse_script((d / "script.md").read_text(encoding="utf-8")) if l.speaker})
    probs = cast_problems(cast, load_voices(), speakers)
    for p in probs:
        print("problem:", p)
    if probs:
        return 1
    jobs.save_job(jobs.mark(job, "cast", "done", note=f"{len(cast.get('characters', []))} characters"))
    print("cast: done")
    return 0

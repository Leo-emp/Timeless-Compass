# THE FRESH VIEWER (`tc viewer`, owner rule r27): after the script passes its checks, a SEPARATE agent that never
# saw the story page or the writing reads only what a viewer would hear, and decides GO or NO-GO.
#
#   python -m tc viewer <job> --packet                    -> jobs/<id>/qa/viewer_packet.md (+ prints the brief path)
#   (the agent spawns ONE fresh subagent with docs/VIEWER_BRIEF.md + the packet; it answers as JSON)
#   python -m tc viewer <job> --record verdict.json       -> jobs/<id>/qa/viewer.json; stage done only on GO
#
# The packet must not leak the writer's intent: no section names, {loop} markers, sources or tags.
import json
from pathlib import Path

from tc import jobs
from tc.cli import register
from tc.paths import ROOT
from tc.script import parse_script

BRIEF = ROOT / "docs" / "VIEWER_BRIEF.md"
FIELDS = {"verdict": str, "dropoffs": list, "felt": list, "would_finish": bool, "would_subscribe": bool, "notes": str}


def viewer_packet(script_text: str) -> str:
    """Only the words a viewer hears, in order: narrator lines plain, character lines as 'NAME: words'."""
    out = []
    for line in parse_script(script_text):
        words = line.spoken.strip()
        if not words:
            continue
        out.append(f"{line.speaker}: {words}" if line.is_character else words)
        if line.beat:
            out.append("(pause)")
    return "\n\n".join(out) + "\n"


def check_verdict(v: dict) -> list[str]:
    probs = []
    for k, t in FIELDS.items():
        if k not in v:
            probs.append(f"missing field: {k}")
        elif not isinstance(v[k], t):
            probs.append(f"{k} must be {t.__name__}")
    if probs:
        return probs
    if v["verdict"] not in ("GO", "NO-GO"):
        probs.append("verdict must be GO or NO-GO")
    for d in v["dropoffs"]:
        if not isinstance(d, dict) or not d.get("at") or not d.get("why"):
            probs.append("each dropoff needs 'at' and 'why'")
    if v["verdict"] == "GO" and (v["dropoffs"] or not v["would_finish"]):
        probs.append("inconsistent: GO with drop-off moments or without would_finish")
    return probs


def is_go(v: dict) -> bool:
    return not check_verdict(v) and v["verdict"] == "GO"


def save_verdict(job_dir: Path, v: dict) -> None:
    """Append a verdict, stamped with the hash of the script it judged (voice only runs on a GO for that text)."""
    from tc.script import script_hash
    qa_dir = Path(job_dir) / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    f = qa_dir / "viewer.json"
    hist = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    hist.append({**v, "script_hash": script_hash(Path(job_dir))})
    f.write_text(json.dumps(hist, indent=2), encoding="utf-8")


def _args(p):
    p.add_argument("job")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--packet", action="store_true", help="write the viewer packet")
    g.add_argument("--record", help="verdict.json from the fresh viewer agent")


@register("viewer", "fresh-viewer GO/NO-GO on the script (r27): --packet, then --record verdict.json", _args)
def _cmd_viewer(args) -> int:
    job = jobs.load_job(args.job)
    d = jobs.job_dir(job.id)
    qa_dir = d / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    if args.packet:
        out = qa_dir / "viewer_packet.md"
        out.write_text(viewer_packet((d / "script.md").read_text(encoding="utf-8")), encoding="utf-8")
        print(f"packet: {out}\nbrief:  {BRIEF}\nGive ONLY these two files to ONE fresh subagent; save its JSON answer.")
        return 0
    v = json.loads(Path(args.record).read_text(encoding="utf-8"))
    probs = check_verdict(v)
    for p in probs:
        print("problem:", p)
    if probs:
        return 1
    save_verdict(d, v)
    if is_go(v):
        jobs.save_job(jobs.mark(job, "viewer", "done", note="fresh viewer: GO"))
        print("viewer: GO")
        return 0
    print("viewer: NO-GO - rewrite the script using these notes, then run a NEW fresh viewer:")
    for dd in v["dropoffs"]:
        print(f"  - at '{dd['at']}': {dd['why']}")
    print("  notes:", v["notes"])
    return 1

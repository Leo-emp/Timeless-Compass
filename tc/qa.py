# SCORED SELF-CHECKS (`tc qa`): the agent judges its own work against fixed checklists before anything moves on.
# Bar (spec 6.6 + 6.14, owner rule r18): EVERY item passes AND the total is >= 90 / 100. Below the bar the agent
# redraws / rewrites and records a new attempt. Results live in jobs/<id>/qa/<kind>.json, one entry per subject
# (the whole video for "story", one shot id for "still", one thumbnail for "thumbnail", ...).
#
#   python -m tc qa <job> still answers.json --subject s012
#   python -m tc qa status <job>
#
# answers.json = {"<item>": {"pass": true, "score": 11, "note": "why"}, ...} with exactly the checklist's items.
import json
from datetime import datetime
from pathlib import Path

from tc import jobs
from tc.cli import register

BAR = 90

# item -> weight; every list sums to 100. The same tables are printed in docs/ART_BIBLE.md (still, thumbnail) and
# docs/SCRIPT_BIBLE.md (story) so the agent scores against what it drew/wrote by.
CHECKLISTS: dict[str, dict[str, int]] = {
    "story": {"hook_strength": 12, "title_promise": 10, "central_question": 8, "character_want_fear_choice": 10,
              "rising_stakes": 8, "cause_and_effect": 8, "loops_paid_off": 8, "rehook_spacing": 6, "twist": 8,
              "emotional_arc": 8, "best_scene_last_third": 4, "strongest_real_elements": 6, "lines_drawable": 4},
    "still": {"matches_line": 12, "composition": 10, "focal_clarity": 8, "depth_layers": 8, "light_atmosphere": 10,
              "detail_density": 10, "acting": 10, "era_accuracy": 10, "character_match": 8, "grip_and_contact": 6,
              "beats_reference": 8},
    "motion": {"on_the_word": 15, "natural_easing": 15, "anticipation_follow_through": 10, "no_freeze": 10,
               "no_snaps": 15, "camera_motivated": 10, "cuts_motivated": 10, "sound_sync": 15},
    "thumbnail": {"emotion": 20, "striking_object": 15, "readable_160px": 20, "words_le_3": 10, "contrast": 15,
                  "matches_video": 20},
}


def score(kind: str, answers: dict) -> dict:
    """Total + pass/fail. Refuses answers that skip or invent items (a skipped item must never pass silently)."""
    if kind not in CHECKLISTS:
        raise ValueError(f"unknown checklist {kind!r}; one of {sorted(CHECKLISTS)}")
    items = CHECKLISTS[kind]
    missing = [i for i in items if i not in answers]
    extra = [i for i in answers if i not in items]
    if missing or extra:
        raise ValueError(f"{kind} answers: missing {missing}, unknown {extra}")
    total, failing = 0, []
    for item, w in items.items():
        a = answers[item]
        total += max(0, min(w, int(a.get("score", 0))))          # clamp to 0..weight
        if not a.get("pass", False):
            failing.append(item)
    return {"total": total, "passed": not failing and total >= BAR, "failing": failing}


def _file(job_dir: Path, kind: str) -> Path:
    return Path(job_dir) / "qa" / f"{kind}.json"


def record(job_dir: Path, kind: str, answers: dict, subject: str = "video") -> dict:
    """Score and store one attempt for one subject; returns the stored entry (with its attempt count)."""
    result = score(kind, answers)
    f = _file(job_dir, kind)
    f.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    prev = data.get(subject, {})
    entry = {**result, "attempts": prev.get("attempts", 0) + 1, "answers": answers,
             "at": datetime.now().isoformat(timespec="seconds")}
    data[subject] = entry
    f.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return entry


def passed(job_dir: Path, kind: str, subject: str = "video") -> bool:
    f = _file(job_dir, kind)
    if not f.exists():
        return False
    return bool(json.loads(f.read_text(encoding="utf-8")).get(subject, {}).get("passed"))


def _args(p):
    p.add_argument("job")
    p.add_argument("kind", help="story / still / motion / thumbnail, or 'status'")
    p.add_argument("answers", nargs="?", help="answers.json")
    p.add_argument("--subject", default="video")


@register("qa", "record a scored self-check (all items pass and total >= 90), or show the job's qa status", _args)
def _cmd_qa(args) -> int:
    d = jobs.job_dir(args.job)
    if args.kind == "status":
        for f in sorted((d / "qa").glob("*.json")):
            if f.stem in CHECKLISTS:
                for subj, e in json.loads(f.read_text(encoding="utf-8")).items():
                    print(f"{f.stem:9} {subj:12} {'PASS' if e['passed'] else 'FAIL'} {e['total']:3}  attempts {e['attempts']}"
                          + (f"  failing: {', '.join(e['failing'])}" if e["failing"] else ""))
        return 0
    answers = json.loads(Path(args.answers).read_text(encoding="utf-8"))
    e = record(d, args.kind, answers, args.subject)
    print(f"{args.kind} {args.subject}: {'PASS' if e['passed'] else 'FAIL'} {e['total']}/100 (attempt {e['attempts']})"
          + (f"; failing: {', '.join(e['failing'])}" if e["failing"] else ""))
    return 0 if e["passed"] else 1

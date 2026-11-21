# SHOT PLAN v2 (`tc shotplan <job>`): what the viewer sees, pinned to the exact words of the voice (r28-r30, r34).
# jobs/<id>/shotplan.json = {"fps": 24, "shots": [...]}, one or more shots per script line, in order. Each shot:
#   id, line (script line index), place (set id: same place = same set inside one video, r23), scene (export name),
#   size ews|ws|ms|cu|ecu, angle eye|low|high|ots|pov, camera {move, amount}, grade {time, mood},
#   transition_in {kind, frames}, era_items [...], start_word (optional: split a line into several shots),
#   beats  [{word, occurrence, do, kind, lead}]   something visibly happens ON that word
#   sfx    [{word, occurrence, sound, db}]        a sound effect on that word
#   music  {cue, from_word} | null                 music only at peaks (r11)
# resolve() turns words into frames using jobs/<id>/timings.json (tc align): a beat's action starts `lead` frames
# (default 6 = 0.25 s) BEFORE its word so the key pose lands ON the word (r29). Output: film/src/jobs/<id>/plan.json.
import json
import re
import subprocess
from pathlib import Path

from tc import jobs
from tc.cli import register
from tc.paths import ROOT

SIZES = {"ews", "ws", "ms", "cu", "ecu"}
ANGLES = {"eye", "low", "high", "ots", "pov"}
CAMERA_MOVES = {"static", "push_in", "pull_out", "pan_left", "pan_right", "tilt_up", "tilt_down", "track",
                "crane_up", "crane_down", "handheld", "rack_focus"}
TRANSITIONS = {"cut", "match", "dissolve", "whip", "fade_black", "flash_white"}
TIMES = {"dawn", "noon", "dusk", "night", "storm", "interior"}
MOODS = {"hope", "neutral", "tension", "battle", "loss", "triumph"}
MAX_GAP_S = 3.0               # r30: something story-related changes at least every 3 s
SAME_RUN = 4                  # 4 shots in a row with the same size + move = monotonous


def _norm(w: str) -> str:
    return re.sub(r"[^a-z0-9']", "", w.lower())


def _line_span(timings: dict, line: int) -> tuple[float, float] | None:
    for l in timings.get("lines", []):
        if l.get("index") == line and l.get("start") is not None:
            return float(l["start"]), float(l["end"])
    return None


def find_word(timings: dict, line: int, word: str, occurrence: int = 1) -> float | None:
    """Start time of the n-th occurrence of `word` inside a script line's time span (None if not heard there)."""
    span = _line_span(timings, line)
    if span is None:
        return None
    inside = [w for w in timings.get("words", []) if span[0] - 0.05 <= w["s"] <= span[1] + 0.05]
    hits = [w["s"] for w in inside if _norm(w["w"]) == _norm(word)]
    if not hits:
        # speech recognition mishears names and rare words ("Themistocles" -> "mysticles", "hulls" -> "halls"):
        # take the most similar heard word in the same line if it is close enough
        import difflib
        scored = sorted(((difflib.SequenceMatcher(None, _norm(w["w"]), _norm(word)).ratio(), w["s"]) for w in inside), reverse=True)
        hits = [scored[0][1]] if scored and scored[0][0] >= 0.6 and occurrence == 1 else []
    return hits[occurrence - 1] if 0 < occurrence <= len(hits) else None


def _shot_start(timings: dict, s: dict, first_of_line: bool) -> float | None:
    if s.get("start_word"):
        return find_word(timings, s["line"], s["start_word"], s.get("start_occurrence", 1))
    span = _line_span(timings, s["line"])
    return span[0] if span else None


def plan_problems(plan: dict, timings: dict, total_s: float) -> list[str]:
    probs, events = [], [0.0]
    shots = plan.get("shots", [])
    if not shots:
        return ["the plan has no shots"]
    seen_lines, ids, prev_start = set(), {s.get("id") for s in shots}, None
    for s in shots:
        sid = s.get("id", "?")
        if s.get("size") not in SIZES:
            probs.append(f"{sid}: size must be one of {sorted(SIZES)}")
        if s.get("angle") not in ANGLES:
            probs.append(f"{sid}: angle must be one of {sorted(ANGLES)}")
        if s.get("camera", {}).get("move") not in CAMERA_MOVES:
            probs.append(f"{sid}: camera move must be one of {sorted(CAMERA_MOVES)}")
        if s.get("transition_in", {}).get("kind") not in TRANSITIONS:
            probs.append(f"{sid}: transition must be one of {sorted(TRANSITIONS)}")
        g = s.get("grade", {})
        if g.get("time") not in TIMES or g.get("mood") not in MOODS:
            probs.append(f"{sid}: grade needs time in {sorted(TIMES)} and mood in {sorted(MOODS)}")
        if not s.get("era_items"):
            probs.append(f"{sid}: list the era items it shows (r32)")
        start = _shot_start(timings, s, s["line"] not in seen_lines)
        seen_lines.add(s.get("line"))
        if start is None:
            probs.append(f"{sid}: its line {s.get('line')} / start_word was not found in the timings")
        else:
            events.append(start)
            # shots must start strictly one after another (else a shot gets zero/negative length and vanishes)
            if prev_start is not None and shots.index(s) > 0 and start <= prev_start:
                probs.append(f"{sid}: starts at or before the previous shot ({start:.2f} s <= {prev_start:.2f} s) - check its start_word")
            prev_start = start if shots.index(s) > 0 else 0.0
        for kind in ("beats", "sfx"):
            for b in s.get(kind, []):
                ln_ = b.get("line", s["line"])          # a beat may sit on a word of a later line the shot also covers
                t = find_word(timings, ln_, b["word"], b.get("occurrence", 1))
                if t is None:
                    probs.append(f"{sid}: {kind[:-1] if kind == 'beats' else 'sfx'} word {b['word']!r} (occurrence {b.get('occurrence', 1)}) not heard in line {ln_}")
                elif kind == "beats":
                    events.append(t)
        m = s.get("music")
        if m:
            if m.get("from_word") and find_word(timings, m.get("line", s["line"]), m["from_word"]) is None:
                probs.append(f"{sid}: music from_word {m['from_word']!r} not heard in line {m.get('line', s['line'])}")
            if m.get("until") and m["until"] not in ids:
                probs.append(f"{sid}: music until {m['until']!r} is not a shot in this plan")
    events = sorted(set(events + [total_s]))
    for a, b in zip(events, events[1:]):
        if b - a > MAX_GAP_S:
            probs.append(f"nothing happens between {a:.1f} s and {b:.1f} s (r30: something every <= {MAX_GAP_S:.0f} s)")
    for i in range(len(shots) - SAME_RUN + 1):
        run = shots[i:i + SAME_RUN]
        if len({(s.get("size"), s.get("camera", {}).get("move")) for s in run}) == 1:
            probs.append(f"{run[0]['id']}..{run[-1]['id']}: {SAME_RUN} shots in a row with the same size + move")
    return probs


def resolve(plan: dict, timings: dict, total_s: float) -> dict:
    """Timed plan: shot start/end frames (cuts on word boundaries), beat frames, sfx seconds."""
    fps = plan.get("fps", 24)
    shots = [dict(s) for s in plan["shots"]]
    starts, seen = [], set()
    for i, s in enumerate(shots):
        t = 0.0 if i == 0 else _shot_start(timings, s, s["line"] not in seen)
        seen.add(s["line"])
        starts.append(t)
    total_f = round(total_s * fps)
    for i, s in enumerate(shots):
        s["start_f"] = round(starts[i] * fps)
        s["end_f"] = round(starts[i + 1] * fps) if i + 1 < len(shots) else total_f
        beats = []
        for b in s.get("beats", []):
            wf = round(find_word(timings, b.get("line", s["line"]), b["word"], b.get("occurrence", 1)) * fps)
            beats.append(dict(b, word_frame=wf, frame=wf - b.get("lead", 6)))   # word_frame = when the action must LAND
        s["beats"] = beats
        s["sfx"] = [dict(x, at=find_word(timings, x.get("line", s["line"]), x["word"], x.get("occurrence", 1))) for x in s.get("sfx", [])]
        if s.get("music") and s["music"].get("from_word"):
            s["music"] = dict(s["music"], at=find_word(timings, s["music"].get("line", s["line"]), s["music"]["from_word"]))
    return {"fps": fps, "frames": total_f, "shots": shots}


def _duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


@register("shotplan", "check jobs/<id>/shotplan.json against the word timings; write the timed plan for the film", lambda p: p.add_argument("job"))
def _cmd_shotplan(args) -> int:
    job = jobs.load_job(args.job)
    d = jobs.job_dir(job.id)
    plan = json.loads((d / "shotplan.json").read_text(encoding="utf-8"))
    timings = json.loads((d / "timings.json").read_text(encoding="utf-8"))
    total = _duration(d / "voice.wav")
    probs = plan_problems(plan, timings, total)
    for p in probs:
        print("problem:", p)
    if probs:
        return 1
    out = ROOT / "film" / "src" / "jobs" / re.sub(r"[^a-z0-9_]", "_", job.id.lower()) / "plan.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(resolve(plan, timings, total), indent=1), encoding="utf-8")
    jobs.save_job(jobs.mark(job, "shots", "done", note=f"{len(plan['shots'])} shots"))
    print(f"shotplan OK -> {out}")
    return 0

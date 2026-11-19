# The shot list: what the viewer SEES for every spoken line (jobs/<id>/shots.json, written by Claude).
# Rules checked here (owner + spec):
#   - literal rule: every script line is covered by at least one shot
#   - pacing: each shot 3-7 s (up to 8 s only if "hold": true)
#   - camera moves come from a fixed film vocabulary
#   - no captions: a card may only be a place/date card or a map label
#   - anti-samey: two shots in a row never share the same set + move + angle
#   - the shots add up to the narration's length
# Timing comes from the real voice (timings.json), so cuts land on the spoken words.
import json
from dataclasses import asdict, dataclass, field

from tc import jobs
from tc.cli import register
from tc.config import Config, get_config
from tc.script import Line, parse_script

CAMERA_MOVES = {"static", "push_in", "pull_out", "pan_left", "pan_right", "tilt_up", "tilt_down",
                "track", "orbit", "crane_up", "crane_down", "handheld"}
CARD_KINDS = {"place_date", "map_label"}
TOTAL_TOLERANCE_S = 0.5


@dataclass
class Shot:
    id: str
    line: int
    at: float | None
    dur: float | None
    hold: bool
    who: list[str]
    where: str
    action: str
    expression: dict
    camera: dict
    sfx: list[str] = field(default_factory=list)
    era: str = ""
    card: dict | None = None
    span: list | None = None          # [start, end] of the spoken line this shot belongs to (set by fill_timing)
    performance: dict | None = None   # per-person acting spec (VISUAL_STANDARD section 4, checked by tc perf)

    @classmethod
    def from_dict(cls, d: dict) -> "Shot":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__} | {"sfx": d.get("sfx") or [], "hold": bool(d.get("hold"))})


def load_shots(path) -> list[Shot]:
    return [Shot.from_dict(d) for d in json.loads(open(path, encoding="utf-8").read())["shots"]]


def fill_timing(shot_list: list[Shot], line_times: list[dict], voice_s: float | None = None) -> list[Shot]:
    """Give every shot a start (at) and length (dur), IN TIMELINE ORDER (returns a new sorted list).
    A line's span runs from its start to the next line's start (pauses belong to the line before them);
    the first line starts at 0 and the last runs to the end of the voice file (voice_s), so the picture never
    stops before the sound. Shots with a dur written by the author keep it; the others split what is left.
    Each line's first shot starts exactly at the line's start, so one line's mistake can't drift the rest."""
    times = sorted(line_times, key=lambda t: t["index"])
    span = {}
    for k, t in enumerate(times):
        start = 0.0 if k == 0 else t["start"]
        end = times[k + 1]["start"] if k + 1 < len(times) else (voice_s if voice_s is not None else t["end"])
        span[t["index"]] = (start, end)
    order = {id(s): i for i, s in enumerate(shot_list)}
    by_line: dict[int, list[Shot]] = {}
    for s in shot_list:
        by_line.setdefault(s.line, []).append(s)
    out = []
    for li in sorted(by_line):
        group = by_line[li]
        if li not in span:                      # a shot pointing at a line that doesn't exist
            for s in group:
                s.dur, s.at, s.span = 0.0, None, None
            out += group
            continue
        start, end = span[li]
        fixed = sum(s.dur for s in group if s.dur)
        free = [s for s in group if not s.dur]
        each = (end - start - fixed) / len(free) if free else 0
        t = start
        for s in sorted(group, key=lambda s: order[id(s)]):
            if not s.dur:
                s.dur = round(each, 3)
            s.at, s.span = round(t, 3), [start, end]
            t += s.dur
        out += group
    return out


def check_shots(shot_list: list[Shot], lines: list[Line], line_times: list[dict], cfg: Config, voice_s: float) -> list[str]:
    p = []
    covered = {s.line for s in shot_list}
    for l in lines:
        if l.index not in covered:
            p.append(f"line {l.index}: no shot shows it ({l.text[:50]!r})")
    known = {l.index for l in lines}
    for s in shot_list:
        if s.line not in known:
            p.append(f"{s.id}: points at line {s.line}, which is not in the script")
    by_line: dict[int, list[Shot]] = {}
    for s in shot_list:
        by_line.setdefault(s.line, []).append(s)
    for li, group in by_line.items():
        sp = group[0].span
        if sp and sum(s.dur or 0 for s in group) > (sp[1] - sp[0]) + 0.05:
            p.append(f"line {li}: its shots last {sum(s.dur or 0 for s in group):.1f} s, longer than the spoken line "
                     f"({sp[1] - sp[0]:.1f} s) - shorten the fixed durations")
        if sp and sp[1] - sp[0] < 0.5:
            p.append(f"line {li}: only {sp[1] - sp[0]:.1f} s of voice (check it in `tc align` flagged lines)")
    lo, hi = cfg.shot_s
    for s in shot_list:
        d = round(s.dur or 0, 3)
        top = cfg.hold_max_s if s.hold else hi
        if not lo <= d <= top:
            p.append(f"{s.id}: {d:.1f} s; shots must be {lo}-{top} s" + ("" if s.hold else " (or set hold for up to 8 s)"))
        if (s.camera or {}).get("move") not in CAMERA_MOVES:
            p.append(f"{s.id}: unknown camera move {(s.camera or {}).get('move')!r}")
        if s.card is not None and s.card.get("kind") not in CARD_KINDS:
            p.append(f"{s.id}: card kind {s.card.get('kind')!r} not allowed (no captions; only {sorted(CARD_KINDS)})")
        if not s.who or not s.where or not s.era:
            p.append(f"{s.id}: who, where and era are required")
    for a, b in zip(shot_list, shot_list[1:]):
        key = lambda s: (s.where, (s.camera or {}).get("move"), (s.camera or {}).get("from"))
        if key(a) == key(b):
            p.append(f"{a.id}/{b.id}: same set-up twice in a row {key(a)} (change set, move or angle)")
    total = sum(s.dur or 0 for s in shot_list)
    if abs(total - voice_s) > TOTAL_TOLERANCE_S:
        p.append(f"shots add up to {total:.1f} s but the voice is {voice_s:.1f} s")
    return p


def collect_needs(shot_list: list[Shot]) -> dict:
    """Everything the shots need from the asset library (input for the library check in Plan 2)."""
    return {"who": sorted({w for s in shot_list for w in s.who}), "where": sorted({s.where for s in shot_list}),
            "era": sorted({s.era for s in shot_list}), "sfx": sorted({x for s in shot_list for x in s.sfx})}


@register("shots", "time + check jobs/<id>/shots.json and list library needs", lambda p: p.add_argument("job"))
def _cmd_shots(args) -> int:
    job = jobs.load_job(args.job)
    d = jobs.job_dir(job.id)
    lines = parse_script((d / "script.md").read_text(encoding="utf-8"))
    times = json.loads((d / "timings.json").read_text(encoding="utf-8"))["lines"]
    voice_s = json.loads((d / "voice.json").read_text(encoding="utf-8"))["duration_s"]
    # shots.json is the AUTHOR's file and is never rewritten (computed timings would freeze into it);
    # the timed result goes to shots.timed.json, which later stages read.
    shot_list = fill_timing(load_shots(d / "shots.json"), times, voice_s)
    (d / "shots.timed.json").write_text(json.dumps({"shots": [asdict(s) for s in shot_list]}, indent=2), encoding="utf-8")
    problems = check_shots(shot_list, lines, times, get_config(), voice_s)
    for x in problems:
        print("-", x)
    (d / "needs.json").write_text(json.dumps(collect_needs(shot_list), indent=2), encoding="utf-8")
    jobs.mark(job, "shots", "failed" if problems else "done", f"{len(shot_list)} shots, {len(problems)} problems"); jobs.save_job(job)
    print(f"{len(shot_list)} shots, {len(problems)} problems; needs.json written")
    return 1 if problems else 0

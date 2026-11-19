# PERFORMANCE SPEC: how every person in every shot ACTS (docs/VISUAL_STANDARD.md section 4), and camera
# variety (section 8). Checked straight from the author's jobs/<id>/shots.json, so it works BEFORE any voice or
# timing exists (the full `tc shots` check needs timings.json; this one doesn't).
#
# Each shot with a person carries, next to the usual fields:
#   "performance": {"xerxes": {"emotion": "contempt", "intensity": 2, "brows": ..., "gaze": ..., "lids": ...,
#                              "mouth": ..., "lips": ..., "jaw": ..., "head": ..., "posture": ..., "orientation": ...,
#                              "hands": ..., "gesture": ..., "weight": ..., "interaction": ...}}
#   "camera": {"move": "push_in", "framing": "close", "angle": "low", "side": "left", "lens": 85, "fstop": 2.0}
# Rules:
#   - every named person in `who` has a full spec (crowds "crowd:..." and props "prop:..." don't need one)
#   - emotion is one the face rig can make; intensity 1-5 (default subtle 1-2, film acting, not theatre)
#   - never the same composition (framing + angle + side) twice in a row
#   - never the same character in the same pose (posture + orientation) in two consecutive shots
#   - the lens fits the framing (close-ups on long lenses: a wide lens distorts a face)
#   - a character who speaks a line is IN a shot of that line, at least once close (close-ups for emotion)
#   - every script line has a shot
#   python -m tc perf <job>
import json

from tc import jobs
from tc.cli import register
from tc.script import Line, parse_script

FIELDS = ["emotion", "intensity", "brows", "gaze", "lids", "mouth", "lips", "jaw", "head",
          "posture", "orientation", "hands", "gesture", "weight", "interaction"]
# the face rig's expressions (blender/lib/expressions.py EXPRESSIONS, WS1); kept here as names only because that
# module needs Blender to import
EMOTIONS = {"neutral", "resolve", "anger", "rage", "fear", "grief", "contempt", "cunning", "awe", "pain", "smile"}
# framing -> allowed lens range in mm (35 mm-equivalent; WS8 camera rules: close-up 85, medium 50, wide 28)
LENS = {"extreme_close": (85, 135), "close": (65, 135), "medium_close": (50, 100), "medium": (35, 65),
        "over_shoulder": (35, 85), "pov": (24, 50), "wide": (18, 40), "extreme_wide": (14, 35), "insert": (50, 135)}
ANGLES = {"eye", "low", "high", "top", "dutch", "ground"}
SIDES = {"left", "centre", "right"}
CLOSE = {"extreme_close", "close", "medium_close"}


def _people(shot: dict) -> list[str]:
    """Named characters in the shot (crowds and props have no individual performance)."""
    return [w for w in shot.get("who") or [] if ":" not in w]


def check_performance(shots: list[dict], lines: list[Line]) -> list[str]:
    p: list[str] = []
    for s in shots:
        sid, cam = s.get("id", "?"), s.get("camera") or {}
        framing = cam.get("framing")
        if framing not in LENS:
            p.append(f"{sid}: camera framing {framing!r}; use one of {sorted(LENS)}")
        else:
            lo, hi = LENS[framing]
            if not lo <= (cam.get("lens") or 0) <= hi:
                p.append(f"{sid}: lens {cam.get('lens')} mm does not fit a {framing} ({lo}-{hi} mm)")
        if cam.get("angle") not in ANGLES:
            p.append(f"{sid}: camera angle {cam.get('angle')!r}; use one of {sorted(ANGLES)}")
        if cam.get("side") not in SIDES:
            p.append(f"{sid}: subject side {cam.get('side')!r}; use one of {sorted(SIDES)}")
        perf = s.get("performance") or {}
        for who in _people(s):
            spec = perf.get(who)
            if not spec:
                p.append(f"{sid}: {who} is in the shot but has no performance spec")
                continue
            missing = [f for f in FIELDS if spec.get(f) in (None, "")]
            if missing:
                p.append(f"{sid}: {who} spec is missing {', '.join(missing)}")
            if spec.get("emotion") not in EMOTIONS:
                p.append(f"{sid}: {who} emotion {spec.get('emotion')!r}; the face rig knows {sorted(EMOTIONS)}")
            if not isinstance(spec.get("intensity"), int) or not 1 <= spec["intensity"] <= 5:
                p.append(f"{sid}: {who} intensity {spec.get('intensity')!r}; must be 1-5")
    for a, b in zip(shots, shots[1:]):
        comp = lambda s: tuple((s.get("camera") or {}).get(k) for k in ("framing", "angle", "side"))
        if comp(a) == comp(b):
            p.append(f"{a.get('id')}/{b.get('id')}: same composition twice in a row {comp(a)}")
        for who in set(_people(a)) & set(_people(b)):
            pa, pb = (a.get("performance") or {}).get(who) or {}, (b.get("performance") or {}).get(who) or {}
            if pa and pb and (pa.get("posture"), pa.get("orientation")) == (pb.get("posture"), pb.get("orientation")):
                p.append(f"{a.get('id')}/{b.get('id')}: {who} in the same pose twice in a row ({pa.get('posture')})")
    by_line: dict[int, list[dict]] = {}
    for s in shots:
        by_line.setdefault(s.get("line"), []).append(s)
    for l in lines:
        group = by_line.get(l.index, [])
        if not group:
            p.append(f"line {l.index}: no shot")
            continue
        if l.is_character:
            cast = l.speaker.lower()
            with_speaker = [s for s in group if cast in (s.get("who") or [])]
            if not with_speaker:
                p.append(f"line {l.index}: {l.speaker} speaks but is in none of its shots")
            elif not any((s.get("camera") or {}).get("framing") in CLOSE for s in with_speaker):
                p.append(f"line {l.index}: {l.speaker} speaks; give them a close or medium_close shot")
    return p


@register("perf", "check the per-shot performance spec + camera variety in jobs/<id>/shots.json",
          lambda p: p.add_argument("job"))
def _cmd_perf(args) -> int:
    d = jobs.job_dir(args.job)
    lines = parse_script((d / "script.md").read_text(encoding="utf-8"))
    shots = json.loads((d / "shots.json").read_text(encoding="utf-8"))["shots"]
    problems = check_performance(shots, lines)
    for x in problems:
        print("-", x)
    print(f"{len(shots)} shots, {len(problems)} performance/camera problems")
    return 1 if problems else 0

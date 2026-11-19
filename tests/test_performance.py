# Tests for the per-shot performance spec (docs/VISUAL_STANDARD.md section 4) + camera variety (section 8).
import copy

from tc import performance as pf
from tc.script import parse_script

SCRIPT = ('## hook\nThe king sat above the strait. [src: f]\n'
          '## build\nXERXES: "Write every name." [dramatised]\n'
          '## payoff\nHe tore his robes. [src: f]\n')


def spec(emotion="resolve", posture="seated upright", orientation="three-quarter left"):
    return {"emotion": emotion, "intensity": 2, "brows": "level, slightly lowered", "gaze": "the strait below",
            "lids": "slightly narrowed", "mouth": "closed, corners down", "lips": "pressed", "jaw": "set",
            "head": "chin up, turned 10 degrees left", "posture": posture, "orientation": orientation,
            "hands": "on the throne arms", "gesture": "none", "weight": "back in the throne",
            "interaction": "ignores the scribe"}


def shot(sid, line, framing, angle="eye", side="centre", who=("xerxes",), perf=None, lens=None):
    lens = lens or {"extreme_close": 100, "close": 85, "medium_close": 65, "medium": 50, "wide": 28,
                    "extreme_wide": 24, "insert": 100, "over_shoulder": 50, "pov": 35}[framing]
    return {"id": sid, "line": line, "who": list(who), "where": "aigaleos_hill", "era": "greece_480bc",
            "action": "sits", "camera": {"move": "static", "framing": framing, "angle": angle, "side": side,
                                         "lens": lens, "fstop": 2.0},
            "performance": perf if perf is not None else {w: spec() for w in who if not w.startswith("crowd:")}}


def good():
    return [shot("s1", 0, "wide", who=("xerxes",), perf={"xerxes": spec(posture="seated upright")}),
            shot("s2", 1, "close", side="left", perf={"xerxes": spec("contempt", posture="leaning forward")}),
            shot("s3", 2, "medium", angle="low", perf={"xerxes": spec("grief", posture="standing, robes torn")})]


LINES = parse_script(SCRIPT)


def test_good_plan_passes():
    assert pf.check_performance(good(), LINES) == []


def test_missing_field():
    s = good(); del s[0]["performance"]["xerxes"]["gaze"]
    assert any("s1" in p and "gaze" in p for p in pf.check_performance(s, LINES))


def test_person_without_spec():
    s = good(); s[0]["performance"] = {}
    assert any("s1" in p and "xerxes" in p and "no performance" in p for p in pf.check_performance(s, LINES))


def test_crowd_needs_no_individual_spec():
    s = good(); s[0]["who"] = ["xerxes", "crowd:scribe:3"]
    assert pf.check_performance(s, LINES) == []


def test_intensity_range():
    s = good(); s[1]["performance"]["xerxes"]["intensity"] = 7
    assert any("intensity" in p for p in pf.check_performance(s, LINES))


def test_unknown_emotion():
    s = good(); s[1]["performance"]["xerxes"]["emotion"] = "happy-ish"
    assert any("emotion" in p for p in pf.check_performance(s, LINES))


def test_same_composition_twice_in_a_row():
    s = good(); s[1]["camera"].update(framing="wide", angle="eye", side="centre", lens=28)
    assert any("same composition" in p for p in pf.check_performance(s, LINES))


def test_same_pose_twice_in_a_row():
    s = good(); s[1]["performance"]["xerxes"]["posture"] = s[0]["performance"]["xerxes"]["posture"]
    s[1]["performance"]["xerxes"]["orientation"] = s[0]["performance"]["xerxes"]["orientation"]
    assert any("same pose" in p for p in pf.check_performance(s, LINES))


def test_lens_must_fit_framing():
    s = good(); s[1]["camera"]["lens"] = 24          # a close-up on a wide lens distorts the face
    assert any("lens" in p for p in pf.check_performance(s, LINES))


def test_speaker_needs_a_close_shot_on_their_line():
    s = good(); s[1]["camera"].update(framing="wide", lens=28)
    assert any("XERXES" in p and "close" in p for p in pf.check_performance(s, LINES))


def test_speaker_must_be_in_the_shot():
    s = good(); s[1]["who"] = ["sicinnus"]; s[1]["performance"] = {"sicinnus": spec()}
    assert any("XERXES" in p for p in pf.check_performance(s, LINES))


def test_every_line_covered():
    s = good()[:2]
    assert any("line 2" in p for p in pf.check_performance(s, LINES))


def test_empty_shot_without_people_is_fine():
    s = good(); s.insert(1, shot("s1b", 0, "insert", who=(), perf={}))
    s[1]["who"] = ["prop:wax_tablet"]
    assert pf.check_performance(s, LINES) == []


def test_shots_module_keeps_performance_through_timing():
    from tc.shots import Shot
    d = copy.deepcopy(good()[0]); d.update(at=None, dur=None, hold=False, expression={})
    assert Shot.from_dict(d).performance["xerxes"]["emotion"] == "resolve"

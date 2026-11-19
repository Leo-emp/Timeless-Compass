# Tests for the shot list: every line shown, pacing, camera vocabulary, no captions, anti-samey.
import json

from tc import shots
from tc.config import Config
from tc.script import parse_script

CFG = Config()
LINES = parse_script("## world\nThe king sat on his throne.\nThe fleet rowed into the strait.\n")
TIMES = [{"index": 0, "start": 0.0, "end": 9.0}, {"index": 1, "start": 9.0, "end": 14.0}]


def shot(i, line, where="strait", move="push_in", frm="low_front", dur=None, hold=False, card=None):
    return shots.Shot.from_dict({"id": f"s{i:03d}", "line": line, "at": None, "dur": dur, "hold": hold,
        "who": ["xerxes"], "where": where, "action": "sits", "expression": {"xerxes": "confident"},
        "camera": {"move": move, "lens_mm": 50, "from": frm}, "sfx": ["wind"], "era": "greece_480bc", "card": card})


def good():
    return shots.fill_timing([shot(1, 0, where="throne"), shot(2, 0, move="pull_out"), shot(3, 1)], TIMES)


def test_good_list_passes():
    assert shots.check_shots(good(), LINES, TIMES, CFG, voice_s=14.0) == []


def test_fill_timing_splits_line():
    s = good()
    assert [x.dur for x in s] == [4.5, 4.5, 5.0] and [x.at for x in s] == [0.0, 4.5, 9.0]


def test_shotlist_rejects_uncovered_line():
    s = shots.fill_timing([shot(1, 0, dur=4.5), shot(2, 0, move="pull_out", dur=4.5)], TIMES)
    assert any("line 1" in p and "no shot" in p for p in shots.check_shots(s, LINES, TIMES, CFG, voice_s=14.0))


def test_duration_bounds():
    s = shots.fill_timing([shot(1, 0, where="throne"), shot(2, 1)], [{"index": 0, "start": 0.0, "end": 9.0}, {"index": 1, "start": 9.0, "end": 14.0}])
    assert any("9.0" in p for p in shots.check_shots(s, LINES, TIMES, CFG, voice_s=14.0))
    held = shots.fill_timing([shot(1, 0, where="throne", hold=True, dur=7.5), shot(2, 0, dur=1.5), shot(3, 1)], TIMES)
    assert not any("s001" in p for p in shots.check_shots(held, LINES, TIMES, CFG, voice_s=14.0))


def test_unknown_camera_move():
    s = good(); s[2].camera["move"] = "dolly_zoom_spin"
    assert any("camera move" in p for p in shots.check_shots(s, LINES, TIMES, CFG, voice_s=14.0))


def test_caption_card_rejected():
    s = good(); s[0].card = {"text": "He sat down", "kind": "subtitle"}
    assert any("card" in p for p in shots.check_shots(s, LINES, TIMES, CFG, voice_s=14.0))


def test_samey_neighbours():
    s = shots.fill_timing([shot(1, 0), shot(2, 0), shot(3, 1, where="throne")], TIMES)
    assert any("same set-up" in p for p in shots.check_shots(s, LINES, TIMES, CFG, voice_s=14.0))


def test_total_must_match_voice():
    assert any("voice" in p for p in shots.check_shots(good(), LINES, TIMES, CFG, voice_s=20.0))


def test_needs_json_collects_assets():
    needs = shots.collect_needs(good())
    assert needs == {"who": ["xerxes"], "where": ["strait", "throne"], "era": ["greece_480bc"], "sfx": ["wind"]}

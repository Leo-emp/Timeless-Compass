# Regression tests for the plan 4 final review (2026-11-21). Each failed before its fix.
import copy

import pytest

from tc import filmjob, shotplan
from tests.test_shotplan import PLAN, TIMINGS, shot


# I1: shot starts must strictly increase (out-of-order start_words made negative-length shots that vanished)
def test_out_of_order_shots_are_a_problem():
    p = copy.deepcopy(PLAN)
    p["shots"] = [shot(1, 0, beats=[{"word": "king", "do": "x", "kind": "gesture"}]),
                  shot(2, 0, start_word="ships", beats=[{"word": "ships", "do": "y", "kind": "reveal"}]),
                  shot(3, 0, start_word="king", beats=[]), shot(4, 1, beats=[{"word": "burn", "do": "z", "kind": "object"}])]
    assert any("starts at or before" in x for x in shotplan.plan_problems(p, TIMINGS, 6.0))


# I2: a music word that isn't heard, an unknown `until` shot, an unknown track - all reported, never silent
def test_music_word_not_heard_is_a_problem():
    p = copy.deepcopy(PLAN); p["shots"][0]["music"] = {"cue": "hook", "from_word": "zzzz"}
    assert any("music" in x and "zzzz" in x for x in shotplan.plan_problems(p, TIMINGS, 6.0))


def test_music_until_unknown_shot_is_a_problem():
    p = copy.deepcopy(PLAN); p["shots"][0]["music"] = {"cue": "hook", "from_word": "The", "until": "s99"}
    assert any("until" in x and "s99" in x for x in shotplan.plan_problems(p, TIMINGS, 6.0))


def test_unknown_track_is_a_clear_error():
    timed = {"fps": 24, "shots": [{"id": "s1", "start_f": 0, "end_f": 24, "music": {"cue": "hook", "track": "nope", "at": 0.0}}]}
    with pytest.raises(ValueError, match="nope"):
        filmjob.music_from_plan(timed, {"tracks": []})


# I3: the film must know each beat's real word frame, not assume a 6-frame lead
def test_resolve_stores_the_word_frame():
    p = copy.deepcopy(PLAN); p["shots"][0]["beats"][0]["lead"] = 12
    b = shotplan.resolve(p, TIMINGS, 6.0)["shots"][0]["beats"][0]
    assert b["word_frame"] == round(0.4 * 24) and b["frame"] == round(0.4 * 24) - 12


# I4: a freeze is judged on the whole picture, so one always-moving detail (waves) can't hide a frozen scene
def test_freeze_uses_whole_frame_change():
    from tc.motioncheck import motion_problems
    tile_max = [0.02] * 240                       # one tile of waves always moving
    mean = [0.0002] * 240                         # but the scene as a whole is frozen
    assert any("frozen" in x for x in motion_problems(tile_max, 24, mean_diffs=mean))


# I5: mux compares the video with the voice length, so a longer re-recorded voice can't be silently cut off
def test_mux_refuses_video_shorter_than_the_voice(tmp_path):
    with pytest.raises(ValueError, match="voice"):
        filmjob.mux(tmp_path / "v.mp4", tmp_path / "a.wav", tmp_path / "o.mp4", expected=54.0,
                    probe=lambda p: 52.3 if p.name == "v.mp4" else 54.3, runner=lambda *a, **k: None)

# Tests for the motion check (`tc motion`): snaps, frozen stretches, and nothing happening on a beat (r29, r30).
from tc.motioncheck import motion_problems

BASE = [0.01] * 240          # 10 s of gentle motion at 24 fps


def test_gentle_motion_is_fine():
    assert motion_problems(BASE, 24) == []


def test_single_spike_is_a_snap():
    d = list(BASE); d[100] = 0.3
    assert any("snap at frame 100" in p for p in motion_problems(d, 24))


def test_cut_is_not_a_snap():
    d = list(BASE); d[100] = 0.3
    assert not any("snap" in p for p in motion_problems(d, 24, cuts=[100]))


def test_three_seconds_still_is_frozen():
    d = list(BASE); d[50:130] = [0.0] * 80
    assert any("frozen from" in p for p in motion_problems(d, 24))


def test_beat_with_no_motion():
    d = [0.01] * 240
    assert any("nothing happens on the beat at frame 120" in p for p in motion_problems(d, 24, beats=[120]))


def test_beat_with_motion_just_before_lands():
    d = [0.01] * 240; d[116] = 0.03
    assert not any("beat" in p for p in motion_problems(d, 24, beats=[120]))

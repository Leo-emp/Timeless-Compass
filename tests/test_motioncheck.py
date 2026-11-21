import math
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


def test_slow_steady_action_counts_as_a_beat():
    d = [0.01] * 240
    for f in range(112, 125):
        d[f] = 0.019                     # below the 2x peak, but steady change all through the window
    d[100] = 0.0; d[130] = 0.0
    assert not any("beat" in p for p in motion_problems(d, 24, beats=[120]))


def test_snap_is_sudden_against_the_frames_just_before():
    from tc.motioncheck import motion_problems
    quiet = [0.004] * 60
    # a smooth eased move of a big figure: change ramps up and down over ~1 s -> not a snap
    ramp = [0.004 + 0.12 * (math.sin(math.pi * i / 24) ** 2) for i in range(25)]
    assert not [p for p in motion_problems(quiet + ramp + quiet, 24) if "snap" in p]
    # a pop (one frame jumps out of stillness) is still a snap
    assert [p for p in motion_problems(quiet + [0.2] + quiet, 24) if "snap" in p]
    # a jerky start (still, then instantly full speed) is still a snap
    assert [p for p in motion_problems(quiet + [0.12] * 20 + quiet, 24) if "snap" in p]
    # a teleport in the middle of a slow move is still a snap
    assert [p for p in motion_problems(quiet + [0.03] * 10 + [0.25] + [0.03] * 10 + quiet, 24) if "snap" in p]

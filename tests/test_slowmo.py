from tc import slowmo


def test_quarter_speed_renders_four_real_frames_per_original_frame():
    m = slowmo.frame_map(0.25)
    assert (m["old"], m["new"]) == (100, 400)
    assert slowmo.render_frames(48, 0.25) == 192


def test_speed_is_clamped_to_film_range():
    assert slowmo.frame_map(0.01)["new"] == 1000       # max 10x slower
    assert slowmo.frame_map(1.0) == {"old": 100, "new": 100}


def test_only_the_biggest_moments_get_slow_motion_and_never_two_in_a_row():
    shots = [{"id": i, "action": a} for i, a in enumerate(
        ["walks to the wall", "the volley of arrows darkens the sky", "the hero dies", "talks",
         "the cavalry charge hits the line", "the cannon fires", "listens", "the ship rams the trireme"])]
    picked = slowmo.pick_moments(shots, max_n=3)
    ids = [s["id"] for s in picked]
    assert len(ids) == 3
    assert all(b - a > 1 for a, b in zip(ids, ids[1:]))      # spaced out, the effect stays special
    assert all(0.2 <= s["speed"] <= 0.5 for s in picked)


def test_dialogue_and_walking_are_never_slowed():
    shots = [{"id": 0, "action": "talks to the king"}, {"id": 1, "action": "walks away"}]
    assert slowmo.pick_moments(shots) == []

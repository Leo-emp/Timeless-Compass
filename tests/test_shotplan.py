# Tests for the v2 shot plan (`tc shotplan`): every beat lands on its word, something happens every <= 3 s (r28-r30).
import copy

from tc.shotplan import plan_problems, resolve

# two lines: "The king watched the ships." (0-2.5 s) / "Then the ships began to burn." (3.0-5.6 s)
WORDS = [{"w": w, "s": s, "e": s + 0.35} for w, s in [("The", 0.0), ("king", 0.4), ("watched", 0.8), ("the", 1.4), ("ships.", 1.8),
                                                         ("Then", 3.0), ("the", 3.4), ("ships", 3.8), ("began", 4.3), ("to", 4.8), ("burn.", 5.1)]]
TIMINGS = {"words": WORDS, "lines": [{"index": 0, "start": 0.0, "end": 2.15}, {"index": 1, "start": 3.0, "end": 5.45}]}


def shot(i, line, size="ws", move="push_in", **kw):
    s = {"id": f"s{i}", "line": line, "place": "throne_hill", "scene": "throne", "size": size, "angle": "eye",
         "camera": {"move": move, "amount": 0.06}, "grade": {"time": "dawn", "mood": "tension"},
         "transition_in": {"kind": "cut", "frames": 0}, "era_items": ["throne"], "beats": [], "sfx": [], "music": None}
    s.update(kw)
    return s


PLAN = {"fps": 24, "shots": [
    shot(1, 0, beats=[{"word": "king", "do": "Xerxes looks up", "kind": "expression"}, {"word": "ships", "do": "ships appear", "kind": "reveal"}],
         sfx=[{"word": "ships", "sound": "waves_soft", "db": -18}]),
    shot(2, 1, size="cu", move="static", beats=[{"word": "burn", "do": "fire bursts", "kind": "object"}]),
]}


def test_valid_plan_resolves_frames():
    assert plan_problems(PLAN, TIMINGS, 6.0) == []
    t = resolve(PLAN, TIMINGS, 6.0)
    s1, s2 = t["shots"]
    assert s1["start_f"] == 0 and s1["end_f"] == s2["start_f"] == round(3.0 * 24) and s2["end_f"] == 144
    assert s1["beats"][0]["frame"] == round(0.4 * 24) - 6          # lands ON the word: starts `lead` frames early
    assert s1["sfx"][0]["at"] == 1.8


def test_unknown_beat_word_is_a_problem():
    p = copy.deepcopy(PLAN); p["shots"][0]["beats"][0]["word"] = "queen"
    assert any("queen" in x for x in plan_problems(p, TIMINGS, 6.0))


def test_repeated_word_uses_occurrence():
    p = copy.deepcopy(PLAN)
    p["shots"][1]["beats"] = [{"word": "the", "occurrence": 1, "do": "x", "kind": "gesture"}, {"word": "burn", "do": "y", "kind": "object"}]
    t = resolve(p, TIMINGS, 6.0)
    assert t["shots"][1]["beats"][0]["frame"] == round(3.4 * 24) - 6   # the 'the' INSIDE line 1, not line 0's


def test_gap_over_three_seconds_is_a_problem():
    p = copy.deepcopy(PLAN); p["shots"][0]["beats"] = []; p["shots"][1]["beats"] = []
    assert any("nothing happens" in x for x in plan_problems(p, TIMINGS, 8.0))


def test_four_same_shots_in_a_row():
    words = [{"w": f"w{i}", "s": i * 1.0, "e": i * 1.0 + 0.4} for i in range(8)]
    tm = {"words": words, "lines": [{"index": i, "start": i * 2.0, "end": i * 2.0 + 1.4} for i in range(4)]}
    p = {"fps": 24, "shots": [shot(i, i, size="ms", move="static", beats=[{"word": f"w{2 * i}", "do": "x", "kind": "gesture"},
                                                                       {"word": f"w{2 * i + 1}", "do": "y", "kind": "gesture"}]) for i in range(4)]}
    assert any("same size + move" in x for x in plan_problems(p, tm, 8.0))


def test_bad_transition_and_move():
    p = copy.deepcopy(PLAN); p["shots"][1]["transition_in"] = {"kind": "spin", "frames": 3}; p["shots"][0]["camera"]["move"] = "barrel_roll"
    probs = plan_problems(p, TIMINGS, 6.0)
    assert any("transition" in x for x in probs) and any("camera move" in x for x in probs)

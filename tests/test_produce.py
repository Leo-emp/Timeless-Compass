# Tests for `tc produce`: the mechanical back half runs in order, skips what is current, stops at the first failure.
import os
import time

import pytest

from tc import produce


def touch(p, age=0):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x", encoding="utf-8")
    t = time.time() - age
    os.utime(p, (t, t))


@pytest.fixture
def job(tmp_path):
    d, film = tmp_path / "job", tmp_path / "film"
    touch(d / "script.md", age=500)
    return d, film


def test_everything_needed_on_a_fresh_job(job):
    d, film = job
    assert produce.plan_steps(d, film) == produce.STEPS


def test_produce_skips_current_steps(job):
    d, film = job
    for f, age in (("dialogue.json", 400), ("voice.wav", 300), ("voice.json", 300), ("timings.json", 200)):
        touch(d / f, age)
    touch(d / "qa" / "length.ok", 180)
    touch(film / "lipsync.json", 150)
    steps = produce.plan_steps(d, film)
    assert steps[0] == "shotplan" and "voice" not in steps


def test_an_edited_input_redoes_its_step_and_everything_after(job):
    d, film = job
    for f, age in (("dialogue.json", 400), ("voice.wav", 300), ("voice.json", 300), ("timings.json", 200)):
        touch(d / f, age)
    touch(d / "script.md", 0)                    # script edited after the voice was made
    assert produce.plan_steps(d, film)[0] == "dialogue"


def test_produce_stops_at_first_failure(job):
    d, film = job
    calls = []
    def run(step):
        calls.append(step)
        return 1 if step == "voice" else 0
    code = produce.run_steps(["dialogue", "voice", "align"], run)
    assert code == 1 and calls == ["dialogue", "voice"]


def test_short_length_capped():
    assert produce.length_problem("short", 181.0)
    assert produce.length_problem("short", 175.0) is None
    assert produce.length_problem("long", 181.0) is None


# ---- plan 5 final-review fixes -------------------------------------------------------------------------------
def test_length_gate_is_a_step_that_reruns_until_it_passes(job, tmp_path):
    d, film = job
    for f, age in (("dialogue.json", 400), ("voice.wav", 300), ("voice.json", 300), ("timings.json", 200)):
        touch(d / f, age)
    assert produce.plan_steps(d, film)[0] == "length"            # no pass marker yet -> the gate runs
    assert produce.length_step(d, "short", lambda p: 190.0) == 1
    assert not (d / "qa" / "length.ok").exists()                 # a failed gate leaves no marker -> runs again next time
    assert produce.length_step(d, "short", lambda p: 121.0) == 0
    assert (d / "qa" / "length.ok").exists()


def test_pick_new_run_ignores_older_and_other_commits():
    runs = [{"databaseId": 9, "headSha": "abc"}, {"databaseId": 8, "headSha": "abc"}, {"databaseId": 7, "headSha": "zzz"}]
    assert produce.pick_new_run(runs, before_id=9, sha="abc") is None      # only the old run exists yet
    runs.insert(0, {"databaseId": 11, "headSha": "other"})
    assert produce.pick_new_run(runs, before_id=9, sha="abc") is None      # another session's run
    runs.insert(0, {"databaseId": 12, "headSha": "abc"})
    assert produce.pick_new_run(runs, before_id=9, sha="abc") == 12


def test_spoken_hash_ignores_markers_but_not_words():
    a = 'He was surrounded. {beat} [src: f-dismiss]\nXERXES: "Lay down your weapons." [dramatised]\n'
    assert produce.spoken_hash(a) == produce.spoken_hash(a.replace("{beat}", "{beat} {loop}"))
    assert produce.spoken_hash(a) != produce.spoken_hash(a.replace("surrounded", "trapped"))


def test_marker_only_edit_does_not_revoice(job):
    d, film = job
    for f, age in (("dialogue.json", 400), ("voice.wav", 300), ("voice.json", 300), ("timings.json", 200)):
        touch(d / f, age)
    (d / "script.md").write_text("He was surrounded.\n", encoding="utf-8")
    produce.save_spoken(d)
    (d / "script.md").write_text("He was surrounded. {loop}\n", encoding="utf-8")   # newer, same spoken words
    assert "voice" not in produce.plan_steps(d, film) and "dialogue" not in produce.plan_steps(d, film)
    (d / "script.md").write_text("He was trapped.\n", encoding="utf-8")
    assert produce.plan_steps(d, film)[0] == "dialogue"


def test_render_preflight_refuses_unsafe_git_states():
    def git(answers):
        return lambda *args: answers.get(args[0], (0, ""))
    ok = {"pushed": (0, ""), "dirty": (0, ""), "untracked": (0, ""), "remote_diff": (0, "")}
    assert produce.render_preflight(git(ok)) is None
    assert "origin/master is not this commit" in produce.render_preflight(git({**ok, "pushed": (1, "")}))
    assert "not committed" in produce.render_preflight(git({**ok, "dirty": (1, "")}))
    assert "not committed" in produce.render_preflight(git({**ok, "untracked": (0, "film/src/jobs/x/scenes.ts")}))
    assert "origin/master" in produce.render_preflight(git({**ok, "remote_diff": (1, "")}))


def test_motion_step_blocks_on_a_crash():
    assert produce.motion_ok(0, "motion: 3 problem(s)\n") is True
    assert produce.motion_ok(1, "problem: snap at frame 4\nmotion: 1 problem(s)\n") is True    # problems = report, not crash
    assert produce.motion_ok(1, "") is False
    assert produce.motion_ok(2, "Traceback ...") is False


def test_spoken_hash_keeps_what_changes_the_audio():
    a = "## build\nHe was surrounded. [src: f-1]\nThey ran.\n"
    assert produce.spoken_hash(a) != produce.spoken_hash(a.replace("surrounded.", "surrounded. {beat}"))   # a pause is heard
    assert produce.spoken_hash(a) != produce.spoken_hash(a.replace("They ran.", "## payoff\nThey ran."))  # new SSML block

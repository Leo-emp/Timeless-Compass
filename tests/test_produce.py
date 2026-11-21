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

# Tests for `tc next`: tells the agent what to do next on a job, with the owner rules for that stage.
import pytest

from tc import jobs, learning, paths
from tc.run import next_action


@pytest.fixture(autouse=True)
def tmp_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "JOBS", tmp_path / "jobs")
    monkeypatch.setattr(paths, "TASTE", tmp_path / "taste")


def test_next_action_for_fresh_job_is_topic():
    job = jobs.create_job("x")
    a = next_action(job)
    assert a["stage"] == "topic" and "tc topics" in a["command"] and job.id in a["command"]


def test_next_action_includes_stage_rules():
    learning.add_rule("hooks must be short", applies_to=["script"])
    learning.add_rule("about voices", applies_to=["voice"])
    job = jobs.create_job("x")
    for s in ("topic", "packaging", "research"):
        jobs.mark(job, s, "done")
    a = next_action(job)
    assert a["stage"] == "script" and a["rules"] == ["r1"]


def test_done_job_says_finished_plan1():
    job = jobs.create_job("x")
    for s in jobs.STAGES:
        jobs.mark(job, s, "done")
    a = next_action(job)
    assert a["stage"] is None and "Plan 2" in a["do"]

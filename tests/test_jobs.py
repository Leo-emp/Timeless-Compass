# Tests for jobs: one folder per video with a resumable stage ledger (job.json).
from datetime import datetime

import pytest

from tc import jobs, paths


@pytest.fixture(autouse=True)
def tmp_jobs(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "JOBS", tmp_path / "jobs")


def test_create_job_id_format():
    job = jobs.create_job("The Trap at Salamis!", now=datetime(2026, 11, 19, 3, 10))
    assert job.id == "20261119-0310-the-trap-at-salamis"
    assert job.kind == "long"
    assert set(job.stages) == set(jobs.STAGES)


def test_save_load_roundtrip():
    job = jobs.create_job("x", now=datetime(2026, 1, 1, 0, 0))
    jobs.mark(job, "topic", "done", "picked")
    jobs.save_job(job)
    back = jobs.load_job(job.id)
    assert back.stages["topic"]["status"] == "done"
    assert back.stages["topic"]["note"] == "picked"


def test_next_stage_after_failed_stage():
    job = jobs.create_job("x")
    jobs.mark(job, "topic", "done")
    jobs.mark(job, "packaging", "failed", "api down")
    assert jobs.next_stage(job) == "packaging"


def test_all_done_returns_none():
    job = jobs.create_job("x")
    for s in jobs.STAGES:
        jobs.mark(job, s, "done")
    assert jobs.next_stage(job) is None


def test_mark_rejects_unknown_stage():
    job = jobs.create_job("x")
    with pytest.raises(ValueError):
        jobs.mark(job, "nonsense", "done")


def test_mark_command_marks_stage(capsys):
    from tc import cli
    job = jobs.create_job("x"); jobs.save_job(job)
    assert cli.main(["mark", job.id, "research", "--note", "12 sources"]) == 0
    assert jobs.load_job(job.id).stages["research"] == {**jobs.load_job(job.id).stages["research"], "status": "done", "note": "12 sources"}

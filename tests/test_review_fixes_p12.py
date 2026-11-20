# Regression tests for the plan 1+2 final review findings (2026-11-21). Each one failed before its fix.
import json

import pytest

from tc import jobs, paths, qa


# Important 1: the default branch for cloud renders must exist (the repo has master, not main)
def test_film_render_default_ref_is_master():
    import argparse
    from tc import film
    p = argparse.ArgumentParser(); film._args(p)
    assert p.parse_args(["render", "X", "--frames", "10"]).ref == "master"


# Important 2: a join must refuse a video whose LAST part is missing
def test_join_refuses_missing_last_part(tmp_path):
    from tc.film import join_parts
    for n in ("part-0-9.mp4", "part-10-19.mp4"):
        (tmp_path / n).write_bytes(b"x")
    with pytest.raises(ValueError, match="last part ends at frame 19"):
        join_parts(tmp_path, tmp_path / "o.mp4", runner=lambda *a, **k: None, total=30)


# Important 3: voice is gated by a viewer GO on the CURRENT script, not by an owner approval
@pytest.fixture
def job(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "JOBS", tmp_path / "jobs")
    j = jobs.create_job("x"); jobs.save_job(j)
    (jobs.job_dir(j.id) / "script.md").write_text("## hook\nA line.\n", encoding="utf-8")
    return j


def test_viewer_go_on_current_script_allows_voice(job):
    from tc.script import is_approved
    from tc.viewer import save_verdict
    d = jobs.job_dir(job.id)
    assert not is_approved(d)
    save_verdict(d, {"verdict": "GO", "dropoffs": [], "felt": [], "would_finish": True, "would_subscribe": True, "notes": ""})
    assert is_approved(d)
    (d / "script.md").write_text("## hook\nA changed line.\n", encoding="utf-8")
    assert not is_approved(d)                               # edited after the GO -> needs a new fresh viewer


# Important 4: hands, other faces and foreground scenery drawn on top also cover faces
@pytest.mark.parametrize("role", ["hand", "face", "fg"])
def test_more_things_can_cover_a_face(role):
    from tc.stillcheck import geometry_problems
    face = {"role": "face", "box": [500, 300, 120, 130], "order": 1, "id": None, "holds": None}
    top = {"role": role, "box": [480, 280, 160, 170], "order": 2, "id": None, "holds": None}
    assert any("covers face" in p for p in geometry_problems([face, top], 1920, 1080))


# Important 5: the grip test uses the real shaft (inspector 'grip'), not the prop's bounding box
def test_grip_false_from_inspector_is_a_problem():
    from tc.stillcheck import geometry_problems
    e = [{"role": "prop", "box": [0, 0, 500, 500], "order": 0, "id": "spear", "holds": None},
         {"role": "hand", "box": [440, 40, 30, 30], "order": 1, "id": None, "holds": "spear", "grip": False}]
    assert any("does not touch" in p for p in geometry_problems(e, 1920, 1080))


# Important 6: a self-check only counts for the exact content it scored
def test_stale_self_check_does_not_pass(tmp_path):
    answers = {i: {"pass": True, "score": w, "note": ""} for i, w in qa.CHECKLISTS["story"].items()}
    qa.record(tmp_path, "story", answers, content_hash="aaa")
    assert qa.passed(tmp_path, "story", content_hash="aaa")
    assert not qa.passed(tmp_path, "story", content_hash="bbb")

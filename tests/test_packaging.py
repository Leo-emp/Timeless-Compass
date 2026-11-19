# Tests for the title + thumbnail packaging check (CTR lever).
import pytest

from tc import jobs, packaging, paths


def test_too_long_title():
    r = packaging.check_titles(["x" * 61])[0]
    assert not r["ok"] and "too long" in r["problems"] and r["length"] == 61


def test_banned_word():
    r = packaging.check_titles(["The SHOCKING secret of Salamis"])[0]
    assert "banned word: shocking" in r["problems"]


def test_all_caps():
    assert "all caps" in packaging.check_titles(["THE TRAP THAT SAVED GREECE"])[0]["problems"]


def test_good_title_ok():
    r = packaging.check_titles(["The Trap That Saved Greece"])[0]
    assert r["ok"] and r["problems"] == []


def test_no_curiosity_hook():
    assert "no curiosity hook" in packaging.check_titles(["Greece and Persia"])[0]["problems"]


def test_pick_must_be_ok_title(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "JOBS", tmp_path / "jobs")
    job = jobs.create_job("x"); jobs.save_job(job)
    with pytest.raises(ValueError):
        packaging.save_packaging(job, ["Greece and Persia", "The Trap That Saved Greece"], ["thumb"], pick=1)
    packaging.save_packaging(job, ["Greece and Persia", "The Trap That Saved Greece"], ["thumb"], pick=2)
    assert job.stages["packaging"]["status"] == "done"


# ---------------- description (rule r12: dramatised dialogue is disclosed) ----------------
DRAMA = '## hook\nAt dawn. [src: h]\n## build\nXERXES: "Burn it." [dramatised]\n## payoff\nThe end. [src: h]\n'
PLAIN = '## hook\nAt dawn. [src: h]\n## build\nLEONIDAS: "Come and take them." [source: Plutarch]\n## payoff\nThe end. [src: h]\n'


def test_description_adds_dramatised_line():
    d = packaging.build_description("The night Athens burned.", DRAMA)
    assert d.endswith("Some dialogue is dramatised.")
    assert d.startswith("The night Athens burned.")


def test_description_without_dramatised_line_is_unchanged():
    assert packaging.build_description("The night Athens burned.", PLAIN) == "The night Athens burned."


def test_description_line_never_doubled():
    once = packaging.build_description("Intro.\n\nSome dialogue is dramatised.", DRAMA)
    assert once.count("Some dialogue is dramatised.") == 1


def test_write_description_file(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "JOBS", tmp_path / "jobs")
    job = jobs.create_job("x", "short"); jobs.save_job(job)
    d = jobs.job_dir(job.id)
    (d / "script.md").write_text(DRAMA, encoding="utf-8")
    out = packaging.write_description(job, "One night in 480 BC.")
    assert out == d / "description.txt"
    assert "Some dialogue is dramatised." in out.read_text(encoding="utf-8")

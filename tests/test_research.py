# Tests for the research stage: a sourced fact sheet per job (ancient authors + modern historians).
import json

import pytest

from tc import jobs, paths, research
from tc.config import Config
from tc.script import check_script, parse_script

WORLD = {
    "world": "test_world",
    "sources": {
        "herodotus": {"author": "Herodotus", "work": "Histories", "kind": "ancient", "date": "c. 430 BC"},
        "strauss": {"author": "Barry Strauss", "work": "The Battle of Salamis", "kind": "modern", "date": "2004"},
    },
    "facts": [
        {"id": "f-sicinnus", "claim": "Themistocles sent his slave Sicinnus to the Persians.",
         "cites": ["herodotus:8.75", "strauss"], "topics": ["secret_message"]},
        {"id": "f-throne", "claim": "Xerxes watched the battle from the foot of Mount Aigaleos.",
         "cites": ["herodotus:8.90"], "topics": ["throne"]},
    ],
}


def test_good_sheet_has_no_problems():
    assert research.check_sheet(WORLD) == []


def test_fact_without_cites():
    bad = json.loads(json.dumps(WORLD)); bad["facts"][0]["cites"] = []
    assert any("f-sicinnus" in p and "no source" in p for p in research.check_sheet(bad))


def test_unknown_source_in_cite():
    bad = json.loads(json.dumps(WORLD)); bad["facts"][1]["cites"] = ["plutarch:13"]
    assert any("unknown source 'plutarch'" in p for p in research.check_sheet(bad))


def test_duplicate_fact_ids():
    bad = json.loads(json.dumps(WORLD)); bad["facts"][1]["id"] = "f-sicinnus"
    assert any("duplicate" in p for p in research.check_sheet(bad))


def test_disputed_fact_needs_a_note():
    bad = json.loads(json.dumps(WORLD)); bad["facts"][0]["status"] = "disputed"
    assert any("disputed" in p for p in research.check_sheet(bad))


def test_sheet_needs_ancient_and_modern_sources():
    bad = json.loads(json.dumps(WORLD)); del bad["sources"]["strauss"]; bad["facts"][0]["cites"] = ["herodotus:8.75"]
    assert any("modern" in p for p in research.check_sheet(bad))


def test_select_facts_by_topic():
    assert [f["id"] for f in research.select_facts(WORLD, ["throne"])] == ["f-throne"]
    assert len(research.select_facts(WORLD, None)) == 2          # no topics = every fact


def test_cite_label_is_readable():
    assert research.cite_label("herodotus:8.75", WORLD["sources"]) == "Herodotus, Histories 8.75"
    assert research.cite_label("strauss", WORLD["sources"]) == "Barry Strauss, The Battle of Salamis (2004)"


def test_write_job_sheet_makes_facts_citable_by_the_script(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "JOBS", tmp_path / "jobs")
    job = jobs.create_job("secret message", "short"); jobs.save_job(job)
    d = jobs.job_dir(job.id)
    (d / "sources.json").write_text(json.dumps({"hand-added": {"title": "x"}}), encoding="utf-8")
    research.write_job_sheet(job, WORLD, ["secret_message"])
    sheet = json.loads((d / "research.json").read_text(encoding="utf-8"))
    assert [f["id"] for f in sheet["facts"]] == ["f-sicinnus"]
    assert set(sheet["sources"]) == {"herodotus", "strauss"}        # only the sources these facts use
    assert "Herodotus, Histories 8.75" in (d / "facts.md").read_text(encoding="utf-8")
    src = json.loads((d / "sources.json").read_text(encoding="utf-8"))
    assert "hand-added" in src and "f-sicinnus" in src               # merged, nothing hand-written lost
    assert job.stages["research"]["status"] == "done"
    # the script checker now accepts [src: f-sicinnus]
    line = " ".join(["w"] * 19) + ". [src: f-sicinnus]"
    script = "\n".join(["## hook", line, "## build", line, line, line, "## payoff", line, line])
    assert check_script(parse_script(script), "short", src, Config()) == []


def test_write_job_sheet_refuses_a_bad_world(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "JOBS", tmp_path / "jobs")
    job = jobs.create_job("x", "short"); jobs.save_job(job)
    bad = json.loads(json.dumps(WORLD)); bad["facts"][0]["cites"] = []
    with pytest.raises(research.ResearchError):
        research.write_job_sheet(job, bad, None)


def test_unknown_topic_is_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "JOBS", tmp_path / "jobs")
    job = jobs.create_job("x", "short"); jobs.save_job(job)
    with pytest.raises(research.ResearchError):
        research.write_job_sheet(job, WORLD, ["nope"])


def test_salamis_world_library_file_is_clean():
    # the real fact sheet shipped in library/research/ must pass its own checks
    world = research.load_world("salamis_480bc")
    assert research.check_sheet(world) == []
    for topic in ["secret_message", "throne", "rams", "athens_burns", "oracle"]:
        assert research.select_facts(world, [topic]), topic

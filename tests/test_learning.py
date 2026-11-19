# Tests for owner rules (the first part of the learning system).
import json

import pytest

from tc import learning, paths


@pytest.fixture(autouse=True)
def tmp_taste(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "TASTE", tmp_path / "taste")


def test_rule_ids_increment():
    assert learning.add_rule("first")["id"] == "r1"
    assert learning.add_rule("second")["id"] == "r2"


def test_rules_md_contains_rule_and_why():
    learning.add_rule("Helmets must look worn", why="shiny looks fake", applies_to=["shots"])
    md = (paths.TASTE / "rules.md").read_text(encoding="utf-8")
    assert "Helmets must look worn" in md and "shiny looks fake" in md and "r1" in md
    data = json.loads((paths.TASTE / "learning.json").read_text(encoding="utf-8"))
    assert data["rules"][0]["applies_to"] == ["shots"]


def test_filter_by_stage():
    learning.add_rule("script rule", applies_to=["script"])
    learning.add_rule("global rule")
    assert [r["text"] for r in learning.list_rules("script")] == ["script rule", "global rule"]
    assert [r["text"] for r in learning.list_rules("voice")] == ["global rule"]


def test_unknown_stage_rejected():
    with pytest.raises(ValueError):
        learning.add_rule("x", applies_to=["nonsense"])

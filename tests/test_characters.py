# Tests for the character registry (`tc characters`, rule r19): one locked identity per named character.
import copy
import json

import pytest

from tc import characters, paths

VOICES = {"characters": {"xerxes": {"provider": "fish", "reference_id": "abc"}}}
SHEET = {"id": "xerxes", "name": "Xerxes", "aliases": ["king xerxes"], "who": "Xerxes I, King of Kings", "kind": "real",
         "era": "persia_480bc", "design_source": "Persepolis reliefs", "voice": "xerxes",
         "look": {"skin": "#d9a77c", "hair": {"style": "nape_bun", "colour": "#1c1612"},
                  "beard": {"style": "squared_curls", "colour": "#1c1612"},
                  "build": {"height": 1.05, "width": 1.0}, "headgear": "crenellated crown",
                  "parts": {"robe": "#5b2a6e", "trim": "#d9b443", "crown": "#e2b23f"}},
         "signature": ["squared curled beard", "crenellated crown"], "version": 1}


@pytest.fixture(autouse=True)
def tmp_lib(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "LIBRARY", tmp_path / "library")
    d = tmp_path / "library" / "characters" / "xerxes"; d.mkdir(parents=True)
    (d / "sheet.json").write_text(json.dumps(SHEET), encoding="utf-8")


def test_valid_sheet():
    assert characters.sheet_problems(SHEET, VOICES) == []


def test_sheet_with_unknown_voice():
    s = dict(SHEET, voice="nobody")
    assert any("voice" in p for p in characters.sheet_problems(s, VOICES))


def test_unknown_part():
    s = copy.deepcopy(SHEET); s["look"]["parts"]["jetpack"] = "#000000"
    assert any("jetpack" in p for p in characters.sheet_problems(s, VOICES))


def test_bad_colour():
    s = copy.deepcopy(SHEET); s["look"]["skin"] = "tan"
    assert any("colour" in p for p in characters.sheet_problems(s, VOICES))


def test_build_out_of_range():
    s = copy.deepcopy(SHEET); s["look"]["build"]["height"] = 2.0
    assert any("build" in p for p in characters.sheet_problems(s, VOICES))


def test_real_person_needs_design_source():
    s = dict(SHEET, design_source="")
    assert any("design_source" in p for p in characters.sheet_problems(s, VOICES))


def test_resolve_by_alias_and_id():
    assert characters.resolve("KING XERXES") == "xerxes" and characters.resolve("Xerxes") == "xerxes"
    assert characters.resolve("NOBODY") is None


def test_registry_lists_ids():
    assert characters.all_ids() == ["xerxes"] and characters.load_sheet("xerxes")["name"] == "Xerxes"

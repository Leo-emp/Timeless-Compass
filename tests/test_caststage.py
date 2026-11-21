# Tests for the cast stage (`tc cast <job>`): every character a video needs exists, passes, and has its own voice.
import json

import pytest

from tc import paths
from tc.caststage import cast_problems

VOICES = {"characters": {"xerxes": {"provider": "fish", "reference_id": "aaa"},
                         "messenger": {"provider": "fish", "reference_id": "bbb"},
                         "copycat": {"provider": "fish", "reference_id": "aaa"}}}


def sheet(cid, voice):
    return {"id": cid, "name": cid.title(), "aliases": [], "who": "x", "kind": "composite", "era": "e", "design_source": "",
            "voice": voice, "look": {"skin": "#aaaaaa", "hair": {"style": "s", "colour": "#111111"}, "beard": None,
                                     "build": {"height": 1, "width": 1}, "headgear": "", "parts": {}}, "signature": ["x"], "version": 1}


@pytest.fixture(autouse=True)
def lib(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "LIBRARY", tmp_path / "library")
    for cid, voice in (("xerxes", "xerxes"), ("mardonius", "copycat")):
        d = tmp_path / "library" / "characters" / cid; d.mkdir(parents=True)
        (d / "sheet.json").write_text(json.dumps(sheet(cid, voice)), encoding="utf-8")


def test_clean_cast():
    assert cast_problems({"characters": ["xerxes"], "extras": ["messenger"]}, VOICES, speakers=["XERXES", "MESSENGER"]) == []


def test_cast_rejects_shared_voice():
    probs = cast_problems({"characters": ["xerxes", "mardonius"], "extras": []}, VOICES, speakers=[])
    assert any("share a voice" in p for p in probs)


def test_unregistered_character():
    assert any("not registered" in p for p in cast_problems({"characters": ["leonidas"], "extras": []}, VOICES, speakers=[]))


def test_speaker_missing_from_cast():
    probs = cast_problems({"characters": ["xerxes"], "extras": []}, VOICES, speakers=["ARTEMISIA"])
    assert any("ARTEMISIA" in p for p in probs)

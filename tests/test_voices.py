# Tests for character voices: registry lookup, unique reference ids, Fish voice search (r19, r26).
import json

import pytest

from tc import characters, paths, voices
from tc.dialogue import voice_for

VOICES = {"characters": {"xerxes": {"provider": "fish", "reference_id": "aaa"},
                         "themistocles": {"provider": "fish", "reference_id": "bbb"}}}


@pytest.fixture(autouse=True)
def tmp_lib(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "LIBRARY", tmp_path / "library")
    d = tmp_path / "library" / "characters" / "themistocles"; d.mkdir(parents=True)
    (d / "sheet.json").write_text(json.dumps({"id": "themistocles", "name": "Themistocles", "aliases": ["themistokles"],
                                              "voice": "themistocles", "look": {}}), encoding="utf-8")
    (tmp_path / "library" / "voices.json").write_text(json.dumps(VOICES), encoding="utf-8")


def test_alias_resolves_voice():
    key, v = voice_for("THEMISTOKLES", None, VOICES)
    assert key == "themistocles" and v["reference_id"] == "bbb"


def test_voices_add_refuses_duplicate_reference():
    with pytest.raises(ValueError, match="already used by xerxes"):
        voices.add_voice("leonidas", "aaa", "deep king")


def test_voices_add_writes_entry():
    voices.add_voice("leonidas", "ccc", "deep weathered commander")
    data = json.loads((paths.LIBRARY / "voices.json").read_text(encoding="utf-8"))
    assert data["characters"]["leonidas"] == {"provider": "fish", "reference_id": "ccc", "use": "deep weathered commander"}


def test_search_keeps_key_in_header():
    seen = {}
    def fake(url, headers=None, timeout=60):
        seen["url"], seen["headers"] = url, headers
        return {"items": [{"_id": "x1", "title": "Deep Narrator", "tags": ["male"], "languages": ["en"]}]}
    out = voices.fish_search("deep male", "SECRET", get=fake)
    assert "SECRET" not in seen["url"] and seen["headers"]["Authorization"] == "Bearer SECRET"
    assert out == [{"id": "x1", "title": "Deep Narrator", "tags": ["male"], "languages": ["en"]}]

# Regression tests for the plan 3 final review (2026-11-21). Each failed before its fix.
import json

import pytest

from tc import characters, paths
from tc.charcheck import character_problems
from tc.caststage import cast_problems

SHEET = {"look": {"skin": "#dcae84", "hair": {"colour": "#2a1d14"}, "beard": None,
                  "parts": {"robe": "#5b2a6e", "trim": "#d9b443"}, "accents": ["#8a6427"]}}


# I1: the check must read the colours ACTUALLY drawn inside a tagged part, not only the colour it claims
def test_drawn_colour_not_on_sheet_is_caught():
    e = {"char": "xerxes", "part": "robe", "fill": "#5b2a6e", "fills": ["#5b2a6f"], "box": [0, 0, 1, 1], "order": 0}
    assert any("#5b2a6f" in p for p in character_problems([e], {"xerxes": SHEET}))


def test_accent_and_outline_colours_are_allowed():
    e = {"char": "xerxes", "part": "robe", "fill": "#5b2a6e", "fills": ["#5b2a6e", "#8a6427", "#2a1c13"], "box": [0, 0, 1, 1], "order": 0}
    assert character_problems([e], {"xerxes": SHEET}) == []


def test_claimed_colour_must_really_be_drawn():
    e = {"char": "xerxes", "part": "robe", "fill": "#5b2a6e", "fills": ["#d9b443"], "box": [0, 0, 1, 1], "order": 0}
    assert any("not drawn" in p for p in character_problems([e], {"xerxes": SHEET}))


# I2: voices set on a script line / job mapping, and extras, can't be shared either
def test_speakers_sharing_a_voice_through_line_keys():
    voices = {"characters": {"messenger": {"provider": "fish", "reference_id": "m"}}}
    probs = cast_problems({"characters": [], "extras": ["messenger"]}, voices, speakers=["MESSENGER", "LEONIDAS"],
                          speaker_voices={"MESSENGER": "messenger", "LEONIDAS": "messenger"})
    assert any("share a voice" in p for p in probs)


# I3: an alias may belong to only one character
def test_duplicate_alias_across_sheets(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "LIBRARY", tmp_path / "library")
    for cid, alias in (("xerxes", "the great king"), ("darius", "The Great King")):
        d = tmp_path / "library" / "characters" / cid; d.mkdir(parents=True)
        (d / "sheet.json").write_text(json.dumps({"id": cid, "name": cid.title(), "aliases": [alias], "look": {}}), encoding="utf-8")
    assert any("the great king" in p for p in characters.registry_problems())

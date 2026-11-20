# Tests for the character check (`tc still --chars`, rule r19): every tagged part uses its sheet colour.
from tc.charcheck import character_problems

SHEETS = {"leonidas": {"look": {"skin": "#dcae84", "hair": {"colour": "#2a1d14"}, "beard": {"colour": "#2a1d14"},
                                "parts": {"cloak": "#9b2b22", "crest": "#b23a2a"}}}}


def el(char, part, fill):
    return {"role": None, "char": char, "part": part, "fill": fill, "box": [0, 0, 1, 1], "order": 0}


def test_matching_colours_pass():
    assert character_problems([el("leonidas", "beard", "#2A1D14"), el("leonidas", "cloak", "#9b2b22")], SHEETS) == []


def test_wrong_part_colour_is_caught():
    probs = character_problems([el("leonidas", "beard", "#2a1d15")], SHEETS)
    assert probs == ["leonidas beard is #2a1d15, sheet says #2a1d14"]


def test_unknown_character():
    assert any("not in the registry" in p for p in character_problems([el("nobody", "skin", "#000000")], SHEETS))


def test_unknown_part():
    assert any("no colour for part" in p for p in character_problems([el("leonidas", "crown", "#e2b23f")], SHEETS))

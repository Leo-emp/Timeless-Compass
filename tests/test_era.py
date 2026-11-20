# Tests for the era lock (`tc era`, rules r4 + r32): every visual item sourced; every shot uses only sheet items.
from tc.era import era_problems, shots_era_problems

SHEET = {"era": "Classical Greece", "place": "Salamis", "years": "480 BC",
         "items": [{"id": "trireme", "kind": "ship", "name": "Athenian trireme", "source": "Olympias reconstruction; Morrison 1986", "notes": ""},
                   {"id": "aspis", "kind": "armour", "name": "hoplite shield", "source": "British Museum 1856,1226.1", "notes": ""}],
         "dont": ["no stirrups", "no Roman lorica", "no Gothic arches"]}


def test_valid_sheet():
    assert era_problems(SHEET) == []


def test_item_without_source():
    bad = {**SHEET, "items": SHEET["items"] + [{"id": "lamp", "kind": "object", "name": "oil lamp", "source": "", "notes": ""}]}
    assert any("lamp" in p and "source" in p for p in era_problems(bad))


def test_unknown_kind():
    bad = {**SHEET, "items": [{**SHEET["items"][0], "kind": "spaceship"}]}
    assert any("kind" in p for p in era_problems(bad))


def test_needs_three_donts():
    assert any("don't" in p for p in era_problems({**SHEET, "dont": ["no stirrups"]}))


def test_shot_citing_unknown_item():
    shots = [{"id": "s1", "era_items": ["trireme", "catapult"]}, {"id": "s2"}]
    probs = shots_era_problems(shots, SHEET)
    assert any("s1" in p and "catapult" in p for p in probs) and any("s2" in p for p in probs)

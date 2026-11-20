# Tests for the story page check (`tc story`): the story is designed before any script line (rules r24, r33).
from pathlib import Path

from tc.story import STORY_SHAPES, story_problems

GOOD = (Path(__file__).parent / "fixtures" / "story_salamis.md").read_text(encoding="utf-8")


def test_worked_example_passes():
    assert story_problems(GOOD, "long") == []


def test_missing_section():
    bad = GOOD.replace("## Fear\n", "## Worry\n")
    assert "missing section: Fear" in story_problems(bad, "long")


def test_unknown_shape():
    bad = GOOD.replace("\nheist\n", "\nadventure\n")
    assert any("story shape must be one of" in p for p in story_problems(bad, "long"))


def test_long_needs_midpoint():
    bad = "\n".join(l for l in GOOD.split("\n") if not l.startswith("- midpoint:"))
    assert "beat sheet missing: midpoint" in story_problems(bad, "long")


def test_short_beats_are_different():
    short = GOOD.split("## Beat sheet")[0] + "## Beat sheet\n- hook: x\n- build: y\n- twist: z\n- ending: w\n\n## Loops" + GOOD.split("## Loops")[1]
    assert story_problems(short, "short") == []
    assert "beat sheet missing: midpoint" in story_problems(short, "long")


def test_loop_without_payoff():
    bad = GOOD.replace("-> payoff: midpoint reveal", "")
    assert "loop without payoff: what was in the secret message?" in story_problems(bad, "long")


def test_music_must_include_opening_and_ending():
    bad = GOOD.replace("Music: opening, the message sent, the rams strike, ending", "Music: the rams strike")
    assert "music plan must include opening and ending" in story_problems(bad, "long")


def test_empty_section_is_a_problem():
    bad = GOOD.replace("Fight the Persian fleet inside the narrow strait, where numbers stop mattering.", "")
    assert "section is empty: Want" in story_problems(bad, "long")


def test_shapes_cover_the_bible():
    assert {"mystery", "heist", "countdown", "rise_and_fall"} <= STORY_SHAPES

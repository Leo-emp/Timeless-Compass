# Tests for matching heard words (whisper) back to script lines.
from tc.align import align_lines
from tc.script import parse_script


def heard(words, start=0.0, step=0.5):
    return [{"w": w, "s": round(start + i * step, 2), "e": round(start + i * step + 0.4, 2)} for i, w in enumerate(words)]


def test_align_exact_words():
    lines = parse_script("## world\nThe king sat.\nThe fleet sank.\n")
    res = align_lines(lines, heard(["The", "king", "sat.", "The", "fleet", "sank."]))
    assert res[0]["start"] == 0.0 and res[0]["end"] == 1.4
    assert res[1]["start"] == 1.5 and res[1]["end"] == 2.9
    assert res[0]["matched_ratio"] == 1.0


def test_align_tolerates_misheard_names():
    lines = parse_script("## world\nThemistocles sent a servant.\n")
    res = align_lines(lines, heard(["the", "mistocles", "sent", "a", "servant"]))
    assert res[0]["start"] is not None and res[0]["end"] is not None
    assert res[0]["matched_ratio"] >= 0.6


def test_unmatched_line_interpolated():
    lines = parse_script("## world\nOne two three.\nZebra quartz.\nFour five six.\n")
    res = align_lines(lines, heard(["one", "two", "three", "four", "five", "six"]))
    assert res[1]["start"] == res[0]["end"]
    assert res[1]["end"] == res[2]["start"]
    assert res[1]["matched_ratio"] == 0.0


def test_lines_monotonic():
    lines = parse_script("## world\nA b c.\nD e f.\nG h i.\n")
    res = align_lines(lines, heard(["a", "b", "c", "d", "e", "f", "g", "h", "i"]))
    starts = [r["start"] for r in res]
    assert starts == sorted(starts)

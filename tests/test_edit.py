import shutil
import subprocess
from pathlib import Path

import pytest

from tc import edit


def _shots():
    return [
        {"id": "s1", "at": 0.0, "dur": 4.0, "where": "salamis_dusk", "card": {"kind": "place_date", "text": "Salamis, September 480 BC"}},
        {"id": "s2", "at": 4.0, "dur": 3.0, "where": "salamis_dusk"},
        {"id": "s3", "at": 7.0, "dur": 5.0, "where": "athens_480bc"},
        {"id": "s4", "at": 12.0, "dur": 3.0, "where": "athens_480bc", "transition": "fade_black"},
    ]


def test_plan_follows_film_grammar_fade_in_cuts_dissolve_on_place_change():
    p = edit.plan(_shots(), have={"s1", "s2", "s3", "s4"})
    t = [s["trans"] for s in p["segments"]]
    assert t == ["fade_in", "cut", "dissolve", "fade_black"]
    assert p["segments"][-1]["fade_out"] > 0                  # the film ends on a fade to black


def test_plan_keeps_every_shot_on_its_spoken_line():
    p = edit.plan(_shots(), have={"s1", "s2", "s3", "s4"})
    assert [s["start"] for s in p["segments"]] == [0.0, 4.0, 7.0, 12.0]
    assert p["shots_end"] == pytest.approx(15.0)
    assert p["total"] == pytest.approx(15.0 + edit.END_CARD_S)


def test_missing_render_becomes_black_and_is_reported_not_a_crash():
    p = edit.plan(_shots(), have={"s1", "s3", "s4"})
    s2 = p["segments"][1]
    assert s2["src"] is None and any("s2" in w for w in p["warnings"])


def test_gap_between_shots_is_filled_by_holding_the_previous_shot():
    shots = _shots(); shots[1]["at"] = 4.5                    # 0.5 s hole after s1
    p = edit.plan(shots, have={"s1", "s2", "s3", "s4"})
    assert p["segments"][0]["dur"] == pytest.approx(4.5)
    assert any("gap" in w for w in p["warnings"])


def test_place_date_card_appears_after_the_shot_starts_and_fades_before_it_ends():
    p = edit.plan(_shots(), have={"s1", "s2", "s3", "s4"})
    (c,) = p["cards"]
    assert c["text"] == "Salamis, September 480 BC"
    assert 0.0 < c["start"] < c["end"] <= 4.0


def test_only_allowed_cards_rule_r3():
    shots = _shots(); shots[1]["card"] = {"kind": "caption", "text": "He is nervous"}
    p = edit.plan(shots, have={"s1", "s2", "s3", "s4"})
    assert len(p["cards"]) == 1 and any("caption" in w for w in p["warnings"])


def test_letterbox_bars_for_235_on_1080p_and_none_for_shorts():
    assert edit.letterbox_bar(1920, 1080, 2.35) == 131
    assert edit.letterbox_bar(1080, 1920, None) == 0


def test_filter_graph_has_dissolve_fades_cards_and_letterbox():
    p = edit.plan(_shots(), have={"s1", "s2", "s3", "s4"})
    g = edit.build_graph(p, size=(1920, 1080), fps=24, card_files=["c0.txt"], font="font.ttf", letterbox=2.35)
    for part in ("xfade=transition=fade", "fade=t=in", "fade=t=out", "drawtext=", "drawbox=", "concat="):
        assert part in g, part
    assert g.rstrip().endswith("[vout]")


def test_blackdetect_parsing_and_qa_ignore_the_planned_fades():
    err = ("[blackdetect @ 0x1] black_start:0 black_end:0.8 black_duration:0.8\n"
           "[blackdetect @ 0x1] black_start:8.2 black_end:9.4 black_duration:1.2\n")
    spans = edit.parse_blackdetect(err)
    assert spans == [(0.0, 0.8), (8.2, 9.4)]
    p = edit.plan(_shots(), have={"s1", "s2", "s3", "s4"})
    problems = edit.qa(p, spans, duration=p["total"], lufs=-12.1, kind="long")
    assert len(problems) == 1 and "8.2" in problems[0]         # the opening fade is fine; the hole at 8.2 s is not


def test_qa_flags_wrong_length_and_loudness():
    p = edit.plan(_shots(), have={"s1", "s2", "s3", "s4"})
    problems = edit.qa(p, [], duration=p["total"] - 2.0, lufs=-16.0, kind="long")
    assert any("length" in x for x in problems) and any("loud" in x for x in problems)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_render_a_real_tiny_master(tmp_path):
    """End to end with tiny generated clips: the master exists, has sound and the planned length."""
    have = {}
    for s, col in zip(_shots(), ("red", "green", "blue", "yellow")):
        f = tmp_path / f"{s['id']}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c={col}:s=320x180:r=24",
                        "-t", str(s["dur"]), "-pix_fmt", "yuv420p", str(f)], check=True)
        have[s["id"]] = f
    audio = tmp_path / "mix.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=f=220:d=15", str(audio)], check=True)
    out = tmp_path / "master.mp4"
    info = edit.render(_shots(), have, audio, out, size=(320, 180), letterbox=2.35, look=None)
    assert out.exists()
    assert info["duration"] == pytest.approx(15.0 + edit.END_CARD_S, abs=0.25)
    assert info["has_audio"]


def test_shot_matching_filter_goes_into_that_shots_chain_before_transitions():
    p = edit.plan(_shots(), have={"s1", "s2", "s3", "s4"})
    p["segments"][1]["match"] = "curves=all='0/0 0.3/0.4 1/1'"
    g = edit.build_graph(p, size=(320, 180), fps=24, letterbox=None)
    line = next(l for l in g.split(";\n") if l.startswith("[1:v]"))
    assert "curves=all='0/0 0.3/0.4 1/1'" in line and line.endswith("[v1]")

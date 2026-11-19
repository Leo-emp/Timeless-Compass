# Tests for narration: SSML building, Azure synthesis errors, mastering loudness.
import subprocess

import pytest

from tc import voice
from tc.config import Config
from tc.script import parse_script

WRAP = ('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US"><voice name="V"><prosody rate="-4%">')


def test_ssml_escapes_and_wraps():
    docs = voice.build_ssml(parse_script("## world\nA & B <tag>.\n"), "V", "-4%")
    assert docs[0].startswith(WRAP) and docs[0].endswith("</prosody></voice></speak>")
    assert "A &amp; B &lt;tag&gt;." in docs[0]


def test_beat_becomes_break():
    docs = voice.build_ssml(parse_script("## world\nSilence. {beat}\n"), "V", "-4%")
    assert '<break time="800ms"/>' in docs[0]


def test_one_doc_per_section():
    docs = voice.build_ssml(parse_script("## cold_open\nA.\n## world\nB.\nC.\n"), "V", "-4%")
    assert len(docs) == 2


def test_synth_raises_on_error_body(tmp_path):
    out = tmp_path / "s.wav"
    fake_post = lambda url, body, headers, timeout=180: (401, b'{"error": "bad key"}', "application/json")
    with pytest.raises(voice.VoiceError):
        voice.synthesize("<speak/>", out, Config(azure_key="k", azure_region="eastus"), post=fake_post)
    assert not out.exists()


def test_synth_writes_audio(tmp_path):
    out = tmp_path / "s.wav"
    fake_post = lambda url, body, headers, timeout=180: (200, b"RIFFdata", "audio/x-wav")
    voice.synthesize("<speak/>", out, Config(azure_key="k", azure_region="eastus"), post=fake_post)
    assert out.read_bytes() == b"RIFFdata"


def test_master_measures_loudness(tmp_path):
    raw = tmp_path / "raw.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=3",
                    "-af", "volume=-20dB", str(raw)], check=True)
    info = voice.master([raw], tmp_path / "voice.wav")
    assert -16 <= info["lufs"] <= -12
    assert info["peak_db"] <= -0.5
    assert 2.9 <= info["duration_s"] <= 3.2


# ---------- dialogue lines (NAME: "...") are spoken by Fish voices, not by the narrator ----------
def test_segments_cut_narration_around_dialogue():
    lines = parse_script('## climax\nA.\nXERXES: "Burn it."\nB.\n## aftermath\nC.\n')
    segs = voice.plan_segments(lines, "V", "-4%")
    assert [s["kind"] for s in segs] == ["ssml", "dialogue", "ssml", "ssml"]
    assert segs[1]["index"] == 1
    assert "Burn it" not in "".join(s.get("doc", "") for s in segs)    # the narrator never reads the line


def test_build_ssml_unchanged_without_dialogue():
    lines = parse_script("## cold_open\nA.\n## world\nB.\nC.\n")
    assert voice.build_ssml(lines, "V", "-4%") == [s["doc"] for s in voice.plan_segments(lines, "V", "-4%")]


def test_dialogue_offsets_sum_the_pieces_before_each_line():
    segs = [{"kind": "ssml"}, {"kind": "dialogue", "index": 3}, {"kind": "ssml"}, {"kind": "dialogue", "index": 7}]
    assert voice.dialogue_offsets(segs, [10.0, 2.5, 4.0, 1.0]) == {"3": 10.0, "7": 16.5}

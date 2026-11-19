# Tests for character dialogue: script lines  NAME: "..."  -> Fish Audio voice per character + usage log.
import json
import subprocess

import pytest

from tc import dialogue
from tc.script import parse_script

VOICES = {"characters": {
    "xerxes": {"provider": "fish", "reference_id": "ref-x", "voice_name": "X"},
    "messenger": {"provider": "fish", "reference_id": "ref-m", "voice_name": "M"},
    "narrator_like": {"provider": "azure", "voice": "V"},
}}


# ---------- finding dialogue lines in the script ----------
def test_detects_dialogue_line():
    d = dialogue.parse_dialogue('XERXES: "Burn the city."')
    assert d == ("XERXES", None, "Burn the city.")


def test_explicit_voice_key_and_curly_quotes():
    assert dialogue.parse_dialogue('LEONIDAS (messenger): “Come and take them.”') == ("LEONIDAS", "messenger", "Come and take them.")


def test_narration_is_not_dialogue():
    assert dialogue.parse_dialogue("At dawn, the King of Persia sat on a golden throne.") is None
    assert dialogue.parse_dialogue('He said: "no".') is None          # lower-case speaker = narration quoting


def test_dialogue_lines_from_script_keep_their_index():
    lines = parse_script('## climax\nThe king rose. [src: h]\nXERXES: "Burn it." [src: h]\n')
    found = dialogue.dialogue_lines(lines)
    assert [(d.index, d.speaker, d.text) for d in found] == [(1, "XERXES", "Burn it.")]


# ---------- choosing the voice ----------
def test_voice_by_speaker_name():
    assert dialogue.voice_for("XERXES", None, VOICES)[0] == "xerxes"


def test_voice_by_explicit_key_and_job_mapping():
    assert dialogue.voice_for("LEONIDAS", "messenger", VOICES)[0] == "messenger"
    assert dialogue.voice_for("SICINNUS", None, VOICES, mapping={"SICINNUS": "messenger"})[0] == "messenger"


def test_unknown_or_non_fish_voice_fails_clearly():
    with pytest.raises(dialogue.DialogueError, match="no voice"):
        dialogue.voice_for("NOBODY", None, VOICES)
    with pytest.raises(dialogue.DialogueError, match="not a Fish voice"):
        dialogue.voice_for("X", "narrator_like", VOICES)


# ---------- Fish request (never spend money, never leak the key) ----------
def test_refuses_paid_models(tmp_path):
    with pytest.raises(dialogue.DialogueError, match="free"):
        dialogue.fish_tts("hi", "ref", tmp_path / "a.mp3", "key", model="s2.1-pro")


def test_fish_request_shape(tmp_path):
    seen = {}
    def fake_post(url, body, headers, timeout=180):
        seen.update(url=url, body=json.loads(body), headers=headers)
        return 200, b"ID3audio", "audio/mpeg"
    out = dialogue.fish_tts("Burn it.", "ref-x", tmp_path / "a.mp3", "SECRET", post=fake_post)
    assert out.read_bytes() == b"ID3audio"
    assert seen["url"].endswith("/v1/tts")
    assert seen["body"] == {"text": "Burn it.", "reference_id": "ref-x", "format": "mp3", "normalize": True}
    assert seen["headers"]["model"] == "s2.1-pro-free"
    assert seen["headers"]["Authorization"] == "Bearer SECRET"


def test_fish_error_writes_nothing_and_hides_key(tmp_path):
    fake_post = lambda url, body, headers, timeout=180: (402, b'{"message":"no credit"}', "application/json")
    with pytest.raises(dialogue.DialogueError) as e:
        dialogue.fish_tts("x", "r", tmp_path / "a.mp3", "SECRET", post=fake_post)
    assert "SECRET" not in str(e.value)
    assert not (tmp_path / "a.mp3").exists()


def test_missing_key_fails_before_any_request(tmp_path):
    def boom(*a, **k):
        raise AssertionError("must not call Fish without a key")
    with pytest.raises(dialogue.DialogueError, match="FISH_AUDIO_API_KEY"):
        dialogue.fish_tts("x", "r", tmp_path / "a.mp3", None, post=boom)


# ---------- usage log ----------
def test_usage_log_appends(tmp_path):
    log = tmp_path / "fish_usage.json"
    dialogue.log_usage({"job": "j1", "text": "a"}, log)
    dialogue.log_usage({"job": "j2", "text": "bb"}, log)
    data = json.loads(log.read_text(encoding="utf-8"))
    assert [e["job"] for e in data["lines"]] == ["j1", "j2"]
    assert all("date" in e for e in data["lines"])


# ---------- voicing every dialogue line of a job ----------
def _fake_mp3(url, body, headers, timeout=180):
    # a real (tiny) mp3 so ffmpeg can convert it
    p = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=300:duration=0.5",
                        "-f", "mp3", "-"], capture_output=True, check=True)
    return 200, p.stdout, "audio/mpeg"


def test_voice_dialogue_makes_padded_wavs_and_caches(tmp_path):
    lines = parse_script('## climax\nNarration. [src: h]\nXERXES: "Burn it." [src: h]\n')
    calls = []
    post = lambda *a, **k: (calls.append(1), _fake_mp3(*a, **k))[1]
    log = tmp_path / "usage.json"
    out = dialogue.voice_dialogue("job1", lines, tmp_path / "dialogue", VOICES, "KEY", post=post, usage_log=log)
    assert len(out) == 1 and out[0]["speaker"] == "XERXES" and out[0]["voice"] == "xerxes"
    # 0.5 s of speech + 0.3 s breath before and after
    assert 1.0 <= out[0]["duration_s"] <= 1.25
    # same line again: no second request, but the use is still logged
    dialogue.voice_dialogue("job1", lines, tmp_path / "dialogue", VOICES, "KEY", post=post, usage_log=log)
    assert len(calls) == 1
    entries = json.loads(log.read_text(encoding="utf-8"))["lines"]
    assert [e["cached"] for e in entries] == [False, True]
    assert entries[0]["reference_id"] == "ref-x" and entries[0]["bytes"] == len("Burn it.")

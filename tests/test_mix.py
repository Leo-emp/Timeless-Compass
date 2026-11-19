# Tests for the final mix: voice + sfx layers + ambience + music (ducked under speech) -> loudness standard.
import json
import subprocess

import pytest

from tc import mix


def _tone(path, freq, secs, db=-20):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={secs}",
                    "-af", f"volume={db}dB", "-ar", "48000", str(path)], check=True)
    return path


def test_targets_shorts_louder():
    assert mix.TARGETS["short"]["lufs"] > mix.TARGETS["long"]["lufs"]
    assert mix.TARGETS["long"]["tp"] <= -1.0


def test_filter_path_escaping_for_windows():
    assert mix._fpath(r"C:\a b\c.wav") == r"'C\:/a b/c.wav'"


def test_clip_gain_brings_every_file_to_the_voice_level():
    # a quiet file (-30 LUFS) asked for at -6 dB under the voice (-14 LUFS) gets +10 dB
    assert mix.clip_gain(-6.0, -30.0) == pytest.approx(10.0)
    assert mix.clip_gain(-6.0, None) == pytest.approx(-6.0)


def test_graph_has_ducking_and_every_clip():
    clips = [{"path": "a.wav", "at": 1.0, "dur": 2.0, "gain": -3, "loop": False, "fade_in": 0.1, "fade_out": 0.2,
              "seek": 0, "bus": "fx"},
             {"path": "m.wav", "at": 0.0, "dur": 4.0, "gain": -6, "loop": True, "fade_in": 1, "fade_out": 2,
              "seek": 3.0, "bus": "music"}]
    g = mix.build_graph(clips, voice_s=5.0, target=mix.TARGETS["long"])
    assert "sidechaincompress" in g and "adelay=1000|1000" in g and "loop=0" in g and "seek_point=3" in g
    assert "loudnorm=I=-12" in g


def test_real_mix_hits_the_loudness_target(tmp_path):
    voice = _tone(tmp_path / "voice.wav", 220, 4, db=-18)
    fx = _tone(tmp_path / "fx.wav", 900, 1, db=-25)
    mus = _tone(tmp_path / "mus.wav", 330, 2, db=-25)
    clips = [{"path": str(fx), "at": 1.0, "dur": 1.0, "gain": -6, "loop": False, "fade_in": 0.05, "fade_out": 0.2,
              "seek": 0, "bus": "fx"},
             {"path": str(mus), "at": 0.0, "dur": 4.0, "gain": -6, "loop": True, "fade_in": 0.5, "fade_out": 1.0,
              "seek": 0, "bus": "music"}]
    info = mix.render(voice, clips, tmp_path / "mix.wav", "short")
    assert abs(info["lufs"] - mix.TARGETS["short"]["lufs"]) <= 1.0
    assert info["peak_db"] <= -0.5
    assert 3.9 <= info["duration_s"] <= 6.5


def test_clips_from_plans_resolves_sounds_and_music(tmp_path):
    sound = {"events": [{"sound": "s1", "at": 1, "dur": 2, "db": -6, "loop": False, "fade_in": 0.1, "fade_out": 0.2}],
             "ambience": [{"sound": "amb", "at": 0, "dur": 9, "db": -20, "loop": True, "fade_in": 0, "fade_out": 1},
                          {"sound": None, "at": 9, "dur": 3, "db": -20, "loop": True, "fade_in": 1, "fade_out": 1}]}
    music = {"cues": [{"track": "t1", "file": "t1.mp3", "at": 2, "dur": 5, "seek": 1, "fade_in": 1, "fade_out": 2, "db": -6}]}
    sfx_idx = {"sounds": [{"id": "s1", "file": "s1.wav", "lufs": -20}, {"id": "amb", "file": "amb.wav", "lufs": -30}]}
    tracks = {"tracks": [{"id": "t1", "file": "t1.mp3", "lufs": -16}]}
    clips, missing = mix.clips_from_plans(sound, music, sfx_idx, tracks, tmp_path / "sfx", tmp_path / "music")
    assert [c["bus"] for c in clips] == ["fx", "amb", "music"]
    assert clips[0]["gain"] == pytest.approx(-6 + (-14 + 20))
    assert clips[2]["seek"] == 1 and clips[2]["path"].endswith("t1.mp3")
    assert missing == ["ambience bed at 9.0 s has no sound"]

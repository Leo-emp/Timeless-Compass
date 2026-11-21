# Tests for lip sync: Rhubarb mouth cues -> a mouth-shape timeline WS1 can key onto the face rig.
import json

from tc import lipsync

CUES = [{"start": 0.0, "end": 0.3, "value": "X"}, {"start": 0.3, "end": 0.5, "value": "D"},
        {"start": 0.5, "end": 0.6, "value": "A"}, {"start": 0.6, "end": 1.0, "value": "X"}]


def test_every_rhubarb_shape_has_mouth_values():
    for shape in "ABCDEFGHX":
        m = lipsync.SHAPES[shape]
        assert 0 <= m["jaw"] <= 1 and "phonemes" in m


def test_timeline_adds_offset_and_mouth_values():
    tl = lipsync.timeline(CUES, offset=10.0)
    assert tl[1]["start"] == 10.3 and tl[1]["shape"] == "D"
    assert tl[1]["jaw"] > tl[2]["jaw"]           # D = wide open, A = closed lips
    assert tl[2]["closed"] == 1.0


def test_frames_sample_the_shape_at_every_frame():
    fr = lipsync.frames(CUES, fps=10)
    assert len(fr) == 10
    assert fr[0] == "X" and fr[3] == "D" and fr[5] == "A" and fr[9] == "X"


def test_cues_for_runs_rhubarb_with_dialog_text(tmp_path):
    seen = {}
    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        out = cmd[cmd.index("-o") + 1]
        open(out, "w").write(json.dumps({"mouthCues": CUES}))
        class R: returncode = 0; stderr = ""
        return R()
    wav = tmp_path / "a.wav"; wav.write_bytes(b"x")
    cues = lipsync.cues_for("rhubarb.exe", wav, "Burn it.", runner=fake_run)
    assert cues == CUES
    assert "--dialogFile" in seen["cmd"] and "-f" in seen["cmd"]


def test_find_rhubarb_uses_env_override(tmp_path, monkeypatch):
    exe = tmp_path / "rhubarb.exe"; exe.write_bytes(b"")
    monkeypatch.setenv("TC_RHUBARB", str(exe))
    assert lipsync.find_rhubarb() == str(exe)


def test_job_lipsync_places_lines_on_the_voice_timeline():
    dialogue = {"lines": [{"index": 4, "speaker": "XERXES", "voice": "xerxes", "lipsync": CUES}]}
    voice = {"dialogue_at": {"4": 12.5}}
    out = lipsync.job_timeline(dialogue, voice, fps=24)
    line = out["lines"][0]
    assert line["at"] == 12.5 and line["speaker"] == "XERXES"
    assert line["cues"][0]["start"] == 12.5
    assert out["fps"] == 24 and len(line["frames"]) == 24


def test_film_lipsync_file_is_written(tmp_path):
    from tc.lipsync import write_film_lipsync
    dialogue = {"lines": [{"index": 3, "speaker": "XERXES", "voice": "xerxes", "lipsync": [{"start": 0.0, "end": 0.2, "value": "D"}]}]}
    voice = {"dialogue_at": {"3": 12.5}}
    out = write_film_lipsync(dialogue, voice, tmp_path / "lipsync.json")
    import json
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["lines"][0]["speaker"] == "XERXES" and d["lines"][0]["cues"][0]["start"] == 12.5

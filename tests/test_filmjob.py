# Tests for wiring a job into the film: the scene registry, sound + music cues from the shot plan, mux.
import pytest

from tc import filmjob

TIMED = {"fps": 24, "frames": 240, "shots": [
    {"id": "s1", "start_f": 0, "end_f": 120, "sfx": [{"word": "ships", "sound": "waves_soft", "db": -18, "at": 1.8}],
     "music": {"cue": "hook", "from_word": "The", "at": 0.0}},
    {"id": "s2", "start_f": 120, "end_f": 240, "sfx": [{"word": "burn", "sound": "fire_big", "db": -10, "at": 6.2}], "music": None}]}
SFX = {"sounds": [{"id": "waves_soft", "file": "w.mp3", "duration": 12.0}, {"id": "fire_big", "file": "f.mp3", "duration": 2.5}]}
TRACKS = {"tracks": [{"id": "drums_dread", "file": "d.mp3", "moods": ["dread", "tension"], "intensity": 3, "length_s": 60},
                     {"id": "lyre_hope", "file": "l.mp3", "moods": ["hope"], "intensity": 2, "length_s": 60}]}


def test_index_lists_job_folders_with_a_plan(tmp_path):
    for j in ("job_a", "job_b"):
        (tmp_path / j).mkdir()
        (tmp_path / j / "plan.json").write_text("{}", encoding="utf-8")
        (tmp_path / j / "scenes.ts").write_text("", encoding="utf-8")
    (tmp_path / "no_plan").mkdir()
    src = filmjob.write_index(tmp_path)
    assert "job_a/plan.json" in src and "job_b/scenes" in src and "no_plan" not in src


def test_sfx_land_on_their_words():
    snd = filmjob.sound_from_plan(TIMED, SFX)
    assert snd["events"][0] == {"sound": "waves_soft", "at": 1.8, "dur": 4.0, "db": -18}   # long beds trimmed to 4 s
    assert snd["events"][1]["at"] == 6.2 and snd["events"][1]["dur"] == 2.5


def test_music_only_where_a_cue_is_named():
    mus = filmjob.music_from_plan(TIMED, TRACKS)
    assert len(mus["cues"]) == 1 and mus["cues"][0]["track"] == "drums_dread" and mus["cues"][0]["at"] == 0.0
    assert mus["cues"][0]["dur"] == 5.0                                  # until the shot ends (frame 120 / 24)


def test_mux_refuses_length_mismatch(tmp_path):
    with pytest.raises(ValueError, match="length"):
        filmjob.mux(tmp_path / "v.mp4", tmp_path / "a.wav", tmp_path / "o.mp4",
                    probe=lambda p: 10.0 if p.name == "v.mp4" else 9.5, runner=lambda *a, **k: None)


def test_music_cue_can_span_shots_until():
    import copy
    t = copy.deepcopy(TIMED); t["shots"][0]["music"]["until"] = "s2"
    assert filmjob.music_from_plan(t, TRACKS)["cues"][0]["dur"] == 10.0


def test_mux_trims_a_short_music_tail(tmp_path):
    calls = []
    filmjob.mux(tmp_path / "v.mp4", tmp_path / "a.wav", tmp_path / "o.mp4",
                probe=lambda p: 52.3 if p.name == "v.mp4" else 54.3, runner=lambda cmd, **k: calls.append(cmd))
    assert "-t" in calls[0] and calls[0][calls[0].index("-t") + 1] == "52.300"

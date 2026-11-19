# Tests for music cues: rule r11 (music only at chosen moments), the tagged track catalogue, the picker.
import json

import pytest

from tc import music

TRACKS = {"tracks": [
    {"id": "lyre_dread", "moods": ["dread", "mystery"], "intensity": 2, "era": ["ancient"], "shape": "slow_build",
     "length_s": 120, "tempo_bpm": 70, "peak_s": 80, "licence": "CC0", "source": "fma", "file": "a.mp3"},
    {"id": "war_drums", "moods": ["menace", "triumph"], "intensity": 5, "era": ["ancient", "epic"], "shape": "steady",
     "length_s": 150, "tempo_bpm": 120, "licence": "Pixabay Content License", "source": "pixabay", "file": "b.mp3"},
    {"id": "epic_rise", "moods": ["tension", "awe"], "intensity": 4, "era": ["epic"], "shape": "slow_build",
     "length_s": 140, "tempo_bpm": 90, "peak_s": 100, "licence": "CC0", "source": "fma", "file": "c.mp3"},
    {"id": "synth_pulse", "moods": ["tension", "dread"], "intensity": 3, "era": ["modern"], "shape": "steady",
     "length_s": 180, "tempo_bpm": 100, "licence": "CC0", "source": "fma", "file": "d.mp3"},
]}

SHOTS = [{"id": f"s{i}", "at": i * 5.0, "dur": 5.0, "era": "greece_480bc"} for i in range(24)]   # 120 s video


def cue(**kw):
    base = {"cue": "tension", "mood": "tension", "from": "s4", "to": "s7"}
    return base | kw


# ---------- catalogue ----------
def test_track_needs_tags_and_a_good_licence():
    assert music.check_track(TRACKS["tracks"][0]) == []
    bad = dict(TRACKS["tracks"][0], moods=["happy"], intensity=9, licence="CC BY-NC")
    problems = " ".join(music.check_track(bad))
    assert "mood" in problems and "intensity" in problems and "licence" in problems


# ---------- rule r11 ----------
def test_cue_kinds_follow_r11():
    probs = music.check_cues({"s4": cue(cue="background")}, SHOTS, "long")
    assert any("r11" in p for p in probs)


def test_no_wall_to_wall_music():
    wall = {"s0": cue(cue="hook", mood="mystery", **{"from": "s0", "to": "s22"})}
    assert any("wall-to-wall" in p for p in music.check_cues(wall, SHOTS, "long"))


def test_peak_must_be_inside_the_cue():
    c = {"s4": cue(peak="s20")}
    assert any("inside" in p for p in music.check_cues(c, SHOTS, "long"))


def test_cues_must_not_overlap_and_need_silence_between():
    cues = {"s2": cue(**{"from": "s2", "to": "s5"}), "s5": cue(cue="battle", mood="menace", **{"from": "s5", "to": "s8"})}
    assert any("overlap" in p for p in music.check_cues(cues, SHOTS, "long"))
    close = {"s2": cue(**{"from": "s2", "to": "s4"}), "s5": cue(cue="battle", mood="menace", **{"from": "s5", "to": "s8"})}
    assert any("music-free" in p for p in music.check_cues(close, SHOTS, "long"))


def test_good_cues_pass():
    cues = {"s0": cue(cue="hook", mood="mystery", **{"from": "s0", "to": "s2"}),
            "s10": cue(cue="climax", mood="tension", peak="s12", **{"from": "s10", "to": "s12"}),
            "s21": cue(cue="ending", mood="awe", **{"from": "s21", "to": "s23"})}
    assert music.check_cues(cues, SHOTS, "long") == []


# ---------- picker ----------
def test_picker_matches_mood_and_era():
    assert music.choose(cue(cue="hook", mood="dread"), "ancient", TRACKS)["id"] == "lyre_dread"
    assert music.choose(cue(cue="battle", mood="menace"), "ancient", TRACKS)["id"] == "war_drums"
    assert music.choose(cue(cue="tension", mood="dread"), "modern", TRACKS)["id"] == "synth_pulse"


def test_picker_skips_tracks_used_in_the_previous_video_and_in_this_one():
    first = music.choose(cue(cue="battle", mood="menace"), "ancient", TRACKS)["id"]
    assert music.choose(cue(cue="battle", mood="menace"), "ancient", TRACKS, banned={first})["id"] != first


def test_era_group():
    assert music.era_group("greece_480bc") == "ancient"
    assert music.era_group("usa_1950s") == "modern"


def test_place_puts_the_peak_on_the_climax_shot():
    c = cue(cue="climax", mood="tension", peak="s13", **{"from": "s10", "to": "s14"})
    t = TRACKS["tracks"][2]                          # peak at 100 s into the track
    p = music.place(c, t, SHOTS)
    assert p["at"] == 50.0 and p["dur"] == 25.0      # starts on a cut, ends at the end of the last shot
    # the track's peak (100 s) lands at 65 s on the timeline = start of shot s13
    assert p["at"] + (t["peak_s"] - p["seek"]) == pytest.approx(65.0)
    assert p["fade_out"] > 0 and p["duck"] is True


def test_used_log_bans_the_previous_videos_tracks(tmp_path):
    f = tmp_path / "used.json"
    music.record_used("job1", ["war_drums"], f)
    music.record_used("job2", ["epic_rise"], f)
    assert music.banned_for("job3", f) == {"epic_rise"}          # only the video right before
    music.record_used("job2", ["lyre_dread"], f)                  # re-picking job2 replaces its entry
    assert music.banned_for("job3", f) == {"lyre_dread"}
    assert music.banned_for("job2", f) == {"war_drums"}           # a job is compared with the one before it


# ---------- learning ----------
def test_retention_dip_during_music_suggests_a_rule():
    placed = [{"cue": "tension", "track": "epic_rise", "at": 40.0, "dur": 20.0}]
    # flat 1%/10 s everywhere, but 8% lost during the music
    retention = [[0, 100], [10, 99], [20, 98], [30, 97], [40, 96], [60, 88], [70, 87], [80, 86]]
    tips = music.retention_lessons(placed, retention)
    assert len(tips) == 1 and "epic_rise" in tips[0]

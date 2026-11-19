# Tests for sound effects: licence gate, Freesound fetch, the local library, layered design per shot, ambience beds.
import json
import subprocess

import pytest

from tc import sfx


# ---------- licence rules (docs/BACKLOG.md WS11) ----------
@pytest.mark.parametrize("lic,ok,credit", [
    ("http://creativecommons.org/publicdomain/zero/1.0/", True, False),
    ("Creative Commons 0", True, False),
    ("https://creativecommons.org/licenses/by/4.0/", True, True),
    ("Attribution", True, True),
    ("http://creativecommons.org/licenses/by-nc/3.0/", False, False),     # NEVER non-commercial
    ("Attribution NonCommercial", False, False),
    ("https://creativecommons.org/licenses/by-nd/4.0/", False, False),    # no-derivatives: we cut + mix sounds
    ("http://creativecommons.org/licenses/sampling+/1.0/", False, False),
    ("Pixabay Content License", True, False),
    ("Sonniss GDC", True, False),
    ("some random licence", False, False),                                 # unknown = refused
])
def test_licence_verdict(lic, ok, credit):
    v = sfx.licence_verdict(lic)
    assert (v["ok"], v["credit"]) == (ok, credit)


# ---------- Freesound ----------
RESULTS = {"results": [
    {"id": 1, "name": "march nc", "license": "http://creativecommons.org/licenses/by-nc/4.0/", "username": "a",
     "duration": 5.0, "previews": {"preview-hq-mp3": "https://x/1.mp3"}, "tags": ["march"]},
    {"id": 2, "name": "march by", "license": "https://creativecommons.org/licenses/by/4.0/", "username": "bob",
     "duration": 6.0, "previews": {"preview-hq-mp3": "https://x/2.mp3"}, "tags": ["march", "footsteps"]},
]}


def test_freesound_search_filters_licences_and_sends_key_in_header():
    seen = {}
    def fake_get(url, headers=None, timeout=60):
        seen.update(url=url, headers=headers)
        return RESULTS
    hits = sfx.freesound_search("army march", "KEY", get=fake_get)
    assert [h["id"] for h in hits] == [2]                     # the NC result is dropped even if the API returns it
    assert seen["headers"] == {"Authorization": "Token KEY"}
    assert "KEY" not in seen["url"]                           # never in the URL (logs / command lines)
    assert "license" in seen["url"]


def test_freesound_needs_key():
    with pytest.raises(sfx.SfxError, match="FREESOUND_API_KEY"):
        sfx.freesound_search("x", None, get=lambda *a, **k: RESULTS)


# ---------- local library ----------
def _tone(path, secs=1.0):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=200:duration={secs}", str(path)], check=True)
    return path


def test_add_sound_copies_file_and_records_licence(tmp_path):
    src = _tone(tmp_path / "steps.wav")
    lib = tmp_path / "lib"
    e = sfx.add_sound(src, ["footsteps", "march"], "freesound", "https://creativecommons.org/licenses/by/4.0/",
                      root=lib, credit='"steps" by bob (freesound.org/s/2) - CC BY 4.0')
    assert (lib / "files" / e["file"]).exists()
    idx = sfx.load_index(lib)
    assert idx["sounds"][0]["credit"].startswith('"steps"') and 0.9 < idx["sounds"][0]["duration_s"] < 1.1


def test_add_sound_refuses_bad_licence_and_missing_credit(tmp_path):
    src = _tone(tmp_path / "a.wav")
    with pytest.raises(sfx.SfxError, match="licence"):
        sfx.add_sound(src, ["x"], "freesound", "Attribution NonCommercial", root=tmp_path / "lib")
    with pytest.raises(sfx.SfxError, match="credit"):
        sfx.add_sound(src, ["x"], "freesound", "Attribution", root=tmp_path / "lib")


def test_credits_only_for_cc_by():
    idx = {"sounds": [{"id": "a", "credit": "A by x - CC BY 4.0", "licence": "Attribution"},
                      {"id": "b", "credit": "", "licence": "Creative Commons 0"}]}
    assert sfx.credits(["a", "b", "a"], idx) == ["A by x - CC BY 4.0"]


# ---------- layered sound design ----------
INDEX = {"sounds": [
    {"id": "steps1", "tags": ["footsteps", "march"], "duration_s": 8},
    {"id": "steps2", "tags": ["footsteps", "march", "gravel"], "duration_s": 8},
    {"id": "armour", "tags": ["armour", "clank"], "duration_s": 4},
    {"id": "sea", "tags": ["sea", "waves", "ambience"], "duration_s": 60},
    {"id": "wind", "tags": ["wind", "ambience"], "duration_s": 60},
]}


def test_pick_best_tag_match_and_varies_with_salt():
    assert sfx.pick(["armour", "clank"], INDEX)["id"] == "armour"
    picks = {sfx.pick(["footsteps", "march"], INDEX, salt=s)["id"] for s in range(6)}
    assert picks == {"steps1", "steps2"}                      # no single sound repeated every time
    assert sfx.pick(["horse"], INDEX) is None


def test_march_is_several_layers():
    layers = sfx.RECIPES["march"]
    assert len(layers) >= 4 and any("footsteps" in l["tags"] for l in layers)


def test_design_places_layers_on_the_shot_and_lists_missing():
    shots = [{"id": "s1", "at": 2.0, "dur": 4.0, "where": "salamis cove", "sfx": ["march"]}]
    plan = sfx.design(shots, INDEX)
    ev = [e for e in plan["events"] if e["shot"] == "s1"]
    assert {e["sound"] for e in ev} >= {"armour"} and any(e["sound"] in ("steps1", "steps2") for e in ev)
    assert all(e["at"] >= 2.0 and e["at"] + e["dur"] <= 6.0 + 1e-6 for e in ev)
    assert any("spear" in " ".join(m) for m in plan["missing"])     # we have no spear sound yet -> fetch list


def test_ambience_beds_merge_consecutive_shots_and_crossfade():
    shots = [{"id": "a", "at": 0.0, "dur": 4.0, "where": "salamis cove", "sfx": []},
             {"id": "b", "at": 4.0, "dur": 5.0, "where": "salamis cove", "sfx": []},
             {"id": "c", "at": 9.0, "dur": 3.0, "where": "mountain pass", "sfx": ["amb:wind"]}]
    beds = sfx.design(shots, INDEX)["ambience"]
    assert [b["ambience"] for b in beds] == ["sea", "wind"]
    assert beds[0]["at"] == 0.0 and beds[0]["dur"] == pytest.approx(9.0 + sfx.XFADE_S)   # overlaps the next bed
    assert beds[1]["at"] == 9.0 and beds[1]["sound"] == "wind"
    assert beds[0]["fade_out"] == sfx.XFADE_S

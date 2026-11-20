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


# ---------------- curated library build (tc sfx build) ----------------
def _r(i, name, rating=4.5, n=10, dl=500, lic="http://creativecommons.org/publicdomain/zero/1.0/", dur=2.0):
    return {"id": i, "name": name, "license": lic, "username": "u", "duration": dur, "avg_rating": rating,
            "num_ratings": n, "num_downloads": dl, "tags": [], "previews": {"preview-hq-mp3": f"http://x/{i}.mp3"}}


def test_rank_prefers_well_rated_by_many_over_one_lucky_five():
    lucky = _r(1, "clash a", rating=5.0, n=1)
    solid = _r(2, "clash b", rating=4.6, n=40)
    assert [r["id"] for r in sfx.rank([lucky, solid])] == [2, 1]


def test_rank_drops_franchise_and_fan_recreations():
    bad = [_r(1, "tmnt_2012_leo_katana_sword"), _r(2, "Lightsaber hum"), _r(3, "Shredder blade clash")]
    good = _r(4, "Sword_Clash (46).wav")
    assert [r["id"] for r in sfx.rank(bad + [good])] == [4]


def test_rank_drops_item_exclude_words():
    # an ancient battle must not get a gunshot or a synth
    rs = [_r(1, "battle with rifle fire"), _r(2, "medieval battle crowd")]
    assert [r["id"] for r in sfx.rank(rs, exclude=["rifle"])] == [2]


def test_add_sound_keeps_mood_and_intensity(tmp_path):
    src = _tone(tmp_path / "a.wav")
    e = sfx.add_sound(src, ["sword", "clash"], "freesound", "Creative Commons 0", root=tmp_path / "lib",
                      mood=["tense", "violent"], intensity=4, freesound_id=326795)
    assert e["mood"] == ["tense", "violent"] and e["intensity"] == 4 and e["freesound_id"] == 326795


def test_build_library_fetches_ranked_skips_known_and_tags_mood(tmp_path):
    src = _tone(tmp_path / "t.wav")
    data = src.read_bytes()
    results = [_r(10, "Sword clash ring", n=30), _r(11, "tmnt sword"), _r(12, "Sword hit", n=5)]
    def fake_get(url, headers=None, timeout=60):
        assert "duration%3A%5B0.5+TO+4" in url                # the item's length range goes to the API
        return {"results": results}
    wanted = [{"name": "sword_hits", "query": "sword clash", "tags": ["sword", "clash"], "mood": ["violent"],
               "intensity": 4, "n": 2, "min_s": 0.5, "max_s": 4}]
    root = tmp_path / "lib"
    rep = sfx.build_library(wanted, "k", root=root, get=fake_get, download=lambda u: (200, data, "audio/mpeg"))
    idx = sfx.load_index(root)
    assert [s["freesound_id"] for s in idx["sounds"]] == [10, 12]       # ranked, franchise one dropped
    assert all(s["intensity"] == 4 and s["mood"] == ["violent"] and "sword" in s["tags"] for s in idx["sounds"])
    assert rep[0]["added"] == 2
    # second run: already have both -> nothing new downloaded
    rep2 = sfx.build_library(wanted, "k", root=root, get=fake_get, download=lambda u: (200, data, "audio/mpeg"))
    assert rep2[0]["added"] == 0 and len(sfx.load_index(root)["sounds"]) == 2


def test_pick_prefers_the_shots_intensity():
    idx = {"sounds": [{"id": "soft", "tags": ["sword", "clash"], "intensity": 2, "duration_s": 1},
                      {"id": "hard", "tags": ["sword", "clash"], "intensity": 5, "duration_s": 1}]}
    assert sfx.pick(["sword", "clash"], idx, intensity=5)["id"] == "hard"
    assert sfx.pick(["sword", "clash"], idx, intensity=1)["id"] == "soft"


def test_battle_recipes_for_the_film_library():
    for ev in ("arrow_volley", "cannon", "cavalry", "war_cry", "shield_wall"):
        assert ev in sfx.RECIPES and len(sfx.RECIPES[ev]) >= 2


def test_wanted_manifest_covers_the_brief_and_matches_recipes():
    import pathlib
    wanted = json.loads(pathlib.Path("library/sfx/wanted.json").read_text(encoding="utf-8"))["wanted"]
    have = [set(w["tags"]) for w in wanted]
    # every recipe layer + ambience can be found by some wanted item
    for layers in sfx.RECIPES.values():
        for l in layers:
            assert any(set(l["tags"]) <= h for h in have), l["tags"]
    for tags in sfx.AMBIENCES.values():
        assert any(set(tags) <= h for h in have), tags
    for w in wanted:
        assert 1 <= w["intensity"] <= 5 and w["mood"] and w["query"]


def test_load_wanted_merges_common_excludes(tmp_path):
    f = tmp_path / "w.json"
    f.write_text(json.dumps({"common_exclude": ["rifle"], "wanted": [
        {"name": "a", "query": "q", "tags": ["x"], "mood": ["calm"], "intensity": 1, "exclude": ["car"]},
        {"name": "b", "query": "q", "tags": ["y"], "mood": ["calm"], "intensity": 1, "exclude_common": False}]}))
    a, b = sfx.load_wanted(f)
    assert set(a["exclude"]) == {"rifle", "car"} and b["exclude"] == []
    assert [w["name"] for w in sfx.load_wanted(f, only=["b"])] == ["b"]


def test_build_library_uses_extra_queries_and_dedups(tmp_path):
    data = _tone(tmp_path / "t.wav").read_bytes()
    seen = []
    def fake_get(url, headers=None, timeout=60):
        seen.append(url)
        return {"results": [_r(1, "battle a", n=20), _r(2, "battle b", n=10)] if "first" in url else [_r(1, "battle a", n=20), _r(3, "battle c", n=5)]}
    wanted = [{"name": "bed", "query": "first", "also": ["second"], "tags": ["battle"], "mood": ["violent"], "intensity": 4, "n": 3}]
    sfx.build_library(wanted, "k", root=tmp_path / "lib", get=fake_get, download=lambda u: (200, data, "audio/mpeg"), log=None)
    assert len(seen) == 2
    assert sorted(s["freesound_id"] for s in sfx.load_index(tmp_path / "lib")["sounds"]) == [1, 2, 3]


def test_rank_require_keeps_only_on_topic_results():
    # the NAME must say it: uploader tags are too loose ("digital wildfire" is tagged fire)
    rs = [_r(1, "Slow Creaky Piano Pedal"), _r(2, "Heavy wooden door close"), dict(_r(3, "take 4"), tags=["door", "wood"])]
    assert [r["id"] for r in sfx.rank(rs, require=["door"])] == [2]


def test_load_wanted_passes_global_reject_ids(tmp_path):
    f = tmp_path / "w.json"
    f.write_text(json.dumps({"reject_ids": [7], "wanted": [
        {"name": "a", "query": "q", "tags": ["x"], "mood": ["calm"], "intensity": 1}]}))
    assert sfx.load_wanted(f)[0]["reject"] == [7]
    rs = [_r(7, "fine name"), _r(8, "fine name too")]
    assert [r["id"] for r in sfx.rank(rs, reject=[7])] == [8]


# ---------------- free-text shot sfx ("roaring fire", "ram impact") ----------------
def test_resolve_maps_known_phrases_to_recipes_or_tags():
    assert sfx.resolve("ram impact") == "ship_ram"
    assert sfx.resolve("roaring fire") == "fire"
    assert sfx.resolve("oars in unison") == "rowing"
    assert sfx.resolve("silence") is None                 # silence = no sound at all
    assert sfx.resolve("a sword drawn") == ["sword", "draw"]


def test_resolve_generic_fallback_drops_little_words_and_uses_synonyms():
    # unknown phrase: stop words go, synonyms map to library tags
    assert sfx.resolve("the timber splintering") == ["wood", "crash"]
    assert sfx.resolve("distant screams") == ["crowd", "scream"]


def test_every_phrase_in_the_five_shorts_resolves_to_a_wanted_sound():
    import glob, pathlib
    wanted = [set(w["tags"]) for w in json.loads(pathlib.Path("library/sfx/wanted.json").read_text(encoding="utf-8"))["wanted"]]
    phrases = {p for j in glob.glob("jobs/*/shots.json")
               for s in json.loads(pathlib.Path(j).read_text(encoding="utf-8"))["shots"] for p in s.get("sfx") or []}
    for p in phrases:
        r = sfx.resolve(p)
        if r is None:
            continue
        layers = [l["tags"] for l in sfx.RECIPES[r]] if isinstance(r, str) else [r]
        for tags in layers:
            assert any(set(tags) <= w for w in wanted), (p, tags)


def test_design_uses_resolve_and_shot_intensity():
    idx = {"sounds": [{"id": "fire_soft", "tags": ["fire", "crackle"], "intensity": 2, "duration_s": 30},
                      {"id": "roar", "tags": ["fire", "roar"], "intensity": 5, "duration_s": 30}]}
    shots = [{"id": "s8", "at": 0, "dur": 5, "where": "athens", "sfx": ["roaring fire", "silence"]}]
    plan = sfx.design(shots, idx)
    assert {"roar", "fire_soft"} <= {e["sound"] for e in plan["events"]}
    assert not any("silence" in " ".join(m) for m in plan["missing"])

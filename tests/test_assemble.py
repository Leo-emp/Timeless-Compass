import json

from tc import assemble


def _lib(tmp_path):
    """A tiny asset library on disk: one character, one wardrobe, one set."""
    for kind, name, body in [
        ("cast", "themistocles", {"name": "themistocles", "era": "greece_480bc", "wardrobe": "greek_civilian_480bc"}),
        ("wardrobe", "greek_civilian_480bc", {"name": "greek_civilian_480bc", "era": "greece_480bc"}),
        ("sets", "salamis_strait_dusk", {"name": "salamis_strait_dusk", "era": "greece_480bc",
                                         "builder": "sets.salamis_dusk", "aliases": ["strait", "harbour"]}),
    ]:
        (tmp_path / kind).mkdir(exist_ok=True)
        (tmp_path / kind / f"{name}.json").write_text(json.dumps(body), encoding="utf-8")
    return assemble.load_library(tmp_path)


def _shot(**kw):
    d = {"id": "s001", "line": 0, "at": 0.0, "dur": 4.0, "hold": False, "who": ["themistocles"], "where": "strait",
         "action": "walks along the harbour wall", "expression": {}, "camera": {"move": "track", "from": "side"},
         "era": "greece_480bc"}
    d.update(kw)
    return d


def test_load_library_indexes_manifests_by_kind_and_name(tmp_path):
    lib = _lib(tmp_path)
    assert set(lib) >= {"cast", "wardrobe", "sets"}
    assert lib["cast"]["themistocles"]["wardrobe"] == "greek_civilian_480bc"


def test_recipe_resolves_cast_with_default_wardrobe_and_set_by_alias(tmp_path):
    r = assemble.recipe_for(_shot(), _lib(tmp_path))
    assert r["cast"] == [{"name": "themistocles", "wardrobe": "greek_civilian_480bc"}]
    assert r["set"] == {"name": "salamis_strait_dusk", "builder": "sets.salamis_dusk"}
    assert r["missing"] == []


def test_recipe_frames_come_from_duration_at_24fps(tmp_path):
    r = assemble.recipe_for(_shot(dur=4.5), _lib(tmp_path))
    assert r["frames"] == 108 and r["fps"] == 24


def test_action_keyword_picks_mocap_clip_or_pose(tmp_path):
    lib = _lib(tmp_path)
    assert assemble.recipe_for(_shot(action="walks along the harbour wall"), lib)["motion"] == {"clip": "16_15"}
    assert assemble.recipe_for(_shot(action="hands the sealed letter to Sicinnus"), lib)["motion"] == {"pose": "hand_over"}


def test_unknown_character_set_and_action_are_reported_as_gaps_not_errors(tmp_path):
    r = assemble.recipe_for(_shot(who=["xerxes"], where="persian camp", action="juggles"), _lib(tmp_path))
    assert r["cast"] == [] and r["set"] is None and r["motion"] is None
    assert r["missing"] == ["cast:xerxes", "set:persian camp", "motion:juggles"]


def test_shot_with_no_people_needs_no_motion(tmp_path):
    r = assemble.recipe_for(_shot(who=[], action="waves roll in at dusk"), _lib(tmp_path))
    assert r["motion"] is None and r["missing"] == []


def test_era_mismatch_is_a_gap(tmp_path):
    r = assemble.recipe_for(_shot(era="usa_1950s"), _lib(tmp_path))
    assert "era:themistocles is greece_480bc, shot is usa_1950s" in r["missing"]


def test_assemble_collects_unique_gaps_across_shots(tmp_path):
    lib = _lib(tmp_path)
    shots = [_shot(id="s1", who=["xerxes"]), _shot(id="s2", who=["xerxes"]), _shot(id="s3")]
    recipes, gaps = assemble.assemble(shots, lib)
    assert [r["shot"] for r in recipes] == ["s1", "s2", "s3"]
    assert gaps == ["cast:xerxes"]


def test_recipe_carries_the_action_text_for_the_acting_layer(tmp_path):
    r = assemble.recipe_for(_shot(action="argues with the generals"), _lib(tmp_path))
    assert r["action"] == "argues with the generals"


def test_mixamo_acting_clips_are_chosen_from_action_words(tmp_path):
    lib = _lib(tmp_path)
    assert assemble.recipe_for(_shot(action="argues with the generals"), lib)["motion"] == {"clip": "arguing"}
    assert assemble.recipe_for(_shot(action="kneels before the king"), lib)["motion"] == {"clip": "kneeling_idle"}
    assert assemble.recipe_for(_shot(action="points at the map"), lib)["motion"] == {"clip": "pointing"}


def test_crowd_entries_become_generated_extras_not_gaps(tmp_path):
    r = assemble.recipe_for(_shot(who=["themistocles", "crowd:citizen:6"]), _lib(tmp_path))
    assert r["missing"] == []
    assert [c["name"] for c in r["cast"]] == ["themistocles"]
    assert r["crowd"] == [{"role": "citizen", "count": 6, "era": "greece_480bc"}]


def test_assemble_fills_crowds_with_unique_people_and_records_them(tmp_path):
    from tc import crowd
    lib = _lib(tmp_path)
    shots = [_shot(id="s1", who=["crowd:citizen:5"]), _shot(id="s2", who=["crowd:citizen:5"])]
    recipes, gaps = assemble.assemble(shots, lib, used_seeds=set())
    seeds = [p["seed"] for r in recipes for p in r["extras"]]
    assert len(seeds) == 10 and len(set(seeds)) == 10           # nobody appears twice
    assert gaps == []

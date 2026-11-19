# Tests for WS9 task 3 (asset cache): which scans each shot needs, the R2 key layout, the 10 GB free-tier budget,
# and cache keys for heavy built assets (.blend files) that change only when their recipe or code changes.
import json

import pytest

from tc import render_cache as rc


INDEX = {
    "boulder_01": {"source": "https://polyhaven.com/a/boulder_01", "bytes": 20_000_000, "kind": "models",
                   "files": ["boulder_01_2k.blend"]},
    "grass_medium_01": {"source": "https://polyhaven.com/a/grass_medium_01", "bytes": 21_000_000, "kind": "models",
                        "files": ["g.blend"]},
    "kylix_cleveland": {"source": "https://sketchfab.com/3d-models/x", "bytes": 5_000_000, "kind": "glb",
                        "files": ["model.glb"]},
}


def test_scans_named_in_source_code_are_found():
    code = "def salamis_dusk():\n    scatter.scatter(g, ['grass_medium_01'], 10)\n    load_scan('boulder_01', 0)\n"
    assert rc.scans_in_code(code, INDEX) == ["boulder_01", "grass_medium_01"]


def test_function_body_is_cut_out_of_a_module():
    code = "def a():\n    x = 'boulder_01'\n\ndef b():\n    y = 'kylix_cleveland'\n"
    assert "kylix" not in rc.function_source(code, "a") and "boulder_01" in rc.function_source(code, "a")


def test_needed_scans_per_recipe_uses_manifest_list_first():
    lib = {"sets": {"cove": {"scans": ["kylix_cleveland"]}}, "cast": {}, "wardrobe": {}}
    recipe = {"shot": "s001", "set": {"name": "cove", "builder": "sets.cove"}, "cast": []}
    assert rc.needed_scans(recipe, lib, INDEX, code_for=lambda builder: "") == ["kylix_cleveland"]


def test_needed_scans_falls_back_to_builder_code_and_wardrobe():
    lib = {"sets": {"cove": {}}, "cast": {}, "wardrobe": {"chiton": {"scans": ["grass_medium_01"]}}}
    recipe = {"shot": "s001", "set": {"name": "cove", "builder": "sets.cove"},
              "cast": [{"name": "t", "wardrobe": "chiton"}]}
    got = rc.needed_scans(recipe, lib, INDEX, code_for=lambda builder: "load_scan('boulder_01')")
    assert got == ["boulder_01", "grass_medium_01"]


def test_r2_keys_and_fetch_source():
    assert rc.r2_key("boulder_01", "boulder_01_2k.blend") == "library/scans/boulder_01/boulder_01_2k.blend"
    assert rc.fallback_source(INDEX["boulder_01"]) == "polyhaven"     # can be re-downloaded free
    assert rc.fallback_source(INDEX["kylix_cleveland"]) is None       # Sketchfab needs a token -> R2 only


def test_budget_refuses_over_the_library_share_of_10gb():
    small = {"a": {"bytes": 1 * rc.GB}}
    assert rc.budget_report(small)["ok"]
    big = {"a": {"bytes": 7 * rc.GB}}
    rep = rc.budget_report(big)
    assert not rep["ok"] and rep["limit_gb"] == rc.LIBRARY_BUDGET_GB < rc.R2_FREE_GB


def test_shard_download_is_only_what_the_shard_needs():
    scans = {"s001": ["boulder_01"], "s002": ["grass_medium_01", "boulder_01"], "s003": ["kylix_cleveland"]}
    assert rc.shard_scans(["s001", "s002"], scans) == ["boulder_01", "grass_medium_01"]


def test_built_asset_key_changes_when_recipe_or_code_changes():
    k1 = rc.built_key("cast", "themistocles", {"hair": "short"}, "def character(): pass")
    k2 = rc.built_key("cast", "themistocles", {"hair": "long"}, "def character(): pass")
    k3 = rc.built_key("cast", "themistocles", {"hair": "short"}, "def character(): return 1")
    assert k1 != k2 and k1 != k3 and k1 == rc.built_key("cast", "themistocles", {"hair": "short"}, "def character(): pass")
    assert k1.startswith("built/cast/themistocles-") and k1.endswith(".blend")


def test_index_from_scan_folders(tmp_path):
    d = tmp_path / "boulder_01"
    d.mkdir()
    (d / "asset.json").write_text(json.dumps({"id": "boulder_01", "kind": "models", "licence": "CC0",
                                              "source": "https://polyhaven.com/a/boulder_01", "files": ["b.blend"]}))
    (d / "b.blend").write_bytes(b"x" * 10)
    idx = rc.build_index(tmp_path)
    assert idx["boulder_01"]["bytes"] == 10 + len((d / "asset.json").read_bytes())
    assert idx["boulder_01"]["licence"] == "CC0"


def test_fetch_plan_skips_files_already_cached(tmp_path):
    (tmp_path / "boulder_01").mkdir()
    (tmp_path / "boulder_01" / "boulder_01_2k.blend").write_bytes(b"x")
    todo = rc.fetch_plan(["boulder_01", "kylix_cleveland"], INDEX, tmp_path)
    assert [(t["id"], t["file"]) for t in todo] == [("kylix_cleveland", "model.glb")]


def test_public_url_needs_owner_setting(monkeypatch):
    monkeypatch.delenv("TC_R2_PUBLIC_URL", raising=False)
    with pytest.raises(rc.CacheError):
        rc.public_url("library/x")
    monkeypatch.setenv("TC_R2_PUBLIC_URL", "https://pub-abc.r2.dev/")
    assert rc.public_url("library/x") == "https://pub-abc.r2.dev/library/x"


def test_scans_for_a_bundle_shard():
    bundle = {"plan": {"kaggle": [{"shots": ["s001"]}], "github": [{"shots": ["s002", "s003"]}]},
              "scans": {"s001": ["boulder_01"], "s002": ["grass_medium_01"], "s003": ["grass_medium_01"]}}
    assert rc.bundle_shard_scans(bundle, "github", 0) == ["grass_medium_01"]
    assert rc.bundle_shard_scans(bundle, None, None) == ["boulder_01", "grass_medium_01"]


def test_built_plan_lists_each_heavy_asset_once():
    lib = {"cast": {"themistocles": {"name": "themistocles", "hair": "short"}},
           "sets": {"cove": {"name": "cove", "builder": "sets.cove"}}, "wardrobe": {}}
    recipes = [{"shot": "s001", "set": {"name": "cove", "builder": "sets.cove"}, "cast": [{"name": "themistocles"}]},
               {"shot": "s002", "set": {"name": "cove", "builder": "sets.cove"}, "cast": []}]
    plan = rc.built_plan(recipes, lib, code_for_kind=lambda kind: f"code of {kind}")
    assert [(p["kind"], p["name"]) for p in plan] == [("cast", "themistocles"), ("sets", "cove")]
    assert plan[0]["key"] == rc.built_key("cast", "themistocles", lib["cast"]["themistocles"], "code of cast")
    assert plan[1]["shots"] == ["s001", "s002"]


def test_code_closure_follows_helper_calls_across_modules():
    modules = {"sets": "def cove():\n    _shore()\n    scatter.rocks()\n\ndef _shore():\n    m = 'grass_medium_01'\n\ndef other():\n    x = 'kylix_cleveland'\n",
               "scatter": "def rocks():\n    load_scan('boulder_01')\n"}
    code = rc.code_closure("sets.cove", modules)
    assert rc.scans_in_code(code, INDEX) == ["boulder_01", "grass_medium_01"]     # not kylix: other() is never called


def test_cast_without_scan_list_uses_cast_code():
    lib = {"sets": {}, "cast": {"t": {}}, "wardrobe": {"chiton": {}}}
    recipe = {"shot": "s001", "set": None, "cast": [{"name": "t", "wardrobe": "chiton"}]}
    got = rc.needed_scans(recipe, lib, INDEX, code_for=lambda b: "", cast_code=lambda: "scan_cloth('grass_medium_01')")
    assert got == ["grass_medium_01"]

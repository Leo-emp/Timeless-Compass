import json

from tc import cast_tool


def test_promote_turns_a_generated_extra_into_a_named_library_character(tmp_path):
    spec = cast_tool.promote("hipparchus", role="commander", era="greece_480bc", seed=77, root=tmp_path,
                             who="Athenian trierarch (ship captain) at Salamis")
    saved = json.loads((tmp_path / "hipparchus.json").read_text(encoding="utf-8"))
    assert saved["name"] == "hipparchus" and saved["era"] == "greece_480bc" and saved["role"] == "commander"
    assert saved["who"].startswith("Athenian trierarch")
    assert saved["generated_from"] == {"role": "commander", "era": "greece_480bc", "seed": 77}
    assert saved == spec


def test_promoting_the_same_seed_twice_gives_the_same_face(tmp_path):
    a = cast_tool.promote("a", role="hoplite", era="greece_480bc", seed=5, root=tmp_path)
    b = cast_tool.promote("b", role="hoplite", era="greece_480bc", seed=5, root=tmp_path)
    assert a["face"] == b["face"] and a["macro"] == b["macro"]


def test_promote_refuses_to_overwrite_an_existing_character(tmp_path):
    cast_tool.promote("x", role="citizen", era="greece_480bc", seed=1, root=tmp_path)
    import pytest
    with pytest.raises(FileExistsError):
        cast_tool.promote("x", role="citizen", era="greece_480bc", seed=2, root=tmp_path)


def test_missing_lists_characters_a_job_needs_that_the_library_lacks(tmp_path):
    (tmp_path / "themistocles.json").write_text("{}", encoding="utf-8")
    needs = {"who": ["themistocles", "leonidas", "crowd:hoplite:40"]}
    assert cast_tool.missing(needs, root=tmp_path) == ["leonidas"]

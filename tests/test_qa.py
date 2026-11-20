# Tests for scored self-checks (`tc qa`): every item must pass AND the total must be >= 90/100 (spec 6.6, 6.14).
import pytest

from tc import qa


def _all(kind: str, pass_=True, frac=0.95) -> dict:
    return {item: {"pass": pass_, "score": round(w * frac), "note": "ok"} for item, w in qa.CHECKLISTS[kind].items()}


def test_every_checklist_sums_to_100():
    for kind, items in qa.CHECKLISTS.items():
        assert sum(items.values()) == 100, kind
    assert set(qa.CHECKLISTS) == {"story", "still", "motion", "thumbnail"}


def test_all_pass_high_total_passes():
    r = qa.score("still", _all("still", frac=1.0))
    assert r["passed"] and r["total"] == 100 and r["failing"] == []


def test_one_failing_item_fails_even_with_high_total():
    a = _all("still", frac=1.0); a["era_accuracy"]["pass"] = False
    r = qa.score("still", a)
    assert not r["passed"] and r["failing"] == ["era_accuracy"]


def test_total_below_90_fails():
    r = qa.score("story", _all("story", frac=0.88))
    assert r["total"] < 90 and not r["passed"]


def test_score_rejects_missing_item():
    a = _all("motion"); del a["no_snaps"]
    with pytest.raises(ValueError, match="no_snaps"):
        qa.score("motion", a)


def test_unknown_item_rejected():
    a = _all("thumbnail"); a["sparkle"] = {"pass": True, "score": 1, "note": ""}
    with pytest.raises(ValueError, match="sparkle"):
        qa.score("thumbnail", a)


def test_score_is_clamped_to_its_weight():
    a = _all("thumbnail", frac=1.0); a["emotion"]["score"] = 999
    assert qa.score("thumbnail", a)["total"] == 100


def test_record_counts_attempts_and_passed(tmp_path):
    bad = _all("still"); bad["acting"]["pass"] = False
    qa.record(tmp_path, "still", bad, subject="s01")
    assert not qa.passed(tmp_path, "still", "s01")
    r = qa.record(tmp_path, "still", _all("still"), subject="s01")
    assert r["attempts"] == 2 and qa.passed(tmp_path, "still", "s01")
    assert not qa.passed(tmp_path, "still", "s02")

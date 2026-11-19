import numpy as np

from tc import look


def _img(rgb, h=40, w=60):
    return np.full((h, w, 3), rgb, dtype=np.float32)


def test_stats_measure_brightness_contrast_and_saturation():
    flat_grey = look.stats(_img((0.5, 0.5, 0.5)))
    assert abs(flat_grey["brightness"] - 0.5) < 0.01
    assert flat_grey["contrast"] < 0.01 and flat_grey["saturation"] < 0.01
    half = _img((0.1, 0.1, 0.1)); half[:, 30:] = 0.9
    assert look.stats(half)["contrast"] > 0.5


def test_warmth_is_positive_for_orange_and_negative_for_blue():
    assert look.stats(_img((0.8, 0.5, 0.2)))["warmth"] > 0.2
    assert look.stats(_img((0.2, 0.4, 0.8)))["warmth"] < -0.2


def test_compare_reports_each_metric_as_ours_vs_reference_range():
    refs = [look.stats(_img((0.3, 0.25, 0.2))), look.stats(_img((0.4, 0.3, 0.2)))]
    report = look.compare(look.stats(_img((0.9, 0.9, 0.9))), refs)
    assert report["brightness"]["verdict"] == "too high"
    assert report["saturation"]["verdict"] == "too low"


def test_compare_accepts_values_inside_the_reference_spread():
    refs = [look.stats(_img((0.3, 0.25, 0.2))), look.stats(_img((0.4, 0.3, 0.2)))]
    report = look.compare(look.stats(_img((0.35, 0.28, 0.2))), refs)
    assert report["brightness"]["verdict"] == "ok"


def test_score_is_100_when_every_metric_is_inside_the_reference_range():
    refs = [look.stats(_img((0.3, 0.25, 0.2))), look.stats(_img((0.4, 0.3, 0.2)))]
    assert look.score(look.compare(look.stats(_img((0.35, 0.28, 0.2))), refs)) == 100
    assert look.score(look.compare(look.stats(_img((0.95, 0.95, 0.95))), refs)) < 60


def test_compare_uses_only_the_reference_frames_with_a_similar_mood():
    """A dusk shot is judged against dusk reference shots, not against night or noon shots too."""
    dusk = [look.stats(_img((0.42, 0.30, 0.20))), look.stats(_img((0.40, 0.28, 0.19))), look.stats(_img((0.44, 0.31, 0.21)))]
    night = [look.stats(_img((0.02, 0.03, 0.06)))] * 3
    noon = [look.stats(_img((0.85, 0.85, 0.9)))] * 3
    too_bright_dusk = look.stats(_img((0.62, 0.45, 0.30)))
    rep = look.compare(too_bright_dusk, dusk + night + noon, k=3)
    assert rep["brightness"]["verdict"] == "too high"

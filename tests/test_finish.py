from tc import finish


def test_filter_chain_has_grade_bloom_grain_and_vignette_in_film_order():
    f = finish.filter_graph(finish.LOOKS["dusk"])
    for part in ("curves=", "colorbalance=", "gblur=", "blend=all_mode=screen", "noise=", "vignette="):
        assert part in f, part
    # grade first, bloom on the graded image, grain last (grain must not be blurred by the bloom)
    assert f.index("colorbalance=") < f.index("gblur=") < f.index("noise=")


def test_strength_zero_turns_bloom_off():
    look = dict(finish.LOOKS["dusk"], bloom=0.0)
    assert "gblur" not in finish.filter_graph(look)


def test_every_named_look_builds():
    for name, look in finish.LOOKS.items():
        assert finish.filter_graph(look).startswith("[0:v]"), name


def test_cinematic_looks_exist_for_every_mood_of_a_history_film():
    for name in ("golden_hour", "cold_dawn", "firelight", "battle", "flashback"):
        assert name in finish.LOOKS, name
        assert finish.filter_graph(finish.LOOKS[name]).endswith("[out]"), name


def test_halation_glows_red_around_highlights_and_comes_before_grain():
    f = finish.filter_graph(dict(finish.LOOKS["dusk"], halation=0.3))
    assert "halation" in f or "colorchannelmixer" in f
    assert f.index("colorchannelmixer") < f.index("noise=")


def test_chromatic_aberration_and_anamorphic_streak_are_optional_layers():
    base = finish.filter_graph(finish.LOOKS["dusk"])
    assert "rgbashift" not in base and "gblur=sigma=60:sigmaV=0.5" not in base
    f = finish.filter_graph(dict(finish.LOOKS["dusk"], aberration=2, streak=0.25))
    assert "rgbashift" in f and "sigmaV=" in f


def test_bleach_bypass_battle_look_is_desaturated_and_contrasty():
    b = finish.LOOKS["battle"]
    assert b["sat"] < 0.85 and b.get("bleach", 0) > 0

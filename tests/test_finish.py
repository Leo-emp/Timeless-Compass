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

# WS19 parchment maps: the 2D painter (tc/maps). Blender half is checked by renders (spike/lib_stills/maps).
import numpy as np
import pytest

from tc.maps import geo, labels, raster as R, spec, territory as T


def test_projection_round_trips_and_north_is_up():
    v = geo.View(20, 30, 50, 46, width=3000)
    for lon, lat in [(20, 46), (35.5, 38.2), (50, 30)]:
        x, y = v.px(lon, lat)
        lo, la = v.lonlat(x, y)
        assert abs(lo - lon) < 1e-9 and abs(la - lat) < 1e-9
    assert v.px(20, 46) == (0.0, 0.0)                    # north-west corner = top-left pixel
    assert v.px(30, 31)[1] > v.px(30, 45)[1]             # further south = lower on the image


def test_16x9_view_has_film_aspect():
    v = geo.view_16x9(32, 38, 30, width=1600)
    assert abs(v.width / v.height - 16 / 9) < 0.01


def test_noise_is_smooth_and_in_range_at_any_cell_size():
    rng = np.random.default_rng(0)
    for cell in (3, 20, 300):
        n = R.value_noise(90, 160, cell, rng)
        assert n.shape == (90, 160) and n.min() >= 0 and n.max() <= 1
    big = R.fbm(120, 200, 80, 3, rng)
    assert np.abs(np.diff(big, axis=1)).mean() < 0.05    # neighbouring pixels close in value: smooth blobs


def test_each_piece_of_land_belongs_to_one_realm_last_wins():
    a = np.zeros((10, 10), np.float32); a[:, :6] = 1
    b = np.zeros((10, 10), np.float32); b[:, 4:] = 1
    ea, eb = T.exclusive([a, b])
    assert (ea + eb).max() <= 1.0
    assert eb[:, 4:6].min() == 1 and ea[:, 4:6].max() == 0


def test_grow_map_starts_at_the_heart_and_spreads_outward():
    v = geo.View(0, 0, 10, 10, width=200)
    m = np.zeros((v.height, v.width), np.float32); m[20:180, 20:180] = 1
    g = T.grow_map(v, m, (5, 5), np.random.default_rng(1))
    cy, cx = int(v.px(5, 5)[1]), int(v.px(5, 5)[0])
    assert g[cy, cx] < 0.3                               # the capital colours first
    assert g[25, 25] > g[cy, cx]                         # the far corner later
    assert g[5, 5] == 1.0                                # outside the realm: never shown


def test_curved_label_bends_and_region_label_has_outline_and_shadow():
    f = labels.font("Cinzel.ttf", 40)
    flat = labels.curved_text("EMPIRE", f, 0)
    bent = labels.curved_text("EMPIRE", f, 30)
    assert bent.height > flat.height                     # a curved line needs more height
    im = labels.region_label(["Byzantine", "Empire"], 40)
    a = np.asarray(im)[..., 3]
    assert a.max() == 255 and (a == 0).any()             # opaque letters on a transparent tile


def test_place_tag_has_icon_above_scroll():
    tag = labels.place_tag("Nicaea", 20, "city", seed=3)
    scroll = labels.scroll("Nicaea", 20)
    assert tag.height > scroll.height and tag.width >= scroll.width


def test_spec_checks_catch_bad_specs():
    good = {"view": {"center": [30, 38], "span_lon": 20},
            "territories": [{"id": "byz", "border": [[20, 40], [25, 42], [26, 38]]}],
            "beats": [{"t": 0, "do": "grow", "id": "byz"}]}
    assert spec.problems(good) == []
    bad = {"view": {}, "territories": [{"id": "x", "border": [[200, 10]]}],
           "places": [{"text": "Rome", "at": [12.5, 41.9], "icon": "castle"}],
           "beats": [{"t": 1, "do": "explode", "id": "x"}, {"do": "grow", "id": "nope"}]}
    errs = " | ".join(spec.problems(bad))
    for part in ("view needs", "border needs", "icon must be", "do must be", "unknown id nope", "t (seconds)"):
        assert part in errs, part


def test_map_shot_needs_no_cast_but_valid_beats():
    from tc.shots import Shot, map_shot_problems
    ok = Shot.from_dict({"id": "s1", "line": 1, "dur": 6, "who": [], "where": "map", "action": "", "expression": {},
                         "camera": {"move": "push_in"}, "era": "crusade_1097",
                         "map": {"spec": "maps/anatolia.json", "beats": [{"t": 1, "do": "grow", "id": "rum"}]}})
    assert map_shot_problems(ok) == []
    bad = Shot.from_dict({"id": "s2", "line": 1, "dur": 6, "who": [], "where": "map", "action": "", "expression": {},
                          "camera": {"move": "push_in"}, "era": "",
                          "map": {"beats": [{"t": 9, "do": "explode"}]}})
    errs = " | ".join(map_shot_problems(bad))
    assert "map.spec" in errs and "must be one of" in errs and "inside the shot" in errs and "era" in errs

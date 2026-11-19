from tc import crowd

GR = "greece_480bc"


def test_same_seed_gives_the_same_person():
    assert crowd.person(42, "citizen", GR) == crowd.person(42, "citizen", GR)


def test_different_seeds_give_different_people():
    assert crowd.distance(crowd.person(1, "citizen", GR), crowd.person(2, "citizen", GR)) > 0.15


def test_people_have_everything_the_3d_builder_needs():
    p = crowd.person(7, "citizen", GR)
    for key in ("role", "era", "macro", "skin", "face", "hair", "wardrobe", "dye", "motion"):
        assert key in p, key
    assert set(p["macro"]) >= {"gender", "age", "muscle", "weight", "height", "race"}


def test_roles_set_gender_and_age():
    queens = [crowd.person(s, "queen", GR) for s in range(10)]
    assert all(q["macro"]["gender"] < 0.2 for q in queens)
    kids = [crowd.person(s, "child", GR) for s in range(10)]
    assert all(k["macro"]["age"] < 0.3 and not k.get("beard") for k in kids)


def test_old_men_go_grey_and_youths_have_little_or_no_beard():
    old = [crowd.person(s, "citizen", GR, age=0.95) for s in range(20)]
    assert sum(p["hair"]["grey"] for p in old) / 20 > 0.4
    young = [crowd.person(s, "citizen", GR, age=0.1) for s in range(20)]
    assert all((p.get("beard") or {}).get("length", 0) < 0.012 for p in young)


def test_rank_shows_in_dyes_kings_wear_costly_colours_servants_undyed():
    king = crowd.person(3, "king", GR); servant = crowd.person(3, "servant", GR)
    assert king["dye"]["rank"] == "royal" and servant["dye"]["rank"] == "poor"
    assert servant["dye"]["grime"] > king["dye"]["grime"]


def test_soldiers_get_armour_and_a_unique_shield_emblem():
    s = [crowd.person(i, "hoplite", GR) for i in range(12)]
    assert all(p["wardrobe"] == "greek_hoplite_480bc" for p in s)
    assert len({p["shield"]["emblem"] for p in s}) >= 6


def test_cast_has_no_lookalikes_and_skips_faces_used_in_earlier_videos():
    people = crowd.cast(30, "citizen", GR, seed=5)
    assert len(people) == 30
    for i in range(30):
        for j in range(i + 1, 30):
            assert crowd.distance(people[i], people[j]) >= crowd.MIN_DISTANCE
    again = crowd.cast(10, "citizen", GR, seed=5, used_seeds={p["seed"] for p in people})
    assert not {p["seed"] for p in again} & {p["seed"] for p in people}


def test_era_changes_the_people_persians_differ_from_greeks():
    g = [crowd.person(s, "citizen", GR) for s in range(30)]
    p = [crowd.person(s, "soldier", "persia_480bc") for s in range(30)]
    assert all(x["wardrobe"].startswith("persian") for x in p)
    assert sum(x["macro"]["race"]["asian"] for x in p) > sum(x["macro"]["race"]["asian"] for x in g)
    assert sum((x.get("beard") or {}).get("length", 0) for x in p) > sum((x.get("beard") or {}).get("length", 0) for x in g)


def test_unknown_role_for_an_era_is_a_clear_error():
    import pytest
    with pytest.raises(KeyError):
        crowd.person(1, "pharaoh", GR)


def test_1950s_people_wear_modern_clothes_and_are_clean_shaven():
    sci = [crowd.person(s, "scientist", "usa_1950s") for s in range(12)]
    assert all(p.get("mpfb_clothes") for p in sci)
    assert sum(1 for p in sci if p.get("beard")) <= 2           # 1950s men: almost all clean-shaven
    sov = crowd.person(3, "official", "ussr_1950s")
    assert sov["mpfb_clothes"] and sov["era"] == "ussr_1950s"
    sec = [crowd.person(s, "secretary", "usa_1950s") for s in range(5)]
    assert all(p["macro"]["gender"] < 0.5 for p in sec)


def test_rome_and_egypt_eras_have_their_own_people():
    rom = [crowd.person(s, "legionary", "rome_100bc") for s in range(10)]
    assert all(not p.get("beard") for p in rom)                    # Republican Romans: clean-shaven
    egy = [crowd.person(s, "priest", "egypt_1250bc") for s in range(10)]
    assert all(p["hair"]["length"] < 0.004 for p in egy)           # Egyptian priests shaved their heads
    pharaoh = crowd.person(1, "pharaoh", "egypt_1250bc")
    assert pharaoh["rank"] == "royal"
    afr_g = sum(crowd.person(s, "citizen", "greece_480bc")["macro"]["race"]["african"] for s in range(20))
    afr_e = sum(crowd.person(s, "worker", "egypt_1250bc")["macro"]["race"]["african"] for s in range(20))
    assert afr_e > afr_g


def test_spartans_have_long_hair_beards_crimson_cloaks_and_mostly_personal_emblems():
    sp = [crowd.person(s, "spartan", "greece_480bc") for s in range(20)]
    assert all(p["hair"]["length"] > 0.1 for p in sp)                 # long, combed hair (Herodotus 7.208)
    assert all(p.get("beard") for p in sp)
    assert all(p["cloak"] == "crimson" for p in sp)                    # phoinikis (Xenophon, Lac. 11.3)
    assert all(p["wardrobe"] == "greek_hoplite_480bc" for p in sp)
    lambdas = sum(1 for p in sp if p["shield"]["emblem"] == "lambda")
    assert 0 < lambdas < 10                                            # uniform lambda came later (~420s BC)

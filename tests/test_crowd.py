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


def test_working_people_of_480bc_have_their_own_roles_and_clothes():
    # farmers, shepherds, fishermen, potters, smiths wear work clothes (exomis) and are poor or common;
    # traders and villagers wear the citizen's chiton; Persian traders/farmers wear the Median dress
    from tc import crowd
    work = {"farmer", "shepherd", "potter", "smith", "fisherman", "rower"}
    for role in work:
        p = crowd.person(3, role, "greece_480bc")
        assert p["role"] == role and p["wardrobe"] == "greek_servant_480bc"
        assert p["rank"] in ("poor", "common")
    for role in ("trader", "villager"):
        p = crowd.person(4, role, "greece_480bc")
        assert p["wardrobe"] in ("greek_civilian_480bc", "greek_woman_480bc")
    assert crowd.person(5, "trader", "persia_480bc")["wardrobe"] == "persian_court_480bc"
    assert crowd.person(6, "farmer", "persia_480bc")["wardrobe"] == "persian_servant_480bc"


# ---- WS17 modern era (Session F): Manhattan Project 1945, Cold War USA 1960, USSR 1960 -------------------------
MODERN_ROLES = ("scientist", "general", "soldier", "agent", "secretary", "test_subject", "journalist", "worker")


def test_new_modern_eras_have_every_secret_project_role():
    for era in ("usa_1945", "usa_1960", "ussr_1960"):
        for role in MODERN_ROLES:
            p = crowd.person(1, role, era)
            assert p["era"] == era and p["mpfb_clothes"], (era, role)   # dressed in MakeHuman's modern clothes
            assert p["wardrobe"] is None                               # never the ancient wardrobe


def test_modern_men_are_clean_shaven_with_short_hair():
    for era in ("usa_1945", "usa_1960", "ussr_1960"):
        ppl = [crowd.person(s, r, era) for s in range(10) for r in ("scientist", "soldier", "agent")]
        men = [p for p in ppl if p["macro"]["gender"] > 0.5]       # women scientists too (Leona Woods, 1942 pile)
        assert sum(1 for p in men if p.get("beard")) <= 3, era
        assert all(p["hair"]["length"] <= 0.02 for p in men), era   # short back-and-sides / crew cuts


def test_scientists_and_doctors_wear_lab_coats_and_test_subjects_hospital_gowns():
    sci = [crowd.person(s, "scientist", "usa_1945") for s in range(20)]
    assert sum(1 for p in sci if "lab_coat" in p["overlays"]) >= 10   # most, not all (some in a suit at a desk)
    doc = [crowd.person(s, "doctor", "usa_1960") for s in range(8)]
    assert all("lab_coat" in p["overlays"] for p in doc)
    sub = [crowd.person(s, "test_subject", "usa_1960") for s in range(8)]
    assert all("hospital_gown" in p["overlays"] for p in sub)


def test_soldiers_wear_their_armys_uniform_and_cap():
    us = crowd.person(2, "soldier", "usa_1945"); su = crowd.person(2, "soldier", "ussr_1960")
    assert any(o.startswith("cap_") for o in us["overlays"]) and any(o.startswith("cap_") for o in su["overlays"])
    assert us["overlays"] != su["overlays"] or us["mpfb_clothes"] != su["mpfb_clothes"]
    gen = crowd.person(4, "general", "usa_1945")
    assert "cap_peaked" in gen["overlays"]


def test_more_men_wear_hats_in_1945_than_in_1960():
    def hats(era):
        ps = [crowd.person(s, r, era) for s in range(30) for r in ("agent", "journalist")]
        return sum(1 for p in ps for c in p["mpfb_clothes"] if c[0].startswith("fedora"))
    assert hats("usa_1945") > hats("usa_1960")


def test_modern_extras_never_look_alike():
    ppl = crowd.cast(8, "agent", "usa_1960", seed=5)
    assert len(ppl) == 8
    assert all(crowd.distance(a, b) >= crowd.MIN_DISTANCE for i, a in enumerate(ppl) for b in ppl[i + 1:])


def test_old_1950s_eras_are_unchanged_by_the_new_ones():
    p = crowd.person(3, "scientist", "usa_1950s")
    assert p["mpfb_clothes"] and "overlays" not in p


def test_modern_clothes_match_the_persons_sex_and_the_period():
    for era in ("usa_1945", "usa_1960", "ussr_1960"):
        for role in MODERN_ROLES + ("doctor", "nurse"):
            for s in range(8):
                p = crowd.person(s, role, era)
                names = [c[0] for c in p["mpfb_clothes"]]
                male = p["macro"]["gender"] > 0.5
                assert all(not n.startswith("female_") for n in names) if male else \
                    all(not n.startswith("male_") for n in names), (era, role, names)
                assert not any(n in ("female_casualsuit02", "female_sportsuit01") for n in names)   # shorts / crop top
    sol = crowd.person(1, "soldier", "usa_1945")
    assert sol["mpfb_clothes"][0][0] == "male_casualsuit05"              # field jacket, not overalls


def test_modern_adults_are_adults():
    # MakeHuman age: 0.1875 = 11 y, 0.5 = 25 y (linear between), 1.0 = 90 y  ->  18 y ~ 0.344
    for era in ("usa_1945", "usa_1960", "ussr_1960"):
        for role in MODERN_ROLES + ("doctor", "nurse"):
            ages = [crowd.person(s, role, era)["macro"]["age"] for s in range(20)]
            assert min(ages) >= 0.36, (era, role, min(ages))
    assert min(crowd.person(s, "general", "usa_1945")["macro"]["age"] for s in range(20)) >= 0.6   # 40+

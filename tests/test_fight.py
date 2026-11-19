from tc import fight


def _by(beats, who):
    return [b for b in beats if b["fighter"] == who]


def test_every_blocked_attack_has_the_guard_up_before_the_blow_lands():
    beats = fight.choreograph(seed=3, exchanges=5, winner="A")
    for b in beats:
        if b["kind"] == "attack" and b.get("answer"):
            ans = b["answer"]
            assert ans["start"] < b["impact"] <= ans["start"] + fight.CLIPS[ans["clip"]]["length"]


def test_the_loser_dies_on_the_winners_last_blow():
    beats = fight.choreograph(seed=4, exchanges=4, winner="B")
    last_attack = [b for b in _by(beats, "B") if b["kind"] == "attack"][-1]
    death = _by(beats, "A")[-1]
    assert death["kind"] == "death"
    assert abs(death["start"] - last_attack["impact"]) <= 2


def test_a_fighter_never_does_two_things_at_once():
    beats = fight.choreograph(seed=5, exchanges=6, winner="A")
    for who in "AB":
        mine = sorted(_by(beats, who), key=lambda b: b["start"])
        for a, b in zip(mine, mine[1:]):
            assert a["start"] + fight.CLIPS[a["clip"]]["length"] + fight.BLEND <= b["start"]


def test_attacks_vary_and_seeds_differ():
    beats = fight.choreograph(seed=6, exchanges=6, winner="A")
    atk = [b["clip"] for b in _by(beats, "A") if b["kind"] == "attack"]
    assert all(x != y for x, y in zip(atk, atk[1:]))
    assert fight.choreograph(seed=1, exchanges=4) != fight.choreograph(seed=2, exchanges=4)
    assert fight.choreograph(seed=1, exchanges=4) == fight.choreograph(seed=1, exchanges=4)


def test_spear_fighters_thrust_and_sword_fighters_cut():
    spear = fight.choreograph(seed=7, exchanges=4, weapons={"A": "spear", "B": "spear"})
    assert all(fight.CLIPS[b["clip"]]["weapon"] in ("spear", "any") for b in spear if b["kind"] == "attack")
    sword = fight.choreograph(seed=7, exchanges=4, weapons={"A": "sword", "B": "sword"})
    assert all(fight.CLIPS[b["clip"]]["weapon"] in ("sword", "any") for b in sword if b["kind"] == "attack")


def test_melee_pairs_start_out_of_step():
    pairs = fight.melee(8, seed=2, frames=240)
    starts = {p["beats"][0]["start"] for p in pairs}
    assert len(pairs) == 8 and len(starts) > 4
    assert all(b["start"] < 240 for p in pairs for b in p["beats"])

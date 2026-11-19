# FIGHT CHOREOGRAPHY (pure Python, no Blender): plans a duel between fighter A and fighter B as timed "beats" -
# who plays which Mixamo clip from which frame - the way a stunt coordinator plans one for film:
#   attack -> the other fighter's guard comes up BEFORE the blow lands (block / parry / shield impact)
#   ... exchanges trade back and forth (sometimes the same man presses twice) ...
#   the final blow is NOT blocked: the loser takes it and dies on the impact frame.
# blender/lib/fight.py then plays the beats on two rigs, face to face. melee() makes many such pairs for the
# background of a battle, each starting at a different moment so the crowd never moves in step.
# Clip timings: 'length' and 'impact' are scene frames (Mixamo 30 fps played 1:1 at 24 fps, a little weightier);
# the impact frame is the moment the weapon hand is fastest - measured by blender/scenes/fight_test.py, which prints
# the measured value for every clip so this table can be corrected.
import random

BLEND = 4          # frames between two clips: Blender's curve eases one clip into the next

CLIPS = {
    # attacks
    "sword_and_shield_slash":           {"kind": "attack", "weapon": "sword", "length": 40, "impact": 18},
    "sword_and_shield_attack":          {"kind": "attack", "weapon": "sword", "length": 44, "impact": 20},
    "standing_melee_attack_downward":   {"kind": "attack", "weapon": "sword", "length": 50, "impact": 24},
    "standing_melee_attack_horizontal": {"kind": "attack", "weapon": "sword", "length": 44, "impact": 20},
    "great_sword_slash":                {"kind": "attack", "weapon": "sword", "length": 52, "impact": 24},
    "stabbing":                         {"kind": "attack", "weapon": "spear", "length": 46, "impact": 22},
    "sword_and_shield_kick":            {"kind": "attack", "weapon": "any",   "length": 40, "impact": 16},
    # guards (lead = frames from the clip start until the guard is up)
    "sword_and_shield_block":           {"kind": "block", "weapon": "any", "length": 34, "lead": 8},
    "great_sword_blocking":             {"kind": "block", "weapon": "sword", "length": 36, "lead": 8},
    "sword_and_shield_impact":          {"kind": "block", "weapon": "any", "length": 30, "lead": 5},
    "standing_block_react_large":       {"kind": "block", "weapon": "any", "length": 40, "lead": 6},
    # hits that do not kill
    "getting_hit":                      {"kind": "hit", "weapon": "any", "length": 30, "lead": 2},
    "hit_reaction":                     {"kind": "hit", "weapon": "any", "length": 30, "lead": 2},
    "stunned":                          {"kind": "hit", "weapon": "any", "length": 60, "lead": 2},
    # deaths
    "sword_and_shield_death":           {"kind": "death", "weapon": "any", "length": 70, "lead": 1},
    "falling_back_death":               {"kind": "death", "weapon": "any", "length": 70, "lead": 1},
    "dying":                            {"kind": "death", "weapon": "any", "length": 90, "lead": 1},
    "death_from_the_front":             {"kind": "death", "weapon": "any", "length": 70, "lead": 1},
}


def _pick(rnd, kind, weapon, avoid=None):
    pool = [c for c, m in CLIPS.items() if m["kind"] == kind and m["weapon"] in (weapon, "any") and c != avoid]
    return rnd.choice(sorted(pool))


def choreograph(seed=0, exchanges=4, winner="A", weapons=None, start=1, hit_chance=0.2):
    """Plan a duel. Returns beats sorted by start: {'fighter', 'clip', 'kind', 'start'} (+ 'impact' and 'answer' -
    the defender's beat - on attacks). The loser's last beat is a death that starts on the winning blow's impact."""
    rnd = random.Random(seed)
    weapons = weapons or {"A": "sword", "B": "sword"}
    loser = "B" if winner == "A" else "A"
    free = {"A": start, "B": start}            # first frame each fighter is free again
    last_attack = {"A": None, "B": None}
    beats = []
    attacker = rnd.choice("AB")
    for i in range(exchanges):
        final = i == exchanges - 1
        if final:
            attacker = winner
        defender = "B" if attacker == "A" else "A"
        clip = _pick(rnd, "attack", weapons[attacker], avoid=last_attack[attacker])
        last_attack[attacker] = clip
        m = CLIPS[clip]
        if final:
            ans_clip = _pick(rnd, "death", "any")
        else:
            ans_clip = _pick(rnd, "hit" if rnd.random() < hit_chance else "block", weapons[defender])
        lead = CLIPS[ans_clip]["lead"]
        # earliest start that leaves both men free: attacker from his free frame, defender's answer `lead` before impact
        a_start = max(free[attacker], free[defender] + lead - m["impact"] + 1)
        impact = a_start + m["impact"]
        d_start = impact - lead
        ans = {"fighter": defender, "clip": ans_clip, "kind": CLIPS[ans_clip]["kind"], "start": d_start}
        beats.append({"fighter": attacker, "clip": clip, "kind": "attack", "start": a_start, "impact": impact,
                      "answer": ans})
        beats.append(ans)
        free[attacker] = a_start + m["length"] + BLEND
        free[defender] = d_start + CLIPS[ans_clip]["length"] + BLEND
        # who presses next: usually the defender answers back, sometimes the attacker presses again
        attacker = defender if rnd.random() < 0.7 else attacker
    return sorted(beats, key=lambda b: (b["start"], b["fighter"]))


def melee(pairs, seed=0, frames=240, weapons=None):
    """Background battle: `pairs` duels, each with its own seed, length and winner, starting out of step."""
    rnd = random.Random(seed)
    out = []
    for k in range(pairs):
        offset = rnd.randint(1, max(2, frames // 3))
        beats = choreograph(seed=seed * 1000 + k, exchanges=rnd.randint(2, 5), winner=rnd.choice("AB"),
                            weapons=weapons, start=offset)
        out.append({"pair": k, "beats": [b for b in beats if b["start"] < frames]})
    return out

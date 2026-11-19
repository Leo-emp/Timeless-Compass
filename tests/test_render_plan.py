# Tests for the render farm planner: split shots across Kaggle GPU sessions and GitHub CPU runners.
from tc.render_plan import estimate_cost, plan_shards


def shot(i, dur, who):
    return {"id": f"s{i:03d}", "dur": dur, "who": who}


def test_cost_grows_with_frames_and_characters():
    assert estimate_cost(shot(1, 4.0, [])) < estimate_cost(shot(2, 4.0, ["a"])) < estimate_cost(shot(3, 4.0, ["a", "b"]))
    assert estimate_cost(shot(4, 8.0, ["a"])) == 2 * estimate_cost(shot(5, 4.0, ["a"]))


def test_every_shot_assigned_exactly_once():
    shots = [shot(i, 3 + i % 4, ["a"] * (i % 3)) for i in range(40)]
    plan = plan_shards(shots, gpu_shards=2, cpu_shards=5)
    ids = [s for group in plan["kaggle"] + plan["github"] for s in group["shots"]]
    assert sorted(ids) == sorted(s["id"] for s in shots)


def test_character_shots_go_to_gpu_landscapes_to_cpu():
    shots = [shot(1, 4, ["themistocles"]), shot(2, 4, []), shot(3, 5, ["xerxes"]), shot(4, 6, [])]
    plan = plan_shards(shots, gpu_shards=1, cpu_shards=1)
    assert plan["kaggle"][0]["shots"] == ["s001", "s003"] or set(plan["kaggle"][0]["shots"]) == {"s001", "s003"}
    assert set(plan["github"][0]["shots"]) == {"s002", "s004"}


def test_shards_are_balanced():
    shots = [shot(i, 4.0, ["a"]) for i in range(20)]
    plan = plan_shards(shots, gpu_shards=4, cpu_shards=0)
    loads = [g["cost"] for g in plan["kaggle"]]
    assert max(loads) - min(loads) <= estimate_cost(shot(0, 4.0, ["a"]))


def test_no_cpu_shards_sends_everything_to_gpu():
    plan = plan_shards([shot(1, 4, []), shot(2, 4, ["a"])], gpu_shards=1, cpu_shards=0)
    assert set(plan["kaggle"][0]["shots"]) == {"s001", "s002"} and plan["github"] == []

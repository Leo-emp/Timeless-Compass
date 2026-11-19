# Tests for WS9 task 4 (speed): every shot gets a TYPE (landscape / wide / medium / closeup), and the type picks the
# render engine (Eevee for wide + landscape, Cycles + OpenImageDenoise for faces), the sample count, and a time estimate.
from tc.render_plan import (ENGINE_FOR, SAMPLES, estimate_seconds, plan_shards, render_settings_for, shot_type,
                            speed_table)


def shot(i, who=(), lens=None, dist=None, dur=4.0, card=None):
    cam = {}
    if lens is not None:
        cam["lens"] = lens
    if dist is not None:
        cam["dist"] = dist
    return {"id": f"s{i:03d}", "dur": dur, "who": list(who), "camera": cam, "card": card}


def test_shot_types():
    assert shot_type(shot(1)) == "landscape"                         # nobody on screen
    assert shot_type(shot(2, ["a"], lens=24)) == "wide"              # short lens = wide
    assert shot_type(shot(3, ["a"], dist=12)) == "wide"              # far camera = wide
    assert shot_type(shot(4, ["a"], lens=85)) == "closeup"           # long lens = close-up
    assert shot_type(shot(5, ["a"], dist=1.2)) == "closeup"          # camera near the face
    assert shot_type(shot(6, ["a"])) == "medium"                     # defaults (40 mm, 3.6 m)
    assert shot_type(shot(7, card={"kind": "map_label"})) == "card"  # a map / place card


def test_eevee_for_wide_and_landscape_cycles_for_faces():
    assert ENGINE_FOR["landscape"] == ENGINE_FOR["wide"] == "EEVEE"
    assert ENGINE_FOR["closeup"] == ENGINE_FOR["medium"] == "CYCLES"
    s = render_settings_for(shot(4, ["a"], lens=85))
    assert s["engine"] == "CYCLES" and s["denoiser"] == "OPENIMAGEDENOISE"
    assert s["samples"] == SAMPLES["closeup"] and s["samples"] <= 128     # denoiser lets us use far fewer samples


def test_estimate_grows_with_frames_and_is_faster_on_gpu():
    a, b = shot(1, ["a"], dur=4.0), shot(2, ["a"], dur=8.0)
    assert estimate_seconds(b, "kaggle") == 2 * estimate_seconds(a, "kaggle")
    assert estimate_seconds(a, "kaggle") < estimate_seconds(a, "github")


def test_speed_table_shows_saving_for_every_type():
    rows = {r["type"]: r for r in speed_table()}
    assert set(rows) >= {"landscape", "wide", "medium", "closeup"}
    for r in rows.values():
        assert r["new_s_per_frame"] < r["old_s_per_frame"] and 0 < r["saved_pct"] < 100


def test_plan_carries_settings_and_hours():
    shots = [shot(1), shot(2, ["a"], lens=85), shot(3, ["a"], lens=24)]
    plan = plan_shards(shots, gpu_shards=1, cpu_shards=1)
    assert set(plan["settings"]) == {"s001", "s002", "s003"}
    assert plan["settings"]["s001"]["engine"] == "EEVEE"
    assert all("hours" in g for g in plan["kaggle"] + plan["github"])

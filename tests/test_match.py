import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image

from tc import match


def _img(path, gain=1.0, cast=(1.0, 1.0, 1.0), sat=1.0):
    """A test frame: a warm gradient + a coloured 'figure', scaled by exposure gain and a colour cast."""
    h, w = 90, 160
    y, x = np.mgrid[0:h, 0:w] / np.array([h, w])[:, None, None]
    base = np.stack([0.25 + 0.6 * x, 0.2 + 0.5 * x, 0.15 + 0.35 * x], -1)
    base[30:70, 60:100] = (0.55, 0.25, 0.35)
    grey = base.mean(-1, keepdims=True)
    base = grey + (base - grey) * sat
    img = np.clip(base * gain * np.array(cast), 0, 1)
    Image.fromarray((img * 255).astype(np.uint8)).save(path)
    return path


def test_stats_measure_exposure_and_colour_cast(tmp_path):
    a = match.stats(_img(tmp_path / "a.png"))
    b = match.stats(_img(tmp_path / "b.png", gain=0.6, cast=(0.9, 1.0, 1.15)))
    assert b["median"] < a["median"]
    assert b["cast"][2] > a["cast"][2] and b["cast"][0] < a["cast"][0]          # bluer, less red


def test_correction_brightens_a_dark_shot_and_removes_its_cast(tmp_path):
    ref = match.stats(_img(tmp_path / "ref.png"))
    src = match.stats(_img(tmp_path / "src.png", gain=0.7, cast=(0.92, 1.0, 1.12)))
    c = match.correction(src, ref)
    assert c["stops"] > 0.2
    assert c["gains"][0] > 1.0 and c["gains"][2] < 1.0


def test_corrections_are_clamped_so_moods_survive(tmp_path):
    ref = match.stats(_img(tmp_path / "ref.png"))
    src = match.stats(_img(tmp_path / "night.png", gain=0.15, cast=(0.6, 0.8, 1.6)))
    c = match.correction(src, ref)
    assert c["stops"] <= match.MAX_STOPS + 1e-9
    assert all(1 - match.MAX_CAST <= g <= 1 + match.MAX_CAST for g in c["gains"])


def test_hero_per_place_and_only_same_place_shots_are_matched():
    shots = [{"id": "a", "dur": 3, "where": "cove"}, {"id": "b", "dur": 6, "where": "cove"},
             {"id": "c", "dur": 4, "where": "palace", "hero": True}, {"id": "d", "dur": 8, "where": "palace"}]
    heroes = match.heroes(shots)
    assert heroes == {"cove": "b", "palace": "c"}           # longest shot, unless one is marked hero


def test_filter_is_identity_for_a_perfect_match(tmp_path):
    s = match.stats(_img(tmp_path / "x.png"))
    assert match.filter_for(match.correction(s, s)) == ""


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_applying_the_filter_really_brings_the_shot_close_to_the_hero(tmp_path):
    ref_p = _img(tmp_path / "ref.png")
    src_p = _img(tmp_path / "src.png", gain=0.7, cast=(0.92, 1.0, 1.12))
    ref, src = match.stats(ref_p), match.stats(src_p)
    f = match.filter_for(match.correction(src, ref))
    out = tmp_path / "fixed.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src_p), "-vf", f"format=gbrp,{f},format=rgb24", str(out)], check=True)
    fixed = match.stats(out)
    assert abs(fixed["median"] - ref["median"]) < abs(src["median"] - ref["median"]) * 0.4
    assert np.abs(np.array(fixed["cast"]) - ref["cast"]).sum() < np.abs(np.array(src["cast"]) - ref["cast"]).sum() * 0.5

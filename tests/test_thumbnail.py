# Tests for the thumbnail system (the parts that need no Blender): plan 3 variants, check them, and
# finish a rendered frame into a 1280x720 YouTube thumbnail + a "does it read on a phone?" check.
import json

import numpy as np
import pytest
from PIL import Image

from tc import jobs, paths, thumbnail
from tc.script import parse_script

SCRIPT = ('## hook\nOne king watched. [src: f]\n## build\nXERXES: "Write every name." [dramatised]\n'
          '## payoff\nHe tore his robes. [src: f]\n')


def plan3():
    return thumbnail.plan_variants(["XERXES"], ["golden throne", "burning Phoenician ship", "scribe's wax tablet"],
                                   set_name="salamis_strait_dusk")


def test_plan_has_three_different_variants():
    p = plan3()
    assert [v["id"] for v in p] == ["A", "B", "C"]
    assert len({v["emotion"] for v in p}) == 3                    # three different emotions to test
    assert len({v["palette"] for v in p}) == 3
    assert {v["face_side"] for v in p} == {"left", "right"}        # not all the same layout
    assert all(v["face"] == "XERXES" and v["era_detail"] for v in p)


def test_plan_uses_close_up_lens():
    v = plan3()[0]
    assert v["camera"]["lens_mm"] >= 85 and v["face_frac"] >= thumbnail.MIN_FACE_FRAC


def test_good_plan_passes_check():
    assert thumbnail.check_plan(plan3()) == []


def test_check_needs_three_variants():
    assert any("3 variants" in p for p in thumbnail.check_plan(plan3()[:2]))


def test_check_same_emotion_twice():
    p = plan3(); p[1]["emotion"] = p[0]["emotion"]
    assert any("emotion" in x for x in thumbnail.check_plan(p))


def test_check_unknown_emotion():
    p = plan3(); p[0]["emotion"] = "happy"
    assert any("unknown emotion" in x for x in thumbnail.check_plan(p))


def test_check_small_face():
    p = plan3(); p[0]["face_frac"] = 0.1
    assert any("face" in x and "small" in x for x in thumbnail.check_plan(p))


def test_check_too_many_words():
    p = plan3(); p[0]["words"] = "THE KING WHO LOST"
    assert any("words" in x for x in thumbnail.check_plan(p))


def test_check_needs_era_detail():
    p = plan3(); p[2]["era_detail"] = ""
    assert any("era detail" in x for x in thumbnail.check_plan(p))


def test_faces_from_script_speakers():
    assert thumbnail.faces_from_script(parse_script(SCRIPT)) == ["XERXES"]


def test_render_request_is_a_blender_job_spec():
    r = thumbnail.render_request("job1", plan3()[0], out_dir=paths.JOBS / "job1" / "thumbs")
    assert r["resolution"] == [1920, 1080] and r["expression"] == plan3()[0]["emotion"]
    assert r["output"].endswith("render_A.png") and r["camera"]["lens_mm"] >= 85


# ---------------- finishing a render (Pillow only) ----------------
def _fake_render(path, w=1920, h=1080, contrast=True):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    if contrast:
        img[:, : w // 2] = (230, 170, 110)        # bright warm face side, dark other side
        img[:, w // 2:] = (12, 10, 18)
    else:
        img[:] = (110, 105, 100)                  # flat grey: will not read on a phone
    Image.fromarray(img).save(path)
    return path


def test_finish_makes_1280x720_jpg(tmp_path):
    out = thumbnail.finish(_fake_render(tmp_path / "r.png"), tmp_path / "t.jpg", plan3()[0])
    im = Image.open(out)
    assert im.size == (1280, 720) and im.format == "JPEG"
    assert out.stat().st_size < 2 * 1024 * 1024                    # YouTube thumbnail limit is 2 MB


def test_finish_with_words(tmp_path):
    v = plan3()[0]; v["words"] = "HIS OWN SHIPS"
    out = thumbnail.finish(_fake_render(tmp_path / "r.png"), tmp_path / "t.jpg", v)
    assert Image.open(out).size == (1280, 720)


def test_mobile_check_contrast(tmp_path):
    good = thumbnail.mobile_check(_fake_render(tmp_path / "g.png"))
    flat = thumbnail.mobile_check(_fake_render(tmp_path / "f.png", contrast=False))
    assert good["ok"] and not flat["ok"]
    assert "contrast" in flat


def test_write_plan_for_job(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "JOBS", tmp_path / "jobs")
    job = jobs.create_job("x", "short"); jobs.save_job(job)
    d = jobs.job_dir(job.id)
    (d / "script.md").write_text(SCRIPT, encoding="utf-8")
    out = thumbnail.write_plan(job, ["golden throne", "burning ship", "wax tablet"], "salamis_strait_dusk")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["variants"]) == 3 and len(data["render_requests"]) == 3
    assert data["variants"][0]["face"] == "XERXES"


def test_write_plan_without_speakers_needs_a_face(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "JOBS", tmp_path / "jobs")
    job = jobs.create_job("x", "short"); jobs.save_job(job)
    (jobs.job_dir(job.id) / "script.md").write_text("## hook\nNarration. [src: f]\n", encoding="utf-8")
    with pytest.raises(ValueError):
        thumbnail.write_plan(job, ["a", "b", "c"], "set")
    assert thumbnail.write_plan(job, ["a", "b", "c"], "set", faces=["THEMISTOCLES"]).exists()

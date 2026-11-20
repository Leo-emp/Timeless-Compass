# Tests for the measured still checks (`tc still`): geometry from the inspector + image statistics.
import random

from PIL import Image

from tc.stillcheck import detail_map, geometry_problems, image_problems

W, H = 1920, 1080


def el(role, box, order, id=None, holds=None):
    return {"role": role, "box": list(box), "order": order, "id": id, "holds": holds}


def test_hand_far_from_its_prop():
    e = [el("prop", (100, 100, 10, 300), 0, id="spear"), el("hand", (500, 500, 30, 30), 1, holds="spear")]
    assert any("does not touch" in p for p in geometry_problems(e, W, H))


def test_hand_on_its_prop_is_fine():
    e = [el("prop", (100, 100, 10, 300), 0, id="spear"), el("hand", (92, 200, 30, 30), 1, holds="spear")]
    assert geometry_problems(e, W, H) == []


def test_later_prop_covers_face_earlier_does_not():
    face = el("face", (500, 300, 120, 130), 1)
    later = el("prop", (480, 280, 160, 170), 2, id="banner")
    earlier = el("prop", (480, 280, 160, 170), 0, id="banner")
    assert any("covers face" in p for p in geometry_problems([face, later], W, H))
    assert not any("covers face" in p for p in geometry_problems([earlier, face], W, H))


def test_text_overflowing_its_box():
    e = [el("textbox", (1400, 50, 300, 60), 0), el("text", (1390, 60, 340, 30), 1)]
    assert any("text overflows" in p for p in geometry_problems(e, W, H))


def test_text_outside_safe_area():
    e = [el("textbox", (1850, 10, 60, 40), 0), el("text", (1855, 15, 50, 30), 1)]
    assert any("outside safe area" in p for p in geometry_problems(e, W, H))


def test_flat_grey_image_is_flat_and_empty():
    probs = image_problems(Image.new("RGB", (W, H), (128, 128, 128)))
    assert any("flat contrast" in p for p in probs) and any("empty area" in p for p in probs)


def test_detailed_image_has_no_empty_tiles():
    random.seed(1)
    img = Image.effect_noise((W, H), 120).convert("RGB")
    assert not any("empty area" in p for p in image_problems(img))


def test_calm_tiles_are_allowed():
    img = Image.new("RGB", (W, H), (128, 128, 128))
    calm = {(c, r) for c in range(8) for r in range(6)}
    assert not any("empty area" in p for p in image_problems(img, calm))


def test_detail_map_shape():
    m = detail_map(Image.new("RGB", (W, H)))
    assert len(m) == 6 and len(m[0]) == 8


def test_extras_may_be_partly_hidden():
    face = dict(el("face", (500, 300, 120, 130), 1), acting="false")
    assert not any("covers face" in p for p in geometry_problems([face, el("prop", (480, 280, 160, 170), 2)], W, H))

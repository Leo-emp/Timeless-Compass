from tc import emblems


def test_every_crowd_emblem_can_be_painted(tmp_path):
    for name in emblems.EMBLEMS:
        f = emblems.paint(name, tmp_path / f"{name}.png", size=256, seed=1)
        assert f.exists() and f.stat().st_size > 500, name


def test_painting_is_deterministic_and_seed_changes_colours(tmp_path):
    a = emblems.paint("owl", tmp_path / "a.png", size=128, seed=3).read_bytes()
    b = emblems.paint("owl", tmp_path / "b.png", size=128, seed=3).read_bytes()
    c = emblems.paint("owl", tmp_path / "c.png", size=128, seed=4).read_bytes()
    assert a == b and a != c


def test_emblem_is_drawn_inside_the_round_shield_face(tmp_path):
    from PIL import Image
    im = Image.open(emblems.paint("trident", tmp_path / "t.png", size=200, seed=2)).convert("RGBA")
    assert im.getpixel((2, 2))[3] == 0            # corners outside the circle are transparent
    assert im.getpixel((100, 100))[3] == 255       # the face is opaque

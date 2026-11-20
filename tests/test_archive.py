# WS17 (Session F): the "declassified archive footage" look.
import shutil
import subprocess

import pytest

from tc import archive


def test_archive_look_is_black_and_white_grainy_weaving_and_scratched():
    f = archive.filter_graph(archive.LOOKS["kinescope"])
    for part in ("hue=s=0", "noise=", "crop=", "drawbox=", "vignette=", "gblur="):
        assert part in f, part
    assert f.startswith("[0:v]") and f.endswith("[out]")


def test_film_order_softness_before_grain_and_weave_last():
    f = archive.filter_graph(archive.LOOKS["kinescope"])
    # the old lens softens the IMAGE (not the grain); the grain is on the film; the whole film then weaves in the gate
    assert f.index("gblur=") < f.index("noise=") < f.index("crop=")


def test_gate_weave_moves_every_frame_but_stays_small():
    f = archive.filter_graph(archive.LOOKS["kinescope"])
    crop = f[f.index("crop="):].split(",")[0]
    assert "n" in crop and "sin(" in crop                         # a function of the frame number
    assert archive.LOOKS["kinescope"]["weave_px"] <= 6             # a real gate wobbles a few pixels, never more


def test_aged_print_is_tinted_and_pillarbox_gives_period_frame():
    f = archive.filter_graph(archive.LOOKS["aged_print"])
    assert "colorchannelmixer" in f                                # faded warm print, not pure grey
    f2 = archive.filter_graph(dict(archive.LOOKS["kinescope"], pillarbox=True))
    assert "pad=" in f2                                            # 1.37:1 academy frame inside 16:9


def test_scratches_can_be_turned_off():
    f = archive.filter_graph(dict(archive.LOOKS["kinescope"], scratches=0))
    assert "drawbox=" not in f


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_real_ffmpeg_turns_a_colour_frame_grey(tmp_path):
    src = tmp_path / "in.png"; dst = tmp_path / "out.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=640x360", "-frames:v", "1",
                    str(src)], check=True)
    assert archive.run(str(src), str(dst), "kinescope") == 0 and dst.exists()
    from PIL import Image
    im = Image.open(dst).convert("RGB").resize((32, 18))
    px = [im.getpixel((x, y)) for y in range(18) for x in range(32)]
    assert max(max(p) - min(p) for p in px) <= 12                  # every pixel ~ grey (r = g = b)
    assert im.size == (32, 18) and Image.open(dst).size == (640, 360)   # same size out as in

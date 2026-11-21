# Tests for thumbnails (spec 6.9): the Node renderer (film/scripts/thumb.mjs) and the measured checks (tc thumb).
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FILM = ROOT / "film"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_thumb_script_renders_fixture(tmp_path):
    from PIL import Image
    dst = FILM / "src" / "jobs" / "_thumb_fixture"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "tests" / "fixtures" / "thumb_fixture" / "thumb.ts", dst / "thumb.ts")
    try:
        out = tmp_path / "a.png"
        r = subprocess.run(["node", "scripts/thumb.mjs", "_thumb_fixture", "a", str(out)], cwd=FILM,
                           capture_output=True, text=True, timeout=180)
        assert r.returncode == 0, r.stderr
        info = json.loads(r.stdout.strip().splitlines()[-1])
        assert info["words"] == ["HI"] and (info["w"], info["h"]) == (64, 36)
        im = Image.open(out).convert("RGB")
        assert im.size == (64, 36)
        r_, g, b = im.getpixel((32, 18))
        assert r_ > 200 and g < 50 and b < 50
    finally:
        shutil.rmtree(dst, ignore_errors=True)


def _busy(w, h, seed=1):
    """A high-contrast test picture (black/white blocks)."""
    from PIL import Image
    import random
    rnd = random.Random(seed)
    im = Image.new("RGB", (w, h), "white")
    px = im.load()
    for bx in range(0, w, 40):
        for by in range(0, h, 40):
            c = (0, 0, 0) if rnd.random() < 0.5 else (255, 255, 255)
            for x in range(bx, min(w, bx + 40)):
                for y in range(by, min(h, by + 40)):
                    px[x, y] = c
    return im


def test_thumb_words_declared_and_capped():
    from tc.thumb import thumb_problems
    im = _busy(1280, 720)
    assert thumb_problems(im, ["ONE", "LAST", "CHANCE"], "long", 300_000) == []
    assert any("more than 3 words" in p for p in thumb_problems(im, ["A", "B", "C", "D"], "long", 300_000))
    assert any("too long" in p for p in thumb_problems(im, ["EXTRAORDINARILY"], "long", 300_000))


def test_thumb_size_checked():
    from tc.thumb import thumb_problems
    assert any("size" in p for p in thumb_problems(_busy(1280, 719), [], "long", 300_000))
    assert thumb_problems(_busy(1080, 1920), [], "short", 300_000) == []
    assert any("2 MB" in p for p in thumb_problems(_busy(1280, 720), [], "long", 2_100_000))


def test_thumb_flat_image_fails_readability():
    from PIL import Image
    from tc.thumb import thumb_problems
    assert any("160 px" in p for p in thumb_problems(Image.new("RGB", (1280, 720), (128, 128, 128)), [], "long", 50_000))


def test_thumb_variants_must_differ():
    from tc.thumb import variants_differ
    a = _busy(1280, 720, 1)
    assert not variants_differ(a, a.copy())
    assert variants_differ(a, _busy(1280, 720, 2))

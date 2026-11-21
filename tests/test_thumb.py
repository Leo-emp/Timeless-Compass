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

import numpy as np
from PIL import Image

from tc import compare


def _save(path, color, size=(160, 90)):
    Image.fromarray((np.ones((size[1], size[0], 3)) * np.array(color) * 255).astype(np.uint8)).save(path)
    return path


def test_each_still_is_paired_with_the_reference_frame_of_closest_mood(tmp_path):
    ref = tmp_path / "ref"; ref.mkdir()
    warm = _save(ref / "warm.jpg", (0.8, 0.5, 0.25))
    cold = _save(ref / "cold.jpg", (0.25, 0.4, 0.7))
    ours = _save(tmp_path / "dusk_shot.png", (0.75, 0.48, 0.3))
    pairs = compare.pair([ours], ref)
    assert pairs[0]["ref"].name == "warm.jpg"
    assert 0 <= pairs[0]["score"] <= 100


def test_sheet_has_one_row_per_still_and_writes_an_image(tmp_path):
    ref = tmp_path / "ref"; ref.mkdir()
    _save(ref / "a.jpg", (0.8, 0.5, 0.25)); _save(ref / "b.jpg", (0.2, 0.3, 0.5))
    stills = [_save(tmp_path / f"s{i}.png", c) for i, c in enumerate([(0.7, 0.5, 0.3), (0.2, 0.3, 0.45), (0.5, 0.5, 0.5)])]
    out = tmp_path / "sheet.jpg"
    rows = compare.sheet(stills, ref, out, width=320)
    assert len(rows) == 3 and out.exists()
    w, h = Image.open(out).size
    assert w == 2 * 320 and h > 3 * 100

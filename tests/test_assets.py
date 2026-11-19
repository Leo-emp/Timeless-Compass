import hashlib
import json

import pytest

from tc import assets

HDRI_FILES = {"hdri": {"2k": {"hdr": {"url": "https://dl.polyhaven.org/x/sky_2k.hdr", "size": 6, "md5": "m1"},
                              "exr": {"url": "https://dl.polyhaven.org/x/sky_2k.exr", "size": 9, "md5": "m2"}}}}
TEX_FILES = {
    "Diffuse": {"2k": {"jpg": {"url": "https://dl/x/rock_diff_2k.jpg", "size": 3, "md5": "a"},
                       "png": {"url": "https://dl/x/rock_diff_2k.png", "size": 30, "md5": "b"}}},
    "nor_gl": {"2k": {"jpg": {"url": "https://dl/x/rock_nor_gl_2k.jpg", "size": 3, "md5": "c"}}},
    "nor_dx": {"2k": {"jpg": {"url": "https://dl/x/rock_nor_dx_2k.jpg", "size": 3, "md5": "d"}}},
    "Rough": {"2k": {"jpg": {"url": "https://dl/x/rock_rough_2k.jpg", "size": 3, "md5": "e"}}},
    "Displacement": {"2k": {"png": {"url": "https://dl/x/rock_disp_2k.png", "size": 5, "md5": "f"}}},
    "blend": {"2k": {"blend": {"url": "https://dl/x/rock_2k.blend", "size": 99, "md5": "g"}}},
}
MODEL_FILES = {"blend": {"2k": {"blend": {"url": "https://dl/x/tree_2k.blend", "size": 50, "md5": "h",
                                          "include": {"textures/tree_diff_2k.jpg": {"url": "https://dl/x/t.jpg", "size": 4, "md5": "i"}}}}},
               "gltf": {"2k": {}}}


def test_hdri_plan_takes_the_hdr_file_at_the_asked_resolution():
    assert assets.plan_files(HDRI_FILES, "hdris", "2k") == [("sky_2k.hdr", "https://dl.polyhaven.org/x/sky_2k.hdr", 6, "m1")]


def test_texture_plan_takes_colour_opengl_normal_roughness_and_displacement_only():
    names = [p[0] for p in assets.plan_files(TEX_FILES, "textures", "2k")]
    assert names == ["rock_diff_2k.jpg", "rock_nor_gl_2k.jpg", "rock_rough_2k.jpg", "rock_disp_2k.png"]


def test_model_plan_takes_the_blend_file_and_its_textures_at_their_relative_paths():
    plan = assets.plan_files(MODEL_FILES, "models", "2k")
    assert plan == [("tree_2k.blend", "https://dl/x/tree_2k.blend", 50, "h"),
                    ("textures/tree_diff_2k.jpg", "https://dl/x/t.jpg", 4, "i")]


def test_missing_resolution_is_an_error():
    with pytest.raises(KeyError):
        assets.plan_files(HDRI_FILES, "hdris", "16k")


def test_budget_refuses_downloads_past_the_local_cap(tmp_path):
    (tmp_path / "old").mkdir()
    (tmp_path / "old" / "big.bin").write_bytes(b"x" * 900)
    assert assets.over_budget(tmp_path, incoming=50, cap_bytes=1000) is False
    assert assets.over_budget(tmp_path, incoming=200, cap_bytes=1000) is True


def test_fetch_downloads_verifies_md5_and_writes_a_cc0_manifest(tmp_path):
    body = b"HDRDATA"
    files = {"hdri": {"2k": {"hdr": {"url": "https://dl/x/sky_2k.hdr", "size": len(body), "md5": hashlib.md5(body).hexdigest()}}}}

    def fake_download(url, path):
        path.write_bytes(body)

    out = assets.fetch("sky", "hdris", "2k", tmp_path, files=files, download=fake_download, cap_bytes=10**9)
    assert (out / "sky_2k.hdr").read_bytes() == body
    m = json.loads((out / "asset.json").read_text(encoding="utf-8"))
    assert m["licence"] == "CC0 (Poly Haven)" and m["source"] == "https://polyhaven.com/a/sky" and m["files"] == ["sky_2k.hdr"]


def test_fetch_rejects_a_corrupt_download_and_leaves_no_file(tmp_path):
    files = {"hdri": {"2k": {"hdr": {"url": "https://dl/x/sky_2k.hdr", "size": 3, "md5": "0" * 32}}}}
    with pytest.raises(assets.AssetError):
        assets.fetch("sky", "hdris", "2k", tmp_path, files=files, download=lambda u, p: p.write_bytes(b"bad"), cap_bytes=10**9)
    assert not (tmp_path / "sky" / "sky_2k.hdr").exists()


def test_fetch_skips_files_already_downloaded(tmp_path):
    body = b"same"
    files = {"hdri": {"2k": {"hdr": {"url": "u", "size": 4, "md5": hashlib.md5(body).hexdigest()}}}}
    (tmp_path / "sky").mkdir()
    (tmp_path / "sky" / "u").write_bytes(body)
    calls = []
    assets.fetch("sky", "hdris", "2k", tmp_path, files=files, download=lambda u, p: calls.append(u), cap_bytes=10**9)
    assert calls == []

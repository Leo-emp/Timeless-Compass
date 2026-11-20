# Tests for the cloud render QUEUE (replaces the single shared cloud/batch.json): every session submits its own
# request file, so two sessions can never overwrite each other; runners (GitHub / Kaggle) pick the files up.
import json
from datetime import datetime

import pytest
from PIL import Image

from tc import cloud_queue as cq

NOW = datetime(2026, 11, 20, 2, 30, 5)
INDEX = {"kloofendal_48d_partly_cloudy_puresky": {"kind": "hdris", "source": "https://polyhaven.com/a/k", "files": []},
         "boulder_01": {"kind": "models", "source": "https://polyhaven.com/a/boulder_01", "files": []},
         "kylix_cleveland": {"kind": "glb", "source": "https://sketchfab.com/3d-models/x", "files": []}}


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A fake repo: one scene script + one lib module, and an empty queue folder."""
    (tmp_path / "blender" / "scenes").mkdir(parents=True)
    (tmp_path / "blender" / "lib").mkdir(parents=True)
    (tmp_path / "blender" / "scenes" / "cannon_test.py").write_text(
        "from lib import cannon, common\ncommon.hdri_world('kloofendal_48d_partly_cloudy_puresky')\ncannon.build('field')\n")
    (tmp_path / "blender" / "lib" / "cannon.py").write_text("def build(kind):\n    load_scan('boulder_01')\n\ndef unused():\n    x = 'kylix_cleveland'\n")
    (tmp_path / "blender" / "lib" / "common.py").write_text("def hdri_world(i):\n    pass\n")
    monkeypatch.setattr(cq, "ROOT", tmp_path)
    monkeypatch.setattr(cq, "QUEUE", tmp_path / "cloud" / "queue")
    return tmp_path


def test_submit_writes_one_unique_file_per_request(repo):
    a = cq.submit("cannon", "blender/scenes/cannon_test.py", ["out/cannon", "64"], session="C", now=NOW, index=INDEX)
    b = cq.submit("cannon", "blender/scenes/cannon_test.py", ["out/cannon", "64"], session="D", now=NOW, index=INDEX)
    assert a != b and a.exists() and b.exists()                 # same name + same second, different sessions
    assert a.name == "20261120-023005-c-cannon.json"
    e = json.loads(a.read_text())
    assert e["id"] == "20261120-023005-c-cannon" and e["target"] == "github" and e["session"] == "C"


def test_submit_never_overwrites(repo):
    cq.submit("cannon", "blender/scenes/cannon_test.py", [], session="C", now=NOW, index=INDEX)
    p = cq.submit("cannon", "blender/scenes/cannon_test.py", [], session="C", now=NOW, index=INDEX)
    assert p.name == "20261120-023005-c-cannon-2.json"          # a second one in the same second gets a suffix


def test_submit_checks_script_and_target(repo):
    with pytest.raises(cq.QueueError):
        cq.submit("x", "blender/scenes/missing.py", [], session="C", now=NOW, index=INDEX)
    with pytest.raises(cq.QueueError):
        cq.submit("x", "blender/scenes/cannon_test.py", [], session="C", target="laptop", now=NOW, index=INDEX)


def test_scans_found_from_the_scene_code(repo):
    e = json.loads(cq.submit("cannon", "blender/scenes/cannon_test.py", [], session="C", now=NOW, index=INDEX).read_text())
    assert e["scans"] == {"hdris": ["kloofendal_48d_partly_cloudy_puresky"], "models": ["boulder_01"]}
    assert e["cloud_missing"] == []                              # nothing that only R2 could give


def test_sketchfab_scans_are_flagged(repo):
    e = cq.make_entry("k", "blender/scenes/cannon_test.py", [], "C", now=NOW, index=INDEX,
                      scans={"glb": ["kylix_cleveland"]})
    assert e["cloud_missing"] == ["kylix_cleveland"]             # not free to fetch on a cloud machine without R2


def test_changed_entries_picks_only_queue_files():
    changed = ["cloud/queue/20261120-023005-c-cannon.json", "tc/x.py", "cloud/queue/README.md",
               "cloud/queue/20261120-023006-d-market.json"]
    assert cq.changed_entries(changed) == ["20261120-023005-c-cannon", "20261120-023006-d-market"]


# ------------------------------------------------------------------ the runner (same on GitHub and Kaggle)
def fake_blender(colour=(120, 100, 80)):
    calls = []
    def run(cmd, env, cwd):
        calls.append((cmd, env))
        out = cwd / "out" / "cannon"
        out.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (16, 8), colour).save(out / "line.png")
        return 0
    return run, calls


def test_run_entry_renders_checks_and_writes_result(repo):
    p = cq.submit("cannon", "blender/scenes/cannon_test.py", ["out/cannon", "64"], session="C", now=NOW, index=INDEX)
    run, calls = fake_blender()
    res = cq.run_entry(json.loads(p.read_text()), "/b/blender", repo, runner=run, gpu=True, fetch=lambda e: None)
    cmd, env = calls[0]
    assert cmd[:4] == ["/b/blender", "-b", "--python", str(repo / "cloud" / "blender_shot.py")]
    assert cmd[5:] == ["out/cannon", "64"]
    assert env["TC_SCRIPT"].endswith("cannon_test.py") and env["TC_GPU"] == "1"
    assert env["TC_DENOISER"] == "OPENIMAGEDENOISE"
    assert res["status"] == "done" and res["images"] == ["out/cannon/line.png"]
    saved = json.loads((repo / "out" / "_results" / "20261120-023005-c-cannon.json").read_text())
    assert saved["status"] == "done"


def test_run_entry_fails_on_black_image(repo):
    p = cq.submit("cannon", "blender/scenes/cannon_test.py", ["out/cannon"], session="C", now=NOW, index=INDEX)
    run, _ = fake_blender(colour=(0, 0, 0))
    res = cq.run_entry(json.loads(p.read_text()), "b", repo, runner=run, fetch=lambda e: None)
    assert res["status"] == "failed" and "black" in json.dumps(res["problems"])


def test_run_entry_fails_when_nothing_rendered(repo):
    p = cq.submit("cannon", "blender/scenes/cannon_test.py", ["out/cannon"], session="C", now=NOW, index=INDEX)
    res = cq.run_entry(json.loads(p.read_text()), "b", repo, runner=lambda cmd, env, cwd: 1, fetch=lambda e: None)
    assert res["status"] == "failed" and res["exit"] == 1

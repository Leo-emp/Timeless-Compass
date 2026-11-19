# Tests for WS9 task 5 (safety): progress ledger (resume after a crash), frame checks (missing / black / broken
# frames), re-queue, the shard worker loop, the job bundle the cloud machines read, and joining frames into videos.
import json
import shutil

import pytest
from PIL import Image

from tc import render_farm as rf


def png(path, colour=(120, 90, 60), size=(16, 8)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, colour).save(path)


def frames(d, numbers, colour=(120, 90, 60)):
    for n in numbers:
        png(d / f"f{n:04d}.png", colour)


# ---------------------------------------------------------------- frame checks
def test_check_frames_all_good(tmp_path):
    frames(tmp_path, range(5, 15))                       # pre-roll: the shot starts on frame 5
    r = rf.check_frames(tmp_path, expected=10)
    assert r["ok"] and r["first"] == 5 and r["count"] == 10 and not r["bad"]


def test_check_frames_finds_gaps_black_and_broken(tmp_path):
    frames(tmp_path, [1, 2, 4, 5])                      # frame 3 missing
    png(tmp_path / "f0006.png", (0, 0, 0))              # black frame
    (tmp_path / "f0007.png").write_bytes(b"")           # empty file = crashed while writing
    r = rf.check_frames(tmp_path, expected=8)
    assert not r["ok"]
    assert r["missing"] == [3, 8]                       # the gap + the frame never reached
    assert set(r["bad"]) == {6, 7}


def test_dark_night_frame_is_not_black(tmp_path):
    frames(tmp_path, [1], colour=(12, 10, 20))         # a moody night shot is dark, not broken
    assert rf.check_frames(tmp_path, expected=1)["ok"]


def test_remove_bad_frames_deletes_only_bad(tmp_path):
    frames(tmp_path, [1, 2])
    png(tmp_path / "f0003.png", (0, 0, 0))
    r = rf.check_frames(tmp_path, expected=3)
    rf.remove_bad_frames(tmp_path, r)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["f0001.png", "f0002.png"]


# ---------------------------------------------------------------- progress ledger
def test_progress_survives_reload(tmp_path):
    p = rf.Progress(tmp_path / "progress.json")
    p.mark("s001", "done", note="10 frames")
    again = rf.Progress(tmp_path / "progress.json")
    assert again.status("s001") == "done" and again.status("s002") == "todo"


# ---------------------------------------------------------------- the worker loop
def make_bundle(shots):
    """A tiny bundle: the shard lists the shots, each recipe has its frame count."""
    return {"job": "j1", "recipes": {s: {"shot": s, "frames": 24} for s in shots},
            "plan": {"kaggle": [{"shots": shots, "cost": 1}], "github": [],
                     "settings": {s: {"engine": "CYCLES", "samples": 64, "denoiser": "OPENIMAGEDENOISE"} for s in shots}}}


class FakeBlender:
    """Pretends to be Blender: writes the frames a render would write (optionally a black one the first time)."""
    def __init__(self, black_once=()):
        self.calls, self.black_once = [], set(black_once)

    def __call__(self, cmd, env):
        shot = env["TC_SHOT"]
        self.calls.append(shot)
        out = rf.Path(env["TC_FRAMES"])
        for n in range(1, 25):                          # shot.py renders at least 24 frames
            f = out / f"f{n:04d}.png"
            if not f.exists():                          # Blender skips frames that already exist (resume)
                black = shot in self.black_once and n == 2
                png(f, (0, 0, 0) if black else (100, 100, 100))
        self.black_once.discard(shot)
        return 0


def test_worker_renders_all_and_records_progress(tmp_path):
    fake = FakeBlender()
    res = rf.run_shard(make_bundle(["s001", "s002"]), "kaggle", 0, tmp_path, blender="blender", runner=fake)
    assert res["done"] == ["s001", "s002"] and fake.calls == ["s001", "s002"]
    prog = json.loads((tmp_path / "progress.json").read_text())
    assert prog["s001"]["status"] == "done"


def test_worker_resumes_and_skips_done_shots(tmp_path):
    rf.run_shard(make_bundle(["s001"]), "kaggle", 0, tmp_path, blender="b", runner=FakeBlender())
    fake = FakeBlender()
    res = rf.run_shard(make_bundle(["s001", "s002"]), "kaggle", 0, tmp_path, blender="b", runner=fake)
    assert fake.calls == ["s002"] and res["done"] == ["s001", "s002"]


def test_worker_requeues_black_frames(tmp_path):
    fake = FakeBlender(black_once={"s001"})
    res = rf.run_shard(make_bundle(["s001"]), "kaggle", 0, tmp_path, blender="b", runner=fake)
    assert fake.calls == ["s001", "s001"]              # rendered again after the black frame was removed
    assert res["done"] == ["s001"]


def test_worker_gives_up_after_retries(tmp_path):
    def always_crash(cmd, env):
        return 1                                        # Blender died, wrote nothing
    res = rf.run_shard(make_bundle(["s001"]), "kaggle", 0, tmp_path, blender="b", runner=always_crash, retries=1)
    assert res["failed"] == ["s001"]
    assert json.loads((tmp_path / "progress.json").read_text())["s001"]["status"] == "failed"


def test_worker_stops_before_the_session_time_limit(tmp_path):
    clock = iter([0, 0, 100, 100, 100]).__next__       # each shot "takes" 100 s
    res = rf.run_shard(make_bundle(["s001", "s002", "s003"]), "kaggle", 0, tmp_path, blender="b",
                       runner=FakeBlender(), clock=clock, budget_s=150, est_s=lambda sid: 60)
    assert res["done"] == ["s001"] and res["paused"] == ["s002", "s003"]


def test_worker_blender_command_uses_cloud_wrapper(tmp_path):
    seen = {}
    def spy(cmd, env):
        seen["cmd"], seen["env"] = cmd, env
        return FakeBlender()(cmd, env)
    rf.run_shard(make_bundle(["s001"]), "kaggle", 0, tmp_path, blender="/b/blender", runner=spy)
    assert seen["cmd"][0] == "/b/blender" and seen["cmd"][1] == "-b"
    assert seen["cmd"][3].replace("\\", "/").endswith("cloud/blender_shot.py")
    assert seen["env"]["TC_ENGINE"] == "CYCLES" and seen["env"]["TC_GPU"] == "1"   # kaggle = GPU


# ---------------------------------------------------------------- bundle + requeue
def test_bundle_holds_recipes_plan_and_scans(tmp_path):
    d = tmp_path / "job"
    (d / "recipes").mkdir(parents=True)
    (d / "recipes" / "s001.json").write_text(json.dumps({"shot": "s001", "frames": 3}))
    (d / "render_plan.json").write_text(json.dumps({"kaggle": [], "github": [], "settings": {}}))
    b = rf.make_bundle("job", d, scans={"s001": ["boulder_01"]})
    assert b["recipes"]["s001"]["frames"] == 3 and b["scans"] == {"s001": ["boulder_01"]}


def test_requeue_lists_shots_that_are_not_ok(tmp_path):
    frames(tmp_path / "kaggle-0" / "s001" / "frames", range(1, 25))
    frames(tmp_path / "github-1" / "s002" / "frames", [1, 3])
    bundle = make_bundle(["s001", "s002", "s003"])
    q = rf.requeue(bundle, tmp_path)
    assert q == ["s002", "s003"]


# ---------------------------------------------------------------- join frames -> shot video
def test_join_command_starts_at_first_frame(tmp_path):
    cmd = rf.join_command(tmp_path / "frames", tmp_path / "s001.mp4", first=7, fps=24)
    assert cmd[0] == "ffmpeg" and "-start_number" in cmd and cmd[cmd.index("-start_number") + 1] == "7"
    assert "yuv420p" in cmd and str(tmp_path / "s001.mp4") == cmd[-1]


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_join_shot_makes_a_video(tmp_path):
    frames(tmp_path / "frames", range(3, 9))
    out = rf.join_shot(tmp_path / "frames", tmp_path / "s001.mp4", expected=6)
    assert out.exists() and out.stat().st_size > 0


def test_join_refuses_broken_frames(tmp_path):
    frames(tmp_path / "frames", [1, 3])
    with pytest.raises(rf.FrameError):
        rf.join_shot(tmp_path / "frames", tmp_path / "s001.mp4", expected=3)


# ---------------------------------------------------------------- join on the cloud machine (small downloads)
def test_worker_can_join_each_done_shot(tmp_path):
    joined = []
    res = rf.run_shard(make_bundle(["s001"]), "kaggle", 0, tmp_path, blender="b", runner=FakeBlender(),
                       joiner=lambda frames_dir, out, n: joined.append((out.name, n)))
    assert res["done"] == ["s001"] and joined == [("s001.mp4", 24)]


def test_requeue_accepts_a_joined_video_without_frames(tmp_path):
    shard = tmp_path / "github-0"
    (shard / "s001.mp4").parent.mkdir(parents=True)
    (shard / "s001.mp4").write_bytes(b"video")
    rf.Progress(shard / "progress.json").mark("s001", "done")
    assert rf.requeue(make_bundle(["s001", "s002"]), tmp_path) == ["s002"]

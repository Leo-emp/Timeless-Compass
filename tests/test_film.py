# Tests for `tc film`: splitting a video into frame ranges, starting cloud parts, joining them, speed numbers.
from pathlib import Path

from tc.film import concat_list, github_dispatch_args, speed_report, split_frames, part_name


def test_split_frames_contiguous():
    r = split_frames(21600, 7)
    assert r[0][0] == 0 and r[-1][1] == 21599
    assert all(b[0] == a[1] + 1 for a, b in zip(r, r[1:]))
    sizes = [b - a + 1 for a, b in r]
    assert max(sizes) - min(sizes) <= 1 and sum(sizes) == 21600


def test_split_frames_more_parts_than_frames():
    assert split_frames(3, 10) == [(0, 0), (1, 1), (2, 2)]


def test_split_frames_rejects_nonsense():
    import pytest
    with pytest.raises(ValueError):
        split_frames(0, 3)
    with pytest.raises(ValueError):
        split_frames(10, 0)


def test_dispatch_args_carry_json_ranges():
    a = github_dispatch_args("FleetTest", [(0, 95), (96, 191)], ref="cinematic-agent")
    assert a[:4] == ["gh", "workflow", "run", "film-render.yml"]
    assert "parts=[[0,95],[96,191]]" in a and "comp=FleetTest" in a and a[a.index("--ref") + 1] == "cinematic-agent"


def test_concat_list_orders_by_start_frame(tmp_path):
    ps = [tmp_path / "part-96-191.mp4", tmp_path / "part-0-95.mp4", tmp_path / "part-1000-1100.mp4"]
    lines = [l for l in concat_list(ps).splitlines() if l.startswith("file")]
    assert lines[0].endswith("part-0-95.mp4'") and lines[1].endswith("part-96-191.mp4'")


def test_part_name():
    assert part_name(0, 95) == "part-0-95.mp4"


def test_speed_report_wall_clock():
    t = [{"from": 0, "to": 99, "seconds": 50, "started": 0, "ended": 60},
         {"from": 100, "to": 199, "seconds": 40, "started": 5, "ended": 50}]
    assert speed_report(t) == {"frames": 200, "render_s_sum": 90, "wall_s": 60, "frames_per_s": 200 / 60}


def test_join_refuses_a_missing_part(tmp_path):
    import pytest
    from tc.film import join_parts
    for n in ("part-0-9.mp4", "part-20-29.mp4"):
        (tmp_path / n).write_bytes(b"x")
    with pytest.raises(ValueError, match="gap"):
        join_parts(tmp_path, tmp_path / "out.mp4", runner=lambda *a, **k: None)


def test_join_finds_parts_in_artifact_subfolders(tmp_path):
    from tc.film import join_parts
    for a, b in ((0, 9), (10, 19)):
        d = tmp_path / f"part-{a}-{b}"; d.mkdir(); (d / f"part-{a}-{b}.mp4").write_bytes(b"x")
    calls = []
    join_parts(tmp_path, tmp_path / "out.mp4", runner=lambda cmd, **k: calls.append(cmd))
    assert calls and calls[0][0] == "ffmpeg" and "copy" in calls[0]
    assert (tmp_path / "concat.txt").read_text().count("file ") == 2


def test_concat_list_gives_each_part_its_exact_duration(tmp_path):
    txt = concat_list([tmp_path / "part-0-23.mp4", tmp_path / "part-24-71.mp4"])
    assert "duration 1.000000" in txt and "duration 2.000000" in txt


def test_clear_parts_removes_stale_parts_before_a_new_fetch(tmp_path):
    # a re-render must never mix old parts with new ones (and gh refuses to overwrite them)
    from tc.film import clear_parts
    (tmp_path / "part-0-485").mkdir()
    (tmp_path / "part-0-485" / "part-0-485.mp4").write_bytes(b"old")
    (tmp_path / "part-486-970.mp4").write_bytes(b"old")
    (tmp_path / "notes.txt").write_text("keep")
    assert clear_parts(tmp_path) == 2
    assert not (tmp_path / "part-0-485").exists() and not (tmp_path / "part-486-970.mp4").exists()
    assert (tmp_path / "notes.txt").exists()

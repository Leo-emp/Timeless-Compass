# Regression tests for the final-review findings (C1, I1-I8). Each one failed before its fix.
import json
import subprocess

import pytest

from tc import align, http, jobs, paths, script, shots, topics, youtube
from tc.config import Config
from tc.script import parse_script

CFG = Config()


def _shot(i, line, dur=None, where=None, move="push_in"):
    return shots.Shot.from_dict({"id": f"s{i:03d}", "line": line, "dur": dur, "who": ["x"], "where": where or f"w{i}",
                                 "action": "a", "expression": {}, "camera": {"move": move, "from": "f"}, "era": "e"})


# C1: computed durations must not freeze into the input file
def test_c1_rerun_after_adding_shot_resplits(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "JOBS", tmp_path / "jobs")
    job = jobs.create_job("x"); jobs.save_job(job); d = jobs.job_dir(job.id)
    (d / "script.md").write_text("## world\nOne line here.\n", encoding="utf-8")
    (d / "timings.json").write_text(json.dumps({"lines": [{"index": 0, "start": 0.0, "end": 9.0}]}), encoding="utf-8")
    (d / "voice.json").write_text(json.dumps({"duration_s": 9.0}), encoding="utf-8")
    one = {"id": "s1", "line": 0, "who": ["x"], "where": "a", "action": "a", "expression": {}, "camera": {"move": "static", "from": "f"}, "era": "e"}
    (d / "shots.json").write_text(json.dumps({"shots": [one]}), encoding="utf-8")
    from tc import cli
    cli.main(["shots", job.id])                                   # 9 s single shot -> fails pacing
    data = json.loads((d / "shots.json").read_text(encoding="utf-8"))
    data["shots"].append({**one, "id": "s2", "where": "b"})        # agent adds a second shot
    (d / "shots.json").write_text(json.dumps(data), encoding="utf-8")
    assert cli.main(["shots", job.id]) == 0                       # now 4.5 + 4.5 s
    timed = json.loads((d / "shots.timed.json").read_text(encoding="utf-8"))["shots"]
    assert [s["dur"] for s in timed] == [4.5, 4.5]


# I1: curl failing (timeout / dropped connection) must not look like success
class FailCurl:
    def __call__(self, cmd, **kw):
        out = cmd[cmd.index("-o") + 1]
        open(out, "wb").write(b"RIFFpartial")
        return subprocess.CompletedProcess(cmd, 28, stdout=b"200 audio/x-wav", stderr=b"")


def test_i1_curl_exit_code_means_failure():
    status, body, ctype = http.post_bytes("https://x", b"", {}, runner=FailCurl())
    assert status == 0
    with pytest.raises(http.HttpError):
        http.get_json("https://x", runner=FailCurl())


# I2: the last line's span must run to the end of the voice file
def test_i2_last_line_runs_to_voice_end():
    s = shots.fill_timing([_shot(1, 0), _shot(2, 1)], [{"index": 0, "start": 0.0, "end": 4.0}, {"index": 1, "start": 4.5, "end": 8.0}], voice_s=9.2)
    assert sum(x.dur for x in s) == pytest.approx(9.2)


# I3: unmatched lines share the gap instead of collapsing to 0 s
def _heard(words, start=0.0, step=0.5):
    return [{"w": w, "s": start + i * step, "e": start + i * step + 0.4} for i, w in enumerate(words)]


def test_i3_two_unmatched_lines_share_gap():
    lines = parse_script("## world\nOne two.\nZebra.\nQuartz.\nThree four.\n")
    res = align.align_lines(lines, _heard(["one", "two", "xx", "yy", "zz", "ww", "three", "four"]))
    assert res[1]["end"] - res[1]["start"] > 0.5 and res[2]["end"] - res[2]["start"] > 0.5


def test_i3_next_line_does_not_steal_unmatched_words():
    lines = parse_script("## world\nOne two.\nThemistocles.\nXerxes ran away.\n")
    res = align.align_lines(lines, _heard(["one", "two", "temmy", "stoklees", "serksees", "ran", "away"]))
    assert res[1]["end"] - res[1]["start"] >= 0.5


# I4: the YouTube key goes in a header, never in the URL / command line
def test_i4_youtube_key_not_in_url(monkeypatch):
    seen = {}
    def fake_get(url, headers=None, timeout=60, runner=None):
        seen["url"], seen["headers"] = url, headers
        return {"items": []}
    monkeypatch.setattr(youtube, "get_json", fake_get)
    youtube.search_videos("salamis", "SECRET")
    assert "SECRET" not in seen["url"] and seen["headers"]["X-Goog-Api-Key"] == "SECRET"


# I5: approval is tied to the exact script text; redoing a stage resets the later ones
def test_i5_edit_after_approval_blocks_voice(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(paths, "JOBS", tmp_path / "jobs")
    job = jobs.create_job("x"); jobs.save_job(job); d = jobs.job_dir(job.id)
    (d / "script.md").write_text("## world\nA.\n", encoding="utf-8")
    script.approve(d)
    (d / "script.md").write_text("## world\nB changed.\n", encoding="utf-8")
    assert not script.is_approved(d)


def test_i5_redo_resets_later_stages():
    job = jobs.create_job("x")
    for s in ("topic", "packaging", "research", "script", "voice", "align", "shots"):
        jobs.mark(job, s, "done")
    jobs.mark(job, "voice", "done", "re-voiced")
    assert job.stages["align"]["status"] == "todo" and job.stages["shots"]["status"] == "todo"
    assert job.stages["script"]["status"] == "done"


# I6: empty sections and lines before the first header are problems
def test_i6_empty_section_rejected():
    text = "## cold_open\nA. [src: s]\n## title\n## world\n## tension\nB. [src: s]\n"
    p = script.check_script(parse_script(text), "long", {"s": {}}, CFG, script.sections_in(text))
    assert any("world" in x and "empty" in x for x in p)


def test_i6_line_before_header_rejected():
    text = "Stray line.\n## cold_open\nA.\n"
    p = script.check_script(parse_script(text), "long", {}, CFG, script.sections_in(text))
    assert any("before the first" in x for x in p)


# I7: each line's first shot starts exactly at that line; overfull fixed durations are reported
def test_i7_shots_anchor_to_line_start():
    s = shots.fill_timing([_shot(1, 0, dur=8.0), _shot(2, 1)], [{"index": 0, "start": 0.0, "end": 5.0}, {"index": 1, "start": 5.0, "end": 10.0}], voice_s=10.0)
    assert s[1].at == 5.0
    lines = parse_script("## world\nA.\nB.\n")
    p = shots.check_shots(s, lines, [], CFG, voice_s=10.0)
    assert any("longer than" in x for x in p)


# I8: --pick is validated and never wipes the ranking
def test_i8_pick_validation(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(paths, "JOBS", tmp_path / "jobs")
    from tc import cli
    job = jobs.create_job("x"); jobs.save_job(job)
    assert cli.main(["topics", job.id, "--pick", "1"]) == 2                 # nothing scored yet
    (jobs.job_dir(job.id) / "topics.json").write_text(json.dumps({"ranked": [{"seed": "a"}, {"seed": "b"}], "picked": None}))
    for bad in ("0", "3", "-1"):
        assert cli.main(["topics", job.id, "--pick", bad]) == 2
    assert len(json.loads((jobs.job_dir(job.id) / "topics.json").read_text())["ranked"]) == 2
    assert cli.main(["topics", job.id, "--pick", "2"]) == 0

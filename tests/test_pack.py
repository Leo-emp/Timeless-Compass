# Tests for `tc pack` (spec 6.11, rule r22): the upload pack the owner uploads by hand in ~2 minutes.
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tc import pack

R2_KEYS = ["TC_R2_ACCOUNT_ID", "TC_R2_ACCESS_KEY_ID", "TC_R2_SECRET_ACCESS_KEY", "TC_R2_BUCKET"]


def _age(p: Path, seconds: float):
    t = time.time() - seconds
    os.utime(p, (t, t))


@pytest.fixture
def jobdir(tmp_path):
    d = tmp_path / "jobs" / "20261121-0919-x"
    (d / "thumb").mkdir(parents=True)
    (d / "qa").mkdir()
    (d / "job.json").write_text(json.dumps({"id": d.name, "title": "x", "kind": "short"}), encoding="utf-8")
    (d / "mix.wav").write_bytes(b"w")
    _age(d / "mix.wav", 100)
    (d / "master.mp4").write_bytes(b"VIDEO-BYTES")
    for v in "ab":
        (d / "thumb" / f"thumbnail_{v}.jpg").write_bytes(b"JPG" + v.encode())
    (d / "qa" / "thumbnail.json").write_text(json.dumps({"video": {"passed": True, "total": 92}}), encoding="utf-8")
    (d / "script.md").write_text('## hook\nXERXES: "Lay down your weapons." [dramatised]\nThey did not run. [src: f-1]\n', encoding="utf-8")
    (d / "sources.json").write_text(json.dumps({"f-1": {"claim": "c", "cites": ["Herodotus, Histories 7.202"]},
                                                "f-2": {"claim": "d", "cites": ["Herodotus, Histories 7.202", "Plutarch, Sayings 225c"]}}),
                                    encoding="utf-8")
    (d / "upload.json").write_text(json.dumps({"title": "Come and Take Them", "description": "Three words to the largest army on Earth.",
                                               "tags": ["thermopylae", "spartans", "history"]}), encoding="utf-8")
    return d


def test_pack_refuses_missing_parts(jobdir):
    assert pack.pack_problems(jobdir) == []
    (jobdir / "thumb" / "thumbnail_b.jpg").unlink()
    assert any("thumbnail_b" in p for p in pack.pack_problems(jobdir))


def test_pack_refuses_unpassed_thumbnail_qa(jobdir):
    (jobdir / "qa" / "thumbnail.json").write_text(json.dumps({"video": {"passed": False, "total": 70}}), encoding="utf-8")
    assert any("thumbnail checklist" in p for p in pack.pack_problems(jobdir))


def test_pack_refuses_stale_master(jobdir):
    _age(jobdir / "master.mp4", 500)                  # older than mix.wav -> built from an old mix
    assert any("older than" in p for p in pack.pack_problems(jobdir))
    (jobdir / "master.mp4").unlink()
    assert any("master.mp4" in p for p in pack.pack_problems(jobdir))


def test_description_has_sources_and_note(jobdir):
    text = pack.description(jobdir)
    assert text.startswith("Three words to the largest army on Earth.")
    assert "Sources:" in text and text.count("Herodotus, Histories 7.202") == 1 and "Plutarch, Sayings 225c" in text
    assert text.rstrip().endswith("Some dialogue is dramatised.")


def test_pack_files_complete(jobdir, tmp_path):
    out = pack.build_pack(jobdir, tmp_path / "packs", now=datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc))
    names = sorted(p.name for p in out.iterdir())
    assert names == sorted(["video.mp4", "thumbnail_a.jpg", "thumbnail_b.jpg", "title.txt", "description.txt", "tags.txt", "posting.txt"])
    assert (out / "video.mp4").read_bytes() == b"VIDEO-BYTES"
    assert (out / "title.txt").read_text(encoding="utf-8").strip() == "Come and Take Them"
    assert "#Shorts" in (out / "description.txt").read_text(encoding="utf-8")       # Shorts are tagged as Shorts


def test_pack_never_writes_env_values(jobdir, tmp_path, monkeypatch):
    monkeypatch.setenv("TC_R2_SECRET_ACCESS_KEY", "sekrit123")
    monkeypatch.setenv("TC_TELEGRAM_BOT_TOKEN", "tok456")
    out = pack.build_pack(jobdir, tmp_path / "packs")
    for p in out.iterdir():
        data = p.read_bytes()
        assert b"sekrit123" not in data and b"tok456" not in data


def test_upload_needs_all_keys():
    full = {k: "v" for k in R2_KEYS}
    assert pack.r2_config(full) is not None
    for k in R2_KEYS:
        assert pack.r2_config({kk: vv for kk, vv in full.items() if kk != k}) is None
    assert pack.r2_config({**full, "TC_R2_BUCKET": ""}) is None


def test_notify_skips_without_keys():
    assert pack.notify("hi", {}) is False


def test_posting_slot_long_and_short():
    sat = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)          # a Saturday
    assert pack.posting_slot("long", sat).startswith("2026-11-21 17:00 UTC")      # Sat 17:00 still ahead
    assert pack.posting_slot("long", datetime(2026, 11, 21, 18, 0, tzinfo=timezone.utc)).startswith("2026-11-24 17:00 UTC")  # next Tue
    assert pack.posting_slot("short", sat).startswith("2026-11-22 15:00 UTC")


def test_notify_keeps_the_token_off_any_command_line(monkeypatch):
    import subprocess
    import urllib.request
    seen = {}

    def no_subprocess(*a, **k):
        raise AssertionError("notify must not start a process (the token would sit in its argv)")

    class Resp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, timeout=0):
        seen["url"] = req.full_url
        return Resp()
    monkeypatch.setattr(subprocess, "run", no_subprocess)
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert pack.notify("hi", {"TC_TELEGRAM_BOT_TOKEN": "t", "TC_TELEGRAM_CHAT_ID": "1"}) is True
    assert seen["url"].endswith("/sendMessage")

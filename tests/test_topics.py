# Tests for topic demand scoring (growth engine).
import json
from pathlib import Path

import pytest

from tc import topics, youtube

FIX = Path(__file__).parent / "fixtures"


def _row(views, subs, published="2024-01-01T00:00:00Z", vid="x"):
    return {"video_id": vid, "title": vid, "channel_id": "c", "views": views, "channel_subs": subs,
            "published": published, "duration_s": 900}


def test_score_orders_by_formula():
    data = {
        "big": [_row(1_000_000, 100_000, "2024-01-01T00:00:00Z")],      # strong demand + outlier
        "mid": [_row(300_000, 1_000_000, "2025-06-01T00:00:00Z")],
        "low": [_row(150_000, 1_000_000, "2026-11-01T00:00:00Z")],      # smaller, weaker outlier, covered 18 days ago
    }
    ranked = topics.score_candidates(list(data), lambda s: data[s], today="2026-11-19")
    assert [r["seed"] for r in ranked] == ["big", "mid", "low"]
    assert ranked[0]["score"] == pytest.approx(0.45 * 1 + 0.35 * 1 + 0.20 * 1, abs=1e-3)
    assert ranked[-1]["score"] == pytest.approx(0.0, abs=1e-3)


def test_outlier_uses_subscriber_floor():
    ranked = topics.score_candidates(["s"], lambda s: [_row(50_000, 0)], today="2026-11-19")
    assert ranked[0]["outlier"] == pytest.approx(50.0)          # 50k views / 1000 floor


def test_parse_fixtures():
    search = json.loads((FIX / "yt_search.json").read_text())
    videos = json.loads((FIX / "yt_videos.json").read_text())
    chans = json.loads((FIX / "yt_channels.json").read_text())
    rows = youtube.rows_from(search, videos, chans)
    assert rows[0] == {"video_id": "v1", "title": "Battle of Salamis", "channel_id": "c1", "views": 2_500_000,
                       "channel_subs": 100_000, "published": "2025-01-10T00:00:00Z", "duration_s": 1110}
    assert rows[1]["duration_s"] == 3720
    assert rows[2]["duration_s"] == 55


def test_shorts_ignored_for_long_demand():
    rows = [_row(5_000_000, 1000, vid="short"), _row(100_000, 1000, vid="long")]
    rows[0]["duration_s"] = 50
    ranked = topics.score_candidates(["s"], lambda s: rows, today="2026-11-19")
    assert ranked[0]["demand"] == 100_000


def test_topics_without_key_is_friendly(capsys, monkeypatch, tmp_path):
    from tc import cli, paths
    from tc.config import Config
    monkeypatch.setattr(paths, "JOBS", tmp_path / "jobs")
    monkeypatch.setattr(topics, "get_config", lambda: Config())
    from tc import jobs
    job = jobs.create_job("x"); jobs.save_job(job)
    code = cli.main(["topics", job.id, "Salamis"])
    out = capsys.readouterr().out
    assert code == 2 and "YOUTUBE_API_KEY" in out and "console.cloud.google.com" in out

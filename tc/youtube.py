# YouTube Data API v3 (free quota) — just the three calls topic scoring needs.
# The key travels in the X-Goog-Api-Key header (via curl's header file), never in the URL.
# search.list (100 quota units) -> videos.list (1 unit) -> channels.list (1 unit).
import re

from tc.http import get_json

API = "https://www.googleapis.com/youtube/v3"


def _iso_duration_s(iso: str) -> int:
    """'PT1H2M3S' -> 3723 seconds."""
    m = re.fullmatch(r"P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def search_videos(query: str, key: str, max_results: int = 25, published_after: str | None = None) -> dict:
    url = f"{API}/search?part=snippet&type=video&maxResults={max_results}&q={_q(query)}"
    if published_after:
        url += f"&publishedAfter={published_after}"
    return get_json(url, {"X-Goog-Api-Key": key})


def video_stats(ids: list[str], key: str) -> dict:
    return get_json(f"{API}/videos?part=statistics,contentDetails&id={','.join(ids)}", {"X-Goog-Api-Key": key})


def channel_stats(ids: list[str], key: str) -> dict:
    return get_json(f"{API}/channels?part=statistics&id={','.join(sorted(set(ids)))}", {"X-Goog-Api-Key": key})


def _q(text: str) -> str:
    from urllib.parse import quote
    return quote(text)


def rows_from(search: dict, videos: dict, channels: dict) -> list[dict]:
    """Join the three API responses into simple rows, one per video (numbers as ints)."""
    vstat = {v["id"]: v for v in videos.get("items", [])}
    subs = {c["id"]: int(c.get("statistics", {}).get("subscriberCount", 0) or 0) for c in channels.get("items", [])}
    rows = []
    for it in search.get("items", []):
        vid = it["id"]["videoId"]
        sn = it["snippet"]
        v = vstat.get(vid, {})
        rows.append({"video_id": vid, "title": sn["title"], "channel_id": sn["channelId"],
                     "views": int(v.get("statistics", {}).get("viewCount", 0) or 0),
                     "channel_subs": subs.get(sn["channelId"], 0), "published": sn["publishedAt"],
                     "duration_s": _iso_duration_s(v.get("contentDetails", {}).get("duration", ""))})
    return rows


def fetch_rows(query: str, key: str) -> list[dict]:
    """Live: search a topic and return joined rows (costs ~102 quota units of the free 10,000/day)."""
    s = search_videos(query, key)
    ids = [it["id"]["videoId"] for it in s.get("items", [])]
    if not ids:
        return []
    v = video_stats(ids, key)
    c = channel_stats([it["snippet"]["channelId"] for it in s["items"]], key)
    return rows_from(s, v, c)

# Topic demand scoring — the first lever of the growth engine (spec 6.0).
# For each candidate topic ("seed") we look at the long-form videos YouTube already has and measure:
#   demand        = median views of those videos            (do people watch this topic?)
#   outlier       = best views / channel subscribers        (can a SMALL channel break out with it?)
#   freshness_gap = days since the newest 100k+ view video  (has nobody covered it well lately?) capped at 730
# Each part is min-max normalised across the seeds (0..1) and combined:
#   score = 0.45*demand + 0.35*outlier + 0.20*freshness_gap
import json
import statistics
from datetime import date

from tc import jobs
from tc.cli import register
from tc.config import get_config
from tc.http import HttpError

SUB_FLOOR = 1000          # tiny channels count as 1000 subscribers, so one lucky video can't explode the ratio
LONG_MIN_S = 180          # Shorts don't tell us about long-form demand
BIG_VIEWS = 100_000
GAP_CAP = 730
WEIGHTS = (0.45, 0.35, 0.20)


def _norm(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    return [1.0 if hi == lo else (v - lo) / (hi - lo) for v in values]


def score_candidates(seeds: list[str], fetch, today: str | None = None) -> list[dict]:
    today_d = date.fromisoformat(today) if today else date.today()
    raw = []
    for seed in seeds:
        rows = [r for r in fetch(seed) if r["duration_s"] >= LONG_MIN_S]
        views = [r["views"] for r in rows] or [0]
        demand = statistics.median(views)
        outlier = max((r["views"] / max(r["channel_subs"], SUB_FLOOR) for r in rows), default=0.0)
        big = [date.fromisoformat(r["published"][:10]) for r in rows if r["views"] >= BIG_VIEWS]
        gap = min(GAP_CAP, (today_d - max(big)).days) if big else GAP_CAP
        top = sorted(rows, key=lambda r: r["views"], reverse=True)[:3]
        raw.append({"seed": seed, "demand": demand, "outlier": outlier, "freshness_gap": gap,
                    "examples": [{"title": r["title"], "views": r["views"], "video_id": r["video_id"]} for r in top]})
    if not raw:
        return []
    nd, no, nf = (_norm([r[k] for r in raw]) for k in ("demand", "outlier", "freshness_gap"))
    for r, a, b, c in zip(raw, nd, no, nf):
        r["score"] = round(WEIGHTS[0] * a + WEIGHTS[1] * b + WEIGHTS[2] * c, 4)
    return sorted(raw, key=lambda r: r["score"], reverse=True)


# ---------------- command ----------------
NO_KEY = ("YOUTUBE_API_KEY is missing in timeless-compass/.env.\n"
          "Free setup: console.cloud.google.com -> new project -> enable 'YouTube Data API v3' -> "
          "Credentials -> Create API key -> add the line YOUTUBE_API_KEY=... to .env")


def _args(p):
    p.add_argument("job")
    p.add_argument("seeds", nargs="*", help="candidate topics to score")
    p.add_argument("--pick", type=int, help="record the owner's choice (1 = top ranked)")


@register("topics", "score candidate topics by YouTube demand", _args)
def _cmd_topics(args) -> int:
    job = jobs.load_job(args.job)
    out = jobs.job_dir(job.id) / "topics.json"
    if args.pick is not None:
        if not out.exists():
            print('Nothing scored yet: run  tc topics <id> "seed 1" "seed 2" ...  first')
            return 2
        ranked = json.loads(out.read_text(encoding="utf-8"))["ranked"]
        if not 1 <= args.pick <= len(ranked):
            print(f"--pick must be between 1 and {len(ranked)}")
            return 2
        chosen = ranked[args.pick - 1]
        out.write_text(json.dumps({"ranked": ranked, "picked": chosen["seed"]}, indent=2), encoding="utf-8")
        jobs.mark(job, "topic", "done", chosen["seed"]); jobs.save_job(job)
        print(f"picked: {chosen['seed']}")
        return 0
    if not args.seeds:
        print("Give at least one seed topic to score")
        return 2
    cfg = get_config()
    if not cfg.youtube_key:
        print(NO_KEY)
        return 2
    from tc.youtube import fetch_rows
    try:
        ranked = score_candidates(args.seeds, lambda s: fetch_rows(s, cfg.youtube_key))
    except HttpError as e:
        print(f"YouTube API error ({e.status}). If 403 'quotaExceeded', the free daily quota resets at midnight Pacific time.")
        return 2
    out.write_text(json.dumps({"ranked": ranked, "picked": None}, indent=2), encoding="utf-8")
    for i, r in enumerate(ranked, 1):
        print(f"{i}. {r['score']:.3f}  {r['seed']}  (median views {r['demand']:,.0f}, outlier x{r['outlier']:.1f}, gap {r['freshness_gap']} d)")
    return 0

# Results Loop + Anti-Sameness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The system learns from real YouTube numbers with no owner step (spec 6.12, M7), and never makes two videos that look alike (anti-goal "looks recycled").

**Architecture:** `tc results` pulls public stats daily (YouTube Data API key) for every pack matched to an upload; matches uploads to packs by exact title (fallback: duration ± 2 s) and stores `youtube_id` in `job.json`; compares each video with the channel's own baseline; turns clear findings into rules (`tc learn … --why "results: <id>"`) and writes `taste/retros/<id>.md`. `tc fingerprint` stores each finished video's palette, set list, shot-size mix and hook type; the art-direction stage refuses a new video that is too close to an earlier one.

**Tech Stack:** Python `tc` (pytest), `tc/http.py` (no new dependencies), the YouTube Data API v3 (public endpoints, API key only).

**Spec:** `docs/superpowers/specs/2026-11-21-2d-autonomous-agent-design.md` (6.11 second paragraph, 6.12, M7, anti-goals)

## Global Constraints

- Free only (r7): YouTube Data API key (`YOUTUBE_API_KEY` in `.env`, owner step — not set yet); quota-aware (≤ 2,000 units/day).
- No owner step; the optional Analytics sign-in is asked once, later.
- Channel id stored once in `.env` (`TC_CHANNEL_ID`) — there is no channel yet (owner).
- Rules learned from results carry `--why "results: <id>"` and can be retired (`tc retire`).
- Never print keys.

## Review Focus

1. **A wrong match** (two uploads with similar titles, a re-upload) attaches stats to the wrong job → `test_match_prefers_exact_title_then_duration`.
2. **A rule learned from noise** (one video, tiny numbers) → `test_no_rule_below_min_videos_and_views`.
3. **Quota exhaustion** mid-run leaves half-written stats → `test_results_run_is_atomic_per_video`.
4. **A fingerprint check that blocks everything** (threshold too strict for one shared palette family) → `test_fingerprint_allows_same_brand_different_sets`.
5. **No channel / no key** → clear "owner step" message, exit 0, nothing written → `test_results_without_keys_is_a_noop`.

---

### Task 1: upload matching (`tc results match`) — pure matcher + job.json `youtube_id`
### Task 2: daily stats + baseline (`tc results pull`) — views/likes/comments/views-per-hour vs channel median
### Task 3: findings → rules + retros (`tc results learn`) — min 3 videos and a baseline gap ≥ 30 % before a rule
### Task 4: fingerprints (`tc fingerprint`) — palette (k-means of key stills), set ids, shot-size histogram, hook type; similarity gate in the artdir stage
### Task 5: Task Scheduler daily run + Telegram summary (only with `TC_TELEGRAM_*`)

Each task: failing tests first (the Review Focus tests live in the task that owns the code), implement, full suite, commit with explicit paths.

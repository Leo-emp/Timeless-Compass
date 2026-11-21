# Thumbnails + Upload Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every finished job gets two freshly drawn, self-checked thumbnails and a complete upload pack the owner uploads in ~2 minutes. This closes M4 for the first Short ("Come and Take Them").

**Architecture:** Thumbnails are drawn per job in `film/src/jobs/<slug>/thumb.ts` (pure SVG functions, same kit as the scenes) and rendered to JPG by a Node script, using the same page renderer as stills. `tc thumb` renders both variants and runs the measured checks (size, file size, 160 px readability, word count). The agent scores the thumbnail checklist (`tc qa ... thumbnail`). `tc pack` assembles `packs/<id>/` from the job (video, thumbnails, title, description with sources and the r12 note, tags, posting slot). It uploads to R2 and sends one Telegram message **only when** the Timeless Compass keys exist in `.env`; otherwise it keeps the pack locally and says so.

**Tech Stack:** Python 3.14 (`tc` CLI, pytest, Pillow, boto3 already installed), Node + puppeteer-core (existing `film/scripts/lib/page.mjs`), TypeScript kit.

**Spec:** `docs/superpowers/specs/2026-11-21-2d-autonomous-agent-design.md` (sections 6.9, 6.11, M4, M6)

## Global Constraints

- Thumbnails: long 1280×720, Shorts 1080×1920; drawn fresh per video (r17, r21); ≤ 3 big words; readable at 160 px; two variants (a, b) for Test & Compare; must match what the video delivers.
- YouTube's thumbnail file limit: ≤ 2 MB, JPG.
- Pack on R2 under `packs/<id>/`: `video.mp4`, `thumbnail_a.jpg`, `thumbnail_b.jpg`, `title.txt`, `description.txt` (sources, chapters for long videos, the r12 note), `tags.txt`, `posting.txt` (6.11).
- r12 note text is exactly `Some dialogue is dramatised.` (`tc/packaging.py DRAMATISED_NOTE`).
- Timeless Compass never shares buckets, keys or code with CapitalCode or Luminous Will. New env names: `TC_R2_ACCOUNT_ID`, `TC_R2_ACCESS_KEY_ID`, `TC_R2_SECRET_ACCESS_KEY`, `TC_R2_BUCKET`, `TC_TELEGRAM_BOT_TOKEN`, `TC_TELEGRAM_CHAT_ID`.
- Never print secret values. Commit with explicit paths only. `packs/` is git-ignored.
- Text is drawn as vector paths (kit `text.ts`); never load fonts at render time.

## Review Focus

1. **A thumbnail word count that counts the drawn text wrongly** (e.g. a date card counted as words, or words hidden in a path): the checker must count the words the module DECLARES and the module must draw only those → `test_thumb_words_declared_and_capped` (Task 2).
2. **A pack built from a stale or missing master** (video older than the latest mux, or no thumbnails): pack must refuse → `test_pack_refuses_missing_parts` (Task 3).
3. **Secrets leaking into pack files or logs** (description built from env, or an error printing the key) → `test_pack_never_writes_env_values` (Task 3).
4. **Upload attempted with half the keys set** (bucket set but no secret): must skip cleanly with a clear message, not crash mid-upload → `test_upload_needs_all_keys` (Task 3).
5. **The description missing the sources or the r12 note when the script has dramatised lines** → `test_description_has_sources_and_note` (Task 3).

---

### Task 1: Thumbnail renderer

**Files:**
- Create: `film/scripts/thumb.mjs`
- Modify: `film/scripts/lib/page.mjs` (only if `renderToPng` cannot already write JPG; otherwise convert in Python)
- Test: `tests/test_thumb.py`

**Interfaces:**
- Produces: `node film/scripts/thumb.mjs <slug> <a|b> <out.png>` → renders `THUMBS[variant]()` from `film/src/jobs/<slug>/thumb.ts` at `THUMB_SIZE` (`{w, h}` exported by the module), and prints JSON `{"words": [...], "w":..,"h":..}` from the module's `WORDS[variant]`.
- Module contract for `thumb.ts`: `export const THUMB_SIZE = {w, h}`, `export const WORDS: Record<'a'|'b', string[]>`, `export const THUMBS: Record<'a'|'b', () => string>` (an SVG string).

- [ ] **Step 1: Write the failing test** `test_thumb_script_renders_fixture` — a tiny fixture module `tests/fixtures/thumb_fixture/thumb.ts` (copied to `film/src/jobs/_thumb_fixture/` by the test, removed after) with a 64×36 red rect and `WORDS = {a: ['HI'], b: []}`; running the script yields a 64×36 PNG whose centre pixel is red, and stdout JSON words `['HI']`. Skip the test when `node` is missing.
- [ ] **Step 2: Run it, expect FAIL** (script missing). `python -m pytest tests/test_thumb.py -q`
- [ ] **Step 3: Implement `thumb.mjs`** by bundling the module with esbuild (as `jobstill.mjs` does) and calling `renderToPng` with `W/H` from `THUMB_SIZE`.
- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Commit** `film/scripts/thumb.mjs tests/test_thumb.py tests/fixtures/thumb_fixture/thumb.ts`.

### Task 2: `tc thumb` — render both variants + measured checks

**Files:**
- Create: `tc/thumb.py` (register command `thumb`)
- Modify: `tc/cli.py` (`_load_commands` gets `thumb`)
- Test: `tests/test_thumb.py`

**Interfaces:**
- Produces: `thumb_problems(img: PIL.Image, words: list[str], kind: str, file_bytes: int) -> list[str]`; `tc thumb <job>` → writes `jobs/<id>/thumb/thumbnail_a.jpg`, `thumbnail_b.jpg`, `thumb/report.json`; exit 1 on any problem.
- Checks: exact size (long 1280×720, short 1080×1920); JPG ≤ 2 MB (quality steps 92→70 until it fits); `len(words) ≤ 3` and each word ≤ 12 letters; readability at 160 px wide: the 160 px downscale's RMS contrast ≥ 0.18 (luminance 0..1) and not a flat image (std of luminance ≥ 0.12); the two variants differ (mean abs diff ≥ 0.05) so Test & Compare tests something.

- [ ] **Step 1: Failing tests** `test_thumb_words_declared_and_capped` (4 words → problem "more than 3 words"), `test_thumb_size_checked` (1280×719 → problem), `test_thumb_flat_image_fails_readability` (grey image → problem), `test_thumb_variants_must_differ`.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** `thumb_problems`, `variants_differ(a, b) -> bool`, and the command (render via Task 1 script, convert PNG→JPG with Pillow).
- [ ] **Step 4: Run all tests, expect PASS.**
- [ ] **Step 5: Commit** `tc/thumb.py tc/cli.py tests/test_thumb.py`.

### Task 3: `tc pack` — assemble, (optionally) upload, notify

**Files:**
- Create: `tc/pack.py` (register command `pack`)
- Modify: `tc/cli.py`, `.gitignore` (`/packs/`)
- Test: `tests/test_pack.py`

**Interfaces:**
- Consumes: `jobs/<id>/master.mp4`, `jobs/<id>/thumb/thumbnail_{a,b}.jpg`, `jobs/<id>/qa/thumbnail.json` (passed), `jobs/<id>/packaging.json` (picked title) or `--title`, `jobs/<id>/sources.json`, `jobs/<id>/script.md`, `jobs/<id>/upload.json` (tags + description base, written by the agent).
- Produces: `build_pack(job_dir: Path, out_root: Path) -> Path` (returns `packs/<id>/`); `pack_problems(job_dir) -> list[str]`; `r2_config(env: dict) -> dict | None` (None unless all four TC_R2_* are set); `upload_pack(pack_dir, cfg)`; `notify(text, env) -> bool` (False when TC_TELEGRAM_* missing); `posting_slot(kind: str, now: datetime) -> str` (long: next Tue/Sat 17:00 UTC; short: next day 15:00 UTC — the spec's starting cadence, results loop tunes later).
- description.txt = base + "\n\nSources:\n" + one line per source (`title — url or citation`) + r12 note via `packaging.build_description`.

- [ ] **Step 1: Failing tests** `test_pack_refuses_missing_parts` (no master / no thumbs / thumbnail qa not passed / master older than mix.wav → each a problem), `test_description_has_sources_and_note`, `test_pack_never_writes_env_values` (set fake `TC_R2_SECRET_ACCESS_KEY=sekrit123` in env; no pack file contains it), `test_upload_needs_all_keys` (3 of 4 keys → `r2_config` None), `test_posting_slot_long_and_short`, `test_pack_files_complete` (the 7 files exist; video copied byte-identical).
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.** R2 via boto3 S3 client, endpoint `https://<account>.r2.cloudflarestorage.com`; Telegram via `tc/http.py`; both wrapped so a failure prints a one-line reason without the key and exits non-zero only for upload errors (missing keys = "kept locally" exit 0).
- [ ] **Step 4: Run all tests, expect PASS.**
- [ ] **Step 5: Commit** `tc/pack.py tc/cli.py .gitignore tests/test_pack.py`.

### Task 4: The Short's thumbnails + pack (closes M4)

**Files:**
- Create: `film/src/jobs/20261121_0919_come_and_take_them_thermopylae/thumb.ts`, `jobs/<id>/upload.json`, `jobs/<id>/packaging.json` (via `tc packaging`)
- Modify: `proof/README.md`, `.claude/skills/timeless/SKILL.md` (thumb + pack steps)

- [ ] **Step 1:** `tc packaging` with 10+ titles; pick one that passes and matches the video.
- [ ] **Step 2:** Draw `thumb.ts` (1080×1920). Variant a: Leonidas large, defiant, spear up, the endless Persian host behind him, words `TAKE THEM` (the reply the video pays off). Variant b: a different composition — the tiny red Spartan line in the pass facing the huge army, Xerxes looming in the sky, words `ONE LAST CHANCE` (the hook's offer). No numbers that are not in `sources.json`.
- [ ] **Step 3:** `tc thumb <id>` passes; view both at full size and at 160 px; score `tc qa <id> thumbnail` honestly (bar 90).
- [ ] **Step 4:** `tc pack <id>` builds `packs/<id>/`; check every file by hand.
- [ ] **Step 5:** Update `proof/README.md` + SKILL.md; commit explicit paths; push.

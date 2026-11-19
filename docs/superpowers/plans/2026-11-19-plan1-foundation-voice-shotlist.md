# Timeless Compass: Plan 1 (Foundation, Topic/Packaging, Script, Voice, Shot List) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the old pipeline with the `tc` agent foundation and deliver milestones M0 + M1: a topic picked by
demand → title/thumbnail brief → validated film-structure script → mastered Lewis narration with real word timings →
a validated shot list JSON, all resumable per job and driven by the `/timeless` skill.

**Architecture:** `tc` is a deterministic Python CLI (tools, validators, file formats, API calls). Claude, following
`.claude/skills/timeless/SKILL.md`, does the judgement work (research, writing titles/scripts/shots) and calls `tc`
to check and record it. Every job lives in `jobs/<id>/` with a `job.json` stage ledger. Later plans add Blender
building (M2), the render farm (M3), edit/audio (M4) and learning/archive (M6).

**Tech Stack:** Python 3.14, pytest, curl (all HTTP goes through curl: Python's own HTTP client hung on this
machine), ffmpeg 9, faster-whisper 1.2.1 (installed in the user site-packages, so run `python` **without** `-I` for
alignment), Azure Speech REST, YouTube Data API v3.

**Spec:** `docs/superpowers/specs/2026-11-19-cinematic-agent-design.md`

## Global Constraints

- Narrator voice: `en-US-LewisMultilingualNeural`; alternative `en-US-Jimmie:DragonHDFlashLatestNeural` (one config value). Narrator only, no character voices.
- SSML pace: `<prosody rate="-4%">`; breaks only at breaths/tension.
- Voice master chain (exact): `highpass=f=70,equalizer=f=160:t=q:w=1:g=2,equalizer=f=3500:t=q:w=1.2:g=1.5,acompressor=threshold=-22dB:ratio=3:attack=8:release=120:makeup=4,loudnorm=I=-14:TP=-1.0:LRA=7`, 48 kHz.
- Long video 10–12 min; Shorts 45–60 s with their own script. 24 fps, 16:9 (Shorts 9:16).
- Script narration at ~150 words/min → long script **1,500–1,800 words**; Short **110–150 words**.
- Re-hook / open-loop marker at least every **90 s** (~225 words); visual change every **3–7 s** (shot duration 3.0–7.0 s; up to 8.0 s only if flagged `"hold": true`).
- Title ≤ **60** characters. No on-screen captions; on-screen text only as place/date cards and map labels.
- Zero spend: free tiers only. No secrets in the repo (repo is **public**). Keys live in `timeless-compass/.env` (git-ignored); the Azure key may be copied there from `capitalcode/.env.local` (owner allows copying own keys; never print them).
- Code is copied in spirit from CapitalCode, never imported from it.
- Every file heavily commented for a beginner reader (owner rule).
- Commits: **only when the owner asks.** Each task ends with a suggested commit; batch them if the owner prefers.
- Never rewrite files with PowerShell Get/Set-Content.

## Review Focus

1. **A script line with no shot:** the literal rule must catch it → `test_shotlist_rejects_uncovered_line` (Task 11).
2. **Word timings that don't match the script** (whisper mishears names like "Themistocles") → alignment must use sequence matching, not exact words, and report unmatched spans → `test_align_tolerates_misheard_names` (Task 10).
3. **Azure returns a non-audio body** (quota, bad key, bad SSML) and it gets saved as an `.mp3` → `test_synth_raises_on_error_body` (Task 9).
4. **Resuming a job after a crash mid-stage** must not redo finished stages or skip the broken one → `test_next_stage_after_failed_stage` (Task 3).
5. **YouTube API quota exhausted / no key** → `tc topics` fails with a clear message, not a traceback → `test_topics_without_key_is_friendly` (Task 6).

---

## File Structure

```
timeless-compass/
  tc/__init__.py          # version
  tc/__main__.py          # `python -m tc` -> cli.main()
  tc/cli.py               # argparse subcommands, thin: parse -> call module -> print
  tc/paths.py             # ROOT, JOBS, TASTE, LIBRARY, env file path
  tc/config.py            # load .env + defaults (voice, rates, limits)
  tc/http.py              # curl wrapper: get_json(), post_bytes()
  tc/jobs.py              # Job dataclass, STAGES, create/load/save/next_stage/mark
  tc/learning.py          # owner rules: add_rule(), list_rules()
  tc/doctor.py            # Check dataclass + run_checks()
  tc/youtube.py           # YouTube Data API client (search, videos, channels)
  tc/topics.py            # score_candidates() + rank()
  tc/packaging.py         # check_titles()
  tc/script.py            # parse_script(), check_script()
  tc/voice.py             # build_ssml(), synthesize(), master()
  tc/align.py             # word timings via faster-whisper + sequence matching
  tc/shots.py             # Shot dataclass, load/check shot list, fill durations from timings
  tc/run.py               # status/next-action report for a job (what Claude should do next)
  tests/...               # one test file per module, fixtures in tests/fixtures/
  .claude/skills/timeless/SKILL.md      # the agent playbook
  ~/.claude/skills/timeless/SKILL.md    # launcher -> repo playbook (like capitalcode)
  taste/rules.md, taste/learning.json   # owner rules
  jobs/                   # git-ignored
  library/                # manifests only (later plans)
```

---

### Task 1: Clean slate + `tc` skeleton (M0)

**Files:**
- Delete (after tag): `api_server.py config.py database.py flux_images.py main.py scheduler.py script_generator.py video_assembler.py video_assembler_ffmpeg.py visuals.py voiceover.py youtube_uploader.py requirements.txt generated_history.json timeless_compass.db dashboard/ assets/ output/ temp/ "spike$n.png"`
- Create: `tc/__init__.py`, `tc/__main__.py`, `tc/cli.py`, `tc/paths.py`, `requirements.txt`, `pytest.ini`, `tests/test_cli.py`
- Modify: `.gitignore` (add `jobs/`, `spike/frames*/`, `spike/**/*.png`, `spike/**/*.mp4`, `spike/**/*.mp3`, `spike/**/*.wav`, `*.blend1`)

**Interfaces:**
- Produces: `tc.paths.ROOT: Path`, `JOBS: Path` (`ROOT/"jobs"`), `TASTE: Path`, `LIBRARY: Path`, `ENV_FILE: Path` (`ROOT/".env"`); `tc.cli.main(argv: list[str] | None = None) -> int` with subcommand registry `COMMANDS: dict[str, Callable[[argparse.Namespace], int]]`.

- [ ] **Step 1:** Tag the old pipeline: `git -C C:/Users/User/timeless-compass tag old-pipeline-final 3b83f2d` → `git tag -l old-pipeline-final` prints it. (Pushing the tag waits for the owner.)
- [ ] **Step 2:** Write the failing test `tests/test_cli.py::test_help_lists_commands`: run `main(["--help"])` (catch `SystemExit`), assert the captured help contains `doctor`, `new`, `status`, `learn`.
- [ ] **Step 3:** Run `cd C:/Users/User/timeless-compass && python -m pytest tests/test_cli.py -v` → FAIL (no module `tc`).
- [ ] **Step 4:** Remove the old files listed above (`git rm -r` for tracked ones, delete untracked ones). Create the skeleton with `argparse`, subparsers wired from `COMMANDS` (each command module registers later; Task 1 registers stubs for `doctor`, `new`, `status`, `learn` that print "not built yet" and return 1). `requirements.txt`: `pytest`, `numpy`, `faster-whisper` (comment: faster-whisper already in user site-packages).
- [ ] **Step 5:** Run the test → PASS. Run `python -m tc --help` → lists the 4 commands.
- [ ] **Step 6 (suggested commit):** `chore: replace old stock-footage pipeline with tc skeleton (old code tagged old-pipeline-final)`

### Task 2: Config + env loading

**Files:** Create `tc/config.py`, `tests/test_config.py`

**Interfaces:**
- Produces: `load_env(path: Path = ENV_FILE) -> dict[str, str]` (parses `KEY=VALUE`, strips quotes and `\r`, ignores `#` lines, never prints values); `@dataclass Config` with fields `voice: str = "en-US-LewisMultilingualNeural"`, `voice_rate: str = "-4%"`, `words_per_min: int = 150`, `long_words: tuple[int,int] = (1500, 1800)`, `short_words: tuple[int,int] = (110, 150)`, `rehook_max_s: int = 90`, `shot_s: tuple[float,float] = (3.0, 7.0)`, `hold_max_s: float = 8.0`, `title_max: int = 60`, `azure_key: str | None`, `azure_region: str | None`, `youtube_key: str | None`; `get_config() -> Config` (env overrides: `TC_VOICE`).

- [ ] **Step 1:** Failing tests: `test_load_env_strips_quotes_and_cr` (file `A="x"\r\n#c\nB=y` → `{"A":"x","B":"y"}`); `test_config_defaults` (empty env → voice `en-US-LewisMultilingualNeural`, `long_words == (1500, 1800)`); `test_tc_voice_override` (`TC_VOICE=en-US-Jimmie:DragonHDFlashLatestNeural` → `cfg.voice` equals it).
- [ ] **Step 2:** `python -m pytest tests/test_config.py -v` → FAIL.
- [ ] **Step 3:** Implement. Env keys read: `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`, `YOUTUBE_API_KEY`, `TC_VOICE`.
- [ ] **Step 4:** Tests PASS. Then copy `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` from `C:/Users/User/capitalcode/.env.local` into `timeless-compass/.env` with a small Python one-off (no printing); confirm by `python -c "from tc.config import get_config as g; c=g(); print(bool(c.azure_key), c.azure_region)"` → `True eastus`.
- [ ] **Step 5 (suggested commit):** `feat(tc): config and env loading`

### Task 3: Jobs and the stage ledger

**Files:** Create `tc/jobs.py`, `tests/test_jobs.py`; register `new` and `status` in `tc/cli.py`

**Interfaces:**
- Produces: `STAGES = ["topic", "packaging", "research", "script", "voice", "align", "shots"]` (Plan 1 scope; later plans append `library`, `build`, `stills`, `render`, `edit`, `qa`, `package`, `archive`); `@dataclass Job(id: str, title: str, kind: str  # "long" | "short", created: str, stages: dict[str, dict])` where each stage dict is `{"status": "todo"|"done"|"failed", "at": iso|None, "note": str}`; `create_job(seed: str, kind: str = "long", now: datetime | None = None) -> Job` (id `yyyymmdd-hhmm-<slug>`, slug from seed, max 40 chars, ascii-lower-hyphen); `load_job(id: str) -> Job`; `save_job(job: Job) -> None` (writes `jobs/<id>/job.json` atomically: temp file + replace); `mark(job: Job, stage: str, status: str, note: str = "") -> Job`; `next_stage(job: Job) -> str | None` (first stage not `done`; a `failed` stage is returned again); `job_dir(id: str) -> Path`.
- CLI: `tc new "<seed>" [--short]` prints the id; `tc status <id>` prints one line per stage.

- [ ] **Step 1:** Failing tests: `test_create_job_id_format` (seed "The Trap at Salamis!", fixed now 2026-11-19 03:10 → id `20261119-0310-the-trap-at-salamis`); `test_save_load_roundtrip` (tmp `JOBS` via monkeypatch); `test_next_stage_after_failed_stage` (topic done, packaging failed → `next_stage == "packaging"`); `test_all_done_returns_none`; `test_mark_rejects_unknown_stage` (raises `ValueError`).
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement; `JOBS` read from `tc.paths` at call time so tests can monkeypatch it.
- [ ] **Step 4:** Run → PASS. `python -m tc new "test topic"` creates `jobs/<id>/job.json`; `python -m tc status <id>` shows 7 `todo` lines. Delete the test job.
- [ ] **Step 5 (suggested commit):** `feat(tc): jobs with resumable stage ledger`

### Task 4: Owner rules (learning, part 1)

**Files:** Create `tc/learning.py`, `taste/rules.md` (header only), `taste/learning.json` (`{"rules": []}`), `tests/test_learning.py`; register `learn` and `rules` in the CLI

**Interfaces:**
- Produces: `add_rule(text: str, why: str = "", applies_to: list[str] | None = None, now: datetime | None = None) -> dict` (assigns `id` = `r1`, `r2`, …; appends to `learning.json` and a `## r<N> (date)` block with **Rule / Why / Applies to** lines to `rules.md`); `list_rules(stage: str | None = None) -> list[dict]` (filter by `applies_to` containing stage, or all). `applies_to` values are stage names from `jobs.STAGES` plus `"all"`.
- CLI: `tc learn "<rule>" [--why "..."] [--stage script --stage voice]`; `tc rules [--stage script]`.

- [ ] **Step 1:** Failing tests: `test_rule_ids_increment` (two adds → `r1`, `r2`); `test_rules_md_contains_rule_and_why`; `test_filter_by_stage` (rule for `script`, rule for `all` → `list_rules("script")` returns both, `list_rules("voice")` returns only the `all` one); `test_unknown_stage_rejected`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement (TASTE dir from `tc.paths`, monkeypatchable). **Step 4:** Run → PASS.
- [ ] **Step 5:** Seed the owner's existing decisions as rules r1–r8 via the CLI: narrator only; serious tone; no on-screen captions; era accuracy; growth first (views/CTR/retention); real people never as exact face copies; no spend; laptop stays light. Then `python -m tc rules` lists 8.
- [ ] **Step 6 (suggested commit):** `feat(tc): owner rules store (tc learn / tc rules)`

### Task 5: `tc doctor`

**Files:** Create `tc/doctor.py`, `tests/test_doctor.py`; register `doctor`

**Interfaces:**
- Consumes: `get_config()`, `tc.http.get_json` (Task 6 creates `tc/http.py`; build it here first, Task 6 reuses it): `get_json(url: str, headers: dict[str,str] | None = None, timeout: int = 60) -> dict | list` and `post_bytes(url: str, body: bytes, headers: dict[str,str], timeout: int = 180) -> tuple[int, bytes, str]` (status, body, content-type), both via `curl` subprocess; raise `HttpError(status, snippet)` on non-2xx for `get_json`.
- Produces: `@dataclass Check(name: str, ok: bool, detail: str, required: bool = True)`; `run_checks(runner=subprocess.run) -> list[Check]` covering: python ≥ 3.12, `ffmpeg` on PATH, `curl` on PATH, `faster_whisper` importable (non-isolated python), Blender at `C:/Users/User/tools/blender-5.3.0-windows-x64/blender.exe` (required=False in Plan 1), MPFB folder exists (required=False), Azure key+region present, Azure voices endpoint reachable (status 200), YouTube key present (required=False until Task 6 is used), free disk on C: ≥ 10 GB (warn below). `tc doctor` prints ✓/✗ per check and returns 1 if any **required** check fails.

- [ ] **Step 1:** Failing tests with a fake runner/fake http: `test_missing_azure_key_fails_required`; `test_low_disk_warns_not_fails` (8 GB → `ok=False, required=False`); `test_all_good_returns_zero`; `test_http_error_raises` (fake curl returning `404`).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement (`shutil.disk_usage("C:/")`, `shutil.which`). **Step 4:** Run → PASS; real `python -m tc doctor` shows ✓ for python/ffmpeg/curl/azure.
- [ ] **Step 5 (suggested commit):** `feat(tc): doctor health checks + curl http helper`

### Task 6: Topic demand scoring (growth engine)

**Files:** Create `tc/youtube.py`, `tc/topics.py`, `tests/test_topics.py`, `tests/fixtures/yt_search.json`, `tests/fixtures/yt_videos.json`, `tests/fixtures/yt_channels.json`; register `topics`

**Interfaces:**
- Consumes: `get_json`, `get_config().youtube_key`.
- Produces: `search_videos(query: str, key: str, max_results: int = 25, published_after: str | None = None) -> list[dict]` (`search.list` part=snippet type=video); `video_stats(ids: list[str], key: str) -> dict[str, dict]` (`videos.list` statistics,contentDetails); `channel_stats(ids: list[str], key: str) -> dict[str, dict]` (`channels.list` statistics).
- `score_candidates(seeds: list[str], fetch) -> list[dict]` where `fetch(seed) -> list[{"video_id","title","channel_id","views","channel_subs","published","duration_s"}]`; per seed computes `demand` = median views of top results, `outlier` = max(views / max(channel_subs, 1000)), `freshness_gap` = days since the newest result over 100k views (capped 730), and `score = 0.45*norm(demand) + 0.35*norm(outlier) + 0.20*norm(freshness_gap)` (min-max normalised across seeds, 0..1); returns seeds sorted by score with the three parts, the top 3 example videos and the raw numbers.
- CLI: `tc topics <job> "seed 1" "seed 2" …` → writes `jobs/<id>/topics.json` and prints the ranked table; marks stage `topic` done only when the owner's pick is recorded via `tc topics <job> --pick N`.

- [ ] **Step 1:** Failing tests: `test_score_orders_by_formula` (3 fake seeds with known numbers → expected order and `score` values to 3 decimals); `test_outlier_uses_subscriber_floor` (channel with 0 subs uses 1000); `test_topics_without_key_is_friendly` (no key → CLI exit 2, message contains "YOUTUBE_API_KEY" and "console.cloud.google.com", no traceback); `test_parse_fixtures` (search+videos+channels fixtures → fetch rows with ints).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement (duration from ISO8601 `PT#M#S`; skip Shorts under 180 s for long-form demand). **Step 4:** Run → PASS.
- [ ] **Step 5:** Owner setup (one-time, free): create a YouTube Data API v3 key in Google Cloud and add `YOUTUBE_API_KEY=` to `.env`. Until then `tc topics` explains this and exits 2.
- [ ] **Step 6 (suggested commit):** `feat(tc): topic demand scoring from YouTube data`

### Task 7: Packaging check (titles + thumbnail brief)

**Files:** Create `tc/packaging.py`, `tests/test_packaging.py`; register `packaging`

**Interfaces:**
- Produces: `check_titles(titles: list[str], max_len: int = 60) -> list[dict]` → per title `{"title", "ok", "problems": [...], "length"}`; problems: `"too long"` (> max_len), `"all caps"` (> 50% of letters uppercase), `"banned word: <w>"` for `["shocking", "you won't believe", "insane", "gone wrong", "!!!"]` (case-insensitive), `"no curiosity hook"` when none of: a number, a question mark, or one of `["secret", "never", "only", "why", "how", "last", "lie", "trap", "hidden", "forgotten"]`.
- `save_packaging(job: Job, titles: list[str], thumbnails: list[str], pick: int | None) -> Path` writes `jobs/<id>/packaging.json` `{"titles": [...checked...], "thumbnail_concepts": [...], "picked": int|None}`; stage `packaging` is done when `picked` is set and that title is `ok`.
- CLI: `tc packaging <job> --titles titles.txt --thumbs thumbs.txt [--pick N]`.

- [ ] **Step 1:** Failing tests: `test_too_long_title` (61 chars → problem `too long`); `test_banned_word`; `test_good_title_ok` ("The Trap That Saved Greece" → ok); `test_pick_must_be_ok_title` (picking a failing title raises `ValueError`).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5 (suggested commit):** `feat(tc): title and thumbnail packaging check`

### Task 8: Script format + checker

**Files:** Create `tc/script.py`, `tests/test_script.py`, `tests/fixtures/script_ok.md`; register `script`

**Script file format** (`jobs/<id>/script.md`, written by Claude):
```
## cold_open
Line text. [src: herodotus-8.75]
At dawn, the King of Persia sat on a golden throne. [src: herodotus-8.90] {loop}
## title
## world
...
```
Section headers must appear in this order: `cold_open, title, world, tension, turning_point, climax, aftermath, outro` (long) or `hook, build, payoff` (short). One narration line per text line; `[src: id]` cites `jobs/<id>/sources.json` ids; `{loop}` marks an open loop / re-hook; `{beat}` marks a held silence. The `title` section may be empty (title card).

**Interfaces:**
- Produces: `@dataclass Line(section: str, index: int, text: str, sources: list[str], loop: bool, beat: bool)`; `parse_script(text: str) -> list[Line]` (strips the markers from `text`); `check_script(lines: list[Line], kind: str, sources: dict, cfg: Config) -> list[str]` (problems; empty = pass): wrong/missing section order; word count outside `cfg.long_words` / `cfg.short_words`; any stretch longer than `cfg.rehook_max_s * cfg.words_per_min / 60` words (= 225) without a `{loop}` (long only, after `cold_open`); a line with a factual claim but no `[src: …]` (rule: every line in `world`, `tension`, `turning_point`, `climax`, `aftermath` needs ≥ 1 source); a `[src: id]` not in `sources`; a line over 30 words ("too long for the ear").
- CLI: `tc script <job>` prints problems; on pass marks stage `script` done (owner approval is recorded separately with `tc script <job> --approve`, required before `voice`).

- [ ] **Step 1:** Failing tests: `test_parse_markers` (line with `[src: a] {loop}` → sources `["a"]`, loop True, clean text); `test_section_order_enforced`; `test_word_count_bounds_long` (1,200 words → problem mentions `1500`); `test_rehook_gap` (260 words without `{loop}` → problem mentions `225`); `test_unknown_source`; `test_fixture_passes` (`script_ok.md` + matching sources → `[]`).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5 (suggested commit):** `feat(tc): film-structure script checker`

### Task 9: Voice: SSML, Azure synth, master

**Files:** Create `tc/voice.py`, `tests/test_voice.py`; register `voice`

**Interfaces:**
- Consumes: `parse_script`, `get_config`, `post_bytes`.
- Produces: `build_ssml(lines: list[Line], voice: str, rate: str) -> list[str]` (one SSML document per **section**, Azure limit-safe; XML-escape text; `{beat}` → `<break time="800ms"/>`, sentence ends inside a line keep natural pauses; wrapper exactly `<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US"><voice name="{voice}"><prosody rate="{rate}">…</prosody></voice></speak>`); `synthesize(ssml: str, out: Path, cfg: Config, post=post_bytes) -> Path` (POST to `https://{region}.tts.speech.microsoft.com/cognitiveservices/v1`, headers `Ocp-Apim-Subscription-Key`, `Content-Type: application/ssml+xml`, `X-Microsoft-OutputFormat: riff-48khz-16bit-mono-pcm`, `User-Agent: timeless-compass`; raise `VoiceError` if status ≠ 200 or content-type not `audio/*`; never write the error body as audio); `master(raw: Path, out: Path) -> dict` (concat section wavs → ffmpeg chain from Global Constraints → `voice.wav` 48 kHz; returns `{"lufs": float, "peak_db": float, "duration_s": float}` measured with `ebur128=peak=true`).
- Output: `jobs/<id>/voice/section_XX.wav`, `jobs/<id>/voice.wav`, `jobs/<id>/voice.json` (sections, durations, loudness).
- CLI: `tc voice <job>` (requires script approved) → stage `voice` done.

- [ ] **Step 1:** Failing tests: `test_ssml_escapes_and_wraps` (`"A & B"` → `A &amp; B`, contains the exact wrapper and voice name); `test_beat_becomes_break`; `test_one_doc_per_section`; `test_synth_raises_on_error_body` (fake post returns `(401, b'{"error"}', "application/json")` → `VoiceError`, no file written); `test_master_measures_loudness` (1 s generated sine via ffmpeg → result has `lufs` between -16 and -12).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Real smoke test on a 3-line throwaway script → `voice.wav` plays; `voice.json` lufs ≈ -14 (±1).
- [ ] **Step 6 (suggested commit):** `feat(tc): Azure narration with mastering`

### Task 10: Word timings (alignment)

**Files:** Create `tc/align.py`, `tests/test_align.py`; register `align`

**Interfaces:**
- Consumes: `voice.wav`, parsed script lines.
- Produces: `transcribe(wav: Path) -> list[dict]` (faster-whisper `small.en`, CPU, int8, `word_timestamps=True`, `vad_filter=False`, `condition_on_previous_text=False`, audio decoded with ffmpeg to 16 kHz mono f32, **no** script prompt) → `[{"w","s","e"}]`; `align_lines(lines: list[Line], heard: list[dict]) -> list[dict]` → per line `{"section","index","start","end","matched_ratio"}` using `difflib.SequenceMatcher` on normalised word lists (lowercase, strip punctuation), interpolating start/end for unmatched words from neighbours; flag lines with `matched_ratio < 0.6`.
- Output: `jobs/<id>/timings.json` `{"words": [...], "lines": [...], "flagged": [indexes]}`. CLI `tc align <job>` (run with plain `python`, not `-I`) → stage `align` done when no line has `start is None`.

- [ ] **Step 1:** Failing tests (pure, no whisper): `test_align_exact_words`; `test_align_tolerates_misheard_names` ("Themistocles sent" heard as "the mistocles sent" → line still gets start/end, ratio ≥ 0.6); `test_unmatched_line_interpolated` (a line whose words are all missing gets start = previous end, end = next start); `test_lines_monotonic` (starts never decrease).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS; real run on Task 9's smoke `voice.wav` gives sensible times.
- [ ] **Step 5 (suggested commit):** `feat(tc): word timings with whisper + sequence alignment`

### Task 11: Shot list schema + checker

**Files:** Create `tc/shots.py`, `tests/test_shots.py`; register `shots`

**Shot list file** (`jobs/<id>/shots.json`, written by Claude):
```json
{"shots": [{"id": "s001", "line": 0, "at": 0.0, "dur": null, "hold": false,
  "who": ["xerxes"], "where": "aigaleos_throne", "action": "sits, smiles, raises goblet",
  "expression": {"xerxes": "confident"}, "camera": {"move": "push_in", "lens_mm": 50, "from": "low_front"},
  "sfx": ["wind_high", "distant_oars"], "era": "greece_480bc", "card": null}]}
```
Camera moves allowed: `static, push_in, pull_out, pan_left, pan_right, tilt_up, tilt_down, track, orbit, crane_up, crane_down, handheld`. `card` is `null` or `{"text": "SALAMIS · 480 BC", "kind": "place_date"|"map_label"}` (no other on-screen text).

**Interfaces:**
- Consumes: `timings.json` lines.
- Produces: `@dataclass Shot` mirroring the JSON; `load_shots(path) -> list[Shot]`; `fill_timing(shots, line_times) -> list[Shot]` (shots of one line split that line's span evenly unless `dur` is given; `at` = cumulative); `check_shots(shots, lines, line_times, cfg) -> list[str]`: every script line index covered by ≥ 1 shot; duration in `cfg.shot_s` (or ≤ `cfg.hold_max_s` when `hold`); unknown camera move; `card.kind` not allowed; `who`/`where`/`era` empty; consecutive shots with identical `(where, camera.move, camera.from)` (anti-samey); total shot time within ±0.5 s of `voice.json` duration.
- CLI `tc shots <job>` → fills timing, writes back, prints problems; stage `shots` done on pass. Also writes `jobs/<id>/needs.json` = the set of all `who`, `where`, `era`, `sfx` values (input for Plan 2's library check).

- [ ] **Step 1:** Failing tests: `test_shotlist_rejects_uncovered_line`; `test_duration_bounds` (9.0 s without hold → problem; 7.5 s with hold → ok); `test_unknown_camera_move`; `test_caption_card_rejected` (`kind: "subtitle"` → problem); `test_samey_neighbours`; `test_fill_timing_splits_line` (line 0 spans 0–9 s with 2 shots → 4.5 s each); `test_needs_json_collects_assets`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5 (suggested commit):** `feat(tc): shot list schema, timing and checks`

### Task 12: The `/timeless` agent playbook + `tc next`

**Files:** Create `tc/run.py`, `tests/test_run.py`, `.claude/skills/timeless/SKILL.md`, `C:/Users/User/.claude/skills/timeless/SKILL.md` (launcher); register `next`

**Interfaces:**
- Consumes: `load_job`, `next_stage`, `list_rules`.
- Produces: `next_action(job: Job) -> dict` → `{"stage", "do": str, "command": str, "rules": [rule ids for that stage]}` with one entry per Plan 1 stage, e.g. `topic` → do "pick 6–10 seed topics in History or Secret Government Projects, then run", command `python -m tc topics <id> "…"`; `script` → do "research done; write jobs/<id>/script.md in the film structure", command `python -m tc script <id>`. CLI `tc next <id>` prints it.
- SKILL.md (exact sections): **Purpose** (one paragraph from spec §1); **Before every stage** (run `python -m tc rules --stage <stage>` and follow them; run `python -m tc next <id>`); **Stage guides** for topic, packaging, research (WebSearch; every fact into `sources.json` `{id: {"title","url","quote"}}`), script (structure from the spec §3 table and §6.0 retention rules; written for the ear; ≤ 30 words/line; serious tone; famous quotes spoken by the narrator), voice, align, shots (literal rule; era rule; 3–7 s; camera vocabulary; no captions); **Owner gates** (packaging pick, script approval); **Feedback** (any owner feedback → `python -m tc learn "…" --why "…" --stage …` before continuing); **Commands table**; **Never** list (no spend, no secrets printed, no commits unless asked, no character voices, no exact faces of real people, no PowerShell Get/Set-Content). Launcher: a short file pointing to the repo SKILL.md and saying "Run every command from C:\Users\User\timeless-compass", like CapitalCode's launcher.

- [ ] **Step 1:** Failing tests: `test_next_action_for_fresh_job_is_topic`; `test_next_action_includes_stage_rules` (rule with `applies_to=["script"]` appears when the next stage is `script`); `test_done_job_says_finished_plan1` (all stages done → `{"stage": None, "do": "Plan 1 stages complete: continue with library/build (Plan 2)"}`).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement `tc/run.py`; write both SKILL.md files. **Step 4:** Run → PASS; `python -m pytest -q` → all tests pass.
- [ ] **Step 5: M1 acceptance run (with the owner):** `/timeless` on a real topic: topics ranked (needs the YouTube key) → owner picks topic and title → research + script (owner approves) → `tc voice` → `tc align` → `tc shots` with no problems. Deliver `voice.wav` + `shots.json` summary to the owner.
- [ ] **Step 6 (suggested commit):** `feat: /timeless agent playbook and next-action guide (M1 complete)`

---

## Next plans (not in this plan)

- **Plan 2 (M2):** Blender library: cast (MPFB), wardrobe kits (scans/modelled + cloth sim), sets, motions (CMU → `cmu_mb`), stills renderer + contact sheet gate; Salamis slice.
- **Plan 3 (M3):** render farm (Kaggle notebook + GitHub matrix workflow + R2 upload, resumable shards, timing measurements).
- **Plan 4 (M4–M5):** edit/audio (timeline, SFX, music, grade, cards, master) + proof clip.
- **Plan 5 (M6–M7):** learning loop (ratings, retros, analytics), Telegram/R2 archive + cleanup, first full video, Shorts.

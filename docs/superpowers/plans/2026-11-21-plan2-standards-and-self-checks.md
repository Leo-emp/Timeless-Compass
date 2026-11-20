# Plan 2 — Standards + self-checks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (owner rule: no subagents for implementation). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Give the agent the written standards it draws and writes by (drawing standard, script + storytelling
standard) and every automatic gate that holds work back until it is production grade: story page check, scored
self-checks (story, still, motion, thumbnail), the fresh viewer GO/NO-GO, measured still checks, motion checks and
the era lock — wired into an autonomous stage ledger with no owner gates.

**Architecture:** Python `tc` gains one module per gate (`story`, `qa`, `viewer`, `stillcheck`, `motioncheck`,
`era`), each a pure checker + a thin command. The film kit tags what it draws (`data-role` attributes on faces,
hands, props, text), and `film/scripts/inspect.mjs` renders a scene still in headless Edge/Chrome and reads the
on-screen boxes of those tags, so geometry checks see exactly what the viewer sees.

**Tech Stack:** Python 3.12 + Pillow + pytest; TypeScript kit + vitest; esbuild (already in vite) + puppeteer-core 24.38.0.

**Spec:** `docs/superpowers/specs/2026-11-21-2d-autonomous-agent-design.md` — sections 6.2 (stages), 6.3, 6.5–6.6,
6.8 (natural flow check), 6.14 (story), rules r18, r20, r24, r27–r33.

## Global Constraints

- Owner rules r15–r35 apply; the bar for every scored self-check is **every item passes AND total ≥ 90/100** (spec 6.6, 6.14).
- No owner gates anywhere (r20): every gate is automatic; failures loop back to the agent.
- The viewer review is done by a **fresh agent that never saw the story page or the writing** (r27): its packet holds only what a viewer hears.
- Lengths (owner, 2026-11-21): long **1,900–2,300** narration words (12–15 min at 150 wpm); Short **300–420** words (2 to under 3 min).
- Re-hook spacing: every ≤ 90 s in long videos, every ≤ 30 s in Shorts (spec 6.14).
- Commit with explicit paths; heavily commented code; commit trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A self-check scored but an item silently missing** — the agent forgets one checklist item and still passes.
   Expect rejection → `test_score_rejects_missing_item` (Task 4).
2. **Viewer packet leaks the writer's intent** — section names, `{loop}` markers, `[src]` tags or the story page in
   the packet bias the viewer. Expect only spoken words and speaker names → `test_packet_has_no_tags_or_sections` (Task 5).
3. **A prop drawn in front of a face** passes because only boxes, not draw order, were compared. Expect "covers face"
   only for elements drawn after the face → `test_later_prop_covers_face_earlier_does_not` (Task 7).
4. **Real cuts flagged as snaps** in the motion check. Expect no snap at listed cut frames → `test_cut_is_not_a_snap` (Task 8).
5. **Old jobs break** when the stage list changes. Expect old job.json files to load with new stages as todo →
   `test_old_job_gets_new_stages` (Task 1).

---

### Task 1: Autonomous stage ledger + new lengths

**Files:** Modify `tc/jobs.py`, `tc/learning.py`, `tc/run.py`, `tc/config.py`, `tc/script.py`; Test `tests/test_jobs.py`, `tests/test_run.py`, `tests/test_script.py`

**Interfaces:**
- Produces: `jobs.STAGES = ["topic", "packaging", "research", "story", "script", "viewer", "voice", "align", "artdir", "cast", "shots", "draw", "stills", "motion", "thumbnail", "render", "mix", "pack", "archive", "results"]`;
  `learning.KNOWN = STAGES + ["build", "edit", "library", "package", "qa", "all"]` (old rule stage names stay valid);
  `run.GUIDE[stage] = (do, command)` for every stage, with **no "owner picks/approves" wording**;
  `Config.long_words = (1900, 2300)`, `Config.short_words = (300, 420)`, `Config.short_rehook_max_s = 30`.

- [ ] **Step 1: Failing tests:** `test_old_job_gets_new_stages` (a job.json with only the 7 old stages loads and
  `next_stage` returns the first not-done stage in the new order); `test_guide_covers_every_stage` (`set(GUIDE) == set(STAGES)`);
  `test_guide_never_waits_for_owner` (no GUIDE text contains "owner"); `test_short_needs_rehook_every_30s`
  (a 320-word Short with one `{loop}` at word 10 fails with "without a {loop} re-hook"); `test_long_word_range` (2,000 words passes the length check).
- [ ] **Step 2: Run** `python -m pytest tests/test_jobs.py tests/test_run.py tests/test_script.py` → FAIL.
- [ ] **Step 3: Implement.** Re-hook check applies to Shorts with `short_rehook_max_s` (skip the `hook` section like `cold_open`).
  GUIDE texts describe the autonomous action and the gate command of Tasks 3–9 (e.g. story → `python -m tc story {id}`).
- [ ] **Step 4: Run** the three files, then the full suite → PASS.
- [ ] **Step 5: Commit** `-- tc/jobs.py tc/learning.py tc/run.py tc/config.py tc/script.py tests/test_jobs.py tests/test_run.py tests/test_script.py`

### Task 2: The drawing standard — `docs/ART_BIBLE.md`

**Files:** Create `docs/ART_BIBLE.md`

- [ ] **Step 1: Write it** with these sections (spec 6.3; each rule concrete and checkable, with numbers):
  1 Construction (r16 numbers: head ≈ 40 % of height, outline `#2a1c13` 7 units characters / 4 backgrounds, one
  shade), 2 Composition (focal point, thirds, ≥ 5 depth layers, no tangents, nothing over faces, safe margins 3 %
  text / 1 % faces, Shorts composed for 9:16), 3 Light + atmosphere (six time-of-day grades with hex palettes,
  haze, rim light, cast shadows), 4 Detail density (no empty tile in the 8×6 detail map except intended sky/sea
  calm areas, background story moments per wide shot ≥ 3), 5 Era lock (r32: sheet items + don't-list), 6 Acting
  (six expressions, gesture-on-word, crowd variety: no two identical neighbours), 7 Text (only place/date + map
  labels, Cinzel, must fit its box), 8 Thumbnail rules (r21: 1280×720, ≤ 3 words, readable at 160 px, strong
  emotion, one striking object), 9 Reference ruler (strips stay in git-ignored `reference/`), 10 The still checklist
  (the exact items + weights of `qa.CHECKLISTS["still"]`, Task 4), 11 Beating the reference (light, depth, acting on
  the word, camera — what the reference lacks, measured 2026-11-21: new picture every ~5.5 s, frozen poses, fades only).
- [ ] **Step 2: Commit** `-- docs/ART_BIBLE.md`

### Task 3: The script + storytelling standard — `docs/SCRIPT_BIBLE.md` + story page check

**Files:** Create `docs/SCRIPT_BIBLE.md`, `tc/story.py`; Test `tests/test_story.py`

**Interfaces:**
- Produces: `STORY_SHAPES = {"mystery", "rise_and_fall", "countdown", "heist", "revenge", "multi_character", "tragedy", "underdog"}`;
  `REQUIRED_HEADINGS = ["Main character", "Other characters", "Want", "Fear", "Choice", "Central question", "Story shape", "Strongest real elements", "Beat sheet", "Loops", "Emotional arc", "Sound plan"]`;
  `story_problems(text: str, kind: str) -> list[str]`; CLI `tc story <job>` (problems, or marks the stage done when the
  `story` self-check in `qa` has also passed).
- Story page format (`jobs/<id>/story.md`): `## <heading>` sections; Beat sheet lines `- <beat>: …` with beats
  `cold_open, world, complication, midpoint, darkest, climax, twist, ending` (long) or `hook, build, twist, ending` (Short);
  Loops lines `- plant: … -> payoff: …`; Sound plan has `Dialogue:` and `Music:` lines, and Music names `opening` and `ending`.

- [ ] **Step 1: Write `docs/SCRIPT_BIBLE.md`:** the story page (with a full worked Salamis example), the story
  toolkit (r33 list), story shapes per topic type, hook types with examples, re-hook patterns, line craft, dialogue
  placement, endings, Shorts rules, and the story checklist (same items + weights as `qa.CHECKLISTS["story"]`).
- [ ] **Step 2: Failing tests:** a complete example page passes; missing "Fear" → `"missing section: Fear"`;
  unknown shape → `"story shape must be one of"`; a long page without `midpoint` → `"beat sheet missing: midpoint"`;
  a loop line without `-> payoff:` → `"loop without payoff"`; Music line without `ending` → `"music plan must include opening and ending"`.
- [ ] **Step 3: Run** `python -m pytest tests/test_story.py` → FAIL. **Step 4: Implement** `tc/story.py`. **Step 5: Run** → PASS.
- [ ] **Step 6: Commit** `-- docs/SCRIPT_BIBLE.md tc/story.py tests/test_story.py tc/cli.py`

### Task 4: Scored self-checks — `tc qa`

**Files:** Create `tc/qa.py`; Test `tests/test_qa.py`

**Interfaces:**
- Produces: `CHECKLISTS: dict[str, dict[str, int]]` (item → weight, each list sums to 100) for `story`, `still`,
  `motion`, `thumbnail`; `score(kind: str, answers: dict) -> dict` where answers = `{item: {"pass": bool, "score": int, "note": str}}`
  → `{"total": int, "passed": bool, "failing": [items]}` (passed = all items pass and total ≥ 90; score clamped to 0..weight);
  `record(job_dir: Path, kind: str, answers: dict, subject: str = "video") -> dict` (writes `jobs/<id>/qa/<kind>.json`,
  keyed by subject, with attempt count); `passed(job_dir: Path, kind: str, subject: str = "video") -> bool`;
  CLI `tc qa <job> <kind> <answers.json> [--subject S]`, `tc qa status <job>`.
- Items (exact names): story = hook_strength 12, title_promise 10, central_question 8, character_want_fear_choice 10,
  rising_stakes 8, cause_and_effect 8, loops_paid_off 8, rehook_spacing 6, twist 8, emotional_arc 8,
  best_scene_last_third 4, strongest_real_elements 6, lines_drawable 4 (=100);
  still = matches_line 12, composition 10, focal_clarity 8, depth_layers 8, light_atmosphere 10, detail_density 10,
  acting 10, era_accuracy 10, character_match 8, grip_and_contact 6, beats_reference 8 (=100);
  motion = on_the_word 15, natural_easing 15, anticipation_follow_through 10, no_freeze 10, no_snaps 15,
  camera_motivated 10, cuts_motivated 10, sound_sync 15 (=100);
  thumbnail = emotion 20, striking_object 15, readable_160px 20, words_le_3 10, contrast 15, matches_video 20 (=100).

- [ ] **Step 1: Failing tests:** weights sum to 100 per list; all-pass 95 → passed; one item `pass: false` at total 97 → not passed and listed;
  total 89 → not passed; `test_score_rejects_missing_item` (missing item → `ValueError` naming it); unknown item → `ValueError`;
  `record` twice increments `attempts`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `-- tc/qa.py tests/test_qa.py tc/cli.py`

### Task 5: The fresh viewer — `tc viewer`

**Files:** Create `tc/viewer.py`, `docs/VIEWER_BRIEF.md`; Test `tests/test_viewer.py`

**Interfaces:**
- Consumes: `script.parse_script`.
- Produces: `viewer_packet(script_text: str) -> str` (only what is heard, in order: narrator lines as plain text,
  character lines as `NAME: line`, `{beat}` as `(pause)`; no section names, tags, sources or `{loop}`);
  `check_verdict(v: dict) -> list[str]` (schema: `verdict` GO|NO-GO, `dropoffs` list of `{at, why}`, `felt` list,
  `would_finish` bool, `would_subscribe` bool, `notes` str; GO with `would_finish: false` or any dropoff is a problem);
  `is_go(v: dict) -> bool`; CLI `tc viewer <job> --packet` (writes `jobs/<id>/qa/viewer_packet.md`, prints the brief
  path) and `tc viewer <job> --record verdict.json` (stores `qa/viewer.json`; marks stage done only on GO).
- `docs/VIEWER_BRIEF.md`: the exact instruction for the fresh agent — read the packet once like a first-time
  YouTube viewer who clicked the title; mark every moment you'd skip or leave and why; say what you felt; decide
  whether you'd finish and subscribe; answer as the JSON schema above; be harsh; never suggest facts.

- [ ] **Step 1: Failing tests:** `test_packet_has_no_tags_or_sections` (packet of a script with `## world`, `[src: x]`,
  `{loop}`, `[dramatised]` contains none of them and keeps the spoken words and `XERXES:`); verdict GO with a dropoff → problem;
  missing `would_subscribe` → problem; valid NO-GO → no problems and `is_go` False.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `-- tc/viewer.py docs/VIEWER_BRIEF.md tests/test_viewer.py tc/cli.py`

### Task 6: Kit tags + scene inspector (stills with on-screen boxes)

**Files:** Modify `film/src/kit/core.ts` (`hand`), `film/src/kit/cast.ts` (`head`, `pole`, `aspis`), `film/package.json`;
Create `film/src/kit/tags.ts`, `film/scripts/inspect.mjs`; Test `film/src/kit/tags.test.ts`

**Interfaces:**
- Produces: kit SVG carries `data-role` = `face` (head group), `hand`, `prop` (pole, aspis), `text`, `textbox`;
  `hand(x, y, skin, holds?: string)` adds `data-holds="<propId>"`; `pole(..., id?: string)` / `aspis(..., id?)` add `data-id`;
  `card(x: number, y: number, w: number, h: number, text: string, size?: number): string` in `tags.ts` (the one place/date
  card, `data-role` textbox + text, Cinzel);
  `node film/scripts/inspect.mjs <module.ts> <exportName> <t> <out.png> [--w 1920 --h 1080]` → writes the still and
  `<out>.json` = `{"elements": [{"role", "id", "holds", "box": [x, y, w, h], "order": n}]}` (screen boxes via `getBBox` +
  `getScreenCTM`, document order).
- [ ] **Step 1: Failing tests (vitest):** `head(...)` output starts with `<g data-role="face"`; `hand(0,0,'#fff','spear1')`
  contains `data-holds="spear1"`; `card(...)` contains `data-role="textbox"` and `data-role="text"`.
- [ ] **Step 2: Run** `npm test` → FAIL. **Step 3: Implement** (puppeteer-core 24.38.0 dev dependency; esbuild bundles the
  module to an IIFE exposing `draw(t)`; executable = Edge on Windows, `PUPPETEER_EXECUTABLE_PATH` elsewhere). **Step 4: Run** → PASS.
- [ ] **Step 5: Verify:** `node film/scripts/inspect.mjs src/compositions/fleet.ts drawFleet 4 out/fleet4.png` → png + json with
  ≥ 12 faces, ≥ 12 hands, 1 text.
- [ ] **Step 6: Commit** `-- film/src/kit film/scripts film/package.json film/package-lock.json`

### Task 7: Measured still checks — `tc still`

**Files:** Create `tc/stillcheck.py`; Test `tests/test_stillcheck.py`

**Interfaces:**
- Consumes: inspector json (Task 6).
- Produces: `geometry_problems(elements: list[dict], w: int, h: int) -> list[str]` — a hand with `holds` must overlap
  its prop's box; any `prop`/`text`/`textbox` drawn **after** a face (higher `order`) covering > 20 % of that face box
  → "covers face"; text box outside its textbox → "text overflows"; faces not fully inside 1 % margin / text outside
  3 % margin → "outside safe area";
  `detail_map(img: Image, cols: int = 8, rows: int = 6) -> list[list[float]]` (edge density per tile, `FIND_EDGES` mean / 255);
  `image_problems(img: Image, allow_calm: set[tuple[int, int]] = set()) -> list[str]` — tiles below 0.010 not in
  `allow_calm` → "empty area at tile (c, r)"; luma p95 − p5 < 90 → "flat contrast"; > 2 % pixels at 255 → "clipped highlights";
  CLI `tc still <png> [--json inspector.json] [--calm "0,0 1,0"]` (prints problems; exit 1 if any).
- [ ] **Step 1: Failing tests:** hand holding a far-away prop → problem; `test_later_prop_covers_face_earlier_does_not`;
  text wider than its box → overflow; a flat grey image → "flat contrast" and empty tiles; a detailed noise image → no empty tiles.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Verify** on the fleet still: `python -m tc still film/out/fleet4.png --json film/out/fleet4.json --calm "0,0 1,0"`
  → no geometry problems (record what it says about tiles in the ledger).
- [ ] **Step 6: Commit** `-- tc/stillcheck.py tests/test_stillcheck.py tc/cli.py`

### Task 8: Motion check — `tc motion`

**Files:** Create `tc/motioncheck.py`; Test `tests/test_motioncheck.py`

**Interfaces:**
- Produces: `frame_diffs(video: Path, scale: int = 160) -> list[float]` (ffmpeg → gray frames → mean abs diff, 0..1);
  `motion_problems(diffs: list[float], fps: int, cuts: list[int] = [], beats: list[int] = []) -> list[str]` —
  snap: diff > max(6 × median, 0.08) at a frame not within ±1 of a cut → "snap at frame N";
  freeze: ≥ 3 s run of diffs < 0.0015 → "frozen from N to M"; late/early: for each beat frame, the largest diff in
  [beat − 8, beat + 4] must be ≥ 2 × the median → else "nothing happens on the beat at frame N";
  CLI `tc motion <mp4> [--cuts f1,f2] [--beats f1,f2]`.
- [ ] **Step 1: Failing tests** on synthetic diff lists: a single spike → snap; `test_cut_is_not_a_snap`; 80 frames of 0.0 at 24 fps → frozen;
  a beat with no motion nearby → problem; a beat with motion 4 frames before → fine.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Verify:** `python -m tc motion film/out/fleet_gh.mp4` → no snaps, no freezes.
- [ ] **Step 6: Commit** `-- tc/motioncheck.py tests/test_motioncheck.py tc/cli.py`

### Task 9: Era lock — `tc era`

**Files:** Create `tc/era.py`; Test `tests/test_era.py`

**Interfaces:**
- Produces: `ERA_KINDS = {"clothing", "armour", "weapon", "hair", "building", "furniture", "ship", "tool", "plant", "animal", "landscape", "colour", "vehicle", "object"}`;
  era sheet `jobs/<id>/era.json` = `{"era": str, "place": str, "years": str, "items": [{"id", "kind", "name", "source", "notes"}], "dont": [str]}`;
  `era_problems(sheet: dict) -> list[str]` (≥ 1 item; every item has kind in ERA_KINDS, non-empty source; unique ids; ≥ 3 don'ts);
  `shots_era_problems(shots: list[dict], sheet: dict) -> list[str]` (every shot lists `era_items`; each id exists);
  CLI `tc era <job>`.
- [ ] **Step 1: Failing tests:** valid sheet passes; item without source → problem; unknown kind → problem; shot citing an unknown item → problem.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `-- tc/era.py tests/test_era.py tc/cli.py`

### Task 10: The agent playbook for the gates

**Files:** Modify `.claude/skills/timeless/SKILL.md`

- [ ] **Step 1: Rewrite** for the autonomous 2D flow: purpose (cinematic 2D animated film, r31), "before every stage"
  (`tc next`, `tc rules --stage`), one short guide per stage from topic to viewer (story page → SCRIPT_BIBLE →
  `tc story` + `tc qa story`; viewer: write the packet, spawn ONE fresh subagent with only `docs/VIEWER_BRIEF.md` + the
  packet, record its JSON), the still/motion/era gates (`tc still`, `tc qa still`, `tc motion`, `tc era`), never-list
  (no AI images, no reused scenes, no owner gates, zero spend), and "later stages arrive in plans 3–9".
- [ ] **Step 2: Verify:** every command named in SKILL.md exists in `python -m tc --help`.
- [ ] **Step 3: Commit** `-- .claude/skills/timeless/SKILL.md`

# Plan 5 — First autonomous Short Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (owner rule: no subagents for implementation). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Shorts (9:16, 2 to under 3 minutes) run through the whole system with no human step: vertical film
compositions, one command that runs the mechanical back half (voices → timings → lip sync → shot plan → cues →
cloud render → join → gates → mix → mux), and one real Short made end to end.

**Architecture:** The timed plan carries its frame size; Root registers each job at that size; the sequence,
camera, grade and finish read the size instead of fixed 1920×1080. `tc produce <job>` walks the mechanical stages
in order, stops on the first failing gate with the exact problem, and is safe to re-run (each step skips when its
output is current). The creative stages (story, script, shot plan, scenes) stay with the agent, guided by the skill.

**Tech Stack:** as plans 1–4.

**Spec:** `docs/superpowers/specs/2026-11-21-2d-autonomous-agent-design.md` — 6.2, 6.3 §2.9 (Shorts composed for 9:16), 6.10, 6.14 (Shorts); rules r20, r24–r30.

## Global Constraints

- Shorts: 1080×1920, 24 fps, 300–420 narration words, re-hook ≤ every 30 s, hook in the first 2 s, the last line
  loops back to the first, made from scratch (own topic, story, scenes) — never cut from a long video.
- Composed for vertical: subjects stacked vertically, never a 16:9 picture cropped (ART_BIBLE §2.9).
- Every gate from plans 2–4 applies unchanged (story ≥ 90, viewer GO, era, cast, still/motion checks).
- Commit with explicit paths; heavily commented code; trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A 16:9 constant left somewhere** (camera focus, letterbox bars, finish rects, whip slide) makes Shorts render
   with a gap or offset → `test_vertical_frame_uses_its_own_size` (Task 1).
2. **`tc produce` re-running a finished expensive step** (re-voicing costs Fish quota, re-rendering costs time) →
   `test_produce_skips_current_steps` (Task 2).
3. **`tc produce` continuing past a failed gate** → `test_produce_stops_at_first_failure` (Task 2).
4. **Wrong size composition registered for a job** → `test_index_carries_size` (Task 1).
5. **A Short over 3:00** (YouTube would treat it as a normal video) → `test_short_length_capped` (Task 2).

---

### Task 1: Vertical compositions

**Files:** Modify `tc/shotplan.py` (timed plan gets `width`, `height` from the job kind), `tc/filmjob.py` (index carries size),
`film/src/Root.tsx`, `film/src/film/sequence.ts`, `film/src/kit/camera.ts`, `film/src/kit/grade.ts`, `film/src/SvgFrame.tsx`;
Test `tests/test_shotplan.py`, `tests/test_filmjob.py`, `film/src/film/sequence.test.ts`, `film/src/kit/camera.test.ts`

**Interfaces:**
- Produces: timed plan `{"fps", "frames", "width", "height", "shots"}` (long 1920×1080, short 1080×1920);
  `ShotCtx.w`, `ShotCtx.h`; `camTransform(t, depth, cam, w = 1920, h = 1080)`; `finish(t, id, opts, w = 1920, h = 1080)`
  (letterbox on vertical = 2.39:1 bars inside the width); index entry `{slug, plan, scenes}` and Root uses `plan.width/height`.
- [ ] **Step 1: Failing tests:** `test_vertical_frame_uses_its_own_size` (a 1080×1920 plan's frame has a 1080×1920 finish rect, whip slides by 1080);
  `test_index_carries_size`; short plan resolves to 1080×1920.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS (+ the fleet still is unchanged).
- [ ] **Step 5: Commit.**

### Task 2: `tc produce <job>` — the mechanical back half

**Files:** Create `tc/produce.py`; Test `tests/test_produce.py`

**Interfaces:**
- Produces: `STEPS = ["dialogue", "voice", "align", "lipsync", "shotplan", "build", "render", "fetch", "join", "motion", "mix", "mux"]`;
  `plan_steps(job_dir: Path, state: dict) -> list[str]` (steps whose output is missing or older than its input);
  `produce(job_id: str, run=..., on="github", parts=None) -> int` — runs each needed step through the existing commands,
  stops at the first non-zero exit and prints which gate failed; writes `jobs/<id>/produce.json` (step → status, time, output hash);
  a Short longer than 179 s fails at `align` (`test_short_length_capped`); CLI `tc produce <job> [--on github|kaggle] [--parts N] [--from STEP]`.
- [ ] **Step 1: Failing tests:** `test_produce_skips_current_steps`, `test_produce_stops_at_first_failure`, `test_short_length_capped`
  (fake runner + fake files).
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit.**

### Task 3: The skill knows the whole flow

**Files:** Modify `.claude/skills/timeless/SKILL.md`

- [ ] **Step 1:** add the art-direction, cast, shot-plan, draw and produce stages (scene code in `film/src/jobs/<slug>/scenes.ts`,
  stills via `node film/scripts/jobstill.mjs`, `tc produce`), the Short rules, and the ordered checklist for one video.
- [ ] **Step 2: Verify** every command named exists. **Step 3: Commit.**

### Task 4: The first autonomous Short

**Files:** `jobs/<short-id>/…`, `film/src/jobs/<slug>/scenes.ts`, `proof/<short>.mp4` (local), `proof/README.md` (append)

- [ ] **Step 1:** topic by demand + story (a fresh topic, not Salamis); story page; script 300–420 words with 2–3 character lines; fresh viewer GO.
- [ ] **Step 2:** era sheet, cast (register any new character first: sheet + drawing + voice), shot plan composed for 9:16.
- [ ] **Step 3:** draw scenes; stills gate per shot; `tc produce`; motion gate; mix; mux.
- [ ] **Step 4:** write the result + gates into `proof/README.md`; commit text files and scenes.

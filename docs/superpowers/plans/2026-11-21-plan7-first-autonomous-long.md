# First Autonomous Long Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take the first 12–15 min video ("The Trap at Salamis", 480 BC) through the whole creative front half to production-ready (merged research → story → script → fresh-viewer GO → era → cast → voices → shot plan) and draw its first chapter to the bar. The remaining chapters and the render continue in the next session (M5).

**Architecture:** Same pipeline as the Short, at long length. One small code addition: `tc research merge` unions the five old Salamis jobs' sourced facts into the new job. Another: `chapters()` turns script sections + word timings into YouTube chapter lines in the pack description. Everything else is agent work through the existing gates (`tc story`, `tc script`, `tc viewer`, `tc era`, `tc cast`, `tc produce`, stills).

**Tech Stack:** Python `tc` (pytest), Remotion film engine, Azure narrator + Fish character voices (free model).

**Spec:** `docs/superpowers/specs/2026-11-21-2d-autonomous-agent-design.md` (6.x pipeline, M5, section 10: the five Salamis jobs become the first test topics, research kept)

## Global Constraints

- Long = 1920×1080, 24 fps, 1,900–2,300 narration words (12–15 min), re-hook ≤ 90 s, sections `cold_open, title, world, tension, turning_point, climax, aftermath, outro`.
- Every factual narrator line has `[src: id]`; imagined lines are `[dramatised]` and must fit the real history (r12).
- Fresh-viewer GO is required for the exact script that is voiced (never re-stamp a GO across a spoken change).
- Drawn fresh for this video (r17); one set per place inside the video (r23); registry characters keep their identity (r19).
- Fish free model only; check `library/fish_usage.json` before voicing.
- YouTube chapters: first at 0:00, ≥ 3 chapters, each ≥ 10 s, one per line `M:SS Title`.

## Review Focus

1. **Merged facts with the same id but different claims** (e.g. two jobs' `f-date`) silently overwrite each other → `test_merge_keeps_conflicting_ids_apart` (Task 1).
2. **Chapters that break YouTube's rules** (not starting at 0:00, a chapter under 10 s, fewer than 3) → `test_chapters_follow_youtube_rules` (Task 2).
3. **A chapter name missing for a section** → falls back to a readable title instead of a raw id like `turning_point` → `test_chapters_fallback_names` (Task 2).
4. **Long pack description without chapters** → `test_long_description_has_chapters` (Task 2).
5. **Short packs gaining chapters** (Shorts don't use them) → `test_short_description_has_no_chapters` (Task 2).

---

### Task 1: `tc research merge`

**Files:** Modify `tc/research.py`; Test `tests/test_research_merge.py`

**Interfaces:** Produces `merge_sources(parts: list[tuple[str, dict]]) -> dict` (`parts` = `(job_tag, sources_dict)`); identical claims under one id merge (cites unioned); a different claim under an existing id gets the id `"<id>-<job_tag>"`. Command: `tc research merge <new_job> <job> [<job> ...]` writes `jobs/<new_job>/sources.json`.

- [ ] Step 1: failing tests `test_merge_unions_cites_for_same_claim`, `test_merge_keeps_conflicting_ids_apart`.
- [ ] Step 2: run → FAIL. Step 3: implement. Step 4: run → PASS. Step 5: commit.

### Task 2: chapters in the long pack

**Files:** Modify `tc/pack.py`; Test `tests/test_pack.py`

**Interfaces:** Produces `chapters(script_text: str, timings: dict, names: dict[str, str]) -> list[str]` (section start = start of its first timed line; `title` section skipped; the first chapter forced to `0:00`; chapters < 10 s merged into the previous one; returns `[]` if fewer than 3). `description()` adds `"Chapters:\n" + lines` for long jobs when `timings.json` exists; names come from `upload.json["chapters"]`, fallback = section id title-cased with `_` → space.

- [ ] Step 1: failing tests (the five Review Focus 2–5 tests).
- [ ] Step 2: FAIL. Step 3: implement. Step 4: PASS (whole suite). Step 5: commit.

### Task 3: the long job's front half

**Files:** `jobs/<id>/{sources.json, story.md, script.md, era.json, cast.json, qa/*}` (git-ignored job data); new character sheets only if the cast needs a new recurring person (registry: `library/characters/<name>/`).

- [ ] `tc new` (kind long, "The Trap at Salamis") → `tc research merge` from the five 20261119 Salamis jobs.
- [ ] Story page (SCRIPT_BIBLE): Themistocles' want/fear/choice; the central question (how does a burnt city beat the largest navy on Earth?); the oracle's "wooden walls" loop paid off at the climax. `tc story` + scored self-check ≥ 90.
- [ ] Script 1,900–2,300 words, character dialogue where it lifts the scene; `tc script` passes.
- [ ] Fresh viewer (`tc viewer --packet` → new subagent, VIEWER_BRIEF) → GO recorded; any spoken change → a NEW viewer.
- [ ] `tc era`, cast (`tc cast`), voices: every speaker has its own voice (`tc voices`).
- [ ] `tc produce` through `length` (voice in 12–15 min).

### Task 4: shot plan + chapter 1 drawn to the bar

- [ ] Shot plan for the whole video (`shotplan.json`, beats pinned to words, gap ≤ 3 s) → `tc shotplan` passes.
- [ ] Draw `scenes.ts` for the cold open + world (chapter 1) fresh; stills gate on every key frame; motion fixes as in the Short (actions centred on words, bold on a phone, cross-fades, eased starts).
- [ ] Ledger exactly which shots are drawn and which remain; proof/README gets the honest status.

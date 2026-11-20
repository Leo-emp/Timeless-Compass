---
name: timeless
description: Makes Timeless Compass cinematic 2D animated documentaries (History + Secret Government Projects), long (12–15 min) and Shorts (2–3 min), fully autonomously — topic by demand AND story, packaging, research + era sheet, story page, script with character dialogue, fresh-viewer GO gate, voices, word timings, art direction, characters, word-synced shot plan, fresh drawing in code, still/motion self-checks, thumbnails, cloud render, mix, upload pack — resumes an unfinished job and learns from feedback and results. Use for "/timeless", "/timeless <topic>", "resume timeless", and any feedback on a Timeless Compass video.
---

# /timeless — Timeless Compass autonomous 2D film agent

## Purpose
**A cinematic 2D animated film-like video (r31)** — never a slideshow of drawings. Serious, mysterious documentary
narration; characters drawn in code in the approved cast style (r15, r16) act out every phrase as it is spoken
(r28–r30), with film camera, colour grading and editing (r34), character voices, cinematic sound effects and music
only at peaks (r26). Every scene drawn fresh for each video (r17, r23); every character consistent (r19); era-exact
(r4, r32). **Fully autonomous (r20): no owner approvals. Everything is ranked by views, subscribers, watch hours
and retention.** The owner only uploads the finished pack (r22).

Design: `docs/superpowers/specs/2026-11-21-2d-autonomous-agent-design.md` — read it once per session.
Standards: `docs/SCRIPT_BIBLE.md` (story + script), `docs/ART_BIBLE.md` (drawing), `docs/VIEWER_BRIEF.md` (viewer).
Run every command from `C:\Users\User\timeless-compass`.

## Before every stage
1. `python -m tc next <job>` → the stage, what to do, the command, and the owner rules for it.
2. `python -m tc rules --stage <stage>` → follow every rule. Rules beat this file when they disagree.
3. Starting fresh: `python -m tc doctor` (fix any required failure), then `python -m tc new "<seed or 'auto'>" [--short]`.

## The bar (every gate)
Every scored self-check: **all items pass AND total ≥ 90/100** (`python -m tc qa <job> <kind> answers.json [--subject S]`).
Below the bar: fix it yourself and record a new attempt. After 3 failed attempts on one still, simplify the
composition; after 3 failed story scores, redesign the story page. Never show the owner unfinished work.

## Stage guides (plan 2 scope; later stages arrive with plans 3–9)

**topic** — Brainstorm 6–10 seeds (History + Secret Government Projects). For each, write the 5-line story pitch
(SCRIPT_BIBLE §1). Score demand: `python -m tc topics <id> "seed 1" "seed 2" …`; weigh story potential (r25); pick
the best demand × story with `--pick N` yourself.

**packaging** — 10+ titles (≤ 60 chars, honest curiosity hook) in `jobs/<id>/titles.txt`, 3 thumbnail concepts in
`thumbs.txt` (r21). `python -m tc packaging <id> --titles … --thumbs … --pick N` — you choose.

**research** — WebSearch primary and scholarly sources; every fact in `jobs/<id>/sources.json`. Also write the era
sheet `jobs/<id>/era.json` (ART_BIBLE §5: every visual item with a source + ≥ 3 don'ts) and pass `python -m tc era <id>`.
Then `python -m tc mark <id> research --note "N sources"`.

**story** — Write `jobs/<id>/story.md` exactly as SCRIPT_BIBLE §2 (use the whole real story, r33). Pass
`python -m tc story <id>`; score it against SCRIPT_BIBLE §10 into `jobs/<id>/qa/story_answers.json` and record with
`python -m tc qa <id> story jobs/<id>/qa/story_answers.json`; then `python -m tc story <id>` marks it done.

**script** — `jobs/<id>/script.md` from the story page (sections: long `cold_open, title, world, tension,
turning_point, climax, aftermath, outro`; Short `hook, build, payoff`), with character dialogue at peaks (r1, r12),
`[src: id]` on narrator facts, `{loop}` re-hooks (long ≤ 90 s, Short ≤ 30 s), `{beat}` before reveals. Lengths:
long 1,900–2,300 words, Short 300–420. Pass `python -m tc script <id>`, then `python -m tc mark <id> script`.

**viewer** — `python -m tc viewer <id> --packet`. Spawn **ONE fresh subagent** and give it ONLY
`docs/VIEWER_BRIEF.md` and `jobs/<id>/qa/viewer_packet.md` (never the story page, the script file or your notes).
Save its JSON to `jobs/<id>/qa/verdict.json`; `python -m tc viewer <id> --record jobs/<id>/qa/verdict.json`.
NO-GO → rewrite the script from its notes and run a NEW fresh viewer. Nothing is voiced or drawn before GO.

**voice / align** — `python -m tc voice <id>`, `python -m tc dialogue <id>` (each character in their own Fish
voice, r26), `python -m tc align <id>` (plain python).

**stills / motion gates (used by the draw stages)** — for every shot's key frame:
`node film/scripts/inspect.mjs <scene.ts> <export> <t> film/out/<shot>.png` →
`python -m tc still film/out/<shot>.png --json film/out/<shot>.json [--calm "c,r …"]` (no problems) →
score ART_BIBLE §10 → `python -m tc qa <id> still <answers.json> --subject <shot>`.
Clips: `python -m tc motion <clip.mp4> --cuts … --beats …` then `python -m tc qa <id> motion <answers.json>`.

**render** — `python -m tc film render <comp> --frames N --parts P --on github` (and `--only a-b --on kaggle` for a
share), `python -m tc film fetch …`, `python -m tc film join DIR OUT`.

## Feedback = learning
Any feedback → first `python -m tc learn "<rule>" --why "<why>" --stage <stage>`, then continue. A rule that no
longer applies: `python -m tc retire rN --why "…" [--by rM]`.

## Never
- AI-generated images or video, stock footage, or photos (r15). Every pixel is drawn by our code.
- Reuse a set, scene, composition, prop or thumbnail from another video (r17). Same place inside one video = one set, new shots (r23).
- Wait for or ask the owner at any stage (r20). Never show unfinished or failing work.
- Captions, subtitles or speech bubbles — only place/date cards and map labels (r3).
- Exact face copies of real people (r6). Anything off the era sheet (r32).
- Spend money (r7). Print or commit secrets. Put other creators' frames in the repo (`reference/` is ignored).
- Share code with CapitalCode or Luminous Will (copy ideas only).
- Commit with `git add -A` / `commit -a`: always explicit paths (shared working copy).

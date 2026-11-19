---
name: timeless
description: Makes Timeless Compass cinematic animated documentaries (History + Secret Government Projects) end to end — topic by demand, title/thumbnail packaging, research, film-structure script, Lewis narration, word timings, shot list (then 3D build/render/edit in later plans) — resumes an unfinished job, and learns from owner feedback. Use for "/timeless", "/timeless <topic>", "resume timeless", and any feedback on a Timeless Compass video.
---

# /timeless — Timeless Compass cinematic documentary agent

## Purpose
Timeless Compass makes **animated, cinematic, movie-style documentaries** about History and Secret Government
Projects: 3D characters in era-correct costume act out every line of a **serious narration**, with real camera
moves, sound design, music and film grading. Target look: ~85% of *Heroes of Bronze* (https://vimeo.com/519612459).
**Growth first:** every choice is ranked by views, CTR and retention. The design is
`docs/superpowers/specs/2026-11-19-cinematic-agent-design.md` — read it once per session.

Run every command from `C:\Users\User\timeless-compass`.

## Before every stage
1. `python -m tc next <job>` → the stage, what to do, the command, and the owner rules for it.
2. `python -m tc rules --stage <stage>` → follow every rule shown. Rules beat this file when they disagree.
3. Starting fresh: `python -m tc doctor` (fix any ERR first), then `python -m tc new "<seed or 'auto'>" [--short]`.

## Stage guides

**topic** — Brainstorm 6–10 seed topics (History + Secret Government Projects) with strong curiosity gaps and
filmable scenes. Score: `python -m tc topics <id> "seed 1" "seed 2" …`. Show the owner the **top 3** with the
numbers and example videos; record their choice with `--pick N`. If the YouTube key is missing, tell the owner the
one-time free setup the tool prints.

**packaging** (before any writing — CTR) — Write 10+ titles (≤ 60 chars, a curiosity hook, honest — the video
must deliver it) to `jobs/<id>/titles.txt` and 3 thumbnail concepts to `thumbs.txt` (one face/emotion + one
striking object + ≤ 3 words; rendered from our 3D scenes later). Run `python -m tc packaging <id> --titles … --thumbs …`,
show the OK ones, owner picks, re-run with `--pick N`.

**research** — WebSearch primary and scholarly sources. Every fact you will say goes in `jobs/<id>/sources.json`:
`{"herodotus-8.75": {"title": "...", "url": "...", "quote": "..."}}`. Note where sources disagree.
Also collect **era facts** for the visuals (exact clothing, armour, buildings, ships, landscape). Then
`python -m tc mark <id> research --note "N sources"`.

**script** — `jobs/<id>/script.md`, sections in order:
long: `cold_open, title, world, tension, turning_point, climax, aftermath, outro` · short: `hook, build, payoff`.
- Cold open: start on the most dramatic moment that matches the title + thumbnail; plant a question in the first 10 s.
- Mini-cliffhanger `{loop}` at least every ~225 words (90 s); pay off every loop; best scene in the last third.
- Written for the ear: ≤ 30 words a line, one idea per line, `{beat}` for held silences before reveals.
- Every line filmable (it must be showable as a picture). Serious, mysterious, never cheesy or clickbait.
- Narrator only: famous quotes are spoken by the narrator ("Leonidas answered with three words…").
- `[src: id]` on every factual line. 1,500–1,800 words (long) / 110–150 (short).
Check: `python -m tc script <id>` until it passes, then show the owner. Only after their yes: `--approve`.

**voice** — `python -m tc voice <id>` (Lewis by default; `TC_VOICE` in .env switches to Jimmie HD Flash).
**align** — `python -m tc align <id>` (plain `python`). Listen to any flagged lines.
**shots** — `jobs/<id>/shots.json`: for every line, 1–3 shots that show **exactly what the words say**, era-correct
(`era` id), `who`/`where`/`action`/`expression`, a camera move from the vocabulary (static, push_in, pull_out,
pan_left/right, tilt_up/down, track, orbit, crane_up/down, handheld), sfx list, optional `card` only of kind
`place_date` or `map_label`. Rhythm: establishing wide → medium → close-up on emotion; slow push-ins on reveals,
fast cuts in battle. `python -m tc shots <id>` until 0 problems (never write `dur` yourself unless a shot must be a fixed length; timings go to `shots.timed.json`). `needs.json` lists the library assets needed. Then `python -m tc assemble <id>`: one Blender build recipe per shot in `recipes/`, and `gaps.json` lists every character, set, era or motion the library lacks — build those assets (blender/lib) before any render, then re-run until 0 gaps.

## Owner gates
1. topic pick (top 3) · 2. title + thumbnail pick · 3. script approval · (later plans: stills contact sheet, final review link)

## Feedback = learning
Any owner feedback, praise or correction → first save it:
`python -m tc learn "<rule>" --why "<why>" --stage <stage> [--stage …]` — then continue.

## Commands
| Command | Does |
|---|---|
| `tc doctor` | health check |
| `tc new "<seed>" [--short]` / `tc status <id>` / `tc next <id>` / `tc mark <id> <stage>` | jobs |
| `tc topics`, `tc packaging`, `tc script`, `tc voice`, `tc align`, `tc shots`, `tc assemble`, `tc render-plan` | stages |
| `tc learn` / `tc rules` | owner rules |

## Never
- Spend money (free tiers only; check pricing before any paid feature). Print or commit secrets.
- Commit or push unless the owner asks. Use PowerShell Get/Set-Content to rewrite files.
- Give characters AI voices. Show real people as exact face copies. Put captions/subtitles on screen.
- Use AI-generated images/video or stock footage. Share code with CapitalCode or Luminous Will (copy ideas only).

# Plan 4 — Film craft + 60-second proof clip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (owner rule: no subagents for implementation). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Everything that makes it a *film* (r31): a word-anchored shot plan, natural motion (anticipation, easing,
follow-through, idle breathing, blinks), lip sync, a camera vocabulary with parallax depth, colour grading + film
finish, transitions with meaning, sound effects and music placed on words — and a **60-second proof clip** made
through it, rendered in the cloud, muxed with its mix and passing every gate, for the owner to watch.

**Architecture:** `tc/shotplan.py` validates a v2 shot plan (`jobs/<id>/shotplan.json`) and resolves every beat's
word to a frame from the word timings → `film/src/jobs/<id>/plan.json`. The kit gains `anim.ts`, `lipsync.ts`,
`camera.ts`, `grade.ts`, `transitions.ts`; `film/src/film/Film.tsx` plays a job's shots in order with their
transitions; each job's scenes are fresh code in `film/src/jobs/<id>/` (r17), registered through a generated index.
Video renders silent in the cloud; `tc film mux` adds the mix locally.

**Tech Stack:** as before (Python + pytest, TypeScript + vitest, Remotion 4.0.506, Azure narrator, Fish voices, Rhubarb, ffmpeg).

**Spec:** `docs/superpowers/specs/2026-11-21-2d-autonomous-agent-design.md` — 6.8 (motion, r28–r30), 6.15 (cinematography,
grading, editing, r34), 6.13 mix (r26, r11), 6.6 gates; rules r3, r16–r19, r23, r28–r34.

## Global Constraints

- Every meaningful phrase makes something visibly happen, about every 1–3 s; no stretch > 3 s where nothing story-related changes (r30).
- Actions start a few frames **before** their word so the key pose lands **on** it; anticipation, easing, follow-through; nobody freezes (r28, r29).
- Camera moves ease in/out; zoom in/out allowed (r34); near layers move more than far ones.
- Music only at peaks (opening, battles/marching, emotional beats, ending); sound effects in every scene, on their words (r11, r26).
- Text on screen only as place/date cards and map labels (r3). Fresh scenes per video, same place = one set (r17, r23).
- Commit with explicit paths; heavily commented code; trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A beat whose word isn't found in the timings** (typo, repeated word) silently lands at frame 0 → `test_unknown_beat_word_is_a_problem`, `test_repeated_word_uses_occurrence` (Task 1).
2. **Transitions overlapping shots** double-count frames so the video drifts out of sync with the voice → `test_timeline_total_equals_voice` (Task 6).
3. **Ids colliding during a dissolve** (two scenes on screen use `c0`, `sky`) → `test_dissolve_scenes_have_unique_ids` (Task 6).
4. **An eased action that overshoots past its end pose and never settles** → `test_tween_settles_exactly` (Task 2).
5. **Mux with a mix shorter/longer than the video** → `test_mux_refuses_length_mismatch` (Task 7).

---

### Task 1: Shot plan v2 — `tc shotplan`

**Files:** Create `tc/shotplan.py`; Test `tests/test_shotplan.py`

**Interfaces:**
- Shot plan `jobs/<id>/shotplan.json` = `{"fps": 24, "shots": [Shot]}`, Shot = `{"id", "line": int, "place": str, "scene": "<export name>",
  "size": "ews|ws|ms|cu|ecu", "angle": "eye|low|high|ots|pov", "camera": {"move": <CAMERA_MOVES>, "amount": float},
  "grade": {"time": "dawn|noon|dusk|night|storm|interior", "mood": "hope|neutral|tension|battle|loss|triumph"},
  "transition_in": {"kind": "cut|match|dissolve|whip|fade_black|flash_white", "frames": int}, "era_items": [ids],
  "beats": [{"word": str, "occurrence": int = 1, "do": str, "kind": "gesture|expression|object|camera|cut|reveal", "lead": int = 6}],
  "sfx": [{"word": str, "occurrence": int = 1, "sound": str, "db": float}], "music": {"cue": str, "from_word": str} | null}`.
- Produces: `CAMERA_MOVES = {"static", "push_in", "pull_out", "pan_left", "pan_right", "tilt_up", "tilt_down", "track", "crane_up", "crane_down", "handheld", "rack_focus"}`;
  `plan_problems(plan: dict, words: list[dict]) -> list[str]` (words = align output `[{"word", "start", "end"}]`, in spoken order;
  every beat/sfx word found in its shot's line span; shot sizes/moves vary — no 4 in a row the same; no gap > 3 s between
  consecutive beats (r30); transition kinds valid); `resolve(plan: dict, words: list[dict]) -> dict` → timed plan:
  each shot gets `start_f`, `end_f` (cut on word/pause boundaries), each beat `frame` (= word start − lead), each sfx `at` seconds;
  CLI `tc shotplan <job>` (problems, else writes `film/src/jobs/<id>/plan.json` and marks the `shots` stage done).
- [ ] **Step 1: Failing tests:** valid plan → no problems + frames resolved; `test_unknown_beat_word_is_a_problem`;
  `test_repeated_word_uses_occurrence` (the 2nd "ships" resolves to its 2nd timing); a 4-s gap between beats → problem;
  four `ms` + `static` shots in a row → problem; shots cover the voice end to end with no gap.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `-- tc/shotplan.py tests/test_shotplan.py tc/cli.py`

### Task 2: Natural motion — `film/src/kit/anim.ts` + arm blending

**Files:** Create `film/src/kit/anim.ts`; Modify `film/src/characters/figure.ts` (arms accept a blend); Test `film/src/kit/anim.test.ts`

**Interfaces:**
- Produces: `easeInOut(x)`, `easeOutBack(x, s = 1.4)` (overshoot then settle), `anticipate(x, a = 0.15)` (small move back, then forward);
  `tween(t: number, t0: number, t1: number, a: number, b: number, ease?: (x: number) => number): number` (clamped; exactly `b` after `t1`);
  `beat(t: number, at: number, lead = 0.25, dur = 0.5): number` (0 → 1 progress of an action landing on `at`);
  `breathe(t: number, seed: number): number` (−1..1, ~0.25 Hz, per-character phase); `blinkAt(t: number, seed: number): boolean`
  (every 3–5 s, 4 frames long, seeded); `sway(t, seed, amp)`.
  Figure: `ArmPose | { from: ArmPose; to: ArmPose; k: number }` for `armL`/`armR` (control points interpolated), and
  `Pose.breath?: number` (chest/shoulders rise ±2 units).
- [ ] **Step 1: Failing tests:** `test_tween_settles_exactly` (`tween(2, 0, 1, 0, 10, easeOutBack) === 10`); easeOutBack exceeds 1 mid-way;
  anticipate dips below 0 early; `beat` is 0 before `at−lead`, 1 after `at−lead+dur`; blinkAt true for ≥ 1 frame in every 6 s and never > 6 frames in a row;
  a blended arm at k = 0.5 differs from both ends.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `-- film/src/kit/anim.ts film/src/kit/anim.test.ts film/src/characters/figure.ts`

### Task 3: Lip sync — Rhubarb cues → mouths

**Files:** Create `film/src/kit/lipsync.ts`; Modify `tc/lipsync.py` (write `film/src/jobs/<id>/lipsync.json`); Test `film/src/kit/lipsync.test.ts`, `tests/test_lipsync.py`

**Interfaces:**
- Produces: `RHUBARB_TO_MOUTH: Record<'A'|'B'|'C'|'D'|'E'|'F'|'G'|'H'|'X', Mouth>` (A→closed, B→smile, C→open, D→wide, E→open, F→o, G→closed, H→open, X→closed);
  `mouthAt(t: number, lines: {speaker: string; at: number; cues: {start: number; end: number; shape: string}[]}[], speaker: string): Mouth | undefined`
  (undefined when that character is not speaking at t → the expression's own mouth).
- [ ] **Step 1: Failing tests:** mouthAt inside a cue returns the mapped shape; outside every line → undefined; another speaker's line → undefined.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** (+ `tc lipsync <job>` writes the json from `dialogue.json`). **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `-- film/src/kit/lipsync.ts film/src/kit/lipsync.test.ts tc/lipsync.py tests/test_lipsync.py`

### Task 4: Camera — `film/src/kit/camera.ts`

**Files:** Create `film/src/kit/camera.ts`; Test `film/src/kit/camera.test.ts`

**Interfaces:**
- Produces: `interface Cam { move: string; amount: number; t0: number; t1: number; focus?: [number, number] }`;
  `camLayer(t: number, depth: number, cam: Cam, content: string, w = 1920, h = 1080): string` — push_in/pull_out scale about
  `focus` (default centre) by `amount × depth`, pans/tilts/tracks translate, cranes translate + slight scale, handheld = seeded
  small shake, all eased with `easeInOut` over [t0, t1]; `rackFocus(t, depth, cam): number` (blur px for a layer: near→far focus pull);
  `blurDefs(): string` (shared `<filter>` set `blur1..blur6`, ids prefixed to stay unique per shot).
- [ ] **Step 1: Failing tests:** push_in at t1 scales by `1 + amount` for depth 1 and `1 + amount × 0.2` for depth 0.2; static leaves the transform identity;
  handheld is deterministic per t; rack focus blur moves from far to near layers across [t0, t1].
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `-- film/src/kit/camera.ts film/src/kit/camera.test.ts`

### Task 5: Colour grading + film finish — `film/src/kit/grade.ts`

**Files:** Create `film/src/kit/grade.ts`; Test `film/src/kit/grade.test.ts`

**Interfaces:**
- Produces: `GRADES: Record<'dawn'|'noon'|'dusk'|'night'|'storm'|'interior', {matrix: number[]; tint: string; tintOpacity: number}>`
  (feColorMatrix values per ART_BIBLE §3), `MOODS` (saturation/contrast offsets: hope, neutral, tension, battle, loss, triumph);
  `gradeDefs(id: string, time, mood): string`; `finish(t: number, id: string, opts?: {vignette?: number; grain?: number; letterbox?: boolean}): string`
  (vignette radial gradient, seeded grain via feTurbulence with a per-frame seed, optional 2.39:1 bars);
  `graded(id, time, mood, content): string` wraps content with the grade filter.
- [ ] **Step 1: Failing tests:** each time of day gives a different matrix; night is darker than noon (matrix luminance sum); grain seed changes per frame
  but is identical for the same t; letterbox bars are 1920 × 138 at top and bottom.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `-- film/src/kit/grade.ts film/src/kit/grade.test.ts`

### Task 6: Transitions + the film sequence

**Files:** Create `film/src/kit/transitions.ts`, `film/src/film/sequence.ts`, `film/src/film/Film.tsx`; Modify `film/src/kit/core.ts`
(id prefix per shot); Test `film/src/film/sequence.test.ts`

**Interfaces:**
- Produces: `withIdPrefix(prefix: string, fn: () => string): string` in core (every `nextId` inside gets the prefix, e.g. `s03c0`);
  `type SceneFn = (t: number, shot: TimedShot) => string`;
  `frameAt(frame: number, plan: TimedPlan, scenes: Record<string, SceneFn>): string` — finds the shot(s) on screen;
  during a transition draws both (dissolve = opacity, fade_black / flash_white = colour overlay, whip = horizontal slide +
  motion streak, match/cut = hard switch), each inside its own id prefix, each with its grade + camera; adds the finish;
  `Film` React component (props: plan, scenes) → `SvgFrame`.
- [ ] **Step 1: Failing tests:** `test_timeline_total_equals_voice` (sum of shot durations − overlaps = voice frames); `test_dissolve_scenes_have_unique_ids`
  (mid-dissolve frame contains `s01c0` and `s02c0`, never a bare duplicate id); a cut frame contains exactly one shot; fade_black midpoint is ~all black overlay.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `-- film/src/kit/transitions.ts film/src/kit/core.ts film/src/film`

### Task 7: Job wiring — scenes per job, registry, cues, mux

**Files:** Create `film/src/jobs/index.ts` (generated), `tc/filmjob.py`; Modify `film/src/Root.tsx`; Test `tests/test_filmjob.py`

**Interfaces:**
- Per job: `film/src/jobs/<jobid>/scenes.ts` (fresh scene code, exports `SCENES: Record<string, SceneFn>`), `plan.json` (timed plan),
  `lipsync.json`. `film/src/jobs/index.ts` = generated list `{ id, plan, scenes, width, height, frames }` that Root registers as
  compositions `Job_<slug>`.
- Produces (Python): `write_index(jobs_dir: Path) -> str` (TS source of the index); `sound_from_plan(timed: dict) -> dict`
  (`sound.json` events `{sound, at, dur, db}` from every sfx word, for `tc mix`); `music_from_plan(timed: dict, tracks: dict) -> dict`
  (`music.json` cues only on shots that name a cue: opening, battle, emotion, ending — r11); `mux_args(video: Path, audio: Path, out: Path) -> list[str]`;
  `mux(video, audio, out, probe=...)` refuses when the lengths differ by > 0.1 s; CLI `tc film build <job>` (index + cues),
  `tc film mux <job> <video>` → `jobs/<id>/master.mp4`.
- [ ] **Step 1: Failing tests:** index lists every job folder with a plan.json; sfx at the word time; music only where a cue is named;
  `test_mux_refuses_length_mismatch`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `-- tc/filmjob.py tests/test_filmjob.py film/src/jobs/index.ts film/src/Root.tsx tc/cli.py`

### Task 8: The 60-second proof clip (Salamis cold open)

**Files:** Create `jobs/<proof-id>/{story.md, script.md, sources.json, era.json, cast.json, shotplan.json}`,
`film/src/jobs/<proof-id>/scenes.ts`, `proof/README.md`; output `proof/salamis_proof.mp4` (git-ignored file, kept locally)

- [ ] **Step 1:** `tc new "The trap at Salamis - proof" --short`. Story page (SCRIPT_BIBLE): Xerxes on his golden throne at dawn
  above the strait; Themistocles' secret message the night before; the Persian ships rowing into the narrows; the trap closes.
  ~150 narration words + 2 character lines (Xerxes, Themistocles), sourced (Herodotus 8.75, 8.90; Aeschylus *Persians*).
- [ ] **Step 2:** era sheet (Classical Greece / Achaemenid Persia, 480 BC: trireme, aspis, Persian court robe, throne,
  parasol, Mount Aigaleos, Salamis strait); `tc era` OK. Cast: xerxes, themistocles (+ a messenger extra if needed); `tc cast` OK.
- [ ] **Step 3:** voice + dialogue + align (the existing commands, with the gate satisfied by recording a fresh-viewer GO
  from a fresh subagent on the packet); lipsync json.
- [ ] **Step 4:** shot plan: 10–14 shots across 4 places (throne hill at dawn, Athenian camp at night, the strait, the
  ram strike), sizes from ews to ecu, ≥ 6 camera moves, grades dawn/night/battle, transitions (fade_black in, a match cut,
  a dissolve, a whip), beats every 1–3 s, sfx on words, music on the opening + the strike. `tc shotplan` OK.
- [ ] **Step 5:** draw `scenes.ts` fresh (ART_BIBLE): sets per place, characters from the registry, acting on beats with
  anticipation/follow-through, idle breathing + blinks, lip sync on the two lines.
- [ ] **Step 6:** stills gate on every shot's key frame: `inspect.mjs` → `tc still --chars` OK → still checklist ≥ 90
  (`tc qa … still --subject <shot> --of <png>`). Redraw failures.
- [ ] **Step 7:** render on GitHub (`tc film render Job_<slug> --frames N --parts 6`), fetch, join `--frames N`,
  `tc motion` with the plan's cuts + beats → OK, motion checklist ≥ 90.
- [ ] **Step 8:** `tc sfx`/`tc music` cues → `tc mix` → `tc film mux` → `proof/salamis_proof.mp4`; check loudness and sync by sampling
  frames at three dialogue words.
- [ ] **Step 9:** `proof/README.md`: what to watch for, and the measured gates. Commit the job's text files, scenes and README
  (not the mp4): `-- jobs/<proof-id>/*.md jobs/<proof-id>/*.json film/src/jobs/<proof-id> proof/README.md`.

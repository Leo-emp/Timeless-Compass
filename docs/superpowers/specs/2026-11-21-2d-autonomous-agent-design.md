# Timeless Compass — autonomous 2D agent (long + Shorts) — design

Date: 2026-11-21 · Replaces the 3D/Blender half of `2026-11-19-cinematic-agent-design.md` (the front half —
topic, packaging, research, script, voice, align, music, sfx, mix, rules — is kept).

## 1. Intent: what and why

**The goal: a cinematic 2D animated film-like video** — it should feel like watching an animated film, not a slideshow.
Timeless Compass is a YouTube channel of serious animated documentaries about **History and Secret Government
Projects**. The owner dropped 3D on 2026-11-21 (quality unreachable) and chose a **2D cartoon look drawn entirely in
code**, aimed at the Japan-history reference video (`Downloads/videoplayback (13).mp4`): thick outlines, round-headed
cast, warm colours, rich detailed sets — and the goal is to **beat** that reference, not match it.

The owner does **not** want to be involved. The system must pick topics, write, voice, draw, animate, check its own
work, render and hand over a finished upload pack — production-ready every time. The single measure of success is
**growth: views, subscribers, watch hours and retention**. Clicks (title + thumbnail) matter most.

Proof the look works (spikes, 2026-11-21, `spike/art_dir/`): cast sheets v1 (approved, r16) and page 2 (gods,
royals, Spartans), Thermopylae and Greek-fleet backgrounds, and an 8 s motion test (`fleet_motion.mp4`: rowing oars,
billowing sail, bobbing ship, parallax camera, blink).

## 2. Goals, non-goals, anti-goals

**Goals**
- One autonomous agent makes **long videos (12–15 min, ~1,900–2,300 narration words)** and **Shorts (2 to under
  3 min, ~300–420 words, 9:16)** end to end with no owner approvals.
- Every scene, background, composition, prop and thumbnail is **drawn fresh for that video** (r17).
- Every character keeps **one consistent identity** across shots and videos (r19).
- Drawn **right the first time** by following a written drawing standard; the agent checks every still against a
  production-grade bar and fixes it itself before anything ships (r18).
- Output an **upload pack** the owner uploads in ~2 minutes (r22).
- A **results loop** that learns from real numbers and changes topics, packaging, hooks and pacing.

**Non-goals**
- Uploading through the YouTube API (owner chose B; may revisit after a Google audit).
- 3D, Blender, AI-generated images or video, stock footage (r15).
- Owner review steps of any kind.

**Anti-goals (a failure even if it "works")**
- Videos that look recycled: same sets, compositions or palettes across videos.
- A character who looks different from shot to shot (wrong beard, crest, colours).
- Stills that reach the owner with obvious defects (props floating, hands not gripping, faces covered, empty areas,
  text overflowing).
- Titles/thumbnails that promise what the video doesn't deliver (kills retention and trust).
- Anything that costs money (r7) or fills the laptop disk (r8).

## 3. Decisions the owner made (as decided)

| # | Decision |
|---|---|
| r15 | No AI images ever; 2D cartoon drawn in code, aimed at the videoplayback(13) reference |
| r16 | Cast style v1 approved (`spike/art_dir/cast_sheet.png`, `cast_lib.js`) |
| r17 | Never reuse scenes; only the style kit is shared |
| r18 | Aim above the reference; drawing standard first; agent self-checks stills to production grade; no draw-show-fix with the owner |
| r19 | Each character's identity stays consistent |
| r20 | Fully autonomous; ranked by views, subscribers, watch hours, retention |
| r21 | Thumbnails drawn fresh per video: rich topic background, the video's characters with strong emotion, one striking object, ≤ 3 big words; CTR first |
| r22 | Delivery = upload pack; owner uploads by hand |
| r23 | Same place inside one video = one set design drawn once for that video; every shot there is a new composition, angle, action or time of day. A different place = a new set from scratch. Never reused between videos |
| — | Lengths: long 12–15 min; Shorts 2 to under 3 min |
| — | Brain = Claude Code, run on a schedule (option 1); not the paid API, not a free model |
| — | Motion where the line calls for it, not everywhere (existing "TC Rich Scenes" preference) |

Older rules that still apply: r1/r12 character voices and dramatised dialogue (Fish voices), r2 serious tone, r3 no
captions/speech bubbles (only place/date cards and map labels), r4 era accuracy, r5 growth first, r6 real people via
costume + name card (no exact face copies), r7 zero spend, r8 laptop light, r11 music only at chosen moments.

## 4. Constraints

- **Zero spend.** Claude Code on the owner's existing subscription; GitHub Actions (repo is **public** → free
  minutes); Cloudflare R2 free 10 GB; Azure narrator and Fish voices as already set up; YouTube Data API free quota.
- **Laptop is weak** (low memory, low disk): no heavy renders locally; big files to R2, local job files deleted after
  the pack is delivered.
- **Shared working copy.** Many sessions use one repo: commit with explicit paths only (existing protocol).
- **Subscription usage limits.** Drawing every shot in code is token-heavy; volume must fit the plan's limits.
- **Windows laptop** runs the brain; Edge is available; Node 24 and Python are installed.

## 5. Approaches considered

| | Brain | Cost | Quality |
|---|---|---|---|
| **1. Claude Code on a schedule (picked)** | This agent, started daily, using `tc` tools + a new 2D engine | No extra cost | Highest — the same brain that drew the spikes |
| 2. Standalone program on the Claude API | Own server, 24/7 | ~$5–15 per long video; breaks r7 | Same as 1 |
| 3. Free model (e.g. Gemini free tier) | Own server | Free | Clearly lower drawing code and scripts; cannot beat the reference |

**Picked 1** (owner, 2026-11-21): the only option that is both free and good enough.

## 6. The system

### 6.1 How it runs without the owner

- **Scheduler:** Windows Task Scheduler on the laptop runs a headless Claude Code session each morning
  (`claude -p "/timeless auto"` with a pre-approved tool list), which resumes the current job or starts the next one
  from the weekly plan. *(Assistant's call — a cloud routine is the fallback if the laptop being on is a problem.)*
- **Weekly plan:** **2 long + 4 Shorts a week** to start *(assistant's call)*; the results loop may raise or lower it.
  `taste/calendar.json` holds the planned slots and best posting times.
- **One job at a time** on the laptop; renders run in the cloud while the next job is being written.
- **Notify on ready:** when an upload pack is done, the owner gets one message (Telegram, already used for
  archives) with the pack link and the suggested posting time. That's the only contact.
- **Never stalls silently:** a watchdog logs every stage; a killed or stalled step is restarted; three failures in a
  row on one job park it and move to the next (logged for the retro).

### 6.2 Stages (each resumable; `tc next <job>` drives them)

| # | Stage | What happens | Gate (automatic) |
|---|---|---|---|
| 0 | **topic** | Demand scoring (existing `tc topics`) **plus a story-potential score (r25)**: main character, real dilemma, rising stakes, twist, visual moments, room for dialogue. For each candidate the agent drafts a 5-line story pitch; the best demand × story wins. Shorts get their own topic | both scores ≥ threshold |
| 1 | **packaging** | 10+ titles scored; 3 thumbnail concepts written (r21); best pair chosen by the agent | `tc packaging` checks |
| 2 | **research** | Sources for every fact; era sheet (costume, armour, buildings, ships, landscape) | every fact sourced |
| 3a | **story design** *(new, r24)* | Before any line: the story page (6.14) — main character, want, fear, central question, beat sheet, twist, ending | story checklist passes |
| 3b | **script** | Written from the story page, following `docs/SCRIPT_BIBLE.md`; loops every ~90 s; dramatised lines tagged | `tc script` passes + story self-check ≥ 90/100, else rewrite |
| 3c | **viewer review** *(new, r27)* | A **separate, fresh viewer agent** (never saw the story page or the writing) reads the script as a first-time viewer: marks every moment it would click away, get bored or confused, notes what it feels, and says whether it would watch to the end and subscribe | **GO / NO-GO**; NO-GO notes go back to 3b; nothing is voiced or drawn before GO |
| 4 | **voice + dialogue + align** | Existing Azure narrator, Fish character lines, word timings | existing checks |
| 5 | **art direction** *(new)* | One page per video: palette per act, settings list, time-of-day plan, signature compositions; must differ from the last ~10 videos | sameness check (6.7) |
| 6 | **cast** *(new)* | Every character needed: load the saved sheet, or create a new sheet and check it | character check (6.5) |
| 7 | **shot plan** | 1–3 shots per line (existing `shots.json` idea), each with a written **scene plan**: layers, who, pose, expression, action, props, light, camera move, motion | plan checked against the drawing standard |
| 8 | **draw** *(new)* | The agent writes fresh scene code per shot (in the job folder) using the style kit | still renders |
| 9 | **stills self-check** *(new)* | Every shot's key frame is rendered and checked (6.6); failures are redrawn by the agent | all shots ≥ bar |
| 10 | **motion** *(new)* | Motion added per the plan (6.8); a few mid-shot frames re-checked | motion check |
| 11 | **thumbnail** *(new)* | Drawn fresh (6.9), self-checked, 2 variants for YouTube Test & Compare | thumbnail bar |
| 12 | **render** | Remotion renders chunks on GitHub Actions in parallel; chunks to R2; joined (6.10) | QA: duration, black frames, sync |
| 13 | **mix** | Existing mix: narrator + character voices + cinematic sfx in every scene + ambience + music **only at peaks (r11, r26)** — opening, ending, battles/marching, tension peaks, emotional scenes; fades on story beats; loudness standard | existing loudness gate + music-placement check (music only on beats the story page marks) |
| 14 | **pack** | Upload pack (6.11) on R2 + Telegram message | pack complete |
| 15 | **archive** | Local job files deleted; pack + master kept on R2 | disk freed |
| 16 | **results** | Daily stats for 30 days feed the learning loop (6.12) | — |

### 6.3 The drawing standard (`docs/ART_BIBLE.md`)

Written **before** the first production scene and read by the agent before every draw stage. It turns "production
grade" into checkable rules. Sections:

1. **Construction** — the approved cast build (r16): head ≈ 40% of height, dot eyes, short thick brows, warm-brown
   outline (one weight for characters, thinner for backgrounds), flat colour + one soft shade on the side away from
   the light; hands drawn over held props (grip rule).
2. **Composition** — one clear focal point; rule-of-thirds placement; ≥ 5 depth layers (sky → far → mid → hero →
   foreground framing); nothing covering faces; no tangents (edges just touching) or awkward overlaps; safe margins;
   Shorts compose for 9:16, never cropped from 16:9.
3. **Light and atmosphere** — where we beat the reference: a grade per time of day (dawn, noon, dusk, night, storm,
   interior lamp), aerial haze for distance, rim light on heroes, cast shadows on the ground.
4. **Detail density** — rich sets: minimum detail per screen region (no empty patches), small background story
   moments (people working, animals, smoke, banners), texture on rock, wood, stone, water.
5. **Era sheets (era lock, r4 + r32)** — built for every video in the research stage: every visual item the story needs —
   clothing, armour, weapons, hairstyles, buildings, furniture, ships, tools, plants, animals, landscape, colours —
   each with a source (museum piece, excavation, period art) and a do/don't list of common anachronisms (e.g. no
   stirrups in 480 BC Greece, no Roman armour on Greeks, no Gothic arches in Egypt). Myths are drawn in the era that
   told them (Greek gods in Archaic/Classical dress, temples and objects). The shot plan names the era sheet item
   for every costume, building and prop; the still self-check has an **era item** that fails any anachronism.
   Example rows already drawn: Spartan hoplite, Corinthian helmet up/down, transverse crest = officer/king,
   trireme (ram, eye, oars, sail).
6. **Acting** — six base expressions (spiked), gestures that match the line, crowd variety (no clones side by side).
7. **Text** — only place/date cards and map labels (r3); fixed card style; text must fit its box.
8. **Thumbnail rules** — see 6.9.
9. **Reference ruler** — side-by-side strips of the reference frames per scene type (crowd wide, interior council,
   battle, sea, map) used only as a quality ruler, never copied (r9). **The strips are someone else's video: they
   never go in the public repo** (assistant's call). They live in `reference/` (git-ignored) on the laptop and in a
   private R2 prefix; the self-check runs on the laptop, so the cloud never needs them.

### 6.4 The style kit (the only shared code, r17)

Ported from the spikes (`cast_lib.js`, `cast_lib2.js`) into TypeScript modules for the renderer:
outline/shade helpers, limb and hand helpers, the head with expressions and blink, mouth shapes for lip sync, hair
and headgear builders, crowd scatter with variety, sky/sea/terrain/weather helpers, camera + parallax layers, a seeded
random generator (same frame every render). **No finished scenes, sets or props live in the kit** — those are written
fresh per video inside `jobs/<id>/scenes/`.

### 6.5 Character registry (r19)

`library/characters/<id>/` per person: `sheet.json` (face shape, skin, hair, beard, build, colours, signature costume,
era, known facts, **their one Fish voice id — r26**), `character.tsx` (draws them in any pose/expression), `sheet.png` (turnaround: front, three-quarter,
six expressions). New characters are created once, pass the character check, then are locked. Generic people
(soldiers, crowds, servants) are not registered; they're generated with variety per scene. Real people follow r6.

**Character check:** each still is compared to the sheet — colours sampled at known regions (hair, beard, costume)
must match; the agent's visual review confirms face, crest/headwear and costume.

### 6.6 Still self-check (r18) — nothing ships below the bar

Two layers on every shot's key frame:

1. **Measured checks (code):** each scene registers the boxes of faces, hands, held props and text as it draws.
   Checks: props touch the hand that holds them; nothing overlaps a face; text inside its box; nothing important in
   the outer margin; no large empty regions (detail map); contrast and palette inside the art direction's range;
   outline weights consistent; no element cut awkwardly by the frame edge.
2. **The agent's own eye:** the agent views the still next to the matching reference strip and scores a fixed
   checklist (composition, focal clarity, depth, light, detail, acting, era accuracy, character match, "matches the
   line", "better than the reference"). **Bar: every item passes and total ≥ 90/100.**

Failures are redrawn by the agent (up to 3 tries; a 4th try simplifies the composition). Every score is logged to
`jobs/<id>/qa/stills.json` and feeds the retro. A contact sheet is saved for the record, never as an owner gate.

### 6.7 Anti-sameness (r17)

Each shot gets a fingerprint (setting type, composition type, camera move, palette, time of day). Fingerprints of the
last ~10 videos are kept in `taste/fingerprints.json`; the art direction and shot plan stages must avoid repeating
recent combinations; the same character always appears in new settings and poses.

### 6.8 Motion — everything synced to the voiceover (r28)

Word timings from the align stage drive every shot: cuts land on word or pause boundaries; each action, gesture
and expression starts on the word that names it ("he **raised** his spear" → the spear rises on *raised*);
character mouths follow their own dialogue (Rhubarb mouth cues per Fish line); sound effects hit on their word.
The shot plan stores these as word-anchored cues, and the self-check samples frames at those words to confirm.

**Acted out in real time, like CapitalCode (r30).** The picture performs the narration phrase by phrase, not one
illustration per line: every meaningful phrase makes something visibly happen — an action, a reaction, an object
appearing or changing, a camera move or a cut — roughly every 1–3 s. A shot is a small sequence of word-anchored
beats (e.g. "Kronos opened his mouth" → jaw opens; "…and swallowed the child" → gulp; Rhea turns away). The
shot plan lists these beats per phrase; the self-check fails any stretch over ~3 s where nothing story-related
changes. Motion comes from the story, never from random looping filler. (Idea copied from CapitalCode, no shared code.)

**Natural flow, never abrupt (r29).** Sync is the target, smoothness is the feel:
- Actions use animation principles: anticipation (a wind-up before the throw), easing in and out, follow-through and
  overlap (head turns first, body follows, cloak settles after). They start a few frames **before** their word so the
  key pose **lands on** it.
- Nobody freezes: characters breathe, blink and shift weight between beats; crowds and nature keep living.
- Cuts are motivated: on a look, a movement or a sound; sound may lead into the next shot or trail out (J/L cuts);
  slow scenes hold longer, battles cut faster.
- Camera moves ease in and out; no sudden jumps or snaps. Music and sound effects fade and swell, never switch.
- The motion check watches a short clip around each key word (not just one frame) and fails jerks, pops, snaps,
  frozen characters and early or late actions.


A motion vocabulary in the kit, used where the line calls for it (not everywhere): blink, talk (lip sync from the
existing Rhubarb data for character lines), expression change, head turn, gestures (point, bow, raise weapon), walk
and march cycles, rowing, crowds moving with offsets, nature (waves, rain, lightning, fire, smoke, flags, sail),
camera push/pull/pan with parallax layers. Shot length follows the word timings; a visual change every ~3–7 s
(existing pacing rule).

### 6.9 Thumbnails (r21)

Drawn fresh per video in the same style at 1280×720: the video's main character(s) large with a strong emotion, one
striking object, a rich background from the topic, ≤ 3 big words, high contrast, readable at phone size (checked by
downscaling to 160 px). Must match what the video delivers. Two variants for YouTube Test & Compare. Shorts get their
own thumbnail too.

### 6.10 Rendering

- **Engine: Remotion** (React → video), the tool CapitalCode already renders on GitHub — **copied, not shared** with
  CapitalCode. Scenes are React components drawing SVG; one frame = a function of time (like the spike's `draw(t)`).
- **Format:** long 1920×1080, Shorts 1080×1920, 24 fps.
- **Cloud:** a GitHub Actions workflow splits a video into chunks across parallel runners; chunks go to R2; a final
  job joins them with the mixed audio. Target: a long video rendered in ≤ 1 h of wall-clock (measured in M1).
- **Laptop** only renders single stills for the self-check.

### 6.11 Upload pack (r22)

On R2 under `packs/<id>/`: `video.mp4`, `thumbnail_a.jpg` + `thumbnail_b.jpg`, `title.txt`, `description.txt`
(sources, chapters, the r12 dramatised-dialogue note), `tags.txt`, `posting.txt` (day + time + any Test & Compare
note). Shorts are separate jobs with their own packs (section 10). The Telegram message gives the link and the
posting slot.

**Linking the upload back to the job (assistant's call):** the owner uploads by hand, so the agent finds the video
itself: each day it lists the channel's newest uploads (Data API, channel ID stored once in `.env`) and matches them
to packs by exact title (fallback: duration ± 2 s). The match is stored in `job.json` as `youtube_id`. No reply is
needed from the owner.

### 6.12 Results loop (learning without the owner)

- Daily for 30 days per video, via the free YouTube Data API key: views, likes, comments, views per hour since
  publish, compared with the channel's own baseline.
- *Optional, one-time owner sign-in later:* YouTube Analytics read-only (CTR, retention curve, watch hours). If
  given, retention dips are mapped to the exact shot and line.
- Findings become rules automatically (`tc learn … --why "results: <video>"`), and re-weight topic scoring, title
  styles, thumbnail types, hook types and pacing. A retro per video: `taste/retros/<id>.md`.

### 6.14 Storytelling (r24) — `docs/SCRIPT_BIBLE.md` + the story self-check

Every video is a **story, not a list of facts**. The script stage is split in two:

**Story page (before any line is written):** `jobs/<id>/story.md`
- **Main character** the viewer follows (a person, not an empire), with a **want**, a **fear** and a **choice** they
  must make. Real history only — the drama comes from what really happened (r4, r12).
- **Central dramatic question** the title and thumbnail promise, answered only at the end.
- **Beat sheet:** cold open (the most dramatic moment) → the world and what's at stake → rising complications
  ("but… therefore…", never "and then") → midpoint turn → darkest moment → climax → twist/reveal → ending line.
- **Loops:** every question planted, with where it pays off; a re-hook every 60–90 s (long) / every 20–30 s (Short).
- **Emotional arc:** what the viewer should feel in each act (curiosity → dread → hope → shock → awe).
- **Sound plan:** where character dialogue lifts a scene (each speaker in their own voice), the sound effects per
  scene, and the few **music moments** (opening, peaks, battles/marching, emotional beats, ending) — so music is
  designed with the story, not laid on top.
- **Dramatic irony and foreshadowing** points; the best scene placed in the last third.
- Shorts: one story, one twist, hook in the first 2 s, ending that loops back to the first line.

**Script craft (from the bible):** hook confirms the title within 5 s; no intro or logo; stakes in human terms;
short ear-friendly lines with varied rhythm; concrete pictures over abstractions (every line must be drawable);
held silences before reveals; character lines only at peak moments; ending answers the opening question, then one
line that sticks, then a natural pointer to a related video (watch hours), never a cheesy subscribe ask.

**Story self-check (before voicing):** scored checklist — hook strength, title promise delivered, central question
clear, character want/fear/choice, rising stakes each act, cause-and-effect links, loops planted and paid off,
re-hook spacing, twist, emotional arc, best scene placement, every line drawable, every fact sourced, length in
range. **Bar: all items pass and ≥ 90/100**, else the agent rewrites (up to 3 passes, then re-designs the story page).

**Learning:** retention dips from the results loop are mapped back to the beat and line; the bible gains rules
(e.g. "slow 'world' sections lose viewers at 1:40 → keep them under 45 s").

### 6.13 What is removed / rewritten

- Tag `old-3d-pipeline-final`, then remove `blender/`, the 3D cloud workflows, and the Blender-based `tc` modules
  (assemble, assets, cast_tool, crowd, emblems, fight, lipsync's face-rig part, performance, render_cache, render_farm,
  render_plan, slowmo, thumbnail, maps, kaggle). Rhubarb timing data, voice, music, sfx, mix stay.
- **Rules to retire or rewrite:** r10 (`tc look` vs Heroes of Bronze), r13 (3D library gate) → replaced by the 6.6
  bar; r14 (maps) → keep the Epic History map *look* but drawn in 2D in this style.
- The `timeless` skill is rewritten for the autonomous flow (no owner gates).

## 7. Milestones

| # | Milestone | Done when |
|---|---|---|
| M0 | Clean slate | Old pipeline tagged and removed; rules r10/r13/r14 rewritten; `tc doctor` passes |
| M1 | Engine + speed | Style kit in Remotion; the fleet test re-made in Remotion; one chunked GitHub render; measured render speed |
| M2 | Standards + checks | `ART_BIBLE.md` + `SCRIPT_BIBLE.md` written; still checks + story self-check working on the spike scenes and one Salamis script |
| M3 | Characters | Registry + character check; Leonidas, Themistocles, Xerxes sheets locked |
| M4 | First autonomous Short | A 2–3 min Short from topic to upload pack with no human step |
| M5 | First autonomous long | A 12–15 min video from topic to upload pack with no human step |
| M6 | Thumbnails + packs + schedule | Fresh thumbnails pass their bar; Task Scheduler runs daily; Telegram notice |
| M7 | Results loop | Daily stats, auto-rules, retros, anti-sameness fingerprints |

## 8. Risks

| Risk | Mitigation |
|---|---|
| Subscription usage limits can't cover 75+ drawn shots per long video × 2/week | Measure tokens per shot in M4/M5; reuse the style kit heavily; lower the weekly plan if needed |
| Self-check passes stills a human would reject | Bar includes side-by-side with the reference; owner's spike approvals become calibration examples; retros tighten the checklist |
| Remotion SVG render speed too slow for 15 min | Measured in M1; more chunks/runners; simplify heavy layers (pre-render static layers to images once per shot) |
| Headless Claude Code needs permission prompts | Pre-approved tool list for the scheduled run; anything outside it fails safe and is logged |
| Laptop off or asleep at schedule time | Task Scheduler "run when available"; existing Stay Awake shortcut; cloud routine fallback |
| R2 over 10 GB | Packs deleted from R2 after a set time once the owner has uploaded; `tc doctor` reports usage |
| Era mistakes | Era sheet from sourced research; checklist item; r4 |

## 9. Left to the builder

- Module boundaries, schemas (scene plan, character sheet, QA log, calendar), test approach.
- How measured checks get geometry from scenes (registration API), detail-map method, thresholds.
- Remotion project layout, chunk size, runner count, join step.
- Exact checklist wording and weights inside the 90/100 bar.
- Telegram bot wiring; pack retention time on R2.

## 10. Calls made by the assistant (owner can overrule)

- Shorts are made from scratch (own topic, script, scenes, thumbnail), never cut from a long video.
- Start at 2 long + 4 Shorts a week.
- Learning uses public stats; the Analytics sign-in is optional and asked once.
- Scheduler on the laptop (Task Scheduler + headless Claude Code); cloud routine as fallback.
- Remotion as the renderer (copied idea from CapitalCode, no shared code); 24 fps.
- Telegram for the one "pack ready" message.
- Self-check bar: all items pass and ≥ 90/100; 3 redraws then simplify.
- The five Salamis jobs already in `jobs/` (research + scripts done, written for the old gates and 132-word Shorts)
  become the first test topics: re-scripted to the new lengths in M4/M5, research kept.
- Fish character voices use the free model; `library/fish_usage.json` tracks use. The script stage caps dramatised
  lines per video so the week's plan stays inside the free allowance; if it runs low, the narrator carries more.

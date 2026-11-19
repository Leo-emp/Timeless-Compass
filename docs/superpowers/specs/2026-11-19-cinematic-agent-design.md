# Timeless Compass: Cinematic Documentary Agent (design)

Date: 2026-11-19 · Status: **approved by owner 2026-11-19** · Replaces the old stock-footage pipeline in this repo.

## 1. Intent: what and why

Timeless Compass is a faceless YouTube channel for **History and Secret Government Projects**. The owner wants
millions of views and revenue (ads, brand deals, digital products). The old pipeline (Gemini + Pexels stock
footage + ElevenLabs + MoviePy) produced generic slideshow videos that do not stand out.

The new system is an **intelligent agent that makes animated, cinematic, movie-style documentaries**. The target
feel is a **film**: 3D characters in era-correct costume acting out every line of a serious narration, real
camera moves, sound design, music and film grading. The look benchmark is the Blender short *Heroes of Bronze*
(<https://vimeo.com/519612459>). **Target: about 85% of that overall**, rising as the asset libraries grow.

It must **learn and get better with every video**: owner feedback, self-review and YouTube results all feed back in.

## 2. Goals, non-goals, anti-goals

**Goals**
- **Growth first (owner rule, from day one): every decision is ranked by views, click-through rate (CTR) and
  retention.** Topic, title, thumbnail, hook, script structure, pacing and editing exist to serve those three numbers
  (see 6.0).
- One prompt (`/timeless <topic>`) leads to a finished, reviewed, upload-ready cinematic documentary.
- Every voiceover line is shown literally: characters act it out, and the picture matches the words.
- Era accuracy: costumes, armour, gods' iconography, buildings, props and landscapes match the time and place.
- Premium, realistic look: proper faces, realistic movement (motion capture), cloth that drapes, worn materials.
- Movie-grade editing: smooth zooms and push-ins, tracking shots, cuts on the voice rhythm, layered sound design and score.
- Zero spend: free tools, free cloud compute, free storage tiers only.
- The laptop stays light: heavy files live in the cloud; the laptop holds only the current job.
- Learns: rules from owner feedback, a growing and upgrading asset library, self-critique, analytics.

**Non-goals (for now)**
- Funny / comedy tone (tested and rejected: AI voices can't do comedy timing).
- 2D code-drawn characters (tested and rejected: not realistic enough). Spikes stay in `spike/` as reference only.
- AI-generated images or video, and stock footage or photos in videos.
- Fully autonomous scheduled operation without a Claude Code session (approach B, rejected because of API cost).
- Eras beyond the first library until the Greek slice is proven.

**Anti-goals: what would make this a failure even if it technically works**
- Characters that look like mannequins or melted shapes (the failed code-drawn Zeus and the shell-armour hoplite).
- Wrong-era details (Roman armour at Thermopylae, modern faces and haircuts on ancient people).
- Samey videos: the same shots, sets or poses recycled so viewers notice.
- Pictures that don't match the narration, or text on screen repeating what the voice says.
- Any surprise cost (paid APIs, R2 over 10 GB, paid GPUs).
- Filling the laptop disk.

## 3. Decisions the owner made (as decided)

| Topic | Decision |
|---|---|
| Niche | History + Secret Government Projects (business stories stay on CapitalCode) |
| Tone | **Serious**, dramatic, mysterious documentary |
| Visual method | **3D**: free open-source human models (MakeHuman/MPFB, CC0) + motion capture, styled and animated by our code. No AI imagery |
| Quality bar | ~85% of *Heroes of Bronze* overall; faces may lag (free tools ceiling ~75–80%) |
| Movement | Characters fully act every line: walk, march, fight, talk (lip sync), eat, react with realistic expressions |
| Era accuracy | Required for clothes, armour, gods, soldiers and backgrounds |
| Editing | Cinematic movie feel: smooth zoom in and out, camera moves, sound effects, music |
| Text on screen | No captions or speech bubbles; the voice tells the story. Only place/date cards and map labels |
| Voice | **Narrator only**: characters act but don't speak (AI character voices tested and rejected as unnatural). Famous quotes are delivered by the narrator. Narrator voice: **Azure `en-US-LewisMultilingualNeural`** (owner: "good"; standard, likely free tier). Alternative kept as one config switch: **Jimmie Dragon HD Flash**. Pricing must be checked before production |
| Voice mastering | Voice chain: high-pass, warm low EQ, presence lift, compression, loudness normalise (spike: −14.6 LUFS, peak −1.2 dB); final mix target set in the edit stage |
| Topic choice | **The system picks** by demand data; owner chooses from its top 3 |
| Modern era | Same cinematic 3D approach for secret government projects (1950s–80s suits, uniforms, labs, war rooms, rockets, nuclear tests). Real people are shown through costume, setting and a name card, **never exact face copies** |
| Spend | **No money.** Free tiers only |
| Rendering | Kaggle free GPUs + GitHub Actions (free, parallel) + laptop as controller |
| Storage | R2 for the asset library and the review copy; YouTube as the main archive; Telegram private channel for full-quality masters; laptop wiped after each job |
| Old pipeline | Delete it (tag it in git first) |
| Approach | **A**: Claude Code agent like CapitalCode, with a learning system |
| Priority | **Views, CTR and retention first**, from the start |
| Format | **10–12 min** 16:9 long-form + **Shorts** (own script, own vertical 9:16 camera in the same 3D scenes; never crop or stretch) |
| Repo | **Public** GitHub repo (unlimited free Actions minutes); no secrets in the repo |
| Script | Film structure: cold open, title, world, rising tension with mini-cliffhangers, turning point, climax, aftermath + reveal; written for the ear, every line filmable, every claim sourced |

## 4. Constraints

- **Hardware:** laptop with Ryzen 7 5825U, integrated Radeon, 16 GB RAM, little free disk. Blender EEVEE on it
  measured ~7–12 s per 720p frame, which is too slow for long videos. The laptop only orchestrates and renders
  Shorts or tests.
- **Free compute limits:** Kaggle about 30 GPU h/week, 12 h per session, 2×T4 or P100; GitHub Actions free with
  unlimited minutes for public repos (6 h per job, up to 20 parallel, CPU only). A public repo means code is visible;
  no secrets in the repo.
- **Free storage limits:** R2 10 GB; Telegram 2 GB per file.
- **Voice cost risk:** the Azure free tier (F0) covers standard neural voices; **HD voices may not be in the free
  tier**. Must verify before use, and fall back to the best free voice if HD costs money.
- **Licences:** every asset must be CC0, public domain or our own. Track the licence per asset. The Three.js sample
  models and face-capture head used in spikes are **not** for production.
- **Brand separation:** copy ideas and code from CapitalCode or Luminous Will, never import or share code across repos.
- **Owner rules:** heavily commented code; no subagents for implementation (inline only); never print or commit
  secrets; commit only when asked; no PowerShell Get/Set-Content rewrites.

## 5. Approaches considered

| | A. Claude Code agent (picked) | B. Autonomous cloud agent | C. Fixed script pipeline |
|---|---|---|---|
| Shape | `/timeless` skill + `tc` CLI; Claude runs the stages, makes judgements, builds missing assets, self-reviews, learns | Agent SDK service on a schedule | Python scripts; LLM only writes the script |
| Intelligence | High | High | Low: can't build assets or judge quality |
| Learning | Yes | Yes | No |
| Cost | Free (owner's Claude Code plan) | Pays per API token | Free |
| Fit | Same shape as the proven CapitalCode agent | New | The old pipeline already failed |

**Picked A** because it's the only one that is both intelligent/learning and free, and it reuses a shape the owner
already runs daily (learn / run / doctor / package / archive, GitHub cloud renders, owner reviews renders).

## 6. The system

### 6.0 Growth engine: views, CTR and retention drive everything

| Lever | What the agent does | Free data source |
|---|---|---|
| **Topic demand** | Before writing, score candidate topics: search demand, outlier videos on competitor channels (views ÷ channel subscribers), recency of coverage, "curiosity gap" strength. Only topics above a threshold go ahead | YouTube Data API (free quota), YouTube search autocomplete, competitor channel lists |
| **Packaging first (CTR)** | The **title and thumbnail are designed before the script**. 10+ title options are scored (curiosity, clarity, ≤ 60 chars, no clickbait lies); 3 thumbnail concepts are rendered from the 3D scenes (one face/emotion + one striking object + ≤ 3 words). The script must deliver what the title promises | Our own 3D renders; YouTube's built-in **Test & Compare** for A/B thumbnails (free) |
| **Hook (first 30 s retention)** | Cold open starts on the most dramatic moment that matches the title and thumbnail; a question is planted in the first 10 s; no slow intro, no logo sting | Retention curve of previous videos |
| **Retention structure** | Open loops; a re-hook / mini-cliffhanger every ~60–90 s; a payoff for every loop; the strongest scene saved for the last third | Audience-retention curves |
| **Visual pacing** | Visual change every ~3–7 s (new shot, camera move or action); no static moments over ~8 s unless deliberate; pattern interrupts at expected drop points | Retention dips mapped to shot timestamps |
| **Length** | 10–12 min long-form (owner decision); Shorts 45–60 s, each with its own script and vertical camera | — |
| **Results loop** | After publishing: pull CTR, views by hour, average view duration and the retention curve; **map every dip and spike to the exact shot and line**; store what worked and what lost viewers as rules; topic scoring is re-weighted by real results | YouTube Analytics API (free, owner's channel) |
| **Shorts → long funnel** | Each long video gets 2–3 Shorts on its most shocking moments, published around launch | — |

Hard rule: a title, thumbnail or hook that promises something the video doesn't deliver is rejected (it kills
retention and trust).

### 6.1 Repo layout (this repo, after the old pipeline is removed)

```
timeless-compass/
  .claude/skills/timeless/SKILL.md     # the agent's playbook (versioned with code); launcher in ~/.claude/skills
  tc/                                  # Python CLI: `python -m tc <command>`
    cli.py  jobs.py  paths.py  doctor.py  learning.py
    research.py  script.py  voice.py  shots.py  build.py  render.py  edit.py  qa.py  package.py  archive.py
  blender/                             # scripts that run INSIDE Blender (bpy + MPFB)
    cast.py  wardrobe.py  sets.py  motion.py  camera.py  lighting.py  shot.py  lipsync.py
  library/                             # small manifests only (JSON + licence); big files live in R2
    cast/  wardrobe/  sets/  props/  motions/  sfx/  music/  grades/
  taste/                               # learning memory
    rules.md  learning.json  retros/
  cloud/                               # Kaggle notebook template + GitHub workflow + shard runner
  docs/superpowers/specs/              # this file
  spike/                               # throwaway experiments (reference only)
```

### 6.2 One video = one job folder

`jobs/<yyyymmdd-hhmm>-<slug>/` holds `job.json` (stage status, so any stage can resume), the research notes, the
script, the voice and timings, the shot list, stills, logs and the edit decision list. Big outputs (frames, shot
renders, the final mp4) go to R2 under `jobs/<id>/…` and are deleted locally after upload.

### 6.3 Stages (`tc run <topic>` walks them; each is resumable)

0. **Topic + packaging:** demand scoring picks the topic; title options and thumbnail concepts are made and the
   owner picks (6.0). Everything after this serves that title and thumbnail.
1. **Research:** sources, timeline, people, places, era facts (costume, armour, architecture). Every claim sourced.
2. **Script:** serious documentary narration. Hook first, mystery and tension, a reveal at the end; written for
   the ear with SSML pauses and emphasis. Owner approves the script before anything expensive.
3. **Voice:** the chosen Azure narrator (narrator only), SSML with breaks and near-natural pace (~−4%). Collect
   **word timings** for cuts and shot durations. Mastered with the voice chain. (Viseme/lip-sync support stays in
   the design for a future character-voice upgrade, but is off.)
4. **Shot list:** every line becomes 1–3 shots: who, where, action, expression, camera move, lens, duration
   (from word timings), sound effects. Literal rule: the picture shows what the words say.
5. **Library check:** list every cast member, costume, set, prop and motion the shots need. **Build any that are
   missing** (section 6.4) and register them, so the library grows.
6. **Build shots:** Blender scenes are assembled per shot from library pieces: character + costume + pose/motion +
   expression + lip sync, set + lighting + atmosphere, camera path.
7. **Stills review (gate):** render one key frame per shot at low cost; the agent checks each against the line, the
   era rules and the quality bar (vision self-critique), fixes issues, then shows the owner a contact sheet.
   Mirrors the CapitalCode rule "review stills before full render; render once".
8. **Render:** shard the shots across Kaggle GPU sessions (heavy shots) and up to 20 GitHub Actions runners (light
   shots). Upload each shot to R2. Resumable per shot.
9. **Edit:** join shots on the voice timeline; cuts on word and pause boundaries; transitions; music bed with
   ducking under the voice; layered sound effects; colour grade per era; film grain; letterbox; place/date cards;
   loudness master. Runs in the cloud.
10. **QA (gate):** automatic checks (duration, black frames, audio levels, sync drift, missing shots), then the owner
    watches the R2 review link.
11. **Package:** title, description with sources, tags, chapters, thumbnail (rendered from the 3D scenes).
12. **Archive and clean:** after approval and upload: master to Telegram, R2 job files deleted, library kept,
    laptop job folder emptied.

### 6.4 The libraries (built once, reused, upgraded)

| Library | What | How it's made |
|---|---|---|
| **Cast** | Named characters with fixed looks (face shape, age, skin, hair, beard) so they're recognisable across shots and videos | MPFB macro sliders + CC0 skins/eyes/eyebrows; beards and hair as Blender hair curves |
| **Wardrobe** | Era kits: e.g. Greek hoplite 480 BC (Corinthian helmet, muscle cuirass or linothorax, aspis, greaves, dory, xiphos, chiton, red cloak), Greek civilian, Greek gods (Zeus himation, laurel, thunderbolt; Poseidon trident; Athena helmet, aegis), Persian Immortal, Persian king | Proper 3D models: CC0 museum scans where they exist (e.g. Smithsonian Open Access), else modelled in Blender by script; robes and cloaks via **cloth simulation**; PBR materials with patina, wear and dirt |
| **Sets** | Places: Athens and Acropolis, Thermopylae pass, Salamis strait, trireme decks, Persian camp, Olympus | Blender scenes: terrain, architecture kits (columns, temples, walls), water, sky (physical sky), fog and volumetrics |
| **Props** | Triremes, rowboats, scrolls, lamps, thrones, weapons | Modelled by script, CC0 where available |
| **Motions** | Walk, march, run, fight moves, fall, row, kneel, bow, sit, eat, talk gestures | Free motion capture (CMU, retargeted to MPFB's `cmu_mb` rig); small hand-keyed fixes for contact |
| **Faces** | Expressions + lip sync | MPFB face rig and visemes driven by Azure viseme events |
| **SFX / Music** | Ambience, foley, impacts, scores | Freesound CC0, Pixabay, YouTube Audio Library (licence logged per file) |
| **Grades** | Colour looks per era and mood | Blender compositor presets |

Every asset has `manifest.json` with: name, era, licence and source, version, owner rating, known weaknesses,
and which videos used it. Big binaries live in R2 (`library/…`), cached on render machines. **The library must
stay under ~6 GB** so R2 stays within the free 10 GB alongside review copies.

### 6.5 Rendering

- **Engine:** Blender EEVEE for most shots (fast); Cycles only if a hero shot needs it and the time budget allows.
- **Kaggle:** a notebook template installs portable Blender + MPFB + library cache, renders its shard, uploads
  shots to R2. Driven by the Kaggle API from the laptop. One-time owner setup: phone-verify the Kaggle account and
  create an API token.
- **GitHub Actions:** a workflow that matrix-shards light shots across up to 20 runners (CPU EEVEE or simplified
  shots). Same "render on github" idea as CapitalCode, copied, not shared.
- **Targets (to be measured in the first build milestone):** ~1–2 h per 10–15 min long video; Shorts faster.
- **Watch processes:** file logs, confirm the first output, a stall watchdog, restart killed shards (owner rules
  from other projects).

### 6.6 Editing and film language (rules the agent follows and refines)

- Aspect 16:9 delivery with optional 2.39:1 letterbox for cinematic sequences; 24 fps.
- Shot rhythm: establishing wide, then medium, then close-up on key emotion; a new shot every ~3–7 s, slower for
  dread, fast cuts for battle.
- Camera: slow push-ins on revelations, pull-outs for scale, tracking for movement, low angles for power,
  subtle handheld in combat. **Smooth zooms are allowed** (the CapitalCode no-zoom rule does not apply).
- Silence or a held beat before reveals; music swells on turning points.
- Sound: ambience bed per set + foley per action + impacts and whooshes on cuts; voice always on top.
- No subtitles or speech bubbles; place/date cards in the brand serif; animated maps for routes and armies.
- Loudness mastered to a fixed target (set in the build; follow the owner's existing audio standards style).

### 6.7 The learning system ("better and better")

1. **Owner feedback becomes rules:** `tc learn "<feedback>"` stores a numbered rule in `taste/rules.md` +
   `learning.json` (with why and how to apply), and the SKILL reads them before every stage. Same mechanism as
   CapitalCode's learning log.
2. **Asset ratings and versions:** owner and self-review ratings per asset; weak assets are flagged for upgrade;
   a new version replaces the old in future shots.
3. **Self-critique:** a vision review of stills and final frames against the script, era rules and the quality bar;
   findings are logged.
4. **Retro per video:** `taste/retros/<job>.md`: what was weak, what got fixed, which library items to build next.
5. **Results loop:** after publishing, pull YouTube stats (views, retention curve, CTR) and record which hooks,
   topics, shot types and pacing held viewers. Topic and script choices use them.
6. **Anti-sameness:** shot fingerprints (set + camera + pose) are tracked across videos so recent combinations are
   not reused.

### 6.8 Commands

`tc run <topic>` · `tc resume [job]` · `tc stills <job>` · `tc render <job> --on=kaggle|github|laptop` ·
`tc edit <job>` · `tc package <job>` · `tc archive <job>` · `tc learn "<feedback>"` · `tc library [list|build|rate]` ·
`tc doctor` (checks Blender, MPFB, keys, R2/Kaggle/GitHub/Telegram access, disk space, free-tier usage).

## 7. Milestones

| # | Milestone | Done when |
|---|---|---|
| M0 | Clean slate | Old pipeline tagged (`old-pipeline-final`) and removed; new layout; `tc doctor` passes |
| M1 | Voice + script + shot list | A topic gives a sourced script, Azure voice with word timings + visemes, and a shot list JSON |
| M2 | First library slice (Salamis) | Themistocles, Sicinnus, Greek civilian kit, dock/strait set, rowboat, 6 motions, lip sync: owner-approved stills |
| M3 | Render farm | One shot renders on Kaggle and on GitHub, uploads to R2; measured seconds per frame |
| M4 | Edit + audio | Shots + voice + SFX + music + grade into a review mp4 on R2 |
| M5 | **Proof clip** | A 30–60 s Salamis sequence end to end; owner judges against the 85% bar |
| M6 | Learning + archive | `tc learn`, retros, asset ratings, Telegram master backup, cleanup |
| M7 | First full video | One full documentary through every stage, then the library grows per topic (hoplite kit, Persians, gods, Thermopylae…) |

## 8. Risks

| Risk | Mitigation |
|---|---|
| Costume quality below the bar (seen in the shell-armour spike) | Real models / scans + cloth sim; owner approves each kit's stills before it enters the library |
| Faces look "game-like" | Better skin shading, hair curves, careful lighting and framing; accept the ~75–80% ceiling |
| Kaggle quota or terms change | Shard across GitHub + laptop; keep shots small; measure in M3 |
| Azure HD voice not free | Check in M1; fall back to the best free neural voice and get owner approval |
| R2 over 10 GB | Library size budget, delete job renders after archive, `tc doctor` reports usage |
| Motion-capture retargeting artefacts (feet sliding, hands not touching) | Foot locking, contact fixes, camera framing |
| Build time is weeks | Milestones each give something visible; proof clip at M5 before the full video |

## 9. Left to the builder

- Exact Python module boundaries, data schemas (job.json, shot list, manifests), and the test approach.
- EEVEE settings per shot type; how shots are split between Kaggle and GitHub.
- Retargeting tooling for CMU motion capture onto the MPFB rig.
- Loudness numbers, grade presets, transition set.
- How the Kaggle notebook is pushed and polled; the Telegram bot setup.

## 10. Calls made by the assistant (owner can overrule)

- CLI in **Python** (Blender and MPFB are Python; the old repo is Python), not TypeScript like CapitalCode.
- Agent playbook lives in the repo (`.claude/skills/timeless/`) with a launcher in `~/.claude/skills`, like CapitalCode.
- 24 fps, 16:9 delivery, optional letterbox.
- Owner gates at: script, stills contact sheet, final review link (mirrors CapitalCode practice).
- First library slice is Salamis (already spiked), not Thermopylae.
- Library budget ≤ ~6 GB on R2.

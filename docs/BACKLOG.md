# Timeless Compass — full build backlog (for parallel sessions)

Goal: animated cinematic 3D documentaries (history + secret government projects) at ~85% of the quality of the
Heroes of Bronze reference (quality ruler only — rule r9: never copy). Status 2026-11-19: ~62% overall.
Branch: `cinematic-agent` in `C:\Users\User\timeless-compass`. Spec: `docs/superpowers/specs/2026-11-19-cinematic-agent-design.md`.

---

## RULES FOR EVERY SESSION (read first)

1. **Claim before you start.** Put your session name next to the task in this file (`CLAIMED: <name>`), and only edit
   the files listed for your workstream. If you must touch another workstream's file, ask the owner first.
2. **Only ONE Blender at a time on this laptop — use the lock file:** before running Blender, check that
   `spike/BLENDER_LOCK` does not exist, then create it containing your session name + start time; delete it when
   Blender exits (also on errors). If it exists, wait or do code/tests instead.
   **Only ONE Blender render at a time on this laptop** (16 GB RAM, often ~4 GB free — two Blenders crash everything).
   Before starting Blender, check `Get-Process blender`. Code, tests, research and tiny Workbench previews are fine;
   long Cycles renders wait their turn. Close Edge/Chrome tabs you don't need.
3. **Disk is ~96% full (≈20 GB free).** Downloads go through `python -m tc assets` (3 GB cap) / `tc sketchfab` /
   `tc mixamo`. Never download whole libraries. Delete your test frames when done.
4. **No commits / pushes** unless the owner says so. Never print or commit keys (`.env` holds MIXAMO_TOKEN,
   SKETCHFAB_TOKEN, FISH_AUDIO_API_KEY, Azure keys). The repo is PUBLIC.
5. **No spending money**, no AI-generated images/3D/music. Free + CC0 / CC-BY only (credit lines go in
   `library/scans/<id>/asset.json`). Mixamo raw files stay outside the repo (`C:\Users\User\tools\mocap\mixamo`).
6. **TDD for `tc/` code** (`python -m pytest`, must stay green). Blender code is verified by renders: put stills in
   `spike/lib_stills/<task>/` and run `python -m tc look <png>` (rule r10, score ≥ 80).
7. Heavily commented code (owner is learning). Era accuracy is mandatory (design from busts, vase paintings,
   museum pieces, Herodotus/Plutarch). Owner rules: `python -m tc rules`.
8. When a task is done: tick it here, add one line to `spike/review/README.md`, keep tests green.

Tools you will use: Blender 5.3 portable `C:\Users\User\tools\blender-5.3.0-windows-x64\blender.exe`
(`blender -b --python <script> -- args`), MPFB (MakeHuman) extension, `python -m tc --help`.

---

## OWNER (needs the human)
- [ ] Commit + push branch `cinematic-agent` (nothing committed yet)
- [ ] Disable the old scheduled `.github/workflows/pipeline.yml` on `main` (still runs Mon/Wed/Fri)
- [ ] Kaggle: phone-verify + API token → `.env` (free GPU rendering — needed before final renders)
- [ ] YouTube Data API key → `.env` `YOUTUBE_API_KEY` (topic demand scoring)
- [ ] Freesound API key → `.env` `FREESOUND_API_KEY` (sound effects)
- [x] Character voices picked → `library/voices.json` (5 Fish voices)
- [ ] Fish Audio: decide free vs paid before monetisation (free plan terms = non-commercial)
- [x] Mixamo account (25 motions downloaded) · [x] Sketchfab token (museum scans downloaded)

---

## WS1 Characters & faces (also: `tc cast` list/missing/promote + `blender/scenes/cast_card.py` character cards) — files: `blender/lib/cast.py`, `blender/lib/expressions.py`, `library/cast/*.json`
(this session — main thread)
- [x] Sculpted faces from portraits, skin v2, wet eyes, age lines, groomed hair/beards, 11 expressions
- [x] Talking face layer: `blender/lib/talk.py` silent_talk / listen / lip_sync(Rhubarb A-H,X); 9 mouth shapes
      verified (`spike/lib_stills/talk2/sheet.png`), teeth split at the bite line
- [ ] Lip sync: integrate Rhubarb Lip Sync (free) → mouth shapes from a dialogue WAV (check MPFB viseme targets)
- [~] Women: `cast.hair_bun` (gathered krobylos + ribbon) + `cast.groom(spec)` written, render test pending; female
      face recipes (Artemisia); jewellery → WS3; children test renders
- [~] Strand eyebrows: `cast.brow_strands` (spec flag `brow_strands`), render test pending
- [x] Cast specs: xerxes (v2 face/hair), leonidas, artemisia, aristides, eurybiades, sicinnus in `library/cast/`
      (their wardrobes come from WS3)
- [ ] Skin close-up pass: pores/micro-normal stronger on cheeks/nose, subsurface tuning, ear translucency check

## WS2 Crowds — files: `tc/crowd.py`, `tests/test_crowd.py`, NEW `blender/lib/crowd.py`
- [x] `tc/crowd.py` generator (roles, eras, no lookalikes, cast history) — tests green
- [~] Blender crowd builder `blender/lib/crowd.py` (mid people fully built + frozen skinned cloth + own clip offset;
      far = instances) + `blender/scenes/crowd_test.py` (render queued)
- [~] Eras: usa_1950s + ussr_1950s done (MakeHuman suits/work suits/fedoras, clean-shaven, 8 roles); TODO egypt,
      rome_republic, medieval
- [x] `tc assemble`: `crowd:<role>:<n>` in `who` → unique extras in the recipe, saved to `cast_history.json`; shot.py
      places them behind the actors

## WS3 Wardrobe — files: `blender/lib/wardrobe.py`, `library/wardrobe/*.json` — CLAIMED: Session D
- [x] Chiton (wide, belt folds), himation, scanned linen/wool (`scan_cloth`), settle-then-follow cloth for motion
- [x] Women's peplos + veil; exomis (one-shoulder worker tunic); child tunic; priest/priestess robes
      DONE (Session D): `wardrobe.peplos/veil/exomis/child_tunic/priest_robes`, scene `blender/scenes/ws3_wardrobe.py`,
      stills `spike/lib_stills/ws3/` (all `tc look` >= 83). Open: veil + priestess stephane tent above the crown;
      overfold flares a little at the arms; child shoulders boxy
- [x] Belts, sandals, cloak pins (fibulae), jewellery (diadems, earrings, necklaces)
      DONE: `belt` (cord+knot / strap, collider), `sandals`, `dress_pins` (perone / fibula), `diadem`, `fillet`,
      `earrings`, `necklace`. Open: pins too small to read at full shot; fibula not yet rendered
- [x] Persian: candys robe (wide sleeves, pleats), trousers, sleeved tunic, tiara/kidaris, Immortal dress → Xerxes v2
      DONE: `trousers`, `candys`, `wide_sleeves`, `median_tunic`, `tight_sleeves`, `persian_cap` (royal / fluted /
      median); Xerxes v2 = `blender/scenes/xerxes_v2.py king` (xerxes_king_v3.png, look 100). Open: squared relief
      beard (WS1), sceptre + lotus (WS7), Immortal spear/bow kit (WS4); fluted cap coded, not rendered
- [x] Wear: patches, frayed hems, sweat/dirt maps by rank (crowd `dye.grime`, `dye.patched`)
      DONE: `worn_cloth` + `crowd_cloth(name, person['dye'])`; swatches `ws3_wardrobe.py swatches [close]`

## WS4 Armour & weapons (main session added: `armour.follow_body` rigid bone-riding kit, emblem shield faces,
## `blender/lib/crowd.arm_hoplite` = unique armed extras; phalanx test queued) — files: `blender/lib/armour.py`, `library/wardrobe/greek_hoplite_480bc.json`
- [ ] Armour follows the body in motion (bind cuirass/greaves/helmet to bones; no clipping on a walk)
- [ ] Compare our Corinthian helmet with the CC0 museum scan `library/scans/helmet_corinthian_cleveland` (glb);
      either adopt the scan (retexture bronze) or improve ours
- [ ] Helmet variants (Chalcidian, pilos), crest colours, commander's tall crest
- [x] Shield emblem painter `tc/emblems.py` (`tc emblems <dir>`): all 22 emblems, vase-painting colours, round alpha
      texture (v1 animals are simple silhouettes) — TODO: map onto `armour.aspis`
- [ ] Linothorax, spear/sword variants, Persian wicker shield (spara), bows + quivers, scale armour

## WS5 Motion & acting — files: `blender/lib/motion.py`, `blender/lib/pose.py`, `blender/lib/life.py`
- [x] CMU + Mixamo retargeting onto the full face rig, life layer, gestures, two-bone `pose.reach` (hand contacts)
- [x] All 25 Mixamo clips tested (`blender/scenes/mixamo_test.py`, report in spike/lib_stills/mixamo/): no failures;
      8 floated (up to 1.66 m) → per-frame grounding `motion.ground_feet` added (re-test queued)
- [~] Grounding done (feet on the floor every frame); hand contacts done (`pose.reach`); TODO foot-sliding lock
- [ ] Sitting on a chair/throne, kneeling, bowing sequences; clip blending (idle → gesture → idle)
- [ ] Action index: tag every clip with action words; expand `tc/assemble.py ACTIONS` from it
- [ ] Rowing animation (oars in stroke + rowers), fighting choreography (two-person exchanges)
- [ ] Horse: test `library/scans/horse_akhalteke` (CC-BY, rigged + 3 animations); era-correct saddle cloth + bridle;
      rider sitting on it

## WS6 Sets & environments — files: `blender/lib/sets.py`, `blender/lib/scatter.py`, `library/sets/*.json`
(this session owns Salamis v2)
- [x] Salamis v2 cove with real scans (rocks, grass, bushes, trees), sandstone wall, amphorae, haze
- [~] Mountains: Voronoi erosion ridges added to `sets.land` (render check pending); scanned rock at distance
- [~] Athens 480 BC: `lib/architecture.py` (Doric temple kit, painted polychrome; houses) + `sets.athens_480bc` with
      the Old Temple of Athena on a flat-topped `sets.mesa` Acropolis (no Parthenon in 480 BC!); TODO: streets/agora,
      tiling-break check, burning version
- [~] Thermopylae: `sets.thermopylae_480bc` (coastal shelf, Kallidromos cliffs, Phocian wall) written, render pending
- [~] `sets.xerxes_throne_aigaleos` (Herodotus 8.90): pavilion, golden throne, standards, camp tents — render queued
- [~] Interiors: `architecture.palace_hall` + `sets.persian_palace_interior` (light shafts) render queued; TODO house
      courtyard, temple interior
- [~] Day skies: `common.hdri_sky` (camera sees real clouds, scene lit gently) used by Athens; TODO night/moon
- [~] FX `blender/lib/fx.py`: smoke columns, flames (blackbody), flickering fire light, embers; used by burning Athens;
      TODO dust, sea spray, wakes

## Animals (main session): downloaded CC-BY/CC0 camels (animated), sheep (animated), seagull, raven (museum CC0) to
## library/scans/animal_*; `fx.bird_flock` (flapping gull/crow flocks, used over Salamis). TODO dogs, goats, oxen, horses (WS7)

## WS18 Animals & cavalry — CLAIMED: Session G (2026-11-20)
Files: NEW `blender/lib/animals.py`, NEW `blender/lib/cavalry.py`, NEW `blender/lib/harness.py` (carts, chariots,
limber), new functions appended to `blender/lib/fx.py` (hoof dust), NEW `blender/scenes/animals_*_test.py`,
NEW `blender/scenes/cavalry_test.py`, `library/scans/animal_*` (new downloads), `spike/lib_stills/ws18/`.
Read-only use of scans_glb/props (Session E), riding/cannon/crowd/cast (main), market/countryside (Session D).
- [ ] Animal library: oxen, donkeys/mules, goats, sheep, dogs, pigs, chickens, camels, war elephants, cats, ground
      birds — real size, own walk/idle where rigged, herd/flock scatter helper, credits in asset.json
- [ ] Animal life: grazing herd, moving flock + shepherd, trotting dogs, pecking chickens, ox-cart, donkey + panniers,
      market animals (for Session D)
- [ ] Cavalry: riders in formation (walk/trot/gallop/charge), era riders (Persian/Greek/Roman/medieval), spear/bow
      while riding, charge test with hoof dust
- [ ] Horse-drawn: chariots (Egyptian 1250 BC, Persian), wagons, Napoleonic limber towing `cannon.build('field')`

## WS16 Countryside (owner request 2026-11-19) — files: NEW `blender/lib/countryside.py`, NEW `blender/scenes/countryside_test.py`, NEW `library/sets/countryside_*.json` — CLAIMED: Session D
- [ ] Grain fields (wheat / barley, swaying, ripe vs green, stubble after harvest), ploughed furrows, fallow
- [ ] Vineyards (low staked vines in rows), olive groves laid out in rows (uses WS6's `tree_olive_zakynthos` scan)
- [ ] Dry-stone field walls + hillside terraces, threshing floor (round paved), farm paths
- [ ] Farmstead: rubble-and-mudbrick farmhouse with courtyard + round farm tower (Attic/island farm towers), beehives
- [ ] Countryside test scene composing it all on a hillside at dusk (uses `sets` terrain/sky helpers read-only)
- [ ] WIND: standing crops + vines move (geometry-node gust waves + flutter, `countryside.wind_scatter`); test clip
- [ ] Daily life — NEW `blender/lib/market.py`, `blender/scenes/daily_life_test.py`: market stalls by trade
      (fish, bread, produce, pottery, oil, wool, grain), goods, merchant's balance, owl coins; villages (houses from
      `architecture.house`, yards, well, bread oven, threshing floor); fishermen's beach (`props.fishing_boat`, nets,
      fish rack). People by trade: `tc/crowd.py` roles farmer/shepherd/potter/smith/trader/villager (+ test) dressed
      by `wardrobe.dress` (exomis/perizoma/pilos/petasos/purse)
- [ ] Tools — NEW `blender/lib/tools.py`: ard plough + yoke, ox team (cow scan), cart with cross-bar wheels, sickle,
      mattock, winnowing shovel, pruning hook, crook, trident, rod, fish trap, carrying pole; `hold()` puts a tool in a
      hand; `dress()` gives each trade its tool

## WS7 Props & ships — files: `blender/lib/props.py`, NEW `blender/lib/scans_glb.py` — CLAIMED: Session E
Owner 2026-11-20: MAXIMUM (hero) quality, "ships majestic", RICH scenes (layered, no plain backgrounds, people in them).
Renders: GitHub render-batch (`cloud/requests/ws7_*.json`; ask Session D / main before pushing cloud/batch.json - the
queue workflow `render-queue.yml` is not committed yet). Museum Sketchfab scans exist only on the laptop.
- [x] glb loader `scans_glb.load_glb` (museum size, IOR-1000 mirror fix, rigged scans, placeholder when missing on CI)
- [x] Museum pottery + helmet (era manifests); horse 1.42 m withers + `horse_tack` (no saddle/stirrups)
- [x] Scanned materials (wood/linen/leather/rope/wicker) + edge wear/grime, code-drawn meander, flame tongues (colour ramp)
- [x] Furniture, lamps, braziers, baskets, rope, anchor; Phoenician trireme v1; fishing boat
- [x] Trireme v3 majestic kit, instanced (1 s first ship / 0.2 s copies), `fleet()`, hero camera; eye plates, painted
      outrigger, 5-tip aphlaston, stolos, stylis + pennants, side-screens, 3-strand LAID ROPE rigging (`_bm_laid_rope`)
- [x] Set sail = real cloth simulation (`trireme_sail_cloth`, wind 700 / 60 fr) + panel puff between strips/brails
- [x] Oar splashes, thranite rowers, bow wave + wake
- [x] Story props: Athlit ram, wreck debris, Delphi tripod / omphalos / suppliant branch, burning timber barricade,
      scribe kit, royal parasol, incense burner, phiale, rhyton, carpet
- [x] RICH kits: `dress_andron` (painted room shell + wall clutter), `dress_symposion/storeroom/quay`, `dress_harbour`,
      `dress_persian_camp` (`persian_tent`: striped panels, valance, guy ropes), `dress_beach_camp`; Aigaleos court dressing
- [x] `populate(kit, era, camera)`: role markers -> REAL crowd extras (lib/crowd) + instances; people ride moving ships
- [x] Ship PLACES for Session B's shots (marks for people + cameras): `place_trireme_rowing_hold` (seated rowing extras
      via `row_seated`, light shafts), `place_trireme_deck`, `place_persian_flagship` (night, fleet lanterns)
- [x] Sketchfab scan audit (`ws7_scan_audit.py` -> `spike/lib_stills/ws7/scan_audit.json`); findings passed to G + D:
      hound probably lying on its side, cat ~150 km, cypress bark lost textures, no size for cow / dog_run / seagull /
      camels / horse_realistic (horse + raven "duplicates" are only 65k-vertex chunks)
- [ ] Rowing hold: rowers still too dark to read; needs WS5 rowing mocap for a convincing stroke
- [ ] Seated / reclining extras (symposion guests, riders) need WS5 sitting + reclining clips (markers already placed)
- [ ] Museum cups/amphorae appear only in laptop renders (R2 cache needed for CI)

## WS8 Lighting & camera — files: NEW `blender/lib/lighting.py`, `blender/lib/camera_moves.py`
- [x] `blender/lib/lighting.py` film_lights(subject, camera, mood): dusk/day/night/firelit/interior/menace; used by shot.py
- [ ] God rays / volumetric shafts (interiors, forest), sun through leaves
- [ ] Shot-type camera rules: lens + distance + focus per shot type (close-up 85 mm f/2, medium 50 mm, wide 28 mm) — CLAIMED: Session D
- [ ] Camera grammar (Session D): rack focus, dolly zoom, layered handheld, impact shake, whip pan, 180° motion blur
- [ ] Every shot through `tc look` + `tc finish` before review

## WS9 Rendering infrastructure — files: `cloud/`, `.github/workflows/`, `tc/render_plan.py` — CLAIMED: Session C
- [x] Kaggle GPU render notebook: `tc kaggle <job> --shard N [--resume]` writes notebook + metadata (`cloud/kaggle/render_shard.py`); GPU OptiX/CUDA, only needed scans, 11 h budget, resume. Needs owner Kaggle token to push
- [x] GitHub Actions CPU shards: `.github/workflows/render-shards.yml` (≤20 runners, manual start, artifacts, resume_run_id, report). Needs owner push + run
- [x] Asset cache: `tc cache index|plan|built|fetch|push`, `library/scans_index.json`, `cloud/build_asset_cache.py`, `cloud/r2_push.sh` (6 GB budget). Needs owner R2 bucket; WS10 must append cached .blend in build.py
- [x] Denoise (OIDN) + lower samples + adaptive; Eevee for wide/landscape (`tc render-plan --speed`, `cloud/blender_shot.py`); estimates until M3 measures
- [x] Resume + frame checks (missing/black/broken) + requeue + join: `tc render-shard`, `tc frames check|requeue|join` (`tc/render_farm.py`)
- [x] Cloud render QUEUE (replaces shared `cloud/batch.json`): `tc queue submit|list|run|kaggle`, one file per request in `cloud/queue/`, `.github/workflows/render-queue.yml` (renders only files a push added), Kaggle GPU still kernel (`cloud/kaggle/render_still.py`, OIDN). Test requests for `cannon_test.py` queued (GPU + CPU). Needs: push of tc/ + cloud/ + workflow, owner OK for the Kaggle push; batch.json retirement = owner

## Main session sets added tonight: athens_480bc (+burning, fx), thermopylae_480bc, xerxes_throne_aigaleos, persian_palace_interior,
## salamis_night_v2, courtyard_house (architecture), lab_1950s (modern.py) — fixes/tests in the render queues

## WS10 Shot pipeline — files: `blender/scenes/shot.py`, `blender/lib/build.py`, `tc/assemble.py`
- [~] `shot.py` uses: full-face-rig mocap, settle-follow cloth, expressions, talk/listen, life layer (done, CLAIMED: main);
      still to add: crowds, museum props, finishing
- [ ] Contact-sheet gate: render one still per shot → sheet → `tc look` → owner review before full render
- [~] Shorts: `shot.py` vertical 1080x1920 mode (`format: short`): own camera, tighter, wider lens; TODO safe areas

## WS11 Audio — files: NEW `tc/sfx.py`, NEW `tc/dialogue.py`, `tc/voice.py` — CLAIMED: Session A
- [x] Dialogue: script lines `NAME: "..."` → Fish Audio voice per character (`spike/voices_fish/` tests), log every
      Fish line used (`library/fish_usage.json`)
      DONE `tc dialogue <id>` (free model only, cached, splices into voice.wav via `tc voice`; live-tested)
- [x] Rhubarb lip sync from dialogue WAV → mouth-shape timeline for WS1
      DONE `tc/lipsync.py`, Rhubarb 1.14 in `C:/Users/User/tools/rhubarb`; `jobs/<id>/lipsync.json` (cues + mouth
      controls jaw/round/closed/wide/teeth_lip/tongue + one shape per frame) for WS1
- [x] SFX sources: Sonniss GDC bundles (best, no credit; download only needed categories), Pixabay SFX (no credit),
      The Beat / PremiumBeat free packs, Freesound (filter per sound: CC0 / CC-BY only, NEVER CC-BY-NC; write credit
      lines). SFX fetch; layered sound design per shot (march = steps + armour +
      spears + chant + wind); ambiences (sea, wind, crowd walla, fire)
      DONE code: `tc sfx add|fetch|plan` -> `jobs/<id>/sound.json`. LIBRARY EMPTY: needs FREESOUND_API_KEY (owner)
      and hand downloads (Sonniss categories / Pixabay) registered with `tc sfx add`
- [x] Music: ONLY at chosen moments (rule r11: hook, tension, battle/climax, emotional beats, ending); other scenes =
      ambience + SFX only. The agent must CHOOSE music by meaning:
      1. `library/music/tracks.json`: every track tagged mood (tension, menace, mystery, grief, triumph, awe, hope,
         dread), intensity 1-5, era fit (ancient: lyre/aulos/frame drum/choir · epic orchestral · cold-war/modern: dark
         strings, synth pulse), shape (slow build / steady / hit / fade-out), length, tempo, licence, source
      2. shot list gets `music: {cue, mood, from, to, era}` only where r11 allows (script structure gives the beats)
      3. picker: best tag match; start on a line/cut, put the track's peak on the climax shot, fade out on a story beat,
         duck under narration, swell in gaps; never the same track in two consecutive videos (`library/music/used.json`)
      4. learning: retention dips during music + owner feedback → rules (`tc learn`)
      Sources: YouTube Audio Library, Pixabay Music (free commercial), FMA CC0/CC-BY
      DONE code: `tc music add|pick|learn` -> `jobs/<id>/music.json`. CATALOGUE EMPTY: tracks to be downloaded by hand
      + tagged with `tc music add`
- [x] Mix + loudness standard (check owner audio rules), Shorts louder
      DONE `tc mix <id>` -> `mix.wav` 48k stereo: long -12 LUFS, Shorts -10 LUFS, TP <= -1 dB, music+ambience ducked
      under voice (CapitalCode-approved levels; owner to confirm by ear on the first real video)

> NOTE for Session A (WS11) from Session D: `tc edit` now cuts the picture; for J/L cuts (pro-editor feel) the
> ambience beds in `tc/sfx.py plan` could start the NEXT place's bed ~0.8-1.2 s BEFORE its first shot (J-cut) and let
> the old bed tail ~1 s past the cut (L-cut) on place changes, instead of a crossfade centred on the cut. Picture
> timing is unchanged (shots.timed.json), so nothing else needs to move.

## WS12 Edit & finish — files: NEW `tc/edit.py`, `tc/finish.py` — CLAIMED: Session D (owner request 2026-11-19)
- [x] `tc finish` film look (grade, bloom, grain, vignette)
      + Session D: looks golden_hour / cold_dawn / firelight / battle (bleach bypass) / flashback; layers halation,
      bleach, chromatic aberration, anamorphic streak (all verified on a real still)
- [x] Timeline assembly: shot renders + narration + dialogue + music + SFX → master (ffmpeg), 2.35:1 letterbox
      DONE `tc edit <job>` (`tc/edit.py`, 11 tests): fade-in, cuts on the line, dissolve on place change, `fade_black`
      dips, held frame under dissolves (keeps sync), film look under the text, end card, mix audio → master.mp4
- [x] Place/date cards and map labels (only allowed text), end card — DONE in `tc edit` (serif, low-left, fades; r3 gate)
- [x] QA: black frames, audio sync, loudness, length, missing shots — DONE `edit.qa` → edit.json (planned fades ignored)

## WS13 Script, research, packaging — files: `tc/script.py`, NEW `tc/research.py`, `tc/packaging.py` — CLAIMED: Session B
- [x] Dialogue lines in the script format (`NAME: "..."  [dramatised]` or `[source: ...]`) + checker: no fixed
      limit (owner 2026-11-19); a source is required only for lines presented as real quotes; dramatised lines allowed (rule r12);
      packaging adds 'Some dialogue is dramatised.' to the description (`tc description <id>`)
- [x] Research stage: sourced facts file per job (Herodotus, Plutarch, modern historians) — `tc research <id>
      --world salamis_480bc --topics ...` (world sheet `library/research/salamis_480bc.json`, 37 facts)
- [x] Thumbnails rendered from the 3D scenes (big face + emotion + era detail), 3 variants — `tc thumbnail`
      (plan + render requests + finish + phone check done; Blender `blender/scenes/thumbnail.py` = TODO in
      `tc/thumbnail.py render_request`, needs WS1/WS8)
- [x] First test series: 5 Salamis-world Shorts (secret message, Xerxes' throne, rams, Athens burning, the oracle)
      — jobs `20261119-1824-*` (script.md passes `tc script`, awaiting owner approval; thumbs/plan.json)

- [x] 2026-11-20 overnight (Session B): 5 Shorts polished (hook -> story -> twist, every narrator line sourced; new fact
      `f-trap-why`), `shots.json` per Short (11-12 shots) with the VISUAL_STANDARD s4 performance spec for every person +
      varied camera; new `tc perf <id>` checker (`tc/performance.py`); `Shot.performance` field added in `tc/shots.py`.
      Needs: cast specs for `ameinias`, `aristonice`, `old_steward`; new sets listed in each job's shots (no renders).

## WS14 Learning & analytics — files: `tc/learning.py`, NEW `tc/analytics.py`
- [ ] YouTube Analytics after upload (OAuth): swipe-away, % watched, subs per 1k views → rules
- [ ] Look-gate history (which settings passed) → defaults for next videos

## WS17 Modern era (1940s-60s secret projects) — CLAIMED: Session F
Files: `blender/lib/modern.py`, NEW `blender/lib/modern_props.py`, NEW `blender/lib/modern_dress.py`, new functions appended to `blender/lib/fx.py`,
NEW `blender/scenes/modern_*_test.py`, NEW `tc/archive.py` + `tests/test_archive.py`, the usa_1945/usa_1960/ussr_1960 block
in `tc/crowd.py` (+ its tests), `cloud/requests/modern_*.json`, `spike/lib_stills/modern/`. Sources in each docstring.
- [~] Sets (`modern.py`): government_office, bunker_command, hangar, desert_test_site (Trinity), interrogation_room,
      psych_ward, mission_control, los_alamos_huts - code written, sources in docstrings; first renders pending
- [~] Props (`modern_props.py`): typewriter, rotary phone, reel-to-reel, stamped folders, Geiger counter, projector,
      desk/chair/filing cabinet/blinds/clock/lamp, jeep, truck, sedans, B-29 shape, jet, V-2 / Redstone / R-7, gantry
- [x] People: eras usa_1945 / usa_1960 / ussr_1960, 10 roles, clothes by sex, adult ages, overlays (tests green).
      `modern_dress.py`: rebind_mpfb_clothes (MakeHuman suits no longer tear when posed - now also called by
      cast.build_human), redye (olive drab reads olive), caps (garrison/peaked/Soviet/pilotka/patrol/flat/nurse),
      ribbons. Open: lab coat + gown skirt shape (v3 in test), still `spike/lib_stills/modern/people/`
- [~] Big moments: `fx.atomic_test` (flash, fireball, cap, stem, base surge) + `fx.rocket_launch` - render pending
- [x] "Declassified archive footage" look: `python -m tc.archive in out --look kinescope|aged_print|test_film [--pillarbox]`
- [~] Test scenes: `blender/scenes/modern_{office,bunker,hangar,desert,interrogation,ward,mission,huts,props,vehicles,atomic,rocket}_test.py`
      (shared runner `modern_shot.py`, error check `modern_dry_build.py`)

## WS15 Housekeeping
- [ ] Keep `README.md`, `blender/README.md`, plan docs current
- [ ] Final whole-branch code review before the owner commits

## WS18 Animals & cavalry — reserved for Session G (owner set up 2026-11-20)
- NOTE from Session D: these load animal scans through `scatter.load_scan` today and should switch to
  `blender/lib/animals.py` once it exists: `countryside.flock`, `tools.ox_team`, `market.caravan`.
- `scatter._load_glb_variant` now drops helper meshes (bounding/collision boxes) before sizing (camel bug).
- NOTE from Session D (for Session G): `animal_camels` does not render yet. After the helper box is dropped the adult
  camel (Object_12 + eyes Object_13, skinned to armature Object_9) measures ~0.1 m: the hierarchy carries scales 0.01
  (camel.fbx), 100 (metarig.001, c, Object_11), 109 (Cube); rescaling the top ancestors gives an untextured orange camel
  in the wrong place. Textures are lost (flat orange). Call site: `market.caravan(...)`; debug: `blender/scenes/camel_check.py`.

## WS19 Maps (owner request 2026-11-20, rule r14) — spec `docs/MAP_STYLE.md`, refs `reference/maps/` — UNCLAIMED
- [ ] Parchment map base: crumpled plane, parchment shader, sea wave engraving, vignette
- [ ] Natural Earth coastlines/rivers → era polygons; stamp scatter (trees, mountains, dunes)
- [ ] Territory fills with emblem patterns + ink-spread grow animation
- [ ] Labels: curved region names, scroll-tag city/leader labels, date strip
- [ ] Animated arrows, pulse rings, battle marker, spotlight
- [ ] Tactical battle map: town of tiny houses, contours, compass rose, extruded unit blocks + banners
- [ ] Shot kind `map` + `map_action` in tc/shots.py; tilted drifting camera preset
- [ ] Side-by-side still vs reference 02 and 05 before any video use

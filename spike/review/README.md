# Morning review — night build of 2026-11-19

## Look at these first
1. `library_contact_sheet.jpg` — everything built tonight (hero shot, set, trireme, Themistocles, hoplite, helmet, face, Xerxes)
2. `compare_ref_vs_ours.jpg` — our renders next to Heroes of Bronze frames (quality ruler only, never copied)
3. `../lib_stills/hero_anim.mp4` — 5-second animated shot (camera push-in, moving sea, servant's bow) — if the render finished
4. `../lib_stills/mocap_walk_v3.mp4`: Themistocles **walking with real motion capture** (CMU), chiton and himation following the body (v2 = the "cape" problem, fixed in v3)
5. Full-size stills: `../lib_stills/` (`hero_salamis_v8.png`, `dressed_med_v2.png`, `hoplite_head_v3.png`, `trireme_v1.png`, `salamis_set_v8.png`)

## Honest quality vs the reference (~50–55% overall)
| Strong already | Weakest |
|---|---|
| cloth folds (real simulation), strand beards/hair, bronze helmet + crest, sea, era accuracy | skin realism in close-up, flat light in some shots, bare hills (no trees/buildings), Xerxes costume (v1), static armour (not yet animated) |

## Built this morning
- **Motion capture works**: world-space retargeting (any CMU clip onto our characters), feet planted, calibration T-pose skipped, eyes/brows/teeth now follow the head (they never did before)
- **Moving cloth**: garments drape standing still first, then follow the body with soft pins, so wool hangs heavy instead of streaming like a cape
- **Shot assembler**: `python -m tc assemble <job>` turns every shot into a build recipe (cast + wardrobe + set + motion + camera) and lists library gaps; `blender/scenes/shot.py` builds and renders any recipe; film camera vocabulary (push in, pull out, pan, tilt, track, orbit, crane, handheld) in `blender/lib/camera_moves.py`. Tests: 84 passing

## Built this afternoon (people + sets push)
- Faces: sculpted per historical portrait, age lines/folds, living skin colour, wet eyes with clear cornea, 11 expressions
- Hair/beards: curly locks, soft hairlines, beard follows the jaw
- Life layer: breathing, blinks, eye saccades, weight shift; mocap on the full face rig
- Clothes: real scanned linen/wool, wide chiton gathered into folds, free neckline
- Sets: Salamis v2 cove with real scanned rocks/grass/bushes/trees, sandstone wall, terracotta amphorae, aerial haze
- `tc look`: measures each render against the closest-mood reference frames (rule r10)
- Stills: `../lib_stills/portrait_v2f.png`, `dressed_v2c_med.png`, `salamis_v2e/`, `hero_v2/`

## What needs you
- Commit + push the branch `cinematic-agent` (nothing is committed; old code is tagged `old-pipeline-final`)
- Old scheduled workflow `pipeline.yml` still runs on **main** on GitHub (Mon/Wed/Fri) — disable it or merge the branch
- Free YouTube Data API key → `.env` as `YOUTUBE_API_KEY=` (topic demand scoring)
- Kaggle: phone-verify the account + create an API token (free GPU rendering)
- Rate the stills (the scores go into each asset's manifest)
- Free **Mixamo** login (mixamo.com, Adobe account): fight / sit / kneel / gesture motions — I'll give the download list
- Free **Sketchfab** account + API token: CC0 museum scans (Greek pottery, helmets, statues) and CC-BY horses
- Free **Freesound** API key: sound effects (marching, armour, swords, crowds, sea)
- 2026-11-19 WS11 Audio (Session A): `tc dialogue` (Fish free model, usage log), lip sync (Rhubarb -> lipsync.json), `tc sfx` (licence gate, Freesound, layered design + ambience beds), `tc music` (r11 cues, tagged catalogue, picker, used.json, retention lessons), `tc mix` (ducking, long -12 / Shorts -10 LUFS). Libraries still empty.
- 2026-11-19 WS13 Script/research/packaging (Session B): script dialogue (`NAME: "..." [dramatised]` / `[source: ...]`, max 2, Line.speaker/voice_key/spoken + `speakers()` for voice/shots), `tc description` (r12 note), `tc research` + `library/research/salamis_480bc.json` (37 sourced facts), 5 Salamis Shorts in `jobs/20261119-1824-*` (pass `tc script`, need owner approval), `tc thumbnail` (3 variants, render requests, finish + phone check; Blender scene = TODO).
- 2026-11-19 WS9 Render infra (Session C): `tc render-plan --speed` (shot type -> Eevee/Cycles+OIDN, samples, s/frame estimates), `tc render-bundle`, `tc render-shard` (progress.json resume, missing/black/broken frame checks + retry, stall watchdog, time budget, cloud-side join), `tc frames check|requeue|join`, `tc cache` (scans_index.json, per-shard scan download, R2 layout + 6 GB budget, built .blend keys), `tc kaggle` notebook builder, `.github/workflows/render-shards.yml` (20 CPU runners). Nothing pushed/run; untested on real cloud machines (owner: Kaggle token, push, R2). See cloud/README.md.
- 2026-11-19 WS3 Wardrobe (Session D): **peplos** (saffron wool, overfold, 2 pins/shoulder, armholes, A-line skirt, woad hem, sandals, earrings) — `lib_stills/ws3/woman_pins_v2.png` (look 83)
- 2026-11-19 WS3 Wardrobe (Session D): **exomis** (one shoulder bare, rope belt, worn poor cloth: stains, patches, frayed hem) — `lib_stills/ws3/servant_v1.png` (look 100; patches since made smaller)
- 2026-11-19 WS3 Wardrobe (Session D): **wear by rank** (royal/rich/common/poor from `tc/crowd.py` dyes) — `lib_stills/ws3/wear_swatches_v3.png` (look 100), hem close-up `wear_close_v1.png`
- 2026-11-19 WS3 Wardrobe (Session D): **veil** (mantle drawn over the head, madder border) — `lib_stills/ws3/woman_veil_v1.png` (look 83; sits a bit high on the crown)
- 2026-11-19 WS3 Wardrobe (Session D): **child's tunic** (belted at the child's waist, madder hem, barefoot) — `lib_stills/ws3/child_v3.png` (look 100)
- 2026-11-19 WS3 Wardrobe (Session D): **priest** (long white chiton, himation with purple border, wool fillet, sandals) — `lib_stills/ws3/priest_v1.png` (look 100)
- 2026-11-19 WS3 Wardrobe (Session D): **priestess** (long white chiton, mantle over the head, gold stephane, necklace) — `lib_stills/ws3/priestess_v2.png` (look 100; stephane sits high)
- 2026-11-19 WS3 Wardrobe (Session D): **Xerxes v2** (upright tiara + gold rosettes, pleated candys with hitched hem, wide gold-bordered sleeves, gold belt, crimson trousers) — `lib_stills/ws3/xerxes_king_v3.png` (look 100); scene `blender/scenes/xerxes_v2.py`
- 2026-11-19 WS3 Wardrobe (Session D): **Median dress** (felt cap with flaps, sleeved ochre tunic, belt, trousers) — `lib_stills/ws3/median_v5.png`
- 2026-11-19 WS7 Props (Session E): **glb scan loader** `scans_glb.load_glb` (real museum size, base on ground, material fix incl. the IOR-1000 mirror bug) — `lib_stills/ws7/pottery_v3.png` (look 83)
- 2026-11-19 WS7 Props (Session E): **museum pottery** black-figure amphora (c. 540), neck-amphora (515-510), Met amphora (c. 510), Douris kylix (c. 480), bell-krater (430-410, background only) — `ws7/pottery_v3.png` (83), `ws7/pottery_close_v2.png` (83)
- 2026-11-19 WS7 Props (Session E): **Corinthian helmet scan** (Cleveland, 500-475 BC, real patina) — `ws7/pottery_close_v2.png` (83)
- 2026-11-19 WS7 Props (Session E): **horse** (CC-BY) at 1.42 m withers, trot/gallop/chewing play — `ws7/horse_trot_f10_v3.png` (100), `ws7/horse_persian_gallop_f20_v2.png` (100, pre-fix straps)
- 2026-11-19 WS7 Props (Session E): **horse tack** saddle cloth greek/persian + girth + bridle + bit + reins, follows the animation, no saddle/stirrups — `ws7/horse_trot_f10_v3.png` (100)
- 2026-11-19 WS7 Props (Session E): **trireme v2** rowing oars (looping stroke), steering oars, crew markers + proxies, motion/swell — `ws7/oars_f1_v1.png` + `ws7/oars_f16_v1.png` (100); sail not yet rendered
- 2026-11-19 WS7 Props (Session E): **Phoenician trireme** (red hull, shield rail, high deck, conical ram, pataikos) — `ws7/fleet_v1.png` (100)
- 2026-11-19 WS7 Props (Session E): **fishing boat** (nets, catch basket, rope, stone anchor, eyes) — `ws7/boat_v2.png` (100)
- 2026-11-19 WS7 Props (Session E): **furniture** klismos, kline, trapeza, footstool, kibotos chest — `ws7/furniture_v3.png` (look 67: too warm; kline blanket needs fix)
- 2026-11-19 WS7 Props (Session E): **light + fire** oil lamp, lamp stand, bronze + clay braziers (charcoal, flames, flicker) — `ws7/furniture_v3.png`, `ws7/furniture_close_v2.png` (67; flame reads as haze)
- 2026-11-19 WS7 Props (Session E): **baskets, rope coil, stone anchor** — basket in `ws7/furniture_v3.png`; rope/anchor built but not yet framed
- 2026-11-20 WS12 Edit (Session D): **`tc edit <job>`** cuts the master: fade-in, cuts on the line, dissolve on place change, dip to black, place/date cards (serif, low-left), 2.35:1 letterbox, end card, film look, QA (black frames, length, loudness, missing shots) — demo frames checked
- 2026-11-20 WS12 Finish (Session D): **5 new film looks** (golden_hour, cold_dawn, firelight, battle bleach-bypass, flashback) + halation, chromatic aberration, anamorphic streak
- 2026-11-20 WS12 Match (Session D): **`tc/match.py` shot matching**: every shot of a place matched to its hero shot (exposure curve, cast, saturation, clamped so moods survive); runs inside `tc edit`
- 2026-11-20 WS7 Props (Session E): **contact sheet v2** `spike/review/ws7_contact_sheet_v2.jpg` (renders on GitHub render-batch, ~3 min per batch)
- 2026-11-20 WS7 Props (Session E): **trireme v3 majestic kit** (eye plates, painted outrigger, 5-tip aphlaston, stolos, stylis + pennants, side-screens, brails, salt-streaked pitch) + hero shots — `ws7/gh_ship_hero_v3.png` (83), `ws7/gh_ship_hero_sail_v2.png` (100), `ws7/gh_ship3_close_v4.png` (100)
- 2026-11-20 WS7 Props (Session E): **fleet()** instanced triremes (1 s first, 0.2 s each) — `ws7/gh_fleet_v2.png` (ships too small on the horizon: framing still to improve)
- 2026-11-20 WS7 Props (Session E): **story props**: wreck debris `ws7/gh_story_debris_v2.png` (100), burning wooden wall `ws7/gh_story_wall_v5.png` (83), Xerxes' court (canopy, carpet, incense burners, phiale, rhyton, scribes) `ws7/gh_story_court_v2.png` (67, too flat), Athlit ram `ws7/gh_story_ram_v3.png` (100), Delphi tripod/omphalos/branches `ws7/gh_story_oracle_v3.png`, scribe kit `ws7/gh_story_scribes_v2.png`
- 2026-11-20 WS7 Props (Session E): **dressing kits** symposion / storeroom / quay — `ws7/symposion_kit_v1.png`, `ws7/quay_v1.png`
- 2026-11-20 WS7 Props (Session E): **materials**: scanned wood/linen/leather/rope/wicker, edge wear + grime, code-drawn meander, fire tongues with colour ramp (no white blow-out)
- 2026-11-20 WS7 Props (Session E): **rich andron** in one call (`props.dress_andron`): painted room shell (red dado, black zone line, meander frieze, beamed ceiling, raised couch platform, door curtain), wall pegs with cups/wreaths/lyre/aulos case/baskets, shelves of jugs, woven hangings with meander borders, mats, sandals, amphorae on ring stands, guest markers for the crowd — `ws7/gh_andron_v3.png` (look 100; museum cups only appear in laptop renders)
- 2026-11-20 WS7 Props (Session E): **cloth-simulated sail** (pinned yard + sheets, stiffer seams, wind 300 → 1.4 m belly) + panel puff — `ws7/gh_ship_hero_sail_v4.png` (100; still flatter than the reference)
- 2026-11-20 WS7 Props (Session E): **Sketchfab scan audit** of 28 scans — findings in docs/BACKLOG.md WS7 + `ws7/scan_audit.json`

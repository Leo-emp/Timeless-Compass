# Timeless Compass — Drawing Standard (ART BIBLE)

Read before every art-direction, cast, shot-plan, draw, stills and thumbnail stage. Every rule here is meant to be
checked: by the measured checks (`tc still`, `tc motion`, `tc era`) or by the scored still checklist (`tc qa … still`,
section 10). **Goal (r31): a cinematic 2D animated film — never a slideshow of drawings.** The reference video
(Japan history, `Downloads/videoplayback (13).mp4`) is the **floor, not the target** (r18).

---

## 1. Construction (rule r16 — cast style v1, approved 2026-11-21)

| Part | Rule |
|---|---|
| Proportion | Head ≈ **40 %** of standing height (head radius 60 units in a ~420-unit figure). Body short and simple |
| Eyes | Small solid dots (rx 6.5, ry 8–9) with one white glint; shocked = rx 9, ry 12 |
| Brows | Short, thick (6–7 units). They carry most of the emotion |
| Nose / mouth | One small curve each. Mouth shapes change with expression and lip sync |
| Outline | One warm dark brown `#2a1c13`, never pure black. **7 units on characters, 4 on backgrounds, 2–3 on far/small things** |
| Colour | Flat fills + **one** soft shade on the side away from the light (ellipse clipped to the shape, ~16 % darker) |
| Hands | Simple round fists. **A held prop is drawn first, the hand after it** — the hand visibly wraps it (owner rule "props in hand") |
| Skin | Correct for the time and place, never one default (Greek warm tan, Egyptian brown, Japanese light, etc.) |
| Identity | Named characters always come from their saved sheet (r19): same face, hair, beard, build, colours, signature costume |

## 2. Composition

1. **One clear focal point** per shot: the thing the line is about. It is the largest, brightest or most contrasted element.
2. **Rule of thirds:** the focal point sits on a third line or intersection; horizon on a third, never dead centre (unless a deliberate symmetric power shot).
3. **At least 5 depth layers** in every set: sky / far / mid / hero / foreground framing. Each is its own `<g>` so the camera can move them at different speeds.
4. **Foreground framing** in wide shots: rocks, columns, branches, a doorway or crowd heads at the edges.
5. **No tangents:** shapes must clearly overlap or clearly separate — never just touch (a spear tip touching the frame edge, a head touching a roof line).
6. **Nothing covers a face** that is acting (no spear, banner, text or hand drawn over it). Checked by `tc still`.
7. **Safe areas:** faces fully inside the frame with ≥ 1 % margin; text ≥ 3 % from every edge.
8. **Scale tells the story:** small figures in a vast place = isolation or awe; a big close face = emotion. Default framing for story beats is full-body or three-quarter (zoom ≤ 1.3× on a character).
9. **Shorts (9:16) are composed for vertical** — subject stacked vertically, never a 16:9 picture cropped.
10. **Every place in a video is designed once, shot many ways** (r23): new angle, distance, action or time of day each time; a different place is a brand-new set.

## 3. Light and atmosphere — where we beat the reference

The reference is evenly lit and flat. Ours has a lighting plan per scene.

| Time | Sky top → horizon | Key light | Shadow tint | Use |
|---|---|---|---|---|
| Dawn | `#e9a77a` → `#fde9c4` | low, warm gold from the side | `rgba(80,35,15,.18)` | beginnings, hope |
| Noon | `#7fb4d6` → `#f8e3b8` | high, neutral | `rgba(60,40,20,.14)` | ordinary world, explanation |
| Dusk | `#5b3f7a` → `#f2a65a` | low orange, long shadows | `rgba(60,20,40,.22)` | turning points, danger coming |
| Night | `#0f1a33` → `#2b3d63` | cold blue moon + warm firelight pools | `rgba(0,0,20,.35)` | secrets, plots, fear |
| Storm | `#3a3f4a` → `#6b7380` | flat grey + white lightning flashes | `rgba(0,0,0,.25)` | chaos, divine anger, battles |
| Interior lamp | warm dark walls | one warm pool of light on the focal point | `rgba(40,20,5,.35)` | councils, conspiracies, letters |

- **Aerial haze:** far layers lose contrast and drift toward the sky colour (mix 30–60 %).
- **Rim light:** heroes in dusk/night/interior get a thin light edge on the side facing the light source.
- **Cast shadows:** every standing figure has a soft contact shadow; long shadows at dawn and dusk.
- **Glow:** light sources (sun, fire, lamps, lightning, divine aura) get a soft radial glow.

## 4. Detail density — rich, never empty (owner "rich scenes" rule)

- The **8 × 6 detail map** of `tc still` may show an empty tile only where calm is intended (open sky, calm sea) and declared with `--calm`.
- Every wide shot has **≥ 3 background story moments**: people working, animals, smoke, banners moving, boats, birds, a child running.
- Texture on materials: rock strata and cracks, wood planks and grain, stone blocks, cloth folds, water marks.
- **Crowds have variety:** no two identical figures side by side (vary colour, pose, height, headgear, facing).
- Motion is not detail: rich = layered, detailed sets; **not** movement everywhere.

## 5. Era lock (rules r4, r32)

- Every video has `jobs/<id>/era.json`: every clothing, armour, weapon, hair, building, furniture, ship, tool, plant, animal and landscape item, **each with a source** (museum piece, excavation, period art), plus a don't-list of common anachronisms.
- Every shot in the plan lists the era items it shows; `tc era` checks them; the still checklist has an era item.
- Myths are drawn in the era that told them (Greek gods in Archaic/Classical Greek dress, temples and objects).
- Real people (r6): costume, setting and name card — never an exact face copy.

## 6. Acting

- Six base expressions (neutral, stern, worried, shocked, sly, grief); faces change on the emotional word.
- Gestures match the line and **land on the word that names them** (r28–r30): anticipation first, then the key pose, then follow-through (r29).
- Nobody freezes: breathing, blinking (every 3–5 s), small weight shifts.
- Listeners react to speakers (turn heads, flinch, nod).
- Mouths move only for characters speaking their own dialogue lines (lip sync from Rhubarb cues).

## 7. Text on screen (rule r3)

- Only **place/date cards** and **map labels**. No captions, subtitles or speech bubbles.
- Card style: parchment `#f4e6c6`, outline `#2a1c13` 4 units, Cinzel bold, fades in over ~1 s. Use `card()` from the kit.
- Text must fit inside its box (checked) and stay in the 3 % safe area.

## 8. Thumbnails (rule r21)

- 1280 × 720, drawn fresh for every video in this style.
- The video's main character(s) **large**, with a **strong emotion** (shock, fury, fear, triumph).
- **One striking object** (the thunderbolt, the poisoned cup, the secret letter, the warship).
- Rich topic background, high contrast between subject and background.
- **≤ 3 big words** (or none). Readable when downscaled to 160 px wide.
- Must promise only what the video delivers.

## 9. Reference ruler

- Reference frames (the Japan video, Epic History maps) are a **quality ruler only**, never copied (r9).
- They live in git-ignored `reference/` (other creators' work never goes in the public repo).
- In the still review, look at our still next to the closest-mood reference strip and ask: "is ours clearly better?"

## 10. The still checklist (`tc qa <job> still <answers.json> --subject <shot>`)

Every item must pass, and the total must be ≥ 90/100. Weights match `tc/qa.py`.

| Item | Weight | Passes when |
|---|---|---|
| matches_line | 12 | The picture shows exactly what the words say at that moment |
| composition | 10 | Focal point on thirds, foreground framing, no tangents, safe areas |
| focal_clarity | 8 | You know where to look within half a second |
| depth_layers | 8 | ≥ 5 layers, haze on far layers |
| light_atmosphere | 10 | The time-of-day grade, glow, rim light and shadows of section 3 |
| detail_density | 10 | No unintended empty areas; ≥ 3 background story moments in wides |
| acting | 10 | Expressions and poses fit the line; listeners react |
| era_accuracy | 10 | Every item on the era sheet; nothing from the don't-list |
| character_match | 8 | Named characters match their sheets exactly |
| grip_and_contact | 6 | Hands wrap props; feet on the ground; shadows under figures |
| beats_reference | 8 | Side by side, it is clearly better than the reference frame |

## 11. How we beat the reference (measured 2026-11-21)

| | Reference | Timeless Compass |
|---|---|---|
| Picture change | new illustration every ~5.5 s, mostly fades | something story-related changes every 1–3 s (r30) |
| Acting | frozen poses, small face flickers | acting on the word, natural motion (r28–r29) |
| Light | flat, even | lighting plan per scene (section 3) |
| Camera | slow drift | push, pull, pan, track, crane, rack focus, parallax depth (r34) |
| Sound | narration + music | character voices, cinematic sound design, music only at peaks (r26) |

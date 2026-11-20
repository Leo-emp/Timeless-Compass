# Map Style — Timeless Compass

Owner rule r14 (2026-11-20): our maps copy the **look and the way of showing maps** in the Epic History TV
"First Crusade" video (owner file `Downloads/videoplayback (10).mp4`). Frames: `reference/maps/`.
We copy the *ideas*, never their art: every pixel is drawn by our own code (no AI images, no stock).

## 1. The look (what makes it premium)

| Part | What they do | Ref frame |
|---|---|---|
| Paper | Aged parchment, cream-to-tan, **crumpled/creased** with soft real shadows in the folds; dark vignette at edges | 01 |
| Sea | Muted teal-grey, with fine **engraved wave lines** (hand-hatched ripples), darker near coasts | 01, 02 |
| Land | Tan paper with hand-drawn stamps: tiny **trees** (forests), **mountain ridges**, dotted deserts, hatched hills | 01, 05 |
| Decor | Small illustrated figures, ships, beasts standing on the map (period woodcut style) | 01 |
| Territories | Flat colour fill (crimson, purple, teal, green) that **keeps the paper texture** + a repeated **emblem pattern** (crosses, stars) in rings across the area; soft glowing edge | 02, 07 |
| Region names | Big carved serif caps, white/cream with dark outline, **slightly curved** along the land | 02 |
| City labels | Small parchment scroll tags with a tiny city icon (towers) above; serif lower-case | 02, 04 |
| Leader labels | Same scroll tag with a small crown | 02 |
| Date tag | Torn paper strip top-right: "c.1097 AD" | 07 |
| Portrait cards | Framed parchment cards with an illustrated figure + name, slide in on the sides | 07 |

## 2. Camera (the biggest reason it feels cinematic)

- The map is a **3D object**: camera is **low and tilted (~35–55°)**, never flat top-down.
- **Always moving slowly**: drift/orbit + gentle push-in; the 8-frame strip (06) shows ~8 s of steady glide.
- Depth of field: far edge of the map softly blurred.
- Reveals: camera pushes from a wide region view down to the city or battlefield.
- **Spotlight**: rest of map darkens to near black, a pool of warm light on the place being talked about (04).

## 3. How things move (animation grammar)

- **Territory grows**: colour spreads over the land like ink soaking in, emblems fade in after.
- **Arrows**: thick red curved arrows draw themselves along the route (head last), with a soft shadow (02).
- **Pulse rings**: concentric glowing rings expand out from a city = "news/call spreads from here" (03).
- **Battle marker**: crossed swords + fire burst pop on the place (04); a flash/explosion on conquest (07).
- **Army banners**: tall standing banner (side's emblem on white cloth) planted on the map, sways gently.
- **Battle maps** (zoomed tactical, 05/06): new close-up map of the field — river, roads, walled town drawn as
  thousands of tiny houses, contour-line hills, compass rose — with **3D extruded unit blocks** in side colour
  (red vs teal), each with a banner; blocks slide, turn, charge; burning = fire sprites on the blocks.
- **Cut away and back**: map shots alternate with illustrated scenes every 5–20 s, never 1 minute of map.

## 4. Our build (Blender, all procedural/own data)

| Need | How |
|---|---|
| Coastlines, rivers | Natural Earth (public domain) shapefiles → era-adjusted polygons per video |
| Borders per era | Own polygon JSON per job (`jobs/<id>/map/*.json`) from research |
| Paper | Plane with crumple displacement + procedural parchment shader + baked stain/age textures |
| Stamps | Small vector library: tree, mountain, hill, dune, wave, house — scattered by land type |
| Emblems | `tc/emblems.py` (already exists) → territory pattern rings |
| Labels | Text curves in brand serif + scroll-tag mesh |
| Units/banners | Extruded blocks + cloth banner reusing our cloth sim |
| Decor figures | Our own 3D cast rendered as flat ink/woodcut silhouettes |

New workstream: **WS19 Maps** in `docs/BACKLOG.md`. Shot list already allows `card: map_label`;
add a shot kind `map` with `map_action` (grow, arrow, pulse, battle, spotlight, units).

## 5. How to use it (built 2026-11-20, Session M)

1. Write a map spec: world/region map = `library/maps/specs/test_crusade_1097.json` (lon/lat), battle map =
   `library/maps/specs/test_antioch_1098.json` (`"kind": "battle"`, km). Per video they live in `jobs/<id>/maps/`.
   Format notes are at the top of `tc/maps/build.py` and `tc/maps/battle.py`.
2. `python -m tc map check <spec>` then `python -m tc map paint <spec> --out <dir> [--width 6144] [--preview]`
   (`preview.png` = flat 2D check with labels; ~13 min at 4096 px on the laptop — run big ones on the cloud).
3. In `shots.json` a map shot carries `"map": {"spec": "maps/x.json", "beats": [...], "target": [lon, lat]}`
   (who may be empty). Beats: show, hide, grow, shrink, arrow, pulse, battle, spotlight, date, move
   (`"along": "<arrow id>"` marches an army along a route).
4. Blender: `blender -b --python blender/scenes/map_test.py -- <pack> <out> <frame|a-b> EEVEE 32 <seconds> <tilt> <dist> <u,v>`
   (`blender/lib/maps.py` builds the crumpled sheet, camera drift, light, labels, arrows, rings, swords, armies).

| Module | Draws |
|---|---|
| `tc/maps/base.py` | parchment, engraved sea, golden coast, rivers, lakes |
| `tc/maps/stamps.py` | trees, mountain chains, tufts, dunes, ships (cog/galley) |
| `tc/maps/territory.py` | realm fills + emblem medallions + grow maps (one owner per pixel) |
| `tc/maps/labels.py` | region/sea names, scroll tags + town/crown icons, date strip, banners |
| `tc/maps/battle.py` | battle field: sand, river, roads, walled town of tiny houses, contour hills, compass |

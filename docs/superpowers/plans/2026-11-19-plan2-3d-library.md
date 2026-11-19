# Timeless Compass: Plan 2 (3D Library) — status record + remaining tasks

**Spec:** `docs/superpowers/specs/2026-11-19-cinematic-agent-design.md` (sections 6.4, 6.5, 7 M2)
**Owner directive (2026-11-19 03:28):** "build the 3D library kit to the highest quality … as close to the video"
(reference: Heroes of Bronze, used only as a quality ruler — rule r9: never copy).
This plan was written after the first build night as a record (the owner asked for the library to be built
directly). Code lives in `blender/lib/`, manifests in `library/`, test renders in `spike/lib_stills/`.

## Built (night of 2026-11-19)

| # | Piece | Files | Self-rating (shape/surface/era) |
|---|---|---|---|
| 1 | Character builder: MakeHuman body, tan, skin pores, strand hair + beard with clumping | `cast.py`, `library/cast/themistocles.json` | 6 / 6 / 7 |
| 2 | Pose library + keyframing | `pose.py` | — |
| 3 | Cloth wardrobe: chiton, himation, long robe, border bands, layer freezing | `wardrobe.py`, `library/wardrobe/greek_civilian_480bc.json` | 7 / 6 / 8 |
| 4 | Hoplite kit: Corinthian helmet + crest, cuirass, pteruges, greaves, aspis, dory | `armour.py`, `library/wardrobe/greek_hoplite_480bc.json` | 6 / 7 / 8 |
| 5 | Persian king v1: robe, mantle, crown, long beard | `armour.persian_crown`, `library/wardrobe/persian_king_480bc.json` | 4 / 5 / 5 (weak) |
| 6 | Salamis strait at dusk set | `sets.py`, `library/sets/salamis_strait_dusk.json` | 6 / 6 / 7 |
| 7 | Athenian trireme | `props.py`, `library/props/trireme_athenian.json` | 6 / 5 / 8 |
| 8 | Integration shot + 5 s animation | `scenes/hero_salamis.py` (`ANIM=1`) | — |

Measured quality vs reference (side-by-side `spike/review/compare_ref_vs_ours.jpg`): **~50–55% overall**.
Biggest gaps: skin realism in close-up, lighting richness (bounce, haze shafts), environment detail (vegetation,
buildings, crowds), garment variety.

## Remaining tasks (in priority order, each ends with owner-reviewed stills)

1. **Rig the clothing/armour for animation** — transfer skin weights from the body to frozen garments and armour
   (Data Transfer + Armature modifier) so they follow the skeleton; re-simulate cloth per shot only where the body
   moves a lot. Test: walk cycle with chiton + himation, no clipping.
2. **Motion capture** — CMU BVH (free) retargeted to MPFB's `cmu_mb` rig: walk, run, row, kneel, bow, sit, point,
   spear thrust, shield push, fall, talk gestures. Foot locking + hand contacts.
3. **Face performance** — expressions (anger, fear, grief, resolve) on the face bones; blinks; eye look-at.
4. **Skin v2** — higher-res skin detail, subsurface tuning, wet eyes (cornea specular), darker eye holes in helmets.
5. **Xerxes v2** — Achaemenid court dress (pleated wide-sleeved candys + trousers), squared curled beard, proper
   crown with rosettes; throne on Mount Aigaleos; parasol bearer.
6. **Crowds** — instanced soldier variants (randomised faces, kit colours, shield emblems) for phalanx / fleet shots.
7. **Sets v2** — Athens + Acropolis (temple kit: columns, entablature, pediment), Thermopylae pass, Persian camp,
   vegetation scattering (olive, pine, maquis), particles (dust, embers, sea spray).
8. **Rowing animation** — trireme oars in stroke, rowers visible through the outrigger, wake.
9. **Shot assembler** — `tc` reads `shots.timed.json` + `needs.json`, picks library assets, builds a Blender scene
   per shot (cast + wardrobe + set + pose/motion + camera move), renders stills for the contact-sheet gate.
10. **Library storage** — `.blend` caches of built assets uploaded to R2 (≤ 6 GB budget), manifests stay in git.

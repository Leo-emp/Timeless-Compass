# Render speed — 2D film engine (measured 2026-11-21, plan 1 task 9)

Test video: `FleetTestLong` (the fleet motion test drawn for 21,600 frames = 15 min at 24 fps, 1920×1080):
a full trireme with 11 crew, 25 oars, 5 far ships, ~200 wave marks, gulls, parallax camera. Real scenes will
be heavier (more characters, richer sets), so treat these as best-case numbers and re-measure on the first Short.

| Run | Farms | Parts | Frames | Render per part | Wall-clock (render) | Whole run incl. setup |
|---|---|---|---|---|---|---|
| Laptop smoke | laptop, 2 tabs | 1 | 48 | 15 s incl. bundling | — | — |
| GitHub 8 s | GitHub | 4 | 192 | ~12 s | 15 s | ~3 min |
| Kaggle 8 s | Kaggle (4 CPU) | 2 | 192 | ~26 s | 52 s (3.7 frames/s) | ~6 min |
| **GitHub 15 min** | **GitHub** | **20** | **21,600** | **~103 s (~10.5 frames/s per runner)** | **134 s** | **~2.5 min** |
| Combined 15 min | GitHub 20 + Kaggle 4 | 24 | 21,600 | GitHub ~100 s, Kaggle ~3 min per part | 754 s (Kaggle is the bottleneck) | ~13 min |

All joins were exact: 192/192 and 21,600/21,600 frames, no jump at the GitHub/Kaggle seam (frame 18,000).

## Defaults (from these numbers)

- **Long video (12–15 min):** GitHub only, 20 parts. Expect ~3–10 min wall-clock with real scenes.
- **Short (2–3 min):** GitHub, 6 parts.
- **Kaggle:** backup farm (when GitHub is busy or failing) or a small share — one Kaggle CPU session renders
  ~3.7 frames/s, about a third of one GitHub runner, so giving it 4 of 24 parts made the whole render 5× slower.
- Kaggle weekly quota used today: ~45 min of CPU sessions (CPU notebooks don't use the 30 h GPU quota).

## Lessons

- Never load fonts at render time: two cloud renders stalled waiting for a font in a fresh browser tab.
  Text is drawn as vector shapes from the bundled font (`film/src/kit/text.ts`).
- Kaggle clones the repo into `/tmp` so the kernel output holds only the parts (otherwise downloading the output pulls the whole repo).

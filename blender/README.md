# Timeless Compass 3D library (Blender, code-built)

Everything here runs **inside Blender 5.3** (portable copy at `C:\Users\User\tools\blender-5.3.0-windows-x64\`)
with the free **MPFB / MakeHuman** extension (CC0 humans). No AI images, no stock footage, no paid assets.

```
blender -b --python blender/scenes/<scene>.py -- <out.png> [samples] [shot]
```

## Library modules (`blender/lib/`)

| Module | What it builds | Method |
|---|---|---|
| `common.py` | materials (PBR, aged bronze with patina, fabric with weave + sheen, strand hair, dyed horsehair), lights, camera, physical sky, render settings | Cycles, AgX colour |
| `cast.py` | **characters**: MakeHuman body + face + skeleton (163 bones incl. face), sun-tan, skin pores, **real strand hair and beards** (Blender hair curves: lie along the skin, curl, clump into locks), beard region from MakeHuman's own face regions | `build_human(spec)`, `scalp_hair()`, `beard()` |
| `pose.py` | named poses from bone directions (`stand_relaxed`, `hoplite_ready`, `hand_over`, `receive`), fist curls, keyframing | `apply_pose()`, `blend_into_pose()` |
| `wardrobe.py` | **cloth-simulated clothing**: chiton (pinned shoulders + belt), himation (over the left shoulder), long robe; garments are frozen and become colliders so layers drape over each other; woven border bands | `chiton()`, `himation()`, `freeze()`, `simulate()` |
| `armour.py` | **hoplite kit**: Corinthian helmet (smoothed-head fit, nose guard, brow arches, almond eyes, mouth slot, strand horsehair crest), muscle cuirass, pteruges, greaves, aspis with painted emblem, dory; **Persian crown** | clean primitives shrink-fitted to a smoothed body proxy |
| `sets.py` | **Salamis strait at dusk**: Ocean-modifier waves + far sea, real-scale hills (Salamis, Aigaleos, Attic coast) with scrub/rock material, weathered stone harbour wall, rowboat, lantern, burning-Athens glow, Persian fleet lights, haze | `salamis_dusk()` |
| `motion.py` | **motion capture**: free CMU BVH clips (walk 16_15, …) retargeted onto MPFB's `cmu_mb` rig in world space (works whatever the rest pose / bone rolls), hip travel scaled to leg length, calibration T-pose skipped automatically, cloth pre-roll blend | `swap_to_mocap_rig()`, `apply_bvh()` |
| `props.py` | **Athenian trireme**: lofted hull, ram, outriggers, deck, aphlaston, bow eyes, 170 oars in 3 banks, mast + furled yard | `trireme(loc, heading)` |

## Asset manifests (`library/`)

Every asset has a JSON manifest: era, design source (historical, never copied from other productions — owner rule r9),
licence, version, self-rating, owner rating (filled when the owner reviews), renders. Big files will live in R2.

## Test scenes (`blender/scenes/`)

| Scene | Shows |
|---|---|
| `portrait_test.py` | face + strand hair + beard close-up |
| `dressed_test.py` | Themistocles in chiton + himation (`full` / `med`) |
| `hoplite_test.py` | full hoplite kit (`med` / `head` / `full`) |
| `xerxes_test.py` | Persian king: long robe, mantle, crown, long beard |
| `salamis_set_test.py` | establishing shot of the strait |
| `trireme_test.py` | three triremes on the strait |
| `mocap_walk_test.py` | Themistocles walking with real motion capture, chiton + himation following, camera tracking |
| `hero_salamis.py` | **integration**: Themistocles hands the sealed message to Sicinnus on the harbour wall; `ANIM=1` renders a 5 s animated shot (camera push-in, moving sea, servant's bow) |

## Lessons learned (keep these)

- MakeHuman's body shape lives in **shape keys**: read rest coordinates with the keys mixed in.
- MakeHuman **purges unused materials** while loading: create materials with `use_fake_user = True`.
- Skin is a shared node group: tint/detail the colour going **into the BSDF**, not the raw texture.
- Never grow armour from the body surface itself (it copies the nose and brows): fit clean shapes onto a **smoothed proxy**.
- Hair strands must start **along the skin** (projected flow + small lift) and **clump** — straight-out strands look like fur.
- Cloth layers: simulate the inner garment, **freeze** it into a collider, then drape the outer one starting above it.
- Scale terrain in **vertex coordinates**, not object scale (object scale multiplies the displacement too).
- Cameras: set `clip_end` to kilometres; the default 100 m hides distant mountains.
- At dusk a low sun hides behind real-scale mountains: golden **side light** (~12°) reads best for faces.
- Laptop (CPU) Cycles: stills 1–4 min, animation ~30 s/frame at 1280×544 — long renders go to the cloud (Plan 3).
- CMU BVH files are **Y-up**: import with `axis_forward='-Z', axis_up='Y'` (with Z-up the skeleton lies on its side and the hips fly off).
- Retarget in **world space** with a rest-direction alignment: CMU actors start from a T-pose, MPFB rigs rest differently; copying local angles bends limbs wrong.
- MPFB adds eyes/brows/lashes/teeth as plain children of the body if they are added before the rig: **pin them to the head bone** or they stay behind when the head moves.
- Cloth with mocap: bake the cloth from frame 1 (`ptcache.bake_all`), then render only the frames after the pre-roll.

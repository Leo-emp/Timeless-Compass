# Timeless Compass — Visual Standard (owner brief, 2026-11-20)

Every session and every agent stage follows this. It merges the owner's **face standard** and the **studio brief**
(both 2026-11-20), adapted to how we work: **every frame is RENDERED 3D** (Blender + MakeHuman), never AI-generated
images (project rule). So "image prompt" below means our **shot spec** (`tc assemble` recipe), and character
consistency is guaranteed by the saved character in `library/cast/<id>.json`, not by prompts.

## Goal
Semi-realistic cinematic 3D storytelling, like a premium animated feature film: realistic anatomy, restrained
stylisation, natural skin, expressive but subtle faces, detailed clothes and sets, film lighting, atmospheric frames.
**Never:** plastic or waxy skin, doll / toy / action-figure / mobile-game look, oversized eyes, exaggerated
proportions, fake smiles, flat lighting, generic "pretty" symmetric faces, over-smooth surfaces.
Facial realism, believable skin and natural proportions come BEFORE extra decorative detail.

## 1. Face anatomy  (code: `cast.build_human`, `cast.sculpt`, `cast.asymmetry`)
- Real skull + face structure; natural eyes / nose / lips / ears; cheekbones + jaw defined (`face` sculpt per character)
- **Subtle asymmetry on every face** — `cast.asymmetry(seed)` drifts eye height, lid fold, eye bags, cheekbone,
  cheek volume on ONE side (MakeHuman l-/r- targets, below deformity level). Never a mirror-perfect face.
- Realistic eyelids + sockets; expressions from muscles (MPFB expression units), never cartoon

## 2. Skin  (code: `cast.skin_detail`, `cast.skin_v2`, `cast.age_face`)
- Pores + fine texture (deeper in the T-zone), natural tone variation (cm-scale mottling), blood redness on nose /
  cheeks / ears / lips, stubble shadow, age lines by age
- Subsurface: Random Walk skin, **~4.5 mm** depth (deeper = wax). Thin oil layer only (coat 0.03)
- Matte-to-natural: roughness 0.42–0.66, a little shinier in the T-zone, never glossy all over
- Not too orange / saturated: check skin under neutral light on the cast card

## 3. Eyes  (code: `cast.face_materials`)
- Iris detail visible, realistic pupil, clear cornea that reflects, **wet lower lid + inner corner** (tear film band)
- Catchlights from the big soft key; gaze aimed at a real target (`talk.listen`, `life` saccades)
- Emotion through small muscle movement, not big shapes

## 4. Per-shot performance spec  (shot plan, filled by the agent for EVERY shot with a person)
`emotion`, `intensity` 1–5 (default subtle 1–2), `brows`, `gaze` (target), `lids` (tension), `mouth`, `lips`,
`jaw`, `head`, plus body: `posture`, `orientation`, `hands`, `gesture`, `weight`, `interaction`.
No two consecutive shots of the same character in the same standing pose.

## 5. Characters  (registry = `library/cast/*.json`, permanent ids)
Before a script is shot, every character gets: identity (age, sex, face structure, skin, eye shape/colour, nose,
lips, jaw, hair, body, distinguishing marks), personality (traits, typical expressions, posture, mannerisms) and
wardrobe (garments, fabrics, colours, accessories, footwear) — all from sources for real people.
Not unnecessarily attractive or symmetric. Identity never changes between shots unless the story says so.

## 6. Clothes  (code: `wardrobe.py`, `costume.py`)
Era-, rank-, job-, weather-correct; scanned real fabrics (linen matte + wrinkles, wool fibrous, leather grain with
controlled highlights, silk drape + soft sheen); believable construction, fit, thickness, folds. Continuity across
connected scenes. **No gaps showing bare skin where the garment should close.**

## 7. Lighting  (code: `lighting.film_lights`, cast card)
Large soft key (2–3 m panel), gentle fill (~1/4, slightly cool), subtle rim, natural falloff, controlled skin
highlights, global illumination, soft shadows; colour grade by mood (`tc look`, `tc finish`).

## 8. Camera
Close-ups for emotion, mediums for interaction, wides for place. Lens, angle, depth of field and subject placement
chosen per shot; **never the same composition twice in a row**. Every shot must say something about the story —
don't illustrate every sentence literally.

## 9. Quality gate (before a still is accepted — rule r13: no full renders until stills pass)
- FACE: natural? eyes believable? skin organic, not plastic or waxy? proportions = the character's?
- CLOTHES: real material? natural folds? outfit consistent? no open gaps / clipping?
- ANATOMY: hands + fingers right? proportions? pose physically possible? feet on the ground?
- CINEMA: light coherent? composition strong? supports the story?
If it fails: name the exact defect, fix the code or the shot, render again. Never accept an obviously defective frame.

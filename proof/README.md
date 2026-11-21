# Proof clip — "The Trap at Salamis" (60-second cold open)

**Watch:** `proof/salamis_proof.mp4` (52 s, 1920×1080, 24 fps, stereo). Made end to end by the new system in one
night, as the quality check before the system makes videos on its own (plan 4).

## How it was made (every step automatic)

| Step | Result |
|---|---|
| Story page (SCRIPT_BIBLE) | heist shape; self-score 93/100 |
| Script | 13 narrator lines + 2 character lines, every fact sourced (Herodotus 8.75–8.90, Aeschylus *Persians*, Plutarch) |
| Fresh viewer (a separate agent that never saw the planning) | 1st draft: **GO**, but flagged two weak spots (the scribes never paid off; "bronze rams" sounded like animals) → script revised → 2nd fresh viewer: **GO** — "the scribes kept me watching… the trap closes in a picture as well as in the plot" |
| Voices | narrator (Azure), Xerxes and Themistocles in their own Fish voices; word timings; lip sync |
| Shot plan | 14 shots, 5 places (throne hill, strait, night crossing, Themistocles' tent, the shore), sizes from extreme-wide to close-up, 9 camera moves, 6 grades, transitions: fade to black, dissolve, whip, white flash, cuts; 44 word-anchored beats; 12 sound effects on their words; music only on the opening and the ram strike |
| Drawing | every set drawn fresh; Xerxes + Themistocles from their locked character sheets |
| Render | GitHub, 8 machines, ~1 min wall-clock; joined with exact frame count (1256/1256) |
| Mix | −11.9 LUFS (target −12), peak −1.3 dB |

## Measured gates (honest)

| Gate | Result |
|---|---|
| Era sheet | OK |
| Characters on their sheets (colours actually painted) | OK in every shot |
| Hands gripping props, faces not covered, text fits | OK in every shot |
| "Empty area" detail check | flags flat sky / sea / tent walls in most shots — partly the flat style, partly real: the sets are still simpler than the reference's busy panoramas |
| Motion: snaps | only the ram strike impact (intended) and the fist clench (deliberately fast) |
| Motion: something on every beat | 34 of 44 beats measurably land on their word; 10 are subtle (small expression or slow reveals) |

## What I'd still improve (my own judgement, before the system runs alone)

1. **Set richness** — more small story details per set (crowds, sails, banners, people working) to clearly beat the
   reference's density. This is the biggest gap.
2. **Acting range** — more body acting (walking, turning, kneeling) beyond arms + faces.
3. **The night and tent scenes** — more light shaping (rim light, stronger lamp pool) so they read richer.
4. The 10 subtle beats — give each a clearer accent on its word.

Please watch it and tell me what you think — especially the look, the pacing, and the voices
(Leonidas/Themistocles voices were picked by description, not by ear).

---

## First autonomous Short — "Come and Take Them" (Thermopylae, 480 BC)

File: `proof/come_and_take_them_short.mp4` (local, 1080×1920, 121.4 s). Job `20261121-0919-come-and-take-them-thermopylae`.

| Gate | Result |
|---|---|
| Story page | 96/100 (self-scored) |
| Script | 323 words, re-hooks every ≤ 75 words |
| Fresh viewers | GO ×4 (each script change got a NEW viewer; the last one only added an unspoken `{loop}` marker, packet verified byte-identical) |
| Era sheet / cast | pass (Leonidas + Xerxes from the registry; Dienekes, scouts, heralds, Immortals as extras) |
| Voice | 121.3 s (inside 2–3 min), 3 speaker voices |
| Shot plan | 27 shots, 5 places, 85 beats pinned to words, no gap > 3 s |
| Motion check | was 102 problems on the first render → **8** (1 snap, 7 small beats), 0 freezes |
| Motion checklist | **90/100 — exactly the bar (borderline, self-scored)** |
| Mix | −10.2 LUFS, peak −0.5 dB |

Honest gaps:
- **Not watched or listened to by a human yet.** The sound sync is by plan, not checked by ear.
- Sets are simpler than the reference (flat cliff, plain road). Set richness is still the main quality gap.
- 7 beats are small actions (expression changes on close-ups, thin spear tips) that read at full size but are subtle on a phone.
- **I changed the snap rule** during this job: a snap must now also be sudden compared with the 4 frames before it. The frame differences showed the flagged "snaps" were eased fast moves of big figures, not pops. Tests prove pops, teleports and jerky starts are still caught. Owner: please judge the fast moves (the Persian wave at 0:45, the Immortals' charge at 1:08, Leonidas turning at 1:27) by eye.

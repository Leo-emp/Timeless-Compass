# Timeless Compass — Script + Storytelling Standard (SCRIPT BIBLE)

Read before the topic, story, script and viewer stages. **Every video is a story, not a list of facts (r24).**
The goal is that a viewer who clicked the title cannot stop watching. Facts stay true and sourced (r4); the drama
comes from what really happened. Character dialogue may be dramatised within real history (r12).

---

## 1. Picking a topic for its story (r25)

For every candidate seed, write a **5-line story pitch** before scoring:

1. **Who** we follow (one person, not an empire) and what they want.
2. **What stands in the way** — the obstacle, enemy or impossible odds.
3. **The hard choice** at the centre.
4. **The twist** — the moment the viewer did not see coming.
5. **The best visual moments** (what will look amazing drawn) and where characters can speak.

Reject a topic when the pitch has no clear person, no real dilemma or no twist — even if demand is high.

## 2. The story page — `jobs/<id>/story.md` (checked by `tc story`)

Written **before any script line.** Required sections, in this order:

```
## Main character        who, why we care, what makes them human
## Other characters      rival / villain / ally / traitor / ensemble — each with what they want
## Want                  what the main character is trying to get
## Fear                  what they fear will happen or stand to lose
## Choice                the hard decision where every option costs something
## Central question      the question the title + thumbnail promise; answered only at the end
## Story shape           one of: mystery, rise_and_fall, countdown, heist, revenge, multi_character, tragedy, underdog
## Strongest real elements   the secrets, betrayals, ironies, sacrifices of the REAL story we must use
## Beat sheet            - <beat>: what happens   (long: cold_open, world, complication, midpoint, darkest, climax, twist, ending
                                                  Short: hook, build, twist, ending)
## Loops                 - plant: <question raised> -> payoff: <where it is answered>
## Emotional arc         what the viewer feels in each act
## Sound plan            Dialogue: <moments a character speaks>   Music: opening, <peaks>, ending
```

### Story toolkit (r33 — use every element the real story offers)

| Element | What it does | Example |
|---|---|---|
| More characters | conflict between wants | Themistocles vs. the Corinthian admiral Adeimantus |
| Secrets | the viewer knows what others don't | the message Sicinnus carries to Xerxes |
| Betrayal | a turn nobody trusts | Ephialtes shows the Persians the mountain path |
| Ticking clock | pressure | "by dawn the Greek fleet will be gone" |
| Mystery | clues revealed one by one | what the Manhattan Project scientists really knew |
| Irony | the outcome reverses the intent | Zeus overthrows his father — then fears his own children |
| Sacrifice | stakes made human | the 300 staying behind |
| Transformation | change over the story | a hero becomes a tyrant |
| Moral dilemma | no right answer | save the city or the people in it |
| Consequence + legacy | why it still matters | how one night decided the West |

### Story shapes by topic type

| Topic | Shape |
|---|---|
| Secret government projects | **mystery** — investigation, clues, revelation |
| Empires, rulers, dynasties | **rise_and_fall** |
| Battles, sieges, escapes | **countdown** |
| Plots, thefts, deceptions | **heist** |
| Feuds, wronged heroes | **revenge** |
| Big events with many players | **multi_character** (cross-cut between sides) |
| Doomed heroes | **tragedy** |
| Small side vs. giant | **underdog** |

## 3. Hooks (the first 30 s decide retention)

- **Open on the most dramatic moment**, then rewind: "By sunset, two hundred ships would be burning…"
- **Confirm the title within 5 s** — the viewer clicked for a promise; show it is coming.
- **Plant one burning question** in the first 10 s.
- **Stakes in human terms:** a person's fear, not "the empire".
- **No intro, no "welcome back", no logo, no channel talk.**

Hook types: *in medias res* (start in the action) · *the impossible fact* ("one man fooled a thousand ships") ·
*the dramatic irony* ("he thought he had won") · *the question* ("why would a king build a fake army?") ·
*the countdown* ("they had six hours").

## 4. Build-up and retention

- **Open loops:** raise questions and pay them off later; every loop on the story page has its payoff.
- **Re-hook** before each section ends: long ≤ every 90 s, Short ≤ every 30 s (`{loop}` marker, checked).
- **"But" and "therefore", never "and then":** every beat changes the situation (cause and effect).
- **Rising stakes:** each act makes things worse; the darkest moment just before the climax.
- **Midpoint turn:** something reverses the direction of the story.
- **Dramatic irony and foreshadowing:** plant small details early that pay off later.
- **Best scene in the last third.**

## 5. Line craft (written for the ear and for drawing)

- ≤ 30 words per line, one idea each; vary rhythm: long, long, short punch.
- **Concrete pictures:** "the sea turned red" beats "heavy losses". Every line must be drawable — it becomes a shot.
- Active verbs on the action words: the animation lands on them (r28–r30).
- `{beat}` = a held silence before a reveal.
- Narrator facts carry `[src: id]`; character lines carry `[dramatised]` or `[source: …]` (r12).
- Serious, mysterious, never cheesy or clickbait (r2). No disclaimers.

## 6. Character dialogue (r1, r12, r26)

- Characters speak at **peak moments**: threats, decisions, confessions, last words, the twist.
- Each named character always uses their **one saved Fish voice**.
- A dramatised line must fit the real person, situation and character — never change what happened.
- Short and sharp: 4–15 words usually hit hardest. The narrator carries the facts.
- Format: `XERXES: "Burn their city. Let them watch it from their ships." [dramatised]`

## 7. Endings

- The final reveal answers the central question.
- Then **one line that sticks** (irony, consequence, the human cost).
- Then a natural pointer to a related video (watch hours) — never a cheesy subscribe ask.

## 8. Shorts (2 to under 3 min, 300–420 words)

- Hook in the **first 2 seconds**, title promise in the first 5.
- **One story, one twist**, no slow world-building.
- Re-hook every ≤ 30 s.
- The last line loops back to the first, so a replay feels seamless.
- Made from scratch: own topic, story page, script, scenes and thumbnail — never cut from a long video.

## 9. Worked example — story page (Salamis, long)

```
## Main character
Themistocles of Athens — a self-made politician everyone distrusts; clever, ambitious, out of time.

## Other characters
Xerxes (wants Greece's surrender, watching from a golden throne) · Eurybiades of Sparta (commands the fleet, wants
to retreat to the Isthmus) · Adeimantus of Corinth (mocks Themistocles: "a man without a city") · Sicinnus (the
slave who carries the secret message) · Aristides (Themistocles' old enemy, who brings the news that saves him) ·
Artemisia (the queen who warned Xerxes not to fight at sea).

## Want
Fight the Persian fleet inside the narrow strait, where numbers stop mattering.

## Fear
The allies sail away in the night and Athens' people, crowded on Salamis, are left to be slaughtered.

## Choice
Secretly tell the enemy where to find the Greeks — betraying his allies to trap them into fighting.

## Central question
How did one man trick the largest navy on Earth into sailing into a trap?

## Story shape
heist

## Strongest real elements
Athens already burned and abandoned · the secret message by a slave · Xerxes on his throne with scribes · Aristides
the exiled rival rowing through the blockade at night · Artemisia ramming her own ally to escape · Xerxes' "my men
have become women, my women men".

## Beat sheet
- cold_open: dawn, Xerxes settles on his throne above the strait, scribes ready to record his victory
- world: Athens is ash; the Greeks are trapped on Salamis and the allies want to leave
- complication: the council votes to retreat; Adeimantus humiliates Themistocles
- midpoint: Themistocles sends Sicinnus to Xerxes with a secret message
- darkest: if Xerxes doesn't believe it, the Greeks scatter and Athens is finished
- climax: the Persian ships jam in the narrows; the Greek rams strike
- twist: Artemisia rams a Persian ally — and Xerxes, fooled, praises her
- ending: the king walks away; the man everyone distrusted saved the West

## Loops
- plant: what was in the secret message? -> payoff: midpoint reveal
- plant: why are the scribes there? -> payoff: they record his defeat
- plant: who is rowing through the blockade at night? -> payoff: Aristides, his old enemy

## Emotional arc
curiosity → dread (Athens burns) → frustration (the council) → tension (the message) → shock (the trap) → awe (the victory) → irony (Xerxes' words)

## Sound plan
Dialogue: Adeimantus' insult, Themistocles to Sicinnus, Xerxes on the throne, Artemisia, Xerxes' last line
Music: opening, the message sent, the rams strike, ending
```

## 10. The story checklist (`tc qa <job> story <answers.json>`)

Every item must pass and the total must be ≥ 90/100 before the script is written in full and sent to the viewer.
Weights match `tc/qa.py`.

| Item | Weight | Passes when |
|---|---|---|
| hook_strength | 12 | The first 10 s would stop a scroller |
| title_promise | 10 | The video delivers exactly what the title + thumbnail promise |
| central_question | 8 | One clear question, answered only at the end |
| character_want_fear_choice | 10 | We follow a person with a want, a fear and a hard choice |
| rising_stakes | 8 | Every act makes it worse |
| cause_and_effect | 8 | "But / therefore" links, no "and then" lists |
| loops_paid_off | 8 | Every planted question is answered |
| rehook_spacing | 6 | Re-hooks within the limits (90 s long, 30 s Short) |
| twist | 8 | A real turn the viewer did not see coming |
| emotional_arc | 8 | The planned feelings, act by act |
| best_scene_last_third | 4 | The strongest scene sits in the last third |
| strongest_real_elements | 6 | The real story's best secrets, betrayals and ironies are used |
| lines_drawable | 4 | Every line can become a clear picture |

## 11. The viewer review (r27)

After the script passes, a **fresh agent** that never saw this page or the writing reads only what a viewer hears
(`tc viewer <job> --packet`, `docs/VIEWER_BRIEF.md`) and returns GO or NO-GO. NO-GO notes go back to the writer.
Nothing is voiced or drawn before GO.

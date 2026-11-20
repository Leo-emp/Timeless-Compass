# Plan 3 — Character registry + voices Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (owner rule: no subagents for implementation). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Every named character has ONE locked identity — a sheet (look + colours + signature costume + design
source + one Fish voice), a drawing function in the film kit and a turnaround image — and every still and every
dialogue line is checked against it (rules r19, r26), with a `cast` stage that makes sure a video's characters exist
and pass before anything is drawn.

**Architecture:** `library/characters/<id>/sheet.json` (data) + `film/src/characters/<id>.ts` (drawing, pure
function of a `Pose`) + `library/characters/<id>/sheet.png` (turnaround rendered by `film/scripts/sheet.mjs`).
Character drawings tag their parts (`data-char`, `data-part`, `fill`), the inspector exports them, and
`tc/charcheck.py` compares every tagged part's colour with the sheet. Dialogue resolves a speaker's voice from the
registry.

**Tech Stack:** as plans 1–2 (Python + pytest, TypeScript kit + vitest, puppeteer-core inspector, Fish Audio free model).

**Spec:** `docs/superpowers/specs/2026-11-21-2d-autonomous-agent-design.md` — 6.2 (cast stage), 6.5 (registry), rules r6, r16, r19, r26, r32.

## Global Constraints

- One look and one voice per named character, forever (r19, r26); scenes around them are always new (r17).
- Real people: costume, setting and name card — never an exact face copy (r6). Design sources are period art and
  museum pieces (r9: never copy other productions).
- Only free Fish models (`s2.1-pro-free`); never voices cloned from real actors or game/anime characters (voices.json note).
- Inside one video no two characters share a voice.
- Commit with explicit paths; heavily commented code; trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Two characters in one video sharing a voice** → `test_cast_rejects_shared_voice` (Task 6).
2. **A character redrawn with a slightly different colour** (hand-typed hex in a scene) passes → `test_wrong_part_colour_is_caught` (Task 4).
3. **Speaker name spelled differently from the registry id** (`THEMISTOKLES`, `King Xerxes`) → aliases in the sheet; `test_alias_resolves_voice` (Task 5).
4. **Sheet references a voice key that is not in voices.json** → `test_sheet_with_unknown_voice` (Task 1).
5. **A drawing function that ignores the Pose** (same picture for every expression) → `test_every_expression_differs` (Task 2).

---

### Task 1: Sheet schema + registry — `tc characters`

**Files:** Create `tc/characters.py`, `library/characters/README.md`; Test `tests/test_characters.py`

**Interfaces:**
- Produces: sheet = `{"id", "name", "aliases": [str], "who", "kind": "real"|"myth"|"composite", "era", "design_source",
  "voice": "<voices.json key>", "look": {"skin": hex, "hair": {"style", "colour"}, "beard": {"style", "colour"} | null,
  "build": {"height": 0.85..1.15, "width": 0.85..1.2}, "headgear": str, "parts": {<part>: hex}}, "signature": [str], "version": int}`;
  `PARTS = {"skin", "hair", "beard", "tunic", "cloak", "armour", "helmet", "crest", "trim", "robe", "crown", "shield"}`;
  `load_sheet(cid: str) -> dict`; `sheet_problems(sheet: dict, voices: dict) -> list[str]`; `all_ids() -> list[str]`;
  `resolve(name: str) -> str | None` (id from a speaker name or alias, case/space-insensitive);
  CLI `tc characters list`, `tc characters check <id>`.
- [ ] **Step 1: Failing tests:** valid sheet passes; `test_sheet_with_unknown_voice`; part not in PARTS → problem; colour not `#rrggbb` → problem;
  build out of range → problem; real person without design_source → problem; `resolve("KING XERXES")` with alias `king xerxes` → `"xerxes"`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** (registry root `paths.LIBRARY / "characters"`). **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `-- tc/characters.py library/characters/README.md tests/test_characters.py tc/cli.py`

### Task 2: The character drawing contract in the kit

**Files:** Create `film/src/characters/types.ts`, `film/src/characters/figure.ts`; Test `film/src/characters/figure.test.ts`

**Interfaces:**
- Produces: `interface Pose { expr: Expr; blink?: boolean; mouth?: 'closed'|'open'|'wide'|'o'|'smile'; armL?: ArmPose; armR?: ArmPose; holds?: string; facing?: 1 | -1 }`;
  `type ArmPose = 'down' | 'hip' | 'point' | 'raise' | 'hold_spear' | 'hold_shield' | 'fist_up' | 'open'`;
  `interface Look { skin: string; parts: Record<string, string>; build: { height: number; width: number } }`;
  `part(char: string, name: string, svg: string): string` (wraps `<g data-char data-part data-fill>`);
  `figure(char: string, look: Look, pose: Pose, layers: { back?: string; body: string; head: string; front?: string }): string`
  (applies build scale + facing flip, arms from ArmPose, mouth shapes from Pose.mouth, blink).
- [ ] **Step 1: Failing tests:** `test_every_expression_differs` (a test figure renders 6 different strings for the 6 Expr);
  `part('leonidas','beard', …)` carries `data-char="leonidas" data-part="beard"`; `facing: -1` adds `scale(-1 1)`; mouth `'o'` differs from `'closed'`.
- [ ] **Step 2: Run** `npm test` → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `-- film/src/characters`

### Task 3: Turnaround sheet renderer — `film/scripts/sheet.mjs`

**Files:** Create `film/scripts/lib/page.mjs` (shared: bundle a TS export, open the page, draw, read tagged elements,
screenshot); Modify `film/scripts/inspect.mjs` (use the shared module; also export `char`, `part`, `fill` per element);
Create `film/scripts/sheet.mjs`, `film/src/characters/sheetScene.ts`

**Interfaces:**
- Produces: `node film/scripts/sheet.mjs <id>` → `library/characters/<id>/sheet.png` (1920×1080: full body front,
  three-quarter facing, six expression heads, colour swatches from the sheet, name + who); inspector elements gain
  `char`, `part`, `fill`.
- [ ] **Step 1:** Refactor inspect.mjs onto page.mjs; run it on the fleet scene → same element count as before (56).
- [ ] **Step 2:** Write sheet.mjs + sheetScene.ts (`drawSheet(id)` imports the character module by id).
- [ ] **Step 3: Verify** after Task 5 (needs a real character).
- [ ] **Step 4: Commit** `-- film/scripts film/src/characters/sheetScene.ts`

### Task 4: Character check — `tc still --chars`

**Files:** Create `tc/charcheck.py`; Modify `tc/stillcheck.py` (`--chars` flag); Test `tests/test_charcheck.py`

**Interfaces:**
- Consumes: inspector elements with `char`, `part`, `fill`; `characters.load_sheet`.
- Produces: `character_problems(elements: list[dict], sheets: dict[str, dict]) -> list[str]` — every element with a
  `char` must belong to a registered sheet; its `part` must exist in `look.parts` (or be `skin`/`hair`/`beard`) and
  its fill must equal the sheet colour (case-insensitive) → else `"leonidas beard is #2a1d15, sheet says #2a1d14"`.
- [ ] **Step 1: Failing tests:** `test_wrong_part_colour_is_caught`; unknown character → problem; matching colours → no problems.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `-- tc/charcheck.py tc/stillcheck.py tests/test_charcheck.py`

### Task 5: The first three characters — Leonidas, Themistocles, Xerxes

**Files:** Create `library/characters/{leonidas,themistocles,xerxes}/sheet.json`, `film/src/characters/{leonidas,themistocles,xerxes}.ts`,
`library/characters/*/sheet.png`; Test `film/src/characters/registry.test.ts`

- [ ] **Step 1:** Write the three sheets from the design sources already researched in `library/cast/<id>.json`
  (Leonidas: Sparta "Leonidas" marble head, long combed hair, full beard, transverse-crest officer helmet, red cloak,
  bronze aspis with Λ; Themistocles: Ostia herm, broad face, heavy brow, short full beard, short curly hair, Athenian
  chiton + himation, no armour in council scenes; Xerxes: Persepolis reliefs, long squared beard in rows of curls,
  hair bunched at the nape, crenellated crown, purple-and-gold robe), aliases, voices (Xerxes → `xerxes`; Leonidas and
  Themistocles → new voices from Task 6).
- [ ] **Step 2: Failing test** `registry.test.ts`: each character module draws all 6 expressions; every `data-part` fill
  it uses equals its sheet.json colour (the test reads the json).
- [ ] **Step 3: Implement** the three drawings with `figure()` + kit parts. **Step 4: Run** → PASS.
- [ ] **Step 5: Render the sheets** (`node film/scripts/sheet.mjs <id>` × 3) and look at each: construction (ART_BIBLE §1),
  era accuracy, grip, identity readable at small size. Fix until each would pass the still checklist.
- [ ] **Step 6:** `python -m tc characters check <id>` × 3 → OK.
- [ ] **Step 7: Commit** `-- library/characters film/src/characters`

### Task 6: Voices from the registry + unique per video

**Files:** Modify `tc/dialogue.py` (`voice_for` falls back to the registry), `library/voices.json`; Create `tc/voices.py`;
Test `tests/test_dialogue.py`, `tests/test_voices.py`

**Interfaces:**
- Produces: `voice_for(speaker, voice_key, voices, mapping)` order: line key → job mapping → **registry sheet voice
  (via `characters.resolve`)** → speaker name; `fish_search(query: str, api_key: str) -> list[dict]` (GET
  `https://api.fish.audio/model?title=<q>&page_size=10`, returns `{id, title, tags, languages}`);
  CLI `tc voices search "<query>"`, `tc voices add <key> <reference_id> --use "<who>"` (refuses a reference_id already used by another key).
- [ ] **Step 1: Failing tests:** `test_alias_resolves_voice` (`THEMISTOKLES` alias → themistocles' voice); `test_voices_add_refuses_duplicate_reference`;
  search builds the right URL with the key in a header (fake http).
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5:** Search Fish for two free English male voices that fit (Leonidas: deep, weathered, commanding,
  ~60; Themistocles: quick, persuasive, mid-40s), add them, set them in the two sheets, voice one test line each
  with `tc dialogue` machinery and check the files exist and are 1–6 s long.
- [ ] **Step 6: Commit** `-- tc/dialogue.py tc/voices.py library/voices.json library/characters tests/test_dialogue.py tests/test_voices.py tc/cli.py`

### Task 7: The cast stage — `tc cast <job>`

**Files:** Create `tc/caststage.py`; Test `tests/test_caststage.py`; Modify `tc/cli.py`

**Interfaces:**
- Produces: `jobs/<id>/cast.json` = `{"characters": [ids], "extras": [str]}`; `cast_problems(cast: dict, voices: dict) -> list[str]`
  (every id registered and its sheet passes; every speaker in script.md resolves to a cast character or an extra voice;
  `test_cast_rejects_shared_voice`); CLI `tc cast <job>` marks the stage done when clean.
- [ ] **Step 1: Failing tests** (shared voice, unregistered id, speaker missing from cast). **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** **Step 4: Run** → PASS. **Step 5: Commit** `-- tc/caststage.py tests/test_caststage.py tc/cli.py`

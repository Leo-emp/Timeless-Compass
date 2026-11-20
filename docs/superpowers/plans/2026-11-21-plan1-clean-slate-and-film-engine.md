# Plan 1 — Clean slate + 2D film engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the 3D/Blender pipeline, retire its rules, and stand up the new 2D film engine (Remotion + the
style kit ported from the spikes) that renders a video in parallel chunks on GitHub Actions **and** Kaggle, with
the render speed measured on a 15-minute test.

**Architecture:** A Remotion project in `film/` draws every frame as an SVG string built by pure TypeScript kit
functions (`film/src/kit/`) and shown by one React component. A part renderer renders a frame range to mp4. Python
`tc film` splits a video into frame ranges, starts the ranges on GitHub (workflow matrix, artifacts) and Kaggle
(pushed notebook, kernel output), fetches the parts and joins them losslessly with ffmpeg.

**Tech Stack:** Python 3.12 + pytest (existing `tc`), Node 22, TypeScript, Remotion 4.0.506 (pinned, no `^`),
vitest 2.1.8, ffmpeg, `gh` CLI, `kaggle` CLI.

**Spec:** `docs/superpowers/specs/2026-11-21-2d-autonomous-agent-design.md` (sections 6.4, 6.10, 6.13, 7 M0–M1).

**This is plan 1 of 9.** Later plans (one per milestone, written when the previous one is done):
2 standards + self-checks (ART_BIBLE, SCRIPT_BIBLE, still/motion/era checks, story check, viewer GO gate) ·
3 character registry + unique voices · **4 film craft kit** (word-synced beats, natural motion principles, lip sync,
camera vocabulary + parallax, colour grading, transitions, sound/music sync, 60 s proof sequence) ·
5 first autonomous Short · 6 first autonomous long · 7 thumbnails + upload packs + schedule + Telegram ·
8 results loop + anti-sameness · 9 2D maps.

## Global Constraints

- Zero spend: free tiers only (public repo → free GitHub minutes; Kaggle free quota; no paid APIs) — r7.
- Laptop stays light: no full renders on the laptop; only single stills and ≤ 48-frame smoke renders — r8.
- No AI images, no stock: every pixel drawn by our code — r15.
- Shared working copy: **commit with explicit paths only** (`git commit -- <paths>`), never `git add -A` / `git commit -a`.
- Code is heavily commented for a learner (owner preference): every file starts with a plain-English header; every
  non-obvious line has a comment.
- No secrets in workflows or notebooks: GitHub renders use artifacts; Kaggle uses its own output store.
- Format: long 1920×1080, Shorts 1080×1920, **24 fps**, h264 + yuv420p mp4.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Seams at part joins** — a frame missing or doubled where two parts meet. Expect the joined video to have
   exactly `total` frames → test `test_split_frames_contiguous` (Task 6) + the frame-count check in Task 9.
2. **Different pictures on different machines** — random layout or clipPath ids depending on render order, so a
   frame rendered alone differs from the same frame inside a range. Expect identical pixels → `kit` id reset per
   frame (Task 3) + the still-vs-range hash check in Task 5.
3. **Missing fonts on Linux** (Georgia/Bahnschrift exist only on Windows) — cards render in a fallback font in the
   cloud. Expect the same card on every machine → bundled OFL fonts (Task 5) + the CI still comparison in Task 9.
4. **Kaggle without internet or over quota** — the notebook can't install Node or clone the repo and fails late.
   Expect a clear early error → `test_kaggle_metadata_internet_on` + the notebook's first-cell check (Task 8).
5. **Other sessions' uncommitted 3D work** — deleting files another session changed loses their work. Expect it
   preserved in git history → Task 1 step 1 commits it before the tag.

---

### Task 1: Preserve, tag and remove the 3D pipeline

**Files:**
- Delete: `blender/`, `cloud/blender_shot.py`, `cloud/build_asset_cache.py`, `cloud/setup_blender_linux.sh`,
  `cloud/scans_polyhaven.json`, `cloud/kaggle/`, `cloud/batch.json`, `cloud/queue/`, `cloud/requests/`,
  `cloud/render_request.json`, `.github/workflows/render-batch.yml`, `render-queue.yml`, `render-scene.yml`,
  `render-shards.yml`, `render-test.yml`
- Delete modules + their tests: `tc/{assemble,assets,cast_tool,crowd,fight,performance,render_cache,render_farm,
  render_plan,slowmo,mixamo,sketchfab,look,compare,cloud_queue,kaggle_kernel,thumbnail}.py` and
  `tests/test_{assemble,assets,cast_tool,crowd,fight,performance,render_cache,render_farm,render_plan,render_speed,
  slowmo,mixamo,sketchfab,look,compare,cloud_queue,kaggle_kernel,thumbnail,grooming}.py`
- Delete library 3D assets: `library/scans/`, `library/scans_index.json`, `library/wardrobe/`, `library/sets/`,
  `library/props/`, `library/animals.json`
- Keep (later plans reuse or replace them): `tc/{edit,finish,match,archive,emblems,lipsync,mapcmd}.py`, `tc/maps/`,
  `library/{cast,maps,music,sfx,research,voices.json,fish_usage.json}`, `spike/`
- Modify: `tc/cli.py` (`_load_commands` module list), `tc/doctor.py` is handled in Task 2

**Interfaces:**
- Produces: a repo whose `python -m pytest` passes and whose `tc --help` lists no removed command.

- [ ] **Step 1: Preserve other sessions' work.** Run `git status --short`. If `BLENDER_LOCK` exists in the repo
  root, stop and wait (another session is rendering). Commit every modified tracked file that is on the delete list
  above, with explicit paths: `git commit -m "wip(3d): final state before removal" -- <those paths>`.
- [ ] **Step 2: Tag.** `git tag old-3d-pipeline-final` and `git push origin old-3d-pipeline-final`.
- [ ] **Step 3: Remove.** `git rm -r` every path in the delete lists.
- [ ] **Step 4: Update `_load_commands`** in `tc/cli.py` to exactly:
  `("jobs", "learning", "doctor", "topics", "packaging", "script", "voice", "align", "shots", "run", "finish",
  "edit", "emblems", "research", "mapcmd", "film")` (`film` arrives in Task 6; the loader already skips missing modules).
- [ ] **Step 5: Fix imports.** Run `python -m pytest`. For any remaining module that imported a removed one, delete
  the dead import and the code path that needed it (no stubs). Expected after fixes: all tests pass.
- [ ] **Step 6: Verify.** `python -m tc --help` → none of: assemble, assets, look, compare, cast, render-plan,
  render-bundle, render-shard, frames, kaggle, queue, cache, mixamo, sketchfab, thumbnail, perf.
- [ ] **Step 7: Commit** `git commit -m "chore(m0): remove the 3D/Blender pipeline (tag old-3d-pipeline-final)" -- <every removed and modified path>`

### Task 2: Retire 3D rules + doctor for the 2D engine

**Files:**
- Modify: `tc/learning.py`, `tc/doctor.py`
- Test: `tests/test_learning.py`, `tests/test_doctor.py`

**Interfaces:**
- Produces: `retire_rule(rule_id: str, why: str, replaced_by: str | None = None, now: datetime | None = None) -> dict`;
  `list_rules(stage: str | None = None, include_retired: bool = False) -> list[dict]`; CLI `tc retire <id> --why … [--by rN]`, `tc rules [--stage S] [--all]`.
  A retired rule keeps its id and gains `"retired": {"date": "YYYY-MM-DD", "why": str, "replaced_by": str | None}`.

- [ ] **Step 1: Failing tests** in `tests/test_learning.py` (use the existing tmp `paths.TASTE` fixture pattern):

```python
def test_retired_rule_hidden_from_stage_lists(tmp_taste):
    add_rule("old 3D gate", applies_to=["render"]); add_rule("new 2D bar", applies_to=["render"])
    retire_rule("r1", why="3D dropped", replaced_by="r2")
    assert [r["id"] for r in list_rules("render")] == ["r2"]
    assert list_rules("render", include_retired=True)[0]["retired"]["replaced_by"] == "r2"

def test_retire_unknown_rule_raises(tmp_taste):
    with pytest.raises(ValueError, match="r99"):
        retire_rule("r99", why="x")

def test_retire_appends_note_to_rules_md(tmp_taste):
    add_rule("old"); retire_rule("r1", why="3D dropped")
    assert "r1 RETIRED" in (paths.TASTE / "rules.md").read_text(encoding="utf-8")
```

  In `tests/test_doctor.py`: `test_doctor_checks_node_and_gh` asserts check names include `"node >= 22"`,
  `"gh CLI logged in"`, `"film engine installed"`, `"kaggle credentials"` (optional) and **not** `"Blender 5.3 portable"`.
- [ ] **Step 2: Run** `python -m pytest tests/test_learning.py tests/test_doctor.py` → FAIL (`retire_rule` not defined; old check names).
- [ ] **Step 3: Implement.** `retire_rule` writes the `retired` block into `learning.json` and appends
  `## rN RETIRED (date)\n- **Why:** …\n- **Replaced by:** …` to `rules.md`; `list_rules` skips retired unless asked.
  Doctor: remove Blender/MPFB checks; add `node >= 22` (parse `node --version`), `npm on PATH`, `gh CLI logged in`
  (`gh auth status` exit 0), `film engine installed` (`film/node_modules/remotion` exists), `kaggle credentials`
  (`~/.kaggle/kaggle.json` or `~/.kaggle/credentials.json` exists — this laptop has the latter — `required=False`).
- [ ] **Step 4: Run** the two test files → PASS; full `python -m pytest` → PASS.
- [ ] **Step 5: Retire the rules for real:**
  `python -m tc retire r10 --why "3D look metric vs Heroes of Bronze; 2D uses the spec 6.6 still bar"`,
  `python -m tc retire r13 --why "3D library gate; replaced by the 6.6 still bar" `,
  `python -m tc retire r14 --why "Blender maps; same look drawn in 2D" --by r35`. Check `python -m tc rules --stage shots` shows none of them.
- [ ] **Step 6: Commit** `-- tc/learning.py tc/doctor.py tests/test_learning.py tests/test_doctor.py taste/learning.json taste/rules.md`

### Task 3: Film project + style kit core

**Files:**
- Create: `film/package.json`, `film/package-lock.json`, `film/tsconfig.json`, `film/remotion.config.ts`,
  `film/vitest.config.ts`, `film/.gitignore` (`node_modules/`, `out/`), `film/src/kit/core.ts`
- Test: `film/src/kit/core.test.ts`

**Interfaces:**
- Produces (all in `film/src/kit/core.ts`, pure functions returning SVG strings unless noted):
  `OUT = '#2a1c13'`, `SW = 7`; `resetIds(): void`; `nextId(prefix: string): string`;
  `rng(seed: number): () => number` (mulberry32, as in the spike); `ease(x: number): number` (in-out quad);
  `wrap(v: number, w: number): number`; `sh(tag: string, attrs: Record<string, string | number>, fill: string): string`;
  `ln(d: string, w?: number, col?: string): string`; `limb(d: string, w: number, col: string): string`;
  `hand(x: number, y: number, skin: string): string`;
  `shade(clipInner: string, cx: number, cy: number, rx: number, ry: number, col?: string): string`;
  `bg(d: string, fill: string, w?: number): string` (background outline, default width 4).

- [ ] **Step 1: Scaffold.** `package.json` with exact versions: `remotion`, `@remotion/cli`, `@remotion/renderer`,
  `@remotion/bundler` all `4.0.506`; `react`/`react-dom` `18.3.1`; dev: `typescript 5.6.3`, `vitest 2.1.8`,
  `@types/react 18.3.12`. Scripts: `"test": "vitest run"`, `"still": "remotion still"`. Run `npm install` in `film/`.
- [ ] **Step 2: Failing tests** `core.test.ts`:

```ts
test('rng is deterministic per seed', () => { const a = rng(480), b = rng(480); expect([a(), a()]).toEqual([b(), b()]); });
test('ease hits 0, 0.5, 1', () => { expect(ease(0)).toBe(0); expect(ease(0.5)).toBe(0.5); expect(ease(1)).toBe(1); });
test('wrap handles negatives', () => { expect(wrap(-10, 100)).toBe(90); });
test('sh uses the house outline', () => { expect(sh('circle', { cx: 1, cy: 2, r: 3 }, '#fff')).toContain(`stroke="${OUT}" stroke-width="${SW}"`); });
test('ids restart each frame so every machine draws the same frame', () => {
  resetIds(); const a = shade('<circle r="1"/>', 0, 0, 1, 1); resetIds(); const b = shade('<circle r="1"/>', 0, 0, 1, 1);
  expect(a).toBe(b);
});
```

- [ ] **Step 3: Run** `npm test` in `film/` → FAIL (module not found).
- [ ] **Step 4: Implement** `core.ts` by porting the helpers from `spike/art_dir/cast_lib.js` (keep their comments),
  replacing the global `uid` with `nextId`/`resetIds`.
- [ ] **Step 5: Run** `npm test` → PASS.
- [ ] **Step 6: Commit** `-- film/package.json film/package-lock.json film/tsconfig.json film/remotion.config.ts film/vitest.config.ts film/.gitignore film/src/kit`

### Task 4: Cast kit (heads, faces, headgear, hoplite parts)

**Files:**
- Create: `film/src/kit/cast.ts`
- Test: `film/src/kit/cast.test.ts`

**Interfaces:**
- Consumes: Task 3 core.
- Produces: `type Expr = 'neutral'|'stern'|'worried'|'shocked'|'sly'|'grief'`;
  `head(skin: string, ex?: Expr, opt?: { age?: boolean; beard?: string; blink?: boolean }): string`;
  `face(ex: Expr): string`; `hair: { chonmage(), kabuto(), corinthian(), roman(), wig(), fedora() }` (each `(): string`);
  `corinthClosed(crest?: 'fan' | 'king' | 'none'): string`; `corinthKingUp(): string`; `bigBeard(col: string, curls?: string): string`;
  `longHairBack(col: string): string`; `longHairTop(col: string): string`; `lashes(): string`;
  `pole(x1: number, y1: number, x2: number, y2: number, col?: string): string`;
  `aspis(cx: number, cy: number, r?: number): string` (emblem scales with r, as fixed in the spike);
  `hopliteBody(skin: string, cloak?: boolean): string`.
  Blink is the `opt.blink` flag (no globals).

- [ ] **Step 1: Failing tests:** `head('#f0cfa8','neutral')` contains two eye ellipses `rx="6.5"`;
  `head(s,'neutral',{blink:true})` contains the lid path `M-30 -299 Q-21 -293 -12 -299`; `aspis(0,0,30)` emblem
  stroke-width is `12*30/84` (≈ 4.29); every `Expr` renders without throwing.
- [ ] **Step 2: Run** `npm test` → FAIL.
- [ ] **Step 3: Implement** by porting from `spike/art_dir/cast_lib.js` and `cast_lib2.js` (generic builders only —
  no named characters; those belong to the character registry in plan 3).
- [ ] **Step 4: Run** `npm test` → PASS.
- [ ] **Step 5: Commit** `-- film/src/kit/cast.ts film/src/kit/cast.test.ts`

### Task 5: Fleet test composition + fonts + determinism

**Files:**
- Create: `film/src/Root.tsx`, `film/src/index.ts`, `film/src/SvgFrame.tsx`, `film/src/compositions/FleetTest.tsx`,
  `film/src/compositions/fleet.ts` (the scene as `drawFleet(t: number): string`), `film/public/fonts/` (EB Garamond
  + Barlow Condensed, OFL, with their `OFL.txt`), `film/src/kit/fonts.ts`
- Test: `film/src/compositions/fleet.test.ts`

**Interfaces:**
- Consumes: Tasks 3–4.
- Produces: compositions **`FleetTest`** (1920×1080, 24 fps, 192 frames) and **`FleetTestLong`** (1920×1080,
  24 fps, 21600 frames = 15 min: the same scene, `t = frame/24`). `SvgFrame({ svg }: { svg: string })` renders a
  full-frame `<svg viewBox="0 0 1920 1080">` with the string inside. `loadFonts(): Promise<void>` (Remotion
  `staticFile` + `delayRender` until the fonts are ready); card text uses `'EB Garamond'`, labels `'Barlow Condensed'`.

- [ ] **Step 1: Failing tests** (`fleet.test.ts`): `drawFleet(4.0) === drawFleet(4.0)` after `resetIds()` each
  time; `drawFleet(0)` contains `THE GREEK FLEET · 480 BC`; `drawFleet(0) !== drawFleet(1)` (it moves).
- [ ] **Step 2: Run** `npm test` → FAIL.
- [ ] **Step 3: Implement** `fleet.ts` by porting `window.draw(t)` from `spike/art_dir/scene_fleet_anim.html`
  (call `resetIds()` at the top; blink via `opt.blink`); `FleetTest.tsx` = `SvgFrame` of `drawFleet(frame / fps)`.
- [ ] **Step 4: Run** `npm test` → PASS.
- [ ] **Step 5: Visual check.** `npx remotion still FleetTest out/f100.png --frame=100` and view it next to
  `spike/art_dir/fleet_motion.mp4` frame 100 (`ffmpeg -ss 4.1667 -i … -frames:v 1`). Expected: same picture
  (fonts may differ slightly — EB Garamond replaces Georgia).
- [ ] **Step 6: Determinism check.** Render frame 100 alone, and frames 96–104 as a sequence
  (`npx remotion render FleetTest out/seq --sequence --frames=96-104`); `sha256` of frame 100 from both must match.
- [ ] **Step 7: Commit** `-- film/src film/public/fonts`

### Task 6: `tc film` — split, start, fetch, join, speed

**Files:**
- Create: `tc/film.py`, `film/render-part.mjs`
- Test: `tests/test_film.py`

**Interfaces:**
- Produces (in `tc/film.py`):
  `split_frames(total: int, parts: int) -> list[tuple[int, int]]` (inclusive ranges, contiguous, sizes differ by ≤ 1);
  `github_dispatch_args(comp: str, ranges: list[tuple[int, int]], ref: str = "main") -> list[str]`
  (the `gh workflow run film-render.yml -f comp=… -f parts=<json> --ref …` argv);
  `concat_list(parts: list[Path]) -> str` (ffmpeg concat-demuxer text, sorted by start frame from the file name `part-<from>-<to>.mp4`);
  `join_parts(parts_dir: Path, out: Path) -> Path` (ffmpeg `-f concat -safe 0 -c copy`);
  `speed_report(timings: list[dict]) -> dict` → `{"frames": int, "render_s_sum": float, "wall_s": float, "frames_per_s": float}`
  (each timing: `{"from", "to", "seconds", "started", "ended"}`; wall = max ended − min started).
  CLI: `tc film parts <frames> <n>`, `tc film render <comp> --frames N --parts N --on github|kaggle`,
  `tc film fetch <run-id|kernel-slug> --on github|kaggle --to DIR`, `tc film join DIR OUT`, `tc film speed DIR`.
- Produces (`film/render-part.mjs`): `node render-part.mjs <comp> <from> <to> <outDir>` → writes
  `outDir/part-<from>-<to>.mp4` and `outDir/timing-<from>-<to>.json`; concurrency from env `CONCURRENCY` (default
  = CPU count); codec h264, `pixelFormat: 'yuv420p'`, `crf: 18`.

- [ ] **Step 1: Failing tests:**

```python
def test_split_frames_contiguous():
    r = split_frames(21600, 7)
    assert r[0][0] == 0 and r[-1][1] == 21599
    assert all(b[0] == a[1] + 1 for a, b in zip(r, r[1:]))
    sizes = [b - a + 1 for a, b in r]; assert max(sizes) - min(sizes) <= 1

def test_split_frames_more_parts_than_frames():
    assert split_frames(3, 10) == [(0, 0), (1, 1), (2, 2)]

def test_dispatch_args_carry_json_ranges():
    a = github_dispatch_args("FleetTest", [(0, 95), (96, 191)])
    assert a[:4] == ["gh", "workflow", "run", "film-render.yml"] and "parts=[[0,95],[96,191]]" in a

def test_concat_list_orders_by_start_frame(tmp_path):
    ps = [tmp_path / "part-96-191.mp4", tmp_path / "part-0-95.mp4"]
    assert concat_list(ps).splitlines()[0].endswith("part-0-95.mp4'")

def test_speed_report_wall_clock():
    t = [{"from": 0, "to": 99, "seconds": 50, "started": 0, "ended": 60},
         {"from": 100, "to": 199, "seconds": 40, "started": 5, "ended": 50}]
    assert speed_report(t) == {"frames": 200, "render_s_sum": 90, "wall_s": 60, "frames_per_s": 200 / 60}
```

- [ ] **Step 2: Run** `python -m pytest tests/test_film.py` → FAIL.
- [ ] **Step 3: Implement** `tc/film.py` (register commands with `@register("film", …)` and an argparse sub-action)
  and `film/render-part.mjs` (`bundle()` from `@remotion/bundler`, `selectComposition` + `renderMedia({ frameRange: [from, to] })`).
- [ ] **Step 4: Run** tests → PASS. Smoke: `node film/render-part.mjs FleetTest 0 47 film/out` → `part-0-47.mp4`
  with 48 frames (`ffprobe -count_frames`).
- [ ] **Step 5: Commit** `-- tc/film.py tests/test_film.py film/render-part.mjs`

### Task 7: GitHub render workflow

**Files:**
- Create: `.github/workflows/film-render.yml`

**Interfaces:**
- Consumes: `film/render-part.mjs` (Task 6), `github_dispatch_args` (Task 6).
- Produces: workflow `film-render` with inputs `comp` (string) and `parts` (JSON list of `[from, to]`); one matrix
  job per range on `ubuntu-latest` (`fail-fast: false`, `max-parallel: 20`, `timeout-minutes: 340`); each uploads
  artifact `part-<from>-<to>` holding the mp4 + timing json. No secrets.

- [ ] **Step 1: Write the workflow:** checkout (sparse: `film/`), `actions/setup-node@v4` node 22 with npm cache on
  `film/package-lock.json`, `npm ci --no-audit --no-fund`, `npx remotion browser ensure`, `node render-part.mjs`,
  `actions/upload-artifact@v4` (retention 3 days).
- [ ] **Step 2: Push** the branch, then `python -m tc film render FleetTest --frames 192 --parts 4 --on github`.
- [ ] **Step 3: Verify.** `python -m tc film fetch <run-id> --on github --to film/out/gh` →
  `python -m tc film join film/out/gh film/out/fleet_gh.mp4`; `ffprobe -count_frames` → **192** frames; view frame
  100 next to the laptop still from Task 5 (fonts identical, picture identical).
- [ ] **Step 4: Commit** `-- .github/workflows/film-render.yml`

### Task 8: Kaggle render

**Files:**
- Create: `tc/film_kaggle.py`
- Test: `tests/test_film_kaggle.py`

**Interfaces:**
- Consumes: `split_frames`, `render-part.mjs`.
- Produces: `film_notebook(comp: str, ranges: list[tuple[int, int]], repo: str = "https://github.com/Leo-emp/Timeless-Compass.git", ref: str = "main") -> dict`
  (Jupyter JSON); `film_metadata(username: str, slug: str) -> dict` (`enable_internet: true`, `enable_gpu: false`,
  `is_private: true`, `kernel_type: "notebook"`, `language: "python"`); `write_film_kernel(comp, ranges, username, out_dir: Path) -> Path`;
  `kaggle_username() -> str` (parse `kaggle config view`, as the removed `kaggle_kernel._username` did).
  `tc film render … --on kaggle` writes the kernel dir and runs `kaggle kernels push -p <dir>`;
  `tc film fetch <slug> --on kaggle --to DIR` runs `kaggle kernels output <user>/<slug> -p DIR`.

- [ ] **Step 1: Failing tests:** `test_kaggle_metadata_internet_on` (`film_metadata("u","s")["enable_internet"] is True`);
  `test_notebook_first_cell_checks_internet` (first code cell contains `urllib.request.urlopen("https://github.com"` and
  raises a clear `RuntimeError("Kaggle internet is off …")`); `test_notebook_renders_every_range` (one
  `render-part.mjs FleetTest <from> <to> /kaggle/working/parts` line per range).
- [ ] **Step 2: Run** `python -m pytest tests/test_film_kaggle.py` → FAIL.
- [ ] **Step 3: Implement.** Notebook cells: internet check → install Node 22 (NodeSource setup script + apt) →
  `git clone --depth 1 --branch <ref> <repo>` → `npm ci` in `film/` → `npx remotion browser ensure` → render each
  range (two at a time, `CONCURRENCY` = cores/2) into `/kaggle/working/parts`.
- [ ] **Step 4: Run** tests → PASS.
- [ ] **Step 5: Real run:** `python -m tc film render FleetTest --frames 192 --parts 2 --on kaggle`, wait for the
  kernel (`kaggle kernels status`), fetch, join → 192 frames, picture matches Task 7.
- [ ] **Step 6: Commit** `-- tc/film_kaggle.py tests/test_film_kaggle.py tc/film.py`

### Task 9: Speed test on a 15-minute video + record

**Files:**
- Create: `docs/RENDER_SPEED.md`
- Modify: `docs/superpowers/specs/2026-11-21-2d-autonomous-agent-design.md` (6.10 target line only, if measured
  numbers differ)

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: GitHub run.** `python -m tc film render FleetTestLong --frames 21600 --parts 20 --on github`; fetch;
  `tc film speed film/out/long_gh` → record frames/s and wall-clock.
- [ ] **Step 2: Combined run.** Split 21600 frames into 24 parts: 20 to GitHub, 4 to Kaggle (one kernel); fetch
  both into one dir; join; `ffprobe -count_frames` → **21600**; spot-check frames at each seam (part boundaries)
  for jumps.
- [ ] **Step 3: Write `docs/RENDER_SPEED.md`:** table of runs (farm, parts, frames/s per runner, wall-clock, total
  minutes), the chosen default split for long videos and Shorts, and Kaggle weekly quota used.
- [ ] **Step 4:** If wall-clock for 15 min is > 60 min, add the measured number and the next speed lever
  (pre-rendered static layers) to spec 6.10; otherwise leave the spec as is.
- [ ] **Step 5: Clean up** `film/out/` (git-ignored) and delete fetched parts after the numbers are recorded (r8).
- [ ] **Step 6: Commit** `-- docs/RENDER_SPEED.md docs/superpowers/specs/2026-11-21-2d-autonomous-agent-design.md`

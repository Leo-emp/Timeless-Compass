# Cloud rendering (WS9)

The laptop never renders long videos (16 GB RAM, tight disk). It **plans** and **checks**; free cloud machines
**render**:

| Machine | What it renders | Free limit | Engine |
|---|---|---|---|
| Kaggle notebook (GPU T4 / P100) | shots with people (medium + close-up faces, hair, cloth) | ~30 GPU h / week, 12 h per session | Cycles + OIDN on GPU (OptiX/CUDA); Eevee for wide shots |
| GitHub Actions (up to 20 CPU runners) | shots with nobody on screen (sea, hills, ships, maps) | unlimited minutes (public repo), 6 h per job | Eevee (software OpenGL) / Cycles CPU |

## The flow (one job)

```
python -m tc assemble <job>              # recipes per shot (+ library gaps)
python -m tc render-plan <job> --speed   # who renders what, engine + samples per shot, hours per shard
python -m tc render-bundle <job>         # cloud/bundles/<job>.json: recipes + plan + scans per shot (no secrets)
python -m tc cache plan <job>            # MB of scans each shard will download
  -- owner: commit + push the bundle --
GitHub:  Actions tab -> render-shards -> Run workflow (job = <job>)
Kaggle:  python -m tc kaggle <job> --shard 0   then   kaggle kernels push -p cloud/kaggle/out/<slug>
  -- when they finish --
gh run download <run id> -D jobs/<job>/render
kaggle kernels output <user>/<slug> -p jobs/<job>/render
python -m tc frames check <job>          # every shot: ok / missing / black frames
python -m tc frames requeue <job>        # shots to send out again -> jobs/<job>/requeue.json
python -m tc frames join <job>           # one video per shot -> jobs/<job>/shots/<shot>.mp4
```

Every cloud machine joins its finished shots into a video itself and deletes their frames, so the laptop downloads
one small mp4 per shot instead of hundreds of PNGs.

## Cloud render QUEUE (stills + test scenes, many sessions at once)

`cloud/batch.json` is ONE shared file: two sessions editing it overwrite each other. The queue replaces it with
**one new file per request** that is never edited afterwards:

```
python -m tc queue submit cannon blender/scenes/cannon_test.py out/cannon 64 --session C            # GitHub CPU
python -m tc queue submit cannon blender/scenes/cannon_test.py out/cannon 128 --session C --target kaggle   # GPU
python -m tc queue list                        # every request: target + status (queued / done / failed)
```

- The file is `cloud/queue/<YYYYMMDD-HHMMSS>-<session>-<name>.json`, created with "fail if it exists" (a clash in
  the same second gets `-2`). The scans the scene needs are found by reading the scene + every `blender/lib`
  function it calls; Sketchfab ones are flagged (`cloud_missing`) because only R2 can give them to a cloud machine.
- **GitHub:** commit + push ONLY your queue file. `.github/workflows/render-queue.yml` renders exactly the files
  that push ADDED (1 runner each, up to 20 in parallel), so it never re-renders another session's requests.
  Artifact `render-<id>` = `out/` with the images + `_results/<id>.json`. Re-run by hand with the `ids` input.
- **Kaggle GPU:** `python -m tc queue kaggle <id> [<id> ...]` writes `cloud/kaggle/out/tc-still-.../` (the
  requests are written INTO the kernel script, so they need not be pushed; the scene code must be). Push with
  `python -m kaggle kernels push -p <folder>` (owner OK: uses GPU quota), then
  `python -m kaggle kernels output <user>/<folder name> -p output/cloud/`.
- **Both runners** run `python -m tc queue run <file> --blender <path> [--gpu]`: scans -> render through
  `cloud/blender_shot.py` (`TC_SCRIPT` = the scene; GPU OptiX/CUDA + OpenImageDenoise + adaptive sampling; the
  scene's own sample count is kept) -> every image checked (missing / black / broken = `failed`) -> optional film
  finish (`--finish IN OUT --look dusk`) -> `out/_results/<id>.json` (status, seconds, images) + `<id>.log`.
- Migration: `batch.json` + `render-batch.yml` keep working until every session has moved; then delete them
  (owner decides, Session D uses batch.json now).

## Safety (crash, kill, time limit)

- `progress.json` per shard is written after **every** shot; running the shard again skips finished shots.
- `blender/scenes/shot.py` skips frames that already exist, so a half-rendered shot continues where it stopped.
- After each shot every frame is checked: **missing** (gaps or never reached), **black** (mean ≤ 1/255: a broken
  render; a dark night shot is fine), **broken** (0 bytes / unreadable). Bad frames are deleted and the shot is
  rendered again (up to 2 retries), then marked `failed`.
- Stall watchdog: a shot that takes 4× its estimate (min 30 min) is killed and retried. Blender output goes to
  `<shard>/<shot>/blender.log`.
- Time limits: Kaggle stops starting new shots after 11 h (sessions end at 12 h); GitHub after 5.5 h (jobs end at 6 h).
  Unfinished shots are `paused`, not lost.
- Resume: Kaggle `python -m tc kaggle <job> --shard N --resume` attaches the last session's output; GitHub: run the
  workflow again with `resume_run_id` = the earlier run's id.

## Speed (task 4) — estimates until M3 measures them

`python -m tc render-plan <job> --speed` prints the table from `tc/render_plan.py`. Shot type comes from the shot
list: nobody on screen = landscape; lens ≤ 28 mm or camera ≥ 8 m = wide; lens ≥ 70 mm or ≤ 1.6 m = close-up.
"Old" = every shot in Cycles at 256 samples with no denoiser.

| Shot type | Engine | Samples | Kaggle T4 s/frame old → new | GitHub CPU s/frame old → new | Saved |
|---|---|---|---|---|---|
| card / map | Eevee | 8 | 2.6 → 0.3 | 26 → 3 | ~88% |
| landscape | Eevee | 32 | 12.8 → 1.5 | 128 → 15 | ~88% |
| wide | Eevee | 48 | 17.9 → 2.5 | 179 → 22 | ~86–88% |
| medium | Cycles + OIDN | 64 | 23.0 → 6.2 | 230 → 60 | ~73% |
| close-up | Cycles + OIDN | 96 | 28.2 → 11.0 | 282 → 108 | ~61% |

Cycles also gets adaptive sampling (threshold 0.02), albedo + normal denoise passes (keeps cloth and skin detail),
8 light bounces. `cloud/blender_shot.py` applies all of this around `shot.py` without editing it. If a machine has
no OpenGL for Eevee, the Kaggle notebook detects it and wide shots fall back to Cycles + OIDN.

## Asset cache (task 3) — Cloudflare R2, free 10 GB

```
R2 bucket (public read through its r2.dev URL; the assets are CC0 / CC-BY, nothing private)
  library/scans_index.json                 what exists, licence, source, files, size
  library/scans/<id>/<files>               the scans exactly as on the laptop (0.61 GB today, 40 scans)
  built/cast/<name>-<hash>.blend           a character built once: body, face, hair, wardrobe (packed textures)
  built/sets/<name>-<hash>.blend           a whole set + its film light
```

- **Budget:** the library may use 6 GB (spec 6.4), leaving 4 GB for review copies. `tc cache index` and
  `cloud/r2_push.sh` refuse to go over it.
- **Per job, only what it needs:** `tc render-bundle` records the scans each shot needs (manifest `"scans"` lists
  first; otherwise read from the builder code, following every helper it calls). Each shard downloads only its own
  shots' scans (`tc cache fetch --bundle ... --shard github:3`).
- **No R2 yet?** Poly Haven scans (33 of 40) are re-downloaded from Poly Haven for free. The 7 Sketchfab museum
  scans need R2 (their download needs a token, which never goes to a cloud machine).
- **Built assets:** `tc cache built <job>` lists the keys a job needs. The hash covers the manifest + the builder code,
  so a change means a new key (no stale characters). Build one on a cloud machine with
  `blender -b --python cloud/build_asset_cache.py -- cast themistocles out/<key>`.
  Still to do (shot pipeline, WS10): make `blender/lib/build.py` append the cached `.blend` instead of building.

## Owner steps (one time each, nothing here costs money)

### Kaggle (free GPU)
1. kaggle.com → sign in → **Settings → Phone verification** (needed for GPU + internet in notebooks).
2. **Settings → API → Create New Token**: downloads `kaggle.json`. Put it at `C:\Users\User\.kaggle\kaggle.json`
   (the Kaggle tool reads it there; do not paste the key in chat or commit it).
3. `pip install kaggle` and check: `kaggle kernels list --mine` (should answer, empty is fine).
4. Tell the agent "Kaggle is ready" — it then generates a notebook with `python -m tc kaggle <job> --shard 0` and
   asks you before pushing it (`kaggle kernels push`), because a push starts a GPU session (uses weekly quota).

### GitHub Actions
1. Commit + push the branch (with `cloud/bundles/<job>.json`).
2. Actions tab → **render-shards** → Run workflow → job id. (The agent never pushes or starts it without asking.)
3. Optional: Settings → Secrets and variables → Actions → **Variables** → `TC_R2_PUBLIC_URL` = the bucket's public URL.

### Cloudflare R2 (asset cache)
1. Cloudflare dashboard → R2 → create bucket `timeless-compass-assets` (free plan; set a billing alert at $1).
2. Bucket → Settings → **Public access → r2.dev subdomain: Allow**. Put that URL in `.env` as `TC_R2_PUBLIC_URL`.
3. R2 → **Manage API tokens** → create a token with *Object Read & Write* on **this bucket only**. Put in `.env`:
   `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`.
4. Install the AWS CLI (`winget install Amazon.AWSCLI`), then, when you say so: `bash cloud/r2_push.sh --dry-run`,
   then `bash cloud/r2_push.sh`.

## Files

| File | What |
|---|---|
| `setup_blender_linux.sh` | installs Blender 5.3 + MPFB + MakeHuman CC0 assets on Linux |
| `blender_shot.py` | Blender wrapper: per-shot engine / samples / OIDN / adaptive, then runs `shot.py` |
| `kaggle/render_shard.py` | Kaggle notebook template (cells split at `# %%`), filled in by `tc kaggle` |
| `kaggle/render_test.py` | the first one-still Kaggle test cell |
| `build_asset_cache.py` | Blender: build one character / set and save it as a compressed `.blend` |
| `r2_push.sh` | owner-run upload of the library (+ built assets) to R2 |
| `bundles/<job>.json` | per-job cloud bundle (written by `tc render-bundle`) |
| `../.github/workflows/render-shards.yml` | the 20-runner CPU workflow (manual start only) |

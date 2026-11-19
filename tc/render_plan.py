# Render farm planner (WS9): split a video's shots between
#   - Kaggle GPU sessions  (heavy shots: characters with hair, cloth, armour)
#   - GitHub Actions CPU runners (light shots: landscapes, sea, maps, establishing shots)
# so that every machine finishes at about the same time (longest-job-first greedy balancing).
#
# It also decides HOW each shot is rendered (WS9 task 4, "speed"):
#   shot TYPE  ->  engine (Eevee or Cycles)  ->  samples  ->  denoiser  ->  estimated seconds per frame.
# The idea: the camera decides how much detail the viewer can see.
#   * landscape / wide shots: people are small, so the fast real-time engine (Eevee) looks good enough;
#   * medium / close-up shots: faces, skin and hair need Cycles (real light bouncing), but with the
#     OpenImageDenoise (OIDN) AI denoiser we can stop at 64-96 samples instead of 256+ and remove the grain after.
#
# IMPORTANT: the seconds-per-frame numbers below are ESTIMATES (from Blender benchmark scaling and the laptop's
# measured 7-12 s/frame Eevee at 720p). Milestone M3 measures the real numbers on Kaggle + GitHub; then replace
# the tables S_PER_100_SAMPLES / EEVEE_S_PER_FRAME with the measured values (`tc render-plan <job> --speed`
# prints what the plan assumes).
import json

from tc import jobs
from tc.cli import register

FPS = 24
CHAR_WEIGHT = 0.5          # each character on screen adds 50% render cost (hair strands, cloth, skin)

# ------------------------------------------------------------------------------------------- shot types
SHOT_TYPES = ("card", "landscape", "wide", "medium", "closeup")
WIDE_LENS_MM, WIDE_DIST_M = 28, 8.0          # lens <= 28 mm or camera >= 8 m from the subject -> wide
CLOSE_LENS_MM, CLOSE_DIST_M = 70, 1.6        # lens >= 70 mm or camera <= 1.6 m from the face -> close-up
DEFAULT_LENS, DEFAULT_DIST = 40, 3.6         # what blender/scenes/shot.py uses when the shot does not say


def shot_type(shot: dict) -> str:
    """What kind of picture is this?  card / landscape / wide / medium / closeup.
    Uses only what the shot list already has: who is on screen + the camera's lens and distance."""
    if shot.get("card"):
        return "card"                                   # a map label or place/date card: almost free to render
    if not shot.get("who"):
        return "landscape"                              # nobody on screen: sea, hills, ships, establishing shot
    cam = shot.get("camera") or {}
    lens = cam.get("lens", DEFAULT_LENS)
    dist = cam.get("dist", DEFAULT_DIST)
    if lens <= WIDE_LENS_MM or dist >= WIDE_DIST_M:
        return "wide"
    if lens >= CLOSE_LENS_MM or dist <= CLOSE_DIST_M:
        return "closeup"
    return "medium"


# ------------------------------------------------------------------------------------------- engine + samples
ENGINE_FOR = {"card": "EEVEE", "landscape": "EEVEE", "wide": "EEVEE", "medium": "CYCLES", "closeup": "CYCLES"}
# Samples per pixel. Cycles numbers are LOW on purpose: OIDN removes the leftover noise.
# Eevee numbers are its "TAA render samples" (anti-aliasing + soft shadows), a different scale.
SAMPLES = {"card": 8, "landscape": 32, "wide": 48, "medium": 64, "closeup": 96}
ADAPTIVE_THRESHOLD = 0.02   # Cycles stops sampling a pixel early once it is this clean (saves time on flat sky/walls)
OLD_SAMPLES = 256           # the "before" baseline: every shot in Cycles at 256 samples


def render_settings_for(shot: dict) -> dict:
    """The render settings for one shot. cloud/blender_shot.py applies them inside Blender."""
    t = shot_type(shot)
    engine = ENGINE_FOR[t]
    s = {"type": t, "engine": engine, "samples": SAMPLES[t]}
    if engine == "CYCLES":
        s["denoiser"] = "OPENIMAGEDENOISE"              # the free Intel AI denoiser (runs on CPU and on GPU)
        s["adaptive_threshold"] = ADAPTIVE_THRESHOLD
    return s


# ------------------------------------------------------------------------------------------- time estimates
# Cycles seconds per frame per 100 samples at 1280x544, by machine and shot type (ESTIMATES, see top of file).
#   kaggle = one NVIDIA T4 with OptiX;  github = 4-core cloud CPU (no GPU).
S_PER_100_SAMPLES = {
    "kaggle": {"card": 1.0, "landscape": 5.0, "wide": 7.0, "medium": 9.0, "closeup": 11.0},
    "github": {"card": 10.0, "landscape": 50.0, "wide": 70.0, "medium": 90.0, "closeup": 110.0},
}
# Eevee seconds per frame (whole frame, at the SAMPLES above). On GitHub there is no GPU, so Eevee runs on a
# software OpenGL driver (Mesa llvmpipe): it works, but much slower than on a real GPU.
EEVEE_S_PER_FRAME = {
    "kaggle": {"card": 0.3, "landscape": 1.5, "wide": 2.5, "medium": 3.0, "closeup": 3.5},
    "github": {"card": 3.0, "landscape": 15.0, "wide": 22.0, "medium": 28.0, "closeup": 32.0},
}
DENOISE_S = {"kaggle": 0.4, "github": 2.0}         # OIDN cost per frame (GPU vs CPU)
LOAD_S_PER_SHOT = 90.0                              # building the scene + cloth bake before the first frame


def seconds_per_frame(t: str, engine: str, samples: int, where: str, denoise: bool = True) -> float:
    if engine == "EEVEE":
        return EEVEE_S_PER_FRAME[where][t]
    return S_PER_100_SAMPLES[where][t] * samples / 100 + (DENOISE_S[where] if denoise else 0.0)


def estimate_seconds(shot: dict, where: str = "kaggle") -> float:
    """Wall-clock seconds to render the whole shot on that machine (frames x seconds per frame).
    The fixed per-shot load time is left out here so a shot twice as long costs exactly twice as much;
    shard totals add LOAD_S_PER_SHOT per shot."""
    s = render_settings_for(shot)
    frames = round((shot.get("dur") or 0) * FPS)
    return frames * seconds_per_frame(s["type"], s["engine"], s["samples"], where)


def speed_table(where: str = "kaggle") -> list[dict]:
    """Before/after seconds per frame for each shot type: OLD = Cycles 256 samples, no denoiser;
    NEW = this file's engine + samples + OIDN. Printed by  tc render-plan <job> --speed."""
    rows = []
    for t in SHOT_TYPES:
        engine = ENGINE_FOR[t]
        old = seconds_per_frame(t, "CYCLES", OLD_SAMPLES, where, denoise=False)
        new = seconds_per_frame(t, engine, SAMPLES[t], where)
        rows.append({"type": t, "engine": engine, "samples": SAMPLES[t], "old_s_per_frame": round(old, 2),
                     "new_s_per_frame": round(new, 2), "saved_pct": round(100 * (1 - new / old))})
    return rows


# ------------------------------------------------------------------------------------------- shard balancing
def estimate_cost(shot: dict) -> float:
    """Relative cost: frames x (1 + 0.5 per character). Kept as a simple, machine-free number for the plan."""
    frames = round((shot.get("dur") or 0) * FPS)
    return frames * (1 + CHAR_WEIGHT * len(shot.get("who") or []))


def _balance(shots: list[dict], n: int, where: str) -> list[dict]:
    """Longest job first: put each shot (biggest first) into the machine with the least work so far.
    Work = estimated seconds on THAT machine type, so Eevee shots count as cheap and close-ups as expensive."""
    groups = [{"shots": [], "cost": 0.0, "seconds": 0.0} for _ in range(n)]
    for s in sorted(shots, key=lambda s: estimate_seconds(s, where), reverse=True):
        g = min(groups, key=lambda g: g["seconds"])
        g["shots"].append(s["id"])
        g["cost"] += estimate_cost(s)
        g["seconds"] += estimate_seconds(s, where) + LOAD_S_PER_SHOT
    for g in groups:
        g["hours"] = round(g["seconds"] / 3600, 2)
    return groups


def plan_shards(shots: list[dict], gpu_shards: int = 2, cpu_shards: int = 10) -> dict:
    heavy = [s for s in shots if s.get("who")]          # people on screen -> GPU
    light = [s for s in shots if not s.get("who")]      # nobody -> CPU runners are fine
    if cpu_shards == 0:
        heavy, light = shots, []
    if gpu_shards == 0:
        heavy, light = [], shots
    return {"kaggle": _balance(heavy, gpu_shards, "kaggle") if gpu_shards else [],
            "github": _balance(light, cpu_shards, "github") if cpu_shards and light else [],
            "settings": {s["id"]: render_settings_for(s) for s in shots}}   # how to render each shot


def _args(p):
    p.add_argument("job")
    p.add_argument("--kaggle", type=int, default=2, help="GPU shards (Kaggle sessions)")
    p.add_argument("--github", type=int, default=10, help="CPU shards (GitHub Actions runners, max 20)")
    p.add_argument("--speed", action="store_true", help="also print the seconds-per-frame table per shot type")


@register("render-plan", "split a job's shots across Kaggle GPUs and GitHub runners", _args)
def _cmd_render_plan(args) -> int:
    if args.speed:
        for where in ("kaggle", "github"):
            print(f"{where}: type       engine  samples  old s/f  new s/f  saved")
            for r in speed_table(where):
                print(f"        {r['type']:<10} {r['engine']:<7} {r['samples']:>5}  {r['old_s_per_frame']:>7}"
                      f"  {r['new_s_per_frame']:>7}  {r['saved_pct']:>4}%")
    d = jobs.job_dir(args.job)
    f = d / "shots.timed.json"
    if not f.exists():
        print("No shots.timed.json yet: run  tc shots <id>  first")
        return 2
    shots = json.loads(f.read_text(encoding="utf-8"))["shots"]
    plan = plan_shards(shots, args.kaggle, min(args.github, 20))
    (d / "render_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    for where in ("kaggle", "github"):
        for i, g in enumerate(plan[where]):
            print(f"{where}[{i}]: {len(g['shots'])} shots, cost {g['cost']:.0f}, about {g['hours']} h")
    return 0

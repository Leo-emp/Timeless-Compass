# Render farm SAFETY + the shard worker (WS9 task 5). Runs on the cloud machines (Kaggle / GitHub) and on the laptop.
#
#   bundle      one small JSON file with everything a cloud machine needs to know about a job: the shot recipes,
#               the render plan (which machine renders which shot, with which engine/samples) and the scans per
#               shot. `tc render-bundle <job>` writes it to cloud/bundles/<job>.json (no secrets inside).
#   worker      `run_shard()` renders the shots of ONE shard, one by one. After every shot it writes
#               progress.json, so a crash, a killed runner or the end of a 12-hour Kaggle session loses at most
#               the shot in flight (and shot.py itself skips frames that already exist, so even that resumes).
#   checks      every finished shot is checked: missing frames (gaps), black frames (a failed render), and broken
#               files (0 bytes / unreadable = Blender died while writing). Bad frames are deleted and the shot is
#               rendered again (only the missing frames get rendered, because existing frames are skipped).
#   requeue     on the laptop, after downloading all shards' frames: list the shots that still are not OK so they
#               can be sent out again (`tc frames requeue <job>`).
#   join        frames -> one video per shot (ffmpeg, H.264, high quality), refusing to join a broken shot.
#
# Only Pillow + the standard library are needed, so this runs on a bare cloud machine.
import json
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

from tc import jobs
from tc.cli import register
from tc.paths import ROOT

FPS = 24
MIN_FRAMES = 24                         # blender/scenes/shot.py renders at least one second
FRAME_RE = re.compile(r"^f(\d{4,})\.png$")   # Blender names frames f0001.png, f0002.png, ...
BLACK_MEAN, BLACK_MAX = 1.0, 3          # mean brightness <= 1/255 and no pixel above 3/255 = a black frame
WRAPPER = ROOT / "cloud" / "blender_shot.py"
BUNDLES = ROOT / "cloud" / "bundles"


class FrameError(Exception):
    pass


# --------------------------------------------------------------------------------------------- frame checks
def _frame_problem(path: Path) -> str | None:
    """None if the frame is fine, else 'empty' / 'broken' / 'black'."""
    if path.stat().st_size == 0:
        return "empty"
    try:
        from PIL import Image, ImageStat
        with Image.open(path) as im:
            g = im.convert("L")                 # brightness only
            mean = ImageStat.Stat(g).mean[0]
            top = g.getextrema()[1]
    except Exception:
        return "broken"
    # A night shot is dark (mean ~10-30) but never PURE black; a failed render (no camera, no light) is all zeros.
    return "black" if mean <= BLACK_MEAN and top <= BLACK_MAX else None


def expected_frames(recipe: dict) -> int:
    return max(int(recipe.get("frames") or 0), MIN_FRAMES)


def check_frames(frames_dir: Path, expected: int, first: int | None = None) -> dict:
    """Check one shot's frame folder.
    first = number of the shot's first frame (shot.py starts after the cloth pre-roll, so it is not always 1);
    when not given, the lowest frame number found is used.
    Returns {ok, first, count, missing: [numbers], bad: {number: problem}}."""
    d = Path(frames_dir)
    found = {}
    for p in d.iterdir() if d.is_dir() else []:
        m = FRAME_RE.match(p.name)
        if m:
            found[int(m.group(1))] = p
    if first is None:
        first = min(found) if found else 1
    want = range(first, first + expected)
    missing = [n for n in want if n not in found]
    bad = {}
    for n in want:
        if n in found:
            problem = _frame_problem(found[n])
            if problem:
                bad[n] = problem
    count = sum(1 for n in want if n in found)
    return {"ok": not missing and not bad, "first": first, "count": count, "missing": missing, "bad": bad}


def remove_bad_frames(frames_dir: Path, report: dict) -> None:
    """Delete the black/broken frames so the next Blender run renders them again."""
    for n in report["bad"]:
        f = Path(frames_dir) / f"f{n:04d}.png"
        if f.exists():
            f.unlink()


# --------------------------------------------------------------------------------------------- progress ledger
class Progress:
    """progress.json: {shot id: {status, at, note, tries}}. Written atomically after every change."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    def status(self, shot: str) -> str:
        return self.data.get(shot, {}).get("status", "todo")

    def mark(self, shot: str, status: str, note: str = "") -> None:
        e = self.data.setdefault(shot, {"tries": 0})
        e.update(status=status, note=note, at=datetime.now().isoformat(timespec="seconds"))
        if status == "rendering":
            e["tries"] = e.get("tries", 0) + 1
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        tmp.replace(self.path)                           # atomic: a crash never leaves half a progress file


# --------------------------------------------------------------------------------------------- the worker
def _run_blender(cmd: list[str], env: dict, timeout: float | None = None) -> int:
    """Run Blender with its output in a log file next to the shot (owner rule: file logs for every process)."""
    log = Path(env["TC_FRAMES"]).parent / "blender.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"\n==== {datetime.now():%Y-%m-%d %H:%M:%S} {' '.join(cmd)}\n")
        f.flush()
        try:
            return subprocess.run(cmd, env={**os.environ, **env}, stdout=f, stderr=subprocess.STDOUT,
                                  timeout=timeout).returncode
        except subprocess.TimeoutExpired:            # stall watchdog: a hung Blender counts as a failed try
            f.write("TIMEOUT: Blender stalled, killed\n")
            return 124


def shard_shots(bundle: dict, where: str, index: int) -> list[str]:
    return list(bundle["plan"][where][index]["shots"])


def run_shard(bundle: dict, where: str, index: int, out: Path, blender: str, runner=None, retries: int = 2,
              clock=time.monotonic, budget_s: float | None = None, est_s=None, joiner=None) -> dict:
    """Render every shot of plan[where][index] into out/<shot>/frames/. Safe to run again at any time.
    budget_s: stop STARTING new shots when the session is nearly over (Kaggle: 12 h per session), so the frames
              already made are saved by the notebook; the next session continues from progress.json.
    est_s(shot id) -> expected seconds for that shot (from tc/render_plan.py) for the budget check.
    joiner(frames_dir, out_mp4, n): when given, every finished shot is also joined into out/<shot>.mp4 on the
              cloud machine, so the laptop (little disk) downloads one small video per shot, not 100+ PNGs."""
    runner = runner or _run_blender
    out = Path(out)
    prog = Progress(out / "progress.json")
    settings = bundle["plan"].get("settings", {})
    done, failed, paused = [], [], []
    start = clock()
    for sid in shard_shots(bundle, where, index):
        recipe = bundle["recipes"][sid]
        frames_dir = out / sid / "frames"
        n = expected_frames(recipe)
        if prog.status(sid) == "done" and check_frames(frames_dir, n)["ok"]:
            done.append(sid)                         # finished in an earlier run: skip
            continue
        if budget_s is not None and est_s is not None and (clock() - start) + est_s(sid) > budget_s:
            paused.append(sid)                       # not enough time left in this session
            continue
        (out / sid).mkdir(parents=True, exist_ok=True)
        rpath = out / sid / "recipe.json"
        rpath.write_text(json.dumps(recipe, indent=2), encoding="utf-8")
        s = settings.get(sid, {})
        env = {"TC_SHOT": sid, "TC_FRAMES": str(frames_dir), "TC_ENGINE": s.get("engine", "CYCLES"),
               "TC_SAMPLES": str(s.get("samples", 64)), "TC_DENOISER": s.get("denoiser", ""),
               "TC_ADAPTIVE": str(s.get("adaptive_threshold", "")), "TC_GPU": "1" if where == "kaggle" else "0"}
        cmd = [blender, "-b", "--python", str(WRAPPER), "--", str(rpath), str(out / sid), env["TC_SAMPLES"], "anim"]
        ok = False
        for _attempt in range(1 + retries):
            prog.mark(sid, "rendering")
            code = runner(cmd, env)
            report = check_frames(frames_dir, n)
            if report["ok"]:
                ok = True
                break
            remove_bad_frames(frames_dir, report)    # black/broken frames go; the next run renders only the gaps
            prog.mark(sid, "retry", note=f"exit {code}, missing {len(report['missing'])}, bad {len(report['bad'])}")
        if ok:
            if joiner:
                joiner(frames_dir, out / f"{sid}.mp4", n)
            prog.mark(sid, "done", note=f"{n} frames")
            done.append(sid)
        else:
            prog.mark(sid, "failed", note="still missing/black frames after retries; see blender.log")
            failed.append(sid)
    return {"done": done, "failed": failed, "paused": paused}


# --------------------------------------------------------------------------------------------- bundle + requeue
def make_bundle(job: str, job_dir: Path, scans: dict | None = None) -> dict:
    d = Path(job_dir)
    recipes = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted((d / "recipes").glob("*.json"))}
    plan = json.loads((d / "render_plan.json").read_text(encoding="utf-8"))
    return {"job": job, "recipes": recipes, "plan": plan, "scans": scans or {}}


def _all_shots(bundle: dict) -> list[str]:
    return [s for where in ("kaggle", "github") for g in bundle["plan"].get(where, []) for s in g["shots"]]


def find_frames(root: Path, shot: str) -> list[Path]:
    """Every <root>/<shard>/<shot>/frames folder (a re-queued shot may exist in two shards)."""
    return sorted(p for p in Path(root).glob(f"*/{shot}/frames") if p.is_dir())


def joined_video(root: Path, shot: str) -> Path | None:
    """A shot video joined on the cloud machine: <root>/<shard>/<shot>.mp4, trusted only when that shard's
    progress.json says the shot is done (the worker checked every frame before joining)."""
    for mp4 in sorted(Path(root).glob(f"*/{shot}.mp4")):
        if mp4.stat().st_size > 0 and Progress(mp4.parent / "progress.json").status(shot) == "done":
            return mp4
    return None


def shot_ok(root: Path, shot: str, n: int) -> bool:
    return joined_video(root, shot) is not None or any(check_frames(d, n)["ok"] for d in find_frames(root, shot))


def requeue(bundle: dict, root: Path) -> list[str]:
    """Shots with no clean result under root (the downloaded shard outputs): no checked video and no complete,
    clean frame folder. These get rendered again."""
    return [sid for sid in _all_shots(bundle) if not shot_ok(root, sid, expected_frames(bundle["recipes"][sid]))]


# --------------------------------------------------------------------------------------------- join -> video
def join_command(frames_dir: Path, out: Path, first: int, fps: int = FPS) -> list[str]:
    """ffmpeg: f0007.png, f0008.png, ... -> out.mp4 (H.264, near-lossless CRF 14, plays everywhere)."""
    return ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-start_number", str(first),
            "-i", str(Path(frames_dir) / "f%04d.png"), "-c:v", "libx264", "-preset", "slow", "-crf", "14",
            "-pix_fmt", "yuv420p", str(out)]


def join_shot(frames_dir: Path, out: Path, expected: int, fps: int = FPS) -> Path:
    report = check_frames(frames_dir, expected)
    if not report["ok"]:
        raise FrameError(f"{frames_dir}: missing {report['missing'][:5]} bad {sorted(report['bad'])[:5]}")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(join_command(frames_dir, out, report["first"], fps), check=True)
    return out


# --------------------------------------------------------------------------------------------- commands
@register("render-bundle", "write cloud/bundles/<job>.json (recipes + plan + scans) for the cloud machines",
          lambda p: p.add_argument("job"))
def _cmd_bundle(args) -> int:
    from tc.render_cache import _job_scans
    d = jobs.job_dir(args.job)
    if not (d / "render_plan.json").exists():
        print("No render_plan.json yet: run  tc render-plan <job>  first")
        return 2
    b = make_bundle(args.job, d, _job_scans(args.job))
    BUNDLES.mkdir(parents=True, exist_ok=True)
    f = BUNDLES / f"{args.job}.json"
    f.write_text(json.dumps(b, indent=2), encoding="utf-8")
    missing = [sid for sid, r in b["recipes"].items() if r.get("missing")]
    print(f"{f.relative_to(ROOT)}: {len(b['recipes'])} shots" + (f"; NOT renderable yet (library gaps): {missing}" if missing else ""))
    return 1 if missing else 0


def _shard_args(p):
    p.add_argument("bundle", help="cloud/bundles/<job>.json")
    p.add_argument("--where", choices=["kaggle", "github"], required=True)
    p.add_argument("--index", type=int, required=True)
    p.add_argument("--out", required=True, help="output folder for this shard")
    p.add_argument("--blender", required=True)
    p.add_argument("--budget-h", type=float, default=None, help="stop starting shots after this many hours")
    p.add_argument("--join", action="store_true", help="also join each finished shot into <out>/<shot>.mp4")


@register("render-shard", "(cloud machines) render one shard of a bundle, resumable", _shard_args)
def _cmd_shard(args) -> int:
    from tc.render_plan import LOAD_S_PER_SHOT, estimate_seconds
    b = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    secs = {sid: (r.get("frames") or 0) / FPS for sid, r in b["recipes"].items()}
    settings = b["plan"].get("settings", {})
    def est(sid):     # rebuild a minimal shot from the settings so render_plan can estimate it
        t = settings.get(sid, {}).get("type", "medium")
        fake = {"dur": secs[sid], "who": [] if t in ("landscape", "card") else ["x"], "card": t == "card",
                "camera": {"lens": {"wide": 24, "closeup": 85}.get(t, 40)}}
        return estimate_seconds(fake, args.where) + LOAD_S_PER_SHOT
    # stall watchdog: a shot taking 4x its estimate (min 30 min) is killed and retried
    runner = lambda cmd, env: _run_blender(cmd, env, timeout=max(4 * est(env["TC_SHOT"]), 1800))
    res = run_shard(b, args.where, args.index, Path(args.out), args.blender, runner=runner,
                    budget_s=args.budget_h * 3600 if args.budget_h else None, est_s=est,
                    joiner=(lambda fd, mp4, n: join_shot(fd, mp4, n)) if args.join else None)
    print(json.dumps(res))
    return 0 if not res["failed"] else 1


def _frames_args(p):
    p.add_argument("action", choices=["check", "requeue", "join"])
    p.add_argument("job")
    p.add_argument("--root", help="folder with the downloaded shard outputs (default jobs/<id>/render)")


@register("frames", "check / requeue / join a job's rendered frames (missing + black frame detection)", _frames_args)
def _cmd_frames(args) -> int:
    d = jobs.job_dir(args.job)
    root = Path(args.root) if args.root else d / "render"
    b = make_bundle(args.job, d)
    if args.action == "requeue":
        todo = requeue(b, root)
        (d / "requeue.json").write_text(json.dumps(todo, indent=2), encoding="utf-8")
        print(f"{len(todo)} shots to render again -> requeue.json: {todo}")
        return 1 if todo else 0
    bad = 0
    for sid in _all_shots(b):
        n = expected_frames(b["recipes"][sid])
        video = joined_video(root, sid)
        good = [f for f in find_frames(root, sid) if check_frames(f, n)["ok"]]
        if video and args.action == "join":                      # already joined + checked in the cloud
            dest = d / "shots" / f"{sid}.mp4"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(video.read_bytes())
            print(f"{sid}: copied cloud video -> {dest.relative_to(d)}")
            continue
        if video and args.action == "check":
            print(f"{sid}: ok (cloud video)")
            continue
        if not good:
            reps = [check_frames(f, n) for f in find_frames(root, sid)]
            print(f"{sid}: NOT OK " + ("(no frames)" if not reps else
                  f"missing {len(reps[0]['missing'])}, bad {len(reps[0]['bad'])}"))
            bad += 1
            continue
        if args.action == "check":
            print(f"{sid}: ok ({n} frames)")
        else:
            out = join_shot(good[0], d / "shots" / f"{sid}.mp4", n)
            print(f"{sid}: joined -> {out.relative_to(d)}")
    return 1 if bad else 0

# `tc produce <job>`: the MECHANICAL back half of a video, in order, with no human step (rule r20).
# The creative stages (story, script, viewer GO, era, cast, shot plan, scene drawing) are done by the agent first;
# then produce runs:
#   dialogue -> voice -> align -> lipsync -> shotplan -> build -> render -> motion -> mix -> mux
# Each step is skipped when its output is newer than its inputs (re-running costs nothing, and paid quota like
# Fish voices is never spent twice); a step whose input changed is redone with everything after it.
# It stops at the FIRST failing step and says which gate failed.
#   python -m tc produce <job> [--on github|kaggle] [--parts N] [--from STEP]
import json
import subprocess
import sys
from pathlib import Path

from tc import jobs
from tc.cli import register
from tc.paths import ROOT

STEPS = ["dialogue", "voice", "align", "lipsync", "shotplan", "build", "render", "motion", "mix", "mux"]
SHORT_MAX_S = 179.0          # a Short must stay under 3 minutes (YouTube treats longer as a normal video)


def _io(d: Path, film: Path) -> dict[str, tuple[list[Path], list[Path]]]:
    """step -> (inputs, outputs). film = film/src/jobs/<slug>."""
    return {
        "dialogue": ([d / "script.md"], [d / "dialogue.json"]),
        "voice": ([d / "script.md", d / "dialogue.json"], [d / "voice.wav", d / "voice.json"]),
        "align": ([d / "voice.wav"], [d / "timings.json"]),
        "lipsync": ([d / "dialogue.json", d / "voice.json"], [film / "lipsync.json"]),
        "shotplan": ([d / "shotplan.json", d / "timings.json"], [film / "plan.json"]),
        "build": ([film / "plan.json"], [d / "sound.json", d / "music.json"]),
        "render": ([film / "plan.json", film / "scenes.ts"], [d / "film.mp4"]),
        "motion": ([d / "film.mp4"], [d / "qa" / "motion.txt"]),
        "mix": ([d / "voice.wav", d / "sound.json", d / "music.json"], [d / "mix.wav"]),
        "mux": ([d / "film.mp4", d / "mix.wav"], [d / "master.mp4"]),
    }


def plan_steps(d: Path, film: Path) -> list[str]:
    """Steps that must run: the first stale one and EVERYTHING after it (later outputs were built from it)."""
    io = _io(d, film)
    for i, step in enumerate(STEPS):
        ins, outs = io[step]
        if not all(o.exists() for o in outs):
            return STEPS[i:]
        newest_in = max((p.stat().st_mtime for p in ins if p.exists()), default=0)
        if min(o.stat().st_mtime for o in outs) < newest_in:
            return STEPS[i:]
    return []


def run_steps(steps: list[str], run) -> int:
    """Run steps in order; stop at the first that fails (run(step) returns an exit code)."""
    for s in steps:
        code = run(s)
        print(f"[produce] {s}: {'ok' if code == 0 else 'FAILED'}", flush=True)
        if code != 0:
            print(f"[produce] stopped at '{s}' - fix that gate and run tc produce again (finished steps are kept)")
            return code
    return 0


def length_problem(kind: str, seconds: float) -> str | None:
    if kind == "short" and seconds > SHORT_MAX_S:
        return f"the Short is {seconds:.1f} s; it must stay under 3 minutes (cut words, re-voice)"
    return None


def _duration(p: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def _tc(*args: str) -> int:
    return subprocess.run([sys.executable, "-m", "tc", *args]).returncode


def _render(job_id: str, slug: str, d: Path, on: str, parts: int) -> int:
    """Commit + push the job's scene code (the cloud renders from the repo), render, fetch, join (exact frames)."""
    film_dir = f"film/src/jobs/{slug}"
    subprocess.run(["git", "add", film_dir, "film/src/jobs/index.ts"], cwd=ROOT)
    subprocess.run(["git", "commit", "-q", "-m", f"film: {job_id} scenes + plan\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>",
                    "--", film_dir, "film/src/jobs/index.ts"], cwd=ROOT)
    if subprocess.run(["git", "push", "-q", "origin", "HEAD:master"], cwd=ROOT).returncode != 0:
        return 1
    plan = json.loads((ROOT / film_dir / "plan.json").read_text(encoding="utf-8"))
    comp = "Job-" + slug.replace("_", "-")
    if _tc("film", "render", comp, "--frames", str(plan["frames"]), "--parts", str(parts), "--on", on) != 0:
        return 1
    if on != "github":
        print("[produce] Kaggle render started; fetch it with tc film fetch, then run tc produce again")
        return 1
    rid = subprocess.run(["gh", "run", "list", "--workflow", "film-render.yml", "-L", "1", "--json", "databaseId",
                          "-q", ".[0].databaseId"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    if subprocess.run(["gh", "run", "watch", rid, "--exit-status"], cwd=ROOT, capture_output=True).returncode != 0:
        print(f"[produce] cloud render {rid} failed: gh run view {rid} --log-failed")
        return 1
    parts_dir = ROOT / "film" / "out" / f"parts_{slug}"
    if _tc("film", "fetch", rid, "--on", "github", "--to", str(parts_dir)) != 0:
        return 1
    return _tc("film", "join", str(parts_dir), str(d / "film.mp4"), "--frames", str(plan["frames"]))


def _motion(d: Path, film: Path) -> int:
    plan = json.loads((film / "plan.json").read_text(encoding="utf-8"))
    cuts = []
    for s in plan["shots"][1:]:
        n = s["transition_in"].get("frames", 0) // 2
        cuts += list(range(s["start_f"] - n, s["start_f"] + n + 1)) if n else [s["start_f"]]
    beats = [b.get("word_frame", b["frame"] + 6) for s in plan["shots"] for b in s["beats"] if b.get("word_frame", 0) >= 0]
    r = subprocess.run([sys.executable, "-m", "tc", "motion", str(d / "film.mp4"), "--cuts", ",".join(map(str, cuts)),
                        "--beats", ",".join(map(str, beats))], capture_output=True, text=True)
    (d / "qa").mkdir(exist_ok=True)
    (d / "qa" / "motion.txt").write_text(r.stdout, encoding="utf-8")
    print(r.stdout[-600:])
    return 0      # the motion report feeds the scored motion checklist (tc qa ... motion); it does not block by itself


def produce(job_id: str, on: str = "github", parts: int | None = None, start: str | None = None) -> int:
    job = jobs.load_job(job_id)
    d = jobs.job_dir(job.id)
    slug = job.id.lower().replace("-", "_")
    film = ROOT / "film" / "src" / "jobs" / slug
    steps = plan_steps(d, film)
    if start:
        steps = STEPS[STEPS.index(start):]
    if not steps:
        print("[produce] everything is current:", d / "master.mp4")
        return 0
    parts = parts or (6 if job.kind == "short" else 20)

    def run(step: str) -> int:
        if step in ("dialogue", "voice", "align", "lipsync", "shotplan", "mix"):
            code = _tc(step, job.id)
            if code == 0 and step == "align":
                problem = length_problem(job.kind, _duration(d / "voice.wav"))
                if problem:
                    print("[produce]", problem)
                    return 1
            return code
        if step == "build":
            return _tc("filmjob", "build", job.id)
        if step == "render":
            return _render(job.id, slug, d, on, parts)
        if step == "motion":
            return _motion(d, film)
        if step == "mux":
            return _tc("filmjob", "mux", job.id, str(d / "film.mp4"))
        return 1

    return run_steps(steps, run)


def _args(p):
    p.add_argument("job")
    p.add_argument("--on", choices=["github", "kaggle"], default="github")
    p.add_argument("--parts", type=int, default=None)
    p.add_argument("--from", dest="start", choices=STEPS, default=None)


@register("produce", "run the mechanical back half of a job (voices -> render -> mix -> master), skipping current steps", _args)
def _cmd_produce(args) -> int:
    return produce(args.job, args.on, args.parts, args.start)

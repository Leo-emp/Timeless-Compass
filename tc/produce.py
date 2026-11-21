# `tc produce <job>`: the MECHANICAL back half of a video, in order, with no human step (rule r20).
# The creative stages (story, script, viewer GO, era, cast, shot plan, scene drawing) are done by the agent first;
# then produce runs:
#   dialogue -> voice -> align -> length -> lipsync -> shotplan -> build -> render -> motion -> mix -> mux
# Each step is skipped when its output is newer than its inputs (re-running costs nothing, and paid quota like
# Fish voices is never spent twice); a step whose input changed is redone with everything after it.
# It stops at the FIRST failing step and says which gate failed.
#   python -m tc produce <job> [--on github|kaggle] [--parts N] [--from STEP]
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from tc import jobs
from tc.cli import register
from tc.paths import ROOT

STEPS = ["dialogue", "voice", "align", "length", "lipsync", "shotplan", "build", "render", "motion", "mix", "mux"]
SHORT_MAX_S = 179.0          # a Short must stay under 3 minutes (YouTube treats longer as a normal video)


def _io(d: Path, film: Path) -> dict[str, tuple[list[Path], list[Path]]]:
    """step -> (inputs, outputs). film = film/src/jobs/<slug>."""
    return {
        "dialogue": ([d / "script.md"], [d / "dialogue.json"]),
        "voice": ([d / "script.md", d / "dialogue.json"], [d / "voice.wav", d / "voice.json"]),
        "align": ([d / "voice.wav"], [d / "timings.json"]),
        "length": ([d / "voice.wav"], [d / "qa" / "length.ok"]),          # marker written only when the gate passes
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
    same_words = spoken_unchanged(d)
    for i, step in enumerate(STEPS):
        ins, outs = io[step]
        if not all(o.exists() for o in outs):
            return STEPS[i:]
        if step in ("dialogue", "voice") and same_words:
            ins = [p for p in ins if p.name != "script.md"]      # marker-only edits never spend Fish quota again
        newest_in = max((p.stat().st_mtime for p in ins if p.exists()), default=0)
        if min(o.stat().st_mtime for o in outs) < newest_in:
            return STEPS[i:]
    return []


def spoken_hash(script_text: str) -> str:
    """Hash of what is HEARD: markers ({beat} {loop}), tags ([src: ..] [dramatised]) and headings removed."""
    lines = [ln for ln in script_text.splitlines() if not ln.lstrip().startswith("#")]
    t = re.sub(r"\{[a-z_]+\}|\[[^\]]*\]", " ", "\n".join(lines))
    return hashlib.sha256(" ".join(t.split()).encode("utf-8")).hexdigest()


def _spoken_file(d: Path) -> Path:
    return d / "qa" / "spoken.sha256"


def save_spoken(d: Path) -> None:
    """Remember the spoken words the current voice was made from (written after a successful voice step)."""
    _spoken_file(d).parent.mkdir(parents=True, exist_ok=True)
    _spoken_file(d).write_text(spoken_hash((d / "script.md").read_text(encoding="utf-8")), encoding="utf-8")


def spoken_unchanged(d: Path) -> bool:
    f, sc = _spoken_file(d), d / "script.md"
    return f.exists() and sc.exists() and f.read_text(encoding="utf-8").strip() == spoken_hash(sc.read_text(encoding="utf-8"))


def length_step(d: Path, kind: str, duration=None) -> int:
    """The length gate as its own step: writes qa/length.ok ONLY on a pass, so a failed gate runs again next time."""
    marker = d / "qa" / "length.ok"
    marker.unlink(missing_ok=True)
    secs = (duration or _duration)(d / "voice.wav")
    problem = length_problem(kind, secs)
    if problem:
        print("[produce]", problem)
        return 1
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(f"{secs:.2f}\n", encoding="utf-8")
    return 0


def pick_new_run(runs: list[dict], before_id: int | None, sha: str) -> int | None:
    """The render run THIS dispatch started: newer than the newest run before it, and built from our pushed commit."""
    for r in runs:
        if (before_id is None or int(r["databaseId"]) > int(before_id)) and r.get("headSha") == sha:
            return int(r["databaseId"])
    return None


def render_preflight(git) -> str | None:
    """Refuse to dispatch unless the cloud will render exactly our scenes. git(name) -> (returncode, stdout) for:
    pushed (0 when origin/master == HEAD), dirty (diff --quiet HEAD), untracked, remote_diff (diff --quiet origin/master).
    The shared working copy may sit on another branch name; what matters is that origin/master IS our commit."""
    if git("pushed")[0] != 0:
        return "origin/master is not this commit after the push: the cloud would render something else"
    if git("dirty")[0] != 0 or git("untracked")[1].strip():
        return "the job's scene files are not committed (another session may hold the git lock): commit them first"
    if git("remote_diff")[0] != 0:
        return "origin/master does not have these scene files yet (push failed?): the cloud would render old scenes"
    return None


def motion_ok(returncode: int, stdout: str) -> bool:
    """A motion report (with or without problems) is fine; a crash (no summary line) must block."""
    return "motion:" in stdout


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
    paths = [film_dir, "film/src/jobs/index.ts"]
    g = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)
    g("add", *paths)
    if g("diff", "--cached", "--quiet", "--", *paths).returncode != 0:
        msg = f"film: {job_id} scenes + plan\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
        if g("commit", "-q", "-m", msg, "--", *paths).returncode != 0:
            print("[produce] git commit failed (another session may hold the lock); try again")
            return 1
    if g("push", "-q", "origin", "HEAD:master").returncode != 0:      # fast-forward only (git refuses otherwise)
        print("[produce] git push failed (origin/master has commits this copy lacks?)")
        return 1
    g("fetch", "-q", "origin", "master")
    answers = {"pushed": lambda: (0 if g("rev-parse", "origin/master").stdout == g("rev-parse", "HEAD").stdout else 1, ""),
               "dirty": lambda: (g("diff", "--quiet", "HEAD", "--", *paths).returncode, ""),
               "untracked": lambda: (0, g("ls-files", "--others", "--exclude-standard", "--", *paths).stdout),
               "remote_diff": lambda: (g("diff", "--quiet", "origin/master", "HEAD", "--", *paths).returncode, "")}
    problem = render_preflight(lambda n: answers[n]())
    if problem:
        print("[produce]", problem)
        return 1
    sha = g("rev-parse", "HEAD").stdout.strip()

    def runs_now() -> list[dict]:
        out = subprocess.run(["gh", "run", "list", "--workflow", "film-render.yml", "-L", "20", "--json", "databaseId,headSha"],
                             capture_output=True, text=True, cwd=ROOT).stdout
        return json.loads(out or "[]")
    before = max((int(r["databaseId"]) for r in runs_now()), default=None)
    plan = json.loads((ROOT / film_dir / "plan.json").read_text(encoding="utf-8"))
    comp = "Job-" + slug.replace("_", "-")
    if _tc("film", "render", comp, "--frames", str(plan["frames"]), "--parts", str(parts), "--on", on) != 0:
        return 1
    if on != "github":
        print("[produce] Kaggle render started; fetch it with tc film fetch, then run tc produce again")
        return 1
    rid = None
    for _ in range(60):                                   # the new run appears a few seconds after dispatch
        rid = pick_new_run(runs_now(), before, sha)
        if rid:
            break
        time.sleep(5)
    if not rid:
        print("[produce] could not find the render run this dispatch started (gh run list)")
        return 1
    rid = str(rid)
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
    if not motion_ok(r.returncode, r.stdout):
        print("[produce] the motion check crashed:", (r.stderr or "")[-400:])
        return 1                                           # no report is written, so this step runs again
    (d / "qa").mkdir(exist_ok=True)
    (d / "qa" / "motion.txt").write_text(r.stdout, encoding="utf-8")
    print(r.stdout[-600:])
    return 0      # problems feed the scored motion checklist (tc qa ... motion); a report never blocks by itself


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
            if code == 0 and step == "voice":
                save_spoken(d)
            return code
        if step == "length":
            return length_step(d, job.kind)
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

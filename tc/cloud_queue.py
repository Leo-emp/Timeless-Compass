# CLOUD RENDER QUEUE: several sessions submit cloud renders without overwriting each other.
#
# THE OLD WAY (still works, Session D uses it): one shared file cloud/batch.json lists which cloud/requests/*.json to
# render. Two sessions editing it at once = one session's list is lost, or renders the other's requests again.
#
# THE QUEUE: every request is its OWN new file, named so it can never clash:
#     cloud/queue/<YYYYMMDD-HHMMSS>-<session>-<name>.json      e.g. 20261120-023005-c-cannon.json
# A file is never edited after it is submitted (created with "x" mode = fail if it exists). To render again, submit
# again (new time = new file). Runners pick the files up:
#   GitHub  .github/workflows/render-queue.yml   on a push, renders exactly the queue files THAT push added
#           (1 free CPU runner each, up to 20 at once); or by hand with a list of ids.
#   Kaggle  python -m tc queue kaggle <id> [<id> ...]   -> one GPU kernel that renders those requests in turn
#           (Blender is installed once per kernel, so batching several stills saves ~5 minutes each).
# Both run the same command on the machine:  python -m tc queue run cloud/queue/<id>.json --blender <path>
#   1. downloads the scans the scene needs (found by reading the scene's code, or listed in the request),
#   2. renders through cloud/blender_shot.py (GPU when there is one, OpenImageDenoise),
#   3. checks every image (missing / black / broken = failed), runs the optional film finish,
#   4. writes out/_results/<id>.json (status, seconds, images, problems) + out/_results/<id>.log (Blender's output).
#
#   python -m tc queue submit cannon blender/scenes/cannon_test.py out/cannon 64 --session C [--target kaggle]
#   python -m tc queue list
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from tc.cli import register
from tc.paths import ROOT

QUEUE = ROOT / "cloud" / "queue"
TARGETS = ("github", "kaggle")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".exr")


class QueueError(Exception):
    pass


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:40] or "x"


# ------------------------------------------------------------------------------------------- which scans
def scans_for_script(script: str, index: dict, root: Path | None = None) -> list[str]:
    """Scan ids a scene script needs: ids quoted in the script itself + in every blender/lib function it calls
    (followed through helpers, see tc/render_cache.code_closure)."""
    from tc.render_cache import code_closure, scans_in_code
    root = Path(root or ROOT)
    src = (root / script).read_text(encoding="utf-8")
    modules = {f.stem: f.read_text(encoding="utf-8") for f in sorted((root / "blender" / "lib").glob("*.py"))}
    code = [src]
    for mod, func in set(re.findall(r"\b(\w+)\.(\w+)\s*\(", src)):
        if mod in modules:
            code.append(code_closure(f"{mod}.{func}", modules))
    return scans_in_code("\n".join(code), index)


def _group(ids: list[str], index: dict) -> dict:
    """['boulder_01', 'k...sky'] -> {'hdris': [...], 'models': [...]} (the kinds `tc assets fetch` wants)."""
    out = {}
    for i in ids:
        out.setdefault(index.get(i, {}).get("kind") or "models", []).append(i)
    return {k: sorted(v) for k, v in sorted(out.items())}


# ------------------------------------------------------------------------------------------- submit
def make_entry(name: str, script: str, args: list[str], session: str, target: str = "github", scans: dict | None = None,
               finish: dict | None = None, now: datetime | None = None, index: dict | None = None) -> dict:
    from tc.render_cache import fallback_source, load_index
    if target not in TARGETS:
        raise QueueError(f"target must be one of {TARGETS}, not {target!r}")
    if not (Path(ROOT) / script).is_file():
        raise QueueError(f"script not found: {script}")
    index = load_index() if index is None else index
    if scans is None:
        scans = _group(scans_for_script(script, index), index)
    ids = [i for v in scans.values() for i in v]
    # Sketchfab scans can't be downloaded for free on a cloud machine (needs a token) unless they are on R2.
    cloud_missing = sorted(i for i in ids if i in index and fallback_source(index[i]) is None)
    now = now or datetime.now()
    return {"id": f"{now:%Y%m%d-%H%M%S}-{_slug(session)}-{_slug(name)}", "name": name, "session": session,
            "submitted": now.isoformat(timespec="seconds"), "target": target, "script": script, "args": list(args),
            "scans": scans, "cloud_missing": cloud_missing, "finish": finish}


def submit(name: str, script: str, args: list[str], session: str, target: str = "github", scans: dict | None = None,
           finish: dict | None = None, now: datetime | None = None, index: dict | None = None) -> Path:
    """Write the request as a NEW file in cloud/queue/ and return its path. Never overwrites anything."""
    e = make_entry(name, script, args, session, target, scans, finish, now, index)
    QUEUE.mkdir(parents=True, exist_ok=True)
    base, n = e["id"], 1
    while True:
        p = QUEUE / f"{e['id']}.json"
        try:
            with open(p, "x", encoding="utf-8") as f:       # "x" = create, fail if it already exists
                f.write(json.dumps(e, indent=2))
            return p
        except FileExistsError:
            n += 1
            e["id"] = f"{base}-{n}"


def changed_entries(paths: list[str]) -> list[str]:
    """Queue ids among changed file paths (what a push added). Used by the GitHub workflow."""
    out = []
    for p in paths:
        m = re.fullmatch(r"cloud/queue/([0-9]{8}-[0-9]{6}-[a-z0-9-]+)\.json", p.strip().replace("\\", "/"))
        if m:
            out.append(m.group(1))
    return out


# ------------------------------------------------------------------------------------------- run (on the machine)
def _blender(cmd: list[str], env: dict, cwd: Path, log: Path) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"==== {datetime.now():%Y-%m-%d %H:%M:%S} {' '.join(cmd)}\n")
        f.flush()
        return subprocess.run(cmd, env={**os.environ, **env}, cwd=cwd, stdout=f, stderr=subprocess.STDOUT).returncode


def _fetch_scans(entry: dict) -> None:
    """Free scans for this request: R2 when TC_R2_PUBLIC_URL is set, else Poly Haven (tc/render_cache.fetch)."""
    from tc.render_cache import fetch, load_index
    ids = [i for v in (entry.get("scans") or {}).values() for i in v if i not in entry.get("cloud_missing", [])]
    if not ids:
        return
    index = load_index()
    known = [i for i in ids if i in index]
    if known:
        fetch(known, index)
    for kind, v in (entry.get("scans") or {}).items():          # ids the index doesn't know: ask Poly Haven directly
        rest = [i for i in v if i not in index]
        if rest:
            subprocess.run([sys.executable, "-m", "tc", "assets", "fetch", *rest, "--kind", kind], check=False)


def _outputs(entry: dict, cwd: Path) -> list[Path]:
    """Images under the request's output paths (args that start with 'out')."""
    found = []
    for a in entry["args"]:
        if not str(a).startswith("out"):
            continue
        p = cwd / a
        if p.is_dir():
            found += [f for f in sorted(p.rglob("*")) if f.suffix.lower() in IMAGE_EXT]
        elif p.is_file():
            found.append(p)
    return found


def run_entry(entry: dict, blender: str, cwd: Path = ROOT, runner=None, gpu: bool = False, fetch=_fetch_scans) -> dict:
    """Render one queue request on this machine and record the result. Returns the result dict."""
    from tc.render_farm import _frame_problem
    cwd = Path(cwd)
    results = cwd / "out" / "_results"
    log = results / f"{entry['id']}.log"
    runner = runner or (lambda cmd, env, d: _blender(cmd, env, d, log))
    fetch(entry)
    env = {"TC_SCRIPT": str(cwd / entry["script"]), "TC_GPU": "1" if gpu else "0", "TC_ENGINE": "CYCLES",
           "TC_DENOISER": "OPENIMAGEDENOISE", "TC_ADAPTIVE": "0.02"}
    cmd = [blender, "-b", "--python", str(cwd / "cloud" / "blender_shot.py"), "--", *entry["args"]]
    t0 = time.time()
    code = runner(cmd, env, cwd)
    seconds = round(time.time() - t0)
    images = _outputs(entry, cwd)
    problems = {str(p.relative_to(cwd)).replace("\\", "/"): _frame_problem(p) for p in images}
    problems = {k: v for k, v in problems.items() if v}
    f = entry.get("finish")
    if f and (cwd / f["in"]).exists() and not problems:
        subprocess.run([sys.executable, "-m", "tc", "finish", f["in"], f["out"], "--look", f.get("look", "dusk")],
                       cwd=cwd, check=False)
        images.append(cwd / f["out"])
    ok = code == 0 and bool(images) and not problems
    res = {"id": entry["id"], "status": "done" if ok else "failed", "exit": code, "seconds": seconds,
           "gpu": gpu, "images": [str(p.relative_to(cwd)).replace("\\", "/") for p in images if p.exists()],
           "problems": problems if images else {"-": "no image written"}}
    results.mkdir(parents=True, exist_ok=True)
    (results / f"{entry['id']}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    return res


# ------------------------------------------------------------------------------------------- commands
def _args(p):
    p.add_argument("action", choices=["submit", "list", "run", "kaggle"])
    p.add_argument("rest", nargs="*", help="submit: <name> <script> [args...] | run: <queue file> | kaggle: <id>...")
    p.add_argument("--session", help="submit: your session letter (A, B, C...)")
    p.add_argument("--target", default="github", choices=TARGETS)
    p.add_argument("--finish", nargs=2, metavar=("IN", "OUT"), help="submit: film-finish IN -> OUT after rendering")
    p.add_argument("--look", default="dusk", help="submit: finish look")
    p.add_argument("--blender", help="run: path to blender")
    p.add_argument("--gpu", action="store_true", help="run: render on the GPU (Kaggle)")


@register("queue", "cloud render queue: submit / list / run / kaggle (one file per request, no overwrites)", _args)
def _cmd_queue(args) -> int:
    if args.action == "submit":
        if len(args.rest) < 2 or not args.session:
            print("usage: tc queue submit <name> <script> [args...] --session <letter>")
            return 2
        fin = {"in": args.finish[0], "out": args.finish[1], "look": args.look} if args.finish else None
        p = submit(args.rest[0], args.rest[1], args.rest[2:], args.session, args.target, finish=fin)
        e = json.loads(p.read_text(encoding="utf-8"))
        print(f"queued {p.relative_to(ROOT)}  scans: {e['scans'] or 'none'}")
        if e["cloud_missing"]:
            print(f"WARNING: not free to fetch in the cloud without R2: {e['cloud_missing']}")
        print("GitHub: commit + push this file (render-queue.yml renders it).  Kaggle: tc queue kaggle " + e["id"])
        return 0
    if args.action == "list":
        for p in sorted(QUEUE.glob("*.json")):
            e = json.loads(p.read_text(encoding="utf-8"))
            r = ROOT / "out" / "_results" / f"{e['id']}.json"
            status = json.loads(r.read_text(encoding="utf-8"))["status"] if r.exists() else "queued"
            print(f"{e['id']:<45} {e['target']:<7} {status:<7} {e['script']}")
        return 0
    if args.action == "run":
        e = json.loads(Path(args.rest[0]).read_text(encoding="utf-8"))
        res = run_entry(e, args.blender, ROOT, gpu=args.gpu)
        print(json.dumps(res, indent=2))
        return 0 if res["status"] == "done" else 1
    from tc.kaggle_kernel import _username, write_still_kernel
    user = _username()
    if not user:
        print("No Kaggle login: python -m kaggle auth login")
        return 2
    entries = [json.loads((QUEUE / f"{i}.json").read_text(encoding="utf-8")) for i in args.rest]
    folder = write_still_kernel(entries, user)
    print(f"ready: {folder.relative_to(ROOT)}\npush (owner OK first): python -m kaggle kernels push -p {folder.relative_to(ROOT)}")
    return 0

# Jobs: every video is one folder  jobs/<id>/  with a job.json "stage ledger".
# The ledger records which stages are done, so a crash or a new session can resume exactly
# where it stopped: next_stage() returns the first stage that is not "done" (a failed one comes back first).
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from tc import paths
from tc.cli import register

# The autonomous 2D pipeline (spec 2026-11-21 section 6.2), in order. Every gate is automatic (rule r20).
STAGES = ["topic", "packaging", "research", "story", "script", "viewer", "voice", "align", "artdir", "cast",
          "shots", "draw", "stills", "motion", "thumbnail", "render", "mix", "pack", "archive", "results"]
STATUSES = ("todo", "done", "failed")


@dataclass
class Job:
    id: str
    title: str                      # the seed topic text (the real title is picked in "packaging")
    kind: str                       # "long" (12-15 min) or "short" (2 to under 3 min)
    created: str
    stages: dict[str, dict] = field(default_factory=dict)


def _slug(text: str, limit: int = 40) -> str:
    """'The Trap at Salamis!' -> 'the-trap-at-salamis' (ascii, lowercase, hyphens, max 40 chars)."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit].strip("-") or "job"


def job_dir(job_id: str) -> Path:
    return paths.JOBS / job_id


def create_job(seed: str, kind: str = "long", now: datetime | None = None) -> Job:
    if kind not in ("long", "short"):
        raise ValueError(f"kind must be 'long' or 'short', not {kind!r}")
    now = now or datetime.now()
    jid = f"{now:%Y%m%d-%H%M}-{_slug(seed)}"
    stages = {s: {"status": "todo", "at": None, "note": ""} for s in STAGES}
    return Job(id=jid, title=seed, kind=kind, created=now.isoformat(timespec="seconds"), stages=stages)


def save_job(job: Job) -> None:
    """Write job.json atomically (temp file, then replace) so a crash never leaves half a file."""
    d = job_dir(job.id)
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "job.json.tmp"
    tmp.write_text(json.dumps(asdict(job), indent=2), encoding="utf-8")
    os.replace(tmp, d / "job.json")


def load_job(job_id: str) -> Job:
    data = json.loads((job_dir(job_id) / "job.json").read_text(encoding="utf-8"))
    job = Job(**data)
    for s in STAGES:                 # a job made by an older version gets any new stages as "todo"
        job.stages.setdefault(s, {"status": "todo", "at": None, "note": ""})
    return job


def mark(job: Job, stage: str, status: str, note: str = "", changed: bool = True) -> Job:
    """Set a stage's status. When a stage is (re)done with changed output, every LATER stage is reset to
    "todo", because it was built from the old output (e.g. re-voicing makes old timings and shots stale).
    Pass changed=False when the stage was re-checked but its output is identical."""
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}; stages are {STAGES}")
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}")
    job.stages[stage] = {"status": status, "at": datetime.now().isoformat(timespec="seconds"), "note": note}
    if status == "done" and changed:
        for later in STAGES[STAGES.index(stage) + 1:]:
            if job.stages.get(later, {}).get("status") != "todo":
                job.stages[later] = {"status": "todo", "at": None, "note": f"reset: {stage} was redone"}
    return job


def next_stage(job: Job) -> str | None:
    for s in STAGES:
        if job.stages.get(s, {}).get("status") != "done":
            return s
    return None


# ---------------- commands ----------------
@register("new", "start a new video job", lambda p: (p.add_argument("seed"), p.add_argument("--short", action="store_true")))
def _cmd_new(args) -> int:
    job = create_job(args.seed, "short" if args.short else "long")
    save_job(job)
    print(job.id)
    return 0


@register("status", "show a job's stages", lambda p: p.add_argument("job"))
def _cmd_status(args) -> int:
    job = load_job(args.job)
    print(f"{job.id}  ({job.kind})  next: {next_stage(job) or 'all Plan 1 stages done'}")
    for s in STAGES:
        st = job.stages[s]
        print(f"  {s:<10} {st['status']:<7} {st['note']}")
    return 0


def _mark_args(p):
    p.add_argument("job"); p.add_argument("stage", choices=STAGES)
    p.add_argument("--status", default="done", choices=STATUSES); p.add_argument("--note", default="")


@register("mark", "set a stage's status by hand (e.g. research done)", _mark_args)
def _cmd_mark(args) -> int:
    job = load_job(args.job)
    mark(job, args.stage, args.status, args.note); save_job(job)
    print(f"{args.stage}: {args.status}")
    return 0

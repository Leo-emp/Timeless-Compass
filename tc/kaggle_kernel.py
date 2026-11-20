# Kaggle kernel builder (WS9 task 1): turn the notebook template cloud/kaggle/render_shard.py into a ready-to-push
# Kaggle notebook for ONE GPU shard of a job.
#
#   python -m tc kaggle <job> --shard 0            -> cloud/kaggle/out/<slug>/{tc-render.ipynb, kernel-metadata.json}
#   python -m tc kaggle <job> --shard 0 --resume   -> same, plus "attach the last session's output" (resume)
#
# Then (owner approved, Kaggle token in ~/.kaggle/kaggle.json):  kaggle kernels push -p cloud/kaggle/out/<slug>
# This file only WRITES the files; it never pushes or starts anything.
#
# The template is a plain .py file split into notebook cells at every "# %%" line (the same convention VS Code and
# Jupytext use), so it is easy to read and diff. "{{NAME}}" placeholders are filled in here.
import json
import os
import re
from pathlib import Path

from tc.cli import register
from tc.paths import ROOT

TEMPLATE = ROOT / "cloud" / "kaggle" / "render_shard.py"
OUT = ROOT / "cloud" / "kaggle" / "out"            # git-ignored: generated per job
REPO = "https://github.com/Leo-emp/Timeless-Compass.git"
BRANCH = "cinematic-agent"
BUDGET_H = 11.0                                     # Kaggle stops a session at 12 h; leave 1 h to finish + save
SLUG_MAX = 50                                       # Kaggle kernel slugs are short


def slug(job: str, index: int) -> str:
    """'20261119-1824-xerxes-throne-at-salamis', 0 -> 'tc-20261119-1824-xerxes-throne-at-salamis-k0' (<= 50)."""
    tail = f"-k{index}"
    body = re.sub(r"[^a-z0-9-]+", "-", f"tc-{job}".lower()).strip("-")
    return body[:SLUG_MAX - len(tail)].rstrip("-") + tail


def _cells(text: str) -> list[dict]:
    """Split the template at '# %%' lines into notebook cells ('# %% [markdown]' = a text cell)."""
    cells, kind, buf = [], None, []

    def flush():
        if kind is None:
            return
        lines = buf[:]
        while lines and not lines[-1].strip():
            lines.pop()
        if kind == "markdown":
            lines = [ln[2:] if ln.startswith("# ") else ln.lstrip("#") for ln in lines]
            cells.append({"cell_type": "markdown", "metadata": {}, "source": _src(lines)})
        else:
            cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                          "source": _src(lines)})

    for line in text.splitlines():
        if line.startswith("# %%"):
            flush()
            kind, buf = ("markdown" if "[markdown]" in line else "code"), []
        else:
            buf.append(line)
    flush()
    return cells


def _src(lines: list[str]) -> list[str]:
    return [ln + "\n" for ln in lines[:-1]] + lines[-1:] if lines else []


def notebook(job: str, index: int, budget_h: float = BUDGET_H, r2_public_url: str = "") -> dict:
    text = TEMPLATE.read_text(encoding="utf-8")
    for k, v in {"JOB": job, "INDEX": str(index), "REPO": REPO, "BRANCH": BRANCH, "BUDGET_H": str(budget_h),
                 "R2_PUBLIC_URL": r2_public_url}.items():
        text = text.replace("{{" + k + "}}", v)
    return {"cells": _cells(text), "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3",
            "language": "python"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}


def metadata(job: str, index: int, username: str, resume_from: str | None = None) -> dict:
    s = slug(job, index)
    return {"id": f"{username}/{s}", "title": s, "code_file": "tc-render.ipynb", "language": "python",
            "kernel_type": "notebook", "is_private": True,      # private: only the owner sees it
            "enable_gpu": True, "enable_internet": True,        # free T4/P100 GPU + internet to clone/download
            "dataset_sources": [], "competition_sources": [],
            "kernel_sources": [resume_from] if resume_from else []}   # last session's output -> /kaggle/input/


def write_kernel(job: str, index: int, username: str, out_root: Path = OUT, resume_from: str | None = None,
                 r2_public_url: str = "") -> Path:
    folder = Path(out_root) / slug(job, index)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "tc-render.ipynb").write_text(json.dumps(notebook(job, index, r2_public_url=r2_public_url), indent=1),
                                            encoding="utf-8")
    (folder / "kernel-metadata.json").write_text(json.dumps(metadata(job, index, username, resume_from), indent=2),
                                                 encoding="utf-8")
    return folder


STILL_TEMPLATE = ROOT / "cloud" / "kaggle" / "render_still.py"


def write_still_kernel(entries: list[dict], username: str, out_root: Path = OUT, r2_public_url: str = "") -> Path:
    """A Kaggle GPU 'script' kernel that renders cloud-queue requests (tc/cloud_queue.py) one after another.
    The requests are written INTO the script (as a JSON string), so they don't have to be pushed first."""
    first = re.sub(r"[^a-z0-9-]+", "-", entries[0]["id"].lower())
    tail = f"-n{len(entries)}"
    name = ("tc-still-" + first)[:SLUG_MAX - len(tail)].rstrip("-") + tail
    text = STILL_TEMPLATE.read_text(encoding="utf-8")
    for k, v in {"ENTRIES_JSON": repr(json.dumps(entries)), "REPO": REPO, "BRANCH": BRANCH,
                 "R2_PUBLIC_URL": r2_public_url}.items():
        text = text.replace("{{" + k + "}}", v)
    folder = Path(out_root) / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "render_still.py").write_text(text, encoding="utf-8")
    meta = {"id": f"{username}/{name}", "title": name, "code_file": "render_still.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
            "dataset_sources": [], "competition_sources": [], "kernel_sources": []}
    (folder / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return folder


def _kaggle_config_view() -> str:
    """Output of `python -m kaggle config view` (user name + settings; it never prints the login token)."""
    import subprocess
    import sys
    try:
        return subprocess.run([sys.executable, "-m", "kaggle", "config", "view"], capture_output=True, text=True,
                              timeout=60).stdout
    except Exception:
        return ""


def _username(config_view=_kaggle_config_view) -> str:
    """The Kaggle user name (not secret). Looked for in this order:
    1. KAGGLE_USERNAME (environment / .env)
    2. ~/.kaggle/kaggle.json (old-style API token file; only its "username" field is used)
    3. `kaggle config view` (the browser login `kaggle auth login` stores the user there)."""
    if os.environ.get("KAGGLE_USERNAME"):
        return os.environ["KAGGLE_USERNAME"]
    f = Path.home() / ".kaggle" / "kaggle.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8")).get("username", "")
    m = re.search(r"^- username:\s*(\S+)", config_view() or "", flags=re.M)
    return m.group(1) if m and m.group(1) != "None" else ""


def _args(p):
    p.add_argument("job")
    p.add_argument("--shard", type=int, required=True, help="kaggle shard index from the render plan")
    p.add_argument("--resume", action="store_true", help="attach this shard's previous session output")


@register("kaggle", "write a ready-to-push Kaggle GPU notebook for one render shard (does not push)", _args)
def _cmd_kaggle(args) -> int:
    user = _username()
    if not user:
        print("No Kaggle user yet. Owner steps: cloud/README.md 'Kaggle' (phone-verify, API token -> ~/.kaggle/kaggle.json)")
        return 2
    resume = f"{user}/{slug(args.job, args.shard)}" if args.resume else None
    folder = write_kernel(args.job, args.shard, user, resume_from=resume,
                          r2_public_url=os.environ.get("TC_R2_PUBLIC_URL", ""))
    print(f"ready: {folder.relative_to(ROOT)}")
    print(f"push (owner OK first):  kaggle kernels push -p {folder.relative_to(ROOT)}")
    print(f"status:                 kaggle kernels status {user}/{slug(args.job, args.shard)}")
    print(f"download output:        kaggle kernels output {user}/{slug(args.job, args.shard)} -p jobs/{args.job}/render")   # lands as render/kaggle-{args.shard}/
    return 0

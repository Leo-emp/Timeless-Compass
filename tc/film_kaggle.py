# KAGGLE side of film renders: the second free render farm next to GitHub (spec 6.10).
# A private Kaggle notebook (free CPUs, internet on) installs Node + the film engine, renders its frame ranges with
# film/render-part.mjs and leaves the parts in /kaggle/working/parts. `tc film fetch <slug> --on kaggle` downloads them.
#
#   python -m tc film render FleetTest --frames 192 --parts 2 --on kaggle     (writes + pushes the notebook)
#   kaggle kernels status <user>/<slug>                                        (wait for "complete")
#   python -m tc film fetch <user>/<slug> --on kaggle --to film/out/kg
#
# The login token stays in ~/.kaggle (never in the repo). Nothing secret goes into the notebook.
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from tc.config import load_env
from tc.paths import ROOT

REPO = "https://github.com/Leo-emp/Timeless-Compass.git"
OUT = ROOT / "film" / "out" / "kaggle"            # git-ignored (film/out/)
SLUG_MAX = 50

# Chrome (used by Remotion) needs these system libraries; Kaggle's image may lack some of them.
CHROME_LIBS = ("libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 "
               "libxfixes3 libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2")


def film_slug(comp: str, ranges: list[tuple[int, int]]) -> str:
    """'FleetTestLong', [(20000, 21599)] -> 'tc-film-fleettestlong-20000' (short, lower-case, Kaggle-safe)."""
    body = re.sub(r"[^a-z0-9-]+", "-", f"tc-film-{comp}".lower()).strip("-")
    tail = f"-{ranges[0][0]}"
    return body[:SLUG_MAX - len(tail)].rstrip("-") + tail


def _cell(src: str) -> dict:
    lines = src.strip("\n").split("\n")
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": [ln + "\n" for ln in lines[:-1]] + lines[-1:]}


def film_notebook(comp: str, ranges: list[tuple[int, int]], repo: str = REPO, ref: str = "master") -> dict:
    """The Jupyter notebook Kaggle runs. Cell 1 fails fast with a clear message if internet is off."""
    # the notebook runs shell commands built from these values: allow only safe names and numbers
    if not re.fullmatch(r"[A-Za-z0-9_-]+", comp) or not re.fullmatch(r"[A-Za-z0-9_./-]+", ref):
        raise ValueError(f"unsafe composition or ref name: {comp!r} {ref!r}")
    ranges = [(int(a), int(b)) for a, b in ranges]
    renders = "\n".join(
        f'run("cd /kaggle/working/tc/film && CONCURRENCY=4 node render-part.mjs {comp} {a} {b} /kaggle/working/parts")'
        for a, b in ranges)
    cells = [
        _cell('''# 1. internet check: without it nothing below can work (Kaggle: Settings -> Internet on)
import urllib.request
try:
    urllib.request.urlopen("https://github.com", timeout=20)
except Exception as e:
    raise RuntimeError("Kaggle internet is off or blocked - turn it on for this notebook") from e
print("internet ok")'''),
        _cell('''# 2. a tiny helper that runs a shell command and stops the notebook if it fails
import subprocess
def run(cmd):
    print("$", cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True)'''),
        _cell(f'''# 3. Node 22 + the libraries headless Chrome needs
run("curl -fsSL https://deb.nodesource.com/setup_22.x | bash - > /dev/null")
run("apt-get install -y -q nodejs {CHROME_LIBS} > /dev/null")
run("node --version")'''),
        _cell(f'''# 4. the film engine at the exact commit branch we render from
run("rm -rf /kaggle/working/tc && git clone --depth 1 --branch {ref} {repo} /kaggle/working/tc")
run("cd /kaggle/working/tc/film && npm ci --no-audit --no-fund && npx remotion browser ensure")'''),
        _cell(f'''# 5. render every range given to this notebook; parts stay in /kaggle/working/parts (kernel output)
{renders}
run("rm -rf /kaggle/working/tc")   # keep only the parts in the output
run("ls -la /kaggle/working/parts")'''),
    ]
    return {"cells": cells, "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
            "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}


def film_metadata(username: str, slug: str) -> dict:
    return {"id": f"{username}/{slug}", "title": slug, "code_file": "film-render.ipynb", "language": "python",
            "kernel_type": "notebook", "is_private": True, "enable_gpu": False, "enable_internet": True,
            "dataset_sources": [], "competition_sources": [], "kernel_sources": []}


def write_film_kernel(comp: str, ranges: list[tuple[int, int]], username: str, out_dir: Path = OUT, ref: str = "master") -> Path:
    slug = film_slug(comp, ranges)
    d = Path(out_dir) / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "film-render.ipynb").write_text(json.dumps(film_notebook(comp, ranges, ref=ref), indent=1), encoding="utf-8")
    (d / "kernel-metadata.json").write_text(json.dumps(film_metadata(username, slug), indent=2), encoding="utf-8")
    return d


def kaggle_username() -> str:
    """Kaggle user name (not secret): KAGGLE_USERNAME from the environment or .env, else `kaggle config view`."""
    name = os.environ.get("KAGGLE_USERNAME") or load_env().get("KAGGLE_USERNAME")
    if name:
        return name
    out = subprocess.run([sys.executable, "-m", "kaggle", "config", "view"], capture_output=True, text=True, timeout=60).stdout
    m = re.search(r"username:\s*(\S+)", out)
    if not m:
        raise RuntimeError("Kaggle user name not found: set KAGGLE_USERNAME in .env")
    return m.group(1)


def push_film_kernel(comp: str, ranges: list[tuple[int, int]], ref: str = "master") -> str:
    """Write the notebook and push it to Kaggle (this starts it). Returns '<user>/<slug>'."""
    user = kaggle_username()
    d = write_film_kernel(comp, ranges, user, ref=ref)
    subprocess.run([sys.executable, "-m", "kaggle", "kernels", "push", "-p", str(d)], check=True)
    return f"{user}/{d.name}"

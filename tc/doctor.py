# `tc doctor`: one command that checks everything the system needs before making a video.
# Each check is ✓ or ✗. "Required" checks failing -> exit code 1. Optional ones only warn.
# All outside-world lookups are passed in as functions, so tests can fake them.
import importlib.util
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from tc import http
from tc.cli import register
from tc.config import Config, get_config

REPO = Path(__file__).resolve().parent.parent
FILM_ENGINE = REPO / "film" / "node_modules" / "remotion"          # installed by `npm install` in film/
KAGGLE_CREDS = [Path.home() / ".kaggle" / "kaggle.json", Path.home() / ".kaggle" / "credentials.json"]
MIN_DISK_GB = 10.0


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


def _disk_free_gb() -> float:
    return shutil.disk_usage("C:/").free / 1e9


def _can_import(mod: str) -> bool:
    # faster-whisper lives in the USER site-packages, so check with a plain (non-isolated) python
    r = subprocess.run([sys.executable, "-c", f"import {mod}"], capture_output=True)
    return r.returncode == 0


def _azure_ok(cfg: Config) -> bool:
    try:
        http.get_json(f"https://{cfg.azure_region}.tts.speech.microsoft.com/cognitiveservices/voices/list",
                      {"Ocp-Apim-Subscription-Key": cfg.azure_key or ""}, timeout=30)
        return True
    except (http.HttpError, ValueError):
        return False


def _node_version() -> str:
    """'v24.14.0' from `node --version`, or '' if node is missing."""
    try:
        return subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _gh_logged_in() -> bool:
    """True when the GitHub CLI is logged in (needed to start cloud renders)."""
    try:
        return subprocess.run(["gh", "auth", "status"], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _node_major(v: str) -> int:
    try:
        return int(v.lstrip("v").split(".")[0])
    except ValueError:
        return 0


def run_checks(cfg: Config | None = None, which=shutil.which, disk_free_gb=_disk_free_gb,
               can_import=_can_import, exists=lambda p: Path(p).exists(), azure_ok=_azure_ok,
               node_version=_node_version, gh_ok=_gh_logged_in) -> list[Check]:
    cfg = cfg or get_config()
    v = sys.version_info
    checks = [
        Check("python >= 3.12", v >= (3, 12), f"{v.major}.{v.minor}"),
        Check("ffmpeg on PATH", bool(which("ffmpeg")), which("ffmpeg") or "missing"),
        Check("curl on PATH", bool(which("curl")), which("curl") or "missing"),
        Check("faster-whisper importable", can_import("faster_whisper"), "word timings"),
    ]
    nv = node_version()
    checks += [
        Check("node >= 22", _node_major(nv) >= 22, nv or "missing"),                 # the 2D film engine runs on Node
        Check("npm on PATH", bool(which("npm")), which("npm") or "missing"),
        Check("gh CLI logged in", gh_ok(), "starts GitHub cloud renders"),
        Check("film engine installed", exists(FILM_ENGINE), "run `npm install` in film/"),
        Check("kaggle credentials", any(exists(p) for p in KAGGLE_CREDS), "second render farm", required=False),
    ]
    has_azure = bool(cfg.azure_key and cfg.azure_region)
    checks.append(Check("Azure Speech key + region", has_azure, cfg.azure_region or "missing in .env"))
    if has_azure:
        checks.append(Check("Azure Speech reachable", azure_ok(cfg), cfg.voice))
    checks.append(Check("YouTube Data API key", bool(cfg.youtube_key), "needed for `tc topics`", required=False))
    free = disk_free_gb()
    checks.append(Check(f"free disk on C: >= {MIN_DISK_GB:.0f} GB", free >= MIN_DISK_GB, f"{free:.1f} GB free", required=False))
    return checks


def exit_code(checks: list[Check]) -> int:
    return 1 if any(c.required and not c.ok for c in checks) else 0


@register("doctor", "check tools, keys and disk space")
def _cmd_doctor(args) -> int:
    checks = run_checks()
    for c in checks:
        mark = "OK " if c.ok else ("ERR" if c.required else "warn")
        print(f"[{mark}] {c.name}: {c.detail}")
    return exit_code(checks)

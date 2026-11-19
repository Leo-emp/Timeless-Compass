# Settings for the whole system, in one place.
# Secret keys come from the .env file (git-ignored). Values are NEVER printed anywhere.
import os
from dataclasses import dataclass
from pathlib import Path

from tc import paths


def load_env(path: Path | None = None) -> dict[str, str]:
    """Read KEY=VALUE lines from a .env file.
    Skips blank lines and # comments, strips surrounding quotes and Windows \\r line endings."""
    path = path or paths.ENV_FILE
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().rstrip("\r")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


@dataclass
class Config:
    # ---- narration (owner: narrator only, Lewis; Jimmie HD Flash is the one-switch alternative) ----
    voice: str = "en-US-LewisMultilingualNeural"
    voice_rate: str = "-4%"                      # near-natural pace
    # ---- script length + retention rules (spec 6.0 / Global Constraints) ----
    words_per_min: int = 150
    long_words: tuple[int, int] = (1500, 1800)  # 10-12 minute video
    short_words: tuple[int, int] = (110, 150)   # 45-60 second Short
    rehook_max_s: int = 90                      # an open loop / re-hook at least every 90 s
    # ---- pacing ----
    shot_s: tuple[float, float] = (3.0, 7.0)    # visual change every 3-7 s
    hold_max_s: float = 8.0                     # longer only if a shot is flagged "hold"
    # ---- packaging ----
    title_max: int = 60
    # ---- keys (None when missing) ----
    azure_key: str | None = None
    azure_region: str | None = None
    youtube_key: str | None = None


def get_config(env_file: Path | None = None) -> Config:
    """Build the settings: defaults, then keys from .env, then TC_VOICE from the environment if set."""
    env = load_env(env_file)
    cfg = Config(
        azure_key=env.get("AZURE_SPEECH_KEY") or None,
        azure_region=env.get("AZURE_SPEECH_REGION") or None,
        youtube_key=env.get("YOUTUBE_API_KEY") or None,
    )
    voice = os.environ.get("TC_VOICE") or env.get("TC_VOICE")
    if voice:
        cfg.voice = voice
    return cfg

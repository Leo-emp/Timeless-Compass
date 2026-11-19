# SHOT MATCHING: make every shot of a scene look like it was graded by one colourist (WS12, Session D).
# Real films are shot over many days and lights; the colourist's first job is to MATCH the shots of a scene to
# its hero shot before any creative look goes on top. Our shots are rendered separately (different cameras,
# lights, samples, even machines), so their exposure and colour drift too. Here, per scene (same 'where'):
#   1. measure each shot (a middle frame): black point (p2), median, white point (p98) of brightness, the colour
#      CAST in the midtones (where faces and sand sit: mean r/g/b divided by their average), saturation
#   2. the hero = the longest shot of that place (or the one marked "hero": true in the shot list)
#   3. correct every other shot toward its hero: a tone curve mapping black/median/white onto the hero's,
#      per-channel gains that cancel the cast difference, a saturation nudge
#   4. CLAMPED (MAX_STOPS, MAX_CAST, MAX_SAT): matching must never erase an intended mood (a deliberately dark
#      or firelit shot); it only removes accidental drift.
# tc edit applies the filter to each shot before the transitions and the film look.
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

MAX_STOPS = 1.0          # at most +-1 stop of exposure correction
MAX_CAST = 0.12          # at most +-12% per colour channel
MAX_SAT = 0.2            # at most +-20% saturation


def _load(path) -> np.ndarray:
    """RGB float array 0..1 from an image, or from the middle frame of a video."""
    p = Path(path)
    if p.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm"):
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                   capture_output=True, text=True, check=True).stdout.strip() or 0)
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "mid.png"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{dur / 2:.2f}", "-i", str(p), "-frames:v", "1",
                            "-vf", "scale=480:-2", str(f)], check=True)
            return np.asarray(Image.open(f).convert("RGB"), dtype=np.float32) / 255
    im = Image.open(p).convert("RGB")
    im.thumbnail((480, 480))
    return np.asarray(im, dtype=np.float32) / 255


def stats(path) -> dict:
    a = _load(path)
    lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    p2, med, p98 = (float(np.percentile(lum, q)) for q in (2, 50, 98))
    mid = (lum > np.percentile(lum, 25)) & (lum < np.percentile(lum, 75))   # midtones: faces, sand, cloth
    m = a[mid].mean(0) if mid.any() else a.reshape(-1, 3).mean(0)
    cast = m / (m.mean() + 1e-6)
    sat = _sat(a)
    small = a[::max(1, a.shape[0] // 36), ::max(1, a.shape[1] // 64)]          # tiny copy: lets us predict
    return {"p2": p2, "median": med, "p98": p98, "cast": [float(c) for c in cast], "sat": sat,
            "px": small.reshape(-1, 3).tolist()}


def _sat(a) -> float:
    a = np.asarray(a, dtype=np.float32)
    mx, mn = a.max(-1), a.min(-1)
    return float(((mx - mn) / (mx + 1e-6)).mean())


def correction(src: dict, ref: dict) -> dict:
    """How to move shot `src` toward hero `ref` (clamped). stops = exposure change at the median; curve =
    (in, out) points for black / median / white; gains = per-channel multipliers; sat = saturation factor."""
    stops = float(np.clip(np.log2((ref["median"] + 1e-4) / (src["median"] + 1e-4)), -MAX_STOPS, MAX_STOPS))
    k = 2 ** stops
    # target points, limited by the exposure clamp: never more than the clamped gain at the median
    lo = float(np.clip(ref["p2"], 0.0, 0.3)); hi = float(np.clip(ref["p98"], 0.6, 1.0))
    med_out = float(np.clip(src["median"] * k, 0.02, 0.98))
    curve = [(float(np.clip(src["p2"], 0, 0.3)), lo), (float(src["median"]), med_out), (float(np.clip(src["p98"], 0.5, 1.0)), hi)]
    gains = [float(np.clip(r / (s + 1e-6), 1 - MAX_CAST, 1 + MAX_CAST)) for s, r in zip(src["cast"], ref["cast"])]
    # saturation AFTER the cast is fixed (removing a cast already brings colour back): predict it on the tiny copy
    after = _sat(np.clip(np.asarray(src["px"]) * np.array(gains), 0, 1)) if src.get("px") else src["sat"]
    sat = float(np.clip(ref["sat"] / (after + 1e-6), 1 - MAX_SAT, 1 + MAX_SAT))
    return {"stops": stops, "curve": curve, "gains": gains, "sat": sat}


def _curve_str(curve) -> str:
    pts = [(0.0, 0.0)] + sorted(curve) + [(1.0, 1.0)]
    clean, last_x, last_y = [], -1.0, -1.0
    for x, y in pts:                                         # strictly rising x, never-falling y (a valid curve)
        x = min(max(x, 0.0), 1.0); y = min(max(y, last_y if last_y >= 0 else 0.0), 1.0)
        if x <= last_x + 0.01:
            continue
        clean.append((x, y)); last_x, last_y = x, y
    return " ".join(f"{x:.3f}/{y:.3f}" for x, y in clean)


def filter_for(c: dict, eps=0.01) -> str:
    """ffmpeg filter (RGB, after format=gbrp) for a correction; '' when nothing needs fixing."""
    parts = []
    if any(abs(y - x) > eps for x, y in c["curve"]):
        parts.append(f"curves=all='{_curve_str(c['curve'])}'")
    g = c["gains"]
    if any(abs(x - 1) > eps for x in g):
        parts.append(f"colorchannelmixer=rr={g[0]:.3f}:gg={g[1]:.3f}:bb={g[2]:.3f}")
    if abs(c["sat"] - 1) > eps:
        parts.append(f"format=yuv444p,eq=saturation={c['sat']:.3f},format=gbrp")
    return ",".join(parts)


def heroes(shots: list[dict]) -> dict:
    """place -> hero shot id: the one marked "hero": true, else the longest shot of that place."""
    out = {}
    for where in {s.get("where") or "" for s in shots}:
        group = [s for s in shots if (s.get("where") or "") == where]
        marked = [s for s in group if s.get("hero")]
        out[where] = (marked[0] if marked else max(group, key=lambda s: float(s.get("dur") or 0)))["id"]
    return out


def match_filters(shots: list[dict], have: dict) -> dict:
    """shot id -> matching filter ('' for heroes and shots without a render)."""
    hs = heroes(shots)
    cache = {}
    def st(sid):
        if sid not in cache:
            cache[sid] = stats(have[sid])
        return cache[sid]
    out = {}
    for s in shots:
        sid, hero = s["id"], hs[s.get("where") or ""]
        if sid == hero or sid not in have or hero not in have:
            out[sid] = ""
            continue
        out[sid] = filter_for(correction(st(sid), st(hero)))
    return out

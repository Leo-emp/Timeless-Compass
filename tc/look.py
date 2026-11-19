# LOOK CHECK: measure a render against the quality reference with NUMBERS, not only by eye.
# (Idea from the open-source "reference look calibration" skill: compare tone and colour statistics.)
# For each image: brightness, contrast (spread of tones), saturation, warmth (orange vs blue), deep-shadow share
# (film looks keep real blacks), and highlight level. Our render passes a metric when it sits inside the range the
# reference frames span (plus a small margin). The reference is a quality RULER only (owner rule r9: never copy).
#   python -m tc look spike/lib_stills/hero.png --ref spike/ref_memory
from pathlib import Path

import numpy as np

from tc.cli import register

METRICS = ("brightness", "contrast", "saturation", "warmth", "shadows", "highlights")
TOLERANCE = {"brightness": 0.03, "contrast": 0.04, "saturation": 0.03, "warmth": 0.03, "shadows": 0.03, "highlights": 0.03}


def stats(img: np.ndarray) -> dict:
    """img: H x W x 3 floats in 0..1 (display colours)."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    mx, mn = img.max(axis=2), img.min(axis=2)
    return {
        "brightness": float(y.mean()),
        "contrast": float(np.percentile(y, 95) - np.percentile(y, 5)),
        "saturation": float(((mx - mn) / (mx + 1e-4)).mean()),
        "warmth": float(((r - b) / (r + g + b + 1e-4)).mean()),
        "shadows": float((y < 0.08).mean()),
        "highlights": float(np.percentile(y, 99)),
    }


def similar(ours: dict, refs: list[dict], k: int | None) -> list[dict]:
    """The k reference frames with the closest MOOD (colour character: warmth + saturation). Brightness is left out
    on purpose, so an over-bright dusk shot is still judged against dusk shots, not matched to noon ones."""
    if not k or k >= len(refs):
        return refs
    return sorted(refs, key=lambda r: (r["warmth"] - ours["warmth"]) ** 2 + (r["saturation"] - ours["saturation"]) ** 2)[:k]


def compare(ours: dict, refs: list[dict], k: int | None = None) -> dict:
    refs = similar(ours, refs, k)
    out = {}
    for m in METRICS:
        vals = [r[m] for r in refs]
        lo, hi = min(vals), max(vals)
        pad = 0.15 * (hi - lo) + TOLERANCE[m]
        v = ours[m]
        verdict = "ok" if lo - pad <= v <= hi + pad else ("too high" if v > hi + pad else "too low")
        out[m] = {"ours": round(v, 3), "ref_min": round(lo, 3), "ref_max": round(hi, 3), "verdict": verdict}
    return out


def score(report: dict) -> int:
    return round(100 * sum(1 for r in report.values() if r["verdict"] == "ok") / len(report))


def load(path, width=480) -> np.ndarray:
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im = im.resize((width, max(1, round(im.height * width / im.width))))
    return np.asarray(im, dtype=np.float32) / 255.0


def _args(p):
    p.add_argument("renders", nargs="+")
    p.add_argument("--ref", default="spike/ref_memory", help="folder of reference frames (quality ruler)")


@register("look", "measure renders against the reference look (tone, contrast, colour)", _args)
def _cmd_look(args) -> int:
    ref_files = sorted(f for f in Path(args.ref).glob("*.jpg") if "sheet" not in f.name)
    refs = [stats(load(f)) for f in ref_files]
    # drop near-black title/fade frames: they are not shots
    refs = [r for r in refs if r["brightness"] > 0.04] or refs
    worst = 100
    for f in args.renders:
        rep = compare(stats(load(f)), refs, k=6)              # judged against the 6 closest-mood reference shots
        s = score(rep); worst = min(worst, s)
        print(f"{f}: look score {s}/100")
        for m, r in rep.items():
            mark = "  " if r["verdict"] == "ok" else "!!"
            print(f"  {mark} {m:11s} ours {r['ours']:.3f}   reference {r['ref_min']:.3f}-{r['ref_max']:.3f}   {r['verdict']}")
    return 0 if worst >= 80 else 1

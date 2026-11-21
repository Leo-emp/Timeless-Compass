# `tc thumb <job>`: render the job's two freshly drawn thumbnail variants (spec 6.9, rule r21) and run the MEASURED
# checks. The judgement checks (emotion, striking object, matches the video...) are the agent's scored checklist:
#   python -m tc qa <job> thumbnail answers.json --of jobs/<id>/thumb/thumbnail_a.jpg
# Measured here:
#   - exact size: long 1280x720, Shorts 1080x1920
#   - JPG <= 2 MB (YouTube's limit); quality steps down 92 -> 70 until it fits
#   - <= 3 words, each <= 12 letters: the words the thumb module DECLARES (WORDS) - it must draw only those
#   - readable at phone size: downscaled to 160 px wide it still has contrast (RMS) and is not a flat picture
#   - the two variants really differ, so YouTube Test & Compare tests something
#   python -m tc thumb <job>
import json
import subprocess
import sys
from pathlib import Path

from tc import jobs
from tc.cli import register
from tc.paths import ROOT

SIZES = {"long": (1280, 720), "short": (1080, 1920)}
MAX_BYTES = 2 * 1024 * 1024
MAX_WORDS, MAX_LETTERS = 3, 12
MIN_RMS, MIN_STD = 0.18, 0.12          # luminance 0..1 at 160 px wide
MIN_VARIANT_DIFF = 0.05


def _lum160(img):
    """Luminance (0..1) of the picture downscaled to 160 px wide: what a phone user sees in a feed."""
    from PIL import Image
    w, h = img.size
    small = img.convert("L").resize((160, max(1, round(160 * h / w))), Image.LANCZOS)
    return [v / 255 for v in small.getdata()]


def thumb_problems(img, words: list[str], kind: str, file_bytes: int) -> list[str]:
    probs = []
    want = SIZES.get(kind, SIZES["long"])
    if img.size != want:
        probs.append(f"size {img.size[0]}x{img.size[1]}, must be {want[0]}x{want[1]}")
    if file_bytes > MAX_BYTES:
        probs.append(f"file is {file_bytes / 1e6:.1f} MB; YouTube allows 2 MB")
    if len(words) > MAX_WORDS:
        probs.append(f"more than 3 words ({len(words)}: {' '.join(words)})")
    probs += [f"word too long: {w}" for w in words if len(w) > MAX_LETTERS]
    lum = _lum160(img)
    mean = sum(lum) / len(lum)
    std = (sum((v - mean) ** 2 for v in lum) / len(lum)) ** 0.5
    if std < MIN_STD or std < MIN_RMS:
        probs.append(f"not readable at 160 px (contrast {std:.2f}, needs {MIN_RMS})")
    return probs


def variants_differ(a, b) -> bool:
    la, lb = _lum160(a), _lum160(b.resize(a.size))
    return sum(abs(x - y) for x, y in zip(la, lb)) / len(la) >= MIN_VARIANT_DIFF


def _to_jpg(png: Path, jpg: Path) -> int:
    """Save as JPG under 2 MB; returns the file size."""
    from PIL import Image
    im = Image.open(png).convert("RGB")
    for q in (92, 88, 84, 80, 75, 70):
        im.save(jpg, "JPEG", quality=q, optimize=True)
        if jpg.stat().st_size <= MAX_BYTES:
            break
    return jpg.stat().st_size


def make_thumbs(job_id: str) -> int:
    from PIL import Image
    job = jobs.load_job(job_id)
    d = jobs.job_dir(job.id)
    slug = job.id.lower().replace("-", "_")
    out = d / "thumb"
    out.mkdir(parents=True, exist_ok=True)
    report, imgs = {}, {}
    for v in ("a", "b"):
        png = out / f"thumbnail_{v}.png"
        r = subprocess.run(["node", "scripts/thumb.mjs", slug, v, str(png)], cwd=ROOT / "film", capture_output=True, text=True)
        if r.returncode != 0:
            print(f"thumbnail {v}: render failed\n{r.stderr[-800:]}")
            return 1
        info = json.loads(r.stdout.strip().splitlines()[-1])
        jpg = out / f"thumbnail_{v}.jpg"
        size = _to_jpg(png, jpg)
        imgs[v] = Image.open(jpg).convert("RGB")
        report[v] = {"words": info["words"], "bytes": size, "problems": thumb_problems(imgs[v], info["words"], job.kind, size)}
    if not variants_differ(imgs["a"], imgs["b"]):
        report["b"]["problems"].append("variant b is almost the same as a (Test & Compare would test nothing)")
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    bad = 0
    for v in ("a", "b"):
        for p in report[v]["problems"]:
            print(f"thumbnail {v}: problem: {p}")
            bad += 1
    print(f"thumbnails: {'OK' if not bad else f'{bad} problem(s)'} -> {out}")
    return 1 if bad else 0


def _args(p):
    p.add_argument("job")


@register("thumb", "render + measure the job's two thumbnail variants (size, 2 MB, <=3 words, readable at 160 px)", _args)
def _cmd_thumb(args) -> int:
    return make_thumbs(args.job)


if __name__ == "__main__":
    sys.exit(make_thumbs(sys.argv[1]))

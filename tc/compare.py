# SIDE-BY-SIDE REVIEW (Session D): our stills next to the reference frame of the closest MOOD, with the look score,
# so the owner can judge the remaining gap frame by frame (rule r9: the reference is a quality ruler, never copied).
#   python -m tc compare spike/lib_stills/cloud_d6 --ref spike/ref_memory --out spike/review/side_by_side.jpg
# Pairing reuses tc look's own numbers (warmth + saturation = mood; brightness left out on purpose).
from pathlib import Path

from tc import look
from tc.cli import register


def _ref_stats(ref_dir):
    refs = sorted(f for f in Path(ref_dir).glob("*.jpg") if "sheet" not in f.name)
    return [(f, look.stats(look.load(f))) for f in refs]


def pair(stills, ref_dir, refs=None) -> list[dict]:
    """For each still: the closest-mood reference frame and the look score against the closest-mood references."""
    refs = refs if refs is not None else _ref_stats(ref_dir)
    out = []
    for s in stills:
        st = look.stats(look.load(s))
        best = min(refs, key=lambda r: (r[1]["warmth"] - st["warmth"]) ** 2 + (r[1]["saturation"] - st["saturation"]) ** 2)
        report = look.compare(st, [r[1] for r in refs], k=min(8, len(refs)))
        out.append({"still": Path(s), "ref": best[0], "score": look.score(report),
                    "misses": [m for m, r in report.items() if r["verdict"] != "ok"]})
    return out


def sheet(stills, ref_dir, out, width=640) -> list[dict]:
    """Write a sheet: one row per still (ours | closest reference), labelled with the score and what misses."""
    from PIL import Image, ImageDraw
    rows = pair(stills, ref_dir)
    h = int(width * 9 / 16)
    img = Image.new("RGB", (2 * width, len(rows) * (h + 24)), (18, 18, 18))
    d = ImageDraw.Draw(img)
    for i, r in enumerate(rows):
        y = i * (h + 24)
        for j, f in enumerate((r["still"], r["ref"])):
            im = Image.open(f).convert("RGB"); im.thumbnail((width, h))
            img.paste(im, (j * width + (width - im.width) // 2, y + 24 + (h - im.height) // 2))
        miss = (" | misses: " + ", ".join(r["misses"])) if r["misses"] else ""
        d.text((6, y + 5), f"OURS  {r['still'].name}   look {r['score']}/100{miss}", fill=(255, 220, 90))
        d.text((width + 6, y + 5), f"REFERENCE (closest mood)  {r['ref'].name}", fill=(170, 200, 255))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=88)
    return rows


def _args(p):
    p.add_argument("stills", nargs="+", help="image files or folders (searched for *.png)")
    p.add_argument("--ref", default="spike/ref_memory")
    p.add_argument("--out", default="spike/review/side_by_side.jpg")


@register("compare", "side-by-side sheet: our stills next to the closest-mood reference frames, with look scores", _args)
def _cmd_compare(args) -> int:
    files = []
    for s in args.stills:
        p = Path(s)
        files += sorted(p.rglob("*.png")) if p.is_dir() else [p]
    rows = sheet(files, args.ref, args.out)
    for r in rows:
        print(f"{r['score']:3d}  {r['still']}  <->  {r['ref'].name}  {', '.join(r['misses'])}")
    print("sheet:", args.out)
    return 0

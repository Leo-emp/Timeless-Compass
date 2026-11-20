# MEASURED STILL CHECKS (`tc still`): the part of "production grade" that numbers can judge (spec 6.6, layer 1).
# Two inputs:
#   - the still image (png): detail map (no empty patches), contrast, clipped highlights
#   - the inspector json (film/scripts/inspect.mjs): on-screen boxes of faces, hands, props and text
# Geometry rules (docs/ART_BIBLE.md sections 1, 2, 7):
#   - a hand that holds a prop must touch it (grip rule)
#   - nothing drawn AFTER a face (on top of it) may cover more than 20 % of it
#   - text stays inside its card; faces inside a 1 % margin; text inside a 3 % margin
# The agent's own eye (the scored still checklist, `tc qa ... still`) judges everything else.
#
#   python -m tc still film/out/s012.png --json film/out/s012.json --calm "0,0 1,0"
import json
from pathlib import Path

from PIL import Image, ImageFilter

from tc.cli import register

COVER_MAX = 0.20          # share of a face box that may be covered by something drawn on top
FACE_MARGIN, TEXT_MARGIN = 0.01, 0.03
EMPTY_TILE = 0.010        # mean edge strength below this = an empty patch
MIN_CONTRAST = 90         # luma p95 - p5
MAX_CLIPPED = 0.02        # share of pure-white pixels


def _overlap(a: list[float], b: list[float]) -> float:
    """Area of the intersection of two [x, y, w, h] boxes."""
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def _inside(inner: list[float], outer: list[float], tol: float = 1.0) -> bool:
    return (inner[0] >= outer[0] - tol and inner[1] >= outer[1] - tol and
            inner[0] + inner[2] <= outer[0] + outer[2] + tol and inner[1] + inner[3] <= outer[1] + outer[3] + tol)


def geometry_problems(elements: list[dict], w: int, h: int) -> list[str]:
    probs = []
    props = {e["id"]: e for e in elements if e["role"] == "prop" and e.get("id")}
    for e in elements:
        if e["role"] == "hand" and e.get("holds"):
            p = props.get(e["holds"])
            if p is None:
                probs.append(f"hand holds unknown prop {e['holds']!r}")
            elif e.get("grip") is False or (e.get("grip") is None and _overlap(e["box"], p["box"]) <= 0):
                probs.append(f"hand does not touch the {e['holds']} it holds")
    # extras (crowd, crew behind a rail) are marked acting="false": they may be partly hidden; acting faces may not
    faces = [e for e in elements if e["role"] == "face" and e.get("acting") != "false"]
    for f in faces:
        area = f["box"][2] * f["box"][3]
        if area <= 0:
            continue
        for e in elements:
            # anything drawn later can cover: props, text, hands, another head, tagged foreground scenery (fg)
            if e["role"] in ("prop", "text", "textbox", "hand", "face", "fg") and e["order"] > f["order"] and e is not f:
                share = _overlap(e["box"], f["box"]) / area
                if share > COVER_MAX:
                    probs.append(f"{e['role']} {e.get('id') or ''} covers face #{f['order']} ({share:.0%})".replace("  ", " "))
    for f in faces:
        x, y, bw, bh = f["box"]
        if x < w * FACE_MARGIN or y < h * FACE_MARGIN or x + bw > w * (1 - FACE_MARGIN) or y + bh > h * (1 - FACE_MARGIN):
            # faces of tiny far crowd figures cut by the frame are fine; only flag faces big enough to read
            if bw * bh > (w * h) * 0.0004:
                probs.append(f"face #{f['order']} outside safe area")
    boxes = [e for e in elements if e["role"] == "textbox"]
    for t in (e for e in elements if e["role"] == "text"):
        x, y, bw, bh = t["box"]
        if x < w * TEXT_MARGIN or y < h * TEXT_MARGIN or x + bw > w * (1 - TEXT_MARGIN) or y + bh > h * (1 - TEXT_MARGIN):
            probs.append(f"text #{t['order']} outside safe area")
        holder = max((b for b in boxes if b["order"] < t["order"]), key=lambda b: b["order"], default=None)
        if holder is not None and not _inside(t["box"], holder["box"]):
            probs.append(f"text overflows its box (#{t['order']})")
    return probs


def detail_map(img: Image.Image, cols: int = 8, rows: int = 6) -> list[list[float]]:
    """Edge strength (0..1) per tile: how much drawn detail each part of the frame has."""
    edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
    W, H = edges.size
    out = []
    for r in range(rows):
        row = []
        for c in range(cols):
            tile = edges.crop((c * W // cols + 2, r * H // rows + 2, (c + 1) * W // cols - 2, (r + 1) * H // rows - 2))
            hist = tile.histogram()
            n = sum(hist) or 1
            row.append(sum(i * v for i, v in enumerate(hist)) / n / 255)
        out.append(row)
    return out


def image_problems(img: Image.Image, allow_calm: set[tuple[int, int]] = frozenset()) -> list[str]:
    probs = []
    for r, row in enumerate(detail_map(img)):
        for c, v in enumerate(row):
            if v < EMPTY_TILE and (c, r) not in allow_calm:
                probs.append(f"empty area at tile ({c}, {r})")
    hist = img.convert("L").histogram()
    n = sum(hist)

    def pct(p):
        acc = 0
        for i, v in enumerate(hist):
            acc += v
            if acc >= p * n:
                return i
        return 255
    if pct(0.95) - pct(0.05) < MIN_CONTRAST:
        probs.append(f"flat contrast (p95-p5 = {pct(0.95) - pct(0.05)})")
    if hist[255] / n > MAX_CLIPPED:
        probs.append(f"clipped highlights ({hist[255] / n:.1%} pure white)")
    return probs


def _args(p):
    p.add_argument("png")
    p.add_argument("--json", help="inspector json (film/scripts/inspect.mjs)")
    p.add_argument("--calm", default="", help='tiles allowed to be calm, e.g. "0,0 1,0" (open sky / calm sea)')
    p.add_argument("--chars", action="store_true", help="also check every character part colour against its sheet (r19)")


@register("still", "measured still checks: grip, faces covered, text fit, safe areas, empty areas, contrast", _args)
def _cmd_still(args) -> int:
    calm = {tuple(int(v) for v in t.split(",")) for t in args.calm.split()}
    img = Image.open(args.png)
    probs = image_problems(img, calm)
    if args.json:
        d = json.loads(Path(args.json).read_text(encoding="utf-8"))
        probs = geometry_problems(d["elements"], d["w"], d["h"]) + probs
        if args.chars:
            from tc.charcheck import character_problems, load_sheets_for
            probs += character_problems(d["elements"], load_sheets_for(d["elements"]))
    for p in probs:
        print("problem:", p)
    print("still:", "OK" if not probs else f"{len(probs)} problem(s)")
    return 1 if probs else 0

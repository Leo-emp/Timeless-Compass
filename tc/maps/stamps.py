# HAND-DRAWN STAMPS: the tiny pictures that make the land look illustrated (reference/maps/01, zoom of Europe):
#   - forests: dense clumps of small round olive trees with a dark outline and a shadow side
#   - mountains: little peaks on the REAL mountain ranges (Natural Earth "Range/mtn" areas), lit on the left,
#     brown-hatched on the right, drawn back-to-front so the near ones overlap the far ones
#   - steppe / open land: small brown tufts and hill strokes (Anatolia and the plains in the reference)
#   - deserts: sparse dots and little dune arcs
# Every stamp is drawn by code with random size, lean and shade, so no two look the same (a stamped, repeated
# look is the #1 tell of a cheap map). Stamps are sorted top-to-bottom before drawing (painter's order).
import math

import numpy as np
from PIL import Image, ImageDraw

from tc.maps import geo, raster as R

INK = (66, 46, 28)
TREE = [(86, 96, 52), (74, 86, 46), (98, 104, 58), (68, 78, 44)]
TREE_DARK = (44, 50, 28)
PEAK_LIGHT = (222, 196, 140)
PEAK_SHADE = (138, 100, 62)
TUFT = (122, 92, 56)


# ------------------------------------------------------------------ where things grow
def biome_masks(view: geo.View, land: np.ndarray, rules: dict | None = None) -> dict[str, np.ndarray]:
    """Split the land into mountain / desert / forest / steppe masks.
    Mountains + deserts come from Natural Earth named regions; forest vs steppe from simple era rules
    (default: wooded Europe north of ~43°N and west of ~32°E, open steppe elsewhere). A job can override with
    `rules` = {"forest": [[lon0, lat0, lon1, lat1], ...], "desert": [...], "steppe": [...]} boxes."""
    rules = rules or {}
    h, w = land.shape
    mtn, des = [], []
    for f in geo.load("regions"):
        cls = f["properties"].get("FEATURECLA")
        if cls == "Range/mtn":
            mtn += geo.rings(f["geometry"])
        elif cls == "Desert":
            des += geo.rings(f["geometry"])
    mountains = R.polygons_mask(view, mtn) * land if mtn else np.zeros_like(land)
    desert = R.polygons_mask(view, des) * land if des else np.zeros_like(land)
    lon = np.linspace(view.lon0, view.lon1, w, dtype=np.float32)[None, :].repeat(h, 0)
    lat = np.linspace(view.lat1, view.lat0, h, dtype=np.float32)[:, None].repeat(w, 1)
    # broken, natural edges for the rule areas: offset the coordinates with noise
    rng = np.random.default_rng(11)
    jit = (R.fbm(h, w, w / 12, 3, rng) - 0.5) * 3.0
    forest = ((lat + jit > 43.5) & (lon + jit < 32) | (lat + jit > 50)).astype(np.float32)
    desert = np.maximum(desert, ((lat + jit < 31.5)).astype(np.float32))
    for kind, boxes in rules.items():
        for lo0, la0, lo1, la1 in boxes:
            box = ((lon >= lo0) & (lon <= lo1) & (lat >= la0) & (lat <= la1)).astype(np.float32)
            if kind == "forest":
                forest = np.maximum(forest, box); desert = desert * (1 - box)
            elif kind == "desert":
                desert = np.maximum(desert, box); forest = forest * (1 - box)
            elif kind == "steppe":
                forest = forest * (1 - box); desert = desert * (1 - box)
    # forests thin out in patches (clearings, farmland) so they are clumps, not a carpet
    clumps = R.smoothstep(0.38, 0.55, R.fbm(h, w, w / 45, 3, rng))
    forest = forest * land * (1 - mountains) * (1 - desert) * clumps
    desert = desert * land * (1 - mountains)
    steppe = land * (1 - mountains) * (1 - desert) * (1 - (forest > 0.5))
    return {"mountain": mountains, "desert": desert, "forest": forest, "steppe": steppe}


def scatter(mask: np.ndarray, spacing: float, rng: np.random.Generator, jitter: float = 0.9) -> list[tuple[float, float]]:
    """Points on a jittered grid, kept where the mask says yes (probability = mask value)."""
    h, w = mask.shape
    pts = []
    ys = np.arange(spacing / 2, h, spacing * 0.866)               # hex-ish rows: offset every other row
    for i, y in enumerate(ys):
        off = spacing / 2 if i % 2 else 0
        xs = np.arange(off, w, spacing)
        jx = xs + (rng.random(len(xs)) - 0.5) * spacing * jitter
        jy = y + (rng.random(len(xs)) - 0.5) * spacing * jitter
        for x, yv in zip(jx, jy):
            xi, yi = int(x), int(yv)
            if 0 <= xi < w and 0 <= yi < h and rng.random() < mask[yi, xi]:
                pts.append((x, yv))
    return pts


# ------------------------------------------------------------------ the stamps
def tree(d: ImageDraw.ImageDraw, x: float, y: float, s: float, rng) -> None:
    """A small round deciduous tree: dark shadow blob, 2-3 olive leaf blobs, a tiny trunk."""
    col = TREE[rng.integers(len(TREE))]
    d.line([(x, y), (x, y + s * 0.55)], fill=INK, width=max(1, int(s * 0.14)))           # trunk
    for k in range(rng.integers(2, 4)):
        ox, oy = (rng.random() - 0.5) * s * 0.6, -s * (0.25 + rng.random() * 0.35)
        r = s * (0.32 + rng.random() * 0.14)
        d.ellipse([x + ox - r + s * 0.08, y + oy - r + s * 0.08, x + ox + r + s * 0.08, y + oy + r + s * 0.08], fill=TREE_DARK)
        d.ellipse([x + ox - r, y + oy - r, x + ox + r, y + oy + r], fill=col)
    # a light fleck on the upper-left (sun from the top-left, like the whole map)
    r = s * 0.12
    d.ellipse([x - s * 0.22 - r, y - s * 0.55 - r, x - s * 0.22 + r, y - s * 0.55 + r], fill=tuple(min(255, c + 30) for c in col))


def mountain(d: ImageDraw.ImageDraw, x: float, y: float, s: float, rng) -> None:
    """A peak: lit left face (paper-light), shaded right face (brown) with hatch lines, ink skyline."""
    lean = (rng.random() - 0.5) * 0.35
    top = (x + lean * s, y - s * (0.8 + rng.random() * 0.4))
    left, right = (x - s * (0.7 + rng.random() * 0.3), y), (x + s * (0.7 + rng.random() * 0.3), y)
    mid = (top[0] + (rng.random() - 0.3) * s * 0.15, y)
    d.polygon([left, top, mid], fill=PEAK_LIGHT)
    d.polygon([mid, top, right], fill=PEAK_SHADE)
    for k in range(1, 4):                                   # hatching on the shade side
        t = k / 4
        a = (top[0] + (right[0] - top[0]) * t, top[1] + (right[1] - top[1]) * t)
        d.line([a, (a[0] - s * 0.18, y)], fill=INK, width=max(1, int(s * 0.06)))
    w = max(1, int(s * 0.09))
    d.line([left, top, right], fill=INK, width=w, joint="curve")    # skyline
    if rng.random() < 0.5:                                  # a small foothill beside it
        fx = x + (0.9 if rng.random() < 0.5 else -0.9) * s
        d.arc([fx - s * 0.5, y - s * 0.5, fx + s * 0.5, y + s * 0.4], 200, 340, fill=INK, width=w)


def tuft(d: ImageDraw.ImageDraw, x: float, y: float, s: float, rng) -> None:
    """Open land: either a small grass tuft (3 strokes) or a low hill arc."""
    w = max(1, int(s * 0.13))
    if rng.random() < 0.55:
        for k in (-1, 0, 1):
            d.line([(x + k * s * 0.18, y), (x + k * s * 0.32 + (rng.random() - 0.5) * s * 0.1, y - s * (0.35 + 0.2 * rng.random()))], fill=TUFT, width=w)
    else:
        d.arc([x - s * 0.55, y - s * 0.35, x + s * 0.55, y + s * 0.35], 190, 350, fill=TUFT, width=w)


def dune(d: ImageDraw.ImageDraw, x: float, y: float, s: float, rng) -> None:
    """Desert: mostly dots, sometimes a dune arc."""
    if rng.random() < 0.7:
        r = s * 0.09
        d.ellipse([x - r, y - r, x + r, y + r], fill=TUFT)
    else:
        d.arc([x - s * 0.6, y - s * 0.25, x + s * 0.6, y + s * 0.3], 200, 340, fill=TUFT, width=max(1, int(s * 0.1)))


# ------------------------------------------------------------------ paint all stamps
def paint_stamps(img: np.ndarray, view: geo.View, land: np.ndarray, seed: int = 3, rules: dict | None = None,
                 density: float = 1.0) -> np.ndarray:
    """Draw every stamp onto the map. Drawn at 2x then reduced (clean anti-aliased edges)."""
    rng = np.random.default_rng(seed)
    unit = view.width / 1000
    masks = biome_masks(view, land, rules)
    S = 2
    layer = Image.new("RGBA", (view.width * S, view.height * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    jobs = []                                   # (y, x, painter, size) for painter's-order sorting
    for x, y in scatter(masks["forest"], 2.5 * unit / density, rng):
        jobs.append((y, x, tree, (2.7 + rng.random() * 1.3) * unit))
    # mountains form CHAINS, not carpets: keep them where a ridge-shaped noise is high inside the range
    h, w = land.shape
    ridge = 1 - np.abs(R.fbm(h, w, w / 40, 3, rng) - 0.5) * 2              # 1 along wandering ridge lines
    chain = masks["mountain"] * R.smoothstep(0.55, 0.85, ridge)
    for x, y in scatter(chain, 4.2 * unit / density, rng):
        jobs.append((y, x, mountain, (2.8 + rng.random() * 2.4) * unit))
    for x, y in scatter(masks["mountain"] * (1 - chain), 5.0 * unit / density, rng, jitter=1.0):
        jobs.append((y, x, tuft, (2.6 + rng.random() * 1.2) * unit))       # foothills between the chains
    for x, y in scatter(masks["steppe"], 4.6 * unit / density, rng, jitter=1.0):
        jobs.append((y, x, tuft, (2.6 + rng.random() * 1.4) * unit))
    for x, y in scatter(masks["desert"], 7.0 * unit / density, rng, jitter=1.0):
        jobs.append((y, x, dune, (2.6 + rng.random() * 1.6) * unit))
    jobs.sort(key=lambda j: j[0])
    for y, x, fn, s in jobs:
        fn(d, x * S, y * S, s * S, rng)
    layer = layer.resize((view.width, view.height), Image.LANCZOS)
    a = np.asarray(layer, np.float32) / 255.0
    alpha = a[..., 3] * (0.85 + 0.15 * R.fbm(view.height, view.width, view.width / 20, 2, rng))   # ink unevenness
    # multiply-blend so the paper grain shows through the ink, then a little normal blend for body
    out = R.multiply(img, a[..., :3], alpha * 0.75)
    return R.mix(out, a[..., :3] * 0.85, alpha * 0.55)


# ------------------------------------------------------------------ decorations (reference/maps/01: ships at sea)
def ship(size: int, rng: np.random.Generator, sail=(236, 226, 200), mark=(150, 34, 28), kind: str = "cog") -> Image.Image:
    """A small period sailing ship drawn in ink: curved hull with planks, one mast, a square sail with a stripe or
    cross, a pennant, a few wave strokes under the hull. kind: 'cog' (medieval) or 'galley' (ancient, oars)."""
    S = 4; W, H = int(size * 1.3), size
    im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    w, h = W * S, H * S
    ink, wood, wood_d = (52, 34, 20, 255), (128, 84, 46, 255), (92, 58, 32, 255)
    # hull: the deck line SAGS in the middle and rises at bow + stern (sheer), the keel is a round belly
    N = 24
    top = [(w * (0.04 + 0.92 * i / N), h * (0.52 + 0.12 * math.sin(math.pi * i / N))) for i in range(N + 1)]
    bot = [(w * (0.9 - 0.8 * i / N), h * (0.66 + 0.2 * math.sin(math.pi * i / N) ** 0.6)) for i in range(N + 1)]
    d.polygon(top + bot, fill=wood, outline=ink, width=S * 2)
    for k in (0.33, 0.62):                                      # plank lines follow the hull curve
        pl = [(x, y1 + (y2 - y1) * k) for (x, y1), (_, y2) in zip(top, reversed(bot))]
        d.line(pl, fill=wood_d, width=S * 2, joint="curve")
    d.line(top, fill=(160, 112, 66, 255), width=S * 2, joint="curve")          # lit gunwale
    if kind == "cog":                                           # stern castle (raised box at the back)
        d.rectangle([w * 0.74, h * 0.4, w * 0.95, h * 0.56], fill=wood, outline=ink, width=S * 2)
        for k in range(4):
            x = w * (0.76 + k * 0.05)
            d.rectangle([x, h * 0.36, x + w * 0.025, h * 0.4], fill=wood_d)
    if kind == "galley":
        for k in range(8):
            x = w * (0.2 + k * 0.08)
            d.line([(x, h * 0.7), (x - w * 0.07, h * 0.97)], fill=ink, width=S * 2)
    mx = w * 0.48
    d.line([(mx, h * 0.62), (mx, h * 0.04)], fill=ink, width=S * 3)              # mast
    d.line([(w * 0.24, h * 0.13), (w * 0.72, h * 0.13)], fill=ink, width=S * 2)   # yard
    # billowing sail: curved sides and a belly at the bottom; shaded on the right
    L_, Rr, T_, B_ = w * 0.25, w * 0.71, h * 0.14, h * 0.5
    sail_pts = [(L_ + (Rr - L_) * i / 12, T_) for i in range(13)]
    sail_pts += [(Rr + w * 0.05 * math.sin(math.pi * j / 10), T_ + (B_ - T_) * j / 10) for j in range(11)]
    sail_pts += [(Rr - (Rr - L_) * i / 12, B_ + h * 0.06 * math.sin(math.pi * i / 12)) for i in range(13)]
    sail_pts += [(L_ + w * 0.03 * math.sin(math.pi * j / 10), B_ - (B_ - T_) * j / 10) for j in range(11)]
    d.polygon(sail_pts, fill=sail + (255,), outline=ink, width=S * 2)
    d.polygon([(mx + w * 0.08, T_), (Rr, T_)] + [(Rr + w * 0.05 * math.sin(math.pi * j / 10), T_ + (B_ - T_) * j / 10) for j in range(11)]
              + [(mx + w * 0.1, B_ + h * 0.05)], fill=(206, 192, 160, 255))
    cx, cy = (L_ + Rr) / 2, (T_ + B_) / 2 + h * 0.02
    if rng.random() < 0.5:
        for k in (-1, 1):
            d.line([(cx + k * w * 0.11, T_ + h * 0.02), (cx + k * w * 0.11, B_ + h * 0.03)], fill=mark + (255,), width=S * 5)
    else:
        d.line([(cx, T_ + h * 0.06), (cx, B_ - h * 0.02)], fill=mark + (255,), width=S * 6)
        d.line([(L_ + w * 0.09, cy), (Rr - w * 0.07, cy)], fill=mark + (255,), width=S * 6)
    d.polygon([(mx, h * 0.02), (mx + w * 0.17, h * 0.045), (mx, h * 0.08)], fill=mark + (255,), outline=ink)
    for k in range(3):                                          # wave strokes
        x = w * (0.15 + k * 0.3)
        d.arc([x, h * 0.86, x + w * 0.22, h * 0.98], 200, 340, fill=(50, 80, 82, 255), width=S * 2)
    return im.resize((W, H), Image.LANCZOS)


def paint_decor(img: np.ndarray, view: geo.View, decor: list[dict], seed: int = 5) -> np.ndarray:
    """Lay decorations (ships for now) onto the map: [{"kind": "cog"|"galley", "at": [lon, lat], "size": 30}]."""
    rng = np.random.default_rng(seed)
    unit = view.width / 1000
    pil = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    for dco in decor:
        im = ship(int(dco.get("size", 30) * unit), rng, kind=dco.get("kind", "cog"))
        if dco.get("flip"):
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        x, y = view.px(*dco["at"])
        pil.alpha_composite(im, (int(x - im.width / 2), int(y - im.height * 0.8)))
    return np.asarray(pil.convert("RGB"), np.float32) / 255

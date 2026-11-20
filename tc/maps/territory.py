# TERRITORIES: empires/kingdoms painted over the land like coloured ink (reference/maps/02, zoom of frame 02).
#
# Look:
#   - flat colour that MULTIPLIES the paper: grain, stains, trees and mountains stay visible underneath
#   - a slightly darker rim just inside the border + a faint glow outside it, so the edge reads from far away
#   - a repeated pattern of light, thin-line MEDALLIONS (a ring with the realm's emblem: cross, crescent, star)
#     spread on a loose grid across the area, semi-transparent
# Animation (done in Blender, prepared here): every territory also gets a GROW map — a smooth 0..1 gradient that
# starts at the realm's heart (its capital) and reaches 1 at the farthest border, with a noisy "ink soaking" edge.
# Blender shows the colour where grow < progress, so animating progress 0 -> 1 spreads the empire across the land.
import math

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from tc.maps import geo, raster as R

# Map colours tuned to the reference (crimson Christendom, royal purple Byzantium, teal Seljuks, green Fatimids)
COLORS = {
    "crimson": "#9c2a26", "purple": "#4b3486", "teal": "#1a6f95", "green": "#3f8a3a",
    "gold": "#c08a2a", "blue": "#2f5a9a", "black": "#3a3430", "orange": "#c0602a", "white": "#e6dcc0",
}


# ------------------------------------------------------------------ emblems (thin-line medallions)
def draw_emblem(d: ImageDraw.ImageDraw, kind: str, cx: float, cy: float, r: float, ink, w: int, solid: bool = False) -> None:
    """A light thin-line emblem inside a ring. All drawn from simple geometry (our own designs)."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ink, width=w)               # outer ring
    d.ellipse([cx - r * 0.84, cy - r * 0.84, cx + r * 0.84, cy + r * 0.84], outline=ink, width=max(1, w // 2))
    k = r * 0.62
    if kind in ("cross", "cross_patee"):
        if kind == "cross":
            d.line([(cx - k, cy), (cx + k, cy)], fill=ink, width=w * 2)
            d.line([(cx, cy - k), (cx, cy + k)], fill=ink, width=w * 2)
        else:                                       # arms that flare out at the ends (cross pattée)
            for a in range(4):
                t = a * math.pi / 2
                c, s = math.cos(t), math.sin(t)
                p = lambda u, v: (cx + u * c - v * s, cy + u * s + v * c)
                d.polygon([p(0, -r * 0.08), p(k, -r * 0.28), p(k, r * 0.28), p(0, r * 0.08)],
                          fill=ink if solid else None, outline=ink, width=w)
        for a in range(4):                          # four small dots between the arms
            t = math.pi / 4 + a * math.pi / 2
            x, y = cx + math.cos(t) * k * 0.62, cy + math.sin(t) * k * 0.62
            d.ellipse([x - w, y - w, x + w, y + w], fill=ink)
    elif kind == "crescent":
        d.arc([cx - k, cy - k, cx + k, cy + k], 40, 320, fill=ink, width=w * 2)
        d.arc([cx - k * 0.55, cy - k * 0.8, cx + k * 0.95, cy + k * 0.8], 60, 300, fill=ink, width=w)
        sx = cx + k * 0.55
        for a in range(5):                          # small star in the crescent's mouth
            t1, t2 = -math.pi / 2 + a * 2 * math.pi / 5, -math.pi / 2 + (a + 2) * 2 * math.pi / 5
            d.line([(sx + math.cos(t1) * k * 0.28, cy + math.sin(t1) * k * 0.28),
                    (sx + math.cos(t2) * k * 0.28, cy + math.sin(t2) * k * 0.28)], fill=ink, width=w)
    elif kind == "star8":                           # eight-pointed star (two overlapping squares)
        for off in (0, math.pi / 4):
            pts = [(cx + math.cos(off + a * math.pi / 2) * k, cy + math.sin(off + a * math.pi / 2) * k) for a in range(4)]
            d.polygon(pts, outline=ink, width=w)
        d.ellipse([cx - k * 0.25, cy - k * 0.25, cx + k * 0.25, cy + k * 0.25], outline=ink, width=w)
    elif kind == "sun":
        d.ellipse([cx - k * 0.4, cy - k * 0.4, cx + k * 0.4, cy + k * 0.4], outline=ink, width=w)
        for a in range(12):
            t = a * math.pi / 6
            d.line([(cx + math.cos(t) * k * 0.55, cy + math.sin(t) * k * 0.55),
                    (cx + math.cos(t) * k, cy + math.sin(t) * k)], fill=ink, width=w)
    elif kind == "chirho":                          # ☧ — Roman/Byzantine
        d.line([(cx, cy - k), (cx, cy + k)], fill=ink, width=w * 2)
        d.arc([cx - k * 0.05, cy - k, cx + k * 0.55, cy - k * 0.35], 270, 90, fill=ink, width=w * 2)
        d.line([(cx - k * 0.6, cy - k * 0.3), (cx + k * 0.6, cy + k * 0.6)], fill=ink, width=w * 2)
        d.line([(cx + k * 0.6, cy - k * 0.3), (cx - k * 0.6, cy + k * 0.6)], fill=ink, width=w * 2)
    elif kind == "lion":                            # simple heraldic shield with a chevron (stand-in for beasts)
        d.polygon([(cx - k * 0.7, cy - k * 0.7), (cx + k * 0.7, cy - k * 0.7), (cx + k * 0.7, cy + k * 0.1),
                   (cx, cy + k * 0.85), (cx - k * 0.7, cy + k * 0.1)], outline=ink, width=w)
        d.line([(cx - k * 0.6, cy + k * 0.2), (cx, cy - k * 0.35), (cx + k * 0.6, cy + k * 0.2)], fill=ink, width=w * 2)
    else:                                           # plain ring with a dot
        d.ellipse([cx - k * 0.2, cy - k * 0.2, cx + k * 0.2, cy + k * 0.2], fill=ink)


# ------------------------------------------------------------------ one territory
def territory_mask(view: geo.View, polygon_lonlat: list, land: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """The realm's area: the rough border polygon from research, clipped to the land, with a HAND-DRAWN border.
    The wobble is a domain warp: every pixel looks up the polygon at a position pushed around by smooth noise,
    so straight edges between research points become natural wandering borders (no visible polygon corners)."""
    m = R.polygons_mask(view, [[polygon_lonlat]], supersample=1)
    h, w = m.shape
    unit = view.width / 1000
    amp = 9 * unit
    dx = (R.fbm(h, w, 60 * unit, 4, rng) - 0.5) * 2 * amp
    dy = (R.fbm(h, w, 60 * unit, 4, rng) - 0.5) * 2 * amp
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    m = ndimage.map_coordinates(m, [np.clip(yy + dy, 0, h - 1), np.clip(xx + dx, 0, w - 1)], order=1)
    m = R.smoothstep(0.35, 0.65, R.blur(m, 0.6 * unit))
    return m * R.smoothstep(0.3, 0.7, land)


def exclusive(masks: list[np.ndarray]) -> list[np.ndarray]:
    """Each piece of land belongs to ONE realm: a later realm in the list wins where two overlap
    (list order = paint order; put the realm the story is about last)."""
    out, taken = [], np.zeros_like(masks[0])
    for m in reversed(masks):
        out.append(m * (1 - taken)); taken = np.maximum(taken, m)
    return out[::-1]


def grow_map(view: geo.View, mask: np.ndarray, seed_lonlat, rng: np.random.Generator) -> np.ndarray:
    """0 at the heart, 1 at the farthest border; noisy so the spreading edge looks like ink soaking paper.
    Outside the territory = 1 (never shown)."""
    h, w = mask.shape
    sx, sy = view.px(*seed_lonlat)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.hypot(xx - sx, yy - sy)
    unit = view.width / 1000
    d = d + (R.fbm(h, w, 25 * unit, 4, rng) - 0.5) * 60 * unit       # ragged, organic spreading front
    inside = mask > 0.5
    if not inside.any():
        return np.ones_like(mask)
    lo, hi = d[inside].min(), d[inside].max()
    g = (d - lo) / max(hi - lo, 1e-6)
    return np.where(inside, np.clip(g, 0, 1) * 0.98, 1.0).astype(np.float32)


def emblem_layer(view: geo.View, mask: np.ndarray, emblem: str, rng: np.random.Generator,
                 spacing_units: float = 62, ink=(236, 226, 200)) -> np.ndarray:
    """RGBA medallion pattern spread inside the territory (only where a whole medallion mostly fits)."""
    unit = view.width / 1000
    S = 2
    img = Image.new("RGBA", (view.width * S, view.height * S), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    r = 17 * unit
    inner = ndimage.distance_transform_edt(mask > 0.5)                # distance to the border, inside
    sp = spacing_units * unit
    ys = np.arange(sp / 2, view.height, sp * 0.866)
    for i, y in enumerate(ys):
        for x in np.arange((sp / 2) if i % 2 else 0, view.width, sp):
            xi, yi = int(x), int(y)
            if 0 <= xi < view.width and 0 <= yi < view.height and inner[yi, xi] > r * 0.7:
                draw_emblem(d, emblem, x * S, y * S, r * S * (0.9 + rng.random() * 0.15), ink + (255,), max(1, int(unit * 0.9 * S)))
    img = img.resize((view.width, view.height), Image.LANCZOS)
    return np.asarray(img, np.float32) / 255.0


def paint_territory(img: np.ndarray, mask: np.ndarray, color: str, emblems: np.ndarray | None,
                    view: geo.View, progress: np.ndarray | float = 1.0) -> np.ndarray:
    """Composite one territory onto the map (used for stills; Blender does the same live with `progress`)."""
    unit = view.width / 1000
    col = R.rgb(COLORS.get(color, color))
    m = mask * (progress if np.isscalar(progress) else progress)
    inner = ndimage.distance_transform_edt(m > 0.5).astype(np.float32)
    rim = (1 - R.smoothstep(0, 4 * unit, inner)) * (m > 0.5)           # darker band inside the border
    h, w = m.shape
    rng = np.random.default_rng(int(col.sum() * 1000))
    wash = 0.8 + 0.2 * R.fbm(h, w, 25 * unit, 4, rng)                    # uneven watercolour wash
    out = R.multiply(img, col * 1.3 * wash[..., None], m * 0.9)         # ink colour soaked into the paper
    out = R.mix(out, col * 0.55, rim * 0.5)
    glow = R.blur(m, 3 * unit) * (1 - m)                                # faint halo outside the edge
    out = R.mix(out, col, glow * 0.35)
    if emblems is not None:
        out = R.mix(out, emblems[..., :3], emblems[..., 3] * m * 0.55)
    return out

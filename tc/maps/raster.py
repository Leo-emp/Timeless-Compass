# RASTER TOOLS: noise, masks and distance fields — the building blocks every map layer is painted from.
# All images here are numpy float32 arrays, values 0..1, shape (height, width) or (height, width, 3).
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from tc.maps import geo


# ------------------------------------------------------------------ noise
def value_noise(h: int, w: int, cell: float, rng: np.random.Generator) -> np.ndarray:
    """Smooth random blobs about `cell` pixels across: a small random grid, smoothly enlarged (cubic zoom).
    SPEED: big blobs carry no fine detail, so they are made at a fraction of the size and enlarged with a cheap
    linear zoom (identical look, ~10x faster on a 6144-px map)."""
    f = int(max(1, min(8, cell // 8)))
    if f > 1:
        small = value_noise(-(-h // f), -(-w // f), cell / f, rng)
        big = Image.fromarray(small, "F").resize((small.shape[1] * f, small.shape[0] * f), Image.BILINEAR)
        return np.clip(np.asarray(big)[:h, :w], 0, 1).astype(np.float32)
    cell = max(cell, 1.0)
    gh, gw = int(h / cell) + 3, int(w / cell) + 3          # enough random points to cover the image
    grid = rng.random((gh, gw), dtype=np.float32)
    # one grid point every `cell` px, smooth bicubic in between (Pillow's resize is ~20x faster than ndimage.zoom)
    big = np.asarray(Image.fromarray(grid, "F").resize((int(gw * cell), int(gh * cell)), Image.BICUBIC))
    return np.clip(big[:h, :w], 0, 1).astype(np.float32)


def fbm(h: int, w: int, cell: float, octaves: int, rng: np.random.Generator, gain: float = 0.5) -> np.ndarray:
    """Fractal noise: big blobs + smaller blobs + smaller... (looks like natural stains, clouds, paper fibre).
    Normalised to 0..1."""
    out = np.zeros((h, w), np.float32); amp, total = 1.0, 0.0
    for o in range(octaves):
        c = cell / (2 ** o)
        if c < 1.5:
            break
        out += amp * value_noise(h, w, c, rng); total += amp; amp *= gain
    out /= total
    lo, hi = np.percentile(out, 1), np.percentile(out, 99)
    return np.clip((out - lo) / max(hi - lo, 1e-6), 0, 1)


def smoothstep(e0: float, e1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ shapes -> masks
def polygons_mask(view: geo.View, polygons, supersample: int = 1) -> np.ndarray:
    """Fill lon/lat polygons (outer ring + holes) into a 0..1 mask the size of the view."""
    W, H = view.width * supersample, view.height * supersample
    img = Image.new("L", (W, H), 0); d = ImageDraw.Draw(img)
    for poly in polygons:
        for i, ring in enumerate(poly):
            if len(ring) < 3 or (i == 0 and not geo.bbox_hits(ring, view)):
                if i == 0:
                    break           # whole polygon is off the map: skip its holes too
                continue
            pts = [tuple(c * supersample for c in view.px(lon, lat)) for lon, lat in ring]
            d.polygon(pts, fill=255 if i == 0 else 0)      # ring 0 = land, later rings = holes (lakes inside)
    if supersample > 1:
        img = img.resize((view.width, view.height), Image.LANCZOS)
    return np.asarray(img, np.float32) / 255.0


def lines_mask(view: geo.View, polylines, width_px: float) -> np.ndarray:
    """Draw lon/lat polylines (rivers, roads) into a 0..1 mask, anti-aliased by drawing at 2x."""
    s = 2
    img = Image.new("L", (view.width * s, view.height * s), 0); d = ImageDraw.Draw(img)
    for line in polylines:
        if len(line) < 2 or not geo.bbox_hits(line, view):
            continue
        pts = [tuple(c * s for c in view.px(lon, lat)) for lon, lat in line]
        d.line(pts, fill=255, width=max(1, int(round(width_px * s))), joint="curve")
    return np.asarray(img.resize((view.width, view.height), Image.LANCZOS), np.float32) / 255.0


def distance(mask: np.ndarray) -> np.ndarray:
    """For every pixel OUTSIDE the mask: distance (pixels) to the nearest mask pixel. Inside = 0."""
    return ndimage.distance_transform_edt(mask < 0.5).astype(np.float32)


def blur(img: np.ndarray, sigma: float) -> np.ndarray:
    if img.ndim == 3:
        return np.stack([ndimage.gaussian_filter(img[..., c], sigma) for c in range(img.shape[2])], -1)
    return ndimage.gaussian_filter(img, sigma)


# ------------------------------------------------------------------ colour helpers
def rgb(hex_or_tuple) -> np.ndarray:
    """'#c8a46e' or (200,164,110) -> float array (0..1)."""
    if isinstance(hex_or_tuple, str):
        h = hex_or_tuple.lstrip("#")
        hex_or_tuple = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return np.array(hex_or_tuple, np.float32) / 255.0


def mix(base: np.ndarray, color, alpha: np.ndarray) -> np.ndarray:
    """Paint `color` (rgb or an image) over `base` with per-pixel opacity `alpha` (0..1)."""
    a = alpha[..., None] if alpha.ndim == 2 else alpha
    return base * (1 - a) + np.asarray(color, np.float32) * a


def multiply(base: np.ndarray, color, alpha: np.ndarray) -> np.ndarray:
    """Like ink soaking into paper: colour MULTIPLIES the paper so its grain and stains still show through."""
    a = alpha[..., None] if alpha.ndim == 2 else alpha
    return base * (1 - a) + base * np.asarray(color, np.float32) * a


def save(img: np.ndarray, path, mode: str = "RGB") -> None:
    """Save a 0..1 array. mode 'I;16' writes a 16-bit greyscale PNG (smooth gradients for animation thresholds)."""
    if mode == "I;16":
        Image.fromarray((np.clip(img, 0, 1) * 65535).astype(np.uint16)).save(path)
    elif img.ndim == 2:
        Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "L").save(path)
    elif img.shape[2] == 4:
        Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGBA").save(path)
    else:
        Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGB").save(path)

# BATTLE MAPS: the zoomed-in tactical map of one battlefield (reference/maps/05 + 06, Antioch 1098).
#
# Look (zoom of the reference):
#   - light SAND paper with long brush streaks and scattered dark shrubs/rocks
#   - river: teal ribbon with darker banks and a lighter centre
#   - roads: brown double-line tracks
#   - walled TOWN: a dark-brown double wall with square gate towers, thousands of tiny grey-brown house blocks
#     packed inside, lighter streets cutting through, a few green garden specks
#   - HILLS: topographic contour lines (brown) with soft shading on the slope away from the light
#   - labels: town name in big red-brown Roman capitals, river name along the river, small names (Citadel)
#   - a COMPASS ROSE (dark, 8 points) on the open ground
# Units (army blocks + banners) are 3D, built by blender/lib/maps.py from the manifest.
#
# Spec ("kind": "battle"), all positions in KILOMETRES (x east, y north) inside a field of size [w, h]:
# {"kind": "battle", "field": [12, 6.75], "seed": 3,
#  "rivers": [{"path": [[x,y],...], "width": 0.12, "name": "River Orontes", "name_at": [x,y], "name_angle": 55}],
#  "roads": [{"path": [[x,y],...]}],
#  "towns": [{"wall": [[x,y],...], "streets": [[[x,y],[x,y]],...], "gates": [[x,y],...], "name": "Antioch",
#             "name_at": [x,y], "density": 1.0}],
#  "hills": [{"at": [x,y], "radius": 1.5, "height": 1.0}],
#  "forts": [{"at": [x,y], "name": "Citadel"}],
#  "compass": [x, y],
#  "units": [{"id": "crusaders_1", "side": "crimson", "at": [x,y], "facing": 30, "rows": 3, "cols": 2,
#             "banners": 2, "emblem": "cross"}],
#  "beats": [{"t": 1, "do": "move", "id": "crusaders_1", "to": [x,y], "dur": 3}]}
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from tc.maps import geo, labels as L, raster as R

SAND, SAND_DARK, SHRUB = "#d4b47c", "#a07a46", "#4c5a3a"
RIVER, RIVER_BANK = "#3f8a92", "#2c5f66"
ROAD, WALL, HOUSE, HOUSE_DARK = "#7a5838", "#4a3020", "#9c8a72", "#5e5040"
CONTOUR = "#9a7446"


def smooth(path, rounds: int = 3, wobble: float = 0.0, rng=None):
    """Chaikin corner cutting: turns a few research points into a smooth flowing line (rivers, roads).
    wobble (km) adds small natural meanders between the points."""
    pts = [tuple(p) for p in path]
    if wobble and rng is not None and len(pts) > 1:
        out = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            dx, dy = b[0] - a[0], b[1] - a[1]; L_ = math.hypot(dx, dy) or 1
            k = (rng.random() - 0.5) * 2 * wobble
            out += [(m[0] - dy / L_ * k, m[1] + dx / L_ * k), b]
        pts = out
    for _ in range(rounds):
        new = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            new += [(a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25), (a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75)]
        new.append(pts[-1]); pts = new
    return pts


def field_view(spec: dict, width: int) -> geo.View:
    w, h = spec.get("field", [12, 6.75])
    return geo.View(0, 0, w, h, width, flat=True)


def sand_paper(h: int, w: int, rng) -> np.ndarray:
    """Light sand paper: base + big soft patches + long horizontal brush streaks + grain."""
    img = np.empty((h, w, 3), np.float32); img[:] = R.rgb(SAND)
    patches = R.fbm(h, w, w / 6, 4, rng)
    img = R.mix(img, R.rgb(SAND_DARK), 0.4 * R.smoothstep(0.5, 1.0, patches))
    # brush streaks: noise stretched 12x along x
    small = R.fbm(max(8, h // 3), max(8, w // 36), 6, 3, rng)
    streak = ndimage.zoom(small, (h / small.shape[0], w / small.shape[1]), order=1)[:h, :w]
    img = img * (0.9 + 0.16 * streak[..., None])
    img = img * (0.97 + 0.05 * rng.random((h, w), dtype=np.float32)[..., None])
    # dark brush HATCHING in patches (reference ground: scratchy strokes of darker ochre, like a dry brush)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    unit = w / 1000
    ph = (yy + xx * 0.25 + R.fbm(h, w, w / 30, 2, rng) * 8 * unit) / (2.2 * unit)
    lines = 1 - R.smoothstep(0.0, 0.25, np.abs(ph - np.round(ph)))
    patch = R.smoothstep(0.42, 0.66, R.fbm(h, w, w / 14, 3, rng)) * R.smoothstep(0.4, 0.6, R.fbm(h, w, 8 * unit, 2, rng))
    img = R.multiply(img, R.rgb("#6a4a2a"), lines * patch * 0.8)
    grit = R.blur((rng.random((h, w), dtype=np.float32) > 0.993).astype(np.float32), 0.5 * unit) * 3
    img = R.multiply(img, R.rgb("#5a4028"), np.clip(grit, 0, 1) * 0.5)
    return np.clip(img, 0, 1)


def hills_layer(img, view, hills, rng):
    """Height field = sum of noisy bumps; brown contour lines at even heights; shade on the far (south-east) side."""
    h, w = img.shape[:2]
    if not hills:
        return img, np.zeros((h, w), np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    H = np.zeros((h, w), np.float32)
    for hl in hills:
        cx, cy = view.px(*hl["at"]); r = view.km_px(hl.get("radius", 1.5))
        d = np.hypot(xx - cx, yy - cy) / r
        H += hl.get("height", 1.0) * np.exp(-d ** 2 * 1.6)
    warp = R.fbm(h, w, w / 18, 4, rng)
    H = H * (0.75 + 0.5 * warp)
    unit = w / 1000
    levels = 11
    ph = H * levels
    line = (1 - R.smoothstep(0.0, 0.09, np.abs(ph - np.round(ph)))) * (H > 0.06)
    gy, gx = np.gradient(R.blur(H, 2 * unit))
    shade = np.clip((gx + gy) * 60 * unit, 0, 1)                 # light from the north-west: SE slopes darker
    img = R.multiply(img, R.rgb("#8a6a40"), shade * 0.5)
    img = R.mix(img, R.rgb("#f0d9a6"), np.clip(-(gx + gy) * 40 * unit, 0, 1) * 0.35)    # lit slopes paler
    img = R.multiply(img, R.rgb(CONTOUR), line * 0.75)
    return img, H


def shrubs(img, view, rng, avoid):
    """Scattered dark shrubs and rocks on open ground (the reference's ground is speckled with them)."""
    h, w = img.shape[:2]; unit = w / 1000
    S = 2
    lay = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    n = int(w * h / (unit * unit) / 420)
    for _ in range(n):
        x, y = rng.random() * w, rng.random() * h
        if avoid[int(y), int(x)] > 0.3:
            continue
        r = unit * (0.5 + rng.random() * 1.1) * S
        col = (58, 70, 46, 230) if rng.random() < 0.6 else (90, 70, 48, 220)
        d.ellipse([x * S - r, y * S - r * 0.8, x * S + r, y * S + r * 0.8], fill=col)
    lay = np.asarray(lay.resize((w, h), Image.LANCZOS), np.float32) / 255
    return R.mix(img, lay[..., :3], lay[..., 3] * 0.8)


def river_layer(img, view, rivers, rng=None):
    m_all = np.zeros(img.shape[:2], np.float32)
    for rv in rivers:
        rv = dict(rv); rv["path"] = smooth(rv["path"], 4, rv.get("meander", 0.25), rng)
        wpx = view.km_px(rv.get("width", 0.12))
        bank = R.lines_mask(view, [rv["path"]], wpx * 1.35)
        water = R.lines_mask(view, [rv["path"]], wpx)
        centre = R.lines_mask(view, [rv["path"]], wpx * 0.35)
        img = R.mix(img, R.rgb(RIVER_BANK), bank * 0.9)
        img = R.mix(img, R.rgb(RIVER), water)
        img = R.mix(img, R.rgb("#5aa6a8"), R.blur(centre, wpx * 0.3) * 0.5)
        m_all = np.maximum(m_all, bank)
    return img, m_all


def road_layer(img, view, roads):
    unit = view.width / 1000
    m_all = np.zeros(img.shape[:2], np.float32)
    for rd in roads:
        path = smooth(rd["path"], 3)
        outer = R.lines_mask(view, [path], 4.4 * unit)
        inner = R.lines_mask(view, [path], 2.4 * unit)
        img = R.mix(img, R.rgb(ROAD), outer * 0.9)
        img = R.mix(img, R.rgb("#c9a774"), inner * 0.9)                     # pale track between the two lines
        m_all = np.maximum(m_all, outer)
    return img, m_all


def town_layer(img, view, town, rng):
    """Packed tiny houses inside the wall, streets left clear, double wall + gate towers on top."""
    h, w = img.shape[:2]; unit = w / 1000
    inside = R.polygons_mask(view, [[[tuple(p) for p in town["wall"]]]], supersample=2)
    streets = R.lines_mask(view, town.get("streets", []), 2.6 * unit) if town.get("streets") else np.zeros_like(inside)
    # lanes: a loose random network so the blocks read as a city, not a carpet
    # lanes between city blocks: edges of random cells (Voronoi-like via nearest of random seeds)
    from scipy.spatial import cKDTree
    seeds = rng.random((max(8, int(inside.sum() / (38 * unit) ** 2)), 2)) * [w, h]
    gy, gx = np.mgrid[0:h:2, 0:w:2]
    dd, _ = cKDTree(seeds).query(np.stack([gx.ravel(), gy.ravel()], -1), k=2)
    edge = (dd[:, 1] - dd[:, 0]).reshape(gx.shape) < 1.6 * unit
    lanes = ndimage.zoom(edge.astype(np.float32), 2, order=0)[:h, :w]
    streets = np.maximum(streets, lanes)
    S = 2
    lay = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sp = 2.3 * unit / max(0.4, town.get("density", 1.0)) ** 0.5
    ys = np.arange(0, h, sp)
    pts = []
    for y in ys:
        for x in np.arange(0, w, sp):
            jx, jy = x + (rng.random() - 0.5) * sp * 0.8, y + (rng.random() - 0.5) * sp * 0.8
            xi, yi = int(jx), int(jy)
            if 0 <= xi < w and 0 <= yi < h and inside[yi, xi] > 0.6 and streets[yi, xi] < 0.2 and rng.random() < 0.88:
                pts.append((jy, jx))
    pts.sort()
    for y, x in pts:                                # back to front: little blocks with a lit roof + dark side
        s = unit * (1.05 + rng.random() * 0.75) * S
        X, Y = x * S, y * S
        v = 120 + rng.random() * 60                 # one brightness per house: grey-brown stone, never coloured
        roof = (int(v), int(v * 0.9), int(v * 0.74), 255)
        dv = 40 + rng.random() * 22
        shade = (int(dv), int(dv * 0.86), int(dv * 0.7), 255)
        d.rectangle([X - s, Y - s * 0.6, X + s, Y + s * 0.8], fill=shade)
        d.rectangle([X - s, Y - s * 0.9, X + s * 0.75, Y + s * 0.35], fill=roof)
        if rng.random() < 0.04:                     # a garden / tree
            d.ellipse([X - s, Y - s, X + s, Y + s], fill=(58, 72, 48, 255))
    lay = np.asarray(lay.resize((w, h), Image.LANCZOS), np.float32) / 255
    img = R.mix(img, R.rgb("#c8ad80"), inside * 0.5)                          # town ground slightly paler/dustier
    img = R.mix(img, lay[..., :3], lay[..., 3])
    # the wall: dark band + pale walkway line inside it, square towers along it, bigger gatehouses
    ring = [tuple(p) for p in town["wall"]] + [tuple(town["wall"][0])]
    outer = R.lines_mask(view, [ring], 6.5 * unit)
    walk = R.lines_mask(view, [ring], 2.0 * unit)
    img = R.mix(img, R.rgb(WALL), outer)
    img = R.mix(img, R.rgb("#8a6a50"), walk)
    tow = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0)); d = ImageDraw.Draw(tow)
    for (x0, y0), (x1, y1) in zip(ring[:-1], ring[1:]):
        a, b = view.px(x0, y0), view.px(x1, y1)
        L_ = math.hypot(b[0] - a[0], b[1] - a[1]); n = max(1, int(L_ / (60 * unit)))
        for k in range(n + 1):
            t = k / n; x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            s = 4.6 * unit * S
            d.rectangle([x * S - s, y * S - s, x * S + s, y * S + s], fill=(74, 48, 32, 255), outline=(40, 24, 14, 255), width=S)
            d.rectangle([x * S - s * 0.45, y * S - s * 0.45, x * S + s * 0.45, y * S + s * 0.45], outline=(150, 118, 88, 255), width=S)
    for g in town.get("gates", []):
        x, y = view.px(*g); s = 7.5 * unit * S
        d.rectangle([x * S - s, y * S - s, x * S + s, y * S + s], fill=(80, 52, 34, 255), outline=(36, 22, 12, 255), width=2 * S)
        d.rectangle([x * S - s * 0.55, y * S - s * 0.55, x * S + s * 0.55, y * S + s * 0.55], outline=(160, 128, 96, 255), width=2 * S)
    tow = np.asarray(tow.resize((w, h), Image.LANCZOS), np.float32) / 255
    img = R.mix(img, tow[..., :3], tow[..., 3])
    return img, np.maximum(inside, outer)


def compass_rose(size: int) -> Image.Image:
    """An 8-point compass rose in dark ink (long N-S-E-W points, short diagonals, split light/dark faces)."""
    S = 3; W = size * S
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = W / 2
    for k in range(8):
        a = k * math.pi / 4
        r = W * (0.48 if k % 2 == 0 else 0.3); wd = W * (0.07 if k % 2 == 0 else 0.05)
        tip = (c + math.sin(a) * r, c - math.cos(a) * r)
        l = (c + math.sin(a - math.pi / 2) * wd, c - math.cos(a - math.pi / 2) * wd)
        rr = (c + math.sin(a + math.pi / 2) * wd, c - math.cos(a + math.pi / 2) * wd)
        d.polygon([(c, c), l, tip], fill=(40, 34, 30, 255))
        d.polygon([(c, c), rr, tip], fill=(92, 80, 68, 255))
    d.ellipse([c - W * 0.04, c - W * 0.04, c + W * 0.04, c + W * 0.04], fill=(40, 34, 30, 255))
    f = L.font("Cinzel.ttf", int(size * 0.12 * S), weight=700)
    d.text((c, W * 0.0), "N", font=f, fill=(40, 34, 30, 255), anchor="mt")
    return im.resize((size, size), Image.LANCZOS)


def paint_battle(spec: dict, out: Path, width: int = 6144, preview: bool = False) -> dict:
    """Paint a battle field pack (same manifest format as world maps + 'units', 'forts')."""
    out.mkdir(parents=True, exist_ok=True)
    view = field_view(spec, width); unit = width / 1000
    rng = np.random.default_rng(int(spec.get("seed", 3)))
    img = sand_paper(view.height, view.width, rng)
    img, H = hills_layer(img, view, spec.get("hills", []), rng)
    img, rmask = river_layer(img, view, spec.get("rivers", []), rng)
    img, roadm = road_layer(img, view, spec.get("roads", []))
    tmask = np.zeros(img.shape[:2], np.float32)
    for t in spec.get("towns", []):
        img, m = town_layer(img, view, t, rng); tmask = np.maximum(tmask, m)
    img = shrubs(img, view, rng, np.maximum(np.maximum(rmask, roadm), tmask))
    R.save(img, out / "base.png")
    def uvk(p):
        x, y = view.px(*p); return [round(x / view.width, 5), round(1 - y / view.height, 5)]
    man = {"kind": "battle", "aspect": round(view.width / view.height, 5), "width_px": view.width,
           "height_px": view.height, "field_km": spec.get("field", [12, 6.75]), "base": "base.png",
           "territories": [], "labels": [], "arrows": [], "pulses": [], "battles": [], "units": [], "forts": [],
           "beats": spec.get("beats", [])}
    def add_label(im, name, at, kind, ident, angle=0.0):
        p = out / f"lbl_{name}.png"
        if angle:
            im = im.rotate(angle, resample=Image.BICUBIC, expand=True)
        im.save(p)
        man["labels"].append({"id": ident, "kind": kind, "file": p.name, "uv": uvk(at),
                              "w": round(im.width / view.width, 5), "h": round(im.height / view.width, 5)})
    for i, t in enumerate(spec.get("towns", [])):
        if t.get("name"):
            f = L.font("Cinzel.ttf", int(t.get("name_size", 16) * unit), weight=800)
            im = L.curved_text(t["name"].upper(), f, 0, 0.05, (150, 44, 26, 255), 0)
            add_label(L.with_shadow(im, unit * 0.6, (int(unit * 0.4), int(unit * 0.5)), 0.35), f"town{i}",
                      t.get("name_at", t["wall"][0]), "region", t.get("id", f"town{i}"))
    for i, rv in enumerate(spec.get("rivers", [])):
        if rv.get("name"):
            im = L.sea_label(rv["name"], int(rv.get("name_size", 9) * unit), 0)
            add_label(im, f"river{i}", rv["name_at"], "sea", f"river{i}", rv.get("name_angle", 0))
    for i, fo in enumerate(spec.get("forts", [])):
        man["forts"].append({"id": fo.get("id", f"fort{i}"), "uv": uvk(fo["at"])})
        if fo.get("name"):
            f = L.font("IMFellEnglish.ttf", int(fo.get("name_size", 9) * unit))
            im = L.curved_text(fo["name"], f, 0, 0.02, (60, 40, 24, 255), 0)
            add_label(im, f"fort{i}", [fo["at"][0], fo["at"][1] - 0.45], "sea", f"fortname{i}")
    if spec.get("compass"):
        im = compass_rose(int(70 * unit)); p = out / "lbl_compass.png"; im.save(p)
        man["labels"].append({"id": "compass", "kind": "sea", "file": p.name, "uv": uvk(spec["compass"]),
                              "w": round(im.width / view.width, 5), "h": round(im.height / view.width, 5)})
    inks = {"crimson": (150, 26, 24), "teal": (24, 96, 120), "green": (40, 100, 40), "purple": (80, 50, 110), "gold": (140, 100, 30)}
    done_banners = set()
    for u in spec.get("units", []):
        e = dict(u); e["uv"] = uvk(u["at"])
        bn = f"banner_{u.get('emblem', 'cross')}_{u.get('side', 'crimson')}.png"
        if bn not in done_banners:                # repaint every run (a stale file once hid a new design)
            done_banners.add(bn)
            L.banner(u.get("emblem", "cross"), inks.get(u.get("side", "crimson"), (60, 40, 30))).save(out / bn)
        e["banner"] = bn
        e.setdefault("scale", 2.4)                  # battle blocks are big and chunky (reference frame 05)
        e["color"] = list(map(float, R.rgb({"crimson": "#a3161a", "teal": "#2a8fb0", "green": "#3f8a3a",
                                            "purple": "#5a3a78", "gold": "#c08a2a"}.get(u.get("side", "crimson"), u.get("side", "crimson")))))
        man["units"].append(e)
    for b in man["beats"]:                        # move targets -> uv too
        if "to" in b:
            b["to_uv"] = uvk(b["to"])
    man["km_per_uv"] = spec.get("field", [12, 6.75])[0]
    if preview:
        pv = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        for e in man["labels"]:
            im = Image.open(out / e["file"])
            cx, cy = e["uv"][0] * view.width, (1 - e["uv"][1]) * view.height
            pv.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))
        pv.convert("RGB").save(out / "preview.png")
    (out / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    return man

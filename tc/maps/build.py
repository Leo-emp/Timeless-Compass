# MAP PACK BUILDER: one map spec (JSON) -> every texture Blender needs + a manifest.
#
#   python -m tc map paint jobs/<id>/maps/<name>.json [--out DIR] [--width 6144] [--preview]
#
# The spec (written by the agent from research; all positions are [longitude, latitude]):
# {
#   "view": {"center": [30, 39], "span_lon": 44},          # what part of the world (16:9)
#   "seed": 7,
#   "biomes": {"forest": [[lon0,lat0,lon1,lat1]], "desert": [...], "steppe": [...]},   # optional overrides
#   "territories": [{"id": "byz", "name": ["Byzantine", "Empire"], "color": "purple", "emblem": "chirho",
#                    "heart": [29, 41], "border": [[lon, lat], ...], "label_at": [27, 39.5], "label_size": 26,
#                    "bend": 8}],
#   "seas":   [{"text": "Black Sea", "at": [34, 43.3], "size": 12, "bend": 4}],
#   "places": [{"text": "Constantinople", "at": [28.97, 41.01], "icon": "capital", "size": 10}],
#   "date": "c.1097 AD",
#   "arrows": [{"id": "march", "path": [[lon, lat], ...], "color": "crimson", "width": 9}],
#   "pulses": [{"id": "call", "at": [3.1, 45.8]}],
#   "battles": [{"id": "dorylaeum", "at": [30.5, 39.8]}],
#   "beats": [{"t": 0.0, "do": "grow", "id": "byz", "dur": 2.0}, ...]     # timeline (see blender/lib/maps.py)
# }
# Sizes are in UNITS = 1/1000 of the map width, so a spec looks the same at any texture resolution.
# Output folder: base.png, terr_<id>.png (R = area, G = grow order, B = emblem pattern), lbl_<n>.png, manifest.json.
# Manifest positions are UV (u = 0 left .. 1 right, v = 0 bottom .. 1 top, Blender's convention).
import json
from pathlib import Path

import numpy as np
from PIL import Image

from tc.maps import base, geo, labels as L, raster as R, stamps, territory as T


def view_from(spec: dict, width: int) -> geo.View:
    v = spec["view"]
    if "box" in v:
        lon0, lat0, lon1, lat1 = v["box"]
        return geo.View(lon0, lat0, lon1, lat1, width)
    return geo.view_16x9(v["center"][0], v["center"][1], v["span_lon"], width)


def uv(view: geo.View, lonlat) -> list[float]:
    x, y = view.px(*lonlat)
    return [round(x / view.width, 5), round(1 - y / view.height, 5)]


def _label_entry(im: Image.Image, out: Path, name: str, view: geo.View, at, kind: str, ident: str) -> dict:
    p = out / f"lbl_{name}.png"; im.save(p)
    return {"id": ident, "kind": kind, "file": p.name, "uv": uv(view, at),
            "w": round(im.width / view.width, 5), "h": round(im.height / view.width, 5)}   # sizes as share of map width


def paint(spec: dict, out: Path, width: int = 6144, preview: bool = False) -> dict:
    """Paint everything in `spec` into `out`. Returns the manifest (also saved as manifest.json)."""
    out.mkdir(parents=True, exist_ok=True)
    view = view_from(spec, width)
    unit = width / 1000
    seed = int(spec.get("seed", 7))
    rng = np.random.default_rng(seed)
    img, land = base.paint_base(view, seed)
    img = stamps.paint_stamps(img, view, land, seed=seed + 1, rules=spec.get("biomes"))
    if spec.get("decor"):
        img = stamps.paint_decor(img, view, spec["decor"], seed + 2)
    R.save(img, out / "base.png")
    man = {"aspect": round(view.width / view.height, 5), "width_px": view.width, "height_px": view.height,
           "view": [view.lon0, view.lat0, view.lon1, view.lat1], "base": "base.png",
           "territories": [], "labels": [], "arrows": [], "pulses": [], "battles": [],
           "beats": spec.get("beats", [])}
    # ---- territories (each pixel belongs to one realm: later in the list wins)
    terrs = spec.get("territories", [])
    masks = T.exclusive([T.territory_mask(view, [tuple(p) for p in t["border"]], land, rng) for t in terrs]) if terrs else []
    preview_img = img.copy() if preview else None
    for t, m in zip(terrs, masks):
        g = T.grow_map(view, m, t.get("heart") or t["border"][0], rng)
        e = T.emblem_layer(view, m, t.get("emblem", "ring"), rng)
        pack = np.stack([m, g, e[..., 3]], -1)
        R.save(pack, out / f"terr_{t['id']}.png")
        man["territories"].append({"id": t["id"], "file": f"terr_{t['id']}.png",
                                   "color": list(map(float, R.rgb(T.COLORS.get(t["color"], t["color"]))))})
        if preview:
            preview_img = T.paint_territory(preview_img, m, t["color"], e, view)
        if t.get("name"):
            im = L.region_label(t["name"], int(t.get("label_size", 22) * unit), t.get("bend", 6))
            man["labels"].append(_label_entry(im, out, t["id"], view, t.get("label_at") or t.get("heart"), "region", t["id"]))
    # ---- sea names, places, date
    for i, s in enumerate(spec.get("seas", [])):
        im = L.sea_label(s["text"], int(s.get("size", 11) * unit), s.get("bend", 4))
        man["labels"].append(_label_entry(im, out, f"sea{i}", view, s["at"], "sea", s.get("id", f"sea{i}")))
    for i, p in enumerate(spec.get("places", [])):
        im = L.place_tag(p["text"], int(p.get("size", 9) * unit), p.get("icon", "city"), seed=seed + i)
        e = _label_entry(im, out, f"place{i}", view, p["at"], "place", p.get("id", p["text"].lower().replace(" ", "_")))
        e["anchor"] = "bottom"                     # tags stand ON the city point (their bottom edge sits there)
        man["labels"].append(e)
    if spec.get("date"):
        im = L.date_strip(spec["date"], int(spec.get("date_size", 14) * unit))
        p = out / "lbl_date.png"; im.save(p)
        man["date"] = {"file": p.name, "w": round(im.width / view.width, 5), "h": round(im.height / view.width, 5)}
    # ---- moving things (built in 3D by Blender): arrows, pulse rings, battle markers
    for a in spec.get("arrows", []):
        man["arrows"].append({"id": a["id"], "uv": [uv(view, p) for p in a["path"]],
                              "color": list(map(float, R.rgb(T.COLORS.get(a.get("color", "crimson"), a.get("color", "crimson"))))),
                              "width": a.get("width", 9) / 1000})
    # ---- armies on the world map: banner groups (no blocks) that march with "move" beats
    man["units"] = []
    inks = {"crimson": (150, 26, 24), "teal": (24, 96, 120), "green": (40, 100, 40), "purple": (80, 50, 110), "gold": (140, 100, 30)}
    done_banners = set()
    for a in spec.get("armies", []):
        bn = f"banner_{a.get('emblem', 'cross')}_{a.get('side', 'crimson')}.png"
        if bn not in done_banners:                # repaint every run (a stale file once hid a new design)
            done_banners.add(bn)
            L.banner(a.get("emblem", "cross"), inks.get(a.get("side", "crimson"), (60, 40, 30))).save(out / bn)
        man["units"].append({"id": a["id"], "uv": uv(view, a["at"]), "banner": bn, "rows": 0, "cols": 0,
                             "banners": a.get("banners", 1), "facing": 0, "scale": a.get("scale", 1.6),
                             "color": list(map(float, R.rgb(T.COLORS.get(a.get("side", "crimson"), a.get("side", "crimson")))))})
    # ---- leader portrait cards (our own cast renders in a parchment frame; slide in at the frame's side)
    man["cards"] = []
    for c in spec.get("cards", []):
        pic = Image.open(c["portrait"]) if c.get("portrait") and Path(c["portrait"]).exists() else None
        im = L.portrait_card(pic, c["name"], int(c.get("size", 60) * unit))
        p = out / f"card_{c['id']}.png"; im.save(p)
        man["cards"].append({"id": c["id"], "file": p.name, "aspect": round(im.width / im.height, 5)})
    routes = {a["id"]: a["path"] for a in spec.get("arrows", [])}
    for b in man["beats"]:
        if "to" in b:
            b["to_uv"] = uv(view, b["to"])
        if b.get("along") in routes:                  # march along an arrow's route, point by point
            b["path_uv"] = [uv(view, p) for p in routes[b["along"]]]
            b["to_uv"] = b["path_uv"][-1]
    for p in spec.get("pulses", []):
        man["pulses"].append({"id": p["id"], "uv": uv(view, p["at"])})
    for b in spec.get("battles", []):
        man["battles"].append({"id": b["id"], "uv": uv(view, b["at"])})
    if preview:                                     # flat 2D preview with every label laid on (for quick review)
        pv = Image.fromarray((np.clip(preview_img, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        for e in man["labels"]:
            im = Image.open(out / e["file"])
            cx, cy = e["uv"][0] * view.width, (1 - e["uv"][1]) * view.height
            y = cy - im.height if e.get("anchor") == "bottom" else cy - im.height / 2
            pv.alpha_composite(im, (int(cx - im.width / 2), int(y)))
        pv.convert("RGB").save(out / "preview.png")
    (out / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    return man

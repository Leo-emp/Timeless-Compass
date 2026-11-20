# BASE MAP PAINTER: parchment + engraved sea + inked coastline + land (stamps come from stamps.py).
#
# Look targets (reference/maps/01 + 02):
#   - paper: warm cream-tan, mottled, darker stains, faint fibres; the land IS the paper (tan, with speckle)
#   - sea: muted grey-teal, darker in open water, lighter in a band hugging the coast,
#          covered in fine engraved ripple lines that run PARALLEL to the coast (like a copper-plate engraving)
#   - coast: a thin dark-brown ink line, plus a soft golden "halo" just inside the land edge
#   - rivers: thin blue-grey ink lines; lakes like small seas
import numpy as np

from tc.maps import geo, raster as R

PALETTE = {
    "paper": "#d9be8a",        # parchment (the land colour too)
    "paper_dark": "#a9844e",   # stains / speckle
    "sea_deep": "#6d8580",     # open sea
    "sea_shallow": "#97a99b",  # band along the coast
    "ink": "#4a3420",          # coastline + engraving ink (brown-black, never pure black)
    "wave_ink": "#3f5c5e",     # sea ripple engraving
    "river": "#5f7f80",
    "halo": "#f0d48a",         # golden glow just inside the coast
}


def paper(h: int, w: int, rng: np.random.Generator) -> np.ndarray:
    """Aged parchment: base colour, large soft stains, medium mottling, fine grain, fibres."""
    base = np.empty((h, w, 3), np.float32); base[:] = R.rgb(PALETTE["paper"])
    stains = R.fbm(h, w, w / 5, 5, rng)                       # big blotchy age stains
    mottle = R.fbm(h, w, w / 40, 4, rng)                      # medium unevenness
    grain = rng.random((h, w), dtype=np.float32)              # pixel grain
    dark = R.rgb(PALETTE["paper_dark"])
    img = R.mix(base, dark, 0.6 * R.smoothstep(0.45, 1.0, stains))
    img = img * (0.86 + 0.2 * mottle[..., None])
    img = img * (0.97 + 0.05 * grain[..., None])
    # fibres: long thin streaks — stretched noise in one direction
    fib = R.value_noise(h, max(2, w // 60), 2.0, rng)
    from scipy import ndimage
    fib = ndimage.zoom(fib, (1, w / fib.shape[1]), order=1)[:, :w]
    img = img * (0.985 + 0.03 * fib[..., None])
    return np.clip(img, 0, 1)


def land_mask(view: geo.View) -> np.ndarray:
    polys = []
    for f in geo.load("land") + geo.load("islands"):
        polys += geo.rings(f["geometry"])
    land = R.polygons_mask(view, polys, supersample=2)
    lakes = []
    for f in geo.load("lakes"):
        if (f["properties"].get("scalerank") or 9) <= 6:         # only lakes big enough to read on screen
            lakes += geo.rings(f["geometry"])
    if lakes:
        land = land * (1 - R.polygons_mask(view, lakes, supersample=2))
    return land


def sea_layer(view: geo.View, land: np.ndarray, rng: np.random.Generator, base: np.ndarray) -> np.ndarray:
    """Colour the sea and engrave it. Reference (zoom of frame 02): soft grey-teal, slightly lighter near the
    coast, covered EVERYWHERE in fine low-contrast wavy scribbles (short wave strokes), plus only one or two
    faint ripple lines hugging the coast. No heavy contour rings."""
    h, w = land.shape
    dist = R.distance(land)                                    # pixels from the nearest coast (0 on land)
    unit = w / 1000                                            # 1 "unit" = 1/1000 of the map width
    # --- colour: shallow band near the coast -> deep in open sea, with blotchy variation (paper under water)
    depth = R.smoothstep(0, 70 * unit, dist) * (0.7 + 0.3 * R.fbm(h, w, w / 8, 3, rng))
    sea = R.mix(np.broadcast_to(R.rgb(PALETTE["sea_shallow"]), (h, w, 3)).copy(), R.rgb(PALETTE["sea_deep"]), depth)
    sea = sea * (0.88 + 0.14 * R.fbm(h, w, w / 30, 4, rng))[..., None]
    # --- scribble waves: rows of small arcs. y position wobbles with x (sine) and with noise, so each row is a
    #     wavy line; rows are broken into short strokes by a dash noise -> looks like hand-drawn ripples.
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = R.fbm(h, w, w / 14, 3, rng) * 10
    row = (yy + 0.8 * unit * np.sin(xx / (1.7 * unit) + warp)) / (1.9 * unit)
    stroke = 1 - R.smoothstep(0.0, 0.17, np.abs(row - np.round(row)))
    dash = R.smoothstep(0.42, 0.62, R.fbm(h, w, 6 * unit, 2, rng))
    scribble = stroke * dash * (0.55 + 0.45 * R.fbm(h, w, w / 20, 2, rng))
    # --- two faint coast-hugging ripple lines
    phase = (dist + (R.fbm(h, w, w / 25, 3, rng) - 0.5) * 3 * unit) / (4.5 * unit)
    hug = (1 - R.smoothstep(0.0, 0.16, np.abs(phase - np.round(phase)))) * (dist > 3.5 * unit) * (dist < 9 * unit)
    engrave = np.clip(scribble * 0.32 + hug * 0.12, 0, 1)
    sea = R.multiply(sea, R.rgb(PALETTE["wave_ink"]), engrave)
    # tiny pale flecks (the reference sea has light dots: paper showing through the wash)
    fleck = R.blur((rng.random((h, w), dtype=np.float32) > 0.9975).astype(np.float32), 0.7 * unit) * 3
    sea = R.mix(sea, R.rgb("#c9d3c4"), np.clip(fleck, 0, 1) * 0.5)
    water = 1 - land
    return R.mix(base, sea, water)


def coast_layer(img: np.ndarray, land: np.ndarray, view: geo.View, rng: np.random.Generator) -> np.ndarray:
    """Reference coast: a BRIGHT golden band on the land side (like light catching the paper edge), fading
    inland over a few pixels, and only a THIN brown ink edge (no heavy black outline)."""
    h, w = land.shape
    unit = w / 1000
    inner = R.distance(1 - land)                               # inside land: distance to the sea
    width = 7 * unit * (0.6 + 0.8 * R.fbm(h, w, 30 * unit, 3, rng))   # band width varies along the coast
    halo = np.exp(-inner / np.maximum(width, 1)) * land
    img = R.mix(img, R.rgb(PALETTE["halo"]), np.clip(halo, 0, 1) * 0.75)
    soft = R.blur(land, 0.5 * unit)
    edge = np.clip(1 - np.abs(soft - 0.5) * 2.6, 0, 1)        # a thin ridge where land meets water
    return R.multiply(img, R.rgb(PALETTE["ink"]) * 0.9, edge * 0.55)


def rivers_layer(img: np.ndarray, view: geo.View, max_rank: int = 5) -> np.ndarray:
    """Major rivers as thin ink lines, slightly thicker for the big ones (scalerank 0-2)."""
    unit = view.width / 1000
    for ranks, wpx in (((0, 1, 2), 1.3 * unit), ((3, 4, 5), 0.8 * unit)):
        ls = []
        for f in geo.load("rivers"):
            r = f["properties"].get("scalerank")
            if r in ranks and r <= max_rank:
                ls += geo.lines(f["geometry"])
        if ls:
            m = R.lines_mask(view, ls, wpx)
            img = R.multiply(img, R.rgb(PALETTE["river"]), m * 0.7)
    return img


def land_tint(img: np.ndarray, land: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Land is the paper, with a fine ochre speckle (the reference's land looks dusted with tiny dots)."""
    h, w = land.shape
    speck = (rng.random((h, w), dtype=np.float32) > 0.985).astype(np.float32)
    speck = R.blur(speck, 0.6) * 2.5
    return R.multiply(img, R.rgb(PALETTE["paper_dark"]) * 0.85, np.clip(speck, 0, 1) * land * 0.5)


def paint_base(view: geo.View, seed: int = 7) -> tuple[np.ndarray, np.ndarray]:
    """The whole base map (without stamps). Returns (rgb image, land mask)."""
    rng = np.random.default_rng(seed)
    land = land_mask(view)
    img = paper(view.height, view.width, rng)
    img = land_tint(img, land, rng)
    img = sea_layer(view, land, rng, img)
    img = rivers_layer(img, view)
    img = coast_layer(img, land, view, rng)
    return img, land

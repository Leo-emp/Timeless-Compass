# GEOGRAPHY: loads Natural Earth (public domain) shapes and turns longitude/latitude into texture pixels.
#
# Natural Earth files live in library/maps/ne/ (git-ignored, ~30 MB, fetched once by `python -m tc map fetch`).
# Projection: "equirectangular with a cosine squeeze" — x = longitude * cos(centre latitude), y = latitude.
# It is the simplest map projection that still looks right for a region the size of the Mediterranean
# (the reference's maps look like this: no strong curvature, Europe not stretched).
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from tc.paths import LIBRARY

NE_DIR = LIBRARY / "maps" / "ne"
NE_BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
NE_FILES = {                                    # short name -> Natural Earth file (10m = the most detailed scale)
    "land": "ne_10m_land",
    "islands": "ne_10m_minor_islands",
    "lakes": "ne_10m_lakes",
    "rivers": "ne_10m_rivers_lake_centerlines",
    "regions": "ne_10m_geography_regions_polys",   # named mountain ranges, deserts, plateaus...
}


@dataclass(frozen=True)
class View:
    """The window of the world the map shows. lon/lat box + texture width in pixels; height follows the box."""
    lon0: float          # west edge (degrees)
    lat0: float          # south edge
    lon1: float          # east edge
    lat1: float          # north edge
    width: int = 6144    # texture width in pixels (6144 keeps detail when the camera pushes in to a city)
    flat: bool = False   # True = a local battlefield in KILOMETRES (x east, y north), no globe squeeze

    @property
    def squeeze(self) -> float:
        """cos(centre latitude): one degree of longitude is shorter than one of latitude away from the equator."""
        if self.flat:
            return 1.0
        return math.cos(math.radians((self.lat0 + self.lat1) / 2))

    @property
    def px_per_deg(self) -> float:
        return self.width / ((self.lon1 - self.lon0) * self.squeeze)

    @property
    def height(self) -> int:
        return int(round((self.lat1 - self.lat0) * self.px_per_deg))

    def px(self, lon: float, lat: float) -> tuple[float, float]:
        """Longitude/latitude -> pixel (x right, y DOWN, like every image)."""
        x = (lon - self.lon0) * self.squeeze * self.px_per_deg
        y = (self.lat1 - lat) * self.px_per_deg
        return x, y

    def lonlat(self, x: float, y: float) -> tuple[float, float]:
        """Pixel -> longitude/latitude (the inverse of px)."""
        return self.lon0 + x / (self.squeeze * self.px_per_deg), self.lat1 - y / self.px_per_deg

    def km_px(self, km: float) -> float:
        """How many pixels a distance in km covers (1 degree of latitude = 111 km; flat views are in km already)."""
        return km * self.px_per_deg if self.flat else km / 111.0 * self.px_per_deg


def view_16x9(lon_c: float, lat_c: float, span_lon: float, width: int = 6144) -> View:
    """A 16:9 view centred on (lon_c, lat_c) that is `span_lon` degrees of longitude wide."""
    # 16:9 in PIXELS: height/width = 9/16, and width in "squeezed degrees" = span_lon * cos(lat_c)
    span_lat = span_lon * math.cos(math.radians(lat_c)) * 9 / 16
    return View(lon_c - span_lon / 2, lat_c - span_lat / 2, lon_c + span_lon / 2, lat_c + span_lat / 2, width)


@lru_cache(maxsize=8)
def load(name: str) -> list[dict]:
    """All features of one Natural Earth file (cached: the land file is 10 MB of JSON)."""
    path = NE_DIR / f"{NE_FILES[name]}.geojson"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run: python -m tc map fetch")
    return json.loads(path.read_text(encoding="utf-8"))["features"]


def rings(geometry: dict) -> list[list[list[tuple[float, float]]]]:
    """A GeoJSON geometry -> list of polygons; each polygon = [outer ring, hole, hole...]; ring = [(lon, lat)...]."""
    t, c = geometry["type"], geometry["coordinates"]
    if t == "Polygon":
        return [[[tuple(p[:2]) for p in r] for r in c]]
    if t == "MultiPolygon":
        return [[[tuple(p[:2]) for p in r] for r in poly] for poly in c]
    return []


def lines(geometry: dict) -> list[list[tuple[float, float]]]:
    """A GeoJSON line geometry -> list of polylines [(lon, lat)...]."""
    t, c = geometry["type"], geometry["coordinates"]
    if t == "LineString":
        return [[tuple(p[:2]) for p in c]]
    if t == "MultiLineString":
        return [[tuple(p[:2]) for p in l] for l in c]
    return []


def bbox_hits(coords, view: View, margin: float = 2.0) -> bool:
    """Does a ring/polyline touch the view (plus a margin in degrees)? Skips the rest of the world fast."""
    xs = [p[0] for p in coords]; ys = [p[1] for p in coords]
    return not (max(xs) < view.lon0 - margin or min(xs) > view.lon1 + margin or
                max(ys) < view.lat0 - margin or min(ys) > view.lat1 + margin)

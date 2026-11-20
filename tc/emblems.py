# SHIELD EMBLEMS (episemata): every hoplite painted his own device on his aspis. Designs follow Attic black- and
# red-figure vase paintings of c. 520-460 BC (shield blazons on the Berlin Painter, Kleophrades Painter, Douris...):
# a single bold silhouette, black or red on a bronze/cream/red field, sometimes a contrasting rim band.
# Drawn by code (Pillow) into a round, alpha-masked texture that blender/lib/armour.aspis can map onto the shield face.
#   python -m tc emblems out_dir            paints all of them (for review)
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

from tc.cli import register

FIELDS = [(176, 132, 72), (214, 196, 160), (150, 40, 28), (40, 36, 32), (190, 150, 90)]     # bronze, cream, red, black, gold
INKS = {(176, 132, 72): [(25, 20, 18), (140, 30, 20)], (214, 196, 160): [(25, 20, 18), (150, 40, 28)],
        (150, 40, 28): [(25, 20, 18), (214, 196, 160)], (40, 36, 32): [(214, 196, 160), (176, 132, 72)],
        (190, 150, 90): [(25, 20, 18), (140, 30, 20)]}


def _poly(d, pts, c, s, cx, cy):
    d.polygon([(cx + x * s, cy + y * s) for x, y in pts], fill=c)


def _draw(name, d, s, cx, cy, ink, field):
    """Each emblem as simple silhouette geometry in a -1..1 box (s = half size in pixels)."""
    W = max(2, int(s * 0.16))
    if name == 'lambda':                                       # Spartan Λ
        d.line([(cx - 0.55 * s, cy + 0.7 * s), (cx, cy - 0.7 * s), (cx + 0.55 * s, cy + 0.7 * s)], fill=ink, width=int(W * 1.4))
    elif name == 'trident':
        d.line([(cx, cy + 0.8 * s), (cx, cy - 0.55 * s)], fill=ink, width=W)
        d.arc([cx - 0.5 * s, cy - 0.95 * s, cx + 0.5 * s, cy - 0.15 * s], 0, 180, fill=ink, width=W)
        for x in (-0.5, 0, 0.5):
            _poly(d, [(x - 0.12, -0.55), (x + 0.12, -0.55), (x, -0.85)], ink, s, cx, cy)
    elif name == 'star':
        pts = []
        for k in range(16):
            r = 0.85 if k % 2 == 0 else 0.35
            a = math.pi * k / 8
            pts.append((r * math.sin(a), -r * math.cos(a)))
        _poly(d, pts, ink, s, cx, cy)
    elif name == 'crescent':
        d.ellipse([cx - 0.7 * s, cy - 0.7 * s, cx + 0.7 * s, cy + 0.7 * s], fill=ink)
        d.ellipse([cx - 0.45 * s, cy - 0.8 * s, cx + 0.85 * s, cy + 0.6 * s], fill=field)
    elif name == 'wheel':
        d.ellipse([cx - 0.7 * s, cy - 0.7 * s, cx + 0.7 * s, cy + 0.7 * s], outline=ink, width=W)
        for k in range(4):
            a = math.pi * k / 4
            d.line([(cx - 0.7 * s * math.cos(a), cy - 0.7 * s * math.sin(a)), (cx + 0.7 * s * math.cos(a), cy + 0.7 * s * math.sin(a))], fill=ink, width=int(W * 0.7))
        d.ellipse([cx - 0.15 * s, cy - 0.15 * s, cx + 0.15 * s, cy + 0.15 * s], fill=ink)
    elif name == 'club':                                       # Herakles' club
        _poly(d, [(-0.12, 0.8), (0.12, 0.8), (0.3, -0.55), (0.18, -0.8), (-0.18, -0.8), (-0.3, -0.55)], ink, s, cx, cy)
    elif name == 'tripod':
        d.ellipse([cx - 0.5 * s, cy - 0.75 * s, cx + 0.5 * s, cy - 0.15 * s], fill=ink)
        for x in (-0.4, 0.0, 0.4):
            d.line([(cx + x * 0.6 * s, cy - 0.3 * s), (cx + x * s * 1.3, cy + 0.8 * s)], fill=ink, width=int(W * 0.8))
    elif name == 'triskeles':                                  # three running legs
        for k in range(3):
            a = 2 * math.pi * k / 3
            ca, sa = math.cos(a), math.sin(a)
            rot = lambda x, y: (x * ca - y * sa, x * sa + y * ca)
            _poly(d, [rot(-0.1, 0), rot(0.1, 0), rot(0.15, -0.6), rot(0.55, -0.7), rot(0.55, -0.55), rot(-0.05, -0.75)], ink, s, cx, cy)
    elif name == 'eye':                                        # apotropaic eye
        d.ellipse([cx - 0.75 * s, cy - 0.35 * s, cx + 0.75 * s, cy + 0.35 * s], fill=ink)
        d.ellipse([cx - 0.3 * s, cy - 0.3 * s, cx + 0.3 * s, cy + 0.3 * s], fill=field)
        d.ellipse([cx - 0.14 * s, cy - 0.14 * s, cx + 0.14 * s, cy + 0.14 * s], fill=ink)
    elif name == 'gorgon':                                     # gorgoneion: round face, staring eyes, grin, tongue
        d.ellipse([cx - 0.65 * s, cy - 0.65 * s, cx + 0.65 * s, cy + 0.65 * s], fill=ink)
        for x in (-0.25, 0.25):
            d.ellipse([cx + (x - 0.12) * s, cy - 0.32 * s, cx + (x + 0.12) * s, cy - 0.08 * s], fill=field)
        d.rectangle([cx - 0.35 * s, cy + 0.15 * s, cx + 0.35 * s, cy + 0.32 * s], fill=field)
        _poly(d, [(-0.1, 0.32), (0.1, 0.32), (0, 0.6)], (150, 40, 28), s, cx, cy)
        for k in range(10):                                    # snake-hair ring
            a = 2 * math.pi * k / 10
            d.ellipse([cx + (0.75 * math.cos(a) - 0.08) * s, cy + (0.75 * math.sin(a) - 0.08) * s,
                       cx + (0.75 * math.cos(a) + 0.08) * s, cy + (0.75 * math.sin(a) + 0.08) * s], fill=ink)
    elif name in ('owl', 'cock', 'eagle'):                     # standing bird silhouettes
        d.ellipse([cx - 0.35 * s, cy - 0.35 * s, cx + 0.35 * s, cy + 0.6 * s], fill=ink)        # body
        d.ellipse([cx - 0.28 * s, cy - 0.75 * s, cx + 0.28 * s, cy - 0.2 * s], fill=ink)        # head
        if name == 'owl':
            for x in (-0.12, 0.12):
                d.ellipse([cx + (x - 0.08) * s, cy - 0.58 * s, cx + (x + 0.08) * s, cy - 0.42 * s], fill=field)
        elif name == 'cock':
            _poly(d, [(-0.05, -0.75), (0.05, -0.95), (0.18, -0.75)], (150, 40, 28), s, cx, cy)
            _poly(d, [(0.3, 0.1), (0.85, -0.3), (0.75, 0.3), (0.35, 0.45)], ink, s, cx, cy)  # tail
        else:
            _poly(d, [(-0.3, -0.1), (-0.9, -0.6), (-0.7, 0.2)], ink, s, cx, cy); _poly(d, [(0.3, -0.1), (0.9, -0.6), (0.7, 0.2)], ink, s, cx, cy)
        d.line([(cx - 0.1 * s, cy + 0.6 * s), (cx - 0.15 * s, cy + 0.85 * s)], fill=ink, width=int(W * 0.5))
        d.line([(cx + 0.1 * s, cy + 0.6 * s), (cx + 0.15 * s, cy + 0.85 * s)], fill=ink, width=int(W * 0.5))
    elif name in ('lion', 'boar', 'bull', 'horse', 'pegasus'):  # four-legged animal in profile (striding)
        d.ellipse([cx - 0.6 * s, cy - 0.3 * s, cx + 0.5 * s, cy + 0.25 * s], fill=ink)          # body
        hx = 0.55
        d.ellipse([cx + (hx - 0.05) * s, cy - 0.55 * s, cx + (hx + 0.35) * s, cy - 0.15 * s], fill=ink)  # head
        _poly(d, [(0.35, -0.2), (0.55, -0.45), (0.6, -0.2)], ink, s, cx, cy)                    # neck
        for x, lean in ((-0.45, -0.1), (-0.25, 0.1), (0.2, -0.1), (0.4, 0.1)):
            d.line([(cx + x * s, cy + 0.1 * s), (cx + (x + lean) * s, cy + 0.75 * s)], fill=ink, width=int(W * 0.6))
        if name == 'bull':
            _poly(d, [(0.7, -0.5), (0.85, -0.8), (0.78, -0.45)], ink, s, cx, cy)
        if name == 'pegasus':
            _poly(d, [(-0.1, -0.25), (-0.5, -0.95), (0.15, -0.6), (0.3, -0.25)], ink, s, cx, cy)
        if name == 'lion':
            d.ellipse([cx + 0.35 * s, cy - 0.7 * s, cx + 0.9 * s, cy - 0.05 * s], outline=ink, width=W)
        if name == 'boar':
            _poly(d, [(-0.4, -0.3), (-0.2, -0.45), (0.0, -0.3)], ink, s, cx, cy)
        d.line([(cx - 0.6 * s, cy - 0.1 * s), (cx - 0.85 * s, cy + 0.3 * s)], fill=ink, width=int(W * 0.4))   # tail
    elif name in ('serpent', 'dolphin', 'crab', 'scorpion'):
        if name == 'serpent':
            pts = [(cx + (0.7 * math.sin(t * 4.2)) * s * 0.6, cy + (t - 0.5) * 1.6 * s) for t in [i / 30 for i in range(31)]]
            d.line(pts, fill=ink, width=W, joint='curve')
            d.ellipse([pts[0][0] - 0.12 * s, pts[0][1] - 0.12 * s, pts[0][0] + 0.12 * s, pts[0][1] + 0.12 * s], fill=ink)
        elif name == 'dolphin':
            d.arc([cx - 0.8 * s, cy - 0.5 * s, cx + 0.8 * s, cy + 0.9 * s], 200, 340, fill=ink, width=int(W * 2.2))
            _poly(d, [(-0.1, -0.5), (0.1, -0.75), (0.2, -0.45)], ink, s, cx, cy)
            _poly(d, [(0.65, -0.05), (0.95, -0.25), (0.9, 0.2)], ink, s, cx, cy)
        else:
            d.ellipse([cx - 0.35 * s, cy - 0.25 * s, cx + 0.35 * s, cy + 0.35 * s], fill=ink)
            for sgn in (-1, 1):
                for k in range(3):
                    d.line([(cx + sgn * 0.3 * s, cy + (0.0 + 0.12 * k) * s), (cx + sgn * 0.75 * s, cy + (0.2 + 0.18 * k) * s)], fill=ink, width=int(W * 0.4))
                d.arc([cx + sgn * 0.3 * s - 0.3 * s, cy - 0.8 * s, cx + sgn * 0.3 * s + 0.3 * s, cy - 0.2 * s], 180 if sgn < 0 else 270, 270 if sgn < 0 else 360, fill=ink, width=int(W * 0.6))
            if name == 'scorpion':
                d.arc([cx - 0.35 * s, cy + 0.2 * s, cx + 0.35 * s, cy + 0.95 * s], 0, 180, fill=ink, width=int(W * 0.7))
    else:
        raise KeyError(name)


def paint(name: str, path: Path, size: int = 512, seed: int = 0) -> Path:
    """One painted shield face: field colour, optional rim band, the emblem; transparent outside the circle."""
    rnd = random.Random(f"{name}:{seed}")
    field = rnd.choice(FIELDS)
    ink = rnd.choice(INKS[field])
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, size - 1, size - 1], fill=field + (255,))
    if rnd.random() < 0.55:                                    # contrasting rim band (tongues / plain), as on many vases
        band = rnd.choice([c for c in INKS[field]])
        d.ellipse([0, 0, size - 1, size - 1], outline=band + (255,), width=max(2, size // 22))
    cx = cy = size / 2
    _draw(name, d, size * 0.36, cx, cy, ink + (255,), field + (255,))
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    return path


# Every shield device we can paint (moved here from the removed 3D crowd module, 2026-11-21).
EMBLEMS = ["lambda", "gorgon", "owl", "trident", "scorpion", "bull", "lion", "boar", "eagle", "serpent", "pegasus",
           "crab", "dolphin", "wheel", "tripod", "club", "triskeles", "cock", "horse", "star", "crescent", "eye"]


def _args(p):
    p.add_argument("out_dir")


@register("emblems", "paint every hoplite shield emblem (vase-painting style) for review", _args)
def _cmd_emblems(args) -> int:
    for n in EMBLEMS:
        print(paint(n, Path(args.out_dir) / f"{n}.png"))
    return 0

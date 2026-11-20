# LABELS — the only text the channel allows on screen (rule r3: place/date cards + map labels).
# Reference/maps/02 + 04 + 07:
#   - REGION names ("BYZANTINE EMPIRE"): big carved Roman capitals, cream with a dark-brown outline and a soft
#     shadow, wide letter spacing, gently CURVED along the land, on 1-3 lines
#   - SEA names ("MEDITERRANEAN SEA"): smaller dark teal capitals printed into the water, no outline
#   - CITY tags: a little parchment SCROLL (rolled ends, shaded) with the name in an old book face, and a tiny
#     drawn town (towers + red roofs) standing above it; LEADER tags carry a small crown instead
#   - DATE strip ("c.1097 AD"): a torn paper strip, top right of frame
# Each label is its own small RGBA image + where it goes, so Blender can fade/pop every label separately.
# Fonts: Cinzel + IM Fell English (both SIL Open Font License, library/maps/fonts/OFL.txt).
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from tc.paths import LIBRARY

FONTS = LIBRARY / "maps" / "fonts"
CREAM, OUTLINE, SHADOW = (242, 232, 205), (52, 36, 24), (20, 12, 6)
SEA_INK, TAG_INK = (44, 68, 70), (52, 34, 20)


def font(name: str, size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONTS / name), size)
    if weight is not None:
        try:
            f.set_variation_by_axes([weight])        # Cinzel is a variable font: 400 regular .. 900 black
        except Exception:
            pass
    return f


def _glyph(ch: str, f, fill, stroke: int, stroke_fill) -> Image.Image:
    """One letter on its own transparent tile (so it can be rotated to follow a curve)."""
    l, t, r, b = f.getbbox(ch, stroke_width=stroke)
    im = Image.new("RGBA", (r - l + stroke * 4 + 4, b - t + stroke * 4 + 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((stroke * 2 + 2 - l, stroke * 2 + 2 - t), ch, font=f, fill=fill,
                            stroke_width=stroke, stroke_fill=stroke_fill)
    return im


def curved_text(text: str, f, bend_deg: float = 0.0, tracking: float = 0.18, fill=CREAM, stroke: int = 0,
                stroke_fill=OUTLINE) -> Image.Image:
    """Text set along an arc. bend_deg = how many degrees the whole line turns (0 = straight, + = smile up).
    tracking = extra space between letters as a share of the font size (the reference spaces capitals wide)."""
    size = f.size
    advances = [f.getlength(c) + size * tracking for c in text]
    total = sum(advances) - size * tracking
    if abs(bend_deg) < 0.5:                                   # straight: plain placement
        radius = None
    else:
        radius = total / math.radians(abs(bend_deg))
    W = int(total + size * 3); H = int(size * 3 + (0 if radius is None else radius * (1 - math.cos(math.radians(abs(bend_deg) / 2))) * 2))
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x = -total / 2
    for c, adv in zip(text, advances):
        g = _glyph(c, f, fill, stroke, stroke_fill)
        cx = x + f.getlength(c) / 2                            # centre of this letter along the line
        if radius is None:
            px, py, ang = cx, 0.0, 0.0
        else:
            a = cx / radius                                    # angle round the arc (radians)
            sgn = 1 if bend_deg > 0 else -1
            px = radius * math.sin(a)
            py = sgn * radius * (1 - math.cos(a))              # + bend: ends rise (smile); - : frown
            ang = -sgn * math.degrees(a)
        gr = g.rotate(ang, resample=Image.BICUBIC, expand=True)
        canvas.alpha_composite(gr, (int(W / 2 + px - gr.width / 2), int(H / 2 - py - gr.height / 2)))
        x += adv
    return canvas.crop(canvas.getbbox() or (0, 0, 1, 1))


def with_shadow(im: Image.Image, blur: float, offset: tuple[int, int], opacity: float = 0.55) -> Image.Image:
    """Soft drop shadow under a label (lifts the letters off the paper like the reference)."""
    pad = int(blur * 3) + max(abs(offset[0]), abs(offset[1]))
    out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    a = im.getchannel("A").point(lambda v: int(v * opacity))
    sh = Image.new("RGBA", im.size, SHADOW + (0,)); sh.putalpha(a)
    out.alpha_composite(sh, (pad + offset[0], pad + offset[1]))
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(im, (pad, pad))
    return out


def region_label(lines: list[str], size: int, bend_deg: float = 8.0) -> Image.Image:
    """BIG region name on 1-3 lines: Cinzel bold capitals, cream, dark outline, soft shadow, curved."""
    f = font("Cinzel.ttf", size, weight=800)
    parts = [curved_text(l.upper(), f, bend_deg, 0.06, CREAM, max(2, size // 14), OUTLINE) for l in lines]
    gap = int(size * -0.05)
    W = max(p.width for p in parts); H = sum(p.height for p in parts) + gap * (len(parts) - 1)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); y = 0
    for p in parts:
        im.alpha_composite(p, ((W - p.width) // 2, y)); y += p.height + gap
    return with_shadow(im, size / 10, (size // 16, size // 12))


def sea_label(text: str, size: int, bend_deg: float = 6.0) -> Image.Image:
    """Sea / river name printed into the water: smaller teal small-caps, wide spacing, no outline."""
    f = font("IMFellEnglishSC.ttf", size)
    im = curved_text(text.upper(), f, bend_deg, 0.22, SEA_INK + (235,), 0)
    return im


# ------------------------------------------------------------------ scroll tags + icons
def scroll(text: str, size: int) -> Image.Image:
    """A small parchment scroll with rolled ends and the name in an old book face (city / leader tag)."""
    f = font("IMFellEnglish.ttf", size)
    tw = int(f.getlength(text)); th = int(size * 1.35)
    pad, roll = int(size * 0.55), int(size * 0.42)
    W, H = tw + pad * 2 + roll * 2, th + int(size * 0.5)
    S = 3                                                     # draw 3x, reduce: crisp edges
    im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    body = [roll * S, int(size * 0.18) * S, (W - roll) * S, (H - int(size * 0.18)) * S]
    d.rectangle([body[0] + 2 * S, body[1] + 3 * S, body[2] + 2 * S, body[3] + 3 * S], fill=(30, 18, 8, 110))   # shadow
    d.rectangle(body, fill=(232, 214, 168, 255), outline=(98, 70, 40, 255), width=max(1, size // 12) * S)
    d.line([body[0], body[1] + 2 * S, body[2], body[1] + 2 * S], fill=(250, 238, 200, 255), width=S * 2)     # top highlight
    d.line([body[0], body[3] - 2 * S, body[2], body[3] - 2 * S], fill=(176, 146, 96, 255), width=S * 2)      # bottom shade
    for x0 in (0, W - roll * 2):                              # the two rolled ends (cylinders)
        r = [x0 * S + roll * S // 2, 0, x0 * S + roll * S * 3 // 2, H * S]
        d.rounded_rectangle(r, radius=roll * S // 2, fill=(214, 190, 140, 255), outline=(98, 70, 40, 255), width=max(1, size // 12) * S)
        d.line([(r[0] + r[2]) // 2, r[1] + 3 * S, (r[0] + r[2]) // 2, r[3] - 3 * S], fill=(160, 128, 80, 255), width=S)
    d.text(((W * S) // 2, (H * S) // 2), text, font=font("IMFellEnglish.ttf", size * S), fill=TAG_INK + (255,), anchor="mm")
    return im.resize((W, H), Image.LANCZOS)


def town_icon(size: int, rng: np.random.Generator, kind: str = "city") -> Image.Image:
    """A tiny drawn town: 3-5 pale stone towers with crenellations or red/blue pointed roofs, a wall in front.
    kind='capital' is bigger with a dome; 'fort' is a single keep."""
    S = 4
    W, H = int(size * 2.2), int(size * 1.4)
    im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ink, stone, shade = (60, 42, 28, 255), (226, 212, 184, 255), (176, 158, 128, 255)
    roofs = [(176, 52, 40, 255), (150, 44, 36, 255), (70, 90, 130, 255)]
    n = {"fort": 1, "city": 4, "capital": 5}.get(kind, 4)
    base = H * S - int(size * 0.1) * S
    xs = np.linspace(W * S * 0.18, W * S * 0.82, n) if n > 1 else [W * S / 2]
    order = sorted(range(n), key=lambda i: rng.random())
    for i in order:
        x = xs[i] + (rng.random() - 0.5) * size * 0.2 * S
        tw = size * (0.32 + rng.random() * 0.12) * S
        th = size * (0.55 + rng.random() * 0.45) * S * (1.25 if kind == "fort" else 1)
        top = base - th
        d.rectangle([x - tw / 2, top, x + tw / 2, base], fill=stone, outline=ink, width=S)
        d.rectangle([x + tw * 0.15, top, x + tw / 2, base], fill=shade)                     # shade side
        d.rectangle([x - tw * 0.12, top + th * 0.3, x + tw * 0.02, top + th * 0.45], fill=ink)   # window
        if rng.random() < 0.55:                                # pointed roof
            d.polygon([(x - tw * 0.62, top), (x, top - tw * 0.95), (x + tw * 0.62, top)], fill=roofs[int(rng.integers(3))], outline=ink)
        else:                                                  # crenellations
            for k in range(3):
                cx = x - tw / 2 + tw * (k + 0.5) / 3
                d.rectangle([cx - tw * 0.11, top - tw * 0.22, cx + tw * 0.11, top], fill=stone, outline=ink, width=S)
    if kind == "capital":                                      # a dome in the middle
        cx = W * S / 2
        d.pieslice([cx - size * 0.45 * S, base - size * 1.35 * S, cx + size * 0.45 * S, base - size * 0.45 * S], 180, 360, fill=(196, 160, 70, 255), outline=ink, width=S)
    if kind != "fort":                                         # town wall in front
        d.rectangle([W * S * 0.1, base - size * 0.22 * S, W * S * 0.9, base], fill=stone, outline=ink, width=S)
    return im.resize((W, H), Image.LANCZOS)


def crown_icon(size: int) -> Image.Image:
    S = 4; W, H = int(size * 1.2), int(size * 0.8)
    im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ink, gold = (70, 46, 20, 255), (214, 170, 70, 255)
    w, h = W * S, H * S
    d.polygon([(w * 0.08, h * 0.95), (w * 0.08, h * 0.3), (w * 0.3, h * 0.6), (w * 0.5, h * 0.1), (w * 0.7, h * 0.6),
               (w * 0.92, h * 0.3), (w * 0.92, h * 0.95)], fill=gold, outline=ink, width=S * 2)
    for x in (0.08, 0.5, 0.92):
        d.ellipse([w * x - S * 5, h * (0.3 if x != 0.5 else 0.1) - S * 5, w * x + S * 5, h * (0.3 if x != 0.5 else 0.1) + S * 5], fill=(180, 40, 40, 255), outline=ink)
    return im.resize((W, H), Image.LANCZOS)


def place_tag(text: str, size: int, icon: str = "city", seed: int = 0) -> Image.Image:
    """Scroll tag with its icon (town / capital / fort / crown / none) centred above it."""
    sc = scroll(text, size)
    rng = np.random.default_rng(seed or abs(hash(text)) % 2 ** 31)
    ic = crown_icon(int(size * 1.1)) if icon == "crown" else (town_icon(int(size * 1.15), rng, icon) if icon != "none" else None)
    if ic is None:
        return sc
    W = max(sc.width, ic.width); H = sc.height + ic.height - int(size * 0.25)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    im.alpha_composite(ic, ((W - ic.width) // 2, 0))
    im.alpha_composite(sc, ((W - sc.width) // 2, H - sc.height))
    return im


def date_strip(text: str, size: int, seed: int = 1) -> Image.Image:
    """Torn paper strip with the date (reference frame 07: 'c.1097 AD', top right)."""
    rng = np.random.default_rng(seed)
    f = font("IMFellEnglish.ttf", size)
    tw = int(f.getlength(text)); W, H = tw + size * 2, int(size * 1.9)
    S = 3
    im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    top = [(x, rng.random() * size * 0.25 * S) for x in np.linspace(0, W * S, 40)]          # torn edges
    bot = [(x, H * S - rng.random() * size * 0.25 * S) for x in np.linspace(W * S, 0, 40)]
    d.polygon(top + bot, fill=(234, 218, 176, 255), outline=(120, 92, 58, 255))
    d.text((W * S // 2, H * S // 2), text, font=font("IMFellEnglish.ttf", size * S), fill=TAG_INK + (255,), anchor="mm")
    im = im.resize((W, H), Image.LANCZOS)
    return with_shadow(im, size / 6, (size // 6, size // 5), 0.5)


def banner(emblem: str, ink=(150, 30, 28), cloth=(236, 230, 214), size: int = 256) -> Image.Image:
    """Army banner cloth (reference 05/06): off-white cloth, the side's emblem in a dark ring, a swallow-tail
    notch at the bottom, faint cloth folds. Drawn tall (w x 1.25w); Blender hangs it on a pole and waves it."""
    from tc.maps.territory import draw_emblem
    S = 2; W, H = size * S, int(size * 1.25) * S
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(0, 0), (W, 0), (W, H), (W // 2, int(H * 0.86)), (0, H)], fill=cloth + (255,))
    for k in range(1, 5):                                   # soft vertical fold shading
        x = W * k / 5
        d.line([(x, 0), (x, H)], fill=(226, 218, 200, 255), width=int(W * 0.018))
    cx, cy, r = W / 2, H * 0.42, W * 0.34
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(246, 240, 226, 255))
    draw_emblem(d, emblem, cx, cy, r, ink + (255,), max(3, int(W * 0.04)), solid=True)     # bold: reads at map distance
    d.line([(0, 2), (W, 2)], fill=(90, 70, 50, 255), width=S * 3)              # hem along the crossbar
    return im.resize((W // S, H // S), Image.LANCZOS)


def portrait_card(portrait: Image.Image | None, name: str, width: int = 360) -> Image.Image:
    """Framed parchment card for a leader (reference frame 07: cards slide in at the sides of the map).
    The portrait is OUR OWN render (a still of the 3D cast member) — never a copied painting. Layout:
    name scroll on top, picture window with a dark double border and gold corner pieces, aged parchment mount."""
    W, H = width, int(width * 1.45)
    S = 2
    im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    rng = np.random.default_rng(abs(hash(name)) % 2 ** 31)
    w, h = W * S, H * S
    d.rectangle([0, 0, w - 1, h - 1], fill=(222, 200, 152, 255), outline=(70, 48, 28, 255), width=S * 3)
    # age the mount: blotches
    stain = Image.new("RGBA", (w, h), (0, 0, 0, 0)); sd = ImageDraw.Draw(stain)   # own layer, then COMPOSITED
    for _ in range(40):
        x, y, r = rng.random() * w, rng.random() * h, rng.random() * w * 0.12
        sd.ellipse([x - r, y - r, x + r, y + r], fill=(170, 136, 84, 34))
    stain = stain.filter(ImageFilter.GaussianBlur(w * 0.03))
    mount = Image.new("RGBA", (w, h), (0, 0, 0, 0)); mount.paste((255, 255, 255, 255), [S * 3, S * 3, w - S * 3, h - S * 3])
    stain.putalpha(Image.fromarray(np.minimum(np.asarray(stain.getchannel("A")), np.asarray(mount.getchannel("A")))))
    im.alpha_composite(stain)
    m = int(w * 0.07)
    win = [m, int(h * 0.16), w - m, h - m]
    d.rectangle([win[0] - S * 6, win[1] - S * 6, win[2] + S * 6, win[3] + S * 6], outline=(70, 48, 28, 255), width=S * 3)
    d.rectangle([win[0] - S * 2, win[1] - S * 2, win[2] + S * 2, win[3] + S * 2], outline=(150, 110, 60, 255), width=S * 2)
    if portrait is not None:
        pw, ph = win[2] - win[0], win[3] - win[1]
        p = portrait.convert("RGBA")
        sc = max(pw / p.width, ph / p.height)
        p = p.resize((int(p.width * sc) + 1, int(p.height * sc) + 1), Image.LANCZOS)
        p = p.crop(((p.width - pw) // 2, 0, (p.width - pw) // 2 + pw, ph))
        im.alpha_composite(p, (win[0], win[1]))
    else:
        d.rectangle(win, fill=(120, 96, 64, 255))
    for cx, cy in ((win[0], win[1]), (win[2], win[1]), (win[0], win[3]), (win[2], win[3])):   # gold corner pieces
        r = S * 9
        d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=(196, 150, 64, 255), outline=(70, 48, 28, 255))
    sc_ = scroll(name, int(width * 0.075) * S)
    im.alpha_composite(sc_, ((w - sc_.width) // 2, int(h * 0.075) - sc_.height // 2 + S * 4))
    im = im.resize((W, H), Image.LANCZOS)
    return with_shadow(im, width / 40, (width // 50, width // 40), 0.6)

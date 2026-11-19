# THUMBNAILS: rendered from OUR OWN 3D scenes (never AI images, never copied frames - rules r5, r9, BACKLOG rule 5).
#
# What makes a history thumbnail get clicked (growth rule r5):
#   1. ONE BIG FACE - a close-up that fills a third or more of the frame (the eye finds faces first)
#   2. A STRONG EMOTION - rage, fear, cunning... read in a split second, even at phone size
#   3. ONE ERA DETAIL - a golden throne, a bronze ram, a burning temple: says "ancient Greece" without words
#   4. CONTRAST - a bright, warm face against a dark background (thumbnails are tiny on a phone)
#   5. 0-3 WORDS at most (optional) - the picture does the work; words never repeat the title
# Every video gets 3 VARIANTS (A, B, C) with different emotions, palettes and layouts, so the owner (and later
# YouTube's "Test & compare") can pick the one that gets clicked.
#
# The pipeline (this file does every step that needs NO Blender):
#   tc thumbnail <job> --details "golden throne;burning ship;wax tablet" --set salamis_strait_dusk
#       -> jobs/<id>/thumbs/plan.json : 3 variants + 3 render requests (Blender job specs)
#   [Blender - TODO, WS1/WS8/WS10: renders thumbs/render_A.png ... from the render requests]
#   tc thumbnail <job> --finish
#       -> thumbs/thumb_A.jpg ... (1280x720, < 2 MB, contrast/colour punch, optional words)
#       + a phone check: is it still readable at 168x94 pixels (the size in the YouTube app list)?
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from tc import jobs
from tc.cli import register

SIZE = (1280, 720)                       # YouTube thumbnail size (16:9)
RENDER_SIZE = [1920, 1080]               # render bigger, then shrink: sharper edges
PHONE_SIZE = (168, 94)                   # how big a thumbnail is in the YouTube phone list
MAX_BYTES = 2 * 1024 * 1024              # YouTube's thumbnail upload limit
MAX_WORDS = 3
MIN_FACE_FRAC = 0.35                     # the face (forehead to chin) fills at least 35% of the frame height
MIN_PHONE_CONTRAST = 0.35                # luminance spread (95th - 5th percentile) at phone size
# Expressions the face rig can already make (blender/lib/expressions.py, WS1) that read well at thumbnail size.
# 'neutral' and 'smile' are left out on purpose: serious tone (rule r2), and calm faces don't get clicks.
EMOTIONS = ["rage", "anger", "fear", "cunning", "contempt", "awe", "grief", "pain", "resolve"]
DEFAULT_EMOTIONS = ["rage", "fear", "cunning"]          # A = power, B = threat, C = scheming
# Palettes = a lighting preset (WS8) + the text colour. Each variant gets a different one.
PALETTES = {
    "ember": {"light": "fire_lit", "text": (255, 196, 92), "note": "warm firelight on the face, near-black background"},
    "gold":  {"light": "dusk",     "text": (255, 230, 160), "note": "low golden sun, deep blue shadows"},
    "steel": {"light": "night",    "text": (220, 235, 255), "note": "cold moonlight + a warm rim, mysterious"},
}
BANNED_WORDS = {"shocking", "insane", "unbelievable", "!!!"}   # same spirit as packaging.BANNED
CAMERA = {"lens_mm": 85, "f_stop": 2.0, "shot": "close_up"}   # close-up lens (WS8 camera rules)


def plan_variants(faces: list[str], era_details: list[str], set_name: str,
                  emotions: list[str] | None = None, words: list[str] | None = None) -> list[dict]:
    """Three thumbnail variants. faces = who can be the big face (cycled), era_details = one prop/detail per
    variant, emotions = three different expressions (default rage / fear / cunning)."""
    if not faces:
        raise ValueError("a thumbnail needs a face: give at least one character")
    emotions = emotions or DEFAULT_EMOTIONS
    palettes = list(PALETTES)
    out = []
    for i, vid in enumerate("ABC"):
        out.append({
            "id": vid,
            "face": faces[i % len(faces)],
            "emotion": emotions[i % len(emotions)],
            "era_detail": era_details[i % len(era_details)] if era_details else "",
            "set": set_name,
            "palette": palettes[i],
            "face_side": "left" if i % 2 == 0 else "right",     # the words / detail go on the other side
            "face_frac": 0.45 if i != 1 else 0.6,               # B is an extreme close-up
            "camera": dict(CAMERA),
            "words": (words[i] if words and i < len(words) else ""),
        })
    return out


def check_plan(plan: list[dict]) -> list[str]:
    """Rules every thumbnail plan must pass (problems list; empty = good)."""
    problems = []
    if len(plan) != 3:
        problems.append(f"need exactly 3 variants (A, B, C), got {len(plan)}")
    if len({v.get('emotion') for v in plan}) != len(plan):
        problems.append("every variant needs a different emotion (we are testing which face gets clicked)")
    for v in plan:
        vid = v.get("id", "?")
        if v.get("emotion") not in EMOTIONS:
            problems.append(f"{vid}: unknown emotion {v.get('emotion')!r}; use one of {EMOTIONS}")
        if not v.get("face"):
            problems.append(f"{vid}: no face")
        if v.get("face_frac", 0) < MIN_FACE_FRAC:
            problems.append(f"{vid}: face too small ({v.get('face_frac')}); at least {MIN_FACE_FRAC} of the frame height")
        if not v.get("era_detail"):
            problems.append(f"{vid}: no era detail (one prop that says when and where)")
        if v.get("palette") not in PALETTES:
            problems.append(f"{vid}: unknown palette {v.get('palette')!r}")
        w = (v.get("words") or "").split()
        if len(w) > MAX_WORDS:
            problems.append(f"{vid}: {len(w)} words; max {MAX_WORDS} (the picture does the work)")
        if {x.lower() for x in w} & BANNED_WORDS:
            problems.append(f"{vid}: cheap clickbait word in {v['words']!r}")
    return problems


def faces_from_script(lines) -> list[str]:
    """The characters who speak in the script, in order (they are the obvious faces)."""
    return list(dict.fromkeys(l.speaker for l in lines if getattr(l, "speaker", None)))


def render_request(job_id: str, v: dict, out_dir: Path) -> dict:
    """What Blender must render for one variant. Written to plan.json; nothing runs here.
    TODO (Blender, WS1 + WS8 + WS10): a new blender/scenes/thumbnail.py reads one request and
      1. builds the set (blender/lib/sets.py) and the character (blender/lib/cast.py, cast spec = face name lower case)
      2. keys the expression with expressions.key_expression(human, rig, request['expression'], frame=1, strength=1.0)
         - thumbnails may push strength to ~1.2 (a little bigger than in the film)
      3. lights with the WS8 preset request['light'] (key + strong rim + low fill, rule r10)
      4. places the 85 mm camera so the face height = face_frac of the frame, on face_side (rule of thirds),
         checked with bpy_extras.object_utils.world_to_camera_view on the head-top and chin bones
      5. puts the era detail in the free half (sharp, not blurred away)
      6. renders Cycles at RENDER_SIZE to request['output'] (respect spike/BLENDER_LOCK - one Blender at a time)
    """
    return {
        "job": job_id, "variant": v["id"], "cast": v["face"].lower(), "expression": v["emotion"],
        "set": v["set"], "era_detail": v["era_detail"], "light": PALETTES[v["palette"]]["light"],
        "camera": dict(v["camera"]), "face_frac": v["face_frac"], "face_side": v["face_side"],
        "resolution": list(RENDER_SIZE), "output": str(Path(out_dir) / f"render_{v['id']}.png"),
    }


# ---------------- after the render: Pillow only ----------------
def _font(px: int):
    """A bold serif if Windows has one (Georgia Bold feels classical), else Pillow's built-in font."""
    for f in ("C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/timesbd.ttf", "DejaVuSerif-Bold.ttf"):
        try:
            return ImageFont.truetype(f, px)
        except OSError:
            continue
    return ImageFont.load_default(size=px)


def _cover(im: Image.Image, size=SIZE) -> Image.Image:
    """Crop to 16:9 from the centre (no stretching), then resize."""
    w, h = im.size
    target = size[0] / size[1]
    if w / h > target:                       # too wide: cut the sides
        nw = int(h * target); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    elif w / h < target:                     # too tall: cut top and bottom
        nh = int(w / target); im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    return im.resize(size, Image.LANCZOS)


def finish(render_png: Path, out_jpg: Path, v: dict) -> Path:
    """Render -> YouTube thumbnail: 1280x720, a little extra contrast/colour/sharpness (thumbnails are seen
    tiny), optional words in the free half with a dark outline, JPEG under 2 MB."""
    im = _cover(Image.open(render_png).convert("RGB"))
    im = ImageEnhance.Contrast(im).enhance(1.12)
    im = ImageEnhance.Color(im).enhance(1.08)
    im = ImageEnhance.Sharpness(im).enhance(1.3)
    words = (v.get("words") or "").strip()
    if words:
        draw = ImageDraw.Draw(im)
        font = _font(118)
        box = draw.textbbox((0, 0), words, font=font, stroke_width=8)
        tw, th = box[2] - box[0], box[3] - box[1]
        margin = 60
        x = SIZE[0] - tw - margin if v.get("face_side", "left") == "left" else margin   # opposite the face
        y = SIZE[1] - th - margin - 20                                                  # low third, clear of the face
        draw.text((x, y), words, font=font, fill=PALETTES[v.get("palette", "ember")]["text"],
                  stroke_width=8, stroke_fill=(8, 6, 10))
    out_jpg = Path(out_jpg)
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    for q in (92, 85, 75, 65):               # step quality down until it fits YouTube's 2 MB limit
        im.save(out_jpg, "JPEG", quality=q, optimize=True)
        if out_jpg.stat().st_size < MAX_BYTES:
            break
    return out_jpg


def mobile_check(png: Path) -> dict:
    """Shrink to phone-list size and measure if it still 'pops': the luminance spread must be big enough
    that a face and a background are still two different things at 168x94 pixels."""
    small = np.asarray(Image.open(png).convert("RGB").resize(PHONE_SIZE, Image.LANCZOS), dtype=np.float32) / 255
    y = 0.2126 * small[..., 0] + 0.7152 * small[..., 1] + 0.0722 * small[..., 2]
    contrast = float(np.percentile(y, 95) - np.percentile(y, 5))
    return {"contrast": round(contrast, 3), "ok": contrast >= MIN_PHONE_CONTRAST}


# ---------------- per job ----------------
def write_plan(job: jobs.Job, era_details: list[str], set_name: str, faces: list[str] | None = None,
               emotions: list[str] | None = None, words: list[str] | None = None) -> Path:
    """jobs/<id>/thumbs/plan.json: the 3 variants + one Blender render request each."""
    from tc.script import parse_script
    d = jobs.job_dir(job.id)
    faces = faces or faces_from_script(parse_script((d / "script.md").read_text(encoding="utf-8")))
    plan = plan_variants(faces, era_details, set_name, emotions, words)
    problems = check_plan(plan)
    if problems:
        raise ValueError("thumbnail plan problems:\n- " + "\n- ".join(problems))
    out_dir = d / "thumbs"
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {"variants": plan, "render_requests": [render_request(job.id, v, out_dir) for v in plan]}
    (out_dir / "plan.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_dir / "plan.json"


def _args(p):
    p.add_argument("job")
    p.add_argument("--details", help="3 era details separated by ; (e.g. 'golden throne;bronze ram;burning temple')")
    p.add_argument("--set", default="salamis_strait_dusk", help="set name from library/sets")
    p.add_argument("--faces", help="characters separated by , (default: the script's speakers)")
    p.add_argument("--emotions", help=f"3 emotions separated by , (from {EMOTIONS})")
    p.add_argument("--words", help="optional words per variant separated by ; (max 3 words each)")
    p.add_argument("--finish", action="store_true", help="turn thumbs/render_*.png into thumb_*.jpg + phone check")


@register("thumbnail", "plan 3 thumbnail variants (3D render requests) or finish the renders", _args)
def _cmd_thumbnail(args) -> int:
    job = jobs.load_job(args.job)
    d = jobs.job_dir(job.id) / "thumbs"
    split = lambda s, sep: [x.strip() for x in s.split(sep)] if s else None
    if not args.finish:
        try:
            out = write_plan(job, split(args.details, ";") or [], args.set, split(args.faces, ","),
                             split(args.emotions, ","), split(args.words, ";"))
        except ValueError as e:
            print(e)
            return 1
        for v in json.loads(out.read_text(encoding="utf-8"))["variants"]:
            print(f"{v['id']}: {v['face']} ({v['emotion']}, {v['palette']}, face {v['face_side']}) + {v['era_detail']}"
                  + (f"  words: {v['words']}" if v["words"] else ""))
        print(f"plan -> {out}. Blender render step is a TODO (see render_request); then: tc thumbnail {job.id} --finish")
        return 0
    plan = json.loads((d / "plan.json").read_text(encoding="utf-8"))
    missing = 0
    for v in plan["variants"]:
        render = d / f"render_{v['id']}.png"
        if not render.exists():
            print(f"{v['id']}: no {render.name} yet (render it in Blender first)"); missing += 1
            continue
        out = finish(render, d / f"thumb_{v['id']}.jpg", v)
        m = mobile_check(out)
        print(f"{v['id']}: {out.name}  phone contrast {m['contrast']} {'OK' if m['ok'] else 'TOO FLAT - relight'}")
    return 1 if missing else 0

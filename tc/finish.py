# FILM FINISHING: what turns a clean 3D render into a movie frame (done after rendering, with ffmpeg, so it costs
# seconds, not render hours, and can be re-tuned without re-rendering):
#   1. grade  - gentle S-curve (rich blacks, soft highlight roll-off) + split toning (cool shadows, warm highlights)
#   2. bloom  - bright areas (sun on water, rim light on hair) glow softly into their surroundings, like real lenses
#   3. grain  - fine moving film grain (hides CG smoothness, makes every frame feel photographed)
#   4. vignette - corners darken a touch, the eye goes to the centre of the action
#   optional film/lens layers (per look, or added by hand):
#   halation  - real film's warm RED glow around bright edges (light scatters back through the film base)
#   bleach    - 'bleach bypass': the silver is left in the print -> desaturated, crushed, metallic (battle scenes)
#   aberration - a pixel or two of red/blue fringe toward the frame edge (real lenses are never perfect)
#   streak    - anamorphic lens flare: highlights stretch into thin horizontal streaks (night fires, torches)
#   python -m tc finish in.png out.png --look dusk          (also works on a frame sequence / video)
import subprocess

from tc.cli import register

LOOKS = {
    # shadows (r, g, b) / highlights (r, g, b) colour balance offsets, -1..1
    "dusk":     {"curve": "0/0 0.12/0.08 0.5/0.5 0.88/0.92 1/1", "shadows": (-0.05, 0.0, 0.06), "highlights": (0.06, 0.02, -0.05),
                 "sat": 1.05, "bloom": 0.35, "bloom_radius": 18, "grain": 7, "vignette": 0.45},
    "day":      {"curve": "0/0 0.1/0.07 0.5/0.5 0.9/0.93 1/1", "shadows": (-0.03, 0.0, 0.04), "highlights": (0.03, 0.01, -0.02),
                 "sat": 1.08, "bloom": 0.2, "bloom_radius": 14, "grain": 6, "vignette": 0.35},
    "night":    {"curve": "0/0 0.15/0.06 0.5/0.45 0.9/0.9 1/1", "shadows": (-0.06, 0.0, 0.09), "highlights": (0.05, 0.02, -0.03),
                 "sat": 0.9, "bloom": 0.45, "bloom_radius": 22, "grain": 9, "vignette": 0.55},
    "interior": {"curve": "0/0 0.14/0.07 0.5/0.48 0.9/0.92 1/1", "shadows": (-0.04, 0.0, 0.05), "highlights": (0.07, 0.03, -0.04),
                 "sat": 1.0, "bloom": 0.3, "bloom_radius": 16, "grain": 8, "vignette": 0.5},
    # --- cinematic moods for a history film
    # low sun, honeyed highlights, teal-ish shadows, soft glow + film halation
    "golden_hour": {"curve": "0/0 0.1/0.07 0.5/0.52 0.88/0.93 1/1", "shadows": (-0.05, 0.0, 0.05), "highlights": (0.1, 0.04, -0.08),
                    "sat": 1.08, "bloom": 0.4, "bloom_radius": 20, "grain": 7, "vignette": 0.45, "halation": 0.22},
    # pre-dawn before battle: cold blue, lifted blacks, quiet
    "cold_dawn": {"curve": "0/0.03 0.15/0.1 0.5/0.47 0.9/0.88 1/0.97", "shadows": (-0.06, 0.0, 0.1), "highlights": (-0.02, 0.01, 0.05),
                  "sat": 0.85, "bloom": 0.25, "bloom_radius": 18, "grain": 8, "vignette": 0.5},
    # lit by fire: deep orange highlights, near-black shadows, halation + horizontal flares on the flames
    "firelight": {"curve": "0/0 0.18/0.06 0.5/0.46 0.9/0.92 1/1", "shadows": (0.0, -0.02, 0.04), "highlights": (0.14, 0.05, -0.1),
                  "sat": 1.1, "bloom": 0.5, "bloom_radius": 24, "grain": 9, "vignette": 0.6, "halation": 0.3, "streak": 0.18},
    # battle: bleach bypass - desaturated, hard contrast, metallic, heavier grain
    "battle": {"curve": "0/0 0.2/0.1 0.5/0.5 0.8/0.9 1/1", "shadows": (-0.02, 0.0, 0.03), "highlights": (0.03, 0.02, 0.0),
               "sat": 0.72, "bloom": 0.15, "bloom_radius": 12, "grain": 12, "vignette": 0.5, "bleach": 0.45, "aberration": 2},
    # memory / oracle / flashback: faded warm, soft, milky blacks, dreamy glow
    "flashback": {"curve": "0/0.06 0.25/0.24 0.5/0.52 0.85/0.86 1/0.95", "shadows": (0.03, 0.01, -0.02), "highlights": (0.06, 0.03, -0.04),
                  "sat": 0.75, "bloom": 0.55, "bloom_radius": 30, "grain": 10, "vignette": 0.6, "halation": 0.15},
}


def filter_graph(look: dict) -> str:
    """ffmpeg filter_complex for one look. Output label [out]."""
    sr, sg, sb = look["shadows"]; hr, hg, hb = look["highlights"]
    grade = (f"curves=all='{look['curve']}',"
             f"colorbalance=rs={sr}:gs={sg}:bs={sb}:rh={hr}:gh={hg}:bh={hb},"
             f"format=yuv444p,eq=saturation={look['sat']},format=gbrp")    # eq only understands YUV colour
    g = f"[0:v]format=gbrp,{grade}"
    if look.get("bleach", 0) > 0:
        # bleach bypass: lay a contrasty black-and-white copy over the colour ('overlay' = deeper blacks, harder
        # highlights, colours drained toward silver)
        g += (f",split[c0][c1];[c1]hue=s=0,curves=all='0/0 0.3/0.2 0.7/0.8 1/1'[bw];"
              f"[c0][bw]blend=all_mode=overlay:all_opacity={look['bleach']}")
    if look.get("bloom", 0) > 0:
        # bloom: keep only the brightest tones, blur them wide, add back with 'screen' (never darkens)
        g += (f",split[a][b];[b]curves=all='0/0 0.5/0 1/1',gblur=sigma={look['bloom_radius']}[glow];"
              f"[a][glow]blend=all_mode=screen:all_opacity={look['bloom']}")
    if look.get("halation", 0) > 0:
        # halation: the brightest edges, tinted red-orange, blurred a little, screened back on
        g += (f",split[h0][h1];[h1]curves=all='0/0 0.7/0 1/1',colorchannelmixer=rr=1:rg=0:rb=0:gr=0.35:gg=0:gb=0:br=0.05:bg=0:bb=0,"
              f"gblur=sigma=6[halo];[h0][halo]blend=all_mode=screen:all_opacity={look['halation']}")
    if look.get("streak", 0) > 0:
        # anamorphic streak: highlights smeared far sideways but not up/down, faint blue-white, screened back on
        g += (f",split[s0][s1];[s1]curves=all='0/0 0.82/0 1/1',gblur=sigma=60:sigmaV=0.5,"
              f"colorchannelmixer=rr=0.6:gg=0.8:bb=1.0[streak];[s0][streak]blend=all_mode=screen:all_opacity={look['streak']}")
    if look.get("aberration", 0) > 0:
        a = int(look["aberration"])                                   # red one way, blue the other (lens fringe)
        g += f",rgbashift=rh={a}:bh={-a}:edge=smear"
    g += (f",noise=alls={look['grain']}:allf=t+u,"
          f"vignette=angle={look['vignette']}:mode=forward[out]")
    return g


def run(src: str, dst: str, look_name: str = "dusk") -> int:
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-filter_complex", filter_graph(LOOKS[look_name]),
           "-map", "[out]"]
    if dst.lower().endswith((".png", ".jpg")):
        cmd += ["-frames:v", "1", "-pix_fmt", "rgb24"]
    else:
        cmd += ["-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p"]
    return subprocess.run(cmd + [dst]).returncode


def _args(p):
    p.add_argument("src"); p.add_argument("dst")
    p.add_argument("--look", default="dusk", choices=sorted(LOOKS))


@register("finish", "film finishing: grade, bloom, grain, vignette (ffmpeg)", _args)
def _cmd_finish(args) -> int:
    return run(args.src, args.dst, args.look)

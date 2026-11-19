# FILM FINISHING: what turns a clean 3D render into a movie frame (done after rendering, with ffmpeg, so it costs
# seconds, not render hours, and can be re-tuned without re-rendering):
#   1. grade  - gentle S-curve (rich blacks, soft highlight roll-off) + split toning (cool shadows, warm highlights)
#   2. bloom  - bright areas (sun on water, rim light on hair) glow softly into their surroundings, like real lenses
#   3. grain  - fine moving film grain (hides CG smoothness, makes every frame feel photographed)
#   4. vignette - corners darken a touch, the eye goes to the centre of the action
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
}


def filter_graph(look: dict) -> str:
    """ffmpeg filter_complex for one look. Output label [out]."""
    sr, sg, sb = look["shadows"]; hr, hg, hb = look["highlights"]
    grade = (f"curves=all='{look['curve']}',"
             f"colorbalance=rs={sr}:gs={sg}:bs={sb}:rh={hr}:gh={hg}:bh={hb},"
             f"format=yuv444p,eq=saturation={look['sat']},format=gbrp")    # eq only understands YUV colour
    g = f"[0:v]format=gbrp,{grade}"
    if look.get("bloom", 0) > 0:
        # bloom: keep only the brightest tones, blur them wide, add back with 'screen' (never darkens)
        g += (f",split[a][b];[b]curves=all='0/0 0.5/0 1/1',gblur=sigma={look['bloom_radius']}[glow];"
              f"[a][glow]blend=all_mode=screen:all_opacity={look['bloom']}")
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

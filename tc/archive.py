# "DECLASSIFIED ARCHIVE FOOTAGE" LOOK (WS17, Session F) - makes a clean 3D render look like a reel pulled out of a
# government film vault in 1945-1965: the 16 mm / 35 mm black-and-white footage you see in Manhattan Project,
# atomic-test and space-race documentaries (e.g. the US Air Force "Lookout Mountain" test films, National Archives
# RG 434 / RG 342 reels, NASA/Army newsreels). What makes old film look old, layer by layer:
#   1. black-and-white  - orthochromatic/panchromatic stock: no colour, harder contrast, crushed blacks
#   2. soft lens        - period lenses + copy-of-a-copy duplication: everything a little soft
#   3. flicker          - the exposure of every frame differs a touch (old shutters, uneven developing)
#   4. scratches + dust - thin vertical lines from the projector gate, black specks of dust on the print
#   5. grain            - coarse moving silver grain (only in brightness, so grey stays grey)
#   6. vignette         - darker corners (old lenses fall off at the edges)
#   7. gate weave       - the whole picture wobbles a few pixels, because film never sits perfectly in the gate
#   optional: aged-print warm tint, 1.37:1 "academy" frame inside a 16:9 picture (black side bars)
#
#   python -m tc.archive in.png out.png --look kinescope        (also works on a frame sequence / a video)
# It is a separate module (not a LOOK in tc/finish.py, which Session D owns): run it INSTEAD of tc finish on shots
# that the script calls archive footage.
import argparse
import subprocess
import sys

LOOKS = {
    # cool neutral B&W, like a kinescope / Army Signal Corps reel
    "kinescope": {"curve": "0/0 0.12/0.04 0.5/0.52 0.85/0.94 1/1", "blur": 0.9, "flicker": 0.035, "scratches": 3,
                  "dust": 4, "grain": 22, "vignette": 0.62, "weave_px": 3, "tint": None, "pillarbox": False},
    # a faded, warm-brown print that has sat in a can for 60 years: lifted blacks, lower contrast, more damage
    "aged_print": {"curve": "0/0.07 0.2/0.16 0.5/0.5 0.85/0.86 1/0.94", "blur": 1.3, "flicker": 0.05, "scratches": 5,
                   "dust": 7, "grain": 26, "vignette": 0.7, "weave_px": 4, "tint": (1.0, 0.92, 0.78), "pillarbox": False},
    # crisp official test film (Lookout Mountain Air Force Station style): sharper, finer grain, little damage
    "test_film": {"curve": "0/0 0.1/0.03 0.5/0.5 0.9/0.97 1/1", "blur": 0.6, "flicker": 0.02, "scratches": 1,
                  "dust": 2, "grain": 16, "vignette": 0.5, "weave_px": 2, "tint": None, "pillarbox": False},
}


def _scratches(n: int) -> list[str]:
    """Thin vertical scratches. Each one sits at a pseudo-random x that jumps every frame (24 fps -> t*24 = frame) and
    shows only part of the time (enable=). Scratch 0 is always visible at t=0 so a single still shows damage too.
    White = a scratch through the emulsion; one in three is dark (a scratch on the base)."""
    out = []
    for k in range(n):
        col = "black@0.45" if k % 3 == 2 else "white@0.4"
        x = f"mod(t*24*{311 + 97 * k}+{157 * k + 40}\\,iw)"
        out.append(f"drawbox=x='{x}':y=0:w={1 + (k % 2)}:h=ih:color={col}:t=fill:"
                   f"enable='lt(mod(t*24+{5 * k}\\,{7 + 3 * k})\\,{3 + k % 2})'")
    return out


def _dust(n: int) -> list[str]:
    """Black dust specks a few pixels big, each in a new place every frame (dust is on the print, not in the scene)."""
    out = []
    for k in range(n):
        x = f"mod(t*24*{397 + 61 * k}+{131 * k + 17}\\,iw)"; y = f"mod(t*24*{241 + 53 * k}+{89 * k + 23}\\,ih)"
        s = 2 + k % 3
        out.append(f"drawbox=x='{x}':y='{y}':w={s}:h={s + 1}:color=black@0.7:t=fill:"
                   f"enable='lt(mod(t*24+{3 * k}\\,{4 + k})\\,2)'")
    return out


def filter_graph(look: dict) -> str:
    """ffmpeg filter_complex for one archive look. Input [0:v], output label [out]. Same size out as in."""
    p = look["weave_px"]
    g = [f"[0:v]format=gbrp,hue=s=0",                                     # 1. black-and-white
         f"curves=all='{look['curve']}'",                                 #    period contrast
         f"gblur=sigma={look['blur']}",                                   # 2. soft old lens / duplication
         "format=yuv444p",                                                #    (eq + luma grain work in YUV)
         f"eq=brightness='{look['flicker']}*(sin(n*2.3)*0.6+random(0)-0.5)':eval=frame"]   # 3. flicker
    if look.get("scratches", 0) > 0:
        g += _scratches(int(look["scratches"])) + _dust(int(look.get("dust", 0)))          # 4. damage
    g += [f"noise=c0s={look['grain']}:c0f=t+u",                           # 5. grain in brightness only
          f"vignette=angle={look['vignette']}:mode=forward",              # 6. corners fall off
          # 7. gate weave: enlarge by 2p pixels, then cut the original size out at an offset that drifts with two
          #    slow sines + a little per-frame jitter (always inside 0..2p, so no black edge ever shows)
          f"scale=iw+{2 * p}:ih+{2 * p}",
          f"crop=iw-{2 * p}:ih-{2 * p}:'{p}+{p * 0.55:.2f}*sin(n*0.83)+{p * 0.25:.2f}*sin(n*2.9+1)':"
          f"'{p}+{p * 0.45:.2f}*sin(n*0.61+2)+{p * 0.3:.2f}*(random(1)-0.5)'"]
    if look.get("tint"):
        r, gg, b = look["tint"]                                           # aged print: grey -> faded warm brown
        g += ["format=gbrp", f"colorchannelmixer=rr={r}:gg={gg}:bb={b}"]
    if look.get("pillarbox"):
        # 1.37:1 academy frame inside a 16:9 picture: keep the centre, black bars left and right (assumes 16:9 input)
        g += ["crop='trunc(ih*1.37/2)*2':ih", "pad='trunc(ih*16/9/2)*2':ih:(ow-iw)/2:0:black"]
    return ",".join(g) + "[out]"


def run(src: str, dst: str, look_name: str = "kinescope", pillarbox: bool = False) -> int:
    look = dict(LOOKS[look_name], pillarbox=pillarbox or LOOKS[look_name]["pillarbox"])
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-filter_complex", filter_graph(look), "-map", "[out]"]
    if dst.lower().endswith((".png", ".jpg")):
        cmd += ["-frames:v", "1", "-pix_fmt", "rgb24"]
    else:
        cmd += ["-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p"]
    return subprocess.run(cmd + [dst]).returncode


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tc.archive", description="declassified archive-footage look (ffmpeg)")
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--look", default="kinescope", choices=sorted(LOOKS))
    ap.add_argument("--pillarbox", action="store_true", help="1.37:1 academy frame with black side bars")
    a = ap.parse_args(argv)
    return run(a.src, a.dst, a.look, a.pillarbox)


if __name__ == "__main__":
    sys.exit(main())

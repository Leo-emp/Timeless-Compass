# EDIT: the timeline - shot renders + the sound mix -> the finished master video (WS12, ffmpeg).
#   python -m tc edit <job> [--look dusk] [--no-letterbox]      ->  jobs/<id>/master.mp4 + edit.json
# Film grammar (owner rule: serious, cinematic; rule r3: only place/date cards and map labels as text):
#   fade in from black at the start, CUT between shots of the same place (the cut lands on the spoken line: shot
#   times come from the real voice, tc shots), DISSOLVE when the story jumps to another place, a dip to black when
#   a shot asks for it ("transition": "fade_black"), a fade out at the end, then the end card.
#   A dissolve never shifts the picture off its words: the outgoing shot HOLDS its last frame under the dissolve,
#   so the incoming shot still starts exactly on its line.
#   Place/date cards fade in half a second after their shot starts, sit low-left inside the picture, fade out
#   before the shot ends. Long videos get a 2.35:1 letterbox (cinema frame); Shorts stay full 9:16.
#   Optional film look from tc/finish.py is applied under the cards (grade + bloom + grain; text stays clean).
#   Before that, every shot is MATCHED to its scene's hero shot (tc/match.py), so cuts never jump in colour.
# QA after rendering: unexpected black frames, length vs plan, loudness vs the mix target, missing shots.
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from tc import jobs
from tc.cli import register

FADE_IN_S = 1.0          # opening fade from black
FADE_OUT_S = 1.5         # closing fade to black
DISSOLVE_S = 0.6         # place-change dissolve
DIP_S = 0.8              # 'fade_black' dip (out + in)
END_CARD_S = 4.0
CARD_DELAY_S, CARD_MAX_S, CARD_FADE_S = 0.5, 4.0, 0.5
CARD_KINDS = {"place_date", "map_label"}
TRANSITIONS = {"cut", "dissolve", "fade_black"}
FONTS = ["C:/Windows/Fonts/constan.ttf", "C:/Windows/Fonts/georgia.ttf", "C:/Windows/Fonts/BOOKOS.TTF",
         "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "/usr/share/fonts/dejavu/DejaVuSerif.ttf"]


def _src(have, sid):
    if isinstance(have, dict):
        return have.get(sid)
    return sid if sid in have else None


def plan(shots: list[dict], have, kind: str = "long") -> dict:
    """The timeline: one segment per shot (start, dur, source or None, transition in, fade out), the allowed
    cards, and warnings (missing renders, gaps, forbidden captions). `have` = set of shot ids with a render, or a
    dict id -> file."""
    order = sorted(shots, key=lambda s: float(s.get("at") or 0.0))
    segs, cards, warn = [], [], []
    for i, s in enumerate(order):
        start = float(s.get("at") if s.get("at") is not None else (segs[-1]["start"] + segs[-1]["dur"] if segs else 0.0))
        dur = float(s.get("dur") or 0.0)
        if segs:
            prev = segs[-1]
            gap = start - (prev["start"] + prev["dur"])
            if gap > 0.05:                                  # hold the previous shot over a hole in the timing
                prev["dur"] += gap
                warn.append(f"gap of {gap:.2f} s before {s['id']}: {prev['id']} held longer")
            elif gap < -0.05:                               # overlap: the earlier shot gives way
                prev["dur"] = max(0.1, prev["dur"] + gap)
        if i == 0:
            trans = "fade_in"
        elif s.get("transition") in TRANSITIONS:
            trans = s["transition"]
        elif (s.get("where") or "") != (order[i - 1].get("where") or ""):
            trans = "dissolve"
        else:
            trans = "cut"
        src = _src(have, s["id"])
        if src is None:
            warn.append(f"missing render for shot {s['id']}: black in the edit")
        segs.append({"id": s["id"], "src": src, "start": start, "dur": dur, "trans": trans,
                     "trans_s": {"fade_in": FADE_IN_S, "dissolve": DISSOLVE_S, "fade_black": DIP_S}.get(trans, 0.0),
                     "fade_out": 0.0, "where": s.get("where")})
        c = s.get("card")
        if c:
            if c.get("kind") in CARD_KINDS and c.get("text"):
                a = start + CARD_DELAY_S
                cards.append({"text": c["text"], "kind": c["kind"], "start": a,
                              "end": min(start + dur - 0.3, a + CARD_MAX_S)})
            else:
                warn.append(f"card on {s['id']} is a '{c.get('kind')}': only place/date cards and map labels (rule r3)")
    if segs:
        segs[-1]["fade_out"] = FADE_OUT_S
    shots_end = (segs[-1]["start"] + segs[-1]["dur"]) if segs else 0.0
    t0 = segs[0]["start"] if segs else 0.0
    return {"segments": segs, "cards": cards, "warnings": warn, "t0": t0, "shots_end": shots_end,
            "total": shots_end - t0 + END_CARD_S, "kind": kind}


def letterbox_bar(w: int, h: int, ratio) -> int:
    """Height of each black bar that turns a w x h frame into `ratio`:1 (None = no letterbox)."""
    if not ratio or w / h >= ratio:
        return 0
    return int(round((h - w / ratio) / 2))


def _fp(p) -> str:
    """A path inside an ffmpeg filter argument: forward slashes, ':' escaped, single-quoted."""
    return "'" + str(p).replace("\\", "/").replace(":", "\\:") + "'"


def find_font() -> str | None:
    return next((f for f in FONTS if os.path.exists(f)), None)


def build_graph(p: dict, size=(1920, 1080), fps=24, card_files=(), font=None, letterbox=2.35, look=None,
                end_title_file=None) -> str:
    """ffmpeg filter_complex for the plan. Input i = segment i (a render, or a black colour source). Output [vout]."""
    W, H = size
    segs = p["segments"]
    g = []
    for i, s in enumerate(segs):
        nxt = segs[i + 1] if i + 1 < len(segs) else None
        hold = nxt["trans_s"] if nxt and nxt["trans"] == "dissolve" else 0.0     # freeze under the dissolve
        D = s["dur"] + hold
        chain = (f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps},setsar=1,"
                 f"format=yuv420p,tpad=stop_mode=clone:stop_duration={D + 1:.3f},trim=duration={D:.3f},setpts=PTS-STARTPTS")
        if s.get("match"):                                  # shot matching (tc/match.py): same grade as its hero
            chain += f",format=gbrp,{s['match']},format=yuv420p"
        if s["trans"] == "fade_in":
            chain += f",fade=t=in:st=0:d={FADE_IN_S}"
        if s["trans"] == "fade_black":
            chain += f",fade=t=in:st=0:d={DIP_S / 2:.3f}"
        if nxt and nxt["trans"] == "fade_black":
            chain += f",fade=t=out:st={D - DIP_S / 2:.3f}:d={DIP_S / 2:.3f}"
        if s["fade_out"]:
            chain += f",fade=t=out:st={D - s['fade_out']:.3f}:d={s['fade_out']}"
        g.append(chain + f",settb=AVTB[v{i}]")                  # one timebase everywhere (xfade needs it)
    cur = "v0"
    for i in range(1, len(segs)):
        s = segs[i]
        out = f"c{i}"
        if s["trans"] == "dissolve":
            g.append(f"[{cur}][v{i}]xfade=transition=fade:duration={s['trans_s']}:offset={s['start'] - p['t0']:.3f},settb=AVTB[{out}]")
        else:
            g.append(f"[{cur}][v{i}]concat=n=2:v=1:a=0[{out}]")
        cur = out
    end = f"color=c=black:s={W}x{H}:r={fps}:d={END_CARD_S},format=yuv420p,setsar=1,settb=AVTB"
    if end_title_file and font:
        end += (f",drawtext=fontfile={_fp(font)}:textfile={_fp(end_title_file)}:fontsize={int(H * 0.05)}:fontcolor=white:"
                f"x=(w-text_w)/2:y=(h-text_h)/2:alpha='min(1,max(0,min((t-0.5)/1,({END_CARD_S}-0.5-t)/1)))'")
    g.append(end + "[endcard]")
    g.append(f"[{cur}][endcard]concat=n=2:v=1:a=0[cat]")
    if look:
        from tc import finish
        fg = finish.filter_graph(finish.LOOKS[look] if isinstance(look, str) else look)
        g.append(fg.replace("[0:v]", "[cat]").replace("[out]", "[graded]"))
    else:
        g.append("[cat]null[graded]")
    bar = letterbox_bar(W, H, letterbox)
    last = "graded"
    post = []
    for k, c in enumerate(p["cards"]):
        if k >= len(card_files):
            break
        a, b = c["start"] - p["t0"], c["end"] - p["t0"]
        alpha = f"'min(1,max(0,min((t-{a:.2f})/{CARD_FADE_S},({b:.2f}-t)/{CARD_FADE_S})))'"
        font_part = f"fontfile={_fp(font)}:" if font else ""
        post.append(f"drawtext={font_part}textfile={_fp(card_files[k])}:fontsize={int(H * 0.042)}:fontcolor=0xF2EBDD:"
                    f"shadowcolor=black@0.6:shadowx=2:shadowy=2:x={int(W * 0.06)}:y={H - bar - int(H * 0.11)}:"
                    f"alpha={alpha}:enable='between(t,{a:.2f},{b:.2f})'")
    if bar:
        post.append(f"drawbox=x=0:y=0:w=iw:h={bar}:color=black:t=fill,drawbox=x=0:y=ih-{bar}:w=iw:h={bar}:color=black:t=fill")
    g.append(f"[{last}]" + (",".join(post) if post else "null") + "[vout]")
    return ";\n".join(g)


def parse_blackdetect(stderr: str) -> list[tuple[float, float]]:
    return [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+)\s+black_end:([\d.]+)", stderr)]


def qa(p: dict, black: list, duration: float, lufs: float | None, kind: str = "long") -> list[str]:
    """Problems a viewer would notice. Planned darkness (opening fade, dips, closing fade + end card) is fine."""
    from tc.mix import TARGETS
    t0 = p["t0"]
    ok = [(0.0, FADE_IN_S + 0.25), (p["shots_end"] - t0 - FADE_OUT_S - 0.25, p["total"] + 1)]
    for s in p["segments"]:
        if s["trans"] == "fade_black":
            ok.append((s["start"] - t0 - DIP_S, s["start"] - t0 + DIP_S))
    problems = []
    for a, b in black:
        if b - a >= 0.25 and not any(a >= x - 0.05 and b <= y + 0.05 for x, y in ok):
            problems.append(f"black frames at {a:.1f}-{b:.1f} s")
    if abs(duration - p["total"]) > 0.5:
        problems.append(f"length {duration:.1f} s, plan {p['total']:.1f} s")
    tgt = TARGETS.get(kind, TARGETS["long"])["lufs"]
    if lufs is not None and abs(lufs - tgt) > 1.0:
        problems.append(f"loudness {lufs:.1f} LUFS, target {tgt} LUFS")
    problems += [w for w in p["warnings"] if w.startswith("missing")]
    return problems


def _probe(path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json", str(path)],
                       capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    return {"duration": float(d["format"]["duration"]),
            "has_audio": any(s.get("codec_type") == "audio" for s in d.get("streams", []))}


def render(shots, have, audio, out, size=(1920, 1080), fps=24, letterbox=2.35, look="dusk", kind="long",
           end_title="Timeless Compass", font=None, match_shots=True) -> dict:
    """Cut the master: plan -> (shot matching) -> filter graph -> ffmpeg (H.264 CRF 16 + AAC), then QA."""
    p = plan(shots, have, kind)
    if match_shots and isinstance(have, dict) and len(have) > 1:
        from tc import match as _match
        mf = _match.match_filters(shots, have)
        for s in p["segments"]:
            s["match"] = mf.get(s["id"], "")
    W, H = size
    font = font or find_font()
    tmp = Path(tempfile.mkdtemp(prefix="tc_edit_"))
    try:
        card_files = []
        for k, c in enumerate(p["cards"]):
            f = tmp / f"card{k}.txt"; f.write_text(c["text"], encoding="utf-8"); card_files.append(f)
        end_file = None
        if end_title:
            end_file = tmp / "end.txt"; end_file.write_text(end_title, encoding="utf-8")
        graph = build_graph(p, size, fps, card_files, font, letterbox, look, end_file)
        n = len(p["segments"])
        graph += f";\n[{n}:a]apad=whole_dur={p['total']:.3f},atrim=duration={p['total']:.3f},afade=t=out:st={p['total'] - 2.5:.3f}:d=2.5[aout]"
        script = tmp / "graph.txt"; script.write_text(graph, encoding="utf-8")
        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        for s in p["segments"]:
            if s["src"] is not None:
                cmd += ["-i", str(s["src"])]
            else:
                cmd += ["-f", "lavfi", "-t", f"{s['dur'] + 1:.3f}", "-i", f"color=c=black:s={W}x{H}:r={fps}"]
        cmd += ["-i", str(audio), "-/filter_complex", str(script), "-map", "[vout]", "-map", "[aout]",
                "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-t", f"{p['total']:.3f}", "-movflags", "+faststart", str(out)]
        subprocess.run(cmd, check=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    info = _probe(out)
    bd = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(out), "-vf", "blackdetect=d=0.25:pix_th=0.08",
                         "-an", "-f", "null", "-"], capture_output=True, text=True)
    black = parse_blackdetect(bd.stderr)
    lufs = None
    if info["has_audio"]:
        try:
            from tc.mix import _measure
            lufs = _measure(out)["lufs"]
        except Exception:
            lufs = None
    info.update({"plan_total": p["total"], "black": black, "lufs": lufs, "warnings": p["warnings"],
                 "problems": qa(p, black, info["duration"], lufs, kind), "cards": p["cards"]})
    return info


def _args(p):
    p.add_argument("job")
    p.add_argument("--look", default="dusk", help="film look from tc finish (or 'none')")
    p.add_argument("--no-letterbox", action="store_true")
    p.add_argument("--no-match", action="store_true", help="skip shot matching (tc/match.py)")


@register("edit", "cut the master video: shots + mix + cards + transitions + letterbox + QA (ffmpeg)", _args)
def _cmd_edit(args) -> int:
    job = jobs.load_job(args.job)
    d = jobs.job_dir(job.id)
    f = d / "shots.timed.json"
    if not f.exists():
        print("No shots.timed.json yet: run  tc shots <id>  first")
        return 2
    data = json.loads(f.read_text(encoding="utf-8"))
    shots = data if isinstance(data, list) else data.get("shots", [])
    have = {s["id"]: d / "shots" / f"{s['id']}.mp4" for s in shots if (d / "shots" / f"{s['id']}.mp4").exists()}
    audio = d / "mix.wav" if (d / "mix.wav").exists() else d / "voice.wav"
    if not audio.exists():
        print("No mix.wav / voice.wav yet: run  tc mix <id>  first")
        return 2
    short = job.kind == "short"
    info = render(shots, have, audio, d / "master.mp4", size=(1080, 1920) if short else (1920, 1080),
                  letterbox=None if (short or args.no_letterbox) else 2.35,
                  look=None if args.look == "none" else args.look, kind=job.kind, match_shots=not args.no_match)
    (d / "edit.json").write_text(json.dumps(info, indent=2, default=str), encoding="utf-8")
    print(f"master.mp4: {info['duration']:.1f} s, {len(have)}/{len(shots)} shots rendered, loudness {info['lufs']} LUFS")
    for w in info["warnings"]:
        print("  warning:", w)
    for x in info["problems"]:
        print("  QA:", x)
    return 0 if not info["problems"] else 1

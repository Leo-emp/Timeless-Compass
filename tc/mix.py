# The final mix: everything you HEAR in the video, in one file  jobs/<id>/mix.wav  (48 kHz stereo).
#
#   voice.wav   narration + character dialogue (tc voice), the loudest thing, never covered
#   sound.json  sfx layers + ambience beds (tc sfx plan)
#   music.json  music cues, only at r11 moments (tc music pick)
#
# How it is mixed:
#   1. every clip is brought to a common level first: its measured loudness (lufs in the library index) is
#      moved to the voice level (-14 LUFS), then the plan's db (e.g. -6 = 6 dB under the voice) is applied
#   2. clips are placed on the timeline (adelay), trimmed, faded, looped where asked, music seeks into the track
#   3. music + ambience are DUCKED under the voice (sidechain compressor keyed by the voice) so every word stays
#      clear, and swell back up in the gaps (r11: music arrives at chosen moments)
#   4. loudness standard (the owner's approved style from CapitalCode): long ~ -12 LUFS, Shorts louder ~ -10 LUFS,
#      true peak <= -1 dBTP; a second gain pass corrects the result if it misses by more than 0.5 LU
# The filter graph goes into a script file (Windows command lines are too short for a few hundred clips).
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from tc import jobs, paths
from tc.cli import register

VOICE_LUFS = -14.0               # tc voice masters narration here (tc/voice.py MASTER_CHAIN)
TARGETS = {"long": {"lufs": -12.0, "tp": -1.0}, "short": {"lufs": -10.0, "tp": -1.0}}
DUCK = "sidechaincompress=threshold=0.02:ratio=8:attack=15:release=400:makeup=1"
TAIL_S = 2.0                     # let the last music fade / reverb ring after the voice ends


def _fpath(p) -> str:
    """A file path written inside an ffmpeg filter: forward slashes, ':' escaped, quoted."""
    return "'" + str(p).replace("\\", "/").replace(":", "\\:") + "'"


def clip_gain(db: float, file_lufs: float | None) -> float:
    """dB to apply to a clip: bring its loudness to the voice level, then the plan's db relative to the voice."""
    return db + ((VOICE_LUFS - file_lufs) if file_lufs is not None else 0.0)


def measure_lufs(path) -> float | None:
    """Integrated loudness of a file (None for silence / unreadable files)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", r.stderr[r.stderr.rfind("Summary:"):])
    v = float(m.group(1)) if m else None
    return v if v is not None and v > -70 else None


def build_graph(clips: list[dict], voice_s: float, target: dict) -> str:
    """The ffmpeg filter graph. Input [0:a] is voice.wav; every clip is read with amovie."""
    fmt = "aformat=sample_rates=48000:channel_layouts=stereo"
    parts = [f"[0:a]{fmt},apad=pad_dur={TAIL_S},asplit=2[voice][key]"]
    buses = {"fx": [], "amb": [], "music": []}
    for i, c in enumerate(clips):
        src = f"amovie={_fpath(c['path'])}" + (":loop=0" if c.get("loop") else "") + \
              (f":seek_point={c['seek']:g}" if c.get("seek") else "")
        ms = int(round(float(c["at"]) * 1000))
        fo = float(c.get("fade_out") or 0)
        chain = [src, fmt, f"atrim=0:{float(c['dur']):.3f}", "asetpts=N/SR/TB"]
        if c.get("fade_in"):
            chain.append(f"afade=t=in:d={float(c['fade_in']):.3f}")
        if fo:
            chain.append(f"afade=t=out:st={max(0.0, float(c['dur']) - fo):.3f}:d={fo:.3f}")
        chain += [f"volume={float(c['gain']):.2f}dB", f"adelay={ms}|{ms}"]
        parts.append(",".join(chain) + f"[c{i}]")
        buses[c["bus"]].append(f"[c{i}]")
    mixed = ["[voice]"]
    if buses["fx"]:
        parts.append("".join(buses["fx"]) + f"amix=inputs={len(buses['fx'])}:normalize=0:duration=longest[fx]")
        mixed.append("[fx]")
    bed = buses["amb"] + buses["music"]
    if bed:
        # music + ambience ducked under the voice
        parts.append("".join(bed) + f"amix=inputs={len(bed)}:normalize=0:duration=longest[bed]")
        parts.append(f"[bed][key]{DUCK}[ducked]")
        mixed.append("[ducked]")
    else:
        parts.append("[key]anullsink")
    total = voice_s + TAIL_S
    parts.append("".join(mixed) + f"amix=inputs={len(mixed)}:normalize=0:duration=first,atrim=0:{total:.3f},"
                 f"loudnorm=I={target['lufs']:g}:TP={target['tp']:g}:LRA=11,"
                 f"alimiter=limit={10 ** ((target['tp'] - 0.3) / 20):.4f}:level=false[out]")
    return ";\n".join(parts)


def _measure(path: Path) -> dict:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    s = r.stderr[r.stderr.rfind("Summary:"):]
    lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", s).group(1))
    peak = float(re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", s).group(1))
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                               capture_output=True, text=True).stdout.strip())
    return {"lufs": lufs, "peak_db": peak, "duration_s": round(dur, 3)}


def _duration(path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                capture_output=True, text=True, check=True).stdout.strip())


def render(voice: Path, clips: list[dict], out: Path, kind: str) -> dict:
    """Mix to out (48 kHz stereo 24-bit wav), then check the loudness and fix it once if it missed."""
    target = TARGETS[kind]
    graph = build_graph(clips, _duration(voice), target)
    fd, script = tempfile.mkstemp(suffix=".ffgraph"); os.close(fd)
    try:
        Path(script).write_text(graph, encoding="utf-8")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(voice), "-/filter_complex", script,
                        "-map", "[out]", "-ar", "48000", "-c:a", "pcm_s24le", str(out)], check=True)
    finally:
        os.remove(script)
    info = _measure(out)
    miss = target["lufs"] - info["lufs"]
    if abs(miss) > 0.5:                            # one correction pass (gain + the same true-peak ceiling)
        tmp = out.with_suffix(".fix.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out), "-af",
                        f"volume={miss:.2f}dB,alimiter=limit={10 ** ((target['tp'] - 0.3) / 20):.4f}:level=false",
                        "-c:a", "pcm_s24le", str(tmp)], check=True)
        os.replace(tmp, out)
        info = _measure(out)
    info.update({"target_lufs": target["lufs"], "true_peak_max": target["tp"], "clips": len(clips)})
    return info


def clips_from_plans(sound: dict, music: dict, sfx_idx: dict, tracks: dict, sfx_dir: Path, music_dir: Path):
    """sound.json + music.json -> mix clips (with paths + gains) and a list of what could not be found."""
    snd = {s["id"]: s for s in sfx_idx.get("sounds", [])}
    trk = {t["id"]: t for t in tracks.get("tracks", [])}
    clips, missing = [], []
    def add(entry, bus, lib, base):
        clips.append({"path": str(Path(base) / lib["file"]), "at": entry["at"], "dur": entry["dur"],
                      "gain": clip_gain(entry.get("db", 0.0), lib.get("lufs")), "loop": bool(entry.get("loop")),
                      "fade_in": entry.get("fade_in", 0), "fade_out": entry.get("fade_out", 0),
                      "seek": entry.get("seek", 0), "bus": bus})
    for e in sound.get("events", []):
        if e["sound"] in snd:
            add(e, "fx", snd[e["sound"]], sfx_dir)
        else:
            missing.append(f"sfx {e['sound']} not in the library")
    for b in sound.get("ambience", []):
        if b.get("sound") in snd:
            add(b, "amb", snd[b["sound"]], sfx_dir)
        else:
            missing.append(f"ambience bed at {float(b['at']):.1f} s has no sound")
    for m in music.get("cues", []):
        t = trk.get(m["track"]) or {"file": m["file"]}
        add(dict(m, loop=False), "music", t, music_dir)
    return clips, missing


@register("mix", "final audio mix: voice + dialogue + sfx + ambience + music (ducked) at the loudness standard",
          lambda p: p.add_argument("job"))
def _cmd_mix(args) -> int:
    from tc import music as music_mod, sfx as sfx_mod
    job = jobs.load_job(args.job)
    d = jobs.job_dir(job.id)
    if not (d / "voice.wav").exists():
        print("No voice.wav yet: run  tc voice <id>  first")
        return 2
    load = lambda f: json.loads((d / f).read_text(encoding="utf-8")) if (d / f).exists() else {}
    sound, music = load("sound.json"), load("music.json")
    if not sound:
        print("note: no sound.json (tc sfx plan <id>) - mixing without sound effects / ambience")
    sfx_idx, tracks = sfx_mod.load_index(), music_mod.load_tracks()
    # measure library files that have no loudness yet, once (saved back to the indexes)
    for lib_idx, key, base, save in ((sfx_idx, "sounds", paths.LIBRARY / "sfx" / "files", paths.LIBRARY / "sfx" / "index.json"),
                                     (tracks, "tracks", paths.LIBRARY / "music" / "files", paths.LIBRARY / "music" / "tracks.json")):
        changed = False
        for s in lib_idx.get(key, []):
            if "lufs" not in s and (base / s["file"]).exists():
                s["lufs"] = measure_lufs(base / s["file"]); changed = True
        if changed:
            save.write_text(json.dumps(lib_idx, indent=2, ensure_ascii=False), encoding="utf-8")
    clips, missing = clips_from_plans(sound, music, sfx_idx, tracks, paths.LIBRARY / "sfx" / "files",
                                      paths.LIBRARY / "music" / "files")
    for m in missing:
        print("  skipped:", m)
    info = render(d / "voice.wav", clips, d / "mix.wav", job.kind)
    info["skipped"] = missing
    (d / "mix.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(f"mix.wav: {info['duration_s']:.1f} s, {info['lufs']} LUFS (target {info['target_lufs']}), peak {info['peak_db']} dB,"
          f" {len(clips)} clips")
    return 0

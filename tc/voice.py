# Narration: script lines -> SSML -> Azure speech -> mastered voice.wav.
# Narrator only (owner rule r1). One SSML document per script section keeps each request small and safe.
# Mastering chain was tuned by ear with the owner (spike 2026-11-19): warm, clear, steady, YouTube loudness.
import json
import re
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

from tc import jobs
from tc.cli import register
from tc.config import Config, get_config
from tc.dialogue import character_of, duration
from tc.http import post_bytes
from tc.script import Line, is_approved, parse_script

SSML_HEAD = ('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
             'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US"><voice name="{voice}"><prosody rate="{rate}">')
SSML_TAIL = "</prosody></voice></speak>"
BEAT = '<break time="800ms"/>'
LINE_GAP = '<break time="350ms"/>'        # a breath between narration lines
MASTER_CHAIN = ("highpass=f=70,equalizer=f=160:t=q:w=1:g=2,equalizer=f=3500:t=q:w=1.2:g=1.5,"
                "acompressor=threshold=-22dB:ratio=3:attack=8:release=120:makeup=4,loudnorm=I=-14:TP=-1.0:LRA=7")


class VoiceError(Exception):
    pass


def plan_segments(lines: list[Line], voice: str, rate: str) -> list[dict]:
    """The voice track in order, as pieces:
         {"kind": "ssml", "doc": ...}        narration (one SSML document per section, as before)
         {"kind": "dialogue", "index": n}    a character line NAME: "..." (its Fish wav comes from tc dialogue)
    A dialogue line cuts the narration of its section in two, so the narrator never reads it out."""
    segs, current, parts = [], None, []
    def flush():
        if parts:
            segs.append({"kind": "ssml", "doc": SSML_HEAD.format(voice=voice, rate=rate) + " ".join(parts) + SSML_TAIL})
    for l in lines:
        if character_of(l):
            flush(); parts = []
            segs.append({"kind": "dialogue", "index": l.index})
            continue
        if l.section != current:
            flush(); parts = []; current = l.section
        text = escape(l.text)
        parts.append((text + " " + BEAT) if l.beat else (text + " " + LINE_GAP))
    flush()
    return segs


def build_ssml(lines: list[Line], voice: str, rate: str) -> list[str]:
    """Only the narration documents (a script without dialogue gives exactly one per section)."""
    return [s["doc"] for s in plan_segments(lines, voice, rate) if s["kind"] == "ssml"]


def dialogue_offsets(segs: list[dict], durations: list[float]) -> dict[str, float]:
    """Where each dialogue line starts in voice.wav: the sum of every piece before it. {"line index": seconds}"""
    out, t = {}, 0.0
    for s, d in zip(segs, durations):
        if s["kind"] == "dialogue":
            out[str(s["index"])] = round(t, 3)
        t += d
    return out


def synthesize(ssml: str, out: Path, cfg: Config, post=post_bytes) -> Path:
    """Send one SSML document to Azure; write the audio only if Azure really returned audio."""
    if not (cfg.azure_key and cfg.azure_region):
        raise VoiceError("AZURE_SPEECH_KEY / AZURE_SPEECH_REGION missing in .env")
    url = f"https://{cfg.azure_region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {"Ocp-Apim-Subscription-Key": cfg.azure_key, "Content-Type": "application/ssml+xml",
               "X-Microsoft-OutputFormat": "riff-48khz-16bit-mono-pcm", "User-Agent": "timeless-compass"}
    status, body, ctype = post(url, ssml.encode("utf-8"), headers, timeout=180)
    if status != 200 or not ctype.startswith("audio/"):
        raise VoiceError(f"Azure TTS failed: HTTP {status} {ctype} {body[:200]!r}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(body)
    return out


def _measure(path: Path) -> dict:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    summary = r.stderr[r.stderr.rfind("Summary:"):]
    lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    peak = float(re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary).group(1))
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                               capture_output=True, text=True).stdout.strip())
    return {"lufs": lufs, "peak_db": peak, "duration_s": round(dur, 3)}


def master(raws: list[Path], out: Path) -> dict:
    """Join the section files in order, run the mastering chain, measure the result."""
    ins = sum([["-i", str(p)] for p in raws], [])
    fc = "".join(f"[{i}:a]" for i in range(len(raws))) + f"concat=n={len(raws)}:v=0:a=1[c];[c]{MASTER_CHAIN}[o]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", fc, "-map", "[o]",
                    "-ar", "48000", "-ac", "1", str(out)], check=True)
    return _measure(out)


@register("voice", "narrate the approved script with Azure and master it", lambda p: p.add_argument("job"))
def _cmd_voice(args) -> int:
    job = jobs.load_job(args.job)
    d = jobs.job_dir(job.id)
    if not is_approved(d):
        print("The script is not approved (or was edited after approval): show the owner, then tc script <id> --approve")
        return 2
    cfg = get_config()
    lines = parse_script((d / "script.md").read_text(encoding="utf-8"))
    segs = plan_segments(lines, cfg.voice, cfg.voice_rate)
    # character lines: their Fish wavs must exist first (tc dialogue <id>)
    spoken = {}
    if any(s["kind"] == "dialogue" for s in segs):
        df = d / "dialogue.json"
        spoken = {r["index"]: d / "dialogue" / r["wav"] for r in json.loads(df.read_text(encoding="utf-8"))["lines"]} if df.exists() else {}
        missing = [s["index"] for s in segs if s["kind"] == "dialogue" and not spoken.get(s["index"], Path("-")).exists()]
        if missing:
            print(f"dialogue lines {missing} are not voiced yet: run  tc dialogue {job.id}  first")
            return 2
    raws, n_ssml = [], sum(s["kind"] == "ssml" for s in segs)
    try:
        for i, s in enumerate(segs):
            if s["kind"] == "dialogue":
                raws.append(spoken[s["index"]])
                continue
            raws.append(synthesize(s["doc"], d / "voice" / f"section_{i:02d}.wav", cfg))
            print(f"narration piece {len([r for r in raws if 'section_' in r.name])}/{n_ssml} voiced")
    except VoiceError as e:
        print(e); jobs.mark(job, "voice", "failed", str(e)[:120]); jobs.save_job(job)
        return 1
    info = master(raws, d / "voice.wav")
    info.update({"voice": cfg.voice, "sections": n_ssml})
    if spoken:
        from tc import lipsync
        info["dialogue_at"] = dialogue_offsets(segs, [duration(r) for r in raws])
        dj = json.loads((d / "dialogue.json").read_text(encoding="utf-8"))
        (d / "lipsync.json").write_text(json.dumps(lipsync.job_timeline(dj, info), indent=2), encoding="utf-8")
    (d / "voice.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    jobs.mark(job, "voice", "done", f"{info['duration_s']:.1f}s at {info['lufs']} LUFS"); jobs.save_job(job)
    print(f"voice.wav: {info['duration_s']:.1f} s, {info['lufs']} LUFS, peak {info['peak_db']} dB")
    return 0


# The audio commands (tc dialogue / sfx / music / mix) live in their own modules. tc/cli.py loads "voice", and
# importing them here registers their commands without editing the shared cli.py (BACKLOG rule 1: WS11 files only).
from tc import dialogue as _dialogue, mix as _mix, music as _music, sfx as _sfx  # noqa: E402,F401

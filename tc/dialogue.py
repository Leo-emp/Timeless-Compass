# Character dialogue: a script line written as   NAME: "..."   is spoken by that character, not the narrator.
#
#   ## climax
#   The king stood up on the hill. [src: herodotus-8.90]
#   XERXES: "My men have become women, and my women men." [src: herodotus-8.88]
#   LEONIDAS (messenger): "Come and take them." [src: plutarch-apoph]      <- (voice key) picks the voice
#
# Every character voice is a Fish Audio voice from library/voices.json (owner picked 5 on 2026-11-19).
# The speaker name finds the voice: XERXES -> "xerxes". A job may map other names in jobs/<id>/cast_voices.json
# ({"SICINNUS": "messenger"}), or the line names the voice in brackets as above.
#
# Money + safety rules (docs/BACKLOG.md):
#   - only FREE Fish models are allowed (s2.1-pro-free); a paid model name is refused before any request
#   - the API key travels in a header file through tc.http (never on a command line, never printed)
#   - every line we use is logged in library/fish_usage.json (who, which voice, how many bytes, when),
#     so the owner can see exactly what the paid plan would cost once the channel is monetised
#   - a line already voiced (same voice + same words) is reused from disk, never requested twice
#
# Output per line: jobs/<id>/dialogue/line_<index>_<voice>_<hash>.mp3 (as Fish sent it) and a .wav
# (48 kHz mono, 0.3 s of silence before and after = a natural breath between narrator and character).
# tc voice then splices these wavs into voice.wav at the right place.
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from tc import jobs, paths
from tc.cli import register
from tc.config import load_env
from tc.http import post_bytes
from tc.script import Line, is_approved, parse_script

FISH_API = "https://api.fish.audio/v1/tts"
FISH_MODEL = "s2.1-pro-free"
FREE_MODELS = {"s2.1-pro-free"}          # the only models that cost nothing (free plan = non-commercial use)
PAD_S = 0.3                              # breath of silence before and after each spoken line

# NAME: "words"   or   NAME (voice_key): "words"   -- NAME is UPPER CASE so narration that quotes someone
# ('He said: "no".') is never mistaken for a character speaking. Straight or curly quotes both work.
_DIALOGUE = re.compile(r'^([A-Z][A-Z0-9_ \'-]{0,40}?)\s*(?:\(([a-z0-9_]+)\))?\s*:\s*["“](.+?)["”]\s*$')


class DialogueError(Exception):
    pass


@dataclass
class DialogueLine:
    index: int          # the line's position in the whole script (same index as tc.script.Line)
    section: str
    speaker: str        # as written in the script, e.g. "XERXES"
    voice_key: str | None
    text: str           # only the spoken words, without the name and quotes


def parse_dialogue(text: str):
    """'XERXES: "Burn it."' -> ("XERXES", None, "Burn it."); narration -> None."""
    m = _DIALOGUE.match(text.strip())
    if not m:
        return None
    return m.group(1).strip(), m.group(2), m.group(3).strip()


def character_of(line) -> tuple[str, str | None, str] | None:
    """(speaker, voice key, spoken words) if a character speaks this script line, else None.
    tc.script (WS13) parses the same NAME: "..." shape into line.speaker / voice_key / spoken; use those when
    present, otherwise read the line text ourselves (both give the same answer)."""
    if getattr(line, "speaker", None):
        return line.speaker, getattr(line, "voice_key", None), getattr(line, "spoken", "") or parse_dialogue(line.text)[2]
    return parse_dialogue(line.text)


def dialogue_lines(lines: list[Line]) -> list[DialogueLine]:
    out = []
    for l in lines:
        d = character_of(l)
        if d:
            out.append(DialogueLine(l.index, l.section, d[0], d[1], d[2]))
    return out


def load_voices(path: Path | None = None) -> dict:
    path = path or paths.LIBRARY / "voices.json"
    return json.loads(Path(path).read_text(encoding="utf-8"))


def voice_for(speaker: str, voice_key: str | None, voices: dict, mapping: dict | None = None) -> tuple[str, dict]:
    """Which voice speaks this line: the (key) on the line, else the job's mapping, else the speaker's own name."""
    chars = voices.get("characters", {})
    key = voice_key or (mapping or {}).get(speaker) or re.sub(r"[^a-z0-9]+", "_", speaker.lower()).strip("_")
    if key not in chars:
        raise DialogueError(f"no voice for {speaker!r} (looked for {key!r}); add it to jobs/<id>/cast_voices.json "
                            f"or write NAME (voice): ... ; voices: {sorted(chars)}")
    v = chars[key]
    if v.get("provider") != "fish" or not v.get("reference_id"):
        raise DialogueError(f"voice {key!r} is not a Fish voice with a reference_id")
    return key, v


def fish_tts(text: str, reference_id: str, out: Path, api_key: str | None, model: str = FISH_MODEL,
             post=post_bytes) -> Path:
    """One Fish Audio request. Writes the mp3 ONLY if Fish really sent audio back."""
    if model not in FREE_MODELS:
        raise DialogueError(f"model {model!r} is not a free Fish model; only {sorted(FREE_MODELS)} (rule: never spend money)")
    if not api_key:
        raise DialogueError("FISH_AUDIO_API_KEY missing in .env")
    body = json.dumps({"text": text, "reference_id": reference_id, "format": "mp3", "normalize": True}).encode("utf-8")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "model": model,
               "User-Agent": "timeless-compass"}
    status, data, ctype = post(FISH_API, body, headers, timeout=180)
    if status != 200 or not ctype.startswith("audio/"):
        # the error body comes from Fish, not from us, so it never contains our key
        raise DialogueError(f"Fish TTS failed: HTTP {status} {ctype} {data[:200]!r}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return out


def log_usage(entry: dict, path: Path | None = None) -> None:
    """Append one used line to library/fish_usage.json (a date is added automatically)."""
    path = Path(path or paths.LIBRARY / "fish_usage.json")
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
        "_note": "Every Fish Audio line used by Timeless Compass (tc dialogue). bytes = what Fish bills on paid plans.",
        "lines": []}
    data["lines"].append({"date": datetime.now().isoformat(timespec="seconds"), **entry})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def to_wav(mp3: Path, wav: Path, pad_s: float = PAD_S) -> float:
    """mp3 -> 48 kHz mono 16-bit wav with a breath of silence on both sides; returns the length in seconds."""
    ms = int(pad_s * 1000)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3),
                    "-af", f"adelay={ms}:all=1,apad=pad_dur={pad_s}", "-ar", "48000", "-ac", "1",
                    "-c:a", "pcm_s16le", str(wav)], check=True)
    return duration(wav)


def duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return round(float(r.stdout.strip()), 3)


def voice_dialogue(job_id: str, lines: list[Line], out_dir: Path, voices: dict, api_key: str | None,
                   mapping: dict | None = None, post=post_bytes, usage_log: Path | None = None) -> list[dict]:
    """Voice every dialogue line of a script. Returns one record per line (also saved as dialogue.json by the command)."""
    out_dir = Path(out_dir)
    records = []
    for d in dialogue_lines(lines):
        key, v = voice_for(d.speaker, d.voice_key, voices, mapping)
        h = hashlib.sha1(f"{v['reference_id']}|{FISH_MODEL}|{d.text}".encode("utf-8")).hexdigest()[:8]
        stem = f"line_{d.index:03d}_{key}_{h}"
        mp3, wav = out_dir / f"{stem}.mp3", out_dir / f"{stem}.wav"
        cached = mp3.exists() and mp3.stat().st_size > 0
        if not cached:
            fish_tts(d.text, v["reference_id"], mp3, api_key, post=post)
        dur = to_wav(mp3, wav)
        log_usage({"job": job_id, "line": d.index, "speaker": d.speaker, "voice": key,
                   "reference_id": v["reference_id"], "model": FISH_MODEL, "bytes": len(d.text.encode("utf-8")),
                   "text": d.text, "file": mp3.name, "cached": cached}, usage_log)
        records.append({"index": d.index, "section": d.section, "speaker": d.speaker, "voice": key, "text": d.text,
                        "mp3": mp3.name, "wav": wav.name, "duration_s": dur, "pad_s": PAD_S})
    return records


@register("dialogue", "voice the script's character lines (NAME: \"...\") with Fish + lip-sync data",
          lambda p: p.add_argument("job"))
def _cmd_dialogue(args) -> int:
    from tc import lipsync                        # here, not at the top: lipsync imports this module
    job = jobs.load_job(args.job)
    d = jobs.job_dir(job.id)
    if not is_approved(d):
        print("No fresh-viewer GO for this exact script (or it was edited after the GO): run tc viewer <id> --packet / --record")
        return 2
    lines = parse_script((d / "script.md").read_text(encoding="utf-8"))
    if not dialogue_lines(lines):
        print("no dialogue lines in the script (narrator only) - nothing to do")
        return 0
    mf = d / "cast_voices.json"
    mapping = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else None
    try:
        records = voice_dialogue(job.id, lines, d / "dialogue", load_voices(), load_env().get("FISH_AUDIO_API_KEY"), mapping)
    except DialogueError as e:
        print(e)
        return 1
    # lip sync (mouth shapes) for WS1, if Rhubarb is installed; dialogue still works without it
    exe = lipsync.find_rhubarb()
    for r in records:
        if exe:
            r["lipsync"] = lipsync.cues_for(exe, d / "dialogue" / r["wav"], r["text"])
    (d / "dialogue.json").write_text(json.dumps({"model": FISH_MODEL, "lines": records}, indent=2, ensure_ascii=False),
                                     encoding="utf-8")
    for r in records:
        print(f"line {r['index']}: {r['speaker']} ({r['voice']}) {r['duration_s']:.1f} s"
              + ("" if exe else "  [no Rhubarb: lip sync skipped]"))
    print("dialogue.json written; now run  tc voice <id>  (it splices these lines into voice.wav)")
    return 0

# Lip sync: which mouth shape a character makes at every moment of a spoken dialogue line.
#
# Rhubarb Lip Sync (free, MIT licence, runs offline: C:\Users\User\tools\rhubarb\...\rhubarb.exe) listens to a
# dialogue wav and returns "mouth cues": time ranges with one of 9 mouth shapes (A-H + X = rest).
# Giving it the line's words (--dialogFile) makes the shapes more accurate.
#
# We turn the cues into a timeline for WS1 (blender/lib/expressions.py drives the face rig):
#   jobs/<id>/lipsync.json  ->  {"fps": 24, "lines": [{index, speaker, at, cues: [...], frames: [...]}]}
# Every cue carries simple mouth controls (0..1) so the face rig does not need to know Rhubarb:
#   jaw    = how far the jaw drops        round  = lips pushed forward (oo, w)
#   closed = lips pressed together (m b p) wide = lips stretched (ee)
#   teeth_lip = top teeth on lower lip (f v)   tongue = tongue up behind teeth (l)
import json
import os
import subprocess
import tempfile
from pathlib import Path

RHUBARB_DIR = Path(r"C:\Users\User\tools\rhubarb")

# Rhubarb's 9 shapes (see its README "Mouth shapes") with our mouth controls.
SHAPES = {
    "X": {"jaw": 0.00, "round": 0.0, "closed": 0.6, "wide": 0.0, "teeth_lip": 0.0, "tongue": 0.0, "phonemes": "rest / silence"},
    "A": {"jaw": 0.00, "round": 0.0, "closed": 1.0, "wide": 0.0, "teeth_lip": 0.0, "tongue": 0.0, "phonemes": "M B P"},
    "B": {"jaw": 0.12, "round": 0.0, "closed": 0.0, "wide": 0.4, "teeth_lip": 0.0, "tongue": 0.0, "phonemes": "K S T EE (teeth almost closed)"},
    "C": {"jaw": 0.35, "round": 0.0, "closed": 0.0, "wide": 0.3, "teeth_lip": 0.0, "tongue": 0.0, "phonemes": "EH AE (open)"},
    "D": {"jaw": 0.70, "round": 0.0, "closed": 0.0, "wide": 0.2, "teeth_lip": 0.0, "tongue": 0.0, "phonemes": "AA (wide open)"},
    "E": {"jaw": 0.30, "round": 0.5, "closed": 0.0, "wide": 0.0, "teeth_lip": 0.0, "tongue": 0.0, "phonemes": "AO ER (slightly rounded)"},
    "F": {"jaw": 0.12, "round": 0.9, "closed": 0.0, "wide": 0.0, "teeth_lip": 0.0, "tongue": 0.0, "phonemes": "UW OW W (puckered)"},
    "G": {"jaw": 0.10, "round": 0.0, "closed": 0.0, "wide": 0.1, "teeth_lip": 1.0, "tongue": 0.0, "phonemes": "F V"},
    "H": {"jaw": 0.30, "round": 0.0, "closed": 0.0, "wide": 0.1, "teeth_lip": 0.0, "tongue": 1.0, "phonemes": "L (tongue up)"},
}


def find_rhubarb() -> str | None:
    """Path to rhubarb.exe: TC_RHUBARB if set, else the newest copy under C:\\Users\\User\\tools\\rhubarb."""
    env = os.environ.get("TC_RHUBARB")
    if env and Path(env).exists():
        return env
    found = sorted(RHUBARB_DIR.glob("*/rhubarb.exe")) if RHUBARB_DIR.exists() else []
    return str(found[-1]) if found else None


def cues_for(exe: str, wav: Path, text: str, runner=subprocess.run) -> list[dict]:
    """Run Rhubarb on one dialogue wav (with its words) and return its mouth cues."""
    fd, txt = tempfile.mkstemp(suffix=".txt"); os.close(fd)
    fd, out = tempfile.mkstemp(suffix=".json"); os.close(fd)
    try:
        Path(txt).write_text(text, encoding="utf-8")
        r = runner([exe, "-q", "-f", "json", "--dialogFile", txt, "-o", out, str(wav)],
                   capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            raise RuntimeError(f"rhubarb failed on {Path(wav).name}: {r.stderr[-300:]}")
        return json.loads(Path(out).read_text(encoding="utf-8"))["mouthCues"]
    finally:
        for p in (txt, out):
            if os.path.exists(p):
                os.remove(p)


def timeline(cues: list[dict], offset: float = 0.0) -> list[dict]:
    """Rhubarb cues -> cues on the video timeline (offset = where the line starts in voice.wav) + mouth controls."""
    out = []
    for c in cues:
        m = {k: v for k, v in SHAPES[c["value"]].items() if k != "phonemes"}
        out.append({"start": round(c["start"] + offset, 3), "end": round(c["end"] + offset, 3), "shape": c["value"], **m})
    return out


def frames(cues: list[dict], fps: int = 24) -> list[str]:
    """One mouth shape per video frame (from the line's own start), easy to key frame-by-frame in Blender."""
    if not cues:
        return []
    end = max(c["end"] for c in cues)
    n = int(round(end * fps))
    out, k = [], 0
    for f in range(n):
        t = (f + 0.5) / fps                      # sample the middle of each frame
        while k + 1 < len(cues) and t >= cues[k]["end"]:
            k += 1
        out.append(cues[k]["value"])
    return out


def job_timeline(dialogue: dict, voice: dict | None, fps: int = 24) -> dict:
    """dialogue.json + voice.json (where tc voice placed each line) -> lipsync.json for the face rig."""
    at = (voice or {}).get("dialogue_at", {})
    lines = []
    for r in dialogue.get("lines", []):
        cues = r.get("lipsync") or []
        start = at.get(str(r["index"]))
        lines.append({"index": r["index"], "speaker": r["speaker"], "voice": r.get("voice"), "at": start,
                      "cues": timeline(cues, start or 0.0), "frames": frames(cues, fps)})
    return {"fps": fps, "note": "at = seconds into voice.wav (None until tc voice has run); frames start at 'at'",
            "lines": lines}


# ---------------- 2D film engine (plan 4): the film reads lip sync from film/src/jobs/<id>/lipsync.json ----------------
def write_film_lipsync(dialogue: dict, voice: dict | None, out: Path, fps: int = 24) -> Path:
    """Write the absolute-time mouth cues the film kit's mouthAt() reads (film/src/kit/lipsync.ts)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(job_timeline(dialogue, voice, fps), indent=1), encoding="utf-8")
    return out


def _cmd_lipsync(args) -> int:
    import re
    from tc import jobs
    from tc.paths import ROOT
    d = jobs.job_dir(args.job)
    load = lambda f: json.loads((d / f).read_text(encoding="utf-8")) if (d / f).exists() else None
    dialogue = load("dialogue.json")
    if not dialogue:
        print("no dialogue.json yet (tc dialogue <id>)")
        return 1
    slug = re.sub(r"[^a-z0-9_]", "_", args.job.lower())
    print(write_film_lipsync(dialogue, load("voice.json"), ROOT / "film" / "src" / "jobs" / slug / "lipsync.json"))
    return 0


def _register():
    from tc.cli import register
    register("lipsync", "write the film's lip-sync cues (film/src/jobs/<id>/lipsync.json) from dialogue.json",
             lambda p: p.add_argument("job"))(_cmd_lipsync)


_register()

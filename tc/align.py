# Word timings: WHEN is each script line actually spoken in voice.wav?
# 1) faster-whisper listens and gives timed words (no script prompt: with one it can "hear" lines not yet spoken).
# 2) difflib lines those heard words up with the script's words, so misheard names
#    ("Themistocles" -> "the mistocles") don't break the timing.
# Cuts and shot durations are built from these times.
# NOTE: run with plain `python`, not `python -I` (faster-whisper is in the user site-packages).
import difflib
import json
import re
import subprocess
from pathlib import Path

from tc import jobs
from tc.cli import register
from tc.script import Line, parse_script

FLAG_RATIO = 0.6


def _norm(w: str) -> str:
    return re.sub(r"[^a-z0-9']", "", w.lower())


def transcribe(wav: Path) -> list[dict]:
    import numpy as np
    from faster_whisper import WhisperModel
    model = WhisperModel("small.en", device="cpu", compute_type="int8")     # ~0.5 GB RAM, CPU only
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, dtype=np.float32)
    segments, _ = model.transcribe(audio, word_timestamps=True, beam_size=5, vad_filter=False,
                                   condition_on_previous_text=False)
    return [{"w": w.word.strip(), "s": round(float(w.start), 3), "e": round(float(w.end), 3)} for seg in segments for w in (seg.words or [])]


def align_lines(lines: list[Line], heard: list[dict]) -> list[dict]:
    script_words, owner = [], []                    # every script word + which line it belongs to
    for li, l in enumerate(lines):
        for w in l.text.split():
            script_words.append(_norm(w)); owner.append(li)
    heard_words = [_norm(h["w"]) for h in heard]
    match = {}                                      # script word index -> heard word index
    sm = difflib.SequenceMatcher(a=script_words, b=heard_words, autojunk=False)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            match[blk.a + k] = blk.b + k
    # first/last matched heard index per line
    per = [[match[i] for i in range(len(script_words)) if owner[i] == li and i in match] for li in range(len(lines))]
    first_word = {}
    for i, li in enumerate(owner):
        first_word.setdefault(li, i)
    out = []
    for li, l in enumerate(lines):
        n = len(l.text.split())
        ratio = round(len(per[li]) / n, 3) if n else 0.0
        out.append({"section": l.section, "index": l.index, "start": None, "end": None, "matched_ratio": ratio, "_h": per[li]})
    for li, r in enumerate(out):
        h = r["_h"]
        if not h:
            continue
        prev_last = next((out[j]["_h"][-1] for j in range(li - 1, -1, -1) if out[j]["_h"]), -1)
        next_first = next((out[j]["_h"][0] for j in range(li + 1, len(out)) if out[j]["_h"]), len(heard))
        words = [i for i, o in enumerate(owner) if o == li]
        lead_unmatched = words[0] not in match
        trail_unmatched = words[-1] not in match
        # Unmatched words at a line's edge (a misheard name) may take the heard words up to the neighbour,
        # but ONLY if that neighbour line was itself matched; otherwise those heard words belong to the
        # unmatched neighbour line and are shared out below.
        prev_ok = li == 0 or bool(out[li - 1]["_h"])
        next_ok = li == len(out) - 1 or bool(out[li + 1]["_h"])
        s_idx = prev_last + 1 if lead_unmatched and prev_ok and prev_last + 1 < h[0] else h[0]
        e_idx = next_first - 1 if trail_unmatched and next_ok and next_first - 1 > h[-1] else h[-1]
        r["start"], r["end"] = heard[s_idx]["s"], heard[e_idx]["e"]
    # runs of lines with no matched words: share the gap between their matched neighbours by word count
    li = 0
    while li < len(out):
        if out[li]["start"] is not None:
            li += 1
            continue
        run = li
        while run < len(out) and out[run]["start"] is None:
            run += 1
        gap_start = out[li - 1]["end"] if li > 0 else 0.0
        gap_end = out[run]["start"] if run < len(out) else (heard[-1]["e"] if heard else gap_start)
        counts = [max(1, len(lines[k].text.split())) for k in range(li, run)]
        t = gap_start
        for k, c in zip(range(li, run), counts):
            out[k]["start"] = round(t, 3)
            t += (gap_end - gap_start) * c / sum(counts)
            out[k]["end"] = round(t, 3)
        li = run
    for r in out:
        r.pop("_h")
    return out


@register("align", "time every script line in voice.wav (run with plain python)", lambda p: p.add_argument("job"))
def _cmd_align(args) -> int:
    job = jobs.load_job(args.job)
    d = jobs.job_dir(job.id)
    lines = parse_script((d / "script.md").read_text(encoding="utf-8"))
    heard = transcribe(d / "voice.wav")
    timed = align_lines(lines, heard)
    flagged = [t["index"] for t in timed if t["matched_ratio"] < FLAG_RATIO]
    (d / "timings.json").write_text(json.dumps({"words": heard, "lines": timed, "flagged": flagged}, indent=2), encoding="utf-8")
    jobs.mark(job, "align", "done", f"{len(timed)} lines, {len(flagged)} flagged"); jobs.save_job(job)
    print(f"timed {len(timed)} lines; flagged (check by ear): {flagged or 'none'}")
    return 0

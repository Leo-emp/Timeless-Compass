# MOTION CHECK (`tc motion`): does the animation flow naturally and act on the words? (rules r28-r30, spec 6.8)
# Works on how much the picture changes from one frame to the next (a "difference" per frame, 0..1):
#   - snap:   a sudden jump that is not a planned cut (things popping, teleporting, jerky starts)
#   - freeze: 3 s or more where nothing at all moves (nobody breathing, no water, no camera) -> slideshow feel
#   - beat:   at every word-anchored beat (from the shot plan) something must visibly happen, landing within
#             8 frames before to 4 frames after the beat (actions start a little early so they LAND on the word)
#
#   python -m tc motion film/out/s012.mp4 --cuts 0,96 --beats 30,61,88
import statistics
import subprocess
from pathlib import Path

from tc.cli import register

SNAP_FACTOR, SNAP_MIN = 6.0, 0.08
# ...and sudden against what was happening just before (median of the previous SNAP_PREV frames): an eased
# move of a big figure ramps up and is NOT a snap; a pop, a teleport or a jerky start still is.
SNAP_LOCAL, SNAP_PREV = 2.5, 4
FREEZE_DIFF, FREEZE_S = 0.0015, 3.0
FREEZE_MEAN = 0.0003      # whole-frame change below this = nothing alive at all (measured: day ~0.0008, night ~0.0004, still ~0)
BEAT_BEFORE, BEAT_AFTER, BEAT_FACTOR = 8, 4, 2.0


def _size(video: Path, scale: int) -> tuple[int, int]:
    """Decode size keeping the video's own shape (16:9 long videos, 9:16 Shorts), even numbers."""
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", str(video)], capture_output=True, text=True, check=True).stdout.strip().split(",")
    vw, vh = int(out[0]), int(out[1])
    return scale, max(2, round(scale * vh / vw / 2) * 2)


def frame_diffs(video: Path, scale: int = 192, cols: int = 8, rows: int = 6) -> list[float]:
    """How much the picture changes between consecutive frames, 0..1: the mean difference of the MOST-changed
    tile (8 x 6 grid), so a local action (a face changing, a hand pointing) counts, not just whole-frame motion."""
    import numpy as np
    w, h = _size(video, scale)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-fps_mode", "passthrough", "-vf", f"scale={w}:{h},gblur=sigma=1.5,format=gray",   # blur: film grain must not count as motion
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, dtype=np.uint8)[: (len(raw) // (w * h)) * w * h].reshape(-1, h, w).astype(np.int16)
    if len(frames) < 2:
        return [0.0] * len(frames)
    d = np.abs(np.diff(frames, axis=0)).astype(np.float32) / 255.0
    th, tw = h // rows, w // cols
    tiles = d[:, : th * rows, : tw * cols].reshape(len(d), rows, th, cols, tw).mean(axis=(2, 4))
    return [0.0] + [float(x) for x in tiles.reshape(len(d), -1).max(axis=1)]


def frame_means(video: Path, scale: int = 192) -> list[float]:
    """Whole-frame mean change per frame (for the freeze test), same decoding as frame_diffs."""
    import numpy as np
    w, h = _size(video, scale)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-fps_mode", "passthrough", "-vf", f"scale={w}:{h},gblur=sigma=1.5,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    f = np.frombuffer(raw, dtype=np.uint8)[: (len(raw) // (w * h)) * w * h].reshape(-1, h, w).astype(np.int16)
    return [0.0] + [float(x) for x in (np.abs(np.diff(f, axis=0)).mean(axis=(1, 2)) / 255.0)] if len(f) > 1 else [0.0] * len(f)


def motion_problems(diffs: list[float], fps: int, cuts: list[int] = (), beats: list[int] = (),
                    mean_diffs: list[float] | None = None) -> list[str]:
    """diffs = change of the most-changed tile per frame (snaps, beats); mean_diffs = whole-frame change (freezes):
    one always-moving detail (waves, smoke) must not hide a scene whose action has frozen."""
    probs = []
    if not diffs:
        return ["no frames"]
    med = statistics.median(diffs) or 1e-6
    cut_frames = {c + k for c in cuts for k in (-1, 0, 1)}
    for i, d in enumerate(diffs):
        prev = statistics.median(diffs[max(0, i - SNAP_PREV):i]) if i > 0 else 0.0
        if i > 0 and d > max(SNAP_FACTOR * med, SNAP_MIN) and d > SNAP_LOCAL * max(prev, 1e-6) and i not in cut_frames:
            probs.append(f"snap at frame {i} (change {d:.3f}, typical {med:.4f})")
    run_start = None
    series, limit = (mean_diffs, FREEZE_MEAN) if mean_diffs is not None else (diffs, FREEZE_DIFF)
    for i, d in enumerate(series + [1.0]):                        # sentinel closes a run at the end
        if i > 0 and d < limit and i not in cut_frames:
            run_start = i if run_start is None else run_start
        else:
            if run_start is not None and (i - run_start) >= FREEZE_S * fps:
                probs.append(f"frozen from frame {run_start} to {i - 1}")
            run_start = None
    for b in beats:
        window = diffs[max(0, b - BEAT_BEFORE): b + BEAT_AFTER + 1]
        # a beat shows either as a clear peak OR as steady change adding up over the window (slow eased actions)
        if not window or (max(window) < BEAT_FACTOR * med and sum(window) < 1.4 * med * len(window)):
            probs.append(f"nothing happens on the beat at frame {b}")
    return probs


def _ints(s: str) -> list[int]:
    return [int(x) for x in s.split(",") if x.strip()]


def _args(p):
    p.add_argument("video")
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--cuts", default="", help="frame numbers of planned cuts, e.g. 0,96,180")
    p.add_argument("--beats", default="", help="frame numbers of word-anchored beats")


@register("motion", "motion check: snaps, frozen stretches, nothing happening on a beat", _args)
def _cmd_motion(args) -> int:
    probs = motion_problems(frame_diffs(Path(args.video)), args.fps, _ints(args.cuts), _ints(args.beats),
                            mean_diffs=frame_means(Path(args.video)))
    for p in probs:
        print("problem:", p)
    print("motion:", "OK" if not probs else f"{len(probs)} problem(s)")
    return 1 if probs else 0

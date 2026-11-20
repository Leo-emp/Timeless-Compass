# `tc film` — render a video made by the 2D film engine (film/) in parallel parts on free cloud machines.
#
# How a render works:
#   1. split   the video's frames into contiguous ranges, e.g. 21,600 frames -> 20 parts of 1,080 frames
#   2. start   each range on a GitHub runner (workflow film-render.yml) and/or in a Kaggle notebook
#   3. fetch   the finished parts (GitHub artifacts / Kaggle kernel output) into one folder
#   4. join    the parts losslessly (ffmpeg concat, no re-encode) into one video
#   5. speed   read every part's timing file -> frames per second and wall-clock time
#
#   python -m tc film parts 21600 20
#   python -m tc film render FleetTestLong --frames 21600 --parts 20 --on github [--ref cinematic-agent]
#   python -m tc film fetch <run-id> --on github --to film/out/long
#   python -m tc film join film/out/long film/out/long.mp4
#   python -m tc film speed film/out/long
import json
import re
import subprocess
from pathlib import Path

from tc.cli import register

WORKFLOW = "film-render.yml"
PART_RE = re.compile(r"part-(\d+)-(\d+)\.mp4$")


def split_frames(total: int, parts: int) -> list[tuple[int, int]]:
    """Inclusive frame ranges covering 0..total-1 with no gaps or overlaps; sizes differ by at most 1."""
    if total < 1 or parts < 1:
        raise ValueError(f"need total >= 1 and parts >= 1 (got {total}, {parts})")
    parts = min(parts, total)                       # never more parts than frames
    base, extra = divmod(total, parts)
    out, start = [], 0
    for i in range(parts):
        size = base + (1 if i < extra else 0)       # the first `extra` parts take one frame more
        out.append((start, start + size - 1))
        start += size
    return out


def part_name(start: int, end: int) -> str:
    """File name every renderer uses for a part, so parts sort and join by their frame numbers."""
    return f"part-{start}-{end}.mp4"


def github_dispatch_args(comp: str, ranges: list[tuple[int, int]], ref: str = "main") -> list[str]:
    """The `gh workflow run` command that starts one GitHub runner per range."""
    parts = json.dumps([list(r) for r in ranges], separators=(",", ":"))
    return ["gh", "workflow", "run", WORKFLOW, "--ref", ref, "-f", f"comp={comp}", "-f", f"parts={parts}"]


def _start_frame(p: Path) -> int:
    m = PART_RE.search(p.name)
    if not m:
        raise ValueError(f"not a part file: {p.name}")
    return int(m.group(1))


def concat_list(parts: list[Path]) -> str:
    """ffmpeg concat-demuxer list, ordered by each part's first frame (not by file name text)."""
    return "".join(f"file '{p.resolve().as_posix()}'\n" for p in sorted(parts, key=_start_frame))


def find_parts(parts_dir: Path) -> list[Path]:
    """Every part-<a>-<b>.mp4 under a folder (GitHub artifacts land in one sub-folder each)."""
    return [p for p in parts_dir.rglob("part-*.mp4") if PART_RE.search(p.name)]


def check_contiguous(parts: list[Path]) -> list[str]:
    """Problems if the parts leave a gap or overlap (a missing part would make a jump in the video)."""
    spans = sorted((int(m.group(1)), int(m.group(2))) for m in (PART_RE.search(p.name) for p in parts))
    probs = []
    if spans and spans[0][0] != 0:
        probs.append(f"first part starts at frame {spans[0][0]}, not 0")
    for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
        if b0 != a1 + 1:
            probs.append(f"gap or overlap between frames {a1} and {b0}")
    return probs


def join_parts(parts_dir: Path, out: Path, runner=subprocess.run) -> Path:
    """Join every part losslessly (stream copy) into `out`. Refuses if a part is missing."""
    parts = find_parts(parts_dir)
    if not parts:
        raise ValueError(f"no part files in {parts_dir}")
    probs = check_contiguous(parts)
    if probs:
        raise ValueError("; ".join(probs))
    lst = parts_dir / "concat.txt"
    lst.write_text(concat_list(parts), encoding="utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    runner(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)], check=True)
    return out


def speed_report(timings: list[dict]) -> dict:
    """Sum of render seconds, wall-clock (first start -> last end) and frames per wall-clock second."""
    frames = sum(t["to"] - t["from"] + 1 for t in timings)
    wall = max(t["ended"] for t in timings) - min(t["started"] for t in timings)
    return {"frames": frames, "render_s_sum": sum(t["seconds"] for t in timings), "wall_s": wall,
            "frames_per_s": frames / wall if wall else 0.0}


def read_timings(parts_dir: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in parts_dir.rglob("timing-*.json")]


# ---------------- commands ----------------
def _args(p):
    sub = p.add_subparsers(dest="action", required=True)
    a = sub.add_parser("parts", help="print the frame ranges for a video")
    a.add_argument("frames", type=int); a.add_argument("n", type=int)
    a = sub.add_parser("render", help="start a render on GitHub or Kaggle")
    a.add_argument("comp"); a.add_argument("--frames", type=int, required=True); a.add_argument("--parts", type=int, default=20)
    a.add_argument("--on", choices=["github", "kaggle"], default="github"); a.add_argument("--ref", default="main")
    a.add_argument("--only", default="", help="render only these part indexes, e.g. 20-23 (for split farms)")
    a = sub.add_parser("fetch", help="download finished parts")
    a.add_argument("id", help="GitHub run id or Kaggle kernel slug"); a.add_argument("--on", choices=["github", "kaggle"], default="github")
    a.add_argument("--to", required=True)
    a = sub.add_parser("join", help="join parts into one video"); a.add_argument("dir"); a.add_argument("out")
    a = sub.add_parser("speed", help="render speed from the parts' timing files"); a.add_argument("dir")


def _pick(ranges: list[tuple[int, int]], only: str) -> list[tuple[int, int]]:
    if not only:
        return ranges
    lo, _, hi = only.partition("-")
    return ranges[int(lo): int(hi or lo) + 1]


@register("film", "2D film engine renders: parts / render / fetch / join / speed", _args)
def _cmd_film(args) -> int:
    if args.action == "parts":
        print(json.dumps(split_frames(args.frames, args.n)))
        return 0
    if args.action == "render":
        ranges = _pick(split_frames(args.frames, args.parts), args.only)
        if args.on == "github":
            subprocess.run(github_dispatch_args(args.comp, ranges, args.ref), check=True)
            print(f"started {len(ranges)} GitHub parts; find the run: gh run list --workflow {WORKFLOW} -L 1")
        else:
            from tc import film_kaggle
            slug = film_kaggle.push_film_kernel(args.comp, ranges, args.ref)
            print(f"pushed Kaggle kernel {slug}; status: kaggle kernels status {slug}")
        return 0
    if args.action == "fetch":
        to = Path(args.to); to.mkdir(parents=True, exist_ok=True)
        if args.on == "github":
            subprocess.run(["gh", "run", "download", args.id, "-D", str(to)], check=True)
        else:
            subprocess.run(["kaggle", "kernels", "output", args.id, "-p", str(to)], check=True)
        print(f"{len(find_parts(to))} parts in {to}")
        return 0
    if args.action == "join":
        print(join_parts(Path(args.dir), Path(args.out)))
        return 0
    if args.action == "speed":
        print(json.dumps(speed_report(read_timings(Path(args.dir))), indent=2))
        return 0
    return 1

# Music cues: music ONLY at chosen moments (owner rule r11), chosen by MEANING, never wall-to-wall.
#
# 1) The catalogue  library/music/tracks.json  - every track is tagged:
#      moods      tension, menace, mystery, grief, triumph, awe, hope, dread
#      intensity  1 (quiet) .. 5 (full battle)
#      era        ancient (lyre / aulos / frame drum / choir) | epic (orchestral) | modern (dark strings, synth pulse)
#      shape      slow_build | steady | hit | fade_out
#      length_s, tempo_bpm, peak_s (where its biggest moment is, if it has one), licence, source, file, credit
#    Sources: YouTube Audio Library, Pixabay Music (free commercial), FMA CC0 / CC-BY. Same licence gate as sfx.
#    Files: library/music/files/ (git-ignored). Add one:  tc music add <file> --moods dread,mystery --intensity 2 ...
#
# 2) The shot list (shots.json, written by Claude) gets a "music" entry ONLY where r11 allows:
#      {"id": "s12", ..., "music": {"cue": "climax", "mood": "tension", "from": "s12", "to": "s15", "peak": "s14"}}
#    cue = hook | tension | battle | climax | emotional | ending   (the script's structure gives the beats)
#    Everything else runs on ambience + sound effects (tc sfx).
#
# 3) The picker: best tag match (mood > era > intensity > shape), starts on a cut, puts the track's peak on the
#    climax shot, fades out on a story beat, ducks under narration (the mix does the ducking), never the same track
#    in two consecutive videos (library/music/used.json) and never twice in one video.
#
# 4) Learning: when YouTube retention drops faster during a cue than in the rest of the video, a rule is SUGGESTED
#    (the owner confirms it with  tc learn ...).
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from tc import jobs, paths
from tc.cli import register
from tc.mix import measure_lufs
from tc.sfx import licence_verdict

MOODS = {"tension", "menace", "mystery", "grief", "triumph", "awe", "hope", "dread"}
ERAS = {"ancient", "epic", "modern"}
SHAPES = {"slow_build", "steady", "hit", "fade_out"}
CUE_KINDS = {"hook", "tension", "battle", "climax", "emotional", "ending"}            # rule r11
# moods that can stand in for each other when nothing matches exactly
NEAR = {"tension": {"dread", "menace"}, "dread": {"tension", "mystery", "menace"}, "menace": {"dread", "tension"},
        "mystery": {"dread", "awe"}, "grief": {"hope"}, "hope": {"awe", "grief"}, "awe": {"triumph", "hope", "mystery"},
        "triumph": {"awe", "hope"}}
# what each kind of moment wants: (intensity, shapes that fit)
CUE_WANTS = {"hook": (3, {"hit", "slow_build"}), "tension": (3, {"slow_build", "steady"}), "battle": (5, {"steady", "hit"}),
             "climax": (5, {"slow_build", "hit"}), "emotional": (2, {"steady", "fade_out"}), "ending": (3, {"fade_out", "slow_build"})}
MAX_SHARE = {"long": 0.40, "short": 0.70}      # at most this much of a video has music
MIN_GAP_S = {"long": 10.0, "short": 3.0}       # music-free stretch between two cues
FADE_IN_S, FADE_OUT_S = 1.0, 2.5


def _lib(root=None) -> Path:
    return Path(root or paths.LIBRARY / "music")


def load_tracks(root=None) -> dict:
    f = _lib(root) / "tracks.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"tracks": []}


# ================= catalogue =================
def check_track(t: dict) -> list[str]:
    p = []
    for key in ("id", "file", "source", "licence", "length_s"):
        if not t.get(key):
            p.append(f"{t.get('id', '?')}: {key} missing")
    if not t.get("moods") or not set(t["moods"]) <= MOODS:
        p.append(f"{t.get('id')}: moods must be from {sorted(MOODS)}")
    if not isinstance(t.get("intensity"), int) or not 1 <= t["intensity"] <= 5:
        p.append(f"{t.get('id')}: intensity must be 1-5")
    if not t.get("era") or not set(t["era"]) <= ERAS:
        p.append(f"{t.get('id')}: era must be from {sorted(ERAS)}")
    if t.get("shape") not in SHAPES:
        p.append(f"{t.get('id')}: shape must be one of {sorted(SHAPES)}")
    v = licence_verdict(t.get("licence", ""))
    if not v["ok"]:
        p.append(f"{t.get('id')}: licence {t.get('licence')!r} not allowed ({v['name']})")
    elif v["credit"] and not t.get("credit"):
        p.append(f"{t.get('id')}: CC-BY track needs a credit line")
    return p


def era_group(era: str) -> str:
    """Shot era ('greece_480bc', 'usa_1950s') -> music era group."""
    e = (era or "").lower()
    if any(x in e for x in ("19", "20", "modern", "cold_war", "ussr", "usa")):
        return "modern"
    return "ancient"


# ================= rule r11: where music may play =================
def _span(c: dict, by_id: dict) -> tuple[float, float]:
    a, b = by_id[c["from"]], by_id[c["to"]]
    return float(a["at"]), float(b["at"]) + float(b["dur"])


def check_cues(cues: dict, shots: list[dict], kind: str) -> list[str]:
    """cues = {shot id: music entry}. Returns problems (empty = OK)."""
    p, by_id = [], {s["id"]: s for s in shots}
    spans = []
    for sid, c in cues.items():
        if c.get("cue") not in CUE_KINDS:
            p.append(f"{sid}: music cue {c.get('cue')!r} - rule r11 allows music only at {sorted(CUE_KINDS)}")
        if c.get("mood") not in MOODS:
            p.append(f"{sid}: mood {c.get('mood')!r} not in {sorted(MOODS)}")
        if c.get("from") not in by_id or c.get("to") not in by_id:
            p.append(f"{sid}: from/to must be shot ids")
            continue
        a, b = _span(c, by_id)
        if b <= a:
            p.append(f"{sid}: music ends before it starts")
            continue
        if c.get("peak") and c["peak"] not in by_id:
            p.append(f"{sid}: peak {c['peak']!r} is not a shot id")
        elif c.get("peak") and not a <= float(by_id[c["peak"]]["at"]) < b:
            p.append(f"{sid}: peak shot {c['peak']} must be inside the cue ({c['from']}..{c['to']})")
        spans.append((a, b, sid))
    spans.sort()
    for (a1, b1, s1), (a2, b2, s2) in zip(spans, spans[1:]):
        if a2 < b1 - 1e-6:
            p.append(f"{s1}/{s2}: music cues overlap")
        elif a2 - b1 < MIN_GAP_S[kind]:
            p.append(f"{s1}/{s2}: only {a2 - b1:.1f} s between cues; leave at least {MIN_GAP_S[kind]:.0f} s music-free (r11)")
    total = max((float(s["at"]) + float(s["dur"]) for s in shots), default=0.0)
    music_s = sum(b - a for a, b, _ in spans)
    if total and music_s / total > MAX_SHARE[kind]:
        p.append(f"music plays {music_s / total:.0%} of the video - that is wall-to-wall; max {MAX_SHARE[kind]:.0%} (r11)")
    return p


# ================= picker =================
def score(c: dict, era: str, t: dict) -> float:
    s = 0.0
    moods = set(t.get("moods", []))
    s += 10 if c.get("mood") in moods else (4 if moods & NEAR.get(c.get("mood"), set()) else -10)
    eras = set(t.get("era", []))
    s += 5 if era in eras else (3 if era == "ancient" and "epic" in eras else -8)
    want_int, want_shapes = CUE_WANTS.get(c.get("cue"), (3, set()))
    s -= 2 * abs(t.get("intensity", 3) - want_int)
    s += 3 if t.get("shape") in want_shapes else 0
    return s


def choose(c: dict, era: str, tracks: dict, banned: set | None = None, need_s: float = 0.0) -> dict | None:
    banned = banned or set()
    pool = [t for t in tracks.get("tracks", []) if t["id"] not in banned and not check_track(t)
            and t.get("length_s", 0) >= need_s]
    if not pool:
        return None
    return max(pool, key=lambda t: (score(c, era, t), t["id"]))


def place(c: dict, t: dict, shots: list[dict]) -> dict:
    """Where the chosen track plays: from the cut that starts the cue to the end of its last shot.
    seek = how far into the track we start, chosen so the track's peak lands on the cue's peak shot."""
    by_id = {s["id"]: s for s in shots}
    a, b = _span(c, by_id)
    seek = 0.0
    if c.get("peak") and t.get("peak_s") is not None:
        peak_t = float(by_id[c["peak"]]["at"])
        seek = max(0.0, float(t["peak_s"]) - (peak_t - a))
    seek = min(seek, max(0.0, float(t["length_s"]) - (b - a)))     # never run past the track's end
    fade_in = 0.3 if c.get("cue") in ("hook", "battle") else FADE_IN_S     # hits arrive fast, builds creep in
    return {"cue": c["cue"], "mood": c["mood"], "track": t["id"], "file": t["file"], "at": round(a, 3),
            "dur": round(b - a, 3), "seek": round(seek, 3), "fade_in": fade_in, "fade_out": min(FADE_OUT_S, (b - a) / 3),
            "duck": True, "db": -6.0}


def pick_all(cues: dict, shots: list[dict], tracks: dict, banned: set) -> tuple[list[dict], list[str]]:
    by_id = {s["id"]: s for s in shots}
    placed, problems, used = [], [], set(banned)
    for sid, c in sorted(cues.items(), key=lambda kv: by_id[kv[1]["from"]]["at"]):
        a, b = _span(c, by_id)
        era = c.get("era") or era_group(by_id[c["from"]].get("era", ""))
        t = choose(c, era, tracks, used, need_s=b - a)
        if t is None:
            problems.append(f"{sid}: no track fits ({c['cue']}, {c['mood']}, {era}, {b - a:.0f} s) - add tracks to library/music")
            continue
        used.add(t["id"])
        placed.append(place(c, t, shots))
    return placed, problems


# ================= used.json: never the same track in two consecutive videos =================
def _load_used(f: Path) -> dict:
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"videos": []}


def record_used(job_id: str, track_ids: list[str], f: Path | None = None) -> None:
    f = Path(f or _lib() / "used.json")
    data = _load_used(f)
    for v in data["videos"]:
        if v["job"] == job_id:
            v["tracks"], v["date"] = list(track_ids), datetime.now().isoformat(timespec="seconds")
            break
    else:
        data["videos"].append({"job": job_id, "date": datetime.now().isoformat(timespec="seconds"), "tracks": list(track_ids)})
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, indent=2), encoding="utf-8")


def banned_for(job_id: str, f: Path | None = None) -> set:
    """Tracks used by the video made just before this one."""
    vids = _load_used(Path(f or _lib() / "used.json"))["videos"]
    ids = [v["job"] for v in vids]
    before = vids[ids.index(job_id) - 1] if job_id in ids and ids.index(job_id) > 0 else (vids[-1] if vids and job_id not in ids else None)
    return set(before["tracks"]) if before else set()


# ================= learning from retention =================
def retention_lessons(placed: list[dict], retention: list[list[float]], ratio: float = 1.8) -> list[str]:
    """retention = [[seconds, % still watching], ...] from YouTube Analytics (WS14).
    A cue where viewers leave `ratio` times faster than the video's average gets a suggested rule."""
    pts = sorted(retention)
    if len(pts) < 2:
        return []
    def pct(t):
        for (t1, p1), (t2, p2) in zip(pts, pts[1:]):
            if t1 <= t <= t2:
                return p1 + (p2 - p1) * (t - t1) / (t2 - t1 or 1)
        return pts[-1][1] if t > pts[-1][0] else pts[0][1]
    avg = (pts[0][1] - pts[-1][1]) / (pts[-1][0] - pts[0][0])          # % lost per second, whole video
    tips = []
    for m in placed:
        a, b = m["at"], m["at"] + m["dur"]
        rate = (pct(a) - pct(b)) / (b - a) if b > a else 0
        if avg > 0 and rate > ratio * avg:
            tips.append(f"{m['track']} ({m['cue']}, {m.get('mood', '?')}) at {a:.0f}-{b:.0f} s lost viewers {rate / avg:.1f}x "
                        f"faster than average. Suggested: tc learn \"Avoid {m['track']}-style music for {m['cue']} cues\" "
                        f"--why \"retention dip during music\" --stage edit")
    return tips


# ================= commands =================
def _cues_from_job(d: Path) -> tuple[dict, list[dict]]:
    authored = json.loads((d / "shots.json").read_text(encoding="utf-8"))["shots"]
    timed = json.loads((d / "shots.timed.json").read_text(encoding="utf-8"))["shots"]
    return {s["id"]: s["music"] for s in authored if s.get("music")}, timed


def _args(p):
    sub = p.add_subparsers(dest="action", required=True)
    a = sub.add_parser("add", help="add a tagged track to library/music")
    a.add_argument("file"); a.add_argument("--id", required=True); a.add_argument("--moods", required=True)
    a.add_argument("--intensity", type=int, required=True); a.add_argument("--era", required=True)
    a.add_argument("--shape", required=True); a.add_argument("--tempo", type=int, default=0)
    a.add_argument("--peak", type=float); a.add_argument("--source", required=True); a.add_argument("--licence", required=True)
    a.add_argument("--credit", default=""); a.add_argument("--url", default="")
    pk = sub.add_parser("pick", help="check the job's music cues (r11) and choose tracks -> jobs/<id>/music.json")
    pk.add_argument("job")
    ln = sub.add_parser("learn", help="compare YouTube retention with the music cues and suggest rules")
    ln.add_argument("job"); ln.add_argument("--retention", required=True, help="json: [[seconds, percent], ...]")


@register("music", "music cues: add tracks / pick by meaning (rule r11) / learn from retention", _args)
def _cmd_music(args) -> int:
    if args.action == "add":
        lib = _lib()
        (lib / "files").mkdir(parents=True, exist_ok=True)
        dest = lib / "files" / f"{args.id}{Path(args.file).suffix.lower()}"
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", args.file],
                           capture_output=True, text=True, check=True)
        t = {"id": args.id, "file": dest.name, "moods": args.moods.split(","), "intensity": args.intensity,
             "era": args.era.split(","), "shape": args.shape, "length_s": round(float(r.stdout.strip()), 2),
             "tempo_bpm": args.tempo, "source": args.source, "licence": args.licence, "credit": args.credit, "url": args.url}
        if args.peak is not None:
            t["peak_s"] = args.peak
        problems = check_track(t)
        if problems:
            print("\n".join("- " + x for x in problems))
            return 1
        shutil.copyfile(args.file, dest)
        t["lufs"] = measure_lufs(dest)            # the mix levels every track to the voice from this
        cat = load_tracks()
        cat["tracks"] = [x for x in cat["tracks"] if x["id"] != t["id"]] + [t]
        (lib / "tracks.json").write_text(json.dumps(cat, indent=2), encoding="utf-8")
        print(f"added {t['id']} ({t['length_s']} s)")
        return 0
    job = jobs.load_job(args.job)
    d = jobs.job_dir(job.id)
    if not (d / "shots.timed.json").exists():
        print("No shots.timed.json yet: run  tc shots <id>  first")
        return 2
    cues, shots = _cues_from_job(d)
    if args.action == "learn":
        placed = json.loads((d / "music.json").read_text(encoding="utf-8"))["cues"]
        tips = retention_lessons(placed, json.loads(Path(args.retention).read_text(encoding="utf-8")))
        print("\n".join(tips) if tips else "no music cue lost viewers faster than the rest of the video")
        return 0
    problems = check_cues(cues, shots, job.kind)
    placed, more = pick_all(cues, shots, load_tracks(), banned_for(job.id)) if not problems else ([], [])
    problems += more
    for x in problems:
        print("-", x)
    (d / "music.json").write_text(json.dumps({"cues": placed, "problems": problems}, indent=2), encoding="utf-8")
    if not problems:
        record_used(job.id, [m["track"] for m in placed])
    print(f"{len(placed)} music cues placed ({sum(m['dur'] for m in placed):.0f} s of music); {len(problems)} problems")
    return 1 if problems else 0

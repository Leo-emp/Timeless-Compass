# SLOW MOTION like the movies: chosen moments (the arrow volley, the charge hitting the line, a hero's death, a cannon
# firing) play at 1/4 - 1/2 speed. Done in Blender with REAL in-between frames (render.frame_map_old/new), not by
# stretching video, so motion stays smooth and motion blur stays correct. The effect is rationed: at most a few per
# video and never in two neighbouring shots, otherwise it stops feeling special.
DRAMATIC = [  # (words in the shot's action, speed) - strongest first
    (("dies", "is killed", "falls dead", "death"), 0.25),
    (("volley", "arrows", "rain of"), 0.3),
    (("charge hits", "crashes into", "rams", "impact", "clash"), 0.3),
    (("cannon fires", "fires", "explodes", "explosion", "blast"), 0.35),
    (("strikes", "slashes", "the blow"), 0.4),
    (("leaps", "jumps", "throws"), 0.5),
]
NEVER = ("talks", "says", "speaks", "walks", "listens", "sits", "waits")


def frame_map(speed: float) -> dict:
    """Blender frame remap for a playback speed (0.25 = four times slower)."""
    speed = min(1.0, max(0.1, speed))
    return {"old": 100, "new": int(round(100 / speed))}


def render_frames(frames: int, speed: float) -> int:
    m = frame_map(speed)
    return int(round(frames * m["new"] / m["old"]))


def _score(action: str):
    a = (action or "").lower()
    if any(w in a for w in NEVER):
        return None
    for rank, (words, speed) in enumerate(DRAMATIC):
        if any(w in a for w in words):
            return rank, speed
    return None


def pick_moments(shots: list, max_n: int = 3) -> list:
    """The shots that get slow motion: the most dramatic first, at most `max_n`, never two neighbours."""
    cands = []
    for i, s in enumerate(shots):
        sc = _score(s.get("action", ""))
        if sc is not None:
            cands.append((sc[0], i, sc[1]))
    picked = {}
    for rank, i, speed in sorted(cands):
        if len(picked) >= max_n:
            break
        if any(abs(i - j) <= 1 for j in picked):
            continue
        picked[i] = speed
    return [dict(shots[i], speed=picked[i]) for i in sorted(picked)]

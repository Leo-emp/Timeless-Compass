# The script: a film-structure narration written by Claude into jobs/<id>/script.md, checked here.
#
# Format (one narration line per text line):
#   ## cold_open
#   At dawn, the King of Persia sat on a golden throne. [src: herodotus-8.90] {loop}
#   ## title
#   ## world
#   ...
#   [src: id]  cites an entry in jobs/<id>/sources.json   (every factual line must have one)
#   {loop}     an open loop / re-hook (a question or cliffhanger that keeps people watching)
#   {beat}     a held silence before or after a line
#
# Character dialogue (owner rules r1 + r12, 2026-11-19) - no fixed limit: wherever a line fits and boosts the vibe:
#   XERXES: "Burn their city. Let them watch it from their ships."  [dramatised]
#   LEONIDAS: "Come and take them."  [source: Plutarch, Sayings of Spartans 225c]
#   SICINNUS (messenger): "The Greeks will run tonight."  [dramatised]     <- (voice key) picks a Fish voice
#   [dramatised]       an IMAGINED line: allowed, needs no source, but it must fit the real history
#                      (right person, real situation, his known character, nothing that changes what happened)
#   [source: ...]      a REAL quote: free text naming where it comes from (author, work, passage)
#   [src: id]          also accepted as the source of a real quote (an id from sources.json / the fact sheet)
# A plain line (no NAME: "...") is the narrator, and narrator facts still need [src: id] as before.
# The speaker NAME is UPPER CASE, so narration that quotes someone ('He said: "no".') stays narration.
import hashlib
import json
import re
from pathlib import Path
from dataclasses import dataclass

from tc import jobs
from tc.cli import register
from tc.config import Config, get_config

LONG_SECTIONS = ["cold_open", "title", "world", "tension", "turning_point", "climax", "aftermath", "outro"]
SHORT_SECTIONS = ["hook", "build", "payoff"]
FACTUAL = {"world", "tension", "turning_point", "climax", "aftermath", "build", "payoff"}
MAX_LINE_WORDS = 30
_SRC = re.compile(r"\[src:\s*([^\]]+)\]")
_QUOTE_SRC = re.compile(r"\[source:\s*([^\]]*)\]")     # [source: free text] = where a real quote comes from
_DRAMATISED = re.compile(r"\[dramati[sz]ed\]", re.I)    # British or American spelling both work
# NAME: "words"  or  NAME (voice_key): "words"   (straight or curly quotes). Same shape tc/dialogue.py reads.
_CHARACTER = re.compile(r'^([A-Z][A-Z0-9_ \'-]{0,40}?)\s*(?:\(([a-z0-9_]+)\))?\s*:\s*["“](.+?)["”]\s*$')


@dataclass
class Line:
    section: str
    index: int            # position in the whole script (0, 1, 2, ...)
    text: str             # narration only, markers removed
    sources: list[str]
    loop: bool
    beat: bool
    # ---- dialogue (all empty for narrator lines; defaults keep older code that builds Line(...) working) ----
    speaker: str | None = None        # "XERXES" when a character speaks, None for the narrator
    voice_key: str | None = None      # the (voice) written after the name, if any
    spoken: str = ""                  # only the words heard (no NAME:, no quotes); for the narrator = text
    dramatised: bool = False          # tagged [dramatised]: imagined line (rule r12)
    quote_source: str | None = None   # text of [source: ...] for a real quote

    @property
    def is_character(self) -> bool:
        """True when a character (not the narrator) speaks this line. Voice uses it to pick a Fish voice,
        shots use it to plan a close-up of the speaker."""
        return self.speaker is not None


def parse_script(text: str) -> list[Line]:
    lines, section = [], None
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("## "):
            section = s[3:].strip()
            continue
        srcs = [x.strip() for m in _SRC.findall(s) for x in m.split(",") if x.strip()]
        loop, beat = "{loop}" in s, "{beat}" in s
        dramatised = bool(_DRAMATISED.search(s))
        q = _QUOTE_SRC.search(s)
        quote_source = q.group(1).strip() if q else None
        # remove every marker; what is left is what gets spoken (plus NAME: for a character line)
        clean = _SRC.sub("", s).replace("{loop}", "").replace("{beat}", "")
        clean = _DRAMATISED.sub("", _QUOTE_SRC.sub("", clean))
        clean = re.sub(r"\s+", " ", clean).strip()
        line = Line(section or "", len(lines), clean, srcs, loop, beat,
                    spoken=clean, dramatised=dramatised, quote_source=quote_source)
        m = _CHARACTER.match(clean)
        if m:                                   # a character speaks: split off the name and the quotes
            line.speaker, line.voice_key, line.spoken = m.group(1).strip(), m.group(2), m.group(3).strip()
        lines.append(line)
    return lines


def has_dramatised(lines: list[Line]) -> bool:
    """Does any character line say something imagined? (packaging then adds a line to the description)"""
    return any(l.is_character and l.dramatised for l in lines)


def speakers(lines: list[Line]) -> dict[int, tuple[str, str | None]]:
    """line index -> (SPEAKER, voice key or None), for the voice stage (which Fish voice) and the
    shot stage (whose face gets the close-up while the line is heard)."""
    return {l.index: (l.speaker, l.voice_key) for l in lines if l.is_character}


def sections_in(text: str) -> list[str]:
    return [l.strip()[3:].strip() for l in text.splitlines() if l.strip().startswith("## ")]


def check_script(lines: list[Line], kind: str, sources: dict, cfg: Config, section_order: list[str] | None = None) -> list[str]:
    problems: list[str] = []
    want = LONG_SECTIONS if kind == "long" else SHORT_SECTIONS
    seen = section_order if section_order is not None else list(dict.fromkeys(l.section for l in lines))
    # the title section may be empty, so it may be missing from `seen` when built from lines
    if [s for s in seen if s != "title"] != [s for s in want if s != "title"]:
        problems.append(f"section order must be {want}, got {seen}")
    if any(l.section == "" for l in lines):
        problems.append("narration found before the first ## section header")
    filled = {l.section for l in lines}
    for s in want:
        if s != "title" and s in seen and s not in filled:
            problems.append(f"section {s} is empty (every section except title needs narration)")
    words = sum(len(l.spoken.split()) for l in lines)       # only words that are heard count
    lo, hi = cfg.long_words if kind == "long" else cfg.short_words
    if not lo <= words <= hi:
        problems.append(f"{words} words; a {kind} script needs {lo}-{hi}")
    # re-hook spacing: long every 90 s (225 words), Shorts every 30 s (75 words); the opening hook itself is skipped
    limit = (cfg.rehook_max_s if kind == "long" else cfg.short_rehook_max_s) * cfg.words_per_min // 60
    opening = "cold_open" if kind == "long" else "hook"
    gap = 0
    for l in lines:
        if l.section == opening:
            continue
        gap += len(l.spoken.split())
        if l.loop:
            gap = 0
        elif gap > limit:
            problems.append(f"line {l.index}: over {limit} words without a {{loop}} re-hook")
            gap = 0
    # no fixed number of character lines (owner 2026-11-19): they go wherever they fit and boost the vibe (r1)
    for l in lines:
        if l.is_character:
            # a character line is EITHER imagined ([dramatised]) OR a real quote ([source: ...] / [src: id])
            real = l.quote_source is not None or bool(l.sources)
            if l.dramatised and real:
                problems.append(f"line {l.index}: {l.speaker} is tagged both [dramatised] and sourced; pick one")
            elif not l.dramatised and not real:
                problems.append(f"line {l.index}: {l.speaker} speaks; tag it [dramatised] or [source: ...] (rule r12)")
            elif l.quote_source is not None and not l.quote_source:
                problems.append(f"line {l.index}: empty [source: ]; name the author + work")
        elif l.section in FACTUAL and not l.sources:
            # narrator facts stay strictly sourced
            problems.append(f"line {l.index}: no source in a factual section ({l.section})")
        for s in l.sources:
            if s not in sources:
                problems.append(f"line {l.index}: unknown source {s!r}")
        if len(l.spoken.split()) > MAX_LINE_WORDS:
            problems.append(f"line {l.index}: {len(l.spoken.split())} words, too long for the ear (max {MAX_LINE_WORDS})")
    return problems


def _script_hash(job_dir: Path) -> str:
    return hashlib.sha256((job_dir / "script.md").read_bytes()).hexdigest()


def approve(job_dir: Path) -> None:
    """Record the owner's approval OF THIS EXACT TEXT (any later edit voids it)."""
    (job_dir / "script.approved").write_text(_script_hash(job_dir) + "\n", encoding="utf-8")


def is_approved(job_dir: Path) -> bool:
    f = job_dir / "script.approved"
    return f.exists() and f.read_text(encoding="utf-8").strip() == _script_hash(job_dir)


def _args(p):
    p.add_argument("job")
    p.add_argument("--approve", action="store_true", help="record the owner's approval (needed before voice)")


@register("script", "check jobs/<id>/script.md (and record owner approval)", _args)
def _cmd_script(args) -> int:
    job = jobs.load_job(args.job)
    d = jobs.job_dir(job.id)
    text = (d / "script.md").read_text(encoding="utf-8")
    sources = json.loads((d / "sources.json").read_text(encoding="utf-8")) if (d / "sources.json").exists() else {}
    lines = parse_script(text)
    problems = check_script(lines, job.kind, sources, get_config(), sections_in(text))
    for p in problems:
        print("-", p)
    if problems:
        jobs.mark(job, "script", "failed", f"{len(problems)} problems"); jobs.save_job(job)
        return 1
    words = sum(len(l.spoken.split()) for l in lines)
    was_approved = is_approved(d)
    if args.approve:
        approve(d)
    approved = is_approved(d)
    # an unchanged, already-approved script keeps the later stages; anything else resets them
    jobs.mark(job, "script", "done", f"{words} words, {'approved' if approved else 'awaiting owner approval'}",
              changed=not (was_approved and approved)); jobs.save_job(job)
    print(f"script OK: {len(lines)} lines, {words} words, ~{words / 150:.1f} min. "
          + ("Owner approved." if approved else "Ask the owner to approve, then: tc script <id> --approve"))
    return 0

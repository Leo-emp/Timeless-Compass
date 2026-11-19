# Packaging = title + thumbnail, decided BEFORE the script (growth engine, spec 6.0).
# Claude writes 10+ title options and 3 thumbnail concepts; this file checks the titles against
# simple click-through rules and records the owner's pick. The script must then deliver the title's promise.
# After the script exists, `tc description <id>` writes the YouTube description. If any character line is
# tagged [dramatised] (rule r12), the description ends with the honest note "Some dialogue is dramatised."
import json
from pathlib import Path

from tc import jobs
from tc.cli import register

MAX_LEN = 60
BANNED = ["shocking", "you won't believe", "insane", "gone wrong", "!!!"]      # cheap clickbait hurts trust + retention
DRAMATISED_NOTE = "Some dialogue is dramatised."   # rule r12: one line, exactly this text
HOOK_WORDS = ["secret", "never", "only", "why", "how", "last", "lie", "trap", "hidden", "forgotten"]


def check_titles(titles: list[str], max_len: int = MAX_LEN) -> list[dict]:
    out = []
    for t in titles:
        t = t.strip()
        low = t.lower()
        problems = []
        if len(t) > max_len:
            problems.append("too long")
        letters = [c for c in t if c.isalpha()]
        if letters and sum(c.isupper() for c in letters) / len(letters) > 0.5:
            problems.append("all caps")
        problems += [f"banned word: {w}" for w in BANNED if w in low]
        words = set(low.replace("?", " ").replace(",", " ").split())
        if not (any(c.isdigit() for c in t) or "?" in t or words & set(HOOK_WORDS)):
            problems.append("no curiosity hook")
        out.append({"title": t, "ok": not problems, "problems": problems, "length": len(t)})
    return out


def save_packaging(job: jobs.Job, titles: list[str], thumbnails: list[str], pick: int | None):
    checked = check_titles(titles)
    if pick is not None:
        if not 1 <= pick <= len(checked):
            raise ValueError(f"pick must be 1..{len(checked)}")
        if not checked[pick - 1]["ok"]:
            raise ValueError(f"title {pick} fails the checks: {checked[pick - 1]['problems']}")
    path = jobs.job_dir(job.id) / "packaging.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"titles": checked, "thumbnail_concepts": thumbnails, "picked": pick}, indent=2), encoding="utf-8")
    if pick is not None:
        jobs.mark(job, "packaging", "done", checked[pick - 1]["title"])
        jobs.save_job(job)
    return path


def build_description(base: str, script_text: str) -> str:
    """The description text: the owner's/Claude's base text, plus the r12 note when the script has an
    imagined ([dramatised]) character line. Never adds the note twice."""
    from tc.script import has_dramatised, parse_script      # imported here: tc.script is a heavier module
    text = base.strip()
    if has_dramatised(parse_script(script_text)) and DRAMATISED_NOTE not in text:
        text = f"{text}\n\n{DRAMATISED_NOTE}" if text else DRAMATISED_NOTE
    return text


def write_description(job: jobs.Job, base: str) -> Path:
    """Write jobs/<id>/description.txt from the base text + the job's script.md."""
    d = jobs.job_dir(job.id)
    out = d / "description.txt"
    out.write_text(build_description(base, (d / "script.md").read_text(encoding="utf-8")) + "\n", encoding="utf-8")
    return out


def _desc_args(p):
    p.add_argument("job")
    p.add_argument("--text", help="text file with the base description (default: the picked title)")


@register("description", "write the YouTube description (adds the r12 dramatised-dialogue note)", _desc_args)
def _cmd_description(args) -> int:
    job = jobs.load_job(args.job)
    d = jobs.job_dir(job.id)
    if not (d / "script.md").exists():
        print("no script.md yet - write and check the script first")
        return 2
    if args.text:
        base = Path(args.text).read_text(encoding="utf-8")
    else:                                    # fall back to the picked title, or the seed topic
        pk = d / "packaging.json"
        data = json.loads(pk.read_text(encoding="utf-8")) if pk.exists() else {}
        pick = data.get("picked")
        base = data["titles"][pick - 1]["title"] if pick else job.title
    out = write_description(job, base)
    print(out.read_text(encoding="utf-8"))
    return 0


def _args(p):
    p.add_argument("job")
    p.add_argument("--titles", required=True, help="text file, one title per line")
    p.add_argument("--thumbs", required=True, help="text file, one thumbnail concept per line")
    p.add_argument("--pick", type=int, help="owner's chosen title number (1-based)")


@register("packaging", "check titles + record the owner's title/thumbnail pick", _args)
def _cmd_packaging(args) -> int:
    job = jobs.load_job(args.job)
    read = lambda f: [l for l in open(f, encoding="utf-8").read().splitlines() if l.strip()]
    titles, thumbs = read(args.titles), read(args.thumbs)
    try:
        save_packaging(job, titles, thumbs, args.pick)
    except ValueError as e:
        print(e)
        return 2
    for i, r in enumerate(check_titles(titles), 1):
        print(f"{i:>2}. {'OK ' if r['ok'] else 'BAD'} ({r['length']:>2}) {r['title']}" + (f"  <- {', '.join(r['problems'])}" if r["problems"] else ""))
    return 0

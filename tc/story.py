# The STORY PAGE check (`tc story <job>`): the story is designed before any script line (owner rules r24, r33).
# jobs/<id>/story.md has fixed "## <heading>" sections (docs/SCRIPT_BIBLE.md section 2). This module checks that
# the page is complete: every section present and filled, a known story shape, every beat of the beat sheet,
# every planted loop has its payoff, and the music plan includes the opening and the ending.
# Quality (is the story GOOD?) is judged separately by the scored story checklist: `tc qa <job> story ...`.
import re
from pathlib import Path

from tc import jobs
from tc.cli import register

REQUIRED_HEADINGS = ["Main character", "Other characters", "Want", "Fear", "Choice", "Central question", "Story shape",
                     "Strongest real elements", "Beat sheet", "Loops", "Emotional arc", "Sound plan"]
STORY_SHAPES = {"mystery", "rise_and_fall", "countdown", "heist", "revenge", "multi_character", "tragedy", "underdog"}
BEATS = {"long": ["cold_open", "world", "complication", "midpoint", "darkest", "climax", "twist", "ending"],
         "short": ["hook", "build", "twist", "ending"]}


def sections(text: str) -> dict[str, str]:
    """'## Want\\nbody...' -> {'Want': 'body...'} (body stripped)."""
    out, name, buf = {}, None, []
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            if name is not None:
                out[name] = "\n".join(buf).strip()
            name, buf = m.group(1), []
        elif name is not None:
            buf.append(line)
    if name is not None:
        out[name] = "\n".join(buf).strip()
    return out


def story_problems(text: str, kind: str) -> list[str]:
    s = sections(text)
    probs = [f"missing section: {h}" for h in REQUIRED_HEADINGS if h not in s]
    probs += [f"section is empty: {h}" for h in REQUIRED_HEADINGS if h in s and not s[h]]
    shape = s.get("Story shape", "").strip().split("\n")[0].strip().lower()
    if "Story shape" in s and s["Story shape"] and shape not in STORY_SHAPES:
        probs.append(f"story shape must be one of {sorted(STORY_SHAPES)}, got {shape!r}")
    # beat sheet: "- <beat>: text"
    have = {m.group(1) for m in re.finditer(r"^-\s*([a-z_]+)\s*:", s.get("Beat sheet", ""), re.M)}
    probs += [f"beat sheet missing: {b}" for b in BEATS[kind] if b not in have]
    # loops: "- plant: ... -> payoff: ..."
    for line in s.get("Loops", "").splitlines():
        line = line.strip()
        if line.startswith("- plant:"):
            plant = line[len("- plant:"):].split("->")[0].strip()
            if not re.search(r"->\s*payoff:\s*\S", line):
                probs.append(f"loop without payoff: {plant}")
    if "Loops" in s and s["Loops"] and "- plant:" not in s["Loops"]:
        probs.append("no loops planted (write '- plant: ... -> payoff: ...')")
    # sound plan: Dialogue + Music lines, music includes opening + ending
    sound = s.get("Sound plan", "")
    music = re.search(r"^Music:\s*(.*)$", sound, re.M)
    if sound and not re.search(r"^Dialogue:\s*\S", sound, re.M):
        probs.append("sound plan needs a 'Dialogue:' line (where characters speak)")
    if sound and (not music or not {"opening", "ending"} <= {w.strip().lower() for w in music.group(1).split(",")}):
        probs.append("music plan must include opening and ending")
    return probs


@register("story", "check jobs/<id>/story.md (the story is designed before the script)", lambda p: p.add_argument("job"))
def _cmd_story(args) -> int:
    from tc import qa
    job = jobs.load_job(args.job)
    d = jobs.job_dir(job.id)
    f = d / "story.md"
    if not f.exists():
        print(f"write {f} first (docs/SCRIPT_BIBLE.md section 2)")
        return 1
    probs = story_problems(f.read_text(encoding="utf-8"), job.kind)
    for p in probs:
        print("problem:", p)
    if probs:
        return 1
    if not qa.passed(d, "story", content_hash=qa.file_hash(f)):       # the score must be for THIS story page
        print("story page complete; now self-score it: python -m tc qa", job.id, "story <answers.json>")
        return 1
    jobs.save_job(jobs.mark(job, "story", "done", note="story page complete + story self-check passed"))
    print("story: done")
    return 0

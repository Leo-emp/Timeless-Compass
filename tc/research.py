# RESEARCH STAGE: a sourced fact sheet for every job, BEFORE the script is written.
#
# Why: rule r12 lets character dialogue be imagined, but the NARRATOR must stay strictly accurate - that is
# where the channel's trust comes from. So every narrator fact in a script cites a fact id ([src: f-...]),
# and every fact cites where it comes from (an ancient author + passage, and/or a modern historian).
#
# Where facts live:
#   library/research/<world>.json      one shared "world" sheet (e.g. salamis_480bc), reused by many videos
#       {"world": "...",
#        "sources": {"herodotus": {"author": "Herodotus", "work": "Histories", "kind": "ancient", "date": "c. 430 BC"}},
#        "facts":   [{"id": "f-sicinnus", "claim": "...", "cites": ["herodotus:8.75", "strauss"],
#                     "topics": ["secret_message"], "status": "agreed" | "disputed", "note": "..."}]}
#   A cite is  "<source id>:<passage>"  (herodotus:8.75 = Histories book 8, chapter 75)  or just "<source id>"
#   (a modern book as a whole).
#
#   python -m tc research <job> --world salamis_480bc --topics secret_message,throne
# writes into jobs/<id>/:
#   research.json   the facts this video uses + only the sources they cite (machine-readable)
#   facts.md        the same as a readable sheet for the owner (claim -> "Herodotus, Histories 8.75")
#   sources.json    MERGED: every fact id becomes citable by the script checker (`tc script` reads this file),
#                   anything already written there by hand is kept
# and marks the job's "research" stage done.
import json
from pathlib import Path

from tc import jobs, paths
from tc.cli import register

KINDS = {"ancient", "modern", "archaeology"}   # archaeology = a find / museum object report (e.g. the Athlit ram)
STATUSES = {"agreed", "disputed"}             # disputed = historians disagree; the note says how, and the
                                              # script must then say "Herodotus says..." instead of stating it


class ResearchError(Exception):
    pass


def load_world(name: str, folder: Path | None = None) -> dict:
    """Read library/research/<name>.json."""
    f = Path(folder or paths.LIBRARY / "research") / f"{name}.json"
    if not f.exists():
        raise ResearchError(f"no fact sheet {f}")
    return json.loads(f.read_text(encoding="utf-8"))


def _source_id(cite: str) -> str:
    """'herodotus:8.75' -> 'herodotus'."""
    return cite.split(":", 1)[0].strip()


def check_sheet(sheet: dict) -> list[str]:
    """Every rule a fact sheet must pass. Returns a list of problems (empty = clean)."""
    problems: list[str] = []
    sources = sheet.get("sources", {})
    for sid, s in sources.items():
        if s.get("kind") not in KINDS:
            problems.append(f"source {sid}: kind must be one of {sorted(KINDS)}")
        if not s.get("author") or not s.get("work"):
            problems.append(f"source {sid}: needs author and work")
    seen = set()
    for f in sheet.get("facts", []):
        fid = f.get("id", "?")
        if fid in seen:
            problems.append(f"duplicate fact id {fid}")
        seen.add(fid)
        if not f.get("claim"):
            problems.append(f"fact {fid}: empty claim")
        if not f.get("cites"):
            problems.append(f"fact {fid}: no source (every fact needs at least one cite)")
        for c in f.get("cites", []):
            if _source_id(c) not in sources:
                problems.append(f"fact {fid}: unknown source {_source_id(c)!r} in cite {c!r}")
        status = f.get("status", "agreed")
        if status not in STATUSES:
            problems.append(f"fact {fid}: status must be one of {sorted(STATUSES)}")
        if status == "disputed" and not f.get("note"):
            problems.append(f"fact {fid}: disputed facts need a note saying who disagrees and how")
    # balance: the ancient writers tell the story, modern historians check it
    used = {_source_id(c) for f in sheet.get("facts", []) for c in f.get("cites", [])}
    used_kinds = {sources[s].get("kind") for s in used if s in sources}
    if sheet.get("facts") and "ancient" not in used_kinds:
        problems.append("no ancient source cited (Herodotus, Plutarch, Aeschylus, Thucydides...)")
    if sheet.get("facts") and "modern" not in used_kinds:
        problems.append("no modern historian cited (they check what the ancient writers claim)")
    return problems


def select_facts(sheet: dict, topics: list[str] | None) -> list[dict]:
    """The facts for one video: those tagged with any of the topics (no topics = all facts)."""
    if not topics:
        return list(sheet.get("facts", []))
    want = set(topics)
    return [f for f in sheet.get("facts", []) if want & set(f.get("topics", []))]


def cite_label(cite: str, sources: dict) -> str:
    """'herodotus:8.75' -> 'Herodotus, Histories 8.75';  'strauss' -> 'Barry Strauss, The Battle of Salamis (2004)'."""
    sid, _, passage = cite.partition(":")
    s = sources[sid.strip()]
    if passage:
        return f"{s['author']}, {s['work']} {passage.strip()}"
    return f"{s['author']}, {s['work']}" + (f" ({s['date']})" if s.get("date") else "")


def facts_markdown(sheet: dict) -> str:
    """A readable fact sheet for the owner."""
    out = [f"# Fact sheet: {sheet.get('world', '')}", "",
           "Narrator lines cite these fact ids: `[src: f-...]`. Disputed facts must be told as "
           "\"Herodotus says...\", never stated flat.", ""]
    for f in sheet["facts"]:
        tag = " **(disputed)**" if f.get("status") == "disputed" else ""
        out.append(f"- `{f['id']}`{tag} {f['claim']}")
        out.append(f"  - sources: {'; '.join(cite_label(c, sheet['sources']) for c in f['cites'])}")
        if f.get("note"):
            out.append(f"  - note: {f['note']}")
    out += ["", "## Sources", ""]
    for sid, s in sheet["sources"].items():
        out.append(f"- `{sid}` ({s['kind']}) {s['author']}, *{s['work']}*" + (f", {s['date']}" if s.get("date") else ""))
    return "\n".join(out) + "\n"


def write_job_sheet(job: jobs.Job, world: dict, topics: list[str] | None) -> Path:
    """Copy the facts for this video out of a world sheet into jobs/<id>/ (see the top of this file)."""
    problems = check_sheet(world)
    if problems:
        raise ResearchError("the world fact sheet has problems:\n- " + "\n- ".join(problems))
    known_topics = {t for f in world.get("facts", []) for t in f.get("topics", [])}
    unknown = [t for t in (topics or []) if t not in known_topics]
    if unknown:
        raise ResearchError(f"unknown topic(s) {unknown}; this sheet has {sorted(known_topics)}")
    facts = select_facts(world, topics)
    used = {_source_id(c) for f in facts for c in f["cites"]}
    sheet = {"world": world.get("world", ""), "topics": topics or [],
             "sources": {k: v for k, v in world["sources"].items() if k in used}, "facts": facts}
    d = jobs.job_dir(job.id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "research.json").write_text(json.dumps(sheet, indent=2, ensure_ascii=False), encoding="utf-8")
    (d / "facts.md").write_text(facts_markdown(sheet), encoding="utf-8")
    # sources.json is what `tc script` checks [src: id] against: add every fact id, keep hand-written entries
    sf = d / "sources.json"
    merged = json.loads(sf.read_text(encoding="utf-8")) if sf.exists() else {}
    for f in facts:
        merged[f["id"]] = {"claim": f["claim"], "cites": [cite_label(c, sheet["sources"]) for c in f["cites"]],
                           "status": f.get("status", "agreed")}
    sf.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    jobs.mark(job, "research", "done", f"{len(facts)} facts from {sheet['world']}")
    jobs.save_job(job)
    return d / "research.json"


def _args(p):
    p.add_argument("job")
    p.add_argument("--world", required=True, help="fact sheet name in library/research/ (e.g. salamis_480bc)")
    p.add_argument("--topics", default="", help="comma-separated topics (default: every fact)")


@register("research", "write the job's sourced fact sheet (research.json, facts.md, sources.json)", _args)
def _cmd_research(args) -> int:
    job = jobs.load_job(args.job)
    topics = [t.strip() for t in args.topics.split(",") if t.strip()] or None
    try:
        out = write_job_sheet(job, load_world(args.world), topics)
    except ResearchError as e:
        print(e)
        return 1
    n = len(json.loads(out.read_text(encoding="utf-8"))["facts"])
    print(f"{n} facts -> {out.parent / 'facts.md'} (cite them in the script as [src: f-...])")
    return 0

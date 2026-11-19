# Owner rules: the first part of the learning system.
# Every piece of owner feedback becomes a numbered rule (r1, r2, ...) with WHY it matters and
# WHICH stages it applies to. The agent reads `tc rules --stage <stage>` before working on a stage,
# so a mistake corrected once stays corrected in every future video.
# Stored twice: taste/learning.json (for the tools) and taste/rules.md (for humans to read).
import json
from datetime import datetime

from tc import paths
from tc.cli import register
from tc.jobs import STAGES

# Stages built in later plans also accept rules now, so feedback about rendering/editing isn't lost.
LATER_STAGES = ["library", "build", "stills", "render", "edit", "qa", "package", "archive"]
KNOWN = STAGES + LATER_STAGES + ["all"]


def _load() -> dict:
    f = paths.TASTE / "learning.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"rules": []}


def add_rule(text: str, why: str = "", applies_to: list[str] | None = None, now: datetime | None = None) -> dict:
    applies_to = applies_to or ["all"]
    bad = [s for s in applies_to if s not in KNOWN]
    if bad:
        raise ValueError(f"unknown stage(s) {bad}; use one of {KNOWN}")
    now = now or datetime.now()
    data = _load()
    rule = {"id": f"r{len(data['rules']) + 1}", "text": text.strip(), "why": why.strip(),
            "applies_to": applies_to, "date": now.strftime("%Y-%m-%d")}
    data["rules"].append(rule)
    paths.TASTE.mkdir(parents=True, exist_ok=True)
    (paths.TASTE / "learning.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    md = paths.TASTE / "rules.md"
    head = "" if md.exists() else "# Timeless Compass owner rules\n\nRead before every stage (`python -m tc rules --stage <stage>`).\n"
    with md.open("a", encoding="utf-8") as f:
        f.write(f"{head}\n## {rule['id']} ({rule['date']})\n- **Rule:** {rule['text']}\n"
                f"- **Why:** {rule['why'] or '-'}\n- **Applies to:** {', '.join(applies_to)}\n")
    return rule


def list_rules(stage: str | None = None) -> list[dict]:
    rules = _load()["rules"]
    if stage is None:
        return rules
    return [r for r in rules if stage in r["applies_to"] or "all" in r["applies_to"]]


# ---------------- commands ----------------
def _learn_args(p):
    p.add_argument("text")
    p.add_argument("--why", default="")
    p.add_argument("--stage", action="append", help="stage this rule applies to (repeatable); default all")


@register("learn", "save an owner rule", _learn_args)
def _cmd_learn(args) -> int:
    r = add_rule(args.text, args.why, args.stage)
    print(f"saved {r['id']}: {r['text']}")
    return 0


@register("rules", "list owner rules", lambda p: p.add_argument("--stage"))
def _cmd_rules(args) -> int:
    for r in list_rules(args.stage):
        print(f"{r['id']} [{', '.join(r['applies_to'])}] {r['text']}" + (f"  (why: {r['why']})" if r["why"] else ""))
    return 0

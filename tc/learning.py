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

# Older rule stage names (from the 3D plans) stay valid so earlier rules keep loading.
OLD_STAGE_NAMES = ["library", "build", "edit", "qa", "package"]
KNOWN = STAGES + [s for s in OLD_STAGE_NAMES if s not in STAGES] + ["all"]


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


def retire_rule(rule_id: str, why: str, replaced_by: str | None = None, now: datetime | None = None) -> dict:
    """Retire a rule that no longer applies (e.g. 3D-only rules after the switch to 2D).
    The rule keeps its id (so numbering never changes) and gains a "retired" block; stage lists skip it."""
    data = _load()
    rule = next((r for r in data["rules"] if r["id"] == rule_id), None)
    if rule is None:
        raise ValueError(f"no rule {rule_id}")
    date = (now or datetime.now()).strftime("%Y-%m-%d")
    rule["retired"] = {"date": date, "why": why.strip(), "replaced_by": replaced_by}
    (paths.TASTE / "learning.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    with (paths.TASTE / "rules.md").open("a", encoding="utf-8") as f:       # humans see the retirement too
        f.write(f"\n## {rule_id} RETIRED ({date})\n- **Why:** {why.strip()}\n- **Replaced by:** {replaced_by or '-'}\n")
    return rule


def list_rules(stage: str | None = None, include_retired: bool = False) -> list[dict]:
    rules = [r for r in _load()["rules"] if include_retired or "retired" not in r]   # retired rules are history only
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


def _rules_args(p):
    p.add_argument("--stage")
    p.add_argument("--all", action="store_true", help="also show retired rules")


@register("rules", "list owner rules", _rules_args)
def _cmd_rules(args) -> int:
    for r in list_rules(args.stage, include_retired=args.all):
        print(f"{r['id']} [{', '.join(r['applies_to'])}] {r['text']}" + (f"  (why: {r['why']})" if r["why"] else ""))
    return 0


def _retire_args(p):
    p.add_argument("rule_id")
    p.add_argument("--why", required=True)
    p.add_argument("--by", default=None, help="the rule that replaces it")


@register("retire", "retire an owner rule that no longer applies (kept as history)", _retire_args)
def _cmd_retire(args) -> int:
    r = retire_rule(args.rule_id, args.why, args.by)
    print(f"retired {r['id']}: {r['text'][:80]}")
    return 0

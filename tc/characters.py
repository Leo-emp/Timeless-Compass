# CHARACTER REGISTRY (`tc characters`, owner rules r19 + r26): every named character has ONE locked identity.
#   library/characters/<id>/sheet.json   the look, colours, signature costume, design source and ONE voice
#   film/src/characters/<id>.ts          draws them in any pose/expression (always from the sheet's colours)
#   library/characters/<id>/sheet.png    turnaround image (film/scripts/sheet.mjs)
# Scenes around a character are always new (r17); the character never changes (r19).
#
#   python -m tc characters list
#   python -m tc characters check leonidas
import json
import re

from tc import paths
from tc.cli import register

PARTS = {"skin", "hair", "beard", "tunic", "cloak", "armour", "helmet", "crest", "trim", "robe", "crown", "shield",
         "belt", "boots", "sash", "cap"}
KINDS = {"real", "myth", "composite"}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def root():
    return paths.LIBRARY / "characters"


def all_ids() -> list[str]:
    r = root()
    return sorted(p.parent.name for p in r.glob("*/sheet.json")) if r.exists() else []


def load_sheet(cid: str) -> dict:
    return json.loads((root() / cid / "sheet.json").read_text(encoding="utf-8"))


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def resolve(name: str) -> str | None:
    """Registry id for a speaker name or alias ('KING XERXES' -> 'xerxes'), case- and spacing-insensitive."""
    want = _norm(name)
    for cid in all_ids():
        s = load_sheet(cid)
        names = {_norm(cid), _norm(s.get("name", ""))} | {_norm(a) for a in s.get("aliases", [])}
        if want in names:
            return cid
    return None


def sheet_problems(sheet: dict, voices: dict) -> list[str]:
    probs = []
    for k in ("id", "name", "who", "era", "voice", "look"):
        if not sheet.get(k):
            probs.append(f"sheet needs '{k}'")
    if sheet.get("kind") not in KINDS:
        probs.append(f"kind must be one of {sorted(KINDS)}")
    if sheet.get("kind") in ("real", "myth") and not str(sheet.get("design_source", "")).strip():
        probs.append("real/myth characters need a design_source (period art / museum piece, never another production)")
    if sheet.get("voice") and sheet["voice"] not in voices.get("characters", {}):
        probs.append(f"voice {sheet['voice']!r} is not in library/voices.json")
    look = sheet.get("look", {})
    colours = {"skin": look.get("skin"), "hair": (look.get("hair") or {}).get("colour")}
    if look.get("beard"):
        colours["beard"] = look["beard"].get("colour")
    for part, col in list(colours.items()) + list(look.get("parts", {}).items()):
        if part not in PARTS:
            probs.append(f"unknown part {part!r}; parts are {sorted(PARTS)}")
        if not isinstance(col, str) or not HEX.match(col):
            probs.append(f"{part} colour must be #rrggbb, got {col!r}")
    b = look.get("build", {})
    if not (0.85 <= b.get("height", 1) <= 1.15 and 0.85 <= b.get("width", 1) <= 1.2):
        probs.append("build height must be 0.85-1.15 and width 0.85-1.2")
    if not sheet.get("signature"):
        probs.append("list the signature details that make them recognisable")
    return probs


def part_colours(sheet: dict) -> dict[str, str]:
    """Every checkable part colour of a character, lower-case: skin, hair, beard + look.parts."""
    look = sheet["look"]
    out = {"skin": look["skin"], "hair": look["hair"]["colour"]}
    if look.get("beard"):
        out["beard"] = look["beard"]["colour"]
    out.update(look.get("parts", {}))
    return {k: v.lower() for k, v in out.items()}


def _args(p):
    p.add_argument("action", choices=["list", "check"])
    p.add_argument("id", nargs="?")


@register("characters", "character registry: list, or check one sheet (r19)", _args)
def _cmd_characters(args) -> int:
    from tc.dialogue import load_voices
    if args.action == "list":
        for cid in all_ids():
            s = load_sheet(cid)
            print(f"{cid:16} {s['name']:20} voice={s.get('voice')}  {s.get('who', '')[:60]}")
        return 0
    probs = sheet_problems(load_sheet(args.id), load_voices())
    for f in ("sheet.png",):
        if not (root() / args.id / f).exists():
            probs.append(f"missing {f} (node film/scripts/sheet.mjs {args.id})")
    for p in probs:
        print("problem:", p)
    print(args.id + ":", "OK" if not probs else f"{len(probs)} problem(s)")
    return 1 if probs else 0

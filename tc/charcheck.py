# CHARACTER CHECK (rule r19): in every still, every tagged part of a named character (data-char / data-part /
# data-fill, written by film/src/characters/figure.ts part()) must use exactly the colour on its sheet.
# Used by `tc still <png> --json <json> --chars`.
from tc import characters

OUTLINE = "#2a1c13"     # the house outline colour may appear in any part


def character_problems(elements: list[dict], sheets: dict[str, dict]) -> list[str]:
    probs, seen = [], set()
    for e in elements:
        cid = e.get("char")
        if not cid:
            continue
        if cid not in sheets:
            if cid not in seen:
                probs.append(f"{cid} is not in the registry (library/characters/{cid}/sheet.json)")
                seen.add(cid)
            continue
        look = sheets[cid]["look"]
        colours = {"skin": look.get("skin"), "hair": (look.get("hair") or {}).get("colour")}
        if look.get("beard"):
            colours["beard"] = look["beard"].get("colour")
        colours.update(look.get("parts", {}))
        want = colours.get(e.get("part"))
        if want is None:
            probs.append(f"{cid}: no colour for part {e.get('part')!r} on the sheet")
        elif str(e.get("fill", "")).lower() != want.lower():
            probs.append(f"{cid} {e['part']} is {str(e.get('fill')).lower()}, sheet says {want.lower()}")
        # the colours really drawn inside the part (inspector: computed fills of every opaque shape in the group)
        drawn = [f.lower() for f in e.get("fills", [])]
        if drawn and want:
            allowed = {c.lower() for c in colours.values() if c} | {a.lower() for a in look.get("accents", [])} | {OUTLINE}
            for f in sorted(set(drawn) - allowed):
                probs.append(f"{cid} {e['part']} draws {f}, which is not on the sheet (parts or accents)")
            if want.lower() not in drawn:
                probs.append(f"{cid} {e['part']}: its sheet colour {want.lower()} is not drawn (it claims it but paints {sorted(set(drawn))})")
    return probs


def load_sheets_for(elements: list[dict]) -> dict[str, dict]:
    """Sheets of every registered character that appears in the still."""
    ids = {e["char"] for e in elements if e.get("char")}
    return {i: characters.load_sheet(i) for i in ids if i in characters.all_ids()}

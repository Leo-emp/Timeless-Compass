# `python -m tc map ...` — WS19 parchment maps (docs/MAP_STYLE.md).
#   tc map fetch                         download the Natural Earth shapes once (~30 MB, public domain)
#   tc map paint <spec.json> [--out D]   paint every texture + manifest for Blender (see tc/maps/build.py)
#   tc map check <spec.json>             validate a spec without painting
import json
from pathlib import Path

from tc.cli import register
from tc.maps import geo
from tc.maps.spec import problems


def _add(p):
    p.add_argument("action", choices=["fetch", "paint", "check"])
    p.add_argument("spec", nargs="?")
    p.add_argument("--out")
    p.add_argument("--width", type=int, default=6144)
    p.add_argument("--preview", action="store_true", help="also write a flat preview.png with all labels")


@register("map", "parchment maps: fetch data, check or paint a map spec", _add)
def run(args) -> int:
    if args.action == "fetch":
        import subprocess
        geo.NE_DIR.mkdir(parents=True, exist_ok=True)
        for f in geo.NE_FILES.values():
            dst = geo.NE_DIR / f"{f}.geojson"
            if dst.exists():
                continue
            r = subprocess.run(["curl", "-sfL", "--max-time", "300", "-o", str(dst), geo.NE_BASE + f + ".geojson"])
            print(("ok   " if r.returncode == 0 else "FAIL ") + f)
        return 0
    if not args.spec:
        print("give a spec file"); return 2
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    errs = [] if spec.get("kind") == "battle" else problems(spec)
    for e in errs:
        print("problem:", e)
    if errs or args.action == "check":
        return 1 if errs else 0
    from tc.maps.build import paint
    from tc.maps.battle import paint_battle
    out = Path(args.out) if args.out else Path(args.spec).with_suffix("")
    man = (paint_battle if spec.get("kind") == "battle" else paint)(spec, out, args.width, args.preview)
    print(f"painted {out}: {len(man['territories'])} territories, {len(man['labels'])} labels, "
          f"{len(man['arrows'])} arrows")
    return 0

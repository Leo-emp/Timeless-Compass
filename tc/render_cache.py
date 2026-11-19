# Asset cache for cloud renders (WS9 task 3).
#
# THE PROBLEM: the scans (Poly Haven rocks/plants/textures, Sketchfab museum pieces) are ~0.6 GB and growing, and
# they are git-ignored (too big for a public repo). A cloud machine that renders 6 shots must not download the
# whole library, and heavy things we BUILD (characters with strand hair + simulated cloth, full sets) should be
# built once and reused instead of rebuilt on every machine.
#
# THE PLAN (all free, nothing runs until the owner says so):
#   1. library/scans_index.json (small, committed): every scan's id, licence, source, files and size.
#      `tc cache index` writes it from the laptop's library/scans/ folders.
#   2. Cloudflare R2 bucket (free tier: 10 GB stored, free egress). Layout:
#         library/scans/<id>/<file>             the scans, exactly as on the laptop
#         built/<kind>/<name>-<hash>.blend      heavy built assets, saved once from Blender (compressed .blend)
#      The library may use at most LIBRARY_BUDGET_GB (6 GB, spec 6.4) so review copies fit in the rest.
#   3. Each render shard downloads ONLY the scans its own shots need (`tc cache fetch <job> --shard kaggle:0`).
#      Reads use the bucket's public r2.dev URL (TC_R2_PUBLIC_URL; the assets are CC0/CC-BY, so public read is
#      fine and needs no key on the cloud machine). If R2 is not set up yet, Poly Haven scans are re-downloaded
#      from Poly Haven itself (free, no key); Sketchfab scans need R2 (their download needs a token).
#   4. Uploads (`tc cache push`) need the owner's R2 keys in .env and an explicit --yes. Never automatic.
#
# A built asset's cache key contains a hash of its manifest + the code that builds it, so when either changes
# the old .blend is simply not used any more (the agent rebuilds and uploads the new one).
import hashlib
import json
import os
import re
from pathlib import Path

from tc import jobs
from tc.cli import register
from tc.paths import LIBRARY, ROOT

GB = 1024 ** 3
R2_FREE_GB = 10                    # Cloudflare R2 free tier storage
LIBRARY_BUDGET_GB = 6              # our share for the library (spec 6.4); the rest is for review copies
INDEX_FILE = LIBRARY / "scans_index.json"
SCANS = LIBRARY / "scans"
BLENDER_LIB = ROOT / "blender" / "lib"


class CacheError(Exception):
    pass


# --------------------------------------------------------------------------------------------- the index
def build_index(scans_root: Path = SCANS) -> dict:
    """{id: {kind, licence, source, files, bytes}} from every library/scans/<id>/asset.json.
    `bytes` is the real size on disk of the whole folder (what R2 will store)."""
    idx = {}
    for meta in sorted(Path(scans_root).glob("*/asset.json")):
        d = meta.parent
        a = json.loads(meta.read_text(encoding="utf-8"))
        files = [str(p.relative_to(d)).replace("\\", "/") for p in sorted(d.rglob("*")) if p.is_file()]
        idx[d.name] = {"kind": a.get("kind"), "res": a.get("res"), "licence": a.get("licence"), "source": a.get("source"),
                       "files": files, "bytes": sum((d / f).stat().st_size for f in files)}
    return idx


def load_index(path: Path = INDEX_FILE) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else {}


# --------------------------------------------------------------------------------------------- what a shot needs
def scans_in_code(code: str, index: dict) -> list[str]:
    """Every scan id written as a quoted string in some code ('boulder_01' or "boulder_01"). Sorted, unique."""
    found = set(re.findall(r"""['"]([A-Za-z0-9_]+)['"]""", code))
    return sorted(found & set(index))


def function_source(module_code: str, func: str) -> str:
    """Cut one top-level function (def func ... up to the next top-level line) out of a module's text."""
    m = re.search(rf"^def {re.escape(func)}\b.*?(?=^\S|\Z)", module_code, flags=re.M | re.S)
    return m.group(0) if m else ""


def code_closure(builder: str, modules: dict[str, str]) -> str:
    """The source of a builder function PLUS every helper it calls, and their helpers, across the blender/lib
    modules ({module name: source}). 'sets.salamis_dusk' calls _harbour_wall(), which calls
    scatter.scan_material('old_sandstone_02') -> that scan is found too. Functions that are never called are left
    out, so a shot does not download scans for sets it does not use."""
    if not builder or "." not in builder:
        return ""
    defined = {}                                        # function name -> [(module, source)]
    for mod, code in modules.items():
        for name in re.findall(r"^def (\w+)", code, flags=re.M):
            defined.setdefault(name, []).append(mod)
    out, seen = [], set()
    todo = [tuple(builder.split(".", 1))]
    while todo:
        mod, func = todo.pop()
        if (mod, func) in seen or mod not in modules:
            continue
        seen.add((mod, func))
        src = function_source(modules[mod], func)
        out.append(src)
        for prefix, name in re.findall(r"\b(?:(\w+)\.)?(\w+)\s*\(", src):
            if prefix in modules:                       # scatter.scan_material(...)
                todo.append((prefix, name))
            elif not prefix:                            # _helper(...) here, or a name imported from another module
                for m in ([mod] if mod in defined.get(name, []) else defined.get(name, [])):
                    todo.append((m, name))
    return "\n".join(out)


def _lib_modules() -> dict[str, str]:
    return {f.stem: f.read_text(encoding="utf-8") for f in sorted(BLENDER_LIB.glob("*.py"))}


def _builder_code(builder: str) -> str:
    """'sets.salamis_dusk' -> the source of salamis_dusk() in blender/lib/sets.py and of every helper it calls."""
    return code_closure(builder, _lib_modules())


def _cast_code() -> str:
    """Characters: the whole people-building code (bodies, faces, hair, wardrobe, armour). Used only when a cast or
    wardrobe manifest does not list its scans; it over-fetches a little (cloth scans of other garments)."""
    return "\n".join((BLENDER_LIB / f).read_text(encoding="utf-8")
                     for f in ("cast.py", "wardrobe.py", "armour.py", "build.py", "expressions.py") if (BLENDER_LIB / f).exists())


def needed_scans(recipe: dict, lib: dict, index: dict, code_for=_builder_code, cast_code=_cast_code) -> list[str]:
    """Which scans one shot recipe needs.
    1. A manifest may list them itself:  "scans": ["boulder_01", ...]  (best: exact, written by the asset's builder).
    2. Otherwise we read the code: the set builder + all helpers it calls; for people the people-building code.
    It may over-fetch a little, but it never misses a scan that the code names."""
    need = set()
    s = recipe.get("set") or {}
    m = (lib.get("sets") or {}).get(s.get("name"), {})
    if m.get("scans"):
        need |= set(m["scans"])
    elif s:
        need |= set(scans_in_code(code_for(s.get("builder") or ""), index))
        if m.get("film_light"):
            need |= set(scans_in_code(code_for(m["film_light"]), index))
    listed = False
    for c in recipe.get("cast") or []:
        for kind, name in (("cast", c.get("name")), ("wardrobe", c.get("wardrobe"))):
            got = ((lib.get(kind) or {}).get(name) or {}).get("scans")
            if got:
                need |= set(got)
                listed = True
    if recipe.get("cast") and not listed:
        need |= set(scans_in_code(cast_code(), index))
    # safety net: a manifest may name a scan in any field (e.g. "cloth": "rough_linen")
    mans = [m] + [((lib.get(k) or {}).get(c.get(f)) or {}) for c in recipe.get("cast") or []
                  for k, f in (("cast", "name"), ("wardrobe", "wardrobe"))]
    need |= set(scans_in_code(json.dumps(mans), index))
    return sorted(need & set(index)) if index else sorted(need)


def shard_scans(shot_ids: list[str], scans_by_shot: dict) -> list[str]:
    """The union of scans for the shots of one shard: that is all the shard downloads."""
    return sorted({sc for sid in shot_ids for sc in scans_by_shot.get(sid, [])})


def bundle_shard_scans(bundle: dict, where: str | None, index: int | None) -> list[str]:
    """Scans for one shard of a cloud bundle (cloud/bundles/<job>.json); where=None -> the whole job."""
    by_shot = bundle.get("scans") or {}
    if where is None:
        return sorted({sc for v in by_shot.values() for sc in v})
    return shard_scans(bundle["plan"][where][index]["shots"], by_shot)


# --------------------------------------------------------------------------------------------- R2 layout + budget
def r2_key(asset_id: str, file: str) -> str:
    return f"library/scans/{asset_id}/{file}"


def built_key(kind: str, name: str, manifest: dict, code: str) -> str:
    """Cache key of a heavy built asset, e.g. built/cast/themistocles-1a2b3c4d5e6f.blend.
    The hash covers the manifest (what to build) and the builder code (how), so any change = new key."""
    h = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode() + b"\0" + code.encode()).hexdigest()[:12]
    return f"built/{kind}/{name}-{h}.blend"


# Which code builds each kind of heavy asset. The whole files are hashed: simple, and it can only over-invalidate
# (rebuild when not strictly needed), never use a stale .blend.
BUILD_CODE = {"cast": ["cast.py", "wardrobe.py", "build.py", "expressions.py"], "sets": ["sets.py", "scatter.py"]}


def _kind_code(kind: str) -> str:
    return "\n".join((BLENDER_LIB / f).read_text(encoding="utf-8") for f in BUILD_CODE[kind] if (BLENDER_LIB / f).exists())


def built_plan(recipes: list[dict], lib: dict, code_for_kind=_kind_code) -> list[dict]:
    """The heavy built assets a job uses, each once: [{kind, name, key, shots}].
    cast = a character built with hair + face + wardrobe (before motion); sets = the full set + its film light.
    cloud/build_asset_cache.py builds one and saves it as a compressed .blend for R2 under `key`."""
    found: dict[tuple, dict] = {}
    code = {}
    for r in recipes:
        items = [("cast", c.get("name")) for c in r.get("cast") or []]
        if r.get("set"):
            items.append(("sets", r["set"].get("name")))
        for kind, name in items:
            m = (lib.get(kind) or {}).get(name)
            if m is None:
                continue                                    # a library gap: tc assemble reports it
            if kind not in code:
                code[kind] = code_for_kind(kind)
            e = found.setdefault((kind, name), {"kind": kind, "name": name,
                                                "key": built_key(kind, name, m, code[kind]), "shots": []})
            e["shots"].append(r["shot"])
    return sorted(found.values(), key=lambda e: (e["kind"], e["name"]))


def fallback_source(entry: dict) -> str | None:
    """Where else a scan can come from if R2 does not have it: 'polyhaven' (free, no key) or None."""
    return "polyhaven" if "polyhaven.com" in (entry.get("source") or "") else None


def budget_report(index: dict, built_bytes: int = 0) -> dict:
    """Does the library fit in our share of the free R2 tier?"""
    used = sum(e.get("bytes", 0) for e in index.values()) + built_bytes
    return {"used_gb": round(used / GB, 2), "limit_gb": LIBRARY_BUDGET_GB, "free_tier_gb": R2_FREE_GB,
            "ok": used <= LIBRARY_BUDGET_GB * GB}


def public_url(key: str) -> str:
    """Download address of an R2 object through the bucket's public URL (owner sets TC_R2_PUBLIC_URL)."""
    base = os.environ.get("TC_R2_PUBLIC_URL", "").strip()
    if not base:
        raise CacheError("TC_R2_PUBLIC_URL is not set (owner step: make the R2 bucket's public r2.dev URL)")
    return base.rstrip("/") + "/" + key


def fetch_plan(scan_ids: list[str], index: dict, root: Path = SCANS) -> list[dict]:
    """Files still missing locally: [{id, file, key}]. Already-cached files are skipped (resume-friendly)."""
    todo = []
    for sid in scan_ids:
        for f in index.get(sid, {}).get("files", []):
            if not (Path(root) / sid / f).exists():
                todo.append({"id": sid, "file": f, "key": r2_key(sid, f)})
    return todo


def _download(url: str, dest: Path) -> None:
    import subprocess
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")              # never leave half a file under the real name
    subprocess.run(["curl", "-sSfL", "--retry", "3", "-o", str(tmp), url], check=True)
    tmp.replace(dest)


def fetch(scan_ids: list[str], index: dict, root: Path = SCANS) -> dict:
    """Download the missing files: R2 public URL first, Poly Haven as the free fallback."""
    got, failed = [], []
    have_r2 = bool(os.environ.get("TC_R2_PUBLIC_URL", "").strip())
    for t in fetch_plan(scan_ids, index, root):
        try:
            if not have_r2:
                raise CacheError("no R2")
            _download(public_url(t["key"]), Path(root) / t["id"] / t["file"])
            got.append(t["key"])
        except Exception:
            failed.append(t["id"])
    for sid in sorted(set(failed)):                      # fallback for whole assets
        entry = index[sid]
        if fallback_source(entry) == "polyhaven":
            from tc import assets
            kind = entry.get("kind") or "models"
            assets.fetch(sid, kind, res=entry.get("res") or "2k", root=Path(root))
            got.append(f"polyhaven:{sid}")
        else:
            raise CacheError(f"{sid}: not on R2 and no free fallback (Sketchfab scans must be uploaded to R2)")
    return {"downloaded": got}


# --------------------------------------------------------------------------------------------- commands
def _args(p):
    p.add_argument("action", choices=["index", "plan", "built", "fetch", "push"])
    p.add_argument("job", nargs="?", help="job id (plan / fetch)")
    p.add_argument("--shard", help="where:index, e.g. kaggle:0 (fetch only that shard's scans)")
    p.add_argument("--bundle", help="fetch: read shots + scans from cloud/bundles/<job>.json (cloud machines)")
    p.add_argument("--yes", action="store_true", help="push: really upload (costs nothing inside the free tier)")


def _job_scans(job: str) -> dict:
    """{shot id: [scan ids]} for every recipe of a job (written by `tc assemble`)."""
    from tc.assemble import load_library
    d = jobs.job_dir(job) / "recipes"
    lib, index = load_library(), load_index()
    return {f.stem: needed_scans(json.loads(f.read_text(encoding="utf-8")), lib, index) for f in sorted(d.glob("*.json"))}


@register("cache", "asset cache for cloud renders: index / plan / fetch / push (R2, free 10 GB)", _args)
def _cmd_cache(args) -> int:
    if args.action == "index":
        idx = build_index()
        INDEX_FILE.write_text(json.dumps(idx, indent=2), encoding="utf-8")
        rep = budget_report(idx)
        print(f"{len(idx)} scans, {rep['used_gb']} GB of the {rep['limit_gb']} GB library budget -> {INDEX_FILE.name}")
        return 0 if rep["ok"] else 1
    if args.action == "push":
        # Uploading is an outward action: the owner must ask for it AND pass --yes. Keys come from .env only.
        if not args.yes:
            idx = load_index()
            print(f"would upload {len(idx)} scans ({budget_report(idx)['used_gb']} GB) to R2; add --yes to do it")
            return 0
        print("upload: run  bash cloud/r2_push.sh  (uses the owner's R2 keys from .env; see cloud/README.md)")
        return 0
    if args.action == "fetch" and args.bundle:            # cloud machines: no jobs/ folder, only the bundle
        b = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
        where, i = args.shard.split(":") if args.shard else (None, None)
        ids = bundle_shard_scans(b, where, int(i) if i is not None else None)
        print(f"fetching {len(ids)} scans for {args.shard or 'the whole job'}")
        print(len(fetch(ids, load_index())["downloaded"]), "files downloaded")
        return 0
    if not args.job:
        print("give a job id")
        return 2
    if args.action == "built":                            # heavy .blend assets this job reuses
        from tc.assemble import load_library
        recipes = [json.loads(f.read_text(encoding="utf-8")) for f in sorted((jobs.job_dir(args.job) / "recipes").glob("*.json"))]
        for e in built_plan(recipes, load_library()):
            print(f"{e['key']}  ({len(e['shots'])} shots)  build: blender -b --python cloud/build_asset_cache.py -- "
                  f"{e['kind']} {e['name']} out/{e['key']}")
        return 0
    scans = _job_scans(args.job)
    index = load_index()
    if args.action == "plan":
        plan = json.loads((jobs.job_dir(args.job) / "render_plan.json").read_text(encoding="utf-8"))
        for where in ("kaggle", "github"):
            for i, g in enumerate(plan.get(where, [])):
                ids = shard_scans(g["shots"], scans)
                mb = sum(index.get(s, {}).get("bytes", 0) for s in ids) / 1024 ** 2
                print(f"{where}[{i}]: {len(ids)} scans, {mb:.0f} MB")
        return 0
    ids = sorted({s for v in scans.values() for s in v})
    if args.shard:
        where, i = args.shard.split(":")
        plan = json.loads((jobs.job_dir(args.job) / "render_plan.json").read_text(encoding="utf-8"))
        ids = shard_scans(plan[where][int(i)]["shots"], scans)
    print(f"fetching {len(ids)} scans")
    print(len(fetch(ids, index)["downloaded"]), "files downloaded")
    return 0

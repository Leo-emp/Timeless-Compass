# SKETCHFAB downloader: real museum photo-scans (many CC0: British Museum, The Met, Smithsonian...) and free CC-BY
# models (horses, ships, armour). Only YouTube-safe licences: CC0 (no credit) and CC BY (credit line, which goes into
# every video description from library/scans/<id>/asset.json). Never NC (non-commercial), ND (no changes) or SA.
# The owner's free API token lives in .env as SKETCHFAB_TOKEN (never printed, never committed).
#   python -m tc sketchfab search "greek amphora"          list allowed matches
#   python -m tc sketchfab get <uid> [--name corinthian_helmet]
import json
import os
import subprocess
import zipfile
from pathlib import Path
from urllib.parse import quote

from tc.cli import register
from tc.config import load_env
from tc.http import get_json
from tc.paths import LIBRARY

API = "https://api.sketchfab.com/v3"
SCANS = LIBRARY / "scans"
ALLOWED = {"cc0": "CC0", "by": "CC BY 4.0"}


LABELS = {"CC0 Public Domain": "cc0", "CC Attribution": "by"}   # search results give labels, model pages give slugs


def slug(m: dict) -> str | None:
    lic = m.get("license") or {}
    return lic.get("slug") or LABELS.get(lic.get("label", ""))


def allowed(m: dict) -> bool:
    return slug(m) in ALLOWED and m.get("isDownloadable", True)


def pick(results: list[dict], n: int = 10) -> list[dict]:
    """Allowed models only; CC0 first (no strings attached), then lighter meshes (faster to render)."""
    ok = [m for m in results if allowed(m)]
    return sorted(ok, key=lambda m: (slug(m) != "cc0", m.get("faceCount") or 0))[:n]


def credit(m: dict) -> str:
    lic = ALLOWED[slug(m)]
    who = (m.get("user") or {}).get("displayName", "unknown")
    return f'"{m["name"]}" by {who}, {m.get("viewerUrl", "sketchfab.com")} ({lic})'


def search(query: str, token: str | None = None) -> list[dict]:
    q = quote(query)
    url = f"{API}/search?type=models&q={q}&downloadable=true&count=24&sort_by=-likeCount"
    data = get_json(url, {"Authorization": f"Token {token}"} if token else None)
    return pick(data.get("results", []), n=24)


def fetch(uid: str, token: str, name: str | None = None, root: Path = SCANS) -> Path:
    m = get_json(f"{API}/models/{uid}", {"Authorization": f"Token {token}"})
    if not allowed(m):
        raise ValueError(f"licence {m.get('license')} is not allowed on a monetised channel")
    d = get_json(f"{API}/models/{uid}/download", {"Authorization": f"Token {token}"})
    pkg = d.get("glb") or d.get("gltf")
    if not pkg:
        raise ValueError("no glTF download offered")
    out = root / (name or ("sf_" + uid[:10]))
    out.mkdir(parents=True, exist_ok=True)
    is_glb = "glb" in d
    dest = out / ("model.glb" if is_glb else "model.zip")
    r = subprocess.run(["curl", "-s", "-f", "-L", "--max-time", "900", "-o", str(dest), pkg["url"]], capture_output=True)
    if r.returncode != 0:
        raise ValueError("download failed")
    if not is_glb:
        with zipfile.ZipFile(dest) as z:
            z.extractall(out)
        dest.unlink()
    (out / "asset.json").write_text(json.dumps({
        "id": out.name, "kind": "sketchfab", "uid": uid, "name": m["name"], "licence": ALLOWED[slug(m)],
        "author": (m.get("user") or {}).get("displayName"), "source": m.get("viewerUrl"), "credit": credit(m),
        "faces": m.get("faceCount")}, indent=2), encoding="utf-8")
    return out


def _args(p):
    p.add_argument("action", choices=["search", "get"])
    p.add_argument("query")
    p.add_argument("--name")


@register("sketchfab", "search/download CC0 + CC-BY models (museum scans, horses) into library/scans", _args)
def _cmd_sketchfab(args) -> int:
    import sys
    sys.stdout.reconfigure(errors="replace")          # author names with accents must not crash the Windows console
    token = load_env().get("SKETCHFAB_TOKEN") or os.environ.get("SKETCHFAB_TOKEN")
    if args.action == "search":
        for m in search(args.query, token):
            print(f"{m['uid']}  {slug(m):4s} {m.get('faceCount') or 0:>8} faces  {m['name'][:50]}  ({m['user']['displayName']})")
        return 0
    if not token:
        print("No SKETCHFAB_TOKEN in .env (sketchfab.com > Settings > Password & API)")
        return 2
    print("ok", fetch(args.query, token, args.name))
    return 0

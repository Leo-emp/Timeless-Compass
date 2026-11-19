# Free scanned assets from Poly Haven (CC0: free for any use, no credit needed), approved by the owner 2026-11-19.
# Photo-scanned ground, rock, stone, plaster and wood textures, real-sky HDRIs (natural light on skin and cloth),
# and scanned models (trees, plants, rocks). Files go to library/scans/<id>/ (git-ignored; big files live in R2).
#   python -m tc assets fetch <id> --kind textures|hdris|models [--res 2k]
# The laptop disk is nearly full, so downloads stop at a local budget (TC_SCANS_CAP_GB, default 3 GB).
import hashlib
import json
import os
import subprocess
from pathlib import Path

from tc.cli import register
from tc.http import get_json
from tc.paths import LIBRARY

SCANS = LIBRARY / "scans"
API = "https://api.polyhaven.com"
TEXTURE_MAPS = ["Diffuse", "nor_gl", "Rough", "Displacement"]     # colour, OpenGL normal (Blender), roughness, height
DEFAULT_CAP = int(float(os.environ.get("TC_SCANS_CAP_GB", "3")) * 1024 ** 3)


class AssetError(Exception):
    pass


def _name(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def plan_files(files: dict, kind: str, res: str = "2k") -> list[tuple[str, str, int, str]]:
    """Which files to download: [(relative path, url, size, md5)]. Raises KeyError if `res` is not offered."""
    if kind == "hdris":
        f = files["hdri"][res]["hdr"]
        return [(_name(f["url"]), f["url"], f["size"], f["md5"])]
    if kind == "textures":
        out = []
        for m in TEXTURE_MAPS:
            if m not in files:
                continue
            fmts = files[m][res]
            f = fmts.get("jpg") or fmts.get("png") or next(iter(fmts.values()))
            out.append((_name(f["url"]), f["url"], f["size"], f["md5"]))
        if not out:
            raise KeyError(res)
        return out
    if kind == "models":
        b = files["blend"][res]["blend"]
        out = [(_name(b["url"]), b["url"], b["size"], b["md5"])]
        out += [(rel, f["url"], f["size"], f["md5"]) for rel, f in b.get("include", {}).items()]
        return out
    raise ValueError(f"unknown kind {kind!r}")


def _dir_size(root: Path) -> int:
    return sum(p.stat().st_size for p in Path(root).rglob("*") if p.is_file()) if Path(root).exists() else 0


def over_budget(root: Path, incoming: int, cap_bytes: int = DEFAULT_CAP) -> bool:
    return _dir_size(root) + incoming > cap_bytes


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _curl_download(url: str, path: Path) -> None:
    res = subprocess.run(["curl", "-s", "-f", "-L", "--max-time", "900", "-o", str(path), url], capture_output=True)
    if res.returncode != 0:
        raise AssetError(f"download failed ({res.returncode}): {url}")


def fetch(asset_id: str, kind: str, res: str = "2k", root: Path = SCANS, files: dict | None = None,
          download=_curl_download, cap_bytes: int = DEFAULT_CAP) -> Path:
    """Download one Poly Haven asset (skipping files already there), verify every checksum, write asset.json."""
    root = Path(root)
    files = files if files is not None else get_json(f"{API}/files/{asset_id}")
    plan = plan_files(files, kind, res)
    out = root / asset_id
    todo = [p for p in plan if not ((out / p[0]).exists() and _md5(out / p[0]) == p[3])]
    if over_budget(root, sum(p[2] for p in todo), cap_bytes):
        raise AssetError(f"{asset_id}: would pass the local scans budget ({cap_bytes / 1024 ** 3:.1f} GB); "
                         "archive unused scans to R2 first")
    for rel, url, _size, md5 in todo:
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        download(url, dest)
        if not dest.exists() or _md5(dest) != md5:
            if dest.exists():
                dest.unlink()
            raise AssetError(f"{asset_id}: checksum mismatch for {rel}")
    (out / "asset.json").write_text(json.dumps({
        "id": asset_id, "kind": kind, "res": res, "licence": "CC0 (Poly Haven)",
        "source": f"https://polyhaven.com/a/{asset_id}", "files": [p[0] for p in plan]}, indent=2), encoding="utf-8")
    return out


def _args(p):
    p.add_argument("action", choices=["fetch", "list"])
    p.add_argument("ids", nargs="*")
    p.add_argument("--kind", default="textures", choices=["textures", "hdris", "models"])
    p.add_argument("--res", default="2k")


@register("assets", "fetch free CC0 scans (Poly Haven) into library/scans, within the disk budget", _args)
def _cmd_assets(args) -> int:
    if args.action == "list":
        for d in sorted(SCANS.glob("*/asset.json")):
            m = json.loads(d.read_text(encoding="utf-8"))
            print(f"{m['id']:32s} {m['kind']:9s} {_dir_size(d.parent) / 1024 ** 2:7.1f} MB")
        print(f"total {_dir_size(SCANS) / 1024 ** 3:.2f} GB of {DEFAULT_CAP / 1024 ** 3:.1f} GB")
        return 0
    bad = 0
    for i in args.ids:
        try:
            print("ok", fetch(i, args.kind, args.res))
        except (AssetError, KeyError) as e:
            print("FAILED", i, e); bad += 1
    return 1 if bad else 0

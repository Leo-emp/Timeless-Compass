# MIXAMO downloader: Adobe's free motion library (commercial use in films/videos allowed; raw files must not be
# redistributed, so they live OUTSIDE the public repo in tools/mocap/mixamo/). The owner logs in on mixamo.com and
# puts the browser's temporary access token in .env as MIXAMO_TOKEN (never printed, never committed).
#   python -m tc mixamo "Breathing Idle" "Talking" ...      (or --list for the default film set)
# Flow (Mixamo's own web API): search the motion -> get its settings (gms_hash) for our character -> ask for an
# FBX export without skin at 30 fps -> wait for the job -> download the file.
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import quote

from tc.cli import register
from tc.config import load_env
from tc.http import HttpError, get_json, post_bytes

API = "https://www.mixamo.com/api/v1"
OUT = Path(os.environ.get("TC_MOCAP", "C:/Users/User/tools/mocap")) / "mixamo"
FILM_SET = [
    "Breathing Idle", "Talking", "Arguing", "Pointing", "Thoughtful Head Shake", "Looking Around", "Sad Idle",
    "Angry Gesture", "Walking", "Sad Walk", "Kneeling Idle", "Stand To Kneel", "Sitting Idle", "Sitting Talking",
    "Stand To Sit", "Quick Formal Bow", "Sword And Shield Idle", "Sword And Shield Slash", "Sword And Shield Block",
    "Sword And Shield Walk", "Stabbing", "Run Forward", "Hit Reaction", "Falling Back Death", "Cheering",
]


def export_body(character_id: str, name: str, gms: dict) -> dict:
    """The export request: FBX, no skin (motion only), 30 fps, no keyframe reduction (full motion detail)."""
    g = dict(gms)
    g["params"] = ",".join(str(p[1]) for p in gms.get("params", []))
    return {"character_id": character_id, "gms_hash": [g], "product_name": name, "type": "Motion",
            "preferences": {"format": "fbx7_2019", "skin": "false", "fps": "30", "reducekf": "0"}}


def best_match(query: str, results: list[dict]):
    if not results:
        return None
    for r in results:
        if r.get("name", "").strip().lower() == query.strip().lower():
            return r
    return results[0]


def file_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") + ".fbx"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "X-Api-Key": "mixamo2", "Accept": "application/json",
            "Content-Type": "application/json"}


def download(names: list[str], token: str, out: Path = OUT) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    h = _headers(token)
    cid = get_json(f"{API}/characters/primary", h)["primary_character_id"]
    done = []
    for name in names:
        dest = out / file_name(name)
        if dest.exists():
            print("have", dest.name); done.append(name); continue
        res = get_json(f"{API}/products?page=1&limit=24&type=Motion&query={quote(name)}", h).get("results", [])
        hit = best_match(name, res)
        if hit is None:
            print("NOT FOUND", name); continue
        prod = get_json(f"{API}/products/{hit['id']}?similar=0&character_id={cid}", h)
        gms = prod["details"]["gms_hash"]
        status, body, _ = post_bytes(f"{API}/animations/export", json.dumps(export_body(cid, hit["name"], gms)).encode(), h)
        if not 200 <= status < 300:
            print("EXPORT FAILED", name, status); continue
        url = None
        for _ in range(60):                                   # the export job takes a few seconds
            time.sleep(2)
            mon = get_json(f"{API}/characters/{cid}/monitor", h)
            if mon.get("status") == "completed":
                url = mon.get("job_result"); break
            if mon.get("status") == "failed":
                break
        if not url:
            print("EXPORT TIMEOUT", name); continue
        import subprocess
        r = subprocess.run(["curl", "-s", "-f", "-L", "--max-time", "300", "-o", str(dest), url], capture_output=True)
        if r.returncode != 0 or not dest.exists():
            print("DOWNLOAD FAILED", name); continue
        print("ok", hit["name"], "->", dest.name); done.append(name)
    return done


def _args(p):
    p.add_argument("names", nargs="*", help="motion names (default: the film set)")


@register("mixamo", "download Mixamo motions (needs MIXAMO_TOKEN in .env) into tools/mocap/mixamo", _args)
def _cmd_mixamo(args) -> int:
    token = load_env().get("MIXAMO_TOKEN") or os.environ.get("MIXAMO_TOKEN")
    if not token:
        print("No MIXAMO_TOKEN in .env (log in on mixamo.com, Console: copy(localStorage.access_token))")
        return 2
    names = args.names or FILM_SET
    try:
        got = download(names, token)
    except HttpError as e:
        print("Mixamo refused the request (token expired? log in again and copy a new one):", e.status)
        return 1
    print(f"{len(got)}/{len(names)} motions in {OUT}")
    return 0 if len(got) == len(names) else 1

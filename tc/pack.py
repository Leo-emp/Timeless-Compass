# `tc pack <job>`: the UPLOAD PACK (spec 6.11, rule r22) - everything the owner needs to upload by hand in ~2 min:
#   packs/<id>/video.mp4  thumbnail_a.jpg  thumbnail_b.jpg  title.txt  description.txt  tags.txt  posting.txt
# The pack is always built locally. It goes to R2 (packs/<id>/...) and one Telegram message is sent ONLY when the
# Timeless Compass keys are in .env (TC_R2_ACCOUNT_ID, TC_R2_ACCESS_KEY_ID, TC_R2_SECRET_ACCESS_KEY, TC_R2_BUCKET,
# TC_TELEGRAM_BOT_TOKEN, TC_TELEGRAM_CHAT_ID). Timeless Compass never uses CapitalCode or Luminous Will buckets.
# Secret values are never written into the pack or printed.
#   python -m tc pack <job>
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tc.cli import register
from tc.paths import ROOT

FILES = ["video.mp4", "thumbnail_a.jpg", "thumbnail_b.jpg", "title.txt", "description.txt", "tags.txt", "posting.txt"]
R2_KEYS = ["TC_R2_ACCOUNT_ID", "TC_R2_ACCESS_KEY_ID", "TC_R2_SECRET_ACCESS_KEY", "TC_R2_BUCKET"]
LONG_SLOTS = (1, 5)          # Tuesday, Saturday (weekday numbers) at 17:00 UTC - the spec's starting cadence (section 10)
LONG_HOUR, SHORT_HOUR = 17, 15


def _job(d: Path) -> dict:
    return json.loads((d / "job.json").read_text(encoding="utf-8"))


def _upload(d: Path) -> dict:
    """upload.json, written by the agent: {"title", "description", "tags"} - the picked title and the base text."""
    return json.loads((d / "upload.json").read_text(encoding="utf-8"))


def pack_problems(d: Path) -> list[str]:
    probs = []
    master, mix = d / "master.mp4", d / "mix.wav"
    if not master.exists():
        probs.append("no master.mp4 (run tc produce)")
    elif mix.exists() and master.stat().st_mtime < mix.stat().st_mtime:
        probs.append("master.mp4 is older than mix.wav (stale master: run tc produce)")
    for v in "ab":
        if not (d / "thumb" / f"thumbnail_{v}.jpg").exists():
            probs.append(f"no thumb/thumbnail_{v}.jpg (run tc thumb)")
    qa = d / "qa" / "thumbnail.json"
    entries = json.loads(qa.read_text(encoding="utf-8")).values() if qa.exists() else []
    if not entries or not all(e.get("passed") for e in entries):
        probs.append("the thumbnail checklist has not passed (tc qa <id> thumbnail)")
    if not (d / "upload.json").exists():
        probs.append("no upload.json (title, description base, tags)")
    else:
        u = _upload(d)
        for k in ("title", "description", "tags"):
            if not u.get(k):
                probs.append(f"upload.json has no {k}")
    return probs


def description(d: Path) -> str:
    """Base text + a de-duplicated source list + the r12 note when the script has dramatised lines."""
    from tc.packaging import build_description
    base = _upload(d)["description"].strip()
    cites: list[str] = []
    src = d / "sources.json"
    if src.exists():
        for fact in json.loads(src.read_text(encoding="utf-8")).values():
            for c in fact.get("cites", []):
                if c not in cites:
                    cites.append(c)
    text = base
    if _job(d).get("kind") == "short":
        text += "\n\n#Shorts #history"
    if cites:
        text += "\n\nSources:\n" + "\n".join(f"- {c}" for c in cites)
    return build_description(text, (d / "script.md").read_text(encoding="utf-8"))


def posting_slot(kind: str, now: datetime) -> str:
    """Next posting time (UTC). Long: next Tue or Sat 17:00. Short: tomorrow 15:00. The results loop tunes these."""
    now = now.astimezone(timezone.utc)
    if kind == "short":
        t = (now + timedelta(days=1)).replace(hour=SHORT_HOUR, minute=0, second=0, microsecond=0)
    else:
        t = now.replace(hour=LONG_HOUR, minute=0, second=0, microsecond=0)
        while t.weekday() not in LONG_SLOTS or t <= now:
            t = (t + timedelta(days=1)).replace(hour=LONG_HOUR)
    return t.strftime("%Y-%m-%d %H:%M UTC (%A)")


def build_pack(d: Path, out_root: Path, now: datetime | None = None) -> Path:
    job, up = _job(d), _upload(d)
    out = Path(out_root) / d.name
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(d / "master.mp4", out / "video.mp4")
    for v in "ab":
        shutil.copyfile(d / "thumb" / f"thumbnail_{v}.jpg", out / f"thumbnail_{v}.jpg")
    (out / "title.txt").write_text(up["title"].strip() + "\n", encoding="utf-8")
    (out / "description.txt").write_text(description(d) + "\n", encoding="utf-8")
    (out / "tags.txt").write_text(", ".join(up["tags"]) + "\n", encoding="utf-8")
    slot = posting_slot(job.get("kind", "long"), now or datetime.now(timezone.utc))
    if job.get("kind") == "short":
        # YouTube Shorts: no A/B thumbnail test; the cover is usually a frame picked in the app
        cover = up.get("cover_frame", "the most striking moment")
        thumbs = ("Cover: Shorts use a frame from the video - pick the frame at " + cover + ". If your app offers "
                  "'upload thumbnail', use thumbnail_a.jpg (thumbnail_b.jpg is the backup).\n"
                  "Upload as a Short (vertical, under 3 minutes).\n")
    else:
        thumbs = "Thumbnails: upload thumbnail_a.jpg; add thumbnail_b.jpg in YouTube 'Test & Compare' (A/B).\n"
    (out / "posting.txt").write_text(f"Post: {slot}\n" + thumbs, encoding="utf-8")
    return out


def r2_config(env: dict) -> dict | None:
    if not all(env.get(k) for k in R2_KEYS):
        return None
    return {k: env[k] for k in R2_KEYS}


def upload_pack(pack_dir: Path, cfg: dict) -> str:
    import boto3
    s3 = boto3.client("s3", endpoint_url=f"https://{cfg['TC_R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                      aws_access_key_id=cfg["TC_R2_ACCESS_KEY_ID"], aws_secret_access_key=cfg["TC_R2_SECRET_ACCESS_KEY"],
                      region_name="auto")
    for p in sorted(pack_dir.iterdir()):
        s3.upload_file(str(p), cfg["TC_R2_BUCKET"], f"packs/{pack_dir.name}/{p.name}")
    return f"r2://{cfg['TC_R2_BUCKET']}/packs/{pack_dir.name}/"


def notify(text: str, env: dict) -> bool:
    """One Telegram message; False (and nothing sent) when the TC bot keys are missing."""
    tok, chat = env.get("TC_TELEGRAM_BOT_TOKEN"), env.get("TC_TELEGRAM_CHAT_ID")
    if not tok or not chat:
        return False
    # sent from Python (not curl): the token is part of the URL and must never sit on a process command line
    import urllib.request
    body = json.dumps({"chat_id": chat, "text": text}).encode("utf-8")
    req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except Exception:                                    # no details: an error message could echo the URL (token)
        return False


def make_pack(job_id: str) -> int:
    import os
    from tc import jobs
    from tc.config import load_env
    d = jobs.job_dir(job_id)
    probs = pack_problems(d)
    if probs:
        for p in probs:
            print("pack: problem:", p)
        return 1
    out = build_pack(d, ROOT / "packs")
    print(f"pack built -> {out}")
    env = {**load_env(), **{k: v for k, v in os.environ.items() if k.startswith("TC_")}}
    where = str(out)
    cfg = r2_config(env)
    if cfg:
        try:
            where = upload_pack(out, cfg)
            print("uploaded ->", where)
        except Exception as e:                       # never print the config: the message names the failure type only
            print(f"pack: R2 upload failed ({type(e).__name__}); the pack is kept locally at {out}")
            return 1
    else:
        print("R2 keys for Timeless Compass are not set: the pack is kept locally (owner step: add TC_R2_* to .env)")
    title = (out / "title.txt").read_text(encoding="utf-8").strip()
    slot = (out / "posting.txt").read_text(encoding="utf-8").splitlines()[0]
    if notify(f"Timeless Compass pack ready: {title}\n{where}\n{slot}", env):
        print("Telegram: sent")
    else:
        print("Telegram: not sent (TC_TELEGRAM_* not set)")
    return 0


def _args(p):
    p.add_argument("job")


@register("pack", "build the upload pack (video, 2 thumbnails, title, description+sources, tags, posting slot)", _args)
def _cmd_pack(args) -> int:
    return make_pack(args.job)


if __name__ == "__main__":
    sys.exit(make_pack(sys.argv[1]))

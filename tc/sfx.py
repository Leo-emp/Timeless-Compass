# Sound effects + ambience: where sounds come from (with the licence rules), the local library, and the
# LAYERED sound design for every shot.
#
# ---- Sources (docs/BACKLOG.md WS11) ----
#   Sonniss GDC bundles  best quality, royalty free, no credit. Huge zips: download ONLY the categories needed,
#                        then register each file with  tc sfx add <file> --source sonniss --licence "Sonniss GDC"
#   Pixabay SFX          free for commercial use, no credit (no API for sounds: download by hand, then tc sfx add)
#   The Beat / PremiumBeat free packs   royalty free, no credit (by hand, then tc sfx add)
#   Freesound            automatic:  tc sfx fetch "<query>" --tags a,b   (needs FREESOUND_API_KEY in .env)
#                        ONLY CC0 or CC-BY. NEVER CC-BY-NC (non-commercial), never ND (we cut and mix sounds),
#                        never Sampling+. CC-BY sounds get a credit line (goes in the video description).
#   The licence of EVERY sound is checked again here (licence_verdict), even when the API filter already did it.
#
# ---- Library ----
#   library/sfx/index.json        the catalogue (committed): id, tags, source, licence, credit, duration
#   library/sfx/files/<id>.<ext>  the audio (git-ignored; capped at TC_SFX_CAP_MB, default 600 MB)
#
# ---- Sound design ----
# A shot lists events in its "sfx" field (shots.json), e.g. ["march"] or ["oars", "amb:sea"].
#   - an event in RECIPES becomes several LAYERS (a march = steps + armour + spears + chant + wind), each from
#     the library by tags, each at its own level, starting a little apart so they don't hit at once
#   - "amb:<name>" sets the shot's ambience bed; otherwise the set ("where") chooses one (cove -> sea)
#   - any other word is looked up directly by tags ("door creak")
# Ambience beds run under consecutive shots with the same ambience and crossfade into the next bed.
# Whatever the library is missing goes to plan["missing"]: the list of things to fetch.
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import urllib.parse
from pathlib import Path

from tc import jobs, paths
from tc.cli import register
from tc.config import load_env
from tc.http import _curl, get_json
from tc.mix import measure_lufs

FREESOUND = "https://freesound.org/apiv2/search/text/"
CAP_BYTES = int(float(os.environ.get("TC_SFX_CAP_MB", "600")) * 1024 ** 2)
XFADE_S = 1.0                 # ambience beds crossfade this long into the next bed
AMBIENCE_DB = -20.0           # ambience sits well under the voice (the mix ducks it further)


class SfxError(Exception):
    pass


def _root(root=None) -> Path:
    return Path(root or paths.LIBRARY / "sfx")


# ================= licence rules =================
def licence_verdict(licence: str) -> dict:
    """{"ok": may we use it, "credit": must we credit it, "name": short licence name}. Unknown = refused."""
    l = (licence or "").lower().replace("_", "-")
    if re.search(r"(^|[^a-z])nc([^a-z]|$)|noncommercial|non-commercial", l):
        return {"ok": False, "credit": False, "name": "non-commercial (never)"}
    if re.search(r"(^|[^a-z])nd([^a-z]|$)|noderiv|no-deriv", l):
        return {"ok": False, "credit": False, "name": "no-derivatives (we cut + mix sounds)"}
    if "sampling" in l:
        return {"ok": False, "credit": False, "name": "sampling+ (refused)"}
    if "zero" in l or "cc0" in l or "commons 0" in l or "publicdomain" in l or "public domain" in l:
        return {"ok": True, "credit": False, "name": "CC0"}
    if "creativecommons.org/licenses/by/" in l or l.strip() in ("attribution", "cc-by", "cc by") or l.startswith("attribution "):
        return {"ok": True, "credit": True, "name": "CC BY"}
    for free in ("pixabay", "sonniss", "premiumbeat", "the beat", "youtube audio library"):
        if free in l:
            return {"ok": True, "credit": False, "name": free}
    return {"ok": False, "credit": False, "name": "unknown (refused)"}


# ================= Freesound =================
def freesound_search(query: str, key: str | None, get=get_json, max_s: float = 60.0, min_s: float = 0.3,
                     page_size: int = 15) -> list[dict]:
    """Search Freesound for CC0 / CC-BY sounds. The key goes in a header (tc.http writes it to a temp file)."""
    if not key:
        raise SfxError("FREESOUND_API_KEY missing in .env (owner task in docs/BACKLOG.md)")
    q = urllib.parse.urlencode({
        "query": query, "page_size": page_size, "sort": "rating_desc",
        "filter": f'license:("Creative Commons 0" OR "Attribution") duration:[{min_s:g} TO {max_s:g}]',
        "fields": "id,name,license,username,duration,previews,tags,url,avg_rating,num_ratings,num_downloads"})
    data = get(f"{FREESOUND}?{q}", headers={"Authorization": f"Token {key}"}, timeout=60)
    return [r for r in data.get("results", []) if licence_verdict(r.get("license", ""))["ok"]]


def _credit_line(r: dict) -> str:
    v = licence_verdict(r["license"])
    return f'"{r["name"]}" by {r["username"]} (freesound.org/s/{r["id"]}) - {v["name"]}' if v["credit"] else ""


def fetch_freesound(query: str, tags: list[str], key: str | None, root=None, n: int = 1, get=get_json,
                    download=None) -> list[dict]:
    """Search + download the top n previews (HQ mp3, free without OAuth) into the library."""
    download = download or (lambda url: _curl(url, None, None, 120, subprocess.run))
    added = []
    for r in freesound_search(query, key, get=get)[:n]:
        status, data, _ = download(r["previews"]["preview-hq-mp3"])
        if status != 200 or not data:
            continue
        tmp = _root(root) / f"_dl_{r['id']}.mp3"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(data)
        try:
            added.append(add_sound(tmp, tags or r.get("tags", [])[:6], "freesound", r["license"], root=root,
                                   credit=_credit_line(r), url=f"https://freesound.org/s/{r['id']}/"))
        finally:
            tmp.unlink(missing_ok=True)
    return added


# ================= curated library build (library/sfx/wanted.json) =================
# Quality first: the API's "rating_desc" puts a single lucky 5-star first. We rank instead by a rating that
# trusts many votes (Bayesian average), a little by downloads, prefer CC0 (no credit line), and drop
# franchise / fan recreations (sounds re-made from TV shows, films, games - not ours to use) and words the
# item excludes (an ancient battle must never get a rifle or a synth).
BANNED_NAMES = ("tmnt", "shredder", "star wars", "starwars", "lightsaber", "light saber", "minecraft", "zelda",
                "pokemon", "marvel", "halo", "mario", "fortnite", "skyrim", "witcher", "game of thrones",
                "lord of the rings", "lotr", "harry potter", "movie", "film rip", "trailer")
PRIOR_RATING, PRIOR_VOTES = 3.5, 5


def _banned(name: str, exclude) -> bool:
    n = name.lower().replace("_", " ").replace("-", " ")
    return any(w in n for w in BANNED_NAMES) or any(w.lower() in n for w in exclude or [])


def _on_topic(r: dict, require) -> bool:
    """At least one required word in the sound's NAME (a 'door' search can return piano pedals; uploader tags are
    too loose to trust - "digital wildfire" is tagged fire)."""
    if not require:
        return True
    text = r.get("name", "").lower().replace("_", " ")
    return any(w.lower() in text for w in require)


def rank(results: list[dict], exclude=None, require=None, reject=None) -> list[dict]:
    """Best first. Score = Bayesian rating (many 4.6 votes beat one 5) + log downloads + a CC0 bonus."""
    def score(r):
        n, avg = r.get("num_ratings") or 0, r.get("avg_rating") or 0
        bayes = (avg * n + PRIOR_RATING * PRIOR_VOTES) / (n + PRIOR_VOTES)
        cc0 = 0.15 if not licence_verdict(r.get("license", ""))["credit"] else 0.0
        return bayes + 0.1 * math.log10(1 + (r.get("num_downloads") or 0)) + cc0
    keep = [r for r in results
            if licence_verdict(r.get("license", ""))["ok"] and not _banned(r.get("name", ""), exclude)
            and _on_topic(r, require) and r.get("id") not in set(reject or [])]
    return sorted(keep, key=score, reverse=True)


def load_wanted(path=None, only=None) -> list[dict]:
    """library/sfx/wanted.json items, each with its own excludes + the common ones (unless exclude_common false)."""
    f = Path(path) if path else _root(None) / "wanted.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    out = []
    for w in data["wanted"]:
        if only and w["name"] not in only:
            continue
        common = data.get("common_exclude", []) if w.get("exclude_common", True) else []
        out.append(dict(w, exclude=list(dict.fromkeys(common + w.get("exclude", []))),
                        reject=data.get("reject_ids", [])))      # ids a human listened to and refused
    return out


def build_library(wanted: list[dict], key: str | None, root=None, get=get_json, download=None, log=print) -> list[dict]:
    """For every wanted item: search Freesound in its length range, rank, add the best n we do not have yet
    (with the item's tags, mood and intensity). Safe to run again: known Freesound ids are skipped."""
    download = download or (lambda url: _curl(url, None, None, 120, subprocess.run))
    report = []
    for w in wanted:
        sounds = load_index(root)["sounds"]
        have = {s.get("freesound_id") for s in sounds}
        n_have = sum(1 for s in sounds if s.get("wanted") == w["name"])
        need = max(0, int(w.get("n", 1)) - n_have)
        added = 0
        if need:
            pool = {}
            for q in [w["query"], *w.get("also", [])]:          # extra queries widen a thin search
                for r in freesound_search(q, key, get=get, min_s=w.get("min_s", 0.3), max_s=w.get("max_s", 60.0),
                                          page_size=30):
                    pool.setdefault(r["id"], r)
            found = rank(list(pool.values()), w.get("exclude"), w.get("require"), w.get("reject"))
            for r in found:
                if added >= need:
                    break
                if r["id"] in have:
                    continue
                status, data, _ = download(r["previews"]["preview-hq-mp3"])
                if status != 200 or not data:
                    continue
                tmp = _root(root) / f"_dl_{r['id']}.mp3"
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_bytes(data)
                try:
                    e = add_sound(tmp, w["tags"], "freesound", r["license"], root=root, credit=_credit_line(r),
                                  url=f"https://freesound.org/s/{r['id']}/", mood=w.get("mood"),
                                  intensity=w.get("intensity"), freesound_id=r["id"])
                finally:
                    tmp.unlink(missing_ok=True)
                idx = load_index(root)
                for s in idx["sounds"]:
                    if s["id"] == e["id"]:
                        s["wanted"], s["name"] = w["name"], r.get("name", "")
                _save_index(idx, root)
                have.add(r["id"])
                added += 1
        report.append({"name": w["name"], "added": added, "had": n_have})
        if log:
            log(f"{w['name']:<22} +{added} (had {n_have}, want {w.get('n', 1)})")
    return report


# ================= the local library =================
def load_index(root=None) -> dict:
    f = _root(root) / "index.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"sounds": []}


def _save_index(idx: dict, root=None) -> None:
    f = _root(root) / "index.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(idx, indent=2, ensure_ascii=False), encoding="utf-8")


def _duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return round(float(r.stdout.strip()), 3)


def add_sound(src: Path, tags: list[str], source: str, licence: str, root=None, credit: str = "", url: str = "",
              mood: list[str] | None = None, intensity: int | None = None, freesound_id: int | None = None) -> dict:
    """Copy one sound into the library after the licence check. CC-BY sounds must come with a credit line."""
    v = licence_verdict(licence)
    if not v["ok"]:
        raise SfxError(f"licence {licence!r} not allowed ({v['name']}): only CC0, CC-BY, Pixabay, Sonniss, PremiumBeat")
    if v["credit"] and not credit.strip():
        raise SfxError("a CC-BY sound needs a credit line (--credit '\"name\" by user (link) - CC BY 4.0')")
    root = _root(root)
    files = root / "files"
    size = Path(src).stat().st_size
    used = sum(p.stat().st_size for p in files.glob("*")) if files.exists() else 0
    if used + size > CAP_BYTES:
        raise SfxError(f"sfx library would pass its {CAP_BYTES // 1024 ** 2} MB cap (disk is nearly full)")
    sid = re.sub(r"[^a-z0-9]+", "_", "_".join(tags[:3]).lower()).strip("_") + "_" + \
        (f"fs{freesound_id}" if freesound_id else hashlib.sha1(Path(src).read_bytes()).hexdigest()[:6])
    files.mkdir(parents=True, exist_ok=True)
    dest = files / f"{sid}{Path(src).suffix.lower()}"
    shutil.copyfile(src, dest)
    idx = load_index(root)
    idx["sounds"] = [s for s in idx["sounds"] if s["id"] != sid]
    entry = {"id": sid, "file": dest.name, "tags": [t.lower() for t in tags], "source": source, "licence": licence,
             "licence_name": v["name"], "credit": credit, "url": url, "duration_s": _duration(dest),
             "lufs": measure_lufs(dest)}         # the mix uses this to level every sound to the voice
    if mood:
        entry["mood"] = [m.lower() for m in mood]       # e.g. tense / violent / calm / grand / sad
    if intensity is not None:
        entry["intensity"] = int(intensity)             # 1 (soft, distant) .. 5 (huge, close)
    if freesound_id:
        entry["freesound_id"] = int(freesound_id)       # so a rebuild never downloads it twice
    idx["sounds"].append(entry)
    _save_index(idx, root)
    return entry


def credits(sound_ids: list[str], idx: dict) -> list[str]:
    """Credit lines (CC-BY only) for the sounds a video used, each once, in first-use order."""
    by_id = {s["id"]: s for s in idx["sounds"]}
    out = []
    for i in sound_ids:
        c = by_id.get(i, {}).get("credit")
        if c and c not in out:
            out.append(c)
    return out


# ================= layered sound design =================
def _L(tags, db, loop=True, delay=0.0):
    return {"tags": tags, "db": db, "loop": loop, "delay": delay}


# event -> layers. db = level of the layer before the final mix (0 = the main layer).
RECIPES = {
    "march":       [_L(["footsteps", "march"], -6), _L(["armour", "clank"], -10, delay=0.2),
                    _L(["spear", "rattle"], -14, delay=0.4), _L(["chant", "men"], -16, loop=False, delay=0.8),
                    _L(["wind"], -20)],
    "battle":      [_L(["battle", "crowd"], -6), _L(["sword", "clash"], -8, delay=0.1),
                    _L(["shield", "hit"], -10, delay=0.3), _L(["shout", "war"], -12, loop=False, delay=0.5),
                    _L(["arrow", "whoosh"], -14, delay=0.7)],
    "rowing":      [_L(["oars", "rowing"], -6), _L(["water", "splash"], -10, delay=0.2),
                    _L(["wood", "creak"], -14, delay=0.4), _L(["drum", "rhythm"], -14, delay=0.0)],
    "ship_ram":    [_L(["wood", "crash"], -4, loop=False), _L(["water", "splash"], -8, loop=False, delay=0.1),
                    _L(["shout", "men"], -12, loop=False, delay=0.4)],
    "fire":        [_L(["fire", "crackle"], -6), _L(["fire", "roar"], -12), _L(["wood", "burning"], -14, delay=0.5)],
    "city_burning": [_L(["fire", "roar"], -6), _L(["building", "collapse"], -10, loop=False, delay=1.0),
                    _L(["crowd", "scream"], -16, loop=False, delay=0.6), _L(["wind"], -18)],
    "crowd":       [_L(["crowd", "walla"], -8), _L(["footsteps", "crowd"], -14)],
    "council":     [_L(["crowd", "murmur"], -12), _L(["room", "tone"], -20)],
    "sword_fight": [_L(["sword", "clash"], -6, loop=False), _L(["footsteps", "scuffle"], -12),
                    _L(["breath", "grunt"], -14, loop=False, delay=0.3)],
    "horse":       [_L(["horse", "hooves"], -6), _L(["horse", "snort"], -14, loop=False, delay=0.6)],
    "door":        [_L(["door", "wood"], -8, loop=False)],
    "writing":     [_L(["quill", "writing"], -10), _L(["room", "tone"], -20)],
    # the battle + film library (2026-11-20)
    "arrow_volley": [_L(["arrow", "whoosh"], -6, loop=False), _L(["arrow", "impact"], -8, loop=False, delay=1.2),
                     _L(["bow", "release"], -12, loop=False)],
    "cannon":      [_L(["cannon", "boom"], -2, loop=False), _L(["cannon", "echo"], -10, loop=False, delay=0.25),
                    _L(["debris", "falling"], -14, loop=False, delay=0.8)],
    "cavalry":     [_L(["horse", "gallop"], -4), _L(["horse", "whinny"], -12, loop=False, delay=0.8),
                    _L(["armour", "clank"], -14, delay=0.3), _L(["shout", "war"], -14, loop=False, delay=1.5)],
    "war_cry":     [_L(["war", "cry"], -4, loop=False), _L(["battle", "crowd"], -12)],
    "shield_wall": [_L(["shield", "clash"], -4, loop=False), _L(["footsteps", "march"], -10),
                    _L(["spear", "rattle"], -14, delay=0.3)],
    "horse_trot":  [_L(["horse", "trot"], -6), _L(["horse", "snort"], -14, loop=False, delay=1.0)],
    "ship":        [_L(["ship", "creak"], -8), _L(["water", "splash"], -14, delay=0.5)],
}

AMBIENCES = {"sea": ["sea", "waves"], "wind": ["wind"], "crowd_walla": ["crowd", "walla"], "fire": ["fire", "crackle"],
             "night": ["night", "crickets"], "harbour": ["harbour", "water"], "camp": ["camp", "fire"],
             "interior": ["room", "tone"], "rain": ["rain"], "storm": ["storm", "thunder"]}

# words in a shot's "where" -> default ambience (first match wins)
SET_AMBIENCE = [(("cove", "beach", "shore", "sea", "salamis", "bay", "strait"), "sea"),
                (("harbour", "harbor", "port", "dock", "piraeus"), "harbour"),
                (("camp", "tent"), "camp"), (("agora", "market", "street", "city"), "crowd_walla"),
                (("hall", "palace", "temple", "house", "room", "interior", "courtyard"), "interior"),
                (("mountain", "pass", "cliff", "hill", "aigaleos", "thermopylae"), "wind")]


# ================= free-text shot sfx -> recipe or tags =================
# Claude writes shot sfx as plain phrases ("roaring fire", "oars in unison", "a cart wheel"). resolve() turns one into
#   a RECIPES key (a layered event), a tag list (one library sound), or None (silence = no sound at all).
# PHRASES holds every phrase the scripts used so far; anything new goes through the word fallback below.
PHRASES = {
    "silence": None, "crowd falls silent": ["crowd", "murmur"],
    "ram impact": "ship_ram", "impact": "ship_ram", "roaring fire": "fire", "fire": "fire",
    "oars": "rowing", "oars in unison": "rowing", "rhythm of oars": "rowing", "thousands of oars": "rowing",
    "oar dip and pull": ["oars", "rowing"], "oars running out": ["oars", "rowing"],
    "a sword drawn": ["sword", "draw"], "a cart wheel": ["cart", "wheel"], "a child crying": ["child", "crying"],
    "a cry carried by the wind": ["war", "cry"], "a quiet prayer": ["whisper", "prayer"], "whispers": ["whisper"],
    "a single drum beat": ["drum", "hit"], "drum beat": ["drum", "rhythm"], "drums": ["drum", "rhythm"],
    "anxious voices": ["voices", "talk"], "arguing voices": ["voices", "talk"], "raised voices": ["voices", "talk"],
    "voices": ["voices", "talk"], "distant persian voices": ["voices", "talk"],
    "orders": ["shout", "men"], "shouted orders in persian": ["shout", "men"], "men shouting": ["shout", "men"],
    "chaos of shouting": ["shout", "men"], "paean chant": ["chant", "men"],
    "banners flapping": ["flag", "flapping"], "birdsong": ["birds"], "morning birds": ["birds"],
    "bow wave": ["boat", "water", "rush"], "water over bronze": ["boat", "water", "rush"],
    "cloth tearing": ["cloth", "tear"], "creaking timber": ["wood", "creak"], "hull grinding hull": ["wood", "creak"],
    "rigging creak": ["rope", "creak"], "rope creak": ["rope", "creak"],
    "crowd murmur": ["crowd", "murmur"], "distant town": ["crowd", "walla"],
    "distant fire": ["fire", "crackle"], "distant fire crackle": ["fire", "crackle"], "embers ticking": ["fire", "crackle"],
    "distant screams": ["crowd", "scream"], "screams": ["crowd", "scream"],
    "fist on table": ["table", "bang"], "flute keeping time": ["flute"],
    "footsteps": ["footsteps"], "footsteps on planks": ["footsteps", "wood"], "guards' steps": ["footsteps", "march"],
    "goat bells": ["goat", "bells"], "grunts": ["breath", "grunt"], "heavy breathing": ["breath", "heavy"],
    "hammering": ["hammer"], "lapping water": ["harbour", "water"], "water": ["water"],
    "low hum of the chamber": ["room", "tone"], "room tone": ["room", "tone"],
    "mountain wind": ["wind"], "wind": ["wind"], "wind on the hill": ["wind"], "sea wind": ["wind"],
    "night surf": ["sea", "waves"], "sea": ["sea", "waves"],
    "oars snapping": ["wood", "crash"], "splintering hull": ["wood", "crash"], "timber collapse": ["wood", "crash"],
    "timber crash": ["wood", "crash"], "timber splitting": ["wood", "crash"],
    "oil lamp flicker": ["lamp", "flame"], "oil lamp hiss": ["lamp", "flame"],
    "regulator bubbles": ["underwater", "bubbles"], "underwater rumble": ["underwater", "rumble"],
    "scrabbling stones": ["stone", "scrape"], "stylus on wax": ["quill", "writing"], "stylus scratch": ["quill", "writing"],
    "torches flaring": ["torch", "fire"],
}
STOP_WORDS = {"a", "an", "the", "of", "on", "in", "by", "and", "with", "distant", "single", "quiet", "little",
              "many", "some", "far", "off", "loud", "soft", "big", "small", "thousands"}
WORD_TAGS = {"timber": ["wood"], "planks": ["wood"], "splintering": ["crash"], "splitting": ["crash"],
             "snapping": ["crash"], "breaking": ["crash"], "roaring": ["roar"], "screams": ["crowd", "scream"],
             "screaming": ["crowd", "scream"], "shouting": ["shout", "men"], "shouts": ["shout", "men"],
             "steps": ["footsteps"], "creaking": ["creak"], "birds": ["birds"], "waves": ["sea", "waves"],
             "crackling": ["crackle"], "flames": ["fire"], "swords": ["sword"], "arrows": ["arrow"]}


def resolve(phrase: str):
    """A shot's sfx phrase -> RECIPES key | [tags] | None (silence)."""
    p = phrase.strip().lower()
    if p in PHRASES:
        return PHRASES[p]
    if p in RECIPES:
        return p
    tags = []
    for w in re.findall(r"[a-z']+", p):
        if w in STOP_WORDS:
            continue
        for t in WORD_TAGS.get(w, [w]):
            if t not in tags:
                tags.append(t)
    return tags or None


def shot_intensity(shot: dict) -> int | None:
    """The shot's intensity 1-5: its own field, else the strongest acted performance in it (VISUAL_STANDARD sec 4)."""
    if shot.get("intensity"):
        return int(shot["intensity"])
    vals = [int(v["intensity"]) for v in (shot.get("performance") or {}).values()
            if isinstance(v, dict) and v.get("intensity")]
    return max(vals) if vals else None


def pick(tags: list[str], idx: dict, salt: int = 0, intensity: int | None = None) -> dict | None:
    """The library sound matching the most tags (all asked tags must match). Ties are rotated by salt,
    so the same event in different shots uses different recordings (no audible copy-paste).
    With the shot's intensity (1-5) only the sounds closest to it stay in the tie (a skirmish gets the
    small sword clash, the climax the huge one)."""
    want = {t.lower() for t in tags}
    hits = [s for s in idx.get("sounds", []) if want <= set(s.get("tags", []))]
    if not hits:
        return None
    best = max(len(set(s["tags"]) & want) for s in hits)
    tied = sorted((s for s in hits if len(set(s["tags"]) & want) == best), key=lambda s: s["id"])
    if intensity is not None:
        gap = lambda s: abs(s.get("intensity", 3) - intensity)
        closest = min(gap(s) for s in tied)
        tied = [s for s in tied if gap(s) == closest]
    return tied[salt % len(tied)]


def _ambience_for(shot: dict) -> str:
    for e in shot.get("sfx") or []:
        if e.startswith("amb:"):
            return e[4:]
    w = (shot.get("where") or "").lower()
    for words, amb in SET_AMBIENCE:
        if any(x in w for x in words):
            return amb
    return "wind"


def design(shots: list[dict], idx: dict) -> dict:
    """Timed shots (shots.timed.json) -> {"events": [...], "ambience": [...], "missing": [[tags], ...]}."""
    events, missing, beds = [], [], []
    def need(tags):
        if tags not in missing:
            missing.append(tags)
    for k, s in enumerate(shots):
        at, dur = float(s.get("at") or 0), float(s.get("dur") or 0)
        for e in s.get("sfx") or []:
            if e.startswith("amb:"):
                continue
            r = resolve(e)
            if r is None:                         # "silence": a deliberate hole in the sound
                continue
            layers = RECIPES[r] if isinstance(r, str) else [_L(r, -8, loop=False)]
            for j, layer in enumerate(layers):
                snd = pick(layer["tags"], idx, salt=k + j, intensity=shot_intensity(s))
                if snd is None:
                    need(layer["tags"])
                    continue
                start = at + min(layer["delay"], dur / 2)
                length = (at + dur - start) if layer["loop"] else min(snd["duration_s"], at + dur - start)
                events.append({"shot": s["id"], "event": e, "sound": snd["id"], "at": round(start, 3),
                               "dur": round(length, 3), "db": layer["db"], "loop": layer["loop"],
                               "fade_in": 0.15, "fade_out": min(0.4, length / 3)})
        amb = _ambience_for(s)
        if beds and beds[-1]["ambience"] == amb and abs(beds[-1]["_end"] - at) < 0.05:
            beds[-1]["_end"] = at + dur
        else:
            beds.append({"ambience": amb, "at": at, "_end": at + dur})
    out_beds = []
    for i, b in enumerate(beds):
        snd = pick(AMBIENCES.get(b["ambience"], [b["ambience"]]), idx, salt=i)
        if snd is None:
            need(AMBIENCES.get(b["ambience"], [b["ambience"]]))
        last = i == len(beds) - 1
        dur = b["_end"] - b["at"] + (0 if last else XFADE_S)        # run on under the next bed: a crossfade
        out_beds.append({"ambience": b["ambience"], "sound": snd["id"] if snd else None, "at": round(b["at"], 3),
                         "dur": round(dur, 3), "db": AMBIENCE_DB, "loop": True,
                         "fade_in": 0.0 if i == 0 else XFADE_S, "fade_out": XFADE_S})
    return {"events": events, "ambience": out_beds, "missing": missing}


# ================= commands =================
def _args(p):
    sub = p.add_subparsers(dest="action", required=True)
    a = sub.add_parser("add", help="register a downloaded sound (Sonniss / Pixabay / PremiumBeat / Freesound)")
    a.add_argument("file"); a.add_argument("--tags", required=True); a.add_argument("--source", required=True)
    a.add_argument("--licence", required=True); a.add_argument("--credit", default=""); a.add_argument("--url", default="")
    f = sub.add_parser("fetch", help="search Freesound (CC0/CC-BY only) and add the best match")
    f.add_argument("query"); f.add_argument("--tags", default=""); f.add_argument("--n", type=int, default=1)
    b = sub.add_parser("build", help="fill the library from library/sfx/wanted.json (ranked, CC0/CC-BY, mood + intensity)")
    b.add_argument("--only", default="", help="comma list of wanted names")
    d = sub.add_parser("plan", help="layered sound design + ambience for a job -> jobs/<id>/sound.json")
    d.add_argument("job"); d.add_argument("--fetch", action="store_true", help="also fetch missing sounds from Freesound")


@register("sfx", "sound effects: add / fetch (licence-checked) / plan a job's sound design", _args)
def _cmd_sfx(args) -> int:
    try:
        if args.action == "add":
            e = add_sound(Path(args.file), [t.strip() for t in args.tags.split(",") if t.strip()], args.source,
                          args.licence, credit=args.credit, url=args.url)
            print(f"added {e['id']} ({e['licence_name']}, {e['duration_s']} s)")
            return 0
        key = load_env().get("FREESOUND_API_KEY")
        if args.action == "build":
            rep = build_library(load_wanted(only=[x for x in args.only.split(",") if x]), key)
            short = [r["name"] for r in rep if r["added"] + r["had"] == 0]
            print(f"library: {len(load_index()['sounds'])} sounds" + (f"; nothing found for {short}" if short else ""))
            return 0
        if args.action == "fetch":
            added = fetch_freesound(args.query, [t.strip() for t in args.tags.split(",") if t.strip()], key, n=args.n)
            for e in added:
                print(f"added {e['id']} ({e['licence_name']})" + (f"  credit: {e['credit']}" if e["credit"] else ""))
            return 0 if added else 1
        d = jobs.job_dir(args.job)
        f = d / "shots.timed.json"
        if not f.exists():
            print("No shots.timed.json yet: run  tc shots <id>  first")
            return 2
        shots = json.loads(f.read_text(encoding="utf-8"))["shots"]
        plan = design(shots, load_index())
        if args.fetch and plan["missing"]:
            for tags in plan["missing"]:
                print(f"fetching {' '.join(tags)} ...")
                fetch_freesound(" ".join(tags), tags, key)
            plan = design(shots, load_index())
        used = [e["sound"] for e in plan["events"]] + [b["sound"] for b in plan["ambience"] if b["sound"]]
        plan["credits"] = credits(used, load_index())
        (d / "sound.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
        print(f"{len(plan['events'])} sfx layers, {len(plan['ambience'])} ambience beds, {len(plan['missing'])} missing")
        for m in plan["missing"]:
            print("  missing:", " ".join(m))
        return 0
    except SfxError as e:
        print(e)
        return 1

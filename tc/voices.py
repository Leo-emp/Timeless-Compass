# CHARACTER VOICES (rule r26): every named character speaks in ONE Fish Audio voice, forever.
#   python -m tc voices search "deep old male"          find candidate public Fish voices (free model only)
#   python -m tc voices add <key> <reference_id> --use "who it is for"
# A reference_id may belong to only one key, so two characters never share a voice. The key is set as the
# "voice" of the character's sheet (library/characters/<id>/sheet.json). Never pick voices cloned from real
# actors, game or anime characters (library/voices.json note).
import json
from urllib.parse import quote

from tc import paths
from tc.cli import register
from tc.config import load_env
from tc.http import get_json

FISH_MODELS = "https://api.fish.audio/model"


def _file():
    return paths.LIBRARY / "voices.json"


def fish_search(query: str, api_key: str, get=get_json, page_size: int = 10) -> list[dict]:
    """Public Fish voices matching a title query; the key travels in a header, never in the URL."""
    data = get(f"{FISH_MODELS}?title={quote(query)}&page_size={page_size}", {"Authorization": f"Bearer {api_key}"}, timeout=60)
    return [{"id": m.get("_id"), "title": m.get("title"), "tags": m.get("tags", []), "languages": m.get("languages", [])}
            for m in data.get("items", [])]


def add_voice(key: str, reference_id: str, use: str) -> dict:
    data = json.loads(_file().read_text(encoding="utf-8"))
    chars = data.setdefault("characters", {})
    for k, v in chars.items():
        if v.get("reference_id") == reference_id and k != key:
            raise ValueError(f"reference_id {reference_id} is already used by {k} (one voice per character)")
    chars[key] = {"provider": "fish", "reference_id": reference_id, "use": use}
    _file().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return chars[key]


def _args(p):
    sub = p.add_subparsers(dest="action", required=True)
    a = sub.add_parser("search"); a.add_argument("query")
    a = sub.add_parser("add"); a.add_argument("key"); a.add_argument("reference_id"); a.add_argument("--use", required=True)


@register("voices", "character voices: search Fish voices, add one (one voice per character, r26)", _args)
def _cmd_voices(args) -> int:
    if args.action == "search":
        key = load_env().get("FISH_AUDIO_API_KEY")
        for m in fish_search(args.query, key):
            print(f"{m['id']}  {m['title'][:50]:50}  {','.join(m['languages'])}  {','.join(m['tags'][:5])}")
        return 0
    print(add_voice(args.key, args.reference_id, args.use))
    return 0

import json
from pathlib import Path

KEYS = {"hairstyle", "hair_length", "hair_texture", "hair_density", "hairline", "hair_colour",
        "beard_style", "beard_length", "beard_density", "moustache", "sideburns", "condition"}


def test_every_named_character_has_a_full_grooming_profile():
    for f in sorted(Path("library/cast").glob("*.json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        g = m.get("grooming")
        assert g, f"{f.stem}: no grooming profile"
        assert KEYS <= set(g), f"{f.stem}: missing {sorted(KEYS - set(g))}"
        assert g["hair_texture"] in ("straight", "wavy", "curly", "coily"), f.stem

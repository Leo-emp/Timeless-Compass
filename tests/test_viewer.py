# Tests for the fresh viewer review (`tc viewer`, rule r27): a separate agent hears only what a viewer hears.
from tc.viewer import check_verdict, is_go, viewer_packet

SCRIPT = """## cold_open
By sunset, two hundred ships would burn. [src: herodotus-8] {loop}
## world
Athens was ash. {beat} [src: herodotus-8]
XERXES (king): "Burn their city. Let them watch." [dramatised]
"""


def test_packet_has_no_tags_or_sections():
    p = viewer_packet(SCRIPT)
    for leak in ("##", "cold_open", "[src", "{loop}", "{beat}", "[dramatised]", "herodotus", "(king)"):
        assert leak not in p, leak
    assert "By sunset, two hundred ships would burn." in p
    assert 'XERXES: Burn their city. Let them watch.' in p
    assert "(pause)" in p


GOOD_NOGO = {"verdict": "NO-GO", "dropoffs": [{"at": "Athens was ash", "why": "too slow"}], "felt": ["bored"],
             "would_finish": False, "would_subscribe": False, "notes": "the middle drags"}


def test_valid_nogo():
    assert check_verdict(GOOD_NOGO) == [] and not is_go(GOOD_NOGO)


def test_go_with_a_dropoff_is_inconsistent():
    v = dict(GOOD_NOGO, verdict="GO", would_finish=True)
    assert any("GO" in p for p in check_verdict(v)) and not is_go(v)


def test_missing_field():
    v = dict(GOOD_NOGO); del v["would_subscribe"]
    assert any("would_subscribe" in p for p in check_verdict(v))


def test_clean_go():
    v = {"verdict": "GO", "dropoffs": [], "felt": ["gripped"], "would_finish": True, "would_subscribe": True, "notes": ""}
    assert check_verdict(v) == [] and is_go(v)

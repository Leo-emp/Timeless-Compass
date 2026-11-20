# Tests for the film-structure script format + checker.
from tc.config import Config
from tc.script import LONG_SECTIONS, check_script, parse_script

# These format tests were written for the old lengths; they pin them so they keep testing the format itself.
CFG = Config(long_words=(1500, 1800), short_words=(110, 150), short_rehook_max_s=600)
SOURCES = {"herodotus-8": {"title": "Histories VIII"}}


def make_script(words_per_section=230, loop_every=8, line_words=20, sources=True, order=LONG_SECTIONS):
    """A valid long script: 7 sections of ~230 words, 20-word lines, a {loop} every 8 lines."""
    out = []
    for sec in order:
        out.append(f"## {sec}")
        if sec == "title":
            continue
        n_lines = max(1, words_per_section // line_words)
        for i in range(n_lines):
            text = " ".join(["word"] * line_words) + "."
            tag = " [src: herodotus-8]" if sources else ""
            loop = " {loop}" if i % loop_every == loop_every - 1 else ""
            out.append(text + tag + loop)
    return "\n".join(out)


def test_parse_markers():
    lines = parse_script("## cold_open\nAt dawn the king sat. [src: a] {loop}\n")
    assert len(lines) == 1
    l = lines[0]
    assert l.section == "cold_open" and l.sources == ["a"] and l.loop and not l.beat
    assert l.text == "At dawn the king sat."


def test_fixture_passes():
    assert check_script(parse_script(make_script()), "long", SOURCES, CFG) == []


def test_section_order_enforced():
    order = list(LONG_SECTIONS); order[2], order[3] = order[3], order[2]
    problems = check_script(parse_script(make_script(order=order)), "long", SOURCES, CFG)
    assert any("section order" in p for p in problems)


def test_word_count_bounds_long():
    problems = check_script(parse_script(make_script(words_per_section=170)), "long", SOURCES, CFG)
    assert any("1500" in p for p in problems)


def test_rehook_gap():
    problems = check_script(parse_script(make_script(loop_every=14)), "long", SOURCES, CFG)
    assert any("225" in p for p in problems)


def test_unknown_source():
    problems = check_script(parse_script(make_script().replace("herodotus-8", "nope", 1)), "long", SOURCES, CFG)
    assert any("unknown source" in p and "nope" in p for p in problems)


def test_missing_source_in_factual_section():
    problems = check_script(parse_script(make_script(sources=False)), "long", SOURCES, CFG)
    assert any("no source" in p for p in problems)


def test_long_line_for_the_ear():
    problems = check_script(parse_script(make_script(line_words=31)), "long", SOURCES, CFG)
    assert any("too long for the ear" in p for p in problems)


# ---------------- character dialogue (rule r12) ----------------
# A short script helper: hook / build / payoff, every narrator line sourced, about 120 words in total.
def make_short(extra_build: str = "") -> str:
    narr = " ".join(["word"] * 19) + ". [src: herodotus-8]"
    out = ["## hook", narr, "## build", narr, narr, narr]
    if extra_build:
        out.append(extra_build)
    out += ["## payoff", narr, narr]
    return "\n".join(out)


def test_dramatised_line_parses_as_character():
    l = parse_script('## build\nXERXES: "Burn their city. Let them watch it from their ships."  [dramatised]\n')[0]
    assert l.speaker == "XERXES" and l.dramatised and l.quote_source is None
    assert l.spoken == "Burn their city. Let them watch it from their ships."
    # text keeps the NAME: "..." form (tc/dialogue.py reads it), the tag is removed
    assert l.text == 'XERXES: "Burn their city. Let them watch it from their ships."'


def test_real_quote_parses_with_free_text_source():
    l = parse_script('## build\nLEONIDAS: "Come and take them."  [source: Plutarch, Sayings of Spartans 225c]\n')[0]
    assert l.speaker == "LEONIDAS" and not l.dramatised
    assert l.quote_source == "Plutarch, Sayings of Spartans 225c"
    assert l.text == 'LEONIDAS: "Come and take them."'


def test_voice_key_in_brackets_is_kept():
    l = parse_script('## build\nSICINNUS (messenger): "The Greeks will run tonight." [dramatised]\n')[0]
    assert l.speaker == "SICINNUS" and l.voice_key == "messenger"


def test_narrator_line_has_no_speaker():
    l = parse_script("## build\nThe king sat on the hill. [src: h]\n")[0]
    assert l.speaker is None and not l.is_character and l.spoken == "The king sat on the hill."


def test_short_with_one_dramatised_line_passes():
    s = make_short('XERXES: "Burn it all." [dramatised]')
    assert check_script(parse_script(s), "short", SOURCES, CFG) == []


def test_dramatised_line_needs_no_src_even_in_factual_section():
    s = make_short('XERXES: "Burn it all." [dramatised]')
    assert not any("no source" in p for p in check_script(parse_script(s), "short", SOURCES, CFG))


def test_character_line_must_be_tagged():
    s = make_short('XERXES: "Burn it all."')
    assert any("[dramatised] or [source:" in p for p in check_script(parse_script(s), "short", SOURCES, CFG))


def test_character_line_cannot_be_both():
    s = make_short('XERXES: "Burn it all." [dramatised] [source: Herodotus 8.53]')
    assert any("both" in p for p in check_script(parse_script(s), "short", SOURCES, CFG))


def test_src_id_counts_as_real_quote_source():
    # [src: id] (a sources.json entry) is also accepted as the source of a real quote
    s = make_short('XERXES: "My men have become women." [src: herodotus-8]')
    assert check_script(parse_script(s), "short", SOURCES, CFG) == []


def test_no_fixed_limit_on_character_lines():
    # owner 2026-11-19: character lines wherever they fit and boost the vibe - no fixed cap
    five = "\n".join(['XERXES: "Burn it." [dramatised]'] * 5)
    problems = check_script(parse_script(make_short(five)), "short", SOURCES, CFG)
    assert not any("character lines" in p for p in problems)


def test_narrator_facts_still_need_sources():
    s = make_short("The fleet sailed at night.")      # narrator, factual section, no source
    assert any("no source" in p for p in check_script(parse_script(s), "short", SOURCES, CFG))


def test_word_limit_uses_spoken_words_only():
    # the speaker name is not spoken, so it does not count towards the 30-word ear limit
    line = 'XERXES: "' + " ".join(["w"] * 30) + '" [dramatised]'
    assert not any("too long" in p for p in check_script(parse_script(make_short(line)), "short", SOURCES, CFG))


def test_has_dramatised_helper():
    from tc.script import has_dramatised
    assert has_dramatised(parse_script(make_short('XERXES: "Go." [dramatised]')))
    assert not has_dramatised(parse_script(make_short()))


def test_speakers_helper_for_voice_and_shots():
    from tc.script import speakers
    s = make_short('XERXES: "Go." [dramatised]\nSICINNUS (messenger): "Now." [dramatised]')
    assert speakers(parse_script(s)) == {4: ("XERXES", None), 5: ("SICINNUS", "messenger")}


def test_curly_quotes_character_line():
    l = parse_script("## build\nXERXES: “Burn it.” [dramatised]\n")[0]
    assert l.speaker == "XERXES" and l.spoken == "Burn it."



# ---------------- 2026-11-21 lengths: long 12-15 min, Shorts 2 to under 3 min ----------------
def test_long_word_range():
    probs = check_script(parse_script(make_script(words_per_section=290)), "long", SOURCES, Config())
    assert not any("words; a long" in p for p in probs)


def test_short_needs_rehook_every_30s():
    narr = " ".join(["word"] * 20) + ". [src: herodotus-8]"
    text = "\n".join(["## hook", narr + " {loop}", "## build"] + [narr] * 10 + ["## payoff"] + [narr] * 5)
    probs = check_script(parse_script(text), "short", SOURCES, Config())
    assert any("without a {loop} re-hook" in p for p in probs)

import os
import json
import random
import config

# ============================================================
# TIMELESS COMPASS — SCRIPT GENERATOR
# ============================================================
# Uses Gemini to generate historically accurate documentary scripts
# with visual search keywords for stock footage matching.
#
# Script structure (designed for Kings and Generals / Epic History style):
#   1. HOOK — dramatic opening moment that grabs attention
#   2. CONTEXT — era, location, key players introduced
#   3. RISING ACTION — events build tension
#   4. CLIMAX — the pivotal battle/moment/decision
#   5. AFTERMATH — consequences that shaped the future
#   6. LEGACY — why it matters today
#
# Each segment includes:
#   - text: narration script (spoken by ElevenLabs)
#   - visual_keywords: search terms for Pexels/Pixabay stock footage
#   - era: time period for era-specific footage filtering
#   - overlay_text: date/name/location shown on screen
#   - mood: guides music selection and pacing
# ============================================================

from google import genai

# --- Historical categories for AI topic selection ---
HISTORY_CATEGORIES = [
    "ancient_civilizations",     # Egypt, Rome, Greece, Mesopotamia, China
    "medieval_kingdoms",         # Crusades, Vikings, Mongols, feudal Japan
    "great_battles",            # Thermopylae, Hastings, Waterloo, Stalingrad
    "rise_and_fall",            # empires rising to power then collapsing
    "exploration_discovery",     # Age of Sail, Columbus, Magellan, Silk Road
    "revolutionary_moments",     # French Revolution, American Revolution, uprisings
    "legendary_figures",         # Alexander, Caesar, Cleopatra, Genghis Khan
    "ancient_mysteries",         # lost cities, unexplained ruins, forgotten peoples
    "world_wars",               # WWI, WWII key moments and turning points
    "cold_war_espionage",       # spy stories, nuclear brinkmanship, proxy wars
]

# --- Eras for visual keyword enrichment ---
ERA_MAP = {
    "ancient_civilizations": "ancient",
    "medieval_kingdoms": "medieval",
    "great_battles": "medieval",
    "rise_and_fall": "ancient",
    "exploration_discovery": "colonial",
    "revolutionary_moments": "colonial",
    "legendary_figures": "ancient",
    "ancient_mysteries": "ancient",
    "world_wars": "world_war_2",
    "cold_war_espionage": "cold_war",
}


def _load_history():
    """
    # Loads the list of previously generated topics
    # so we never repeat the same historical event
    """
    if os.path.exists(config.HISTORY_FILE):
        with open(config.HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"topics": []}


def _save_history(history):
    """
    # Saves the updated topic history to disk
    """
    with open(config.HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def generate_script(topic=None, video_format=None):
    """
    # Generates a complete documentary script using Gemini
    #
    # Args:
    #   topic: specific historical event/figure, or None for AI-suggested
    #   video_format: VideoFormat enum (determines script length)
    #
    # Returns:
    #   (script_data, topic_title) tuple
    #   script_data has: segments[], metadata{}
    """
    if video_format is None:
        video_format = config.VideoFormat.LONG_FORM

    profile = config.get_format_profile(video_format)
    duration_range = profile["duration_range"]

    # --- Calculate target segment count based on duration ---
    # Average speaking rate: ~150 words/minute
    # Each segment: ~2-3 sentences (~40-60 words)
    min_duration, max_duration = duration_range
    target_minutes = (min_duration + max_duration) / 2 / 60
    target_segments = int(target_minutes * profile["scenes_per_minute"])

    # --- Load history to avoid repeats ---
    history = _load_history()
    previous_topics = history.get("topics", [])
    avoid_list = ", ".join(previous_topics[-50:]) if previous_topics else "none"

    # --- Configure Gemini (new SDK) ---
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    # --- Build the prompt ---
    if topic:
        topic_instruction = f'Create a documentary script about: "{topic}"'
    else:
        category = random.choice(HISTORY_CATEGORIES)
        topic_instruction = (
            f"Pick a fascinating historical event or figure from the category: {category}. "
            f"Choose something dramatic and visually interesting. "
            f"DO NOT pick any of these previously covered topics: {avoid_list}"
        )

    prompt = f"""You are a world-class history documentary scriptwriter for the YouTube channel "Timeless Compass".
Your style combines the visual storytelling of Kings and Generals with the dramatic narration of Epic History TV.

{topic_instruction}

Write a documentary script with EXACTLY {target_segments} segments.

IMPORTANT RULES:
- Write in a scholarly but engaging tone — authoritative, not sensational
- Include specific dates, names, numbers, and locations
- Every segment needs BOTH narration text AND visual search keywords
- Visual keywords should describe REAL footage available on stock sites
  (ancient ruins, medieval castles, battlefields, maps, landscapes, artifacts, paintings, statues)
- Do NOT reference AI-generated images — we use REAL stock footage only
- Include overlay_text for important dates, names, and locations
- The script should feel like watching a BBC or History Channel documentary

SCRIPT STRUCTURE:
1. HOOK (1-2 segments): Start with the most dramatic moment — a battle cry, a fateful decision, a city burning
2. CONTEXT (2-3 segments): Pull back — introduce the era, the key players, the stakes
3. RISING ACTION (40% of segments): Events escalate — alliances form, armies march, tension builds
4. CLIMAX (2-3 segments): The pivotal moment — the battle, the betrayal, the turning point
5. AFTERMATH (2-3 segments): The immediate consequences — who won, who fell, what changed
6. LEGACY (1-2 segments): Why this matters today — lasting impact on our world

Return ONLY valid JSON in this exact format:
{{
  "topic_title": "The Fall of Constantinople (1453)",
  "category": "great_battles",
  "era": "medieval",
  "segments": [
    {{
      "text": "On the morning of May 29th, 1453, the greatest city in the Christian world drew its last breath...",
      "visual_keywords": "medieval fortress walls siege ancient city dramatic sky",
      "era": "medieval",
      "overlay_text": "Constantinople, May 29, 1453",
      "mood": "tension",
      "section": "hook"
    }}
  ],
  "metadata": {{
    "title": "The Fall of Constantinople — How an Empire Died in a Day",
    "description": "In 1453, the Ottoman Empire shattered the walls of Constantinople...",
    "tags": ["history", "constantinople", "ottoman", "byzantine", "medieval", "battle"],
    "thumbnail_prompt": "ancient city walls under siege with smoke and dramatic sky"
  }}
}}

MOOD OPTIONS: "epic", "tension", "somber", "triumphant", "mysterious", "dramatic", "contemplative"

VISUAL KEYWORDS RULES:
- Use concrete nouns: "ancient stone ruins columns" not "the feeling of decay"
- Include era-specific terms: "medieval armor sword" or "roman columns marble"
- Add atmosphere: "dramatic sky sunset golden hour" or "foggy landscape mist"
- Think about what stock footage sites actually have
- Each segment should have UNIQUE keywords (no repeating the same search)
- Landscape orientation (16:9) footage works best

Return ONLY the JSON. No markdown, no code fences, no explanation."""

    # --- Call Gemini ---
    print(f"[SCRIPT] Generating {target_segments}-segment documentary script...")
    response = client.models.generate_content(
        model="gemini-3.6-flash", contents=prompt
    )

    # --- Parse the response ---
    response_text = response.text.strip()

    # --- Strip markdown code fences if present ---
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        response_text = "\n".join(lines)

    try:
        script_data = json.loads(response_text)
    except json.JSONDecodeError:
        # Gemini sometimes produces trailing commas or unescaped chars — attempt repair
        import re as _re
        cleaned = _re.sub(r',\s*([}\]])', r'\1', response_text)  # trailing commas
        cleaned = cleaned.replace('\n', '\\n').replace('\t', '\\t')  # unescaped newlines in strings
        try:
            script_data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Last resort: truncate to last valid closing brace
            last_brace = response_text.rfind('}')
            if last_brace > 0:
                script_data = json.loads(response_text[:last_brace + 1])
            else:
                raise
    topic_title = script_data.get("topic_title", topic or "Unknown Topic")

    # --- Save to history ---
    history["topics"].append(topic_title)
    _save_history(history)

    print(f"[SCRIPT] Generated: {topic_title}")
    print(f"[SCRIPT] Segments: {len(script_data['segments'])}")

    return script_data, topic_title


def get_full_narration(script_data):
    """
    # Concatenates all segment text into a single narration string
    # Used for voiceover generation
    """
    segments = script_data.get("segments", [])
    narration_parts = []

    for seg in segments:
        text = seg.get("text", "").strip()
        if text:
            narration_parts.append(text)

    return " ".join(narration_parts)


def enrich_visual_keywords(segments):
    """
    # Uses Gemini to generate alternative visual search keywords
    # for each segment, improving stock footage match rates.
    #
    # For each segment, generates 2-3 alternative keyword sets
    # that describe the same visual concept differently.
    #
    # This is called AFTER the initial script is generated,
    # before the visual search phase.
    """
    if not config.GEMINI_API_KEY:
        return segments

    client = genai.Client(api_key=config.GEMINI_API_KEY)

    # --- Build batch prompt for all segments ---
    keyword_list = []
    for i, seg in enumerate(segments):
        kw = seg.get("visual_keywords", "")
        text = seg.get("text", "")
        keyword_list.append(f"{i}: keywords='{kw}' | narration='{text[:100]}'")

    prompt = f"""For each numbered item below, generate 2-3 ALTERNATIVE stock footage search queries
that would find similar but different footage on Pexels or Pixabay.

Focus on REAL footage categories: landscapes, architecture, artifacts, nature, cities, monuments.
Use concrete nouns, not abstract concepts. Think about what stock video sites actually have.

Items:
{chr(10).join(keyword_list)}

Return ONLY valid JSON — a list of lists:
[[\"alt query 1\", \"alt query 2\"], [\"alt query 1\", \"alt query 2\"], ...]

No markdown, no code fences."""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash", contents=prompt
        )
        response_text = response.text.strip()

        # --- Strip markdown fences ---
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            response_text = "\n".join(lines)

        alt_keywords = json.loads(response_text)

        # --- Attach alt keywords to segments ---
        for i, seg in enumerate(segments):
            if i < len(alt_keywords):
                seg["visual_keywords_alt"] = alt_keywords[i]

        print(f"[SCRIPT] Enriched {len(segments)} segments with alt keywords")

    except Exception as e:
        print(f"[SCRIPT] Alt keyword enrichment failed (non-fatal): {e}")

    return segments


# --- Quick test ---
if __name__ == "__main__":
    script_data, title = generate_script("The Battle of Thermopylae")
    print(f"\nTitle: {title}")
    print(f"Segments: {len(script_data['segments'])}")
    for i, seg in enumerate(script_data["segments"][:3]):
        print(f"\n--- Segment {i+1} ---")
        print(f"Text: {seg['text'][:100]}...")
        print(f"Keywords: {seg['visual_keywords']}")
        print(f"Overlay: {seg.get('overlay_text', 'none')}")

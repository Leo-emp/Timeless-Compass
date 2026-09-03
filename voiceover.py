import os
import json
import requests
import config

# ============================================================
# TIMELESS COMPASS — VOICEOVER GENERATOR
# ============================================================
# Uses ElevenLabs API to generate documentary narration
# with word-level timestamps for caption synchronization.
#
# Voice: Daniel (British, scholarly, warm, authoritative)
# Model: eleven_multilingual_v2
#
# Key features:
#   - Word-level timestamps for precise caption placement
#   - Clean text preprocessing (removes markers, fixes punctuation)
#   - Configurable stability/similarity per format profile
# ============================================================


def clean_script_text(text):
    """
    # Preprocesses narration text for TTS
    # Removes markers, fixes punctuation, ensures clean speech
    """
    # --- Replace pause markers with actual pauses (ellipsis) ---
    text = text.replace("[PAUSE]", "...")
    text = text.replace("[pause]", "...")

    # --- Replace em dashes with commas for natural speech ---
    text = text.replace(" — ", ", ")
    text = text.replace("—", ", ")

    # --- Fix smart quotes to straight quotes ---
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')

    # --- Remove any bracketed stage directions ---
    import re
    text = re.sub(r'\[.*?\]', '', text)

    # --- Clean up extra whitespace ---
    text = " ".join(text.split())

    return text.strip()


def generate_voiceover(narration_text, output_path, profile=None):
    """
    # Generates voiceover audio with word-level timestamps
    #
    # Args:
    #   narration_text: full narration string
    #   output_path: where to save the MP3 file
    #   profile: format profile dict with voice settings
    #
    # Returns:
    #   list of word timestamp dicts: [{"word": "In", "start": 0.0, "end": 0.15}, ...]
    """
    if profile is None:
        profile = config.get_format_profile(config.VideoFormat.LONG_FORM)

    # --- Clean the text for TTS ---
    clean_text = clean_script_text(narration_text)

    # --- Check quota before generating ---
    quota = _check_quota()
    if quota is not None:
        print(f"[VOICEOVER] Quota remaining: {quota} chars")
        if quota < len(clean_text):
            print(f"[VOICEOVER] ERROR: Need {len(clean_text)} chars but only {quota} remaining")
            print(f"[VOICEOVER] Upgrade your ElevenLabs plan or wait for quota reset")
            return []

    # --- ElevenLabs API endpoint (with timestamps) ---
    voice_id = profile.get("voice_id", "onwK4e9ZLuTAKqWW03F9")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"

    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "text": clean_text,
        "model_id": profile.get("voice_model", "eleven_multilingual_v2"),
        "voice_settings": {
            "stability": profile.get("voice_stability", 0.72),
            "similarity_boost": profile.get("voice_similarity", 0.82),
            "style": profile.get("voice_style", 0.25),
            "use_speaker_boost": True,
        },
    }

    print(f"[VOICEOVER] Generating narration ({len(clean_text)} chars)...")
    print(f"[VOICEOVER] Voice: Daniel (scholarly, warm, authoritative)")

    try:
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            print(f"[VOICEOVER] API error: {response.status_code}")
            print(f"[VOICEOVER] Response: {response.text[:200]}")
            return []

        data = response.json()

        # --- Save audio file ---
        import base64
        audio_b64 = data.get("audio_base64", "")
        if audio_b64:
            audio_bytes = base64.b64decode(audio_b64)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            print(f"[VOICEOVER] Saved: {output_path}")
        else:
            print("[VOICEOVER] WARNING: No audio data in response")
            return []

        # --- Parse word-level timestamps ---
        alignment = data.get("alignment", {})
        word_timestamps = _parse_alignment(alignment, clean_text)

        print(f"[VOICEOVER] Timestamps: {len(word_timestamps)} words")
        return word_timestamps

    except Exception as e:
        print(f"[VOICEOVER] Error: {e}")
        return []


def _parse_alignment(alignment, full_text):
    """
    # Parses ElevenLabs character-level alignment into word-level timestamps
    #
    # ElevenLabs returns:
    #   characters: list of individual characters
    #   character_start_times_seconds: list of start times
    #   character_end_times_seconds: list of end times
    #
    # We reconstruct word boundaries from character data
    """
    characters = alignment.get("characters", [])
    start_times = alignment.get("character_start_times_seconds", [])
    end_times = alignment.get("character_end_times_seconds", [])

    if not characters or not start_times or not end_times:
        return []

    word_timestamps = []
    current_word = ""
    word_start = None

    for i, char in enumerate(characters):
        if char == " " or i == len(characters) - 1:
            # --- End of word ---
            if i == len(characters) - 1 and char != " ":
                current_word += char

            if current_word.strip():
                word_end = end_times[i] if i == len(characters) - 1 else end_times[i - 1]
                word_timestamps.append({
                    "word": current_word.strip(),
                    "start": word_start if word_start is not None else 0.0,
                    "end": word_end,
                })

            current_word = ""
            word_start = None
        else:
            if not current_word:
                word_start = start_times[i]
            current_word += char

    return word_timestamps


def _check_quota():
    """
    # Checks remaining ElevenLabs character quota
    # Returns remaining characters, or None if check fails
    """
    try:
        url = "https://api.elevenlabs.io/v1/user/subscription"
        headers = {"xi-api-key": config.ELEVENLABS_API_KEY}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            limit = data.get("character_limit", 0)
            used = data.get("character_count", 0)
            return max(0, limit - used)
    except Exception:
        pass
    return None


def get_audio_duration(audio_path):
    """
    # Returns the duration of an audio file in seconds
    # Uses moviepy for accurate duration measurement
    """
    try:
        from moviepy import AudioFileClip
        clip = AudioFileClip(audio_path)
        duration = clip.duration
        clip.close()
        return duration
    except Exception as e:
        print(f"[VOICEOVER] Duration check error: {e}")
        return 0.0


# --- Quick test ---
if __name__ == "__main__":
    test_text = (
        "In the year 480 BC, a force of three hundred Spartan warriors "
        "stood against the might of the Persian Empire at a narrow coastal "
        "pass called Thermopylae. Their sacrifice would echo through the ages."
    )

    output = os.path.join(config.TEMP_DIR, "test_voiceover.mp3")
    timestamps = generate_voiceover(test_text, output)

    if timestamps:
        print(f"\nFirst 5 words:")
        for w in timestamps[:5]:
            print(f"  {w['word']}: {w['start']:.2f}s - {w['end']:.2f}s")

        duration = get_audio_duration(output)
        print(f"\nDuration: {duration:.1f}s")

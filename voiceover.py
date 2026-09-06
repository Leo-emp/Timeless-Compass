import os
import json
import re
import base64
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
#   - Auto-chunking: splits scripts > 9000 chars at sentence boundaries,
#     generates audio per chunk, concatenates, and merges timestamps
# ============================================================

# --- ElevenLabs per-request character limit ---
# Free tier caps at 10,000 chars per request. We chunk at 9,000 to leave margin
# for any encoding overhead. Each chunk is a complete sentence group so speech
# doesn't cut mid-word.
CHUNK_CHAR_LIMIT = 9000


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
    text = re.sub(r'\[.*?\]', '', text)

    # --- Clean up extra whitespace ---
    text = " ".join(text.split())

    return text.strip()


def _split_into_chunks(text, limit=CHUNK_CHAR_LIMIT):
    """
    # Splits text into chunks under `limit` chars, breaking at sentence boundaries.
    # Sentences end with . ! or ? followed by a space or end-of-string.
    # If a single sentence exceeds the limit, it's sent as-is (ElevenLabs may reject it,
    # but splitting mid-sentence would produce unnatural speech).
    """
    # --- Split into sentences ---
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # --- Would adding this sentence exceed the limit? ---
        candidate = (current_chunk + " " + sentence).strip() if current_chunk else sentence
        if len(candidate) <= limit:
            current_chunk = candidate
        else:
            # --- Flush current chunk if it has content ---
            if current_chunk:
                chunks.append(current_chunk)
            # --- Start new chunk with this sentence ---
            current_chunk = sentence

    # --- Don't forget the last chunk ---
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def generate_voiceover(narration_text, output_path, profile=None):
    """
    # Generates voiceover audio with word-level timestamps.
    # Auto-chunks scripts over 9000 chars so they don't exceed ElevenLabs' 10K limit.
    # Each chunk is generated separately, then audio is concatenated and timestamps merged.
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

    # --- Decide: single request or chunked ---
    if len(clean_text) <= CHUNK_CHAR_LIMIT:
        # Short enough for one request
        print(f"[VOICEOVER] Generating narration ({len(clean_text)} chars, single request)...")
        audio_bytes, word_timestamps = _generate_single_chunk(clean_text, profile)
        if audio_bytes is None:
            return []
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        print(f"[VOICEOVER] Saved: {output_path}")
        print(f"[VOICEOVER] Timestamps: {len(word_timestamps)} words")
        return word_timestamps

    # --- Chunked generation for long scripts ---
    chunks = _split_into_chunks(clean_text)
    print(f"[VOICEOVER] Script is {len(clean_text)} chars — splitting into {len(chunks)} chunks")

    all_audio_parts = []  # raw bytes per chunk
    all_timestamps = []   # merged word timestamps with offset correction
    time_offset = 0.0     # cumulative audio duration from previous chunks

    for i, chunk in enumerate(chunks):
        print(f"[VOICEOVER] Generating chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)...")
        audio_bytes, word_timestamps = _generate_single_chunk(chunk, profile)

        if audio_bytes is None:
            print(f"[VOICEOVER] ERROR: Chunk {i + 1} failed — aborting")
            return []

        all_audio_parts.append(audio_bytes)

        # --- Offset timestamps by cumulative duration of previous chunks ---
        for wt in word_timestamps:
            all_timestamps.append({
                "word": wt["word"],
                "start": wt["start"] + time_offset,
                "end": wt["end"] + time_offset,
            })

        # --- Calculate this chunk's audio duration for the next offset ---
        # Write temp file, measure duration, delete
        temp_chunk_path = output_path + f".chunk{i}.mp3"
        with open(temp_chunk_path, "wb") as f:
            f.write(audio_bytes)
        chunk_duration = get_audio_duration(temp_chunk_path)
        time_offset += chunk_duration
        os.remove(temp_chunk_path)
        print(f"[VOICEOVER] Chunk {i + 1} duration: {chunk_duration:.1f}s (cumulative: {time_offset:.1f}s)")

    # --- Concatenate all audio chunks into final file ---
    print(f"[VOICEOVER] Concatenating {len(all_audio_parts)} audio chunks...")
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "wb") as f:
        for part in all_audio_parts:
            f.write(part)
    print(f"[VOICEOVER] Saved: {output_path}")
    print(f"[VOICEOVER] Total timestamps: {len(all_timestamps)} words, {time_offset:.1f}s")

    return all_timestamps


def _generate_single_chunk(text, profile):
    """
    # Generates audio + timestamps for a single text chunk (must be under 10K chars).
    # Returns (audio_bytes, word_timestamps) or (None, []) on failure.
    """
    voice_id = profile.get("voice_id", "onwK4e9ZLuTAKqWW03F9")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"

    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "text": text,
        "model_id": profile.get("voice_model", "eleven_multilingual_v2"),
        "voice_settings": {
            "stability": profile.get("voice_stability", 0.72),
            "similarity_boost": profile.get("voice_similarity", 0.82),
            "style": profile.get("voice_style", 0.25),
            "use_speaker_boost": True,
        },
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code != 200:
            print(f"[VOICEOVER] API error: {response.status_code}")
            print(f"[VOICEOVER] Response: {response.text[:200]}")
            return None, []

        data = response.json()

        # --- Decode audio ---
        audio_b64 = data.get("audio_base64", "")
        if not audio_b64:
            print("[VOICEOVER] WARNING: No audio data in response")
            return None, []

        audio_bytes = base64.b64decode(audio_b64)

        # --- Parse word-level timestamps ---
        alignment = data.get("alignment", {})
        word_timestamps = _parse_alignment(alignment, text)

        return audio_bytes, word_timestamps

    except Exception as e:
        print(f"[VOICEOVER] Error: {e}")
        return None, []


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

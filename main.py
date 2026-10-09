import os
import sys
import time
import json
import random
import config
from script_generator import generate_script, get_full_narration
from visuals import search_and_download_videos
from voiceover import generate_voiceover, get_audio_duration
# --- Pure ffmpeg assembler (5-10x faster than MoviePy) ---
from video_assembler_ffmpeg import assemble_video
from flux_images import generate_all_segment_images

# ============================================================
# TIMELESS COMPASS — AUTOMATED HISTORY DOCUMENTARY PIPELINE
# ============================================================
# Creates premium history / documentary videos automatically:
#
#   1. Generate script + visual keywords (Gemini)
#   2. Download stock footage (Pexels + Pixabay)
#   3. Generate narration voiceover (ElevenLabs)
#   4. Assemble final video (ffmpeg + Ken Burns + color grade)
#   5. Generate YouTube metadata (from script)
#
# Usage:
#   python main.py                                -> AI picks a topic
#   python main.py "The Fall of Rome"             -> specific topic
#   python main.py --format short                 -> 60s teaser
#   python main.py --format mid                   -> 6-10 min video
#   python main.py --format long                  -> 10-15 min deep dive
#   python main.py --quality 4k                   -> 4K output
#
# Cost per video (~10 min):
#   Script:    ~$0.02  (Gemini Flash)
#   Voiceover: ~$0.50  (ElevenLabs)
#   Footage:   FREE    (Pexels + Pixabay stock)
#   Assembly:  FREE    (ffmpeg local)
#   TOTAL:     ~$0.52 per video
#
# Revenue per video (at 100K views, $8-15 CPM):
#   $800 - $1,500 per video
# ============================================================


def validate_setup():
    """
    # Checks all required API keys and directories before starting
    """
    errors = []

    # --- Check required API keys ---
    if not config.GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY not set in .env")
    if not config.ELEVENLABS_API_KEY:
        errors.append("ELEVENLABS_API_KEY not set in .env")
    if not config.PEXELS_API_KEY:
        errors.append("PEXELS_API_KEY not set in .env (primary footage source)")

    # --- Optional but recommended ---
    if not config.PIXABAY_API_KEY:
        print("[SETUP] Note: PIXABAY_API_KEY not set — using Pexels only")

    # --- Create directories ---
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(config.TEMP_DIR, exist_ok=True)
    os.makedirs(config.ASSETS_DIR, exist_ok=True)
    os.makedirs(config.MUSIC_DIR, exist_ok=True)
    os.makedirs(config.SFX_DIR, exist_ok=True)

    if errors:
        print("\n[SETUP ERROR] Fix the following before running:\n")
        for e in errors:
            print(f"  - {e}")
        print(f"\n  Edit your .env file at: {os.path.join(config.BASE_DIR, '.env')}")
        return False

    return True


def _make_cache_key(topic, video_format):
    """
    # Creates a stable cache directory name from topic + format.
    # Same topic + format always maps to the same directory,
    # so retries reuse cached script / voiceover / footage.
    # Returns (safe_key_string, cache_dir_path)
    """
    # --- Sanitize topic for filesystem ---
    safe = (topic or "ai_pick").replace(" ", "_").replace("'", "")
    safe = "".join(c for c in safe if c.isalnum() or c in "_-")[:50]
    fmt_tag = video_format.value if video_format else "long"
    key = f"{safe}_{fmt_tag}"

    cache_dir = os.path.join(config.TEMP_DIR, "cache", key)
    os.makedirs(cache_dir, exist_ok=True)
    return key, cache_dir


def run_pipeline(topic=None, video_format=None, quality="1080p"):
    """
    # Main pipeline — runs all steps in sequence
    # NOW WITH CACHING: if the pipeline fails midway and you retry
    # with the same topic, cached Gemini scripts and ElevenLabs
    # voiceover are reused automatically (saves API credits).
    #
    # Cache location: temp/cache/<topic>_<format>/
    #   - script.json       → cached Gemini script
    #   - voiceover.mp3     → cached ElevenLabs audio
    #   - timestamps.json   → cached word-level timestamps
    #   - clips/            → cached Pexels footage
    #
    # Args:
    #   topic:         specific historical event/figure, or None for AI-suggested
    #   video_format:  VideoFormat enum (long/mid/short)
    #   quality:       "1080p" or "4k"
    """
    if video_format is None:
        video_format = config.VideoFormat.LONG_FORM

    profile = config.get_format_profile(video_format, quality=quality)
    start_time = time.time()

    print("\n" + "=" * 60)
    print("  TIMELESS COMPASS — DOCUMENTARY PIPELINE")
    print(f"  Format: {video_format.value} ({profile['width']}x{profile['height']})")
    print(f"  Quality: {profile.get('quality', '1080p').upper()}")
    print("=" * 60)

    # --- STEP 1: VALIDATE SETUP ---
    print("\n[STEP 1/6] Validating setup...")
    if not validate_setup():
        return None

    # ================================================================
    # STEP 2: GENERATE SCRIPT (with cache)
    # ================================================================
    # Cache key is topic-stable — no timestamp — so retries hit cache.
    # If topic is None (AI picks), we cache under "ai_pick" initially,
    # then rename the cache dir to the real topic once Gemini returns.
    # ================================================================
    print("\n[STEP 2/6] Generating documentary script...")

    # --- Build topic-stable cache directory ---
    cache_key, cache_dir = _make_cache_key(topic, video_format)
    script_cache_path = os.path.join(cache_dir, "script.json")

    script_data = None
    topic_title = None

    # --- Check for cached script from a previous run ---
    if os.path.exists(script_cache_path):
        try:
            with open(script_cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            # --- Validate the cache has actual segments ---
            if cached.get("segments") and len(cached["segments"]) > 0:
                script_data = cached
                topic_title = cached.get("metadata", {}).get("title", topic or "Unknown")
                print(f"[SCRIPT] CACHED -- reusing script for '{topic_title}' "
                      f"({len(script_data['segments'])} segments)")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[SCRIPT] Cache corrupted ({e}), regenerating...")
            script_data = None

    if script_data is None:
        # --- Generate fresh script via Gemini API ---
        script_data, topic_title = generate_script(topic, video_format=video_format)

        # --- If topic was AI-picked, rename cache dir to match real topic ---
        if topic is None and topic_title:
            new_key, new_cache_dir = _make_cache_key(topic_title, video_format)
            if new_cache_dir != cache_dir:
                # --- Move cache to topic-specific directory ---
                if not os.path.exists(new_cache_dir):
                    os.rename(cache_dir, new_cache_dir)
                cache_dir = new_cache_dir
                script_cache_path = os.path.join(cache_dir, "script.json")

        # --- Save script to cache for retry ---
        with open(script_cache_path, "w", encoding="utf-8") as f:
            json.dump(script_data, f, indent=2, ensure_ascii=False)
        print(f"[SCRIPT] Cached to {script_cache_path}")

    narration_text = get_full_narration(script_data)
    segment_count = len(script_data["segments"])
    print(f"[SCRIPT] Topic: {topic_title}")
    print(f"[SCRIPT] Segments: {segment_count}")
    print(f"[SCRIPT] Narration preview: {narration_text[:200]}...")

    # --- Create work directory (timestamp-based) for final assembly ---
    safe_title = topic_title.replace(" ", "_").replace("'", "")[:50]
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_name = f"{safe_title}_{timestamp}"
    work_dir = os.path.join(config.TEMP_DIR, video_name)
    os.makedirs(work_dir, exist_ok=True)

    # --- Save script to work dir too (for reference alongside output) ---
    with open(os.path.join(work_dir, "script.json"), "w", encoding="utf-8") as f:
        json.dump(script_data, f, indent=2, ensure_ascii=False)

    # ================================================================
    # STEP 3: GENERATE VISUALS — Hybrid Flux Pro + Pexels (with cache)
    # ================================================================
    # Each segment has visual_source="flux" or "pexels":
    #   - flux: AI-generated cinematic art via fal.ai (battles, portraits)
    #   - pexels: real stock footage (landmarks, nature, aerial)
    # Both are cached in cache_dir so retries skip API calls.
    #
    # Flux images get Ken Burns motion applied during assembly,
    # so they look like video clips, not static slides.
    # ================================================================
    print(f"\n[STEP 3/6] Generating visuals for {segment_count} segments...")

    # --- Determine aspect ratio from format ---
    aspect_ratio = "9:16" if video_format == config.VideoFormat.SHORT else "16:9"

    # --- Step 3a: Generate Flux Pro images for tagged segments ---
    cached_flux_dir = os.path.join(cache_dir, "flux_images")
    flux_images = {}
    flux_segment_count = sum(
        1 for s in script_data["segments"]
        if s.get("visual_source") == "flux"
    )

    if flux_segment_count > 0:
        print(f"[STEP 3a] Generating {flux_segment_count} Flux Pro AI images...")
        flux_images = generate_all_segment_images(
            script_data["segments"], cached_flux_dir, aspect_ratio
        )
    else:
        print("[STEP 3a] No Flux segments — all Pexels footage")

    # --- Step 3b: Download Pexels footage for remaining segments ---
    cached_clips_dir = os.path.join(cache_dir, "clips")
    pexels_segment_count = segment_count - flux_segment_count
    clip_paths = None

    if pexels_segment_count > 0:
        print(f"[STEP 3b] Downloading {pexels_segment_count} Pexels clips...")

        # --- Check for cached footage clips ---
        if os.path.exists(cached_clips_dir):
            cached_files = [
                os.path.join(cached_clips_dir, f)
                for f in sorted(os.listdir(cached_clips_dir))
                if f.endswith((".mp4", ".webm")) and os.path.getsize(
                    os.path.join(cached_clips_dir, f)) > 50_000
            ]
            # --- Need enough clips for non-flux segments ---
            if len(cached_files) >= pexels_segment_count - 1:
                print(f"[FOOTAGE] CACHED -- reusing {len(cached_files)} Pexels clips")
                clip_paths = cached_files

        if clip_paths is None:
            clip_paths = search_and_download_videos(
                script_data["segments"], cached_clips_dir, profile
            )
    else:
        clip_paths = []

    # --- Merge Flux images and Pexels clips into unified visual list ---
    # Each segment gets either a Flux image path or a Pexels clip path.
    # The assembler handles both (Ken Burns for images, direct for clips).
    unified_visuals = []
    pexels_idx = 0
    for i in range(segment_count):
        if i in flux_images:
            # --- Flux Pro AI image for this segment ---
            unified_visuals.append({
                "type": "image",
                "path": flux_images[i],
            })
        elif clip_paths and pexels_idx < len(clip_paths):
            # --- Pexels stock footage clip ---
            path = clip_paths[pexels_idx]
            pexels_idx += 1
            if path is not None:
                unified_visuals.append({
                    "type": "video",
                    "path": path,
                })
            else:
                unified_visuals.append(None)
        else:
            unified_visuals.append(None)

    # --- Count what we got ---
    valid_count = sum(1 for v in unified_visuals if v is not None)
    flux_count = sum(1 for v in unified_visuals if v and v["type"] == "image")
    pexels_count = sum(1 for v in unified_visuals if v and v["type"] == "video")

    if valid_count == 0:
        print("[ERROR] No visuals generated. Check PEXELS_API_KEY and FAL_KEY.")
        return None

    print(f"[VISUALS] {valid_count} total: {flux_count} Flux images + {pexels_count} Pexels clips")

    # --- Build legacy clip_paths list for assembler compatibility ---
    # Until the assembler is upgraded to handle the unified format,
    # pass all paths as a flat list (images + videos mixed)
    clip_paths = [v["path"] for v in unified_visuals if v is not None]

    # ================================================================
    # STEP 4: GENERATE VOICEOVER (with cache)
    # ================================================================
    # Voiceover is the most expensive step (~$0.50 per video).
    # Cached in cache_dir/voiceover.mp3 + timestamps.json so retries
    # never waste ElevenLabs credits on the same script text.
    # ================================================================
    print("\n[STEP 4/6] Generating voiceover (ElevenLabs)...")

    # --- Check for cached voiceover ---
    cached_voiceover = os.path.join(cache_dir, "voiceover.mp3")
    cached_timestamps = os.path.join(cache_dir, "timestamps.json")
    voiceover_path = os.path.join(work_dir, "voiceover.mp3")

    if (os.path.exists(cached_voiceover)
            and os.path.getsize(cached_voiceover) > 1000
            and os.path.exists(cached_timestamps)):
        # --- Reuse cached voiceover (saves ~$0.50) ---
        import shutil
        shutil.copy2(cached_voiceover, voiceover_path)
        with open(cached_timestamps, "r", encoding="utf-8") as f:
            word_timestamps = json.load(f)
        print(f"[VOICEOVER] CACHED -- reusing voiceover "
              f"({len(word_timestamps)} word timestamps)")
    else:
        # --- Generate fresh voiceover via ElevenLabs API ---
        word_timestamps = generate_voiceover(narration_text, voiceover_path, profile)

        # --- Cache voiceover + timestamps for retry ---
        if os.path.exists(voiceover_path) and os.path.getsize(voiceover_path) > 1000:
            import shutil
            shutil.copy2(voiceover_path, cached_voiceover)
            with open(cached_timestamps, "w", encoding="utf-8") as f:
                json.dump(word_timestamps, f)
            print(f"[VOICEOVER] Cached to {cached_voiceover}")

    # --- Check voiceover was generated successfully ---
    if not os.path.exists(voiceover_path):
        print("[ERROR] Voiceover generation failed. Check ElevenLabs quota/key.")
        print("[ERROR] You may need to upgrade your ElevenLabs plan or wait for quota reset.")
        return None

    audio_duration = get_audio_duration(voiceover_path)
    if audio_duration <= 0:
        print("[ERROR] Voiceover file is empty or invalid.")
        return None

    print(f"[VOICEOVER] Duration: {audio_duration:.1f}s ({audio_duration / 60:.1f} min)")

    # --- STEP 5: FIND MUSIC ---
    print("\n[STEP 5/6] Selecting background music...")
    music_path = _find_music()

    # --- STEP 6: ASSEMBLE FINAL VIDEO ---
    print("\n[STEP 6/6] Assembling final documentary...")
    output_path = os.path.join(config.OUTPUT_DIR, f"{video_name}.mp4")

    assemble_video(
        video_clip_paths=clip_paths,
        voiceover_path=voiceover_path,
        script_data=script_data,
        word_timestamps=word_timestamps,
        music_path=music_path,
        output_path=output_path,
        video_format=video_format,
    )

    # --- Save metadata for YouTube upload ---
    metadata = script_data.get("metadata", {})
    meta_path = output_path.replace(".mp4", "_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # --- Done! ---
    elapsed = time.time() - start_time
    file_size = os.path.getsize(output_path) / (1024 * 1024)

    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print(f"  Topic: {topic_title}")
    print(f"  Duration: {audio_duration:.1f}s ({audio_duration / 60:.1f} min)")
    print(f"  File: {output_path}")
    print(f"  Size: {file_size:.1f} MB")
    print(f"  Metadata: {meta_path}")
    print(f"  Pipeline time: {elapsed / 60:.1f} min")
    print(f"  Estimated cost: ~$0.52")
    print("=" * 60)

    return {
        "topic_title": topic_title,
        "output_path": output_path,
        "metadata_path": meta_path,
        "duration": audio_duration,
        "file_size_mb": file_size,
        "pipeline_time_min": elapsed / 60,
        "estimated_cost": 0.52,
    }


def _find_music():
    """
    # Finds a background music track from assets/music/
    # Expects orchestral/cinematic tracks for documentary feel
    """
    if not os.path.exists(config.MUSIC_DIR):
        return None

    tracks = [
        f for f in os.listdir(config.MUSIC_DIR)
        if f.endswith((".mp3", ".wav", ".ogg"))
    ]

    if not tracks:
        print("[MUSIC] No background music found in assets/music/")
        print("[MUSIC] Add orchestral/cinematic MP3 tracks for atmosphere")
        return None

    track = random.choice(tracks)
    path = os.path.join(config.MUSIC_DIR, track)
    print(f"[MUSIC] Selected: {track}")
    return path


# ============================================================
# CLI ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Timeless Compass — Automated History Documentary Pipeline"
    )
    parser.add_argument(
        "topic", nargs="?", default=None,
        help="Specific historical topic (optional, AI picks if omitted)"
    )
    parser.add_argument(
        "--format", choices=["long", "mid", "short"], default="long",
        help="Video format: long (10-15min), mid (6-10min), short (60s)"
    )
    parser.add_argument(
        "--quality", choices=["1080p", "4k"], default="1080p",
        help="Output quality"
    )

    args = parser.parse_args()

    # --- Map format string to enum ---
    format_map = {
        "long": config.VideoFormat.LONG_FORM,
        "mid": config.VideoFormat.MID_FORM,
        "short": config.VideoFormat.SHORT,
    }

    result = run_pipeline(
        topic=args.topic,
        video_format=format_map[args.format],
        quality=args.quality,
    )

    if result:
        print(f"\nVideo ready: {result['output_path']}")
    else:
        print("\nPipeline failed. Check errors above.")
        sys.exit(1)

import os
import sys
import time
import json
import random
import config
from script_generator import generate_script, get_full_narration
from visuals import search_and_download_videos
from voiceover import generate_voiceover, get_audio_duration
from video_assembler import assemble_video

# ============================================================
# TIMELESS COMPASS — AUTOMATED HISTORY DOCUMENTARY PIPELINE
# ============================================================
# Creates premium history / documentary videos automatically:
#
#   1. Generate script + visual keywords (Gemini)
#   2. Download stock footage (Pexels + Pixabay)
#   3. Generate narration voiceover (ElevenLabs)
#   4. Assemble final video (MoviePy + Ken Burns + color grade)
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
#   Assembly:  FREE    (MoviePy local)
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


def run_pipeline(topic=None, video_format=None, quality="1080p"):
    """
    # Main pipeline — runs all steps in sequence
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
    print("\n[STEP 1/5] Validating setup...")
    if not validate_setup():
        return None

    # --- STEP 2: GENERATE SCRIPT ---
    print("\n[STEP 2/5] Generating documentary script...")
    script_data, topic_title = generate_script(topic, video_format=video_format)
    narration_text = get_full_narration(script_data)
    segment_count = len(script_data["segments"])
    print(f"[SCRIPT] Topic: {topic_title}")
    print(f"[SCRIPT] Segments: {segment_count}")
    print(f"[SCRIPT] Narration preview: {narration_text[:200]}...")

    # --- Create working directory for this video ---
    safe_title = topic_title.replace(" ", "_").replace("'", "")[:50]
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_name = f"{safe_title}_{timestamp}"
    work_dir = os.path.join(config.TEMP_DIR, video_name)
    os.makedirs(work_dir, exist_ok=True)

    # --- Save script for reference ---
    with open(os.path.join(work_dir, "script.json"), "w", encoding="utf-8") as f:
        json.dump(script_data, f, indent=2, ensure_ascii=False)

    # --- STEP 3: DOWNLOAD STOCK FOOTAGE ---
    print(f"\n[STEP 3/5] Downloading {segment_count} stock footage clips...")
    clips_dir = os.path.join(work_dir, "clips")
    clip_paths = search_and_download_videos(
        script_data["segments"], clips_dir, profile
    )

    if not clip_paths:
        print("[ERROR] No footage downloaded. Check your PEXELS_API_KEY.")
        return None

    print(f"[FOOTAGE] Downloaded {len(clip_paths)} clips")

    # --- STEP 4: GENERATE VOICEOVER ---
    print("\n[STEP 4/5] Generating voiceover (ElevenLabs)...")
    voiceover_path = os.path.join(work_dir, "voiceover.mp3")
    word_timestamps = generate_voiceover(narration_text, voiceover_path, profile)

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

    # --- Find background music ---
    music_path = _find_music()

    # --- STEP 5: ASSEMBLE FINAL VIDEO ---
    print("\n[STEP 5/5] Assembling final documentary...")
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

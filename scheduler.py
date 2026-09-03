import os
import time
import random
import json
import schedule
import config
from config import VideoFormat
from main import run_pipeline
from youtube_uploader import upload_video, is_authenticated

# ============================================================
# TIMELESS COMPASS — SCHEDULER
# ============================================================
# Generates videos on a cron schedule and auto-posts to YouTube.
# Runs continuously in a terminal — same pattern as Luminous Will.
#
# Schedule:
#   Long-form (10-15 min):  Mon / Wed / Fri at 2 AM
#   Mid-form  (6-10 min):   Tue / Thu at 3 AM
#   Short-form (60s):       Daily at 4 AM (optional)
#
# Start:  python scheduler.py
# Stop:   Ctrl+C
#
# The scheduler:
#   1. Generates a video (AI picks the topic)
#   2. Saves to output/ with metadata
#   3. Auto-uploads to YouTube (if connected)
#   4. Logs everything to scheduler_log.json
# ============================================================

LOG_FILE = os.path.join(config.BASE_DIR, "scheduler_log.json")
USED_TOPICS_FILE = os.path.join(config.BASE_DIR, ".used_topics.json")


def _load_log():
    """
    # Loads the scheduler run log
    """
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"runs": []}


def _save_log(log):
    """
    # Saves the scheduler run log
    """
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def _log_run(result, video_format, youtube_url=None, error=None):
    """
    # Records a scheduler run (success or failure)
    """
    log = _load_log()
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "format": video_format,
        "status": "success" if result else "failed",
        "topic": result.get("topic_title", "unknown") if result else "unknown",
        "duration_seconds": result.get("duration", 0) if result else 0,
        "file_size_mb": result.get("file_size_mb", 0) if result else 0,
        "output_path": result.get("output_path", "") if result else "",
        "youtube_url": youtube_url,
        "error": error,
        "cost": result.get("estimated_cost", 0) if result else 0,
    }
    log["runs"].append(entry)
    # --- Keep last 200 entries ---
    log["runs"] = log["runs"][-200:]
    _save_log(log)
    return entry


def generate_and_post(video_format="long"):
    """
    # Main task: generate a video and upload to YouTube
    """
    print(f"\n{'='*60}")
    print(f"  SCHEDULER — {video_format.upper()} FORM")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # --- Map format string to enum ---
    format_map = {
        "long": VideoFormat.LONG_FORM,
        "mid": VideoFormat.MID_FORM,
        "short": VideoFormat.SHORT,
    }
    fmt = format_map.get(video_format, VideoFormat.LONG_FORM)

    try:
        # --- Step 1: Generate the video ---
        result = run_pipeline(topic=None, video_format=fmt, quality="1080p")

        if not result:
            print("[SCHEDULER] Pipeline failed — no output")
            _log_run(None, video_format, error="Pipeline returned None")
            return

        print(f"[SCHEDULER] Video ready: {result['output_path']}")

        # --- Step 2: Auto-upload to YouTube ---
        youtube_url = None
        if is_authenticated():
            # --- Load metadata for YouTube ---
            metadata_path = result.get("metadata_path", "")
            metadata = {}
            if metadata_path and os.path.exists(metadata_path):
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

            title = metadata.get("title", result.get("topic_title", "Timeless Compass"))
            description = metadata.get("description", "")
            tags = metadata.get("tags", ["history", "documentary"])

            # --- Add channel branding to description ---
            description += (
                "\n\n---\n"
                "Timeless Compass — Navigate the ages.\n"
                "Subscribe for weekly history documentaries.\n"
                "\n#history #documentary #timelesscompass"
            )

            print("[SCHEDULER] Uploading to YouTube...")
            youtube_url = upload_video(
                video_path=result["output_path"],
                title=title,
                description=description,
                tags=tags,
                category_id="27",
            )

            if youtube_url:
                print(f"[SCHEDULER] Uploaded: {youtube_url}")
            else:
                print("[SCHEDULER] YouTube upload failed (video saved locally)")
        else:
            print("[SCHEDULER] YouTube not connected — video saved locally only")

        # --- Log success ---
        entry = _log_run(result, video_format, youtube_url=youtube_url)
        print(f"[SCHEDULER] Logged: {entry['topic']}")
        print(f"[SCHEDULER] Cost: ~${entry['cost']:.2f}")

    except Exception as e:
        print(f"[SCHEDULER] Error: {e}")
        _log_run(None, video_format, error=str(e))


def run_long():
    """# Generates a 10-15 min deep-dive documentary"""
    generate_and_post("long")

def run_mid():
    """# Generates a 6-10 min overview video"""
    generate_and_post("mid")

def run_short():
    """# Generates a 60s teaser"""
    generate_and_post("short")


# ============================================================
# SCHEDULE CONFIGURATION
# ============================================================

def start_scheduler():
    """
    # Sets up the cron schedule and runs forever
    #
    # Default schedule:
    #   Long-form:  Mon / Wed / Fri at 02:00
    #   Mid-form:   Tue / Thu at 03:00
    #
    # Adjust times below to your timezone
    """
    print("\n" + "=" * 60)
    print("  TIMELESS COMPASS — SCHEDULER")
    print("  Auto-generating history documentaries")
    print("=" * 60)
    print(f"\n  YouTube: {'Connected' if is_authenticated() else 'Not connected (local only)'}")
    print(f"  Gemini:  {'OK' if config.GEMINI_API_KEY else 'MISSING'}")
    print(f"  11Labs:  {'OK' if config.ELEVENLABS_API_KEY else 'MISSING'}")
    print(f"  Pexels:  {'OK' if config.PEXELS_API_KEY else 'MISSING'}")
    print()

    # --- Long-form: Mon / Wed / Fri at 2 AM ---
    schedule.every().monday.at("02:00").do(run_long)
    schedule.every().wednesday.at("02:00").do(run_long)
    schedule.every().friday.at("02:00").do(run_long)

    # --- Mid-form: Tue / Thu at 3 AM ---
    schedule.every().tuesday.at("03:00").do(run_mid)
    schedule.every().thursday.at("03:00").do(run_mid)

    print("  Schedule:")
    print("    Mon/Wed/Fri 02:00 — Long-form (10-15 min)")
    print("    Tue/Thu     03:00 — Mid-form (6-10 min)")
    print()
    print("  Waiting for next scheduled run...")
    print("  Press Ctrl+C to stop\n")

    while True:
        schedule.run_pending()
        time.sleep(60)


# ============================================================
# CLI ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Timeless Compass Scheduler")
    parser.add_argument(
        "--now", choices=["long", "mid", "short"],
        help="Generate one video immediately instead of waiting for schedule"
    )
    parser.add_argument(
        "--test", action="store_true",
        help="Generate a short test video to verify everything works"
    )

    args = parser.parse_args()

    if args.test:
        # --- Quick test: generate a short video ---
        print("[TEST] Generating a short test video...")
        generate_and_post("short")
    elif args.now:
        # --- Generate one immediately ---
        generate_and_post(args.now)
    else:
        # --- Run on schedule ---
        start_scheduler()

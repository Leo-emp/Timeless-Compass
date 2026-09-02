import os
from dotenv import load_dotenv
from enum import Enum

# ============================================================
# TIMELESS COMPASS — CONFIGURATION
# ============================================================
# Automated history / documentary video pipeline
# All API keys live in .env — never hardcode secrets
#
# Required keys:
#   GEMINI_API_KEY       — script generation + visual keywords
#   ELEVENLABS_API_KEY   — narration voice
#   PEXELS_API_KEY       — stock footage (primary source)
#
# Optional keys:
#   PIXABAY_API_KEY      — stock footage (secondary/fallback)
#   BLOB_READ_WRITE_TOKEN — Vercel Blob cloud upload
#   YOUTUBE_CLIENT_ID     — auto-upload to YouTube
#   YOUTUBE_CLIENT_SECRET — auto-upload to YouTube
#
# Cost per 10-min video: ~$1
#   Script:    ~$0.02  (Gemini Flash)
#   Voiceover: ~$0.50  (ElevenLabs)
#   Footage:   FREE    (Pexels + Pixabay)
#   Assembly:  FREE    (MoviePy local)
# ============================================================

# --- Ensure FFmpeg is on PATH (winget install location) ---
_ffmpeg_dir = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Microsoft", "WinGet", "Packages",
    "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
    "ffmpeg-9.0.1-full_build", "bin",
)
if os.path.isdir(_ffmpeg_dir) and _ffmpeg_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

# --- Load environment variables from .env ---
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# --- Core API Keys ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()

# --- Optional API Keys ---
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "").strip()
BLOB_READ_WRITE_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN", "").strip()
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()

# --- Directory paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
MUSIC_DIR = os.path.join(ASSETS_DIR, "music")
SFX_DIR = os.path.join(ASSETS_DIR, "sfx")

# --- History file to avoid repeating topics ---
HISTORY_FILE = os.path.join(BASE_DIR, "generated_history.json")

# --- Pexels search defaults ---
# History documentaries use LANDSCAPE footage (16:9)
PEXELS_ORIENTATION = "landscape"
PEXELS_SIZE = "large"
PEXELS_PER_PAGE = 15


# ============================================================
# VIDEO FORMAT SYSTEM
# ============================================================
# Three content formats with different specs:
#   - LONG_FORM:  16:9, 10-15 min deep dives (main content)
#   - MID_FORM:   16:9, 6-10 min focused episodes
#   - SHORT:      9:16, 60s teasers for Shorts/TikTok/Reels
# ============================================================

class VideoFormat(Enum):
    LONG_FORM = "long"       # 16:9, 10-15 min deep dives
    MID_FORM = "mid"         # 16:9, 6-10 min focused episodes
    SHORT = "short"          # 9:16, 60s teasers


# --- Format profiles — ALL format-specific settings live here ---
FORMAT_PROFILES = {
    VideoFormat.LONG_FORM: {
        # --- Resolution & output ---
        "width": 1920,
        "height": 1080,
        "fps": 24,                               # cinematic frame rate
        "bitrate": "12000k",
        # --- Duration ---
        "duration_range": (600, 900),             # 10-15 minutes
        # --- Scene timing ---
        "scene_duration": 8,                      # seconds per visual (longer for Ken Burns)
        "scenes_per_minute": 7,                   # slower pacing than true crime
        # --- Pexels search ---
        "pexels_orientation": "landscape",        # 16:9 footage
        # --- Narration ---
        # Using ElevenLabs "Daniel" voice — British, scholarly, warm
        "voice_id": "onwK4e9ZLuTAKqWW03F9",
        "voice_model": "eleven_multilingual_v2",
        "voice_stability": 0.72,                  # steady, authoritative
        "voice_similarity": 0.82,
        "voice_style": 0.25,                      # calm, measured delivery
        # --- Audio mixing (dB-based) ---
        "voiceover_boost_db": 2.0,
        "music_level_db": -12,                    # orchestral music slightly more present
        "sfx_level_db": -10,
        # --- Ken Burns effect ---
        "ken_burns_zoom_range": (1.0, 1.15),      # subtle 15% zoom over clip duration
        "ken_burns_pan_speed": 0.02,              # slow pan across image
        # --- Color grading ---
        "brightness_factor": 0.85,                # warm, not dark
        "saturation_factor": 0.75,                # slightly desaturated vintage feel
        "sepia_intensity": 0.15,                  # subtle warm sepia tint
        "color_temp_shift": 8,                    # warm shift (positive = warm)
        # --- Text overlays (dates, names, locations) ---
        "overlay_font_size": 38,
        "overlay_font": "Georgia",
        "overlay_position_y": 0.92,               # bottom of frame
        "overlay_bg_opacity": 0.6,                # semi-transparent dark bar
        # --- Captions ---
        "caption_font_size": 48,
        "caption_position_y": 0.85,
        "caption_stroke_width": 2,
        "caption_font": "Georgia",
    },

    VideoFormat.MID_FORM: {
        "width": 1920,
        "height": 1080,
        "fps": 24,
        "bitrate": "10000k",
        "duration_range": (360, 600),             # 6-10 minutes
        "scene_duration": 7,
        "scenes_per_minute": 8,
        "pexels_orientation": "landscape",
        "voice_id": "onwK4e9ZLuTAKqWW03F9",
        "voice_model": "eleven_multilingual_v2",
        "voice_stability": 0.72,
        "voice_similarity": 0.82,
        "voice_style": 0.25,
        "voiceover_boost_db": 2.0,
        "music_level_db": -12,
        "sfx_level_db": -10,
        "ken_burns_zoom_range": (1.0, 1.15),
        "ken_burns_pan_speed": 0.02,
        "brightness_factor": 0.85,
        "saturation_factor": 0.75,
        "sepia_intensity": 0.15,
        "color_temp_shift": 8,
        "overlay_font_size": 38,
        "overlay_font": "Georgia",
        "overlay_position_y": 0.92,
        "overlay_bg_opacity": 0.6,
        "caption_font_size": 48,
        "caption_position_y": 0.85,
        "caption_stroke_width": 2,
        "caption_font": "Georgia",
    },

    VideoFormat.SHORT: {
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "bitrate": "10000k",
        "duration_range": (50, 70),               # 50-70 seconds
        "scene_duration": 5,                      # faster pacing for shorts
        "scenes_per_minute": 12,
        "pexels_orientation": "portrait",         # 9:16 for shorts
        "voice_id": "onwK4e9ZLuTAKqWW03F9",
        "voice_model": "eleven_multilingual_v2",
        "voice_stability": 0.70,
        "voice_similarity": 0.85,
        "voice_style": 0.30,
        "voiceover_boost_db": 3.0,
        "music_level_db": -10,
        "sfx_level_db": -8,
        "ken_burns_zoom_range": (1.0, 1.20),      # slightly more dramatic for shorts
        "ken_burns_pan_speed": 0.03,
        "brightness_factor": 0.85,
        "saturation_factor": 0.75,
        "sepia_intensity": 0.15,
        "color_temp_shift": 8,
        "overlay_font_size": 42,
        "overlay_font": "Georgia",
        "overlay_position_y": 0.55,
        "overlay_bg_opacity": 0.6,
        "caption_font_size": 58,
        "caption_position_y": 0.60,
        "caption_stroke_width": 2,
        "caption_font": "Georgia",
    },
}


def get_format_profile(video_format, quality="1080p"):
    """
    # Returns the complete settings dict for a given format
    # quality="4k" overrides resolution for premium output
    """
    profile = FORMAT_PROFILES[video_format].copy()

    if quality == "4k" and video_format != VideoFormat.SHORT:
        profile["width"] = 3840
        profile["height"] = 2160
        profile["bitrate"] = "30000k"
        profile["quality"] = "4k"
    else:
        profile["quality"] = "1080p"

    return profile


# ============================================================
# VISUAL SEARCH KEYWORDS
# ============================================================
# History-specific keyword mappings for stock footage search
# These help Gemini generate better visual_keywords for each era
# ============================================================

ERA_VISUAL_KEYWORDS = {
    "ancient": "ancient ruins columns marble temple stone civilization archaeological",
    "medieval": "medieval castle fortress knights armor cathedral stone walls torch",
    "renaissance": "renaissance painting art marble sculpture grand hall palace",
    "colonial": "colonial ships sailing ocean port harbor old town cobblestone",
    "industrial": "industrial factory smoke chimney steam engine railway coal mine",
    "world_war_1": "trenches barbed wire soldiers mud battlefield artillery war",
    "world_war_2": "tanks soldiers battlefield bombing ruins military convoy war",
    "cold_war": "nuclear missile submarine spy espionage berlin wall propaganda",
    "modern": "modern city skyline government building parliament diplomacy",
}

# --- Keywords to AVOID in search results ---
# These don't match the documentary aesthetic
AVOID_KEYWORDS = [
    "cartoon", "anime", "illustration", "comic", "animated",
    "funny", "comedy", "meme", "party", "celebration",
    "cute", "baby", "kitten", "puppy", "toy",
    "selfie", "tiktok", "dance", "prank",
]

# --- Brand-relevant words that get bonus scoring weight ---
BRAND_BONUS_WORDS = {
    "ancient", "historic", "historical", "medieval", "castle", "ruins",
    "temple", "monument", "palace", "cathedral", "fortress", "empire",
    "kingdom", "dynasty", "civilization", "archaeological", "artifact",
    "battle", "war", "soldier", "army", "military", "warrior",
    "map", "globe", "compass", "scroll", "manuscript", "library",
    "ocean", "ship", "sailing", "voyage", "exploration", "expedition",
    "mountain", "desert", "landscape", "aerial", "panoramic",
    "statue", "sculpture", "marble", "column", "arch", "dome",
    "cinematic", "dramatic", "atmospheric", "epic", "grand",
    "sunset", "sunrise", "golden", "fog", "mist", "clouds",
    "old", "vintage", "antique", "weathered", "aged", "patina",
}


# ============================================================
# BRAND IDENTITY
# ============================================================
CHANNEL_NAME = "Timeless Compass"
CHANNEL_TAGLINE = "Navigate the ages."
BRAND_COLORS = {
    "primary": "#1A1410",       # dark warm brown
    "secondary": "#2C2418",     # aged parchment dark
    "accent": "#C49A6C",        # antique gold
    "text": "#E8E2D8",          # warm ivory
    "highlight": "#8B6914",     # deep gold for emphasis
}

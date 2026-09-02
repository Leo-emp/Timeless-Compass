import os
import requests
import time
import random
import re
import config
from script_generator import enrich_visual_keywords

# ============================================================
# TIMELESS COMPASS — VISUAL SOURCER
# ============================================================
# Downloads free stock footage from Pexels + Pixabay APIs
# Optimized for HISTORY DOCUMENTARY content:
#   - Landscapes, ruins, castles, monuments, battlefields
#   - Maps, globes, old cities, harbors, mountains
#   - Artifacts, statues, paintings, manuscripts
#   - Atmospheric shots: fog, sunrise, dramatic skies
#
# SEARCH STRATEGY:
#   1. Primary keywords from script_generator
#   2. Alt keywords from Gemini enrichment
#   3. Era-specific fallback queries
#   4. Generic cinematic landscape fallbacks
#
# SOURCES:
#   1. Pexels API (primary) — great landscape/architecture footage
#   2. Pixabay API (secondary) — additional variety + fallback
# ============================================================

# --- Keywords to AVOID in search results ---
# These don't match the documentary aesthetic
AVOID_KEYWORDS = config.AVOID_KEYWORDS

# --- Words to ignore when scoring relevance ---
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
    "neither", "each", "every", "all", "any", "few", "more", "most",
    "other", "some", "such", "no", "only", "own", "same", "than",
    "too", "very", "just", "because", "as", "until", "while", "of",
    "at", "by", "for", "with", "about", "against", "between", "through",
    "during", "before", "after", "above", "below", "to", "from", "up",
    "down", "in", "out", "on", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how",
    "what", "which", "who", "whom", "this", "that", "these", "those",
    "i", "me", "my", "myself", "we", "our", "you", "your", "he", "him",
    "his", "she", "her", "it", "its", "they", "them", "their",
}

# --- Brand-relevant words that get bonus scoring weight ---
BRAND_BONUS_WORDS = config.BRAND_BONUS_WORDS


def _extract_content_words(text):
    """
    # Extracts meaningful words from text for relevance scoring
    # Strips punctuation, lowercases, removes stop words
    """
    words = re.findall(r'[a-z]+', text.lower())
    return {w for w in words if w not in STOP_WORDS and len(w) > 2}


def _score_video_relevance(video_meta, script_text, keywords, source="pexels"):
    """
    # Scores how well a stock video matches the script segment
    # Higher score = better match for the documentary
    #
    # Scoring factors:
    #   - Keyword overlap with video tags/URL (primary)
    #   - Script text overlap with metadata (semantic)
    #   - Brand bonus for history/documentary content
    #   - Resolution bonus for HD/4K footage
    #   - Penalty for avoid-keyword matches
    """
    score = 0.0

    # --- Extract searchable text from video metadata ---
    if source == "pexels":
        video_text = str(video_meta.get("url", "")).lower()
        video_text += " " + str(video_meta.get("image", "")).lower()
        user_name = str(video_meta.get("user", {}).get("name", "")).lower()
        video_text += " " + user_name
    else:
        # Pixabay has explicit tags field
        video_text = str(video_meta.get("tags", "")).lower()
        video_text += " " + str(video_meta.get("pageURL", "")).lower()

    video_words = set(re.findall(r'[a-z]+', video_text))

    # --- Score 1: Keyword overlap (strongest signal, up to 5 points) ---
    keyword_words = _extract_content_words(keywords)
    keyword_matches = keyword_words & video_words
    if keyword_words:
        score += (len(keyword_matches) / len(keyword_words)) * 5.0

    # --- Score 2: Script text overlap (semantic signal, up to 3 points) ---
    script_words = _extract_content_words(script_text)
    script_matches = script_words & video_words
    if script_words:
        score += (len(script_matches) / len(script_words)) * 3.0

    # --- Score 3: Brand bonus for history-related content (up to 2 points) ---
    brand_matches = BRAND_BONUS_WORDS & video_words
    score += min(len(brand_matches) * 0.4, 2.0)

    # --- Score 4: Resolution bonus ---
    # 4K = +1.0, HD = +0.5, below 720p = heavy penalty
    width = video_meta.get("width", 0)
    height = video_meta.get("height", 0)
    if width >= 3840 or height >= 3840:
        score += 1.0
    elif width >= 1920 or height >= 1920:
        score += 0.5
    elif width < 720 and height < 720 and width > 0:
        score -= 8.0

    # --- Penalty: avoid keywords reduce score ---
    for bad in AVOID_KEYWORDS:
        if bad in video_text:
            score -= 1.0

    return max(score, 0.0)


def _search_pexels_candidates(query, used_ids, orientation=None):
    """
    # Searches Pexels and returns candidate videos (without downloading)
    """
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": config.PEXELS_API_KEY}
    params = {
        "query": query,
        "orientation": orientation or config.PEXELS_ORIENTATION,
        "size": config.PEXELS_SIZE,
        "per_page": config.PEXELS_PER_PAGE,
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            return []

        data = response.json()
        videos = data.get("videos", [])
        if not videos:
            return []

        # --- Filter out used and unwanted videos ---
        available = _filter_videos(videos, used_ids)
        if not available:
            available = [v for v in videos if v["id"] not in used_ids] or videos

        return available

    except Exception as e:
        print(f"[VISUALS] Pexels candidates error: {e}")
        return []


def _search_pixabay_candidates(query, used_ids):
    """
    # Searches Pixabay and returns candidate videos (without downloading)
    """
    url = "https://pixabay.com/api/videos/"
    params = {
        "key": config.PIXABAY_API_KEY,
        "q": query,
        "video_type": "film",
        "per_page": 10,
        "safesearch": "true",
    }

    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return []

        data = response.json()
        hits = data.get("hits", [])
        if not hits:
            return []

        # --- Filter out used and unwanted content ---
        available = []
        for v in hits:
            vid_id = v.get("id", 0)
            if vid_id in used_ids:
                continue
            tags = str(v.get("tags", "")).lower()
            page_url = str(v.get("pageURL", "")).lower()
            skip = False
            for bad in AVOID_KEYWORDS:
                if bad in tags or bad in page_url:
                    skip = True
                    break
            if not skip:
                available.append(v)

        if not available:
            available = [v for v in hits if v.get("id", 0) not in used_ids] or hits

        return available

    except Exception as e:
        print(f"[VISUALS] Pixabay candidates error: {e}")
        return []


def _download_pexels_video(video_meta, output_dir, index):
    """
    # Downloads a specific Pexels video by its metadata
    """
    video_file = _get_best_pexels_file(video_meta)
    if not video_file:
        return None

    download_url = video_file["link"]
    file_path = os.path.join(output_dir, f"clip_{index:03d}.mp4")

    print(f"[VISUALS] Pexels downloading: {video_file.get('quality', '?')} "
          f"({video_file.get('width', '?')}x{video_file.get('height', '?')})")

    try:
        video_response = requests.get(download_url, stream=True)
        with open(file_path, "wb") as f:
            for chunk in video_response.iter_content(chunk_size=8192):
                f.write(chunk)
        return file_path
    except Exception as e:
        print(f"[VISUALS] Download error: {e}")
        return None


def _download_pixabay_video(video_meta, output_dir, index):
    """
    # Downloads a specific Pixabay video by its metadata
    """
    download_url, width, height = _get_best_pixabay_file(video_meta)
    if not download_url:
        return None

    file_path = os.path.join(output_dir, f"clip_{index:03d}.mp4")

    print(f"[VISUALS] Pixabay downloading: {width}x{height}")

    try:
        video_response = requests.get(download_url, stream=True)
        with open(file_path, "wb") as f:
            for chunk in video_response.iter_content(chunk_size=8192):
                f.write(chunk)
        return file_path
    except Exception as e:
        print(f"[VISUALS] Download error: {e}")
        return None


def search_and_download_videos(script_segments, output_dir, profile=None):
    """
    # For each script segment, searches Pexels + Pixabay with semantic matching
    # Uses multi-query search and relevance scoring to pick best footage
    #
    # Flow per segment:
    #   1. Build query list: primary + alt keywords + simplified fallback
    #   2. Search both Pexels and Pixabay with each query
    #   3. Score ALL candidates against script text
    #   4. Download the highest-scoring result
    #
    # Returns: list of file paths to downloaded video clips
    """
    os.makedirs(output_dir, exist_ok=True)
    downloaded_clips = []
    used_pexels_ids = set()
    used_pixabay_ids = set()

    # --- Check which APIs are available ---
    has_pexels = bool(config.PEXELS_API_KEY)
    has_pixabay = bool(config.PIXABAY_API_KEY)

    if not has_pexels and not has_pixabay:
        print("[VISUALS] ERROR: No API keys configured for Pexels or Pixabay!")
        return []

    # --- Enrich all segments with alt keywords via Gemini ---
    script_segments = enrich_visual_keywords(script_segments)

    # --- Format-specific search orientation ---
    orientation = profile.get("pexels_orientation", "landscape") if profile else "landscape"

    # --- Era-specific fallback queries ---
    # When primary search fails, try era-appropriate generic footage
    era_fallbacks = {
        "ancient": [
            "ancient ruins columns sunset", "greek temple marble dramatic sky",
            "roman colosseum historical", "egyptian pyramid desert golden",
            "ancient statue marble weathered", "mediterranean coast ancient",
        ],
        "medieval": [
            "medieval castle fortress dramatic", "stone castle walls fog",
            "cathedral gothic interior light", "medieval village cobblestone",
            "sword armor knight historical", "old fortress tower landscape",
        ],
        "colonial": [
            "old sailing ship ocean", "harbor port colonial architecture",
            "old map compass navigation", "cobblestone street old city",
            "lighthouse coast dramatic waves", "old wooden ship sea",
        ],
        "world_war_1": [
            "war memorial cemetery dramatic", "battlefield landscape fog",
            "military cemetery crosses rows", "old military equipment museum",
        ],
        "world_war_2": [
            "war memorial dramatic sky", "military museum tank historical",
            "battlefield memorial landscape", "old military ruins dramatic",
        ],
        "cold_war": [
            "berlin wall memorial", "military bunker cold war",
            "government building dramatic sky", "nuclear power plant industrial",
        ],
        "renaissance": [
            "renaissance painting museum gallery", "marble sculpture museum",
            "grand palace interior ornate", "florence cathedral dome aerial",
        ],
        "industrial": [
            "old factory industrial ruins", "steam train railway historical",
            "coal mine industrial dramatic", "old bridge iron structure",
        ],
        "modern": [
            "modern city skyline dramatic", "government parliament building",
            "diplomatic summit conference", "aerial city landscape sunset",
        ],
    }

    # --- Generic cinematic fallbacks (last resort) ---
    generic_fallbacks = [
        "ancient ruins dramatic sunset landscape", "medieval castle fog dramatic",
        "old map compass globe navigation", "dramatic mountain landscape clouds",
        "ocean waves dramatic cinematic sunset", "old library books manuscripts",
        "statue monument dramatic sky", "desert landscape dramatic golden hour",
        "foggy forest atmospheric cinematic", "aerial landscape river valley",
        "old stone bridge architecture", "dramatic clouds timelapse sky",
    ]

    for i, segment in enumerate(script_segments):
        keywords = segment.get("visual_keywords", "")
        script_text = segment.get("text", "")
        alt_keywords = segment.get("visual_keywords_alt", [])
        era = segment.get("era", "ancient")

        print(f"[VISUALS] ({i+1}/{len(script_segments)}) Searching: {keywords}")

        # --- Build the query list: primary + alts + simplified ---
        queries = [keywords]
        for alt in alt_keywords[:3]:
            if alt and alt != keywords:
                queries.append(alt)
        # --- Simplified 2-word version as fallback ---
        simple_words = keywords.split()[:2]
        simple_query = " ".join(simple_words)
        if simple_query != keywords:
            queries.append(simple_query)

        # --- Collect all candidates from all queries ---
        all_candidates = []

        for q_idx, query in enumerate(queries):
            # --- Search Pexels ---
            if has_pexels:
                pexels_results = _search_pexels_candidates(query, used_pexels_ids, orientation)
                for video_meta in pexels_results[:5]:
                    score = _score_video_relevance(video_meta, script_text, keywords, source="pexels")
                    all_candidates.append((score, video_meta, "pexels"))

            # --- Search Pixabay ---
            if has_pixabay:
                pixabay_results = _search_pixabay_candidates(query, used_pixabay_ids)
                for video_meta in pixabay_results[:5]:
                    score = _score_video_relevance(video_meta, script_text, keywords, source="pixabay")
                    all_candidates.append((score, video_meta, "pixabay"))

            # --- Rate limit between queries ---
            if q_idx < len(queries) - 1:
                time.sleep(0.5)

        # --- Sort candidates by relevance score (highest first) ---
        all_candidates.sort(key=lambda x: x[0], reverse=True)

        video_path = None

        if all_candidates:
            best_score = all_candidates[0][0]
            print(f"[VISUALS] Found {len(all_candidates)} candidates, best score: {best_score:.1f}")

            # --- Try downloading the highest-scored candidates ---
            for score, video_meta, source in all_candidates[:5]:
                if source == "pexels":
                    used_pexels_ids.add(video_meta["id"])
                    video_path = _download_pexels_video(video_meta, output_dir, i)
                else:
                    used_pixabay_ids.add(video_meta["id"])
                    video_path = _download_pixabay_video(video_meta, output_dir, i)

                if video_path:
                    print(f"[VISUALS] Selected ({source}, score={score:.1f}): {os.path.basename(video_path)}")
                    break

        # --- Era-specific fallbacks ---
        if not video_path:
            print(f"[VISUALS] Trying era-specific fallbacks for '{era}'...")
            fallbacks = era_fallbacks.get(era, generic_fallbacks)
            for fallback in fallbacks:
                if has_pexels:
                    candidates = _search_pexels_candidates(fallback, used_pexels_ids, orientation)
                    if candidates:
                        video_meta = candidates[0]
                        used_pexels_ids.add(video_meta["id"])
                        video_path = _download_pexels_video(video_meta, output_dir, i)
                if not video_path and has_pixabay:
                    candidates = _search_pixabay_candidates(fallback, used_pixabay_ids)
                    if candidates:
                        video_meta = candidates[0]
                        used_pixabay_ids.add(video_meta["id"])
                        video_path = _download_pixabay_video(video_meta, output_dir, i)
                if video_path:
                    break

        # --- Generic fallbacks (absolute last resort) ---
        if not video_path:
            print(f"[VISUALS] Trying generic cinematic fallbacks...")
            for fallback in generic_fallbacks:
                if has_pexels:
                    candidates = _search_pexels_candidates(fallback, used_pexels_ids, orientation)
                    if candidates:
                        video_meta = candidates[0]
                        used_pexels_ids.add(video_meta["id"])
                        video_path = _download_pexels_video(video_meta, output_dir, i)
                if video_path:
                    break

        if video_path:
            downloaded_clips.append(video_path)
        else:
            print(f"[VISUALS] WARNING: No clip found for segment {i+1}")

        # --- Respect API rate limits ---
        time.sleep(1)

    print(f"[VISUALS] Downloaded {len(downloaded_clips)} clips total")
    return downloaded_clips


# ============================================================
# SHARED HELPERS
# ============================================================

def _filter_videos(videos, used_ids):
    """
    # Filters Pexels video results: removes used IDs and unwanted content
    """
    available = []
    for v in videos:
        if v["id"] in used_ids:
            continue
        video_url = str(v.get("url", "")).lower()
        video_image = str(v.get("image", "")).lower()
        skip = False
        for bad in AVOID_KEYWORDS:
            if bad in video_url or bad in video_image:
                skip = True
                break
        if not skip:
            available.append(v)
    return available


def _get_best_pexels_file(video_data):
    """
    # Picks the best quality video file from Pexels response
    # For documentaries: prefer LANDSCAPE orientation, HD or higher
    """
    video_files = video_data.get("video_files", [])
    if not video_files:
        return None

    landscape_files = []
    portrait_files = []

    for vf in video_files:
        w = vf.get("width", 0)
        h = vf.get("height", 0)
        if w >= h:
            landscape_files.append(vf)
        else:
            portrait_files.append(vf)

    # --- Prefer landscape for documentary format ---
    candidates = landscape_files if landscape_files else portrait_files

    # --- Sort by resolution (higher is better) ---
    candidates.sort(key=lambda x: x.get("height", 0) * x.get("width", 0), reverse=True)

    # --- Return best quality (reasonable size) ---
    for vf in candidates:
        w = vf.get("width", 0)
        if 720 <= w <= 3840:
            return vf

    return candidates[0] if candidates else video_files[0]


def _get_best_pixabay_file(video_data):
    """
    # Picks the best quality video file from Pixabay response
    # Prefers large (1920px) > medium (1280px) > small (960px)
    """
    videos = video_data.get("videos", {})
    if not videos:
        return None, 0, 0

    for size_key in ["large", "medium", "small"]:
        vf = videos.get(size_key, {})
        url = vf.get("url", "")
        width = vf.get("width", 0)
        height = vf.get("height", 0)
        if url and width > 0:
            return url, width, height

    tiny = videos.get("tiny", {})
    if tiny.get("url"):
        return tiny["url"], tiny.get("width", 0), tiny.get("height", 0)

    return None, 0, 0


# --- Quick test ---
if __name__ == "__main__":
    test_segments = [
        {"visual_keywords": "ancient roman colosseum ruins dramatic sky", "era": "ancient"},
        {"visual_keywords": "medieval castle fortress fog landscape", "era": "medieval"},
        {"visual_keywords": "old sailing ship ocean waves dramatic", "era": "colonial"},
    ]
    clips = search_and_download_videos(test_segments, config.TEMP_DIR)
    print(f"\nDownloaded {len(clips)} test clips")

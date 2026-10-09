import os
import requests
import config

# ============================================================
# TIMELESS COMPASS — FLUX PRO IMAGE GENERATOR
# ============================================================
# Generates high-quality cinematic historical illustrations
# using fal.ai's Flux Pro v1.1 Ultra model.
#
# Used alongside Pexels stock footage — Gemini's script generator
# decides per-segment whether Flux or Pexels fits better:
#   - Battles, portraits, ancient scenes → Flux Pro (AI art)
#   - Real landmarks, nature, modern sites → Pexels (stock footage)
#
# Style consistency:
#   Every Flux prompt ends with a locked style suffix so all
#   AI-generated images share the same visual language across
#   the entire video. No random AI art salad.
#
# Cost: ~$0.06 per image (4MP resolution)
# ============================================================

# --- Cinematic documentary style suffix ---
# Appended to EVERY Flux prompt for visual consistency across the video.
# Describes: art style, color palette, lighting, mood, composition.
# This is the single most important thing for cohesive video quality.
STYLE_SUFFIX_LANDSCAPE = (
    "Cinematic oil painting style, dark moody earth tones, "
    "muted warm palette with deep amber and burnt sienna accents, "
    "dramatic chiaroscuro lighting with strong directional light, "
    "atmospheric fog and haze, epic wide-angle composition, "
    "rich textural detail, museum-quality brushwork, "
    "no text, no watermark, no UI elements, no modern objects, "
    "highly detailed, 8K resolution"
)

STYLE_SUFFIX_PORTRAIT = (
    "Cinematic oil painting style, dark moody earth tones, "
    "muted warm palette with deep amber and burnt sienna accents, "
    "dramatic chiaroscuro lighting with strong directional light, "
    "atmospheric fog and haze, dramatic vertical composition, "
    "rich textural detail, museum-quality brushwork, "
    "no text, no watermark, no UI elements, no modern objects, "
    "highly detailed, 8K resolution"
)

# --- Scene-type specific prompt prefixes ---
# These help Flux understand what KIND of historical scene to render.
# The script generator tags each segment with a visual_type.
SCENE_PREFIXES = {
    # --- Battle/conflict scenes need dynamic energy ---
    "battle": "An epic historical battle scene depicting ",
    # --- Portraits need regal, dramatic framing ---
    "portrait": "A dramatic historical portrait painting of ",
    # --- Landscapes need atmospheric, vast compositions ---
    "landscape": "A sweeping cinematic landscape of ",
    # --- Architecture needs monumental scale ---
    "architecture": "A grand architectural view of ",
    # --- Events need narrative composition ---
    "event": "A dramatic historical scene depicting ",
    # --- Maps/diagrams — Flux can't do these accurately, skip ---
    "map": None,
    # --- Default for untagged segments ---
    "scene": "A cinematic historical scene of ",
}


def generate_flux_image(prompt, output_path, aspect_ratio="16:9"):
    """
    # Generates a single high-quality image via fal.ai Flux Pro v1.1 Ultra.
    #
    # Args:
    #   prompt: scene description (style suffix appended automatically)
    #   output_path: where to save the PNG file
    #   aspect_ratio: "16:9" for landscape, "9:16" for portrait/shorts
    #
    # Returns:
    #   output_path on success, None on failure
    #
    # Caching: if output_path already exists and is >50KB, skips generation.
    # This integrates with the pipeline-level caching in main.py.
    """
    # --- Skip if already generated (cache hit) ---
    if os.path.exists(output_path) and os.path.getsize(output_path) > 50_000:
        print(f"[FLUX] CACHED -- {os.path.basename(output_path)}")
        return output_path

    # --- Check for FAL_KEY ---
    fal_key = config.FAL_KEY if hasattr(config, 'FAL_KEY') else os.getenv("FAL_KEY", "")
    if not fal_key:
        print("[FLUX] ERROR: FAL_KEY not set in .env — cannot generate Flux images")
        print("[FLUX] Get a key at https://fal.ai and add FAL_KEY=... to your .env")
        return None

    # --- Import fal client ---
    try:
        import fal_client
    except ImportError:
        try:
            import fal as fal_client
        except ImportError:
            print("[FLUX] ERROR: fal-client not installed. Run: pip install fal-client")
            return None

    # --- Pick style suffix based on aspect ratio ---
    style_suffix = STYLE_SUFFIX_PORTRAIT if aspect_ratio == "9:16" else STYLE_SUFFIX_LANDSCAPE

    # --- Build the full prompt: scene description + style lock ---
    full_prompt = f"{prompt}. {style_suffix}"

    # --- Ensure output directory exists ---
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    try:
        # --- Set FAL_KEY for the client ---
        os.environ["FAL_KEY"] = fal_key

        print(f"[FLUX] Generating: {prompt[:80]}...")

        # --- Call Flux Pro v1.1 Ultra (highest quality, 4MP) ---
        result = fal_client.subscribe(
            "fal-ai/flux-pro/v1.1-ultra",
            arguments={
                "prompt": full_prompt,
                "aspect_ratio": aspect_ratio,
                "num_images": 1,
                "output_format": "png",
                # --- raw=True gives more natural, less over-processed look ---
                "raw": True,
                # --- safety_tolerance 5 = permissive (battles, dark scenes) ---
                "safety_tolerance": "5",
            },
        )

        # --- Download the generated image ---
        if result and "images" in result and len(result["images"]) > 0:
            img_url = result["images"][0]["url"]
            resp = requests.get(img_url, timeout=30)
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                file_size = os.path.getsize(output_path) / 1024
                print(f"[FLUX] Saved: {os.path.basename(output_path)} ({file_size:.0f} KB)")
                return output_path

        print("[FLUX] Empty result from fal.ai")
        return None

    except Exception as e:
        print(f"[FLUX] Generation failed: {e}")
        return None


def generate_segment_image(segment, index, output_dir, aspect_ratio="16:9"):
    """
    # Generates a Flux Pro image for one script segment.
    #
    # Builds the prompt from the segment's visual_keywords + narration text,
    # prepends a scene-type prefix, and appends the style suffix.
    #
    # Args:
    #   segment: dict with text, visual_keywords, visual_type, era, etc.
    #   index: segment number (for filename)
    #   output_dir: directory to save images
    #   aspect_ratio: "16:9" or "9:16"
    #
    # Returns:
    #   path to generated image, or None on failure
    """
    # --- Extract scene info from segment ---
    visual_keywords = segment.get("visual_keywords", "")
    narration = segment.get("text", "")
    visual_type = segment.get("visual_type", "scene")
    era = segment.get("era", "")

    # --- Skip map segments (Flux can't do accurate maps) ---
    if visual_type == "map":
        print(f"[FLUX] Segment {index + 1}: map type, skipping (use Pexels instead)")
        return None

    # --- Get scene prefix ---
    prefix = SCENE_PREFIXES.get(visual_type, SCENE_PREFIXES["scene"])
    if prefix is None:
        return None

    # --- Build the scene description ---
    # Combine visual_keywords with key narration context for specificity.
    # Trim narration to first sentence for focus — too much text = confused output.
    first_sentence = narration.split(".")[0] if narration else ""

    # --- Era-specific details help Flux get the period right ---
    era_hints = {
        "ancient": "ancient world, classical antiquity",
        "medieval": "medieval period, Middle Ages",
        "renaissance": "Renaissance era, 15th-16th century",
        "colonial": "Age of Exploration, colonial era, 16th-18th century",
        "industrial": "Industrial Revolution, 19th century",
        "world_war_1": "World War I, early 20th century, 1914-1918",
        "world_war_2": "World War II, 1939-1945",
        "cold_war": "Cold War era, mid-20th century",
        "modern": "modern era, contemporary",
    }
    era_hint = era_hints.get(era, "")

    # --- Assemble the prompt ---
    # Structure: [prefix] + [keywords] + [context] + [era]
    prompt_parts = [prefix]

    if visual_keywords:
        prompt_parts.append(visual_keywords)

    if first_sentence and len(first_sentence) < 150:
        prompt_parts.append(f"depicting {first_sentence}")

    if era_hint:
        prompt_parts.append(f"set in the {era_hint}")

    prompt = ", ".join(prompt_parts)

    # --- Generate the image ---
    output_path = os.path.join(output_dir, f"flux_segment_{index:02d}.png")
    return generate_flux_image(prompt, output_path, aspect_ratio)


def generate_all_segment_images(segments, output_dir, aspect_ratio="16:9"):
    """
    # Generates Flux Pro images for all segments tagged as visual_source="flux".
    # Segments tagged as "pexels" are skipped (handled by visuals.py).
    #
    # Args:
    #   segments: list of script segment dicts
    #   output_dir: directory to save images
    #   aspect_ratio: "16:9" or "9:16"
    #
    # Returns:
    #   dict mapping segment index → image path (only Flux segments)
    """
    os.makedirs(output_dir, exist_ok=True)

    flux_images = {}
    flux_count = 0
    skip_count = 0

    for i, seg in enumerate(segments):
        source = seg.get("visual_source", "pexels")

        if source != "flux":
            skip_count += 1
            continue

        path = generate_segment_image(seg, i, output_dir, aspect_ratio)
        if path:
            flux_images[i] = path
            flux_count += 1

    print(f"[FLUX] Generated {flux_count} images, skipped {skip_count} (Pexels)")
    return flux_images

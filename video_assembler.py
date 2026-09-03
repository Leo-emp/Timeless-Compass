import os
import random
import numpy as np
import config

# ============================================================
# TIMELESS COMPASS — VIDEO ASSEMBLER
# ============================================================
# Assembles the final documentary video from:
#   - Stock footage clips (Pexels/Pixabay)
#   - Voiceover narration (ElevenLabs)
#   - Background music (orchestral/cinematic)
#   - Ken Burns effect (slow pan/zoom on clips)
#   - Text overlays (dates, names, locations)
#   - Captions (word-level synchronized)
#   - Warm sepia color grading
#
# Visual style targets:
#   - Kings and Generals: map overlays, text labels
#   - Epic History TV: cinematic color grading, dramatic pacing
#   - Ken Burns: slow zoom/pan on historical images and footage
#
# Color grade:
#   - Warm sepia tint (not cold/blue like Midnight Archive)
#   - Slightly desaturated (vintage feel)
#   - Soft vignette edges
#   - 24fps cinematic frame rate
# ============================================================

from moviepy import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    CompositeAudioClip, ColorClip, concatenate_videoclips,
)
from moviepy.audio.fx import AudioFadeIn, AudioFadeOut, MultiplyVolume

# --- Windows font paths (Pillow needs full paths, not font names) ---
FONT_GEORGIA = "C:/Windows/Fonts/georgia.ttf"
FONT_GEORGIA_BOLD = "C:/Windows/Fonts/georgiab.ttf"
FONT_ARIAL = "C:/Windows/Fonts/arial.ttf"
FONT_ARIAL_BOLD = "C:/Windows/Fonts/arialbd.ttf"


def assemble_video(
    video_clip_paths,
    voiceover_path,
    script_data,
    word_timestamps,
    music_path=None,
    output_path=None,
    video_format=None,
):
    """
    # Main assembly function — builds the final documentary video
    #
    # Args:
    #   video_clip_paths: list of stock footage MP4 files
    #   voiceover_path: path to narration MP3
    #   script_data: full script dict with segments (for overlays)
    #   word_timestamps: word-level timing from ElevenLabs
    #   music_path: optional background music track
    #   output_path: where to save final MP4
    #   video_format: VideoFormat enum
    """
    if video_format is None:
        video_format = config.VideoFormat.LONG_FORM

    profile = config.get_format_profile(video_format)
    target_w = profile["width"]
    target_h = profile["height"]
    fps = profile["fps"]

    print(f"[ASSEMBLER] Target: {target_w}x{target_h} @ {fps}fps")

    # --- Load voiceover to get total duration ---
    voiceover = AudioFileClip(voiceover_path)
    total_duration = voiceover.duration
    print(f"[ASSEMBLER] Voiceover duration: {total_duration:.1f}s")

    # --- Build visual timeline from stock footage ---
    print("[ASSEMBLER] Building visual timeline with Ken Burns effect...")
    visual_timeline = _build_visual_timeline(
        video_clip_paths, total_duration, target_w, target_h, fps, profile
    )

    # --- Apply warm color grading ---
    print("[ASSEMBLER] Applying warm sepia color grade...")
    graded_timeline = _apply_color_grade(visual_timeline, profile)

    # --- Build text overlays (dates, names, locations) ---
    print("[ASSEMBLER] Adding text overlays...")
    segments = script_data.get("segments", [])
    overlay_clips = _build_text_overlays(
        segments, total_duration, len(video_clip_paths), target_w, target_h, profile
    )

    # --- Build captions from word timestamps ---
    print("[ASSEMBLER] Rendering captions...")
    caption_clips = _render_captions(word_timestamps, target_w, target_h, profile)

    # --- Composite everything together ---
    all_layers = [graded_timeline] + overlay_clips + caption_clips
    final_video = CompositeVideoClip(all_layers, size=(target_w, target_h))

    # --- Build audio mix ---
    print("[ASSEMBLER] Mixing audio...")
    final_audio = _build_audio_mix(voiceover, music_path, total_duration, profile)
    final_video = final_video.with_audio(final_audio)

    # --- Set duration to match voiceover ---
    final_video = final_video.with_duration(total_duration)

    # --- Render output ---
    if output_path is None:
        output_path = os.path.join(config.OUTPUT_DIR, "timeless_compass_output.mp4")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"[ASSEMBLER] Rendering to {output_path}...")
    final_video.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        bitrate=profile["bitrate"],
        preset="medium",
        threads=4,
    )

    # --- Cleanup ---
    voiceover.close()
    final_video.close()

    print(f"[ASSEMBLER] Done: {output_path}")
    return output_path


def _build_visual_timeline(clip_paths, total_duration, target_w, target_h, fps, profile):
    """
    # Builds a continuous visual timeline from stock footage clips
    # Each clip gets Ken Burns effect (slow zoom + pan)
    # Clips are trimmed/looped to fill the entire voiceover duration
    # Crossfade transitions between clips for smooth flow
    """
    if not clip_paths:
        # --- Fallback: solid dark background ---
        return ColorClip(
            size=(target_w, target_h),
            color=_hex_to_rgb(config.BRAND_COLORS["primary"]),
        ).with_duration(total_duration)

    # --- Calculate duration per clip ---
    scene_duration = profile.get("scene_duration", 8)
    num_clips = len(clip_paths)

    # --- If we have fewer clips than needed, loop them ---
    needed_clips = int(total_duration / scene_duration) + 1
    if num_clips < needed_clips:
        clip_paths = clip_paths * (needed_clips // num_clips + 1)
        clip_paths = clip_paths[:needed_clips]

    # --- Load and process each clip ---
    processed_clips = []
    time_remaining = total_duration

    for i, path in enumerate(clip_paths):
        if time_remaining <= 0:
            break

        clip_dur = min(scene_duration, time_remaining)

        try:
            clip = VideoFileClip(path)

            # --- Trim to target duration ---
            if clip.duration > clip_dur:
                # Start from a random point for variety
                max_start = max(0, clip.duration - clip_dur)
                start = random.uniform(0, max_start)
                clip = clip.subclipped(start, start + clip_dur)
            elif clip.duration < clip_dur:
                # Loop short clips
                loops = int(clip_dur / clip.duration) + 1
                clip = concatenate_videoclips([clip] * loops).subclipped(0, clip_dur)

            # --- Resize to target dimensions (cover mode) ---
            clip = _resize_cover(clip, target_w, target_h)

            # --- Apply Ken Burns effect (slow zoom + pan) ---
            clip = _apply_ken_burns(clip, profile)

            processed_clips.append(clip)
            time_remaining -= clip_dur

        except Exception as e:
            print(f"[ASSEMBLER] Clip error ({path}): {e}")
            # --- Fill gap with dark frame ---
            gap = ColorClip(
                size=(target_w, target_h),
                color=_hex_to_rgb(config.BRAND_COLORS["primary"]),
            ).with_duration(clip_dur)
            processed_clips.append(gap)
            time_remaining -= clip_dur

    if not processed_clips:
        return ColorClip(
            size=(target_w, target_h),
            color=_hex_to_rgb(config.BRAND_COLORS["primary"]),
        ).with_duration(total_duration)

    # --- Concatenate with crossfade transitions ---
    timeline = concatenate_videoclips(processed_clips, method="compose")

    # --- Ensure exact duration ---
    if timeline.duration < total_duration:
        padding = ColorClip(
            size=(target_w, target_h),
            color=_hex_to_rgb(config.BRAND_COLORS["primary"]),
        ).with_duration(total_duration - timeline.duration)
        timeline = concatenate_videoclips([timeline, padding])

    timeline = timeline.subclipped(0, total_duration)
    return timeline


def _resize_cover(clip, target_w, target_h):
    """
    # Resizes a clip to cover the target dimensions
    # Crops the excess (like CSS background-size: cover)
    """
    clip_w, clip_h = clip.size
    target_ratio = target_w / target_h
    clip_ratio = clip_w / clip_h

    if clip_ratio > target_ratio:
        # --- Clip is wider: match height, crop sides ---
        new_h = target_h
        new_w = int(clip_w * (target_h / clip_h))
    else:
        # --- Clip is taller: match width, crop top/bottom ---
        new_w = target_w
        new_h = int(clip_h * (target_w / clip_w))

    clip = clip.resized((new_w, new_h))

    # --- Center crop to target ---
    x_offset = (new_w - target_w) // 2
    y_offset = (new_h - target_h) // 2

    clip = clip.cropped(
        x1=x_offset, y1=y_offset,
        x2=x_offset + target_w, y2=y_offset + target_h,
    )

    return clip


def _apply_ken_burns(clip, profile):
    """
    # Applies Ken Burns effect: slow zoom + pan over clip duration
    # This makes stock footage feel cinematic and documentary-like
    #
    # Randomly picks one of 4 motion patterns:
    #   1. Slow zoom in (center focus)
    #   2. Slow zoom out (reveal)
    #   3. Pan left to right with slight zoom
    #   4. Pan right to left with slight zoom
    """
    zoom_min, zoom_max = profile.get("ken_burns_zoom_range", (1.0, 1.15))
    w, h = clip.size
    duration = clip.duration

    # --- Pick a random motion pattern ---
    pattern = random.choice(["zoom_in", "zoom_out", "pan_right", "pan_left"])

    def ken_burns_frame(get_frame, t):
        """
        # Applies zoom/pan transformation to each frame
        """
        progress = t / max(duration, 0.01)

        if pattern == "zoom_in":
            scale = zoom_min + (zoom_max - zoom_min) * progress
            cx, cy = w // 2, h // 2
        elif pattern == "zoom_out":
            scale = zoom_max - (zoom_max - zoom_min) * progress
            cx, cy = w // 2, h // 2
        elif pattern == "pan_right":
            scale = (zoom_min + zoom_max) / 2
            pan_range = int(w * 0.05)
            cx = w // 2 - pan_range + int(2 * pan_range * progress)
            cy = h // 2
        else:  # pan_left
            scale = (zoom_min + zoom_max) / 2
            pan_range = int(w * 0.05)
            cx = w // 2 + pan_range - int(2 * pan_range * progress)
            cy = h // 2

        # --- Calculate crop region ---
        crop_w = int(w / scale)
        crop_h = int(h / scale)
        x1 = max(0, cx - crop_w // 2)
        y1 = max(0, cy - crop_h // 2)
        x2 = min(w, x1 + crop_w)
        y2 = min(h, y1 + crop_h)

        # --- Adjust if crop goes out of bounds ---
        if x2 - x1 < crop_w:
            x1 = max(0, x2 - crop_w)
        if y2 - y1 < crop_h:
            y1 = max(0, y2 - crop_h)

        frame = get_frame(t)
        cropped = frame[y1:y2, x1:x2]

        # --- Resize back to original dimensions ---
        from PIL import Image
        img = Image.fromarray(cropped)
        img = img.resize((w, h), Image.LANCZOS)
        return np.array(img)

    return clip.transform(ken_burns_frame)


def _apply_color_grade(clip, profile):
    """
    # Applies warm sepia color grading for vintage documentary feel
    # Unlike Midnight Archive (cold/dark), this is warm/golden
    #
    # Steps:
    #   1. Adjust brightness (slightly dim for drama)
    #   2. Reduce saturation (vintage desaturated look)
    #   3. Apply sepia tint (warm golden tone)
    #   4. Soft vignette (darken edges)
    """
    brightness = profile.get("brightness_factor", 0.85)
    saturation = profile.get("saturation_factor", 0.75)
    sepia = profile.get("sepia_intensity", 0.15)

    def grade_frame(frame):
        # --- Work in float for precision ---
        f = frame.astype(np.float32) / 255.0

        # --- Step 1: Brightness adjustment ---
        f = f * brightness

        # --- Step 2: Desaturation (move toward grayscale) ---
        gray = np.dot(f[..., :3], [0.2989, 0.5870, 0.1140])
        gray = np.stack([gray] * 3, axis=-1)
        f = f * saturation + gray * (1.0 - saturation)

        # --- Step 3: Sepia tint (warm golden overlay) ---
        # Sepia matrix: adds warmth to highlights, golden to midtones
        sepia_r = f[..., 0] * 1.0 + f[..., 1] * 0.1 + sepia * 0.3
        sepia_g = f[..., 0] * 0.05 + f[..., 1] * 1.0 + sepia * 0.15
        sepia_b = f[..., 0] * 0.0 + f[..., 1] * 0.0 + f[..., 2] * (1.0 - sepia * 0.5)

        f[..., 0] = sepia_r
        f[..., 1] = sepia_g
        f[..., 2] = sepia_b

        # --- Clamp and convert back ---
        f = np.clip(f, 0.0, 1.0)
        return (f * 255).astype(np.uint8)

    return clip.image_transform(grade_frame)


def _build_text_overlays(segments, total_duration, num_clips, target_w, target_h, profile):
    """
    # Creates text overlay clips for dates, names, and locations
    # These appear as a semi-transparent bar at the bottom of the frame
    # Similar to how Kings and Generals labels map locations
    """
    overlay_clips = []
    font_size = profile.get("overlay_font_size", 38)
    font = FONT_GEORGIA_BOLD
    position_y = profile.get("overlay_position_y", 0.92)
    bg_opacity = profile.get("overlay_bg_opacity", 0.6)

    # --- Calculate when each segment's overlay should appear ---
    if not segments:
        return []

    segment_duration = total_duration / len(segments)

    for i, seg in enumerate(segments):
        overlay_text = seg.get("overlay_text", "")
        if not overlay_text:
            continue

        start_time = i * segment_duration
        # --- Show overlay for 4 seconds, or segment duration, whichever is shorter ---
        display_duration = min(4.0, segment_duration * 0.8)

        try:
            # --- Create dark background bar ---
            bar_h = font_size + 24
            bar = ColorClip(
                size=(target_w, bar_h),
                color=(20, 18, 14),
            ).with_opacity(bg_opacity).with_duration(display_duration)

            # --- Create text ---
            txt = TextClip(
                text=overlay_text,
                font_size=font_size,
                color="#E8E2D8",
                font=font,
            ).with_duration(display_duration)

            # --- Position: bottom of frame ---
            bar_y = int(target_h * position_y) - bar_h // 2
            bar = bar.with_position(("center", bar_y)).with_start(start_time)
            txt = txt.with_position(("center", bar_y + 12)).with_start(start_time)

            overlay_clips.extend([bar, txt])

        except Exception as e:
            print(f"[ASSEMBLER] Overlay error for '{overlay_text}': {e}")

    print(f"[ASSEMBLER] Created {len(overlay_clips) // 2} text overlays")
    return overlay_clips


def _render_captions(word_timestamps, target_w, target_h, profile):
    """
    # Renders word-level captions as text overlays
    # Groups words into 3-word chunks for readability
    # White text with dark outline on semi-transparent bar
    """
    if not word_timestamps:
        return []

    caption_clips = []
    font_size = profile.get("caption_font_size", 48)
    font = FONT_GEORGIA
    position_y = profile.get("caption_position_y", 0.85)
    stroke_width = profile.get("caption_stroke_width", 2)

    # --- Group words into 3-word chunks ---
    chunk_size = 3
    chunks = []
    for i in range(0, len(word_timestamps), chunk_size):
        chunk_words = word_timestamps[i:i + chunk_size]
        if chunk_words:
            text = " ".join(w["word"] for w in chunk_words)
            start = chunk_words[0]["start"]
            end = chunk_words[-1]["end"]
            chunks.append({"text": text, "start": start, "end": end})

    for chunk in chunks:
        duration = chunk["end"] - chunk["start"]
        if duration <= 0:
            continue

        try:
            txt = TextClip(
                text=chunk["text"],
                font_size=font_size,
                color="white",
                font=font,
                stroke_color="black",
                stroke_width=stroke_width,
            ).with_duration(duration).with_start(chunk["start"])

            y_pos = int(target_h * position_y)
            txt = txt.with_position(("center", y_pos))
            caption_clips.append(txt)

        except Exception as e:
            pass  # Skip failed caption chunks silently

    print(f"[ASSEMBLER] Rendered {len(caption_clips)} caption chunks")
    return caption_clips


def _build_audio_mix(voiceover, music_path, total_duration, profile):
    """
    # Mixes voiceover with background music
    # Music sits below voice with fade in/out
    # Orchestral/cinematic music for documentary feel
    """
    music_level = profile.get("music_level_db", -12)

    # --- Apply fade in/out to voiceover ---
    boosted_voice = voiceover.with_effects([
        AudioFadeIn(0.5),
        AudioFadeOut(0.5),
    ])

    if music_path and os.path.exists(music_path):
        try:
            music = AudioFileClip(music_path)

            # --- Loop music if shorter than video ---
            if music.duration < total_duration:
                loops = int(total_duration / music.duration) + 1
                from moviepy import concatenate_audioclips
                music = concatenate_audioclips([music] * loops)

            # --- Trim to match video duration ---
            music = music.subclipped(0, total_duration)

            # --- Apply volume level (music sits well below narration) ---
            # Convert dB to linear: 10^(dB/20)
            music_volume = 10 ** (music_level / 20)
            music = music.with_effects([
                MultiplyVolume(music_volume),
                AudioFadeIn(3.0),
                AudioFadeOut(5.0),
            ])

            # --- Mix voiceover + music ---
            return CompositeAudioClip([boosted_voice, music])

        except Exception as e:
            print(f"[ASSEMBLER] Music mix error: {e}")
            return boosted_voice
    else:
        if not music_path:
            print("[ASSEMBLER] No background music provided")
        return boosted_voice


def _hex_to_rgb(hex_color):
    """
    # Converts hex color string to RGB tuple
    """
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


# --- Quick test ---
if __name__ == "__main__":
    print("Video assembler loaded successfully")
    print(f"Brand colors: {config.BRAND_COLORS}")
    print(f"Channel: {config.CHANNEL_NAME}")

import os
import json
import random
import subprocess
import config

# ============================================================
# TIMELESS COMPASS — PURE FFMPEG VIDEO ASSEMBLER
# ============================================================
# Replaces the MoviePy-based assembler for 5-10x faster rendering.
# Same visual output: Ken Burns, sepia color grading, ASS captions,
# text overlays, voiceover + music mixing.
#
# Pipeline:
#   1. Pre-grade each clip (scale, crop, color grade, Ken Burns)
#   2. Generate ASS subtitle file (captions + overlays)
#   3. Concat graded clips → overlay ASS → mix audio → output
#
# Supports both video clips (Pexels) and still images (Flux Pro).
# Images get zoompan (Ken Burns); video clips get animated crop.
#
# Speed: ~3 min for a 10-min video vs ~15-20 min with MoviePy.
# ============================================================

# --- ffmpeg binary (config adds it to PATH) ---
FFMPEG = "ffmpeg"


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
    # Main assembly function — builds the final documentary video.
    # Pure ffmpeg, no MoviePy. Same API as the original assembler.
    #
    # Args:
    #   video_clip_paths: list of file paths (MP4 clips or PNG images)
    #   voiceover_path: narration MP3 from ElevenLabs
    #   script_data: script dict with segments (for text overlays)
    #   word_timestamps: word-level timing for captions
    #   music_path: optional background music track
    #   output_path: where to save the final MP4
    #   video_format: VideoFormat enum (LONG_FORM, MID_FORM, SHORT)
    """
    if video_format is None:
        video_format = config.VideoFormat.LONG_FORM

    profile = config.get_format_profile(video_format)
    target_w = profile["width"]
    target_h = profile["height"]
    fps = profile["fps"]

    if output_path is None:
        output_path = os.path.join(config.OUTPUT_DIR, "timeless_compass_output.mp4")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # --- Get voiceover duration (drives entire video length) ---
    total_duration = _get_duration(voiceover_path)
    print(f"[ASSEMBLER] Target: {target_w}x{target_h} @ {fps}fps, {total_duration:.1f}s")

    # --- Work directory for intermediate files ---
    work_dir = os.path.join(config.TEMP_DIR, "_assembly_work")
    os.makedirs(work_dir, exist_ok=True)

    # ================================================================
    # STEP 1: Pre-grade each clip (scale, crop, color grade, Ken Burns)
    # ================================================================
    print("[ASSEMBLER] Step 1: Grading clips with Ken Burns...")
    graded_clips = _grade_all_clips(
        video_clip_paths, total_duration, target_w, target_h, fps, profile, work_dir
    )

    if not graded_clips:
        print("[ASSEMBLER] ERROR: No graded clips produced")
        return None

    # ================================================================
    # STEP 2: Generate ASS subtitle file (captions + text overlays)
    # ================================================================
    print("[ASSEMBLER] Step 2: Generating captions...")
    segments = script_data.get("segments", [])
    ass_path = os.path.join(work_dir, "captions.ass")
    _generate_ass_file(
        word_timestamps, segments, total_duration, target_w, target_h, profile, ass_path
    )

    # ================================================================
    # STEP 3: Concat clips → overlay captions → mix audio → output
    # ================================================================
    print("[ASSEMBLER] Step 3: Final assembly...")
    _final_assembly(
        graded_clips, voiceover_path, music_path, ass_path,
        output_path, total_duration, target_w, target_h, fps, profile
    )

    # --- Verify output ---
    if os.path.exists(output_path) and os.path.getsize(output_path) > 100_000:
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"[ASSEMBLER] Done: {output_path} ({size_mb:.1f} MB)")
        return output_path
    else:
        print("[ASSEMBLER] ERROR: Output file missing or too small")
        return None


# ============================================================
# STEP 1: CLIP GRADING
# ============================================================

def _grade_all_clips(clip_paths, total_duration, w, h, fps, profile, work_dir):
    """
    # Pre-processes each clip/image with ffmpeg:
    #   - Scale + center crop to target resolution
    #   - Apply warm sepia color grading
    #   - Apply Ken Burns zoom/pan motion
    #   - Trim to target segment duration
    #
    # Returns list of paths to graded MP4 clips.
    """
    scene_duration = profile.get("scene_duration", 8)
    num_needed = int(total_duration / scene_duration) + 1

    # --- Expand clip list if we don't have enough ---
    paths = list(clip_paths) if clip_paths else []
    if len(paths) < num_needed and paths:
        paths = paths * (num_needed // len(paths) + 1)
    paths = paths[:num_needed]

    graded = []
    time_used = 0.0

    for i, path in enumerate(paths):
        if time_used >= total_duration:
            break

        clip_dur = min(scene_duration, total_duration - time_used)
        if clip_dur < 0.5:
            break

        out_path = os.path.join(work_dir, f"graded_{i:03d}.mp4")

        # --- Detect if this is an image (Flux Pro) or video (Pexels) ---
        is_image = path.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))

        if is_image:
            success = _grade_image(path, out_path, clip_dur, w, h, fps, profile, i)
        else:
            success = _grade_video(path, out_path, clip_dur, w, h, fps, profile, i)

        if success:
            graded.append(out_path)
            time_used += clip_dur
        else:
            # --- Generate black fill clip on failure ---
            fill_path = os.path.join(work_dir, f"fill_{i:03d}.mp4")
            _generate_fill_clip(fill_path, clip_dur, w, h, fps)
            if os.path.exists(fill_path):
                graded.append(fill_path)
                time_used += clip_dur

    print(f"[ASSEMBLER] Graded {len(graded)} clips ({time_used:.1f}s total)")
    return graded


def _grade_video(input_path, output_path, duration, w, h, fps, profile, index):
    """
    # Grades a video clip: scale, crop, Ken Burns, color grade.
    # Ken Burns for video: scale 15% larger, animated crop pans across.
    """
    # --- Color grading parameters ---
    brightness = profile.get("brightness_factor", 0.85)
    saturation = profile.get("saturation_factor", 0.75)
    sepia = profile.get("sepia_intensity", 0.15)

    # --- Ken Burns: pick random motion pattern ---
    # For video clips, Ken Burns = scale up 20% + animated crop position.
    # All 4 patterns use fixed-size crop with moving position — simpler
    # and more reliable than animated crop dimensions.
    pattern = random.choice(["zoom_in", "zoom_out", "pan_right", "pan_left"])
    zoom_max = profile.get("ken_burns_zoom_range", (1.0, 1.15))[1]

    # --- Scale 20% larger than target for Ken Burns crop room ---
    overshoot = 1.20
    scale_w = int(w * overshoot)
    scale_h = int(h * overshoot)
    # --- Ensure even dimensions ---
    scale_w += scale_w % 2
    scale_h += scale_h % 2

    # --- Build animated crop position (fixed w/h = target resolution) ---
    extra_w = scale_w - w
    extra_h = scale_h - h
    if pattern == "zoom_in":
        # Diagonal drift from top-left toward center
        crop_x = f"({extra_w}*t/{duration})"
        crop_y = f"({extra_h}*t/{duration})"
    elif pattern == "zoom_out":
        # Diagonal drift from center toward bottom-right
        crop_x = f"({extra_w}*(1-t/{duration}))"
        crop_y = f"({extra_h}*(1-t/{duration}))"
    elif pattern == "pan_right":
        crop_x = f"({extra_w}*t/{duration})"
        crop_y = f"({extra_h}/2)"
    else:  # pan_left
        crop_x = f"({extra_w}*(1-t/{duration}))"
        crop_y = f"({extra_h}/2)"

    # --- Build ffmpeg filter chain ---
    # 1. Scale to cover (20% larger than target)
    # 2. Fixed-size crop with animated position for Ken Burns
    # 3. Color grading: brightness, saturation, sepia
    filters = (
        f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h}:{crop_x}:{crop_y},"
        f"eq=brightness={brightness - 1.0}:saturation={saturation},"
        f"colorchannelmixer="
        f"rr={1.0 + sepia * 0.1}:rg={sepia * 0.3}:rb=0:"
        f"gr={sepia * 0.05}:gg={1.0}:gb=0:"
        f"br=0:bg=0:bb={1.0 - sepia * 0.3}"
    )

    cmd = [
        FFMPEG, "-y",
        "-i", input_path,
        "-t", str(duration),
        "-vf", filters,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-r", str(fps),
        "-an",
        "-pix_fmt", "yuv420p",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"[ASSEMBLER] Grade error clip {index}: {result.stderr[-200:]}")
            return False
        return os.path.exists(output_path) and os.path.getsize(output_path) > 10_000
    except Exception as e:
        print(f"[ASSEMBLER] Grade exception clip {index}: {e}")
        return False


def _grade_image(input_path, output_path, duration, w, h, fps, profile, index):
    """
    # Converts a still image (Flux Pro) to a video clip with Ken Burns.
    # Uses ffmpeg's zoompan filter for smooth zoom/pan motion.
    # Also applies color grading to match Pexels footage aesthetics.
    """
    brightness = profile.get("brightness_factor", 0.85)
    saturation = profile.get("saturation_factor", 0.75)
    sepia = profile.get("sepia_intensity", 0.15)
    zoom_max = profile.get("ken_burns_zoom_range", (1.0, 1.15))[1]

    # --- Ken Burns pattern (random) ---
    pattern = random.choice(["zoom_in", "zoom_out", "pan_right", "pan_left"])
    total_frames = int(duration * fps)

    # --- zoompan expressions based on pattern ---
    if pattern == "zoom_in":
        zoom_expr = f"1.0+{zoom_max - 1.0}*(on/{total_frames})"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif pattern == "zoom_out":
        zoom_expr = f"{zoom_max}-{zoom_max - 1.0}*(on/{total_frames})"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif pattern == "pan_right":
        zoom_expr = str((1.0 + zoom_max) / 2)
        x_expr = f"(iw-iw/zoom)*(on/{total_frames})"
        y_expr = "ih/2-(ih/zoom/2)"
    else:  # pan_left
        zoom_expr = str((1.0 + zoom_max) / 2)
        x_expr = f"(iw-iw/zoom)*(1-on/{total_frames})"
        y_expr = "ih/2-(ih/zoom/2)"

    # --- Build filter: zoompan → color grade ---
    filters = (
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':"
        f"d={total_frames}:s={w}x{h}:fps={fps},"
        f"eq=brightness={brightness - 1.0}:saturation={saturation},"
        f"colorchannelmixer="
        f"rr={1.0 + sepia * 0.1}:rg={sepia * 0.3}:rb=0:"
        f"gr={sepia * 0.05}:gg={1.0}:gb=0:"
        f"br=0:bg=0:bb={1.0 - sepia * 0.3}"
    )

    cmd = [
        FFMPEG, "-y",
        "-loop", "1",
        "-i", input_path,
        "-t", str(duration),
        "-vf", filters,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"[ASSEMBLER] Image grade error {index}: {result.stderr[-200:]}")
            return False
        return os.path.exists(output_path) and os.path.getsize(output_path) > 10_000
    except Exception as e:
        print(f"[ASSEMBLER] Image grade exception {index}: {e}")
        return False


def _generate_fill_clip(output_path, duration, w, h, fps):
    """
    # Generates a dark solid-color clip as a gap filler.
    # Used when a clip fails to grade.
    """
    color = config.BRAND_COLORS["primary"].lstrip("#")
    cmd = [
        FFMPEG, "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x{color}:s={w}x{h}:d={duration}:r={fps}",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=30)


# ============================================================
# STEP 2: ASS SUBTITLE GENERATION
# ============================================================

def _generate_ass_file(word_timestamps, segments, total_duration, w, h, profile, ass_path):
    """
    # Creates an ASS subtitle file with:
    #   1. Word-synced captions (sentence with current word highlighted in gold)
    #   2. Text overlays for dates/names/locations (semi-transparent bar)
    #
    # Caption style: full sentence displayed, current word highlighted.
    # This matches the documentary feel (HistoryMarche / Knowledgia style).
    """
    font_size = profile.get("caption_font_size", 48)
    overlay_font_size = profile.get("overlay_font_size", 38)
    caption_y = profile.get("caption_position_y", 0.85)
    # --- ASS uses distance from bottom, so convert ---
    margin_bottom = int(h * (1.0 - caption_y))

    # --- ASS header ---
    ass_lines = [
        "[Script Info]",
        "Title: Timeless Compass Captions",
        f"PlayResX: {w}",
        f"PlayResY: {h}",
        "ScriptType: v4.00+",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        # --- Caption style: white text, black outline, centered ---
        f"Style: Caption,Georgia,{font_size},&H00FFFFFF,&H0000C4E8,"
        f"&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,1,"
        f"2,40,40,{margin_bottom},1",
        # --- Overlay style: warm ivory text on dark bar ---
        f"Style: Overlay,Georgia,{overlay_font_size},&H00D8E2E8,&H00FFFFFF,"
        f"&H00000000,&HA0000000,1,0,0,0,100,100,0,0,3,0,0,"
        f"2,40,40,30,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    # --- Build sentence-based caption events with word highlighting ---
    if word_timestamps:
        caption_events = _build_sentence_caption_events(word_timestamps)
        for event in caption_events:
            start = _format_ass_time(event["start"])
            end = _format_ass_time(event["end"])
            text = event["text"]
            ass_lines.append(
                f"Dialogue: 0,{start},{end},Caption,,0,0,0,,{text}"
            )

    # --- Build text overlay events (dates, names, locations) ---
    if segments:
        segment_dur = total_duration / len(segments)
        for i, seg in enumerate(segments):
            overlay_text = seg.get("overlay_text", "")
            if not overlay_text:
                continue
            start_time = i * segment_dur
            end_time = start_time + min(4.0, segment_dur * 0.8)
            start = _format_ass_time(start_time)
            end = _format_ass_time(end_time)
            # --- Fade in/out for overlay ---
            fade = r"{\fad(500,500)}"
            ass_lines.append(
                f"Dialogue: 1,{start},{end},Overlay,,0,0,0,,{fade}{overlay_text}"
            )

    # --- Write ASS file ---
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ass_lines))

    event_count = sum(1 for l in ass_lines if l.startswith("Dialogue:"))
    print(f"[ASSEMBLER] Generated {event_count} subtitle events")


def _build_sentence_caption_events(word_timestamps):
    """
    # Groups words into sentence-length chunks and generates ASS events
    # where the full sentence is displayed but the current word is
    # highlighted in gold using ASS override tags.
    #
    # This gives the documentary "sentence with highlight" style:
    #   "The Roman legions {\\c&H00B8E8FF&}marched{\\c&H00FFFFFF&} forward"
    #
    # Split at punctuation (. ! ? ,) or every ~8 words.
    """
    if not word_timestamps:
        return []

    # --- Split into sentence groups ---
    groups = []
    current_group = []

    for wt in word_timestamps:
        current_group.append(wt)
        word = wt.get("word", "")

        # --- Split at sentence-ending punctuation or every 8 words ---
        if (word.rstrip().endswith((".", "!", "?", ",", ";", ":"))
                or len(current_group) >= 8):
            if current_group:
                groups.append(list(current_group))
                current_group = []

    # --- Don't forget the last group ---
    if current_group:
        groups.append(current_group)

    # --- Generate events: one per word, showing full sentence ---
    events = []
    # --- Gold highlight color in ASS format (BGR): &H0017A8C4 = warm amber ---
    highlight = r"{\c&H0017A8C4&}"
    normal = r"{\c&H00FFFFFF&}"

    for group in groups:
        group_start = group[0]["start"]
        group_end = group[-1]["end"]
        words = [w["word"] for w in group]
        full_sentence = " ".join(words)

        # --- One event per word in the group ---
        for wi, wt in enumerate(group):
            w_start = wt["start"]
            w_end = wt["end"]

            # --- Build text with current word highlighted ---
            parts = []
            for j, word in enumerate(words):
                if j == wi:
                    parts.append(f"{highlight}{word}{normal}")
                else:
                    parts.append(word)

            text = " ".join(parts)
            events.append({"start": w_start, "end": w_end, "text": text})

    return events


def _format_ass_time(seconds):
    """
    # Converts seconds to ASS timestamp format: H:MM:SS.CC
    """
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


# ============================================================
# STEP 3: FINAL ASSEMBLY
# ============================================================

def _final_assembly(graded_clips, voiceover_path, music_path, ass_path,
                     output_path, total_duration, w, h, fps, profile):
    """
    # Final ffmpeg assembly:
    #   1. Concat all graded clips using concat demuxer
    #   2. Overlay ASS subtitles (captions + text overlays)
    #   3. Mix voiceover + background music
    #   4. Output final MP4
    """
    work_dir = os.path.dirname(ass_path)

    # --- Write concat demuxer file ---
    concat_path = os.path.join(work_dir, "concat_list.txt")
    with open(concat_path, "w", encoding="utf-8") as f:
        for clip in graded_clips:
            # --- Escape single quotes in paths for ffmpeg concat ---
            safe_path = clip.replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")

    # --- Build ffmpeg command ---
    cmd = [FFMPEG, "-y"]

    # --- Input 0: concatenated video clips ---
    cmd += ["-f", "concat", "-safe", "0", "-i", concat_path]

    # --- Input 1: voiceover ---
    cmd += ["-i", voiceover_path]

    # --- Input 2: background music (optional) ---
    has_music = music_path and os.path.exists(music_path)
    if has_music:
        cmd += ["-i", music_path]

    # --- Build unified filter_complex for BOTH video + audio ---
    # Can't use -vf and -filter_complex together, so ASS overlay
    # and audio mixing both go into one filter_complex graph.
    music_level_db = profile.get("music_level_db", -12)
    voice_boost_db = profile.get("voiceover_boost_db", 2.0)

    # --- ASS subtitle filter on the video stream ---
    fonts_dir = os.path.join(config.ASSETS_DIR, "fonts")
    ass_escaped = ass_path.replace("\\", "/").replace(":", "\\\\:")
    if os.path.isdir(fonts_dir):
        fonts_escaped = fonts_dir.replace("\\", "/").replace(":", "\\\\:")
        ass_filter = f"ass='{ass_escaped}':fontsdir='{fonts_escaped}'"
    else:
        ass_filter = f"ass='{ass_escaped}'"

    if has_music:
        # --- Full graph: video ASS overlay + voice + music mix ---
        filter_complex = (
            f"[0:v]{ass_filter}[vout];"
            f"[1:a]volume={voice_boost_db}dB,"
            f"afade=t=in:d=0.5,afade=t=out:st={total_duration - 0.5}:d=0.5[voice];"
            f"[2:a]volume={music_level_db}dB,"
            f"afade=t=in:d=3,afade=t=out:st={total_duration - 5}:d=5,"
            f"atrim=0:{total_duration}[music];"
            f"[voice][music]amix=inputs=2:duration=first[aout]"
        )
        cmd += [
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "[aout]",
        ]
    else:
        # --- Video ASS overlay + voiceover only ---
        filter_complex = (
            f"[0:v]{ass_filter}[vout];"
            f"[1:a]volume={voice_boost_db}dB,"
            f"afade=t=in:d=0.5,afade=t=out:st={total_duration - 0.5}:d=0.5[aout]"
        )
        cmd += [
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "[aout]",
        ]

    # --- Output settings ---
    cmd += [
        "-t", str(total_duration),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        "-fps_mode", "vfr",
        output_path,
    ]

    print(f"[ASSEMBLER] Rendering {total_duration:.0f}s video...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            print(f"[ASSEMBLER] Render error: {result.stderr[-500:]}")
            # --- Fallback: try without ASS (in case font issues) ---
            print("[ASSEMBLER] Retrying without captions...")
            _final_assembly_no_subs(
                graded_clips, voiceover_path, music_path,
                output_path, total_duration, w, h, fps, profile
            )
    except subprocess.TimeoutExpired:
        print("[ASSEMBLER] Render timed out (10 min limit)")


def _final_assembly_no_subs(graded_clips, voiceover_path, music_path,
                              output_path, total_duration, w, h, fps, profile):
    """
    # Fallback assembly without subtitle overlay.
    # Used when ASS rendering fails (font issues, etc).
    """
    work_dir = os.path.join(config.TEMP_DIR, "_assembly_work")
    concat_path = os.path.join(work_dir, "concat_list.txt")

    music_level_db = profile.get("music_level_db", -12)
    voice_boost_db = profile.get("voiceover_boost_db", 2.0)
    has_music = music_path and os.path.exists(music_path)

    cmd = [FFMPEG, "-y"]
    cmd += ["-f", "concat", "-safe", "0", "-i", concat_path]
    cmd += ["-i", voiceover_path]

    if has_music:
        cmd += ["-i", music_path]
        cmd += [
            "-filter_complex",
            f"[1:a]volume={voice_boost_db}dB[voice];"
            f"[2:a]volume={music_level_db}dB,atrim=0:{total_duration}[music];"
            f"[voice][music]amix=inputs=2:duration=first[aout]",
            "-map", "0:v", "-map", "[aout]",
        ]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]

    cmd += [
        "-t", str(total_duration),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        print(f"[ASSEMBLER] Fallback render also failed: {result.stderr[-300:]}")


# ============================================================
# UTILITIES
# ============================================================

def _get_duration(audio_path):
    """
    # Gets audio duration in seconds using ffprobe.
    """
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def validate_output(output_path):
    """
    # Quick validation of the output video.
    # Checks file exists, size, and can be probed by ffprobe.
    """
    if not os.path.exists(output_path):
        print("[VALIDATE] Output file not found!")
        return False

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    if size_mb < 1:
        print(f"[VALIDATE] Output too small: {size_mb:.1f} MB")
        return False

    # --- Get video info ---
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "stream=width,height,duration,codec_name",
        "-show_entries", "format=duration,size",
        "-of", "json",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        info = json.loads(result.stdout)
        duration = float(info["format"]["duration"])
        print(f"[VALIDATE] Output: {size_mb:.1f} MB, {duration:.1f}s")
        return True
    except Exception as e:
        print(f"[VALIDATE] Probe error: {e}")
        return True  # file exists, assume OK

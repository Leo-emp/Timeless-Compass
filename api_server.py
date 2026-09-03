import os
import sys
import time
import threading
import json
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional

import database as db
import youtube_uploader as yt
import config
from main import run_pipeline
from config import VideoFormat

# ============================================================
# TIMELESS COMPASS — API SERVER
# ============================================================
# FastAPI backend powering the Next.js dashboard.
#
# Runs the video generation pipeline as background jobs,
# tracks progress, manages schedules, handles YouTube uploads.
#
# Start:  uvicorn api_server:app --reload --port 8000
# ============================================================

app = FastAPI(title="Timeless Compass API", version="1.0.0")

# --- Allow Next.js dashboard to call the API ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Track running jobs in memory ---
active_jobs = {}


# ============================================================
# REQUEST MODELS
# ============================================================

class GenerateRequest(BaseModel):
    topic: Optional[str] = None
    format: str = "long"
    quality: str = "1080p"

class ScheduleRequest(BaseModel):
    name: str
    frequency: str = "daily"
    days_of_week: str = "1,3,5"
    time_of_day: str = "09:00"
    format: str = "long"
    quality: str = "1080p"
    topic_mode: str = "auto"
    auto_upload: bool = False

class ScheduleUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    frequency: Optional[str] = None
    days_of_week: Optional[str] = None
    time_of_day: Optional[str] = None
    format: Optional[str] = None
    auto_upload: Optional[bool] = None


# ============================================================
# DASHBOARD STATS
# ============================================================

@app.get("/api/stats")
def get_stats():
    """
    # Returns dashboard overview statistics
    """
    stats = db.get_stats()

    # --- Add API key status ---
    stats["api_keys"] = {
        "gemini": bool(config.GEMINI_API_KEY),
        "elevenlabs": bool(config.ELEVENLABS_API_KEY),
        "pexels": bool(config.PEXELS_API_KEY),
        "pixabay": bool(config.PIXABAY_API_KEY),
        "youtube": yt.is_authenticated(),
    }

    return stats


# ============================================================
# VIDEO GENERATION JOBS
# ============================================================

def _run_generation(job_id, topic, video_format, quality):
    """
    # Background thread: runs the full pipeline and updates job status
    """
    try:
        # --- Mark as running ---
        db.update_job(job_id, status="running", started_at=time.time(),
                      progress=5, progress_message="Starting pipeline...")

        # --- Map format string to enum ---
        format_map = {
            "long": VideoFormat.LONG_FORM,
            "mid": VideoFormat.MID_FORM,
            "short": VideoFormat.SHORT,
        }
        fmt = format_map.get(video_format, VideoFormat.LONG_FORM)

        # --- Update progress at each stage ---
        db.update_job(job_id, progress=10, progress_message="Generating script...")

        # --- Run the pipeline ---
        result = run_pipeline(topic=topic, video_format=fmt, quality=quality)

        if result:
            # --- Create video record ---
            metadata_path = result.get("metadata_path", "")
            metadata = {}
            if metadata_path and os.path.exists(metadata_path):
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

            video_id = db.create_video(
                job_id=job_id,
                title=metadata.get("title", result.get("topic_title", "Untitled")),
                description=metadata.get("description", ""),
                tags=metadata.get("tags", []),
                output_path=result["output_path"],
                file_size_mb=result["file_size_mb"],
                duration_seconds=result["duration"],
                format=video_format,
                quality=quality,
            )

            db.update_job(
                job_id,
                status="completed",
                completed_at=time.time(),
                progress=100,
                progress_message="Video ready!",
                video_id=video_id,
            )
        else:
            db.update_job(
                job_id,
                status="failed",
                completed_at=time.time(),
                progress=0,
                progress_message="Pipeline returned no output",
                error="Pipeline failed — check ElevenLabs quota or API keys",
            )

    except Exception as e:
        db.update_job(
            job_id,
            status="failed",
            completed_at=time.time(),
            progress=0,
            progress_message=str(e)[:200],
            error=str(e),
        )
    finally:
        # --- Remove from active jobs ---
        active_jobs.pop(job_id, None)


@app.post("/api/generate")
def start_generation(req: GenerateRequest):
    """
    # Starts a new video generation job in the background
    """
    # --- Check if a job is already running ---
    running = db.list_jobs(status="running")
    if running:
        raise HTTPException(400, "A generation job is already running. Wait for it to finish.")

    # --- Create the job ---
    job_id = db.create_job(topic=req.topic, format=req.format, quality=req.quality)

    # --- Start background thread ---
    thread = threading.Thread(
        target=_run_generation,
        args=(job_id, req.topic, req.format, req.quality),
        daemon=True,
    )
    thread.start()
    active_jobs[job_id] = thread

    return {"job_id": job_id, "status": "queued"}


@app.get("/api/jobs")
def list_jobs(limit: int = 20, status: Optional[str] = None):
    """
    # Returns recent generation jobs
    """
    return db.list_jobs(limit=limit, status=status)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    """
    # Returns a single job's details and progress
    """
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


# ============================================================
# VIDEOS
# ============================================================

@app.get("/api/videos")
def list_videos(limit: int = 50):
    """
    # Returns all completed videos
    """
    return db.list_videos(limit=limit)


@app.get("/api/videos/{video_id}")
def get_video(video_id: str):
    """
    # Returns a single video's details
    """
    video = db.get_video(video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    return video


@app.delete("/api/videos/{video_id}")
def delete_video(video_id: str):
    """
    # Deletes a video record (keeps the file)
    """
    video = db.get_video(video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    db.delete_video(video_id)
    return {"deleted": True}


@app.get("/api/videos/{video_id}/file")
def serve_video_file(video_id: str):
    """
    # Serves the actual video file for preview/download
    """
    video = db.get_video(video_id)
    if not video:
        raise HTTPException(404, "Video not found")

    path = video.get("output_path", "")
    if not path or not os.path.exists(path):
        raise HTTPException(404, "Video file not found on disk")

    return FileResponse(path, media_type="video/mp4", filename=os.path.basename(path))


# ============================================================
# SCHEDULES
# ============================================================

@app.get("/api/schedules")
def list_schedules():
    """
    # Returns all schedules
    """
    return db.list_schedules()


@app.post("/api/schedules")
def create_schedule(req: ScheduleRequest):
    """
    # Creates a new generation schedule
    """
    schedule_id = db.create_schedule(
        name=req.name,
        frequency=req.frequency,
        days_of_week=req.days_of_week,
        time_of_day=req.time_of_day,
        format=req.format,
        quality=req.quality,
        topic_mode=req.topic_mode,
        auto_upload=req.auto_upload,
    )
    return {"schedule_id": schedule_id}


@app.patch("/api/schedules/{schedule_id}")
def update_schedule(schedule_id: str, req: ScheduleUpdateRequest):
    """
    # Updates a schedule's settings
    """
    schedule = db.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")

    updates = {}
    if req.enabled is not None:
        updates["enabled"] = 1 if req.enabled else 0
    if req.frequency:
        updates["frequency"] = req.frequency
    if req.days_of_week:
        updates["days_of_week"] = req.days_of_week
    if req.time_of_day:
        updates["time_of_day"] = req.time_of_day
    if req.format:
        updates["format"] = req.format
    if req.auto_upload is not None:
        updates["auto_upload"] = 1 if req.auto_upload else 0

    if updates:
        db.update_schedule(schedule_id, **updates)

    return db.get_schedule(schedule_id)


@app.delete("/api/schedules/{schedule_id}")
def delete_schedule(schedule_id: str):
    """
    # Deletes a schedule
    """
    schedule = db.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    db.delete_schedule(schedule_id)
    return {"deleted": True}


# ============================================================
# YOUTUBE
# ============================================================

@app.get("/api/youtube/status")
def youtube_status():
    """
    # Returns YouTube connection status
    """
    return {
        "authenticated": yt.is_authenticated(),
        "client_id_set": bool(os.getenv("YOUTUBE_CLIENT_ID", "")),
    }


@app.get("/api/youtube/auth-url")
def youtube_auth_url():
    """
    # Returns the YouTube OAuth authorization URL
    """
    url = yt.get_auth_url()
    if not url:
        raise HTTPException(400, "YOUTUBE_CLIENT_ID not set in .env")
    return {"url": url}


@app.get("/api/youtube/callback")
def youtube_callback(code: str = Query(...)):
    """
    # OAuth callback — exchanges code for tokens
    """
    success = yt.exchange_code(code)
    if success:
        # --- Redirect back to dashboard settings ---
        return RedirectResponse("http://localhost:3000/settings?youtube=connected")
    raise HTTPException(400, "Token exchange failed")


@app.post("/api/youtube/upload/{video_id}")
def upload_to_youtube(video_id: str):
    """
    # Uploads a video to YouTube
    """
    video = db.get_video(video_id)
    if not video:
        raise HTTPException(404, "Video not found")

    if not yt.is_authenticated():
        raise HTTPException(400, "YouTube not connected — authorize first")

    path = video.get("output_path", "")
    if not path or not os.path.exists(path):
        raise HTTPException(404, "Video file not found on disk")

    # --- Upload in background thread ---
    def _upload():
        try:
            db.update_video(video_id, youtube_status="uploading")
            url = yt.upload_video(
                video_path=path,
                title=video.get("title", "Untitled"),
                description=video.get("description", ""),
                tags=video.get("tags", []),
            )
            if url:
                db.update_video(video_id,
                                youtube_url=url,
                                youtube_status="uploaded",
                                uploaded_at=time.time())
            else:
                db.update_video(video_id, youtube_status="failed")
        except Exception as e:
            db.update_video(video_id, youtube_status="failed")
            print(f"[YOUTUBE] Upload error: {e}")

    thread = threading.Thread(target=_upload, daemon=True)
    thread.start()

    return {"status": "uploading", "video_id": video_id}


# ============================================================
# SCHEDULER RUNNER
# ============================================================

def _run_scheduler():
    """
    # Background thread: checks schedules every minute
    # and triggers generation when a schedule is due
    """
    import datetime

    while True:
        try:
            schedules = db.list_schedules()
            now = datetime.datetime.now()

            for sched in schedules:
                if not sched.get("enabled"):
                    continue

                # --- Check if it's time to run ---
                time_str = sched.get("time_of_day", "09:00")
                hour, minute = map(int, time_str.split(":"))
                days = [int(d) for d in sched.get("days_of_week", "1,3,5").split(",")]

                # --- Python weekday: 0=Monday, 6=Sunday ---
                if now.weekday() not in days:
                    continue

                if now.hour != hour or now.minute != minute:
                    continue

                # --- Check if already ran today ---
                last_run = sched.get("last_run")
                if last_run:
                    last_dt = datetime.datetime.fromtimestamp(last_run)
                    if last_dt.date() == now.date():
                        continue

                # --- Time to generate! ---
                print(f"[SCHEDULER] Triggering: {sched['name']}")
                db.update_schedule(sched["id"], last_run=time.time())

                job_id = db.create_job(
                    topic=None,
                    format=sched.get("format", "long"),
                    quality=sched.get("quality", "1080p"),
                )
                thread = threading.Thread(
                    target=_run_generation,
                    args=(job_id, None, sched.get("format", "long"), sched.get("quality", "1080p")),
                    daemon=True,
                )
                thread.start()
                active_jobs[job_id] = thread

        except Exception as e:
            print(f"[SCHEDULER] Error: {e}")

        # --- Check every 60 seconds ---
        time.sleep(60)


# --- Start scheduler on server boot ---
@app.on_event("startup")
def startup():
    scheduler_thread = threading.Thread(target=_run_scheduler, daemon=True)
    scheduler_thread.start()
    print("[SCHEDULER] Background scheduler started")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import uvicorn
    print("\n  Timeless Compass API Server")
    print("  http://localhost:8000")
    print("  http://localhost:8000/docs  (Swagger UI)\n")
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)

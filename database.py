import os
import sqlite3
import json
import time
import uuid

# ============================================================
# TIMELESS COMPASS — DATABASE LAYER
# ============================================================
# SQLite database for tracking video generation jobs,
# completed videos, schedules, and YouTube tokens.
#
# Tables:
#   jobs     — generation jobs with status tracking
#   videos   — completed videos with metadata
#   schedules — cron schedules for auto-generation
# ============================================================

DB_PATH = os.path.join(os.path.dirname(__file__), "timeless_compass.db")


def get_db():
    """
    # Returns a connection to the SQLite database
    # Creates tables on first use
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """
    # Creates all tables if they don't exist
    """
    conn = get_db()
    conn.executescript("""
        -- Jobs table: tracks each video generation run
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            topic TEXT,
            format TEXT DEFAULT 'long',
            quality TEXT DEFAULT '1080p',
            status TEXT DEFAULT 'queued',
            progress INTEGER DEFAULT 0,
            progress_message TEXT DEFAULT '',
            created_at REAL,
            started_at REAL,
            completed_at REAL,
            error TEXT,
            video_id TEXT
        );

        -- Videos table: completed videos with metadata
        CREATE TABLE IF NOT EXISTS videos (
            id TEXT PRIMARY KEY,
            job_id TEXT,
            title TEXT,
            description TEXT,
            tags TEXT,
            output_path TEXT,
            thumbnail_path TEXT,
            file_size_mb REAL,
            duration_seconds REAL,
            format TEXT,
            quality TEXT,
            youtube_url TEXT,
            youtube_status TEXT DEFAULT 'not_uploaded',
            created_at REAL,
            uploaded_at REAL,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );

        -- Schedules table: automated generation schedules
        CREATE TABLE IF NOT EXISTS schedules (
            id TEXT PRIMARY KEY,
            name TEXT,
            frequency TEXT DEFAULT 'daily',
            days_of_week TEXT DEFAULT '1,3,5',
            time_of_day TEXT DEFAULT '09:00',
            format TEXT DEFAULT 'long',
            quality TEXT DEFAULT '1080p',
            topic_mode TEXT DEFAULT 'auto',
            auto_upload INTEGER DEFAULT 0,
            enabled INTEGER DEFAULT 1,
            last_run REAL,
            next_run REAL,
            created_at REAL
        );

        -- Indexes for common queries
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_videos_created ON videos(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_schedules_enabled ON schedules(enabled);
    """)
    conn.commit()
    conn.close()


# ============================================================
# JOB OPERATIONS
# ============================================================

def create_job(topic=None, format="long", quality="1080p"):
    """
    # Creates a new generation job and returns its ID
    """
    job_id = str(uuid.uuid4())[:8]
    conn = get_db()
    conn.execute(
        "INSERT INTO jobs (id, topic, format, quality, status, created_at) VALUES (?, ?, ?, ?, 'queued', ?)",
        (job_id, topic, format, quality, time.time())
    )
    conn.commit()
    conn.close()
    return job_id


def update_job(job_id, **kwargs):
    """
    # Updates a job's fields (status, progress, error, etc.)
    """
    conn = get_db()
    sets = []
    values = []
    for key, val in kwargs.items():
        sets.append(f"{key} = ?")
        values.append(val)
    values.append(job_id)
    conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def get_job(job_id):
    """
    # Returns a single job by ID
    """
    conn = get_db()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_jobs(limit=50, status=None):
    """
    # Returns recent jobs, optionally filtered by status
    """
    conn = get_db()
    if status:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============================================================
# VIDEO OPERATIONS
# ============================================================

def create_video(job_id, title, description, tags, output_path,
                 file_size_mb, duration_seconds, format, quality):
    """
    # Creates a video record after successful generation
    """
    video_id = str(uuid.uuid4())[:8]
    conn = get_db()
    conn.execute(
        """INSERT INTO videos
        (id, job_id, title, description, tags, output_path, file_size_mb,
         duration_seconds, format, quality, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (video_id, job_id, title, description, json.dumps(tags),
         output_path, file_size_mb, duration_seconds, format, quality, time.time())
    )
    conn.commit()
    conn.close()
    return video_id


def get_video(video_id):
    """
    # Returns a single video by ID
    """
    conn = get_db()
    row = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        # --- Parse tags JSON ---
        if d.get("tags"):
            try:
                d["tags"] = json.loads(d["tags"])
            except (json.JSONDecodeError, TypeError):
                d["tags"] = []
        return d
    return None


def list_videos(limit=50):
    """
    # Returns recent videos sorted by creation date
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM videos ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        if d.get("tags"):
            try:
                d["tags"] = json.loads(d["tags"])
            except (json.JSONDecodeError, TypeError):
                d["tags"] = []
        results.append(d)
    return results


def update_video(video_id, **kwargs):
    """
    # Updates video fields (youtube_url, youtube_status, etc.)
    """
    conn = get_db()
    sets = []
    values = []
    for key, val in kwargs.items():
        sets.append(f"{key} = ?")
        values.append(val)
    values.append(video_id)
    conn.execute(f"UPDATE videos SET {', '.join(sets)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_video(video_id):
    """
    # Deletes a video record (does NOT delete the file)
    """
    conn = get_db()
    conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
    conn.commit()
    conn.close()


# ============================================================
# SCHEDULE OPERATIONS
# ============================================================

def create_schedule(name, frequency="daily", days_of_week="1,3,5",
                    time_of_day="09:00", format="long", quality="1080p",
                    topic_mode="auto", auto_upload=False):
    """
    # Creates a new generation schedule
    """
    schedule_id = str(uuid.uuid4())[:8]
    conn = get_db()
    conn.execute(
        """INSERT INTO schedules
        (id, name, frequency, days_of_week, time_of_day, format, quality,
         topic_mode, auto_upload, enabled, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
        (schedule_id, name, frequency, days_of_week, time_of_day,
         format, quality, topic_mode, 1 if auto_upload else 0, time.time())
    )
    conn.commit()
    conn.close()
    return schedule_id


def list_schedules():
    """
    # Returns all schedules
    """
    conn = get_db()
    rows = conn.execute("SELECT * FROM schedules ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_schedule(schedule_id):
    """
    # Returns a single schedule by ID
    """
    conn = get_db()
    row = conn.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_schedule(schedule_id, **kwargs):
    """
    # Updates schedule fields
    """
    conn = get_db()
    sets = []
    values = []
    for key, val in kwargs.items():
        sets.append(f"{key} = ?")
        values.append(val)
    values.append(schedule_id)
    conn.execute(f"UPDATE schedules SET {', '.join(sets)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_schedule(schedule_id):
    """
    # Deletes a schedule
    """
    conn = get_db()
    conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()


# ============================================================
# STATS
# ============================================================

def get_stats():
    """
    # Returns dashboard statistics
    """
    conn = get_db()
    total_videos = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
    total_uploaded = conn.execute(
        "SELECT COUNT(*) FROM videos WHERE youtube_status = 'uploaded'"
    ).fetchone()[0]
    active_jobs = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE status IN ('queued', 'running')"
    ).fetchone()[0]
    active_schedules = conn.execute(
        "SELECT COUNT(*) FROM schedules WHERE enabled = 1"
    ).fetchone()[0]

    # --- Total duration of all videos ---
    total_duration = conn.execute(
        "SELECT COALESCE(SUM(duration_seconds), 0) FROM videos"
    ).fetchone()[0]

    # --- Total file size ---
    total_size = conn.execute(
        "SELECT COALESCE(SUM(file_size_mb), 0) FROM videos"
    ).fetchone()[0]

    conn.close()
    return {
        "total_videos": total_videos,
        "total_uploaded": total_uploaded,
        "active_jobs": active_jobs,
        "active_schedules": active_schedules,
        "total_duration_minutes": round(total_duration / 60, 1),
        "total_size_gb": round(total_size / 1024, 2),
    }


# --- Initialize on import ---
init_db()

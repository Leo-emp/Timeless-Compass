"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getStats, listJobs, listVideos, formatRelative, formatDuration } from "@/lib/api";
import type { Stats, Job, Video } from "@/lib/api";

// ============================================================
// OVERVIEW PAGE — Dashboard home with stats, active jobs, recent videos
// ============================================================

export default function OverviewPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [videos, setVideos] = useState<Video[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
    // --- Poll every 5 seconds for live job updates ---
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  async function loadData() {
    try {
      const [s, j, v] = await Promise.all([
        getStats(),
        listJobs(10),
        listVideos(5),
      ]);
      setStats(s);
      setJobs(j);
      setVideos(v);
      setError("");
    } catch {
      setError("Cannot connect to API server. Start it with: python api_server.py");
    }
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto mt-20 text-center">
        <div className="card">
          <h2 className="text-lg font-bold mb-2" style={{ color: "var(--color-error)" }}>
            API Server Offline
          </h2>
          <p className="text-sm mb-4" style={{ color: "var(--color-text-secondary)" }}>
            {error}
          </p>
          <code
            className="block px-4 py-3 rounded-lg text-sm"
            style={{ background: "var(--color-surface-2)", color: "var(--color-accent)" }}
          >
            cd timeless-compass && python api_server.py
          </code>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex items-center justify-center h-64">
        <p style={{ color: "var(--color-text-muted)" }}>Loading...</p>
      </div>
    );
  }

  // --- Active/running jobs ---
  const activeJobs = jobs.filter((j) => j.status === "running" || j.status === "queued");

  return (
    <div className="max-w-5xl">
      {/* --- Page header --- */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1">Dashboard</h1>
        <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
          Automated history documentary pipeline
        </p>
      </div>

      {/* --- Stat cards --- */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Videos" value={stats.total_videos} />
        <StatCard label="Uploaded" value={stats.total_uploaded} accent />
        <StatCard label="Content" value={`${stats.total_duration_minutes}m`} />
        <StatCard label="Storage" value={`${stats.total_size_gb} GB`} />
      </div>

      {/* --- API Key Status --- */}
      <div className="card mb-6">
        <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--color-text-secondary)" }}>
          API CONNECTIONS
        </h3>
        <div className="flex gap-4">
          {Object.entries(stats.api_keys).map(([key, connected]) => (
            <div key={key} className="flex items-center gap-2">
              <div
                className="w-2 h-2 rounded-full"
                style={{ background: connected ? "var(--color-success)" : "var(--color-error)" }}
              />
              <span className="text-xs capitalize" style={{ color: "var(--color-text-secondary)" }}>
                {key}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* --- Active jobs --- */}
      {activeJobs.length > 0 && (
        <div className="card mb-6">
          <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--color-accent)" }}>
            GENERATING NOW
          </h3>
          {activeJobs.map((job) => (
            <div key={job.id} className="mb-4 last:mb-0">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">
                  {job.topic || "AI-selected topic"}
                </span>
                <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                  {job.progress}%
                </span>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${job.progress}%` }} />
              </div>
              <p className="text-xs mt-1" style={{ color: "var(--color-text-muted)" }}>
                {job.progress_message}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* --- Recent videos --- */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold" style={{ color: "var(--color-text-secondary)" }}>
            RECENT VIDEOS
          </h3>
          <Link href="/videos" className="text-xs" style={{ color: "var(--color-accent)" }}>
            View all
          </Link>
        </div>

        {videos.length === 0 ? (
          <div className="py-8 text-center">
            <p className="text-sm mb-2" style={{ color: "var(--color-text-muted)" }}>
              No videos yet
            </p>
            <Link href="/generate" className="btn btn-primary text-sm">
              Generate your first video
            </Link>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {videos.map((video) => (
              <div
                key={video.id}
                className="flex items-center justify-between px-4 py-3 rounded-lg"
                style={{ background: "var(--color-surface-2)" }}
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{video.title}</p>
                  <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                    {formatDuration(video.duration_seconds)} &middot;{" "}
                    {video.file_size_mb.toFixed(1)} MB &middot;{" "}
                    {formatRelative(video.created_at)}
                  </p>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  {video.youtube_status === "uploaded" ? (
                    <span className="badge badge-success">Uploaded</span>
                  ) : (
                    <span className="badge badge-neutral">Local</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* --- Recent job history --- */}
      {jobs.length > 0 && (
        <div className="card mt-6">
          <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--color-text-secondary)" }}>
            JOB HISTORY
          </h3>
          <div className="flex flex-col gap-2">
            {jobs.slice(0, 8).map((job) => (
              <div
                key={job.id}
                className="flex items-center justify-between px-3 py-2 rounded-lg text-sm"
                style={{ background: "var(--color-surface-2)" }}
              >
                <span className="truncate flex-1">{job.topic || "Auto-selected"}</span>
                <div className="flex items-center gap-3 ml-4">
                  <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                    {formatRelative(job.created_at)}
                  </span>
                  <span
                    className={`badge ${
                      job.status === "completed"
                        ? "badge-success"
                        : job.status === "failed"
                        ? "badge-error"
                        : job.status === "running"
                        ? "badge-warning"
                        : "badge-neutral"
                    }`}
                  >
                    {job.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// --- Stat card component ---
function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: boolean;
}) {
  return (
    <div className="card">
      <p className="text-xs mb-1" style={{ color: "var(--color-text-muted)" }}>
        {label}
      </p>
      <p
        className="text-2xl font-bold"
        style={{ color: accent ? "var(--color-accent)" : "var(--color-text)" }}
      >
        {value}
      </p>
    </div>
  );
}

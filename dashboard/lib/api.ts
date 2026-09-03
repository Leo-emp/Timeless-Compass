// ============================================================
// API CLIENT — Calls the FastAPI backend via Next.js proxy
// All /api/* requests are proxied to localhost:8000 via next.config.ts
// ============================================================

const BASE = "";

// --- Generic fetch wrapper with error handling ---
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(error || `API error: ${res.status}`);
  }

  return res.json();
}

// ============================================================
// TYPES
// ============================================================

export interface Stats {
  total_videos: number;
  total_uploaded: number;
  active_jobs: number;
  active_schedules: number;
  total_duration_minutes: number;
  total_size_gb: number;
  api_keys: {
    gemini: boolean;
    elevenlabs: boolean;
    pexels: boolean;
    pixabay: boolean;
    youtube: boolean;
  };
}

export interface Job {
  id: string;
  topic: string | null;
  format: string;
  quality: string;
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  progress_message: string;
  created_at: number;
  started_at: number | null;
  completed_at: number | null;
  error: string | null;
  video_id: string | null;
}

export interface Video {
  id: string;
  job_id: string;
  title: string;
  description: string;
  tags: string[];
  output_path: string;
  file_size_mb: number;
  duration_seconds: number;
  format: string;
  quality: string;
  youtube_url: string | null;
  youtube_status: string;
  created_at: number;
  uploaded_at: number | null;
}

export interface Schedule {
  id: string;
  name: string;
  frequency: string;
  days_of_week: string;
  time_of_day: string;
  format: string;
  quality: string;
  topic_mode: string;
  auto_upload: number;
  enabled: number;
  last_run: number | null;
  next_run: number | null;
  created_at: number;
}

// ============================================================
// API FUNCTIONS
// ============================================================

// --- Stats ---
export const getStats = () => request<Stats>("/api/stats");

// --- Jobs ---
export const startGeneration = (data: {
  topic?: string;
  format?: string;
  quality?: string;
}) => request<{ job_id: string }>("/api/generate", {
  method: "POST",
  body: JSON.stringify(data),
});

export const listJobs = (limit = 20) =>
  request<Job[]>(`/api/jobs?limit=${limit}`);

export const getJob = (id: string) =>
  request<Job>(`/api/jobs/${id}`);

// --- Videos ---
export const listVideos = (limit = 50) =>
  request<Video[]>(`/api/videos?limit=${limit}`);

export const getVideo = (id: string) =>
  request<Video>(`/api/videos/${id}`);

export const deleteVideo = (id: string) =>
  request<{ deleted: boolean }>(`/api/videos/${id}`, { method: "DELETE" });

// --- YouTube ---
export const getYoutubeStatus = () =>
  request<{ authenticated: boolean; client_id_set: boolean }>("/api/youtube/status");

export const getYoutubeAuthUrl = () =>
  request<{ url: string }>("/api/youtube/auth-url");

export const uploadToYoutube = (videoId: string) =>
  request<{ status: string }>(`/api/youtube/upload/${videoId}`, { method: "POST" });

// --- Schedules ---
export const listSchedules = () =>
  request<Schedule[]>("/api/schedules");

export const createSchedule = (data: {
  name: string;
  frequency?: string;
  days_of_week?: string;
  time_of_day?: string;
  format?: string;
  quality?: string;
  auto_upload?: boolean;
}) => request<{ schedule_id: string }>("/api/schedules", {
  method: "POST",
  body: JSON.stringify(data),
});

export const updateSchedule = (id: string, data: Record<string, unknown>) =>
  request<Schedule>(`/api/schedules/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const deleteSchedule = (id: string) =>
  request<{ deleted: boolean }>(`/api/schedules/${id}`, { method: "DELETE" });

// --- Helpers ---
export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function formatDate(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatRelative(timestamp: number): string {
  const diff = Date.now() / 1000 - timestamp;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

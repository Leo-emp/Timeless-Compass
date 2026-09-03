// ============================================================
// API CLIENT — Calls Next.js API routes (GitHub Actions backend)
// Production-ready: no local Python server needed
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

// --- GitHub Actions run status ---
export interface RunStatus {
  id: number;
  status: string;
  conclusion: string | null;
  progress: number;
  steps: Array<{ name: string; status: string; conclusion: string | null }>;
  created_at: string;
  updated_at: string;
  html_url: string;
}

export interface RecentRun {
  id: number;
  status: string;
  conclusion: string | null;
  created_at: string;
  html_url: string;
}

// ============================================================
// API FUNCTIONS
// ============================================================

// --- Trigger generation via GitHub Actions ---
export const startGeneration = (data: {
  topic?: string;
  format?: string;
  quality?: string;
}) => request<{ dispatched: boolean; run_id: number | null; status: string; html_url: string | null }>("/api/generate", {
  method: "POST",
  body: JSON.stringify(data),
});

// --- Poll a specific run's status ---
export const getRunStatus = (runId: number) =>
  request<RunStatus>(`/api/generate?run_id=${runId}`);

// --- Get recent pipeline runs ---
export const getRecentRuns = () =>
  request<{ runs: RecentRun[] }>("/api/generate");

// --- Helpers ---
export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function formatDate(timestamp: number | string): string {
  const date = typeof timestamp === "string" ? new Date(timestamp) : new Date(timestamp * 1000);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatRelative(timestamp: number | string): string {
  const ms = typeof timestamp === "string" ? new Date(timestamp).getTime() : timestamp * 1000;
  const diff = (Date.now() - ms) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

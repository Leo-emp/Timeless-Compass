"use client";

import { useEffect, useState } from "react";
import { getRecentRuns, formatRelative } from "@/lib/api";
import type { RecentRun } from "@/lib/api";

// ============================================================
// VIDEOS PAGE — Pipeline run history (videos generated via GitHub Actions)
// ============================================================

export default function VideosPage() {
  const [runs, setRuns] = useState<RecentRun[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadRuns();
  }, []);

  async function loadRuns() {
    try {
      const data = await getRecentRuns();
      setRuns(data.runs ?? []);
    } catch {
      // --- API might not be configured yet ---
    }
    setLoading(false);
  }

  function conclusionBadge(conclusion: string | null, status?: string) {
    if (conclusion === "success") return { bg: "var(--color-success)", label: "Success" };
    if (conclusion === "failure") return { bg: "var(--color-error)", label: "Failed" };
    if (conclusion === "cancelled") return { bg: "var(--color-text-muted)", label: "Cancelled" };
    if (status === "in_progress" || status === "queued") return { bg: "var(--color-accent)", label: "Running" };
    return { bg: "var(--color-text-muted)", label: status ?? "Unknown" };
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p style={{ color: "var(--color-text-muted)" }}>Loading...</p>
      </div>
    );
  }

  const successful = runs.filter((r) => r.conclusion === "success");
  const failed = runs.filter((r) => r.conclusion === "failure");

  return (
    <div className="max-w-5xl">
      {/* --- Page header --- */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold mb-1">Pipeline Runs</h1>
          <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
            {runs.length} run{runs.length !== 1 ? "s" : ""} &middot;{" "}
            {successful.length} successful &middot;{" "}
            {failed.length} failed
          </p>
        </div>
      </div>

      {runs.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-sm mb-2" style={{ color: "var(--color-text-muted)" }}>
            No pipeline runs yet
          </p>
          <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
            Go to Generate to create your first documentary
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {runs.map((run) => {
            const badge = conclusionBadge(run.conclusion, run.status);
            return (
              <a
                key={run.id}
                href={run.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="card flex items-center justify-between transition-colors hover:brightness-110"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold mb-1">Pipeline #{run.id}</p>
                  <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                    {formatRelative(run.created_at)} &middot;{" "}
                    {new Date(run.created_at).toLocaleDateString("en-US", {
                      weekday: "short",
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>

                <span
                  className="badge ml-4"
                  style={{
                    background: `${badge.bg}20`,
                    color: badge.bg,
                  }}
                >
                  {badge.label}
                </span>
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
}

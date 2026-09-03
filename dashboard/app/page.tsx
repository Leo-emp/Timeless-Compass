"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getRecentRuns, formatRelative } from "@/lib/api";
import type { RecentRun } from "@/lib/api";

// ============================================================
// OVERVIEW PAGE — Dashboard home with recent runs and quick actions
// ============================================================

export default function OverviewPage() {
  const [runs, setRuns] = useState<RecentRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
    // --- Poll every 10 seconds for live updates ---
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  async function loadData() {
    try {
      const data = await getRecentRuns();
      setRuns(data.runs ?? []);
      setError("");
    } catch {
      setError("Cannot connect. Check GITHUB_TOKEN in Vercel env vars.");
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

  if (error) {
    return (
      <div className="max-w-2xl mx-auto mt-20 text-center">
        <div className="card">
          <h2 className="text-lg font-bold mb-2" style={{ color: "var(--color-error)" }}>
            Setup Required
          </h2>
          <p className="text-sm mb-4" style={{ color: "var(--color-text-secondary)" }}>
            {error}
          </p>
          <div
            className="px-4 py-3 rounded-lg text-sm text-left"
            style={{ background: "var(--color-surface-2)", color: "var(--color-accent)" }}
          >
            <p className="font-semibold mb-2">Required env vars:</p>
            <code className="block text-xs leading-relaxed">
              GITHUB_TOKEN — GitHub personal access token (repo scope)<br />
              GITHUB_REPO — Leo-emp/timeless-compass
            </code>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p style={{ color: "var(--color-text-muted)" }}>Loading...</p>
      </div>
    );
  }

  // --- Active/running jobs ---
  const activeRuns = runs.filter((r) => r.status === "in_progress" || r.status === "queued");
  const completedRuns = runs.filter((r) => r.status === "completed");

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
      <div className="grid grid-cols-3 gap-4 mb-8">
        <StatCard label="Total Runs" value={runs.length} />
        <StatCard
          label="Successful"
          value={completedRuns.filter((r) => r.conclusion === "success").length}
          accent
        />
        <StatCard
          label="Failed"
          value={completedRuns.filter((r) => r.conclusion === "failure").length}
        />
      </div>

      {/* --- Active runs --- */}
      {activeRuns.length > 0 && (
        <div className="card mb-6">
          <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--color-accent)" }}>
            GENERATING NOW
          </h3>
          {activeRuns.map((run) => (
            <a
              key={run.id}
              href={run.html_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between px-4 py-3 rounded-lg mb-2 last:mb-0"
              style={{ background: "var(--color-surface-2)" }}
            >
              <span className="text-sm font-medium">Pipeline #{run.id}</span>
              <span className="badge badge-warning">{run.status}</span>
            </a>
          ))}
        </div>
      )}

      {/* --- Quick action --- */}
      <div className="card mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold mb-1">Generate a new documentary</h3>
            <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
              Pick a topic or let AI choose from 10 history categories
            </p>
          </div>
          <Link href="/generate" className="btn btn-primary">
            Generate
          </Link>
        </div>
      </div>

      {/* --- Recent run history --- */}
      {runs.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--color-text-secondary)" }}>
            RECENT RUNS
          </h3>
          <div className="flex flex-col gap-2">
            {runs.map((run) => (
              <a
                key={run.id}
                href={run.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between px-3 py-2 rounded-lg text-sm"
                style={{ background: "var(--color-surface-2)" }}
              >
                <span className="truncate flex-1">Pipeline #{run.id}</span>
                <div className="flex items-center gap-3 ml-4">
                  <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                    {formatRelative(run.created_at)}
                  </span>
                  <span
                    className="badge"
                    style={{
                      background: `${conclusionBadge(run.conclusion, run.status).bg}20`,
                      color: conclusionBadge(run.conclusion, run.status).bg,
                    }}
                  >
                    {conclusionBadge(run.conclusion, run.status).label}
                  </span>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {runs.length === 0 && (
        <div className="card text-center py-12">
          <p className="text-sm mb-2" style={{ color: "var(--color-text-muted)" }}>
            No pipeline runs yet
          </p>
          <Link href="/generate" className="btn btn-primary text-sm">
            Generate your first documentary
          </Link>
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

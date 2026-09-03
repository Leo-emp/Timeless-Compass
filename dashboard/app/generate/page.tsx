"use client";

import { useState, useEffect } from "react";
import { startGeneration, getRunStatus, getRecentRuns, formatRelative } from "@/lib/api";
import type { RunStatus, RecentRun } from "@/lib/api";

// ============================================================
// GENERATE PAGE — Trigger pipeline via GitHub Actions
// ============================================================

const TOPIC_HINTS = [
  "The Fall of the Roman Empire",
  "How the Silk Road Changed the World",
  "The Real Story of Cleopatra",
  "Why Empires Collapse: Patterns in History",
  "The Industrial Revolution's Hidden Cost",
];

export default function GeneratePage() {
  const [topic, setTopic] = useState("");
  const [format, setFormat] = useState("long");
  const [quality, setQuality] = useState("1080p");
  const [generating, setGenerating] = useState(false);
  const [currentRun, setCurrentRun] = useState<RunStatus | null>(null);
  const [recentRuns, setRecentRuns] = useState<RecentRun[]>([]);
  const [error, setError] = useState("");
  const [hint] = useState(() => TOPIC_HINTS[Math.floor(Math.random() * TOPIC_HINTS.length)]);

  // --- Load recent runs on mount ---
  useEffect(() => {
    loadRecentRuns();
  }, []);

  // --- Poll current run status while active ---
  useEffect(() => {
    if (!currentRun || currentRun.status === "completed") return;

    const interval = setInterval(async () => {
      try {
        const updated = await getRunStatus(currentRun.id);
        setCurrentRun(updated);
        if (updated.status === "completed") {
          setGenerating(false);
          loadRecentRuns();
        }
      } catch {
        // --- Keep polling on network errors ---
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [currentRun]);

  async function loadRecentRuns() {
    try {
      const data = await getRecentRuns();
      setRecentRuns(data.runs ?? []);
    } catch {
      // --- GITHUB_TOKEN might not be set yet ---
    }
  }

  async function handleGenerate() {
    setError("");
    setGenerating(true);

    try {
      const result = await startGeneration({
        topic: topic.trim() || undefined,
        format,
        quality,
      });

      if (result.run_id) {
        setCurrentRun({
          id: result.run_id,
          status: result.status ?? "queued",
          conclusion: null,
          progress: 0,
          steps: [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          html_url: result.html_url ?? "",
        });
      } else {
        // --- Dispatched but couldn't get run ID ---
        setGenerating(false);
        loadRecentRuns();
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Generation failed");
      setGenerating(false);
    }
  }

  function handleReset() {
    setCurrentRun(null);
    setTopic("");
    setError("");
  }

  function conclusionBadge(conclusion: string | null, status?: string) {
    if (conclusion === "success") return { bg: "var(--color-success)", label: "Success" };
    if (conclusion === "failure") return { bg: "var(--color-error)", label: "Failed" };
    if (conclusion === "cancelled") return { bg: "var(--color-text-muted)", label: "Cancelled" };
    if (status === "in_progress" || status === "queued") return { bg: "var(--color-accent)", label: "Running" };
    return { bg: "var(--color-text-muted)", label: status ?? "Unknown" };
  }

  return (
    <div className="max-w-2xl">
      {/* --- Page header --- */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1">Generate Video</h1>
        <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
          Trigger the documentary pipeline via GitHub Actions
        </p>
      </div>

      {/* --- Generation form --- */}
      {!currentRun && (
        <div className="card">
          {/* --- Topic input --- */}
          <div className="mb-5">
            <label className="block text-xs font-semibold mb-2" style={{ color: "var(--color-text-secondary)" }}>
              TOPIC
            </label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder={hint}
              className="w-full"
            />
            <p className="text-xs mt-1" style={{ color: "var(--color-text-muted)" }}>
              AI selects from 10 history categories if left blank
            </p>
          </div>

          {/* --- Format selector --- */}
          <div className="mb-5">
            <label className="block text-xs font-semibold mb-2" style={{ color: "var(--color-text-secondary)" }}>
              FORMAT
            </label>
            <div className="grid grid-cols-3 gap-3">
              {[
                { value: "long", label: "Long Form", desc: "10-15 min deep dive" },
                { value: "mid", label: "Mid Form", desc: "6-10 min overview" },
                { value: "short", label: "Short", desc: "60s teaser" },
              ].map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setFormat(opt.value)}
                  className="px-4 py-3 rounded-lg text-left transition-colors"
                  style={{
                    background: format === opt.value ? "rgba(196, 149, 106, 0.1)" : "var(--color-surface-2)",
                    border: `1px solid ${format === opt.value ? "var(--color-accent)" : "var(--color-border)"}`,
                  }}
                >
                  <span className="block text-sm font-semibold">{opt.label}</span>
                  <span className="block text-xs" style={{ color: "var(--color-text-muted)" }}>
                    {opt.desc}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* --- Quality selector --- */}
          <div className="mb-6">
            <label className="block text-xs font-semibold mb-2" style={{ color: "var(--color-text-secondary)" }}>
              QUALITY
            </label>
            <div className="flex gap-3">
              {["1080p", "4k"].map((q) => (
                <button
                  key={q}
                  onClick={() => setQuality(q)}
                  className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                  style={{
                    background: quality === q ? "rgba(196, 149, 106, 0.1)" : "var(--color-surface-2)",
                    border: `1px solid ${quality === q ? "var(--color-accent)" : "var(--color-border)"}`,
                    color: quality === q ? "var(--color-accent)" : "var(--color-text-secondary)",
                  }}
                >
                  {q.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {/* --- Cost estimate --- */}
          <div
            className="flex items-center justify-between px-4 py-3 rounded-lg mb-6"
            style={{ background: "var(--color-surface-2)" }}
          >
            <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
              Estimated cost
            </span>
            <span className="text-sm font-bold" style={{ color: "var(--color-accent)" }}>
              ~${format === "long" ? "1.00" : format === "mid" ? "0.75" : "0.30"}
            </span>
          </div>

          {/* --- Error message --- */}
          {error && (
            <div
              className="px-4 py-3 rounded-lg mb-4 text-sm"
              style={{ background: "rgba(248, 113, 113, 0.1)", color: "var(--color-error)" }}
            >
              {error}
            </div>
          )}

          {/* --- Generate button --- */}
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="btn btn-primary w-full justify-center text-base"
          >
            {generating ? "Dispatching..." : "Generate Documentary"}
          </button>
        </div>
      )}

      {/* --- Active run progress --- */}
      {currentRun && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold" style={{ color: "var(--color-text-secondary)" }}>
              {currentRun.status === "completed"
                ? currentRun.conclusion === "success" ? "GENERATION COMPLETE" : "GENERATION FAILED"
                : "GENERATING..."}
            </h3>
            <span
              className="badge"
              style={{
                background: `${conclusionBadge(currentRun.conclusion, currentRun.status).bg}20`,
                color: conclusionBadge(currentRun.conclusion, currentRun.status).bg,
              }}
            >
              {conclusionBadge(currentRun.conclusion, currentRun.status).label}
            </span>
          </div>

          {/* --- Progress bar --- */}
          <div className="mb-2">
            <div className="flex justify-between text-xs mb-1">
              <span style={{ color: "var(--color-text-muted)" }}>Progress</span>
              <span style={{ color: "var(--color-accent)" }}>{currentRun.progress}%</span>
            </div>
            <div className="progress-track">
              <div
                className="progress-fill"
                style={{
                  width: `${currentRun.progress}%`,
                  background: currentRun.conclusion === "failure" ? "var(--color-error)" : undefined,
                }}
              />
            </div>
          </div>

          {/* --- Pipeline steps --- */}
          {currentRun.steps.length > 0 && (
            <div className="flex flex-col gap-2 mt-4 mb-6">
              {currentRun.steps.map((step, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div
                    className="w-5 h-5 rounded-full flex items-center justify-center text-[10px]"
                    style={{
                      background: step.status === "completed"
                        ? (step.conclusion === "success" ? "var(--color-success)" : "var(--color-error)")
                        : step.status === "in_progress" ? "var(--color-accent)"
                        : "var(--color-surface-2)",
                      color: step.status !== "queued" ? "#0C0A08" : "var(--color-text-muted)",
                    }}
                  >
                    {step.status === "completed" ? (step.conclusion === "success" ? "✓" : "✕") : ""}
                  </div>
                  <span
                    className="text-sm"
                    style={{
                      color: step.status === "completed" ? "var(--color-text)" : "var(--color-text-muted)",
                    }}
                  >
                    {step.name}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* --- GitHub link --- */}
          {currentRun.html_url && (
            <a
              href={currentRun.html_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs underline"
              style={{ color: "var(--color-accent)" }}
            >
              View on GitHub Actions
            </a>
          )}

          {/* --- Reset button when done --- */}
          {currentRun.status === "completed" && (
            <button onClick={handleReset} className="btn btn-secondary w-full justify-center mt-4">
              Generate Another
            </button>
          )}
        </div>
      )}

      {/* --- Recent pipeline runs --- */}
      {recentRuns.length > 0 && !currentRun && (
        <div className="card mt-6">
          <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--color-text-secondary)" }}>
            RECENT RUNS
          </h3>
          <div className="flex flex-col gap-2">
            {recentRuns.map((run) => (
              <a
                key={run.id}
                href={run.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between px-4 py-3 rounded-lg transition-colors"
                style={{ background: "var(--color-surface-2)" }}
              >
                <span className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
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
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import { startGeneration, getJob, formatDuration } from "@/lib/api";
import type { Job } from "@/lib/api";

// ============================================================
// GENERATE PAGE — Manual video generation with live progress
// ============================================================

export default function GeneratePage() {
  const [topic, setTopic] = useState("");
  const [format, setFormat] = useState("long");
  const [quality, setQuality] = useState("1080p");
  const [generating, setGenerating] = useState(false);
  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [error, setError] = useState("");

  // --- Poll for job progress while generating ---
  useEffect(() => {
    if (!currentJob || currentJob.status === "completed" || currentJob.status === "failed") return;

    const interval = setInterval(async () => {
      try {
        const updated = await getJob(currentJob.id);
        setCurrentJob(updated);

        if (updated.status === "completed" || updated.status === "failed") {
          setGenerating(false);
        }
      } catch {
        // --- API might be busy, keep polling ---
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [currentJob]);

  async function handleGenerate() {
    setError("");
    setGenerating(true);

    try {
      const result = await startGeneration({
        topic: topic.trim() || undefined,
        format,
        quality,
      });

      // --- Start polling the job ---
      const job = await getJob(result.job_id);
      setCurrentJob(job);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Generation failed");
      setGenerating(false);
    }
  }

  function handleReset() {
    setCurrentJob(null);
    setTopic("");
    setError("");
  }

  return (
    <div className="max-w-2xl">
      {/* --- Page header --- */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1">Generate Video</h1>
        <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
          Create a new history documentary
        </p>
      </div>

      {/* --- Generation form --- */}
      {!currentJob && (
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
              placeholder="Leave empty for AI to pick (e.g. The Fall of Rome)"
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
              ~$0.52
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
            {generating ? "Starting..." : "Generate Documentary"}
          </button>
        </div>
      )}

      {/* --- Job progress --- */}
      {currentJob && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold" style={{ color: "var(--color-text-secondary)" }}>
              {currentJob.status === "completed" ? "GENERATION COMPLETE" :
               currentJob.status === "failed" ? "GENERATION FAILED" :
               "GENERATING..."}
            </h3>
            <span
              className={`badge ${
                currentJob.status === "completed" ? "badge-success" :
                currentJob.status === "failed" ? "badge-error" :
                "badge-warning"
              }`}
            >
              {currentJob.status}
            </span>
          </div>

          {/* --- Topic --- */}
          <p className="text-lg font-bold mb-4">
            {currentJob.topic || "AI-selected topic"}
          </p>

          {/* --- Progress bar --- */}
          <div className="mb-2">
            <div className="flex justify-between text-xs mb-1">
              <span style={{ color: "var(--color-text-muted)" }}>Progress</span>
              <span style={{ color: "var(--color-accent)" }}>{currentJob.progress}%</span>
            </div>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${currentJob.progress}%` }} />
            </div>
          </div>

          <p className="text-xs mb-6" style={{ color: "var(--color-text-muted)" }}>
            {currentJob.progress_message}
          </p>

          {/* --- Pipeline steps --- */}
          <div className="flex flex-col gap-2 mb-6">
            {[
              { step: "Script Generation", threshold: 10 },
              { step: "Stock Footage Download", threshold: 30 },
              { step: "Voiceover (ElevenLabs)", threshold: 50 },
              { step: "Video Assembly", threshold: 70 },
              { step: "Final Output", threshold: 95 },
            ].map((s) => (
              <div key={s.step} className="flex items-center gap-3">
                <div
                  className="w-5 h-5 rounded-full flex items-center justify-center text-[10px]"
                  style={{
                    background: currentJob.progress >= s.threshold
                      ? "var(--color-accent)"
                      : "var(--color-surface-2)",
                    color: currentJob.progress >= s.threshold ? "#0C0A08" : "var(--color-text-muted)",
                  }}
                >
                  {currentJob.progress >= s.threshold ? "✓" : ""}
                </div>
                <span
                  className="text-sm"
                  style={{
                    color: currentJob.progress >= s.threshold
                      ? "var(--color-text)"
                      : "var(--color-text-muted)",
                  }}
                >
                  {s.step}
                </span>
              </div>
            ))}
          </div>

          {/* --- Error details --- */}
          {currentJob.status === "failed" && currentJob.error && (
            <div
              className="px-4 py-3 rounded-lg mb-4 text-sm"
              style={{ background: "rgba(248, 113, 113, 0.1)", color: "var(--color-error)" }}
            >
              {currentJob.error}
            </div>
          )}

          {/* --- Action buttons --- */}
          {(currentJob.status === "completed" || currentJob.status === "failed") && (
            <button onClick={handleReset} className="btn btn-secondary w-full justify-center">
              Generate Another
            </button>
          )}
        </div>
      )}
    </div>
  );
}

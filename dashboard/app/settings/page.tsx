"use client";

import { useEffect, useState } from "react";
import { getStats, getYoutubeStatus, getYoutubeAuthUrl } from "@/lib/api";
import type { Stats } from "@/lib/api";

// ============================================================
// SETTINGS PAGE — API keys status, YouTube auth, pipeline config
// ============================================================

export default function SettingsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [ytStatus, setYtStatus] = useState<{ authenticated: boolean; client_id_set: boolean } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSettings();
  }, []);

  async function loadSettings() {
    try {
      const [s, yt] = await Promise.all([getStats(), getYoutubeStatus()]);
      setStats(s);
      setYtStatus(yt);
    } catch {
      // --- API offline ---
    }
    setLoading(false);
  }

  async function handleYoutubeConnect() {
    try {
      const { url } = await getYoutubeAuthUrl();
      window.open(url, "_blank");
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed to get auth URL");
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p style={{ color: "var(--color-text-muted)" }}>Loading...</p>
      </div>
    );
  }

  const apiKeys = stats?.api_keys || {
    gemini: false, elevenlabs: false, pexels: false, pixabay: false, youtube: false,
  };

  return (
    <div className="max-w-2xl">
      {/* --- Page header --- */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1">Settings</h1>
        <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
          API connections and pipeline configuration
        </p>
      </div>

      {/* --- API Keys status --- */}
      <div className="card mb-6">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--color-text-secondary)" }}>
          API KEYS
        </h3>
        <p className="text-xs mb-4" style={{ color: "var(--color-text-muted)" }}>
          Set these in your .env file in the timeless-compass root directory
        </p>

        <div className="flex flex-col gap-3">
          <ApiKeyRow
            name="Gemini"
            envVar="GEMINI_API_KEY"
            connected={apiKeys.gemini}
            description="Script generation (Gemini 2.5 Flash)"
          />
          <ApiKeyRow
            name="ElevenLabs"
            envVar="ELEVENLABS_API_KEY"
            connected={apiKeys.elevenlabs}
            description="Voiceover narration (Daniel voice)"
          />
          <ApiKeyRow
            name="Pexels"
            envVar="PEXELS_API_KEY"
            connected={apiKeys.pexels}
            description="Primary stock footage source (free)"
          />
          <ApiKeyRow
            name="Pixabay"
            envVar="PIXABAY_API_KEY"
            connected={apiKeys.pixabay}
            description="Secondary stock footage source (free, optional)"
          />
        </div>
      </div>

      {/* --- YouTube connection --- */}
      <div className="card mb-6">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--color-text-secondary)" }}>
          YOUTUBE AUTO-UPLOAD
        </h3>

        {ytStatus?.authenticated ? (
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full" style={{ background: "var(--color-success)" }} />
            <span className="text-sm font-medium" style={{ color: "var(--color-success)" }}>
              Connected
            </span>
          </div>
        ) : (
          <div>
            <p className="text-sm mb-4" style={{ color: "var(--color-text-secondary)" }}>
              Connect your YouTube channel to auto-upload generated videos.
            </p>

            {/* --- Setup steps --- */}
            <div
              className="flex flex-col gap-2 mb-4 px-4 py-3 rounded-lg"
              style={{ background: "var(--color-surface-2)" }}
            >
              <p className="text-xs font-semibold mb-1" style={{ color: "var(--color-text-muted)" }}>
                SETUP STEPS:
              </p>
              <Step n={1} done={ytStatus?.client_id_set}>
                Create a Google Cloud project and enable YouTube Data API v3
              </Step>
              <Step n={2} done={ytStatus?.client_id_set}>
                Create OAuth 2.0 credentials (Desktop app type)
              </Step>
              <Step n={3} done={ytStatus?.client_id_set}>
                Add YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET to .env
              </Step>
              <Step n={4} done={ytStatus?.authenticated}>
                Click Connect below to authorize
              </Step>
            </div>

            <button
              onClick={handleYoutubeConnect}
              disabled={!ytStatus?.client_id_set}
              className="btn btn-primary"
            >
              Connect YouTube
            </button>

            {!ytStatus?.client_id_set && (
              <p className="text-xs mt-2" style={{ color: "var(--color-text-muted)" }}>
                Add YOUTUBE_CLIENT_ID to .env first
              </p>
            )}
          </div>
        )}
      </div>

      {/* --- Pipeline config info --- */}
      <div className="card mb-6">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--color-text-secondary)" }}>
          PIPELINE CONFIG
        </h3>

        <div className="grid grid-cols-2 gap-4">
          <ConfigRow label="Voice" value="Daniel (British, scholarly)" />
          <ConfigRow label="Model" value="Gemini 2.5 Flash" />
          <ConfigRow label="TTS Model" value="eleven_multilingual_v2" />
          <ConfigRow label="Color Grade" value="Warm sepia" />
          <ConfigRow label="Effects" value="Ken Burns (slow zoom/pan)" />
          <ConfigRow label="Footage" value="Pexels + Pixabay (free)" />
          <ConfigRow label="Cost/Video" value="~$0.52" />
          <ConfigRow label="Categories" value="10 history categories" />
        </div>
      </div>

      {/* --- .env template --- */}
      <div className="card">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--color-text-secondary)" }}>
          .ENV TEMPLATE
        </h3>
        <pre
          className="text-xs px-4 py-3 rounded-lg overflow-x-auto"
          style={{
            background: "var(--color-surface-2)",
            color: "var(--color-accent)",
            fontFamily: "'Cascadia Code', 'Fira Code', Consolas, monospace",
          }}
        >{`GEMINI_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
PEXELS_API_KEY=your_key_here
PIXABAY_API_KEY=your_key_here
YOUTUBE_CLIENT_ID=your_client_id
YOUTUBE_CLIENT_SECRET=your_client_secret`}</pre>
      </div>
    </div>
  );
}

// --- API key status row ---
function ApiKeyRow({
  name,
  envVar,
  connected,
  description,
}: {
  name: string;
  envVar: string;
  connected?: boolean;
  description: string;
}) {
  return (
    <div
      className="flex items-center justify-between px-4 py-3 rounded-lg"
      style={{ background: "var(--color-surface-2)" }}
    >
      <div>
        <p className="text-sm font-medium">{name}</p>
        <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
          {description}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <code className="text-[11px]" style={{ color: "var(--color-text-muted)" }}>
          {envVar}
        </code>
        <div
          className="w-2.5 h-2.5 rounded-full"
          style={{ background: connected ? "var(--color-success)" : "var(--color-error)" }}
        />
      </div>
    </div>
  );
}

// --- Setup step ---
function Step({ n, done, children }: { n: number; done?: boolean; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2">
      <div
        className="w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold mt-0.5 shrink-0"
        style={{
          background: done ? "var(--color-accent)" : "var(--color-border)",
          color: done ? "#0C0A08" : "var(--color-text-muted)",
        }}
      >
        {done ? "✓" : n}
      </div>
      <span className="text-xs" style={{ color: done ? "var(--color-text)" : "var(--color-text-muted)" }}>
        {children}
      </span>
    </div>
  );
}

// --- Config info row ---
function ConfigRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>{label}</p>
      <p className="text-sm font-medium">{value}</p>
    </div>
  );
}

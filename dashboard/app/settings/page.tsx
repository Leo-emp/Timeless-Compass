"use client";

// ============================================================
// SETTINGS PAGE — Environment variables and pipeline config
// ============================================================

export default function SettingsPage() {
  return (
    <div className="max-w-2xl">
      {/* --- Page header --- */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1">Settings</h1>
        <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
          Pipeline configuration and required setup
        </p>
      </div>

      {/* --- GitHub Secrets --- */}
      <div className="card mb-6">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--color-text-secondary)" }}>
          GITHUB SECRETS (PIPELINE)
        </h3>
        <p className="text-xs mb-4" style={{ color: "var(--color-text-muted)" }}>
          Set these in your repo Settings → Secrets → Actions
        </p>

        <div className="flex flex-col gap-3">
          <SecretRow name="GEMINI_API_KEY" desc="Script generation (Gemini 2.5 Flash)" required />
          <SecretRow name="ELEVENLABS_API_KEY" desc="Voiceover narration" required />
          <SecretRow name="ELEVENLABS_VOICE_ID" desc="ElevenLabs voice to use" required />
          <SecretRow name="PEXELS_API_KEY" desc="Primary stock footage (free)" required />
          <SecretRow name="PIXABAY_API_KEY" desc="Secondary footage fallback (free)" />
          <SecretRow name="BLOB_READ_WRITE_TOKEN" desc="Vercel Blob for cloud storage" />
          <SecretRow name="ALERT_WEBHOOK_URL" desc="Discord/Slack alert webhook" />
        </div>
      </div>

      {/* --- Vercel Env Vars --- */}
      <div className="card mb-6">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--color-text-secondary)" }}>
          VERCEL ENV VARS (DASHBOARD)
        </h3>
        <p className="text-xs mb-4" style={{ color: "var(--color-text-muted)" }}>
          Set these in Vercel → Project → Settings → Environment Variables
        </p>

        <div className="flex flex-col gap-3">
          <SecretRow name="GITHUB_TOKEN" desc="Personal access token with repo scope" required />
          <SecretRow name="GITHUB_REPO" desc="e.g. Leo-emp/timeless-compass (defaults to this)" />
          <SecretRow name="DASHBOARD_PASSWORD" desc="Bearer token for API auth (optional in dev)" />
        </div>
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

      {/* --- Architecture --- */}
      <div className="card">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--color-text-secondary)" }}>
          ARCHITECTURE
        </h3>
        <div className="flex flex-col gap-2 text-sm" style={{ color: "var(--color-text-secondary)" }}>
          <p><strong>Dashboard</strong> — Next.js on Vercel (this app)</p>
          <p><strong>Pipeline</strong> — Python + FFmpeg on GitHub Actions</p>
          <p><strong>Trigger</strong> — Dashboard dispatches workflow_dispatch</p>
          <p><strong>Schedule</strong> — GitHub Actions cron (Mon/Wed/Fri 07:00 UTC)</p>
          <p><strong>Storage</strong> — Vercel Blob (videos + thumbnails)</p>
        </div>
      </div>
    </div>
  );
}

function SecretRow({ name, desc, required }: { name: string; desc: string; required?: boolean }) {
  return (
    <div
      className="flex items-center justify-between px-4 py-3 rounded-lg"
      style={{ background: "var(--color-surface-2)" }}
    >
      <div>
        <div className="flex items-center gap-2">
          <code className="text-xs font-semibold" style={{ color: "var(--color-accent)" }}>
            {name}
          </code>
          {required && (
            <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "rgba(248, 113, 113, 0.1)", color: "var(--color-error)" }}>
              required
            </span>
          )}
        </div>
        <p className="text-xs mt-0.5" style={{ color: "var(--color-text-muted)" }}>
          {desc}
        </p>
      </div>
    </div>
  );
}

function ConfigRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>{label}</p>
      <p className="text-sm font-medium">{value}</p>
    </div>
  );
}

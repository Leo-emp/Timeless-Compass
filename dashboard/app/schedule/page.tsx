"use client";

// ============================================================
// SCHEDULE PAGE — Shows cron schedule config (GitHub Actions)
// ============================================================

export default function SchedulePage() {
  return (
    <div className="max-w-3xl">
      {/* --- Page header --- */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1">Schedule</h1>
        <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
          Automated pipeline runs via GitHub Actions cron
        </p>
      </div>

      {/* --- Current schedule --- */}
      <div className="card mb-6">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--color-text-secondary)" }}>
          ACTIVE SCHEDULE
        </h3>

        <div
          className="flex items-center justify-between px-4 py-4 rounded-lg"
          style={{ background: "var(--color-surface-2)" }}
        >
          <div>
            <p className="text-base font-bold mb-1">Mon / Wed / Fri</p>
            <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
              07:00 UTC &middot; Long form documentary &middot; AI-selected topic
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: "var(--color-success)" }} />
            <span className="text-xs font-medium" style={{ color: "var(--color-success)" }}>Active</span>
          </div>
        </div>
      </div>

      {/* --- How to change --- */}
      <div className="card mb-6">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--color-text-secondary)" }}>
          HOW TO CHANGE SCHEDULE
        </h3>
        <p className="text-sm mb-4" style={{ color: "var(--color-text-secondary)" }}>
          The schedule is defined in the GitHub Actions workflow file. To change it:
        </p>

        <div className="flex flex-col gap-3">
          <Step n={1}>
            Open <code className="text-xs px-1.5 py-0.5 rounded" style={{ background: "var(--color-surface-2)", color: "var(--color-accent)" }}>
              .github/workflows/pipeline.yml
            </code>
          </Step>
          <Step n={2}>
            Edit the <code className="text-xs px-1.5 py-0.5 rounded" style={{ background: "var(--color-surface-2)", color: "var(--color-accent)" }}>
              cron
            </code> line (uses standard cron syntax)
          </Step>
          <Step n={3}>Commit and push — schedule updates immediately</Step>
        </div>

        <pre
          className="text-xs px-4 py-3 rounded-lg mt-4 overflow-x-auto"
          style={{
            background: "var(--color-surface-2)",
            color: "var(--color-accent)",
            fontFamily: "'Cascadia Code', 'Fira Code', Consolas, monospace",
          }}
        >{`# Current cron: Mon/Wed/Fri 07:00 UTC
- cron: '0 7 * * 1,3,5'

# Examples:
# Daily at 6am:    '0 6 * * *'
# Weekdays at 8am: '0 8 * * 1-5'
# Every 6 hours:   '0 */6 * * *'`}</pre>
      </div>

      {/* --- Manual trigger info --- */}
      <div className="card">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--color-text-secondary)" }}>
          MANUAL TRIGGER
        </h3>
        <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
          Use the <a href="/generate" className="underline" style={{ color: "var(--color-accent)" }}>Generate</a> page
          to trigger a one-off video at any time, with a custom topic and format.
        </p>
      </div>
    </div>
  );
}

function Step({ n, children }: { n: number; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <div
        className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5"
        style={{ background: "rgba(196, 149, 106, 0.15)", color: "var(--color-accent)" }}
      >
        {n}
      </div>
      <span className="text-sm" style={{ color: "var(--color-text)" }}>{children}</span>
    </div>
  );
}

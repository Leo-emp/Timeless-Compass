// # GitHub Actions integration — dispatch workflows and poll run status
// # Used by dashboard API routes to trigger video generation remotely

const GITHUB_API = 'https://api.github.com'

// # Read config from env — set these in Vercel dashboard
function getConfig() {
  const token = process.env.GITHUB_TOKEN ?? ''
  const repo = process.env.GITHUB_REPO ?? 'Leo-emp/timeless-compass'
  const workflow = 'pipeline.yml'
  return { token, repo, workflow }
}

// # Auth header helper
function headers(token: string) {
  return {
    Authorization: `Bearer ${token}`,
    Accept: 'application/vnd.github.v3+json',
    'Content-Type': 'application/json',
  }
}

// # Trigger a pipeline run via workflow_dispatch
export async function triggerWorkflow(inputs: {
  topic?: string
  format?: string
  quality?: string
}) {
  const { token, repo, workflow } = getConfig()
  if (!token) throw new Error('GITHUB_TOKEN not configured')

  const res = await fetch(
    `${GITHUB_API}/repos/${repo}/actions/workflows/${workflow}/dispatches`,
    {
      method: 'POST',
      headers: headers(token),
      body: JSON.stringify({
        ref: 'main',
        inputs: {
          topic: inputs.topic ?? '',
          format: inputs.format ?? 'long',
          quality: inputs.quality ?? '1080p',
        },
      }),
    }
  )

  // # 204 = dispatched successfully (no response body)
  if (res.status !== 204) {
    const text = await res.text()
    throw new Error(`Dispatch failed (${res.status}): ${text}`)
  }

  // # Wait briefly then fetch the new run ID for polling
  await new Promise((r) => setTimeout(r, 2000))
  const latestRun = await getLatestRun()
  return latestRun
}

// # Get the most recent workflow run
export async function getLatestRun() {
  const { token, repo, workflow } = getConfig()
  if (!token) return null

  const res = await fetch(
    `${GITHUB_API}/repos/${repo}/actions/workflows/${workflow}/runs?per_page=1`,
    { headers: headers(token) }
  )

  if (!res.ok) return null
  const data = await res.json()
  return data.workflow_runs?.[0] ?? null
}

// # Get recent workflow runs (for dashboard history)
export async function getRecentRuns(limit = 10) {
  const { token, repo, workflow } = getConfig()
  if (!token) return []

  const res = await fetch(
    `${GITHUB_API}/repos/${repo}/actions/workflows/${workflow}/runs?per_page=${limit}`,
    { headers: headers(token) }
  )

  if (!res.ok) return []
  const data = await res.json()
  return (data.workflow_runs ?? []).map((r: any) => ({
    id: r.id,
    status: r.status,
    conclusion: r.conclusion,
    created_at: r.created_at,
    updated_at: r.updated_at,
    html_url: r.html_url,
  }))
}

// # Get a specific run with step-level progress
export async function getRunStatus(runId: string) {
  const { token, repo } = getConfig()
  if (!token) throw new Error('GITHUB_TOKEN not configured')
  if (!/^\d+$/.test(runId)) throw new Error('Invalid run ID')

  const [runRes, jobsRes] = await Promise.all([
    fetch(`${GITHUB_API}/repos/${repo}/actions/runs/${runId}`, {
      headers: headers(token),
    }),
    fetch(`${GITHUB_API}/repos/${repo}/actions/runs/${runId}/jobs`, {
      headers: headers(token),
    }),
  ])

  if (!runRes.ok) throw new Error('Run not found')

  const run = await runRes.json()
  const jobsData = jobsRes.ok ? await jobsRes.json() : { jobs: [] }

  const job = jobsData.jobs?.[0]
  const steps = (job?.steps ?? []).map((s: any) => ({
    name: s.name,
    status: s.status,
    conclusion: s.conclusion,
  }))

  const totalSteps = steps.length || 1
  const completedSteps = steps.filter((s: any) => s.status === 'completed').length
  const progress = Math.round((completedSteps / totalSteps) * 100)

  return {
    id: run.id,
    status: run.status,
    conclusion: run.conclusion,
    progress,
    steps,
    created_at: run.created_at,
    updated_at: run.updated_at,
    html_url: run.html_url,
  }
}

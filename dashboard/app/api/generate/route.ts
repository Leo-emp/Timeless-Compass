// # POST /api/generate — dispatch pipeline via GitHub Actions
// # GET /api/generate?run_id=xxx — poll run status
import { NextRequest, NextResponse } from 'next/server'
import { triggerWorkflow, getRecentRuns, getRunStatus } from '@/lib/github'

// # Auth check — fails closed in production (no password = 503)
function checkAuth(req: NextRequest): NextResponse | null {
  const password = process.env.DASHBOARD_PASSWORD

  if (!password) {
    if (process.env.NODE_ENV === 'production') {
      return NextResponse.json({ error: 'DASHBOARD_PASSWORD not configured' }, { status: 503 })
    }
    return null
  }

  const auth = req.headers.get('authorization')
  if (!auth?.startsWith('Bearer ')) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const token = auth.slice(7)
  if (token.length !== password.length || token !== password) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }
  return null
}

export async function POST(req: NextRequest) {
  const denied = checkAuth(req)
  if (denied) return denied

  try {
    let body: Record<string, string> = {}
    try { body = await req.json() } catch { /* empty body ok */ }

    const run = await triggerWorkflow({
      topic: body.topic,
      format: body.format,
      quality: body.quality,
    })

    return NextResponse.json({
      dispatched: true,
      run_id: run?.id ?? null,
      status: run?.status ?? 'unknown',
      html_url: run?.html_url ?? null,
    })
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : 'Dispatch failed'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

export async function GET(req: NextRequest) {
  const denied = checkAuth(req)
  if (denied) return denied

  const url = new URL(req.url)
  const runId = url.searchParams.get('run_id')

  try {
    if (runId) {
      const status = await getRunStatus(runId)
      return NextResponse.json(status)
    }

    const runs = await getRecentRuns(5)
    return NextResponse.json({ runs })
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : 'Failed to fetch'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

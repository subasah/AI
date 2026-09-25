import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type CallDetail, type CallSummary } from '../api'

export default function CallsPage() {
  const { id } = useParams()
  const [calls, setCalls] = useState<CallSummary[]>([])
  const [detail, setDetail] = useState<CallDetail | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (id) {
      api
        .getCall(id)
        .then(setDetail)
        .catch((err: Error) => setError(err.message))
      return
    }
    api
      .listCalls({ limit: 50 })
      .then(setCalls)
      .catch((err: Error) => setError(err.message))
  }, [id])

  if (id) {
    return (
      <div>
        <div className="page-head">
          <div>
            <Link to="/calls" className="muted" style={{ fontSize: '0.85rem' }}>
              ← All calls
            </Link>
            <h1 style={{ margin: '0.35rem 0 0' }}>Call debug</h1>
            <p>Transcript turns, tool request/response payloads, and agent events from MySQL.</p>
          </div>
        </div>
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
        {!detail && !error && <p className="muted">Loading…</p>}
        {detail && (
          <>
            <div className="panel" style={{ marginBottom: '1rem' }}>
              <div className="chip-row">
                <span className="chip">{detail.call.id}</span>
                <span className={`badge ${detail.call.status}`}>{detail.call.status}</span>
                <span className="chip">{detail.call.direction}</span>
                <span className="chip">{detail.call.pipeline_mode || 'n/a'}</span>
                <span className="chip">{detail.call.deployment_id}</span>
              </div>
            </div>

            <div className="grid grid-2">
              <div className="panel">
                <h2 style={{ marginTop: 0, fontSize: '1.1rem' }}>Turns (input / output)</h2>
                {detail.turns.map((t) => (
                  <div key={t.seq} style={{ marginBottom: '0.75rem', borderBottom: '1px solid var(--line)', paddingBottom: '0.6rem' }}>
                    <div className="muted" style={{ fontSize: '0.75rem' }}>
                      #{t.seq} · {t.role}
                      {t.agent_id ? ` · ${t.agent_id}` : ''}
                    </div>
                    <div style={{ whiteSpace: 'pre-wrap' }}>{t.content}</div>
                  </div>
                ))}
                {!detail.turns.length && <p className="muted">No turns recorded yet.</p>}
              </div>

              <div className="panel">
                <h2 style={{ marginTop: 0, fontSize: '1.1rem' }}>Tool I/O</h2>
                {detail.tool_io.map((t) => (
                  <div key={t.seq} style={{ marginBottom: '0.85rem', borderBottom: '1px solid var(--line)', paddingBottom: '0.6rem' }}>
                    <strong>{t.tool_name}</strong>{' '}
                    <span className={`badge ${t.ok ? 'active' : 'draft'}`}>{t.ok ? 'ok' : 'failed'}</span>
                    {t.latency_ms != null && (
                      <span className="muted" style={{ marginLeft: 8, fontSize: '0.75rem' }}>
                        {t.latency_ms}ms
                      </span>
                    )}
                    <pre style={{ fontSize: '0.75rem', overflow: 'auto', background: 'var(--bg-deep)', padding: '0.6rem', borderRadius: 8 }}>
                      {JSON.stringify({ arguments: t.arguments, result: t.result, error_code: t.error_code }, null, 2)}
                    </pre>
                  </div>
                ))}
                {!detail.tool_io.length && <p className="muted">No tool calls yet.</p>}
              </div>
            </div>

            <div className="panel" style={{ marginTop: '1rem' }}>
              <h2 style={{ marginTop: 0, fontSize: '1.1rem' }}>Events</h2>
              <table className="table">
                <thead>
                  <tr>
                    <th>Seq</th>
                    <th>Type</th>
                    <th>Payload</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.events.map((e) => (
                    <tr key={e.seq}>
                      <td>{e.seq}</td>
                      <td>{e.event_type}</td>
                      <td>
                        <code style={{ fontSize: '0.75rem' }}>{JSON.stringify(e.payload)}</code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    )
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1 style={{ margin: 0 }}>Call history</h1>
          <p>MySQL-backed transcripts and tool I/O for debugging agent behavior.</p>
        </div>
      </div>
      {error && (
        <div className="panel" style={{ marginBottom: '1rem', borderColor: 'rgba(212,103,90,0.4)' }}>
          <strong>Call log unavailable.</strong>
          <p className="muted" style={{ margin: '0.35rem 0 0' }}>
            {error}
          </p>
        </div>
      )}
      <div className="panel">
        <table className="table">
          <thead>
            <tr>
              <th>Call</th>
              <th>Direction</th>
              <th>Status</th>
              <th>Deployment</th>
              <th>Started</th>
            </tr>
          </thead>
          <tbody>
            {calls.map((c) => (
              <tr key={c.id}>
                <td>
                  <Link to={`/calls/${c.id}`}>{c.id.slice(0, 8)}…</Link>
                </td>
                <td className="muted">{c.direction}</td>
                <td>
                  <span className={`badge ${c.status}`}>{c.status}</span>
                </td>
                <td className="muted">{c.deployment_id}</td>
                <td className="muted">{c.started_at}</td>
              </tr>
            ))}
            {!calls.length && !error && (
              <tr>
                <td colSpan={5} className="muted">
                  No calls yet. Start an inbound/outbound session to populate MySQL.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

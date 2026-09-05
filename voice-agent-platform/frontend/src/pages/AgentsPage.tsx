import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Deployment } from '../api'

export default function AgentsPage() {
  const [deployments, setDeployments] = useState<Deployment[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .listDeployments()
      .then(setDeployments)
      .catch((err: Error) => setError(err.message))
  }, [])

  return (
    <div>
      <div className="page-head">
        <div>
          <h1 style={{ margin: 0 }}>Voice agents</h1>
          <p>Each deployment is a sellable agent package: swarm, flows, prompts, MCP, and tools.</p>
        </div>
        <Link className="btn btn-primary" to="/create">
          New delivery
        </Link>
      </div>

      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

      <div className="grid" style={{ gap: '0.85rem' }}>
        {deployments.map((d) => (
          <Link key={d.id} to={`/agents/${d.id}`} className="panel" style={{ display: 'block' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'start' }}>
              <div>
                <h2 style={{ margin: 0, fontSize: '1.2rem' }}>{d.name}</h2>
                <p className="muted" style={{ margin: '0.35rem 0 0' }}>
                  {d.industry.replace('_', ' ')} · {d.direction} ·{' '}
                  {d.voice?.pipeline_mode === 'classic' ? 'classic STT/TTS' : 'Gemini Live'} · v
                  {d.version}
                </p>
                <div className="chip-row" style={{ marginTop: '0.75rem' }}>
                  <span className="chip">{d.agents.length} agents</span>
                  <span className="chip">{d.tools.length} tools</span>
                  <span className="chip">{d.flows.length} flows</span>
                  <span className="chip">{d.mcp_servers.length} MCP</span>
                </div>
              </div>
              <span className={`badge ${d.status}`}>{d.status}</span>
            </div>
          </Link>
        ))}
        {!deployments.length && (
          <div className="panel muted">No agents yet. Create one from an industry template.</div>
        )}
      </div>
    </div>
  )
}

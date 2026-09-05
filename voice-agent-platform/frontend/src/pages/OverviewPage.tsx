import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Company, type Deployment } from '../api'

export default function OverviewPage() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [deployments, setDeployments] = useState<Deployment[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.listCompanies(), api.listDeployments()])
      .then(([c, d]) => {
        setCompanies(c)
        setDeployments(d)
      })
      .catch((err: Error) => setError(err.message))
  }, [])

  const active = deployments.filter((d) => d.status === 'active').length

  return (
    <div>
      <div className="page-head">
        <div>
          <h1 style={{ margin: 0 }}>Overview</h1>
          <p>Own the agent brain — sell the experience. Attach each customer&apos;s services via MCP or HTTP tools.</p>
        </div>
        <Link className="btn btn-primary" to="/create">
          Create voice agent
        </Link>
      </div>

      {error && (
        <div className="panel" style={{ marginBottom: '1rem', borderColor: 'rgba(212,103,90,0.4)' }}>
          <strong>API unreachable.</strong>
          <p className="muted" style={{ margin: '0.35rem 0 0' }}>
            Start the backend on :8080. {error}
          </p>
        </div>
      )}

      <div className="grid grid-3" style={{ marginBottom: '1.25rem' }}>
        <div className="panel">
          <div className="muted">Customer companies</div>
          <p className="stat-value">{companies.length}</p>
        </div>
        <div className="panel">
          <div className="muted">Voice agents</div>
          <p className="stat-value">{deployments.length}</p>
        </div>
        <div className="panel">
          <div className="muted">Active deliveries</div>
          <p className="stat-value">{active}</p>
        </div>
      </div>

      <div className="panel">
        <h2 style={{ marginTop: 0, fontSize: '1.2rem' }}>Recent deployments</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Industry</th>
              <th>Status</th>
              <th>Agents / Tools / MCP</th>
            </tr>
          </thead>
          <tbody>
            {deployments.slice(0, 8).map((d) => (
              <tr key={d.id}>
                <td>
                  <Link to={`/agents/${d.id}`}>{d.name}</Link>
                </td>
                <td className="muted">{d.industry.replace('_', ' ')}</td>
                <td>
                  <span className={`badge ${d.status}`}>{d.status}</span>
                </td>
                <td className="muted">
                  {d.agents.length} / {d.tools.length} / {d.mcp_servers.length}
                </td>
              </tr>
            ))}
            {!deployments.length && (
              <tr>
                <td colSpan={4} className="muted">
                  No deployments yet — create a company, then sell an agent from a template.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

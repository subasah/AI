import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

const EXPECTED = import.meta.env.VITE_ADMIN_TOKEN || 'dev-admin-token'

export default function LoginPage() {
  const [token, setToken] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (token.trim() !== EXPECTED) {
      setError('Invalid access token. Use the shared ADMIN_ACCESS_TOKEN.')
      return
    }
    localStorage.setItem('ava_access', token.trim())
    navigate('/')
  }

  return (
    <div className="login-wrap">
      <form className="login-panel" onSubmit={onSubmit}>
        <div className="brand-mark" style={{ marginBottom: '0.75rem' }}>
          Aether<span>Voice</span>
        </div>
        <h1>Operator access</h1>
        <p>
          Your team creates voice agents here, configures flows/prompts/MCP/tools, then delivers them to
          customer companies.
        </p>
        <div className="field">
          <label htmlFor="token">Access token</label>
          <input
            id="token"
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="dev-admin-token"
            autoFocus
          />
        </div>
        {error && <p style={{ color: 'var(--danger)', fontSize: '0.9rem' }}>{error}</p>}
        <button className="btn btn-primary" type="submit" style={{ width: '100%' }}>
          Enter control plane
        </button>
      </form>
    </div>
  )
}

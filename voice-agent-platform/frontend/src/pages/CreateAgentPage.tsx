import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type Company, type Industry, type TemplateInfo } from '../api'

export default function CreateAgentPage() {
  const navigate = useNavigate()
  const [companies, setCompanies] = useState<Company[]>([])
  const [templates, setTemplates] = useState<TemplateInfo[]>([])
  const [companyId, setCompanyId] = useState('')
  const [industry, setIndustry] = useState<Industry>('restaurant')
  const [name, setName] = useState('')
  const [phones, setPhones] = useState('')
  const [direction, setDirection] = useState<'inbound' | 'outbound' | 'both'>('both')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    Promise.all([api.listCompanies(), api.listTemplates()])
      .then(([c, t]) => {
        setCompanies(c)
        setTemplates(t)
        if (c[0]) {
          setCompanyId(c[0].id)
          setIndustry(c[0].industry === 'custom' ? 'restaurant' : c[0].industry)
          setName(`${c[0].name} Voice Agent`)
        }
      })
      .catch((err: Error) => setError(err.message))
  }, [])

  useEffect(() => {
    const company = companies.find((c) => c.id === companyId)
    if (company && !name) setName(`${company.name} Voice Agent`)
  }, [companyId, companies, name])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const dep = await api.createDeployment({
        name,
        company_id: companyId,
        industry,
        direction,
        from_template: true,
        phone_numbers: phones
          .split(',')
          .map((p) => p.trim())
          .filter(Boolean),
        created_by: 'platform-admin',
      })
      navigate(`/agents/${dep.id}`)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1 style={{ margin: 0 }}>Create & sell</h1>
          <p>
            Pick a customer and industry template. You keep control of the swarm, prompts, flows, MCP, and
            tools — then point tools at their internal services.
          </p>
        </div>
      </div>

      <form className="panel" onSubmit={onSubmit} style={{ maxWidth: 720 }}>
        <div className="field">
          <label>Sell to company</label>
          <select value={companyId} onChange={(e) => setCompanyId(e.target.value)} required>
            {!companies.length && <option value="">Create a company first</option>}
            {companies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label>Industry template</label>
          <div className="grid" style={{ gap: '0.6rem' }}>
            {templates.map((t) => (
              <button
                key={t.industry}
                type="button"
                className="btn btn-ghost"
                onClick={() => setIndustry(t.industry)}
                style={{
                  textAlign: 'left',
                  borderColor: industry === t.industry ? 'rgba(61,155,110,0.55)' : undefined,
                  background: industry === t.industry ? 'rgba(61,155,110,0.12)' : undefined,
                }}
              >
                <strong>{t.label}</strong>
                <div className="muted" style={{ fontSize: '0.85rem', marginTop: 4 }}>
                  {t.description}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="field">
          <label>Deployment name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </div>

        <div className="grid grid-2">
          <div className="field">
            <label>Direction</label>
            <select value={direction} onChange={(e) => setDirection(e.target.value as typeof direction)}>
              <option value="both">Inbound + outbound</option>
              <option value="inbound">Inbound only</option>
              <option value="outbound">Outbound only</option>
            </select>
          </div>
          <div className="field">
            <label>Phone numbers (comma-separated)</label>
            <input
              value={phones}
              onChange={(e) => setPhones(e.target.value)}
              placeholder="+15555550101"
            />
          </div>
        </div>

        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

        <button className="btn btn-primary" type="submit" disabled={busy || !companyId}>
          {busy ? 'Creating…' : 'Create deployment'}
        </button>
      </form>
    </div>
  )
}

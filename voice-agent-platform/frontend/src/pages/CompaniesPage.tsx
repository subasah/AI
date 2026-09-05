import { useEffect, useState, type FormEvent } from 'react'
import { api, type Company, type Industry } from '../api'

const industries: Industry[] = ['restaurant', 'car_dealer', 'mortgage_servicing', 'custom']

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [name, setName] = useState('')
  const [industry, setIndustry] = useState<Industry>('restaurant')
  const [email, setEmail] = useState('')
  const [brand, setBrand] = useState('professional, warm, concise')
  const [error, setError] = useState('')

  async function refresh() {
    setCompanies(await api.listCompanies())
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message))
  }, [])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await api.createCompany({
        name,
        industry,
        contact_email: email || null,
        brand_voice: brand,
        timezone: 'America/New_York',
      })
      setName('')
      setEmail('')
      await refresh()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1 style={{ margin: 0 }}>Companies</h1>
          <p>Customers you sell to. You keep ownership of flows, prompts, skills, agents, and tool wiring.</p>
        </div>
      </div>

      <div className="grid grid-2">
        <form className="panel" onSubmit={onCreate}>
          <h2 style={{ marginTop: 0, fontSize: '1.15rem' }}>Add company</h2>
          <div className="field">
            <label>Company name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="Harbor Bistro" />
          </div>
          <div className="field">
            <label>Industry</label>
            <select value={industry} onChange={(e) => setIndustry(e.target.value as Industry)}>
              {industries.map((i) => (
                <option key={i} value={i}>
                  {i.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Contact email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="ops@customer.com" />
          </div>
          <div className="field">
            <label>Brand voice</label>
            <input value={brand} onChange={(e) => setBrand(e.target.value)} />
          </div>
          {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
          <button className="btn btn-primary" type="submit">
            Save company
          </button>
        </form>

        <div className="panel">
          <h2 style={{ marginTop: 0, fontSize: '1.15rem' }}>Directory</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Industry</th>
                <th>Voice</th>
              </tr>
            </thead>
            <tbody>
              {companies.map((c) => (
                <tr key={c.id}>
                  <td>
                    <div>{c.name}</div>
                    <div className="muted" style={{ fontSize: '0.75rem' }}>
                      {c.id}
                    </div>
                  </td>
                  <td className="muted">{c.industry.replace('_', ' ')}</td>
                  <td className="muted">{c.brand_voice}</td>
                </tr>
              ))}
              {!companies.length && (
                <tr>
                  <td colSpan={3} className="muted">
                    No companies yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

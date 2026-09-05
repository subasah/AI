import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type Deployment, type PipelineMode } from '../api'

export default function AgentDetailPage() {
  const { id } = useParams()
  const [dep, setDep] = useState<Deployment | null>(null)
  const [error, setError] = useState('')
  const [mcpUrl, setMcpUrl] = useState('https://CUSTOMER_MCP_HOST/sse')
  const [mcpId, setMcpId] = useState('customer_services')
  const [toolName, setToolName] = useState('')
  const [toolDesc, setToolDesc] = useState('')
  const [toolUrl, setToolUrl] = useState('')
  const [preamble, setPreamble] = useState('')
  const [pipelineMode, setPipelineMode] = useState<PipelineMode>('gemini_live')
  const [geminiVoice, setGeminiVoice] = useState('Puck')
  const [geminiModel, setGeminiModel] = useState(
    'models/gemini-2.5-flash-native-audio-preview-12-2025',
  )
  const [message, setMessage] = useState('')

  async function refresh() {
    if (!id) return
    const d = await api.getDeployment(id)
    setDep(d)
    setPreamble(d.global_system_preamble || '')
    setPipelineMode(d.voice?.pipeline_mode || 'gemini_live')
    setGeminiVoice(d.voice?.gemini_voice || 'Puck')
    setGeminiModel(d.voice?.gemini_model || 'models/gemini-2.5-flash-native-audio-preview-12-2025')
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message))
  }, [id])

  async function activate() {
    if (!id) return
    const d = await api.activateDeployment(id)
    setDep(d)
    setMessage('Deployment activated — ready for inbound/outbound handlers.')
  }

  async function savePreamble(e: FormEvent) {
    e.preventDefault()
    if (!id) return
    const d = await api.patchDeployment(id, { global_system_preamble: preamble })
    setDep(d)
    setMessage('Prompts updated.')
  }

  async function saveVoice(e: FormEvent) {
    e.preventDefault()
    if (!id || !dep) return
    const d = await api.patchDeployment(id, {
      voice: {
        ...dep.voice,
        pipeline_mode: pipelineMode,
        gemini_voice: geminiVoice,
        gemini_model: geminiModel,
        gemini_api_key_ref: 'GOOGLE_API_KEY',
      },
    })
    setDep(d)
    setMessage(
      pipelineMode === 'gemini_live'
        ? 'Voice pipeline set to Gemini Live Flash (speech → speech). Only GOOGLE_API_KEY needed.'
        : 'Voice pipeline set to classic STT → LLM → TTS (Deepgram + OpenAI + Cartesia).',
    )
  }

  async function attachMcp(e: FormEvent) {
    e.preventDefault()
    if (!id) return
    const d = await api.attachMcp(id, {
      id: mcpId,
      name: 'Customer MCP',
      transport: 'sse',
      url: mcpUrl,
      enabled: true,
      include_tools: [],
    })
    setDep(d)
    setMessage('MCP server attached. Enable credentials in .env when ready.')
  }

  async function attachTool(e: FormEvent) {
    e.preventDefault()
    if (!id) return
    const d = await api.attachTool(id, {
      name: toolName,
      description: toolDesc,
      endpoint_url: toolUrl || null,
      mock_response: { ok: true, note: 'Replace with live customer API' },
    })
    setDep(d)
    setToolName('')
    setToolDesc('')
    setToolUrl('')
    setMessage('Tool attached — point endpoint_url at the customer service anytime.')
  }

  if (error) return <p style={{ color: 'var(--danger)' }}>{error}</p>
  if (!dep) return <p className="muted">Loading…</p>

  return (
    <div>
      <div className="page-head">
        <div>
          <Link to="/agents" className="muted" style={{ fontSize: '0.85rem' }}>
            ← All agents
          </Link>
          <h1 style={{ margin: '0.35rem 0 0' }}>{dep.name}</h1>
          <p>
            {dep.industry.replace('_', ' ')} · company {dep.company_id} · entry agent{' '}
            {dep.entry_agent_id || '—'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <span className={`badge ${dep.status}`}>{dep.status}</span>
          {dep.status !== 'active' && (
            <button className="btn btn-primary" onClick={() => activate().catch((e) => setError(e.message))}>
              Activate
            </button>
          )}
        </div>
      </div>

      {message && (
        <div className="panel" style={{ marginBottom: '1rem', borderColor: 'rgba(61,155,110,0.35)' }}>
          {message}
        </div>
      )}

      <div className="grid grid-2" style={{ marginBottom: '1rem' }}>
        <div className="panel">
          <h2 style={{ marginTop: 0, fontSize: '1.1rem' }}>Swarm agents</h2>
          {dep.agents.map((a) => (
            <div key={a.id} style={{ marginBottom: '0.85rem', paddingBottom: '0.85rem', borderBottom: '1px solid var(--line)' }}>
              <strong>{a.name}</strong>
              <div className="muted" style={{ fontSize: '0.85rem' }}>
                {a.role}
              </div>
              <div className="chip-row" style={{ marginTop: '0.45rem' }}>
                {a.tool_names.map((t) => (
                  <span className="chip" key={t}>
                    {t}
                  </span>
                ))}
                {a.handoff_targets.map((h) => (
                  <span className="chip" key={h}>
                    → {h}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="panel">
          <h2 style={{ marginTop: 0, fontSize: '1.1rem' }}>Tools & MCP</h2>
          <div className="chip-row" style={{ marginBottom: '0.75rem' }}>
            {dep.tools.map((t) => (
              <span className="chip" key={t.name} title={t.description}>
                {t.name}
                {t.mcp_binding ? ' (mcp)' : t.endpoint_url ? ' (http)' : ' (mock)'}
              </span>
            ))}
          </div>
          {dep.mcp_servers.map((m) => (
            <div key={m.id} className="muted" style={{ fontSize: '0.85rem', marginBottom: '0.35rem' }}>
              MCP <strong style={{ color: 'var(--text)' }}>{m.name}</strong> · {m.url || 'no url'} ·{' '}
              {m.enabled ? 'enabled' : 'disabled'}
            </div>
          ))}
          <div style={{ marginTop: '0.75rem' }}>
            <div className="muted" style={{ fontSize: '0.85rem' }}>Flows</div>
            <div className="chip-row">
              {dep.flows.map((f) => (
                <span className="chip" key={f.id}>
                  {f.name}
                </span>
              ))}
              {!dep.flows.length && <span className="muted">None</span>}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-2" style={{ marginBottom: '1rem' }}>
        <form className="panel" onSubmit={saveVoice}>
          <h2 style={{ marginTop: 0, fontSize: '1.1rem' }}>Voice pipeline</h2>
          <p className="muted" style={{ marginTop: 0, fontSize: '0.85rem' }}>
            Gemini Live Flash takes caller audio and returns audio directly — no Deepgram or Cartesia.
          </p>
          <div className="field">
            <label>Mode</label>
            <select
              value={pipelineMode}
              onChange={(e) => setPipelineMode(e.target.value as PipelineMode)}
            >
              <option value="gemini_live">Gemini Live Flash (speech → speech)</option>
              <option value="classic">Classic (Deepgram STT → LLM → Cartesia TTS)</option>
            </select>
          </div>
          {pipelineMode === 'gemini_live' && (
            <>
              <div className="field">
                <label>Gemini voice</label>
                <select value={geminiVoice} onChange={(e) => setGeminiVoice(e.target.value)}>
                  {['Puck', 'Charon', 'Kore', 'Fenrir', 'Aoede'].map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Model</label>
                <input value={geminiModel} onChange={(e) => setGeminiModel(e.target.value)} />
              </div>
              <p className="muted" style={{ fontSize: '0.8rem' }}>
                Secret: <code>GOOGLE_API_KEY</code> in <code>.env</code>
              </p>
            </>
          )}
          {pipelineMode === 'classic' && (
            <p className="muted" style={{ fontSize: '0.8rem' }}>
              Secrets: <code>DEEPGRAM_API_KEY</code>, <code>OPENAI_API_KEY</code>,{' '}
              <code>CARTESIA_API_KEY</code>
            </p>
          )}
          <button className="btn btn-primary" type="submit">
            Save voice pipeline
          </button>
        </form>

        <form className="panel" onSubmit={savePreamble}>
          <h2 style={{ marginTop: 0, fontSize: '1.1rem' }}>Global prompt (you own this)</h2>
          <div className="field">
            <label>System preamble</label>
            <textarea value={preamble} onChange={(e) => setPreamble(e.target.value)} />
          </div>
          <button className="btn btn-primary" type="submit">
            Save prompts
          </button>
        </form>
      </div>

      <div className="grid grid-2">
        <form className="panel" onSubmit={attachMcp}>
          <h2 style={{ marginTop: 0, fontSize: '1.1rem' }}>Attach MCP</h2>
          <div className="field">
            <label>Server id</label>
            <input value={mcpId} onChange={(e) => setMcpId(e.target.value)} required />
          </div>
          <div className="field">
            <label>SSE URL</label>
            <input value={mcpUrl} onChange={(e) => setMcpUrl(e.target.value)} required />
          </div>
          <button className="btn btn-ghost" type="submit">
            Attach MCP server
          </button>
        </form>

        <form className="panel" onSubmit={attachTool}>
          <h2 style={{ marginTop: 0, fontSize: '1.1rem' }}>Attach another service (tool)</h2>
          <div className="field">
            <label>Tool name</label>
            <input value={toolName} onChange={(e) => setToolName(e.target.value)} required placeholder="get_loyalty_points" />
          </div>
          <div className="field">
            <label>Description (LLM reads this)</label>
            <input value={toolDesc} onChange={(e) => setToolDesc(e.target.value)} required />
          </div>
          <div className="field">
            <label>Customer endpoint URL (optional until live)</label>
            <input value={toolUrl} onChange={(e) => setToolUrl(e.target.value)} placeholder="https://api.customer.com/loyalty" />
          </div>
          <button className="btn btn-ghost" type="submit">
            Attach tool
          </button>
        </form>
      </div>
    </div>
  )
}

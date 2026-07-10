export type Industry = 'restaurant' | 'car_dealer' | 'mortgage_servicing' | 'custom'

export interface Company {
  id: string
  name: string
  industry: Industry
  contact_email?: string | null
  timezone: string
  brand_voice: string
  metadata?: Record<string, unknown>
}

export interface ToolConfig {
  name: string
  description: string
  endpoint_url?: string | null
  mcp_binding?: string | null
  auth_secret_ref?: string | null
  mock_response?: Record<string, unknown> | null
}

export interface MCPServerConfig {
  id: string
  name: string
  transport: string
  url?: string | null
  enabled: boolean
  include_tools: string[]
}

export interface AgentConfig {
  id: string
  name: string
  role: string
  system_prompt: string
  entry_message?: string
  tool_names: string[]
  skill_ids: string[]
  handoff_targets: string[]
}

export type PipelineMode = 'gemini_live' | 'classic'

export interface VoiceProviderConfig {
  pipeline_mode: PipelineMode
  gemini_model?: string
  gemini_voice?: string
  gemini_api_key_ref?: string
  gemini_language?: string
  gemini_use_local_vad?: boolean
  stt_provider?: string
  tts_provider?: string
  llm_provider?: string
  llm_model?: string
  tts_voice_id?: string | null
}

export interface Deployment {
  id: string
  name: string
  company_id: string
  industry: Industry
  direction: 'inbound' | 'outbound' | 'both'
  status: string
  voice: VoiceProviderConfig
  agents: AgentConfig[]
  tools: ToolConfig[]
  skills: { id: string; name: string }[]
  flows: { id: string; name: string }[]
  mcp_servers: MCPServerConfig[]
  entry_agent_id?: string | null
  phone_numbers: string[]
  outbound_script?: string | null
  global_system_preamble?: string
  tags: string[]
  version: number
  created_by?: string | null
}

export interface TemplateInfo {
  industry: Industry
  label: string
  description: string
}

const API = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') || ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<{ status: string }>('/api/health'),
  listCompanies: () => request<Company[]>('/api/companies'),
  createCompany: (body: Partial<Company> & { name: string }) =>
    request<Company>('/api/companies', { method: 'POST', body: JSON.stringify(body) }),
  listDeployments: (companyId?: string) =>
    request<Deployment[]>(`/api/deployments${companyId ? `?company_id=${companyId}` : ''}`),
  getDeployment: (id: string) => request<Deployment>(`/api/deployments/${id}`),
  createDeployment: (body: Record<string, unknown>) =>
    request<Deployment>('/api/deployments', { method: 'POST', body: JSON.stringify(body) }),
  patchDeployment: (id: string, body: Record<string, unknown>) =>
    request<Deployment>(`/api/deployments/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  activateDeployment: (id: string) =>
    request<Deployment>(`/api/deployments/${id}/activate`, { method: 'POST' }),
  attachMcp: (id: string, server: MCPServerConfig) =>
    request<Deployment>(`/api/deployments/${id}/mcp`, {
      method: 'POST',
      body: JSON.stringify({ server }),
    }),
  attachTool: (id: string, tool: ToolConfig) =>
    request<Deployment>(`/api/deployments/${id}/tools`, {
      method: 'POST',
      body: JSON.stringify({ tool }),
    }),
  listTemplates: () => request<TemplateInfo[]>('/api/templates'),
  previewTemplate: (industry: Industry, company_name: string) =>
    request<Deployment>('/api/templates/preview', {
      method: 'POST',
      body: JSON.stringify({ industry, company_name, company_id: 'preview' }),
    }),
}

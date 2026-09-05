"""Pydantic models for multi-tenant voice agent configuration.

Your company owns flows, prompts, MCP attachments, skills, agents, and tool
wiring. Customer companies receive a deployment that points at their internal
services via MCP / HTTP tool endpoints.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Industry(str, Enum):
    RESTAURANT = "restaurant"
    CAR_DEALER = "car_dealer"
    MORTGAGE_SERVICING = "mortgage_servicing"
    CUSTOM = "custom"


class CallDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BOTH = "both"


class ToolAuthType(str, Enum):
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"
    OAUTH2 = "oauth2"


class ToolConfig(BaseModel):
    """One function the LLM can call — does one job."""

    name: str
    description: str
    parameters: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}, "required": []}
    )
    # How to execute against the customer's internal service
    endpoint_url: str | None = None
    http_method: str = "POST"
    auth_type: ToolAuthType = ToolAuthType.NONE
    auth_header: str = "Authorization"
    # Secret name in env / vault — never store raw tokens in config
    auth_secret_ref: str | None = None
    # Optional MCP tool binding: "server_id/tool_name"
    mcp_binding: str | None = None
    timeout_seconds: float = 15.0
    mock_response: dict[str, Any] | None = None


class SkillConfig(BaseModel):
    """A cluster of related tools + a focused sub-prompt."""

    id: str
    name: str
    description: str
    system_prompt: str
    tool_names: list[str] = Field(default_factory=list)
    flow_id: str | None = None


class AgentConfig(BaseModel):
    """LLM + prompt + tools pursuing an autonomous goal."""

    id: str
    name: str
    role: str
    system_prompt: str
    entry_message: str = ""
    skill_ids: list[str] = Field(default_factory=list)
    tool_names: list[str] = Field(default_factory=list)
    # Agent IDs this agent may hand off to
    handoff_targets: list[str] = Field(default_factory=list)
    temperature: float = 0.4
    max_tokens: int = 512


class FlowState(BaseModel):
    id: str
    instruction: str
    allowed_tools: list[str] = Field(default_factory=list)
    transitions: dict[str, str] = Field(default_factory=dict)
    is_terminal: bool = False


class FlowConfig(BaseModel):
    """Finite state machine that constrains LLM improvisation."""

    id: str
    name: str
    description: str
    initial_state: str
    states: list[FlowState]


class MCPServerConfig(BaseModel):
    """Attach a customer's MCP server so tools/resources are discoverable."""

    id: str
    name: str
    transport: str = "sse"  # sse | stdio | streamable_http
    url: str | None = None
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env_secret_refs: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
    # Tools exposed by this server that should be registered
    include_tools: list[str] = Field(default_factory=list)


class PipelineMode(str, Enum):
    """How audio is processed end-to-end.

    - gemini_live: speech → Gemini Live Flash → speech (no separate STT/TTS)
    - classic: Deepgram STT → LLM → Cartesia/ElevenLabs TTS
    """

    GEMINI_LIVE = "gemini_live"
    CLASSIC = "classic"


class VoiceProviderConfig(BaseModel):
    # Default: multimodal Gemini Live (voice in → voice out)
    pipeline_mode: PipelineMode = PipelineMode.GEMINI_LIVE

    # --- Gemini Live (speech-to-speech) ---
    # e.g. models/gemini-2.5-flash-native-audio-preview-12-2025
    gemini_model: str = "models/gemini-2.5-flash-native-audio-preview-12-2025"
    gemini_voice: str = "Puck"  # Puck | Charon | Kore | Fenrir | Aoede | ...
    gemini_api_key_ref: str = "GOOGLE_API_KEY"
    gemini_language: str = "en-US"
    # Server-side VAD is built into Gemini Live; set True to use local Silero instead
    gemini_use_local_vad: bool = False

    # --- Classic cascade (only used when pipeline_mode=classic) ---
    stt_provider: str = "deepgram"
    tts_provider: str = "cartesia"
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    tts_voice_id: str | None = None
    stt_api_key_ref: str = "DEEPGRAM_API_KEY"
    tts_api_key_ref: str = "CARTESIA_API_KEY"
    llm_api_key_ref: str = "OPENAI_API_KEY"

    transport: str = "daily"  # daily | twilio | webrtc
    daily_api_key_ref: str = "DAILY_API_KEY"
    twilio_account_sid_ref: str = "TWILIO_ACCOUNT_SID"
    twilio_auth_token_ref: str = "TWILIO_AUTH_TOKEN"
    twilio_phone_number_ref: str = "TWILIO_PHONE_NUMBER"

    def required_secret_refs(self) -> list[str]:
        if self.pipeline_mode == PipelineMode.GEMINI_LIVE:
            return [self.gemini_api_key_ref]
        return [self.stt_api_key_ref, self.tts_api_key_ref, self.llm_api_key_ref]


class CompanyConfig(BaseModel):
    """Customer company you sell / deliver a voice agent to."""

    id: str
    name: str
    industry: Industry = Industry.CUSTOM
    contact_email: str | None = None
    timezone: str = "America/New_York"
    brand_voice: str = "professional, warm, concise"
    metadata: dict[str, Any] = Field(default_factory=dict)


class VoiceAgentDeployment(BaseModel):
    """Full owned configuration for one customer deployment.

    Your company controls: flows, prompts, MCP, skills, agents, tool calling.
    Customer provides: internal service endpoints / MCP servers / secrets.
    """

    id: str
    name: str
    company_id: str
    industry: Industry = Industry.CUSTOM
    direction: CallDirection = CallDirection.BOTH
    status: str = "draft"  # draft | active | paused | archived
    voice: VoiceProviderConfig = Field(default_factory=VoiceProviderConfig)
    agents: list[AgentConfig] = Field(default_factory=list)
    skills: list[SkillConfig] = Field(default_factory=list)
    tools: list[ToolConfig] = Field(default_factory=list)
    flows: list[FlowConfig] = Field(default_factory=list)
    mcp_servers: list[MCPServerConfig] = Field(default_factory=list)
    # Which agent greets inbound / starts outbound
    entry_agent_id: str | None = None
    global_system_preamble: str = (
        "You are a voice agent. Keep replies to 1–3 short sentences. "
        "Never invent facts — only speak from tool results. "
        "If the caller asks for a human, escalate immediately."
    )
    outbound_script: str | None = None
    phone_numbers: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_by: str | None = None
    version: int = 1

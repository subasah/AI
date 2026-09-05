"""Industry-agnostic voice agent library.

Building blocks (from tool → skill → agent → swarm → MCP):
  Tool   — one function the LLM can call
  Skill  — related tools + a focused sub-prompt
  Agent  — LLM + prompt + tools pursuing a goal
  Swarm  — agents that hand off work to each other
  MCP    — standardized connector for customer services
"""

from library.agents.base import BaseAgent
from library.config.models import (
    AgentConfig,
    CompanyConfig,
    FlowConfig,
    MCPServerConfig,
    SkillConfig,
    ToolConfig,
    VoiceAgentDeployment,
)
from library.swarm.orchestrator import SwarmOrchestrator
from library.tools.dispatcher import ToolDispatcher

__all__ = [
    "BaseAgent",
    "AgentConfig",
    "CompanyConfig",
    "FlowConfig",
    "MCPServerConfig",
    "SkillConfig",
    "ToolConfig",
    "VoiceAgentDeployment",
    "SwarmOrchestrator",
    "ToolDispatcher",
]

__version__ = "0.1.0"

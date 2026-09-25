from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from library.config.models import AgentConfig, SkillConfig, ToolConfig


class BaseAgent(ABC):
    """Abstract agent: prompt + tools + optional entry message."""

    def __init__(
        self,
        config: AgentConfig,
        skills: list[SkillConfig] | None = None,
        tools: list[ToolConfig] | None = None,
    ) -> None:
        self.config = config
        self.skills = skills or []
        self.tools = tools or []

    @abstractmethod
    def get_system_instruction(self) -> str:
        ...

    def get_tools(self) -> list[dict[str, Any]]:
        """OpenAI-style tool declarations for the LLM."""
        declarations: list[dict[str, Any]] = []
        for tool in self.tools:
            declarations.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
            )
        # Handoff tools for swarm routing
        for target in self.config.handoff_targets:
            declarations.append(
                {
                    "type": "function",
                    "function": {
                        "name": f"transfer_to_{target}",
                        "description": (
                            f"Transfer the caller to the '{target}' agent. "
                            "Call this when the caller's need matches that agent's role."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "reason": {
                                    "type": "string",
                                    "description": "Brief reason for the handoff",
                                }
                            },
                            "required": ["reason"],
                        },
                    },
                }
            )
        return declarations

    def get_entry_message(self) -> str:
        return self.config.entry_message

    def get_tool_names(self) -> list[str]:
        names = list(self.config.tool_names)
        for skill in self.skills:
            names.extend(skill.tool_names)
        return list(dict.fromkeys(names))


class ConfigurableAgent(BaseAgent):
    """Agent fully driven by deployment config (industry-agnostic)."""

    def get_system_instruction(self) -> str:
        parts = [self.config.system_prompt]
        for skill in self.skills:
            parts.append(f"\n## Skill: {skill.name}\n{skill.system_prompt}")
        if self.config.handoff_targets:
            targets = ", ".join(self.config.handoff_targets)
            parts.append(
                f"\n## Handoffs\nYou may transfer to: {targets}. "
                "Use the matching transfer_to_* tool when appropriate."
            )
        return "\n".join(parts)

from __future__ import annotations

from typing import Any

from loguru import logger

from library.agents.base import ConfigurableAgent
from library.config.models import VoiceAgentDeployment
from library.observability.call_logger import CallLogger


class SwarmOrchestrator:
    """Manages agent handoffs for a single call."""

    def __init__(
        self,
        deployment: VoiceAgentDeployment,
        agents: dict[str, ConfigurableAgent],
        call_logger: CallLogger | None = None,
    ) -> None:
        self.deployment = deployment
        self.agents = agents
        self.logger = call_logger or CallLogger(call_id="unknown")
        entry = deployment.entry_agent_id or (deployment.agents[0].id if deployment.agents else None)
        if not entry or entry not in agents:
            raise ValueError("Deployment has no valid entry_agent_id")
        self.active_agent_id = entry
        self.handoff_history: list[dict[str, Any]] = []

    @property
    def active(self) -> ConfigurableAgent:
        return self.agents[self.active_agent_id]

    def system_prompt(self) -> str:
        preamble = self.deployment.global_system_preamble
        return f"{preamble}\n\n{self.active.get_system_instruction()}"

    def tools(self) -> list[dict[str, Any]]:
        return self.active.get_tools()

    def entry_message(self) -> str:
        return self.active.get_entry_message()

    def maybe_handoff(self, tool_name: str, reason: str = "") -> bool:
        """If tool_name is transfer_to_<agent_id>, switch active agent."""
        prefix = "transfer_to_"
        if not tool_name.startswith(prefix):
            return False
        target = tool_name[len(prefix) :]
        if target not in self.agents:
            self.logger.log("handoff_failed", target=target, reason="unknown_agent")
            return False
        if target not in self.active.config.handoff_targets:
            self.logger.log("handoff_denied", target=target, from_agent=self.active_agent_id)
            return False

        previous = self.active_agent_id
        self.active_agent_id = target
        record = {"from": previous, "to": target, "reason": reason}
        self.handoff_history.append(record)
        self.logger.log("handoff", **record)
        logger.info("Handoff {} → {} ({})", previous, target, reason)
        return True

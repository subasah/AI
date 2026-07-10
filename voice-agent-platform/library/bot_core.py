"""Assemble a Pipecat-style voice pipeline from a VoiceAgentDeployment.

API tokens are read from environment via secret refs. Until you buy/add keys,
the bot can still boot in mock mode for config validation.
"""

from __future__ import annotations

import os
from typing import Any

from loguru import logger

from library.agents.factory import build_agents
from library.config.models import VoiceAgentDeployment
from library.mcp.client import MCPClientManager
from library.observability.call_logger import CallLogger
from library.swarm.orchestrator import SwarmOrchestrator
from library.tools.dispatcher import ToolDispatcher


def resolve_secret(ref: str | None) -> str | None:
    if not ref:
        return None
    return os.getenv(ref) or None


class VoiceBotSession:
    """Runtime session for one phone/WebRTC call."""

    def __init__(self, deployment: VoiceAgentDeployment, call_id: str | None = None) -> None:
        self.deployment = deployment
        self.logger = CallLogger(call_id=call_id, company_id=deployment.company_id)
        self.mcp = MCPClientManager(deployment.mcp_servers)
        self.dispatcher = ToolDispatcher(
            deployment.tools,
            call_logger=self.logger,
            secret_resolver=resolve_secret,
            mcp_client=self.mcp,
        )
        self.agents = build_agents(deployment)
        self.swarm = SwarmOrchestrator(deployment, self.agents, call_logger=self.logger)
        self._register_handoff_handlers()

    def _register_handoff_handlers(self) -> None:
        for agent in self.agents.values():
            for target in agent.config.handoff_targets:

                async def _handoff(args: dict[str, Any], _t: str = target) -> dict[str, Any]:
                    ok = self.swarm.maybe_handoff(f"transfer_to_{_t}", reason=args.get("reason", ""))
                    return {
                        "transferred": ok,
                        "active_agent": self.swarm.active_agent_id,
                        "entry_message": self.swarm.entry_message() if ok else None,
                    }

                self.dispatcher.register(f"transfer_to_{target}", _handoff)

    async def start(self) -> dict[str, Any]:
        await self.mcp.connect_all()
        self.logger.log(
            "session_start",
            deployment_id=self.deployment.id,
            entry_agent=self.swarm.active_agent_id,
        )
        return {
            "call_id": self.logger.call_id,
            "system_prompt": self.swarm.system_prompt(),
            "tools": self.swarm.tools(),
            "entry_message": self.swarm.entry_message(),
            "voice": self.deployment.voice.model_dump(),
        }

    async def handle_tool_call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = await self.dispatcher.handle(name, arguments)
        # Refresh prompt/tools after possible handoff
        if name.startswith("transfer_to_") and result.get("ok"):
            result["session"] = {
                "system_prompt": self.swarm.system_prompt(),
                "tools": self.swarm.tools(),
                "entry_message": self.swarm.entry_message(),
            }
        return result

    def missing_secrets(self) -> list[str]:
        voice = self.deployment.voice
        refs = [
            voice.stt_api_key_ref,
            voice.tts_api_key_ref,
            voice.llm_api_key_ref,
        ]
        missing = [r for r in refs if not resolve_secret(r)]
        return missing

    async def build_pipecat_pipeline(self) -> Any:
        """Optional live Pipecat pipeline when dependencies + keys exist."""
        missing = self.missing_secrets()
        if missing:
            logger.warning(
                "Pipecat pipeline deferred — missing secrets: {}. "
                "Session still usable for config/tool dry-runs.",
                missing,
            )
            return None

        try:
            from pipecat.audio.vad.silero import SileroVADAnalyzer
            from pipecat.audio.vad.vad_analyzer import VADParams
            from pipecat.pipeline.pipeline import Pipeline
            from pipecat.processors.aggregators.llm_context import LLMContext
            from pipecat.processors.aggregators.llm_response_universal import (
                LLMContextAggregatorPair,
            )
            from pipecat.services.cartesia.tts import CartesiaTTSService
            from pipecat.services.deepgram.stt import DeepgramSTTService
            from pipecat.services.openai.llm import OpenAILLMService
        except ImportError:
            logger.warning("pipecat not installed — skipping live pipeline assembly")
            return None

        voice = self.deployment.voice
        stt = DeepgramSTTService(api_key=resolve_secret(voice.stt_api_key_ref))
        tts = CartesiaTTSService(
            api_key=resolve_secret(voice.tts_api_key_ref),
            voice_id=voice.tts_voice_id or "71a7ad14-091c-4e8e-a314-022ece01c121",
        )
        llm = OpenAILLMService(
            api_key=resolve_secret(voice.llm_api_key_ref),
            model=voice.llm_model,
        )

        messages = [{"role": "system", "content": self.swarm.system_prompt()}]
        context = LLMContext(messages)
        context_aggregator = LLMContextAggregatorPair(context)

        # Transport is attached by incoming/outgoing handlers
        pipeline = Pipeline(
            [
                stt,
                context_aggregator.user(),
                llm,
                tts,
                context_aggregator.assistant(),
            ]
        )
        return {
            "pipeline": pipeline,
            "vad": SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            "context": context,
            "session": self,
        }

    async def close(self) -> None:
        await self.mcp.close()
        self.logger.log("session_end")

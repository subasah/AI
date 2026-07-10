"""Assemble a Pipecat-style voice pipeline from a VoiceAgentDeployment.

Two pipeline modes:
  - gemini_live (default): speech → Gemini Live Flash → speech (no STT/TTS vendors)
  - classic: Deepgram STT → OpenAI LLM → Cartesia TTS

API tokens are read from environment via secret refs. Until you buy/add keys,
the bot can still boot in mock mode for config validation.
"""

from __future__ import annotations

import os
from typing import Any

from loguru import logger

from library.agents.factory import build_agents
from library.config.models import PipelineMode, VoiceAgentDeployment
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
        voice = self.deployment.voice
        self.logger.log(
            "session_start",
            deployment_id=self.deployment.id,
            entry_agent=self.swarm.active_agent_id,
            pipeline_mode=voice.pipeline_mode.value,
        )
        return {
            "call_id": self.logger.call_id,
            "system_prompt": self.swarm.system_prompt(),
            "tools": self.swarm.tools(),
            "entry_message": self.swarm.entry_message(),
            "voice": voice.model_dump(),
            "pipeline_mode": voice.pipeline_mode.value,
            "missing_secrets": self.missing_secrets(),
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
        return [r for r in self.deployment.voice.required_secret_refs() if not resolve_secret(r)]

    async def build_pipecat_pipeline(self) -> Any:
        """Assemble the live pipeline for the configured mode."""
        mode = self.deployment.voice.pipeline_mode
        missing = self.missing_secrets()
        if missing:
            logger.warning(
                "Pipecat pipeline deferred (mode={}) — missing secrets: {}. "
                "Session still usable for config/tool dry-runs.",
                mode.value,
                missing,
            )
            return None

        if mode == PipelineMode.GEMINI_LIVE:
            return await self._build_gemini_live_pipeline()
        return await self._build_classic_pipeline()

    async def _build_gemini_live_pipeline(self) -> Any:
        """Speech-to-speech: transport audio ↔ Gemini Live Flash (no Deepgram/Cartesia)."""
        try:
            from pipecat.pipeline.pipeline import Pipeline
            from pipecat.processors.aggregators.llm_context import LLMContext
            from pipecat.processors.aggregators.llm_response_universal import (
                LLMContextAggregatorPair,
            )
            from pipecat.services.google.gemini_live import GeminiLiveLLMService
        except ImportError:
            logger.warning(
                "pipecat[google] not installed — skipping Gemini Live pipeline. "
                'Install with: pip install "pipecat-ai[google]"'
            )
            return None

        voice = self.deployment.voice
        settings_kwargs: dict[str, Any] = {
            "model": voice.gemini_model,
            "voice": voice.gemini_voice,
            "system_instruction": self.swarm.system_prompt(),
            "language": voice.gemini_language,
        }

        # Optional local VAD instead of Gemini server VAD
        vad_analyzer = None
        try:
            from pipecat.services.google.gemini_live import GeminiVADParams

            if voice.gemini_use_local_vad:
                from pipecat.audio.vad.silero import SileroVADAnalyzer

                settings_kwargs["vad"] = GeminiVADParams(disabled=True)
                vad_analyzer = SileroVADAnalyzer()
        except ImportError:
            pass

        llm = GeminiLiveLLMService(
            api_key=resolve_secret(voice.gemini_api_key_ref),
            settings=GeminiLiveLLMService.Settings(**settings_kwargs),
            tools=self.swarm.tools(),
        )

        # Wire tool calls from Gemini Live into our dispatcher (MCP / HTTP / mock)
        async def _on_function_call(params: Any) -> None:
            name = getattr(params, "function_name", None) or getattr(params, "name", None)
            arguments = getattr(params, "arguments", None) or {}
            if not name:
                return
            result = await self.handle_tool_call(name, arguments if isinstance(arguments, dict) else {})
            result_callback = getattr(params, "result_callback", None)
            if callable(result_callback):
                await result_callback(result)

        if hasattr(llm, "register_function"):
            # Catch-all registration when supported by the installed pipecat version
            try:
                llm.register_function(None, _on_function_call)
            except TypeError:
                for tool in self.swarm.tools():
                    fn = tool.get("function") or {}
                    tname = fn.get("name") or tool.get("name")
                    if tname:
                        llm.register_function(tname, _on_function_call)

        messages = [{"role": "system", "content": self.swarm.system_prompt()}]
        context = LLMContext(messages)

        aggregator_kwargs: dict[str, Any] = {"realtime_service_mode": True}
        try:
            from pipecat.processors.aggregators.llm_response_universal import (
                LLMUserAggregatorParams,
            )

            if vad_analyzer is not None:
                aggregator_kwargs["user_params"] = LLMUserAggregatorParams(vad_analyzer=vad_analyzer)
        except ImportError:
            pass

        try:
            context_aggregator = LLMContextAggregatorPair(context, **aggregator_kwargs)
        except TypeError:
            # Older pipecat without realtime_service_mode
            context_aggregator = LLMContextAggregatorPair(context)

        # Multimodal path: no separate STT/TTS processors — Gemini handles both.
        # Transport input/output are attached by incoming/outgoing handlers.
        pipeline = Pipeline(
            [
                context_aggregator.user(),
                llm,
                context_aggregator.assistant(),
            ]
        )

        self.logger.log("pipeline_built", mode="gemini_live", model=voice.gemini_model)
        return {
            "pipeline": pipeline,
            "mode": PipelineMode.GEMINI_LIVE.value,
            "llm": llm,
            "context": context,
            "vad": vad_analyzer,
            "session": self,
            "notes": (
                "Gemini Live Flash: caller audio goes to Gemini; Gemini returns audio. "
                "No Deepgram/Cartesia required."
            ),
        }

    async def _build_classic_pipeline(self) -> Any:
        """Classic cascade: STT → LLM → TTS."""
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
            logger.warning("pipecat classic extras not installed — skipping classic pipeline")
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

        pipeline = Pipeline(
            [
                stt,
                context_aggregator.user(),
                llm,
                tts,
                context_aggregator.assistant(),
            ]
        )
        self.logger.log("pipeline_built", mode="classic")
        return {
            "pipeline": pipeline,
            "mode": PipelineMode.CLASSIC.value,
            "vad": SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            "context": context,
            "session": self,
        }

    async def close(self) -> None:
        await self.mcp.close()
        self.logger.log("session_end")

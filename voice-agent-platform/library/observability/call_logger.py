from __future__ import annotations

import uuid
from typing import Any, Callable

from loguru import logger


class CallLogger:
    """Structured logging with call_id correlation + optional MySQL persistence.

    Process logs always fire. When a CallRepository is attached, every turn,
    tool I/O payload, and event is also written to MySQL for debugging.
    """

    def __init__(
        self,
        call_id: str | None = None,
        company_id: str | None = None,
        deployment_id: str | None = None,
        repository: Any | None = None,
        agent_id_provider: Callable[[], str | None] | None = None,
    ) -> None:
        self.call_id = call_id or str(uuid.uuid4())
        self.company_id = company_id
        self.deployment_id = deployment_id
        self.repository = repository
        self._agent_id_provider = agent_id_provider
        self._bound = logger.bind(call_id=self.call_id, company_id=company_id)
        self._pending_tool_args: dict[str, dict[str, Any]] = {}

    def _agent_id(self) -> str | None:
        if self._agent_id_provider:
            try:
                return self._agent_id_provider()
            except Exception:  # noqa: BLE001
                return None
        return None

    def log(self, event: str, **kwargs: Any) -> None:
        self._bound.info(event, event=event, **kwargs)
        if self.repository is not None and event not in {
            "tool_called",
            "tool_succeeded",
            "tool_failed",
            "turn",
        }:
            try:
                self.repository.add_event(
                    call_id=self.call_id,
                    event_type=event,
                    payload=kwargs or None,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to persist call event {}: {}", event, exc)

    def tool_called(self, name: str, **kwargs: Any) -> None:
        args = kwargs.get("arguments") if isinstance(kwargs.get("arguments"), dict) else kwargs
        self._pending_tool_args[name] = args if isinstance(args, dict) else {"raw": args}
        self.log("tool_called", tool=name, **kwargs)

    def tool_succeeded(self, name: str, latency_ms: float, **kwargs: Any) -> None:
        self._bound.info("tool_succeeded", event="tool_succeeded", tool=name, latency_ms=latency_ms, **kwargs)
        result = kwargs.get("result")
        args = self._pending_tool_args.pop(name, kwargs.get("arguments"))
        if self.repository is not None:
            try:
                self.repository.add_tool_io(
                    call_id=self.call_id,
                    tool_name=name,
                    arguments=args if isinstance(args, dict) else {"raw": args},
                    result=result if isinstance(result, dict) else {"result": result},
                    ok=True,
                    latency_ms=latency_ms,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to persist tool success {}: {}", name, exc)

    def tool_failed(self, name: str, code: str, message: str, **kwargs: Any) -> None:
        self._bound.info(
            "tool_failed",
            event="tool_failed",
            tool=name,
            error_code=code,
            error_message=message,
            **kwargs,
        )
        args = self._pending_tool_args.pop(name, kwargs.get("arguments"))
        if self.repository is not None:
            try:
                self.repository.add_tool_io(
                    call_id=self.call_id,
                    tool_name=name,
                    arguments=args if isinstance(args, dict) else {"raw": args},
                    result={"error": {"code": code, "message": message}},
                    ok=False,
                    error_code=code,
                    latency_ms=kwargs.get("latency_ms"),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to persist tool failure {}: {}", name, exc)

    def turn(self, role: str, text: str, **kwargs: Any) -> None:
        self._bound.info("turn", event="turn", role=role, text=text[:500], **kwargs)
        if self.repository is not None:
            try:
                self.repository.add_turn(
                    call_id=self.call_id,
                    role=role,
                    content=text,
                    agent_id=kwargs.get("agent_id") or self._agent_id(),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to persist turn: {}", exc)

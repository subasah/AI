from __future__ import annotations

import uuid
from typing import Any

from loguru import logger


class CallLogger:
    """Structured logging with call_id correlation for every event."""

    def __init__(self, call_id: str | None = None, company_id: str | None = None) -> None:
        self.call_id = call_id or str(uuid.uuid4())
        self.company_id = company_id
        self._bound = logger.bind(call_id=self.call_id, company_id=company_id)

    def log(self, event: str, **kwargs: Any) -> None:
        self._bound.info(event, event=event, **kwargs)

    def tool_called(self, name: str, **kwargs: Any) -> None:
        self.log("tool_called", tool=name, **kwargs)

    def tool_succeeded(self, name: str, latency_ms: float, **kwargs: Any) -> None:
        self.log("tool_succeeded", tool=name, latency_ms=latency_ms, **kwargs)

    def tool_failed(self, name: str, code: str, message: str, **kwargs: Any) -> None:
        self.log("tool_failed", tool=name, error_code=code, error_message=message, **kwargs)

    def turn(self, role: str, text: str, **kwargs: Any) -> None:
        self.log("turn", role=role, text=text[:500], **kwargs)

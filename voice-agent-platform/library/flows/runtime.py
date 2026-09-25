from __future__ import annotations

from typing import Any

from library.config.models import FlowConfig, FlowState


class FlowRuntime:
    """Enforces a finite state machine so the LLM cannot skip steps."""

    def __init__(self, config: FlowConfig) -> None:
        self.config = config
        self.state = config.initial_state
        self.context: dict[str, Any] = {}
        self._states: dict[str, FlowState] = {s.id: s for s in config.states}

    @property
    def current(self) -> FlowState:
        return self._states[self.state]

    def instruction(self) -> str:
        return self.current.instruction

    def allowed_tools(self) -> list[str]:
        return list(self.current.allowed_tools)

    def transition(self, event: str, **data: Any) -> str:
        self.context.update(data)
        nxt = self.current.transitions.get(event)
        if not nxt:
            return (
                f"Invalid event '{event}' in state '{self.state}'. "
                f"Stay on: {self.current.instruction}"
            )
        self.state = nxt
        if self.current.is_terminal:
            return f"Flow complete ({self.state}). {self.current.instruction}"
        return self.current.instruction

    def snapshot(self) -> dict[str, Any]:
        return {"flow_id": self.config.id, "state": self.state, "context": self.context}

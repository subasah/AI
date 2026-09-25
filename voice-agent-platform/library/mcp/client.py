"""MCP client wrapper for attaching customer internal services.

Uses the Model Context Protocol so tomorrow you can plug another service
without rewriting tool handlers — just register a new MCP server on the
deployment and optionally bind tools via `mcp_binding`.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from library.config.models import MCPServerConfig


class MCPClientManager:
    """Lazy MCP connections keyed by server id.

    Real SDK wiring (mcp / anthropic mcp client) is optional — when the
    package or credentials are missing, call_tool returns a clear error so
    the voice loop stays up.
    """

    def __init__(self, servers: list[MCPServerConfig]) -> None:
        self._servers = {s.id: s for s in servers if s.enabled}
        self._sessions: dict[str, Any] = {}

    @property
    def server_ids(self) -> list[str]:
        return list(self._servers.keys())

    async def connect_all(self) -> None:
        for server_id, cfg in self._servers.items():
            try:
                await self._connect(cfg)
            except Exception as exc:  # noqa: BLE001
                logger.warning("MCP server {} unavailable: {}", server_id, exc)

    async def _connect(self, cfg: MCPServerConfig) -> None:
        # Placeholder for official MCP client session.
        # Install `mcp` and wire stdio/sse transports when tokens are ready.
        self._sessions[cfg.id] = {
            "config": cfg,
            "connected": False,
            "note": "MCP SDK not initialized — set MCP_* env and install mcp package",
        }
        logger.info("Registered MCP server '{}' ({})", cfg.id, cfg.transport)

    async def list_tools(self, server_id: str) -> list[dict[str, Any]]:
        cfg = self._servers.get(server_id)
        if not cfg:
            return []
        # When live, query the session. Until then, advertise configured includes.
        return [{"name": name, "server_id": server_id} for name in cfg.include_tools]

    async def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        if server_id not in self._servers:
            raise ValueError(f"Unknown MCP server '{server_id}'")
        session = self._sessions.get(server_id)
        if not session or not session.get("connected"):
            return {
                "ok": False,
                "error": {
                    "code": "mcp_not_connected",
                    "message": (
                        f"MCP server '{server_id}' is configured but not connected. "
                        "Install the mcp package and provide credentials to enable live calls."
                    ),
                },
                "tool": tool_name,
                "arguments": arguments,
            }
        # Live path: session.call_tool(tool_name, arguments)
        raise NotImplementedError("Wire MCP session.call_tool when SDK is available")

    async def close(self) -> None:
        self._sessions.clear()

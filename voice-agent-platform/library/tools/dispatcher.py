from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

import httpx
from loguru import logger

from library.config.models import ToolAuthType, ToolConfig
from library.observability.call_logger import CallLogger

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class ToolDispatcher:
    """Registry + 4-level error handling for tool calls.

    Execution order:
      1. Local registered handler
      2. MCP binding (server_id/tool_name)
      3. HTTP endpoint on customer service
      4. mock_response (dev / no credentials yet)
    """

    def __init__(
        self,
        tools: list[ToolConfig],
        call_logger: CallLogger | None = None,
        secret_resolver: Callable[[str], str | None] | None = None,
        mcp_client: Any | None = None,
    ) -> None:
        self._tools = {t.name: t for t in tools}
        self._handlers: dict[str, ToolHandler] = {}
        self._logger = call_logger or CallLogger(call_id="unknown")
        self._secret_resolver = secret_resolver or (lambda _ref: None)
        self._mcp_client = mcp_client

    def register(self, name: str, handler: ToolHandler) -> None:
        self._handlers[name] = handler

    def declarations(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    async def handle(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        self._logger.tool_called(name, arguments=arguments)

        try:
            if name not in self._tools and name not in self._handlers:
                return self._error(name, "unknown_tool", f"Tool '{name}' is not registered.")

            # Level 1 — local handler
            if name in self._handlers:
                result = await self._handlers[name](arguments)
                self._logger.tool_succeeded(
                    name, latency_ms=self._ms(started), result=result, arguments=arguments
                )
                return {"ok": True, "tool": name, "result": result}

            tool = self._tools[name]

            # Level 2 — MCP
            if tool.mcp_binding and self._mcp_client is not None:
                result = await self._call_mcp(tool, arguments)
                self._logger.tool_succeeded(
                    name, latency_ms=self._ms(started), result=result, arguments=arguments
                )
                return {"ok": True, "tool": name, "result": result}

            # Level 3 — HTTP customer service
            if tool.endpoint_url:
                result = await self._call_http(tool, arguments)
                self._logger.tool_succeeded(
                    name, latency_ms=self._ms(started), result=result, arguments=arguments
                )
                return {"ok": True, "tool": name, "result": result}

            # Level 4 — mock (safe default while API tokens are pending)
            if tool.mock_response is not None:
                self._logger.tool_succeeded(
                    name,
                    latency_ms=self._ms(started),
                    result={**tool.mock_response, "mocked": True},
                    arguments=arguments,
                )
                return {"ok": True, "tool": name, "result": tool.mock_response, "mocked": True}

            return self._error(
                name,
                "not_configured",
                f"Tool '{name}' has no handler, MCP binding, endpoint, or mock.",
            )

        except httpx.TimeoutException:
            return self._error(name, "timeout", f"Tool '{name}' timed out.")
        except httpx.HTTPStatusError as exc:
            return self._error(name, "http_error", f"HTTP {exc.response.status_code}: {exc}")
        except Exception as exc:  # noqa: BLE001 — surface to LLM safely
            logger.exception("Tool {} failed", name)
            return self._error(name, "exception", str(exc))

    async def _call_http(self, tool: ToolConfig, arguments: dict[str, Any]) -> Any:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if tool.auth_type != ToolAuthType.NONE and tool.auth_secret_ref:
            secret = self._secret_resolver(tool.auth_secret_ref)
            if secret:
                if tool.auth_type == ToolAuthType.BEARER:
                    headers[tool.auth_header] = f"Bearer {secret}"
                elif tool.auth_type == ToolAuthType.API_KEY:
                    headers[tool.auth_header] = secret
                else:
                    headers[tool.auth_header] = secret

        async with httpx.AsyncClient(timeout=tool.timeout_seconds) as client:
            method = tool.http_method.upper()
            if method == "GET":
                resp = await client.get(tool.endpoint_url, params=arguments, headers=headers)
            else:
                resp = await client.request(method, tool.endpoint_url, json=arguments, headers=headers)
            resp.raise_for_status()
            if resp.headers.get("content-type", "").startswith("application/json"):
                return resp.json()
            return {"raw": resp.text}

    async def _call_mcp(self, tool: ToolConfig, arguments: dict[str, Any]) -> Any:
        server_id, mcp_tool = tool.mcp_binding.split("/", 1)
        return await self._mcp_client.call_tool(server_id, mcp_tool, arguments)

    @staticmethod
    def _ms(started: float) -> float:
        return round((time.perf_counter() - started) * 1000, 2)

    def _error(self, name: str, code: str, message: str) -> dict[str, Any]:
        self._logger.tool_failed(name, code=code, message=message)
        return {"ok": False, "tool": name, "error": {"code": code, "message": message}}

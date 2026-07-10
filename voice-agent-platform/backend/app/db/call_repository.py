"""MySQL persistence for call I/O — required for production debugging.

Stores call sessions, conversational turns (input/output), tool request/response
payloads, and structured events (handoffs, errors). Config (companies/deployments)
may still use JSON locally; call observability always prefers MySQL.
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

import pymysql
from loguru import logger
from pymysql.cursors import DictCursor


class CallRepository:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
    ) -> None:
        self._cfg = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "charset": "utf8mb4",
            "cursorclass": DictCursor,
            "autocommit": True,
        }
        self._seq_lock = threading.Lock()
        self._seqs: dict[str, int] = {}
        self._wait_ready()
        self._ensure_schema()

    @classmethod
    def from_env(cls) -> CallRepository:
        return cls(
            host=os.getenv("MYSQL_HOST", "mysql"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "aethervoice"),
            password=os.getenv("MYSQL_PASSWORD", "aethervoice_pass_change_me"),
            database=os.getenv("MYSQL_DATABASE", "aethervoice"),
        )

    def _connect(self):
        return pymysql.connect(**self._cfg)

    def _wait_ready(self, attempts: int = 40, delay: float = 1.5) -> None:
        last: Exception | None = None
        for i in range(attempts):
            try:
                with self._connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                return
            except Exception as exc:  # noqa: BLE001
                last = exc
                logger.warning("CallRepository waiting for MySQL ({}/{}): {}", i + 1, attempts, exc)
                time.sleep(delay)
        raise RuntimeError(f"MySQL not reachable for call logging: {last}")

    def _ensure_schema(self) -> None:
        stmts = [
            """
            CREATE TABLE IF NOT EXISTS calls (
              id VARCHAR(64) PRIMARY KEY,
              company_id VARCHAR(64) NULL,
              deployment_id VARCHAR(64) NULL,
              direction VARCHAR(16) NOT NULL DEFAULT 'inbound',
              status VARCHAR(32) NOT NULL DEFAULT 'active',
              pipeline_mode VARCHAR(32) NULL,
              entry_agent_id VARCHAR(64) NULL,
              from_number VARCHAR(64) NULL,
              to_number VARCHAR(64) NULL,
              metadata JSON NULL,
              started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              ended_at TIMESTAMP NULL,
              INDEX idx_calls_company (company_id),
              INDEX idx_calls_deployment (deployment_id),
              INDEX idx_calls_started (started_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS call_turns (
              id BIGINT AUTO_INCREMENT PRIMARY KEY,
              call_id VARCHAR(64) NOT NULL,
              seq INT NOT NULL,
              role VARCHAR(32) NOT NULL,
              content MEDIUMTEXT NOT NULL,
              agent_id VARCHAR(64) NULL,
              created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_turns_call (call_id, seq)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS call_tool_io (
              id BIGINT AUTO_INCREMENT PRIMARY KEY,
              call_id VARCHAR(64) NOT NULL,
              seq INT NOT NULL,
              tool_name VARCHAR(128) NOT NULL,
              arguments JSON NULL,
              result JSON NULL,
              ok TINYINT(1) NOT NULL DEFAULT 0,
              error_code VARCHAR(64) NULL,
              latency_ms DOUBLE NULL,
              created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_tools_call (call_id, seq),
              INDEX idx_tools_name (tool_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS call_events (
              id BIGINT AUTO_INCREMENT PRIMARY KEY,
              call_id VARCHAR(64) NOT NULL,
              seq INT NOT NULL,
              event_type VARCHAR(64) NOT NULL,
              payload JSON NULL,
              created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_events_call (call_id, seq),
              INDEX idx_events_type (event_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
        ]
        with self._connect() as conn:
            with conn.cursor() as cur:
                for stmt in stmts:
                    cur.execute(stmt)

    def _next_seq(self, call_id: str) -> int:
        with self._seq_lock:
            n = self._seqs.get(call_id, 0) + 1
            self._seqs[call_id] = n
            return n

    @staticmethod
    def _json(value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value, default=str)

    def start_call(
        self,
        *,
        call_id: str,
        company_id: str | None,
        deployment_id: str | None,
        direction: str = "inbound",
        pipeline_mode: str | None = None,
        entry_agent_id: str | None = None,
        from_number: str | None = None,
        to_number: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO calls (
                      id, company_id, deployment_id, direction, status,
                      pipeline_mode, entry_agent_id, from_number, to_number, metadata
                    ) VALUES (%s,%s,%s,%s,'active',%s,%s,%s,%s,CAST(%s AS JSON))
                    ON DUPLICATE KEY UPDATE
                      status='active',
                      metadata=COALESCE(CAST(%s AS JSON), metadata)
                    """,
                    (
                        call_id,
                        company_id,
                        deployment_id,
                        direction,
                        pipeline_mode,
                        entry_agent_id,
                        from_number,
                        to_number,
                        self._json(metadata),
                        self._json(metadata),
                    ),
                )
        with self._seq_lock:
            self._seqs.setdefault(call_id, 0)

    def end_call(self, call_id: str, status: str = "ended") -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE calls SET status=%s, ended_at=CURRENT_TIMESTAMP WHERE id=%s",
                    (status, call_id),
                )

    def add_turn(
        self,
        *,
        call_id: str,
        role: str,
        content: str,
        agent_id: str | None = None,
    ) -> int:
        seq = self._next_seq(call_id)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO call_turns (call_id, seq, role, content, agent_id)
                    VALUES (%s,%s,%s,%s,%s)
                    """,
                    (call_id, seq, role, content, agent_id),
                )
        return seq

    def add_tool_io(
        self,
        *,
        call_id: str,
        tool_name: str,
        arguments: dict[str, Any] | None,
        result: dict[str, Any] | None,
        ok: bool,
        error_code: str | None = None,
        latency_ms: float | None = None,
    ) -> int:
        seq = self._next_seq(call_id)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO call_tool_io
                      (call_id, seq, tool_name, arguments, result, ok, error_code, latency_ms)
                    VALUES (%s,%s,%s,CAST(%s AS JSON),CAST(%s AS JSON),%s,%s,%s)
                    """,
                    (
                        call_id,
                        seq,
                        tool_name,
                        self._json(arguments),
                        self._json(result),
                        1 if ok else 0,
                        error_code,
                        latency_ms,
                    ),
                )
        return seq

    def add_event(self, *, call_id: str, event_type: str, payload: dict[str, Any] | None = None) -> int:
        seq = self._next_seq(call_id)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO call_events (call_id, seq, event_type, payload)
                    VALUES (%s,%s,%s,CAST(%s AS JSON))
                    """,
                    (call_id, seq, event_type, self._json(payload)),
                )
        return seq

    def list_calls(
        self,
        *,
        company_id: str | None = None,
        deployment_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if company_id:
            clauses.append("company_id=%s")
            params.append(company_id)
        if deployment_id:
            clauses.append("deployment_id=%s")
            params.append(deployment_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(min(max(limit, 1), 200))
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT id, company_id, deployment_id, direction, status, pipeline_mode,
                           entry_agent_id, from_number, to_number, metadata,
                           started_at, ended_at
                    FROM calls
                    {where}
                    ORDER BY started_at DESC
                    LIMIT %s
                    """,
                    params,
                )
                rows = cur.fetchall()
        return [self._normalize_row(r) for r in rows]

    def get_call_detail(self, call_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, company_id, deployment_id, direction, status, pipeline_mode,
                           entry_agent_id, from_number, to_number, metadata,
                           started_at, ended_at
                    FROM calls WHERE id=%s
                    """,
                    (call_id,),
                )
                call = cur.fetchone()
                if not call:
                    return None
                cur.execute(
                    "SELECT seq, role, content, agent_id, created_at FROM call_turns WHERE call_id=%s ORDER BY seq",
                    (call_id,),
                )
                turns = cur.fetchall()
                cur.execute(
                    """
                    SELECT seq, tool_name, arguments, result, ok, error_code, latency_ms, created_at
                    FROM call_tool_io WHERE call_id=%s ORDER BY seq
                    """,
                    (call_id,),
                )
                tools = cur.fetchall()
                cur.execute(
                    "SELECT seq, event_type, payload, created_at FROM call_events WHERE call_id=%s ORDER BY seq",
                    (call_id,),
                )
                events = cur.fetchall()
        return {
            "call": self._normalize_row(call),
            "turns": [self._normalize_row(t) for t in turns],
            "tool_io": [self._normalize_row(t) for t in tools],
            "events": [self._normalize_row(e) for e in events],
        }

    @staticmethod
    def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in row.items():
            if hasattr(v, "isoformat"):
                out[k] = v.isoformat()
            elif isinstance(v, (bytes, bytearray)):
                try:
                    out[k] = json.loads(v.decode("utf-8"))
                except Exception:  # noqa: BLE001
                    out[k] = v.decode("utf-8", errors="replace")
            elif isinstance(v, str) and k in {"metadata", "arguments", "result", "payload"}:
                try:
                    out[k] = json.loads(v)
                except Exception:  # noqa: BLE001
                    out[k] = v
            else:
                out[k] = v
        return out


_repo: CallRepository | None = None
_repo_failed = False


def get_call_repository() -> CallRepository | None:
    """Return MySQL call repo when configured; None only if MySQL is unavailable."""
    global _repo, _repo_failed
    if _repo is not None:
        return _repo
    if _repo_failed:
        return None

    # Prefer MySQL whenever host/credentials look like a real DB setup
    backend = os.getenv("STORE_BACKEND", "json").lower()
    force = os.getenv("CALL_LOG_MYSQL", "").lower() in {"1", "true", "yes"}
    if backend != "mysql" and not force and not os.getenv("MYSQL_HOST"):
        return None

    try:
        _repo = CallRepository.from_env()
        logger.info("Call I/O persistence enabled (MySQL)")
        return _repo
    except Exception as exc:  # noqa: BLE001
        _repo_failed = True
        logger.error(
            "CRITICAL: Call I/O cannot persist to MySQL ({}). "
            "Transcripts/tool payloads will only hit process logs until MySQL is up.",
            exc,
        )
        return None

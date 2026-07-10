from __future__ import annotations

import json
import os
import time
from typing import Any

import pymysql
from loguru import logger
from pymysql.cursors import DictCursor

from library.config.models import CompanyConfig, VoiceAgentDeployment


class MySQLStore:
    """Persistent control-plane store backed by MySQL."""

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
        self._wait_ready()
        self._ensure_schema()

    @classmethod
    def from_env(cls) -> MySQLStore:
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
                logger.info("MySQL ready at {}:{}", self._cfg["host"], self._cfg["port"])
                return
            except Exception as exc:  # noqa: BLE001
                last = exc
                logger.warning("Waiting for MySQL ({}/{}): {}", i + 1, attempts, exc)
                time.sleep(delay)
        raise RuntimeError(f"MySQL not reachable: {last}")

    def _ensure_schema(self) -> None:
        ddl = [
            """
            CREATE TABLE IF NOT EXISTS companies (
              id VARCHAR(64) PRIMARY KEY,
              payload JSON NOT NULL,
              updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS deployments (
              id VARCHAR(64) PRIMARY KEY,
              company_id VARCHAR(64) NOT NULL,
              payload JSON NOT NULL,
              updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
              INDEX idx_deployments_company (company_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
        ]
        with self._connect() as conn:
            with conn.cursor() as cur:
                for stmt in ddl:
                    cur.execute(stmt)

    @staticmethod
    def _loads(payload: Any) -> dict[str, Any]:
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8")
        if isinstance(payload, str):
            return json.loads(payload)
        return dict(payload)

    def list_companies(self) -> list[CompanyConfig]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT payload FROM companies ORDER BY updated_at DESC")
                rows = cur.fetchall()
        return [CompanyConfig.model_validate(self._loads(r["payload"])) for r in rows]

    def get_company(self, company_id: str) -> CompanyConfig | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT payload FROM companies WHERE id=%s", (company_id,))
                row = cur.fetchone()
        if not row:
            return None
        return CompanyConfig.model_validate(self._loads(row["payload"]))

    def upsert_company(self, company: CompanyConfig) -> CompanyConfig:
        payload = json.dumps(company.model_dump(mode="json"))
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO companies (id, payload) VALUES (%s, CAST(%s AS JSON))
                    ON DUPLICATE KEY UPDATE payload = CAST(%s AS JSON)
                    """,
                    (company.id, payload, payload),
                )
        return company

    def delete_company(self, company_id: str) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                n = cur.execute("DELETE FROM companies WHERE id=%s", (company_id,))
        return n > 0

    def list_deployments(self, company_id: str | None = None) -> list[VoiceAgentDeployment]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                if company_id:
                    cur.execute(
                        "SELECT payload FROM deployments WHERE company_id=%s ORDER BY updated_at DESC",
                        (company_id,),
                    )
                else:
                    cur.execute("SELECT payload FROM deployments ORDER BY updated_at DESC")
                rows = cur.fetchall()
        return [VoiceAgentDeployment.model_validate(self._loads(r["payload"])) for r in rows]

    def get_deployment(self, deployment_id: str) -> VoiceAgentDeployment | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT payload FROM deployments WHERE id=%s", (deployment_id,))
                row = cur.fetchone()
        if not row:
            return None
        return VoiceAgentDeployment.model_validate(self._loads(row["payload"]))

    def upsert_deployment(self, deployment: VoiceAgentDeployment) -> VoiceAgentDeployment:
        payload = json.dumps(deployment.model_dump(mode="json"))
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO deployments (id, company_id, payload)
                    VALUES (%s, %s, CAST(%s AS JSON))
                    ON DUPLICATE KEY UPDATE
                      company_id = VALUES(company_id),
                      payload = CAST(%s AS JSON)
                    """,
                    (deployment.id, deployment.company_id, payload, payload),
                )
        return deployment

    def delete_deployment(self, deployment_id: str) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                n = cur.execute("DELETE FROM deployments WHERE id=%s", (deployment_id,))
        return n > 0

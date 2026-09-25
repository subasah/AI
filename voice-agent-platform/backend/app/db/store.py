from __future__ import annotations

import os
from typing import Any, Protocol

from library.config.models import CompanyConfig, VoiceAgentDeployment


class Store(Protocol):
    def list_companies(self) -> list[CompanyConfig]: ...
    def get_company(self, company_id: str) -> CompanyConfig | None: ...
    def upsert_company(self, company: CompanyConfig) -> CompanyConfig: ...
    def delete_company(self, company_id: str) -> bool: ...
    def list_deployments(self, company_id: str | None = None) -> list[VoiceAgentDeployment]: ...
    def get_deployment(self, deployment_id: str) -> VoiceAgentDeployment | None: ...
    def upsert_deployment(self, deployment: VoiceAgentDeployment) -> VoiceAgentDeployment: ...
    def delete_deployment(self, deployment_id: str) -> bool: ...


def new_id(prefix: str) -> str:
    import uuid

    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def create_store() -> Store:
    backend = os.getenv("STORE_BACKEND", "json").lower()
    if backend == "mysql":
        from backend.app.db.mysql_store import MySQLStore

        return MySQLStore.from_env()
    from backend.app.db.json_store import JsonStore

    return JsonStore()


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = create_store()
    return _store


class _StoreProxy:
    """Module-level `store` that resolves on first attribute access."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_store(), name)


store = _StoreProxy()

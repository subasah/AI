from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from library.config.models import CompanyConfig, VoiceAgentDeployment

DATA_DIR = Path(__file__).resolve().parents[3] / "configs" / "runtime"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class JsonStore:
    """Simple file-backed store so the platform runs without a DB at first.

    Swap for Postgres later — same service interface.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or DATA_DIR
        self.companies_path = self.root / "companies.json"
        self.deployments_path = self.root / "deployments.json"
        self._ensure()

    def _ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        if not self.companies_path.exists():
            self.companies_path.write_text("[]", encoding="utf-8")
        if not self.deployments_path.exists():
            self.deployments_path.write_text("[]", encoding="utf-8")

    def _read(self, path: Path) -> list[dict[str, Any]]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, path: Path, rows: list[dict[str, Any]]) -> None:
        path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    # Companies
    def list_companies(self) -> list[CompanyConfig]:
        return [CompanyConfig.model_validate(r) for r in self._read(self.companies_path)]

    def get_company(self, company_id: str) -> CompanyConfig | None:
        for c in self.list_companies():
            if c.id == company_id:
                return c
        return None

    def upsert_company(self, company: CompanyConfig) -> CompanyConfig:
        rows = self._read(self.companies_path)
        for i, row in enumerate(rows):
            if row.get("id") == company.id:
                rows[i] = company.model_dump(mode="json")
                self._write(self.companies_path, rows)
                return company
        rows.append(company.model_dump(mode="json"))
        self._write(self.companies_path, rows)
        return company

    def delete_company(self, company_id: str) -> bool:
        rows = self._read(self.companies_path)
        new_rows = [r for r in rows if r.get("id") != company_id]
        if len(new_rows) == len(rows):
            return False
        self._write(self.companies_path, new_rows)
        return True

    # Deployments
    def list_deployments(self, company_id: str | None = None) -> list[VoiceAgentDeployment]:
        deps = [VoiceAgentDeployment.model_validate(r) for r in self._read(self.deployments_path)]
        if company_id:
            return [d for d in deps if d.company_id == company_id]
        return deps

    def get_deployment(self, deployment_id: str) -> VoiceAgentDeployment | None:
        for d in self.list_deployments():
            if d.id == deployment_id:
                return d
        return None

    def upsert_deployment(self, deployment: VoiceAgentDeployment) -> VoiceAgentDeployment:
        rows = self._read(self.deployments_path)
        for i, row in enumerate(rows):
            if row.get("id") == deployment.id:
                rows[i] = deployment.model_dump(mode="json")
                self._write(self.deployments_path, rows)
                return deployment
        rows.append(deployment.model_dump(mode="json"))
        self._write(self.deployments_path, rows)
        return deployment

    def delete_deployment(self, deployment_id: str) -> bool:
        rows = self._read(self.deployments_path)
        new_rows = [r for r in rows if r.get("id") != deployment_id]
        if len(new_rows) == len(rows):
            return False
        self._write(self.deployments_path, new_rows)
        return True


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


store = JsonStore()

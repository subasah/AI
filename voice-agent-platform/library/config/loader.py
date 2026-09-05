from __future__ import annotations

import json
from pathlib import Path

import yaml

from library.config.models import CompanyConfig, VoiceAgentDeployment


def load_deployment(path: str | Path) -> VoiceAgentDeployment:
    path = Path(path)
    data = _read(path)
    return VoiceAgentDeployment.model_validate(data)


def load_company(path: str | Path) -> CompanyConfig:
    path = Path(path)
    data = _read(path)
    return CompanyConfig.model_validate(data)


def save_deployment(deployment: VoiceAgentDeployment, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = deployment.model_dump(mode="json")
    if path.suffix in {".yaml", ".yml"}:
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text)

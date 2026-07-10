"""Incoming call handler.

Twilio (or similar) hits /voice/incoming → we look up the deployment by
called number → start a VoiceBotSession → return TwiML / WebRTC join info.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from library.bot_core import VoiceBotSession
from library.config.loader import load_deployment
from library.config.models import VoiceAgentDeployment

router = APIRouter(prefix="/voice", tags=["incoming"])

# In production, load from the control-plane API / DB.
_DEPLOYMENTS: dict[str, VoiceAgentDeployment] = {}
_SESSIONS: dict[str, VoiceBotSession] = {}


def register_deployment(deployment: VoiceAgentDeployment) -> None:
    _DEPLOYMENTS[deployment.id] = deployment
    for number in deployment.phone_numbers:
        _DEPLOYMENTS[f"phone:{number}"] = deployment


def load_deployments_from_dir(directory: str | Path) -> int:
    directory = Path(directory)
    count = 0
    if not directory.exists():
        return 0
    for path in list(directory.glob("*.json")) + list(directory.glob("*.yaml")) + list(directory.glob("*.yml")):
        dep = load_deployment(path)
        register_deployment(dep)
        count += 1
    return count


def resolve_deployment(called_number: str | None, deployment_id: str | None) -> VoiceAgentDeployment:
    if deployment_id and deployment_id in _DEPLOYMENTS:
        return _DEPLOYMENTS[deployment_id]
    if called_number and f"phone:{called_number}" in _DEPLOYMENTS:
        return _DEPLOYMENTS[f"phone:{called_number}"]
    # Fallback: first active deployment (dev)
    for dep in _DEPLOYMENTS.values():
        if not str(dep).startswith("phone:") and getattr(dep, "status", "draft") in {"active", "draft"}:
            return dep
    raise HTTPException(status_code=404, detail="No voice agent deployment found for this number")


@router.post("/incoming")
async def incoming_call(request: Request) -> Response:
    """Twilio voice webhook for inbound PSTN calls."""
    form = await request.form()
    called = form.get("To") or form.get("Called")
    caller = form.get("From")
    deployment_id = request.query_params.get("deployment_id")

    deployment = resolve_deployment(str(called) if called else None, deployment_id)
    session = VoiceBotSession(
        deployment,
        direction="inbound",
        from_number=str(caller) if caller else None,
        to_number=str(called) if called else None,
        metadata={"provider": "twilio"},
    )
    bootstrap = await session.start()
    _SESSIONS[session.logger.call_id] = session

    logger.info(
        "Inbound call caller={} called={} deployment={} call_id={}",
        caller,
        called,
        deployment.id,
        session.logger.call_id,
    )

    # If Daily/WebRTC room URL is configured, return TwiML that connects stream.
    # Until Twilio/Daily tokens exist, return a safe placeholder gather.
    public_base = os.getenv("PUBLIC_BASE_URL", "http://localhost:8080")
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>{bootstrap.get("entry_message") or "Please hold while we connect you."}</Say>
  <Connect>
    <Stream url="wss://{public_base.replace('https://', '').replace('http://', '')}/voice/stream/{session.logger.call_id}" />
  </Connect>
</Response>
"""
    return Response(content=twiml, media_type="application/xml")


@router.post("/incoming/web")
async def incoming_web(payload: dict[str, Any]) -> dict[str, Any]:
    """Browser / WebRTC inbound session bootstrap (no Twilio)."""
    deployment = resolve_deployment(payload.get("phone_number"), payload.get("deployment_id"))
    session = VoiceBotSession(
        deployment,
        call_id=payload.get("call_id"),
        direction="inbound",
        from_number=payload.get("from_number"),
        to_number=payload.get("phone_number"),
        metadata={"provider": "web", **(payload.get("metadata") or {})},
    )
    bootstrap = await session.start()
    _SESSIONS[session.logger.call_id] = session
    missing = session.missing_secrets()
    return {
        **bootstrap,
        "deployment_id": deployment.id,
        "company_id": deployment.company_id,
        "missing_secrets": missing,
        "mode": "mock" if missing else "live",
    }


@router.post("/session/{call_id}/turns")
async def record_turn(call_id: str, payload: dict[str, Any]) -> dict[str, str]:
    """Record a user or assistant utterance for MySQL debugging."""
    session = _SESSIONS.get(call_id)
    if not session:
        raise HTTPException(status_code=404, detail="Unknown call session")
    role = (payload.get("role") or "user").lower()
    text = payload.get("text") or payload.get("content") or ""
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    if role == "user":
        await session.record_user_input(text)
    else:
        await session.record_agent_output(text)
    return {"status": "recorded", "call_id": call_id, "role": role}


@router.post("/session/{call_id}/tools/{tool_name}")
async def run_tool(call_id: str, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    session = _SESSIONS.get(call_id)
    if not session:
        raise HTTPException(status_code=404, detail="Unknown call session")
    return await session.handle_tool_call(tool_name, payload.get("arguments") or {})


@router.delete("/session/{call_id}")
async def end_session(call_id: str) -> dict[str, str]:
    session = _SESSIONS.pop(call_id, None)
    if session:
        await session.close()
    return {"status": "ended", "call_id": call_id}

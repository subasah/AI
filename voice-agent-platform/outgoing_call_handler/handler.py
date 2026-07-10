"""Outgoing call handler.

Your platform (or a customer campaign) posts a dial request → we place the
call via Twilio → attach the same VoiceBotSession / swarm as inbound.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from library.bot_core import VoiceBotSession
from library.config.models import VoiceAgentDeployment

# Reuse inbound registry when running as a combined app
try:
    from incoming_call_handler.handler import (  # type: ignore
        _DEPLOYMENTS,
        _SESSIONS,
        register_deployment,
        resolve_deployment,
    )
except Exception:  # noqa: BLE001
    _DEPLOYMENTS: dict[str, VoiceAgentDeployment] = {}
    _SESSIONS: dict[str, VoiceBotSession] = {}

    def register_deployment(deployment: VoiceAgentDeployment) -> None:
        _DEPLOYMENTS[deployment.id] = deployment
        for number in deployment.phone_numbers:
            _DEPLOYMENTS[f"phone:{number}"] = deployment

    def resolve_deployment(called_number: str | None, deployment_id: str | None) -> VoiceAgentDeployment:
        if deployment_id and deployment_id in _DEPLOYMENTS:
            return _DEPLOYMENTS[deployment_id]
        for dep in list(_DEPLOYMENTS.values()):
            if isinstance(dep, VoiceAgentDeployment):
                return dep
        raise HTTPException(status_code=404, detail="No deployment found")


router = APIRouter(prefix="/voice", tags=["outgoing"])


class OutboundCallRequest(BaseModel):
    deployment_id: str
    to_number: str
    from_number: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    # Optional override of opening line
    opening_line: str | None = None


class OutboundCallResponse(BaseModel):
    call_id: str
    deployment_id: str
    status: str
    provider_call_sid: str | None = None
    entry_message: str | None = None
    missing_secrets: list[str] = Field(default_factory=list)
    mode: str = "mock"


def _twilio_client():
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        return None
    try:
        from twilio.rest import Client

        return Client(sid, token)
    except ImportError:
        logger.warning("twilio package not installed")
        return None


@router.post("/outgoing", response_model=OutboundCallResponse)
async def start_outbound(req: OutboundCallRequest) -> OutboundCallResponse:
    deployment = resolve_deployment(None, req.deployment_id)
    session = VoiceBotSession(deployment)
    bootstrap = await session.start()
    _SESSIONS[session.logger.call_id] = session

    opening = req.opening_line or deployment.outbound_script or bootstrap.get("entry_message")
    missing = session.missing_secrets()
    from_number = req.from_number or os.getenv("TWILIO_PHONE_NUMBER")
    public_base = os.getenv("PUBLIC_BASE_URL", "http://localhost:8080")

    provider_sid = None
    status = "mock_queued"
    client = _twilio_client()
    if client and from_number and not missing:
        call = client.calls.create(
            to=req.to_number,
            from_=from_number,
            url=f"{public_base}/voice/outgoing/twiml/{session.logger.call_id}",
            status_callback=f"{public_base}/voice/outgoing/status/{session.logger.call_id}",
        )
        provider_sid = call.sid
        status = "dialing"
    else:
        logger.info(
            "Outbound mock dial to={} deployment={} missing_secrets={}",
            req.to_number,
            deployment.id,
            missing,
        )

    session.logger.log(
        "outbound_started",
        to=req.to_number,
        from_number=from_number,
        context=req.context,
        opening=opening,
    )

    return OutboundCallResponse(
        call_id=session.logger.call_id,
        deployment_id=deployment.id,
        status=status,
        provider_call_sid=provider_sid,
        entry_message=opening,
        missing_secrets=missing,
        mode="live" if provider_sid else "mock",
    )


@router.post("/outgoing/twiml/{call_id}")
async def outbound_twiml(call_id: str) -> Any:
    from fastapi import Response

    session = _SESSIONS.get(call_id)
    if not session:
        raise HTTPException(status_code=404, detail="Unknown call")
    say = session.deployment.outbound_script or session.swarm.entry_message()
    public_base = os.getenv("PUBLIC_BASE_URL", "http://localhost:8080")
    host = public_base.replace("https://", "").replace("http://", "")
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>{say}</Say>
  <Connect>
    <Stream url="wss://{host}/voice/stream/{call_id}" />
  </Connect>
</Response>
"""
    return Response(content=twiml, media_type="application/xml")


@router.post("/outgoing/status/{call_id}")
async def outbound_status(call_id: str, payload: dict[str, Any] | None = None) -> dict[str, str]:
    session = _SESSIONS.get(call_id)
    if session:
        session.logger.log("outbound_status", **(payload or {}))
    return {"status": "ok"}

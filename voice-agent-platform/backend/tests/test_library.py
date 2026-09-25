from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from library.bot_core import VoiceBotSession
from library.flows.runtime import FlowRuntime
from library.industries.templates import (
    car_dealer_template,
    mortgage_servicing_template,
    restaurant_template,
)


def test_restaurant_template_has_entry_and_tools():
    dep = restaurant_template("co_x", "Test Bistro")
    assert dep.entry_agent_id == "greeter"
    assert any(t.name == "create_reservation" for t in dep.tools)
    assert len(dep.agents) >= 3


def test_default_pipeline_is_gemini_live():
    from library.config.models import PipelineMode, VoiceProviderConfig

    voice = VoiceProviderConfig()
    assert voice.pipeline_mode == PipelineMode.GEMINI_LIVE
    assert voice.required_secret_refs() == ["GOOGLE_API_KEY"]

    classic = VoiceProviderConfig(pipeline_mode=PipelineMode.CLASSIC)
    assert set(classic.required_secret_refs()) == {
        "DEEPGRAM_API_KEY",
        "CARTESIA_API_KEY",
        "OPENAI_API_KEY",
    }


def test_mortgage_payment_flow_transitions():
    dep = mortgage_servicing_template("co_m", "Servicer")
    flow = next(f for f in dep.flows if f.id == "payment_flow")
    rt = FlowRuntime(flow)
    assert "how much" in rt.transition("user_wants_payment").lower()
    assert rt.state == "collecting_amount"


@pytest.mark.asyncio
async def test_session_tool_mock_and_handoff():
    dep = car_dealer_template("co_d", "Dealer")
    session = VoiceBotSession(dep, call_id="test-call")
    boot = await session.start()
    assert boot["entry_message"]
    result = await session.handle_tool_call(
        "transfer_to_sales",
        {"reason": "wants inventory"},
    )
    assert result["ok"] is True
    assert session.swarm.active_agent_id == "sales"
    inv = await session.handle_tool_call("search_inventory", {"make": "Honda"})
    assert inv["ok"] is True
    assert inv.get("mocked") is True
    await session.close()


def test_call_logger_persists_to_repository():
    from library.observability.call_logger import CallLogger

    class FakeRepo:
        def __init__(self):
            self.turns = []
            self.tools = []
            self.events = []

        def add_turn(self, **kwargs):
            self.turns.append(kwargs)
            return len(self.turns)

        def add_tool_io(self, **kwargs):
            self.tools.append(kwargs)
            return len(self.tools)

        def add_event(self, **kwargs):
            self.events.append(kwargs)
            return len(self.events)

    repo = FakeRepo()
    log = CallLogger(call_id="c1", company_id="co", repository=repo)
    log.turn("user", "I want a table for two")
    log.tool_called("check_availability", arguments={"party_size": 2})
    log.tool_succeeded("check_availability", latency_ms=12.5, result={"available": True})
    log.log("handoff", from_agent="greeter", to="reservations")

    assert len(repo.turns) == 1
    assert repo.turns[0]["content"] == "I want a table for two"
    assert len(repo.tools) == 1
    assert repo.tools[0]["ok"] is True
    assert repo.tools[0]["arguments"]["party_size"] == 2
    assert any(e["event_type"] == "handoff" for e in repo.events)
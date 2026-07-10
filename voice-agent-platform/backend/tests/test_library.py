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

"""Industry starter templates.

Each template is a VoiceAgentDeployment skeleton your team customizes
per customer (endpoints, MCP, brand voice, phone numbers).
"""

from __future__ import annotations

from library.config.models import (
    AgentConfig,
    CallDirection,
    FlowConfig,
    FlowState,
    Industry,
    MCPServerConfig,
    SkillConfig,
    ToolAuthType,
    ToolConfig,
    VoiceAgentDeployment,
)
from library.prompts.templates import DEFAULT_GUARDRAILS, compose_system_prompt


def restaurant_template(company_id: str, company_name: str) -> VoiceAgentDeployment:
    tools = [
        ToolConfig(
            name="check_availability",
            description=(
                "Checks table availability for a date, time, and party size. "
                "Call when the caller wants to reserve or asks if a time is free."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time": {"type": "string", "description": "HH:MM local"},
                    "party_size": {"type": "integer"},
                },
                "required": ["date", "time", "party_size"],
            },
            endpoint_url=None,
            mock_response={"available": True, "table": "Patio-4"},
        ),
        ToolConfig(
            name="create_reservation",
            description=(
                "Creates a reservation AFTER the caller confirms name, party size, date, and time. "
                "Never call before explicit confirmation."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "guest_name": {"type": "string"},
                    "phone": {"type": "string"},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                    "party_size": {"type": "integer"},
                    "notes": {"type": "string"},
                },
                "required": ["guest_name", "date", "time", "party_size"],
            },
            mock_response={"reservation_id": "RST-1001", "status": "confirmed"},
        ),
        ToolConfig(
            name="get_hours_and_menu_info",
            description="Returns hours, location, and high-level menu categories. Call for hours or menu questions.",
            parameters={"type": "object", "properties": {}, "required": []},
            mock_response={
                "hours": "Tue–Sun 5pm–10pm",
                "address": "123 Main St",
                "menu_categories": ["starters", "mains", "desserts", "wine"],
            },
        ),
    ]

    skills = [
        SkillConfig(
            id="reservations",
            name="Reservations",
            description="Book and check tables",
            system_prompt="Collect party size, date, time, then name. Confirm before create_reservation.",
            tool_names=["check_availability", "create_reservation"],
            flow_id="reservation_flow",
        )
    ]

    flows = [
        FlowConfig(
            id="reservation_flow",
            name="Reservation",
            description="Happy-path booking",
            initial_state="collect_party",
            states=[
                FlowState(
                    id="collect_party",
                    instruction="Ask party size.",
                    transitions={"party_given": "collect_datetime"},
                ),
                FlowState(
                    id="collect_datetime",
                    instruction="Ask preferred date and time, then call check_availability.",
                    allowed_tools=["check_availability"],
                    transitions={"slot_ok": "collect_name", "slot_busy": "collect_datetime"},
                ),
                FlowState(
                    id="collect_name",
                    instruction="Ask for guest name and phone.",
                    transitions={"details_given": "confirm"},
                ),
                FlowState(
                    id="confirm",
                    instruction="Read back the reservation and ask for yes/no.",
                    allowed_tools=["create_reservation"],
                    transitions={"confirmed": "complete", "declined": "collect_datetime"},
                ),
                FlowState(
                    id="complete",
                    instruction="Confirm booking ID briefly and offer anything else.",
                    is_terminal=True,
                ),
            ],
        )
    ]

    greeter = AgentConfig(
        id="greeter",
        name="Greeter",
        role="Welcome and route",
        system_prompt=compose_system_prompt(
            identity=f"Greeting host for {company_name}.",
            goals="Welcome callers; route to reservations or info.",
            style="Warm, concise, restaurant-appropriate.",
            guardrails=DEFAULT_GUARDRAILS,
        ),
        entry_message=f"Thanks for calling {company_name}. Are you looking to make a reservation, or can I help with hours and menu?",
        handoff_targets=["reservations", "info"],
    )
    reservations = AgentConfig(
        id="reservations",
        name="Reservations",
        role="Book tables",
        system_prompt=compose_system_prompt(
            identity=f"Reservations specialist for {company_name}.",
            goals="Book tables accurately using tools only.",
            style="Friendly and precise.",
            tools_hint="Use check_availability then create_reservation after confirmation.",
            guardrails=DEFAULT_GUARDRAILS,
        ),
        skill_ids=["reservations"],
        tool_names=["check_availability", "create_reservation"],
        handoff_targets=["greeter", "info"],
    )
    info = AgentConfig(
        id="info",
        name="Info",
        role="Hours and menu",
        system_prompt=compose_system_prompt(
            identity=f"Info agent for {company_name}.",
            goals="Answer hours/location/menu category questions via tools.",
            style="Helpful and brief.",
            tools_hint="Call get_hours_and_menu_info for facts.",
            guardrails=DEFAULT_GUARDRAILS,
        ),
        tool_names=["get_hours_and_menu_info"],
        handoff_targets=["greeter", "reservations"],
    )

    return VoiceAgentDeployment(
        id=f"dep_{company_id}_restaurant",
        name=f"{company_name} Restaurant Voice Agent",
        company_id=company_id,
        industry=Industry.RESTAURANT,
        direction=CallDirection.BOTH,
        agents=[greeter, reservations, info],
        skills=skills,
        tools=tools,
        flows=flows,
        mcp_servers=[
            MCPServerConfig(
                id="pos_or_reservations",
                name="Customer reservation / POS MCP",
                transport="sse",
                url="https://CUSTOMER_MCP_HOST/sse",
                include_tools=["check_availability", "create_reservation"],
                enabled=False,
            )
        ],
        entry_agent_id="greeter",
        outbound_script=(
            f"Hi, this is {company_name} calling about your reservation. "
            "Is now a good time for a quick confirmation?"
        ),
        tags=["restaurant", "reservations"],
    )


def car_dealer_template(company_id: str, company_name: str) -> VoiceAgentDeployment:
    tools = [
        ToolConfig(
            name="search_inventory",
            description=(
                "Searches vehicle inventory by make, model, year, or budget. "
                "Call when the caller asks what cars are available."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "make": {"type": "string"},
                    "model": {"type": "string"},
                    "year_min": {"type": "integer"},
                    "max_price": {"type": "number"},
                },
                "required": [],
            },
            mock_response={
                "vehicles": [
                    {"vin": "1HGCM...", "year": 2024, "make": "Honda", "model": "Accord", "price": 28900}
                ]
            },
        ),
        ToolConfig(
            name="schedule_test_drive",
            description="Schedules a test drive after confirming vehicle, date/time, and driver name.",
            parameters={
                "type": "object",
                "properties": {
                    "vin": {"type": "string"},
                    "customer_name": {"type": "string"},
                    "phone": {"type": "string"},
                    "datetime": {"type": "string"},
                },
                "required": ["vin", "customer_name", "datetime"],
            },
            mock_response={"appointment_id": "TD-220", "status": "booked"},
        ),
        ToolConfig(
            name="get_service_appointment_slots",
            description="Returns open service department slots. Call for oil change / repair scheduling.",
            parameters={
                "type": "object",
                "properties": {
                    "service_type": {"type": "string"},
                    "preferred_date": {"type": "string"},
                },
                "required": ["service_type"],
            },
            mock_response={"slots": ["2026-07-11T09:00", "2026-07-11T14:00"]},
            auth_type=ToolAuthType.API_KEY,
            auth_secret_ref="CUSTOMER_DMS_API_KEY",
        ),
    ]

    greeter = AgentConfig(
        id="greeter",
        name="Greeter",
        role="Route sales vs service",
        system_prompt=compose_system_prompt(
            identity=f"Front desk for {company_name}.",
            goals="Route to sales or service quickly.",
            style="Professional dealership tone.",
            guardrails=DEFAULT_GUARDRAILS,
        ),
        entry_message=f"Thank you for calling {company_name}. Are you calling about sales or service?",
        handoff_targets=["sales", "service"],
    )
    sales = AgentConfig(
        id="sales",
        name="Sales",
        role="Inventory and test drives",
        system_prompt=compose_system_prompt(
            identity=f"Sales specialist for {company_name}.",
            goals="Help find vehicles and book test drives using tools.",
            style="Consultative, never pushy.",
            tools_hint="search_inventory then schedule_test_drive after confirmation.",
            guardrails=DEFAULT_GUARDRAILS,
        ),
        tool_names=["search_inventory", "schedule_test_drive"],
        handoff_targets=["greeter", "service"],
    )
    service = AgentConfig(
        id="service",
        name="Service",
        role="Service appointments",
        system_prompt=compose_system_prompt(
            identity=f"Service advisor for {company_name}.",
            goals="Offer real appointment slots from tools only.",
            style="Clear and helpful.",
            tools_hint="Use get_service_appointment_slots.",
            guardrails=DEFAULT_GUARDRAILS,
        ),
        tool_names=["get_service_appointment_slots"],
        handoff_targets=["greeter", "sales"],
    )

    return VoiceAgentDeployment(
        id=f"dep_{company_id}_dealer",
        name=f"{company_name} Dealership Voice Agent",
        company_id=company_id,
        industry=Industry.CAR_DEALER,
        direction=CallDirection.BOTH,
        agents=[greeter, sales, service],
        tools=tools,
        skills=[],
        flows=[],
        mcp_servers=[
            MCPServerConfig(
                id="dms",
                name="Dealer DMS MCP",
                transport="sse",
                url="https://CUSTOMER_DMS_MCP/sse",
                include_tools=["search_inventory", "schedule_test_drive", "get_service_appointment_slots"],
                enabled=False,
            )
        ],
        entry_agent_id="greeter",
        outbound_script=(
            f"Hi, this is {company_name}. I'm calling about your vehicle inquiry. "
            "Do you have a minute?"
        ),
        tags=["automotive", "sales", "service"],
    )


def mortgage_servicing_template(company_id: str, company_name: str) -> VoiceAgentDeployment:
    tools = [
        ToolConfig(
            name="verify_identity",
            description=(
                "Verifies caller identity using loan number + last 4 of SSN + DOB. "
                "Must succeed before any account data is shared."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "loan_number": {"type": "string"},
                    "ssn_last4": {"type": "string"},
                    "date_of_birth": {"type": "string", "description": "YYYY-MM-DD"},
                },
                "required": ["loan_number", "ssn_last4", "date_of_birth"],
            },
            mock_response={"verified": True, "member_id": "M-88991"},
            auth_secret_ref="CUSTOMER_LOS_API_KEY",
            auth_type=ToolAuthType.BEARER,
        ),
        ToolConfig(
            name="get_loan_details",
            description="Returns balance, next due date, and payment status for a verified member.",
            parameters={
                "type": "object",
                "properties": {"member_id": {"type": "string"}},
                "required": ["member_id"],
            },
            mock_response={
                "balance": 243500.12,
                "next_due": "2026-08-01",
                "amount_due": 1820.44,
                "status": "current",
            },
            mcp_binding="loan_servicing/get_loan_details",
        ),
        ToolConfig(
            name="make_payment",
            description=(
                "Posts a payment ONLY after verification and explicit caller confirmation of amount and method."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "member_id": {"type": "string"},
                    "amount": {"type": "number"},
                    "method": {"type": "string", "enum": ["ach", "card", "debit"]},
                },
                "required": ["member_id", "amount", "method"],
            },
            mock_response={"payment_id": "PAY-7781", "status": "accepted"},
            mcp_binding="loan_servicing/make_payment",
        ),
        ToolConfig(
            name="escalate_to_human",
            description="Transfers to a live servicing agent. Call when requested or after 3 failed verifications.",
            parameters={
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "required": ["reason"],
            },
            mock_response={"queued": True, "queue": "mortgage_servicing"},
        ),
    ]

    flows = [
        FlowConfig(
            id="payment_flow",
            name="Payment",
            description="Collect → confirm → pay",
            initial_state="idle",
            states=[
                FlowState(
                    id="idle",
                    instruction="Wait until caller wants to pay.",
                    transitions={"user_wants_payment": "collecting_amount"},
                ),
                FlowState(
                    id="collecting_amount",
                    instruction="Ask how much they want to pay.",
                    transitions={"amount_provided": "collecting_method"},
                ),
                FlowState(
                    id="collecting_method",
                    instruction="Ask payment method (ACH, card, debit).",
                    transitions={"method_provided": "confirming"},
                ),
                FlowState(
                    id="confirming",
                    instruction="Confirm amount and method; only then call make_payment.",
                    allowed_tools=["make_payment"],
                    transitions={"user_confirmed": "processing", "user_declined": "collecting_amount"},
                ),
                FlowState(
                    id="processing",
                    instruction="Report payment result briefly.",
                    transitions={"payment_ok": "complete"},
                ),
                FlowState(id="complete", instruction="Offer receipt summary.", is_terminal=True),
            ],
        )
    ]

    greeter = AgentConfig(
        id="greeter",
        name="Greeter",
        role="Welcome and route",
        system_prompt=compose_system_prompt(
            identity=f"Mortgage servicing greeter for {company_name}.",
            goals="Welcome; route to verification for any account topic.",
            style="Calm, regulated, professional.",
            guardrails=DEFAULT_GUARDRAILS + " Never discuss loan details before verification.",
        ),
        entry_message=f"Thank you for calling {company_name} loan servicing. How can I help you today?",
        handoff_targets=["verification"],
        tool_names=["escalate_to_human"],
    )
    verification = AgentConfig(
        id="verification",
        name="Verification",
        role="Identity checks",
        system_prompt=compose_system_prompt(
            identity="Identity verification agent.",
            goals="Verify loan number, SSN last 4, and DOB before any account data.",
            style="Patient and clear. One question at a time.",
            tools_hint="Call verify_identity. After 3 failures, escalate_to_human.",
            guardrails=DEFAULT_GUARDRAILS,
        ),
        tool_names=["verify_identity", "escalate_to_human"],
        handoff_targets=["payment", "loan_info"],
    )
    payment = AgentConfig(
        id="payment",
        name="Payment",
        role="Payments",
        system_prompt=compose_system_prompt(
            identity="Payment specialist.",
            goals="Collect amount and method, confirm, then make_payment.",
            style="Precise; always confirm.",
            tools_hint="Follow payment_flow. Use make_payment only after confirmation.",
            guardrails=DEFAULT_GUARDRAILS,
        ),
        tool_names=["make_payment", "get_loan_details", "escalate_to_human"],
        skill_ids=[],
        handoff_targets=["loan_info"],
    )
    loan_info = AgentConfig(
        id="loan_info",
        name="Loan Info",
        role="Balances and due dates",
        system_prompt=compose_system_prompt(
            identity="Loan information agent.",
            goals="Share only tool-grounded loan facts.",
            style="Clear numbers, no jargon overload.",
            tools_hint="Call get_loan_details with verified member_id.",
            guardrails=DEFAULT_GUARDRAILS,
        ),
        tool_names=["get_loan_details", "escalate_to_human"],
        handoff_targets=["payment"],
    )

    return VoiceAgentDeployment(
        id=f"dep_{company_id}_mortgage",
        name=f"{company_name} Mortgage Servicing Voice Agent",
        company_id=company_id,
        industry=Industry.MORTGAGE_SERVICING,
        direction=CallDirection.BOTH,
        agents=[greeter, verification, payment, loan_info],
        tools=tools,
        skills=[
            SkillConfig(
                id="payments",
                name="Payments",
                description="Payment collection skill",
                system_prompt="Enforce confirmation before posting payment.",
                tool_names=["make_payment", "get_loan_details"],
                flow_id="payment_flow",
            )
        ],
        flows=flows,
        mcp_servers=[
            MCPServerConfig(
                id="loan_servicing",
                name="Loan servicing MCP",
                transport="sse",
                url="https://CUSTOMER_LOS_MCP/sse",
                include_tools=["get_loan_details", "make_payment", "verify_identity"],
                enabled=False,
            )
        ],
        entry_agent_id="greeter",
        outbound_script=(
            f"Hello, this is {company_name} calling about your mortgage account. "
            "I need to verify your identity before we continue. Is now a good time?"
        ),
        tags=["mortgage", "servicing", "regulated"],
    )


TEMPLATES = {
    Industry.RESTAURANT: restaurant_template,
    Industry.CAR_DEALER: car_dealer_template,
    Industry.MORTGAGE_SERVICING: mortgage_servicing_template,
}


def build_template(industry: Industry, company_id: str, company_name: str) -> VoiceAgentDeployment:
    if industry not in TEMPLATES:
        raise ValueError(f"No template for industry {industry}")
    return TEMPLATES[industry](company_id, company_name)

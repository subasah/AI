from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.db.store import new_id, store
from incoming_call_handler.handler import register_deployment
from library.config.models import (
    AgentConfig,
    CallDirection,
    FlowConfig,
    Industry,
    MCPServerConfig,
    SkillConfig,
    ToolConfig,
    VoiceAgentDeployment,
    VoiceProviderConfig,
)
from library.industries.templates import build_template

router = APIRouter(prefix="/deployments", tags=["deployments"])


class DeploymentCreate(BaseModel):
    name: str
    company_id: str
    industry: Industry = Industry.CUSTOM
    direction: CallDirection = CallDirection.BOTH
    from_template: bool = True
    phone_numbers: list[str] = Field(default_factory=list)
    created_by: str | None = None


class DeploymentPatch(BaseModel):
    name: str | None = None
    status: str | None = None
    direction: CallDirection | None = None
    phone_numbers: list[str] | None = None
    agents: list[AgentConfig] | None = None
    skills: list[SkillConfig] | None = None
    tools: list[ToolConfig] | None = None
    flows: list[FlowConfig] | None = None
    mcp_servers: list[MCPServerConfig] | None = None
    entry_agent_id: str | None = None
    global_system_preamble: str | None = None
    outbound_script: str | None = None
    voice: VoiceProviderConfig | None = None
    tags: list[str] | None = None


class AttachMCPRequest(BaseModel):
    server: MCPServerConfig


class AttachToolRequest(BaseModel):
    tool: ToolConfig


@router.get("")
def list_deployments(company_id: str | None = None) -> list[VoiceAgentDeployment]:
    return store.list_deployments(company_id=company_id)


@router.post("", status_code=201)
def create_deployment(body: DeploymentCreate) -> VoiceAgentDeployment:
    company = store.get_company(body.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found — create company first")

    if body.from_template and body.industry != Industry.CUSTOM:
        deployment = build_template(body.industry, body.company_id, company.name)
        deployment.id = new_id("dep")
        deployment.name = body.name
        deployment.direction = body.direction
        deployment.phone_numbers = body.phone_numbers
        deployment.created_by = body.created_by
        deployment.status = "draft"
    else:
        deployment = VoiceAgentDeployment(
            id=new_id("dep"),
            name=body.name,
            company_id=body.company_id,
            industry=body.industry,
            direction=body.direction,
            phone_numbers=body.phone_numbers,
            created_by=body.created_by,
            status="draft",
            agents=[],
            tools=[],
            skills=[],
            flows=[],
            mcp_servers=[],
        )

    store.upsert_deployment(deployment)
    register_deployment(deployment)
    return deployment


@router.get("/{deployment_id}")
def get_deployment(deployment_id: str) -> VoiceAgentDeployment:
    dep = store.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return dep


@router.patch("/{deployment_id}")
def patch_deployment(deployment_id: str, body: DeploymentPatch) -> VoiceAgentDeployment:
    dep = store.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")
    data = dep.model_dump(mode="json")
    updates = body.model_dump(exclude_unset=True, mode="json")
    data.update(updates)
    data["version"] = dep.version + 1
    updated = VoiceAgentDeployment.model_validate(data)
    store.upsert_deployment(updated)
    register_deployment(updated)
    return updated


@router.post("/{deployment_id}/mcp")
def attach_mcp(deployment_id: str, body: AttachMCPRequest) -> VoiceAgentDeployment:
    dep = store.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")
    servers = [s for s in dep.mcp_servers if s.id != body.server.id]
    servers.append(body.server)
    dep.mcp_servers = servers
    dep.version += 1
    store.upsert_deployment(dep)
    register_deployment(dep)
    return dep


@router.post("/{deployment_id}/tools")
def attach_tool(deployment_id: str, body: AttachToolRequest) -> VoiceAgentDeployment:
    """Easily attach another customer service tomorrow."""
    dep = store.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")
    tools = [t for t in dep.tools if t.name != body.tool.name]
    tools.append(body.tool)
    dep.tools = tools
    dep.version += 1
    store.upsert_deployment(dep)
    register_deployment(dep)
    return dep


@router.post("/{deployment_id}/activate")
def activate(deployment_id: str) -> VoiceAgentDeployment:
    dep = store.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if not dep.agents:
        raise HTTPException(status_code=400, detail="Add at least one agent before activating")
    if not dep.entry_agent_id:
        dep.entry_agent_id = dep.agents[0].id
    dep.status = "active"
    dep.version += 1
    store.upsert_deployment(dep)
    register_deployment(dep)
    return dep


@router.delete("/{deployment_id}")
def delete_deployment(deployment_id: str) -> dict[str, str]:
    if not store.delete_deployment(deployment_id):
        raise HTTPException(status_code=404, detail="Deployment not found")
    return {"status": "deleted", "id": deployment_id}


@router.get("/{deployment_id}/export")
def export_deployment(deployment_id: str) -> dict[str, Any]:
    dep = store.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return dep.model_dump(mode="json")

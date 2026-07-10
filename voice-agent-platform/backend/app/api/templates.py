from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from library.config.models import Industry, VoiceAgentDeployment
from library.industries.templates import TEMPLATES, build_template

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplatePreviewRequest(BaseModel):
    industry: Industry
    company_id: str = "preview"
    company_name: str = "Preview Co"


@router.get("")
def list_templates() -> list[dict[str, str]]:
    return [
        {
            "industry": industry.value,
            "label": industry.value.replace("_", " ").title(),
            "description": _DESC.get(industry, ""),
        }
        for industry in TEMPLATES
    ]


@router.post("/preview", response_model=VoiceAgentDeployment)
def preview_template(body: TemplatePreviewRequest) -> VoiceAgentDeployment:
    if body.industry not in TEMPLATES:
        raise HTTPException(status_code=400, detail="Unknown industry template")
    return build_template(body.industry, body.company_id, body.company_name)


_DESC = {
    Industry.RESTAURANT: "Reservations, hours, menu routing with confirmation flow",
    Industry.CAR_DEALER: "Sales inventory, test drives, and service scheduling",
    Industry.MORTGAGE_SERVICING: "Verification, loan info, payments, human escalation",
}

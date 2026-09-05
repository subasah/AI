from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.db.store import new_id, store
from library.config.models import CompanyConfig, Industry

router = APIRouter(prefix="/companies", tags=["companies"])


class CompanyCreate(BaseModel):
    name: str
    industry: Industry = Industry.CUSTOM
    contact_email: str | None = None
    timezone: str = "America/New_York"
    brand_voice: str = "professional, warm, concise"
    metadata: dict = Field(default_factory=dict)


@router.get("")
def list_companies() -> list[CompanyConfig]:
    return store.list_companies()


@router.post("", status_code=201)
def create_company(body: CompanyCreate) -> CompanyConfig:
    company = CompanyConfig(id=new_id("co"), **body.model_dump())
    return store.upsert_company(company)


@router.get("/{company_id}")
def get_company(company_id: str) -> CompanyConfig:
    company = store.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.put("/{company_id}")
def update_company(company_id: str, body: CompanyCreate) -> CompanyConfig:
    existing = store.get_company(company_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Company not found")
    company = CompanyConfig(id=company_id, **body.model_dump())
    return store.upsert_company(company)


@router.delete("/{company_id}")
def delete_company(company_id: str) -> dict[str, str]:
    if not store.delete_company(company_id):
        raise HTTPException(status_code=404, detail="Company not found")
    return {"status": "deleted", "id": company_id}

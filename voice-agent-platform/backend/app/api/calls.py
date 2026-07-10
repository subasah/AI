from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.app.db.call_repository import get_call_repository

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("")
def list_calls(
    company_id: str | None = None,
    deployment_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    repo = get_call_repository()
    if repo is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Call I/O persistence requires MySQL. "
                "Set STORE_BACKEND=mysql (Docker Compose does this) or CALL_LOG_MYSQL=true."
            ),
        )
    return repo.list_calls(company_id=company_id, deployment_id=deployment_id, limit=limit)


@router.get("/{call_id}")
def get_call(call_id: str) -> dict[str, Any]:
    repo = get_call_repository()
    if repo is None:
        raise HTTPException(status_code=503, detail="Call I/O persistence requires MySQL")
    detail = repo.get_call_detail(call_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Call not found")
    return detail

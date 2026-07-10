"""Combined FastAPI app: control plane + incoming + outgoing handlers."""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

ROOT = Path(__file__).resolve().parents[2]  # voice-agent-platform/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from backend.app.api import calls, companies, deployments, health, templates  # noqa: E402
from incoming_call_handler import handler as incoming  # noqa: E402
from outgoing_call_handler import handler as outgoing  # noqa: E402


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from backend.app.db.call_repository import get_call_repository
    from backend.app.db.store import store
    from library.config.loader import load_deployment
    from library.config.models import CompanyConfig

    # Eagerly init call I/O MySQL repo when configured (Docker sets STORE_BACKEND=mysql)
    repo = get_call_repository()
    if repo is None:
        logger.warning(
            "Call transcript/tool I/O will NOT persist to MySQL. "
            "Use docker compose (STORE_BACKEND=mysql) for production debugging."
        )
    else:
        logger.info("Call transcript/tool I/O persistence is active")

    examples = ROOT / "configs" / "examples"
    n = incoming.load_deployments_from_dir(examples)
    # Seed control-plane store so the admin UI sees demo customers
    if examples.exists():
        for path in list(examples.glob("*.json")) + list(examples.glob("*.yaml")):
            dep = load_deployment(path)
            if not store.get_company(dep.company_id):
                nice_name = dep.name
                for suffix in (" Voice Agent", " Restaurant", " Dealership", " Mortgage Servicing"):
                    if nice_name.endswith(suffix):
                        nice_name = nice_name[: -len(suffix)]
                # Prefer names baked into templates via company_name
                nice_name = {
                    "co_demo_bistro": "Harbor Bistro",
                    "co_demo_dealer": "Summit Motors",
                    "co_demo_mortgage": "Northline Servicing",
                }.get(dep.company_id, nice_name.strip() or dep.company_id)
                store.upsert_company(
                    CompanyConfig(
                        id=dep.company_id,
                        name=nice_name,
                        industry=dep.industry,
                        brand_voice="professional, warm, concise",
                    )
                )
            if not store.get_deployment(dep.id):
                store.upsert_deployment(dep)
                incoming.register_deployment(dep)
    # Share registry with outgoing
    outgoing._DEPLOYMENTS = incoming._DEPLOYMENTS
    outgoing._SESSIONS = incoming._SESSIONS
    logger.info("Loaded {} example deployments from {}", n, examples)
    yield


app = FastAPI(
    title="Agnostic Voice Agent Platform",
    description=(
        "Multi-tenant control plane to create industry-agnostic voice agents, "
        "attach customer MCP/tools, and handle inbound/outbound calls."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(companies.router, prefix="/api")
app.include_router(deployments.router, prefix="/api")
app.include_router(templates.router, prefix="/api")
app.include_router(calls.router, prefix="/api")
app.include_router(incoming.router)
app.include_router(outgoing.router)


def main() -> None:
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8080")),
        reload=os.getenv("RELOAD", "true").lower() == "true",
    )


if __name__ == "__main__":
    main()

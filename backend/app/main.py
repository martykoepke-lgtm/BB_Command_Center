"""
BB Enabled Command — FastAPI Application Entry Point.

Wires together the API routers, CORS middleware, database lifecycle,
the AI orchestrator singleton, and Nexus integration services
(event bus, workflow chains, WebSocket manager, file storage, email).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.agents.orchestrator import Orchestrator, create_orchestrator
from app.config import get_settings
from app.middleware import (
    RequestLoggingMiddleware,
    configure_logging,
    register_exception_handlers,
)
from app.services.email_service import init_email_service
from app.services.event_bus import init_event_bus
from app.services.file_storage import init_file_storage
from app.services.workflow_chains import register_workflow_chains
from app.services.ws_manager import init_ws_manager

# ---------------------------------------------------------------------------
# Application state — shared singletons
# ---------------------------------------------------------------------------

_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    """Dependency: returns the global AI orchestrator instance."""
    if _orchestrator is None:
        raise RuntimeError("Orchestrator not initialized — app not started")
    return _orchestrator


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown hooks
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup:  initialize the AI orchestrator, connect to database.
    Shutdown: close database connections, release resources.
    """
    global _orchestrator
    settings = get_settings()

    # 1. Wire up the AI agent system
    _orchestrator = create_orchestrator()
    agent_names = [a.value for a in _orchestrator._agents]
    print(f"[startup] AI orchestrator online — agents: {', '.join(agent_names)}")

    # 2. Database connection — verify engine is reachable
    from app.database import engine
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("[startup] Database connection: OK")
    except Exception as e:
        print(f"[startup] Database connection: FAILED ({e}) — app will start but DB operations will fail")

    # 3. Nexus integration services
    event_bus = init_event_bus()
    init_ws_manager()
    init_file_storage(settings)
    init_email_service(settings)
    register_workflow_chains(event_bus)
    print(f"[startup] Nexus services online — {event_bus.handler_count} event handlers registered")

    yield  # ---------- app is running ----------

    # Shutdown
    await engine.dispose()
    print("[shutdown] Resources released")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(debug=settings.app_debug)

    app = FastAPI(
        title="BB Enabled Command",
        description="Performance Excellence Operating System — AI-driven Lean Six Sigma platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware stack (order matters — outermost first)
    # Request logging wraps everything: logs timing + adds X-Request-ID
    app.add_middleware(RequestLoggingMiddleware)

    # CORS — allow frontend dev server
    origins = [o.strip() for o in settings.cors_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    from app.routers import ai as ai_router
    from app.routers import auth as auth_router
    from app.routers import requests as requests_router
    from app.routers import initiatives as initiatives_router
    from app.routers import users as users_router
    from app.routers import teams as teams_router
    from app.routers import actions as actions_router
    from app.routers import artifacts as artifacts_router
    from app.routers import notes as notes_router
    from app.routers import documents as documents_router
    from app.routers import metrics as metrics_router
    from app.routers import datasets as datasets_router
    from app.routers import analyses as analyses_router
    from app.routers import dashboards as dashboards_router
    from app.routers import reports as reports_router
    from app.routers import ws_dashboard as ws_dashboard_router
    from app.routers import my_work as my_work_router
    from app.routers import stakeholders as stakeholders_router

    app.include_router(auth_router.router, prefix="/api")
    app.include_router(ai_router.router, prefix="/api")
    app.include_router(requests_router.router, prefix="/api")
    app.include_router(initiatives_router.router, prefix="/api")
    app.include_router(users_router.router, prefix="/api")
    app.include_router(teams_router.router, prefix="/api")
    app.include_router(actions_router.router, prefix="/api")
    app.include_router(artifacts_router.router, prefix="/api")
    app.include_router(notes_router.router, prefix="/api")
    app.include_router(documents_router.router, prefix="/api")
    app.include_router(metrics_router.router, prefix="/api")
    app.include_router(datasets_router.router, prefix="/api")
    app.include_router(analyses_router.router, prefix="/api")
    app.include_router(dashboards_router.router, prefix="/api")
    app.include_router(reports_router.router, prefix="/api")
    app.include_router(ws_dashboard_router.router, prefix="/api")
    app.include_router(my_work_router.router, prefix="/api")
    app.include_router(stakeholders_router.router, prefix="/api")

    # Standardized error responses
    register_exception_handlers(app)

    # Health check
    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "service": "bb-enabled-command",
            "agents_loaded": _orchestrator is not None,
        }

    return app


# ---------------------------------------------------------------------------
# Module-level app instance (used by `uvicorn app.main:app`)
# ---------------------------------------------------------------------------

app = create_app()

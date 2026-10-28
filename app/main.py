"""FastAPI application entry point for Privatemode AI 2API."""

from __future__ import annotations

import logging
import sys
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.v1.admin import router as admin_router
from app.api.v1.chat import router as chat_router
from app.api.v1.models import router as models_router
from app.api.v1.register import router as register_router
from app.core.config import settings
from app.core.dependencies import account_manager
from app.core.exceptions import AccountPoolError, PrivatemodeError, UpstreamError

logger = logging.getLogger("privatemode2api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions - configure UTF-8 logging handler for Windows console
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    # Clear existing handlers to prevent duplicate or non-utf8 outputs
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    # Force stdout / stderr encoding to utf-8 if possible
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s"))
    root_logger.addHandler(handler)
    stats = await account_manager.get_stats()
    logger.info(
        "Privatemode2API started on %s:%d | Total accounts: %d (Active: %d, Exhausted: %d)",
        settings.HOST,
        settings.PORT,
        stats["total_accounts"],
        stats["active_accounts"],
        stats["exhausted_accounts"],
    )
    yield
    # Shutdown actions
    account_manager.save_accounts()
    logger.info("Privatemode2API shut down cleanly.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Privatemode AI 2API",
        description="OpenAI-compatible 2API gateway and registration service for Privatemode AI",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Enable CORS for web-based UI clients (NextChat, LobeChat, Cherry Studio, etc.)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # OpenAI-compatible exception handlers
    @app.exception_handler(AccountPoolError)
    async def account_pool_error_handler(request: Request, exc: AccountPoolError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "message": str(exc),
                    "type": "insufficient_quota",
                    "code": 503,
                }
            },
        )

    @app.exception_handler(UpstreamError)
    async def upstream_error_handler(request: Request, exc: UpstreamError):
        return JSONResponse(
            status_code=exc.status_code or 502,
            content={
                "error": {
                    "message": str(exc),
                    "type": "upstream_error",
                    "code": exc.status_code,
                    "detail": exc.detail,
                }
            },
        )

    @app.exception_handler(PrivatemodeError)
    async def generic_privatemode_error_handler(request: Request, exc: PrivatemodeError):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "message": str(exc),
                    "type": "privatemode_error",
                    "code": 500,
                }
            },
        )

    # Include API routers under /v1 prefix
    app.include_router(chat_router, prefix="/v1", tags=["Chat"])
    app.include_router(models_router, prefix="/v1", tags=["Models"])
    app.include_router(register_router, prefix="/v1", tags=["Registration"])
    app.include_router(admin_router, prefix="/v1", tags=["Admin"])
    app.include_router(admin_router, tags=["Admin (Dashboard)"])

    # Also route chat and models at root level for clients omitting /v1
    app.include_router(chat_router, tags=["Chat (Root)"])
    app.include_router(models_router, tags=["Models (Root)"])

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict[str, Any]:
        stats = await account_manager.get_stats()
        return {
            "status": "healthy",
            "active_accounts": stats["active_accounts"],
            "total_accounts": stats["total_accounts"],
            "default_model": settings.DEFAULT_MODEL,
        }

    # Web Dashboard route
    @app.get("/", response_class=HTMLResponse, tags=["Web Dashboard"])
    @app.get("/dashboard", response_class=HTMLResponse, tags=["Web Dashboard"])
    async def serve_dashboard():
        template_path = os.path.join(os.path.dirname(__file__), "templates", "dashboard.html")
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        return HTMLResponse(content="<h3>Dashboard template not found</h3>", status_code=404)

    @app.get("/api/info", tags=["Info"])
    async def api_info() -> dict[str, Any]:
        stats = await account_manager.get_stats()
        return {
            "service": "Privatemode AI 2API",
            "version": "1.0.0",
            "status": "running",
            "accounts": stats,
            "endpoints": {
                "chat_completions": "/v1/chat/completions",
                "models": "/v1/models",
                "register": "/v1/register",
                "register_status": "/v1/register/status/{job_id}",
                "admin_pool": "/v1/admin/pool",
                "admin_accounts": "/v1/admin/accounts",
                "docs": "/docs",
            },
        }

    return app


app = create_app()

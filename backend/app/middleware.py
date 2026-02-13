"""
API middleware — request logging, timing, and standardized error responses.

Provides:
  - RequestLoggingMiddleware: logs method, path, status, duration for every request
  - Standardized exception handlers for HTTPException and unhandled errors
"""

from __future__ import annotations

import time
import logging
import traceback
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("bb_command")


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every request with method, path, status code, and duration.
    Adds a unique request ID header for tracing.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid4())[:8]
        start = time.perf_counter()

        # Attach request_id to state so handlers can reference it
        request.state.request_id = request_id

        try:
            response = await call_next(request)
        except Exception:
            # Catch unhandled errors that escape the call stack
            duration_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "[%s] %s %s → 500 (%.1fms) UNHANDLED",
                request_id, request.method, request.url.path, duration_ms,
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000

        # Log level based on status code
        status = response.status_code
        if status >= 500:
            logger.error("[%s] %s %s → %d (%.1fms)", request_id, request.method, request.url.path, status, duration_ms)
        elif status >= 400:
            logger.warning("[%s] %s %s → %d (%.1fms)", request_id, request.method, request.url.path, status, duration_ms)
        else:
            logger.info("[%s] %s %s → %d (%.1fms)", request_id, request.method, request.url.path, status, duration_ms)

        # Add tracing header
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"

        return response


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

def register_exception_handlers(app: FastAPI):
    """Register standardized JSON error responses."""

    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Return consistent JSON shape for all HTTP errors."""
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "status_code": exc.status_code,
                "detail": exc.detail,
                "request_id": request_id,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Return readable validation errors."""
        request_id = getattr(request.state, "request_id", "unknown")
        errors = []
        for err in exc.errors():
            loc = " → ".join(str(l) for l in err.get("loc", []))
            errors.append({
                "field": loc,
                "message": err.get("msg", ""),
                "type": err.get("type", ""),
            })
        return JSONResponse(
            status_code=422,
            content={
                "error": True,
                "status_code": 422,
                "detail": "Validation error",
                "errors": errors,
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch-all for unhandled exceptions — log full traceback, return safe response."""
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            "[%s] Unhandled exception on %s %s:\n%s",
            request_id, request.method, request.url.path,
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "status_code": 500,
                "detail": "Internal server error",
                "request_id": request_id,
            },
        )


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

def configure_logging(debug: bool = False):
    """Set up structured logging for the application."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Quiet down noisy libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

"""Structured logging middleware for SHARMI API.

Logs requests and responses in JSON format with request ID for tracing.
"""

import json
import logging
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Configure structured logger
logger = logging.getLogger("sharmi.api")
logger.setLevel(logging.INFO)

# Add JSON formatter if not already configured
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests and responses in structured JSON format."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        request_id = getattr(request.state, "request_id", "unknown")

        # Extract request info
        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""
        client_host = request.client.host if request.client else "unknown"

        # Log request
        logger.info(
            json.dumps({
                "event": "request_start",
                "request_id": request_id,
                "method": method,
                "path": path,
                "query": query,
                "client": client_host,
            })
        )

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                json.dumps({
                    "event": "request_error",
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                })
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log response
        logger.info(
            json.dumps({
                "event": "request_complete",
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
            })
        )

        return response


def log_analysis_event(
    request_id: str,
    event_type: str,
    hazard_id: str | None = None,
    community_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Log an analysis-related event with structured data."""
    log_data = {
        "event": event_type,
        "request_id": request_id,
    }
    if hazard_id:
        log_data["hazard_id"] = hazard_id
    if community_id:
        log_data["community_id"] = community_id
    if details:
        log_data["details"] = details

    logger.info(json.dumps(log_data))
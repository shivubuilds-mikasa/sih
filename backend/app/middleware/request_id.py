"""Request ID middleware for SHARMI API.

Ensures every request has a unique X-Request-ID header for tracing.
If not provided by client, generates a new one.
"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add X-Request-ID header to all requests and responses."""

    HEADER_NAME = "x-request-id"

    async def dispatch(self, request: Request, call_next) -> Response:
        # Get request ID from header or generate new one
        request_id = request.headers.get(self.HEADER_NAME)
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in request state for access in handlers
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers[self.HEADER_NAME] = request_id
        return response
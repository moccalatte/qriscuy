"""Custom FastAPI middlewares for observability."""
from __future__ import annotations

import logging
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .monitoring import observe_request

logger = logging.getLogger("qriscuy.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request metadata, latency, and status codes."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:  # type: ignore[override]
        start = time.perf_counter()
        route = request.scope.get("route")
        route_path = route.path if route else request.url.path
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request failed",
                extra={
                    "method": request.method,
                    "path": route_path,
                    "client": request.client.host if request.client else None,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            observe_request(request.method, route_path, 500, duration_ms)
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        level = logging.INFO
        if response.status_code >= 500:
            level = logging.ERROR
        elif response.status_code >= 400:
            level = logging.WARNING

        logger.log(
            level,
            "request completed",
            extra={
                "method": request.method,
                "path": route_path,
                "status_code": response.status_code,
                "client": request.client.host if request.client else None,
                "duration_ms": round(duration_ms, 2),
            },
        )
        observe_request(request.method, route_path, response.status_code, duration_ms)
        return response

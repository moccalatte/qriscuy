"""Monitoring helpers and Prometheus metrics exporters."""
from __future__ import annotations

from typing import Final

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

_HTTP_REQUEST_TOTAL: Final = Counter(
    "qriscuy_http_requests_total",
    "Total HTTP requests",
    labelnames=("method", "route", "status"),
)
_HTTP_REQUEST_LATENCY: Final = Histogram(
    "qriscuy_http_request_duration_seconds",
    "Latency of HTTP requests",
    labelnames=("method", "route"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
_SERVICE_ERRORS_TOTAL: Final = Counter(
    "qriscuy_service_errors_total",
    "Service-level errors by code",
    labelnames=("code", "route"),
)


def observe_request(method: str, route: str, status_code: int, duration_ms: float) -> None:
    _HTTP_REQUEST_TOTAL.labels(method=method, route=route, status=str(status_code)).inc()
    _HTTP_REQUEST_LATENCY.labels(method=method, route=route).observe(duration_ms / 1000)


def record_service_error(code: str, route: str) -> None:
    _SERVICE_ERRORS_TOTAL.labels(code=code, route=route).inc()


def metrics_payload() -> tuple[bytes, str]:
    """Return Prometheus exposition payload and content type."""

    return generate_latest(), CONTENT_TYPE_LATEST

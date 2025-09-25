"""Shared service error definitions."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ServiceError(Exception):
    code: str
    message: str
    status_code: int = 400

    def __str__(self) -> str:  # noqa: D401 override
        return f"{self.code}: {self.message}"


def err_sig_invalid(message: str | None = None) -> ServiceError:
    return ServiceError(code="ERR_SIG_INVALID", message=message or "Signature validation failed", status_code=401)


def err_fp_expired(message: str | None = None) -> ServiceError:
    return ServiceError(code="ERR_FP_EXPIRED", message=message or "Fingerprint expired", status_code=410)


def err_replay(message: str | None = None) -> ServiceError:
    return ServiceError(code="ERR_REPLAY", message=message or "Fingerprint already used", status_code=409)


def err_bad_payload(message: str | None = None) -> ServiceError:
    return ServiceError(code="ERR_BAD_PAYLOAD", message=message or "Invalid request payload", status_code=400)

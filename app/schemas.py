"""Pydantic schemas for API contracts."""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PolicyEnum(str, Enum):
    FAST = "FAST"
    SAFE = "SAFE"


class GenerateQRRequest(BaseModel):
    merchant_id: str = Field(min_length=3, max_length=64)
    merchant_payload: str = Field(description="Base QRIS payload string")
    amount: int = Field(ge=1)
    currency: str = Field(default="IDR", min_length=3, max_length=3)
    policy: PolicyEnum | None = None


class GenerateQRResponse(BaseModel):
    invoice_id: UUID
    status: str
    payload: str
    crc: str
    qr_png_base64: str
    fingerprint_b64: str
    signature_hex: str
    timestamp: int
    nonce: str


class ScanRequest(BaseModel):
    fingerprint_b64: str
    signature_hex: str
    timestamp: int
    nonce: str
    device_id: str | None = None
    client_meta: dict[str, Any] | None = None


class ScanResponse(BaseModel):
    invoice_id: UUID
    status: str
    status_changed: bool


class InvoiceStatusResponse(BaseModel):
    invoice_id: UUID
    status: str
    policy: PolicyEnum
    amount: int
    currency: str
    merchant_id: str


class ConfirmRequest(BaseModel):
    action: Literal["SUCCESS", "REJECTED"]


class ConfirmResponse(BaseModel):
    invoice_id: UUID
    status: str

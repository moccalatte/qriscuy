"""Scan callback handling services."""
from __future__ import annotations

import hmac
import json
import time
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..models import Fingerprint, Invoice, InvoicePolicy, InvoiceStatus, ScanEvent
from .errors import err_bad_payload, err_fp_expired, err_replay, err_sig_invalid


@dataclass(slots=True)
class ScanResult:
    invoice: Invoice
    status_changed: bool


class ScanService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def handle_scan(
        self,
        *,
        fingerprint_b64: str,
        signature_hex: str,
        timestamp: int,
        nonce: str,
        device_id: str | None = None,
        client_meta: dict[str, Any] | None = None,
    ) -> ScanResult:
        fp_row = await self._fetch_fingerprint(fingerprint_b64)
        if not fp_row:
            raise err_bad_payload("Fingerprint not found")

        invoice = fp_row.invoice

        expected_sig = hmac.new(settings.hmac_secret.encode(), fingerprint_b64.encode(), sha256).hexdigest()
        if not hmac.compare_digest(signature_hex, expected_sig):
            raise err_sig_invalid()
        if not hmac.compare_digest(fp_row.sig_hex, expected_sig):
            raise err_sig_invalid("Fingerprint signature mismatch")
        if fp_row.nonce != nonce:
            raise err_bad_payload("Nonce mismatch")
        if fp_row.ts != timestamp:
            raise err_bad_payload("Timestamp mismatch")

        now = int(time.time())
        if now - fp_row.ts > fp_row.ttl_sec:
            invoice.status = InvoiceStatus.EXPIRED
            await self.session.commit()
            raise err_fp_expired()

        if invoice.status in {InvoiceStatus.SCANNED, InvoiceStatus.SUCCESS}:
            raise err_replay()

        event = ScanEvent(
            invoice_id=invoice.id,
            device_id=device_id,
            client_meta=json.dumps(client_meta) if client_meta else None,
        )
        self.session.add(event)

        previous_status = invoice.status
        invoice.status = InvoiceStatus.SCANNED

        if invoice.policy == InvoicePolicy.FAST:
            invoice.status = InvoiceStatus.SUCCESS

        await self.session.commit()
        await self.session.refresh(invoice)

        return ScanResult(invoice=invoice, status_changed=invoice.status != previous_status)

    async def _fetch_fingerprint(self, fp_b64: str) -> Fingerprint | None:
        stmt = (
            select(Fingerprint)
            .where(Fingerprint.fp_b64 == fp_b64)
            .options(selectinload(Fingerprint.invoice))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

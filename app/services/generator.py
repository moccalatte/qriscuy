"""Invoice generation and QR building services."""
from __future__ import annotations

import base64
import hmac
import secrets
import time
from dataclasses import dataclass
from hashlib import sha256

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import Fingerprint, Invoice, InvoicePolicy
from ..qris_encoder import EncodedPayload, Tag62Data, inject_tag62
from ..renderer import render_qr_payload


@dataclass(slots=True)
class GenerateResult:
    invoice: Invoice
    encoded: EncodedPayload
    qr_png_base64: str
    fingerprint_b64: str
    signature_hex: str
    timestamp: int
    nonce: str


class InvoiceGenerator:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_invoice(
        self,
        *,
        merchant_id: str,
        merchant_payload: str,
        amount: int,
        currency: str = "IDR",
        policy: InvoicePolicy | None = None,
    ) -> GenerateResult:
        invoice = Invoice(
            merchant_id=merchant_id,
            merchant_payload=merchant_payload,
            amount=amount,
            currency=currency,
            policy=policy or InvoicePolicy(settings.default_policy),
        )

        ts = int(time.time())
        nonce = secrets.token_urlsafe(8)
        fp_raw = f"{invoice.id}|{merchant_id}|{amount}|{ts}|{nonce}"
        fp_b64 = base64.urlsafe_b64encode(fp_raw.encode()).decode().rstrip("=")

        signature = hmac.new(settings.hmac_secret.encode(), fp_b64.encode(), sha256).hexdigest()

        tag62 = Tag62Data(
            fingerprint_b64=fp_b64,
            signature_hex=signature,
            timestamp=ts,
            nonce=nonce,
            algorithm="HMAC-SHA256",
        )
        encoded_payload = inject_tag62(merchant_payload, tag62)

        render = render_qr_payload(encoded_payload.payload, title=settings.app_name)

        fingerprint = Fingerprint(
            invoice_id=invoice.id,
            fp_b64=fp_b64,
            sig_hex=signature,
            ts=ts,
            nonce=nonce,
            ttl_sec=settings.ttl_seconds,
        )

        self.session.add(invoice)
        self.session.add(fingerprint)
        await self.session.commit()
        await self.session.refresh(invoice)

        return GenerateResult(
            invoice=invoice,
            encoded=encoded_payload,
            qr_png_base64=render["png_base64"],
            fingerprint_b64=fp_b64,
            signature_hex=signature,
            timestamp=ts,
            nonce=nonce,
        )

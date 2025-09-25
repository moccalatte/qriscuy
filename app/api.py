"""FastAPI application for qriscuy."""
from __future__ import annotations

from uuid import UUID

import logging

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .logging_conf import configure_logging
from .middleware import RequestLoggingMiddleware
from .monitoring import metrics_payload, record_service_error
from .models import Invoice, InvoicePolicy, InvoiceStatus, get_session, init_db
from .schemas import (
    ConfirmRequest,
    ConfirmResponse,
    GenerateQRRequest,
    GenerateQRResponse,
    InvoiceStatusResponse,
    PolicyEnum,
    ScanRequest,
    ScanResponse,
)
from .services.errors import ServiceError
from .services.generator import InvoiceGenerator
from .services.scan import ScanService

app = FastAPI(title="qriscuy", version="0.1.0")
app.add_middleware(RequestLoggingMiddleware)

logger = logging.getLogger("qriscuy.api")


def _warn_insecure_defaults() -> None:
    if settings.api_key == "dev-secret-key":
        logger.warning(
            "api key menggunakan nilai default",
            extra={"config_key": "api_key"},
        )
    if settings.hmac_secret == "change-me":
        logger.warning(
            "hmac_secret menggunakan nilai default",
            extra={"config_key": "hmac_secret"},
        )


@app.on_event("startup")
async def on_startup() -> None:
    configure_logging()
    _warn_insecure_defaults()
    await init_db()


async def require_api_key(x_api_key: str = Header(...)) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
    route = request.scope.get("route")
    route_path = route.path if route else request.url.path
    logger.warning(
        "service error",
        extra={"code": exc.code, "path": route_path, "method": request.method},
    )
    record_service_error(exc.code, route_path)
    return JSONResponse(status_code=exc.status_code, content={"code": exc.code, "message": exc.message})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    route = request.scope.get("route")
    route_path = route.path if route else request.url.path
    logger.exception(
        "unhandled exception",
        extra={"path": route_path, "method": request.method},
    )
    return JSONResponse(status_code=500, content={"code": "ERR_INTERNAL", "message": "Internal server error"})


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics", tags=["system"])
async def metrics() -> Response:
    payload, content_type = metrics_payload()
    return Response(content=payload, media_type=content_type)


@app.post("/v1/qr", response_model=GenerateQRResponse, tags=["qr"], dependencies=[Depends(require_api_key)])
async def generate_qr(
    payload: GenerateQRRequest,
    session: AsyncSession = Depends(get_session),
) -> GenerateQRResponse:
    generator = InvoiceGenerator(session)
    policy = InvoicePolicy(payload.policy.value) if payload.policy else None
    result = await generator.create_invoice(
        merchant_id=payload.merchant_id,
        merchant_payload=payload.merchant_payload,
        amount=payload.amount,
        currency=payload.currency,
        policy=policy,
    )
    invoice = result.invoice

    return GenerateQRResponse(
        invoice_id=UUID(invoice.id),
        status=invoice.status.value,
        payload=result.encoded.payload,
        crc=result.encoded.crc,
        qr_png_base64=result.qr_png_base64,
        fingerprint_b64=result.fingerprint_b64,
        signature_hex=result.signature_hex,
        timestamp=result.timestamp,
        nonce=result.nonce,
    )


@app.post("/v1/scan", response_model=ScanResponse, tags=["scan"], dependencies=[Depends(require_api_key)])
async def scan_callback(payload: ScanRequest, session: AsyncSession = Depends(get_session)) -> ScanResponse:
    service = ScanService(session)
    result = await service.handle_scan(
        fingerprint_b64=payload.fingerprint_b64,
        signature_hex=payload.signature_hex,
        timestamp=payload.timestamp,
        nonce=payload.nonce,
        device_id=payload.device_id,
        client_meta=payload.client_meta,
    )

    return ScanResponse(invoice_id=UUID(result.invoice.id), status=result.invoice.status.value, status_changed=result.status_changed)


@app.get("/v1/invoices/{invoice_id}", response_model=InvoiceStatusResponse, tags=["invoices"], dependencies=[Depends(require_api_key)])
async def get_invoice(invoice_id: UUID, session: AsyncSession = Depends(get_session)) -> InvoiceStatusResponse:
    stmt = select(Invoice).where(Invoice.id == str(invoice_id)).limit(1)
    result = await session.execute(stmt)
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return InvoiceStatusResponse(
        invoice_id=UUID(invoice.id),
        status=invoice.status.value,
        policy=PolicyEnum(invoice.policy.value),
        amount=invoice.amount,
        currency=invoice.currency,
        merchant_id=invoice.merchant_id,
    )


@app.post(
    "/v1/invoices/{invoice_id}/confirm",
    response_model=ConfirmResponse,
    tags=["invoices"],
    dependencies=[Depends(require_api_key)],
)
async def confirm_invoice(invoice_id: UUID, payload: ConfirmRequest, session: AsyncSession = Depends(get_session)) -> ConfirmResponse:
    stmt = select(Invoice).where(Invoice.id == str(invoice_id)).limit(1)
    result = await session.execute(stmt)
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if payload.action == "SUCCESS":
        invoice.status = InvoiceStatus.SUCCESS
    else:
        invoice.status = InvoiceStatus.REJECTED

    await session.commit()
    await session.refresh(invoice)

    return ConfirmResponse(invoice_id=UUID(invoice.id), status=invoice.status.value)

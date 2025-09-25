"""Database models and session utilities."""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .config import settings


class Base(DeclarativeBase):
    pass


class InvoiceStatus(str, enum.Enum):
    CREATED = "CREATED"
    SCANNED = "SCANNED"
    SUCCESS = "SUCCESS"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class InvoicePolicy(str, enum.Enum):
    FAST = "FAST"
    SAFE = "SAFE"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    merchant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="IDR")
    status: Mapped[InvoiceStatus] = mapped_column(SqlEnum(InvoiceStatus), default=InvoiceStatus.CREATED)
    policy: Mapped[InvoicePolicy] = mapped_column(SqlEnum(InvoicePolicy), default=InvoicePolicy.SAFE)
    merchant_payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    fingerprint: Mapped["Fingerprint"] = relationship(back_populates="invoice", uselist=False)
    scan_events: Mapped[list["ScanEvent"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")


class Fingerprint(Base):
    __tablename__ = "fingerprints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), unique=True)
    fp_b64: Mapped[str] = mapped_column(Text, nullable=False)
    sig_hex: Mapped[str] = mapped_column(Text, nullable=False)
    ts: Mapped[int] = mapped_column(Integer, nullable=False)
    nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    ttl_sec: Mapped[int] = mapped_column(Integer, nullable=False)

    invoice: Mapped[Invoice] = relationship(back_populates="fingerprint")


class ScanEvent(Base):
    __tablename__ = "scan_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"))
    device_id: Mapped[str | None] = mapped_column(String(64))
    client_meta: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    invoice: Mapped[Invoice] = relationship(back_populates="scan_events")


engine = create_async_engine(settings.database_url, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Provide AsyncSession for FastAPI dependency."""

    async with SessionLocal() as session:
        yield session


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

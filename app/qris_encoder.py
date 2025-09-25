"""QRIS payload encoder with Tag 62 fingerprint embedding."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .crc import crc16_ccitt
from .tlv import TLVItem, build_tlv, parse_tlv


@dataclass(frozen=True)
class Tag62Data:
    fingerprint_b64: str
    signature_hex: str
    timestamp: int
    nonce: str
    algorithm: str | None = None

    def to_subitems(self) -> Iterable[TLVItem]:
        yield TLVItem(tag="01", value=self.fingerprint_b64)
        yield TLVItem(tag="02", value=self.signature_hex)
        yield TLVItem(tag="03", value=str(self.timestamp))
        yield TLVItem(tag="04", value=self.nonce)
        if self.algorithm:
            yield TLVItem(tag="05", value=self.algorithm)


@dataclass(frozen=True)
class EncodedPayload:
    payload: str
    crc: str


def strip_crc(base_payload: str) -> str:
    """Remove Tag 63 (CRC) from an EMV payload if present."""

    items = [item for item in parse_tlv(base_payload)]
    filtered = [item for item in items if item.tag != "63"]
    return build_tlv(filtered)


def inject_tag62(base_payload: str, tag62: Tag62Data) -> EncodedPayload:
    """Attach Tag 62 data and compute CRC16-CCITT."""

    payload_wo_crc = strip_crc(base_payload)
    items = [item for item in parse_tlv(payload_wo_crc) if item.tag != "62"]
    tag62_value = build_tlv(tag62.to_subitems())
    items.append(TLVItem(tag="62", value=tag62_value))
    payload_no_crc = build_tlv(items)
    crc_input = f"{payload_no_crc}6304"
    crc = crc16_ccitt(crc_input)
    final_payload = f"{payload_no_crc}6304{crc}"
    return EncodedPayload(payload=final_payload, crc=crc)

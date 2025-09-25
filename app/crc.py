"""CRC16-CCITT implementation."""
from __future__ import annotations

CRC16_POLY = 0x1021
CRC16_INIT = 0xFFFF


def crc16_ccitt(data: str) -> str:
    """Compute CRC16-CCITT (0x1021) for EMV payload strings."""

    checksum = CRC16_INIT
    for ch in data.encode("utf-8"):
        checksum ^= ch << 8
        for _ in range(8):
            if checksum & 0x8000:
                checksum = (checksum << 1) ^ CRC16_POLY
            else:
                checksum <<= 1
            checksum &= 0xFFFF
    return f"{checksum:04X}"

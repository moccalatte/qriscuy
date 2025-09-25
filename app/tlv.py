"""Utility helpers to build and parse EMV-style TLV payloads."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator


@dataclass(frozen=True)
class TLVItem:
    tag: str
    value: str

    def serialize(self) -> str:
        length = f"{len(self.value):02d}"
        return f"{self.tag}{length}{self.value}"


def build_tlv(items: Iterable[TLVItem]) -> str:
    """Serialize iterable of TLV items into EMV string."""

    return "".join(item.serialize() for item in items)


def parse_tlv(payload: str) -> Iterator[TLVItem]:
    """Parse TLV payload string into TLV items."""

    idx = 0
    total = len(payload)
    while idx + 4 <= total:
        tag = payload[idx : idx + 2]
        length = int(payload[idx + 2 : idx + 4])
        value_start = idx + 4
        value_end = value_start + length
        if value_end > total:
            raise ValueError("Invalid TLV length exceeds payload")
        value = payload[value_start:value_end]
        yield TLVItem(tag=tag, value=value)
        idx = value_end
    if idx != total:
        raise ValueError("Dangling TLV data detected")

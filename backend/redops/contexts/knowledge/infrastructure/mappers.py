"""Row serialisation for the ``SourceRecordStore`` port (SPEC.md section 6).

The durable and process-local adapters share one payload shape so a reload is
re-validated through the ``SourceRecord`` value object rather than trusted as
stored: the locator, checksum, capture time and access rule all round-trip, and
a stored row the value object would reject raises on load instead of being read
back as a real source (SPEC.md section 3).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from redops.contexts.knowledge.domain.entities import SourceRecord


def source_to_payload(source: SourceRecord) -> dict[str, Any]:
    """Serialise an immutable source record."""

    return {
        "source_id": source.source_id,
        "tenant_id": source.tenant_id,
        "locator": source.locator,
        "checksum": source.checksum,
        "captured_on": source.captured_on.isoformat(),
        "access_rule": source.access_rule,
    }


def source_from_payload(payload: dict[str, Any]) -> SourceRecord:
    """Rebuild a source record from a stored payload, re-validating its fields."""

    return SourceRecord(
        source_id=payload["source_id"],
        tenant_id=payload["tenant_id"],
        locator=payload["locator"],
        checksum=payload["checksum"],
        captured_on=date.fromisoformat(payload["captured_on"]),
        access_rule=payload["access_rule"],
    )

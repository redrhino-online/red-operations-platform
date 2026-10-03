"""Row serialisation for the ``MeasurementRegistry`` port (SPEC.md section 6).

The durable and process-local adapters share one payload shape so a reload is
re-validated through the ``MetricDefinition`` and ``MeasurementRecord`` value
objects rather than trusted as stored: the metric identity, funnel step, unit,
direction and version, and the record's window, value, basis, source, sample and
recorded date all round-trip, and a stored row the domain would reject raises on
load instead of being read back as a real registry entry (SPEC.md section 3).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from redops.contexts.measurement.domain.value_objects import (
    MeasurementBasis,
    MeasurementRecord,
    MeasurementWindow,
    MetricDefinition,
    MetricDirection,
    MetricFunnelStep,
    MetricUnit,
)


def metric_to_payload(metric: MetricDefinition) -> dict[str, Any]:
    """Serialise one versioned metric definition."""

    return {
        "metric_id": metric.metric_id,
        "tenant_id": metric.tenant_id,
        "name": metric.name,
        "funnel_step": metric.funnel_step.value,
        "unit": metric.unit.value,
        "direction": metric.direction.value,
        "version": metric.version,
    }


def metric_from_payload(payload: dict[str, Any]) -> MetricDefinition:
    """Rebuild a metric definition from a stored payload, re-validating fields."""

    return MetricDefinition(
        metric_id=payload["metric_id"],
        tenant_id=payload["tenant_id"],
        name=payload["name"],
        funnel_step=MetricFunnelStep(payload["funnel_step"]),
        unit=MetricUnit(payload["unit"]),
        direction=MetricDirection(payload["direction"]),
        version=payload["version"],
    )


def record_to_payload(record: MeasurementRecord) -> dict[str, Any]:
    """Serialise an observation, embedding the exact metric version it attaches to."""

    return {
        "record_id": record.record_id,
        "tenant_id": record.tenant_id,
        "metric": metric_to_payload(record.metric),
        "value": record.value,
        "window_start": record.window.start.isoformat(),
        "window_end": record.window.end.isoformat(),
        "basis": record.basis.value,
        "source": record.source,
        "sample_size": record.sample_size,
        "recorded_on": record.recorded_on.isoformat(),
    }


def record_from_payload(payload: dict[str, Any]) -> MeasurementRecord:
    """Rebuild an observation from a stored payload, re-validating its fields.

    The metric definition, the window and the basis are rebuilt through their
    value objects, so a stored row the domain would reject (for example a record
    written before its window closed) raises on load rather than being read back
    as a real observation (SPEC.md sections 3 and 11).
    """

    return MeasurementRecord(
        record_id=payload["record_id"],
        tenant_id=payload["tenant_id"],
        metric=metric_from_payload(payload["metric"]),
        value=payload["value"],
        window=MeasurementWindow(
            start=date.fromisoformat(payload["window_start"]),
            end=date.fromisoformat(payload["window_end"]),
        ),
        basis=MeasurementBasis(payload["basis"]),
        source=payload["source"],
        sample_size=payload["sample_size"],
        recorded_on=date.fromisoformat(payload["recorded_on"]),
    )

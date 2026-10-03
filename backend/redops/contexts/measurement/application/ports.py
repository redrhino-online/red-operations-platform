"""Application ports for the Measurement bounded context (SPEC.md section 6).

A port is defined by an application need: the ``/measurements`` API surface must
read and write the stage 10 metric registry -- the versioned ``MetricDefinition``
and the ``MeasurementRecord`` observations that attach to it -- without the entry
point reaching into a concrete store. SPEC.md section 3 makes a Measurement a
client resource ("metric definition, window, baseline, observation, source"), so
the port is always scoped by tenant and a blank tenant is refused rather than read
or written unscoped. The adapter is chosen in the composition layer, so the use
case depends on the interface, not a concrete store.
"""

from __future__ import annotations

import abc

from redops.contexts.measurement.domain.value_objects import (
    MeasurementRecord,
    MetricDefinition,
)


class MeasurementRegistry(abc.ABC):
    """Seam for the metric registry, keyed by tenant (SPEC.md sections 3 and 7).

    SPEC.md section 3 keys a Measurement aggregate by its exact metric definition
    and window, and Phase 5 requires a metric registry. ``list_metrics`` and
    ``list_records`` return only the requested tenant's rows; ``save_metric`` and
    ``save_record`` are append-only: an identical replay is idempotent, but a
    same-key re-statement with a different body is refused so a pinned metric
    version or a recorded observation is never silently rewritten. ``close``
    releases any connection the adapter opened.
    """

    @abc.abstractmethod
    def list_metrics(self, tenant_id: str) -> tuple[MetricDefinition, ...]:
        """Return the tenant's metric definitions, ordered by metric then version."""

    @abc.abstractmethod
    def get_metric(
        self, tenant_id: str, metric_id: str, version: int
    ) -> MetricDefinition | None:
        """Return one tenant-scoped metric definition version, or ``None``."""

    @abc.abstractmethod
    def list_records(self, tenant_id: str) -> tuple[MeasurementRecord, ...]:
        """Return the tenant's observations, ordered by recorded then record id."""

    @abc.abstractmethod
    def get_record(
        self, tenant_id: str, record_id: str
    ) -> MeasurementRecord | None:
        """Return one tenant-scoped observation, or ``None`` if unknown."""

    @abc.abstractmethod
    def save_metric(self, metric: MetricDefinition) -> None:
        """Store a metric definition, refusing a different same-key body."""

    @abc.abstractmethod
    def save_record(self, record: MeasurementRecord) -> None:
        """Store an observation, refusing a different same-id body."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""

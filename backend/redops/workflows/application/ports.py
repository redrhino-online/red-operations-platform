"""Application ports for RED durable workflow runs (SPEC.md sections 6 and 7).

A port is defined by an application need. The resume use case must persist and
reload a run without knowing whether the store is a PostgreSQL adapter or an
in-memory test double, and it must perform a step's external effect without
knowing the connector behind it. Both are chosen in the composition layer, so
the use case depends on these interfaces, not concrete adapters.

The run store is tenant scoped on reads (SPEC.md section 9: every tenant
resource and query carries ``tenant_id``), so a run owned by another client is
indistinguishable from a missing one.
"""

from __future__ import annotations

import abc

from redops.workflows.domain.entities import WorkflowRun
from redops.workflows.domain.value_objects import WorkflowStep


class WorkflowRunStore(abc.ABC):
    """Durable storage for workflow runs (SPEC.md section 7)."""

    @abc.abstractmethod
    def save(self, run: WorkflowRun) -> None:
        """Persist the run's current state before any dependent side effect."""

    @abc.abstractmethod
    def get(self, run_id: str, *, tenant_id: str) -> WorkflowRun | None:
        """Return the tenant's run, or ``None`` if it is absent or foreign."""


class WorkflowStepExecutor(abc.ABC):
    """Performs one step's external effect (SPEC.md sections 6 and 7).

    Implementations must be idempotent: a run whose step was interrupted after
    its state was persisted is re-run on resume, so executing the same step
    twice must not create a duplicate external operation (SPEC.md section 11:
    "duplicate delivery creates one external operation"; ADR 0005: "Make
    workflow resumption idempotent").
    """

    @abc.abstractmethod
    def execute(self, run: WorkflowRun, step: WorkflowStep) -> None:
        """Carry out the step's effect for the run."""

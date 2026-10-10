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

from typing import Protocol

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

    @abc.abstractmethod
    def list_resumable(self, *, tenant_id: str) -> tuple[str, ...]:
        """Return the tenant's run ids that have a step due (SPEC.md section 7).

        A background worker must find the in-flight runs to resume, and that
        scan is itself a tenant-scoped query: it returns only the requested
        client's runs, so a worker for one client never sees, reads or advances
        another client's run (SPEC.md section 9: "Test cross client access at
        API, retrieval, background worker, and artifact URL layers"). A run with
        no step due -- pending, awaiting a human approval, completed or failed --
        is not returned, so the worker never commits a waiting approval or
        restarts a terminal run (SPEC.md section 11).
        """

    @abc.abstractmethod
    def list_awaiting_approval(self, *, tenant_id: str) -> tuple[str, ...]:
        """Return the tenant's run ids waiting at a human approval gate (K12).

        SPEC.md section 14 condition 8 binds the pipeline's human gates to RED
        approvals, and the approval experience must surface what is waiting. The
        scan is tenant scoped like ``list_resumable`` (SPEC.md section 9) and
        returns only the runs whose status is ``awaiting_approval``.
        """

    def close(self) -> None:
        """Release any resource the adapter owns for the caller's request.

        A durable adapter holds a connection; a process-local adapter holds
        nothing. The default is a no-op, so the lifecycle concern stays with the
        adapter that needs it rather than leaking into the port's data contract
        (SPEC.md section 6).
        """

        return None


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


class StageGateApprovalPort(Protocol):
    """Whether a stage's RED approval is recorded (K12; SPEC.md section 14).

    A pipeline gate step is bound to the stage gate the canonical template
    defines, and that gate is approved only when the tenant's durable ledger
    holds a passing decision for the stage. The port keeps that check behind a
    seam so the workflow use case never reads the Governance store directly
    (SPEC.md section 6).
    """

    def has_passing_decision(self, *, tenant_id: str, stage_number: int) -> bool:
        """Whether stage ``stage_number`` authorizes downstream use for the tenant."""

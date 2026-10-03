"""Application use cases for RED durable workflow runs (SPEC.md sections 6 and 7).

SPEC.md section 7: "Persist run state before side effects; resume from committed
steps." ADR 0005: "Make workflow resumption idempotent and persist run state
before side effects," and a node restart must resume an in-flight approval wait.

``RunWorkflowHandler`` is the single place that orders persistence and side
effects. It persists the run *before* executing a step, commits the step after,
and re-executes only an interrupted (still ``in_progress``) step on resume, so a
committed step is never repeated and a waiting approval is left for its human.
The use case depends on the ``WorkflowRunStore`` and ``WorkflowStepExecutor``
ports, never on a concrete database or connector (SPEC.md section 6, onion rule).
"""

from __future__ import annotations

from datetime import date

from redops.workflows.application.ports import (
    WorkflowRunStore,
    WorkflowStepExecutor,
)
from redops.workflows.domain.entities import WorkflowRun
from redops.workflows.domain.errors import WorkflowRunNotFoundError
from redops.workflows.domain.value_objects import (
    WorkflowDefinition,
    WorkflowRunStatus,
    WorkflowStepKind,
)

_TERMINAL_OR_WAITING = (
    WorkflowRunStatus.COMPLETED,
    WorkflowRunStatus.FAILED,
    WorkflowRunStatus.AWAITING_APPROVAL,
)


class RunWorkflowHandler:
    """Start, resume and approve durable workflow runs."""

    def __init__(
        self, *, store: WorkflowRunStore, executor: WorkflowStepExecutor
    ) -> None:
        self._store = store
        self._executor = executor

    def start(
        self,
        *,
        definition: WorkflowDefinition,
        tenant_id: str,
        run_id: str,
        actor: str,
        reason: str,
        on: date,
        correlation_id: str,
    ) -> WorkflowRun:
        """Create and advance a new run until it completes or waits for a human.

        The pending run is persisted before the first side effect so a crash
        between creation and the first step is recoverable.
        """
        run = WorkflowRun(run_id=run_id, tenant_id=tenant_id, definition=definition)
        run.start(actor=actor, reason=reason, on=on, correlation_id=correlation_id)
        self._store.save(run)
        return self._advance(
            run, actor=actor, reason=reason, on=on, correlation_id=correlation_id
        )

    def resume(
        self,
        run_id: str,
        *,
        tenant_id: str,
        actor: str,
        reason: str,
        on: date,
        correlation_id: str,
    ) -> WorkflowRun:
        """Reload a run after a restart and continue from its committed steps."""
        run = self._load(run_id, tenant_id=tenant_id)
        return self._advance(
            run, actor=actor, reason=reason, on=on, correlation_id=correlation_id
        )

    def approve(
        self,
        run_id: str,
        *,
        tenant_id: str,
        actor: str,
        reason: str,
        on: date,
        correlation_id: str,
    ) -> WorkflowRun:
        """Commit a waiting approval step and continue the run.

        The approving ``actor`` is a named human passed by the caller; the use
        case never infers or invents an approver (SPEC.md section 4).
        """
        run = self._load(run_id, tenant_id=tenant_id)
        run.approve(actor=actor, reason=reason, on=on, correlation_id=correlation_id)
        self._store.save(run)
        return self._advance(
            run, actor=actor, reason=reason, on=on, correlation_id=correlation_id
        )

    def fail(
        self,
        run_id: str,
        *,
        tenant_id: str,
        reason: str,
        actor: str,
        on: date,
        correlation_id: str,
    ) -> WorkflowRun:
        """Fail a running or waiting run and persist the terminal state."""
        run = self._load(run_id, tenant_id=tenant_id)
        run.fail(reason=reason, actor=actor, on=on, correlation_id=correlation_id)
        self._store.save(run)
        return run

    def _advance(
        self,
        run: WorkflowRun,
        *,
        actor: str,
        reason: str,
        on: date,
        correlation_id: str,
    ) -> WorkflowRun:
        if run.status in _TERMINAL_OR_WAITING:
            return run

        if run.in_progress_step is not None:
            interrupted = run.resume_step()
            if interrupted is not None:
                self._executor.execute(run, interrupted)
                run.commit_step(
                    actor=actor, reason=reason, on=on, correlation_id=correlation_id
                )
                self._store.save(run)

        while run.status is WorkflowRunStatus.RUNNING:
            step = run.next_step
            if step is None:
                break
            if step.kind is WorkflowStepKind.APPROVAL:
                run.await_approval(
                    actor=actor, reason=reason, on=on, correlation_id=correlation_id
                )
                self._store.save(run)
                return run
            run.begin_step(
                actor=actor, reason=reason, on=on, correlation_id=correlation_id
            )
            self._store.save(run)
            self._executor.execute(run, step)
            run.commit_step(
                actor=actor, reason=reason, on=on, correlation_id=correlation_id
            )
            self._store.save(run)
        return run

    def _load(self, run_id: str, *, tenant_id: str) -> WorkflowRun:
        run = self._store.get(run_id, tenant_id=tenant_id)
        if run is None:
            raise WorkflowRunNotFoundError(
                f"workflow run {run_id!r} is not visible to tenant {tenant_id!r}"
            )
        return run

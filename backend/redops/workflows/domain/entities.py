"""The durable workflow run entity (SPEC.md section 7, ADR 0005).

A ``WorkflowRun`` is one execution of a versioned ``WorkflowDefinition``. It
pins the definition it started on, so a newer published version never changes an
in-flight run (SPEC.md section 10). It advances strictly one step at a time and
records its state, so a worker that restarts can reload the run and resume from
the committed steps without repeating committed side effects.

The entity is pure: it performs no I/O and depends on no web, ORM, queue or
vendor code (SPEC.md section 6, onion rule). Persisting the run *before* a side
effect and re-running an interrupted step idempotently is the application use
case's job (ADR 0005); the entity only exposes the durable state and the
begin/commit/await/approve transitions that make that possible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from redops.workflows.domain.errors import (
    InvalidWorkflowDefinitionError,
    WorkflowStepOrderError,
)
from redops.workflows.domain.policies import WorkflowTransitionPolicy
from redops.workflows.domain.value_objects import (
    WorkflowDefinition,
    WorkflowRunStatus,
    WorkflowRunTransition,
    WorkflowStep,
    WorkflowStepKind,
)

_TERMINAL = (WorkflowRunStatus.COMPLETED, WorkflowRunStatus.FAILED)


@dataclass
class WorkflowRun:
    """One durable execution of a versioned workflow definition."""

    run_id: str
    tenant_id: str
    definition: WorkflowDefinition
    status: WorkflowRunStatus = WorkflowRunStatus.PENDING
    completed_steps: tuple[str, ...] = ()
    in_progress_step: str | None = None
    pending_approval: str | None = None
    failure_reason: str | None = None
    _transitions: list[WorkflowRunTransition] = field(
        default_factory=list, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, str) or not self.run_id.strip():
            raise InvalidWorkflowDefinitionError("a workflow run id is required")
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise InvalidWorkflowDefinitionError("a workflow run tenant id is required")
        if not isinstance(self.definition, WorkflowDefinition):
            raise InvalidWorkflowDefinitionError(
                "a workflow run requires a WorkflowDefinition"
            )
        names = self.definition.step_names
        if not isinstance(self.completed_steps, tuple):
            raise InvalidWorkflowDefinitionError(
                "workflow run completed steps must be a tuple"
            )
        if len(self.completed_steps) > len(names):
            raise InvalidWorkflowDefinitionError(
                "workflow run has more completed steps than its definition has"
            )
        if self.completed_steps != names[: len(self.completed_steps)]:
            raise InvalidWorkflowDefinitionError(
                "workflow run completed steps must be the definition's leading "
                "steps in order"
            )
        current = names[len(self.completed_steps)] if len(self.completed_steps) < len(names) else None
        if self.in_progress_step is not None:
            if self.in_progress_step != current:
                raise InvalidWorkflowDefinitionError(
                    "a workflow run's in-progress step must be its next step"
                )
            if self.status is not WorkflowRunStatus.RUNNING:
                raise InvalidWorkflowDefinitionError(
                    "a workflow run may only have an in-progress step while running"
                )
        if self.pending_approval is not None:
            if self.pending_approval != current:
                raise InvalidWorkflowDefinitionError(
                    "a workflow run's pending approval must be its next step"
                )
            if self.status is not WorkflowRunStatus.AWAITING_APPROVAL:
                raise InvalidWorkflowDefinitionError(
                    "a workflow run may only await approval while awaiting approval"
                )
        if self.status is WorkflowRunStatus.COMPLETED:
            if len(self.completed_steps) != len(names):
                raise InvalidWorkflowDefinitionError(
                    "a completed workflow run has not committed every step"
                )
            if self.in_progress_step is not None or self.pending_approval is not None:
                raise InvalidWorkflowDefinitionError(
                    "a completed workflow run has no open step"
                )
        if self.status is WorkflowRunStatus.AWAITING_APPROVAL and self.pending_approval is None:
            raise InvalidWorkflowDefinitionError(
                "a workflow run awaiting approval must name the pending step"
            )
        if self.status is WorkflowRunStatus.FAILED:
            if not isinstance(self.failure_reason, str) or not self.failure_reason.strip():
                raise InvalidWorkflowDefinitionError(
                    "a failed workflow run requires a failure reason"
                )

    @property
    def transitions(self) -> tuple[WorkflowRunTransition, ...]:
        return tuple(self._transitions)

    @property
    def is_terminal(self) -> bool:
        return self.status in _TERMINAL

    @property
    def next_step(self) -> WorkflowStep | None:
        """The definition step the run has not committed, or ``None`` if done."""
        if len(self.completed_steps) >= len(self.definition.steps):
            return None
        return self.definition.step_at(len(self.completed_steps))

    def restore_history(
        self, transitions: tuple[WorkflowRunTransition, ...]
    ) -> None:
        """Restore a persisted transition log on rehydration (SPEC.md section 4)."""
        self._transitions = list(transitions)

    def start(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> None:
        """Move a pending run to running. Illegal from any other status."""
        self._transition(
            WorkflowRunStatus.RUNNING,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def begin_step(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> WorkflowStep:
        """Mark the next task step in progress so the side effect is preceded by durable state.

        The caller persists the run after this call and before executing the
        step's side effect, so a crash leaves the run with ``in_progress_step``
        set and the step is re-run idempotently on resume (ADR 0005).
        """
        if self.status is not WorkflowRunStatus.RUNNING:
            raise WorkflowStepOrderError(
                "only a running workflow can begin a step"
            )
        if self.in_progress_step is not None:
            raise WorkflowStepOrderError(
                f"workflow step {self.in_progress_step!r} is already in progress"
            )
        step = self.next_step
        if step is None:
            raise WorkflowStepOrderError("the workflow run has no step to begin")
        if step.kind is WorkflowStepKind.APPROVAL:
            raise WorkflowStepOrderError(
                f"workflow step {step.name!r} is an approval and must wait for a human"
            )
        self.in_progress_step = step.name
        return step

    def commit_step(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> WorkflowStep:
        """Commit the in-progress step and advance to the next step.

        Committing only the step that is in progress makes resumption
        idempotent: a committed step is never re-run, and the run completes only
        when its final step commits.
        """
        if self.status is not WorkflowRunStatus.RUNNING:
            raise WorkflowStepOrderError(
                "only a running workflow can commit a step"
            )
        if self.in_progress_step is None:
            raise WorkflowStepOrderError("the workflow run has no step in progress")
        step = self.next_step
        if step is None or step.name != self.in_progress_step:
            raise WorkflowStepOrderError(
                "the workflow run can only commit its in-progress step"
            )
        self.completed_steps = self.completed_steps + (step.name,)
        self.in_progress_step = None
        if len(self.completed_steps) == len(self.definition.steps):
            self._transition(
                WorkflowRunStatus.COMPLETED,
                actor=actor,
                reason=reason,
                on=on,
                correlation_id=correlation_id,
            )
        return step

    def await_approval(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> WorkflowStep:
        """Persist the run waiting on its next approval step (ADR 0005)."""
        if self.status is not WorkflowRunStatus.RUNNING:
            raise WorkflowStepOrderError(
                "only a running workflow can await approval"
            )
        step = self.next_step
        if step is None or step.kind is not WorkflowStepKind.APPROVAL:
            raise WorkflowStepOrderError(
                "the workflow run's next step is not an approval"
            )
        self.pending_approval = step.name
        self._transition(
            WorkflowRunStatus.AWAITING_APPROVAL,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )
        return step

    def approve(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> WorkflowStep:
        """Commit the pending approval step and resume the run.

        The human actor is recorded, never inferred; the entity cannot approve
        on its own (SPEC.md section 4).
        """
        if self.status is not WorkflowRunStatus.AWAITING_APPROVAL:
            raise WorkflowStepOrderError(
                "only a workflow awaiting approval can be approved"
            )
        step = self.next_step
        if step is None or step.name != self.pending_approval:
            raise WorkflowStepOrderError(
                "the workflow run has no pending approval to commit"
            )
        self.completed_steps = self.completed_steps + (step.name,)
        self.pending_approval = None
        if len(self.completed_steps) == len(self.definition.steps):
            self._transition(
                WorkflowRunStatus.COMPLETED,
                actor=actor,
                reason=reason,
                on=on,
                correlation_id=correlation_id,
            )
        else:
            self._transition(
                WorkflowRunStatus.RUNNING,
                actor=actor,
                reason=reason,
                on=on,
                correlation_id=correlation_id,
            )
        return step

    def fail(
        self, *, reason: str, actor: str, on: date, correlation_id: str
    ) -> None:
        """Move a running or waiting run to failed with a reason."""
        if not isinstance(reason, str) or not reason.strip():
            raise WorkflowStepOrderError("failing a workflow run requires a reason")
        if self.status not in (WorkflowRunStatus.RUNNING, WorkflowRunStatus.AWAITING_APPROVAL):
            raise WorkflowStepOrderError(
                "only a running or waiting workflow can fail"
            )
        self.failure_reason = reason
        self._transition(
            WorkflowRunStatus.FAILED,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def resume_step(self) -> WorkflowStep | None:
        """The step a restarting worker should act on, or ``None`` if none is due.

        A completed or failed run is terminal. A run awaiting approval is
        preserved for the human and returns ``None`` (SPEC.md section 11:
        "restarting worker preserves a waiting workflow"). An interrupted task
        returns that same step so it is re-run idempotently rather than skipped.
        """
        if self.status in _TERMINAL or self.status is WorkflowRunStatus.AWAITING_APPROVAL:
            return None
        if self.status is WorkflowRunStatus.PENDING:
            return None
        if self.in_progress_step is not None:
            return self.definition.step_at(
                self.definition.index_of(self.in_progress_step)
            )
        return self.next_step

    def _transition(
        self,
        target: WorkflowRunStatus,
        *,
        actor: str,
        reason: str,
        on: date,
        correlation_id: str,
    ) -> None:
        previous = self.status
        WorkflowTransitionPolicy().require(previous, target)
        self.status = target
        self._transitions.append(
            WorkflowRunTransition(
                actor=actor,
                reason=reason,
                occurred_at=on,
                old_status=previous,
                new_status=target,
                correlation_id=correlation_id,
            )
        )

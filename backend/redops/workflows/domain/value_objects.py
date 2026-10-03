"""Value objects for RED durable workflow runs (SPEC.md section 7, ADR 0005).

SPEC.md section 7: "Workflow definition includes version, typed inputs, steps,
gate requirements, retry and timeout policy, output schema, and rollback or
compensation." A ``WorkflowDefinition`` is the immutable, versioned, ordered
step list; a ``WorkflowStep`` is a task or a human approval gate. Pinning the
version on the definition means an in-flight run keeps the definition it started
on when a newer version is published (SPEC.md section 10).

``WorkflowRunStatus`` is the run lifecycle. ``WorkflowRunTransition`` records the
actor, reason, timestamp, old and new status and correlation id of each status
change, so a run's history is reconstructible after a restart (SPEC.md sections
4 and 7).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from redops.workflows.domain.errors import (
    InvalidWorkflowDefinitionError,
    UnknownWorkflowStepError,
)


class WorkflowStepKind(Enum):
    """Whether a step runs a task or waits for a human approval.

    A ``TASK`` step has an external side effect the run performs idempotently.
    An ``APPROVAL`` step is a human gate: the run waits in ``AWAITING_APPROVAL``
    and a named human, not the worker, advances it (SPEC.md section 4: an agent
    cannot confer human approval upon itself).
    """

    TASK = "task"
    APPROVAL = "approval"


class WorkflowRunStatus(Enum):
    """Lifecycle of a durable workflow run (SPEC.md section 7)."""

    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class WorkflowStep:
    """One ordered step of a workflow definition."""

    name: str
    kind: WorkflowStepKind = WorkflowStepKind.TASK

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise InvalidWorkflowDefinitionError("a workflow step name is required")
        if not isinstance(self.kind, WorkflowStepKind):
            raise InvalidWorkflowDefinitionError(
                f"workflow step {self.name!r} kind must be a WorkflowStepKind"
            )


@dataclass(frozen=True)
class WorkflowDefinition:
    """A versioned, ordered, immutable workflow definition (SPEC.md section 7)."""

    definition_id: str
    version: str
    steps: tuple[WorkflowStep, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("id", self.definition_id),
            ("version", self.version),
        ):
            if not isinstance(value, str) or not value.strip():
                raise InvalidWorkflowDefinitionError(
                    f"workflow definition {label} is required"
                )
        if not isinstance(self.steps, tuple) or not self.steps:
            raise InvalidWorkflowDefinitionError(
                "a workflow definition requires at least one step"
            )
        names = [step.name for step in self.steps]
        if len(set(names)) != len(names):
            raise InvalidWorkflowDefinitionError(
                "a workflow definition cannot repeat a step name"
            )

    @property
    def step_names(self) -> tuple[str, ...]:
        return tuple(step.name for step in self.steps)

    def step_at(self, index: int) -> WorkflowStep:
        if not isinstance(index, int) or index < 0 or index >= len(self.steps):
            raise UnknownWorkflowStepError(
                f"workflow step index {index!r} is out of range"
            )
        return self.steps[index]

    def index_of(self, name: str) -> int:
        for index, step in enumerate(self.steps):
            if step.name == name:
                return index
        raise UnknownWorkflowStepError(
            f"workflow definition {self.definition_id!r} has no step {name!r}"
        )


@dataclass(frozen=True)
class WorkflowRunTransition:
    """One recorded status change on a run (SPEC.md section 4)."""

    actor: str
    reason: str
    occurred_at: date
    old_status: WorkflowRunStatus
    new_status: WorkflowRunStatus
    correlation_id: str

    def __post_init__(self) -> None:
        for label, value in (
            ("actor", self.actor),
            ("reason", self.reason),
            ("correlation id", self.correlation_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise InvalidWorkflowDefinitionError(
                    f"a workflow run transition {label} is required"
                )
        if not isinstance(self.old_status, WorkflowRunStatus) or not isinstance(
            self.new_status, WorkflowRunStatus
        ):
            raise InvalidWorkflowDefinitionError(
                "a workflow run transition status must be a WorkflowRunStatus"
            )

"""Named domain errors for RED durable workflow runs (pure domain).

SPEC.md section 4: "Reject illegal transitions rather than silently coercing
state." SPEC.md section 7 requires a run to resume from committed steps, so a
request to act on a step out of order, or on a run whose status forbids the
action, is refused with a named error instead of mutating durable state.
"""

from __future__ import annotations


class WorkflowError(Exception):
    """Base class for durable workflow run rule violations."""


class InvalidWorkflowDefinitionError(WorkflowError, ValueError):
    """A workflow definition is missing a required field or repeats a step.

    A definition without an id or version cannot be pinned, and a definition
    without steps cannot run. Repeating a step name would make a persisted
    committed-step list ambiguous, so the definition refuses it up front.
    """


class UnknownWorkflowStepError(WorkflowError, ValueError):
    """A step named by a caller is not in the run's pinned definition.

    An in-flight run keeps the definition version it started on (SPEC.md
    section 10), so a step the pinned definition does not name is refused
    rather than resolved against some other version.
    """


class WorkflowStepOrderError(WorkflowError):
    """A run tried to act on a step other than its next committed step.

    SPEC.md section 7: "resume from committed steps." Acting on an arbitrary
    step would let a caller skip or repeat work, so only the run's current step
    may be begun, committed or approved.
    """


class IllegalWorkflowTransitionError(WorkflowError):
    """A run status change is not legal from the run's current status.

    The run is a state machine (SPEC.md section 4); an illegal transition is
    rejected instead of coerced, so a completed or failed run can never be
    silently restarted or a pending run advanced.
    """


class WorkflowRunNotFoundError(WorkflowError):
    """A tenant-scoped run lookup found no run (SPEC.md section 9).

    Run lookups are tenant scoped, so a run owned by another client is
    indistinguishable from a missing run and never leaks its existence.
    """

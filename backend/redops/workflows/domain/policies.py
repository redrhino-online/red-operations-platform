"""Composable policy for legal workflow run transitions (SPEC.md section 4).

SPEC.md section 4: "Reject illegal transitions rather than silently coercing
state." The policy is a small, pure table so the run entity stays a state
machine and the rule is testable on its own.
"""

from __future__ import annotations

from redops.workflows.domain.errors import IllegalWorkflowTransitionError
from redops.workflows.domain.value_objects import WorkflowRunStatus

_PENDING = WorkflowRunStatus.PENDING
_RUNNING = WorkflowRunStatus.RUNNING
_AWAITING = WorkflowRunStatus.AWAITING_APPROVAL
_COMPLETED = WorkflowRunStatus.COMPLETED
_FAILED = WorkflowRunStatus.FAILED


class WorkflowTransitionPolicy:
    """Refuses any run status change that is not on the legal transition table."""

    _ALLOWED = frozenset(
        {
            (_PENDING, _RUNNING),
            (_RUNNING, _AWAITING),
            (_RUNNING, _COMPLETED),
            (_RUNNING, _FAILED),
            (_AWAITING, _RUNNING),
            (_AWAITING, _COMPLETED),
            (_AWAITING, _FAILED),
        }
    )

    def require(
        self, previous: WorkflowRunStatus, target: WorkflowRunStatus
    ) -> None:
        if (previous, target) not in self._ALLOWED:
            raise IllegalWorkflowTransitionError(
                "a workflow run cannot move from "
                f"{previous.value!r} to {target.value!r}"
            )

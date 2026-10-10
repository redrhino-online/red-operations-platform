"""Composable policy for legal workflow run transitions (SPEC.md section 4).

SPEC.md section 4: "Reject illegal transitions rather than silently coercing
state." The policy is a small, pure table so the run entity stays a state
machine and the rule is testable on its own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

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


@dataclass(frozen=True)
class GateStepBinding:
    """The stage a pipeline gate step is bound to (K12; SPEC.md section 14).

    The stage 0-10 pipeline definition names every gate step ``gate-<stage>``
    (K11), so the binding is derivable from the step name and the run's pending
    gate maps to exactly one stage of the canonical template. A step that is not
    a pipeline gate binds to nothing and keeps the generic approval behavior.
    """

    stage_number: int

    @classmethod
    def from_step_name(cls, name: str) -> "GateStepBinding | None":
        match = re.fullmatch(r"gate-(\d+)", name.strip())
        return cls(stage_number=int(match.group(1))) if match else None

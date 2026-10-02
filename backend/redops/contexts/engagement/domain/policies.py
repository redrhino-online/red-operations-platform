"""Lifecycle policy for the Engagement bounded context (pure domain).

SPEC.md section 4 names the engagement summary states and requires illegal
transitions to be rejected rather than silently coerced. The canonical
progression is forward-only, one step at a time; a workspace may pause from an
active state and resume to the state it paused from, and a completed workspace is
terminal.
"""

from __future__ import annotations

from redops.contexts.engagement.domain.errors import IllegalLifecycleTransitionError
from redops.contexts.engagement.domain.value_objects import (
    CANONICAL_PROGRESSION,
    EngagementLifecycle,
)


class WorkspaceLifecyclePolicy:
    """Evaluates whether an engagement lifecycle transition is legal."""

    def can_advance(
        self, current: EngagementLifecycle, target: EngagementLifecycle
    ) -> bool:
        if current.is_terminal or current is EngagementLifecycle.PAUSED:
            return False
        if target is EngagementLifecycle.PAUSED:
            return False
        if target is EngagementLifecycle.COMPLETED:
            return current in {
                EngagementLifecycle.OPTIMIZATION,
                EngagementLifecycle.EXPANSION,
            }
        if target.is_terminal:
            return False
        try:
            current_index = CANONICAL_PROGRESSION.index(current)
            target_index = CANONICAL_PROGRESSION.index(target)
        except ValueError:
            return False
        return target_index == current_index + 1

    def require_advance(
        self, current: EngagementLifecycle, target: EngagementLifecycle
    ) -> None:
        if not self.can_advance(current, target):
            raise IllegalLifecycleTransitionError(
                f"engagement cannot advance from {current.value!r} to "
                f"{target.value!r}"
            )

    def require_pause(self, current: EngagementLifecycle) -> None:
        if not current.is_active:
            raise IllegalLifecycleTransitionError(
                f"engagement in {current.value!r} cannot be paused"
            )

    def require_resume(self, current: EngagementLifecycle) -> None:
        if current is not EngagementLifecycle.PAUSED:
            raise IllegalLifecycleTransitionError(
                f"engagement in {current.value!r} is not paused and cannot resume"
            )

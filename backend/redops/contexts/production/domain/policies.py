"""Build lifecycle policy for the Production bounded context (pure domain).

Encodes SPEC.md section 3: a BuildObject moves through its lifecycle states and
illegal transitions are rejected rather than silently coerced.
"""

from __future__ import annotations

from typing import Mapping

from redops.contexts.production.domain.errors import IllegalBuildTransitionError
from redops.contexts.production.domain.value_objects import BuildState


class BuildTransitionPolicy:
    """Legal BuildObject state transitions (SPEC.md sections 3 and 4)."""

    ALLOWED: Mapping[BuildState, frozenset[BuildState]] = {
        BuildState.IDENTIFIED: frozenset(
            {
                BuildState.SOURCE_REQUIRED,
                BuildState.READY,
                BuildState.SUPERSEDED,
                BuildState.ARCHIVED,
            }
        ),
        BuildState.SOURCE_REQUIRED: frozenset(
            {BuildState.READY, BuildState.SUPERSEDED, BuildState.ARCHIVED}
        ),
        BuildState.READY: frozenset(
            {
                BuildState.IN_DEVELOPMENT,
                BuildState.SUPERSEDED,
                BuildState.ARCHIVED,
            }
        ),
        BuildState.IN_DEVELOPMENT: frozenset(
            {
                BuildState.INTERNAL_REVIEW,
                BuildState.CHANGES_REQUIRED,
                BuildState.SUPERSEDED,
                BuildState.ARCHIVED,
            }
        ),
        BuildState.INTERNAL_REVIEW: frozenset(
            {
                BuildState.CLIENT_REVIEW,
                BuildState.CHANGES_REQUIRED,
                BuildState.APPROVED,
                BuildState.SUPERSEDED,
                BuildState.ARCHIVED,
            }
        ),
        BuildState.CLIENT_REVIEW: frozenset(
            {
                BuildState.CHANGES_REQUIRED,
                BuildState.APPROVED,
                BuildState.SUPERSEDED,
                BuildState.ARCHIVED,
            }
        ),
        BuildState.CHANGES_REQUIRED: frozenset(
            {
                BuildState.IN_DEVELOPMENT,
                BuildState.READY,
                BuildState.SUPERSEDED,
                BuildState.ARCHIVED,
            }
        ),
        BuildState.APPROVED: frozenset(
            {
                BuildState.PRODUCTION_READY,
                BuildState.SUPERSEDED,
                BuildState.ARCHIVED,
            }
        ),
        BuildState.PRODUCTION_READY: frozenset(
            {BuildState.DEPLOYED, BuildState.SUPERSEDED, BuildState.ARCHIVED}
        ),
        BuildState.DEPLOYED: frozenset(
            {BuildState.MEASURING, BuildState.SUPERSEDED, BuildState.ARCHIVED}
        ),
        BuildState.MEASURING: frozenset(
            {BuildState.OPTIMIZING, BuildState.SUPERSEDED, BuildState.ARCHIVED}
        ),
        BuildState.OPTIMIZING: frozenset(
            {BuildState.MEASURING, BuildState.SUPERSEDED, BuildState.ARCHIVED}
        ),
        BuildState.SUPERSEDED: frozenset({BuildState.ARCHIVED}),
        BuildState.ARCHIVED: frozenset(),
    }

    def can_transition(self, current: BuildState, target: BuildState) -> bool:
        return target in self.ALLOWED.get(current, frozenset())

    def require(self, current: BuildState, target: BuildState) -> None:
        if not self.can_transition(current, target):
            raise IllegalBuildTransitionError(
                f"cannot transition build from {current.value!r} to {target.value!r}"
            )

"""Aggregates for the Production bounded context (pure domain).

BuildObject is the unit of production work (SPEC.md section 3). Its invariant is
that an active build always has an owner and a next action, so the command
center can always answer who is accountable and what happens next.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from redops.contexts.production.domain.errors import InvalidBuildError
from redops.contexts.production.domain.value_objects import BuildState, BuildTransition


def _require_text(value: str, label: str) -> str:
    if not value or not value.strip():
        raise InvalidBuildError(f"{label} is required")
    return value


@dataclass
class BuildObject:
    """One unit of production work with a lifecycle and a named owner.

    Required fields come from the SPEC.md section 3 aggregate table: type,
    purpose, audience, state, owner, next action, blockers and refs. An active
    build (any state other than Superseded or Archived) must have an owner and a
    next action. Every state change is recorded with actor, reason, timestamp,
    old and new state, and a correlation ID; illegal transitions are rejected
    rather than silently coerced.
    """

    build_id: str
    build_type: str
    purpose: str
    audience: str
    owner: str
    next_action: str
    state: BuildState = BuildState.IDENTIFIED
    blockers: frozenset[str] = field(default_factory=frozenset)
    refs: frozenset[str] = field(default_factory=frozenset)
    _transitions: list[BuildTransition] = field(
        default_factory=list, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        _require_text(self.build_id, "build id")
        _require_text(self.build_type, "build type")
        _require_text(self.purpose, "build purpose")
        _require_text(self.audience, "build audience")
        _require_text(self.owner, "build owner")
        if self.is_active:
            _require_text(self.next_action, "build next action")

    @property
    def is_active(self) -> bool:
        return not self.state.is_terminal

    @property
    def is_blocked(self) -> bool:
        return bool(self.blockers)

    @property
    def transitions(self) -> tuple[BuildTransition, ...]:
        return tuple(self._transitions)

    def add_blocker(self, blocker: str) -> None:
        _require_text(blocker, "blocker")
        self.blockers = self.blockers | {blocker}

    def remove_blocker(self, blocker: str) -> None:
        self.blockers = self.blockers - {blocker}

    def reassign_owner(self, owner: str) -> None:
        self.owner = _require_text(owner, "build owner")

    def set_next_action(self, next_action: str) -> None:
        if self.is_active:
            self.next_action = _require_text(next_action, "build next action")
        else:
            self.next_action = next_action

    def require_source(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> BuildTransition:
        return self._transition(
            BuildState.SOURCE_REQUIRED,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def mark_ready(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> BuildTransition:
        return self._transition(
            BuildState.READY,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def start_development(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> BuildTransition:
        return self._transition(
            BuildState.IN_DEVELOPMENT,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def submit_for_internal_review(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> BuildTransition:
        return self._transition(
            BuildState.INTERNAL_REVIEW,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def submit_for_client_review(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> BuildTransition:
        return self._transition(
            BuildState.CLIENT_REVIEW,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def request_changes(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> BuildTransition:
        return self._transition(
            BuildState.CHANGES_REQUIRED,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def approve(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> BuildTransition:
        return self._transition(
            BuildState.APPROVED,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def mark_production_ready(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> BuildTransition:
        return self._transition(
            BuildState.PRODUCTION_READY,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def deploy(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> BuildTransition:
        return self._transition(
            BuildState.DEPLOYED,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def start_measuring(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> BuildTransition:
        return self._transition(
            BuildState.MEASURING,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def start_optimizing(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> BuildTransition:
        return self._transition(
            BuildState.OPTIMIZING,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def supersede(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> BuildTransition:
        return self._transition(
            BuildState.SUPERSEDED,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def archive(
        self, *, actor: str, reason: str, on: date, correlation_id: str
    ) -> BuildTransition:
        return self._transition(
            BuildState.ARCHIVED,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def _transition(
        self,
        target: BuildState,
        *,
        actor: str,
        reason: str,
        on: date,
        correlation_id: str,
    ) -> BuildTransition:
        from redops.contexts.production.domain.policies import BuildTransitionPolicy

        previous = self.state
        BuildTransitionPolicy().require(previous, target)
        self.state = target
        if target.is_terminal:
            self.next_action = ""
        transition = BuildTransition(
            actor=actor,
            reason=reason,
            occurred_at=on,
            old_state=previous,
            new_state=target,
            correlation_id=correlation_id,
        )
        self._transitions.append(transition)
        return transition

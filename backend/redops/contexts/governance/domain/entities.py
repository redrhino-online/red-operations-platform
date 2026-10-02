"""Aggregates for the Governance bounded context (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from redops.contexts.governance.domain.errors import (
    ApprovalAuthorityError,
    ApprovalExpiredError,
    SelfApprovalError,
)
from redops.contexts.governance.domain.value_objects import (
    ApprovalOutcome,
    AssetVersionRef,
    GateState,
    Waiver,
)


@dataclass
class StageGate:
    """A gate on one production stage (0-10).

    A gate authorizes downstream work only when it is Approved and every required
    exact asset version is present and approved. A waiver never substitutes for
    an absent asset, and dependencies are enforced by GateIntegrityPolicy.
    """

    stage_number: int
    template_version: str
    required_assets: frozenset[AssetVersionRef]
    dependencies: frozenset[int] = field(default_factory=frozenset)
    approved_assets: frozenset[AssetVersionRef] = field(default_factory=frozenset)
    state: GateState = GateState.NOT_STARTED
    proposed_by: str | None = None
    approver: str | None = None
    waiver: Waiver | None = None

    def missing_assets(self) -> frozenset[AssetVersionRef]:
        return frozenset(self.required_assets - self.approved_assets)

    def authorizes_downstream(self) -> bool:
        return self.state is GateState.APPROVED and not self.missing_assets()


@dataclass(frozen=True)
class Decision:
    """An append-only governance decision record (SPEC.md section 3).

    A decision names its subject, the exact affected version, the choice, the
    actor, the timestamp and the rationale. It is never edited or deleted; a
    new decision supersedes an earlier one by being appended alongside it.
    """

    subject: str
    choice: str
    rationale: str
    actor: str
    decided_on: date
    affected_version: AssetVersionRef | None = None

    def __post_init__(self) -> None:
        if not self.subject or not self.subject.strip():
            raise ValueError("decision subject is required")
        if not self.choice or not self.choice.strip():
            raise ValueError("decision choice is required")
        if not self.rationale or not self.rationale.strip():
            raise ValueError("decision rationale is required")
        if not self.actor or not self.actor.strip():
            raise ValueError("decision actor is required")


class DecisionLog:
    """Append-only history of governance decisions.

    The log exposes no update or delete operation by design: decision history
    is append only. Reads return immutable tuples so callers cannot mutate the
    stored history.
    """

    def __init__(self) -> None:
        self._entries: list[Decision] = []

    def record(self, decision: Decision) -> None:
        self._entries.append(decision)

    @property
    def entries(self) -> tuple[Decision, ...]:
        return tuple(self._entries)

    def for_subject(self, subject: str) -> tuple[Decision, ...]:
        return tuple(entry for entry in self._entries if entry.subject == subject)


@dataclass
class ApprovalRequest:
    """A version-specific request for a designated human approval.

    Approval pins one exact asset version and one intended downstream scope.
    The requester can never be the approver, and only the designated approver
    can decide. An approval authorizes exactly the version and scope it pins,
    until it expires or is superseded (SPEC.md sections 3, 4 and 11).
    """

    asset: AssetVersionRef
    scope: str
    requested_by: str
    approver: str
    outcome: ApprovalOutcome = ApprovalOutcome.PENDING
    expires_on: date | None = None

    def __post_init__(self) -> None:
        if not self.scope or not self.scope.strip():
            raise ValueError("approval scope is required")
        if not self.requested_by or not self.requested_by.strip():
            raise ValueError("approval requester is required")
        if not self.approver or not self.approver.strip():
            raise ValueError("approval approver is required")
        if self.approver == self.requested_by:
            raise SelfApprovalError("author cannot be the designated approver")

    def is_expired(self, on: date) -> bool:
        return self.expires_on is not None and on > self.expires_on

    def authorizes(self, asset: AssetVersionRef, scope: str, on: date) -> bool:
        return (
            self.outcome is ApprovalOutcome.APPROVED
            and self.asset == asset
            and self.scope == scope
            and not self.is_expired(on)
        )

    def approve(self, *, actor: str, on: date, rationale: str = "approved") -> Decision:
        if actor != self.approver:
            raise ApprovalAuthorityError(
                f"{actor!r} is not the designated approver {self.approver!r}"
            )
        if self.is_expired(on):
            raise ApprovalExpiredError("approval request has expired")
        self.outcome = ApprovalOutcome.APPROVED
        return self._decision(ApprovalOutcome.APPROVED, actor, on, rationale)

    def reject(self, *, actor: str, on: date, rationale: str) -> Decision:
        if actor != self.approver:
            raise ApprovalAuthorityError(
                f"{actor!r} is not the designated approver {self.approver!r}"
            )
        self.outcome = ApprovalOutcome.REJECTED
        return self._decision(ApprovalOutcome.REJECTED, actor, on, rationale)

    def supersede(
        self,
        *,
        actor: str,
        on: date,
        rationale: str,
        log: DecisionLog | None = None,
    ) -> Decision:
        self.outcome = ApprovalOutcome.SUPERSEDED
        decision = self._decision(ApprovalOutcome.SUPERSEDED, actor, on, rationale)
        if log is not None:
            log.record(decision)
        return decision

    def _decision(
        self,
        outcome: ApprovalOutcome,
        actor: str,
        on: date,
        rationale: str,
    ) -> Decision:
        return Decision(
            subject=self.asset.asset_id,
            choice=outcome.value,
            rationale=rationale,
            actor=actor,
            decided_on=on,
            affected_version=self.asset,
        )

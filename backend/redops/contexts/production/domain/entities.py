"""Aggregates for the Production bounded context (pure domain).

BuildObject is the unit of production work (SPEC.md section 3). Its invariant is
that an active build always has an owner and a next action, so the command
center can always answer who is accountable and what happens next.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from typing import TYPE_CHECKING, Iterable

from redops.contexts.commercial.domain.entities import CampaignMessage
from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.production.domain.errors import (
    AuthorityAmplifierApprovalOrderError,
    AuthorityAmplifierDependencyError,
    InvalidAuthorityAmplifierError,
    InvalidBuildError,
)
from redops.contexts.production.domain.value_objects import (
    SCRIPT_SECTION_ORDER,
    AmplifierApproval,
    AuthorityAmplifierState,
    BuildState,
    BuildTransition,
    ScriptSection,
    VisualProductionPackage,
)

if TYPE_CHECKING:
    from redops.contexts.method.domain.entities import MethodVersion


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

    SPEC.md section 3 also makes every child resource belong to exactly one
    client and section 9 requires ``tenant_id`` on every tenant resource, so a
    build carries its client tenant and cannot be stored or read unscoped.
    """

    build_id: str
    tenant_id: str
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
        _require_text(self.tenant_id, "build tenant id")
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


@dataclass(frozen=True)
class AuthorityAmplifier:
    """The stage 7 Authority Amplifier, approved at "Authority Amplifier Approved".

    SPEC.md section 4, stage 7 "Produce": the required asset package is the
    approved script in Promise, Proof, Problems, Steps, Context, Action order,
    plus the storyboard, brand treatment, presentation, speaker notes, recording,
    edited and hosted video and player assets. Stage 7 has two distinct
    approvals: the script and its supported claims pass review before any visual
    or video production (Phase 4 TDD example: "visual Authority Amplifier
    production cannot be authorized by an unapproved script"), and final creative
    acceptance is separate.

    The amplifier is grounded on the approved stage 6 `CampaignMessage` and the
    method's claims (SPEC.md section 3: production requires approved
    dependencies), so unsupported proof is flagged. It is frozen: approval pins
    an exact asset rather than mutating it, and an upstream change returns it to
    review required.
    """

    amplifier_id: str
    tenant_id: str
    message: CampaignMessage
    owner: str
    script: tuple[ScriptSection, ...]
    proof_claim_ids: frozenset[str]
    visuals: VisualProductionPackage | None = field(default=None)
    script_approval: AmplifierApproval | None = field(default=None)
    creative_approval: AmplifierApproval | None = field(default=None)
    state: AuthorityAmplifierState = AuthorityAmplifierState.DRAFT
    review_reason: str | None = field(default=None)

    def __post_init__(self) -> None:
        for label, value in (
            ("authority amplifier id", self.amplifier_id),
            ("authority amplifier tenant id", self.tenant_id),
            ("authority amplifier owner", self.owner),
        ):
            if not value or not value.strip():
                raise InvalidAuthorityAmplifierError(f"{label} is required")
        if self.message.tenant_id != self.tenant_id:
            raise AuthorityAmplifierDependencyError(
                "an authority amplifier cannot be grounded on another tenant's "
                "message"
            )
        self._require_canonical_script()
        if not self.proof_claim_ids:
            raise InvalidAuthorityAmplifierError(
                "an authority amplifier requires at least one proof claim"
            )

    def _require_canonical_script(self) -> None:
        if len(self.script) != len(SCRIPT_SECTION_ORDER):
            raise InvalidAuthorityAmplifierError(
                "the authority amplifier script requires every section in "
                "Promise, Proof, Problems, Steps, Context, Action order"
            )
        for expected, section in zip(SCRIPT_SECTION_ORDER, self.script):
            if section.kind is not expected:
                raise InvalidAuthorityAmplifierError(
                    "the authority amplifier script must be in Promise, Proof, "
                    "Problems, Steps, Context, Action order"
                )

    @property
    def is_script_approved(self) -> bool:
        return self.script_approval is not None

    @property
    def is_approved(self) -> bool:
        return self.creative_approval is not None

    @property
    def is_terminal(self) -> bool:
        return self.state.is_terminal

    def approve_script(
        self,
        *,
        approved_by: str,
        intended_use: str,
        on: date,
        approved_methods: Iterable["MethodVersion"],
        claims: Iterable[Claim],
    ) -> "AuthorityAmplifier":
        """Return a script-approved amplifier once its proof is supported.

        SPEC.md section 4, stage 7: the script and its supported claims pass
        review before visual or video production. The message must be approved
        and the method an approved dependency, and every proof claim must be a
        claim of the approved method backed by a known, directly sourced
        knowledge claim (Phase 4 TDD example: "unsupported proof is flagged").
        """
        from redops.contexts.production.domain.policies import (
            AuthorityAmplifierPolicy,
        )

        AuthorityAmplifierPolicy().require_script_approvable(
            self, approved_methods, claims
        )
        return replace(
            self,
            state=AuthorityAmplifierState.SCRIPT_APPROVED,
            script_approval=AmplifierApproval(
                approved_by=approved_by,
                intended_use=intended_use,
                approved_on=on,
            ),
            review_reason=None,
        )

    def produce_visuals(
        self, *, package: VisualProductionPackage
    ) -> "AuthorityAmplifier":
        """Attach the visual package once the script is approved.

        Visual or video production cannot be authorized by an unapproved script
        (SPEC.md section 4, stage 7 and Phase 4 TDD example "visual Authority
        Amplifier production cannot be authorized by an unapproved script").
        """
        if self.script_approval is None:
            raise AuthorityAmplifierApprovalOrderError(
                f"authority amplifier {self.amplifier_id!r} cannot produce "
                "visuals before its script is approved"
            )
        return replace(self, visuals=package)

    def approve_creative(
        self, *, approved_by: str, intended_use: str, on: date
    ) -> "AuthorityAmplifier":
        """Return the final creative acceptance, which is separate from script.

        SPEC.md section 4, stage 7: final creative acceptance requires the
        complete visual and video package and the earlier script approval, so
        script approval alone never completes the gate.
        """
        if self.script_approval is None:
            raise AuthorityAmplifierApprovalOrderError(
                f"authority amplifier {self.amplifier_id!r} cannot receive "
                "creative acceptance before its script is approved"
            )
        if self.visuals is None:
            raise AuthorityAmplifierDependencyError(
                f"authority amplifier {self.amplifier_id!r} cannot receive "
                "creative acceptance without its stage 7 visual package"
            )
        return replace(
            self,
            state=AuthorityAmplifierState.APPROVED,
            creative_approval=AmplifierApproval(
                approved_by=approved_by,
                intended_use=intended_use,
                approved_on=on,
            ),
            review_reason=None,
        )

    def mark_review_required(self, *, reason: str) -> "AuthorityAmplifier":
        """Return this amplifier marked review required after a change upstream.

        SPEC.md section 4: changing an approved upstream method or message marks
        dependent assets review required. An approved amplifier loses that
        approval until reviewed again, and a terminal amplifier stays terminal.
        """
        if not reason or not reason.strip():
            raise InvalidAuthorityAmplifierError(
                "authority amplifier review reason is required"
            )
        if self.state.is_terminal:
            raise InvalidAuthorityAmplifierError(
                "a terminal authority amplifier cannot be marked review required"
            )
        return replace(
            self,
            state=AuthorityAmplifierState.REVIEW_REQUIRED,
            review_reason=reason,
        )

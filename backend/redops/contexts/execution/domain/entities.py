"""Aggregates for the Execution bounded context (pure domain).

FunnelIntegration is the stage 8 funnel integration, completed at the "Funnel
Complete" checkpoint (SPEC.md section 4). Its invariant is that the funnel is
grounded on the approved stage 7 Authority Amplifier and that it only becomes
complete after a test prospect completes the capture, engagement and conversion
handoffs with reliable records and ownership.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from redops.contexts.execution.domain.errors import (
    FunnelDependencyError,
    InvalidFunnelError,
    InvalidLaunchQAError,
    LaunchQAAuthorityError,
    LaunchQADependencyError,
)
from redops.contexts.execution.domain.value_objects import (
    FunnelAssetPackage,
    FunnelState,
    LaunchQAState,
    ProspectPathDryRun,
    QACheck,
    TrafficAuthorization,
)
from redops.contexts.production.domain.entities import AuthorityAmplifier


@dataclass(frozen=True)
class FunnelIntegration:
    """The stage 8 funnel integration, approved at "Funnel Complete".

    SPEC.md section 4, stage 8 "Integrate": the required asset package is the
    campaign architecture, pages, forms, qualification, booking, sequences, CRM,
    tags, automation, analytics, tracking, sales handoff and SOPs. The "Funnel
    Complete" checkpoint requires a test prospect to complete capture, engagement
    and conversion handoffs with reliable records and ownership.

    The funnel is grounded on the approved stage 7 `AuthorityAmplifier` (SPEC.md
    section 3: production requires approved dependencies), so a funnel cannot be
    completed on an amplifier that has not received creative acceptance. It is
    frozen: completion pins an exact asset and the dry run evidence rather than
    mutating them, and an upstream change returns it to review required.
    """

    integration_id: str
    tenant_id: str
    amplifier: AuthorityAmplifier
    owner: str
    assets: FunnelAssetPackage
    state: FunnelState = FunnelState.DRAFT
    dry_run: ProspectPathDryRun | None = field(default=None)
    review_reason: str | None = field(default=None)

    def __post_init__(self) -> None:
        for label, value in (
            ("funnel integration id", self.integration_id),
            ("funnel integration tenant id", self.tenant_id),
            ("funnel integration owner", self.owner),
        ):
            if not value or not value.strip():
                raise InvalidFunnelError(f"{label} is required")
        if self.amplifier.tenant_id != self.tenant_id:
            raise FunnelDependencyError(
                "a funnel cannot be grounded on another tenant's authority "
                "amplifier"
            )
        if self.dry_run is not None and self.dry_run.tenant_id != self.tenant_id:
            raise FunnelDependencyError(
                "a funnel cannot pin another tenant's prospect path dry run"
            )

    @property
    def is_complete(self) -> bool:
        return self.state is FunnelState.COMPLETE

    @property
    def is_terminal(self) -> bool:
        return self.state.is_terminal

    def mark_funnel_complete(
        self, dry_run: ProspectPathDryRun
    ) -> "FunnelIntegration":
        """Return a complete funnel once the stage 8 checkpoint passes.

        SPEC.md section 4, stage 8: the "Funnel Complete" checkpoint requires the
        approved stage 7 dependency and a test prospect that completes capture,
        engagement and conversion handoffs with reliable records and ownership. A
        failed or missing handoff prevents completion (Phase 4 TDD example:
        "failed prospect routing prevents Funnel Complete"). The dry run evidence
        is pinned so completion is traceable to the observed prospect path.
        """
        from redops.contexts.execution.domain.policies import (
            FunnelCompletionPolicy,
        )

        FunnelCompletionPolicy().require(self, dry_run)
        return replace(
            self,
            state=FunnelState.COMPLETE,
            dry_run=dry_run,
            review_reason=None,
        )

    def mark_review_required(self, *, reason: str) -> "FunnelIntegration":
        """Return this funnel marked review required after a change upstream.

        SPEC.md section 4: changing an approved upstream asset marks dependent
        assets review required. A complete funnel loses that completion until the
        dependency is reviewed again, and a terminal funnel stays terminal.
        """
        if not reason or not reason.strip():
            raise InvalidFunnelError("funnel review reason is required")
        if self.state.is_terminal:
            raise InvalidFunnelError(
                "a terminal funnel cannot be marked review required"
            )
        return replace(
            self, state=FunnelState.REVIEW_REQUIRED, review_reason=reason
        )


@dataclass(frozen=True)
class LaunchQA:
    """The stage 9 launch QA, approved at "Launch Approved".

    SPEC.md section 4, stage 9 "QA": all critical path checks pass, exceptions
    have owners, and the designated human authorizes traffic. The QA is grounded
    on the completed stage 8 `FunnelIntegration` (SPEC.md section 3: production
    requires approved dependencies), so traffic cannot be authorized on a funnel
    that has not passed "Funnel Complete". Stage 9 reports READY_FOR_TRAFFIC, not
    live or completed, so the aggregate pins the authorization rather than
    claiming traffic has begun. It is frozen: approval pins the exact evidence
    and an upstream change returns it to review required.
    """

    qa_id: str
    tenant_id: str
    funnel: FunnelIntegration
    owner: str
    designated_authority: str
    checks: tuple[QACheck, ...]
    state: LaunchQAState = LaunchQAState.DRAFT
    authorization: TrafficAuthorization | None = field(default=None)
    review_reason: str | None = field(default=None)

    def __post_init__(self) -> None:
        for label, value in (
            ("launch QA id", self.qa_id),
            ("launch QA tenant id", self.tenant_id),
            ("launch QA owner", self.owner),
            ("launch QA designated authority", self.designated_authority),
        ):
            if not value or not value.strip():
                raise InvalidLaunchQAError(f"{label} is required")
        if self.funnel.tenant_id != self.tenant_id:
            raise LaunchQADependencyError(
                "a launch QA cannot be grounded on another tenant's funnel"
            )
        if self.designated_authority == self.owner:
            raise LaunchQAAuthorityError(
                "the launch QA owner cannot also be the designated human "
                "authority that authorizes traffic"
            )
        kinds = [check.kind for check in self.checks]
        if len(kinds) != len(set(kinds)):
            raise InvalidLaunchQAError(
                "a launch QA records each check at most once"
            )

    @property
    def is_ready_for_traffic(self) -> bool:
        return self.state is LaunchQAState.READY_FOR_TRAFFIC

    @property
    def is_terminal(self) -> bool:
        return self.state.is_terminal

    def authorize_traffic(
        self, *, authorization: TrafficAuthorization
    ) -> "LaunchQA":
        """Return a ready-for-traffic QA once the stage 9 checkpoint passes.

        SPEC.md section 4, stage 9: the "Launch Approved" checkpoint requires all
        critical path checks to pass, exceptions to have owners, and the
        designated human authority to authorize traffic. A failed critical path
        check, an incomplete funnel, or a non-designated authorizer prevents
        readiness (Phase 4 TDD example: "failed message, technical or commercial
        QA prevents Launch Approved"). The authorization is pinned so readiness
        is traceable to the human decision; it does not assert live traffic.
        """
        from redops.contexts.execution.domain.policies import (
            LaunchApprovedPolicy,
        )

        LaunchApprovedPolicy().require(self, authorization)
        return replace(
            self,
            state=LaunchQAState.READY_FOR_TRAFFIC,
            authorization=authorization,
            review_reason=None,
        )

    def mark_review_required(self, *, reason: str) -> "LaunchQA":
        """Return this QA marked review required after a change upstream.

        SPEC.md section 4: changing an approved upstream asset marks dependent
        assets review required. A ready QA loses that readiness until the
        dependency is reviewed again, and a terminal QA stays terminal.
        """
        if not reason or not reason.strip():
            raise InvalidLaunchQAError("launch QA review reason is required")
        if self.state.is_terminal:
            raise InvalidLaunchQAError(
                "a terminal launch QA cannot be marked review required"
            )
        return replace(
            self, state=LaunchQAState.REVIEW_REQUIRED, review_reason=reason
        )

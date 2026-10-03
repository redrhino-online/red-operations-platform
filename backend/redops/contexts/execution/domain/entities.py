"""Aggregates for the Execution bounded context (pure domain).

FunnelIntegration is the stage 8 funnel integration, completed at the "Funnel
Complete" checkpoint (SPEC.md section 4). Its invariant is that the funnel is
grounded on the approved stage 7 Authority Amplifier and that it only becomes
complete after a test prospect completes the capture, engagement and conversion
handoffs with reliable records and ownership.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date

from redops.contexts.execution.domain.errors import (
    FunnelDependencyError,
    InvalidFunnelError,
    InvalidLaunchQAError,
    InvalidPerformanceBaselineError,
    LaunchQAAuthorityError,
    LaunchQADependencyError,
    PerformanceBaselineDependencyError,
)
from redops.contexts.execution.domain.value_objects import (
    CompliancePackage,
    FunnelAssetPackage,
    FunnelState,
    MILESTONE_ORDER,
    LaunchAssetPackage,
    LaunchQAState,
    MilestoneObservation,
    PerformanceBaselineState,
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
    compliance: CompliancePackage | None = field(default=None)

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
        if self.compliance is not None and (
            self.compliance.tenant_id != self.tenant_id
        ):
            raise LaunchQADependencyError(
                "a launch QA cannot pin another tenant's compliance package"
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
        if (
            self.state is LaunchQAState.READY_FOR_TRAFFIC
            and self.compliance is None
        ):
            raise InvalidLaunchQAError(
                "a ready-for-traffic launch QA must pin its reviewed compliance "
                "package; a missing compliance asset prevents launch approval"
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
        QA prevents Launch Approved"). SPEC.md section 4 also requires "consent
        where applicable", so the reviewed compliance and consent package must be
        present and complete, or a scoped human waiver must cover each absent
        asset, before traffic is authorized (canon files 21 and 34 inform the
        compliance asset set). The authorization is pinned so readiness is
        traceable to the human decision; it does not assert live traffic.
        """
        from redops.contexts.execution.domain.policies import (
            ComplianceRequiredPolicy,
            LaunchApprovedPolicy,
        )

        LaunchApprovedPolicy().require(self, authorization)
        ComplianceRequiredPolicy().require(
            self, on=authorization.authorized_on
        )
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


@dataclass(frozen=True)
class PerformanceBaseline:
    """The stage 10 performance baseline (SPEC.md section 4).

    SPEC.md section 4, stage 10 "Launch": the required asset package is the live
    campaign, spend and lead records, conversion and engagement measures,
    applications, bookings, shows, closes, acquisition cost, attribution and
    issue log. The "Performance Baseline Established" checkpoint treats first
    qualified traffic and the subsequent lead, appointment and sale as distinct
    observed milestones, with missing observations shown as pending.

    The baseline is grounded on the stage 9 `LaunchQA` that authorizes traffic
    (SPEC.md section 3: production requires approved dependencies). Campaign
    activation alone therefore does not establish a baseline: the stage 9
    authorization must exist and first qualified traffic must be observed before
    the checkpoint passes (Phase 5 TDD example: "launch alone cannot complete the
    engagement"). It is frozen, so an established baseline pins the exact
    observations and an upstream change returns it to review required.
    """

    baseline_id: str
    tenant_id: str
    launch_qa: LaunchQA
    owner: str
    assets: LaunchAssetPackage
    milestones: tuple[MilestoneObservation, ...]
    state: PerformanceBaselineState = PerformanceBaselineState.DRAFT
    established_on: date | None = field(default=None)
    review_reason: str | None = field(default=None)

    def __post_init__(self) -> None:
        for label, value in (
            ("performance baseline id", self.baseline_id),
            ("performance baseline tenant id", self.tenant_id),
            ("performance baseline owner", self.owner),
        ):
            if not value or not value.strip():
                raise InvalidPerformanceBaselineError(f"{label} is required")
        if self.launch_qa.tenant_id != self.tenant_id:
            raise PerformanceBaselineDependencyError(
                "a performance baseline cannot be grounded on another tenant's "
                "launch QA"
            )
        for observation in self.milestones:
            if observation.tenant_id != self.tenant_id:
                raise PerformanceBaselineDependencyError(
                    "a performance baseline cannot record another tenant's "
                    "milestone observation"
                )
        kinds = [observation.kind for observation in self.milestones]
        if len(kinds) != len(set(kinds)):
            raise InvalidPerformanceBaselineError(
                "a performance baseline records each milestone at most once"
            )

    @property
    def observed_kinds(self) -> frozenset:
        return frozenset(
            observation.kind
            for observation in self.milestones
            if observation.is_observed
        )

    @property
    def pending_kinds(self) -> frozenset:
        return frozenset(
            observation.kind
            for observation in self.milestones
            if not observation.is_observed
        )

    @property
    def missing_kinds(self) -> frozenset:
        present = frozenset(observation.kind for observation in self.milestones)
        return frozenset(MILESTONE_ORDER) - present

    @property
    def is_established(self) -> bool:
        return self.state is PerformanceBaselineState.ESTABLISHED

    @property
    def is_terminal(self) -> bool:
        return self.state.is_terminal

    def establish(self, *, on: date) -> "PerformanceBaseline":
        """Return an established baseline once the stage 10 checkpoint passes.

        SPEC.md section 4, stage 10: the "Performance Baseline Established"
        checkpoint requires the stage 9 authorization and an observed first
        qualified traffic milestone. Later milestones may be pending. An absent
        milestone is refused rather than omitted, so missing observations remain
        visible as pending (Phase 5 TDD example: "launch alone cannot complete the
        engagement"). The observations are pinned so the baseline is traceable to
        what was actually observed.
        """
        from redops.contexts.execution.domain.policies import (
            PerformanceBaselinePolicy,
        )

        PerformanceBaselinePolicy().require(self, on)
        return replace(
            self,
            state=PerformanceBaselineState.ESTABLISHED,
            established_on=on,
            review_reason=None,
        )

    def mark_review_required(self, *, reason: str) -> "PerformanceBaseline":
        """Return this baseline marked review required after a change upstream.

        SPEC.md section 4: changing an approved upstream asset marks dependent
        assets review required. An established baseline loses that establishment
        until the dependency is reviewed again, and a terminal baseline stays
        terminal.
        """
        if not reason or not reason.strip():
            raise InvalidPerformanceBaselineError(
                "performance baseline review reason is required"
            )
        if self.state.is_terminal:
            raise InvalidPerformanceBaselineError(
                "a terminal performance baseline cannot be marked review required"
            )
        return replace(
            self,
            state=PerformanceBaselineState.REVIEW_REQUIRED,
            review_reason=reason,
        )

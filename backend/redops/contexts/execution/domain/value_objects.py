"""Value objects for the Execution bounded context (pure domain).

SPEC.md section 4, stage 8 "Integrate" defines the required asset package
(campaign architecture, pages, forms, qualification, booking, sequences, CRM,
tags, automation, analytics, tracking, sales handoff and SOPs) and the "Funnel
Complete" checkpoint: a test prospect completes capture, engagement and
conversion handoffs with reliable records and ownership.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING

from redops.contexts.execution.domain.errors import (
    FunnelIntegrationPackageTenantBoundaryError,
    InvalidFunnelError,
    InvalidFunnelIntegrationPackageError,
    InvalidLaunchQAError,
    InvalidLaunchQAPackageError,
    InvalidPerformanceBaselineError,
    InvalidPerformanceClaimError,
    LaunchQAPackageTenantBoundaryError,
)
from redops.contexts.governance.domain.value_objects import StageAssetVersion

if TYPE_CHECKING:
    from redops.contexts.execution.domain.entities import (
        FunnelIntegration,
        LaunchQA,
    )


class FunnelState(Enum):
    """Readiness of the stage 8 funnel integration (SPEC.md sections 3 and 4).

    A DRAFT funnel only becomes COMPLETE when the prospect path dry run passes
    the "Funnel Complete" checkpoint. An upstream change returns it to
    REVIEW_REQUIRED. Superseded and Archived are terminal.
    """

    DRAFT = "draft"
    COMPLETE = "complete"
    REVIEW_REQUIRED = "review_required"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"

    @property
    def is_terminal(self) -> bool:
        return self in _TERMINAL_FUNNEL_STATES


_TERMINAL_FUNNEL_STATES = frozenset(
    {FunnelState.SUPERSEDED, FunnelState.ARCHIVED}
)


class HandoffKind(Enum):
    """The prospect path handoffs that must complete (SPEC.md section 4).

    The "Funnel Complete" checkpoint names three: capture, engagement and
    conversion.
    """

    CAPTURE = "capture"
    ENGAGEMENT = "engagement"
    CONVERSION = "conversion"


HANDOFF_ORDER: tuple[HandoffKind, ...] = (
    HandoffKind.CAPTURE,
    HandoffKind.ENGAGEMENT,
    HandoffKind.CONVERSION,
)


class HandoffOutcome(Enum):
    """Whether a prospect path handoff routed or failed for the test prospect."""

    ROUTED = "routed"
    FAILED = "failed"


@dataclass(frozen=True)
class FunnelAssetPackage:
    """The stage 8 required asset package (SPEC.md section 4, stage 8).

    SPEC.md section 4, stage 8 "Integrate": the required asset package is the
    campaign architecture, pages, forms, qualification, booking, sequences, CRM,
    tags, automation, analytics, tracking, sales handoff and SOPs. The package is
    frozen and reject-only, so a missing artifact cannot be represented as a
    completed stage 8 deliverable.
    """

    campaign_architecture: str
    pages: str
    forms: str
    qualification: str
    booking: str
    sequences: str
    crm: str
    tags: str
    automation: str
    analytics: str
    tracking: str
    sales_handoff: str
    sops: str

    def __post_init__(self) -> None:
        for label, value in (
            ("campaign architecture", self.campaign_architecture),
            ("pages", self.pages),
            ("forms", self.forms),
            ("qualification", self.qualification),
            ("booking", self.booking),
            ("sequences", self.sequences),
            ("crm", self.crm),
            ("tags", self.tags),
            ("automation", self.automation),
            ("analytics", self.analytics),
            ("tracking", self.tracking),
            ("sales handoff", self.sales_handoff),
            ("SOPs", self.sops),
        ):
            if not value or not value.strip():
                raise InvalidFunnelError(
                    f"funnel asset package {label} is required"
                )


CANONICAL_FUNNEL_KINDS: tuple[str, ...] = (
    "campaign-architecture",
    "pages",
    "forms",
    "qualification",
    "booking",
    "sequences",
    "crm",
    "tags",
    "automation",
    "analytics",
    "tracking",
    "sales-handoff",
    "sops",
)


@dataclass(frozen=True)
class FunnelIntegrationPackage:
    """The reviewed stage 8 funnel, projected to the thirteen canonical gate kinds.

    SPEC.md section 4, stage 8 "Integrate" and its "Funnel Complete" checkpoint:
    a stage is complete only when its required assets exist, pass the checkpoint
    and receive approval for downstream use, and a passing gate pins the exact
    evidence. The required asset package is the campaign architecture, pages,
    forms, qualification, booking, sequences, CRM, tags, automation, analytics,
    tracking, sales handoff and SOPs. The Execution context reviews that as one
    rich ``FunnelIntegration`` (the thirteen assets belong to the same funnel,
    grounded on the approved stage 7 amplifier and a same-tenant prospect path dry
    run); this package is the bridge to the governance gate, which pins one exact
    ``StageAssetVersion`` per canonical kind.

    The canon (SPEC.md section 12.3: stage 8 uses canon files 13, 14, 21 and 22)
    describes a minimum-viable CAC funnel of opt-in, amplifier, scheduling and
    confirmation pages wired to a CRM and scheduling tool, with PAG
    (pixel/audience/goal) tracking installed on every page. ``FunnelIntegration``
    already enforces the same-tenant approved amplifier and dry run at
    construction and completion, so each canonical kind is projected from the
    single reviewed funnel at one positive integer version.

    A ``FunnelIntegration`` only owns its completed evidence once
    ``mark_funnel_complete`` passes the checkpoint, so this package refuses a
    funnel that has not reached ``FunnelState.COMPLETE``: thirteen kinds cannot be
    pinned as this client's evidence without a funnel whose capture, engagement
    and conversion handoffs actually routed (SPEC.md section 4). It also refuses a
    blank identity, a versionless funnel or a cross-tenant funnel rather than
    silently pinning inexact or foreign evidence (SPEC.md sections 3 and 4).
    """

    package_id: str
    tenant_id: str
    funnel: "FunnelIntegration"
    funnel_version: int

    def __post_init__(self) -> None:
        for label, value in (
            ("funnel integration package id", self.package_id),
            ("funnel integration package tenant id", self.tenant_id),
        ):
            if not value or not value.strip():
                raise InvalidFunnelIntegrationPackageError(
                    f"{label} is required"
                )
        if self.funnel.tenant_id != self.tenant_id:
            raise FunnelIntegrationPackageTenantBoundaryError(
                f"stage 8 funnel {self.funnel.integration_id!r} belongs to "
                f"tenant {self.funnel.tenant_id!r}, not package tenant "
                f"{self.tenant_id!r}"
            )
        if not isinstance(self.funnel_version, int) or self.funnel_version < 1:
            raise InvalidFunnelIntegrationPackageError(
                "the funnel integration version must be a positive integer so "
                "the stage 8 gate can pin the reviewed asset at an exact version"
            )
        if not self.funnel.is_complete:
            raise InvalidFunnelIntegrationPackageError(
                f"stage 8 funnel {self.funnel.integration_id!r} has not passed "
                "Funnel Complete, so its thirteen asset kinds cannot be pinned "
                "as exact evidence"
            )

    @property
    def kinds(self) -> frozenset[str]:
        """The canonical kinds the reviewed stage 8 funnel projects onto."""
        return frozenset(CANONICAL_FUNNEL_KINDS)

    def missing_kinds(self) -> tuple[str, ...]:
        """Canonical stage 8 kinds not covered by the projected funnel."""
        covered = {asset.kind for asset in self.stage_asset_versions()}
        return tuple(
            kind for kind in CANONICAL_FUNNEL_KINDS if kind not in covered
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_kinds()

    def stage_asset_versions(self) -> tuple[StageAssetVersion, ...]:
        """Project the reviewed stage 8 funnel onto exact governance evidence.

        Every canonical kind belongs to the same reviewed ``FunnelIntegration``,
        so each is pinned to that funnel's identity at its exact version.
        Governance still pins each projection for the workspace tenant, so a
        cross-client funnel is refused rather than silently authorized (SPEC.md
        sections 3, 4 and 11).
        """
        return tuple(
            StageAssetVersion(
                asset_id=self.funnel.integration_id,
                tenant_id=self.tenant_id,
                kind=kind,
                version=self.funnel_version,
            )
            for kind in CANONICAL_FUNNEL_KINDS
        )


@dataclass(frozen=True)
class HandoffRecord:
    """One recorded capture, engagement or conversion handoff for a test prospect.

    SPEC.md section 4, stage 8: the "Funnel Complete" checkpoint requires the
    handoffs to complete with reliable records and ownership. A routed handoff
    therefore needs both a reliable record reference and a named owner; a failed
    handoff is still recorded against an owner so the failure is attributable.
    """

    kind: HandoffKind
    outcome: HandoffOutcome
    tenant_id: str
    record_id: str
    owner: str
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.tenant_id or not self.tenant_id.strip():
            raise InvalidFunnelError("handoff tenant id is required")
        if not self.owner or not self.owner.strip():
            raise InvalidFunnelError("handoff owner is required")
        if self.outcome is HandoffOutcome.ROUTED and (
            not self.record_id or not self.record_id.strip()
        ):
            raise InvalidFunnelError(
                "a routed handoff requires a reliable record reference"
            )

    @property
    def is_routed(self) -> bool:
        return self.outcome is HandoffOutcome.ROUTED


@dataclass(frozen=True)
class ProspectPathDryRun:
    """A test prospect's run through the stage 8 funnel path (SPEC.md section 4).

    The dry run records the capture, engagement and conversion handoffs. It is
    complete only when every canonical handoff is present exactly once and all
    routed, so a failed or missing routing step leaves the path incomplete
    (Phase 4 TDD example: "failed prospect routing prevents Funnel Complete").
    """

    dry_run_id: str
    tenant_id: str
    handoffs: tuple[HandoffRecord, ...]

    def __post_init__(self) -> None:
        if not self.dry_run_id or not self.dry_run_id.strip():
            raise InvalidFunnelError("prospect path dry run id is required")
        if not self.tenant_id or not self.tenant_id.strip():
            raise InvalidFunnelError("prospect path dry run tenant id is required")
        kinds = [record.kind for record in self.handoffs]
        if len(kinds) != len(set(kinds)):
            raise InvalidFunnelError(
                "a prospect path dry run records each handoff at most once"
            )

    @property
    def completed_kinds(self) -> frozenset[HandoffKind]:
        return frozenset(
            record.kind for record in self.handoffs if record.is_routed
        )

    @property
    def failed_kinds(self) -> frozenset[HandoffKind]:
        return frozenset(
            record.kind
            for record in self.handoffs
            if not record.is_routed
        )

    @property
    def missing_kinds(self) -> frozenset[HandoffKind]:
        present = frozenset(record.kind for record in self.handoffs)
        return frozenset(HANDOFF_ORDER) - present

    @property
    def is_complete(self) -> bool:
        return self.completed_kinds == frozenset(HANDOFF_ORDER)


class LaunchQAState(Enum):
    """Readiness of the stage 9 launch QA (SPEC.md section 4).

    A DRAFT QA only becomes READY_FOR_TRAFFIC when the "Launch Approved"
    checkpoint passes. READY_FOR_TRAFFIC is an authorization to begin traffic,
    explicitly not evidence that traffic is live: live observation is a stage 10
    milestone (SPEC.md section 4, stage 9 "shows Ready for Traffic, not live or
    completed"). An upstream change returns it to REVIEW_REQUIRED; Superseded and
    Archived are terminal.
    """

    DRAFT = "draft"
    READY_FOR_TRAFFIC = "ready_for_traffic"
    REVIEW_REQUIRED = "review_required"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"

    @property
    def is_terminal(self) -> bool:
        return self in _TERMINAL_LAUNCH_STATES


_TERMINAL_LAUNCH_STATES = frozenset(
    {LaunchQAState.SUPERSEDED, LaunchQAState.ARCHIVED}
)


class QACheckKind(Enum):
    """The stage 9 launch QA checks (SPEC.md section 4, stage 9).

    SPEC.md section 4, stage 9 "QA": the recorded message; technical and
    commercial tests on desktop and mobile; forms, CRM, email, automation,
    booking, tracking, payment when relevant, handoff, client approval, budget,
    creative, dashboard and the launch decision. Payment is only relevant to some
    offers and the dashboard is a reporting view, so those are not on the
    critical path and may be explicitly excepted with an owner.
    """

    RECORDED_MESSAGE = "recorded_message"
    TECHNICAL_DESKTOP = "technical_desktop"
    TECHNICAL_MOBILE = "technical_mobile"
    COMMERCIAL_DESKTOP = "commercial_desktop"
    COMMERCIAL_MOBILE = "commercial_mobile"
    FORMS = "forms"
    CRM = "crm"
    EMAIL = "email"
    AUTOMATION = "automation"
    BOOKING = "booking"
    TRACKING = "tracking"
    PAYMENT = "payment"
    SALES_HANDOFF = "sales_handoff"
    CLIENT_APPROVAL = "client_approval"
    BUDGET = "budget"
    CREATIVE = "creative"
    DASHBOARD = "dashboard"
    LAUNCH_DECISION = "launch_decision"

    @property
    def is_critical_path(self) -> bool:
        return self not in _NON_CRITICAL_QA_CHECKS


QA_CHECK_ORDER: tuple[QACheckKind, ...] = tuple(QACheckKind)

_NON_CRITICAL_QA_CHECKS = frozenset(
    {QACheckKind.PAYMENT, QACheckKind.DASHBOARD}
)


class QACheckOutcome(Enum):
    """Whether a stage 9 check passed, failed, or was explicitly excepted.

    An exception does not make an absent check appear present: it names a human
    risk owner and is only allowed off the critical path (SPEC.md sections 4 and
    5).
    """

    PASSED = "passed"
    FAILED = "failed"
    EXCEPTED = "excepted"


@dataclass(frozen=True)
class QACheck:
    """One recorded stage 9 launch QA check.

    Every check carries the evidence that supports its outcome so the gate is
    traceable. An excepted check requires a named owner, so an exception is a
    scoped human decision rather than a silent omission (SPEC.md sections 4 and
    5). A failed check is recorded with its owner and can never authorize traffic.
    """

    kind: QACheckKind
    outcome: QACheckOutcome
    evidence: str
    owner: str = ""
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.evidence or not self.evidence.strip():
            raise InvalidLaunchQAError(
                f"stage 9 QA check {self.kind.value!r} evidence is required"
            )
        if self.outcome is QACheckOutcome.EXCEPTED and (
            not self.owner or not self.owner.strip()
        ):
            raise InvalidLaunchQAError(
                f"stage 9 QA check {self.kind.value!r} exception requires a "
                "named owner"
            )

    @property
    def is_passing(self) -> bool:
        return self.outcome is QACheckOutcome.PASSED


CANONICAL_LAUNCH_KINDS: tuple[str, ...] = (
    "recorded-message",
    "technical-tests",
    "commercial-tests",
    "qa-forms",
    "qa-crm",
    "qa-email",
    "qa-automation",
    "qa-booking",
    "qa-tracking",
    "qa-payment",
    "qa-handoff",
    "client-approval",
    "budget-approval",
    "creative-approval",
    "launch-dashboard",
    "launch-decision",
)


CANONICAL_LAUNCH_KIND_CHECKS: dict[str, tuple[QACheckKind, ...]] = {
    "recorded-message": (QACheckKind.RECORDED_MESSAGE,),
    "technical-tests": (
        QACheckKind.TECHNICAL_DESKTOP,
        QACheckKind.TECHNICAL_MOBILE,
    ),
    "commercial-tests": (
        QACheckKind.COMMERCIAL_DESKTOP,
        QACheckKind.COMMERCIAL_MOBILE,
    ),
    "qa-forms": (QACheckKind.FORMS,),
    "qa-crm": (QACheckKind.CRM,),
    "qa-email": (QACheckKind.EMAIL,),
    "qa-automation": (QACheckKind.AUTOMATION,),
    "qa-booking": (QACheckKind.BOOKING,),
    "qa-tracking": (QACheckKind.TRACKING,),
    "qa-payment": (QACheckKind.PAYMENT,),
    "qa-handoff": (QACheckKind.SALES_HANDOFF,),
    "client-approval": (QACheckKind.CLIENT_APPROVAL,),
    "budget-approval": (QACheckKind.BUDGET,),
    "creative-approval": (QACheckKind.CREATIVE,),
    "launch-dashboard": (QACheckKind.DASHBOARD,),
    "launch-decision": (QACheckKind.LAUNCH_DECISION,),
}


@dataclass(frozen=True)
class LaunchQAPackage:
    """The reviewed stage 9 launch QA, projected to the sixteen canonical gate kinds.

    SPEC.md section 4, stage 9 "QA" and its "Launch Approved" checkpoint: a stage
    is complete only when its required assets exist, pass the checkpoint and
    receive approval for downstream use, and a passing gate pins the exact
    evidence. The required asset package is the recorded message, technical and
    commercial tests on desktop and mobile, forms, CRM, email, automation,
    booking, tracking, payment when relevant, handoff, client approval, budget,
    creative, dashboard and the launch decision. The Execution context reviews
    that as one rich ``LaunchQA`` (the checks belong to the same QA, grounded on
    the completed stage 8 funnel and a designated human authorization); this
    package is the bridge to the governance gate, which pins one exact
    ``StageAssetVersion`` per canonical kind.

    The canon (SPEC.md section 12.3: stage 9 uses canon files 01, 08, 21, 22 and
    24) carries a funnel pre-launch checklist together with the compliance assets
    (GDPR consent, Facebook and income disclaimers, privacy and terms) and the
    learning-versus-optimization and set-and-forget rules. ``LaunchQA`` already
    enforces the complete same-tenant check set, the critical-path outcomes and
    the designated-authority traffic authorization at construction and
    authorization, so each canonical kind is projected from the single reviewed QA
    at one positive integer version. The QACheckKind set is finer grained than the
    sixteen kinds (technical and commercial QA each cover desktop and mobile), so
    ``CANONICAL_LAUNCH_KIND_CHECKS`` records which checks evidence each kind.

    A ``LaunchQA`` only owns its launch evidence once ``authorize_traffic`` passes
    the checkpoint, so this package refuses a QA that has not reached
    ``LaunchQAState.READY_FOR_TRAFFIC``: sixteen kinds cannot be pinned as this
    client's evidence without a QA that actually passed and was authorized to
    begin traffic (SPEC.md section 4). It also refuses a blank identity, a
    versionless QA or a cross-tenant QA rather than silently pinning inexact or
    foreign evidence (SPEC.md sections 3 and 4).
    """

    package_id: str
    tenant_id: str
    qa: "LaunchQA"
    qa_version: int

    def __post_init__(self) -> None:
        for label, value in (
            ("launch QA package id", self.package_id),
            ("launch QA package tenant id", self.tenant_id),
        ):
            if not value or not value.strip():
                raise InvalidLaunchQAPackageError(f"{label} is required")
        if self.qa.tenant_id != self.tenant_id:
            raise LaunchQAPackageTenantBoundaryError(
                f"stage 9 launch QA {self.qa.qa_id!r} belongs to tenant "
                f"{self.qa.tenant_id!r}, not package tenant {self.tenant_id!r}"
            )
        if not isinstance(self.qa_version, int) or self.qa_version < 1:
            raise InvalidLaunchQAPackageError(
                "the launch QA version must be a positive integer so the stage 9 "
                "gate can pin the reviewed asset at an exact version"
            )
        if not self.qa.is_ready_for_traffic:
            raise InvalidLaunchQAPackageError(
                f"stage 9 launch QA {self.qa.qa_id!r} has not passed Launch "
                "Approved, so its sixteen asset kinds cannot be pinned as exact "
                "evidence"
            )

    @property
    def kinds(self) -> frozenset[str]:
        """The canonical kinds the reviewed stage 9 launch QA projects onto."""
        return frozenset(CANONICAL_LAUNCH_KINDS)

    def missing_kinds(self) -> tuple[str, ...]:
        """Canonical stage 9 kinds not covered by the projected launch QA."""
        covered = {asset.kind for asset in self.stage_asset_versions()}
        return tuple(
            kind for kind in CANONICAL_LAUNCH_KINDS if kind not in covered
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_kinds()

    def stage_asset_versions(self) -> tuple[StageAssetVersion, ...]:
        """Project the reviewed stage 9 launch QA onto exact governance evidence.

        Every canonical kind is evidenced by checks that belong to the same
        reviewed ``LaunchQA``, so each is pinned to that QA's identity at its
        exact version. Governance still pins each projection for the workspace
        tenant, so a cross-client QA is refused rather than silently authorized
        (SPEC.md sections 3, 4 and 11).
        """
        return tuple(
            StageAssetVersion(
                asset_id=self.qa.qa_id,
                tenant_id=self.tenant_id,
                kind=kind,
                version=self.qa_version,
            )
            for kind in CANONICAL_LAUNCH_KINDS
        )


@dataclass(frozen=True)
class TrafficAuthorization:
    """A designated human's authorization to begin traffic (SPEC.md section 4).

    The "Launch Approved" checkpoint requires "the designated human authorizes
    traffic". The record names the human authority, the intended use and the date.
    It authorizes the operator to begin; it is not evidence that traffic is live,
    which is a separate stage 10 observation.
    """

    authorized_by: str
    intended_use: str
    authorized_on: date

    def __post_init__(self) -> None:
        if not self.authorized_by or not self.authorized_by.strip():
            raise InvalidLaunchQAError(
                "traffic authorization requires a designated human authority"
            )
        if not self.intended_use or not self.intended_use.strip():
            raise InvalidLaunchQAError(
                "traffic authorization intended use is required"
            )


class MilestoneKind(Enum):
    """The distinct stage 10 post-launch milestones (SPEC.md section 4).

    SPEC.md section 4, stage 10 "Launch": the "Performance Baseline Established"
    checkpoint treats first qualified traffic and the subsequent lead, appointment
    and sale as distinct observed milestones. They are distinct because campaign
    activation, a raw lead, a qualified appointment and a sale are different
    facts; conflating them would let a launch alone look like a measured result
    (Phase 5 TDD example: "traffic, lead, qualified appointment and sale are
    distinct observed milestones").
    """

    FIRST_QUALIFIED_TRAFFIC = "first_qualified_traffic"
    LEAD = "lead"
    APPOINTMENT = "appointment"
    SALE = "sale"


MILESTONE_ORDER: tuple[MilestoneKind, ...] = (
    MilestoneKind.FIRST_QUALIFIED_TRAFFIC,
    MilestoneKind.LEAD,
    MilestoneKind.APPOINTMENT,
    MilestoneKind.SALE,
)


class ObservationStatus(Enum):
    """Whether a stage 10 milestone has been observed or is still pending.

    SPEC.md section 4, stage 10: missing observations are shown as pending, never
    omitted or filled with a guess. A pending milestone is a visible gap, not an
    observation.
    """

    OBSERVED = "observed"
    PENDING = "pending"


@dataclass(frozen=True)
class MilestoneObservation:
    """One recorded stage 10 milestone observation (SPEC.md sections 3 and 4).

    An observed milestone pins the date and the source it was observed from, so
    an observation is traceable and distinct from a causal conclusion (SPEC.md
    section 3: "Observations are distinct from causal conclusions"). A pending
    milestone carries neither a date nor a source, so an unobserved milestone
    cannot be represented as an observation.
    """

    kind: MilestoneKind
    status: ObservationStatus
    tenant_id: str
    observed_on: date | None = None
    source: str = ""
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.tenant_id or not self.tenant_id.strip():
            raise InvalidPerformanceBaselineError(
                "milestone observation tenant id is required"
            )
        if self.status is ObservationStatus.OBSERVED:
            if not isinstance(self.observed_on, date):
                raise InvalidPerformanceBaselineError(
                    f"observed milestone {self.kind.value!r} requires a date"
                )
            if not self.source or not self.source.strip():
                raise InvalidPerformanceBaselineError(
                    f"observed milestone {self.kind.value!r} requires a source"
                )
        else:
            if self.observed_on is not None or (
                self.source and self.source.strip()
            ):
                raise InvalidPerformanceBaselineError(
                    f"pending milestone {self.kind.value!r} cannot carry an "
                    "observation"
                )

    @property
    def is_observed(self) -> bool:
        return self.status is ObservationStatus.OBSERVED


@dataclass(frozen=True)
class LaunchAssetPackage:
    """The stage 10 required asset package (SPEC.md section 4, stage 10).

    SPEC.md section 4, stage 10 "Launch": the required asset package is the live
    campaign, spend and lead records, conversion and engagement measures,
    applications, bookings, shows, closes, acquisition cost, attribution and
    issue log. The package is frozen and reject-only, so a missing artifact
    cannot be represented as a completed stage 10 deliverable.
    """

    live_campaign: str
    spend_records: str
    lead_records: str
    conversion_measures: str
    engagement_measures: str
    applications: str
    bookings: str
    shows: str
    closes: str
    acquisition_cost: str
    attribution: str
    issue_log: str

    def __post_init__(self) -> None:
        for label, value in (
            ("live campaign", self.live_campaign),
            ("spend records", self.spend_records),
            ("lead records", self.lead_records),
            ("conversion measures", self.conversion_measures),
            ("engagement measures", self.engagement_measures),
            ("applications", self.applications),
            ("bookings", self.bookings),
            ("shows", self.shows),
            ("closes", self.closes),
            ("acquisition cost", self.acquisition_cost),
            ("attribution", self.attribution),
            ("issue log", self.issue_log),
        ):
            if not value or not value.strip():
                raise InvalidPerformanceBaselineError(
                    f"stage 10 asset package {label} is required"
                )


class PerformanceBaselineState(Enum):
    """Readiness of the stage 10 performance baseline (SPEC.md section 4).

    A DRAFT baseline becomes ESTABLISHED only when the "Performance Baseline
    Established" checkpoint passes: the stage 9 launch QA authorizes traffic and
    first qualified traffic is observed. Later milestones may remain pending.
    An upstream change returns it to REVIEW_REQUIRED; Superseded and Archived are
    terminal.
    """

    DRAFT = "draft"
    ESTABLISHED = "established"
    REVIEW_REQUIRED = "review_required"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"

    @property
    def is_terminal(self) -> bool:
        return self in _TERMINAL_BASELINE_STATES


_TERMINAL_BASELINE_STATES = frozenset(
    {
        PerformanceBaselineState.SUPERSEDED,
        PerformanceBaselineState.ARCHIVED,
    }
)


class ClaimKind(Enum):
    """Whether a performance statement is an observation, interpretation or cause.

    SPEC.md section 3, Measurement invariant: observations are distinct from
    causal conclusions. A causal conclusion asserts that an observed movement was
    caused by the campaign; an interpretation reports the same movement without
    claiming causation.
    """

    OBSERVATION = "observation"
    INTERPRETATION = "interpretation"
    CAUSAL_CONCLUSION = "causal_conclusion"


@dataclass(frozen=True)
class PerformanceClaim:
    """A stage 10 performance statement about the campaign (SPEC.md section 3).

    The claim names the subject, the statement, its kind, the sample size and the
    source. A causal conclusion can only be recorded against an established
    baseline with an adequate sample; otherwise it must be an interpretation
    (Phase 5 TDD examples: "missing baseline blocks a before and after claim",
    "low sample size keeps causal claim as interpretation").
    """

    claim_id: str
    tenant_id: str
    subject: str
    statement: str
    kind: ClaimKind
    sample_size: int
    source: str
    baseline_id: str | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("claim id", self.claim_id),
            ("claim tenant id", self.tenant_id),
            ("claim subject", self.subject),
            ("claim statement", self.statement),
            ("claim source", self.source),
        ):
            if not value or not value.strip():
                raise InvalidPerformanceClaimError(f"{label} is required")
        if self.sample_size < 0:
            raise InvalidPerformanceClaimError(
                "claim sample size cannot be negative"
            )

    def as_interpretation(self) -> "PerformanceClaim":
        """Return a causal claim downgraded to an interpretation.

        A low sample size cannot support a causal conclusion, but the same
        observed movement can still be recorded as an interpretation rather than
        discarded (Phase 5 TDD example: "low sample size keeps causal claim as
        interpretation").
        """
        if self.kind is not ClaimKind.CAUSAL_CONCLUSION:
            raise InvalidPerformanceClaimError(
                "only a causal conclusion can be downgraded to an interpretation"
            )
        return replace(self, kind=ClaimKind.INTERPRETATION)

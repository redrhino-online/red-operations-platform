"""Value objects for the Execution bounded context (pure domain).

SPEC.md section 4, stage 8 "Integrate" defines the required asset package
(campaign architecture, pages, forms, qualification, booking, sequences, CRM,
tags, automation, analytics, tracking, sales handoff and SOPs) and the "Funnel
Complete" checkpoint: a test prospect completes capture, engagement and
conversion handoffs with reliable records and ownership.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from redops.contexts.execution.domain.errors import (
    InvalidFunnelError,
    InvalidLaunchQAError,
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

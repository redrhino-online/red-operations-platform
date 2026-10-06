"""Value objects for the Governance bounded context (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING, Iterable, Mapping

from redops.contexts.governance.domain.errors import (
    CrossTenantAssetError,
    InvalidStageTemplateError,
    MetricReportingError,
    MetricReportingTenantBoundaryError,
    ProductionViewError,
    StageRunProjectionError,
    UmbrellaPlanCoverageError,
    UmbrellaPlanReportingError,
    UmbrellaPlanReportingTenantBoundaryError,
    VersionlessAssetError,
)

if TYPE_CHECKING:
    from redops.contexts.governance.domain.entities import GateLedger, StageRun


class GateState(Enum):
    """Gate states from SPEC.md section 4."""

    NOT_STARTED = "not_started"
    WORKING = "working"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    CHANGES_REQUIRED = "changes_required"
    BLOCKED = "blocked"
    WAIVED = "waived"
    SUPERSEDED = "superseded"


class ApprovalOutcome(Enum):
    """Outcome of a version-specific approval request (SPEC.md section 3)."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"
    SUPERSEDED = "superseded"


class GateDisposition(Enum):
    """The recorded outcome of a stage gate decision (SPEC.md section 4).

    Only APPROVED passes the gate. A waiver is a scoped human decision that
    records risk; it never makes an absent asset present and never passes a
    gate. Changes Required, Blocked and Superseded never authorize downstream
    work.
    """

    APPROVED = "approved"
    CHANGES_REQUIRED = "changes_required"
    BLOCKED = "blocked"
    WAIVED = "waived"
    SUPERSEDED = "superseded"

    @property
    def is_passing(self) -> bool:
        return self is GateDisposition.APPROVED


class StageStatus(Enum):
    """Status of a StageRun (SPEC.md section 3 aggregate table).

    A stage reaches COMPLETE only through an accepted gate decision, never by
    activity. The other states mirror the gate states so a blocked or waived
    stage never appears complete.
    """

    NOT_STARTED = "not_started"
    WORKING = "working"
    IN_REVIEW = "in_review"
    COMPLETE = "complete"
    CHANGES_REQUIRED = "changes_required"
    BLOCKED = "blocked"
    WAIVED = "waived"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class StageTransition:
    """One recorded StageRun status change (SPEC.md section 4).

    Records the actor, reason, timestamp, old and new status, and correlation
    ID so a stage's history can be reconstructed and audited.
    """

    actor: str
    reason: str
    occurred_at: date
    old_status: StageStatus
    new_status: StageStatus
    correlation_id: str

    def __post_init__(self) -> None:
        if not self.actor or not self.actor.strip():
            raise ValueError("stage transition actor is required")
        if not self.reason or not self.reason.strip():
            raise ValueError("stage transition reason is required")
        if not self.correlation_id or not self.correlation_id.strip():
            raise ValueError("stage transition correlation id is required")


@dataclass(frozen=True)
class AssetVersionRef:
    """An exact, pinned asset version. Gate approval pins these, not bare asset names."""

    asset_id: str
    version: int

    def __post_init__(self) -> None:
        if not self.asset_id or not self.asset_id.strip():
            raise ValueError("asset_id must be a non-empty identifier")
        if self.version < 1:
            raise ValueError("asset version must be >= 1")

    def __str__(self) -> str:
        return f"{self.asset_id}@{self.version}"


@dataclass(frozen=True)
class StageAssetVersion:
    """An exact version of one real stage asset, scoped to one tenant.

    A stage asset produced by a bounded context (an intake asset, an avatar, a
    signature solution) has a unique id, one owning tenant, the canonical
    template asset kind and a positive version. The governance gate pins an
    ``AssetVersionRef`` keyed by the asset *kind*, so the owning tenant must be
    checked against the workspace before the asset can become gate evidence
    (SPEC.md sections 3 and 4: every tenant resource belongs to exactly one
    client; a passing gate pins the exact evidence and intended downstream use).

    The value object is frozen and reject-only: an asset with no positive
    version cannot be represented as an exact version, and ``pin`` refuses an
    asset whose tenant is not the workspace tenant rather than silently pinning
    another client's asset.
    """

    asset_id: str
    tenant_id: str
    kind: str
    version: int

    def __post_init__(self) -> None:
        for label, value in (
            ("stage asset id", self.asset_id),
            ("stage asset tenant id", self.tenant_id),
            ("stage asset kind", self.kind),
        ):
            if not value or not value.strip():
                raise VersionlessAssetError(
                    f"{label} is required to pin an exact asset version"
                )
        if not isinstance(self.version, int) or self.version < 1:
            raise VersionlessAssetError(
                "a real stage asset requires a positive integer version to be "
                "pinned; a versionless asset is not exact evidence"
            )

    def pin(self, *, tenant_id: str) -> AssetVersionRef:
        """Return the exact ``AssetVersionRef`` this asset pins for one workspace.

        The workspace tenant is supplied by the caller because governance never
        invents the owning client (SPEC.md section 11). A mismatched tenant is
        refused so a cross-client asset cannot be pinned as gate evidence.
        """
        if self.tenant_id != tenant_id:
            raise CrossTenantAssetError(
                f"stage asset {self.asset_id!r} belongs to tenant "
                f"{self.tenant_id!r}, not workspace tenant {tenant_id!r}"
            )
        return AssetVersionRef(self.kind, self.version)


def duplicate_asset_kinds(
    assets: Iterable[AssetVersionRef],
) -> frozenset[str]:
    """Return asset kinds for which more than one exact version is pinned.

    A gate must pin exactly one version per required asset kind; a kind that
    appears at two versions leaves the approved version ambiguous (SPEC.md
    sections 3 and 4).
    """
    counts: dict[str, int] = {}
    for asset in assets:
        counts[asset.asset_id] = counts.get(asset.asset_id, 0) + 1
    return frozenset(kind for kind, count in counts.items() if count > 1)


@dataclass(frozen=True)
class Waiver:
    """A scoped human decision. It never creates or substitutes for an asset.

    SPEC.md section 4 requires a waiver to name its reason, risk owner, expiry or
    review trigger, and downstream effects. Recording the concrete downstream
    stages, assets or journeys the waiver affects keeps it scoped: a waiver
    without an impact surface would be a blanket bypass that can silently release
    unrelated dependent work.
    """

    reason: str
    risk_owner: str
    downstream_effects: frozenset[str]
    review_trigger: str = ""
    expires_on: date | None = None

    def __post_init__(self) -> None:
        if not self.reason or not self.reason.strip():
            raise ValueError("waiver reason is required")
        if not self.risk_owner or not self.risk_owner.strip():
            raise ValueError("waiver risk owner is required")
        if (not self.review_trigger or not self.review_trigger.strip()) and self.expires_on is None:
            raise ValueError("waiver requires an expiry or review trigger")
        if not self.downstream_effects:
            raise ValueError(
                "waiver must record the downstream effects it is scoped to"
            )
        for effect in self.downstream_effects:
            if not effect or not effect.strip():
                raise ValueError(
                    "waiver downstream effects must be non-empty identifiers"
                )

    def is_expired(self, on: date) -> bool:
        """A waiver past its expiry date is no longer a live risk acceptance.

        SPEC.md section 4 requires a waiver to carry an expiry or review trigger
        and says a failed or expired prerequisite blocks dependent authorization
        until resolved. A waiver without an explicit expiry relies on its review
        trigger and never expires by date, mirroring ``ApprovalRequest``.
        """
        return self.expires_on is not None and on > self.expires_on


@dataclass(frozen=True)
class StageDefinition:
    """One stage of the versioned 0-10 production template (SPEC.md section 4).

    Names the required asset package (as asset kinds, versioned at gate time),
    the checkpoint rubric, the accountable role and the approver role, and the
    prerequisite stages. A stage depends only on earlier stages, so the template
    is acyclic.
    """

    stage_number: int
    name: str
    required_asset_kinds: frozenset[str]
    checkpoint: str
    accountable_role: str
    approver_role: str
    dependencies: frozenset[int] = frozenset()

    def __post_init__(self) -> None:
        if self.stage_number < 0:
            raise InvalidStageTemplateError("stage number must be >= 0")
        for label, value in (
            ("name", self.name),
            ("checkpoint", self.checkpoint),
            ("accountable role", self.accountable_role),
            ("approver role", self.approver_role),
        ):
            if not value or not value.strip():
                raise InvalidStageTemplateError(
                    f"stage {self.stage_number} {label} is required"
                )
        if not self.required_asset_kinds:
            raise InvalidStageTemplateError(
                f"stage {self.stage_number} requires at least one asset kind"
            )
        for kind in self.required_asset_kinds:
            if not kind or not kind.strip():
                raise InvalidStageTemplateError(
                    f"stage {self.stage_number} has a blank asset kind"
                )
        if self.stage_number in self.dependencies:
            raise InvalidStageTemplateError(
                f"stage {self.stage_number} cannot depend on itself"
            )


@dataclass(frozen=True)
class StageTemplate:
    """A versioned 0-10 production pipeline (SPEC.md section 4).

    The template is the canonical source of the stage dependency graph, the
    required asset package per stage, the checkpoint, and the accountable and
    approver roles. Stages are numbered contiguously from zero, and every
    dependency points to an earlier stage, so the graph cannot contain a cycle.
    """

    version: str
    stages: tuple[StageDefinition, ...]

    def __post_init__(self) -> None:
        if not self.version or not self.version.strip():
            raise InvalidStageTemplateError("template version is required")
        if not self.stages:
            raise InvalidStageTemplateError("template requires at least one stage")
        numbers = [stage.stage_number for stage in self.stages]
        if len(set(numbers)) != len(numbers):
            raise InvalidStageTemplateError("stage numbers must be unique")
        if sorted(numbers) != list(range(len(numbers))):
            raise InvalidStageTemplateError(
                "stage numbers must be contiguous from zero"
            )
        for stage in self.stages:
            forward = sorted(
                dependency
                for dependency in stage.dependencies
                if dependency >= stage.stage_number
            )
            if forward:
                raise InvalidStageTemplateError(
                    f"stage {stage.stage_number} has a forward dependency: {forward}"
                )

    def definition_for(self, stage_number: int) -> StageDefinition | None:
        for stage in self.stages:
            if stage.stage_number == stage_number:
                return stage
        return None

    def dependencies_of(self, stage_number: int) -> frozenset[int]:
        definition = self.definition_for(stage_number)
        return definition.dependencies if definition is not None else frozenset()

    def required_asset_kinds(self, stage_number: int) -> frozenset[str]:
        definition = self.definition_for(stage_number)
        return (
            definition.required_asset_kinds
            if definition is not None
            else frozenset()
        )


@dataclass(frozen=True)
class PipelineProgress:
    """Verified progress across the stage 0-10 pipeline (SPEC.md section 4).

    Progress is reported as the number of stages whose latest durable gate
    decision is passing plus caller-supplied verified post-launch milestones.
    Activity is reported separately and never contributes to verified progress,
    so progress is never displayed as tasks checked off. A blocked, changes
    required, waived or superseded stage is not an approved gate and does not
    count.
    """

    approved_gates: int
    total_gates: int
    verified_post_launch_milestones: int = 0
    activity_entries: int = 0

    def __post_init__(self) -> None:
        for name, value in (
            ("approved gates", self.approved_gates),
            ("total gates", self.total_gates),
            ("verified post launch milestones", self.verified_post_launch_milestones),
            ("activity entries", self.activity_entries),
        ):
            if value < 0:
                raise ValueError(f"{name} cannot be negative")
        if self.approved_gates > self.total_gates:
            raise ValueError("approved gates cannot exceed total gates")

    @classmethod
    def from_ledger(
        cls,
        ledger: "GateLedger",
        *,
        on: date,
        verified_post_launch_milestones: int = 0,
        activity_entries: int = 0,
    ) -> "PipelineProgress":
        """Derive verified progress from the durable gate ledger at ``on``.

        Only gates whose latest passing decision still authorizes at ``on``
        count as approved; a gate whose pinned approvals have expired is not
        verified progress. Milestone observations are supplied by the caller
        because they are owned by the Measurement context, not inferred here.
        """
        stages = ledger.template.stages
        approved = sum(
            1
            for stage in stages
            if ledger.has_passing_decision(stage.stage_number, on=on)
        )
        return cls(
            approved_gates=approved,
            total_gates=len(stages),
            verified_post_launch_milestones=verified_post_launch_milestones,
            activity_entries=activity_entries,
        )

    @property
    def verified_progress(self) -> int:
        return self.approved_gates + self.verified_post_launch_milestones

    @property
    def gates_remaining(self) -> int:
        return self.total_gates - self.approved_gates


class MetricReportingBasis(Enum):
    """Whether a METRICS reporting figure is observed or a placeholder.

    SPEC.md section 4 separates metrics as a reporting dimension and the
    Measurement invariant keeps observations distinct from causal conclusions.
    The canon's dashboard discipline (canon files 23 and 24) starts from
    placeholder numbers that are not real metrics until observed over enough
    instances, so the METRICS dimension reports only OBSERVED rows; a PLACEHOLDER
    row is refused rather than rendered as verified progress.
    """

    OBSERVED = "observed"
    PLACEHOLDER = "placeholder"


@dataclass(frozen=True)
class MetricMovement:
    """A measured before-and-after of one approved stage 10 improvement.

    SPEC.md section 4, stage 10 with Phase 5: "one improvement is approved and
    measured" and a performance review "records baseline and observed result".
    The governance view does not compute the movement; it carries the measured
    before and after values and the measured date so the METRICS dimension can
    show the observed movement next to the metric's latest figure. Values are
    kept distinct from a causal conclusion (SPEC.md section 3, Measurement
    invariant).
    """

    improvement_id: str
    before: float
    after: float
    measured_on: date

    def __post_init__(self) -> None:
        if not self.improvement_id or not self.improvement_id.strip():
            raise MetricReportingError(
                "a metric movement requires the improvement it measured"
            )
        for label, value in (("before", self.before), ("after", self.after)):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise MetricReportingError(
                    f"a metric movement {label} value must be a real number"
                )
        if not isinstance(self.measured_on, date):
            raise MetricReportingError(
                "a metric movement requires the date it was measured"
            )


@dataclass(frozen=True)
class MetricReportingView:
    """One observed metric row of the production view's METRICS dimension.

    SPEC.md section 4 requires the production view to separate metrics from the
    other seven reporting dimensions, and section 3 keys a Measurement aggregate
    by "metric definition, window, baseline, observation, source". The
    Measurement context owns that write model; this frozen row is that context's
    typed projection onto the read model, so the view never invents a metric,
    window, sample or source. A row carries the registered metric identity and
    classification, the latest observed value over a closed window with its
    sample and source, and, where an approved improvement has been measured, the
    observed ``MetricMovement``. A placeholder figure or a row outside the
    required shape is refused rather than rendered as verified progress (SPEC.md
    sections 4 and 12.4).
    """

    metric_id: str
    tenant_id: str
    name: str
    funnel_step: str
    unit: str
    direction: str
    value: float
    window_start: date
    window_end: date
    sample_size: int
    source: str
    recorded_on: date
    basis: MetricReportingBasis = MetricReportingBasis.OBSERVED
    movement: MetricMovement | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("metric id", self.metric_id),
            ("metric tenant id", self.tenant_id),
            ("metric name", self.name),
            ("metric funnel step", self.funnel_step),
            ("metric unit", self.unit),
            ("metric direction", self.direction),
            ("metric source", self.source),
        ):
            if not value or not value.strip():
                raise MetricReportingError(
                    f"a METRICS reporting row requires its {label}"
                )
        if self.basis is not MetricReportingBasis.OBSERVED:
            raise MetricReportingError(
                "the METRICS dimension reports observed measurements only; a "
                "placeholder figure cannot appear as a verified metric"
            )
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise MetricReportingError(
                "a METRICS reporting row requires a real observed value"
            )
        if not isinstance(self.window_start, date) or not isinstance(
            self.window_end, date
        ):
            raise MetricReportingError(
                "a METRICS reporting row requires a start and end window date"
            )
        if self.window_end < self.window_start:
            raise MetricReportingError(
                "a METRICS reporting row window cannot end before it starts"
            )
        if (
            not isinstance(self.sample_size, int)
            or isinstance(self.sample_size, bool)
            or self.sample_size < 0
        ):
            raise MetricReportingError(
                "a METRICS reporting row requires a non-negative integer sample"
            )
        if not isinstance(self.recorded_on, date):
            raise MetricReportingError(
                "a METRICS reporting row requires the date it was recorded"
            )
        if self.movement is not None and not isinstance(
            self.movement, MetricMovement
        ):
            raise MetricReportingError(
                "a METRICS reporting row movement must be a typed measured "
                "movement"
            )


@dataclass(frozen=True)
class UmbrellaPlanReportingView:
    """One umbrella-plan row of the production view (SPEC.md sections 4, 12.5).

    The canon's umbrella plan is the engagement's single-page plan over the whole
    stage 0-10 pipeline, revisited every 90 days (canon files 00 and 01). It is a
    planning decision, not a new required gate kind, so the production view
    carries it as a caller-supplied, tenant-scoped read-model projection: the
    plan identity, its owning client, the accountable owner, the stages it covers
    and the review and next-review dates. The view never invents a plan, owner or
    review date, and a row outside the required shape is refused rather than
    rendered as this engagement's plan.
    """

    plan_id: str
    tenant_id: str
    owner: str
    covered_stages: frozenset[int]
    reviewed_on: date
    next_review_due: date

    def __post_init__(self) -> None:
        for label, value in (
            ("umbrella plan id", self.plan_id),
            ("umbrella plan tenant id", self.tenant_id),
            ("umbrella plan owner", self.owner),
        ):
            if not value or not value.strip():
                raise UmbrellaPlanReportingError(
                    f"an umbrella plan reporting row requires its {label}"
                )
        if not self.covered_stages:
            raise UmbrellaPlanReportingError(
                "an umbrella plan reporting row requires at least one covered stage"
            )
        for stage in self.covered_stages:
            if not isinstance(stage, int) or isinstance(stage, bool) or stage < 0:
                raise UmbrellaPlanReportingError(
                    "an umbrella plan reporting row stage must be a non-negative number"
                )
        if not isinstance(self.reviewed_on, date) or not isinstance(
            self.next_review_due, date
        ):
            raise UmbrellaPlanReportingError(
                "an umbrella plan reporting row requires its review and next-review dates"
            )
        if self.next_review_due <= self.reviewed_on:
            raise UmbrellaPlanReportingError(
                "an umbrella plan reporting row next review must be after its review"
            )

    def is_current(self, on: date) -> bool:
        """Whether the plan's 90-day revisit is not yet due at ``on``."""
        return on < self.next_review_due

    def is_overdue(self, on: date) -> bool:
        """Whether the plan's 90-day revisit is due or past at ``on``."""
        return not self.is_current(on)


class ReportingDimension(Enum):
    """The eight reporting dimensions of the production-manager view.

    SPEC.md section 4 requires the production view to "separate eight reporting
    dimensions: assets, milestones, checkpoints, metrics, owner, dependency,
    status and due date" and to count activity separately from gate completion.
    Governance derives six of them directly from the versioned ``StageTemplate``
    and the durable ``GateLedger``: assets, checkpoints, owner, dependency, status
    and due date. Milestones and metrics are supplied by the caller because the
    Measurement context owns post-launch evidence and the typed metric registry,
    and the view never invents a metric, milestone or causal conclusion from them
    (SPEC.md sections 4 and 12.5).
    """

    ASSETS = "assets"
    MILESTONES = "milestones"
    CHECKPOINTS = "checkpoints"
    METRICS = "metrics"
    OWNER = "owner"
    DEPENDENCY = "dependency"
    STATUS = "status"
    DUE_DATE = "due_date"


PRODUCTION_REPORTING_DIMENSIONS: tuple[ReportingDimension, ...] = tuple(
    ReportingDimension
)


@dataclass(frozen=True)
class StageProductionView:
    """One stage of the production-manager view (SPEC.md section 4).

    Answers, for a single stage at one evaluation instant: what should exist
    (``required_asset_kinds`` from the template), what is present and approved
    (``approved_assets``, the exact pinned versions whose per-asset approval is
    still effective), what is missing (``missing_asset_kinds``), who is
    accountable (``assigned_owner``), which dependency blocks work
    (``blocking_dependencies``), what approval is next (the stage's checkpoint
    and approver role) and when it is due (``due_on``). The stage's overall
    ``status`` is the durable gate state, which is kept separate from the
    per-asset approval coverage, so a blocked or waived gate never appears
    approved (SPEC.md section 4). The view is a read model: it never invents a
    named owner, approver, due date, metric or milestone.
    """

    stage_number: int
    name: str
    checkpoint: str
    status: GateState
    required_asset_kinds: frozenset[str]
    approved_assets: frozenset[AssetVersionRef]
    accountable_role: str
    approver_role: str
    dependencies: frozenset[int]
    blocking_dependencies: frozenset[int]
    assigned_owner: str | None = None
    recorded_approver: str | None = None
    due_on: date | None = None
    next_action: str = ""
    blockers: frozenset[str] = frozenset()
    waiver: Waiver | None = None
    entered_at: date | None = None

    def __post_init__(self) -> None:
        if self.stage_number < 0:
            raise ProductionViewError("stage view number must be >= 0")
        for label, value in (
            ("name", self.name),
            ("checkpoint", self.checkpoint),
            ("accountable role", self.accountable_role),
            ("approver role", self.approver_role),
        ):
            if not value or not value.strip():
                raise ProductionViewError(
                    f"stage {self.stage_number} {label} is required"
                )
        if not self.required_asset_kinds:
            raise ProductionViewError(
                f"stage {self.stage_number} view requires at least one asset kind"
            )
        for kind in self.required_asset_kinds:
            if not kind or not kind.strip():
                raise ProductionViewError(
                    f"stage {self.stage_number} view has a blank asset kind"
                )
        for asset in self.approved_assets:
            if asset.asset_id not in self.required_asset_kinds:
                raise ProductionViewError(
                    f"stage {self.stage_number} view shows approved asset "
                    f"{asset} outside its required package"
                )
        duplicates = duplicate_asset_kinds(self.approved_assets)
        if duplicates:
            names = ", ".join(sorted(duplicates))
            raise ProductionViewError(
                "a stage view must show exactly one approved version per asset "
                f"kind; multiple versions declared for: {names}"
            )
        if self.stage_number in self.dependencies:
            raise ProductionViewError(
                "a stage view cannot list its own stage as a prerequisite"
            )
        if self.stage_number in self.blocking_dependencies:
            raise ProductionViewError(
                "a stage view cannot list its own stage as a blocking dependency"
            )
        if not self.blocking_dependencies <= self.dependencies:
            raise ProductionViewError(
                "a stage view's blocking dependencies must be a subset of its "
                "template dependencies"
            )
        for blocker in self.blockers:
            if not blocker or not blocker.strip():
                raise ProductionViewError(
                    "stage view blockers must be non-empty identifiers"
                )

    @property
    def missing_asset_kinds(self) -> frozenset[str]:
        """Required kinds with no currently effective exact approved version."""
        approved = frozenset(asset.asset_id for asset in self.approved_assets)
        return self.required_asset_kinds - approved

    @property
    def is_approved(self) -> bool:
        """Whether the stage currently authorizes downstream work.

        A stage is approved only when its durable gate state is ``APPROVED``, it
        has no missing required asset kind and no prerequisite blocks it. A
        blocked, changes-required, waived or superseded state never counts, and a
        waiver cannot make a missing asset present (SPEC.md section 4).
        """
        return (
            self.status is GateState.APPROVED
            and not self.missing_asset_kinds
            and not self.blocking_dependencies
        )


@dataclass(frozen=True)
class EngagementProductionView:
    """The production-manager view for one client engagement (SPEC.md section 4).

    Composes the per-stage ``StageProductionView`` records for the whole
    versioned 0-10 pipeline and answers the engagement-level questions: the
    current stage, the next approval, which stages are blocked, and verified
    progress. It also exposes the eight reporting dimensions separately and
    counts activity apart from gate completion, so progress is never displayed as
    tasks checked off. It is derived purely from the ``StageTemplate`` and the
    durable ``GateLedger`` at an evaluation instant; the engagement and tenant
    labels are supplied by the caller because governance never invents the owning
    client (SPEC.md section 11).
    """

    engagement: str
    tenant_id: str
    template_version: str
    stages: tuple[StageProductionView, ...]
    progress: PipelineProgress
    metric_reporting: tuple[MetricReportingView, ...] = ()
    umbrella_plan: UmbrellaPlanReportingView | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("engagement", self.engagement),
            ("tenant", self.tenant_id),
            ("template version", self.template_version),
        ):
            if not value or not value.strip():
                raise ProductionViewError(f"production view {label} is required")
        if not self.stages:
            raise ProductionViewError(
                "production view requires at least one stage"
            )
        numbers = [stage.stage_number for stage in self.stages]
        if len(set(numbers)) != len(numbers):
            raise ProductionViewError(
                "production view stage numbers must be unique"
            )
        if sorted(numbers) != list(range(len(numbers))):
            raise ProductionViewError(
                "production view stage numbers must be contiguous from zero"
            )
        if self.progress.total_gates != len(self.stages):
            raise ProductionViewError(
                "production view progress must cover every stage in the view; "
                f"progress reports {self.progress.total_gates} gates but the "
                f"view holds {len(self.stages)} stages"
            )
        seen_metrics: set[str] = set()
        for row in self.metric_reporting:
            if not isinstance(row, MetricReportingView):
                raise ProductionViewError(
                    "production view metric reporting must be typed observed "
                    "metric rows"
                )
            if row.tenant_id != self.tenant_id:
                raise MetricReportingTenantBoundaryError(
                    f"production view metric {row.metric_id!r} belongs to tenant "
                    f"{row.tenant_id!r}, not workspace tenant {self.tenant_id!r}"
                )
            if row.metric_id in seen_metrics:
                raise ProductionViewError(
                    f"production view reports metric {row.metric_id!r} more than "
                    "once; the METRICS dimension shows one row per registered "
                    "metric"
                )
            seen_metrics.add(row.metric_id)
        if self.umbrella_plan is not None:
            if not isinstance(self.umbrella_plan, UmbrellaPlanReportingView):
                raise UmbrellaPlanReportingError(
                    "production view umbrella plan must be a typed umbrella plan "
                    "reporting row"
                )
            if self.umbrella_plan.tenant_id != self.tenant_id:
                raise UmbrellaPlanReportingTenantBoundaryError(
                    f"production view umbrella plan {self.umbrella_plan.plan_id!r} "
                    f"belongs to tenant {self.umbrella_plan.tenant_id!r}, not "
                    f"workspace tenant {self.tenant_id!r}"
                )
            view_stages = frozenset(stage.stage_number for stage in self.stages)
            if self.umbrella_plan.covered_stages != view_stages:
                raise UmbrellaPlanCoverageError(
                    "production view umbrella plan must cover exactly the view's "
                    f"stages {sorted(view_stages)}, not "
                    f"{sorted(self.umbrella_plan.covered_stages)}"
                )

    @classmethod
    def from_ledger(
        cls,
        ledger: "GateLedger",
        *,
        engagement: str,
        tenant_id: str,
        on: date,
        verified_post_launch_milestones: int = 0,
        activity_entries: int = 0,
        metric_reporting: tuple[MetricReportingView, ...] = (),
        umbrella_plan: UmbrellaPlanReportingView | None = None,
        stage_runs: tuple["StageRun", ...] = (),
    ) -> "EngagementProductionView":
        """Derive the whole production view from a template and gate ledger.

        The stage dependency graph, required asset package and checkpoint rubric
        come from the ledger's versioned ``StageTemplate``; the gate states, pinned
        exact approved versions, owners, approvers, due dates, blockers and scoped
        waivers come from the durable ``GateDecision`` records at ``on``. A
        prerequisite that does not authorize at ``on`` — because it never passed
        or because its own approvals have expired — is reported as a blocking
        dependency, so a failed or expired prerequisite blocks the dependent
        stage in the view until it is resolved (SPEC.md section 4). Milestone and
        activity counts and the typed observed metric rows are supplied by the
        caller because the Measurement and Operations contexts own them; the view
        never infers or fabricates them.

        The durable ``StageRun`` records are supplied by the caller (loaded
        through the ``StageRunRepository`` port) because Governance never reads
        its own store in the domain. A run for this engagement and template
        version supplies the assigned owner, status and entered-at for a stage
        whose gate has not yet been decided; once a ``GateDecision`` exists the
        gate state remains authoritative. A run from another tenant, engagement
        or template version, one for an undefined stage, or a second run for one
        stage is refused rather than rendered as this engagement's progress.
        """
        expected_stage_numbers = {
            definition.stage_number for definition in ledger.template.stages
        }
        runs_by_stage: dict[int, StageRun] = {}
        for run in stage_runs:
            if run.tenant_id != tenant_id:
                raise StageRunProjectionError(
                    f"stage run for stage {run.stage_number} belongs to tenant "
                    f"{run.tenant_id!r}, not workspace tenant {tenant_id!r}"
                )
            if run.engagement != engagement:
                raise StageRunProjectionError(
                    f"stage run for stage {run.stage_number} belongs to "
                    f"engagement {run.engagement!r}, not {engagement!r}"
                )
            if run.template_version != ledger.template.version:
                raise StageRunProjectionError(
                    f"stage run for stage {run.stage_number} carries template "
                    f"version {run.template_version!r}, not "
                    f"{ledger.template.version!r}"
                )
            if run.stage_number not in expected_stage_numbers:
                raise StageRunProjectionError(
                    f"stage run targets stage {run.stage_number}, which the "
                    "template does not define"
                )
            if run.stage_number in runs_by_stage:
                raise StageRunProjectionError(
                    f"production view received two stage runs for stage "
                    f"{run.stage_number}"
                )
            runs_by_stage[run.stage_number] = run
        states = ledger.dependency_states(on=on)
        stages = tuple(
            _stage_production_view(
                ledger,
                definition,
                states,
                on,
                runs_by_stage.get(definition.stage_number),
            )
            for definition in ledger.template.stages
        )
        progress = PipelineProgress.from_ledger(
            ledger,
            on=on,
            verified_post_launch_milestones=verified_post_launch_milestones,
            activity_entries=activity_entries,
        )
        return cls(
            engagement=engagement,
            tenant_id=tenant_id,
            template_version=ledger.template.version,
            stages=stages,
            progress=progress,
            metric_reporting=metric_reporting,
            umbrella_plan=umbrella_plan,
        )

    def stage_by_number(self, stage_number: int) -> StageProductionView | None:
        for stage in self.stages:
            if stage.stage_number == stage_number:
                return stage
        return None

    @property
    def current_stage(self) -> StageProductionView | None:
        """The first stage that does not yet authorize downstream work.

        Returns ``None`` when every stage in the pipeline is approved, which
        means the engagement is in post-launch measurement rather than blocked in
        production (SPEC.md section 4: campaign activation alone does not complete
        the engagement).
        """
        for stage in self.stages:
            if not stage.is_approved:
                return stage
        return None

    @property
    def next_approval(self) -> StageProductionView | None:
        """The stage whose checkpoint approval is next, if any."""
        return self.current_stage

    @property
    def blocked_stages(self) -> tuple[StageProductionView, ...]:
        return tuple(
            stage for stage in self.stages if stage.status is GateState.BLOCKED
        )

    def dimension(self, dimension: ReportingDimension) -> tuple:
        """Return the reporting slice for one of the eight dimensions.

        Each dimension is reported separately, never conflated: assets expose the
        required, approved and missing kinds per stage; milestones expose the
        caller-supplied verified post-launch count; metrics expose the
        caller-supplied typed observed metric rows and their measured movements;
        checkpoints, owner, dependency, status and due date expose the per-stage
        view values. Activity is not a dimension and never appears in a slice
        (SPEC.md section 4).
        """
        if dimension is ReportingDimension.ASSETS:
            return tuple(
                (
                    stage.stage_number,
                    stage.required_asset_kinds,
                    stage.approved_assets,
                    stage.missing_asset_kinds,
                )
                for stage in self.stages
            )
        if dimension is ReportingDimension.MILESTONES:
            return (self.progress.verified_post_launch_milestones,)
        if dimension is ReportingDimension.CHECKPOINTS:
            return tuple(
                (stage.stage_number, stage.checkpoint) for stage in self.stages
            )
        if dimension is ReportingDimension.METRICS:
            return self.metric_reporting
        if dimension is ReportingDimension.OWNER:
            return tuple(
                (stage.stage_number, stage.assigned_owner)
                for stage in self.stages
            )
        if dimension is ReportingDimension.DEPENDENCY:
            return tuple(
                (stage.stage_number, stage.blocking_dependencies)
                for stage in self.stages
            )
        if dimension is ReportingDimension.STATUS:
            return tuple(
                (stage.stage_number, stage.status) for stage in self.stages
            )
        if dimension is ReportingDimension.DUE_DATE:
            return tuple(
                (stage.stage_number, stage.due_on) for stage in self.stages
            )
        raise ProductionViewError(
            f"production view does not represent reporting dimension "
            f"{dimension!r}"
        )


_RUN_GATE_STATE: Mapping[StageStatus, GateState] = {
    StageStatus.NOT_STARTED: GateState.NOT_STARTED,
    StageStatus.WORKING: GateState.WORKING,
    StageStatus.IN_REVIEW: GateState.IN_REVIEW,
    StageStatus.COMPLETE: GateState.APPROVED,
    StageStatus.CHANGES_REQUIRED: GateState.CHANGES_REQUIRED,
    StageStatus.BLOCKED: GateState.BLOCKED,
    StageStatus.WAIVED: GateState.WAIVED,
    StageStatus.SUPERSEDED: GateState.SUPERSEDED,
}


def _stage_production_view(
    ledger: "GateLedger",
    definition: StageDefinition,
    states: "Mapping[int, GateState]",
    on: date,
    run: "StageRun | None" = None,
) -> StageProductionView:
    """Build one ``StageProductionView`` from the template and latest decision.

    The durable gate state is authoritative once a decision exists for the
    stage; a persisted ``StageRun`` fills the gap for a stage that has none, so
    the view can report an assigned owner, a working or blocked state and the
    instant the stage was entered before its gate is decided (SPEC.md sections 3
    and 4). A run that carries no tenant, or one from another engagement or
    template version, is refused by the caller rather than merged here.
    """
    latest = ledger.decision_for(definition.stage_number)
    if latest is None:
        approved: frozenset[AssetVersionRef] = frozenset()
        waiver = None
    else:
        unapproved = latest.unapproved_assets_at(on)
        approved = frozenset(
            asset for asset in latest.required_assets if asset not in unapproved
        )
        waiver = (
            latest.waiver
            if latest.disposition is GateDisposition.WAIVED
            else None
        )
    blocking = frozenset(
        dependency
        for dependency in definition.dependencies
        if not ledger.has_passing_decision(dependency, on=on)
    )
    status = states[definition.stage_number]
    if latest is None and run is not None:
        status = _RUN_GATE_STATE[run.status]
    assigned_owner = (
        latest.assigned_owner
        if latest is not None
        else (run.assigned_owner if run is not None else None)
    )
    return StageProductionView(
        stage_number=definition.stage_number,
        name=definition.name,
        checkpoint=definition.checkpoint,
        status=status,
        required_asset_kinds=definition.required_asset_kinds,
        approved_assets=approved,
        accountable_role=definition.accountable_role,
        approver_role=definition.approver_role,
        dependencies=definition.dependencies,
        blocking_dependencies=blocking,
        assigned_owner=assigned_owner,
        recorded_approver=latest.reviewer if latest is not None else None,
        due_on=latest.due_on if latest is not None else None,
        next_action=latest.next_action if latest is not None else "",
        blockers=latest.blockers if latest is not None else frozenset(),
        waiver=waiver,
        entered_at=run.entered_at if run is not None else None,
    )

"""Value objects for the Governance bounded context (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING, Iterable, Mapping

from redops.contexts.governance.domain.errors import (
    CrossTenantAssetError,
    InvalidStageTemplateError,
    ProductionViewError,
    VersionlessAssetError,
)

if TYPE_CHECKING:
    from redops.contexts.governance.domain.entities import GateLedger


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


class ReportingDimension(Enum):
    """The eight reporting dimensions of the production-manager view.

    SPEC.md section 4 requires the production view to "separate eight reporting
    dimensions: assets, milestones, checkpoints, metrics, owner, dependency,
    status and due date" and to count activity separately from gate completion.
    Governance derives six of them directly from the versioned ``StageTemplate``
    and the durable ``GateLedger``: assets, checkpoints, owner, dependency, status
    and due date. Milestones are supplied because the Measurement context owns
    post-launch evidence, and metrics are not yet sourced by any context, so that
    dimension is reported empty rather than invented (SPEC.md sections 12.1 and
    12.5).
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
        activity counts are supplied by the caller because the Measurement and
        Operations contexts own them; the view never infers or fabricates them.
        """
        states = ledger.dependency_states(on=on)
        stages = tuple(
            _stage_production_view(ledger, definition, states, on)
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
        caller-supplied verified post-launch count; checkpoints, owner,
        dependency, status and due date expose the per-stage view values; and
        metrics are empty because no context sources them yet. Activity is not a
        dimension and never appears in a slice (SPEC.md section 4).
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
            return ()
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


def _stage_production_view(
    ledger: "GateLedger",
    definition: StageDefinition,
    states: "Mapping[int, GateState]",
    on: date,
) -> StageProductionView:
    """Build one ``StageProductionView`` from the template and latest decision."""
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
    return StageProductionView(
        stage_number=definition.stage_number,
        name=definition.name,
        checkpoint=definition.checkpoint,
        status=states[definition.stage_number],
        required_asset_kinds=definition.required_asset_kinds,
        approved_assets=approved,
        accountable_role=definition.accountable_role,
        approver_role=definition.approver_role,
        dependencies=definition.dependencies,
        blocking_dependencies=blocking,
        assigned_owner=latest.assigned_owner if latest is not None else None,
        recorded_approver=latest.reviewer if latest is not None else None,
        due_on=latest.due_on if latest is not None else None,
        next_action=latest.next_action if latest is not None else "",
        blockers=latest.blockers if latest is not None else frozenset(),
        waiver=waiver,
    )

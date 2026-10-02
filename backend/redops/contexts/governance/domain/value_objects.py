"""Value objects for the Governance bounded context (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Iterable

from redops.contexts.governance.domain.errors import InvalidStageTemplateError


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
    """A scoped human decision. It never creates or substitutes for an asset."""

    reason: str
    risk_owner: str
    review_trigger: str = ""
    expires_on: date | None = None

    def __post_init__(self) -> None:
        if not self.reason or not self.reason.strip():
            raise ValueError("waiver reason is required")
        if not self.risk_owner or not self.risk_owner.strip():
            raise ValueError("waiver risk owner is required")
        if (not self.review_trigger or not self.review_trigger.strip()) and self.expires_on is None:
            raise ValueError("waiver requires an expiry or review trigger")


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

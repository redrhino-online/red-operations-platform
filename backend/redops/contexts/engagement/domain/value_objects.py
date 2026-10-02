"""Value objects for the Engagement bounded context (pure domain).

The ClientWorkspace aggregate is the tenant root every client-owned resource
attaches to. Its lifecycle mirrors the engagement summary state in SPEC.md
section 4 ("Engagement: Intake, Diagnosis, ... Paused, Completed"); the stages 0
to 10 are the production checkpoints, and parallel BuildObjects may sit in
different build states while the engagement summary is elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from redops.contexts.engagement.domain.errors import (
    InvalidAuthorityError,
    InvalidIntakeAssetError,
    InvalidIntakePackageError,
    TenantBoundaryError,
)
from redops.contexts.governance.domain.value_objects import StageAssetVersion


class EngagementLifecycle(Enum):
    """The engagement summary state from SPEC.md section 4.

    The states follow the canonical engagement progression: the stage 0-10 names
    in order, then Optimization and Expansion for the post-launch measurement and
    portfolio work, with Paused and Completed as the non-linear states. Completed
    is terminal.
    """

    INTAKE = "intake"
    DIAGNOSIS = "diagnosis"
    POSITIONING = "positioning"
    DIAGNOSTIC_MODELING = "diagnostic_modeling"
    IP_PACKAGING = "ip_packaging"
    PRODUCTIZATION = "productization"
    CAMPAIGN_MESSAGING = "campaign_messaging"
    AUTHORITY_AMPLIFIER_PRODUCTION = "authority_amplifier_production"
    FUNNEL_INTEGRATION = "funnel_integration"
    LAUNCH_QA = "launch_qa"
    FIRST_CAMPAIGN_LAUNCH = "first_campaign_launch"
    OPTIMIZATION = "optimization"
    EXPANSION = "expansion"
    PAUSED = "paused"
    COMPLETED = "completed"

    @property
    def is_terminal(self) -> bool:
        return self is EngagementLifecycle.COMPLETED

    @property
    def is_active(self) -> bool:
        return self not in {EngagementLifecycle.PAUSED, EngagementLifecycle.COMPLETED}


CANONICAL_PROGRESSION: tuple[EngagementLifecycle, ...] = (
    EngagementLifecycle.INTAKE,
    EngagementLifecycle.DIAGNOSIS,
    EngagementLifecycle.POSITIONING,
    EngagementLifecycle.DIAGNOSTIC_MODELING,
    EngagementLifecycle.IP_PACKAGING,
    EngagementLifecycle.PRODUCTIZATION,
    EngagementLifecycle.CAMPAIGN_MESSAGING,
    EngagementLifecycle.AUTHORITY_AMPLIFIER_PRODUCTION,
    EngagementLifecycle.FUNNEL_INTEGRATION,
    EngagementLifecycle.LAUNCH_QA,
    EngagementLifecycle.FIRST_CAMPAIGN_LAUNCH,
    EngagementLifecycle.OPTIMIZATION,
    EngagementLifecycle.EXPANSION,
)


@dataclass(frozen=True)
class ClientAuthority:
    """A named actor and the authority they hold in a client workspace.

    SPEC.md section 3 records a workspace's authorities, and SPEC.md section 4
    requires named human owners and a client-designated authority. The value
    object names the actor and the authority; it does not invent the concrete
    authority roles, which remain an open decision (SPEC.md section 11).
    """

    actor: str
    authority: str

    def __post_init__(self) -> None:
        if not self.actor or not self.actor.strip():
            raise InvalidAuthorityError("client authority actor is required")
        if not self.authority or not self.authority.strip():
            raise InvalidAuthorityError("client authority name is required")


@dataclass(frozen=True)
class LifecycleTransition:
    """One recorded engagement lifecycle change (SPEC.md section 4).

    Records the actor, reason, timestamp, old and new state and correlation ID so
    the workspace history can be reconstructed and audited, mirroring the other
    context state machines.
    """

    actor: str
    reason: str
    occurred_at: date
    old_lifecycle: EngagementLifecycle
    new_lifecycle: EngagementLifecycle
    correlation_id: str

    def __post_init__(self) -> None:
        if not self.actor or not self.actor.strip():
            raise ValueError("lifecycle transition actor is required")
        if not self.reason or not self.reason.strip():
            raise ValueError("lifecycle transition reason is required")
        if not self.correlation_id or not self.correlation_id.strip():
            raise ValueError("lifecycle transition correlation id is required")


class IntakeAssetKind(Enum):
    """The canonical stage 0 "Intake" required asset kinds.

    SPEC.md section 4, stage 0 "Intake" names the required asset package: client
    record, signed scope, billing confirmation, questionnaire, existing and brand
    asset inventories, access checklist, baseline measures, workspace,
    communication channel, timeline, responsibilities and launch definition. The
    string values match the governance stage 0-10 template's asset kinds exactly
    so a gate can pin an exact asset version per kind.
    """

    CLIENT_RECORD = "client-record"
    SIGNED_SCOPE = "signed-scope"
    BILLING_CONFIRMATION = "billing-confirmation"
    INTAKE_QUESTIONNAIRE = "intake-questionnaire"
    BRAND_ASSET_INVENTORY = "brand-asset-inventory"
    ACCESS_CHECKLIST = "access-checklist"
    BASELINE_MEASURES = "baseline-measures"
    WORKSPACE = "workspace"
    COMMUNICATION_CHANNEL = "communication-channel"
    TIMELINE = "timeline"
    RESPONSIBILITIES = "responsibilities"
    LAUNCH_DEFINITION = "launch-definition"


CANONICAL_INTAKE_KINDS: tuple[IntakeAssetKind, ...] = tuple(IntakeAssetKind)


def _require_intake_text(value: str, label: str) -> str:
    if not value or not value.strip():
        raise InvalidIntakeAssetError(f"{label} is required")
    return value


@dataclass(frozen=True)
class IntakeAsset:
    """One stage 0 intake asset with a kind, an exact version, an owner and a source.

    SPEC.md section 1: every output has a source, status, owner and next action.
    SPEC.md section 4, stage 0: the required asset package is a set of named
    assets. SPEC.md sections 3 and 4 require a passing gate to pin the exact
    asset versions, so an asset carries a typed positive version rather than
    burying it in its display id. The asset is frozen and reject-only, so an asset
    that leaves its kind, version, owner, summary or evidence unspecified cannot
    be represented as a real intake asset. Evidence is recorded as Knowledge claim
    ids so the checkpoint can require it to be directly sourced.
    """

    asset_id: str
    tenant_id: str
    kind: IntakeAssetKind
    version: int
    owner: str
    summary: str
    evidence_claim_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("intake asset id", self.asset_id),
            ("intake asset tenant id", self.tenant_id),
            ("intake asset owner", self.owner),
            ("intake asset summary", self.summary),
        ):
            _require_intake_text(value, label)
        if not isinstance(self.kind, IntakeAssetKind):
            raise InvalidIntakeAssetError(
                "intake asset kind must be a canonical IntakeAssetKind"
            )
        if not isinstance(self.version, int) or self.version < 1:
            raise InvalidIntakeAssetError(
                "an intake asset requires a positive integer version to be "
                "pinned as exact gate evidence"
            )
        if not self.evidence_claim_ids:
            raise InvalidIntakeAssetError(
                "an intake asset requires at least one source claim"
            )
        for claim_id in self.evidence_claim_ids:
            _require_intake_text(claim_id, "intake asset evidence claim id")

    @property
    def canonical_kind(self) -> str:
        """The asset kind exactly as the governance stage template names it."""
        return self.kind.value

    def stage_asset_version(self) -> StageAssetVersion:
        """Project this real asset onto the governance exact-version evidence.

        The projection reuses the asset's own id, tenant, canonical kind and
        version; governance still pins it for the workspace tenant, so a
        cross-client asset is refused rather than silently authorized (SPEC.md
        sections 3 and 11).
        """
        return StageAssetVersion(
            asset_id=self.asset_id,
            tenant_id=self.tenant_id,
            kind=self.canonical_kind,
            version=self.version,
        )



@dataclass(frozen=True)
class IntakePackage:
    """The collected stage 0 intake assets behind the "Production Ready" gate.

    SPEC.md section 4, stage 0 "Intake": the required asset package is a
    collection of required assets, and SPEC.md section 3 requires every child
    resource to belong to exactly one client. The package may be built up while
    incomplete, and reports its missing kinds; the "Production Ready" checkpoint
    is a separate policy decision, so an incomplete package is never silently
    treated as complete.
    """

    package_id: str
    tenant_id: str
    assets: tuple[IntakeAsset, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("intake package id", self.package_id),
            ("intake package tenant id", self.tenant_id),
        ):
            if not value or not value.strip():
                raise InvalidIntakePackageError(f"{label} is required")
        seen: set[IntakeAssetKind] = set()
        for asset in self.assets:
            if not isinstance(asset, IntakeAsset):
                raise InvalidIntakePackageError(
                    "an intake package may only contain IntakeAsset entries"
                )
            if asset.tenant_id != self.tenant_id:
                raise TenantBoundaryError(
                    f"intake asset {asset.asset_id!r} belongs to tenant "
                    f"{asset.tenant_id!r}, not package tenant {self.tenant_id!r}"
                )
            if asset.kind in seen:
                raise InvalidIntakePackageError(
                    f"intake package repeats asset kind {asset.kind.value!r}"
                )
            seen.add(asset.kind)

    @property
    def kinds(self) -> frozenset[IntakeAssetKind]:
        return frozenset(asset.kind for asset in self.assets)

    def has(self, kind: IntakeAssetKind) -> bool:
        return kind in self.kinds

    def asset(self, kind: IntakeAssetKind) -> IntakeAsset:
        for asset in self.assets:
            if asset.kind is kind:
                return asset
        raise InvalidIntakePackageError(
            f"intake package has no {kind.value!r} asset"
        )

    def missing_kinds(self) -> tuple[IntakeAssetKind, ...]:
        present = self.kinds
        return tuple(kind for kind in CANONICAL_INTAKE_KINDS if kind not in present)

    @property
    def is_complete(self) -> bool:
        return not self.missing_kinds()

    @property
    def owners(self) -> frozenset[str]:
        return frozenset(asset.owner for asset in self.assets)

    def stage_asset_versions(self) -> tuple[StageAssetVersion, ...]:
        """Yield the governance exact-version evidence for the assets present.

        This is the bridge from the Engagement stage 0 intake assets to the
        version-per-kind evidence a governance ``StageGate`` pins. Projecting only
        the assets the package holds keeps a partial package honest: the gate
        assembler still refuses a package that is missing a canonical kind
        (SPEC.md sections 3, 4 and 11).
        """
        return tuple(asset.stage_asset_version() for asset in self.assets)

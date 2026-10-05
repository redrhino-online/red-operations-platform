"""Value objects for the Commercial Design bounded context (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from redops.contexts.commercial.domain.errors import (
    AudienceReachObservationError,
    CampaignMessageTenantBoundaryError,
    ContentCrusherDependencyError,
    ContentCrusherObservationError,
    ContentCrusherTenantBoundaryError,
    ContentPlanDependencyError,
    ContentPlanObservationError,
    ContentPlanTenantBoundaryError,
    ContentPlanThemeError,
    ContentRoadmapDependencyError,
    ContentRoadmapFormatError,
    ContentRoadmapObservationError,
    ContentRoadmapTenantBoundaryError,
    ContentSyndicationDependencyError,
    ContentSyndicationFormatError,
    ContentSyndicationObservationError,
    ContentSyndicationTenantBoundaryError,
    InvalidContentCrusherError,
    InvalidContentPlanError,
    InvalidContentSyndicationError,
    CurrencyTenantBoundaryError,
    DiagnosisTenantBoundaryError,
    DiagnosticTenantBoundaryError,
    FunnelFinderObservationError,
    FunnelFinderTenantBoundaryError,
    InvalidAudienceReachError,
    InvalidAvatarProfileError,
    InvalidBusinessSnapshotError,
    InvalidCampaignMessagePackageError,
    InvalidContentRoadmapError,
    InvalidCurrencyInventoryError,
    InvalidCurrencyPackageError,
    InvalidDeliverySpecificationError,
    InvalidDiagnosisPackageError,
    InvalidDiagnosticPackageError,
    InvalidFunnelFinderError,
    InvalidMarketAwarenessMapError,
    InvalidMillionDollarMessageError,
    InvalidNurtureError,
    InvalidOfferError,
    InvalidOfferFunnelAuditError,
    InvalidOfferPackageError,
    InvalidPositioningDecisionError,
    InvalidProductProgramError,
    InvalidSignaturePackageError,
    InvalidTargetMarketMatchmakerError,
    ProductProgramDependencyError,
    ProductProgramObservationError,
    ProductProgramPricingError,
    ProductProgramTenantBoundaryError,
    MarketAwarenessTargetingError,
    NurtureDependencyError,
    NurtureObservationError,
    NurtureSequenceError,
    NurtureTenantBoundaryError,
    OfferTenantBoundaryError,
    SignatureTenantBoundaryError,
    TargetMarketObservationError,
    TargetMarketTenantBoundaryError,
)
from redops.contexts.governance.domain.value_objects import StageAssetVersion
from redops.contexts.method.domain.entities import DiagnosticModel, SignatureSolution
from redops.contexts.method.domain.transformations import (
    THIRTEEN_TRANSFORMATIONS_KIND,
    ThirteenTransformations,
)
from redops.contexts.method.domain.value_objects import (
    ImpactAssessment,
    PrimaryCurrency,
    SemanticVersion,
)

if TYPE_CHECKING:
    from redops.contexts.commercial.domain.entities import (
        CampaignMessage,
        OfferVersion,
    )


class OfferState(Enum):
    """The readiness state of an OfferVersion (SPEC.md sections 3 and 4).

    A draft offer can become production ready only when its method dependency
    is approved. An upstream method change moves a production ready offer back
    to review required, and a terminal offer cannot be revived.
    """

    DRAFT = "draft"
    PRODUCTION_READY = "production_ready"
    REVIEW_REQUIRED = "review_required"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"

    @property
    def is_terminal(self) -> bool:
        return self in _TERMINAL_OFFER_STATES


_TERMINAL_OFFER_STATES = frozenset({OfferState.SUPERSEDED, OfferState.ARCHIVED})


class CampaignMessageState(Enum):
    """The readiness state of a CampaignMessage (SPEC.md sections 3 and 4).

    A draft message can be approved only when its avatar, currency, problem,
    promise, method, product and CTA agree with the approved stage 5 offer it is
    grounded on. An upstream change moves an approved message back to review
    required, and a terminal message cannot be revived.
    """

    DRAFT = "draft"
    APPROVED = "approved"
    REVIEW_REQUIRED = "review_required"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"

    @property
    def is_terminal(self) -> bool:
        return self in _TERMINAL_MESSAGE_STATES


_TERMINAL_MESSAGE_STATES = frozenset(
    {CampaignMessageState.SUPERSEDED, CampaignMessageState.ARCHIVED}
)



@dataclass(frozen=True)
class MethodReference:
    """An exact dependency on one approved method version and intended use.

    Pinning the method id, semantic version and intended use means a later
    method revision does not silently satisfy the reference (SPEC.md section 3).
    """

    method_id: str
    version: SemanticVersion
    intended_use: str

    def __post_init__(self) -> None:
        if not self.method_id or not self.method_id.strip():
            raise InvalidOfferError("method reference id is required")
        if not self.intended_use or not self.intended_use.strip():
            raise InvalidOfferError("method reference intended use is required")


@dataclass(frozen=True)
class OfferImpactAssessment:
    """The discovered effect of an approved method change on dependent offers.

    SPEC.md section 4: a change marks dependent offers review required with a
    human owner and due date. The `offers` are the newly re-marked versions and
    `impact` is the owned review queue, so the discovery is a real traversal of
    `OfferVersion.method_refs` rather than a caller-supplied list.
    """

    impact: ImpactAssessment
    offers: tuple["OfferVersion", ...] = ()

    @property
    def review_required_offer_ids(self) -> tuple[str, ...]:
        return tuple(offer.offer_id for offer in self.offers)


@dataclass(frozen=True)
class StepDelivery:
    """One stage 5 delivery row for a named method step.

    SPEC.md section 4, stage 5 "Productize" and its "Offer Locked" checkpoint:
    every method step has an action, actor, deliverable, timing and measure. The
    value object is frozen and reject-only, so a method step without a stated
    actor, deliverable, timing or measure cannot be represented as delivered.
    """

    step_id: str
    tenant_id: str
    action: str
    actor: str
    deliverable: str
    timing: str
    measure: str

    def __post_init__(self) -> None:
        for label, value in (
            ("step delivery step id", self.step_id),
            ("step delivery tenant id", self.tenant_id),
            ("step delivery action", self.action),
            ("step delivery actor", self.actor),
            ("step delivery deliverable", self.deliverable),
            ("step delivery timing", self.timing),
            ("step delivery measure", self.measure),
        ):
            if not value or not value.strip():
                raise InvalidDeliverySpecificationError(f"{label} is required")


@dataclass(frozen=True)
class DeliverySpecification:
    """The stage 5 delivery specification, locked at "Offer Locked".

    SPEC.md section 4, stage 5 "Productize": the required asset package is the
    delivery model, duration, modules, responsibilities, support cadence, stage
    deliverables, outcome measures, pricing and payments, scope, guarantee
    decision, eligibility and offer stack, and the checkpoint requires that
    "every method step has an action, actor, deliverable, timing and measure".

    The specification is grounded on the exact locked stage 4 `SignatureSolution`
    so it cannot declare deliveries for steps the method does not have, or leave
    a method step undelivered. It is frozen and reject-only: an approval pins an
    exact asset version rather than mutating it (SPEC.md section 3).
    """

    delivery_id: str
    tenant_id: str
    signature_solution: SignatureSolution
    delivery_model: str
    duration: str
    modules: tuple[str, ...]
    responsibilities: tuple[str, ...]
    support_cadence: str
    step_deliveries: tuple[StepDelivery, ...]
    outcome_measures: tuple[str, ...]
    pricing_payments: str
    scope: str
    guarantee_decision: str
    eligibility: str
    offer_stack: tuple[str, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("delivery specification id", self.delivery_id),
            ("delivery specification tenant id", self.tenant_id),
            ("delivery model", self.delivery_model),
            ("delivery duration", self.duration),
            ("support cadence", self.support_cadence),
            ("pricing and payments", self.pricing_payments),
            ("delivery scope", self.scope),
            ("guarantee decision", self.guarantee_decision),
            ("delivery eligibility", self.eligibility),
        ):
            if not value or not value.strip():
                raise InvalidDeliverySpecificationError(f"{label} is required")
        for label, entries in (
            ("modules", self.modules),
            ("responsibilities", self.responsibilities),
            ("outcome measures", self.outcome_measures),
            ("offer stack", self.offer_stack),
        ):
            if not entries:
                raise InvalidDeliverySpecificationError(
                    f"a delivery specification requires at least one {label} entry"
                )
            for entry in entries:
                if not entry or not entry.strip():
                    raise InvalidDeliverySpecificationError(
                        f"{label} entries must not be blank"
                    )
        if self.signature_solution.tenant_id != self.tenant_id:
            raise InvalidDeliverySpecificationError(
                "a delivery specification cannot cover another tenant's method"
            )
        if not self.step_deliveries:
            raise InvalidDeliverySpecificationError(
                "a delivery specification requires a delivery for every method step"
            )
        method_steps = {step.step_id for step in self.signature_solution.steps}
        delivered: set[str] = set()
        for row in self.step_deliveries:
            if row.tenant_id != self.tenant_id:
                raise InvalidDeliverySpecificationError(
                    "a delivery specification cannot mix deliveries from another "
                    "tenant"
                )
            if row.step_id in delivered:
                raise InvalidDeliverySpecificationError(
                    f"method step {row.step_id!r} has more than one delivery"
                )
            if row.step_id not in method_steps:
                raise InvalidDeliverySpecificationError(
                    f"delivery step {row.step_id!r} is not a method step"
                )
            delivered.add(row.step_id)
        missing = method_steps - delivered
        if missing:
            raise InvalidDeliverySpecificationError(
                "every method step requires a delivery, missing "
                f"{sorted(missing)}"
            )

    def delivery_for(self, step_id: str) -> StepDelivery:
        """Return the single delivery row for a named method step."""
        for row in self.step_deliveries:
            if row.step_id == step_id:
                return row
        raise InvalidDeliverySpecificationError(
            f"method step {step_id!r} has no delivery"
        )


@dataclass(frozen=True)
class AvatarProfile:
    """The stage 1 avatar, locked at the "Avatar Locked" checkpoint.

    SPEC.md section 4, stage 1 "Diagnose": the required asset package is the
    business snapshot, offer and funnel audit, avatar with demographics and
    psychographics, pains, goals, consequences of inaction, awareness, customer
    evidence and voice notes. The checkpoint requires that "a stranger can
    recognize who the customer is, what matters, and why now". The profile is
    frozen and reject-only, so an avatar that leaves the person, what matters or
    why now unspecified cannot be represented as a lockable avatar. Customer
    evidence is recorded as Knowledge claim ids so the lock can require it to be
    directly sourced (SPEC.md sections 1 and 11).
    """

    avatar_id: str
    tenant_id: str
    name: str
    demographics: str
    psychographics: str
    pains: tuple[str, ...]
    goals: tuple[str, ...]
    consequences_of_inaction: tuple[str, ...]
    awareness: str
    customer_evidence_claim_ids: tuple[str, ...]
    voice_notes: tuple[str, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("avatar profile id", self.avatar_id),
            ("avatar profile tenant id", self.tenant_id),
            ("avatar name", self.name),
            ("avatar demographics", self.demographics),
            ("avatar psychographics", self.psychographics),
            ("avatar awareness", self.awareness),
        ):
            if not value or not value.strip():
                raise InvalidAvatarProfileError(f"{label} is required")
        for label, entries in (
            ("pains", self.pains),
            ("goals", self.goals),
            ("consequences of inaction", self.consequences_of_inaction),
            ("customer evidence", self.customer_evidence_claim_ids),
            ("voice notes", self.voice_notes),
        ):
            if not entries:
                raise InvalidAvatarProfileError(
                    f"an avatar profile requires at least one {label} entry"
                )
            for entry in entries:
                if not entry or not entry.strip():
                    raise InvalidAvatarProfileError(
                        f"{label} entries must not be blank"
                    )


def _require_entries(
    entries: tuple[str, ...], label: str, error: type[ValueError]
) -> None:
    if not entries:
        raise error(f"requires at least one {label} entry")
    for entry in entries:
        if not entry or not entry.strip():
            raise error(f"{label} entries must not be blank")


@dataclass(frozen=True)
class BusinessSnapshot:
    """The stage 1 business snapshot, an input to the "Avatar Locked" checkpoint.

    SPEC.md section 4, stage 1 "Diagnose": the required asset package names the
    business snapshot alongside the offer and funnel audit and the avatar. It
    records the current business state the diagnosis is grounded on: the business
    model, the offers currently sold, how demand currently arrives, the constraints
    on the business, and a narrative. It is frozen and reject-only, and it carries
    the Knowledge claim ids that evidence it because SPEC.md section 1 requires
    every output to have a source.
    """

    snapshot_id: str
    tenant_id: str
    business_model: str
    current_offers: tuple[str, ...]
    lead_sources: tuple[str, ...]
    constraints: tuple[str, ...]
    narrative: str
    evidence_claim_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("business snapshot id", self.snapshot_id),
            ("business snapshot tenant id", self.tenant_id),
            ("business model", self.business_model),
            ("business snapshot narrative", self.narrative),
        ):
            if not value or not value.strip():
                raise InvalidBusinessSnapshotError(f"{label} is required")
        for label, entries in (
            ("current offers", self.current_offers),
            ("lead sources", self.lead_sources),
            ("constraints", self.constraints),
            ("evidence", self.evidence_claim_ids),
        ):
            _require_entries(entries, label, InvalidBusinessSnapshotError)


@dataclass(frozen=True)
class OfferFunnelAudit:
    """The stage 1 offer and funnel audit, an input to the "Avatar Locked" checkpoint.

    SPEC.md section 4, stage 1 "Diagnose": the required asset package names the
    offer and funnel audit. It records what the diagnosis found about the current
    offer and customer path: the offer findings, the funnel steps, the conversion
    evidence, the identified gaps, and a narrative. It is frozen and reject-only,
    and it carries the Knowledge claim ids that evidence it because SPEC.md section
    1 requires every output to have a source.
    """

    audit_id: str
    tenant_id: str
    offer_findings: tuple[str, ...]
    funnel_steps: tuple[str, ...]
    conversion_evidence: tuple[str, ...]
    gaps: tuple[str, ...]
    narrative: str
    evidence_claim_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("offer and funnel audit id", self.audit_id),
            ("offer and funnel audit tenant id", self.tenant_id),
            ("offer and funnel audit narrative", self.narrative),
        ):
            if not value or not value.strip():
                raise InvalidOfferFunnelAuditError(f"{label} is required")
        for label, entries in (
            ("offer findings", self.offer_findings),
            ("funnel steps", self.funnel_steps),
            ("conversion evidence", self.conversion_evidence),
            ("gaps", self.gaps),
            ("evidence", self.evidence_claim_ids),
        ):
            _require_entries(entries, label, InvalidOfferFunnelAuditError)


class MarketAwarenessLevel(Enum):
    """The canon's five levels of market awareness (canon file 04).

    The canon uses the levels to place a prospect before any research or message
    is shaped (canon file 04: "you have to understand where your prospect is"):
    completely unaware, problem aware, solution aware, product aware and most
    aware. The rank orders them from least to most aware along the buying path,
    and the completely unaware are explicitly not the initial target (canon file
    04: "which is who we definitely do not want to sell to initially").
    """

    COMPLETELY_UNAWARE = "completely_unaware"
    PROBLEM_AWARE = "problem_aware"
    SOLUTION_AWARE = "solution_aware"
    PRODUCT_AWARE = "product_aware"
    MOST_AWARE = "most_aware"

    @property
    def rank(self) -> int:
        """The position of the level along the buying path, from 0 to 4."""
        return _MARKET_AWARENESS_RANK[self]

    @property
    def is_initially_targetable(self) -> bool:
        """Whether the canon treats this level as an initial target."""
        return self is not MarketAwarenessLevel.COMPLETELY_UNAWARE


_MARKET_AWARENESS_RANK: dict[MarketAwarenessLevel, int] = {
    level: index for index, level in enumerate(MarketAwarenessLevel)
}

AWARENESS_MAP_KIND = "awareness-map"


@dataclass(frozen=True)
class MarketAwarenessMap:
    """The stage 1 market awareness map for one client and one level.

    SPEC.md section 12.3 maps the market awareness levels to stage 1 "Diagnose"
    and section 12.5 records the positioning and decision tools as a canon gap
    informed by canon file 04. The map names the awareness level the market
    currently sits at, the research evidence that places it there (canon file 04
    reads the market's own language from Amazon reviews, Quora, Reddit, Facebook
    groups and search), what a message must supply at that level, and an optional
    retarget level further down the funnel. It is frozen and reject-only, so an
    untyped level or a map with no evidence or message requirements cannot be
    represented as stage 1 awareness-map evidence, and it never authorizes
    outreach or spend (SPEC.md sections 4 and 9).
    """

    map_id: str
    tenant_id: str
    primary_level: MarketAwarenessLevel
    research_evidence: tuple[str, ...]
    message_requirements: tuple[str, ...]
    retarget_level: MarketAwarenessLevel | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("market awareness map id", self.map_id),
            ("market awareness map tenant id", self.tenant_id),
        ):
            if not value or not value.strip():
                raise InvalidMarketAwarenessMapError(f"{label} is required")
        if not isinstance(self.primary_level, MarketAwarenessLevel):
            raise InvalidMarketAwarenessMapError(
                "a market awareness map requires one of the five canon awareness "
                "levels"
            )
        _require_entries(
            self.research_evidence,
            "research evidence",
            InvalidMarketAwarenessMapError,
        )
        _require_entries(
            self.message_requirements,
            "message requirements",
            InvalidMarketAwarenessMapError,
        )
        if self.retarget_level is not None:
            if not isinstance(self.retarget_level, MarketAwarenessLevel):
                raise InvalidMarketAwarenessMapError(
                    "a retarget level must be one of the five canon awareness "
                    "levels"
                )
            if self.retarget_level.rank <= self.primary_level.rank:
                raise MarketAwarenessTargetingError(
                    f"market awareness map {self.map_id!r} retargets "
                    f"{self.retarget_level.value!r}, which is not further down the "
                    f"funnel than its primary level {self.primary_level.value!r}"
                )

    def as_stage_asset(self, *, version: int) -> StageAssetVersion:
        """Project the map onto exact ``awareness-map`` gate evidence.

        The governance gate pins one exact ``StageAssetVersion`` per canonical
        kind, so the map is projected at a positive integer version and a
        versionless projection is refused rather than silently pinned (SPEC.md
        sections 3 and 4).
        """
        if not isinstance(version, int) or version < 1:
            raise InvalidMarketAwarenessMapError(
                "the market awareness map version must be a positive integer so "
                "the stage 1 gate can pin the reviewed asset at an exact version"
            )
        return StageAssetVersion(
            asset_id=self.map_id,
            tenant_id=self.tenant_id,
            kind=AWARENESS_MAP_KIND,
            version=version,
        )


CANONICAL_DIAGNOSIS_KINDS: tuple[str, ...] = (
    "avatar-profile",
    "pains",
    "goals",
    "consequences-of-inaction",
    "awareness-map",
    "audience-reach-estimate",
    "target-market-match",
    "customer-evidence",
    "voice-notes",
    "business-snapshot",
    "offer-funnel-audit",
)

_AVATAR_DIAGNOSIS_KINDS: tuple[str, ...] = (
    "avatar-profile",
    "pains",
    "goals",
    "consequences-of-inaction",
    "customer-evidence",
    "voice-notes",
)


@dataclass(frozen=True)
class DiagnosisPackage:
    """The reviewed stage 1 assets, projected to the canonical gate kinds.

    SPEC.md section 4, stage 1 "Diagnose": the required asset package enumerates
    the avatar with demographics, psychographics, pains, goals, consequences of
    inaction, awareness, customer evidence and voice notes alongside the business
    snapshot and the offer and funnel audit. The Commercial context reviews those
    as three rich value objects (``AvatarProfile``, ``BusinessSnapshot``,
    ``OfferFunnelAudit``); this package is the bridge to the governance gate,
    which pins one exact ``StageAssetVersion`` per canonical kind. The avatar
    value carries the content for its seven kinds; the business snapshot and offer
    and funnel audit each satisfy one kind.

    SPEC.md sections 4 and 12.3 (canon files 02 and 03) also make the measured
    market a stage 1 input, so the typed ``AudienceReachEstimate`` is carried and
    projected as the ``audience-reach-estimate`` kind. The canon's positioning
    and decision tools (canon file 00) force a defensible choice of the target
    market, so the typed ``TargetMarketMatchmaker`` is carried and projected as
    the ``target-market-match`` kind. Per the owner decision in SPEC.md section
    12.5 a canon-informed asset already implemented is a required kind of its
    target stage, never a new stage.

    SPEC.md sections 3 and 4 require a passing gate to pin the exact evidence, so
    each reviewed asset is projected with a positive integer version and a blank
    version or a cross-tenant value is refused rather than silently pinned. The
    canon (SPEC.md section 12.3: stage 1 uses canon files 02, 03 and 04) groups
    the avatar's pains, goals, consequences and why into one Avatar Goals Grid,
    but the SPEC stage 1 package enumerates them as separate required items, so
    they are projected as separate kinds while the avatar carries the content.

    The ``awareness-map`` kind is pinned from the typed ``MarketAwarenessMap``
    canon asset, not from the avatar's free-text awareness note (SPEC.md sections
    4 and 12.5). Requiring the typed map with its research evidence and message
    requirements makes the gate reject a stage 1 package whose awareness position
    is an untyped note rather than a researched, targetable position.
    """

    package_id: str
    tenant_id: str
    avatar: AvatarProfile
    avatar_version: int
    business_snapshot: BusinessSnapshot
    business_snapshot_version: int
    offer_funnel_audit: OfferFunnelAudit
    offer_funnel_audit_version: int
    awareness_map: MarketAwarenessMap
    awareness_map_version: int
    audience_reach_estimate: AudienceReachEstimate
    audience_reach_estimate_version: int
    target_market_match: TargetMarketMatchmaker
    target_market_match_version: int

    def __post_init__(self) -> None:
        for label, value in (
            ("diagnosis package id", self.package_id),
            ("diagnosis package tenant id", self.tenant_id),
        ):
            if not value or not value.strip():
                raise InvalidDiagnosisPackageError(f"{label} is required")
        for label, value, expected in (
            ("avatar", self.avatar, AvatarProfile),
            ("business snapshot", self.business_snapshot, BusinessSnapshot),
            ("offer and funnel audit", self.offer_funnel_audit,
             OfferFunnelAudit),
            ("awareness map", self.awareness_map, MarketAwarenessMap),
            ("audience reach estimate", self.audience_reach_estimate,
             AudienceReachEstimate),
            ("target market match", self.target_market_match,
             TargetMarketMatchmaker),
        ):
            if not isinstance(value, expected):
                raise InvalidDiagnosisPackageError(
                    f"diagnosis {label} must be a typed reviewed asset"
                )
            if value.tenant_id != self.tenant_id:
                raise DiagnosisTenantBoundaryError(
                    f"diagnosis {label} belongs to tenant {value.tenant_id!r}, "
                    f"not package tenant {self.tenant_id!r}"
                )
        for label, value in (
            ("avatar version", self.avatar_version),
            ("business snapshot version", self.business_snapshot_version),
            ("offer and funnel audit version", self.offer_funnel_audit_version),
            ("awareness map version", self.awareness_map_version),
            ("audience reach estimate version",
             self.audience_reach_estimate_version),
            ("target market match version", self.target_market_match_version),
        ):
            if not isinstance(value, int) or value < 1:
                raise InvalidDiagnosisPackageError(
                    f"{label} must be a positive integer so the stage 1 gate can "
                    "pin the reviewed asset at an exact version"
                )

    @property
    def kinds(self) -> frozenset[str]:
        """The canonical kinds the three reviewed assets project onto."""
        return frozenset(CANONICAL_DIAGNOSIS_KINDS)

    def missing_kinds(self) -> tuple[str, ...]:
        """Canonical stage 1 kinds not covered by the projected assets."""
        covered = {asset.kind for asset in self.stage_asset_versions()}
        return tuple(
            kind for kind in CANONICAL_DIAGNOSIS_KINDS if kind not in covered
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_kinds()

    def _avatar_asset(self, kind: str) -> StageAssetVersion:
        return StageAssetVersion(
            asset_id=self.avatar.avatar_id,
            tenant_id=self.tenant_id,
            kind=kind,
            version=self.avatar_version,
        )

    def stage_asset_versions(self) -> tuple[StageAssetVersion, ...]:
        """Project the reviewed stage 1 assets onto exact governance evidence.

        The avatar value satisfies its seven canonical kinds at one exact version;
        the business snapshot and offer and funnel audit satisfy one kind each.
        Governance still pins each projection for the workspace tenant, so a
        cross-client value is refused rather than silently authorized (SPEC.md
        sections 3, 4 and 11).
        """
        return (
            *(self._avatar_asset(kind) for kind in _AVATAR_DIAGNOSIS_KINDS),
            self.awareness_map.as_stage_asset(version=self.awareness_map_version),
            self.audience_reach_estimate.as_stage_asset(
                version=self.audience_reach_estimate_version
            ),
            self.target_market_match.as_stage_asset(
                version=self.target_market_match_version
            ),
            StageAssetVersion(
                asset_id=self.business_snapshot.snapshot_id,
                tenant_id=self.tenant_id,
                kind="business-snapshot",
                version=self.business_snapshot_version,
            ),
            StageAssetVersion(
                asset_id=self.offer_funnel_audit.audit_id,
                tenant_id=self.tenant_id,
                kind="offer-funnel-audit",
                version=self.offer_funnel_audit_version,
            ),
        )


@dataclass(frozen=True)
class CurrencyInventory:
    """The stage 2 currency inventory: the reach the offer could claim.

    SPEC.md section 4, stage 2 "Position": the required asset package names the
    category, the currency inventory and the primary currency. The reference
    model canon (SPEC.md section 12.3: stage 2 uses canon files 04, 05 and 06)
    has the currency calculator leave the general category behind and list every
    currency the offer can increase or decrease before the one currency is
    chosen. The value object is frozen and reject-only, so an inventory that
    names no category or no currency on either side cannot be represented as a
    reviewed stage 2 asset.
    """

    inventory_id: str
    tenant_id: str
    category: str
    currencies_to_increase: tuple[str, ...]
    currencies_to_decrease: tuple[str, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("currency inventory id", self.inventory_id),
            ("currency inventory tenant id", self.tenant_id),
            ("currency category", self.category),
        ):
            if not value or not value.strip():
                raise InvalidCurrencyInventoryError(f"{label} is required")
        _require_entries(
            self.currencies_to_increase,
            "currencies to increase",
            InvalidCurrencyInventoryError,
        )
        _require_entries(
            self.currencies_to_decrease,
            "currencies to decrease",
            InvalidCurrencyInventoryError,
        )


@dataclass(frozen=True)
class PositioningDecision:
    """The stage 2 positioning decision: the problem, prognosis and acceptance line.

    SPEC.md section 4, stage 2 "Position": the required asset package names the
    horizon, qualifications, transformation statement and core problem. The canon
    (files 05 and 06) frames this as the four step problem, prescription and
    prognosis with a stated acceptance and rejection line. The value object is
    frozen and reject-only, so a decision that leaves the problem, the
    transformation, the horizon or either side of the acceptance line
    unspecified cannot be represented as a reviewed stage 2 asset.
    """

    decision_id: str
    tenant_id: str
    core_problem: str
    transformation_statement: str
    horizon: str
    qualifications: tuple[str, ...]
    disqualifications: tuple[str, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("positioning decision id", self.decision_id),
            ("positioning decision tenant id", self.tenant_id),
            ("positioning core problem", self.core_problem),
            ("positioning transformation statement", self.transformation_statement),
            ("positioning horizon", self.horizon),
        ):
            if not value or not value.strip():
                raise InvalidPositioningDecisionError(f"{label} is required")
        _require_entries(
            self.qualifications,
            "qualifications",
            InvalidPositioningDecisionError,
        )
        _require_entries(
            self.disqualifications,
            "disqualifications",
            InvalidPositioningDecisionError,
        )


@dataclass(frozen=True)
class MillionDollarMessage:
    """The stage 2 million dollar message and its formula components.

    SPEC.md section 4, stage 2 "Position": the required asset package ends with
    the Million Dollar Message. The canon (file 06) states the formula as a
    single avatar times one currency with a metric and a timeline minus the pain
    removed. The value object is frozen and reject-only, so a message that leaves
    the avatar, currency, metric, timeline or pain unspecified cannot be
    represented as a complete stage 2 asset.
    """

    message_id: str
    tenant_id: str
    avatar: str
    currency: str
    metric: str
    timeline: str
    pain: str
    message: str

    def __post_init__(self) -> None:
        for label, value in (
            ("million dollar message id", self.message_id),
            ("million dollar message tenant id", self.tenant_id),
            ("million dollar message avatar", self.avatar),
            ("million dollar message currency", self.currency),
            ("million dollar message metric", self.metric),
            ("million dollar message timeline", self.timeline),
            ("million dollar message pain", self.pain),
            ("million dollar message text", self.message),
        ):
            if not value or not value.strip():
                raise InvalidMillionDollarMessageError(f"{label} is required")


CANONICAL_CURRENCY_KINDS: tuple[str, ...] = (
    "category",
    "currency-inventory",
    "primary-currency",
    "current-measures",
    "desired-measures",
    "horizon",
    "qualifications",
    "transformation-statement",
    "core-problem",
    "million-dollar-message",
)


@dataclass(frozen=True)
class CurrencyPackage:
    """The reviewed stage 2 assets, projected to the ten canonical gate kinds.

    SPEC.md section 4, stage 2 "Position" and its "Currency Locked" checkpoint: a
    stage is complete only when its required assets exist, pass the checkpoint and
    receive approval for downstream use, and a passing gate pins the exact
    evidence. The Commercial context reviews the stage 2 package as four rich
    value objects; this package is the bridge to the governance gate, which pins
    one exact ``StageAssetVersion`` per canonical kind. The currency inventory
    satisfies the category and inventory kinds, the ``PrimaryCurrency`` satisfies
    the primary currency and its two measures, the positioning decision satisfies
    the horizon, qualifications, transformation statement and core problem, and
    the million dollar message satisfies its own kind.

    The canon (SPEC.md section 12.3: stage 2 uses canon files 04, 05 and 06) also
    frames the message as the avatar times the currency minus the pain; the SPEC
    stage 2 package enumerates those as separate required items, so they are
    projected as separate kinds while the message carries the composed text.
    Each reviewed asset is projected with a positive integer version, and a blank
    version, blank identity or cross-tenant value is refused rather than silently
    pinned (SPEC.md sections 3 and 4).
    """

    package_id: str
    tenant_id: str
    inventory: CurrencyInventory
    inventory_version: int
    positioning: PositioningDecision
    positioning_version: int
    primary_currency: PrimaryCurrency
    primary_currency_version: int
    million_dollar_message: MillionDollarMessage
    million_dollar_message_version: int

    def __post_init__(self) -> None:
        for label, value in (
            ("currency package id", self.package_id),
            ("currency package tenant id", self.tenant_id),
        ):
            if not value or not value.strip():
                raise InvalidCurrencyPackageError(f"{label} is required")
        for label, value in (
            ("currency inventory", self.inventory),
            ("positioning decision", self.positioning),
            ("primary currency", self.primary_currency),
            ("million dollar message", self.million_dollar_message),
        ):
            if value.tenant_id != self.tenant_id:
                raise CurrencyTenantBoundaryError(
                    f"stage 2 {label} belongs to tenant {value.tenant_id!r}, "
                    f"not package tenant {self.tenant_id!r}"
                )
        for label, value in (
            ("currency inventory version", self.inventory_version),
            ("positioning decision version", self.positioning_version),
            ("primary currency version", self.primary_currency_version),
            ("million dollar message version", self.million_dollar_message_version),
        ):
            if not isinstance(value, int) or value < 1:
                raise InvalidCurrencyPackageError(
                    f"{label} must be a positive integer so the stage 2 gate can "
                    "pin the reviewed asset at an exact version"
                )

    @property
    def kinds(self) -> frozenset[str]:
        """The canonical kinds the reviewed stage 2 assets project onto."""
        return frozenset(CANONICAL_CURRENCY_KINDS)

    def missing_kinds(self) -> tuple[str, ...]:
        """Canonical stage 2 kinds not covered by the projected assets."""
        covered = {asset.kind for asset in self.stage_asset_versions()}
        return tuple(
            kind for kind in CANONICAL_CURRENCY_KINDS if kind not in covered
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_kinds()

    def stage_asset_versions(self) -> tuple[StageAssetVersion, ...]:
        """Project the reviewed stage 2 assets onto exact governance evidence.

        Governance pins each projection for the workspace tenant, so a
        cross-client value is refused rather than silently authorized (SPEC.md
        sections 3, 4 and 11).
        """
        inventory_version = self.inventory_version
        positioning_version = self.positioning_version
        currency_version = self.primary_currency_version
        message_version = self.million_dollar_message_version
        return (
            StageAssetVersion(
                asset_id=self.inventory.inventory_id,
                tenant_id=self.tenant_id,
                kind="category",
                version=inventory_version,
            ),
            StageAssetVersion(
                asset_id=self.inventory.inventory_id,
                tenant_id=self.tenant_id,
                kind="currency-inventory",
                version=inventory_version,
            ),
            StageAssetVersion(
                asset_id=self.primary_currency.currency,
                tenant_id=self.tenant_id,
                kind="primary-currency",
                version=currency_version,
            ),
            StageAssetVersion(
                asset_id=self.primary_currency.currency,
                tenant_id=self.tenant_id,
                kind="current-measures",
                version=currency_version,
            ),
            StageAssetVersion(
                asset_id=self.primary_currency.currency,
                tenant_id=self.tenant_id,
                kind="desired-measures",
                version=currency_version,
            ),
            StageAssetVersion(
                asset_id=self.positioning.decision_id,
                tenant_id=self.tenant_id,
                kind="horizon",
                version=positioning_version,
            ),
            StageAssetVersion(
                asset_id=self.positioning.decision_id,
                tenant_id=self.tenant_id,
                kind="qualifications",
                version=positioning_version,
            ),
            StageAssetVersion(
                asset_id=self.positioning.decision_id,
                tenant_id=self.tenant_id,
                kind="transformation-statement",
                version=positioning_version,
            ),
            StageAssetVersion(
                asset_id=self.positioning.decision_id,
                tenant_id=self.tenant_id,
                kind="core-problem",
                version=positioning_version,
            ),
            StageAssetVersion(
                asset_id=self.million_dollar_message.message_id,
                tenant_id=self.tenant_id,
                kind="million-dollar-message",
                version=message_version,
            ),
        )


CANONICAL_DIAGNOSTIC_KINDS: tuple[str, ...] = (
    "profit-pyramid-levels",
    "observable-measures",
    "level-symptoms",
    "level-behaviors",
    "level-problems",
    "progression",
    "qualification-logic",
    "diagnostic-model-name",
    "diagnostic-model-visual",
    "diagnostic-model-copy",
)


@dataclass(frozen=True)
class DiagnosticPackage:
    """The reviewed stage 3 model, projected to the ten canonical gate kinds.

    SPEC.md section 4, stage 3 "Model" and its "Diagnostic Model Approved"
    checkpoint: a stage is complete only when its required assets exist, pass the
    checkpoint and receive approval for downstream use, and a passing gate pins
    the exact evidence. The required asset package is the Profit Pyramid levels,
    their observable measures, symptoms, behaviors and problems, progression,
    qualification logic, name, visual and explanatory copy. The Method context
    reviews that as one rich ``DiagnosticModel`` (the levels, progression,
    qualification logic, name, visual and copy are all attributes of the same
    delivered pyramid); this package is the bridge to the governance gate, which
    pins one exact ``StageAssetVersion`` per canonical kind.

    The canon (SPEC.md section 12.3: stage 3 uses canon files 07 and 08) requires
    a clear currency, four observable levels with clear titles, symptoms and
    metrics, one powerful visual model presented to every prospect, and
    explanatory copy, graded by a pre-launch checklist. Each canonical kind is
    projected from the single reviewed model at one positive integer version, and
    a blank identity, a versionless model or a cross-tenant model is refused
    rather than silently pinned (SPEC.md sections 3 and 4).
    """

    package_id: str
    tenant_id: str
    model: DiagnosticModel
    model_version: int

    def __post_init__(self) -> None:
        for label, value in (
            ("diagnostic package id", self.package_id),
            ("diagnostic package tenant id", self.tenant_id),
        ):
            if not value or not value.strip():
                raise InvalidDiagnosticPackageError(f"{label} is required")
        if self.model.tenant_id != self.tenant_id:
            raise DiagnosticTenantBoundaryError(
                f"stage 3 model {self.model.model_id!r} belongs to tenant "
                f"{self.model.tenant_id!r}, not package tenant {self.tenant_id!r}"
            )
        if not isinstance(self.model_version, int) or self.model_version < 1:
            raise InvalidDiagnosticPackageError(
                "the diagnostic model version must be a positive integer so the "
                "stage 3 gate can pin the reviewed asset at an exact version"
            )

    @property
    def kinds(self) -> frozenset[str]:
        """The canonical kinds the reviewed stage 3 model projects onto."""
        return frozenset(CANONICAL_DIAGNOSTIC_KINDS)

    def missing_kinds(self) -> tuple[str, ...]:
        """Canonical stage 3 kinds not covered by the projected model."""
        covered = {asset.kind for asset in self.stage_asset_versions()}
        return tuple(
            kind for kind in CANONICAL_DIAGNOSTIC_KINDS if kind not in covered
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_kinds()

    def stage_asset_versions(self) -> tuple[StageAssetVersion, ...]:
        """Project the reviewed stage 3 model onto exact governance evidence.

        Every canonical kind belongs to the same reviewed ``DiagnosticModel``, so
        each is pinned to that model's identity at its exact version. Governance
        still pins each projection for the workspace tenant, so a cross-client
        model is refused rather than silently authorized (SPEC.md sections 3, 4
        and 11).
        """
        return tuple(
            StageAssetVersion(
                asset_id=self.model.model_id,
                tenant_id=self.tenant_id,
                kind=kind,
                version=self.model_version,
            )
            for kind in CANONICAL_DIAGNOSTIC_KINDS
        )


CANONICAL_SIGNATURE_KINDS: tuple[str, ...] = (
    "transformation-map",
    "process-inventory",
    "three-phases",
    "nine-steps",
    "named-stages",
    "starting-state",
    "final-state",
    "stage-inputs",
    "stage-actions",
    "stage-outputs",
    "transformation-narrative",
    "transformation-visual",
    THIRTEEN_TRANSFORMATIONS_KIND,
)


@dataclass(frozen=True)
class SignaturePackage:
    """The reviewed stage 4 solution, projected to the canonical gate kinds.

    SPEC.md section 4, stage 4 "Package IP" and its "IP Architecture Locked"
    checkpoint: a stage is complete only when its required assets exist, pass the
    checkpoint and receive approval for downstream use, and a passing gate pins
    the exact evidence. The required asset package is the transformation map,
    process inventory, three phases, nine steps, named stages, starting and final
    states, stage inputs/actions/outputs, narrative and visual. The Method
    context reviews that as one rich ``SignatureSolution`` (the phases, steps,
    inputs, actions, outputs, states, map, narrative and visual are all attributes
    of the same coherent transformation); this package is the bridge to the
    governance gate, which pins one exact ``StageAssetVersion`` per canonical
    kind.

    The canon (SPEC.md section 12.3: stage 4 uses canon files 09 and 10) requires
    three main phases and nine clear steps from point A to point B, each named
    stage carrying its own from/to transformation, titled from the million dollar
    message. ``SignatureSolution`` already enforces that coherent shape and its
    continuity at construction, so each solution kind is projected from the
    single reviewed solution at one positive integer version, and a blank
    identity, a versionless solution or a cross-tenant solution is refused rather
    than silently pinned (SPEC.md sections 3 and 4).

    SPEC.md sections 4 and 12.5 (owner decision 2026-10-03) make a canon-informed
    asset already implemented in a bounded context a required asset kind of its
    target stage gate, so the typed ``ThirteenTransformations`` (canon files 09
    and 10) is carried and projected as the ``thirteen-transformations`` kind.
    Requiring the typed shifts, rather than the solution's own phase/step
    attributes alone, makes the "IP Architecture Locked" gate record the canon's
    thirteen titled from/to shifts it reviewed.
    """

    package_id: str
    tenant_id: str
    solution: SignatureSolution
    solution_version: int
    transformations: ThirteenTransformations
    transformations_version: int

    def __post_init__(self) -> None:
        for label, value in (
            ("signature package id", self.package_id),
            ("signature package tenant id", self.tenant_id),
        ):
            if not value or not value.strip():
                raise InvalidSignaturePackageError(f"{label} is required")
        if self.solution.tenant_id != self.tenant_id:
            raise SignatureTenantBoundaryError(
                f"stage 4 solution {self.solution.solution_id!r} belongs to tenant "
                f"{self.solution.tenant_id!r}, not package tenant {self.tenant_id!r}"
            )
        if not isinstance(self.solution_version, int) or self.solution_version < 1:
            raise InvalidSignaturePackageError(
                "the signature solution version must be a positive integer so the "
                "stage 4 gate can pin the reviewed asset at an exact version"
            )
        if not isinstance(self.transformations, ThirteenTransformations):
            raise InvalidSignaturePackageError(
                "stage 4 transformations must be a typed reviewed asset"
            )
        if self.transformations.tenant_id != self.tenant_id:
            raise SignatureTenantBoundaryError(
                f"stage 4 transformations {self.transformations.transformations_id!r} "
                f"belongs to tenant {self.transformations.tenant_id!r}, not package "
                f"tenant {self.tenant_id!r}"
            )
        if (
            not isinstance(self.transformations_version, int)
            or self.transformations_version < 1
        ):
            raise InvalidSignaturePackageError(
                "the thirteen transformations version must be a positive integer so "
                "the stage 4 gate can pin the reviewed asset at an exact version"
            )

    @property
    def kinds(self) -> frozenset[str]:
        """The canonical kinds the reviewed stage 4 assets project onto."""
        return frozenset(CANONICAL_SIGNATURE_KINDS)

    def missing_kinds(self) -> tuple[str, ...]:
        """Canonical stage 4 kinds not covered by the projected assets."""
        covered = {asset.kind for asset in self.stage_asset_versions()}
        return tuple(
            kind for kind in CANONICAL_SIGNATURE_KINDS if kind not in covered
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_kinds()

    def stage_asset_versions(self) -> tuple[StageAssetVersion, ...]:
        """Project the reviewed stage 4 assets onto exact governance evidence.

        The solution kinds belong to the single reviewed ``SignatureSolution`` and
        are pinned to its identity at its exact version; the
        ``thirteen-transformations`` kind belongs to the typed
        ``ThirteenTransformations`` and is pinned to the shifts' own identity at
        their exact version. Governance still pins each projection for the
        workspace tenant, so a cross-client solution or shift set is refused
        rather than silently authorized (SPEC.md sections 3, 4 and 11).
        """
        solution_kinds = tuple(
            kind
            for kind in CANONICAL_SIGNATURE_KINDS
            if kind != THIRTEEN_TRANSFORMATIONS_KIND
        )
        return (
            *(
                StageAssetVersion(
                    asset_id=self.solution.solution_id,
                    tenant_id=self.tenant_id,
                    kind=kind,
                    version=self.solution_version,
                )
                for kind in solution_kinds
            ),
            self.transformations.as_stage_asset(
                version=self.transformations_version
            ),
        )


PRODUCT_PROGRAM_KIND = "product-program"

CANONICAL_OFFER_KINDS: tuple[str, ...] = (
    "delivery-model",
    "duration",
    "modules",
    "responsibilities",
    "support-cadence",
    "stage-deliverables",
    "outcome-measures",
    "pricing-payments",
    "scope",
    "guarantee-decision",
    "eligibility",
    "offer-stack",
    PRODUCT_PROGRAM_KIND,
)


@dataclass(frozen=True)
class OfferPackage:
    """The reviewed stage 5 delivery, projected to the canonical gate kinds.

    SPEC.md section 4, stage 5 "Productize" and its "Offer Locked" checkpoint: a
    stage is complete only when its required assets exist, pass the checkpoint
    and receive approval for downstream use, and a passing gate pins the exact
    evidence. The required asset package is the delivery model, duration,
    modules, responsibilities, support cadence, stage deliverables, outcome
    measures, pricing and payments, scope, guarantee decision, eligibility and
    offer stack. The Commercial context reviews that as one rich
    ``DeliverySpecification`` (the delivery model, duration, modules,
    responsibilities, cadence, step deliveries, outcome measures, pricing,
    scope, guarantee, eligibility and offer stack are all attributes of the same
    delivered offer, grounded on the locked stage 4 method, and every method step
    must carry an action, actor, deliverable, timing and measure); this package
    is the bridge to the governance gate, which pins one exact
    ``StageAssetVersion`` per canonical kind.

    The canon (SPEC.md section 12.3: stage 5 uses canon files 11 and 12) requires
    choosing one delivery model from the Product Matrix, outlining a
    six-to-twelve week program that follows the signature solution, pricing by
    outcome rather than time and materials, and stating eligibility, guarantee
    and support terms. ``DeliverySpecification`` already enforces that coherent
    shape and its dependency on the locked stage 4 method at construction, so
    each delivery kind is projected from the single reviewed delivery at one
    positive integer version, and a blank identity, a versionless delivery or a
    cross-tenant delivery is refused rather than silently pinned (SPEC.md
    sections 3 and 4).

    SPEC.md sections 4 and 12.5 (owner decision 2026-10-03) make a canon-informed
    asset already implemented in a bounded context a required asset kind of its
    target stage gate, so the typed ``ProductProgram`` (canon files 11 and 12) is
    carried and projected as the ``product-program`` kind. Requiring the typed
    program, rather than the delivery's free-text delivery model and pricing,
    makes the "Offer Locked" gate reject a stage 5 package whose product matrix
    model, outcome pricing basis, six-to-twelve week structure or per-step module
    set is an untyped note.
    """

    package_id: str
    tenant_id: str
    delivery: DeliverySpecification
    delivery_version: int
    product_program: "ProductProgram"
    product_program_version: int

    def __post_init__(self) -> None:
        for label, value in (
            ("offer package id", self.package_id),
            ("offer package tenant id", self.tenant_id),
        ):
            if not value or not value.strip():
                raise InvalidOfferPackageError(f"{label} is required")
        if self.delivery.tenant_id != self.tenant_id:
            raise OfferTenantBoundaryError(
                f"stage 5 delivery {self.delivery.delivery_id!r} belongs to tenant "
                f"{self.delivery.tenant_id!r}, not package tenant {self.tenant_id!r}"
            )
        if not isinstance(self.delivery_version, int) or self.delivery_version < 1:
            raise InvalidOfferPackageError(
                "the delivery specification version must be a positive integer so "
                "the stage 5 gate can pin the reviewed asset at an exact version"
            )
        if not isinstance(self.product_program, ProductProgram):
            raise InvalidOfferPackageError(
                "stage 5 product program must be a typed reviewed asset"
            )
        if self.product_program.tenant_id != self.tenant_id:
            raise OfferTenantBoundaryError(
                f"stage 5 product program {self.product_program.program_id!r} "
                f"belongs to tenant {self.product_program.tenant_id!r}, not "
                f"package tenant {self.tenant_id!r}"
            )
        if (
            not isinstance(self.product_program_version, int)
            or self.product_program_version < 1
        ):
            raise InvalidOfferPackageError(
                "the product program version must be a positive integer so the "
                "stage 5 gate can pin the reviewed asset at an exact version"
            )

    @property
    def kinds(self) -> frozenset[str]:
        """The canonical kinds the reviewed stage 5 assets project onto."""
        return frozenset(CANONICAL_OFFER_KINDS)

    def missing_kinds(self) -> tuple[str, ...]:
        """Canonical stage 5 kinds not covered by the projected assets."""
        covered = {asset.kind for asset in self.stage_asset_versions()}
        return tuple(
            kind for kind in CANONICAL_OFFER_KINDS if kind not in covered
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_kinds()

    def stage_asset_versions(self) -> tuple[StageAssetVersion, ...]:
        """Project the reviewed stage 5 assets onto exact governance evidence.

        The delivery kinds belong to the single reviewed ``DeliverySpecification``
        and are pinned to its identity at its exact version; the
        ``product-program`` kind belongs to the typed ``ProductProgram`` and is
        pinned to the program's own identity at its exact version. Governance
        still pins each projection for the workspace tenant, so a cross-client
        delivery or program is refused rather than silently authorized (SPEC.md
        sections 3, 4 and 11).
        """
        delivery_kinds = tuple(
            kind for kind in CANONICAL_OFFER_KINDS if kind != PRODUCT_PROGRAM_KIND
        )
        return (
            *(
                StageAssetVersion(
                    asset_id=self.delivery.delivery_id,
                    tenant_id=self.tenant_id,
                    kind=kind,
                    version=self.delivery_version,
                )
                for kind in delivery_kinds
            ),
            self.product_program.as_stage_asset(
                version=self.product_program_version
            ),
        )


CONTENT_ROADMAP_KIND = "content-roadmap"
CONTENT_CRUSHER_KIND = "content-crusher"
CONTENT_PLAN_KIND = "content-plan"

CANONICAL_MESSAGE_KINDS: tuple[str, ...] = (
    "promise",
    "problem-hierarchy",
    "desired-outcome",
    "proof-objections",
    "story",
    "method-explanation",
    "cta",
    "lead-magnet",
    "hook",
    "angles",
    "landing-message",
    "authority-amplifier-outline",
    CONTENT_ROADMAP_KIND,
    CONTENT_CRUSHER_KIND,
    CONTENT_PLAN_KIND,
)


@dataclass(frozen=True)
class CampaignMessagePackage:
    """The reviewed stage 6 message, projected to the canonical gate kinds.

    SPEC.md section 4, stage 6 "Message" and its "Campaign Message Approved"
    checkpoint: a stage is complete only when its required assets exist, pass the
    checkpoint and receive approval for downstream use, and a passing gate pins the
    exact evidence. The required asset package is the promise, problem hierarchy,
    desired outcome, proof and objections, story, method explanation, CTA, lead
    magnet, hook, angles, landing message and Authority Amplifier outline. The
    Commercial context reviews that as one rich ``CampaignMessage`` (all of those
    fields are attributes of the same approved message, grounded on the approved
    stage 5 offer and congruent on avatar, currency, problem, promise, method,
    product and CTA); this package is the bridge to the governance gate, which
    pins one exact ``StageAssetVersion`` per canonical kind.

    The canon (SPEC.md section 12.3: stage 6 uses canon files 06, 15, 24 and
    25-28) requires reusing the Million Dollar Message in copy, the 5P messaging
    frame, the Authority Amplifier script as the universal content framework, and
    a Content Roadmap, Content Crusher and an Extract content plan. ``CampaignMessage``
    already enforces that coherent shape and its dependency on the approved stage
    5 offer at construction, so each message kind is projected from the single
    reviewed message at one positive integer version. The Content Roadmap (canon
    files 25-28, owner decision 2026-10-03), the Content Crusher (canon files 12,
    16 and 32, owner decision 2026-10-03) and the Content Plan (canon files 25, 27
    and 28, owner decision 2026-10-03) are separate typed Commercial assets, so
    their ``content-roadmap``, ``content-crusher`` and ``content-plan`` kinds are
    projected from each asset's own identity at that asset's exact version. A
    blank identity, a versionless message, roadmap, crusher or plan, or a
    cross-tenant one is refused rather than silently pinned (SPEC.md sections 3
    and 4).
    """

    package_id: str
    tenant_id: str
    message: "CampaignMessage"
    message_version: int
    roadmap: "ContentRoadmap"
    roadmap_version: int
    crusher: "ContentCrusher"
    crusher_version: int
    plan: "ContentPlan"
    plan_version: int

    def __post_init__(self) -> None:
        for label, value in (
            ("campaign message package id", self.package_id),
            ("campaign message package tenant id", self.tenant_id),
        ):
            if not value or not value.strip():
                raise InvalidCampaignMessagePackageError(f"{label} is required")
        if self.message.tenant_id != self.tenant_id:
            raise CampaignMessageTenantBoundaryError(
                f"stage 6 message {self.message.message_id!r} belongs to tenant "
                f"{self.message.tenant_id!r}, not package tenant"
                f" {self.tenant_id!r}"
            )
        if not isinstance(self.roadmap, ContentRoadmap):
            raise InvalidCampaignMessagePackageError(
                "the stage 6 content roadmap must be a typed content roadmap"
            )
        if self.roadmap.tenant_id != self.tenant_id:
            raise CampaignMessageTenantBoundaryError(
                f"stage 6 content roadmap {self.roadmap.roadmap_id!r} belongs to "
                f"tenant {self.roadmap.tenant_id!r}, not package tenant"
                f" {self.tenant_id!r}"
            )
        if not isinstance(self.message_version, int) or self.message_version < 1:
            raise InvalidCampaignMessagePackageError(
                "the campaign message version must be a positive integer so the "
                "stage 6 gate can pin the reviewed asset at an exact version"
            )
        if not isinstance(self.roadmap_version, int) or self.roadmap_version < 1:
            raise InvalidCampaignMessagePackageError(
                "the content roadmap version must be a positive integer so the "
                "stage 6 gate can pin the reviewed asset at an exact version"
            )
        if not isinstance(self.crusher, ContentCrusher):
            raise InvalidCampaignMessagePackageError(
                "the stage 6 content crusher must be a typed content crusher"
            )
        if self.crusher.tenant_id != self.tenant_id:
            raise CampaignMessageTenantBoundaryError(
                f"stage 6 content crusher {self.crusher.crusher_id!r} belongs to "
                f"tenant {self.crusher.tenant_id!r}, not package tenant"
                f" {self.tenant_id!r}"
            )
        if not isinstance(self.crusher_version, int) or self.crusher_version < 1:
            raise InvalidCampaignMessagePackageError(
                "the content crusher version must be a positive integer so the "
                "stage 6 gate can pin the reviewed asset at an exact version"
            )
        if not isinstance(self.plan, ContentPlan):
            raise InvalidCampaignMessagePackageError(
                "the stage 6 content plan must be a typed content plan"
            )
        if self.plan.tenant_id != self.tenant_id:
            raise CampaignMessageTenantBoundaryError(
                f"stage 6 content plan {self.plan.plan_id!r} belongs to tenant "
                f"{self.plan.tenant_id!r}, not package tenant "
                f"{self.tenant_id!r}"
            )
        if not isinstance(self.plan_version, int) or self.plan_version < 1:
            raise InvalidCampaignMessagePackageError(
                "the content plan version must be a positive integer so the "
                "stage 6 gate can pin the reviewed asset at an exact version"
            )

    @property
    def kinds(self) -> frozenset[str]:
        """The canonical kinds the reviewed stage 6 message projects onto."""
        return frozenset(CANONICAL_MESSAGE_KINDS)

    def missing_kinds(self) -> tuple[str, ...]:
        """Canonical stage 6 kinds not covered by the projected message."""
        covered = {asset.kind for asset in self.stage_asset_versions()}
        return tuple(
            kind for kind in CANONICAL_MESSAGE_KINDS if kind not in covered
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_kinds()

    def stage_asset_versions(self) -> tuple[StageAssetVersion, ...]:
        """Project the reviewed stage 6 message, roadmap and crusher to evidence.

        Every message kind belongs to the same reviewed ``CampaignMessage``, so
        each is pinned to that message's identity at its exact version, while the
        ``content-roadmap``, ``content-crusher`` and ``content-plan`` kinds are
        pinned to the roadmap's, crusher's and plan's own identities at their
        exact versions. Governance still pins each projection for the workspace
        tenant, so a cross-client message, roadmap, crusher or plan is refused
        rather than silently authorized (SPEC.md sections 3, 4 and 11).
        """
        message_kinds = tuple(
            kind
            for kind in CANONICAL_MESSAGE_KINDS
            if kind
            not in (CONTENT_ROADMAP_KIND, CONTENT_CRUSHER_KIND, CONTENT_PLAN_KIND)
        )
        return (
            *(
                StageAssetVersion(
                    asset_id=self.message.message_id,
                    tenant_id=self.tenant_id,
                    kind=kind,
                    version=self.message_version,
                )
                for kind in message_kinds
            ),
            self.roadmap.as_stage_asset(version=self.roadmap_version),
            self.crusher.as_stage_asset(version=self.crusher_version),
            self.plan.as_stage_asset(version=self.plan_version),
        )


class NurtureAudienceState(Enum):
    """The prospect states the canon's follow-up lifecycle re-engages (canon 24).

    The canon follows up with the people who did not convert at each step: leads
    who opted in but did not book (canon files 15 and 33), people who booked a
    call but did not show, people who took the call but did not enrol (canon file
    24: "whether they've showed up or not, if they haven't signed up, then I need
    to get a sequence going for them after that"), and the people who never
    opened an email (canon file 24: "there's another 70% of the people that never
    opened your email"). Naming the state keeps a sequence aimed at one recoverable
    prospect rather than an untyped mailing list.
    """

    OPTED_IN_NOT_BOOKED = "opted_in_not_booked"
    BOOKED_NO_SHOW = "booked_no_show"
    ATTENDED_NOT_ENROLLED = "attended_not_enrolled"
    NON_OPENER = "non_opener"


REQUIRED_NURTURE_STATES: tuple[NurtureAudienceState, ...] = (
    NurtureAudienceState.OPTED_IN_NOT_BOOKED,
    NurtureAudienceState.BOOKED_NO_SHOW,
    NurtureAudienceState.ATTENDED_NOT_ENROLLED,
    NurtureAudienceState.NON_OPENER,
)


class NurtureModality(Enum):
    """The canon's 5P messaging modalities for follow-up (canon file 33).

    The canon's 5P framework selects one copy modality per follow-up message: the
    problem or pain the prospect has, the promise of the outcome, the proof from
    other clients, a ping that asks a question, or a direct promotion (canon file
    33: "a problem people have... the promise of what life or the outcome will
    be... demonstrate proof... ping them, ask them a question... or a promotion").
    """

    PROBLEM = "problem"
    PROMISE = "promise"
    PROOF = "proof"
    PING = "ping"
    PROMOTION = "promotion"


@dataclass(frozen=True)
class NurtureMessage:
    """One follow-up message in the canon's nurture lifecycle (canon 15, 24, 33).

    A message derives from one named step of the Signature Solution Series (canon
    file 15: the series takes each Signature Solution step and turns it into
    follow-up content), carries its prospect state and one of the 5P modalities,
    and names the subject and the purpose it serves. The canon's one-question
    survey is the "ping" modality, which asks exactly one question, so a ping
    without a question and a non-ping that carries one are both refused (canon
    file 24: "if I send a one question email to your list").
    """

    message_id: str
    tenant_id: str
    name: str
    audience_state: NurtureAudienceState
    modality: NurtureModality
    signature_step: str
    subject: str
    purpose: str
    question: str | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("nurture message id", self.message_id),
            ("nurture message tenant id", self.tenant_id),
            ("nurture message name", self.name),
            ("nurture message signature step", self.signature_step),
            ("nurture message subject", self.subject),
            ("nurture message purpose", self.purpose),
        ):
            if not value or not value.strip():
                raise InvalidNurtureError(f"{label} is required")
        if not isinstance(self.audience_state, NurtureAudienceState):
            raise InvalidNurtureError(
                "a nurture message requires a named prospect state"
            )
        if not isinstance(self.modality, NurtureModality):
            raise InvalidNurtureError(
                "a nurture message requires one of the 5P messaging modalities"
            )
        if self.modality is NurtureModality.PING:
            if not self.question or not self.question.strip():
                raise NurtureSequenceError(
                    f"nurture message {self.message_id!r} uses the ping modality "
                    "and must ask exactly one question"
                )
        elif self.question is not None:
            raise NurtureSequenceError(
                f"nurture message {self.message_id!r} carries a question but does "
                "not use the ping modality; the one-question survey is a ping"
            )


@dataclass(frozen=True)
class NurtureSequence:
    """An ordered follow-up sequence for one prospect state (canon 15, 24).

    The canon sends follow-up content over time by prospect state; the one
    exception is the non-opener, who is re-engaged by resending the message with
    different headlines rather than one identical copy (canon file 24: "sending
    that message to them two or three times over the next week... with maybe
    different headlines"), so a non-opener sequence requires at least two distinct
    subjects. A sequence is frozen, all its messages belong to one tenant and one
    state, and message identities are unique.
    """

    sequence_id: str
    tenant_id: str
    audience_state: NurtureAudienceState
    messages: tuple[NurtureMessage, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("nurture sequence id", self.sequence_id),
            ("nurture sequence tenant id", self.tenant_id),
        ):
            if not value or not value.strip():
                raise InvalidNurtureError(f"{label} is required")
        if not isinstance(self.audience_state, NurtureAudienceState):
            raise InvalidNurtureError(
                "a nurture sequence requires a named prospect state"
            )
        if not self.messages:
            raise NurtureSequenceError(
                f"nurture sequence {self.sequence_id!r} requires at least one "
                "message"
            )
        seen: set[str] = set()
        for message in self.messages:
            if not isinstance(message, NurtureMessage):
                raise NurtureSequenceError(
                    "a nurture sequence message must be a typed nurture message"
                )
            if message.tenant_id != self.tenant_id:
                raise NurtureTenantBoundaryError(
                    f"nurture sequence {self.sequence_id!r} belongs to tenant "
                    f"{self.tenant_id!r}, but message {message.message_id!r} "
                    f"belongs to tenant {message.tenant_id!r}"
                )
            if message.audience_state is not self.audience_state:
                raise NurtureSequenceError(
                    f"nurture sequence {self.sequence_id!r} targets "
                    f"{self.audience_state.value!r}, but message "
                    f"{message.message_id!r} targets "
                    f"{message.audience_state.value!r}"
                )
            if message.message_id in seen:
                raise NurtureSequenceError(
                    f"nurture sequence {self.sequence_id!r} contains duplicate "
                    f"message id {message.message_id!r}"
                )
            seen.add(message.message_id)
        if (
            self.audience_state is NurtureAudienceState.NON_OPENER
            and len({message.subject for message in self.messages}) < 2
        ):
            raise NurtureSequenceError(
                f"nurture sequence {self.sequence_id!r} re-engages non-openers, "
                "who are resent the message with different headlines; it needs at "
                "least two distinct subjects"
            )


NURTURE_PLAN_KIND = "nurture-plan"


@dataclass(frozen=True)
class NurturePlan:
    """The canon's follow-up and nurture lifecycle for a client (SPEC.md 12).

    SPEC.md section 12.3 places the follow-up and nurture lifecycle (the
    Signature Solution Series, the 5P email system, the one-question survey and
    re-engagement) after stage 10, and section 12.5 records it as a canon gap
    informed by canon files 15, 24, 33 and 34. The plan grounds its content on a
    same-tenant stage 4 ``SignatureSolution`` so every message derives from one of
    the solution's named steps, binds the sequences to a named owner and one
    tenant, and reports the prospect states it does not yet cover.

    The methodology owner placed the plan as a required ``nurture-plan`` kind of
    the stage 10 "Performance Baseline Established" gate (owner decision
    2026-10-04, P2; SPEC.md sections 4 and 12.5), so the stage 10 gate pins the
    reviewed follow-up lifecycle at its own identity and version. It is an asset
    inside an existing stage, never a new or renamed stage.

    The plan is never an observed result: it is the follow-up content that will
    run, while any measured movement stays a separate observation (SPEC.md section
    3, Measurement invariant). It does not authorize sending or publishing; that
    remains a named human approval (SPEC.md sections 4 and 9).
    """

    plan_id: str
    tenant_id: str
    owner: str
    method: SignatureSolution
    sequences: tuple[NurtureSequence, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("nurture plan id", self.plan_id),
            ("nurture plan tenant id", self.tenant_id),
            ("nurture plan owner", self.owner),
        ):
            if not value or not value.strip():
                raise InvalidNurtureError(f"{label} is required")
        if not isinstance(self.method, SignatureSolution):
            raise NurtureDependencyError(
                "a nurture plan must derive its content from a typed stage 4 "
                "Signature Solution"
            )
        if self.method.tenant_id != self.tenant_id:
            raise NurtureTenantBoundaryError(
                f"nurture plan {self.plan_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its Signature Solution "
                f"{self.method.solution_id!r} belongs to tenant "
                f"{self.method.tenant_id!r}"
            )
        step_names = {step.name for step in self.method.steps}
        seen: set[str] = set()
        for sequence in self.sequences:
            if not isinstance(sequence, NurtureSequence):
                raise NurtureSequenceError(
                    "a nurture plan sequence must be a typed nurture sequence"
                )
            if sequence.tenant_id != self.tenant_id:
                raise NurtureTenantBoundaryError(
                    f"nurture plan {self.plan_id!r} cites sequence "
                    f"{sequence.sequence_id!r} from another tenant"
                )
            if sequence.sequence_id in seen:
                raise NurtureSequenceError(
                    f"nurture plan {self.plan_id!r} contains duplicate sequence id "
                    f"{sequence.sequence_id!r}"
                )
            seen.add(sequence.sequence_id)
            for message in sequence.messages:
                if message.signature_step not in step_names:
                    raise NurtureDependencyError(
                        f"nurture message {message.message_id!r} derives from "
                        f"Signature Solution step {message.signature_step!r}, "
                        "which the plan's Signature Solution does not name"
                    )

    @property
    def covered_states(self) -> tuple[NurtureAudienceState, ...]:
        """The prospect states the plan's sequences cover."""
        return tuple(
            state
            for state in REQUIRED_NURTURE_STATES
            if any(
                sequence.audience_state is state for sequence in self.sequences
            )
        )

    def missing_states(self) -> tuple[NurtureAudienceState, ...]:
        """Canon prospect states the plan does not yet cover."""
        covered = set(self.covered_states)
        return tuple(
            state for state in REQUIRED_NURTURE_STATES if state not in covered
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_states()

    @property
    def is_plan(self) -> bool:
        return True

    def as_stage_asset(self, *, version: int) -> StageAssetVersion:
        """Project the plan onto exact ``nurture-plan`` evidence.

        SPEC.md sections 4 and 12.5: a canon-informed asset already implemented
        in a bounded context becomes a required asset kind of its target stage
        gate, so the stage 10 "Performance Baseline Established" gate pins the
        reviewed follow-up lifecycle as one exact ``StageAssetVersion`` (owner
        decision 2026-10-04, P2). A versionless projection is refused rather than
        silently pinned (SPEC.md sections 3 and 4).
        """
        if not isinstance(version, int) or version < 1:
            raise InvalidNurtureError(
                "the nurture plan version must be a positive integer so the "
                "stage 10 gate can pin the reviewed asset at an exact version"
            )
        return StageAssetVersion(
            asset_id=self.plan_id,
            tenant_id=self.tenant_id,
            kind=NURTURE_PLAN_KIND,
            version=version,
        )

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a nurture plan as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The plan
        describes the follow-up content that will run, while any measured movement
        is a separate observation, so a plan is never an observation.
        """
        raise NurtureObservationError(
            f"nurture plan {claim_id!r} is follow-up content to run, not an "
            "observed result, and cannot be recorded as an observation"
        )


TARGET_MARKET_MATCH_KIND = "target-market-match"


@dataclass(frozen=True)
class TargetMarketCandidate:
    """One candidate target market judged by the canon's match criteria.

    SPEC.md section 12.5 records the positioning and decision tools as a canon
    gap. The canon's target market matchmaker judges each candidate market on
    being an audience you are passionate to help, a clear problem the offer
    solves, real profit, a place where you can have a presence and be known to
    them, and a clear pathway from point A to point B (canon file 00). The
    candidate is frozen and reject-only, so a market that leaves any of those
    criteria unstated cannot be represented as a match candidate.
    """

    market_id: str
    name: str
    passion: str
    problem: str
    profit: str
    reachability: str
    pathway: str

    def __post_init__(self) -> None:
        for label, value in (
            ("target market candidate id", self.market_id),
            ("target market candidate name", self.name),
            ("target market candidate passion", self.passion),
            ("target market candidate problem", self.problem),
            ("target market candidate profit", self.profit),
            ("target market candidate reachability", self.reachability),
            ("target market candidate pathway", self.pathway),
        ):
            if not value or not value.strip():
                raise InvalidTargetMarketMatchmakerError(f"{label} is required")


@dataclass(frozen=True)
class TargetMarketMatchmaker:
    """The canon's target market matchmaker for one client and one selection.

    SPEC.md section 12.5 records the target market matchmaker as part of the
    positioning and decision tools canon gap. The canon takes two or three
    candidate target markets and narrows them to the one to serve now (canon file
    00), judged on the ``TargetMarketCandidate`` criteria, and the awareness
    research (canon file 04) places the chosen market. The match is frozen and
    reject-only, so fewer than two candidates, a duplicate candidate, a selected
    market that is not among the candidates, or a cross-tenant awareness map
    cannot be represented as a target market decision.

    Per the owner decision in SPEC.md section 12.5 a canon-informed asset already
    implemented in a bounded context becomes a required asset kind of its target
    stage gate in stage order, so this is the stage 1 ``target-market-match``
    kind, an asset inside the existing stage, never a new stage. It does not
    authorize outreach or spend (SPEC.md sections 4 and 9) and it is never an
    observation (SPEC.md section 3).
    """

    matchmaker_id: str
    tenant_id: str
    candidates: tuple[TargetMarketCandidate, ...]
    selected_market_id: str
    awareness_map: MarketAwarenessMap

    def __post_init__(self) -> None:
        for label, value in (
            ("target market matchmaker id", self.matchmaker_id),
            ("target market matchmaker tenant id", self.tenant_id),
            ("target market selected market id", self.selected_market_id),
        ):
            if not value or not value.strip():
                raise InvalidTargetMarketMatchmakerError(f"{label} is required")
        candidates = tuple(self.candidates)
        if len(candidates) < 2:
            raise InvalidTargetMarketMatchmakerError(
                "the target market matchmaker requires at least two candidate "
                "markets to narrow from"
            )
        seen: set[str] = set()
        for candidate in candidates:
            if not isinstance(candidate, TargetMarketCandidate):
                raise InvalidTargetMarketMatchmakerError(
                    "a target market matchmaker candidate must be a typed market "
                    "candidate"
                )
            if candidate.market_id in seen:
                raise InvalidTargetMarketMatchmakerError(
                    f"target market matchmaker {self.matchmaker_id!r} contains "
                    f"duplicate candidate market id {candidate.market_id!r}"
                )
            seen.add(candidate.market_id)
        if self.selected_market_id not in seen:
            raise InvalidTargetMarketMatchmakerError(
                f"target market matchmaker {self.matchmaker_id!r} selects market "
                f"{self.selected_market_id!r}, which is not one of its candidates"
            )
        if not isinstance(self.awareness_map, MarketAwarenessMap):
            raise InvalidTargetMarketMatchmakerError(
                "a target market matchmaker requires the awareness map that "
                "places the chosen market"
            )
        if self.awareness_map.tenant_id != self.tenant_id:
            raise TargetMarketTenantBoundaryError(
                f"target market matchmaker {self.matchmaker_id!r} belongs to "
                f"tenant {self.tenant_id!r}, but its awareness map "
                f"{self.awareness_map.map_id!r} belongs to tenant "
                f"{self.awareness_map.tenant_id!r}"
            )

    @property
    def selected_market(self) -> TargetMarketCandidate:
        """The one candidate market selected to serve now."""
        return next(
            candidate
            for candidate in self.candidates
            if candidate.market_id == self.selected_market_id
        )

    @property
    def is_decision(self) -> bool:
        """A target market matchmaker is a planning decision, not activity."""
        return True

    def as_stage_asset(self, *, version: int) -> StageAssetVersion:
        """Project the match onto exact ``target-market-match`` evidence.

        SPEC.md sections 4 and 12.5: a canon-informed asset already implemented
        in a bounded context becomes a required asset kind of its target stage
        gate, so the stage 1 "Avatar Locked" gate pins the chosen target market
        as one exact ``StageAssetVersion``. A versionless projection is refused
        rather than silently pinned (SPEC.md sections 3 and 4).
        """
        if not isinstance(version, int) or version < 1:
            raise InvalidTargetMarketMatchmakerError(
                "the target market match version must be a positive integer so "
                "the stage 1 gate can pin the reviewed asset at an exact version"
            )
        return StageAssetVersion(
            asset_id=self.matchmaker_id,
            tenant_id=self.tenant_id,
            kind=TARGET_MARKET_MATCH_KIND,
            version=version,
        )

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a target market match as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The match
        decides which market to serve, while any measured movement is a separate
        observation, so a match is never an observation.
        """
        raise TargetMarketObservationError(
            f"target market match {claim_id!r} is a planning decision, not an "
            "observed result, and cannot be recorded as an observation"
        )


class OfferPriceBand(Enum):
    """The banded pricing of an offer, a canon funnel finder factor.

    SPEC.md section 12.5 records the positioning and decision tools as a canon
    gap. The canon's funnel finder is based partly on "the pricing of your
    offer" (canon file 13), with low-end products ("$5") and a high-ticket
    consulting package ("$20,000") as the two stated extremes. The band is the
    typed form of that factor so a selection can be checked against it.
    """

    LOW_TICKET = "low_ticket"
    MID_TICKET = "mid_ticket"
    HIGH_TICKET = "high_ticket"


class FunnelType(Enum):
    """The funnel types the canon funnel finder chooses among (canon files 13, 14).

    The canon's funnel finder helps decide "which type of marketing system or
    funnel to deploy" and enumerates the types it trains its community on:
    liquid funnels to sell low-end products, local funnels to drive people into a
    retail or professional services company, the CAC (coach, agency, consultant)
    funnel, webinar funnels, quiz funnels and launch funnels (canon file 13).
    """

    LIQUID = "liquid"
    LOCAL = "local"
    CAC = "cac"
    WEBINAR = "webinar"
    QUIZ = "quiz"
    LAUNCH = "launch"

    @property
    def requires_sales_conversation(self) -> bool:
        """Whether the funnel converts through a scheduled sales call.

        The canon's CAC funnel ends by getting the prospect "to schedule a call
        and then ... conduct the call and then ... enroll them and charge them"
        (canon file 13), unlike the low-end, self-serve and webinar funnels.
        """
        return self is FunnelType.CAC


@dataclass(frozen=True)
class FunnelProfile:
    """The business profile the canon funnel finder selects a funnel for.

    SPEC.md section 12.5 records the positioning and decision tools as a canon
    gap. The canon's funnel finder is "based on the technical level ... how
    experienced you are, the pricing of your offer ... And then the business
    model" (canon file 13). The profile is frozen and reject-only, so a business
    that leaves any of those factors unstated cannot be represented as a funnel
    finder input.
    """

    profile_id: str
    tenant_id: str
    technical_level: str
    experience: str
    offer_price: OfferPriceBand
    business_model: str

    def __post_init__(self) -> None:
        for label, value in (
            ("funnel profile id", self.profile_id),
            ("funnel profile tenant id", self.tenant_id),
            ("funnel profile technical level", self.technical_level),
            ("funnel profile experience", self.experience),
            ("funnel profile business model", self.business_model),
        ):
            if not value or not value.strip():
                raise InvalidFunnelFinderError(f"{label} is required")
        if not isinstance(self.offer_price, OfferPriceBand):
            raise InvalidFunnelFinderError(
                "a funnel profile requires a typed offer price band"
            )


@dataclass(frozen=True)
class FunnelFinder:
    """The canon's funnel finder selection for one client and one business.

    SPEC.md section 12.5 records the funnel finder as part of the positioning and
    decision tools canon gap, and section 12.3 places the pre-stage-8 selection
    with canon files 13 and 14. The finder takes the funnel types the business
    could deploy and selects the one that fits its technical level, experience,
    offer price and business model (canon file 13). The finder is frozen and
    reject-only, so fewer than two considered types, a duplicate type, a selected
    type that is not among the considered types, or a cross-tenant profile cannot
    be represented as a funnel decision.

    It is a planning decision for the pre-stage-8 selection, not a new required
    gate kind (a methodology-owner decision, SPEC.md section 12.5). It does not
    authorize outreach or spend (SPEC.md sections 4 and 9) and it is never an
    observation (SPEC.md section 3).
    """

    finder_id: str
    tenant_id: str
    profile: FunnelProfile
    considered_types: tuple[FunnelType, ...]
    selected_type: FunnelType
    rationale: str

    def __post_init__(self) -> None:
        for label, value in (
            ("funnel finder id", self.finder_id),
            ("funnel finder tenant id", self.tenant_id),
            ("funnel finder rationale", self.rationale),
        ):
            if not value or not value.strip():
                raise InvalidFunnelFinderError(f"{label} is required")
        if not isinstance(self.profile, FunnelProfile):
            raise InvalidFunnelFinderError(
                "a funnel finder requires the typed business profile it decides for"
            )
        types = tuple(self.considered_types)
        if len(types) < 2:
            raise InvalidFunnelFinderError(
                "the funnel finder requires at least two considered funnel types "
                "to choose from"
            )
        seen: set[FunnelType] = set()
        for funnel_type in types:
            if not isinstance(funnel_type, FunnelType):
                raise InvalidFunnelFinderError(
                    "a considered funnel type must be one of the canon funnel types"
                )
            if funnel_type in seen:
                raise InvalidFunnelFinderError(
                    f"funnel finder {self.finder_id!r} considers duplicate funnel "
                    f"type {funnel_type.value!r}"
                )
            seen.add(funnel_type)
        if not isinstance(self.selected_type, FunnelType):
            raise InvalidFunnelFinderError(
                "a funnel finder must select one of the canon funnel types"
            )
        if self.selected_type not in seen:
            raise InvalidFunnelFinderError(
                f"funnel finder {self.finder_id!r} selects funnel type "
                f"{self.selected_type.value!r}, which is not one of its considered "
                "types"
            )
        if self.profile.tenant_id != self.tenant_id:
            raise FunnelFinderTenantBoundaryError(
                f"funnel finder {self.finder_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its profile {self.profile.profile_id!r} "
                f"belongs to tenant {self.profile.tenant_id!r}"
            )

    @property
    def is_decision(self) -> bool:
        """A funnel finder is a planning decision, not activity."""
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a funnel selection as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The finder
        decides which funnel to deploy, while any measured movement is a separate
        observation, so a finder is never an observation.
        """
        raise FunnelFinderObservationError(
            f"funnel finder {claim_id!r} is a planning decision, not an observed "
            "result, and cannot be recorded as an observation"
        )


class ContentBeat(Enum):
    """The beats of the Authority Amplifier script (canon file 26; SPEC stage 7).

    SPEC.md section 12.3 maps the Authority Amplifier script to stages 6 and 7,
    and section 4 stage 7 fixes its order as Promise, Proof, Problems, Steps,
    Context, Action. The canon's Content Blitz reuses that script as the
    framework for every piece of audience-building content (canon file 26: "these
    two to five minute videos ... still use the authority amplifier script
    because that's the framework I want you to use for every piece of content").
    """

    PROMISE = "promise"
    PROOF = "proof"
    PROBLEMS = "problems"
    STEPS = "steps"
    CONTEXT = "context"
    ACTION = "action"


AUTHORITY_AMPLIFIER_BEATS: tuple[ContentBeat, ...] = (
    ContentBeat.PROMISE,
    ContentBeat.PROOF,
    ContentBeat.PROBLEMS,
    ContentBeat.STEPS,
    ContentBeat.CONTEXT,
    ContentBeat.ACTION,
)


class ContentChannel(Enum):
    """The channels each piece of canon content is published to (canon 29, 31).

    The canon publishes every audience-building piece "to YouTube, Facebook and
    blog at a minimum" (canon file 29), syndicates it to the email list, social
    groups and podcast (canon file 31), and warns that posting an asset in only
    one place loses most of its equity. The channel is the typed form of that
    distribution route.
    """

    BLOG = "blog"
    YOUTUBE = "youtube"
    FACEBOOK = "facebook"
    EMAIL = "email"
    SOCIAL_GROUPS = "social_groups"
    PODCAST = "podcast"


MINIMUM_PUBLISH_CHANNELS: tuple[ContentChannel, ...] = (
    ContentChannel.BLOG,
    ContentChannel.YOUTUBE,
    ContentChannel.FACEBOOK,
)


@dataclass(frozen=True)
class ContentTopic:
    """One content topic mapped from a Signature Solution step (canon 26, 27).

    SPEC.md section 12.5 records the content roadmap as part of the
    audience-building and content flywheel canon gap. The canon builds the
    roadmap by taking each step of the Signature Solution and brainstorming the
    FAQs, topics and search queries the audience asks about it (canon files 26
    and 27), following the Authority Amplifier script format for every piece
    (canon file 26). The topic is frozen and reject-only, so a topic that leaves
    its step, question, channels or script format unstated cannot be represented
    as content in the plan.
    """

    topic_id: str
    tenant_id: str
    name: str
    signature_step: str
    question: str
    channels: tuple[ContentChannel, ...]
    script_beats: tuple[ContentBeat, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("content topic id", self.topic_id),
            ("content topic tenant id", self.tenant_id),
            ("content topic name", self.name),
            ("content topic signature step", self.signature_step),
            ("content topic question", self.question),
        ):
            if not value or not value.strip():
                raise InvalidContentRoadmapError(f"{label} is required")
        channels = tuple(self.channels)
        if not channels:
            raise InvalidContentRoadmapError(
                "a content topic must name at least one channel it is published to"
            )
        seen_channels: set[ContentChannel] = set()
        for channel in channels:
            if not isinstance(channel, ContentChannel):
                raise InvalidContentRoadmapError(
                    "a content topic channel must be a typed content channel"
                )
            if channel in seen_channels:
                raise ContentRoadmapFormatError(
                    f"content topic {self.topic_id!r} names duplicate channel "
                    f"{channel.value!r}"
                )
            seen_channels.add(channel)
        beats = tuple(self.script_beats)
        if beats != AUTHORITY_AMPLIFIER_BEATS:
            raise ContentRoadmapFormatError(
                f"content topic {self.topic_id!r} must follow the Authority "
                "Amplifier script order Promise, Proof, Problems, Steps, Context, "
                "Action"
            )


@dataclass(frozen=True)
class ContentRoadmap:
    """The canon's content roadmap for one client and one Signature Solution.

    SPEC.md section 12.5 records the content roadmap as part of the
    audience-building and content flywheel canon gap and maps it to stage 6
    content assets. The roadmap maps a same-tenant stage 4 ``SignatureSolution``
    onto content topics (canon files 26 and 27: "create a content roadmap using
    the signature solution to map out the topics, FAQs and search queries"),
    binds the plan to a named owner and one tenant, and reports the solution
    steps it does not yet cover. It is frozen and reject-only, so a blank
    identity, an untyped or foreign method, a duplicate topic, or a topic from a
    step the solution does not name cannot be represented as a content plan.

    It is a stage 6 planning decision, not a new required gate kind (a
    methodology-owner decision, SPEC.md section 12.5). It does not authorize
    publishing or spend (SPEC.md sections 4 and 9) and it is never an observation
    (SPEC.md section 3).
    """

    roadmap_id: str
    tenant_id: str
    owner: str
    method: SignatureSolution
    topics: tuple[ContentTopic, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("content roadmap id", self.roadmap_id),
            ("content roadmap tenant id", self.tenant_id),
            ("content roadmap owner", self.owner),
        ):
            if not value or not value.strip():
                raise InvalidContentRoadmapError(f"{label} is required")
        if not isinstance(self.method, SignatureSolution):
            raise ContentRoadmapDependencyError(
                "a content roadmap must map from a typed stage 4 Signature Solution"
            )
        if self.method.tenant_id != self.tenant_id:
            raise ContentRoadmapTenantBoundaryError(
                f"content roadmap {self.roadmap_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its Signature Solution "
                f"{self.method.solution_id!r} belongs to tenant "
                f"{self.method.tenant_id!r}"
            )
        if not self.topics:
            raise InvalidContentRoadmapError(
                f"content roadmap {self.roadmap_id!r} requires at least one topic"
            )
        step_names = {step.name for step in self.method.steps}
        seen: set[str] = set()
        for topic in self.topics:
            if not isinstance(topic, ContentTopic):
                raise InvalidContentRoadmapError(
                    "a content roadmap topic must be a typed content topic"
                )
            if topic.tenant_id != self.tenant_id:
                raise ContentRoadmapTenantBoundaryError(
                    f"content roadmap {self.roadmap_id!r} cites topic "
                    f"{topic.topic_id!r} from another tenant"
                )
            if topic.topic_id in seen:
                raise InvalidContentRoadmapError(
                    f"content roadmap {self.roadmap_id!r} contains duplicate topic "
                    f"id {topic.topic_id!r}"
                )
            seen.add(topic.topic_id)
            if topic.signature_step not in step_names:
                raise ContentRoadmapDependencyError(
                    f"content topic {topic.topic_id!r} maps from Signature Solution "
                    f"step {topic.signature_step!r}, which the roadmap's Signature "
                    "Solution does not name"
                )

    @property
    def covered_steps(self) -> tuple[str, ...]:
        """The Signature Solution steps the roadmap already has a topic for."""
        topics = self.topics
        return tuple(
            step.name
            for step in self.method.steps
            if any(topic.signature_step == step.name for topic in topics)
        )

    def missing_steps(self) -> tuple[str, ...]:
        """Signature Solution steps the roadmap does not yet cover with a topic."""
        covered = set(self.covered_steps)
        return tuple(
            step.name for step in self.method.steps if step.name not in covered
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_steps()

    @property
    def is_plan(self) -> bool:
        """A content roadmap is a plan, not activity or an observed result."""
        return True

    def as_stage_asset(self, *, version: int) -> StageAssetVersion:
        """Project the roadmap onto exact ``content-roadmap`` gate evidence.

        SPEC.md sections 4 and 12.5 (owner decision 2026-10-03): a
        canon-informed asset already implemented in a bounded context becomes a
        required asset kind of its target stage gate, so the stage 6 "Campaign
        Message Approved" gate pins the typed content roadmap (canon files 25-28)
        as one exact ``StageAssetVersion``. A versionless projection is refused
        rather than silently pinned (SPEC.md sections 3 and 4).
        """
        if not isinstance(version, int) or version < 1:
            raise InvalidContentRoadmapError(
                "the content roadmap version must be a positive integer so the "
                "stage 6 gate can pin the reviewed asset at an exact version"
            )
        return StageAssetVersion(
            asset_id=self.roadmap_id,
            tenant_id=self.tenant_id,
            kind=CONTENT_ROADMAP_KIND,
            version=version,
        )

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a content roadmap as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The
        roadmap describes the content that will be produced and published, while
        any measured movement is a separate observation, so a roadmap is never an
        observation.
        """
        raise ContentRoadmapObservationError(
            f"content roadmap {claim_id!r} is content to produce and publish, not "
            "an observed result, and cannot be recorded as an observation"
        )


class SyndicationChannel(Enum):
    """The channels the canon syndicates a content asset to (canon file 31).

    SPEC.md section 12.5 maps the content flywheel's syndication schedule to
    stage 6 content assets and stage 10 audience operations. The canon syndicates
    every asset "anywhere you can reach your audience": the email list, messenger
    subscribers, the people who belong to your groups, LinkedIn, Twitter,
    Facebook and the podcast feed (canon file 31). The channel is the typed form
    of those distribution routes.
    """

    EMAIL = "email"
    MESSENGER = "messenger"
    SOCIAL_GROUP = "social_group"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    PODCAST = "podcast"


class SyndicationCadence(Enum):
    """How often one asset is re-syndicated on a channel (canon file 31).

    The canon queues each asset to publish repeatedly: "put this on Twitter every
    three hours. Put one of these on Facebook every other day, put one of these
    on LinkedIn" (canon file 31). The cadence is the typed form of that recurring
    schedule.
    """

    MULTIPLE_DAILY = "multiple_daily"
    DAILY = "daily"
    EVERY_OTHER_DAY = "every_other_day"
    WEEKLY = "weekly"


class RecycledFormat(Enum):
    """The derivative formats a content asset is recycled into (canon file 31).

    The canon's "bonus step" is to recycle a good asset into other formats: an
    infographic that explains the post, lead magnets, content gateways, the audio
    pulled out as a podcast, and a video series offered for an opt-in (canon file
    31). The format is the typed form of those derivatives.
    """

    INFOGRAPHIC = "infographic"
    LEAD_MAGNET = "lead_magnet"
    CONTENT_GATEWAY = "content_gateway"
    PODCAST_AUDIO = "podcast_audio"
    OPT_IN_VIDEO = "opt_in_video"


OWNED_SYNDICATION_CHANNELS: tuple[SyndicationChannel, ...] = (
    SyndicationChannel.EMAIL,
    SyndicationChannel.MESSENGER,
    SyndicationChannel.SOCIAL_GROUP,
)


@dataclass(frozen=True)
class ChannelSyndication:
    """One channel and the cadence an asset is syndicated on it (canon 31).

    A channel syndication pairs a typed ``SyndicationChannel`` with the recurring
    ``SyndicationCadence`` the canon queues for that channel. It is frozen and
    reject-only, so an untyped channel or cadence cannot be represented as part
    of the schedule.
    """

    channel: SyndicationChannel
    cadence: SyndicationCadence

    def __post_init__(self) -> None:
        if not isinstance(self.channel, SyndicationChannel):
            raise InvalidContentSyndicationError(
                "a syndication channel must be a typed syndication channel"
            )
        if not isinstance(self.cadence, SyndicationCadence):
            raise InvalidContentSyndicationError(
                "a syndication cadence must be a typed syndication cadence"
            )


@dataclass(frozen=True)
class DailyPromotionBudget:
    """The canon's low fixed daily promotion spend for one asset (canon 30, 31).

    The canon promotes every piece of content on the "dollar a day strategy",
    started at "$5 a day" / "$3" minimum, and later cranks it up or down after
    the learning phase rather than switching it off (canon files 30 and 31). The
    budget is frozen and reject-only, so a non-positive amount, a missing
    currency or a non-decimal amount cannot be represented as the promotion plan.
    """

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise InvalidContentSyndicationError(
                "a daily promotion budget amount must be a Decimal"
            )
        if self.amount <= 0:
            raise InvalidContentSyndicationError(
                "a daily promotion budget must be a positive daily amount"
            )
        if not isinstance(self.currency, str) or not self.currency.strip():
            raise InvalidContentSyndicationError(
                "a daily promotion budget currency is required"
            )


@dataclass(frozen=True)
class TopicSyndication:
    """How one roadmap topic is syndicated, promoted and recycled (canon 31).

    SPEC.md section 12.5 records the content syndication and recycling schedule
    as the remaining delivery asset of the audience-building and content flywheel
    canon gap. A syndication distributes one Content Roadmap topic to at least
    one typed channel on a per-channel cadence, promotes it on a positive daily
    budget (canon 30) and recycles it into at least one typed derivative format
    (canon 31). It is frozen and reject-only, so a blank topic, an untyped or
    duplicate channel, an untyped or duplicate recycled format or an untyped
    budget cannot be represented as part of the schedule.
    """

    topic_id: str
    channels: tuple[ChannelSyndication, ...]
    recycled_formats: tuple[RecycledFormat, ...]
    promotion_budget: DailyPromotionBudget

    def __post_init__(self) -> None:
        if not self.topic_id or not self.topic_id.strip():
            raise InvalidContentSyndicationError(
                "a topic syndication topic id is required"
            )
        channels = tuple(self.channels)
        if not channels:
            raise InvalidContentSyndicationError(
                "a topic syndication must name at least one channel it is "
                "syndicated to"
            )
        seen_channels: set[SyndicationChannel] = set()
        for entry in channels:
            if not isinstance(entry, ChannelSyndication):
                raise InvalidContentSyndicationError(
                    "a topic syndication channel must be a typed channel "
                    "syndication"
                )
            if entry.channel in seen_channels:
                raise ContentSyndicationFormatError(
                    f"topic syndication {self.topic_id!r} repeats channel "
                    f"{entry.channel.value!r}"
                )
            seen_channels.add(entry.channel)
        formats = tuple(self.recycled_formats)
        if not formats:
            raise InvalidContentSyndicationError(
                "a topic syndication must recycle the asset into at least one "
                "derivative format"
            )
        seen_formats: set[RecycledFormat] = set()
        for fmt in formats:
            if not isinstance(fmt, RecycledFormat):
                raise InvalidContentSyndicationError(
                    "a topic syndication recycled format must be a typed "
                    "recycled format"
                )
            if fmt in seen_formats:
                raise ContentSyndicationFormatError(
                    f"topic syndication {self.topic_id!r} repeats recycled format "
                    f"{fmt.value!r}"
                )
            seen_formats.add(fmt)
        if not isinstance(self.promotion_budget, DailyPromotionBudget):
            raise InvalidContentSyndicationError(
                "a topic syndication must carry a typed daily promotion budget"
            )


@dataclass(frozen=True)
class ContentSyndicationPlan:
    """The canon's content syndication and recycling schedule for one client.

    SPEC.md section 12.5 records the content syndication and recycling schedule as
    the remaining delivery asset of the audience-building and content flywheel
    canon gap and maps it to stage 6 content assets and stage 10 audience
    operations. The plan distributes a same-tenant ``ContentRoadmap`` by
    syndicating each planned topic to multiple channels on a cadence, promoting it
    on a dollar-a-day budget and recycling it into derivatives (canon files 29,
    30 and 31), binds the plan to a named owner and one tenant, and reports the
    roadmap topics it does not yet syndicate. It is frozen and reject-only, so a
    blank identity, an untyped or foreign roadmap, a duplicate or ungrounded
    topic syndication cannot be represented as a schedule.

    It is a stage 6/10 planning asset, not a new required gate kind (a
    methodology-owner decision, SPEC.md section 12.5). It does not authorize
    publishing or spend (SPEC.md sections 4 and 9) and it is never an observation
    (SPEC.md section 3).
    """

    plan_id: str
    tenant_id: str
    owner: str
    roadmap: ContentRoadmap
    syndications: tuple[TopicSyndication, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("content syndication plan id", self.plan_id),
            ("content syndication plan tenant id", self.tenant_id),
            ("content syndication plan owner", self.owner),
        ):
            if not value or not value.strip():
                raise InvalidContentSyndicationError(f"{label} is required")
        if not isinstance(self.roadmap, ContentRoadmap):
            raise ContentSyndicationDependencyError(
                "a content syndication plan must distribute a typed Content "
                "Roadmap"
            )
        if self.roadmap.tenant_id != self.tenant_id:
            raise ContentSyndicationTenantBoundaryError(
                f"content syndication plan {self.plan_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its Content Roadmap "
                f"{self.roadmap.roadmap_id!r} belongs to tenant "
                f"{self.roadmap.tenant_id!r}"
            )
        if not self.syndications:
            raise InvalidContentSyndicationError(
                f"content syndication plan {self.plan_id!r} requires at least one "
                "topic syndication"
            )
        topic_ids = {topic.topic_id for topic in self.roadmap.topics}
        seen: set[str] = set()
        for syndication in self.syndications:
            if not isinstance(syndication, TopicSyndication):
                raise InvalidContentSyndicationError(
                    "a content syndication plan entry must be a typed topic "
                    "syndication"
                )
            if syndication.topic_id in seen:
                raise InvalidContentSyndicationError(
                    f"content syndication plan {self.plan_id!r} contains duplicate "
                    f"topic syndication {syndication.topic_id!r}"
                )
            seen.add(syndication.topic_id)
            if syndication.topic_id not in topic_ids:
                raise ContentSyndicationDependencyError(
                    f"topic syndication {syndication.topic_id!r} distributes a "
                    "topic the plan's Content Roadmap does not name"
                )

    @property
    def covered_topics(self) -> tuple[str, ...]:
        """The roadmap topics the plan already syndicates."""
        syndicated = {entry.topic_id for entry in self.syndications}
        return tuple(
            topic.topic_id
            for topic in self.roadmap.topics
            if topic.topic_id in syndicated
        )

    def missing_topics(self) -> tuple[str, ...]:
        """Roadmap topics the plan does not yet syndicate."""
        syndicated = {entry.topic_id for entry in self.syndications}
        return tuple(
            topic.topic_id
            for topic in self.roadmap.topics
            if topic.topic_id not in syndicated
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_topics()

    @property
    def is_plan(self) -> bool:
        """A content syndication plan is a plan, not activity or a result."""
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a content syndication plan as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The plan
        describes the distribution that will happen, while any measured movement
        is a separate observation, so a plan is never an observation.
        """
        raise ContentSyndicationObservationError(
            f"content syndication plan {claim_id!r} is distribution to perform, "
            "not an observed result, and cannot be recorded as an observation"
        )


@dataclass(frozen=True)
class ContentPromise:
    """The canon's measurable promise line for one piece of content (canon 32).

    The canon puts a promise with a metric and a timeline in every marketing
    message: "I always want to have in every marketing message a promise, a hook
    that's clearly measurable, relevant to them. With a timeline" (canon file
    32). The promise is frozen and reject-only, so an unmeasured or timeless
    promise cannot be represented as the content's hook.
    """

    measure: str
    timeline: str

    def __post_init__(self) -> None:
        for label, value in (
            ("content promise measure", self.measure),
            ("content promise timeline", self.timeline),
        ):
            if not value or not value.strip():
                raise InvalidContentCrusherError(f"{label} is required")


@dataclass(frozen=True)
class ContentCrusher:
    """The canon's Content Crusher outline for one roadmap topic (canon 12, 16, 32).

    SPEC.md section 12.5 records the Content Crusher as part of the
    audience-building and content flywheel canon gap and maps it to stage 6
    content assets. The canon uses the Content Crusher to turn one idea into
    "world class content" in any format (canon file 32): it captures the topic
    and title, a promise with a metric and a timeline, the transformation from
    the customer's top frustrations to their goal, a visual model, a metaphor,
    the context of where the content lives in the whole program, the steps, a
    real story, a choice and the next action. Rule one is that content never
    leaves the method -- "we never create a piece of content that doesn't live in
    the signature solution" (canon file 28) -- so the crusher is grounded on a
    same-tenant ``ContentRoadmap`` topic and teaches the roadmap's own Signature
    Solution steps.

    It is frozen and reject-only, so a blank identity, a missing beat, an untyped
    promise, a foreign or absent roadmap, a topic the roadmap does not plan or a
    step the solution does not name cannot be represented as a content outline.

    It is a stage 6 planning asset, not a new required gate kind (a
    methodology-owner decision, SPEC.md section 12.5). It does not authorize
    publishing or spend (SPEC.md sections 4 and 9) and it is never an observation
    (SPEC.md section 3). The canon suggests capturing the customer's "top three
    frustrations"; RED requires at least one and records the narrower count as an
    intentional deviation (SPEC.md section 12.1).
    """

    crusher_id: str
    tenant_id: str
    owner: str
    roadmap: ContentRoadmap
    topic_id: str
    title: str
    promise: ContentPromise
    frustrations: tuple[str, ...]
    goal: str
    model: str
    metaphor: str
    context: str
    steps: tuple[str, ...]
    story: str
    choice: str
    action: str

    def __post_init__(self) -> None:
        for label, value in (
            ("content crusher id", self.crusher_id),
            ("content crusher tenant id", self.tenant_id),
            ("content crusher owner", self.owner),
            ("content crusher topic id", self.topic_id),
            ("content crusher title", self.title),
            ("content crusher goal", self.goal),
            ("content crusher model", self.model),
            ("content crusher metaphor", self.metaphor),
            ("content crusher context", self.context),
            ("content crusher story", self.story),
            ("content crusher choice", self.choice),
            ("content crusher action", self.action),
        ):
            if not value or not value.strip():
                raise InvalidContentCrusherError(f"{label} is required")
        if not isinstance(self.promise, ContentPromise):
            raise InvalidContentCrusherError(
                "a content crusher must carry a typed content promise"
            )
        frustrations = tuple(self.frustrations)
        if not frustrations:
            raise InvalidContentCrusherError(
                "a content crusher must name at least one customer frustration"
            )
        for frustration in frustrations:
            if not frustration or not frustration.strip():
                raise InvalidContentCrusherError(
                    "a content crusher frustration must be a non-blank statement"
                )
        if not isinstance(self.roadmap, ContentRoadmap):
            raise ContentCrusherDependencyError(
                "a content crusher must outline a topic from a typed Content "
                "Roadmap"
            )
        if self.roadmap.tenant_id != self.tenant_id:
            raise ContentCrusherTenantBoundaryError(
                f"content crusher {self.crusher_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its Content Roadmap "
                f"{self.roadmap.roadmap_id!r} belongs to tenant "
                f"{self.roadmap.tenant_id!r}"
            )
        topic_ids = {topic.topic_id for topic in self.roadmap.topics}
        if self.topic_id not in topic_ids:
            raise ContentCrusherDependencyError(
                f"content crusher {self.crusher_id!r} outlines topic "
                f"{self.topic_id!r}, which the roadmap's Content Roadmap does not "
                "name"
            )
        step_names = {step.name for step in self.roadmap.method.steps}
        steps = tuple(self.steps)
        if not steps:
            raise InvalidContentCrusherError(
                "a content crusher must teach at least one Signature Solution step"
            )
        seen: set[str] = set()
        for step in steps:
            if not step or not step.strip():
                raise InvalidContentCrusherError(
                    "a content crusher step must be a non-blank Signature "
                    "Solution step"
                )
            if step in seen:
                raise InvalidContentCrusherError(
                    f"content crusher {self.crusher_id!r} teaches duplicate step "
                    f"{step!r}"
                )
            seen.add(step)
            if step not in step_names:
                raise ContentCrusherDependencyError(
                    f"content crusher {self.crusher_id!r} teaches step {step!r}, "
                    "which the roadmap's Signature Solution does not name"
                )

    @property
    def is_plan(self) -> bool:
        """A content crusher is a plan, not activity or an observed result."""
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a content crusher as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The
        crusher describes the content that will be produced, while any measured
        movement is a separate observation, so a crusher is never an observation.
        """
        raise ContentCrusherObservationError(
            f"content crusher {claim_id!r} is content to produce, not an observed "
            "result, and cannot be recorded as an observation"
        )

    def as_stage_asset(self, *, version: int) -> StageAssetVersion:
        """Project the crusher onto exact ``content-crusher`` gate evidence.

        SPEC.md sections 4 and 12.5 (owner decision 2026-10-03): a canon-informed
        asset already implemented in a bounded context becomes a required asset
        kind of its target stage gate, so the stage 6 "Campaign Message Approved"
        gate pins the typed content crusher (canon files 12, 16 and 32) as one
        exact ``StageAssetVersion``. A versionless projection is refused rather
        than silently pinned (SPEC.md sections 3 and 4).
        """
        if not isinstance(version, int) or version < 1:
            raise InvalidContentCrusherError(
                "the content crusher version must be a positive integer so the "
                "stage 6 gate can pin the reviewed asset at an exact version"
            )
        return StageAssetVersion(
            asset_id=self.crusher_id,
            tenant_id=self.tenant_id,
            kind=CONTENT_CRUSHER_KIND,
            version=version,
        )


class ProductMatrixModel(Enum):
    """The canon's seven ways to monetize a signature solution (canon 11, 12).

    SPEC.md section 4, stage 5 "Productize" names the delivery model, and
    SPEC.md section 12.3 shapes it with the canon's Perfect Product training
    (canon files 11 and 12). The canon calls the seven models "the top seven
    business models that you can use to monetize your knowledge" (canon file 11)
    and recommends group consulting as the best of both worlds. The model is the
    typed form of that delivery choice.
    """

    BOOKS_AND_INFO_PRODUCTS = "books_and_info_products"
    TRAINING_AND_MEMBERSHIPS = "training_and_memberships"
    SOFTWARE_APPLICATIONS = "software_applications"
    LIVE_EVENTS_AND_WORKSHOPS = "live_events_and_workshops"
    GROUP_CONSULTING = "group_consulting"
    ONE_ON_ONE_CONSULTING = "one_on_one_consulting"
    DONE_FOR_YOU_AGENCY = "done_for_you_agency"


PRODUCT_MATRIX_MODELS: tuple[ProductMatrixModel, ...] = (
    ProductMatrixModel.BOOKS_AND_INFO_PRODUCTS,
    ProductMatrixModel.TRAINING_AND_MEMBERSHIPS,
    ProductMatrixModel.SOFTWARE_APPLICATIONS,
    ProductMatrixModel.LIVE_EVENTS_AND_WORKSHOPS,
    ProductMatrixModel.GROUP_CONSULTING,
    ProductMatrixModel.ONE_ON_ONE_CONSULTING,
    ProductMatrixModel.DONE_FOR_YOU_AGENCY,
)

RECOMMENDED_PRODUCT_MODEL = ProductMatrixModel.GROUP_CONSULTING


class ProgramPricingBasis(Enum):
    """How a product program is priced (canon file 11).

    The canon prices the program "based on outcomes and value to your clients,
    not time and materials" (canon file 11). The basis is the typed form of that
    choice, and the time and materials basis is refused.
    """

    OUTCOME_VALUE = "outcome_value"
    TIME_AND_MATERIALS = "time_and_materials"


class ProgramCadence(Enum):
    """The canon's weekly delivery rhythm (canon file 12).

    The canon's Monday and Thursday method releases one piece of training on
    Monday and one coaching session on Thursday (canon file 12), so the program
    delivers at most one module a week.
    """

    MONDAY_TRAINING_THURSDAY_COACHING = "monday_training_thursday_coaching"


MINIMUM_PROGRAM_WEEKS = 6
MAXIMUM_PROGRAM_WEEKS = 12


@dataclass(frozen=True)
class ProductModule:
    """One step of the signature solution delivered as a program module.

    SPEC.md section 12.3 shapes stage 5 with the canon's Perfect Product training
    (canon files 11 and 12). The canon structures the program as one module per
    step of the signature solution: "break your signature solution into nine
    clear modules" (canon file 12), and each module names the outcome it produces
    and the deliverable it leaves with the client. The module is frozen and
    reject-only, so a module that leaves its step, outcome or deliverable unstated
    cannot be represented as part of the program.
    """

    module_id: str
    tenant_id: str
    signature_step: str
    position: int
    outcome: str
    deliverable: str

    def __post_init__(self) -> None:
        for label, value in (
            ("product module id", self.module_id),
            ("product module tenant id", self.tenant_id),
            ("product module signature step", self.signature_step),
            ("product module outcome", self.outcome),
            ("product module deliverable", self.deliverable),
        ):
            if not value or not value.strip():
                raise InvalidProductProgramError(f"{label} is required")
        if isinstance(self.position, bool) or not isinstance(self.position, int):
            raise InvalidProductProgramError(
                "a product module position must be an integer"
            )
        if self.position < 1:
            raise InvalidProductProgramError(
                "a product module position must be a positive integer"
            )


@dataclass(frozen=True)
class ProductProgram:
    """The canon's productized offer for one client and one Signature Solution.

    SPEC.md section 4, stage 5 "Productize" and its "Offer Locked" checkpoint
    need a delivery model, duration, pricing and a deliverable for every method
    step, and SPEC.md section 12.3 shapes stage 5 with the canon's Perfect
    Product training (canon files 11 and 12). The canon chooses one of the
    product matrix's seven business models (canon file 11), structures the
    program over six to twelve weeks (canon file 12), prices it on outcomes and
    value rather than time and materials (canon file 11) and delivers it on the
    Monday training and Thursday coaching cadence (canon file 12). The program is
    grounded on the same-tenant stage 4 ``SignatureSolution`` and delivers each
    of its steps as one module.

    It is frozen and reject-only, so a blank identity or owner, an untyped model,
    a time and materials pricing basis, a duration outside six to twelve weeks, a
    cadence other than Monday and Thursday, a foreign or absent method, a
    duplicate module, a module for a step the method does not have or a program
    that packs more weekly modules than it has weeks cannot be represented as a
    productized offer.

    It is a stage 5 required gate asset: per the owner decision in SPEC.md
    section 12.5 (2026-10-03), a canon-informed asset already implemented becomes
    a required kind of its target stage gate, so ``OfferPackage`` carries and
    projects it as the ``product-program`` kind. It does not authorize spending,
    publishing or client commitments (SPEC.md sections 4 and 9) and it is never an
    observation (SPEC.md section 3).
    """

    program_id: str
    tenant_id: str
    owner: str
    method: SignatureSolution
    model: ProductMatrixModel
    pricing_basis: ProgramPricingBasis
    duration_weeks: int
    cadence: ProgramCadence
    modules: tuple[ProductModule, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("product program id", self.program_id),
            ("product program tenant id", self.tenant_id),
            ("product program owner", self.owner),
        ):
            if not value or not value.strip():
                raise InvalidProductProgramError(f"{label} is required")
        if not isinstance(self.model, ProductMatrixModel):
            raise InvalidProductProgramError(
                "a product program must choose a typed product matrix model"
            )
        if not isinstance(self.pricing_basis, ProgramPricingBasis):
            raise InvalidProductProgramError(
                "a product program must name a typed pricing basis"
            )
        if self.pricing_basis is ProgramPricingBasis.TIME_AND_MATERIALS:
            raise ProductProgramPricingError(
                f"product program {self.program_id!r} prices on time and "
                "materials, but the canon prices the program on outcomes and "
                "value to the client"
            )
        if isinstance(self.duration_weeks, bool) or not isinstance(
            self.duration_weeks, int
        ):
            raise InvalidProductProgramError(
                "a product program duration must be a whole number of weeks"
            )
        if not MINIMUM_PROGRAM_WEEKS <= self.duration_weeks <= MAXIMUM_PROGRAM_WEEKS:
            raise InvalidProductProgramError(
                "a product program duration must be between "
                f"{MINIMUM_PROGRAM_WEEKS} and {MAXIMUM_PROGRAM_WEEKS} weeks, got "
                f"{self.duration_weeks}"
            )
        if not isinstance(self.cadence, ProgramCadence):
            raise InvalidProductProgramError(
                "a product program must name a typed delivery cadence"
            )
        if self.cadence is not ProgramCadence.MONDAY_TRAINING_THURSDAY_COACHING:
            raise InvalidProductProgramError(
                "a product program must deliver on the canon's Monday training "
                "and Thursday coaching cadence"
            )
        if not isinstance(self.method, SignatureSolution):
            raise ProductProgramDependencyError(
                "a product program must be grounded on a typed stage 4 Signature "
                "Solution"
            )
        if self.method.tenant_id != self.tenant_id:
            raise ProductProgramTenantBoundaryError(
                f"product program {self.program_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its Signature Solution "
                f"{self.method.solution_id!r} belongs to tenant "
                f"{self.method.tenant_id!r}"
            )
        modules = tuple(self.modules)
        if not modules:
            raise InvalidProductProgramError(
                f"product program {self.program_id!r} requires at least one module"
            )
        step_names = {step.name for step in self.method.steps}
        seen_ids: set[str] = set()
        seen_steps: set[str] = set()
        for module in modules:
            if not isinstance(module, ProductModule):
                raise InvalidProductProgramError(
                    "a product program module must be a typed product module"
                )
            if module.tenant_id != self.tenant_id:
                raise ProductProgramTenantBoundaryError(
                    f"product program {self.program_id!r} cites module "
                    f"{module.module_id!r} from another tenant"
                )
            if module.module_id in seen_ids:
                raise InvalidProductProgramError(
                    f"product program {self.program_id!r} contains duplicate module "
                    f"id {module.module_id!r}"
                )
            seen_ids.add(module.module_id)
            if module.signature_step in seen_steps:
                raise InvalidProductProgramError(
                    f"product program {self.program_id!r} delivers step "
                    f"{module.signature_step!r} more than once"
                )
            seen_steps.add(module.signature_step)
            if module.signature_step not in step_names:
                raise ProductProgramDependencyError(
                    f"product module {module.module_id!r} teaches step "
                    f"{module.signature_step!r}, which the program's Signature "
                    "Solution does not name"
                )
        if len(modules) > self.duration_weeks:
            raise InvalidProductProgramError(
                f"product program {self.program_id!r} delivers {len(modules)} "
                f"modules in {self.duration_weeks} weeks, but the Monday and "
                "Thursday cadence delivers at most one module a week"
            )

    @property
    def covered_steps(self) -> tuple[str, ...]:
        """The Signature Solution steps the program already delivers."""
        modules = self.modules
        return tuple(
            step.name
            for step in self.method.steps
            if any(module.signature_step == step.name for module in modules)
        )

    @property
    def missing_steps(self) -> tuple[str, ...]:
        """Signature Solution steps the program does not yet deliver."""
        covered = set(self.covered_steps)
        return tuple(
            step.name for step in self.method.steps if step.name not in covered
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_steps

    def module_for(self, step_name: str) -> ProductModule:
        """Return the single module delivering a named Signature Solution step."""
        for module in self.modules:
            if module.signature_step == step_name:
                return module
        raise ProductProgramDependencyError(
            f"Signature Solution step {step_name!r} has no module in product "
            f"program {self.program_id!r}"
        )

    @property
    def is_recommended_model(self) -> bool:
        """Whether the program chose the canon's recommended group consulting."""
        return self.model is RECOMMENDED_PRODUCT_MODEL

    @property
    def is_plan(self) -> bool:
        """A product program is a plan, not activity or an observed result."""
        return True

    def as_stage_asset(self, *, version: int) -> StageAssetVersion:
        """Project the program onto exact ``product-program`` gate evidence.

        SPEC.md sections 4 and 12.5 (owner decision 2026-10-03): a canon-informed
        asset already implemented in a bounded context becomes a required asset
        kind of its target stage gate, so the stage 5 "Offer Locked" gate pins the
        typed product program (canon files 11 and 12) as one exact
        ``StageAssetVersion``. A versionless projection is refused rather than
        silently pinned (SPEC.md sections 3 and 4).
        """
        if not isinstance(version, int) or version < 1:
            raise InvalidProductProgramError(
                "the product program version must be a positive integer so the "
                "stage 5 gate can pin the reviewed asset at an exact version"
            )
        return StageAssetVersion(
            asset_id=self.program_id,
            tenant_id=self.tenant_id,
            kind=PRODUCT_PROGRAM_KIND,
            version=version,
        )

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a product program as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The
        program describes the delivery model and pricing that will run, while any
        measured movement is a separate observation, so a program is never an
        observation.
        """
        raise ProductProgramObservationError(
            f"product program {claim_id!r} is a delivery and pricing plan, not an "
            "observed result, and cannot be recorded as an observation"
        )


class ResearchPlatform(Enum):
    """The audience sizing platforms the canon uses to size a market.

    SPEC.md section 12.3 maps audience sizing research onto stage 1 "Diagnose"
    and cites canon files 02 and 03. The canon sizes a market with Facebook's
    free Audience Insights tool -- "the most streamlined and effective way to
    start gathering audience data" (canon file 02) -- and confirms it with the
    native LinkedIn search "in addition to Facebook ... just to make sure you're
    climbing the right mountain" (canon file 03).
    """

    FACEBOOK_AUDIENCE_INSIGHTS = "facebook_audience_insights"
    LINKEDIN_SEARCH = "linkedin_search"


class InterestKind(Enum):
    """The kinds of interest signal the canon's audience sizing narrows on.

    The canon narrows an audience with the experts, authors, books, tools,
    publications and associations its avatar follows, not broad interests: "I
    want to say what experts or gurus might they follow? ... I want to look at
    authors. I want to look at books ... what publications or associations, what
    tools would they use?" (canon file 02). The enumerated kinds are the canon's
    own categories; ``OTHER`` keeps room for a signal the canon names but does
    not categorize.
    """

    EXPERT = "expert"
    AUTHOR = "author"
    BOOK = "book"
    TOOL = "tool"
    PUBLICATION = "publication"
    ASSOCIATION = "association"
    OTHER = "other"


@dataclass(frozen=True)
class InterestSignal:
    """One named interest the canon's audience sizing narrows on (canon file 02).

    The canon looks up specific experts, authors, tools, publications and
    associations because "those are general interests that aren't going to give
    me the kind of results I want" (canon file 02). The signal is frozen and
    reject-only, so a blank value or an untyped kind cannot be represented as an
    interest the sizing used.
    """

    kind: InterestKind
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, InterestKind):
            raise InvalidAudienceReachError(
                "an interest signal requires a typed canon interest kind"
            )
        if not self.value or not self.value.strip():
            raise InvalidAudienceReachError(
                "an interest signal requires a named expert, author, book, tool, "
                "publication or association"
            )


@dataclass(frozen=True)
class AudienceDefinition:
    """The location, age, gender and interests that define a sized audience.

    The canon sizes a market by location, age and gender plus a set of specific
    interest signals rather than broad interests (canon file 02: "Let's start
    with the location ... the age, the location ... Both genders, and let's look
    at some of these interests"). It is frozen and reject-only, so a blank
    filter or an audience with no distinct interest signal cannot be represented
    as a sized market.
    """

    location: str
    age: str
    gender: str
    interests: tuple[InterestSignal, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("audience location", self.location),
            ("audience age", self.age),
            ("audience gender", self.gender),
        ):
            if not value or not value.strip():
                raise InvalidAudienceReachError(f"{label} is required")
        interests = tuple(self.interests)
        if not interests:
            raise InvalidAudienceReachError(
                "an audience definition requires at least one specific interest "
                "signal, not only broad interests"
            )
        seen: set[tuple[InterestKind, str]] = set()
        for signal in interests:
            if not isinstance(signal, InterestSignal):
                raise InvalidAudienceReachError(
                    "an audience definition interest must be a typed interest "
                    "signal"
                )
            key = (signal.kind, signal.value.strip().lower())
            if key in seen:
                raise InvalidAudienceReachError(
                    f"audience definition repeats the {signal.kind.value} "
                    f"interest signal {signal.value!r}"
                )
            seen.add(key)


AUDIENCE_REACH_ESTIMATE_KIND = "audience-reach-estimate"


@dataclass(frozen=True)
class AudienceReachEstimate:
    """A canon-shaped stage 1 estimate of how big and reachable a market is.

    SPEC.md section 12.3 maps audience sizing research onto stage 1 "Diagnose"
    (canon files 02 and 03), and the canon's market gate is that "the market is
    big enough, reachable, and has a problem worth solving" (canon README, the
    Market station). The estimate names the research platform the sizing ran on,
    the audience definition it measured, the estimated reachable audience size,
    the source note the canon records it from, and the date it was captured, and
    it binds a named owner per SPEC.md section 12.4. The canon treats the sizing
    as a rough first pass that will change (canon file 02: "it doesn't have to be
    perfect. You'll probably change it"), so the estimate is a research input and
    is never an observation (SPEC.md section 3). It is frozen and reject-only,
    and it never authorizes outreach or spend (SPEC.md sections 4 and 9).
    """

    estimate_id: str
    tenant_id: str
    owner: str
    platform: ResearchPlatform
    audience: AudienceDefinition
    estimated_reach: int
    source_note: str
    captured_on: date

    def __post_init__(self) -> None:
        for label, value in (
            ("audience reach estimate id", self.estimate_id),
            ("audience reach estimate tenant id", self.tenant_id),
            ("audience reach estimate owner", self.owner),
            ("audience reach estimate source note", self.source_note),
        ):
            if not value or not value.strip():
                raise InvalidAudienceReachError(f"{label} is required")
        if not isinstance(self.platform, ResearchPlatform):
            raise InvalidAudienceReachError(
                "an audience reach estimate requires a typed canon research "
                "platform"
            )
        if not isinstance(self.audience, AudienceDefinition):
            raise InvalidAudienceReachError(
                "an audience reach estimate requires a typed audience definition"
            )
        if (
            not isinstance(self.estimated_reach, int)
            or isinstance(self.estimated_reach, bool)
            or self.estimated_reach <= 0
        ):
            raise InvalidAudienceReachError(
                "an audience reach estimate requires a positive integer "
                "reachable audience size"
            )
        if not isinstance(self.captured_on, date):
            raise InvalidAudienceReachError(
                "an audience reach estimate requires the date its sizing was "
                "captured"
            )

    @property
    def is_litmus_test(self) -> bool:
        """The canon treats sizing as a first-pass litmus test, not a result."""
        return True

    @property
    def is_plan(self) -> bool:
        """An audience reach estimate is a research input, not activity."""
        return True

    def as_stage_asset(self, *, version: int) -> StageAssetVersion:
        """Project the sizing onto exact ``audience-reach-estimate`` evidence.

        SPEC.md sections 4 and 12.5: a canon-informed asset already implemented
        in a bounded context becomes a required asset kind of its target stage
        gate, so the stage 1 "Avatar Locked" gate pins this measured market as
        one exact ``StageAssetVersion``. A versionless projection is refused
        rather than silently pinned (SPEC.md sections 3 and 4).
        """
        if not isinstance(version, int) or version < 1:
            raise InvalidAudienceReachError(
                "the audience reach estimate version must be a positive integer "
                "so the stage 1 gate can pin the reviewed asset at an exact "
                "version"
            )
        return StageAssetVersion(
            asset_id=self.estimate_id,
            tenant_id=self.tenant_id,
            kind=AUDIENCE_REACH_ESTIMATE_KIND,
            version=version,
        )

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent an audience reach estimate as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The canon
        calls the sizing a rough first pass that will change, so the estimate is
        a research input and any measured movement stays a separate observation.
        """
        raise AudienceReachObservationError(
            f"audience reach estimate {claim_id!r} is a market research input, "
            "not an observed result, and cannot be recorded as an observation"
        )


CONTENT_PLAN_CANON_REFERENCE = "25, 27, 28"


class ContentIdeaSource(Enum):
    """The Extract motions RED pulls ideas from (SPEC.md section 12.5).

    The canon builds every content topic by brainstorming the FAQs and questions
    the audience already asks about a step of the Signature Solution (canon file
    27: "just brainstorming FAQs and questions you already know your audience is
    asking"), and reminds the operator that clients keep asking the same question.
    RED types the sources the Extract motion pulls from: the FAQs, the problems
    the step solves, the process itself, and the reviews and praise the client
    already has (SPEC.md section 12.5).
    """

    FAQ = "faq"
    PROBLEM = "problem"
    PROCESS = "process"
    REVIEW_AND_PRAISE = "review_and_praise"


class ContentPlanChannel(Enum):
    """The two plans the Extract motion builds (SPEC.md section 12.5).

    The implementation plan's canon gap register names "an email and social
    content plan" as the Extract output, so RED types those two deliveries and a
    plan cannot represent itself as complete without both.
    """

    EMAIL = "email"
    SOCIAL = "social"


@dataclass(frozen=True)
class ContentTheme:
    """One currency-aligned theme grouping extracted content ideas.

    The Extract motion groups the ideas it pulls from the Signature Solution
    around the one locked currency (SPEC.md section 12.5; canon file 27), so a
    theme records the measure of that currency it advances. The theme is frozen
    and reject-only, so a blank identity or a theme with no currency measure
    cannot be represented as a theme the ideas group under.
    """

    theme_id: str
    tenant_id: str
    name: str
    currency_measure: str

    def __post_init__(self) -> None:
        for label, value in (
            ("content theme id", self.theme_id),
            ("content theme tenant id", self.tenant_id),
            ("content theme name", self.name),
            ("content theme currency measure", self.currency_measure),
        ):
            if not value or not value.strip():
                raise InvalidContentPlanError(f"{label} is required")


@dataclass(frozen=True)
class ContentIdea:
    """One idea the Extract motion pulls from a Signature Solution step.

    The canon's first content rule is that content never leaves the method ("we
    never create a piece of content that doesn't live in the signature solution",
    canon file 28). The idea records the step it comes from, the typed source it
    was extracted as (SPEC.md section 12.5), the question the audience already
    asks, the currency-aligned theme it belongs to, and the plan channels it
    feeds. It is frozen and reject-only, so an idea that leaves its step, source,
    prompt, theme or channel set unstated cannot be represented.
    """

    idea_id: str
    tenant_id: str
    signature_step: str
    source: ContentIdeaSource
    prompt: str
    theme_id: str
    channels: tuple[ContentPlanChannel, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("content idea id", self.idea_id),
            ("content idea tenant id", self.tenant_id),
            ("content idea signature step", self.signature_step),
            ("content idea prompt", self.prompt),
            ("content idea theme id", self.theme_id),
        ):
            if not value or not value.strip():
                raise InvalidContentPlanError(f"{label} is required")
        if not isinstance(self.source, ContentIdeaSource):
            raise InvalidContentPlanError(
                "a content idea source must be a typed extract source"
            )
        channels = tuple(self.channels)
        if not channels:
            raise InvalidContentPlanError(
                f"content idea {self.idea_id!r} must feed at least one plan channel"
            )
        seen: set[ContentPlanChannel] = set()
        for channel in channels:
            if not isinstance(channel, ContentPlanChannel):
                raise InvalidContentPlanError(
                    "a content idea channel must be a typed content plan channel"
                )
            if channel in seen:
                raise InvalidContentPlanError(
                    f"content idea {self.idea_id!r} names duplicate channel "
                    f"{channel.value!r}"
                )
            seen.add(channel)


@dataclass(frozen=True)
class ContentPlan:
    """The Extract content plan feeding stage 6 and stage 10 content operations.

    SPEC.md section 12.5 records the Extract motion ("pull key ideas from the
    signature solution ... group themes around the one currency, and build an
    email and social content plan") as a canon gap, and the implementation plan's
    canon gap register names this pure-domain ``ContentPlan`` as its bounded
    slice, an asset inside stage 6, not a new stage or required gate kind. The
    plan grounds on a same-tenant stage 4 ``SignatureSolution`` and stage 2
    ``PrimaryCurrency``, groups the extracted ideas under currency-aligned
    themes, requires both an email and a social delivery, binds a named owner and
    reports the solution steps it does not yet cover. It is frozen and
    reject-only, so a blank identity, an untyped or foreign method or currency, a
    duplicate theme or idea, a theme the currency does not carry, an idea whose
    step the solution does not name, or a plan missing either delivery cannot be
    represented as a content plan.

    It does not authorize publishing or spend (SPEC.md sections 4 and 9) and it
    is never an observation (SPEC.md section 3).
    """

    plan_id: str
    tenant_id: str
    owner: str
    method: SignatureSolution
    currency: PrimaryCurrency
    themes: tuple[ContentTheme, ...]
    ideas: tuple[ContentIdea, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("content plan id", self.plan_id),
            ("content plan tenant id", self.tenant_id),
            ("content plan owner", self.owner),
        ):
            if not value or not value.strip():
                raise InvalidContentPlanError(f"{label} is required")
        if not isinstance(self.method, SignatureSolution):
            raise ContentPlanDependencyError(
                "a content plan must extract from a typed stage 4 Signature Solution"
            )
        if self.method.tenant_id != self.tenant_id:
            raise ContentPlanTenantBoundaryError(
                f"content plan {self.plan_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its Signature Solution "
                f"{self.method.solution_id!r} belongs to tenant "
                f"{self.method.tenant_id!r}"
            )
        if not isinstance(self.currency, PrimaryCurrency):
            raise ContentPlanDependencyError(
                "a content plan must group its themes around a typed stage 2 "
                "Primary Currency"
            )
        if self.currency.tenant_id != self.tenant_id:
            raise ContentPlanTenantBoundaryError(
                f"content plan {self.plan_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its Primary Currency belongs to tenant "
                f"{self.currency.tenant_id!r}"
            )
        themes = tuple(self.themes)
        if not themes:
            raise InvalidContentPlanError(
                f"content plan {self.plan_id!r} requires at least one theme"
            )
        currency_measures = {
            self.currency.current_measure.strip(),
            self.currency.desired_measure.strip(),
        }
        theme_ids: set[str] = set()
        for theme in themes:
            if not isinstance(theme, ContentTheme):
                raise InvalidContentPlanError(
                    "a content plan theme must be a typed content theme"
                )
            if theme.tenant_id != self.tenant_id:
                raise ContentPlanTenantBoundaryError(
                    f"content plan {self.plan_id!r} cites theme "
                    f"{theme.theme_id!r} from another tenant"
                )
            if theme.theme_id in theme_ids:
                raise InvalidContentPlanError(
                    f"content plan {self.plan_id!r} contains duplicate theme id "
                    f"{theme.theme_id!r}"
                )
            theme_ids.add(theme.theme_id)
            if theme.currency_measure.strip() not in currency_measures:
                raise ContentPlanThemeError(
                    f"content theme {theme.theme_id!r} advances measure "
                    f"{theme.currency_measure!r}, which the locked primary "
                    f"currency {self.currency.currency!r} does not carry"
                )
        ideas = tuple(self.ideas)
        if not ideas:
            raise InvalidContentPlanError(
                f"content plan {self.plan_id!r} requires at least one idea"
            )
        step_names = {step.name for step in self.method.steps}
        seen_ideas: set[str] = set()
        delivered: set[ContentPlanChannel] = set()
        for idea in ideas:
            if not isinstance(idea, ContentIdea):
                raise InvalidContentPlanError(
                    "a content plan idea must be a typed content idea"
                )
            if idea.tenant_id != self.tenant_id:
                raise ContentPlanTenantBoundaryError(
                    f"content plan {self.plan_id!r} cites idea {idea.idea_id!r} "
                    "from another tenant"
                )
            if idea.idea_id in seen_ideas:
                raise InvalidContentPlanError(
                    f"content plan {self.plan_id!r} contains duplicate idea id "
                    f"{idea.idea_id!r}"
                )
            seen_ideas.add(idea.idea_id)
            if idea.signature_step not in step_names:
                raise ContentPlanDependencyError(
                    f"content idea {idea.idea_id!r} maps from Signature Solution "
                    f"step {idea.signature_step!r}, which the plan's Signature "
                    "Solution does not name"
                )
            if idea.theme_id not in theme_ids:
                raise InvalidContentPlanError(
                    f"content idea {idea.idea_id!r} groups under theme "
                    f"{idea.theme_id!r}, which the plan does not declare"
                )
            delivered.update(idea.channels)
        missing_deliveries = [
            channel.value
            for channel in ContentPlanChannel
            if channel not in delivered
        ]
        if missing_deliveries:
            raise InvalidContentPlanError(
                f"content plan {self.plan_id!r} must build an email and a social "
                "content plan; missing delivery channels: "
                + ", ".join(sorted(missing_deliveries))
            )

    @property
    def covered_steps(self) -> tuple[str, ...]:
        """The Signature Solution steps the plan already has an idea for."""
        ideas = self.ideas
        return tuple(
            step.name
            for step in self.method.steps
            if any(idea.signature_step == step.name for idea in ideas)
        )

    def missing_steps(self) -> tuple[str, ...]:
        """Signature Solution steps the plan does not yet cover with an idea."""
        covered = set(self.covered_steps)
        return tuple(
            step.name for step in self.method.steps if step.name not in covered
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_steps()

    def ideas_for_theme(self, theme_id: str) -> tuple[ContentIdea, ...]:
        """The extracted ideas grouped under one currency-aligned theme."""
        return tuple(idea for idea in self.ideas if idea.theme_id == theme_id)

    @property
    def is_plan(self) -> bool:
        """A content plan is a plan, not activity or an observed result."""
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a content plan as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The plan
        describes the content that will be planned, produced and published, while
        any measured reach is a separate observation, so a content plan is never
        an observation.
        """
        raise ContentPlanObservationError(
            f"content plan {claim_id!r} is content to plan, produce and publish, "
            "not an observed result, and cannot be recorded as an observation"
        )


    def as_stage_asset(self, *, version: int) -> StageAssetVersion:
        """Project the plan onto exact ``content-plan`` gate evidence.

        SPEC.md sections 4 and 12.5 (owner decision 2026-10-03): a canon-informed
        asset already implemented in a bounded context becomes a required asset
        kind of its target stage gate, so the stage 6 "Campaign Message Approved"
        gate pins the typed content plan (canon files 25, 27 and 28) as one exact
        ``StageAssetVersion``. A versionless projection is refused rather than
        silently pinned (SPEC.md sections 3 and 4).
        """
        if not isinstance(version, int) or version < 1:
            raise InvalidContentPlanError(
                "the content plan version must be a positive integer so the "
                "stage 6 gate can pin the reviewed asset at an exact version"
            )
        return StageAssetVersion(
            asset_id=self.plan_id,
            tenant_id=self.tenant_id,
            kind=CONTENT_PLAN_KIND,
            version=version,
        )

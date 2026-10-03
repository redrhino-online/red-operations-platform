"""Value objects for the Commercial Design bounded context (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from redops.contexts.commercial.domain.errors import (
    CampaignMessageTenantBoundaryError,
    CurrencyTenantBoundaryError,
    DiagnosisTenantBoundaryError,
    DiagnosticTenantBoundaryError,
    InvalidAvatarProfileError,
    InvalidBusinessSnapshotError,
    InvalidCampaignMessagePackageError,
    InvalidCurrencyInventoryError,
    InvalidCurrencyPackageError,
    InvalidDeliverySpecificationError,
    InvalidDiagnosisPackageError,
    InvalidDiagnosticPackageError,
    InvalidMarketAwarenessMapError,
    InvalidMillionDollarMessageError,
    InvalidNurtureError,
    InvalidOfferError,
    InvalidOfferFunnelAuditError,
    InvalidOfferPackageError,
    InvalidPositioningDecisionError,
    InvalidSignaturePackageError,
    InvalidTargetMarketMatchmakerError,
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
    "awareness-map",
    "customer-evidence",
    "voice-notes",
)


@dataclass(frozen=True)
class DiagnosisPackage:
    """The reviewed stage 1 assets, projected to the nine canonical gate kinds.

    SPEC.md section 4, stage 1 "Diagnose": the required asset package enumerates
    the avatar with demographics, psychographics, pains, goals, consequences of
    inaction, awareness, customer evidence and voice notes alongside the business
    snapshot and the offer and funnel audit. The Commercial context reviews those
    as three rich value objects (``AvatarProfile``, ``BusinessSnapshot``,
    ``OfferFunnelAudit``); this package is the bridge to the governance gate,
    which pins one exact ``StageAssetVersion`` per canonical kind. The avatar
    value carries the content for its seven kinds; the business snapshot and offer
    and funnel audit each satisfy one kind.

    SPEC.md sections 3 and 4 require a passing gate to pin the exact evidence, so
    each reviewed asset is projected with a positive integer version and a blank
    version or a cross-tenant value is refused rather than silently pinned. The
    canon (SPEC.md section 12.3: stage 1 uses canon files 02, 03 and 04) groups
    the avatar's pains, goals, consequences and why into one Avatar Goals Grid,
    but the SPEC stage 1 package enumerates them as separate required items, so
    they are projected as separate kinds while the avatar carries the content.
    """

    package_id: str
    tenant_id: str
    avatar: AvatarProfile
    avatar_version: int
    business_snapshot: BusinessSnapshot
    business_snapshot_version: int
    offer_funnel_audit: OfferFunnelAudit
    offer_funnel_audit_version: int

    def __post_init__(self) -> None:
        for label, value in (
            ("diagnosis package id", self.package_id),
            ("diagnosis package tenant id", self.tenant_id),
        ):
            if not value or not value.strip():
                raise InvalidDiagnosisPackageError(f"{label} is required")
        for label, value in (
            ("avatar", self.avatar),
            ("business snapshot", self.business_snapshot),
            ("offer and funnel audit", self.offer_funnel_audit),
        ):
            if value.tenant_id != self.tenant_id:
                raise DiagnosisTenantBoundaryError(
                    f"diagnosis {label} belongs to tenant {value.tenant_id!r}, "
                    f"not package tenant {self.tenant_id!r}"
                )
        for label, value in (
            ("avatar version", self.avatar_version),
            ("business snapshot version", self.business_snapshot_version),
            ("offer and funnel audit version", self.offer_funnel_audit_version),
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
)


@dataclass(frozen=True)
class SignaturePackage:
    """The reviewed stage 4 solution, projected to the twelve canonical gate kinds.

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
    continuity at construction, so each canonical kind is projected from the
    single reviewed solution at one positive integer version, and a blank
    identity, a versionless solution or a cross-tenant solution is refused rather
    than silently pinned (SPEC.md sections 3 and 4).
    """

    package_id: str
    tenant_id: str
    solution: SignatureSolution
    solution_version: int

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

    @property
    def kinds(self) -> frozenset[str]:
        """The canonical kinds the reviewed stage 4 solution projects onto."""
        return frozenset(CANONICAL_SIGNATURE_KINDS)

    def missing_kinds(self) -> tuple[str, ...]:
        """Canonical stage 4 kinds not covered by the projected solution."""
        covered = {asset.kind for asset in self.stage_asset_versions()}
        return tuple(
            kind for kind in CANONICAL_SIGNATURE_KINDS if kind not in covered
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_kinds()

    def stage_asset_versions(self) -> tuple[StageAssetVersion, ...]:
        """Project the reviewed stage 4 solution onto exact governance evidence.

        Every canonical kind belongs to the same reviewed ``SignatureSolution``,
        so each is pinned to that solution's identity at its exact version.
        Governance still pins each projection for the workspace tenant, so a
        cross-client solution is refused rather than silently authorized (SPEC.md
        sections 3, 4 and 11).
        """
        return tuple(
            StageAssetVersion(
                asset_id=self.solution.solution_id,
                tenant_id=self.tenant_id,
                kind=kind,
                version=self.solution_version,
            )
            for kind in CANONICAL_SIGNATURE_KINDS
        )


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
)


@dataclass(frozen=True)
class OfferPackage:
    """The reviewed stage 5 delivery, projected to the twelve canonical gate kinds.

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
    each canonical kind is projected from the single reviewed delivery at one
    positive integer version, and a blank identity, a versionless delivery or a
    cross-tenant delivery is refused rather than silently pinned (SPEC.md
    sections 3 and 4).
    """

    package_id: str
    tenant_id: str
    delivery: DeliverySpecification
    delivery_version: int

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

    @property
    def kinds(self) -> frozenset[str]:
        """The canonical kinds the reviewed stage 5 delivery projects onto."""
        return frozenset(CANONICAL_OFFER_KINDS)

    def missing_kinds(self) -> tuple[str, ...]:
        """Canonical stage 5 kinds not covered by the projected delivery."""
        covered = {asset.kind for asset in self.stage_asset_versions()}
        return tuple(
            kind for kind in CANONICAL_OFFER_KINDS if kind not in covered
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_kinds()

    def stage_asset_versions(self) -> tuple[StageAssetVersion, ...]:
        """Project the reviewed stage 5 delivery onto exact governance evidence.

        Every canonical kind belongs to the same reviewed
        ``DeliverySpecification``, so each is pinned to that delivery's identity
        at its exact version. Governance still pins each projection for the
        workspace tenant, so a cross-client delivery is refused rather than
        silently authorized (SPEC.md sections 3, 4 and 11).
        """
        return tuple(
            StageAssetVersion(
                asset_id=self.delivery.delivery_id,
                tenant_id=self.tenant_id,
                kind=kind,
                version=self.delivery_version,
            )
            for kind in CANONICAL_OFFER_KINDS
        )


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
)


@dataclass(frozen=True)
class CampaignMessagePackage:
    """The reviewed stage 6 message, projected to the twelve canonical gate kinds.

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
    a Content Roadmap and Content Crusher. ``CampaignMessage`` already enforces
    that coherent shape and its dependency on the approved stage 5 offer at
    construction, so each canonical kind is projected from the single reviewed
    message at one positive integer version, and a blank identity, a versionless
    message or a cross-tenant message is refused rather than silently pinned
    (SPEC.md sections 3 and 4).
    """

    package_id: str
    tenant_id: str
    message: "CampaignMessage"
    message_version: int

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
        if not isinstance(self.message_version, int) or self.message_version < 1:
            raise InvalidCampaignMessagePackageError(
                "the campaign message version must be a positive integer so the "
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
        """Project the reviewed stage 6 message onto exact governance evidence.

        Every canonical kind belongs to the same reviewed ``CampaignMessage``, so
        each is pinned to that message's identity at its exact version. Governance
        still pins each projection for the workspace tenant, so a cross-client
        message is refused rather than silently authorized (SPEC.md sections 3, 4
        and 11).
        """
        return tuple(
            StageAssetVersion(
                asset_id=self.message.message_id,
                tenant_id=self.tenant_id,
                kind=kind,
                version=self.message_version,
            )
            for kind in CANONICAL_MESSAGE_KINDS
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

    It is a planning decision for stages 1 and 2, not a new required gate kind (a
    methodology-owner decision, SPEC.md section 12.5). It does not authorize
    outreach or spend (SPEC.md sections 4 and 9) and it is never an observation
    (SPEC.md section 3).
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

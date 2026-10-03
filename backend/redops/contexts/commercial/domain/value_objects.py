"""Value objects for the Commercial Design bounded context (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from redops.contexts.commercial.domain.errors import (
    DiagnosisTenantBoundaryError,
    InvalidAvatarProfileError,
    InvalidBusinessSnapshotError,
    InvalidDeliverySpecificationError,
    InvalidDiagnosisPackageError,
    InvalidOfferError,
    InvalidOfferFunnelAuditError,
)
from redops.contexts.governance.domain.value_objects import StageAssetVersion
from redops.contexts.method.domain.entities import SignatureSolution
from redops.contexts.method.domain.value_objects import (
    ImpactAssessment,
    SemanticVersion,
)

if TYPE_CHECKING:
    from redops.contexts.commercial.domain.entities import OfferVersion


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

"""Readiness policy for the Commercial Design bounded context (pure domain).

SPEC.md section 3: "Production requires approved dependencies". An offer may
only become production ready when each of its method references is satisfied by
an approved method version for the same tenant, at the exact version and
intended use. This is the offer-side half of the SPEC.md section 4 method
change impact rule.
"""

from __future__ import annotations

from datetime import date
from typing import Iterable

from redops.contexts.commercial.domain.entities import (
    CampaignMessage,
    OfferVersion,
)
from redops.contexts.commercial.domain.errors import (
    AvatarLockedError,
    CampaignMessageAlignmentError,
    MarketAwarenessTargetingError,
    OfferReadinessError,
    TargetMarketMatchError,
    UnsourcedDiagnosisEvidenceError,
)
from redops.contexts.commercial.domain.value_objects import (
    AvatarProfile,
    BusinessSnapshot,
    MarketAwarenessMap,
    MethodReference,
    OfferFunnelAudit,
    OfferImpactAssessment,
    TargetMarketMatchmaker,
)
from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.knowledge.domain.policies import sourced_claim_ids
from redops.contexts.method.domain.entities import MethodVersion
from redops.contexts.method.domain.policies import MethodChangeImpactPolicy
from redops.contexts.method.domain.value_objects import (
    ArtifactKind,
    DependentArtifact,
)


class OfferReadinessPolicy:
    """Refuses production readiness when a method dependency is not approved.

    It also enforces that the stage 5 `DeliverySpecification` is grounded on the
    exact stage 4 Signature Solution pinned by an approved method reference, so
    an offer cannot carry a delivery package for a different transformation than
    the method it is grounded on (SPEC.md sections 3 and 4).
    """

    def require(
        self, offer: OfferVersion, approved_methods: Iterable[MethodVersion]
    ) -> None:
        if offer.state.is_terminal:
            raise OfferReadinessError(
                f"terminal offer {offer.offer_id!r} cannot be production ready"
            )
        methods = tuple(approved_methods)
        for reference in offer.method_refs:
            if not any(self._matches(offer, reference, method) for method in methods):
                raise OfferReadinessError(
                    f"offer {offer.offer_id!r} cannot be production ready: "
                    f"method {reference.method_id!r} version "
                    f"{reference.version} for {reference.intended_use!r} is not "
                    "an approved dependency for this tenant"
                )
        if offer.delivery_specification is not None:
            self._require_grounded_delivery_specification(offer, methods)

    def _require_grounded_delivery_specification(
        self, offer: OfferVersion, methods: tuple[MethodVersion, ...]
    ) -> None:
        specification = offer.delivery_specification
        assert specification is not None
        grounded = specification.signature_solution
        for reference in offer.method_refs:
            for method in methods:
                if self._matches(offer, reference, method) and (
                    method.signature_solution == grounded
                ):
                    return
        raise OfferReadinessError(
            f"offer {offer.offer_id!r} cannot be production ready: its stage 5 "
            "delivery specification is not grounded on the Signature Solution "
            "pinned by an approved method reference"
        )

    @staticmethod
    def _matches(
        offer: OfferVersion, reference: MethodReference, method: MethodVersion
    ) -> bool:
        return (
            method.method_id == reference.method_id
            and method.tenant_id == offer.tenant_id
            and method.authorizes(reference.version, reference.intended_use)
        )


class OfferChangeImpactPolicy:
    """Discovers dependent offers when an approved method version changes.

    SPEC.md section 4 and section 11: changing an approved method version must
    identify its dependents. This policy matches a candidate `OfferVersion` by
    its pinned `method_refs` (method id, exact previous version and intended use)
    and marks each non-terminal match review required, reusing the Method
    context's assessment for validation, severity and the owned review queue.
    """

    def assess(
        self,
        previous: MethodVersion,
        current: MethodVersion,
        offers: Iterable[OfferVersion],
        *,
        due_on: date,
        reason: str = "upstream method version changed",
    ) -> OfferImpactAssessment:
        dependents = tuple(
            offer for offer in offers if self._depends_on(offer, previous)
        )
        requirements = tuple(
            DependentArtifact(offer.offer_id, ArtifactKind.OFFER, offer.owner)
            for offer in dependents
        )
        impact = MethodChangeImpactPolicy().assess(
            previous, current, requirements, due_on=due_on, reason=reason
        )
        marked = tuple(
            offer.mark_review_required(reason=reason) for offer in dependents
        )
        return OfferImpactAssessment(impact=impact, offers=marked)

    @staticmethod
    def _depends_on(offer: OfferVersion, previous: MethodVersion) -> bool:
        if not previous.is_approved or offer.state.is_terminal:
            return False
        if offer.tenant_id != previous.tenant_id:
            return False
        intended_use = previous.approval.intended_use
        return any(
            reference.method_id == previous.method_id
            and reference.version == previous.semantic_version
            and reference.intended_use == intended_use
            for reference in offer.method_refs
        )


class CampaignMessageAlignmentPolicy:
    """Refuses approval when a stage 6 message conflicts with its locked offer.

    SPEC.md section 4, stage 6 "Message" and its "Campaign Message Approved"
    checkpoint: the avatar, currency, problem, promise, method, product and CTA
    must agree. The avatar, promise and product are compared to the approved
    stage 5 offer; the method must be one the offer pins and is authorized by an
    approved method version; the currency and problem are compared to that
    approved method's locked stage 2 primary currency and stage 3 diagnostic
    model. A message that conflicts with any of these, or that is grounded on an
    offer that is not production ready, cannot be approved (Phase 4 TDD example:
    "campaign message conflicting with the offer blocks approval").
    """

    def require(
        self,
        message: CampaignMessage,
        approved_methods: Iterable[MethodVersion],
    ) -> None:
        if message.state.is_terminal:
            raise CampaignMessageAlignmentError(
                f"terminal campaign message {message.message_id!r} cannot be "
                "approved"
            )
        offer = message.offer
        if offer.tenant_id != message.tenant_id:
            raise CampaignMessageAlignmentError(
                "a campaign message cannot be grounded on another tenant's offer"
            )
        if not offer.is_production_ready:
            raise CampaignMessageAlignmentError(
                f"campaign message {message.message_id!r} cannot be approved: "
                "it is grounded on a stage 5 offer that is not production ready"
            )
        if message.avatar != offer.audience:
            raise CampaignMessageAlignmentError(
                f"campaign message {message.message_id!r} avatar does not agree "
                "with the approved offer audience"
            )
        if message.promise != offer.promise:
            raise CampaignMessageAlignmentError(
                f"campaign message {message.message_id!r} promise does not agree "
                "with the approved offer promise"
            )
        if message.product_offer_id != offer.offer_id:
            raise CampaignMessageAlignmentError(
                f"campaign message {message.message_id!r} product does not agree "
                "with the approved offer"
            )
        if message.method_reference not in offer.method_refs:
            raise CampaignMessageAlignmentError(
                f"campaign message {message.message_id!r} method does not agree "
                "with any method pinned by the approved offer"
            )
        method = self._authorizing(message, tuple(approved_methods))
        if method is None:
            raise CampaignMessageAlignmentError(
                f"campaign message {message.message_id!r} cannot be approved: its "
                "method is not an approved dependency for this tenant"
            )
        currency = method.primary_currency
        if currency is None or message.currency != currency.currency:
            raise CampaignMessageAlignmentError(
                f"campaign message {message.message_id!r} currency does not agree "
                "with the approved method's locked primary currency"
            )
        model = method.diagnostic_model
        problems = (
            frozenset(
                problem
                for level in model.levels
                for problem in level.problems
            )
            if model is not None
            else frozenset()
        )
        if message.problem not in problems:
            raise CampaignMessageAlignmentError(
                f"campaign message {message.message_id!r} problem does not agree "
                "with the approved method's diagnostic model"
            )

    @staticmethod
    def _authorizing(
        message: CampaignMessage, methods: tuple[MethodVersion, ...]
    ) -> MethodVersion | None:
        reference = message.method_reference
        for method in methods:
            if (
                method.method_id == reference.method_id
                and method.tenant_id == message.tenant_id
                and method.authorizes(reference.version, reference.intended_use)
            ):
                return method
        return None


class AvatarLockedPolicy:
    """Refuses the stage 1 "Avatar Locked" checkpoint on an unsourced avatar.

    SPEC.md section 4, stage 1 "Diagnose" and its "Avatar Locked" checkpoint: a
    stranger can recognize who the customer is, what matters, and why now, and
    the required asset package names customer evidence. SPEC.md section 1
    requires every output to have a source, so the avatar's customer evidence
    must be a known, directly sourced Knowledge claim of the same client.
    Evidence that is unsourced, merely derived or proposed, or belongs to another
    client cannot support the lock (SPEC.md sections 1, 4 and 11).
    """

    def require_locked(
        self, profile: AvatarProfile, claims: Iterable[Claim]
    ) -> None:
        sourced = sourced_claim_ids(profile.tenant_id, claims)
        for claim_id in profile.customer_evidence_claim_ids:
            if claim_id not in sourced:
                raise AvatarLockedError(
                    f"avatar {profile.avatar_id!r} cannot lock: customer "
                    f"evidence {claim_id!r} is not a known, directly sourced "
                    "claim for this tenant"
                )


class MarketAwarenessPolicy:
    """Refuses a stage 1 awareness position the canon does not target initially.

    SPEC.md section 12.3 maps the market awareness levels to stage 1 "Diagnose"
    and section 12.5 records them as a canon gap. The canon places the completely
    unaware outside the initial target (canon file 04: "which is who we definitely
    do not want to sell to initially") and aims at people actively seeking a
    solution, so an awareness map whose primary level is completely unaware cannot
    be represented as a defensible stage 1 position (SPEC.md section 4, stage 1
    "Avatar Locked").
    """

    def require_targetable(self, awareness: MarketAwarenessMap) -> None:
        if not awareness.primary_level.is_initially_targetable:
            raise MarketAwarenessTargetingError(
                f"market awareness map {awareness.map_id!r} targets the "
                f"{awareness.primary_level.value!r} market, which the canon does "
                "not treat as an initial target"
            )


class TargetMarketMatchPolicy:
    """Refuses a target market match the canon cannot serve now.

    SPEC.md section 12.5 records the target market matchmaker as part of the
    positioning and decision tools canon gap. The canon narrows the candidate
    markets to the one to serve now (canon file 00), and its awareness research
    (canon file 04) places the completely unaware outside the initial target
    ("which is who we definitely do not want to sell to initially"). A match
    whose chosen market's awareness position is not initially targetable cannot
    be the current target market (SPEC.md sections 4 and 12.5).
    """

    def require_servable(self, match: TargetMarketMatchmaker) -> None:
        if not match.awareness_map.primary_level.is_initially_targetable:
            raise TargetMarketMatchError(
                f"target market match {match.matchmaker_id!r} selects market "
                f"{match.selected_market_id!r}, but its awareness position "
                f"{match.awareness_map.primary_level.value!r} is not an initial "
                "target the canon will serve"
            )


class DiagnosisEvidencePolicy:
    """Refuses a stage 1 diagnosis asset evidenced by unsourced material.

    SPEC.md section 4, stage 1 "Diagnose" and SPEC.md section 1: the business
    snapshot and the offer and funnel audit are required diagnosis assets, and
    every output has a source. Each asset's evidence must be a known, directly
    sourced Knowledge claim of the same client, so an unsourced, derived,
    proposed or foreign claim cannot be represented as stage 1 diagnosis
    evidence (SPEC.md sections 1, 4 and 11).
    """

    def require_business_snapshot_sourced(
        self, snapshot: BusinessSnapshot, claims: Iterable[Claim]
    ) -> None:
        self._require(
            "business snapshot",
            snapshot.snapshot_id,
            snapshot.tenant_id,
            snapshot.evidence_claim_ids,
            claims,
        )

    def require_offer_funnel_audit_sourced(
        self, audit: OfferFunnelAudit, claims: Iterable[Claim]
    ) -> None:
        self._require(
            "offer and funnel audit",
            audit.audit_id,
            audit.tenant_id,
            audit.evidence_claim_ids,
            claims,
        )

    @staticmethod
    def _require(
        label: str,
        asset_id: str,
        tenant_id: str,
        evidence_claim_ids: tuple[str, ...],
        claims: Iterable[Claim],
    ) -> None:
        sourced = sourced_claim_ids(tenant_id, claims)
        for claim_id in evidence_claim_ids:
            if claim_id not in sourced:
                raise UnsourcedDiagnosisEvidenceError(
                    f"{label} {asset_id!r} cannot be evidenced: claim "
                    f"{claim_id!r} is not a known, directly sourced claim for "
                    "this tenant"
                )

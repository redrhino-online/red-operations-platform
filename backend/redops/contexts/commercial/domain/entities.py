"""Aggregates for the Commercial Design bounded context (pure domain).

OfferVersion is the client's offer specification at a pinned method dependency
(SPEC.md section 3). Its invariant is that production readiness requires an
approved method dependency at the exact version and intended use it references.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable

from redops.contexts.commercial.domain.errors import (
    CampaignMessageDependencyError,
    InvalidCampaignMessageError,
    InvalidOfferError,
    OfferDependencyError,
    OfferReadinessError,
)
from redops.contexts.commercial.domain.value_objects import (
    CampaignMessageState,
    DeliverySpecification,
    MethodReference,
    OfferState,
)
from redops.contexts.method.domain.entities import MethodVersion


def _require_text(value: str, label: str) -> str:
    if not value or not value.strip():
        raise InvalidOfferError(f"{label} is required")
    return value


@dataclass(frozen=True)
class OfferVersion:
    """One version of a client's offer with a pinned method dependency.

    Required fields come from the SPEC.md section 3 aggregate table: audience,
    promise, eligibility, price hypothesis and method refs. An offer becomes
    production ready only when every method reference is satisfied by an
    approved method version for the same tenant, exact version and intended use
    (SPEC.md section 3 "Production requires approved dependencies").
    """

    offer_id: str
    tenant_id: str
    audience: str
    promise: str
    eligibility: str
    price_hypothesis: str
    method_refs: tuple[MethodReference, ...]
    owner: str
    state: OfferState = OfferState.DRAFT
    delivery_specification: DeliverySpecification | None = field(default=None)
    review_reason: str | None = field(default=None)

    def __post_init__(self) -> None:
        _require_text(self.offer_id, "offer id")
        _require_text(self.tenant_id, "offer tenant id")
        _require_text(self.audience, "offer audience")
        _require_text(self.promise, "offer promise")
        _require_text(self.eligibility, "offer eligibility")
        _require_text(self.price_hypothesis, "offer price hypothesis")
        _require_text(self.owner, "offer owner")
        if not self.method_refs:
            raise InvalidOfferError(
                "an offer requires at least one method reference"
            )
        if (
            self.delivery_specification is not None
            and self.delivery_specification.tenant_id != self.tenant_id
        ):
            raise OfferDependencyError(
                "an offer cannot pin another tenant's delivery specification"
            )

    @property
    def is_production_ready(self) -> bool:
        return self.state is OfferState.PRODUCTION_READY

    def require_production_ready(
        self, approved_methods: Iterable[MethodVersion]
    ) -> "OfferVersion":
        """Return a production ready offer once its dependencies are approved.

        Every method reference must be satisfied by an approved method version:
        same method id, same tenant, exact semantic version and intended use.
        The offer must also carry its complete stage 5 `DeliverySpecification`,
        because the stage 5 "Offer Locked" checkpoint requires the delivery
        package before an offer can authorize production (SPEC.md section 4).
        An absent or stale approval, or a missing delivery package, leaves the
        offer in its current state rather than being represented as approved
        (SPEC.md sections 3 and 4).
        """
        from redops.contexts.commercial.domain.policies import (
            OfferReadinessPolicy,
        )

        OfferReadinessPolicy().require(self, approved_methods)
        if self.delivery_specification is None:
            raise OfferReadinessError(
                f"offer {self.offer_id!r} cannot be production ready: it is "
                "missing the stage 5 delivery specification (Offer Locked)"
            )
        return replace(self, state=OfferState.PRODUCTION_READY, review_reason=None)

    def revised(
        self,
        *,
        audience: str | None = None,
        promise: str | None = None,
        eligibility: str | None = None,
        price_hypothesis: str | None = None,
        method_refs: tuple[MethodReference, ...] | None = None,
        owner: str | None = None,
        delivery_specification: DeliverySpecification | None = None,
    ) -> "OfferVersion":
        """Return a new draft offer with no inherited stage 5 asset or readiness.

        SPEC.md section 4: changing an approved upstream method marks dependent
        offers review required, and an approval is version specific rather than
        transferable. The stage 5 delivery specification is grounded on the
        locked stage 4 Signature Solution, so a revision (especially one that
        changes the method reference) cannot carry the old specification or the
        production ready state forward. The specification is dropped unless a
        fresh one is supplied, and the offer returns to draft for re-approval.
        """
        if self.state.is_terminal:
            raise InvalidOfferError("a terminal offer cannot be revised")
        return replace(
            self,
            audience=self.audience if audience is None else audience,
            promise=self.promise if promise is None else promise,
            eligibility=self.eligibility if eligibility is None else eligibility,
            price_hypothesis=(
                self.price_hypothesis if price_hypothesis is None else price_hypothesis
            ),
            method_refs=self.method_refs if method_refs is None else method_refs,
            owner=self.owner if owner is None else owner,
            delivery_specification=delivery_specification,
            state=OfferState.DRAFT,
            review_reason=None,
        )

    def mark_review_required(self, *, reason: str) -> "OfferVersion":
        """Return this offer marked review required after a change upstream.

        SPEC.md section 4: changing an approved upstream method marks dependent
        offers review required. A production ready offer loses that readiness
        until the dependency is reviewed again, and a terminal offer stays
        terminal.
        """
        _require_text(reason, "offer review reason")
        if self.state.is_terminal:
            raise InvalidOfferError("a terminal offer cannot be marked review required")
        return replace(self, state=OfferState.REVIEW_REQUIRED, review_reason=reason)


def _require_message_text(value: str, label: str) -> str:
    if not value or not value.strip():
        raise InvalidCampaignMessageError(f"{label} is required")
    return value


def _require_message_entries(entries: tuple[str, ...], label: str) -> None:
    if not entries:
        raise InvalidCampaignMessageError(
            f"a campaign message requires at least one {label} entry"
        )
    for entry in entries:
        if not entry or not entry.strip():
            raise InvalidCampaignMessageError(
                f"{label} entries must not be blank"
            )


@dataclass(frozen=True)
class CampaignMessage:
    """The stage 6 campaign message, approved at "Campaign Message Approved".

    SPEC.md section 4, stage 6 "Message": the required asset package is the
    promise, problem hierarchy, desired outcome, proof and objections, story,
    method explanation, CTA, lead magnet, hook, angles, landing message and
    Authority Amplifier outline. The checkpoint requires that "avatar, currency,
    problem, promise, method, product and CTA agree", and the message is grounded
    on the approved stage 5 offer, so production requires an approved dependency
    (SPEC.md section 3). It is frozen: approval pins an exact asset rather than
    mutating it, and an upstream change returns it to review required.
    """

    message_id: str
    tenant_id: str
    offer: OfferVersion
    owner: str
    avatar: str
    currency: str
    problem: str
    promise: str
    cta: str
    method_reference: MethodReference
    product_offer_id: str
    problem_hierarchy: tuple[str, ...]
    desired_outcome: str
    proof_objections: tuple[str, ...]
    story: str
    method_explanation: str
    lead_magnet: str
    hook: str
    angles: tuple[str, ...]
    landing_message: str
    authority_amplifier_outline: str
    state: CampaignMessageState = CampaignMessageState.DRAFT
    review_reason: str | None = field(default=None)

    def __post_init__(self) -> None:
        for label, value in (
            ("campaign message id", self.message_id),
            ("campaign message tenant id", self.tenant_id),
            ("campaign message owner", self.owner),
            ("campaign message avatar", self.avatar),
            ("campaign message currency", self.currency),
            ("campaign message problem", self.problem),
            ("campaign message promise", self.promise),
            ("campaign message CTA", self.cta),
            ("campaign message product offer id", self.product_offer_id),
            ("campaign message desired outcome", self.desired_outcome),
            ("campaign message story", self.story),
            ("campaign message method explanation", self.method_explanation),
            ("campaign message lead magnet", self.lead_magnet),
            ("campaign message hook", self.hook),
            ("campaign message landing message", self.landing_message),
            (
                "campaign message Authority Amplifier outline",
                self.authority_amplifier_outline,
            ),
        ):
            _require_message_text(value, label)
        _require_message_entries(self.problem_hierarchy, "problem hierarchy")
        _require_message_entries(self.proof_objections, "proof and objections")
        _require_message_entries(self.angles, "angles")
        if self.offer.tenant_id != self.tenant_id:
            raise CampaignMessageDependencyError(
                "a campaign message cannot be grounded on another tenant's offer"
            )

    @property
    def is_approved(self) -> bool:
        return self.state is CampaignMessageState.APPROVED

    def approve(
        self, approved_methods: Iterable[MethodVersion]
    ) -> "CampaignMessage":
        """Return an approved message once it agrees with its locked offer.

        SPEC.md section 4, stage 6: the "Campaign Message Approved" checkpoint
        requires the avatar, currency, problem, promise, method, product and CTA
        to agree and the message to be grounded on the approved stage 5 offer.
        A conflicting or under-grounded message stays in its current state rather
        than being represented as approved.
        """
        from redops.contexts.commercial.domain.policies import (
            CampaignMessageAlignmentPolicy,
        )

        CampaignMessageAlignmentPolicy().require(self, approved_methods)
        return replace(
            self, state=CampaignMessageState.APPROVED, review_reason=None
        )

    def mark_review_required(self, *, reason: str) -> "CampaignMessage":
        """Return this message marked review required after a change upstream.

        SPEC.md section 4: changing an approved upstream method or offer marks
        dependent assets review required. An approved message loses that approval
        until reviewed again, and a terminal message stays terminal.
        """
        _require_message_text(reason, "campaign message review reason")
        if self.state.is_terminal:
            raise InvalidCampaignMessageError(
                "a terminal campaign message cannot be marked review required"
            )
        return replace(
            self, state=CampaignMessageState.REVIEW_REQUIRED, review_reason=reason
        )

"""Aggregates for the Commercial Design bounded context (pure domain).

OfferVersion is the client's offer specification at a pinned method dependency
(SPEC.md section 3). Its invariant is that production readiness requires an
approved method dependency at the exact version and intended use it references.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable

from redops.contexts.commercial.domain.errors import InvalidOfferError
from redops.contexts.commercial.domain.value_objects import (
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

    @property
    def is_production_ready(self) -> bool:
        return self.state is OfferState.PRODUCTION_READY

    def require_production_ready(
        self, approved_methods: Iterable[MethodVersion]
    ) -> "OfferVersion":
        """Return a production ready offer once its dependencies are approved.

        Every method reference must be satisfied by an approved method version:
        same method id, same tenant, exact semantic version and intended use.
        An absent or stale approval leaves the offer in its current state rather
        than being represented as approved (SPEC.md sections 3 and 4).
        """
        from redops.contexts.commercial.domain.policies import (
            OfferReadinessPolicy,
        )

        OfferReadinessPolicy().require(self, approved_methods)
        return replace(self, state=OfferState.PRODUCTION_READY, review_reason=None)

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

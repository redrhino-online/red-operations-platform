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

from redops.contexts.commercial.domain.entities import OfferVersion
from redops.contexts.commercial.domain.errors import OfferReadinessError
from redops.contexts.commercial.domain.value_objects import (
    MethodReference,
    OfferImpactAssessment,
)
from redops.contexts.method.domain.entities import MethodVersion
from redops.contexts.method.domain.policies import MethodChangeImpactPolicy
from redops.contexts.method.domain.value_objects import (
    ArtifactKind,
    DependentArtifact,
)


class OfferReadinessPolicy:
    """Refuses production readiness when a method dependency is not approved."""

    def require(
        self, offer: OfferVersion, approved_methods: Iterable[MethodVersion]
    ) -> None:
        if offer.state.is_terminal:
            raise OfferReadinessError(
                f"terminal offer {offer.offer_id!r} cannot be production ready"
            )
        methods = tuple(approved_methods)
        for reference in offer.method_refs:
            if not self._is_satisfied(offer, reference, methods):
                raise OfferReadinessError(
                    f"offer {offer.offer_id!r} cannot be production ready: "
                    f"method {reference.method_id!r} version "
                    f"{reference.version} for {reference.intended_use!r} is not "
                    "an approved dependency for this tenant"
                )

    @staticmethod
    def _is_satisfied(
        offer: OfferVersion,
        reference: MethodReference,
        methods: tuple[MethodVersion, ...],
    ) -> bool:
        return any(
            method.method_id == reference.method_id
            and method.tenant_id == offer.tenant_id
            and method.authorizes(reference.version, reference.intended_use)
            for method in methods
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

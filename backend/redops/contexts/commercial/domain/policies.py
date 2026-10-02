"""Readiness policy for the Commercial Design bounded context (pure domain).

SPEC.md section 3: "Production requires approved dependencies". An offer may
only become production ready when each of its method references is satisfied by
an approved method version for the same tenant, at the exact version and
intended use. This is the offer-side half of the SPEC.md section 4 method
change impact rule.
"""

from __future__ import annotations

from typing import Iterable

from redops.contexts.commercial.domain.entities import OfferVersion
from redops.contexts.commercial.domain.errors import OfferReadinessError
from redops.contexts.commercial.domain.value_objects import MethodReference
from redops.contexts.method.domain.entities import MethodVersion


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

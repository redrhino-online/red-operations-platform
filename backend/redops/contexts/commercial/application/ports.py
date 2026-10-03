"""Application ports for the Commercial Design bounded context (SPEC.md section 6).

A port is defined by an application need: the stage 6 to 10 gate use cases must
resolve the exact production ready stage 5 ``OfferVersion`` a prior gate was
pinned to, instead of trusting a repeated request body that re-states the offer
and its approval. The adapter is chosen in the composition layer, so the use case
depends on the interface, not a concrete store.

The stage 7 to 10 gates additionally ground on the exact stage 6
``CampaignMessage`` a prior gate approved at "Campaign Message Approved", so the
same resolve-not-restate rule applies to that message.
"""

from __future__ import annotations

import abc

from redops.contexts.commercial.domain.entities import (
    CampaignMessage,
    OfferVersion,
)


class OfferVersionRepository(abc.ABC):
    """Seam for production ready offers, keyed by client and offer id.

    SPEC.md section 3: a passing gate pins the exact approved asset versions and
    intended use; SPEC.md section 4 keeps a previous approved version
    historically identifiable. The store is append-only per
    ``(tenant_id, offer_id)``: a production ready offer is immutable, and a later
    gate resolves it rather than re-declaring it. ``close`` releases any
    connection the adapter opened.
    """

    @abc.abstractmethod
    def get(self, tenant_id: str, offer_id: str) -> OfferVersion | None:
        """Return the exact production ready offer, or ``None`` if unknown."""

    @abc.abstractmethod
    def save(self, offer: OfferVersion) -> None:
        """Store a production ready offer, refusing a different same-id body."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""


class CampaignMessageRepository(abc.ABC):
    """Seam for approved stage 6 messages, keyed by client and message id.

    SPEC.md section 3: a passing gate pins the exact approved asset versions and
    intended use; SPEC.md section 4 keeps a previous approved version
    historically identifiable. The store is append-only per
    ``(tenant_id, message_id)``: an approved message is immutable, and a later
    gate resolves it rather than re-declaring it. ``close`` releases any
    connection the adapter opened.
    """

    @abc.abstractmethod
    def get(self, tenant_id: str, message_id: str) -> CampaignMessage | None:
        """Return the exact approved message, or ``None`` if unknown."""

    @abc.abstractmethod
    def save(self, message: CampaignMessage) -> None:
        """Store an approved message, refusing a different same-id body."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""

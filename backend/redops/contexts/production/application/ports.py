"""Application ports for the Production bounded context (SPEC.md section 6).

A port is defined by an application need: the stage 8 to 10 gate use cases must
resolve the exact stage 7 ``AuthorityAmplifier`` a prior gate approved at
"Authority Amplifier Approved", instead of trusting a repeated request body that
re-states the amplifier and its two approvals (SPEC.md sections 3 and 4). The
adapter is chosen in the composition layer, so the use case depends on the
interface, not a concrete store.
"""

from __future__ import annotations

import abc

from redops.contexts.production.domain.entities import AuthorityAmplifier


class AuthorityAmplifierRepository(abc.ABC):
    """Seam for approved stage 7 amplifiers, keyed by client and amplifier id.

    SPEC.md section 3: a passing gate pins the exact approved asset versions and
    intended use; SPEC.md section 4 keeps a previous approved version
    historically identifiable. The store is append-only per
    ``(tenant_id, amplifier_id)``: an approved amplifier is immutable, and a later
    gate resolves it rather than re-declaring it. ``close`` releases any
    connection the adapter opened.
    """

    @abc.abstractmethod
    def get(
        self, tenant_id: str, amplifier_id: str
    ) -> AuthorityAmplifier | None:
        """Return the exact approved amplifier, or ``None`` if unknown."""

    @abc.abstractmethod
    def save(self, amplifier: AuthorityAmplifier) -> None:
        """Store an approved amplifier, refusing a different same-id body."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""

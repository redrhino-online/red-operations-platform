"""The idempotency-keyed outbound connector effect (Execution domain).

SPEC.md section 6 calls connectors "outbound adapters with explicit scopes and
replay safe operations", and SPEC.md section 7 requires "request identity and
idempotency key where retries matter". SPEC.md section 11 makes that concrete:
"duplicate delivery creates one external operation".

These pure value objects give an outbound effect a stable identity before any
adapter runs. ``ConnectorEffect`` names the client, the idempotency key, the
connector, the target and an exact content digest, so a retry of the same
request is distinguishable from a reused key that carries different content.
``ExternalOperation`` is the append-only record of the one external operation
the effect produced, keyed by ``(tenant_id, idempotency_key)``. The domain holds
no transport, no store and no vendor code: it only states what an effect is and
whether a recorded operation answers it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from redops.contexts.execution.domain.errors import (
    ConnectorTenantBoundaryError,
    InvalidConnectorEffectError,
)


@dataclass(frozen=True)
class ConnectorEffect:
    """One idempotency-keyed outbound request (SPEC.md sections 6 and 7).

    ``idempotency_key`` is the request identity within the client's connector
    scope; ``payload_digest`` pins the exact content so a repeated key with the
    same digest is a retry and a repeated key with a different digest is a
    conflict. The value object is frozen: an effect is what was requested, not a
    mutable draft.
    """

    tenant_id: str
    idempotency_key: str
    connector: str
    target: str
    payload_digest: str
    requested_on: date

    def __post_init__(self) -> None:
        if not self.tenant_id or not self.tenant_id.strip():
            raise ConnectorTenantBoundaryError(
                "a connector effect requires a non-blank tenant id; an outbound "
                "operation is a client resource and cannot be delivered unscoped"
            )
        for label, value in (
            ("connector effect idempotency key", self.idempotency_key),
            ("connector effect connector", self.connector),
            ("connector effect target", self.target),
            ("connector effect payload digest", self.payload_digest),
        ):
            if not value or not value.strip():
                raise InvalidConnectorEffectError(f"{label} is required")


@dataclass(frozen=True)
class ExternalOperation:
    """The one recorded external operation an effect produced (SPEC.md section 11).

    ``external_ref`` is the connector's own identifier for the operation that
    actually ran. ``matches`` reports whether a recorded operation answers a
    candidate effect: the same tenant, key, connector, target and content
    digest. A recorded operation is append-only; a conflicting effect is refused
    by the store rather than overwriting it.
    """

    effect: ConnectorEffect
    external_ref: str
    delivered_on: date

    def __post_init__(self) -> None:
        if not self.external_ref or not self.external_ref.strip():
            raise InvalidConnectorEffectError(
                "an external operation requires the connector's non-blank "
                "external reference for the operation that ran"
            )

    def matches(self, candidate: ConnectorEffect) -> bool:
        """Whether this recorded operation answers ``candidate`` exactly."""
        return (
            self.effect.tenant_id == candidate.tenant_id
            and self.effect.idempotency_key == candidate.idempotency_key
            and self.effect.connector == candidate.connector
            and self.effect.target == candidate.target
            and self.effect.payload_digest == candidate.payload_digest
        )

"""Reference adapter for the shared prompt-injection guard.

``InMemoryInjectionGuard`` is the process-local reference implementation of the
``InjectionGuard`` port. It is bound to one active client: material it admits is
scoped to that client and marked untrusted, and it refuses to admit material for
or validate an action belonging to any other client (SPEC.md section 5). Tool
calls and gate changes are validated against the authority line by
``InjectionGuardPolicy``, so content that was merely ingested cannot direct a
tool call or change a gate. A durable adapter may implement the same port later,
for example to also append an immutable audit event; no such decision exists
today, so only the reference adapter is provided.
"""

from __future__ import annotations

from redops.shared.security.application.ports import InjectionGuard
from redops.shared.security.domain.errors import InjectionTenantBoundaryError
from redops.shared.security.domain.policies import InjectionGuardPolicy
from redops.shared.security.domain.value_objects import (
    IngestedMaterial,
    ProposedGateChange,
    ProposedToolCall,
)


def _require_tenant(value: str, operation: str) -> None:
    """Refuse an unscoped guard operation on a client's material."""

    if not value or not value.strip():
        raise InjectionTenantBoundaryError(
            f"a prompt-injection guard {operation} requires a non-blank client "
            "id; ingested material and proposed actions are client resources "
            "and cannot be handled unscoped"
        )


class InMemoryInjectionGuard(InjectionGuard):
    """Process-local guard scoped to a single active client."""

    def __init__(self, tenant_id: str) -> None:
        _require_tenant(tenant_id, "session")
        self._tenant_id = tenant_id

    @property
    def tenant_id(self) -> str:
        """The one client this guard is scoped to."""

        return self._tenant_id

    def ingest(self, source_ref: str, text: str) -> IngestedMaterial:
        return IngestedMaterial(
            tenant_id=self._tenant_id,
            source_ref=source_ref,
            text=text,
        )

    def authorize_tool_call(self, call: ProposedToolCall) -> None:
        self._require_active(call.tenant_id, "tool call")
        InjectionGuardPolicy.authorize_tool_call(call)

    def authorize_gate_change(self, change: ProposedGateChange) -> None:
        self._require_active(change.tenant_id, "gate change")
        InjectionGuardPolicy.authorize_gate_change(change)

    def _require_active(self, tenant_id: str, operation: str) -> None:
        _require_tenant(tenant_id, operation)
        if tenant_id != self._tenant_id:
            raise InjectionTenantBoundaryError(
                f"a {operation} for client '{tenant_id}' cannot be handled by "
                f"a guard scoped to client '{self._tenant_id}'; SPEC.md section "
                "5 limits a session to the active client"
            )

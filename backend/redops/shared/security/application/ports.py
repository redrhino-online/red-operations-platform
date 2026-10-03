"""Application port for the shared prompt-injection guard (SPEC.md sections 5 and 9).

SPEC.md section 5 requires the platform to treat ingested client material as
data, limit retrieval to the active client, and validate tool calls outside
model output. The port is defined by that need: admit content for one active
client as untrusted, citable material, then validate a proposed tool call or
gate change against the authority line before it can act.

The guard is bound to a single active client, matching SPEC.md section 5's
"limiting retrieval to the active client" and section 9's cross-client ban. A
durable adapter (for example one that also records an immutable audit event)
implements the same port without changing callers.
"""

from __future__ import annotations

import abc

from redops.shared.security.domain.value_objects import (
    IngestedMaterial,
    ProposedGateChange,
    ProposedToolCall,
)


class InjectionGuard(abc.ABC):
    """Seam for admitting untrusted material and validating proposed actions.

    ``ingest`` returns the content as untrusted ``IngestedMaterial`` scoped to
    the active client; ``authorize_tool_call`` and ``authorize_gate_change``
    raise a named error when the proposed action is grounded on data rather
    than on an operator decision or an approved gate. ``close`` releases any
    resource the adapter opened.
    """

    @abc.abstractmethod
    def ingest(self, source_ref: str, text: str) -> IngestedMaterial:
        """Admit one source's text as untrusted material for the active client."""

    @abc.abstractmethod
    def authorize_tool_call(self, call: ProposedToolCall) -> None:
        """Validate a proposed tool call, refusing a data-only basis."""

    @abc.abstractmethod
    def authorize_gate_change(self, change: ProposedGateChange) -> None:
        """Validate a proposed gate change, refusing a data-only basis."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""

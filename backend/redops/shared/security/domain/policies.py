"""Pure policy rules for the shared prompt-injection guard (SPEC.md section 5).

The policy is the authority line itself, with no I/O: an action may proceed only
when its basis is a human operator decision or an already-approved gate. Model
output and ingested client material are data (SPEC.md section 5), so an action
grounded on either is refused with a named error rather than silently allowed.
"""

from __future__ import annotations

from redops.shared.security.domain.errors import UntrustedAuthorityError
from redops.shared.security.domain.value_objects import (
    AuthorityBasis,
    ProposedGateChange,
    ProposedToolCall,
)


class InjectionGuardPolicy:
    """Refuse any action that would derive authority from data."""

    @staticmethod
    def require_authority(basis: AuthorityBasis, purpose: str) -> None:
        """Raise unless ``basis`` carries human authority (SPEC.md section 5)."""

        if not isinstance(basis, AuthorityBasis):
            raise UntrustedAuthorityError(
                f"{purpose} needs a typed authority basis; got {basis!r}"
            )
        if not basis.confers_authority:
            raise UntrustedAuthorityError(
                f"{purpose} cannot be grounded on {basis.value}; only an "
                "operator decision or an approved gate confers authority "
                "(SPEC.md section 5)"
            )

    @classmethod
    def authorize_tool_call(cls, call: ProposedToolCall) -> None:
        """Validate a proposed tool call outside model output."""

        cls.require_authority(call.basis, f"tool call '{call.tool_name}'")

    @classmethod
    def authorize_gate_change(cls, change: ProposedGateChange) -> None:
        """Refuse a gate change an agent tries to confer upon itself."""

        cls.require_authority(change.basis, f"stage {change.stage} gate change")

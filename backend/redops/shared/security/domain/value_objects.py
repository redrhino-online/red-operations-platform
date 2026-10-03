"""Value objects for the shared prompt-injection guard (SPEC.md sections 5 and 9).

The guard's job is to keep a hard line between authority and data. A human
operator decision or an already-approved gate confers authority (SPEC.md
section 4); ingested client material and model output do not (SPEC.md section
5). ``IngestedMaterial`` makes that concrete: it is frozen, scoped to one
client, pinned to a source reference, and *always* untrusted, so no downstream
code can mistake content it merely read for an instruction it must obey.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from redops.shared.security.domain.errors import UntrustedContentError


class ContentTrust(str, Enum):
    """Whether a piece of content may act as authority.

    Ingested client material and model output are ``UNTRUSTED``: they are data
    to reason about, never an instruction that grants authority (SPEC.md
    section 5). ``TRUSTED`` is reserved for content that a human authority
    produced or approved under SPEC.md section 4.
    """

    UNTRUSTED = "untrusted"
    TRUSTED = "trusted"


class AuthorityBasis(str, Enum):
    """Where an action's authority comes from (SPEC.md sections 4 and 5).

    Only ``OPERATOR_DECISION`` and ``APPROVED_GATE`` carry human authority.
    ``MODEL_OUTPUT`` and ``INGESTED_MATERIAL`` are data: SPEC.md section 5
    forbids an agent conferring authority upon itself, so an action grounded on
    them is refused rather than executed.
    """

    OPERATOR_DECISION = "operator_decision"
    APPROVED_GATE = "approved_gate"
    MODEL_OUTPUT = "model_output"
    INGESTED_MATERIAL = "ingested_material"

    @property
    def confers_authority(self) -> bool:
        """True only for a human decision or an already-approved gate."""

        return self in (
            AuthorityBasis.OPERATOR_DECISION,
            AuthorityBasis.APPROVED_GATE,
        )


@dataclass(frozen=True)
class IngestedMaterial:
    """One client's ingested content, held as untrusted, citable data.

    The trust class is fixed at construction: ``IngestedMaterial`` can never be
    built as trusted or authority-bearing, so text that says "approve the gate"
    or "call the delete tool" stays data (SPEC.md section 5). It is bound to the
    client it was read for and to a source reference so it remains traceable
    (SPEC.md sections 3 and 9).
    """

    tenant_id: str
    source_ref: str
    text: str

    def __post_init__(self) -> None:
        for label, value in (
            ("ingested material tenant id", self.tenant_id),
            ("ingested material source reference", self.source_ref),
            ("ingested material text", self.text),
        ):
            if not value or not value.strip():
                raise UntrustedContentError(f"{label} is required")

    @property
    def trust(self) -> ContentTrust:
        """Ingested client material is always untrusted data."""

        return ContentTrust.UNTRUSTED

    @property
    def confers_authority(self) -> bool:
        """Ingested material never grants authority, whatever it claims."""

        return False


@dataclass(frozen=True)
class ProposedToolCall:
    """A tool call proposed for one client, with the basis it claims.

    SPEC.md section 5 requires tool calls to be validated outside model output:
    the call must name where its authority comes from, and the guard refuses it
    when that basis is data (``MODEL_OUTPUT`` or ``INGESTED_MATERIAL``) rather
    than a human decision or an approved gate.
    """

    tenant_id: str
    tool_name: str
    basis: AuthorityBasis

    def __post_init__(self) -> None:
        for label, value in (
            ("proposed tool call tenant id", self.tenant_id),
            ("proposed tool call name", self.tool_name),
        ):
            if not value or not value.strip():
                raise UntrustedContentError(f"{label} is required")


@dataclass(frozen=True)
class ProposedGateChange:
    """A gate change proposed for one client, with the basis it claims.

    A gate records a human approval (SPEC.md section 4). An action that tries to
    change a gate on the strength of ingested material or model output is
    refused by the guard, so no agent can confer approval upon itself.
    """

    tenant_id: str
    stage: int
    basis: AuthorityBasis

    def __post_init__(self) -> None:
        if not self.tenant_id or not self.tenant_id.strip():
            raise UntrustedContentError(
                "proposed gate change tenant id is required"
            )
        if not isinstance(self.stage, int) or isinstance(self.stage, bool) or self.stage < 0:
            raise UntrustedContentError(
                "proposed gate change stage must be a non-negative integer"
            )

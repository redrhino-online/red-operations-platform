"""Aggregates for the Method bounded context (pure domain).

MethodVersion is the approved Signature Solution at an exact semantic version
(SPEC.md section 3). It is frozen: a change produces a new version, and the
previous approved version keeps its own approval so history stays identifiable.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date

from redops.contexts.method.domain.errors import (
    InvalidMethodError,
    MethodApprovalError,
)
from redops.contexts.method.domain.value_objects import (
    MethodApproval,
    SemanticVersion,
)


def _require_text(value: str, label: str) -> str:
    if not value or not value.strip():
        raise InvalidMethodError(f"{label} is required")
    return value


@dataclass(frozen=True)
class MethodVersion:
    """One version of a client's Signature Solution method.

    Required fields come from the SPEC.md section 3 aggregate table: parent
    method, stages, currency, claims and a semantic version. Approval pins the
    exact version and intended use; it never carries over to a revised version,
    and a revision must advance the semantic version so the prior approved
    method remains historically identifiable (SPEC.md section 4).
    """

    method_id: str
    tenant_id: str
    parent_method: str
    semantic_version: SemanticVersion
    stages: tuple[str, ...]
    currency: str
    claims: frozenset[str] = field(default_factory=frozenset)
    approval: MethodApproval | None = None

    def __post_init__(self) -> None:
        _require_text(self.method_id, "method id")
        _require_text(self.tenant_id, "method tenant id")
        _require_text(self.parent_method, "method parent")
        _require_text(self.currency, "method currency")
        if not self.stages:
            raise InvalidMethodError("a method requires at least one stage")
        for stage in self.stages:
            _require_text(stage, "method stage")
        if self.approval is not None and self.approval.version != self.semantic_version:
            raise MethodApprovalError(
                "method approval must pin this method's exact version"
            )

    @property
    def is_approved(self) -> bool:
        return self.approval is not None

    def approve(
        self,
        *,
        approved_by: str,
        intended_use: str,
        on: date,
    ) -> "MethodVersion":
        """Return a new method approval pinned to this exact version and use.

        SPEC.md section 3: approval pins an exact version and intended use. The
        approver identity is supplied by the caller; designation remains a
        governance decision.
        """
        _require_text(approved_by, "method approver")
        return replace(
            self,
            approval=MethodApproval(
                version=self.semantic_version,
                intended_use=intended_use,
                approved_by=approved_by,
                approved_on=on,
            ),
        )

    def authorizes(self, version: SemanticVersion, intended_use: str) -> bool:
        return self.approval is not None and self.approval.authorizes(
            version, intended_use
        )

    def revised(
        self,
        *,
        semantic_version: SemanticVersion,
        stages: tuple[str, ...] | None = None,
        currency: str | None = None,
        claims: frozenset[str] | None = None,
    ) -> "MethodVersion":
        """Return a new version of this method with no inherited approval.

        The new version must be strictly newer than the current one, and the
        approval is dropped so a revision cannot silently reuse an old approval
        (SPEC.md section 4).
        """
        semantic_version.change_from(self.semantic_version)
        return replace(
            self,
            semantic_version=semantic_version,
            stages=self.stages if stages is None else stages,
            currency=self.currency if currency is None else currency,
            claims=self.claims if claims is None else claims,
            approval=None,
        )

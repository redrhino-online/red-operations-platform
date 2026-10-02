"""Aggregates for the Method bounded context (pure domain).

MethodVersion is the approved Signature Solution at an exact semantic version
(SPEC.md section 3). It is frozen: a change produces a new version, and the
previous approved version keeps its own approval so history stays identifiable.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date

from redops.contexts.method.domain.errors import (
    InvalidDiagnosticModelError,
    InvalidMethodError,
    MethodApprovalError,
    MethodDependencyError,
)
from redops.contexts.method.domain.value_objects import (
    MethodApproval,
    PrimaryCurrency,
    ProfitPyramidLevel,
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

    The stage 2 primary currency and stage 3 diagnostic model are pinned as
    exact tenant assets because production requires approved dependencies
    (SPEC.md section 3). They are optional while a method is still a draft so
    work can be drafted in parallel, but approval cannot proceed without them
    (SPEC.md section 4).
    """

    method_id: str
    tenant_id: str
    parent_method: str
    semantic_version: SemanticVersion
    stages: tuple[str, ...]
    currency: str
    claims: frozenset[str] = field(default_factory=frozenset)
    approval: MethodApproval | None = None
    primary_currency: PrimaryCurrency | None = None
    diagnostic_model: "DiagnosticModel | None" = None

    def __post_init__(self) -> None:
        _require_text(self.method_id, "method id")
        _require_text(self.tenant_id, "method tenant id")
        _require_text(self.parent_method, "method parent")
        _require_text(self.currency, "method currency")
        if not self.stages:
            raise InvalidMethodError("a method requires at least one stage")
        for stage in self.stages:
            _require_text(stage, "method stage")
        if (
            self.primary_currency is not None
            and self.primary_currency.tenant_id != self.tenant_id
        ):
            raise MethodDependencyError(
                "a method cannot pin another tenant's primary currency"
            )
        if (
            self.diagnostic_model is not None
            and self.diagnostic_model.tenant_id != self.tenant_id
        ):
            raise MethodDependencyError(
                "a method cannot pin another tenant's diagnostic model"
            )
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
        governance decision. Production requires approved dependencies, so a
        method cannot be approved until its stage 2 primary currency and stage 3
        diagnostic model are pinned (SPEC.md section 3).
        """
        _require_text(approved_by, "method approver")
        if self.primary_currency is None:
            raise MethodDependencyError(
                "an approved method must pin its stage 2 primary currency"
            )
        if self.diagnostic_model is None:
            raise MethodDependencyError(
                "an approved method must pin its stage 3 diagnostic model"
            )
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
        primary_currency: PrimaryCurrency | None = None,
        diagnostic_model: "DiagnosticModel | None" = None,
    ) -> "MethodVersion":
        """Return a new version of this method with no inherited approval.

        The new version must be strictly newer than the current one, and the
        approval is dropped so a revision cannot silently reuse an old approval
        (SPEC.md section 4). The pinned stage 2 primary currency and stage 3
        diagnostic model are dropped too, so the new version must re-state and
        re-approve its upstream dependencies rather than inheriting an approval
        granted to a different exact version.
        """
        semantic_version.change_from(self.semantic_version)
        return replace(
            self,
            semantic_version=semantic_version,
            stages=self.stages if stages is None else stages,
            currency=self.currency if currency is None else currency,
            claims=self.claims if claims is None else claims,
            primary_currency=primary_currency,
            diagnostic_model=diagnostic_model,
            approval=None,
        )


@dataclass(frozen=True)
class DiagnosticModel:
    """A client's Profit Pyramid at the stage 3 "Diagnostic Model Approved" gate.

    SPEC.md section 4, stage 3 "Model": the model records the ordered Profit
    Pyramid levels, their progression and qualification logic. The checkpoint
    requires a prospect to recognize their current and desired next level using
    observable differences, so adjacent levels with an identical observable
    signature are rejected. The model is frozen: approval pins an exact version
    of the asset rather than mutating it (SPEC.md section 3).
    """

    model_id: str
    tenant_id: str
    name: str
    levels: tuple[ProfitPyramidLevel, ...]
    progression: str
    qualification_logic: str

    def __post_init__(self) -> None:
        _require_text(self.model_id, "diagnostic model id")
        _require_text(self.tenant_id, "diagnostic model tenant id")
        _require_text(self.name, "diagnostic model name")
        _require_text(self.progression, "diagnostic model progression")
        _require_text(
            self.qualification_logic, "diagnostic model qualification logic"
        )
        if len(self.levels) < 2:
            raise InvalidDiagnosticModelError(
                "a diagnostic model requires at least two pyramid levels"
            )
        for level in self.levels:
            if level.tenant_id != self.tenant_id:
                raise InvalidDiagnosticModelError(
                    "a diagnostic model cannot mix levels from another tenant"
                )
        for lower, higher in zip(self.levels, self.levels[1:]):
            if not lower.distinguishable_from(higher):
                raise InvalidDiagnosticModelError(
                    f"adjacent levels {lower.level_id!r} and {higher.level_id!r} "
                    "cannot be told apart by any observable difference"
                )

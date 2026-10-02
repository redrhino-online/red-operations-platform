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
    InvalidSignatureSolutionError,
    MethodApprovalError,
    MethodDependencyError,
)
from redops.contexts.method.domain.value_objects import (
    MethodApproval,
    PrimaryCurrency,
    ProfitPyramidLevel,
    SemanticVersion,
    SignatureStep,
    TransformationPhase,
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

    The stage 2 primary currency, stage 3 diagnostic model and stage 4 Signature
    Solution are pinned as exact tenant assets because production requires
    approved dependencies (SPEC.md section 3). They are optional while a method
    is still a draft so work can be drafted in parallel, but approval cannot
    proceed without them (SPEC.md section 4).
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
    signature_solution: "SignatureSolution | None" = None

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
        if (
            self.signature_solution is not None
            and self.signature_solution.tenant_id != self.tenant_id
        ):
            raise MethodDependencyError(
                "a method cannot pin another tenant's signature solution"
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
        method cannot be approved until its stage 2 primary currency, stage 3
        diagnostic model and stage 4 Signature Solution are pinned (SPEC.md
        section 3).
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
        if self.signature_solution is None:
            raise MethodDependencyError(
                "an approved method must pin its stage 4 signature solution"
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
        signature_solution: "SignatureSolution | None" = None,
    ) -> "MethodVersion":
        """Return a new version of this method with no inherited approval.

        The new version must be strictly newer than the current one, and the
        approval is dropped so a revision cannot silently reuse an old approval
        (SPEC.md section 4). The pinned stage 2 primary currency, stage 3
        diagnostic model and stage 4 Signature Solution are dropped too, so the
        new version must re-state and re-approve its upstream dependencies rather
        than inheriting an approval granted to a different exact version.
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
            signature_solution=signature_solution,
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


SIGNATURE_PHASE_COUNT = 3
SIGNATURE_STEP_COUNT = 9


@dataclass(frozen=True)
class SignatureSolution:
    """The stage 4 transformation structure, locked at "IP Architecture Locked".

    SPEC.md section 4, stage 4 "Package IP": the required asset package is the
    transformation map, process inventory, three phases, nine steps, named
    stages, starting and final states, stage inputs/actions/outputs, narrative
    and visual. The checkpoint requires that "the transformation is coherent and
    explainable without listing every tactic", which this aggregate enforces by
    fixing the canonical three phase, nine step shape (the Governance template's
    `three-phases` and `nine-steps` kinds) and requiring the named stages to form
    one continuous chain from the declared starting state to the declared final
    state. It is frozen: an approval pins an exact asset version rather than
    mutating it (SPEC.md section 3).
    """

    solution_id: str
    tenant_id: str
    transformation_map: str
    process_inventory: tuple[str, ...]
    phases: tuple[TransformationPhase, ...]
    starting_state: str
    final_state: str
    narrative: str
    visual: str

    def __post_init__(self) -> None:
        for label, value in (
            ("signature solution id", self.solution_id),
            ("signature solution tenant id", self.tenant_id),
            ("transformation map", self.transformation_map),
            ("signature solution starting state", self.starting_state),
            ("signature solution final state", self.final_state),
            ("transformation narrative", self.narrative),
            ("transformation visual", self.visual),
        ):
            if not value or not value.strip():
                raise InvalidSignatureSolutionError(f"{label} is required")
        if not self.process_inventory:
            raise InvalidSignatureSolutionError(
                "a Signature Solution requires a process inventory"
            )
        for entry in self.process_inventory:
            if not entry or not entry.strip():
                raise InvalidSignatureSolutionError(
                    "process inventory entries must not be blank"
                )
        if len(self.phases) != SIGNATURE_PHASE_COUNT:
            raise InvalidSignatureSolutionError(
                "a Signature Solution requires exactly "
                f"{SIGNATURE_PHASE_COUNT} phases, got {len(self.phases)}"
            )
        if self.step_count != SIGNATURE_STEP_COUNT:
            raise InvalidSignatureSolutionError(
                "a Signature Solution requires exactly "
                f"{SIGNATURE_STEP_COUNT} steps, got {self.step_count}"
            )
        for candidate in self.phases:
            if candidate.tenant_id != self.tenant_id:
                raise InvalidSignatureSolutionError(
                    "a Signature Solution cannot mix phases from another tenant"
                )
        named_stages = self.steps
        for previous, current in zip(named_stages, named_stages[1:]):
            if not current.continues_from(previous):
                raise InvalidSignatureSolutionError(
                    f"named stage {current.step_id!r} must begin where "
                    f"{previous.step_id!r} ended"
                )
        if named_stages[0].starting_state != self.starting_state:
            raise InvalidSignatureSolutionError(
                "the declared starting state must be the first named stage's "
                "starting state"
            )
        if named_stages[-1].final_state != self.final_state:
            raise InvalidSignatureSolutionError(
                "the declared final state must be the last named stage's final state"
            )

    @property
    def steps(self) -> tuple[SignatureStep, ...]:
        """The named stages in phase order, forming one transformation chain."""
        return tuple(step for phase in self.phases for step in phase.steps)

    @property
    def step_count(self) -> int:
        return sum(len(phase.steps) for phase in self.phases)

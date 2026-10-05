"""The client-authored enrollment process (pure domain), shaped by canon 35-49.

SPEC.md section 12.7 makes RED's process-design service a product capability: RED
helps each client design and implement their own sales process, in the client's
voice, using the enrollment block (canon files 35-49) as the template rather than
as copy. The result is a versioned, client-approved stage 8/9 asset that the
client or their team runs and that feeds stage 10 measurement. It is an asset
inside an existing stage, never a new pipeline stage, so implementing it is not a
named-owner decision (SPEC.md section 12.5).

The required shape is the one SPEC.md section 12.7 fixes; the canon supplies the
substance:

- Canon files 39-45 give the six part enrollment process in order: frame (39),
  discover problems (40, 41), prescription (42), application (43), invitation
  (44) and the objection crusher (45).
- Canon files 39-43 give the five pass-or-fail checkpoints, each a gate the call
  does not pass until it is met: intent (39), commitment (40), value (41),
  confidence (42) and desire (43). A checkpoint is pass or fail; the closer does
  not proceed on a lower result (canon files 39 and 40).
- Canon file 43 draws the client's acceptance and rejection line ("who we accept
  and who we reject") from hard and soft attributes.
- Canon file 45 answers the common objections by returning every concern to the
  three core questions of clarity, commitment and confidence.
- Canon file 47 names the three strategy-session models: the single call model,
  the fast track call model and the paid strategy session.
- Canon file 47 keeps the booking window inside three days ("we never let them
  book more than 72 hours out") and applies a strict no-show policy.

Canon text is treated as data (SPEC.md section 12.2): only structure, terminology
and intent are extracted, never copied. The process is a plan, not an observation
(SPEC.md section 3); it does not authorize spend, sending, publishing, payment or
any client commitment (SPEC.md sections 4 and 9), which stay human decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from redops.contexts.commercial.domain.value_objects import ProductProgram
from redops.contexts.execution.domain.errors import (
    ClientProcessDependencyError,
    ClientProcessObservationError,
    ClientProcessTenantBoundaryError,
    InvalidClientProcessError,
)
from redops.contexts.governance.domain.value_objects import StageAssetVersion
from redops.contexts.method.domain.entities import DiagnosticModel, SignatureSolution
from redops.contexts.method.domain.value_objects import PrimaryCurrency

CANON_REFERENCE = "35-49"

# The methodology owner placed the client-authored process as a required
# ``client-process`` kind of the stage 9 "Launch Approved" gate (owner decision
# 2026-10-04, E2; SPEC.md sections 4, 12.5 and 12.7), so a passing stage 9 gate
# pins the exact reviewed process.
CLIENT_PROCESS_KIND = "client-process"

# Canon file 47 bounds the booking window: "we never let them book more than 72
# hours out", which the pre-call material repeats as "within 72 hours. No more".
MINIMUM_BOOKING_WINDOW_DAYS = 1
MAXIMUM_BOOKING_WINDOW_DAYS = 3


class ClientProcessStepKind(Enum):
    """The six parts of the canon enrollment process in order (canon 39-45)."""

    FRAME = "frame"
    DISCOVER_PROBLEMS = "discover-problems"
    PRESCRIPTION = "prescription"
    APPLICATION = "application"
    INVITATION = "invitation"
    OBJECTION_CRUSHER = "objection-crusher"


CLIENT_PROCESS_STEP_ORDER: tuple[ClientProcessStepKind, ...] = (
    ClientProcessStepKind.FRAME,
    ClientProcessStepKind.DISCOVER_PROBLEMS,
    ClientProcessStepKind.PRESCRIPTION,
    ClientProcessStepKind.APPLICATION,
    ClientProcessStepKind.INVITATION,
    ClientProcessStepKind.OBJECTION_CRUSHER,
)


class ClientCheckpointKind(Enum):
    """The five pass-or-fail call checkpoints in order (canon 39-43)."""

    INTENT = "intent"
    COMMITMENT = "commitment"
    VALUE = "value"
    CONFIDENCE = "confidence"
    DESIRE = "desire"


CLIENT_CHECKPOINT_ORDER: tuple[ClientCheckpointKind, ...] = (
    ClientCheckpointKind.INTENT,
    ClientCheckpointKind.COMMITMENT,
    ClientCheckpointKind.VALUE,
    ClientCheckpointKind.CONFIDENCE,
    ClientCheckpointKind.DESIRE,
)


class StrategySessionModel(Enum):
    """The three strategy-session models the canon names (canon file 47)."""

    SINGLE_CALL = "single-call"
    FAST_TRACK = "fast-track"
    PAID_STRATEGY_SESSION = "paid-strategy-session"


def _require_blank_free(label: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidClientProcessError(f"{label} is required")


def _require_blank_free_unique(
    label: str, values: Iterable[str]
) -> None:
    items = tuple(values)
    if not items:
        raise InvalidClientProcessError(f"a client process requires at least one {label}")
    seen: set[str] = set()
    for value in items:
        if not isinstance(value, str) or not value.strip():
            raise InvalidClientProcessError(f"a client process {label} is required")
        if value in seen:
            raise InvalidClientProcessError(
                f"a client process repeats {label} {value!r}"
            )
        seen.add(value)


@dataclass(frozen=True)
class ClientProcessStep:
    """One part of the client's own enrollment process (canon 39-45).

    The canon delivers its process in a fixed order and tells the client to write
    their own version of each part in their own voice, so a step carries the
    client's purpose and prompt for that part. It is frozen and reject-only: a
    blank purpose, a blank prompt or an untyped part cannot be represented as part
    of the process.
    """

    step_kind: ClientProcessStepKind
    purpose: str
    prompt: str

    def __post_init__(self) -> None:
        if not isinstance(self.step_kind, ClientProcessStepKind):
            raise InvalidClientProcessError(
                "a client process step must name one of the canon process parts"
            )
        _require_blank_free("client process step purpose", self.purpose)
        _require_blank_free("client process step prompt", self.prompt)


@dataclass(frozen=True)
class ClientCheckpoint:
    """One pass-or-fail checkpoint the client's call must clear (canon 39-43).

    The canon makes every checkpoint a hard gate: the closer does not advance on
    anything less than a pass, and on a fail either ends the call or steps back to
    reset the current part (canon files 39 and 40). The checkpoint carries the
    client's own question and the action the client takes when it fails, so a
    blank question or a missing fail action cannot be represented as a checkpoint.
    """

    kind: ClientCheckpointKind
    question: str
    on_fail_action: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ClientCheckpointKind):
            raise InvalidClientProcessError(
                "a client process checkpoint must be one of the canon checkpoints"
            )
        _require_blank_free("client process checkpoint question", self.question)
        _require_blank_free(
            "client process checkpoint on-fail action", self.on_fail_action
        )


@dataclass(frozen=True)
class ClientObjectionAnswer:
    """The client's answer to one common enrollment objection (canon file 45).

    The canon reduces every objection to the three core questions of clarity,
    commitment and confidence and answers each in the client's own words, so an
    answer carries the concern and the response. It is frozen and reject-only: a
    blank concern or a blank answer cannot be represented as an objection answer.
    """

    concern: str
    answer: str

    def __post_init__(self) -> None:
        _require_blank_free("client process objection concern", self.concern)
        _require_blank_free("client process objection answer", self.answer)


@dataclass(frozen=True)
class ClientProcessHomework:
    """The client's pre-call homework qualifier (canon files 36, 41, 47).

    The canon gives booked prospects homework that starts helping them before the
    call, drawing on a piece of the client's own method, and keeps the booking
    window inside three days (canon file 47: "we never let them book more than 72
    hours out"). The homework is frozen and reject-only: it must name a method
    step, carry at least one duplicate-free question and keep the call inside the
    canon's booking window.
    """

    signature_step: str
    questions: tuple[str, ...]
    booking_window_days: int

    def __post_init__(self) -> None:
        _require_blank_free(
            "client process homework method step", self.signature_step
        )
        _require_blank_free_unique(
            "homework question", tuple(self.questions)
        )
        if isinstance(self.booking_window_days, bool) or not isinstance(
            self.booking_window_days, int
        ):
            raise InvalidClientProcessError(
                "a client process booking window must be a whole number of days"
            )
        if not (
            MINIMUM_BOOKING_WINDOW_DAYS
            <= self.booking_window_days
            <= MAXIMUM_BOOKING_WINDOW_DAYS
        ):
            raise InvalidClientProcessError(
                "a client process booking window must be within the canon's "
                "three-day limit (canon file 47: never more than 72 hours out)"
            )


@dataclass(frozen=True)
class ClientProcessCommitmentTerms:
    """The client's price floor and no-show rules (canon file 47).

    The canon prices the outcome rather than the stuff and states a price without
    justifying it, and it applies a strict no-show policy so the client's calendar
    stays a priority (canon file 47). The terms are frozen and reject-only: the
    price floor must be a positive integer and at least one duplicate-free no-show
    rule is required.
    """

    price_floor: int
    no_show_rules: tuple[str, ...]

    def __post_init__(self) -> None:
        if isinstance(self.price_floor, bool) or not isinstance(
            self.price_floor, int
        ):
            raise InvalidClientProcessError(
                "a client process price floor must be a whole number"
            )
        if self.price_floor <= 0:
            raise InvalidClientProcessError(
                "a client process price floor must be positive"
            )
        _require_blank_free_unique("no-show rule", tuple(self.no_show_rules))


@dataclass(frozen=True)
class ClientProcess:
    """A client-authored enrollment process (SPEC.md section 12.7).

    The process binds a named RED owner and the client's designated authority to a
    same-tenant stage 2 ``PrimaryCurrency``, stage 3 ``DiagnosticModel``, stage 4
    ``SignatureSolution`` and stage 5 ``ProductProgram`` (SPEC.md section 12.7),
    the client's chosen strategy-session model, pre-call homework, the six canon
    process parts in order, the five pass-or-fail checkpoints in order, the
    acceptance and rejection line, the objection answers and the commitment terms.

    It is frozen and reject-only, so the required shape cannot be bypassed: the
    process must be versioned, the approver must be distinct from the owner, each
    upstream asset must be typed and same-tenant, the homework must draw on a step
    the Signature Solution actually names, the parts and checkpoints must be
    exactly the canon's in order, the acceptance and rejection lines must both
    exist and not overlap, at least one objection must be answered, the strategy
    model and terms must be typed. It is a planning asset inside stage 8/9, and the
    methodology owner placed it as a required ``client-process`` kind of the stage 9
    "Launch Approved" gate (owner decision 2026-10-04, E2; SPEC.md sections 4, 12.5
    and 12.7), so a passing stage 9 gate pins the exact reviewed process. It does
    not authorize spend, sending, publishing, payment or any client commitment
    (SPEC.md sections 4 and 9) and it is never an observation (SPEC.md section 3).
    """

    process_id: str
    tenant_id: str
    owner: str
    approver: str
    version: int
    currency: PrimaryCurrency
    model: DiagnosticModel
    method: SignatureSolution
    program: ProductProgram
    strategy: StrategySessionModel
    homework: ClientProcessHomework
    steps: tuple[ClientProcessStep, ...]
    checkpoints: tuple[ClientCheckpoint, ...]
    acceptance_criteria: tuple[str, ...]
    rejection_criteria: tuple[str, ...]
    objections: tuple[ClientObjectionAnswer, ...]
    terms: ClientProcessCommitmentTerms

    def __post_init__(self) -> None:
        for label, value in (
            ("client process id", self.process_id),
            ("client process tenant id", self.tenant_id),
            ("client process owner", self.owner),
        ):
            _require_blank_free(label, value)
        _require_blank_free("client process approver", self.approver)
        if self.approver == self.owner:
            raise InvalidClientProcessError(
                f"client process {self.process_id!r} names {self.owner!r} as both "
                "the RED owner and the client approver; the written process must "
                "be approved by the client's designated authority, not its author"
            )
        if isinstance(self.version, bool) or not isinstance(self.version, int):
            raise InvalidClientProcessError(
                "a client process version must be a whole number"
            )
        if self.version < 1:
            raise InvalidClientProcessError(
                "a client process version must be a positive integer so a passing "
                "gate can pin the exact version"
            )
        if not isinstance(self.strategy, StrategySessionModel):
            raise InvalidClientProcessError(
                "a client process must choose one of the canon strategy-session "
                "models"
            )
        if not isinstance(self.homework, ClientProcessHomework):
            raise InvalidClientProcessError(
                "a client process requires typed pre-call homework"
            )
        if not isinstance(self.terms, ClientProcessCommitmentTerms):
            raise InvalidClientProcessError(
                "a client process requires typed commitment terms"
            )
        self._require_grounding()

        step_kinds = tuple(step.step_kind for step in self.steps)
        if step_kinds != CLIENT_PROCESS_STEP_ORDER:
            raise InvalidClientProcessError(
                "a client process must carry exactly the canon parts frame, "
                "discover problems, prescription, application, invitation and the "
                "objection crusher, once each, in order"
            )
        checkpoint_kinds = tuple(item.kind for item in self.checkpoints)
        if checkpoint_kinds != CLIENT_CHECKPOINT_ORDER:
            raise InvalidClientProcessError(
                "a client process must carry exactly the canon checkpoints intent, "
                "commitment, value, confidence and desire, once each, in order"
            )
        _require_blank_free_unique(
            "acceptance criterion", tuple(self.acceptance_criteria)
        )
        _require_blank_free_unique(
            "rejection criterion", tuple(self.rejection_criteria)
        )
        overlap = set(self.acceptance_criteria) & set(self.rejection_criteria)
        if overlap:
            names = ", ".join(sorted(overlap))
            raise InvalidClientProcessError(
                "a client process cannot accept and reject on the same criterion: "
                f"{names}"
            )
        if not self.objections:
            raise InvalidClientProcessError(
                "a client process requires at least one answered common objection"
            )
        seen_concerns: set[str] = set()
        for objection in self.objections:
            if not isinstance(objection, ClientObjectionAnswer):
                raise InvalidClientProcessError(
                    "a client process objection must be a typed objection answer"
                )
            if objection.concern in seen_concerns:
                raise InvalidClientProcessError(
                    f"a client process answers objection {objection.concern!r} "
                    "more than once"
                )
            seen_concerns.add(objection.concern)

    def _require_grounding(self) -> None:
        for label, value, identity in (
            ("stage 2 currency", self.currency, "currency"),
            ("stage 3 model", self.model, "model_id"),
            ("stage 4 Signature Solution", self.method, "solution_id"),
            ("stage 5 product program", self.program, "program_id"),
        ):
            if value is None:
                raise ClientProcessDependencyError(
                    f"a client process must be grounded on a typed {label}"
                )
            if not hasattr(value, "tenant_id"):
                raise ClientProcessDependencyError(
                    f"a client process must be grounded on a typed {label}"
                )
            if value.tenant_id != self.tenant_id:
                raise ClientProcessTenantBoundaryError(
                    f"client process {self.process_id!r} belongs to tenant "
                    f"{self.tenant_id!r}, but its {label} "
                    f"{getattr(value, identity, '?')!r} belongs to tenant "
                    f"{value.tenant_id!r}"
                )
        step_names = {step.name for step in self.method.steps}
        if self.homework.signature_step not in step_names:
            raise ClientProcessDependencyError(
                f"client process homework draws on method step "
                f"{self.homework.signature_step!r}, which the process's Signature "
                "Solution does not name"
            )

    @property
    def canon_reference(self) -> str:
        """The canon file block whose structure shaped this artifact."""
        return CANON_REFERENCE

    @property
    def step_kinds(self) -> tuple[ClientProcessStepKind, ...]:
        """The canon process parts the client process carries, in order."""
        return tuple(step.step_kind for step in self.steps)

    @property
    def checkpoint_kinds(self) -> tuple[ClientCheckpointKind, ...]:
        """The canon checkpoints the client process carries, in order."""
        return tuple(item.kind for item in self.checkpoints)

    def step_for(self, step_kind: ClientProcessStepKind) -> ClientProcessStep:
        """The client's wording for one canon process part."""
        for step in self.steps:
            if step.step_kind is step_kind:
                return step
        raise InvalidClientProcessError(
            f"client process {self.process_id!r} has no {step_kind.value!r} part"
        )

    def checkpoint_for(self, kind: ClientCheckpointKind) -> ClientCheckpoint:
        """The client's question and fail action for one canon checkpoint."""
        for item in self.checkpoints:
            if item.kind is kind:
                return item
        raise InvalidClientProcessError(
            f"client process {self.process_id!r} has no {kind.value!r} checkpoint"
        )

    @property
    def feeds_stages(self) -> tuple[int, ...]:
        """The downstream stages the process feeds (SPEC.md section 12.7)."""
        return (9, 10)

    @property
    def is_plan(self) -> bool:
        """A client process is a plan, not activity or an observed result."""
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a client process as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The
        process describes the enrollment conversation the client will run and the
        terms it will offer, while any enrolled prospect, collected payment or
        measured movement stays a separate observed or authorized record, so the
        process is never an observation.
        """
        raise ClientProcessObservationError(
            f"client process {claim_id!r} is a process to run, not an observed "
            "result, and cannot be recorded as an observation"
        )

    def as_stage_asset(self, *, version: int) -> StageAssetVersion:
        """Project the reviewed process onto exact ``client-process`` evidence.

        The methodology owner placed the client-authored enrollment process as a
        required ``client-process`` kind of the stage 9 "Launch Approved" gate
        (owner decision 2026-10-04, E2; SPEC.md sections 4, 12.5 and 12.7). The
        reviewed process is projected at a positive integer version, and a
        versionless projection is refused rather than silently pinned, so a passing
        stage 9 gate records the exact client process it approved (SPEC.md sections
        3 and 4).
        """
        if not isinstance(version, int) or version < 1:
            raise InvalidClientProcessError(
                "the client process version must be a positive integer so the "
                "stage 9 gate can pin the reviewed asset at an exact version"
            )
        return StageAssetVersion(
            asset_id=self.process_id,
            tenant_id=self.tenant_id,
            kind=CLIENT_PROCESS_KIND,
            version=version,
        )

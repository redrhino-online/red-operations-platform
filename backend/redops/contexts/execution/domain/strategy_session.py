"""The canon paid strategy-session kit (pure domain), shaped by canon 47, 48.

SPEC.md section 12.5 records the strategy-session kit as a canon gap: a paid
roadmap session that qualifies the lead, earns revenue and bridges to the program.
The implementation plan's canon gap backlog item G4 names this pure-domain
``StrategySessionKit`` as its bounded slice, a stage 8/9 asset and the third
enrollment model, not a new stage or required gate kind. The canon supplies the
substance:

- Canon file 47 makes the paid strategy session the bridge between paying nothing
  and a high-ticket program: a 60 to 90 minute session that builds a 90-day
  roadmap, usually $1,000, gated by a short application, with the fee credited to
  the first month of the program ("I'll take the thousand dollars you paid. Now
  it's your first month of coaching").
- Synthesized ``ops/playbooks/strategy-session.md``,
  ``ops/checklists/strategy-session-call.md`` and
  ``ops/sops/strategy-session-run.md`` fix the $500 floor, the before-and-after
  map over the signature solution, the three calm questions asked in order (plan
  works, alone, want help) and the fee credit.

Canon text is treated as data (SPEC.md section 12.2): only structure, terminology
and intent are extracted, never copied. The kit is a plan, not an observation
(SPEC.md section 3); it does not authorize sending, spend, payment or any client
commitment (SPEC.md sections 4 and 9), which stay human decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from redops.contexts.commercial.domain.value_objects import ProductProgram
from redops.contexts.execution.domain.client_process import StrategySessionModel
from redops.contexts.execution.domain.errors import (
    InvalidStrategySessionError,
    StrategySessionDependencyError,
    StrategySessionFormatError,
    StrategySessionObservationError,
    StrategySessionTenantBoundaryError,
)
from redops.contexts.method.domain.entities import SignatureSolution

STRATEGY_SESSION_CANON_REFERENCE = "47, 48; Certification Day 4; Live Sessions 8"

# Canon file 47 prices the paid strategy session "usually $1,000" and the
# synthesized playbook fixes the floor at $500.
STRATEGY_SESSION_DEFAULT_PRICE = 1000
STRATEGY_SESSION_PRICE_FLOOR = 500

# Canon file 47 runs the session for "60 to 90 minutes" and builds a 90-day
# roadmap.
STRATEGY_SESSION_MIN_MINUTES = 60
STRATEGY_SESSION_MAX_MINUTES = 90
STRATEGY_SESSION_PLAN_DAYS = 90

# The canon's three calm questions, asked in order (synthesized playbook).
STRATEGY_SESSION_QUESTION_COUNT = 3


class StrategySessionQuestionKind(Enum):
    """The three calm questions the paid session asks in order (canon 47)."""

    CONFIDENCE = "confidence"
    ALONE = "alone"
    HELP = "help"


STRATEGY_SESSION_QUESTION_ORDER: tuple[StrategySessionQuestionKind, ...] = (
    StrategySessionQuestionKind.CONFIDENCE,
    StrategySessionQuestionKind.ALONE,
    StrategySessionQuestionKind.HELP,
)


def _require_blank_free(label: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidStrategySessionError(f"{label} is required")


def _require_blank_free_unique(label: str, values: Iterable[str]) -> None:
    items = tuple(values)
    if not items:
        raise InvalidStrategySessionError(
            f"a strategy session requires at least one {label}"
        )
    seen: set[str] = set()
    for value in items:
        if not isinstance(value, str) or not value.strip():
            raise InvalidStrategySessionError(
                f"a strategy session {label} is required"
            )
        if value in seen:
            raise InvalidStrategySessionError(
                f"a strategy session repeats {label} {value!r}"
            )
        seen.add(value)


@dataclass(frozen=True)
class StrategySessionQuestion:
    """One of the three calm questions the paid session asks (canon 47).

    The canon closes the session with three calm questions rather than a pitch,
    asked in order. A question is frozen and reject-only, so a blank question or
    an untyped kind cannot be represented as part of the close.
    """

    kind: StrategySessionQuestionKind
    question: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, StrategySessionQuestionKind):
            raise InvalidStrategySessionError(
                "a strategy session question must name one of the canon questions"
            )
        _require_blank_free("strategy session question", self.question)


@dataclass(frozen=True)
class StrategySessionApplication:
    """The short application that gates the paid session (canon 47).

    The canon gates the session with a short application so the specialist talks
    only to qualified leads. The application is frozen and reject-only: it must
    carry an identity and at least one duplicate-free question.
    """

    application_id: str
    questions: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_blank_free(
            "strategy session application id", self.application_id
        )
        _require_blank_free_unique(
            "application question", tuple(self.questions)
        )


@dataclass(frozen=True)
class StrategySessionRoadmapStep:
    """One step of the before-and-after map over the signature solution (canon 47).

    The canon walks the lead through each step of the roadmap and marks what they
    have and what is missing; that gap is the reason to join. A step is frozen and
    reject-only, so a blank step name, a blank "has" note or a blank "missing" note
    cannot be represented as part of the map.
    """

    step_name: str
    has: str
    missing: str

    def __post_init__(self) -> None:
        _require_blank_free("strategy session roadmap step name", self.step_name)
        _require_blank_free("strategy session roadmap has note", self.has)
        _require_blank_free("strategy session roadmap missing note", self.missing)


@dataclass(frozen=True)
class StrategySessionRoadmap:
    """The before-and-after map over the client's signature solution (canon 47).

    The canon builds the 90-day plan by walking the lead through each step of the
    signature solution and marking what they have and what is missing. The map is
    frozen and reject-only: it must carry at least one typed step and must not
    repeat a step. The kit then checks that the map covers every step of the
    same-tenant signature solution exactly once.
    """

    tenant_id: str
    steps: tuple[StrategySessionRoadmapStep, ...]

    def __post_init__(self) -> None:
        _require_blank_free("strategy session roadmap tenant id", self.tenant_id)
        steps = tuple(self.steps)
        if not steps:
            raise InvalidStrategySessionError(
                "a strategy session roadmap requires at least one step"
            )
        seen: set[str] = set()
        for step in steps:
            if not isinstance(step, StrategySessionRoadmapStep):
                raise InvalidStrategySessionError(
                    "a strategy session roadmap step must be a typed roadmap step"
                )
            if step.step_name in seen:
                raise StrategySessionFormatError(
                    f"strategy session roadmap repeats step {step.step_name!r}; "
                    "the before-and-after map walks each signature solution step "
                    "exactly once (canon file 47)"
                )
            seen.add(step.step_name)

    @property
    def step_names(self) -> tuple[str, ...]:
        """The signature solution steps the map walks, in order."""
        return tuple(step.step_name for step in self.steps)


@dataclass(frozen=True)
class StrategySessionFeeCredit:
    """The rule that credits the session fee to the program (canon 47).

    The canon credits the fee to the first month of the program ("I'll take the
    thousand dollars you paid. Now it's your first month of coaching"), so the
    credit is frozen and reject-only: it must name the first month and carry a
    note.
    """

    credited_to_month: int
    note: str

    def __post_init__(self) -> None:
        if isinstance(self.credited_to_month, bool) or not isinstance(
            self.credited_to_month, int
        ):
            raise InvalidStrategySessionError(
                "a strategy session fee credit must name a whole month"
            )
        if self.credited_to_month != 1:
            raise StrategySessionFormatError(
                "a strategy session fee credit must apply to the first month of "
                "the program (canon file 47)"
            )
        _require_blank_free("strategy session fee credit note", self.note)


@dataclass(frozen=True)
class StrategySessionKit:
    """The canon paid strategy-session kit (SPEC.md section 12.5, backlog G4).

    The kit binds a named owner to a same-tenant stage 4 ``SignatureSolution`` and
    stage 5 ``ProductProgram``, the session price and duration, the short
    application gate, the before-and-after roadmap, the three calm questions in
    order and the fee credit. It is the typed form of the third enrollment model
    (``StrategySessionModel.PAID_STRATEGY_SESSION``).

    It is frozen and reject-only, so the canon's shape cannot be bypassed: the
    price must be at least the $500 floor, the session must run 60 to 90 minutes,
    the application must be typed and duplicate-free, the roadmap must cover every
    step of the same-tenant signature solution exactly once, the questions must be
    exactly the canon's three in order, and the fee must be credited to the first
    month of the program. It is a stage 8/9 planning asset, not a required gate
    kind, and it does not authorize sending, spend, payment or any client
    commitment (SPEC.md sections 4 and 9). It is never an observation (SPEC.md
    section 3).
    """

    kit_id: str
    tenant_id: str
    owner: str
    solution: SignatureSolution
    program: ProductProgram
    session_price: int
    session_minutes: int
    application: StrategySessionApplication
    roadmap: StrategySessionRoadmap
    questions: tuple[StrategySessionQuestion, ...]
    fee_credit: StrategySessionFeeCredit

    def __post_init__(self) -> None:
        for label, value in (
            ("strategy session kit id", self.kit_id),
            ("strategy session kit tenant id", self.tenant_id),
            ("strategy session kit owner", self.owner),
        ):
            _require_blank_free(label, value)
        self._require_grounding()
        if isinstance(self.session_price, bool) or not isinstance(
            self.session_price, int
        ):
            raise InvalidStrategySessionError(
                "a strategy session price must be a whole number"
            )
        if self.session_price < STRATEGY_SESSION_PRICE_FLOOR:
            raise StrategySessionFormatError(
                f"strategy session kit {self.kit_id!r} prices the session at "
                f"{self.session_price}; the canon's floor is "
                f"{STRATEGY_SESSION_PRICE_FLOOR} (canon file 47)"
            )
        if isinstance(self.session_minutes, bool) or not isinstance(
            self.session_minutes, int
        ):
            raise InvalidStrategySessionError(
                "a strategy session duration must be a whole number of minutes"
            )
        if not (
            STRATEGY_SESSION_MIN_MINUTES
            <= self.session_minutes
            <= STRATEGY_SESSION_MAX_MINUTES
        ):
            raise StrategySessionFormatError(
                f"strategy session kit {self.kit_id!r} runs "
                f"{self.session_minutes} minutes; the canon runs the session for "
                "60 to 90 minutes (canon file 47)"
            )
        if not isinstance(self.application, StrategySessionApplication):
            raise InvalidStrategySessionError(
                "a strategy session kit requires a typed application gate"
            )
        if not isinstance(self.roadmap, StrategySessionRoadmap):
            raise InvalidStrategySessionError(
                "a strategy session kit requires a typed before-and-after roadmap"
            )
        if self.roadmap.tenant_id != self.tenant_id:
            raise StrategySessionTenantBoundaryError(
                f"strategy session kit {self.kit_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its roadmap belongs to tenant "
                f"{self.roadmap.tenant_id!r}"
            )
        self._require_roadmap_coverage()
        for item in self.questions:
            if not isinstance(item, StrategySessionQuestion):
                raise InvalidStrategySessionError(
                    "a strategy session question must be a typed question"
                )
        question_kinds = tuple(item.kind for item in self.questions)
        if question_kinds != STRATEGY_SESSION_QUESTION_ORDER:
            raise StrategySessionFormatError(
                "a strategy session kit must ask exactly the canon's three "
                "questions (confidence, alone, help), once each, in order "
                "(canon file 47)"
            )
        if not isinstance(self.fee_credit, StrategySessionFeeCredit):
            raise InvalidStrategySessionError(
                "a strategy session kit requires a typed fee credit"
            )

    def _require_grounding(self) -> None:
        for label, value, expected, identity in (
            (
                "stage 4 Signature Solution",
                self.solution,
                SignatureSolution,
                "solution_id",
            ),
            (
                "stage 5 product program",
                self.program,
                ProductProgram,
                "program_id",
            ),
        ):
            if not isinstance(value, expected):
                raise StrategySessionDependencyError(
                    f"a strategy session kit must be grounded on a typed {label}"
                )
            if value.tenant_id != self.tenant_id:
                raise StrategySessionTenantBoundaryError(
                    f"strategy session kit {self.kit_id!r} belongs to tenant "
                    f"{self.tenant_id!r}, but its {label} "
                    f"{getattr(value, identity, '?')!r} belongs to tenant "
                    f"{value.tenant_id!r}"
                )

    def _require_roadmap_coverage(self) -> None:
        solution_steps = {step.name for step in self.solution.steps}
        for step in self.roadmap.steps:
            if step.step_name not in solution_steps:
                raise StrategySessionDependencyError(
                    f"strategy session kit {self.kit_id!r} carries a roadmap step "
                    f"{step.step_name!r}, which the Signature Solution "
                    f"{self.solution.solution_id!r} does not name; the "
                    "before-and-after map walks the signature solution, never a "
                    "new step (canon file 47)"
                )
        if set(self.roadmap.step_names) != solution_steps:
            raise StrategySessionFormatError(
                f"strategy session kit {self.kit_id!r} does not cover every step "
                "of its Signature Solution exactly once; the before-and-after map "
                "walks each step (canon file 47)"
            )

    @property
    def canon_reference(self) -> str:
        """The canon file block whose structure shaped this artifact."""
        return STRATEGY_SESSION_CANON_REFERENCE

    @property
    def model(self) -> StrategySessionModel:
        """The enrollment model this kit is the typed form of (canon file 47)."""
        return StrategySessionModel.PAID_STRATEGY_SESSION

    @property
    def plan_days(self) -> int:
        """The length of the roadmap the session builds (canon file 47)."""
        return STRATEGY_SESSION_PLAN_DAYS

    @property
    def question_kinds(self) -> tuple[StrategySessionQuestionKind, ...]:
        """The canon questions the kit asks, in order."""
        return tuple(item.kind for item in self.questions)

    @property
    def feeds_stages(self) -> tuple[int, ...]:
        """The downstream stages the kit feeds (SPEC.md section 12.5)."""
        return (9, 10)

    @property
    def is_plan(self) -> bool:
        """A strategy-session kit is a plan, not activity or an observed result."""
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a strategy-session kit as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The kit
        describes the session that will run and the terms it will offer, while any
        booked session, collected fee or measured conversion stays a separate
        observed or authorized record, so a kit is never an observation.
        """
        raise StrategySessionObservationError(
            f"strategy session kit {claim_id!r} is a session to run, not an "
            "observed result, and cannot be recorded as an observation"
        )

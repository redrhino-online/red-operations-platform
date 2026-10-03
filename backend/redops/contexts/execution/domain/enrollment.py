"""The canon enrollment and sales call over the stage 8 funnel (pure domain).

SPEC.md section 12.5 records the canon's enrollment and sales call -- the 10x
Enrollment Call script, the medical-style frame/examine/prescribe/prognosis, the
pre-call homework qualifier, acceptance and rejection ("red velvet rope")
criteria and live payment and checkout -- as a canon gap between stages 8 and 10,
used to "convert an engaged prospect into a client with a defined,
authority-preserving process". Section 12.3 maps canon files 00, 13, 14, 21 and
24 onto the surrounding stages.

The shape is canon-informed:

- Canon file 00 calls the "10x enrollment call" a medical-office process --
  "there's analysis, there's kind of an examination, a prescription, and a
  prognosis" -- and says you should be "opting out people every step of the way"
  because "once I frame a conversation with someone, I don't go to discovery if
  there's a red flag".
- Canon file 21 requires a pre-call homework qualifier that gives away "a piece
  of my signature solution", schedules the call "within 72 hours. No more than
  that", and closes live -- "always have the purse on the phone" and "accept
  their money live" over card or PayPal.
- Canon file 06 draws the "red velvet rope" between who is accepted and who is
  rejected, with hard metrics.

SPEC.md section 12.6 records that the dedicated sales/enrollment training and the
enumerated "six step process" are absent from the supplied canon, so this models
only the explicitly named four stages (frame, examine, prescribe, prognosis) and
records the gap rather than inventing the missing steps.

The plan is an explicit stage 8/9 asset over the same-tenant stage 8
``FunnelIntegration`` (SPEC.md section 12.5). It is not a new required gate kind
(a methodology-owner decision), it does not authorize spend, payment, external
commitment or traffic (SPEC.md sections 4 and 9) and it is never an observation
(SPEC.md section 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from redops.contexts.execution.domain.entities import FunnelIntegration
from redops.contexts.execution.domain.errors import (
    EnrollmentDependencyError,
    EnrollmentObservationError,
    EnrollmentTenantBoundaryError,
    InvalidEnrollmentError,
)


class EnrollmentStepKind(Enum):
    """The canon's four explicitly named enrollment call stages (canon file 00).

    Canon file 00 describes the "10x enrollment call" as a medical office: "there's
    analysis, there's kind of an examination, a prescription, and a prognosis", and
    later names the frame that opens the conversation. SPEC.md section 12.6 warns
    the enumerated "six step process" promised by the canon is absent from the
    supplied files, so RED models exactly the four stages the canon states rather
    than inventing the missing two.
    """

    FRAME = "frame"
    EXAMINE = "examine"
    PRESCRIBE = "prescribe"
    PROGNOSIS = "prognosis"


ENROLLMENT_STEP_ORDER: tuple[EnrollmentStepKind, ...] = (
    EnrollmentStepKind.FRAME,
    EnrollmentStepKind.EXAMINE,
    EnrollmentStepKind.PRESCRIBE,
    EnrollmentStepKind.PROGNOSIS,
)


@dataclass(frozen=True)
class EnrollmentStep:
    """One stage of the enrollment call (canon file 00).

    The canon has the closer "opt out" people "every step of the way", so each
    stage carries the red-flag check it applies before the conversation advances.
    A step is frozen and reject-only, so a blank purpose, a missing opt-out check
    or an untyped stage cannot be represented as part of the call.
    """

    step_kind: EnrollmentStepKind
    purpose: str
    opt_out_check: str

    def __post_init__(self) -> None:
        for label, value in (
            ("enrollment step purpose", self.purpose),
            ("enrollment step opt-out check", self.opt_out_check),
        ):
            if not value or not value.strip():
                raise InvalidEnrollmentError(f"{label} is required")
        if not isinstance(self.step_kind, EnrollmentStepKind):
            raise InvalidEnrollmentError(
                "an enrollment step must name one of the canon call stages"
            )


@dataclass(frozen=True)
class EnrollmentHomework:
    """The pre-call homework qualifier (canon file 21).

    The canon sends a booked prospect to a homework page that gives away "a piece
    of my signature solution" and asks qualifier questions (current sales, what is
    holding them back, their currency), and it lets them schedule "within 72 hours.
    No more than that". The homework is frozen and reject-only: it must name the
    signature solution step it draws on, carry at least one duplicate-free
    question, and keep the call inside the canon's three-day window.
    """

    signature_step: str
    questions: tuple[str, ...]
    max_days_to_call: int

    def __post_init__(self) -> None:
        if not self.signature_step or not self.signature_step.strip():
            raise InvalidEnrollmentError(
                "enrollment homework must name the signature solution step it "
                "draws on"
            )
        if not self.questions:
            raise InvalidEnrollmentError(
                "enrollment homework requires at least one qualifier question"
            )
        seen: set[str] = set()
        for question in self.questions:
            if not question or not question.strip():
                raise InvalidEnrollmentError(
                    "an enrollment homework question is required"
                )
            if question in seen:
                raise InvalidEnrollmentError(
                    f"enrollment homework repeats question {question!r}"
                )
            seen.add(question)
        if not 1 <= self.max_days_to_call <= 3:
            raise InvalidEnrollmentError(
                "enrollment homework must schedule the call within the canon's "
                "three-day window (canon file 21: within 72 hours, no more)"
            )


@dataclass(frozen=True)
class EnrollmentQualification:
    """The canon's "red velvet rope" accept and reject criteria (canon file 06).

    The canon asks "who do you accept and reject? Where is this line? This red
    velvet rope?", with hard metrics such as a sales floor or years in business.
    The rope is frozen and reject-only: it needs at least one accept criterion and
    at least one reject criterion, each non-blank and duplicate-free, so a plan
    cannot claim to qualify prospects while defining only one side of the line.
    """

    accept_criteria: tuple[str, ...]
    reject_criteria: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.accept_criteria:
            raise InvalidEnrollmentError(
                "an enrollment qualification requires at least one accept "
                "criterion"
            )
        if not self.reject_criteria:
            raise InvalidEnrollmentError(
                "an enrollment qualification requires at least one reject "
                "criterion"
            )
        seen: set[str] = set()
        for criterion in (*self.accept_criteria, *self.reject_criteria):
            if not criterion or not criterion.strip():
                raise InvalidEnrollmentError(
                    "an enrollment qualification criterion is required"
                )
            if criterion in seen:
                raise InvalidEnrollmentError(
                    f"enrollment qualification repeats criterion {criterion!r}"
                )
            seen.add(criterion)


class EnrollmentPaymentMethod(Enum):
    """The live payment methods the canon names (canon file 21)."""

    CARD = "card"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"


@dataclass(frozen=True)
class EnrollmentPayment:
    """The live payment and checkout handoff (canon file 21).

    The canon says "always have the purse on the phone" and "accept their money
    live", taking a deposit over card or PayPal. The terms are frozen and
    reject-only: the method must be typed, the deposit must be positive, and the
    payment must be captured live -- so the plan cannot represent an enrollment
    that defers payment or collects nothing as the canon's live close. The value
    describes the terms the named human closer will offer; it does not itself
    charge or authorize a commitment (SPEC.md sections 4 and 9).
    """

    method: EnrollmentPaymentMethod
    deposit_amount: int
    collected_live: bool

    def __post_init__(self) -> None:
        if not isinstance(self.method, EnrollmentPaymentMethod):
            raise InvalidEnrollmentError(
                "an enrollment payment must name one of the canon payment methods"
            )
        if self.deposit_amount <= 0:
            raise InvalidEnrollmentError(
                "an enrollment payment requires a positive deposit"
            )
        if not self.collected_live:
            raise InvalidEnrollmentError(
                "the canon collects payment live (canon file 21: always have the "
                "purse on the phone); an enrollment payment must be captured live"
            )


@dataclass(frozen=True)
class EnrollmentPlan:
    """The canon enrollment and sales call over the stage 8 funnel (SPEC.md 12.5).

    The plan binds a named owner and the accountable human closer to a same-tenant
    stage 8 ``FunnelIntegration``, the pre-call homework, exactly the canon's four
    call stages in order, the red velvet rope and the live payment terms. It is a
    planning decision, not a new required gate kind (a methodology-owner decision,
    SPEC.md section 12.5), it does not authorize spend, payment, external
    commitment or traffic (SPEC.md sections 4 and 9) and it is never an observation
    (SPEC.md section 3).
    """

    plan_id: str
    tenant_id: str
    owner: str
    closer: str
    funnel: FunnelIntegration
    homework: EnrollmentHomework
    steps: tuple[EnrollmentStep, ...]
    qualification: EnrollmentQualification
    payment: EnrollmentPayment

    def __post_init__(self) -> None:
        for label, value in (
            ("enrollment plan id", self.plan_id),
            ("enrollment plan tenant id", self.tenant_id),
            ("enrollment plan owner", self.owner),
            ("enrollment plan closer", self.closer),
        ):
            if not value or not value.strip():
                raise InvalidEnrollmentError(f"{label} is required")
        if not isinstance(self.funnel, FunnelIntegration):
            raise EnrollmentDependencyError(
                "an enrollment plan must be grounded on a typed stage 8 funnel, "
                "not a free-text reference"
            )
        if self.funnel.tenant_id != self.tenant_id:
            raise EnrollmentTenantBoundaryError(
                f"enrollment plan {self.plan_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its funnel "
                f"{self.funnel.integration_id!r} belongs to tenant "
                f"{self.funnel.tenant_id!r}"
            )
        if not isinstance(self.homework, EnrollmentHomework):
            raise InvalidEnrollmentError(
                "an enrollment plan requires a typed pre-call homework"
            )
        if not isinstance(self.qualification, EnrollmentQualification):
            raise InvalidEnrollmentError(
                "an enrollment plan requires typed red velvet rope criteria"
            )
        if not isinstance(self.payment, EnrollmentPayment):
            raise InvalidEnrollmentError(
                "an enrollment plan requires typed live payment terms"
            )
        if not self.steps:
            raise InvalidEnrollmentError(
                "an enrollment plan requires the canon call stages"
            )
        for item in self.steps:
            if not isinstance(item, EnrollmentStep):
                raise InvalidEnrollmentError(
                    "an enrollment plan step must be a typed enrollment step"
                )
        if self.step_kinds != ENROLLMENT_STEP_ORDER:
            raise InvalidEnrollmentError(
                "an enrollment plan must carry exactly the canon call stages "
                "frame, examine, prescribe and prognosis, once each, in order"
            )

    @property
    def step_kinds(self) -> tuple[EnrollmentStepKind, ...]:
        """The canon call stages the plan carries, in plan order."""
        return tuple(item.step_kind for item in self.steps)

    def step_for(self, step_kind: EnrollmentStepKind) -> EnrollmentStep:
        """The plan's stage for one canon call step."""
        for item in self.steps:
            if item.step_kind is step_kind:
                return item
        raise InvalidEnrollmentError(
            f"enrollment plan {self.plan_id!r} has no {step_kind.value!r} stage"
        )

    @property
    def is_plan(self) -> bool:
        """An enrollment plan is a plan, not an observed result."""
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent an enrollment plan as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The plan
        describes the call that will run and the payment terms that will be
        offered, while any enrolled prospect or collected payment stays a separate
        observed or authorized record, so a plan is never an observation.
        """
        raise EnrollmentObservationError(
            f"enrollment plan {claim_id!r} is a call to run, not an observed "
            "result, and cannot be recorded as an observation"
        )

"""The canon delivery ladder and ascension plan (pure domain), shaped by canon 11, 12.

SPEC.md section 12.5 records the delivery ladder and ascension as a canon gap:
one-to-one beta, live cohort, evergreen; a 90-day roadmap audit; one deliverable
per step. The implementation plan's canon gap backlog item G5 names this
pure-domain ``DeliveryLadder`` as its bounded slice, a post-launch Portfolio
asset that represents the client's own delivery (Serve) and the next-offer path,
not a new stage or required gate kind. The canon supplies the substance:

- Canon files 11 and 12, the Certification series and Live Sessions 5 and 12 fix
  the delivery ladder: start one to one, move to a live cohort, then record it as
  an evergreen program.
- Synthesized ``ops/playbooks/delivery.md`` fixes the roadmap audit (once every
  90 days, check the client against their own roadmap and find the missing step),
  one deliverable per step (every module gives the client a working tool), the
  success goals set at kickoff, the gate (results are measured against the goals;
  if they do not match, fix the plan before closing) and the ascension (turn each
  finished step into a small offer).

The ladder is grounded on the same-tenant stage 5 ``ProductProgram`` it delivers,
so the client's own delivery is traceable to the productized offer. It is a plan,
not an observation (SPEC.md section 3); it does not authorize sending, spend,
publishing or any client commitment (SPEC.md sections 4 and 9), which stay human
decisions. Canon text is treated as data (SPEC.md section 12.2): only structure,
terminology and intent are extracted, never copied.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Iterable, Mapping

from redops.contexts.commercial.domain.value_objects import ProductProgram
from redops.contexts.portfolio.domain.errors import (
    DeliveryAuditCadenceError,
    DeliveryAuditOrderError,
    DeliveryGateError,
    DeliveryLadderDependencyError,
    DeliveryLadderFormatError,
    DeliveryLadderObservationError,
    DeliveryLadderTenantBoundaryError,
    InvalidDeliveryLadderError,
)
from redops.contexts.portfolio.domain.value_objects import QUARTERLY_REVIEW_DAYS

DELIVERY_CANON_REFERENCE = "11, 12; Certification; Live Sessions 5, 12"

# The canon audits the client against their own roadmap once every 90 days
# (synthesized ops/playbooks/delivery.md), the same quarter as the umbrella plan.
ROADMAP_AUDIT_DAYS = QUARTERLY_REVIEW_DAYS


class DeliveryRung(Enum):
    """The canon's delivery ladder (canon files 11 and 12).

    The canon's delivery playbook says to "start one to one. Move to a live
    cohort. Then record it as an evergreen program" (synthesized
    ``ops/playbooks/delivery.md``), so the ladder is an ordered ascension from the
    most hands-on rung to the most leveraged one.
    """

    ONE_TO_ONE = "one_to_one"
    LIVE_COHORT = "live_cohort"
    EVERGREEN = "evergreen"


DELIVERY_RUNG_ORDER: tuple[DeliveryRung, ...] = (
    DeliveryRung.ONE_TO_ONE,
    DeliveryRung.LIVE_COHORT,
    DeliveryRung.EVERGREEN,
)


def _require_blank_free(label: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidDeliveryLadderError(f"{label} is required")


@dataclass(frozen=True)
class DeliveryStep:
    """One program step delivered with a working tool (canon delivery playbook).

    The canon says "one deliverable per step. Every module gives the client a
    working tool" (synthesized ``ops/playbooks/delivery.md``). A step names the
    program step it delivers and the working tool the client leaves with. It is
    frozen and reject-only: a blank step name or deliverable cannot be represented
    as part of the delivery plan.
    """

    step_name: str
    deliverable: str

    def __post_init__(self) -> None:
        _require_blank_free("delivery step name", self.step_name)
        _require_blank_free("delivery step deliverable", self.deliverable)


@dataclass(frozen=True)
class RoadmapAudit:
    """One 90-day roadmap audit (canon delivery playbook).

    The canon audits the client against their own roadmap once every 90 days and
    finds the missing step (synthesized ``ops/playbooks/delivery.md``). An audit
    records who performed it, when, and the exact date the next audit is due (one
    90-day quarter later), so the audit trail has an owner and a cadence.
    """

    audited_on: date
    next_audit_on: date
    actor: str

    def __post_init__(self) -> None:
        _require_blank_free("roadmap audit actor", self.actor)
        if not isinstance(self.audited_on, date) or not isinstance(
            self.next_audit_on, date
        ):
            raise InvalidDeliveryLadderError(
                "a roadmap audit requires audit and next-audit dates"
            )
        expected = self.audited_on + timedelta(days=ROADMAP_AUDIT_DAYS)
        if self.next_audit_on != expected:
            raise DeliveryAuditCadenceError(
                f"roadmap audit by {self.actor!r} on {self.audited_on} must "
                f"schedule its next audit on {expected}, not {self.next_audit_on}"
            )


@dataclass(frozen=True)
class DeliveryGoal:
    """A success goal set at kickoff (canon delivery playbook).

    The canon sets success goals at kickoff and measures results against them
    (synthesized ``ops/playbooks/delivery.md``). A goal names what is being moved,
    the metric it is measured by and the target, so the close gate has something
    specific to check.
    """

    name: str
    metric: str
    target: str

    def __post_init__(self) -> None:
        for label, value in (
            ("delivery goal name", self.name),
            ("delivery goal metric", self.metric),
            ("delivery goal target", self.target),
        ):
            _require_blank_free(label, value)


@dataclass(frozen=True)
class DeliveryResult:
    """A caller-supplied measured result for one goal (SPEC.md section 3).

    The Measurement context owns observed results; the delivery ladder never
    infers or fabricates one. A result names the goal it answers, the observed
    value and whether it met the goal, so the close gate can compare results to
    the goals set at kickoff without the ladder storing an observation.
    """

    goal_name: str
    observed: str
    met: bool

    def __post_init__(self) -> None:
        _require_blank_free("delivery result goal name", self.goal_name)
        _require_blank_free("delivery result observed value", self.observed)
        if not isinstance(self.met, bool):
            raise InvalidDeliveryLadderError(
                "a delivery result must state whether it met the goal"
            )


@dataclass(frozen=True)
class AscensionOffer:
    """One small offer a finished step becomes (canon delivery playbook).

    The canon says to "turn each finished step into a small offer" (synthesized
    ``ops/playbooks/delivery.md``), the next-offer path of the portfolio. An offer
    names the program step it comes from and the small offer itself. It is frozen
    and reject-only: a blank step name or offer name cannot be represented as part
    of the ascension path.
    """

    step_name: str
    offer_name: str

    def __post_init__(self) -> None:
        _require_blank_free("ascension offer step name", self.step_name)
        _require_blank_free("ascension offer name", self.offer_name)


@dataclass(frozen=True)
class DeliveryLadder:
    """The canon delivery ladder and ascension plan (SPEC.md section 12.5, G5).

    The ladder binds a named owner to a same-tenant stage 5 ``ProductProgram``,
    the canon rungs (one-to-one, live cohort, evergreen), one deliverable per
    program step, at least one 90-day roadmap audit, at least one success goal and
    at least one ascension offer. It is the typed form of the client's own
    delivery (Serve) and the next-offer path.

    It is frozen and reject-only, so the canon's shape cannot be bypassed: the
    rungs must be an ordered, duplicate-free subsequence of the canon ladder
    beginning at one-to-one, the step deliverables must be exactly one per program
    step in program order, the audits must keep the 90-day cadence in order, the
    goals must be present, and every ascension offer must name a program step. It
    is a post-launch planning asset, not a required gate kind, and it does not
    authorize sending, spend, publishing or any client commitment (SPEC.md
    sections 4 and 9). It is never an observation (SPEC.md section 3).
    """

    ladder_id: str
    tenant_id: str
    owner: str
    program: ProductProgram
    rungs: tuple[DeliveryRung, ...]
    steps: tuple[DeliveryStep, ...]
    audits: tuple[RoadmapAudit, ...]
    goals: tuple[DeliveryGoal, ...]
    ascension_offers: tuple[AscensionOffer, ...]
    created_on: date

    def __post_init__(self) -> None:
        for label, value in (
            ("delivery ladder id", self.ladder_id),
            ("delivery ladder tenant id", self.tenant_id),
            ("delivery ladder owner", self.owner),
        ):
            _require_blank_free(label, value)
        if not isinstance(self.created_on, date):
            raise InvalidDeliveryLadderError(
                "a delivery ladder requires a creation date"
            )
        self._require_grounding()
        self._require_rungs()
        self._require_steps()
        self._require_audits()
        self._require_goals()
        self._require_ascension_offers()

    def _require_grounding(self) -> None:
        if not isinstance(self.program, ProductProgram):
            raise DeliveryLadderDependencyError(
                "a delivery ladder must be grounded on a typed stage 5 Product "
                "Program"
            )
        if self.program.tenant_id != self.tenant_id:
            raise DeliveryLadderTenantBoundaryError(
                f"delivery ladder {self.ladder_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its Product Program "
                f"{self.program.program_id!r} belongs to tenant "
                f"{self.program.tenant_id!r}"
            )

    def _require_rungs(self) -> None:
        rungs = tuple(self.rungs)
        if not rungs:
            raise InvalidDeliveryLadderError(
                "a delivery ladder requires at least one rung"
            )
        for rung in rungs:
            if not isinstance(rung, DeliveryRung):
                raise InvalidDeliveryLadderError(
                    "a delivery ladder rung must be one of the canon rungs"
                )
        if rungs[0] is not DeliveryRung.ONE_TO_ONE:
            raise DeliveryLadderFormatError(
                "the canon delivery ladder starts one to one (canon files 11 and "
                "12; synthesized ops/playbooks/delivery.md)"
            )
        positions = [DELIVERY_RUNG_ORDER.index(rung) for rung in rungs]
        if positions != sorted(set(positions)):
            raise DeliveryLadderFormatError(
                "a delivery ladder must carry the canon rungs one to one, live "
                "cohort and evergreen in order, without repeats (canon files 11 "
                "and 12)"
            )

    def _require_steps(self) -> None:
        steps = tuple(self.steps)
        if not steps:
            raise InvalidDeliveryLadderError(
                "a delivery ladder requires at least one step deliverable"
            )
        for item in steps:
            if not isinstance(item, DeliveryStep):
                raise InvalidDeliveryLadderError(
                    "a delivery ladder step must be a typed delivery step"
                )
        program_steps = tuple(
            module.signature_step for module in self.program.modules
        )
        for item in steps:
            if item.step_name not in program_steps:
                raise DeliveryLadderDependencyError(
                    f"delivery ladder {self.ladder_id!r} delivers step "
                    f"{item.step_name!r}, which the Product Program "
                    f"{self.program.program_id!r} does not name"
                )
        if tuple(item.step_name for item in steps) != program_steps:
            raise DeliveryLadderFormatError(
                f"delivery ladder {self.ladder_id!r} must carry exactly one "
                "deliverable per program step, in program order (synthesized "
                "ops/playbooks/delivery.md)"
            )

    def _require_audits(self) -> None:
        audits = tuple(self.audits)
        if not audits:
            raise InvalidDeliveryLadderError(
                "a delivery ladder requires at least one 90-day roadmap audit"
            )
        previous: RoadmapAudit | None = None
        for item in audits:
            if not isinstance(item, RoadmapAudit):
                raise InvalidDeliveryLadderError(
                    "a delivery ladder audit must be a typed roadmap audit"
                )
            if item.audited_on < self.created_on:
                raise DeliveryAuditOrderError(
                    f"roadmap audit by {item.actor!r} on {item.audited_on} "
                    f"precedes the ladder creation date {self.created_on}"
                )
            if previous is not None and item.audited_on < previous.next_audit_on:
                raise DeliveryAuditOrderError(
                    f"roadmap audit by {item.actor!r} on {item.audited_on} "
                    f"precedes its previous audit date {previous.next_audit_on}"
                )
            previous = item

    def _require_goals(self) -> None:
        goals = tuple(self.goals)
        if not goals:
            raise InvalidDeliveryLadderError(
                "a delivery ladder requires at least one success goal"
            )
        for item in goals:
            if not isinstance(item, DeliveryGoal):
                raise InvalidDeliveryLadderError(
                    "a delivery ladder goal must be a typed delivery goal"
                )

    def _require_ascension_offers(self) -> None:
        offers = tuple(self.ascension_offers)
        if not offers:
            raise InvalidDeliveryLadderError(
                "a delivery ladder requires at least one ascension offer"
            )
        program_steps = {
            module.signature_step for module in self.program.modules
        }
        seen: set[str] = set()
        for item in offers:
            if not isinstance(item, AscensionOffer):
                raise InvalidDeliveryLadderError(
                    "a delivery ladder ascension offer must be a typed offer"
                )
            if item.step_name not in program_steps:
                raise DeliveryLadderDependencyError(
                    f"delivery ladder {self.ladder_id!r} turns step "
                    f"{item.step_name!r} into a small offer, but the Product "
                    f"Program {self.program.program_id!r} does not name that step"
                )
            if item.step_name in seen:
                raise DeliveryLadderFormatError(
                    f"delivery ladder {self.ladder_id!r} turns step "
                    f"{item.step_name!r} into more than one small offer"
                )
            seen.add(item.step_name)

    @property
    def canon_reference(self) -> str:
        """The canon file block whose structure shaped this artifact."""
        return DELIVERY_CANON_REFERENCE

    @property
    def rung_kinds(self) -> tuple[DeliveryRung, ...]:
        """The canon rungs the ladder carries, in order."""
        return tuple(self.rungs)

    @property
    def covered_steps(self) -> tuple[str, ...]:
        """The program steps the ladder delivers, in program order."""
        return tuple(item.step_name for item in self.steps)

    @property
    def latest_audit(self) -> RoadmapAudit:
        """The most recent recorded roadmap audit."""
        return self.audits[-1]

    @property
    def next_audit_due(self) -> date:
        """The date the next 90-day roadmap audit is due."""
        return self.latest_audit.next_audit_on

    @property
    def is_post_launch(self) -> bool:
        """The canon runs delivery in the Serve stage, after the client buys."""
        return True

    @property
    def is_plan(self) -> bool:
        """A delivery ladder is a plan, not activity or an observed result."""
        return True

    def close(self, *, results: Iterable[DeliveryResult]) -> None:
        """Close the delivery only when every kickoff goal is met.

        The canon measures results against the goals set at kickoff and says to
        fix the plan before closing when the results do not match (synthesized
        ``ops/playbooks/delivery.md``). The results are caller-supplied
        observations (SPEC.md section 3); the ladder checks them without storing
        them. A missing or unmet goal, or a result for a goal the ladder does not
        carry, is refused with ``DeliveryGateError``.
        """
        items = tuple(results)
        for item in items:
            if not isinstance(item, DeliveryResult):
                raise DeliveryGateError(
                    "a delivery close requires typed measured results"
                )
        by_goal: Mapping[str, DeliveryResult] = {
            item.goal_name: item for item in items
        }
        if len(by_goal) != len(items):
            raise DeliveryGateError(
                "a delivery close cannot carry two results for one goal"
            )
        goal_names = {goal.name for goal in self.goals}
        missing = goal_names - set(by_goal)
        if missing:
            raise DeliveryGateError(
                f"delivery ladder {self.ladder_id!r} cannot close; no result for "
                "goal(s) " + ", ".join(sorted(missing))
            )
        unknown = set(by_goal) - goal_names
        if unknown:
            raise DeliveryGateError(
                f"delivery ladder {self.ladder_id!r} cannot close; result(s) for "
                "unknown goal(s) " + ", ".join(sorted(unknown))
            )
        unmet = sorted(
            name for name, item in by_goal.items() if not item.met
        )
        if unmet:
            raise DeliveryGateError(
                f"delivery ladder {self.ladder_id!r} cannot close; goal(s) not "
                "met: " + ", ".join(unmet) + "; fix the plan before closing "
                "(synthesized ops/playbooks/delivery.md)"
            )

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a delivery ladder as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The ladder
        describes the delivery and ascension the client will run, while any
        attendance, completion or result stays a separate observation, so a ladder
        is never an observation.
        """
        raise DeliveryLadderObservationError(
            f"delivery ladder {claim_id!r} is a delivery and ascension plan, not "
            "an observed result, and cannot be recorded as an observation"
        )

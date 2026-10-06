"""The canon service line (pure domain), shaped by ``internal/service-ops.md``.

SPEC.md section 12.5 records the canon's service-line artifacts as a canon gap:
the kickoff checklist, the module production standard, the session guide, the
client scorecard and the case study template. The implementation plan's canon gap
backlog item G7 names typed artifacts for them, with the case study as sourced
proof that is client-approved and version-scoped. The canon supplies the
substance:

- ``internal/service-ops.md`` fixes the service line as onboard, deliver, track
  and prove, with the gate "results are measured against the goals set at
  kickoff", and points at the five synthesized checklists.
- Synthesized ``ops/checklists/kickoff.md`` fixes the named delivery lead, the
  welcome within one business day, success goals written as a number and a date,
  the start date, the collected access, the shared one-page plan and the first
  module on the calendar.
- Synthesized ``ops/checklists/module-production.md`` fixes the module goal and
  the one currency, and the outline-to-publish steps.
- Synthesized ``ops/checklists/session-guide.md`` fixes the session goal, the one
  idea, one example, the client task, and the next step and date.
- Synthesized ``ops/checklists/client-scorecard.md`` fixes the four things the
  scorecard watches (attendance, progress, results, risk) and a risk that carries
  an action.
- Synthesized ``ops/checklists/case-study.md`` and
  ``ops/sops/case-study-capture.md`` fix the case study as a real measured
  result, written permission, an approved quote and a version-scoped,
  client-approved story.

The service line is grounded on the same-tenant stage 5 ``ProductProgram`` it
delivers, so the delivery plan is traceable to the productized offer. It is a
plan, not an observation (SPEC.md section 3); it does not authorize sending,
spend, publishing or any client commitment (SPEC.md sections 4 and 9), which stay
human decisions. Canon text is treated as data (SPEC.md section 12.2): only
structure, terminology and intent are extracted, never copied.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from redops.contexts.commercial.domain.value_objects import ProductProgram
from redops.contexts.operations.domain.errors import (
    CaseStudyAuthorityError,
    CaseStudyProofError,
    CaseStudyVersionError,
    InvalidServiceLineError,
    ServiceLineDependencyError,
    ServiceLineFormatError,
    ServiceLineGateError,
    ServiceLineObservationError,
    ServiceLineTenantBoundaryError,
)

SERVICE_LINE_CANON_REFERENCE = (
    "internal/service-ops.md; ops/checklists/kickoff.md, module-production.md, "
    "session-guide.md, client-scorecard.md, case-study.md"
)

# The canon sends the welcome note "within one business day" (synthesized
# ops/checklists/kickoff.md).
WELCOME_WITHIN_DAYS = 1


def _require_blank_free(label: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidServiceLineError(f"{label} is required")


def _require_bool(label: str, value: bool) -> None:
    if not isinstance(value, bool):
        raise InvalidServiceLineError(f"{label} must be stated as true or false")


class ScorecardDimension(Enum):
    """The four things the client scorecard watches (synthesized scorecard).

    The canon's scorecard checklist says "the scorecard watches four things" and
    names attendance, progress, results and risk (synthesized
    ``ops/checklists/client-scorecard.md``), so the scorecard covers all four in
    order.
    """

    ATTENDANCE = "attendance"
    PROGRESS = "progress"
    RESULTS = "results"
    RISK = "risk"


SCORECARD_DIMENSIONS: tuple[ScorecardDimension, ...] = (
    ScorecardDimension.ATTENDANCE,
    ScorecardDimension.PROGRESS,
    ScorecardDimension.RESULTS,
    ScorecardDimension.RISK,
)


class RiskKind(Enum):
    """The canon's risk kinds (synthesized ops/checklists/client-scorecard.md).

    The canon's scorecard checklist says to "mark any risk: quiet, stuck, or
    behind" (synthesized ``ops/checklists/client-scorecard.md``), so a risk names
    one of the three canon kinds.
    """

    QUIET = "quiet"
    STUCK = "stuck"
    BEHIND = "behind"


@dataclass(frozen=True)
class SuccessGoal:
    """One success goal set at kickoff (synthesized ops/checklists/kickoff.md).

    The canon's kickoff checklist says to "set success goals with the client" and
    to "write each goal as a number and a date" (synthesized
    ``ops/checklists/kickoff.md``). A goal records its description, its numeric
    target and the date it is due, so a goal is measurable rather than a wish.
    """

    description: str
    target: str
    due_on: date

    def __post_init__(self) -> None:
        _require_blank_free("success goal description", self.description)
        _require_blank_free("success goal target", self.target)
        if not isinstance(self.due_on, date):
            raise InvalidServiceLineError(
                "a success goal must be written with a due date"
            )


@dataclass(frozen=True)
class KickoffChecklist:
    """The canon kickoff checklist (synthesized ops/checklists/kickoff.md).

    The canon's kickoff checklist names the delivery lead, sends a welcome note
    within one business day, sets success goals as a number and a date, agrees a
    start date, collects access, shares the one-page plan and puts the first
    module on the calendar (synthesized ``ops/checklists/kickoff.md``). It is
    frozen and reject-only, so a kickoff missing its lead, goals, access or plan
    cannot be represented as complete.
    """

    delivery_lead: str
    welcome_within_days: int
    goals: tuple[SuccessGoal, ...]
    start_on: date
    access: frozenset[str]
    plan_shared: bool
    first_module_on: date

    def __post_init__(self) -> None:
        _require_blank_free("kickoff delivery lead", self.delivery_lead)
        if isinstance(self.welcome_within_days, bool) or not isinstance(
            self.welcome_within_days, int
        ):
            raise InvalidServiceLineError(
                "a kickoff welcome must be a whole number of days"
            )
        if self.welcome_within_days != WELCOME_WITHIN_DAYS:
            raise ServiceLineFormatError(
                "a kickoff must welcome the client within one business day "
                f"({WELCOME_WITHIN_DAYS} day), not {self.welcome_within_days} "
                "(synthesized ops/checklists/kickoff.md)"
            )
        goals = tuple(self.goals)
        if not goals:
            raise InvalidServiceLineError(
                "a kickoff requires at least one success goal"
            )
        for item in goals:
            if not isinstance(item, SuccessGoal):
                raise InvalidServiceLineError(
                    "a kickoff goal must be a typed success goal"
                )
        if not isinstance(self.start_on, date):
            raise InvalidServiceLineError("a kickoff requires a start date")
        access = frozenset(self.access)
        if not access:
            raise InvalidServiceLineError(
                "a kickoff requires the access collected from the client"
            )
        for item in access:
            if not isinstance(item, str) or not item.strip():
                raise InvalidServiceLineError(
                    "kickoff access must be non-empty identifiers"
                )
        _require_bool("kickoff plan shared", self.plan_shared)
        if not self.plan_shared:
            raise ServiceLineGateError(
                "a kickoff is done only when the one-page plan is shared "
                "(synthesized ops/checklists/kickoff.md)"
            )
        if not isinstance(self.first_module_on, date):
            raise InvalidServiceLineError(
                "a kickoff requires the first module date"
            )
        if self.first_module_on < self.start_on:
            raise ServiceLineFormatError(
                "a kickoff cannot schedule the first module before the start date "
                "(synthesized ops/checklists/kickoff.md)"
            )


@dataclass(frozen=True)
class ModuleProductionStandard:
    """The canon module production standard (synthesized module-production.md).

    The canon's module production checklist knows the module goal and the one
    currency and runs the build from outline to publish, one idea per section
    (synthesized ``ops/checklists/module-production.md``). The standard carries
    the goal, the currency and the ordered steps; ``confirm`` enforces the canon's
    done criteria (the script and slides match, the video is on brand and the
    module is published).
    """

    module_goal: str
    currency: str
    steps: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_blank_free("module production goal", self.module_goal)
        _require_blank_free("module production currency", self.currency)
        steps = tuple(self.steps)
        if not steps:
            raise InvalidServiceLineError(
                "a module production standard requires its ordered steps"
            )
        for step in steps:
            if not isinstance(step, str) or not step.strip():
                raise InvalidServiceLineError(
                    "a module production step must be a non-blank step"
                )
        if len(set(steps)) != len(steps):
            raise ServiceLineFormatError(
                "a module production standard must run each step once "
                "(synthesized ops/checklists/module-production.md)"
            )

    def confirm(
        self,
        *,
        script_matches_slides: bool,
        on_brand: bool,
        published: bool,
    ) -> None:
        """Confirm the canon's module done criteria, or refuse.

        The canon's module production checklist is done only when the script and
        slides match, the video is clear and on brand and the module is live for
        the client (synthesized ``ops/checklists/module-production.md``). An unmet
        criterion is refused with ``ServiceLineGateError``, so a module cannot be
        confirmed before it meets the standard.
        """
        for label, value in (
            ("script matches slides", script_matches_slides),
            ("on brand", on_brand),
            ("published", published),
        ):
            _require_bool(f"module {label}", value)
        if not (script_matches_slides and on_brand and published):
            raise ServiceLineGateError(
                "a module is done only when the script and slides match, the video "
                "is on brand and the module is published (synthesized "
                "ops/checklists/module-production.md)"
            )


@dataclass(frozen=True)
class SessionGuide:
    """The canon session guide (synthesized ops/checklists/session-guide.md).

    The canon's session guide knows the session goal, teaches the one idea for the
    day, shows one example, asks the client to do the task and says the next step
    and the next date (synthesized ``ops/checklists/session-guide.md``). It is
    frozen and reject-only, so a session without a goal, idea, example, task or
    next step cannot be represented as a guide.
    """

    session_goal: str
    one_idea: str
    example: str
    task: str
    next_step: str
    next_on: date

    def __post_init__(self) -> None:
        for label, value in (
            ("session goal", self.session_goal),
            ("session one idea", self.one_idea),
            ("session example", self.example),
            ("session task", self.task),
            ("session next step", self.next_step),
        ):
            _require_blank_free(label, value)
        if not isinstance(self.next_on, date):
            raise InvalidServiceLineError(
                "a session guide must name the next session date"
            )


@dataclass(frozen=True)
class ScorecardRisk:
    """One risk on the client scorecard (synthesized client-scorecard.md).

    The canon's scorecard checklist says to "mark any risk: quiet, stuck, or
    behind" and to "write one action for the next week" (synthesized
    ``ops/checklists/client-scorecard.md``). A risk names one of the canon kinds
    and the action that addresses it, so a risk is never left without an owner
    action.
    """

    kind: RiskKind
    action: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, RiskKind):
            raise InvalidServiceLineError(
                "a scorecard risk must name one of the canon risk kinds"
            )
        _require_blank_free("scorecard risk action", self.action)


@dataclass(frozen=True)
class ClientScorecard:
    """The canon client scorecard (synthesized ops/checklists/client-scorecard.md).

    The canon's scorecard checklist watches four things -- attendance, progress,
    results and risk -- and is done only when it is shared with the delivery lead
    (synthesized ``ops/checklists/client-scorecard.md``). The scorecard carries
    the four canon dimensions in order and the risks, each with an action.
    """

    dimensions: tuple[ScorecardDimension, ...]
    risks: tuple[ScorecardRisk, ...]
    shared_with_lead: bool

    def __post_init__(self) -> None:
        dimensions = tuple(self.dimensions)
        for dimension in dimensions:
            if not isinstance(dimension, ScorecardDimension):
                raise InvalidServiceLineError(
                    "a scorecard dimension must be one of the canon dimensions"
                )
        if dimensions != SCORECARD_DIMENSIONS:
            raise ServiceLineFormatError(
                "a scorecard must watch the four canon things -- attendance, "
                "progress, results and risk -- in order, without repeats "
                "(synthesized ops/checklists/client-scorecard.md)"
            )
        risks = tuple(self.risks)
        for item in risks:
            if not isinstance(item, ScorecardRisk):
                raise InvalidServiceLineError(
                    "a scorecard risk must be a typed scorecard risk"
                )
        _require_bool("scorecard shared with lead", self.shared_with_lead)
        if not self.shared_with_lead:
            raise ServiceLineGateError(
                "a scorecard is done only when it is shared with the delivery lead "
                "(synthesized ops/checklists/client-scorecard.md)"
            )


@dataclass(frozen=True)
class CaseStudyClaim:
    """A version-scoped, client-approved case study claim (SPEC.md section 4).

    The claim is the client-approved proof a case study yields: the study, the
    client, the approved version and the intended use, plus the approved quote.
    SPEC.md section 4 scopes client-approved information to a version and intended
    use, so the claim carries both and cannot be reused outside that scope.
    """

    study_id: str
    tenant_id: str
    client_name: str
    approved_version: str
    intended_use: str
    quote: str

    def __post_init__(self) -> None:
        for label, value in (
            ("case study claim study id", self.study_id),
            ("case study claim tenant id", self.tenant_id),
            ("case study claim client name", self.client_name),
            ("case study claim approved version", self.approved_version),
            ("case study claim intended use", self.intended_use),
            ("case study claim quote", self.quote),
        ):
            _require_blank_free(label, value)


@dataclass(frozen=True)
class CaseStudy:
    """The canon case study template (synthesized case-study.md and capture SOP).

    The canon's case study checklist confirms the result is real and measured,
    collects the starting and ending numbers, asks for written permission, takes
    one quote in the client's own words, sends the draft to the client and
    publishes only after approval (synthesized ``ops/checklists/case-study.md``
    and ``ops/sops/case-study-capture.md``). SPEC.md sections 1 and 4 forbid an
    unreviewed testimonial or performance claim and scope client-approved
    information to a version and intended use.

    The template may exist before the result lands, so construction requires the
    study's identity and content but not the approval. ``claim`` is the gate: it
    refuses an unsourced result, an unapproved testimonial and an unversioned
    claim, so the platform never presents a testimonial the canon and SPEC do not
    allow.
    """

    study_id: str
    tenant_id: str
    client_name: str
    result_measured: bool
    start_numbers: str
    end_numbers: str
    quote: str
    quote_approved: bool
    written_permission: bool
    approved_version: str
    intended_use: str
    published: bool

    def __post_init__(self) -> None:
        for label, value in (
            ("case study id", self.study_id),
            ("case study tenant id", self.tenant_id),
            ("case study client name", self.client_name),
            ("case study quote", self.quote),
        ):
            _require_blank_free(label, value)
        for label, value in (
            ("case study result measured", self.result_measured),
            ("case study quote approved", self.quote_approved),
            ("case study written permission", self.written_permission),
            ("case study published", self.published),
        ):
            _require_bool(label, value)

    def claim(self) -> CaseStudyClaim:
        """Return the version-scoped, client-approved claim, or refuse.

        The canon confirms the result is real and measured and collects the
        starting and ending numbers before writing the story (synthesized
        ``ops/checklists/case-study.md`` and ``ops/sops/case-study-capture.md``),
        so an unmeasured result or missing numbers is refused with
        ``CaseStudyProofError``. The canon requires written permission and an
        approved quote and says never to publish without written permission, so an
        unapproved testimonial is refused with ``CaseStudyAuthorityError``. SPEC.md
        section 4 scopes client-approved information to a version and intended use,
        so a claim without either is refused with ``CaseStudyVersionError``.
        """
        if not self.result_measured or not (
            self.start_numbers and self.start_numbers.strip()
        ) or not (self.end_numbers and self.end_numbers.strip()):
            raise CaseStudyProofError(
                f"case study {self.study_id!r} has no real, measured result with "
                "starting and ending numbers; the canon confirms the result before "
                "writing the story (synthesized ops/checklists/case-study.md)"
            )
        if not self.written_permission or not self.quote_approved:
            raise CaseStudyAuthorityError(
                f"case study {self.study_id!r} has no written permission or no "
                "approved quote; the canon never publishes a story without written "
                "permission (synthesized ops/sops/case-study-capture.md)"
            )
        if not (self.approved_version and self.approved_version.strip()) or not (
            self.intended_use and self.intended_use.strip()
        ):
            raise CaseStudyVersionError(
                f"case study {self.study_id!r} is not scoped to an approved version "
                "and intended use; client-approved information is version scoped "
                "(SPEC.md section 4)"
            )
        return CaseStudyClaim(
            study_id=self.study_id,
            tenant_id=self.tenant_id,
            client_name=self.client_name,
            approved_version=self.approved_version,
            intended_use=self.intended_use,
            quote=self.quote,
        )


@dataclass(frozen=True)
class ServiceLine:
    """The canon service line (SPEC.md section 12.5, G7).

    The service line binds a named owner to a same-tenant stage 5
    ``ProductProgram`` and the five canon artifacts: the kickoff checklist, the
    module production standard, the session guide, the client scorecard and the
    case study. It is the typed form of the white-glove service that runs the
    productized program, the delivery layer after the partnership line (G6).

    It is frozen and reject-only, so the canon's shape cannot be bypassed: the
    kickoff must welcome within one business day and share the plan, the module
    standard must run each step once, the scorecard must watch the four canon
    dimensions in order and be shared, and the case study must be sourced,
    approved and version-scoped before it yields a claim. It is a post-launch
    planning asset, not a required gate kind, and it does not authorize sending,
    spend, publishing or any client commitment (SPEC.md sections 4 and 9). It is
    never an observation (SPEC.md section 3).
    """

    service_line_id: str
    tenant_id: str
    owner: str
    program: ProductProgram
    kickoff: KickoffChecklist
    module_standard: ModuleProductionStandard
    session_guide: SessionGuide
    scorecard: ClientScorecard
    case_study: CaseStudy
    created_on: date

    def __post_init__(self) -> None:
        for label, value in (
            ("service line id", self.service_line_id),
            ("service line tenant id", self.tenant_id),
            ("service line owner", self.owner),
        ):
            _require_blank_free(label, value)
        if not isinstance(self.created_on, date):
            raise InvalidServiceLineError(
                "a service line requires a creation date"
            )
        self._require_grounding()
        self._require_artifacts()
        self._require_case_study_tenant()

    def _require_grounding(self) -> None:
        if not isinstance(self.program, ProductProgram):
            raise ServiceLineDependencyError(
                "a service line must be grounded on a typed stage 5 Product "
                "Program"
            )
        if self.program.tenant_id != self.tenant_id:
            raise ServiceLineTenantBoundaryError(
                f"service line {self.service_line_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its Product Program "
                f"{self.program.program_id!r} belongs to tenant "
                f"{self.program.tenant_id!r}"
            )

    def _require_artifacts(self) -> None:
        for label, value, expected in (
            ("kickoff checklist", self.kickoff, KickoffChecklist),
            (
                "module production standard",
                self.module_standard,
                ModuleProductionStandard,
            ),
            ("session guide", self.session_guide, SessionGuide),
            ("client scorecard", self.scorecard, ClientScorecard),
            ("case study", self.case_study, CaseStudy),
        ):
            if not isinstance(value, expected):
                raise InvalidServiceLineError(
                    f"a service line requires a typed {label}"
                )

    def _require_case_study_tenant(self) -> None:
        if self.case_study.tenant_id != self.tenant_id:
            raise ServiceLineTenantBoundaryError(
                f"service line {self.service_line_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its case study "
                f"{self.case_study.study_id!r} belongs to tenant "
                f"{self.case_study.tenant_id!r}"
            )

    @property
    def canon_reference(self) -> str:
        """The canon file block whose structure shaped this artifact."""
        return SERVICE_LINE_CANON_REFERENCE

    @property
    def is_post_launch(self) -> bool:
        """The canon runs the service line after the sale, in the Serve stage."""
        return True

    @property
    def is_plan(self) -> bool:
        """A service line is a delivery plan, not activity or an observed result."""
        return True

    def prove(self) -> CaseStudyClaim:
        """Return the case study claim that proves the kickoff goals were met.

        The canon's service-ops gate is "results are measured against the goals
        set at kickoff" (``internal/service-ops.md``), and the case study is the
        proof. The gate delegates to the case study's own claim, so an unsourced,
        unapproved or unversioned case study is refused rather than presented as
        proof.
        """
        return self.case_study.claim()

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a service line as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The
        service line is the delivery plan and its checklists, while any
        attendance, progress, result or published case study stays a separate
        observation, so a service line is never an observation.
        """
        raise ServiceLineObservationError(
            f"service line {claim_id!r} is a delivery plan, not an observed "
            "result, and cannot be recorded as an observation"
        )

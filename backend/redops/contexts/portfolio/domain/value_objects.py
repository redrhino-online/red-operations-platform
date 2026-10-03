"""Value objects for the Portfolio bounded context (pure domain).

SPEC.md section 3 gives the Portfolio context the engagement roadmap, and
SPEC.md section 12.5 records the canon's umbrella planning as a canon gap: the
Online Business Launch Map and the one-page Bulletproof Business Plan (canon
files 00 and 01). Canon file 00 puts the whole strategy -- foundation, signature
solution, funnel and floodgates -- "into one really powerful page" over the
12-week program. Canon file 01 requires the one-page business plan's goals and
metrics to be specific, to be revisited every 90 days, and not to be put on the
shelf.

RED maps the canon's four launch-map parts onto the versioned stage 0 to 10
template (SPEC.md section 4). That mapping is an intentional implementation
deviation from the canon's 12-week coaching calendar: the canon governs the
shape and intent (four strategy parts on one page, specific targets, a 90-day
revisit), while SPEC.md section 4 governs the stage backbone the plan is drawn
over.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum

from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.governance.domain.value_objects import (
    StageAssetVersion,
    StageTemplate,
)
from redops.contexts.portfolio.domain.errors import (
    InvalidOpportunityError,
    InvalidUmbrellaPlanError,
    OpportunityAuthorityError,
    OpportunityTenantBoundaryError,
    UmbrellaPlanDependencyError,
    UmbrellaPlanFormatError,
    UmbrellaPlanObservationError,
    UmbrellaPlanTenantBoundaryError,
    UmbrellaReviewCadenceError,
    UmbrellaReviewOrderError,
)

QUARTERLY_REVIEW_DAYS = 90


class LaunchMapSection(Enum):
    """The four parts of the canon's Online Business Launch Map (canon file 00).

    Canon file 00 lays the whole strategy out as the foundation ("do you know who
    your target market is ... a clear message that's irresistible to them"), the
    signature solution ("how do you productize your offer and package it in a
    visual way"), the funnel ("attract leads, engage them ... the authority
    amplifier ... a conversion event") and the floodgates ("traffic on demand ...
    content marketing and social media ... retargeting").
    """

    FOUNDATION = "foundation"
    SIGNATURE_SOLUTION = "signature_solution"
    FUNNEL = "funnel"
    FLOODGATES = "floodgates"


LAUNCH_MAP_SECTIONS: tuple[LaunchMapSection, ...] = (
    LaunchMapSection.FOUNDATION,
    LaunchMapSection.SIGNATURE_SOLUTION,
    LaunchMapSection.FUNNEL,
    LaunchMapSection.FLOODGATES,
)

LAUNCH_MAP_SECTION_STAGES: dict[LaunchMapSection, tuple[int, ...]] = {
    LaunchMapSection.FOUNDATION: (0, 1, 2),
    LaunchMapSection.SIGNATURE_SOLUTION: (3, 4, 5),
    LaunchMapSection.FUNNEL: (6, 7, 8, 9),
    LaunchMapSection.FLOODGATES: (10,),
}


@dataclass(frozen=True)
class UmbrellaSection:
    """One canon launch-map part covering a span of pipeline stages.

    Canon file 00's foundation carries the avatar and the message (stages 0 to
    2), the signature solution productizes the method (stages 3 to 5), the funnel
    produces and integrates the campaign (stages 6 to 9), and the floodgates
    launch and drive traffic (stage 10). The section names its objective so the
    one-page map says what that part of the engagement is for, not only which
    stages it spans.
    """

    section: LaunchMapSection
    stages: tuple[int, ...]
    objective: str

    def __post_init__(self) -> None:
        if not isinstance(self.section, LaunchMapSection):
            raise InvalidUmbrellaPlanError(
                "an umbrella section must be a typed launch map section"
            )
        if not self.objective or not self.objective.strip():
            raise InvalidUmbrellaPlanError(
                "an umbrella section requires an objective"
            )
        stages = tuple(self.stages)
        if not stages:
            raise InvalidUmbrellaPlanError(
                "an umbrella section must cover at least one stage"
            )
        seen: set[int] = set()
        for stage in stages:
            if not isinstance(stage, int) or stage < 0:
                raise InvalidUmbrellaPlanError(
                    "an umbrella section stage must be a non-negative number"
                )
            if stage in seen:
                raise UmbrellaPlanFormatError(
                    f"umbrella section {self.section.value!r} repeats stage "
                    f"{stage}"
                )
            seen.add(stage)


@dataclass(frozen=True)
class BusinessTarget:
    """A specific, measurable goal of the canon's bulletproof business plan.

    Canon file 01 warns that the business plan fails when "metrics aren't
    specific enough" and when it is treated as an exercise. A target therefore
    names what is being moved, the metric it is measured by, the goal value or
    direction, and the date it is due, mirroring the canon's
    avatar-times-currency-times-metric-times-timeline discipline (SPEC.md section
    12.3 stage 2).
    """

    target_id: str
    name: str
    metric: str
    goal: str
    due_on: date

    def __post_init__(self) -> None:
        for label, value in (
            ("business target id", self.target_id),
            ("business target name", self.name),
            ("business target metric", self.metric),
            ("business target goal", self.goal),
        ):
            if not value or not value.strip():
                raise InvalidUmbrellaPlanError(f"{label} is required")
        if not isinstance(self.due_on, date):
            raise InvalidUmbrellaPlanError(
                "a business target requires a due date"
            )


@dataclass(frozen=True)
class QuarterlyReview:
    """One 90-day revisit of the umbrella plan (canon file 01).

    Canon file 01 requires the one-page plan to be "redone every 90 days" and not
    put on the shelf, so a review records who reviewed the plan, when, and the
    exact date the next revisit is due (one 90-day quarter later). The review is
    named by its actor so the revisit trail has an owner.
    """

    reviewed_on: date
    next_review_on: date
    actor: str

    def __post_init__(self) -> None:
        if not self.actor or not self.actor.strip():
            raise InvalidUmbrellaPlanError("a quarterly review requires an actor")
        if not isinstance(self.reviewed_on, date) or not isinstance(
            self.next_review_on, date
        ):
            raise InvalidUmbrellaPlanError(
                "a quarterly review requires review and next-review dates"
            )
        expected = self.reviewed_on + timedelta(days=QUARTERLY_REVIEW_DAYS)
        if self.next_review_on != expected:
            raise UmbrellaReviewCadenceError(
                f"quarterly review by {self.actor!r} on {self.reviewed_on} must "
                f"schedule its next revisit on {expected}, not "
                f"{self.next_review_on}"
            )


@dataclass(frozen=True)
class UmbrellaPlan:
    """The canon's single-page engagement plan over the stage 0 to 10 pipeline.

    SPEC.md section 12.5 records the canon's umbrella planning as a canon gap
    mapped to "portfolio and engagement planning over stages 0 to 10". The plan
    binds the canon's Online Business Launch Map sections (canon file 00), at
    least one specific bulletproof-business-plan target (canon file 01) and the
    canon's 90-day revisit cadence to one named owner, one client workspace and
    one versioned stage template. Every template stage is covered by exactly one
    launch-map section, so the one page spans the whole pipeline.

    It is a planning decision, not a new required gate kind (a methodology-owner
    decision, SPEC.md section 12.5). It does not authorize production, spend or
    traffic (SPEC.md sections 4 and 9) and it is never an observation (SPEC.md
    section 3).
    """

    plan_id: str
    tenant_id: str
    owner: str
    workspace: ClientWorkspace
    template: StageTemplate
    sections: tuple[UmbrellaSection, ...]
    targets: tuple[BusinessTarget, ...]
    reviews: tuple[QuarterlyReview, ...]
    created_on: date

    def __post_init__(self) -> None:
        for label, value in (
            ("umbrella plan id", self.plan_id),
            ("umbrella plan tenant id", self.tenant_id),
            ("umbrella plan owner", self.owner),
        ):
            if not value or not value.strip():
                raise InvalidUmbrellaPlanError(f"{label} is required")
        if not isinstance(self.created_on, date):
            raise InvalidUmbrellaPlanError(
                "an umbrella plan requires a creation date"
            )
        if not isinstance(self.workspace, ClientWorkspace):
            raise UmbrellaPlanDependencyError(
                "an umbrella plan must belong to a typed client workspace"
            )
        if self.workspace.tenant_id != self.tenant_id:
            raise UmbrellaPlanTenantBoundaryError(
                f"umbrella plan {self.plan_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its workspace "
                f"{self.workspace.workspace_id!r} belongs to tenant "
                f"{self.workspace.tenant_id!r}"
            )
        if not isinstance(self.template, StageTemplate):
            raise UmbrellaPlanDependencyError(
                "an umbrella plan must be drawn over a typed versioned stage "
                "template"
            )

        stage_numbers = {stage.stage_number for stage in self.template.stages}
        section_kinds = [section.section for section in self.sections]
        for kind in LAUNCH_MAP_SECTIONS:
            count = section_kinds.count(kind)
            if count == 0:
                raise UmbrellaPlanFormatError(
                    f"umbrella plan is missing the canon launch map section "
                    f"{kind.value!r}"
                )
            if count > 1:
                raise UmbrellaPlanFormatError(
                    f"umbrella plan repeats the canon launch map section "
                    f"{kind.value!r}"
                )
        if len(section_kinds) != len(LAUNCH_MAP_SECTIONS):
            raise UmbrellaPlanFormatError(
                "umbrella plan must carry exactly the canon launch map sections"
            )
        covered: list[int] = []
        for section in self.sections:
            for stage in section.stages:
                if stage not in stage_numbers:
                    raise UmbrellaPlanDependencyError(
                        f"umbrella section {section.section.value!r} covers stage "
                        f"{stage}, which the plan's stage template does not name"
                    )
                if stage in covered:
                    raise UmbrellaPlanFormatError(
                        f"umbrella plan covers stage {stage} more than once"
                    )
                covered.append(stage)
        missing = tuple(sorted(stage_numbers - set(covered)))
        if missing:
            raise UmbrellaPlanFormatError(
                "umbrella plan does not cover every template stage; missing "
                + ", ".join(str(stage) for stage in missing)
            )

        if not self.targets:
            raise InvalidUmbrellaPlanError(
                "an umbrella plan requires at least one specific business target"
            )
        target_ids: set[str] = set()
        for target in self.targets:
            if not isinstance(target, BusinessTarget):
                raise InvalidUmbrellaPlanError(
                    "an umbrella plan target must be a typed business target"
                )
            if target.target_id in target_ids:
                raise UmbrellaPlanFormatError(
                    f"umbrella plan repeats target id {target.target_id!r}"
                )
            target_ids.add(target.target_id)
            if target.due_on < self.created_on:
                raise UmbrellaPlanFormatError(
                    f"business target {target.target_id!r} is due before the "
                    "umbrella plan was created"
                )

        if not self.reviews:
            raise InvalidUmbrellaPlanError(
                "an umbrella plan requires at least one quarterly review"
            )
        previous: QuarterlyReview | None = None
        for review in self.reviews:
            if not isinstance(review, QuarterlyReview):
                raise InvalidUmbrellaPlanError(
                    "an umbrella plan review must be a typed quarterly review"
                )
            if review.reviewed_on < self.created_on:
                raise UmbrellaReviewOrderError(
                    f"quarterly review by {review.actor!r} on "
                    f"{review.reviewed_on} precedes the plan creation date "
                    f"{self.created_on}"
                )
            if previous is not None and review.reviewed_on < previous.next_review_on:
                raise UmbrellaReviewOrderError(
                    f"quarterly review by {review.actor!r} on "
                    f"{review.reviewed_on} precedes its previous revisit date "
                    f"{previous.next_review_on}"
                )
            previous = review

    @property
    def covered_stages(self) -> tuple[int, ...]:
        """The template stages the launch map already covers, in order."""
        covered = {stage for section in self.sections for stage in section.stages}
        return tuple(sorted(covered))

    def missing_stages(self) -> tuple[int, ...]:
        """Template stages the launch map does not yet cover."""
        covered = set(self.covered_stages)
        return tuple(
            sorted(
                stage.stage_number
                for stage in self.template.stages
                if stage.stage_number not in covered
            )
        )

    @property
    def latest_review(self) -> QuarterlyReview:
        """The most recent recorded revisit."""
        return self.reviews[-1]

    @property
    def next_review_due(self) -> date:
        """The date the next 90-day revisit is due."""
        return self.latest_review.next_review_on

    @property
    def is_plan(self) -> bool:
        """An umbrella plan is a plan, not activity or an observed result."""
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent an umbrella plan as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The plan
        states the engagement's intended strategy and targets, while any measured
        movement is a separate observation, so a plan is never an observation.
        """
        raise UmbrellaPlanObservationError(
            f"umbrella plan {claim_id!r} is an intended strategy, not an observed "
            "result, and cannot be recorded as an observation"
        )



class OpportunityKind(Enum):
    """The canon's Grow effects for a portfolio opportunity (canon files 11, 12).

    SPEC.md section 12.3 records the canon's Grow motion: it "splits the
    foundation offer into smaller offers that act as new entry points and raise
    customer lifetime value". An opportunity is one of those two effects, so the
    register distinguishes a new entry point from a lifetime value offer and
    cannot record an untyped expansion.
    """

    ENTRY_POINT = "entry_point"
    LIFETIME_VALUE = "lifetime_value"


class OpportunityState(Enum):
    """The lifecycle of a portfolio opportunity (SPEC.md sections 1 and 5).

    The register holds proposals only: an opportunity stays ``PROPOSED`` until a
    human investment authority acts. ``APPROVED``, ``REJECTED`` and ``PARKED``
    are named so an attempt to store an opportunity as already decided is
    refused with a named error rather than silently accepted as approved fact.
    """

    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    PARKED = "parked"


@dataclass(frozen=True)
class Opportunity:
    """One proposed portfolio expansion, grounded on an exact approved asset.

    SPEC.md section 7 lists ``/opportunities`` and SPEC.md section 1 puts
    portfolio expansion in the product contract. The canon's Grow motion splits
    the foundation offer into smaller offers that are new entry points and raise
    customer lifetime value (canon files 11 and 12, mapped in SPEC.md section
    12.3), and the IP Portfolio Development agent owns the derivative
    opportunity and must escalate investment and launch (SPEC.md section 5). This
    value object records the register entry: an opaque id, the owning tenant, a
    title, a typed kind, the exact same-tenant ``StageAssetVersion`` it derives
    from, its investment case, its expected outcome, a named owner, a next action
    and the capture date.

    It is reject-only and frozen. A blank identity, an untyped kind, a
    versionless or cross-tenant source, a missing case, outcome, owner or action,
    or an attempt to record the proposal as approved is refused, so the platform
    never presents a proposed expansion as an authorized investment (SPEC.md
    sections 1, 4 and 5). Recording an opportunity authorizes no investment, no
    spend and no launch.
    """

    opportunity_id: str
    tenant_id: str
    title: str
    kind: OpportunityKind
    source: StageAssetVersion
    investment_case: str
    expected_outcome: str
    owner: str
    next_action: str
    captured_on: date
    state: OpportunityState = OpportunityState.PROPOSED

    def __post_init__(self) -> None:
        for label, value in (
            ("opportunity id", self.opportunity_id),
            ("opportunity tenant id", self.tenant_id),
            ("opportunity title", self.title),
            ("opportunity investment case", self.investment_case),
            ("opportunity expected outcome", self.expected_outcome),
            ("opportunity owner", self.owner),
            ("opportunity next action", self.next_action),
        ):
            if not value or not value.strip():
                raise InvalidOpportunityError(f"{label} is required")
        if not isinstance(self.kind, OpportunityKind):
            raise InvalidOpportunityError(
                "an opportunity requires a typed kind (an entry point or a "
                "lifetime value offer)"
            )
        if not isinstance(self.source, StageAssetVersion):
            raise InvalidOpportunityError(
                "an opportunity requires the exact stage asset version it "
                "derives from; a versionless source is not traceable"
            )
        if self.source.tenant_id != self.tenant_id:
            raise OpportunityTenantBoundaryError(
                f"opportunity {self.opportunity_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its source asset belongs to tenant "
                f"{self.source.tenant_id!r}; an opportunity cannot cross a "
                "client boundary"
            )
        if not isinstance(self.captured_on, date):
            raise InvalidOpportunityError(
                "an opportunity requires a capture date"
            )
        if not isinstance(self.state, OpportunityState):
            raise InvalidOpportunityError(
                "an opportunity requires a typed lifecycle state"
            )
        if self.state is not OpportunityState.PROPOSED:
            raise OpportunityAuthorityError(
                f"opportunity {self.opportunity_id!r} is a proposal and stays "
                f"proposed until a human investment authority acts; the platform "
                f"cannot record it as {self.state.value!r} (SPEC.md sections 1 "
                "and 5)"
            )

    @property
    def source_key(self) -> tuple[str, int]:
        """The exact source asset kind and version this opportunity derives from."""
        return (self.source.kind, self.source.version)

    @property
    def is_proposal(self) -> bool:
        """An opportunity is a proposal, never a client approved fact."""
        return True

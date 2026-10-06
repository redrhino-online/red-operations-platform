"""The canon partnership line and certification (pure domain), shaped by canon 11, 12.

SPEC.md section 12.5 records the partnership line and certification as a canon
gap: the four-offer path, renewal and win-back, the referral and partner plan,
community rules, the reputation track and the certified consultant standard. The
implementation plan's canon gap backlog item G6 names typed artifacts that keep
every client with a next step, a post-launch Portfolio asset that extends the
client's program, not a new stage or required gate kind. The canon supplies the
substance:

- Canon files 11 and 12, the Certification series, Live Sessions 5 and 12 and
  High Ticket Funnels 19 fix the four-offer path (a free entry, a small offer, a
  core offer and a partner offer, each leading to the next) and the partnership
  loop (retain, grow, refer, renew).
- Synthesized ``ops/playbooks/partnership.md`` fixes the regular check-ins, the
  gate ("every client has a next step and a reason to stay"), asking for referrals
  after a win and not before, a community with simple rules, and tracking reviews,
  stories and press.
- Synthesized ``ops/playbooks/certification.md`` and
  ``ops/sops/certification-exam.md`` fix the short standard of a few clear skills,
  the exam with a clear pass mark, the proof rule ("certify only after a real
  result. No result, no badge"), the register of certified people and the yearly
  recheck of the standard.

The plan is grounded on the same-tenant stage 5 ``ProductProgram`` it extends, so
the partnership line is traceable to the productized offer. It is a plan, not an
observation (SPEC.md section 3); it does not authorize sending, spend, publishing
or any client commitment (SPEC.md sections 4 and 9), which stay human decisions.
Canon text is treated as data (SPEC.md section 12.2): only structure, terminology
and intent are extracted, never copied.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from redops.contexts.commercial.domain.value_objects import ProductProgram
from redops.contexts.portfolio.domain.errors import (
    CertificationProofError,
    CertificationStandardError,
    InvalidPartnershipPlanError,
    PartnershipDependencyError,
    PartnershipFormatError,
    PartnershipGateError,
    PartnershipObservationError,
    PartnershipTenantBoundaryError,
)

PARTNERSHIP_CANON_REFERENCE = (
    "11, 12; Certification; Live Sessions 5, 12; High Ticket Funnels 19"
)

# The canon rechecks the certification standard every year (synthesized
# ops/playbooks/certification.md and ops/sops/certification-exam.md).
CERTIFICATION_RECHECK_DAYS = 365

# The canon keeps the standard short: "a few clear skills, not a long list"
# (synthesized ops/playbooks/certification.md).
MAX_CERTIFICATION_SKILLS = 6


def _require_blank_free(label: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidPartnershipPlanError(f"{label} is required")


class PartnershipOfferRung(Enum):
    """The canon's four-offer path (canon files 11 and 12).

    The canon's partnership playbook says "a free entry, a small offer, a core
    offer, and a partner offer. Each one leads to the next" (synthesized
    ``ops/playbooks/partnership.md``), so the path is an ordered ascension from the
    free entry to the partner offer.
    """

    ENTRY = "entry"
    MID = "mid"
    CORE = "core"
    PARTNER = "partner"


PARTNERSHIP_OFFER_ORDER: tuple[PartnershipOfferRung, ...] = (
    PartnershipOfferRung.ENTRY,
    PartnershipOfferRung.MID,
    PartnershipOfferRung.CORE,
    PartnershipOfferRung.PARTNER,
)


class PartnershipMove(Enum):
    """The canon's partnership loop (synthesized ops/playbooks/partnership.md).

    The canon's partnership loop has four moves: retain, grow, refer and renew
    (synthesized ``ops/playbooks/partnership.md``), so the loop is an ordered
    cycle that keeps the client for the long term.
    """

    RETAIN = "retain"
    GROW = "grow"
    REFER = "refer"
    RENEW = "renew"


PARTNERSHIP_MOVE_ORDER: tuple[PartnershipMove, ...] = (
    PartnershipMove.RETAIN,
    PartnershipMove.GROW,
    PartnershipMove.REFER,
    PartnershipMove.RENEW,
)


class ReputationKind(Enum):
    """The canon's reputation track (synthesized ops/playbooks/partnership.md).

    The canon's partnership playbook says to "track reviews, stories, and press"
    (synthesized ``ops/playbooks/partnership.md``), so the reputation track covers
    all three kinds.
    """

    REVIEW = "review"
    STORY = "story"
    PRESS = "press"


REPUTATION_KINDS: tuple[ReputationKind, ...] = (
    ReputationKind.REVIEW,
    ReputationKind.STORY,
    ReputationKind.PRESS,
)


@dataclass(frozen=True)
class PartnershipOffer:
    """One offer on the canon's four-offer path (canon files 11 and 12).

    The canon slices the offer into a free entry, a small offer, a core offer and
    a partner offer, each leading to the next (synthesized
    ``ops/playbooks/partnership.md``). An offer names its rung and the offer
    itself. It is frozen and reject-only: a blank offer name or an untyped rung
    cannot be represented as part of the path.
    """

    rung: PartnershipOfferRung
    offer_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.rung, PartnershipOfferRung):
            raise InvalidPartnershipPlanError(
                "a partnership offer must name one of the canon rungs"
            )
        _require_blank_free("partnership offer name", self.offer_name)


@dataclass(frozen=True)
class PartnershipCheckIn:
    """A regular client check-in (synthesized ops/playbooks/partnership.md).

    The canon says to "hold regular check-ins" and to "keep a check-in rhythm"
    (synthesized ``ops/playbooks/partnership.md``). A check-in records the cadence
    in days and the owner who holds it, so the relationship has a rhythm and an
    accountable person rather than relying on memory.
    """

    cadence_days: int
    owner: str

    def __post_init__(self) -> None:
        if isinstance(self.cadence_days, bool) or not isinstance(
            self.cadence_days, int
        ):
            raise InvalidPartnershipPlanError(
                "a partnership check-in cadence must be a whole number of days"
            )
        if self.cadence_days < 1:
            raise InvalidPartnershipPlanError(
                "a partnership check-in cadence must be at least one day"
            )
        _require_blank_free("partnership check-in owner", self.owner)


@dataclass(frozen=True)
class ReferralPlan:
    """The canon's referral and partner plan (synthesized partnership playbook).

    The canon says to "ask happy clients for referrals" and to "ask after a win,
    not before", listing asking too early as a common failure (synthesized
    ``ops/playbooks/partnership.md``). A referral plan records that it asks after a
    win and names the partner offer it leads to, so the referral ask is tied to a
    result and to the next step.
    """

    ask_after_win: bool
    partner_offer_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.ask_after_win, bool):
            raise InvalidPartnershipPlanError(
                "a referral plan must state whether it asks after a win"
            )
        _require_blank_free("referral plan partner offer name", self.partner_offer_name)


@dataclass(frozen=True)
class CommunityRules:
    """The canon's community rules (synthesized ops/playbooks/partnership.md).

    The canon says to "build a community of clients" and to "start small and set
    simple rules" (synthesized ``ops/playbooks/partnership.md``). The rules are a
    non-empty, duplicate-free set of short rules, so the community has a simple,
    explicit standard.
    """

    rules: tuple[str, ...]

    def __post_init__(self) -> None:
        rules = tuple(self.rules)
        if not rules:
            raise InvalidPartnershipPlanError(
                "a partnership plan requires at least one community rule"
            )
        for rule in rules:
            _require_blank_free("community rule", rule)
        if len(set(rules)) != len(rules):
            raise PartnershipFormatError(
                "a partnership plan must carry simple, unique community rules"
            )


@dataclass(frozen=True)
class ReputationTrack:
    """The canon's reputation track (synthesized ops/playbooks/partnership.md).

    The canon says to "track reviews, stories, and press" (synthesized
    ``ops/playbooks/partnership.md``). The track covers all three canon kinds
    without repeats, so the reputation record is complete.
    """

    kinds: tuple[ReputationKind, ...]

    def __post_init__(self) -> None:
        kinds = tuple(self.kinds)
        if not kinds:
            raise InvalidPartnershipPlanError(
                "a partnership plan requires a reputation track"
            )
        for kind in kinds:
            if not isinstance(kind, ReputationKind):
                raise InvalidPartnershipPlanError(
                    "a reputation track must carry the canon reputation kinds"
                )
        if len(set(kinds)) != len(kinds):
            raise PartnershipFormatError(
                "a reputation track must not repeat a canon reputation kind"
            )
        if set(kinds) != set(REPUTATION_KINDS):
            raise PartnershipFormatError(
                "a reputation track must cover reviews, stories and press "
                "(synthesized ops/playbooks/partnership.md)"
            )


@dataclass(frozen=True)
class CertificationStandard:
    """The canon's certified consultant standard (synthesized certification docs).

    The canon keeps the standard short -- "a few clear skills, not a long list" --
    requires a clear exam pass mark and rechecks the standard every year
    (synthesized ``ops/playbooks/certification.md`` and
    ``ops/sops/certification-exam.md``). A standard carries a short, unique list of
    non-blank skills, a non-blank pass mark and the yearly recheck.
    """

    skills: tuple[str, ...]
    pass_mark: str
    recheck_days: int

    def __post_init__(self) -> None:
        skills = tuple(self.skills)
        if not skills:
            raise CertificationStandardError(
                "a certification standard requires at least one skill"
            )
        if len(skills) > MAX_CERTIFICATION_SKILLS:
            raise CertificationStandardError(
                "a certification standard must keep a short list of skills, at "
                f"most {MAX_CERTIFICATION_SKILLS} (synthesized "
                "ops/playbooks/certification.md)"
            )
        for skill in skills:
            if not isinstance(skill, str) or not skill.strip():
                raise CertificationStandardError(
                    "a certification standard skill must be a non-blank skill"
                )
        if len(set(skills)) != len(skills):
            raise CertificationStandardError(
                "a certification standard must not repeat a skill"
            )
        if not isinstance(self.pass_mark, str) or not self.pass_mark.strip():
            raise CertificationStandardError(
                "a certification standard requires a clear exam pass mark"
            )
        if isinstance(self.recheck_days, bool) or not isinstance(
            self.recheck_days, int
        ):
            raise CertificationStandardError(
                "a certification standard recheck must be a whole number of days"
            )
        if self.recheck_days != CERTIFICATION_RECHECK_DAYS:
            raise CertificationStandardError(
                "a certification standard must be rechecked every year "
                f"({CERTIFICATION_RECHECK_DAYS} days), not {self.recheck_days}"
            )


@dataclass(frozen=True)
class CertifiedOperator:
    """One operator put forward for certification (synthesized certification docs).

    The canon's proof rule is "certify only after a real result. No result, no
    badge", and each certified person must pass the exam (synthesized
    ``ops/playbooks/certification.md``). An operator records their name, whether
    they hold a real result and whether they passed the exam, so the plan can
    refuse a certification the canon does not allow.
    """

    name: str
    has_real_result: bool
    passed_exam: bool

    def __post_init__(self) -> None:
        _require_blank_free("certified operator name", self.name)
        if not isinstance(self.has_real_result, bool) or not isinstance(
            self.passed_exam, bool
        ):
            raise InvalidPartnershipPlanError(
                "a certified operator must state their result and exam outcome"
            )


@dataclass(frozen=True)
class PartnershipPlan:
    """The canon partnership line and certification (SPEC.md section 12.5, G6).

    The plan binds a named owner to a same-tenant stage 5 ``ProductProgram``, the
    canon four-offer path, the partnership loop, a regular check-in, a referral
    plan, community rules, a reputation track and a certification standard. It is
    the typed form of the client's retention and expansion path, the next step
    after the delivery ladder (G5).

    It is frozen and reject-only, so the canon's shape cannot be bypassed: the
    offers must be the four canon rungs in order, the moves must be the four canon
    moves in order, the referral plan must ask after a win and name the partner
    offer, the community rules must be simple and unique, the reputation track must
    cover reviews, stories and press, and the certification standard must be short
    with a yearly recheck. It is a post-launch planning asset, not a required gate
    kind, and it does not authorize sending, spend, publishing or any client
    commitment (SPEC.md sections 4 and 9). It is never an observation (SPEC.md
    section 3).
    """

    plan_id: str
    tenant_id: str
    owner: str
    program: ProductProgram
    offers: tuple[PartnershipOffer, ...]
    moves: tuple[PartnershipMove, ...]
    check_in: PartnershipCheckIn
    referral_plan: ReferralPlan
    community_rules: CommunityRules
    reputation_track: ReputationTrack
    certification: CertificationStandard
    created_on: date

    def __post_init__(self) -> None:
        for label, value in (
            ("partnership plan id", self.plan_id),
            ("partnership plan tenant id", self.tenant_id),
            ("partnership plan owner", self.owner),
        ):
            _require_blank_free(label, value)
        if not isinstance(self.created_on, date):
            raise InvalidPartnershipPlanError(
                "a partnership plan requires a creation date"
            )
        self._require_grounding()
        self._require_offers()
        self._require_moves()
        self._require_check_in()
        self._require_referral_plan()
        self._require_community_rules()
        self._require_reputation_track()
        self._require_certification()

    def _require_grounding(self) -> None:
        if not isinstance(self.program, ProductProgram):
            raise PartnershipDependencyError(
                "a partnership plan must be grounded on a typed stage 5 Product "
                "Program"
            )
        if self.program.tenant_id != self.tenant_id:
            raise PartnershipTenantBoundaryError(
                f"partnership plan {self.plan_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its Product Program "
                f"{self.program.program_id!r} belongs to tenant "
                f"{self.program.tenant_id!r}"
            )

    def _require_offers(self) -> None:
        offers = tuple(self.offers)
        if not offers:
            raise InvalidPartnershipPlanError(
                "a partnership plan requires the canon four-offer path"
            )
        for item in offers:
            if not isinstance(item, PartnershipOffer):
                raise InvalidPartnershipPlanError(
                    "a partnership plan offer must be a typed partnership offer"
                )
        rungs = tuple(item.rung for item in offers)
        if rungs != PARTNERSHIP_OFFER_ORDER:
            raise PartnershipFormatError(
                "a partnership plan must carry the canon four-offer path -- entry, "
                "mid, core and partner -- in order, without repeats (canon files "
                "11 and 12; synthesized ops/playbooks/partnership.md)"
            )

    def _require_moves(self) -> None:
        moves = tuple(self.moves)
        if not moves:
            raise InvalidPartnershipPlanError(
                "a partnership plan requires the canon partnership loop"
            )
        for move in moves:
            if not isinstance(move, PartnershipMove):
                raise InvalidPartnershipPlanError(
                    "a partnership plan move must be one of the canon moves"
                )
        if moves != PARTNERSHIP_MOVE_ORDER:
            raise PartnershipFormatError(
                "a partnership plan must carry the canon partnership loop -- "
                "retain, grow, refer and renew -- in order, without repeats "
                "(synthesized ops/playbooks/partnership.md)"
            )

    def _require_check_in(self) -> None:
        if not isinstance(self.check_in, PartnershipCheckIn):
            raise InvalidPartnershipPlanError(
                "a partnership plan requires a typed regular check-in"
            )

    def _require_referral_plan(self) -> None:
        if not isinstance(self.referral_plan, ReferralPlan):
            raise InvalidPartnershipPlanError(
                "a partnership plan requires a typed referral plan"
            )
        if not self.referral_plan.ask_after_win:
            raise PartnershipGateError(
                f"partnership plan {self.plan_id!r} asks for referrals before a "
                "win; the canon asks after a win, not before (synthesized "
                "ops/playbooks/partnership.md)"
            )
        partner = self.next_offer
        if self.referral_plan.partner_offer_name != partner.offer_name:
            raise PartnershipDependencyError(
                f"partnership plan {self.plan_id!r} referral plan names partner "
                f"offer {self.referral_plan.partner_offer_name!r}, but the plan's "
                f"partner offer is {partner.offer_name!r}"
            )

    def _require_community_rules(self) -> None:
        if not isinstance(self.community_rules, CommunityRules):
            raise InvalidPartnershipPlanError(
                "a partnership plan requires typed community rules"
            )

    def _require_reputation_track(self) -> None:
        if not isinstance(self.reputation_track, ReputationTrack):
            raise InvalidPartnershipPlanError(
                "a partnership plan requires a typed reputation track"
            )

    def _require_certification(self) -> None:
        if not isinstance(self.certification, CertificationStandard):
            raise InvalidPartnershipPlanError(
                "a partnership plan requires a typed certification standard"
            )

    @property
    def canon_reference(self) -> str:
        """The canon file block whose structure shaped this artifact."""
        return PARTNERSHIP_CANON_REFERENCE

    @property
    def offer_rungs(self) -> tuple[PartnershipOfferRung, ...]:
        """The canon four-offer path the plan carries, in order."""
        return tuple(item.rung for item in self.offers)

    @property
    def next_offer(self) -> PartnershipOffer:
        """The partner offer, the client's next step on the four-offer path."""
        for item in self.offers:
            if item.rung is PartnershipOfferRung.PARTNER:
                return item
        raise PartnershipDependencyError(
            f"partnership plan {self.plan_id!r} has no partner offer"
        )

    @property
    def has_next_step(self) -> bool:
        """The canon gate: every client has a next step."""
        return any(
            item.rung is PartnershipOfferRung.PARTNER for item in self.offers
        )

    @property
    def reason_to_stay(self) -> bool:
        """The canon gate: every client has a reason to stay (renewal)."""
        return PartnershipMove.RENEW in self.moves

    @property
    def is_post_launch(self) -> bool:
        """The canon runs partnership in the Grow and Partner stages, after delivery."""
        return True

    @property
    def is_plan(self) -> bool:
        """A partnership plan is a plan, not activity or an observed result."""
        return True

    def certify(self, operator: CertifiedOperator) -> None:
        """Certify an operator only after a real result and a passed exam.

        The canon's proof rule is "certify only after a real result. No result, no
        badge", and each certified person must pass the exam (synthesized
        ``ops/playbooks/certification.md``). An untyped operator, an operator with
        no real result or an operator who did not pass the exam is refused with
        ``CertificationProofError``, so the register cannot claim a certification
        the canon does not allow.
        """
        if not isinstance(operator, CertifiedOperator):
            raise CertificationProofError(
                "a certification requires a typed certified operator"
            )
        if not operator.has_real_result:
            raise CertificationProofError(
                f"operator {operator.name!r} has no real result; the canon certifies "
                "only after a real result (synthesized ops/playbooks/certification.md)"
            )
        if not operator.passed_exam:
            raise CertificationProofError(
                f"operator {operator.name!r} did not pass the exam; the canon "
                "certifies only the people who pass (synthesized "
                "ops/playbooks/certification.md)"
            )

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a partnership plan as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The plan
        describes the retention and expansion the client will run, while any
        renewal, referral or review stays a separate observation, so a plan is
        never an observation.
        """
        raise PartnershipObservationError(
            f"partnership plan {claim_id!r} is a retention and expansion plan, not "
            "an observed result, and cannot be recorded as an observation"
        )

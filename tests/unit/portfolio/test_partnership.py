"""Behavioral tests for the canon partnership line and certification (Portfolio).

Rules under test come from the canon's partnership and certification material and
the implementation plan's canon gap backlog item G6 (SPEC.md section 12.5 records
the partnership line and certification as a canon gap; the backlog names "typed
artifacts with tests; every client has a next step; human decision for any
commitment"). The shape is extracted from:

- Canon files 11 and 12, the Certification series, Live Sessions 5 and 12 and
  High Ticket Funnels 19: the four-offer path (a free entry, a small offer, a core
  offer and a partner offer, each leading to the next) and the partnership loop
  (retain, grow, refer, renew).
- Synthesized `ops/playbooks/partnership.md`: regular check-ins, the gate ("every
  client has a next step and a reason to stay"), asking for referrals after a win
  and not before, a community with simple rules, and tracking reviews, stories and
  press.
- Synthesized `ops/playbooks/certification.md` and `ops/sops/certification-exam.md`:
  a short standard of a few clear skills, an exam with a clear pass mark, the proof
  rule ("certify only after a real result. No result, no badge"), a register of
  certified people and a yearly recheck of the standard.

The plan is a post-launch Portfolio planning asset, not a new required gate kind.
It does not authorize sending, spend, publishing or any client commitment (SPEC.md
sections 4 and 9) and it is never an observation (SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

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
from redops.contexts.portfolio.domain.partnership import (
    CERTIFICATION_RECHECK_DAYS,
    MAX_CERTIFICATION_SKILLS,
    PARTNERSHIP_CANON_REFERENCE,
    PARTNERSHIP_MOVE_ORDER,
    PARTNERSHIP_OFFER_ORDER,
    REPUTATION_KINDS,
    CertifiedOperator,
    CertificationStandard,
    CommunityRules,
    PartnershipCheckIn,
    PartnershipMove,
    PartnershipOffer,
    PartnershipOfferRung,
    PartnershipPlan,
    ReferralPlan,
    ReputationKind,
    ReputationTrack,
)

from ..commercial.fixtures import product_program
from ..method.fixtures import TENANT, signature_solution

OTHER_TENANT = "client-other"
CREATED = date(2026, 10, 2)


def offer(rung: PartnershipOfferRung, **overrides) -> PartnershipOffer:
    values = {
        "rung": rung,
        "offer_name": f"the {getattr(rung, 'value', rung)} offer",
    }
    values.update(overrides)
    return PartnershipOffer(**values)


def offers() -> tuple[PartnershipOffer, ...]:
    return tuple(offer(rung) for rung in PARTNERSHIP_OFFER_ORDER)


def check_in(**overrides) -> PartnershipCheckIn:
    values = {"cadence_days": 30, "owner": "red-partnership-lead"}
    values.update(overrides)
    return PartnershipCheckIn(**values)


def referral(**overrides) -> ReferralPlan:
    values = {
        "ask_after_win": True,
        "partner_offer_name": "the partner offer",
    }
    values.update(overrides)
    return ReferralPlan(**values)


def community(**overrides) -> CommunityRules:
    values = {"rules": ("be kind", "no pitching")}
    values.update(overrides)
    return CommunityRules(**values)


def reputation(**overrides) -> ReputationTrack:
    values = {"kinds": REPUTATION_KINDS}
    values.update(overrides)
    return ReputationTrack(**values)


def standard(**overrides) -> CertificationStandard:
    values = {
        "skills": (
            "explain the one currency and message",
            "build the funnel and the pages",
            "run the enrollment call with the checkpoints",
            "read the numbers and fix the weak step",
        ),
        "pass_mark": "80 percent",
        "recheck_days": CERTIFICATION_RECHECK_DAYS,
    }
    values.update(overrides)
    return CertificationStandard(**values)


def operator(**overrides) -> CertifiedOperator:
    values = {
        "name": "client-operator-1",
        "has_real_result": True,
        "passed_exam": True,
    }
    values.update(overrides)
    return CertifiedOperator(**values)


def plan(**overrides) -> PartnershipPlan:
    program = overrides.pop("program", None)
    if program is None:
        program = product_program()
    tenant_id = overrides.pop("tenant_id", None)
    if tenant_id is None:
        tenant_id = getattr(program, "tenant_id", TENANT)
    values = {
        "plan_id": "partnership-3f",
        "tenant_id": tenant_id,
        "owner": "red-partnership-lead",
        "program": program,
        "offers": offers(),
        "moves": PARTNERSHIP_MOVE_ORDER,
        "check_in": check_in(),
        "referral_plan": referral(),
        "community_rules": community(),
        "reputation_track": reputation(),
        "certification": standard(),
        "created_on": CREATED,
    }
    values.update(overrides)
    return PartnershipPlan(**values)


class PartnershipOfferTests(unittest.TestCase):
    def test_the_canon_four_offer_path_has_four_rungs_in_order(self):
        self.assertEqual(
            (
                PartnershipOfferRung.ENTRY,
                PartnershipOfferRung.MID,
                PartnershipOfferRung.CORE,
                PartnershipOfferRung.PARTNER,
            ),
            PARTNERSHIP_OFFER_ORDER,
        )

    def test_a_plan_accepts_the_canon_four_offer_path(self):
        self.assertEqual(PARTNERSHIP_OFFER_ORDER, plan().offer_rungs)

    def test_a_plan_refuses_a_missing_offer_rung(self):
        with self.assertRaises(PartnershipFormatError):
            plan(offers=offers()[:-1])

    def test_a_plan_refuses_out_of_order_offers(self):
        broken = (
            offer(PartnershipOfferRung.ENTRY),
            offer(PartnershipOfferRung.CORE),
            offer(PartnershipOfferRung.MID),
            offer(PartnershipOfferRung.PARTNER),
        )
        with self.assertRaises(PartnershipFormatError):
            plan(offers=broken)

    def test_a_plan_refuses_duplicate_offer_rungs(self):
        broken = (
            offer(PartnershipOfferRung.ENTRY),
            offer(PartnershipOfferRung.ENTRY),
            offer(PartnershipOfferRung.CORE),
            offer(PartnershipOfferRung.PARTNER),
        )
        with self.assertRaises(PartnershipFormatError):
            plan(offers=broken)

    def test_a_plan_requires_at_least_one_offer(self):
        with self.assertRaises(InvalidPartnershipPlanError):
            plan(offers=())

    def test_a_plan_requires_a_typed_offer(self):
        with self.assertRaises(InvalidPartnershipPlanError):
            plan(offers=("entry",))

    def test_an_offer_requires_a_typed_rung(self):
        with self.assertRaises(InvalidPartnershipPlanError):
            offer("entry")

    def test_an_offer_requires_a_name(self):
        with self.assertRaises(InvalidPartnershipPlanError):
            offer(PartnershipOfferRung.ENTRY, offer_name="  ")


class PartnershipMoveTests(unittest.TestCase):
    def test_the_canon_partnership_loop_has_four_moves_in_order(self):
        self.assertEqual(
            (
                PartnershipMove.RETAIN,
                PartnershipMove.GROW,
                PartnershipMove.REFER,
                PartnershipMove.RENEW,
            ),
            PARTNERSHIP_MOVE_ORDER,
        )

    def test_a_plan_accepts_the_canon_partnership_loop(self):
        self.assertEqual(PARTNERSHIP_MOVE_ORDER, plan().moves)

    def test_a_plan_refuses_a_missing_move(self):
        with self.assertRaises(PartnershipFormatError):
            plan(moves=PARTNERSHIP_MOVE_ORDER[:-1])

    def test_a_plan_refuses_out_of_order_moves(self):
        broken = (
            PartnershipMove.RETAIN,
            PartnershipMove.REFER,
            PartnershipMove.GROW,
            PartnershipMove.RENEW,
        )
        with self.assertRaises(PartnershipFormatError):
            plan(moves=broken)

    def test_a_plan_refuses_duplicate_moves(self):
        broken = (
            PartnershipMove.RETAIN,
            PartnershipMove.RETAIN,
            PartnershipMove.REFER,
            PartnershipMove.RENEW,
        )
        with self.assertRaises(PartnershipFormatError):
            plan(moves=broken)

    def test_a_plan_requires_a_typed_move(self):
        with self.assertRaises(InvalidPartnershipPlanError):
            plan(moves=("retain",))


class PartnershipCheckInTests(unittest.TestCase):
    def test_a_plan_requires_a_regular_check_in(self):
        self.assertEqual(30, plan().check_in.cadence_days)

    def test_a_plan_refuses_a_non_positive_check_in_cadence(self):
        with self.assertRaises(InvalidPartnershipPlanError):
            check_in(cadence_days=0)

    def test_a_plan_refuses_a_blank_check_in_owner(self):
        with self.assertRaises(InvalidPartnershipPlanError):
            check_in(owner="  ")

    def test_a_plan_requires_a_typed_check_in(self):
        with self.assertRaises(InvalidPartnershipPlanError):
            plan(check_in="monthly")


class ReferralPlanTests(unittest.TestCase):
    def test_a_plan_requires_a_referral_plan(self):
        self.assertTrue(plan().referral_plan.ask_after_win)

    def test_a_plan_refuses_asking_for_referrals_before_a_win(self):
        with self.assertRaises(PartnershipGateError):
            plan(referral_plan=referral(ask_after_win=False))

    def test_a_plan_refuses_a_referral_plan_for_an_unknown_partner_offer(self):
        with self.assertRaises(PartnershipDependencyError):
            plan(referral_plan=referral(partner_offer_name="some other offer"))

    def test_a_plan_requires_a_typed_referral_plan(self):
        with self.assertRaises(InvalidPartnershipPlanError):
            plan(referral_plan="referrals")


class CommunityRulesTests(unittest.TestCase):
    def test_a_plan_requires_community_rules(self):
        self.assertEqual(("be kind", "no pitching"), plan().community_rules.rules)

    def test_a_plan_refuses_empty_community_rules(self):
        with self.assertRaises(InvalidPartnershipPlanError):
            community(rules=())

    def test_a_plan_refuses_a_blank_community_rule(self):
        with self.assertRaises(InvalidPartnershipPlanError):
            community(rules=("be kind", "  "))

    def test_a_plan_refuses_duplicate_community_rules(self):
        with self.assertRaises(PartnershipFormatError):
            community(rules=("be kind", "be kind"))

    def test_a_plan_requires_a_typed_community_rules(self):
        with self.assertRaises(InvalidPartnershipPlanError):
            plan(community_rules=("be kind",))


class ReputationTrackTests(unittest.TestCase):
    def test_the_canon_reputation_track_covers_reviews_stories_and_press(self):
        self.assertEqual(
            (
                ReputationKind.REVIEW,
                ReputationKind.STORY,
                ReputationKind.PRESS,
            ),
            REPUTATION_KINDS,
        )

    def test_a_plan_requires_the_canon_reputation_track(self):
        self.assertEqual(REPUTATION_KINDS, plan().reputation_track.kinds)

    def test_a_plan_refuses_a_reputation_track_missing_a_canon_kind(self):
        with self.assertRaises(PartnershipFormatError):
            plan(reputation_track=reputation(kinds=(ReputationKind.REVIEW,)))

    def test_a_plan_refuses_duplicate_reputation_kinds(self):
        with self.assertRaises(PartnershipFormatError):
            reputation(
                kinds=(
                    ReputationKind.REVIEW,
                    ReputationKind.REVIEW,
                    ReputationKind.STORY,
                    ReputationKind.PRESS,
                )
            )

    def test_a_plan_requires_a_typed_reputation_track(self):
        with self.assertRaises(InvalidPartnershipPlanError):
            plan(reputation_track=("review",))


class CertificationStandardTests(unittest.TestCase):
    def test_the_canon_rechecks_the_standard_every_year(self):
        self.assertEqual(365, CERTIFICATION_RECHECK_DAYS)
        self.assertEqual(365, plan().certification.recheck_days)

    def test_a_standard_refuses_a_recheck_off_the_yearly_cadence(self):
        with self.assertRaises(CertificationStandardError):
            standard(recheck_days=30)

    def test_a_standard_requires_a_short_list_of_skills(self):
        self.assertEqual(4, len(plan().certification.skills))
        too_many = tuple(f"skill {index}" for index in range(MAX_CERTIFICATION_SKILLS + 1))
        with self.assertRaises(CertificationStandardError):
            standard(skills=too_many)

    def test_a_standard_requires_at_least_one_skill(self):
        with self.assertRaises(CertificationStandardError):
            standard(skills=())

    def test_a_standard_refuses_a_blank_skill(self):
        with self.assertRaises(CertificationStandardError):
            standard(skills=("explain the currency", "  "))

    def test_a_standard_requires_a_pass_mark(self):
        with self.assertRaises(CertificationStandardError):
            standard(pass_mark="  ")

    def test_a_plan_requires_a_typed_certification_standard(self):
        with self.assertRaises(InvalidPartnershipPlanError):
            plan(certification="standard")


class CertificationProofTests(unittest.TestCase):
    def test_certify_accepts_an_operator_with_a_real_result_and_a_pass(self):
        plan().certify(operator())

    def test_certify_refuses_an_operator_without_a_real_result(self):
        with self.assertRaises(CertificationProofError):
            plan().certify(operator(has_real_result=False))

    def test_certify_refuses_an_operator_who_did_not_pass_the_exam(self):
        with self.assertRaises(CertificationProofError):
            plan().certify(operator(passed_exam=False))

    def test_certify_requires_a_typed_operator(self):
        with self.assertRaises(CertificationProofError):
            plan().certify("operator")


class PartnershipPlanGroundingTests(unittest.TestCase):
    def test_a_plan_grounds_on_a_same_tenant_program(self):
        self.assertEqual("program-3f", plan().program.program_id)

    def test_a_plan_refuses_a_program_from_another_tenant(self):
        foreign = product_program(solution=signature_solution(OTHER_TENANT))
        with self.assertRaises(PartnershipTenantBoundaryError):
            plan(program=foreign, tenant_id=TENANT)

    def test_a_plan_requires_a_typed_program(self):
        with self.assertRaises(PartnershipDependencyError):
            plan(program="program")

    def test_a_plan_requires_identity(self):
        for field in ("plan_id", "tenant_id", "owner"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidPartnershipPlanError):
                    plan(**{field: "  "})

    def test_a_plan_requires_a_creation_date(self):
        with self.assertRaises(InvalidPartnershipPlanError):
            plan(created_on="2026-10-02")


class PartnershipPlanShapeTests(unittest.TestCase):
    def test_a_plan_has_a_next_step_and_a_reason_to_stay(self):
        built = plan()
        self.assertTrue(built.has_next_step)
        self.assertTrue(built.reason_to_stay)
        self.assertEqual(PartnershipOfferRung.PARTNER, built.next_offer.rung)

    def test_a_plan_is_a_plan_not_an_observation(self):
        built = plan()
        self.assertTrue(built.is_plan)
        with self.assertRaises(PartnershipObservationError):
            built.as_observation(claim_id="claim-1")

    def test_a_plan_is_frozen(self):
        built = plan()
        with self.assertRaises(FrozenInstanceError):
            built.owner = "someone-else"

    def test_a_plan_reports_its_canon_reference_and_post_launch_stage(self):
        built = plan()
        self.assertEqual(PARTNERSHIP_CANON_REFERENCE, built.canon_reference)
        self.assertTrue(built.is_post_launch)


if __name__ == "__main__":
    unittest.main()

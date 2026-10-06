"""Behavioral tests for the canon service line (Operations).

Rules under test come from the canon's service-ops map and the implementation
plan's canon gap backlog item G7 (SPEC.md section 12.5 records the service-line
artifacts as a canon gap; the backlog names "typed artifact with tests; case
study claim refuses an unapproved or unsourced testimonial"). The shape is
extracted from:

- ``internal/service-ops.md``: the service line is onboard, deliver, track,
  prove; the gate is "results are measured against the goals set at kickoff".
- Synthesized ``ops/checklists/kickoff.md``: a named delivery lead, a welcome
  within one business day, success goals written as a number and a date, a start
  date, collected access, a shared one-page plan and a first module on the
  calendar.
- Synthesized ``ops/checklists/module-production.md``: the module goal and the
  one currency, and the outline-to-publish steps.
- Synthesized ``ops/checklists/session-guide.md``: the session goal, one idea,
  one example, a task, and the next step and date.
- Synthesized ``ops/checklists/client-scorecard.md``: the four things watched
  (attendance, progress, results, risk) and a risk that carries an action.
- Synthesized ``ops/checklists/case-study.md`` and ``ops/sops/case-study-capture.md``:
  a real measured result, written permission, an approved quote, and a version
  scoped, client-approved story. SPEC.md sections 1 and 4 forbid an unreviewed
  testimonial or performance claim and scope client-approved information to a
  version and intended use.

The service line is a post-launch Operations planning asset, not a new required
gate kind. It does not authorize sending, spend, publishing or any client
commitment (SPEC.md sections 4 and 9) and it is never an observation (SPEC.md
section 3).
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

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
from redops.contexts.operations.domain.service_line import (
    SCORECARD_DIMENSIONS,
    SERVICE_LINE_CANON_REFERENCE,
    WELCOME_WITHIN_DAYS,
    CaseStudy,
    CaseStudyClaim,
    ClientScorecard,
    KickoffChecklist,
    ModuleProductionStandard,
    RiskKind,
    ScorecardDimension,
    ScorecardRisk,
    ServiceLine,
    SessionGuide,
    SuccessGoal,
)

from ..commercial.fixtures import product_program
from ..method.fixtures import TENANT, signature_solution

OTHER_TENANT = "client-other"
CREATED = date(2026, 10, 2)


def goal(**overrides) -> SuccessGoal:
    values = {
        "description": "book qualified calls",
        "target": "20 calls a week",
        "due_on": date(2026, 12, 1),
    }
    values.update(overrides)
    return SuccessGoal(**values)


def kickoff(**overrides) -> KickoffChecklist:
    values = {
        "delivery_lead": "red-delivery-lead",
        "welcome_within_days": WELCOME_WITHIN_DAYS,
        "goals": (goal(),),
        "start_on": date(2026, 10, 6),
        "access": frozenset({"ad account", "calendar", "email", "site"}),
        "plan_shared": True,
        "first_module_on": date(2026, 10, 13),
    }
    values.update(overrides)
    return KickoffChecklist(**values)


def module_standard(**overrides) -> ModuleProductionStandard:
    values = {
        "module_goal": "the client can run the diagnose module",
        "currency": "qualified calls",
        "steps": ("outline", "script", "slides", "record", "edit", "publish"),
    }
    values.update(overrides)
    return ModuleProductionStandard(**values)


def session_guide(**overrides) -> SessionGuide:
    values = {
        "session_goal": "the client can write the offer",
        "one_idea": "price on outcomes",
        "example": "the 3F offer",
        "task": "draft the offer page",
        "next_step": "review the offer page",
        "next_on": date(2026, 10, 20),
    }
    values.update(overrides)
    return SessionGuide(**values)


def risk(**overrides) -> ScorecardRisk:
    values = {"kind": RiskKind.QUIET, "action": "send a check-in note"}
    values.update(overrides)
    return ScorecardRisk(**values)


def scorecard(**overrides) -> ClientScorecard:
    values = {
        "dimensions": SCORECARD_DIMENSIONS,
        "risks": (risk(),),
        "shared_with_lead": True,
    }
    values.update(overrides)
    return ClientScorecard(**values)


def case_study(**overrides) -> CaseStudy:
    values = {
        "study_id": "case-3f",
        "tenant_id": TENANT,
        "client_name": "3F",
        "result_measured": True,
        "start_numbers": "0 calls a week",
        "end_numbers": "20 calls a week",
        "quote": "we finally know who to talk to",
        "quote_approved": True,
        "written_permission": True,
        "approved_version": "v1",
        "intended_use": "3f pilot case study",
        "published": True,
    }
    values.update(overrides)
    return CaseStudy(**values)


def service_line(**overrides) -> ServiceLine:
    program = overrides.pop("program", None)
    if program is None:
        program = product_program()
    tenant_id = overrides.pop("tenant_id", None)
    if tenant_id is None:
        tenant_id = getattr(program, "tenant_id", TENANT)
    values = {
        "service_line_id": "service-3f",
        "tenant_id": tenant_id,
        "owner": "red-service-owner",
        "program": program,
        "kickoff": kickoff(),
        "module_standard": module_standard(),
        "session_guide": session_guide(),
        "scorecard": scorecard(),
        "case_study": case_study(),
        "created_on": CREATED,
    }
    values.update(overrides)
    return ServiceLine(**values)


class KickoffChecklistTests(unittest.TestCase):
    def test_a_kickoff_names_a_delivery_lead(self):
        self.assertEqual("red-delivery-lead", kickoff().delivery_lead)

    def test_a_kickoff_refuses_a_blank_delivery_lead(self):
        with self.assertRaises(InvalidServiceLineError):
            kickoff(delivery_lead="  ")

    def test_a_kickoff_welcomes_within_one_business_day(self):
        self.assertEqual(1, WELCOME_WITHIN_DAYS)
        self.assertEqual(1, kickoff().welcome_within_days)

    def test_a_kickoff_refuses_a_late_welcome(self):
        with self.assertRaises(ServiceLineFormatError):
            kickoff(welcome_within_days=3)

    def test_a_kickoff_requires_at_least_one_goal(self):
        with self.assertRaises(InvalidServiceLineError):
            kickoff(goals=())

    def test_a_kickoff_requires_a_typed_goal(self):
        with self.assertRaises(InvalidServiceLineError):
            kickoff(goals=("book calls",))

    def test_a_goal_is_written_as_a_number_and_a_date(self):
        built = goal()
        self.assertEqual("20 calls a week", built.target)
        self.assertEqual(date(2026, 12, 1), built.due_on)

    def test_a_goal_refuses_a_blank_target(self):
        with self.assertRaises(InvalidServiceLineError):
            goal(target="  ")

    def test_a_goal_refuses_a_missing_date(self):
        with self.assertRaises(InvalidServiceLineError):
            goal(due_on="2026-12-01")

    def test_a_kickoff_requires_collected_access(self):
        with self.assertRaises(InvalidServiceLineError):
            kickoff(access=frozenset())

    def test_a_kickoff_refuses_blank_access(self):
        with self.assertRaises(InvalidServiceLineError):
            kickoff(access=frozenset({"ad account", "  "}))

    def test_a_kickoff_requires_a_shared_plan(self):
        with self.assertRaises(ServiceLineGateError):
            kickoff(plan_shared=False)

    def test_a_kickoff_requires_a_start_date(self):
        with self.assertRaises(InvalidServiceLineError):
            kickoff(start_on="2026-10-06")

    def test_a_kickoff_requires_the_first_module_on_or_after_the_start(self):
        with self.assertRaises(ServiceLineFormatError):
            kickoff(start_on=date(2026, 10, 6), first_module_on=date(2026, 10, 1))


class ModuleProductionStandardTests(unittest.TestCase):
    def test_a_module_standard_names_its_goal_and_currency(self):
        built = module_standard()
        self.assertEqual("the client can run the diagnose module", built.module_goal)
        self.assertEqual("qualified calls", built.currency)

    def test_a_module_standard_refuses_a_blank_goal(self):
        with self.assertRaises(InvalidServiceLineError):
            module_standard(module_goal="  ")

    def test_a_module_standard_refuses_a_blank_currency(self):
        with self.assertRaises(InvalidServiceLineError):
            module_standard(currency="  ")

    def test_a_module_standard_requires_ordered_steps(self):
        self.assertEqual(
            ("outline", "script", "slides", "record", "edit", "publish"),
            module_standard().steps,
        )

    def test_a_module_standard_refuses_empty_steps(self):
        with self.assertRaises(InvalidServiceLineError):
            module_standard(steps=())

    def test_a_module_standard_refuses_duplicate_steps(self):
        with self.assertRaises(ServiceLineFormatError):
            module_standard(steps=("outline", "outline"))

    def test_a_module_standard_refuses_a_blank_step(self):
        with self.assertRaises(InvalidServiceLineError):
            module_standard(steps=("outline", "  "))

    def test_a_module_standard_confirms_the_done_criteria(self):
        module_standard().confirm(
            script_matches_slides=True, on_brand=True, published=True
        )

    def test_a_module_standard_refuses_an_unmet_done_criterion(self):
        for field in ("script_matches_slides", "on_brand", "published"):
            with self.subTest(field=field):
                criteria = {
                    "script_matches_slides": True,
                    "on_brand": True,
                    "published": True,
                }
                criteria[field] = False
                with self.assertRaises(ServiceLineGateError):
                    module_standard().confirm(**criteria)


class SessionGuideTests(unittest.TestCase):
    def test_a_session_guide_names_the_goal_idea_example_and_task(self):
        built = session_guide()
        self.assertEqual("the client can write the offer", built.session_goal)
        self.assertEqual("price on outcomes", built.one_idea)
        self.assertEqual("the 3F offer", built.example)
        self.assertEqual("draft the offer page", built.task)

    def test_a_session_guide_names_the_next_step_and_date(self):
        built = session_guide()
        self.assertEqual("review the offer page", built.next_step)
        self.assertEqual(date(2026, 10, 20), built.next_on)

    def test_a_session_guide_requires_every_field(self):
        for field in (
            "session_goal",
            "one_idea",
            "example",
            "task",
            "next_step",
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidServiceLineError):
                    session_guide(**{field: "  "})

    def test_a_session_guide_requires_a_next_date(self):
        with self.assertRaises(InvalidServiceLineError):
            session_guide(next_on="2026-10-20")


class ClientScorecardTests(unittest.TestCase):
    def test_the_scorecard_watches_four_things_in_order(self):
        self.assertEqual(
            (
                ScorecardDimension.ATTENDANCE,
                ScorecardDimension.PROGRESS,
                ScorecardDimension.RESULTS,
                ScorecardDimension.RISK,
            ),
            SCORECARD_DIMENSIONS,
        )
        self.assertEqual(SCORECARD_DIMENSIONS, scorecard().dimensions)

    def test_a_scorecard_refuses_a_missing_dimension(self):
        with self.assertRaises(ServiceLineFormatError):
            scorecard(dimensions=SCORECARD_DIMENSIONS[:-1])

    def test_a_scorecard_refuses_out_of_order_dimensions(self):
        broken = (
            ScorecardDimension.PROGRESS,
            ScorecardDimension.ATTENDANCE,
            ScorecardDimension.RESULTS,
            ScorecardDimension.RISK,
        )
        with self.assertRaises(ServiceLineFormatError):
            scorecard(dimensions=broken)

    def test_a_scorecard_refuses_duplicate_dimensions(self):
        broken = (
            ScorecardDimension.ATTENDANCE,
            ScorecardDimension.ATTENDANCE,
            ScorecardDimension.RESULTS,
            ScorecardDimension.RISK,
        )
        with self.assertRaises(ServiceLineFormatError):
            scorecard(dimensions=broken)

    def test_a_scorecard_requires_a_typed_dimension(self):
        with self.assertRaises(InvalidServiceLineError):
            scorecard(dimensions=("attendance",))

    def test_a_scorecard_risk_carries_an_action(self):
        self.assertEqual("send a check-in note", risk().action)

    def test_a_scorecard_risk_requires_a_typed_kind(self):
        with self.assertRaises(InvalidServiceLineError):
            risk(kind="quiet")

    def test_a_scorecard_risk_requires_an_action(self):
        with self.assertRaises(InvalidServiceLineError):
            risk(action="  ")

    def test_a_scorecard_requires_a_typed_risk(self):
        with self.assertRaises(InvalidServiceLineError):
            scorecard(risks=("quiet",))

    def test_a_scorecard_requires_being_shared_with_the_lead(self):
        with self.assertRaises(ServiceLineGateError):
            scorecard(shared_with_lead=False)


class CaseStudyTests(unittest.TestCase):
    def test_a_case_study_claim_returns_the_version_scoped_proof(self):
        claim = case_study().claim()
        self.assertIsInstance(claim, CaseStudyClaim)
        self.assertEqual("v1", claim.approved_version)
        self.assertEqual("3f pilot case study", claim.intended_use)
        self.assertEqual("case-3f", claim.study_id)

    def test_a_case_study_refuses_an_unsourced_result(self):
        with self.assertRaises(CaseStudyProofError):
            case_study(result_measured=False).claim()

    def test_a_case_study_refuses_missing_numbers(self):
        with self.assertRaises(CaseStudyProofError):
            case_study(start_numbers="  ").claim()

    def test_a_case_study_refuses_an_unapproved_testimonial(self):
        with self.assertRaises(CaseStudyAuthorityError):
            case_study(written_permission=False).claim()

    def test_a_case_study_refuses_an_unapproved_quote(self):
        with self.assertRaises(CaseStudyAuthorityError):
            case_study(quote_approved=False).claim()

    def test_a_case_study_refuses_an_unversioned_claim(self):
        with self.assertRaises(CaseStudyVersionError):
            case_study(approved_version="  ").claim()

    def test_a_case_study_refuses_a_claim_without_an_intended_use(self):
        with self.assertRaises(CaseStudyVersionError):
            case_study(intended_use="  ").claim()

    def test_a_case_study_requires_identity_and_content(self):
        for field in ("study_id", "tenant_id", "client_name", "quote"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidServiceLineError):
                    case_study(**{field: "  "})

    def test_a_case_study_requires_typed_flags(self):
        with self.assertRaises(InvalidServiceLineError):
            case_study(result_measured="yes")


class ServiceLineTests(unittest.TestCase):
    def test_a_service_line_carries_the_five_canon_artifacts(self):
        built = service_line()
        self.assertIsInstance(built.kickoff, KickoffChecklist)
        self.assertIsInstance(built.module_standard, ModuleProductionStandard)
        self.assertIsInstance(built.session_guide, SessionGuide)
        self.assertIsInstance(built.scorecard, ClientScorecard)
        self.assertIsInstance(built.case_study, CaseStudy)

    def test_a_service_line_grounds_on_a_same_tenant_program(self):
        self.assertEqual("program-3f", service_line().program.program_id)

    def test_a_service_line_refuses_a_program_from_another_tenant(self):
        foreign = product_program(solution=signature_solution(OTHER_TENANT))
        with self.assertRaises(ServiceLineTenantBoundaryError):
            service_line(program=foreign, tenant_id=TENANT)

    def test_a_service_line_refuses_a_case_study_from_another_tenant(self):
        with self.assertRaises(ServiceLineTenantBoundaryError):
            service_line(case_study=case_study(tenant_id=OTHER_TENANT))

    def test_a_service_line_requires_a_typed_program(self):
        with self.assertRaises(ServiceLineDependencyError):
            service_line(program="program")

    def test_a_service_line_requires_typed_artifacts(self):
        for field in (
            "kickoff",
            "module_standard",
            "session_guide",
            "scorecard",
            "case_study",
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidServiceLineError):
                    service_line(**{field: "artifact"})

    def test_a_service_line_requires_identity(self):
        for field in ("service_line_id", "tenant_id", "owner"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidServiceLineError):
                    service_line(**{field: "  "})

    def test_a_service_line_requires_a_creation_date(self):
        with self.assertRaises(InvalidServiceLineError):
            service_line(created_on="2026-10-02")

    def test_a_service_line_is_a_plan_not_an_observation(self):
        built = service_line()
        self.assertTrue(built.is_plan)
        with self.assertRaises(ServiceLineObservationError):
            built.as_observation(claim_id="claim-1")

    def test_a_service_line_is_frozen(self):
        built = service_line()
        with self.assertRaises(FrozenInstanceError):
            built.owner = "someone-else"

    def test_a_service_line_reports_its_canon_reference_and_post_launch_stage(self):
        built = service_line()
        self.assertEqual(SERVICE_LINE_CANON_REFERENCE, built.canon_reference)
        self.assertTrue(built.is_post_launch)

    def test_a_service_line_proves_results_against_the_kickoff_goals(self):
        built = service_line()
        claim = built.prove()
        self.assertIsInstance(claim, CaseStudyClaim)
        self.assertEqual(1, len(built.kickoff.goals))

    def test_a_service_line_refuses_to_prove_without_an_approved_case_study(self):
        with self.assertRaises(CaseStudyAuthorityError):
            service_line(case_study=case_study(written_permission=False)).prove()


if __name__ == "__main__":
    unittest.main()

"""Behavioral tests for the canon webinar kit (Execution domain).

Rules under test come from the canon's winning-webinar material and the
implementation plan's canon gap backlog item G3 (SPEC.md section 12.5 records the
webinar kit as a canon gap; the backlog names a typed artifact that "records the
chosen path and the automation gate; refuses automation below the live-run bar").
The shape is extracted from:

- Canon file 32 and the Winning Webinar series: the six-phase run of show (frame,
  teach, shift, sell, show, close), three teach blocks that match the three phases
  of the signature solution, one offer, the page set (sign up, train, webinar,
  replay, order), the 5P email sequence, the 3 to 5 day closing sequence, the
  replay to everyone and retargeting by where each group stopped.
- Winning Webinar 13: the 10-and-10 rule -- automate a webinar only after ten live
  runs at 10% or better -- and never present an automated webinar as live.
- Synthesized `ops/playbooks/webinar.md`, `ops/checklists/webinar-run-of-show.md`
  and `ops/sops/webinar-build.md`: the six phases, the about-60-minute clock, the
  simple path first, and the closing sequence.

The kit is the scaled enrollment path, a stage 6/8/10 planning asset, not a new
required gate kind. It does not authorize sending, spend, publishing or any client
commitment (SPEC.md sections 4 and 9) and it is never an observation (SPEC.md
section 3).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.execution.domain.errors import (
    InvalidWebinarError,
    WebinarAutomationError,
    WebinarDependencyError,
    WebinarFormatError,
    WebinarObservationError,
    WebinarTenantBoundaryError,
)
from redops.contexts.execution.domain.webinar import (
    WEBINAR_AUTOMATION_CONVERSION_PERCENT,
    WEBINAR_AUTOMATION_LIVE_RUNS,
    WEBINAR_CANON_REFERENCE,
    WEBINAR_CLOSING_MAX_DAYS,
    WEBINAR_CLOSING_MIN_DAYS,
    WEBINAR_EMAIL_ORDER,
    WEBINAR_MAX_MINUTES,
    WEBINAR_MIN_MINUTES,
    WEBINAR_PAGE_ORDER,
    WEBINAR_PHASE_ORDER,
    WEBINAR_TARGET_MINUTES,
    EnrollmentPath,
    WebinarAutomation,
    WebinarClosingSequence,
    WebinarEmail,
    WebinarEmailKind,
    WebinarEmailSequence,
    WebinarKit,
    WebinarMode,
    WebinarPage,
    WebinarPageSet,
    WebinarPhase,
    WebinarPhaseBlock,
    WebinarTeachBlock,
)

from ..method.fixtures import signature_solution
from .fixtures import TENANT

OTHER_TENANT = "client-other"


def phase_block(
    phase: WebinarPhase = WebinarPhase.FRAME, **overrides
) -> WebinarPhaseBlock:
    values = {
        "phase": phase,
        "purpose": f"the {phase.value} purpose",
        "minutes": 10,
    }
    values.update(overrides)
    return WebinarPhaseBlock(**values)


def phase_blocks(minutes: int = 10) -> tuple[WebinarPhaseBlock, ...]:
    return tuple(phase_block(phase, minutes=minutes) for phase in WEBINAR_PHASE_ORDER)


def teach_block(phase_name: str, **overrides) -> WebinarTeachBlock:
    values = {
        "phase_name": phase_name,
        "promise": f"the measurable outcome for {phase_name}",
        "obstacles": (f"the first obstacle for {phase_name}",),
    }
    values.update(overrides)
    return WebinarTeachBlock(**values)


def teach_blocks(solution=None) -> tuple[WebinarTeachBlock, ...]:
    source = solution if solution is not None else signature_solution()
    return tuple(teach_block(phase.name) for phase in source.phases)


def page_set(**overrides) -> WebinarPageSet:
    values = {"pages": WEBINAR_PAGE_ORDER}
    values.update(overrides)
    return WebinarPageSet(**values)


def email(kind: WebinarEmailKind, **overrides) -> WebinarEmail:
    values = {"kind": kind, "subject": f"the {kind.value} email"}
    values.update(overrides)
    return WebinarEmail(**values)


def email_sequence(**overrides) -> WebinarEmailSequence:
    values = {"emails": tuple(email(kind) for kind in WEBINAR_EMAIL_ORDER)}
    values.update(overrides)
    return WebinarEmailSequence(**values)


def closing(**overrides) -> WebinarClosingSequence:
    values = {
        "days": 4,
        "steps": ("replay", "proof", "questions", "last call"),
    }
    values.update(overrides)
    return WebinarClosingSequence(**values)


def automation(**overrides) -> WebinarAutomation:
    values = {
        "mode": WebinarMode.LIVE,
        "live_runs": 0,
        "conversion_percent": 0,
    }
    values.update(overrides)
    return WebinarAutomation(**values)


def webinar(**overrides) -> WebinarKit:
    values = {
        "kit_id": "webinar-3f",
        "tenant_id": TENANT,
        "owner": "delivery-lead",
        "solution": signature_solution(),
        "path": EnrollmentPath.SCALED,
        "simple_path_proven": True,
        "phases": phase_blocks(),
        "teach_blocks": teach_blocks(),
        "offer": "the one program offer",
        "pages": page_set(),
        "emails": email_sequence(),
        "closing": closing(),
        "replay_to_all": True,
        "retargeting_groups": ("registered", "attended", "replay-only"),
        "automation": automation(),
    }
    values.update(overrides)
    return WebinarKit(**values)


class WebinarShapeTests(unittest.TestCase):
    def test_canon_reference_names_the_webinar_sources(self) -> None:
        self.assertIn("32", WEBINAR_CANON_REFERENCE)
        self.assertIn("Winning Webinar", WEBINAR_CANON_REFERENCE)

    def test_a_valid_kit_is_a_plan_that_feeds_stages_six_eight_and_ten(self) -> None:
        kit = webinar()
        self.assertTrue(kit.is_plan)
        self.assertEqual((6, 8, 10), kit.feeds_stages)
        self.assertEqual(WEBINAR_CANON_REFERENCE, kit.canon_reference)
        self.assertEqual(EnrollmentPath.SCALED, kit.path)

    def test_the_kit_is_frozen(self) -> None:
        kit = webinar()
        with self.assertRaises(FrozenInstanceError):
            kit.owner = "someone-else"  # type: ignore[misc]

    def test_blank_identity_is_refused(self) -> None:
        for field in ("kit_id", "owner"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidWebinarError):
                    webinar(**{field: "  "})


class WebinarPathTests(unittest.TestCase):
    def test_the_webinar_is_the_scaled_path(self) -> None:
        self.assertEqual(EnrollmentPath.SCALED, webinar().path)

    def test_the_simple_path_is_refused(self) -> None:
        with self.assertRaises(WebinarFormatError):
            webinar(path=EnrollmentPath.SIMPLE)

    def test_the_simple_path_must_be_proven_first(self) -> None:
        with self.assertRaises(WebinarFormatError):
            webinar(simple_path_proven=False)


class WebinarRunOfShowTests(unittest.TestCase):
    def test_the_six_phases_run_in_order(self) -> None:
        self.assertEqual(
            (
                WebinarPhase.FRAME,
                WebinarPhase.TEACH,
                WebinarPhase.SHIFT,
                WebinarPhase.SELL,
                WebinarPhase.SHOW,
                WebinarPhase.CLOSE,
            ),
            WEBINAR_PHASE_ORDER,
        )
        self.assertEqual(
            WEBINAR_PHASE_ORDER,
            tuple(block.phase for block in webinar().phases),
        )

    def test_a_missing_or_out_of_order_phase_is_refused(self) -> None:
        with self.assertRaises(WebinarFormatError):
            webinar(phases=phase_blocks()[:-1])
        with self.assertRaises(WebinarFormatError):
            webinar(phases=tuple(reversed(phase_blocks())))

    def test_the_clock_is_about_sixty_minutes(self) -> None:
        self.assertEqual(60, WEBINAR_TARGET_MINUTES)
        self.assertEqual(60, sum(block.minutes for block in webinar().phases))
        with self.assertRaises(WebinarFormatError):
            webinar(phases=phase_blocks(minutes=WEBINAR_MIN_MINUTES // 6 - 1))
        with self.assertRaises(WebinarFormatError):
            webinar(phases=phase_blocks(minutes=WEBINAR_MAX_MINUTES // 6 + 1))

    def test_a_blank_purpose_or_non_positive_minutes_is_refused(self) -> None:
        with self.assertRaises(InvalidWebinarError):
            phase_block(purpose="   ")
        with self.assertRaises(InvalidWebinarError):
            phase_block(minutes=0)


class WebinarTeachBlockTests(unittest.TestCase):
    def test_three_teach_blocks_match_the_three_solution_phases(self) -> None:
        solution = signature_solution()
        self.assertEqual(
            tuple(phase.name for phase in solution.phases),
            tuple(block.phase_name for block in webinar().teach_blocks),
        )

    def test_a_teach_block_must_name_a_solution_phase(self) -> None:
        solution = signature_solution()
        blocks = teach_blocks(solution)[:-1] + (teach_block("Invent a phase"),)
        with self.assertRaises(WebinarDependencyError):
            webinar(teach_blocks=blocks)

    def test_missing_extra_or_duplicate_teach_blocks_are_refused(self) -> None:
        solution = signature_solution()
        with self.assertRaises(WebinarFormatError):
            webinar(teach_blocks=teach_blocks(solution)[:-1])
        extra = teach_blocks(solution) + (teach_block(solution.phases[0].name),)
        with self.assertRaises(WebinarFormatError):
            webinar(teach_blocks=extra)

    def test_a_blank_promise_or_obstacle_is_refused(self) -> None:
        with self.assertRaises(InvalidWebinarError):
            teach_block("Diagnose and Position", promise="   ")
        with self.assertRaises(InvalidWebinarError):
            teach_block("Diagnose and Position", obstacles=())
        with self.assertRaises(InvalidWebinarError):
            teach_block(
                "Diagnose and Position", obstacles=("same", "same")
            )


class WebinarOfferTests(unittest.TestCase):
    def test_the_webinar_makes_one_offer(self) -> None:
        self.assertEqual("the one program offer", webinar().offer)

    def test_a_blank_offer_is_refused(self) -> None:
        with self.assertRaises(InvalidWebinarError):
            webinar(offer="   ")


class WebinarPageSetTests(unittest.TestCase):
    def test_the_page_set_is_the_canon_five_pages_in_order(self) -> None:
        self.assertEqual(
            (
                WebinarPage.SIGN_UP,
                WebinarPage.TRAIN,
                WebinarPage.WEBINAR,
                WebinarPage.REPLAY,
                WebinarPage.ORDER,
            ),
            WEBINAR_PAGE_ORDER,
        )
        self.assertEqual(WEBINAR_PAGE_ORDER, webinar().pages.pages)

    def test_a_missing_or_extra_page_is_refused(self) -> None:
        with self.assertRaises(WebinarFormatError):
            webinar(pages=page_set(pages=WEBINAR_PAGE_ORDER[:-1]))
        extra = WEBINAR_PAGE_ORDER + (WebinarPage.SIGN_UP,)
        with self.assertRaises(WebinarFormatError):
            webinar(pages=page_set(pages=extra))


class WebinarEmailSequenceTests(unittest.TestCase):
    def test_the_email_sequence_uses_the_five_5p_types_in_order(self) -> None:
        self.assertEqual(
            (
                WebinarEmailKind.PROBLEM,
                WebinarEmailKind.PROMISE,
                WebinarEmailKind.PROOF,
                WebinarEmailKind.PING,
                WebinarEmailKind.PROMOTION,
            ),
            WEBINAR_EMAIL_ORDER,
        )
        self.assertEqual(
            WEBINAR_EMAIL_ORDER,
            tuple(item.kind for item in webinar().emails.emails),
        )

    def test_a_missing_or_extra_email_type_is_refused(self) -> None:
        with self.assertRaises(WebinarFormatError):
            webinar(emails=email_sequence(emails=email_sequence().emails[:-1]))
        extra = email_sequence().emails + (email(WebinarEmailKind.PROBLEM),)
        with self.assertRaises(WebinarFormatError):
            webinar(emails=email_sequence(emails=extra))

    def test_a_blank_subject_is_refused(self) -> None:
        with self.assertRaises(InvalidWebinarError):
            email(WebinarEmailKind.PROBLEM, subject="   ")


class WebinarClosingSequenceTests(unittest.TestCase):
    def test_the_closing_sequence_runs_three_to_five_days(self) -> None:
        self.assertEqual(3, WEBINAR_CLOSING_MIN_DAYS)
        self.assertEqual(5, WEBINAR_CLOSING_MAX_DAYS)
        self.assertEqual(4, closing().days)
        with self.assertRaises(WebinarFormatError):
            webinar(closing=closing(days=2))
        with self.assertRaises(WebinarFormatError):
            webinar(closing=closing(days=6))

    def test_a_blank_closing_step_is_refused(self) -> None:
        with self.assertRaises(InvalidWebinarError):
            closing(steps=())
        with self.assertRaises(InvalidWebinarError):
            closing(steps=("replay", "replay"))


class WebinarFollowUpTests(unittest.TestCase):
    def test_the_replay_goes_to_everyone(self) -> None:
        self.assertTrue(webinar().replay_to_all)
        with self.assertRaises(WebinarFormatError):
            webinar(replay_to_all=False)

    def test_retargeting_needs_at_least_one_duplicate_free_group(self) -> None:
        with self.assertRaises(InvalidWebinarError):
            webinar(retargeting_groups=())
        with self.assertRaises(InvalidWebinarError):
            webinar(retargeting_groups=("registered", "registered"))


class WebinarAutomationTests(unittest.TestCase):
    def test_the_ten_and_ten_bar_is_ten_runs_at_ten_percent(self) -> None:
        self.assertEqual(10, WEBINAR_AUTOMATION_LIVE_RUNS)
        self.assertEqual(10, WEBINAR_AUTOMATION_CONVERSION_PERCENT)

    def test_a_live_webinar_needs_no_bar(self) -> None:
        kit = webinar(automation=automation(mode=WebinarMode.LIVE))
        self.assertFalse(kit.automation.is_automated)

    def test_automation_below_the_bar_is_refused(self) -> None:
        with self.assertRaises(WebinarAutomationError):
            webinar(
                automation=automation(
                    mode=WebinarMode.AUTOMATED,
                    live_runs=WEBINAR_AUTOMATION_LIVE_RUNS - 1,
                    conversion_percent=WEBINAR_AUTOMATION_CONVERSION_PERCENT,
                )
            )
        with self.assertRaises(WebinarAutomationError):
            webinar(
                automation=automation(
                    mode=WebinarMode.AUTOMATED,
                    live_runs=WEBINAR_AUTOMATION_LIVE_RUNS,
                    conversion_percent=WEBINAR_AUTOMATION_CONVERSION_PERCENT - 1,
                )
            )

    def test_automation_at_the_bar_is_accepted(self) -> None:
        kit = webinar(
            automation=automation(
                mode=WebinarMode.AUTOMATED,
                live_runs=WEBINAR_AUTOMATION_LIVE_RUNS,
                conversion_percent=WEBINAR_AUTOMATION_CONVERSION_PERCENT,
            )
        )
        self.assertTrue(kit.automation.is_automated)
        self.assertTrue(kit.automation.meets_automation_bar)

    def test_an_automated_webinar_cannot_be_presented_as_live(self) -> None:
        with self.assertRaises(WebinarAutomationError):
            webinar(
                automation=automation(
                    mode=WebinarMode.AUTOMATED,
                    live_runs=WEBINAR_AUTOMATION_LIVE_RUNS,
                    conversion_percent=WEBINAR_AUTOMATION_CONVERSION_PERCENT,
                    presented_as_live=True,
                )
            )


class WebinarGroundingTests(unittest.TestCase):
    def test_the_kit_must_be_grounded_on_a_typed_solution(self) -> None:
        with self.assertRaises(WebinarDependencyError):
            webinar(solution="not-a-solution")

    def test_a_foreign_solution_is_refused(self) -> None:
        with self.assertRaises(WebinarTenantBoundaryError):
            webinar(solution=signature_solution(OTHER_TENANT))

    def test_a_kit_cannot_be_recorded_as_an_observation(self) -> None:
        with self.assertRaises(WebinarObservationError):
            webinar().as_observation(claim_id="claim-1")


if __name__ == "__main__":
    unittest.main()

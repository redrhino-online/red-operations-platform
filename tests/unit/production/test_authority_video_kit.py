"""Behavioral tests for the canon authority-video kit (Production domain).

Rules under test come from the canon's authority-video material and the
implementation plan's canon gap backlog item G2 (SPEC.md section 12.5 records the
authority-video kit as a canon gap; the backlog names a typed artifact that
"extends the stage 7 `AuthorityAmplifier`; refuses a step video whose step the
solution does not name"). The shape is extracted from:

- Canon files 13-18 and the High Ticket Funnels 05, 06, 08 series: the six-block
  script (Promise, Proof, Problems, Steps, Context, Action) that runs every
  asset, block shuffling (one body, many hooks), and the 10-pack (one flagship
  video plus nine step videos, one per signature-solution step).
- Synthesized `ops/playbooks/authority-video.md` and
  `ops/sops/authority-video-build.md`: the gate (the script follows the six
  blocks, shows the signature solution, has one clear action, and is checked
  before the slides are made), the 8 to 20 minute flagship length, and the
  common failures (slides before the script, no proof, more than one action, a
  video that is too long).

The kit is a stage 7 production plan, not a new required gate kind. It does not
authorize publishing or spend (SPEC.md sections 4 and 9) and it is never an
observation (SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.production.domain.errors import (
    AuthorityVideoKitDependencyError,
    AuthorityVideoKitFormatError,
    AuthorityVideoKitObservationError,
    AuthorityVideoKitTenantBoundaryError,
    InvalidAuthorityVideoKitError,
)
from redops.contexts.production.domain.value_objects import (
    AUTHORITY_VIDEO_CANON_REFERENCE,
    AuthorityStepVideo,
    AuthorityVideoKit,
)
from redops.contexts.method.domain.entities import SignatureSolution

from .fixtures import TENANT, approved_amplifier, authority_amplifier
from ..commercial.fixtures import (
    approved_method,
    campaign_message,
    delivery_specification,
    offer_version,
)
from ..method.fixtures import signature_solution

OTHER_TENANT = "client-other"


def other_tenant_amplifier():
    solution = signature_solution(tenant_id=OTHER_TENANT)
    delivery = delivery_specification(signature_solution=solution)
    offer = offer_version(
        tenant_id=OTHER_TENANT, delivery_specification=delivery
    ).require_production_ready(
        (approved_method(tenant_id=OTHER_TENANT, solution=solution),)
    )
    message = campaign_message(offer=offer).approve(
        (approved_method(tenant_id=OTHER_TENANT, solution=solution),)
    )
    return authority_amplifier(
        message=message,
        amplifier_id="amplifier-other",
        tenant_id=OTHER_TENANT,
    )


def step_video(name: str, **overrides) -> AuthorityStepVideo:
    values = {
        "video_id": f"video-{name.lower().replace(' ', '-')}",
        "tenant_id": TENANT,
        "step_name": name,
        "title": f"{name} step video",
        "duration_minutes": 3,
        "action": "book the strategy call",
    }
    values.update(overrides)
    return AuthorityStepVideo(**values)


def authority_video_kit(**overrides) -> AuthorityVideoKit:
    solution = overrides.pop("solution", None) or signature_solution()
    amplifier = overrides.pop("amplifier", None) or approved_amplifier()
    step_videos = overrides.pop("step_videos", None)
    if step_videos is None:
        source = (
            solution
            if isinstance(solution, SignatureSolution)
            else signature_solution()
        )
        step_videos = tuple(step_video(step.name) for step in source.steps)
    values = {
        "kit_id": "video-kit-3f",
        "tenant_id": TENANT,
        "owner": "production-manager",
        "amplifier": amplifier,
        "solution": solution,
        "flagship_title": "the 3f authority video",
        "flagship_duration_minutes": 12,
        "flagship_action": "book the strategy call",
        "step_videos": step_videos,
    }
    values.update(overrides)
    return AuthorityVideoKit(**values)


class AuthorityVideoKitTest(unittest.TestCase):
    def test_canon_reference_names_the_authority_video_sources(self) -> None:
        self.assertIn("13-18", AUTHORITY_VIDEO_CANON_REFERENCE)
        self.assertIn("High Ticket Funnels 05", AUTHORITY_VIDEO_CANON_REFERENCE)

    def test_a_complete_kit_is_frozen_and_reports_the_ten_pack(self) -> None:
        kit = authority_video_kit()
        self.assertTrue(kit.is_plan)
        self.assertEqual(len(kit.step_videos), 9)
        self.assertEqual(
            {video.step_name for video in kit.step_videos},
            {step.name for step in signature_solution().steps},
        )
        self.assertEqual(kit.script, approved_amplifier().script)
        with self.assertRaises(FrozenInstanceError):
            kit.flagship_title = "changed"  # type: ignore[misc]

    def test_blank_identity_is_refused(self) -> None:
        for field in (
            "kit_id",
            "owner",
            "flagship_title",
            "flagship_action",
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidAuthorityVideoKitError):
                    authority_video_kit(**{field: "  "})

    def test_kit_must_be_grounded_on_a_typed_amplifier(self) -> None:
        with self.assertRaises(AuthorityVideoKitDependencyError):
            authority_video_kit(amplifier="not-an-amplifier")

    def test_kit_must_be_grounded_on_a_typed_signature_solution(self) -> None:
        with self.assertRaises(AuthorityVideoKitDependencyError):
            authority_video_kit(solution="not-a-solution")

    def test_kit_refuses_a_cross_tenant_amplifier_or_solution(self) -> None:
        with self.assertRaises(AuthorityVideoKitTenantBoundaryError):
            authority_video_kit(amplifier=other_tenant_amplifier())
        with self.assertRaises(AuthorityVideoKitTenantBoundaryError):
            authority_video_kit(solution=signature_solution("client-other"))

    def test_kit_requires_the_script_checked_before_the_video_is_cut(self) -> None:
        # An amplifier with no visual package has not produced the video the
        # nine step videos are cut from (the canon gate: script before slides).
        with self.assertRaises(AuthorityVideoKitDependencyError):
            authority_video_kit(amplifier=authority_amplifier())

    def test_flagship_must_run_eight_to_twenty_minutes(self) -> None:
        with self.assertRaises(AuthorityVideoKitFormatError):
            authority_video_kit(flagship_duration_minutes=7)
        with self.assertRaises(AuthorityVideoKitFormatError):
            authority_video_kit(flagship_duration_minutes=21)

    def test_flagship_duration_must_be_a_whole_number(self) -> None:
        with self.assertRaises(InvalidAuthorityVideoKitError):
            authority_video_kit(flagship_duration_minutes="12")

    def test_kit_requires_exactly_nine_step_videos(self) -> None:
        solution = signature_solution()
        eight = tuple(step_video(step.name) for step in solution.steps[:8])
        with self.assertRaises(AuthorityVideoKitFormatError):
            authority_video_kit(step_videos=eight)
        ten = tuple(step_video(step.name) for step in solution.steps) + (
            step_video("Diagnose", video_id="video-extra"),
        )
        with self.assertRaises(AuthorityVideoKitFormatError):
            authority_video_kit(step_videos=ten)

    def test_step_video_must_name_a_step_the_solution_names(self) -> None:
        solution = signature_solution()
        videos = tuple(step_video(step.name) for step in solution.steps[:-1]) + (
            step_video("Invent a new step"),
        )
        with self.assertRaises(AuthorityVideoKitDependencyError):
            authority_video_kit(step_videos=videos)

    def test_step_videos_must_not_repeat_a_step(self) -> None:
        solution = signature_solution()
        videos = tuple(step_video(step.name) for step in solution.steps[:-1]) + (
            step_video(solution.steps[0].name, video_id="video-duplicate"),
        )
        with self.assertRaises(AuthorityVideoKitFormatError):
            authority_video_kit(step_videos=videos)

    def test_step_video_must_be_a_typed_step_video(self) -> None:
        with self.assertRaises(InvalidAuthorityVideoKitError):
            authority_video_kit(step_videos=("not-a-video",) * 9)

    def test_step_video_must_be_positive_and_not_longer_than_the_flagship(self) -> None:
        solution = signature_solution()
        with self.assertRaises(InvalidAuthorityVideoKitError):
            step_video(solution.steps[-1].name, duration_minutes=0)
        long_videos = tuple(
            step_video(step.name, duration_minutes=13) for step in solution.steps
        )
        with self.assertRaises(AuthorityVideoKitFormatError):
            authority_video_kit(step_videos=long_videos)

    def test_step_video_refuses_a_cross_tenant_video(self) -> None:
        solution = signature_solution()
        videos = tuple(step_video(step.name) for step in solution.steps[:-1]) + (
            step_video(solution.steps[-1].name, tenant_id="client-other"),
        )
        with self.assertRaises(AuthorityVideoKitTenantBoundaryError):
            authority_video_kit(step_videos=videos)

    def test_kit_is_never_an_observation(self) -> None:
        with self.assertRaises(AuthorityVideoKitObservationError):
            authority_video_kit().as_observation(claim_id="claim-1")


if __name__ == "__main__":
    unittest.main()

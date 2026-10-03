"""Behavioral tests for the canon Content Crusher (Commercial domain).

Rules under test come from SPEC.md section 12.5 (the audience-building and
content flywheel is a canon gap mapped to stages 6 and 10) and section 12.3
(stage 6 uses canon files 25-28 and 32-34), shaped by the canon's Content
Crusher framework (canon files 12, 16 and 32):

- A content crusher captures one topic as a world class outline: the topic and
  title, a promise with a metric and a timeline, the transformation from the
  customer's top frustrations to their goal, a visual model, a metaphor, the
  context of where the content lives in the whole program, the steps, a real
  story, a choice and the next action (canon file 32).
- The content never drifts from the method: "we never create a piece of content
  that doesn't live in the signature solution" (canon file 28), so the crusher is
  grounded on a same-tenant Content Roadmap topic and teaches the signature
  solution's own steps.

The crusher is a stage 6 planning asset, not a new required gate kind (a
methodology-owner decision, SPEC.md section 12.5). It does not authorize
publishing or spend (SPEC.md sections 4 and 9) and it is never an observation
(SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.errors import (
    ContentCrusherDependencyError,
    ContentCrusherObservationError,
    ContentCrusherTenantBoundaryError,
    InvalidContentCrusherError,
)
from redops.contexts.commercial.domain.value_objects import (
    AUTHORITY_AMPLIFIER_BEATS,
    ContentCrusher,
    ContentPromise,
    ContentRoadmap,
    ContentTopic,
    MINIMUM_PUBLISH_CHANNELS,
)

from .fixtures import TENANT
from ..method.fixtures import signature_solution


def content_topic(**overrides) -> ContentTopic:
    values = {
        "topic_id": "topic-diagnose-1",
        "tenant_id": TENANT,
        "name": "why referrals stall at four a month",
        "signature_step": "Diagnose",
        "question": "why do my referrals stop at four a month?",
        "channels": MINIMUM_PUBLISH_CHANNELS,
        "script_beats": AUTHORITY_AMPLIFIER_BEATS,
    }
    values.update(overrides)
    return ContentTopic(**values)


def content_roadmap(**overrides) -> ContentRoadmap:
    values = {
        "roadmap_id": "roadmap-3f",
        "tenant_id": TENANT,
        "owner": "content-operator",
        "method": signature_solution(),
        "topics": (
            content_topic(),
            content_topic(
                topic_id="topic-position-1",
                name="how to pick the referral outcome that matters",
                signature_step="Position",
                question="which referral outcome should I measure?",
            ),
        ),
    }
    values.update(overrides)
    return ContentRoadmap(**values)


def content_promise(**overrides) -> ContentPromise:
    values = {
        "measure": "four more qualified referrals a month",
        "timeline": "in 30 days",
    }
    values.update(overrides)
    return ContentPromise(**values)


def content_crusher(**overrides) -> ContentCrusher:
    values = {
        "crusher_id": "crusher-diagnose-1",
        "tenant_id": TENANT,
        "owner": "content-operator",
        "roadmap": content_roadmap(),
        "topic_id": "topic-diagnose-1",
        "title": "the four-referral ceiling and how to break it",
        "promise": content_promise(),
        "frustrations": (
            "referrals arrive randomly",
            "asking for referrals feels pushy",
        ),
        "goal": "a predictable twelve referrals a month",
        "model": "asset://content/referral-ceiling.png",
        "metaphor": "like a tap that only drips",
        "context": "this is step one of the nine step journey",
        "steps": ("Diagnose", "Position"),
        "story": "a client doubled referrals after mapping the ceiling",
        "choice": "keep guessing or run the diagnostic",
        "action": "book the diagnostic call",
    }
    values.update(overrides)
    return ContentCrusher(**values)


class ContentPromiseTests(unittest.TestCase):
    def test_a_promise_requires_its_measure_and_timeline(self):
        for override in (
            {"measure": ""},
            {"measure": "  "},
            {"timeline": ""},
            {"timeline": "  "},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidContentCrusherError):
                    content_promise(**override)

    def test_a_promise_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            content_promise().timeline = "someday"


class ContentCrusherTests(unittest.TestCase):
    def test_a_crusher_requires_its_identity_owner_and_title(self):
        for override in (
            {"crusher_id": ""},
            {"tenant_id": "  "},
            {"owner": ""},
            {"title": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidContentCrusherError):
                    content_crusher(**override)

    def test_a_crusher_requires_every_canonical_beat(self):
        for override in (
            {"topic_id": ""},
            {"goal": ""},
            {"model": "  "},
            {"metaphor": ""},
            {"context": ""},
            {"story": ""},
            {"choice": ""},
            {"action": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidContentCrusherError):
                    content_crusher(**override)

    def test_a_crusher_requires_a_typed_promise(self):
        with self.assertRaises(InvalidContentCrusherError):
            content_crusher(promise="more referrals")

    def test_a_crusher_requires_at_least_one_customer_frustration(self):
        with self.assertRaises(InvalidContentCrusherError):
            content_crusher(frustrations=())

    def test_a_crusher_refuses_a_blank_frustration(self):
        with self.assertRaises(InvalidContentCrusherError):
            content_crusher(frustrations=("referrals arrive randomly", "  "))

    def test_a_crusher_requires_at_least_one_signature_step(self):
        with self.assertRaises(InvalidContentCrusherError):
            content_crusher(steps=())

    def test_a_crusher_refuses_a_blank_step(self):
        with self.assertRaises(InvalidContentCrusherError):
            content_crusher(steps=("Diagnose", " "))

    def test_a_crusher_refuses_duplicate_steps(self):
        with self.assertRaises(InvalidContentCrusherError):
            content_crusher(steps=("Diagnose", "Diagnose"))

    def test_a_crusher_requires_a_typed_content_roadmap(self):
        with self.assertRaises(ContentCrusherDependencyError):
            content_crusher(roadmap="the roadmap")

    def test_a_crusher_refuses_a_cross_tenant_roadmap(self):
        other = content_roadmap(
            tenant_id="client-other",
            method=signature_solution(tenant_id="client-other"),
            topics=(content_topic(tenant_id="client-other"),),
        )

        with self.assertRaises(ContentCrusherTenantBoundaryError):
            content_crusher(roadmap=other, tenant_id=TENANT)

    def test_a_crusher_refuses_a_topic_the_roadmap_does_not_name(self):
        with self.assertRaises(ContentCrusherDependencyError):
            content_crusher(topic_id="topic-not-planned")

    def test_a_crusher_refuses_a_step_the_solution_does_not_name(self):
        with self.assertRaises(ContentCrusherDependencyError):
            content_crusher(steps=("Enroll",))

    def test_a_crusher_teaches_the_solutions_own_steps(self):
        crusher = content_crusher()

        self.assertEqual(("Diagnose", "Position"), crusher.steps)

    def test_a_crusher_is_a_plan_not_an_observation(self):
        self.assertTrue(content_crusher().is_plan)
        with self.assertRaises(ContentCrusherObservationError):
            content_crusher().as_observation(claim_id="claim-1")

    def test_a_crusher_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            content_crusher().owner = "someone-else"


if __name__ == "__main__":
    unittest.main()

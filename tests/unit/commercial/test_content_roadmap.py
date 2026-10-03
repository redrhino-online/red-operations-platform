"""Behavioral tests for the canon Content Roadmap (Commercial domain).

Rules under test come from SPEC.md section 12.5 (the audience-building and content
flywheel is a canon gap mapped to stages 6 and 10) and section 12.3 (stage 6 uses
canon files 25-28), shaped by the canon's Content Blitz (canon files 25-31):

- The roadmap maps the steps of the client's Signature Solution to content topics:
  "create a content roadmap using the signature solution to map out the topics,
  FAQs and search queries" (canon file 26), and "take each step of your signature
  solution ... just brainstorming FAQs and questions you already know your audience
  is asking" (canon file 27).
- Every piece of audience-building content uses the Authority Amplifier script
  format: "these two to five minute videos ... still use the authority amplifier
  script because that's the framework I want you to use for every piece of
  content" (canon file 26), whose order is Promise, Proof, Problems, Steps,
  Context, Action (SPEC.md section 4, stage 7).
- Content must be published widely, not left in one place: "upload to YouTube,
  Facebook and blog at a minimum" (canon file 29), and "never ever post something
  on social media once once you're losing 99% of the equity of the asset you've
  created" (canon file 31).

The roadmap is a stage 6 planning asset, not a new required gate kind (a
methodology-owner decision, SPEC.md section 12.5). It does not authorize
publishing or spend (SPEC.md sections 4 and 9) and it is never an observation
(SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.errors import (
    ContentDistributionError,
    ContentRoadmapDependencyError,
    ContentRoadmapFormatError,
    ContentRoadmapObservationError,
    ContentRoadmapTenantBoundaryError,
    InvalidContentRoadmapError,
)
from redops.contexts.commercial.domain.policies import ContentDistributionPolicy
from redops.contexts.commercial.domain.value_objects import (
    AUTHORITY_AMPLIFIER_BEATS,
    ContentBeat,
    ContentChannel,
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


class ContentBeatTests(unittest.TestCase):
    def test_the_authority_amplifier_beats_are_in_the_canon_order(self):
        self.assertEqual(
            (
                ContentBeat.PROMISE,
                ContentBeat.PROOF,
                ContentBeat.PROBLEMS,
                ContentBeat.STEPS,
                ContentBeat.CONTEXT,
                ContentBeat.ACTION,
            ),
            AUTHORITY_AMPLIFIER_BEATS,
        )

    def test_the_authority_amplifier_beats_are_named(self):
        self.assertEqual(
            {"promise", "proof", "problems", "steps", "context", "action"},
            {beat.value for beat in ContentBeat},
        )


class ContentChannelTests(unittest.TestCase):
    def test_the_canon_minimum_publish_channels_are_named(self):
        self.assertEqual(
            (ContentChannel.BLOG, ContentChannel.YOUTUBE, ContentChannel.FACEBOOK),
            MINIMUM_PUBLISH_CHANNELS,
        )


class ContentTopicTests(unittest.TestCase):
    def test_a_topic_requires_its_identity_step_question_and_scripts(self):
        self.assertEqual("Diagnose", content_topic().signature_step)
        for override in (
            {"topic_id": ""},
            {"tenant_id": "  "},
            {"name": ""},
            {"signature_step": ""},
            {"question": "  "},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidContentRoadmapError):
                    content_topic(**override)

    def test_a_topic_requires_typed_channels(self):
        with self.assertRaises(InvalidContentRoadmapError):
            content_topic(channels=("blog", "youtube"))

    def test_a_topic_requires_at_least_one_channel(self):
        with self.assertRaises(InvalidContentRoadmapError):
            content_topic(channels=())

    def test_a_topic_refuses_duplicate_channels(self):
        with self.assertRaises(ContentRoadmapFormatError):
            content_topic(
                channels=(ContentChannel.BLOG, ContentChannel.BLOG)
            )

    def test_a_topic_must_follow_the_authority_amplifier_beat_order(self):
        with self.assertRaises(ContentRoadmapFormatError):
            content_topic(
                script_beats=(
                    ContentBeat.PROOF,
                    ContentBeat.PROMISE,
                    ContentBeat.PROBLEMS,
                    ContentBeat.STEPS,
                    ContentBeat.CONTEXT,
                    ContentBeat.ACTION,
                )
            )

    def test_a_topic_missing_a_beat_is_refused(self):
        with self.assertRaises(ContentRoadmapFormatError):
            content_topic(script_beats=AUTHORITY_AMPLIFIER_BEATS[:-1])

    def test_a_topic_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            content_topic().name = "another topic"


class ContentRoadmapTests(unittest.TestCase):
    def test_a_roadmap_requires_its_identity_owner_method_and_topics(self):
        for override in (
            {"roadmap_id": ""},
            {"tenant_id": "  "},
            {"owner": ""},
            {"topics": ()},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidContentRoadmapError):
                    content_roadmap(**override)

    def test_a_roadmap_requires_a_typed_signature_solution(self):
        with self.assertRaises(ContentRoadmapDependencyError):
            content_roadmap(method="the nine steps")

    def test_a_roadmap_refuses_a_cross_tenant_signature_solution(self):
        with self.assertRaises(ContentRoadmapTenantBoundaryError):
            content_roadmap(method=signature_solution(tenant_id="client-other"))

    def test_a_roadmap_refuses_a_cross_tenant_topic(self):
        with self.assertRaises(ContentRoadmapTenantBoundaryError):
            content_roadmap(
                topics=(content_topic(tenant_id="client-other"),)
            )

    def test_a_roadmap_refuses_duplicate_topic_ids(self):
        with self.assertRaises(InvalidContentRoadmapError):
            content_roadmap(
                topics=(content_topic(), content_topic())
            )

    def test_a_roadmap_refuses_a_topic_from_a_step_the_solution_does_not_name(self):
        with self.assertRaises(ContentRoadmapDependencyError):
            content_roadmap(
                topics=(content_topic(signature_step="Enroll"),)
            )

    def test_a_roadmap_reports_the_steps_it_covers_and_misses(self):
        roadmap = content_roadmap()

        self.assertEqual(("Diagnose", "Position"), roadmap.covered_steps)
        self.assertIn("Model", roadmap.missing_steps())
        self.assertNotIn("Diagnose", roadmap.missing_steps())
        self.assertFalse(roadmap.is_complete)

    def test_a_roadmap_covering_every_step_is_complete(self):
        solution = signature_solution()
        topics = tuple(
            content_topic(
                topic_id=f"topic-{step.step_id}",
                name=f"{step.name} topic",
                signature_step=step.name,
                question=f"what does {step.name} change?",
            )
            for step in solution.steps
        )

        roadmap = content_roadmap(method=solution, topics=topics)

        self.assertEqual(9, len(roadmap.covered_steps))
        self.assertEqual((), roadmap.missing_steps())
        self.assertTrue(roadmap.is_complete)

    def test_a_roadmap_is_a_plan_not_an_observation(self):
        self.assertTrue(content_roadmap().is_plan)
        with self.assertRaises(ContentRoadmapObservationError):
            content_roadmap().as_observation(claim_id="claim-1")

    def test_a_roadmap_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            content_roadmap().owner = "someone-else"


class ContentDistributionPolicyTests(unittest.TestCase):
    def test_a_roadmap_whose_topics_reach_the_minimum_channels_passes(self):
        ContentDistributionPolicy().require_minimum_reach(content_roadmap())

    def test_a_topic_that_leaves_the_blog_alone_is_refused(self):
        under_distributed = content_roadmap(
            topics=(
                content_topic(
                    channels=(ContentChannel.BLOG, ContentChannel.YOUTUBE)
                ),
            )
        )

        with self.assertRaises(ContentDistributionError):
            ContentDistributionPolicy().require_minimum_reach(under_distributed)


if __name__ == "__main__":
    unittest.main()

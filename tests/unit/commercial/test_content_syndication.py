"""Behavioral tests for the canon Content Syndication plan (Commercial domain).

Rules under test come from SPEC.md section 12.5 (the audience-building and content
flywheel is a canon gap mapped to stages 6 and 10; the syndication/recycling
schedule is its remaining delivery asset) and section 12.3 (stage 6 content and
stage 10 audience operations), shaped by the canon's Content Blitz publish,
promote and syndicate training (canon files 29, 30 and 31):

- Content is published and then syndicated everywhere the audience can be reached,
  not left in one place: "Every piece of content you create, it'd be silly for you
  not to put that to Facebook groups, to put to your email list, your messenger
  subscribers, people who belong to your groups" and "never ever post something on
  social media once you're losing 99% of the equity of the asset you've created"
  (canon file 31).
- The schedule re-posts the same asset on a per-channel cadence: queue tools "put
  this on Twitter every three hours. Put one of these on Facebook every other
  day, put one of these on LinkedIn" (canon file 31).
- Promotion is a low fixed daily spend, the "dollar a day strategy", started at
  "$5 a day" / "$3" minimum before it is cranked up after the learning phase
  (canon files 30 and 31).
- A good content asset is recycled into derivatives: "you can create lead magnets,
  you can create content gateways ... take the audio and pull it out as a podcast"
  and an infographic that explains the post (canon file 31).

The plan is a stage 6/10 planning asset, not a new required gate kind (a
methodology-owner decision, SPEC.md section 12.5). It does not authorize
publishing or spend (SPEC.md sections 4 and 9), and it is never an observation
(SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal

from redops.contexts.commercial.domain.errors import (
    ContentSyndicationDependencyError,
    ContentSyndicationError,
    ContentSyndicationFormatError,
    ContentSyndicationObservationError,
    ContentSyndicationTenantBoundaryError,
    InvalidContentSyndicationError,
)
from redops.contexts.commercial.domain.policies import (
    ContentSyndicationPolicy,
)
from redops.contexts.commercial.domain.value_objects import (
    AUTHORITY_AMPLIFIER_BEATS,
    MINIMUM_PUBLISH_CHANNELS,
    ChannelSyndication,
    ContentRoadmap,
    ContentSyndicationPlan,
    ContentTopic,
    DailyPromotionBudget,
    RecycledFormat,
    SyndicationCadence,
    SyndicationChannel,
    TopicSyndication,
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


def daily_budget(**overrides) -> DailyPromotionBudget:
    values = {"amount": Decimal("1"), "currency": "USD"}
    values.update(overrides)
    return DailyPromotionBudget(**values)


def topic_syndication(**overrides) -> TopicSyndication:
    values = {
        "topic_id": "topic-diagnose-1",
        "channels": (
            ChannelSyndication(SyndicationChannel.EMAIL, SyndicationCadence.WEEKLY),
            ChannelSyndication(
                SyndicationChannel.FACEBOOK, SyndicationCadence.EVERY_OTHER_DAY
            ),
        ),
        "recycled_formats": (RecycledFormat.INFOGRAPHIC,),
        "promotion_budget": daily_budget(),
    }
    values.update(overrides)
    return TopicSyndication(**values)


def syndication_plan(**overrides) -> ContentSyndicationPlan:
    values = {
        "plan_id": "syndication-3f",
        "tenant_id": TENANT,
        "owner": "content-operator",
        "roadmap": content_roadmap(),
        "syndications": (
            topic_syndication(),
            topic_syndication(
                topic_id="topic-position-1",
                channels=(
                    ChannelSyndication(
                        SyndicationChannel.SOCIAL_GROUP, SyndicationCadence.WEEKLY
                    ),
                    ChannelSyndication(
                        SyndicationChannel.LINKEDIN, SyndicationCadence.DAILY
                    ),
                ),
                recycled_formats=(RecycledFormat.PODCAST_AUDIO,),
            ),
        ),
    }
    values.update(overrides)
    return ContentSyndicationPlan(**values)


class SyndicationChannelTests(unittest.TestCase):
    def test_the_canon_syndication_channels_are_named(self):
        self.assertEqual(
            {
                "email",
                "messenger",
                "social_group",
                "linkedin",
                "twitter",
                "facebook",
                "podcast",
            },
            {channel.value for channel in SyndicationChannel},
        )


class SyndicationCadenceTests(unittest.TestCase):
    def test_the_canon_cadences_are_named(self):
        self.assertEqual(
            {"multiple_daily", "daily", "every_other_day", "weekly"},
            {cadence.value for cadence in SyndicationCadence},
        )


class RecycledFormatTests(unittest.TestCase):
    def test_the_canon_recycled_formats_are_named(self):
        self.assertEqual(
            {
                "infographic",
                "lead_magnet",
                "content_gateway",
                "podcast_audio",
                "opt_in_video",
            },
            {fmt.value for fmt in RecycledFormat},
        )


class ChannelSyndicationTests(unittest.TestCase):
    def test_a_channel_syndication_requires_typed_parts(self):
        with self.assertRaises(InvalidContentSyndicationError):
            ChannelSyndication("email", SyndicationCadence.WEEKLY)
        with self.assertRaises(InvalidContentSyndicationError):
            ChannelSyndication(SyndicationChannel.EMAIL, "weekly")

    def test_a_channel_syndication_is_immutable(self):
        entry = ChannelSyndication(SyndicationChannel.EMAIL, SyndicationCadence.DAILY)
        with self.assertRaises(FrozenInstanceError):
            entry.channel = SyndicationChannel.PODCAST


class DailyPromotionBudgetTests(unittest.TestCase):
    def test_a_budget_requires_a_positive_amount_and_a_currency(self):
        self.assertEqual(Decimal("1"), daily_budget().amount)
        for override in (
            {"amount": Decimal("0")},
            {"amount": Decimal("-5")},
            {"currency": ""},
            {"currency": "  "},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidContentSyndicationError):
                    daily_budget(**override)

    def test_a_budget_refuses_a_non_decimal_amount(self):
        with self.assertRaises(InvalidContentSyndicationError):
            daily_budget(amount=1)

    def test_a_budget_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            daily_budget().amount = Decimal("5")


class TopicSyndicationTests(unittest.TestCase):
    def test_a_topic_syndication_requires_its_topic_and_channels(self):
        for override in (
            {"topic_id": ""},
            {"topic_id": "  "},
            {"channels": ()},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidContentSyndicationError):
                    topic_syndication(**override)

    def test_a_topic_syndication_requires_typed_channels(self):
        with self.assertRaises(InvalidContentSyndicationError):
            topic_syndication(channels=(("email", "weekly"),))

    def test_a_topic_syndication_refuses_a_duplicate_channel(self):
        with self.assertRaises(ContentSyndicationFormatError):
            topic_syndication(
                channels=(
                    ChannelSyndication(
                        SyndicationChannel.EMAIL, SyndicationCadence.WEEKLY
                    ),
                    ChannelSyndication(
                        SyndicationChannel.EMAIL, SyndicationCadence.DAILY
                    ),
                )
            )

    def test_a_topic_syndication_requires_a_recycled_derivative(self):
        with self.assertRaises(InvalidContentSyndicationError):
            topic_syndication(recycled_formats=())

    def test_a_topic_syndication_requires_typed_recycled_formats(self):
        with self.assertRaises(InvalidContentSyndicationError):
            topic_syndication(recycled_formats=("infographic",))

    def test_a_topic_syndication_refuses_a_duplicate_recycled_format(self):
        with self.assertRaises(ContentSyndicationFormatError):
            topic_syndication(
                recycled_formats=(RecycledFormat.INFOGRAPHIC, RecycledFormat.INFOGRAPHIC)
            )

    def test_a_topic_syndication_requires_a_typed_promotion_budget(self):
        with self.assertRaises(InvalidContentSyndicationError):
            topic_syndication(promotion_budget=Decimal("1"))

    def test_a_topic_syndication_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            topic_syndication().topic_id = "topic-other"


class ContentSyndicationPlanTests(unittest.TestCase):
    def test_a_plan_requires_its_identity_owner_roadmap_and_syndications(self):
        for override in (
            {"plan_id": ""},
            {"tenant_id": "  "},
            {"owner": ""},
            {"syndications": ()},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidContentSyndicationError):
                    syndication_plan(**override)

    def test_a_plan_requires_a_typed_content_roadmap(self):
        with self.assertRaises(ContentSyndicationDependencyError):
            syndication_plan(roadmap="the content roadmap")

    def test_a_plan_refuses_a_cross_tenant_content_roadmap(self):
        foreign = ContentRoadmap(
            roadmap_id="roadmap-other",
            tenant_id="client-other",
            owner="other-operator",
            method=signature_solution(tenant_id="client-other"),
            topics=(content_topic(tenant_id="client-other"),),
        )
        with self.assertRaises(ContentSyndicationTenantBoundaryError):
            syndication_plan(roadmap=foreign)

    def test_a_plan_refuses_a_syndication_for_a_topic_not_on_the_roadmap(self):
        with self.assertRaises(ContentSyndicationDependencyError):
            syndication_plan(
                syndications=(topic_syndication(topic_id="topic-not-on-roadmap"),)
            )

    def test_a_plan_refuses_duplicate_topic_syndications(self):
        with self.assertRaises(InvalidContentSyndicationError):
            syndication_plan(
                syndications=(topic_syndication(), topic_syndication())
            )

    def test_a_plan_refuses_an_untyped_syndication(self):
        with self.assertRaises(InvalidContentSyndicationError):
            syndication_plan(syndications=("topic-diagnose-1",))

    def test_a_plan_reports_the_topics_it_covers_and_misses(self):
        plan = syndication_plan()

        self.assertEqual(
            ("topic-diagnose-1", "topic-position-1"), plan.covered_topics
        )
        self.assertEqual((), plan.missing_topics())
        self.assertTrue(plan.is_complete)

    def test_a_plan_missing_a_topic_is_not_complete(self):
        plan = syndication_plan(syndications=(topic_syndication(),))

        self.assertEqual(("topic-diagnose-1",), plan.covered_topics)
        self.assertEqual(("topic-position-1",), plan.missing_topics())
        self.assertFalse(plan.is_complete)

    def test_a_plan_is_a_plan_not_an_observation(self):
        self.assertTrue(syndication_plan().is_plan)
        with self.assertRaises(ContentSyndicationObservationError):
            syndication_plan().as_observation(claim_id="claim-1")

    def test_a_plan_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            syndication_plan().owner = "someone-else"


class ContentSyndicationPolicyTests(unittest.TestCase):
    def test_a_multichannel_syndication_passes(self):
        ContentSyndicationPolicy().require_multichannel(syndication_plan())

    def test_a_syndication_left_on_one_platform_is_refused(self):
        single_channel = syndication_plan(
            syndications=(
                topic_syndication(
                    channels=(
                        ChannelSyndication(
                            SyndicationChannel.FACEBOOK,
                            SyndicationCadence.EVERY_OTHER_DAY,
                        ),
                    ),
                ),
            )
        )

        with self.assertRaises(ContentSyndicationError):
            ContentSyndicationPolicy().require_multichannel(single_channel)

    def test_a_syndication_reaching_an_owned_channel_passes(self):
        ContentSyndicationPolicy().require_owned_reach(syndication_plan())

    def test_a_syndication_without_an_owned_channel_is_refused(self):
        borrowed_only = syndication_plan(
            syndications=(
                topic_syndication(
                    channels=(
                        ChannelSyndication(
                            SyndicationChannel.LINKEDIN, SyndicationCadence.DAILY
                        ),
                        ChannelSyndication(
                            SyndicationChannel.TWITTER, SyndicationCadence.DAILY
                        ),
                    ),
                ),
            )
        )

        with self.assertRaises(ContentSyndicationError):
            ContentSyndicationPolicy().require_owned_reach(borrowed_only)


if __name__ == "__main__":
    unittest.main()

"""Behavioral tests for the canon's banner-ad spec and swipe reference.

Rules under test come from SPEC.md section 12.5 (the retargeting-system canon
gap: "Retargeting Roadmap, invisible opt-in, banner specs") and SPEC.md section
4, stages 8 and 10, shaped by the canon's retargeting training (canon files 33
and 34). The canon supplies a "banner ad specs and guidelines" reference
"specifically for Google's banner ad specs", the two most common display sizes
it actually runs ("the 3 by 250 and the 728"), the Facebook/Perfect Audience ad
image size ("600 by 315"), and separate banner/sidebar swipe files collected from
competitors "to give you some inspiration" (canon file 33 and canon file 34). The
artifact names each channel's required dimensions and a swipe-copy note so a
stage 8/10 campaign can size its creative and learn from observed ads; it
generates no creative and never authorizes spend (SPEC.md sections 4 and 9).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.measurement.domain.errors import (
    BannerAdCanonSpecError,
    BannerAdObservationError,
    InvalidBannerAdError,
)
from redops.contexts.measurement.domain.value_objects import (
    CANON_DISPLAY_BANNER_DIMENSIONS,
    CANON_FACEBOOK_AD_DIMENSION,
    BannerAdReference,
    BannerAdReferenceLibrary,
    BannerAdReferencePolicy,
    BannerDimension,
    RetargetingChannel,
)

TENANT = "client-3f"


def dimension(**overrides) -> BannerDimension:
    values = {"width": 300, "height": 250}
    values.update(overrides)
    return BannerDimension(**values)


def reference(**overrides) -> BannerAdReference:
    values = {
        "reference_id": "ref-google-display",
        "channel": RetargetingChannel.GOOGLE_DISPLAY,
        "dimensions": (
            BannerDimension(300, 250),
            BannerDimension(728, 90),
        ),
        "swipe_note": "collected competitor display banners for inspiration",
    }
    values.update(overrides)
    return BannerAdReference(**values)


def library(**overrides) -> BannerAdReferenceLibrary:
    values = {
        "library_id": "lib-banner-3f",
        "tenant_id": TENANT,
        "owner": "creative-operator",
        "references": (reference(),),
    }
    values.update(overrides)
    return BannerAdReferenceLibrary(**values)


class BannerDimensionTests(unittest.TestCase):
    def test_a_dimension_reports_its_pixel_label(self):
        self.assertEqual("300x250", dimension().label)
        self.assertEqual("728x90", dimension(width=728, height=90).label)

    def test_a_dimension_requires_positive_integer_sides(self):
        for overrides in (
            {"width": 0},
            {"height": 0},
            {"width": -1},
            {"height": "250"},
            {"width": True},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(InvalidBannerAdError):
                    dimension(**overrides)

    def test_a_dimension_is_immutable(self):
        banner = dimension()

        with self.assertRaises(FrozenInstanceError):
            banner.width = 728


class BannerAdReferenceTests(unittest.TestCase):
    def test_a_reference_names_its_channel_dimensions_and_swipe_note(self):
        ref = reference()

        self.assertIs(RetargetingChannel.GOOGLE_DISPLAY, ref.channel)
        self.assertEqual(("300x250", "728x90"), ref.labels)
        self.assertIn("inspiration", ref.swipe_note)

    def test_a_reference_requires_its_identity_and_swipe_note(self):
        for field in ("reference_id", "swipe_note"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidBannerAdError):
                    reference(**{field: "  "})

    def test_a_reference_requires_a_named_channel(self):
        with self.assertRaises(InvalidBannerAdError):
            reference(channel="google_display")

    def test_a_reference_requires_a_non_empty_tuple_of_dimensions(self):
        for overrides in (
            {"dimensions": ()},
            {"dimensions": [BannerDimension(300, 250)]},
            {"dimensions": "300x250"},
            {"dimensions": ("300x250",)},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(InvalidBannerAdError):
                    reference(**overrides)

    def test_a_reference_refuses_a_duplicate_dimension(self):
        with self.assertRaises(InvalidBannerAdError):
            reference(
                dimensions=(
                    BannerDimension(300, 250),
                    BannerDimension(300, 250),
                )
            )

    def test_a_reference_is_immutable(self):
        ref = reference()

        with self.assertRaises(FrozenInstanceError):
            ref.swipe_note = "other"


class BannerAdReferencePolicyTests(unittest.TestCase):
    def test_the_canon_names_the_google_display_sizes(self):
        self.assertEqual(
            (BannerDimension(300, 250), BannerDimension(728, 90)),
            CANON_DISPLAY_BANNER_DIMENSIONS,
        )

    def test_the_canon_names_the_facebook_ad_image_size(self):
        self.assertEqual(BannerDimension(600, 315), CANON_FACEBOOK_AD_DIMENSION)

    def test_google_display_must_declare_both_canon_sizes(self):
        BannerAdReferencePolicy.require_canon_sizes(reference())

    def test_google_display_missing_a_canon_size_is_refused(self):
        with self.assertRaises(BannerAdCanonSpecError):
            BannerAdReferencePolicy.require_canon_sizes(
                reference(dimensions=(BannerDimension(300, 250),))
            )

    def test_google_display_may_add_beyond_the_canon_sizes(self):
        BannerAdReferencePolicy.require_canon_sizes(
            reference(
                dimensions=(
                    BannerDimension(300, 250),
                    BannerDimension(728, 90),
                    BannerDimension(160, 600),
                )
            )
        )

    def test_facebook_channels_must_declare_the_canon_image_size(self):
        for channel in (
            RetargetingChannel.FACEBOOK_NEWSFEED,
            RetargetingChannel.FACEBOOK_RIGHT_RAIL,
        ):
            with self.subTest(channel=channel):
                BannerAdReferencePolicy.require_canon_sizes(
                    reference(
                        channel=channel,
                        dimensions=(BannerDimension(600, 315),),
                    )
                )
                with self.assertRaises(BannerAdCanonSpecError):
                    BannerAdReferencePolicy.require_canon_sizes(
                        reference(
                            channel=channel,
                            dimensions=(BannerDimension(1200, 628),),
                        )
                    )

    def test_a_canon_silent_channel_is_allowed_and_recorded_as_a_gap(self):
        twitter = reference(
            channel=RetargetingChannel.TWITTER,
            dimensions=(BannerDimension(600, 300),),
        )

        BannerAdReferencePolicy.require_canon_sizes(twitter)

    def test_the_policy_requires_a_typed_reference(self):
        with self.assertRaises(InvalidBannerAdError):
            BannerAdReferencePolicy.require_canon_sizes("ref-google-display")


class BannerAdReferenceLibraryTests(unittest.TestCase):
    def test_a_library_binds_an_owner_to_its_references(self):
        lib = library()

        self.assertEqual("creative-operator", lib.owner)
        self.assertEqual((RetargetingChannel.GOOGLE_DISPLAY,), lib.channels)
        self.assertTrue(lib.covers(RetargetingChannel.GOOGLE_DISPLAY))
        self.assertIsNotNone(
            lib.specification_for(RetargetingChannel.GOOGLE_DISPLAY)
        )
        self.assertIsNone(lib.specification_for(RetargetingChannel.TWITTER))

    def test_a_library_requires_its_identity_and_owner(self):
        for field in ("library_id", "tenant_id", "owner"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidBannerAdError):
                    library(**{field: "  "})

    def test_a_library_requires_at_least_one_typed_reference(self):
        with self.assertRaises(InvalidBannerAdError):
            library(references=())
        with self.assertRaises(InvalidBannerAdError):
            library(references=("ref-google-display",))
        with self.assertRaises(InvalidBannerAdError):
            library(references=[reference()])

    def test_a_library_refuses_a_duplicate_channel_reference(self):
        with self.assertRaises(InvalidBannerAdError):
            library(references=(reference(), reference()))

    def test_a_library_reports_the_canon_channels_it_does_not_cover(self):
        lib = library()

        self.assertEqual(
            (
                RetargetingChannel.FACEBOOK_NEWSFEED,
                RetargetingChannel.FACEBOOK_RIGHT_RAIL,
            ),
            lib.missing_canon_channels(),
        )
        self.assertFalse(lib.is_canon_complete)

    def test_a_library_covering_the_canon_channels_is_complete(self):
        lib = library(
            references=(
                reference(),
                reference(
                    reference_id="ref-facebook-newsfeed",
                    channel=RetargetingChannel.FACEBOOK_NEWSFEED,
                    dimensions=(BannerDimension(600, 315),),
                ),
                reference(
                    reference_id="ref-facebook-right-rail",
                    channel=RetargetingChannel.FACEBOOK_RIGHT_RAIL,
                    dimensions=(BannerDimension(600, 315),),
                ),
            )
        )

        self.assertEqual((), lib.missing_canon_channels())
        self.assertTrue(lib.is_canon_complete)

    def test_a_library_is_a_reference_and_never_an_observation(self):
        lib = library()

        self.assertTrue(lib.is_reference)
        with self.assertRaises(BannerAdObservationError):
            lib.as_observation(claim_id="claim-banner-library")

    def test_a_library_is_immutable(self):
        lib = library()

        with self.assertRaises(FrozenInstanceError):
            lib.owner = "other"


if __name__ == "__main__":
    unittest.main()

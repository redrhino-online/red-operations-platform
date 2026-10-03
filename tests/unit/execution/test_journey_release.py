"""Behavioral tests for the ``JourneyRelease`` core aggregate (Execution domain).

Rules under test come from SPEC.md section 3, which names ``JourneyRelease``
(assets, routing, configuration digest, rollback ref) as a core aggregate with
the invariant "Launch needs signed readiness and authorized release", and from
SPEC.md section 4, which requires launch integration checks, a customer path dry
run, a named operator and a rollback, and which keeps a previous deployed
release historically identifiable. The release is grounded on the stage 9
``LaunchQA`` ("Launch Approved"); the canon has no dedicated journey release
file, so the SPEC governs the shape (SPEC.md section 12.1).

A release never authorizes live traffic (that is a stage 10 observation) and
never confers human approval; it only records the authorized release.
"""

import unittest
from dataclasses import FrozenInstanceError, replace

from redops.contexts.execution.domain.errors import (
    InvalidJourneyReleaseError,
    JourneyReleaseAuthorityError,
    JourneyReleaseDependencyError,
    JourneyReleaseReadinessError,
    JourneyReleaseTenantBoundaryError,
)
from redops.contexts.execution.domain.journey_release import JourneyRelease
from redops.contexts.execution.domain.value_objects import (
    LaunchQAState,
    TrafficAuthorization,
)
from redops.contexts.governance.domain.value_objects import StageAssetVersion

from .fixtures import TENANT, launch_qa, ready_for_traffic

OTHER_TENANT = "client-other"


def asset(kind: str = "pages", **overrides) -> StageAssetVersion:
    values = {
        "asset_id": f"asset-{kind}",
        "tenant_id": TENANT,
        "kind": kind,
        "version": 1,
    }
    values.update(overrides)
    return StageAssetVersion(**values)


def release(qa=None, assets=None, **overrides) -> JourneyRelease:
    values = {
        "release_id": "release-3f",
        "tenant_id": TENANT,
        "qa": ready_for_traffic() if qa is None else qa,
        "assets": (asset("pages"), asset("forms")) if assets is None else assets,
        "routing": "route://3f/main",
        "configuration_digest": "sha256:config",
        "rollback_ref": "release://3f/previous",
    }
    values.update(overrides)
    return JourneyRelease(**values)


class JourneyReleaseTests(unittest.TestCase):
    def test_a_signed_ready_authorized_qa_produces_a_release(self):
        accepted = release()
        self.assertEqual(accepted.tenant_id, TENANT)
        self.assertEqual(accepted.released_kinds, {"pages", "forms"})
        self.assertTrue(accepted.is_signed_ready)
        self.assertTrue(accepted.is_authorized)

    def test_a_release_must_be_grounded_on_a_typed_launch_qa(self):
        with self.assertRaises(JourneyReleaseDependencyError):
            release(qa="ready")

    def test_a_qa_not_ready_for_traffic_cannot_authorize_a_release(self):
        with self.assertRaises(JourneyReleaseReadinessError):
            release(qa=launch_qa())

    def test_a_ready_qa_without_authorization_cannot_authorize_a_release(self):
        ready = replace(launch_qa(), state=LaunchQAState.READY_FOR_TRAFFIC)
        with self.assertRaises(JourneyReleaseReadinessError):
            release(qa=ready)

    def test_an_authorization_by_a_non_designated_actor_is_refused(self):
        ready = ready_for_traffic()
        rogue = replace(
            ready,
            authorization=TrafficAuthorization(
                authorized_by="rogue",
                intended_use=ready.authorization.intended_use,
                authorized_on=ready.authorization.authorized_on,
            ),
        )
        with self.assertRaises(JourneyReleaseAuthorityError):
            release(qa=rogue)

    def test_a_cross_tenant_qa_is_refused(self):
        with self.assertRaises(JourneyReleaseTenantBoundaryError):
            release(tenant_id=OTHER_TENANT)

    def test_a_cross_tenant_asset_is_refused(self):
        with self.assertRaises(JourneyReleaseTenantBoundaryError):
            release(assets=(asset("pages", tenant_id=OTHER_TENANT),))

    def test_an_empty_asset_package_is_refused(self):
        with self.assertRaises(InvalidJourneyReleaseError):
            release(assets=())

    def test_two_versions_of_one_kind_are_refused(self):
        with self.assertRaises(InvalidJourneyReleaseError):
            release(
                assets=(
                    asset("pages", version=1),
                    asset("pages", asset_id="asset-pages-v2", version=2),
                )
            )

    def test_blank_release_identity_fields_are_refused(self):
        for field in (
            "release_id",
            "routing",
            "configuration_digest",
            "rollback_ref",
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidJourneyReleaseError):
                    release(**{field: "  "})

    def test_a_release_is_frozen(self):
        accepted = release()
        with self.assertRaises(FrozenInstanceError):
            accepted.release_id = "release-other"

    def test_a_launch_qa_type_is_enforced_before_attribute_access(self):
        # A non-LaunchQA groundings must not leak an AttributeError.
        with self.assertRaises(JourneyReleaseDependencyError):
            JourneyRelease(
                release_id="release-3f",
                tenant_id=TENANT,
                qa=object(),
                assets=(asset("pages"),),
                routing="route://3f/main",
                configuration_digest="sha256:config",
                rollback_ref="release://3f/previous",
            )


if __name__ == "__main__":
    unittest.main()

"""Behavioral tests for the authorized journey release store (Execution application).

Rules under test come from SPEC.md sections 3, 4 and 9:
- A passing gate pins exact approved asset versions and intended use, and the
  ``JourneyRelease`` invariant is "launch needs signed readiness and authorized
  release" (SPEC.md section 3).
- A previous deployed release stays historically identifiable, and a change is a
  new identity rather than an overwrite (SPEC.md section 4).
- A journey release is a client resource: it must carry its tenant on every read
  and write, and one client's release cannot be resolved for another (SPEC.md
  sections 3 and 9).

The ``/journeys`` surface resolves the exact release from this seam.
"""

from __future__ import annotations

import unittest

from redops.contexts.execution.domain.errors import (
    JourneyReleaseTenantBoundaryError,
    JourneyReleaseVersionConflictError,
    JourneyReleaseVersionTenantBoundaryError,
)
from redops.contexts.execution.domain.journey_release import JourneyRelease
from redops.contexts.execution.infrastructure.mappers import (
    journey_release_from_payload,
    journey_release_to_payload,
)
from redops.contexts.execution.infrastructure.repositories import (
    InMemoryJourneyReleaseRepository,
)
from redops.contexts.governance.domain.value_objects import StageAssetVersion

from .fixtures import TENANT, ready_for_traffic

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


def release(**overrides) -> JourneyRelease:
    values = {
        "release_id": "release-3f",
        "tenant_id": TENANT,
        "qa": ready_for_traffic(),
        "assets": (asset("pages"), asset("forms")),
        "routing": "route://3f/main",
        "configuration_digest": "sha256:config",
        "rollback_ref": "release://3f/previous",
    }
    values.update(overrides)
    return JourneyRelease(**values)


class JourneyReleaseRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryJourneyReleaseRepository()

    def test_a_saved_release_is_resolved_by_its_id(self):
        stored = release()

        self.repository.save(stored)

        self.assertEqual(stored, self.repository.get(TENANT, stored.release_id))

    def test_unknown_release_resolves_to_none(self):
        self.repository.save(release())

        self.assertIsNone(self.repository.get(TENANT, "release-other"))

    def test_a_different_body_under_the_same_id_is_refused(self):
        self.repository.save(release())

        with self.assertRaises(JourneyReleaseVersionConflictError):
            self.repository.save(release(routing="route://3f/changed"))

    def test_re_saving_the_identical_release_is_idempotent(self):
        stored = release()
        self.repository.save(stored)

        self.repository.save(stored)

        self.assertEqual(stored, self.repository.get(TENANT, stored.release_id))

    def test_a_blank_tenant_is_refused_on_read(self):
        stored = release()
        self.repository.save(stored)

        for tenant in ("", "   "):
            with self.subTest(tenant=tenant):
                with self.assertRaises(JourneyReleaseVersionTenantBoundaryError):
                    self.repository.get(tenant, stored.release_id)

    def test_one_clients_release_is_not_visible_to_another(self):
        self.repository.save(release())

        self.assertIsNone(self.repository.get(OTHER_TENANT, "release-3f"))
        self.assertEqual((), self.repository.list(OTHER_TENANT))

    def test_listing_returns_only_the_tenants_releases(self):
        self.repository.save(release())
        self.repository.save(
            release(
                release_id="release-3f-2",
                assets=(asset("pages", asset_id="asset-pages-2"),),
            )
        )

        listed = self.repository.list(TENANT)

        self.assertEqual(
            {"release-3f", "release-3f-2"},
            {item.release_id for item in listed},
        )


class JourneyReleaseMapperTests(unittest.TestCase):
    """The durable payload round-trips the full authorized release aggregate.

    SPEC.md section 4: a passing gate pins the exact approved version, so the
    payload the PostgreSQL adapter stores must rebuild an equal release -- its
    grounding authorized stage 9 QA and every exact released asset version
    included -- rather than a laxer release that would read back after a restart.
    """

    def test_an_authorized_release_round_trips_exactly(self):
        stored = release()

        self.assertEqual(
            stored,
            journey_release_from_payload(journey_release_to_payload(stored)),
        )

    def test_the_qa_and_assets_survive(self):
        stored = release()

        rebuilt = journey_release_from_payload(
            journey_release_to_payload(stored)
        )

        self.assertTrue(rebuilt.is_signed_ready)
        self.assertTrue(rebuilt.is_authorized)
        self.assertEqual(stored.qa, rebuilt.qa)
        self.assertEqual(stored.assets, rebuilt.assets)
        self.assertEqual(stored.released_kinds, {"pages", "forms"})

    def test_a_stored_payload_the_domain_would_reject_raises(self):
        payload = journey_release_to_payload(release())
        payload["assets"] = [
            {
                "asset_id": "asset-pages",
                "tenant_id": OTHER_TENANT,
                "kind": "pages",
                "version": 1,
            }
        ]

        with self.assertRaises(JourneyReleaseTenantBoundaryError):
            journey_release_from_payload(payload)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

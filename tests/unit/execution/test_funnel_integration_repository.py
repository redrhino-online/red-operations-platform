"""Behavioral tests for the completed funnel store (Execution application).

Rules under test come from SPEC.md sections 3, 4 and 9:
- A passing gate pins exact approved asset versions and intended use (SPEC.md
  section 3).
- A previous approved version stays historically identifiable, and a change is a
  new revision rather than an overwrite (SPEC.md section 4).
- A funnel is a client resource: it must carry its tenant on every read and
  write, and one client's funnel cannot be resolved for another (SPEC.md
  sections 3 and 9).

The stage 9 and 10 gates resolve the exact stage 8 funnel a prior gate completed
from this seam instead of trusting a repeated request body.
"""

from __future__ import annotations

import unittest

from redops.contexts.execution.domain.errors import (
    FunnelDependencyError,
    FunnelReadinessError,
    FunnelVersionConflictError,
    FunnelVersionTenantBoundaryError,
)
from redops.contexts.execution.infrastructure.mappers import (
    funnel_integration_from_payload,
    funnel_integration_to_payload,
)
from redops.contexts.execution.infrastructure.repositories import (
    InMemoryFunnelIntegrationRepository,
)

from .fixtures import (
    TENANT,
    complete_funnel,
    funnel_integration,
)


class FunnelIntegrationRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryFunnelIntegrationRepository()

    def test_a_saved_complete_funnel_is_resolved_by_its_id(self):
        funnel = complete_funnel()

        self.repository.save(funnel)

        self.assertEqual(
            funnel,
            self.repository.get(TENANT, funnel.integration_id),
        )

    def test_unknown_funnel_resolves_to_none(self):
        self.repository.save(complete_funnel())

        self.assertIsNone(self.repository.get(TENANT, "funnel-other"))

    def test_a_different_body_under_the_same_id_is_refused(self):
        self.repository.save(complete_funnel())

        with self.assertRaises(FunnelVersionConflictError):
            self.repository.save(complete_funnel(owner="a different owner"))

    def test_re_saving_the_identical_funnel_is_idempotent(self):
        funnel = complete_funnel()
        self.repository.save(funnel)

        self.repository.save(funnel)

        self.assertEqual(
            funnel,
            self.repository.get(TENANT, funnel.integration_id),
        )

    def test_a_funnel_without_completion_cannot_be_stored(self):
        with self.assertRaises(FunnelReadinessError):
            self.repository.save(funnel_integration())

    def test_a_blank_tenant_is_refused_on_read(self):
        funnel = complete_funnel()
        self.repository.save(funnel)

        for tenant in ("", "   "):
            with self.subTest(tenant=tenant):
                with self.assertRaises(FunnelVersionTenantBoundaryError):
                    self.repository.get(tenant, funnel.integration_id)

    def test_one_clients_funnel_is_not_visible_to_another(self):
        self.repository.save(complete_funnel())

        self.assertIsNone(self.repository.get("client-other", "funnel-3f"))


class FunnelIntegrationMapperTests(unittest.TestCase):
    """The durable payload round-trips the full completed funnel aggregate.

    SPEC.md section 4: a passing gate pins the exact approved version, so the
    payload the PostgreSQL adapter stores must rebuild an equal funnel -- its
    grounding amplifier, its thirteen asset references and its pinned prospect
    path dry run included -- rather than a laxer funnel that would read back after
    a restart.
    """

    def test_a_complete_funnel_round_trips_exactly(self):
        funnel = complete_funnel()

        self.assertEqual(
            funnel,
            funnel_integration_from_payload(
                funnel_integration_to_payload(funnel)
            ),
        )

    def test_the_grounding_amplifier_and_dry_run_survive_the_round_trip(self):
        funnel = complete_funnel()

        rebuilt = funnel_integration_from_payload(
            funnel_integration_to_payload(funnel)
        )

        self.assertTrue(rebuilt.is_complete)
        self.assertEqual(funnel.amplifier, rebuilt.amplifier)
        self.assertTrue(rebuilt.amplifier.is_approved)
        self.assertEqual(funnel.dry_run, rebuilt.dry_run)
        self.assertTrue(rebuilt.dry_run.is_complete)

    def test_a_stored_payload_the_domain_would_reject_raises(self):
        payload = funnel_integration_to_payload(complete_funnel())
        payload["tenant_id"] = "client-other"

        with self.assertRaises(FunnelDependencyError):
            funnel_integration_from_payload(payload)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

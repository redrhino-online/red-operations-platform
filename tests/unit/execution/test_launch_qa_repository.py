"""Behavioral tests for the authorized launch QA store (Execution application).

Rules under test come from SPEC.md sections 3, 4 and 9:
- A passing gate pins exact approved asset versions and intended use (SPEC.md
  section 3).
- A previous approved version stays historically identifiable, and a change is a
  new revision rather than an overwrite (SPEC.md section 4).
- A launch QA is a client resource: it must carry its tenant on every read and
  write, and one client's QA cannot be resolved for another (SPEC.md sections 3
  and 9).

The stage 10 gate resolves the exact stage 9 QA a prior gate authorized from this
seam instead of trusting a repeated request body.
"""

from __future__ import annotations

import unittest

from redops.contexts.execution.domain.errors import (
    LaunchQADependencyError,
    LaunchQAReadinessError,
    LaunchQAVersionConflictError,
    LaunchQAVersionTenantBoundaryError,
)
from redops.contexts.execution.infrastructure.mappers import (
    launch_qa_from_payload,
    launch_qa_to_payload,
)
from redops.contexts.execution.infrastructure.repositories import (
    InMemoryLaunchQARepository,
)

from .fixtures import TENANT, launch_qa, ready_for_traffic


class LaunchQARepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryLaunchQARepository()

    def test_a_saved_authorized_qa_is_resolved_by_its_id(self):
        qa = ready_for_traffic()

        self.repository.save(qa)

        self.assertEqual(qa, self.repository.get(TENANT, qa.qa_id))

    def test_unknown_qa_resolves_to_none(self):
        self.repository.save(ready_for_traffic())

        self.assertIsNone(self.repository.get(TENANT, "qa-other"))

    def test_a_different_body_under_the_same_id_is_refused(self):
        self.repository.save(ready_for_traffic())

        with self.assertRaises(LaunchQAVersionConflictError):
            self.repository.save(ready_for_traffic(owner="a different owner"))

    def test_re_saving_the_identical_qa_is_idempotent(self):
        qa = ready_for_traffic()
        self.repository.save(qa)

        self.repository.save(qa)

        self.assertEqual(qa, self.repository.get(TENANT, qa.qa_id))

    def test_a_qa_without_traffic_authorization_cannot_be_stored(self):
        with self.assertRaises(LaunchQAReadinessError):
            self.repository.save(launch_qa())

    def test_a_blank_tenant_is_refused_on_read(self):
        qa = ready_for_traffic()
        self.repository.save(qa)

        for tenant in ("", "   "):
            with self.subTest(tenant=tenant):
                with self.assertRaises(LaunchQAVersionTenantBoundaryError):
                    self.repository.get(tenant, qa.qa_id)

    def test_one_clients_qa_is_not_visible_to_another(self):
        self.repository.save(ready_for_traffic())

        self.assertIsNone(self.repository.get("client-other", "qa-3f"))

    def test_list_returns_the_tenants_qas_in_id_order(self):
        self.repository.save(ready_for_traffic(qa_id="qa-b"))
        self.repository.save(ready_for_traffic(qa_id="qa-a"))

        listed = self.repository.list(TENANT)

        self.assertEqual(["qa-a", "qa-b"], [qa.qa_id for qa in listed])

    def test_a_blank_tenant_is_refused_on_list(self):
        for tenant in ("", "   "):
            with self.subTest(tenant=tenant):
                with self.assertRaises(LaunchQAVersionTenantBoundaryError):
                    self.repository.list(tenant)


class LaunchQAMapperTests(unittest.TestCase):
    """The durable payload round-trips the full authorized QA aggregate.

    SPEC.md section 4: a passing gate pins the exact approved version, so the
    payload the PostgreSQL adapter stores must rebuild an equal QA -- its grounded
    stage 8 funnel, its sixteen-check evidence, its compliance package and its
    pinned traffic authorization included -- rather than a laxer QA that would read
    back after a restart.
    """

    def test_an_authorized_qa_round_trips_exactly(self):
        qa = ready_for_traffic()

        self.assertEqual(qa, launch_qa_from_payload(launch_qa_to_payload(qa)))

    def test_the_funnel_checks_compliance_and_authorization_survive(self):
        qa = ready_for_traffic()

        rebuilt = launch_qa_from_payload(launch_qa_to_payload(qa))

        self.assertTrue(rebuilt.is_ready_for_traffic)
        self.assertEqual(qa.funnel, rebuilt.funnel)
        self.assertTrue(rebuilt.funnel.is_complete)
        self.assertEqual(qa.checks, rebuilt.checks)
        self.assertEqual(qa.compliance, rebuilt.compliance)
        self.assertEqual(qa.authorization, rebuilt.authorization)

    def test_a_stored_payload_the_domain_would_reject_raises(self):
        payload = launch_qa_to_payload(ready_for_traffic())
        payload["tenant_id"] = "client-other"

        with self.assertRaises(LaunchQADependencyError):
            launch_qa_from_payload(payload)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

"""Behavioral tests for the approved amplifier store (Production application).

Rules under test come from SPEC.md sections 3, 4 and 9:
- A passing gate pins exact approved asset versions and intended use (SPEC.md
  section 3).
- A previous approved version stays historically identifiable, and a change is a
  new revision rather than an overwrite (SPEC.md section 4).
- An amplifier is a client resource: it must carry its tenant on every read and
  write, and one client's amplifier cannot be resolved for another (SPEC.md
  sections 3 and 9).

The stage 8 to 10 gates resolve the exact stage 7 amplifier a prior gate approved
from this seam instead of trusting a repeated request body.
"""

from __future__ import annotations

import unittest

from redops.contexts.production.domain.errors import (
    AuthorityAmplifierDependencyError,
    AuthorityAmplifierReadinessError,
    AuthorityAmplifierVersionConflictError,
    AuthorityAmplifierVersionTenantBoundaryError,
)
from redops.contexts.production.infrastructure.mappers import (
    authority_amplifier_from_payload,
    authority_amplifier_to_payload,
)
from redops.contexts.production.infrastructure.repositories import (
    InMemoryAuthorityAmplifierRepository,
)

from .fixtures import (
    TENANT,
    approved_amplifier,
    script_approved_amplifier,
)


class AuthorityAmplifierRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryAuthorityAmplifierRepository()

    def test_a_saved_approved_amplifier_is_resolved_by_its_id(self):
        amplifier = approved_amplifier()

        self.repository.save(amplifier)

        self.assertEqual(
            amplifier,
            self.repository.get(TENANT, amplifier.amplifier_id),
        )

    def test_unknown_amplifier_resolves_to_none(self):
        self.repository.save(approved_amplifier())

        self.assertIsNone(self.repository.get(TENANT, "amplifier-other"))

    def test_a_different_body_under_the_same_id_is_refused(self):
        self.repository.save(approved_amplifier())

        with self.assertRaises(AuthorityAmplifierVersionConflictError):
            self.repository.save(
                approved_amplifier(owner="a different owner")
            )

    def test_re_saving_the_identical_amplifier_is_idempotent(self):
        amplifier = approved_amplifier()
        self.repository.save(amplifier)

        self.repository.save(amplifier)

        self.assertEqual(
            amplifier,
            self.repository.get(TENANT, amplifier.amplifier_id),
        )

    def test_an_amplifier_without_creative_acceptance_cannot_be_stored(self):
        with self.assertRaises(AuthorityAmplifierReadinessError):
            self.repository.save(script_approved_amplifier())

    def test_a_blank_tenant_is_refused_on_read(self):
        amplifier = approved_amplifier()
        self.repository.save(amplifier)

        for tenant in ("", "   "):
            with self.subTest(tenant=tenant):
                with self.assertRaises(
                    AuthorityAmplifierVersionTenantBoundaryError
                ):
                    self.repository.get(tenant, amplifier.amplifier_id)

    def test_one_clients_amplifier_is_not_visible_to_another(self):
        self.repository.save(approved_amplifier())

        self.assertIsNone(
            self.repository.get("client-other", "amplifier-3f")
        )


class AuthorityAmplifierMapperTests(unittest.TestCase):
    """The durable payload round-trips the full approved amplifier aggregate.

    SPEC.md section 4: a passing gate pins the exact approved version, so the
    payload the PostgreSQL adapter stores must rebuild an equal amplifier -- its
    grounding message, its canonical script, its visual package and both distinct
    approvals included -- rather than a laxer amplifier that would read back after
    a restart.
    """

    def test_an_approved_amplifier_round_trips_exactly(self):
        amplifier = approved_amplifier()

        self.assertEqual(
            amplifier,
            authority_amplifier_from_payload(
                authority_amplifier_to_payload(amplifier)
            ),
        )

    def test_the_grounding_message_and_visuals_survive_the_round_trip(self):
        amplifier = approved_amplifier()

        rebuilt = authority_amplifier_from_payload(
            authority_amplifier_to_payload(amplifier)
        )

        self.assertEqual(amplifier.message, rebuilt.message)
        self.assertTrue(rebuilt.message.is_approved)
        self.assertEqual(amplifier.visuals, rebuilt.visuals)
        self.assertTrue(rebuilt.is_approved)
        self.assertIsNotNone(rebuilt.script_approval)

    def test_a_stored_payload_the_domain_would_reject_raises(self):
        payload = authority_amplifier_to_payload(approved_amplifier())
        payload["tenant_id"] = "client-other"

        with self.assertRaises(AuthorityAmplifierDependencyError):
            authority_amplifier_from_payload(payload)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

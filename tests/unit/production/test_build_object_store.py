"""Behavioral tests for the durable BuildObject store (SPEC.md sections 3 and 4).

SPEC.md section 3 makes a BuildObject the unit of production work and requires
every child resource to belong to exactly one client; section 9 requires
``tenant_id`` on every tenant resource. These tests exercise the port contract
through the in-memory adapter and the payload mapper: a build is stored and
reloaded with its identity, owner, next action, state, blockers, refs and its
recorded transition history, and an unscoped read or write is refused.
"""

from __future__ import annotations

import unittest
from datetime import date

from redops.contexts.production.domain.entities import BuildObject
from redops.contexts.production.domain.errors import (
    BuildTenantBoundaryError,
    InvalidBuildError,
)
from redops.contexts.production.domain.value_objects import BuildState
from redops.contexts.production.infrastructure.mappers import (
    build_from_payload,
    build_to_payload,
)
from redops.contexts.production.infrastructure.repositories import (
    InMemoryBuildObjectRepository,
)

TENANT = "client-3f"
OTHER_TENANT = "client-other"
TODAY = date(2026, 10, 3)


def build_object(**overrides) -> BuildObject:
    values = {
        "build_id": "build-1",
        "tenant_id": TENANT,
        "build_type": "authority-amplifier-video",
        "purpose": "stage 7 creative",
        "audience": "3f prospects",
        "owner": "production-manager",
        "next_action": "record the video",
        "refs": frozenset({"authority-amplifier-script@1"}),
    }
    values.update(overrides)
    return BuildObject(**values)


class BuildObjectStoreTests(unittest.TestCase):
    def test_a_saved_build_is_resolved_for_its_own_tenant(self) -> None:
        store = InMemoryBuildObjectRepository()
        store.save(build_object())

        found = store.get(TENANT, "build-1")

        self.assertIsNotNone(found)
        self.assertEqual("production-manager", found.owner)
        self.assertEqual("record the video", found.next_action)
        self.assertIs(BuildState.IDENTIFIED, found.state)

    def test_a_build_is_not_resolved_for_another_tenant(self) -> None:
        store = InMemoryBuildObjectRepository()
        store.save(build_object())

        self.assertIsNone(store.get(OTHER_TENANT, "build-1"))
        self.assertEqual((), store.list(OTHER_TENANT))

    def test_an_unscoped_read_or_write_is_refused(self) -> None:
        store = InMemoryBuildObjectRepository()

        with self.assertRaises(BuildTenantBoundaryError):
            store.get("   ", "build-1")
        with self.assertRaises(InvalidBuildError):
            build_object(tenant_id="")

    def test_list_returns_only_the_tenant_builds_ordered_by_id(self) -> None:
        store = InMemoryBuildObjectRepository()
        store.save(build_object(build_id="build-b"))
        store.save(build_object(build_id="build-a"))
        store.save(build_object(build_id="build-x", tenant_id=OTHER_TENANT))

        listed = store.list(TENANT)

        self.assertEqual(("build-a", "build-b"), tuple(b.build_id for b in listed))

    def test_a_transition_history_survives_a_round_trip(self) -> None:
        build = build_object()
        build.mark_ready(
            actor="production-manager",
            reason="sources delivered",
            on=TODAY,
            correlation_id="corr-1",
        )

        reloaded = build_from_payload(build_to_payload(build))

        self.assertIs(BuildState.READY, reloaded.state)
        self.assertEqual(1, len(reloaded.transitions))
        transition = reloaded.transitions[0]
        self.assertEqual("production-manager", transition.actor)
        self.assertIs(BuildState.IDENTIFIED, transition.old_state)
        self.assertIs(BuildState.READY, transition.new_state)

    def test_a_saved_build_is_replaced_by_its_next_snapshot(self) -> None:
        store = InMemoryBuildObjectRepository()
        build = build_object()
        store.save(build)
        build.mark_ready(
            actor="production-manager",
            reason="sources delivered",
            on=TODAY,
            correlation_id="corr-1",
        )

        store.save(build)

        self.assertIs(BuildState.READY, store.get(TENANT, "build-1").state)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

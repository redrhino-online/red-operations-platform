"""Behavioral tests for BuildObject optimistic versioning (SPEC.md section 7).

SPEC.md section 7: "optimistic version checking returns conflict on stale
updates." A BuildObject is a live aggregate (SPEC.md section 4), so every
mutation advances its version and a caller that read an older version is refused
rather than silently overwriting a newer state. The version is the aggregate's
own monotonic counter, not an asset version: it exists so two writers cannot
clobber each other's build edits.
"""

import unittest
from datetime import date

from redops.contexts.production.domain.entities import BuildObject
from redops.contexts.production.domain.errors import (
    BuildObjectVersionConflictError,
    InvalidBuildError,
)
from redops.contexts.production.domain.value_objects import BuildState

TODAY = date(2026, 10, 6)
CORRELATION = "corr-build-version-1"


def build_object(**overrides) -> BuildObject:
    values = {
        "build_id": "build-1",
        "tenant_id": "3fmindset",
        "build_type": "authority-amplifier-video",
        "purpose": "stage 7 creative",
        "audience": "3f prospects",
        "owner": "production-manager",
        "next_action": "record the video",
        "refs": frozenset({"authority-amplifier-script@1"}),
    }
    values.update(overrides)
    return BuildObject(**values)


class BuildVersionTests(unittest.TestCase):
    def test_a_new_build_starts_at_version_one(self):
        self.assertEqual(1, build_object().version)

    def test_each_mutation_advances_the_version(self):
        build = build_object()

        build.add_blocker("waiting on footage")
        self.assertEqual(2, build.version)

        build.remove_blocker("waiting on footage")
        self.assertEqual(3, build.version)

        build.reassign_owner("production-manager-2")
        self.assertEqual(4, build.version)

        build.set_next_action("record the video")
        self.assertEqual(5, build.version)

        build.mark_ready(
            actor="specialist-1",
            reason="footage arrived",
            on=TODAY,
            correlation_id=CORRELATION,
        )
        self.assertEqual(6, build.version)
        self.assertIs(BuildState.READY, build.state)

    def test_require_version_accepts_the_current_version(self):
        build = build_object()

        build.require_version(1)

        self.assertEqual(1, build.version)

    def test_require_version_refuses_a_stale_version_without_changing_state(self):
        build = build_object()
        build.add_blocker("waiting on footage")

        with self.assertRaises(BuildObjectVersionConflictError):
            build.require_version(1)

        self.assertEqual(2, build.version)
        self.assertIn("waiting on footage", build.blockers)

    def test_require_version_refuses_a_non_positive_version(self):
        with self.assertRaises(InvalidBuildError):
            build_object().require_version(0)

    def test_require_version_refuses_a_boolean(self):
        with self.assertRaises(InvalidBuildError):
            build_object().require_version(True)

    def test_a_non_positive_constructed_version_is_rejected(self):
        with self.assertRaises(InvalidBuildError):
            build_object(version=0)

    def test_transition_to_advances_the_version_and_records_the_transition(self):
        build = build_object()

        transition = build.transition_to(
            BuildState.READY,
            actor="specialist-1",
            reason="footage arrived",
            on=TODAY,
            correlation_id=CORRELATION,
        )

        self.assertEqual(2, build.version)
        self.assertIs(BuildState.READY, build.state)
        self.assertIs(BuildState.IDENTIFIED, transition.old_state)
        self.assertIs(BuildState.READY, transition.new_state)


if __name__ == "__main__":
    unittest.main()

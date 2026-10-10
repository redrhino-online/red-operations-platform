"""Behavioral tests for the K10 RED runtime-store seed.

Item K10 (IMPLEMENTATION_PLAN.md) seeds the runtime Departments/Council/People
stores RED: the nine agents' charters become departments, the chartered
capability slots 10 and 11 stay proposal-only, and the generic C-suite defaults
are gone so the surfaces render RED only (SPEC.md section 14 condition 7,
ADR 0006). The seed drives the vendored departments store through its public
API, so it is idempotent: a rerun changes nothing.

The tests skip cleanly when the vendored ``openexecutive`` package is not
importable (the domain-only interpreter runs the suite without it).
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HAS_OPENEXECUTIVE = importlib.util.find_spec("openexecutive") is not None
SKIP_REASON = "the runtime-store seed needs the vendored openexecutive package"

# The generic C-suite defaults `departments.store.seed_default_departments`
# inserts on a fresh database (departments/charters DEFAULT_DEPARTMENTS).
GENERIC_SLUGS = (
    "strategy",
    "finance",
    "hr",
    "legal",
    "operations",
    "marketing",
    "product",
    "board_comms",
)

# RED's roster: the nine section 5 agents plus the chartered proposal-only
# capability slots 10 and 11 (ADR 0006).
RED_TITLES = (
    "Discovery and Diagnosis",
    "IP Structuring",
    "Offer and Journey Design",
    "Knowledge Management",
    "Governance and Approval",
    "Business Asset Production",
    "Campaign and Journey Execution",
    "Insight and Performance",
    "IP Portfolio Development",
    "Client Success and Engagement Health",
    "Assurance, Risk and Compliance",
)

SLOT_TITLES = ("Client Success and Engagement Health", "Assurance, Risk and Compliance")


@unittest.skipUnless(HAS_OPENEXECUTIVE, SKIP_REASON)
class SeedRedStoresTests(unittest.TestCase):
    """The seed makes the runtime departments RED once and a rerun changes nothing."""

    def setUp(self) -> None:
        from redops.seed_red_stores import seed_red_departments

        self.seed = seed_red_departments
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db_path = Path(tmp.name) / "episodic_memory.db"

    def _states(self):
        from openexecutive.departments import store

        return store.list_departments(self.db_path)

    def test_seeds_red_departments_and_removes_the_generic_c_suite(self) -> None:
        self.seed(self.db_path)

        titles = [state.config.title for state in self._states()]
        for title in RED_TITLES:
            self.assertIn(title, titles, title)
        slugs = [state.config.slug for state in self._states()]
        for slug in GENERIC_SLUGS:
            self.assertNotIn(slug, slugs, slug)
        self.assertEqual(len(self._states()), len(RED_TITLES))

    def test_rerun_changes_nothing(self) -> None:
        self.seed(self.db_path)

        def snapshot():
            return [
                (
                    state.config.slug,
                    state.config.title,
                    state.config.specialist_key,
                    state.config.charter.mission,
                    state.config.charter.scope,
                    state.config.charter.out_of_scope,
                )
                for state in self._states()
            ]

        before = snapshot()
        summary = self.seed(self.db_path)
        self.assertEqual(snapshot(), before)
        self.assertEqual(summary["created"], [])
        self.assertEqual(summary["removed"], [])
        self.assertEqual(summary["updated"], [])

    def test_capability_slots_are_proposal_only(self) -> None:
        from openexecutive.departments.models import AuthorityLevel

        self.seed(self.db_path)

        for title in SLOT_TITLES:
            state = next(
                (s for s in self._states() if s.config.title == title), None
            )
            self.assertIsNotNone(state, title)
            self.assertIsNone(state.config.specialist_key, title)
            self.assertEqual(
                state.config.authority_level, AuthorityLevel.PROPOSE_ONLY, title
            )

    def test_nine_specialists_map_to_the_red_router(self) -> None:
        from openexecutive.agents.redops_agents import RED_SPECIALIST_AREAS

        self.seed(self.db_path)

        keys = {
            state.config.specialist_key
            for state in self._states()
            if state.config.specialist_key
        }
        self.assertEqual(keys, set(RED_SPECIALIST_AREAS))

    def test_charter_mission_comes_from_the_agent_charter(self) -> None:
        self.seed(self.db_path)

        state = next(
            (s for s in self._states() if s.config.title == "Discovery and Diagnosis"),
            None,
        )
        self.assertIsNotNone(state)
        self.assertIn("Establish what is true", state.config.charter.mission)
        self.assertTrue(state.config.charter.scope)
        self.assertTrue(state.config.charter.out_of_scope)


if __name__ == "__main__":
    unittest.main()

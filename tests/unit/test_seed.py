"""Behavioral tests for the K1 3F pilot workspace seed.

Item K1 (IMPLEMENTATION_PLAN.md) seeds the ``3fmindset`` pilot workspace end to
end through the real domain use cases so the single-shell cockpit renders real
data. SPEC.md section 1 makes the 3F pilot the first client, section 4 makes the
stage 0-10 pipeline the product, section 6 requires the API to call use cases
through ports, and section 7 makes the stage gate an explicit REST resource. The
live check ``[14.6]`` in ``scripts/check_cockpit_overhaul.sh`` requires
``GET /red/clients?tenant_id=3fmindset`` to answer with the pilot workspace.

These tests drive the real FastAPI app with fresh in-memory adapters substituted
for every port the seed's routes touch, then assert the seed is complete and
idempotent. A separate class exercises the real PostgreSQL path when
``DATABASE_URL``, psycopg and alembic are present, mirroring
``tests/unit/production/test_build_object_postgres.py``.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock

DATABASE_URL = os.environ.get("DATABASE_URL")
REPO_ROOT = Path(__file__).resolve().parents[2]
HAS_PSYCOPG = importlib.util.find_spec("psycopg") is not None
HAS_ALEMBIC = importlib.util.find_spec("alembic") is not None
RUN_POSTGRES = bool(DATABASE_URL) and HAS_PSYCOPG and HAS_ALEMBIC
SKIP_REASON = (
    "PostgreSQL seed test requires DATABASE_URL, psycopg and alembic; "
    "export DATABASE_URL and install the app dependencies to run it"
)


def _override(store):
    """Return a zero-argument dependency override for one store instance.

    FastAPI inspects an override's signature; a parameter with a default would
    be treated as a query parameter, so the override must take no arguments.
    """

    return lambda: store


class SeedPilotWorkspaceTests(unittest.TestCase):
    """The seed creates the pilot workspace once and a rerun changes nothing."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient
            from redops.api.app import create_app
            from redops.api.routes import (
                get_authority_amplifier_repository,
                get_build_object_repository,
                get_campaign_message_repository,
                get_claim_store,
                get_client_workspace_store,
                get_funnel_integration_repository,
                get_gate_ledger_repository,
                get_launch_qa_repository,
                get_method_version_repository,
                get_offer_version_repository,
                get_source_record_store,
                get_stage_run_repository,
            )
            from redops.contexts.commercial.infrastructure.repositories import (
                InMemoryCampaignMessageRepository,
                InMemoryOfferVersionRepository,
            )
            from redops.contexts.engagement.infrastructure.repositories import (
                InMemoryClientWorkspaceStore,
            )
            from redops.contexts.execution.infrastructure.repositories import (
                InMemoryFunnelIntegrationRepository,
                InMemoryLaunchQARepository,
            )
            from redops.contexts.governance.infrastructure.repositories import (
                InMemoryGateLedgerRepository,
                InMemoryStageRunRepository,
            )
            from redops.contexts.knowledge.infrastructure.repositories import (
                InMemoryClaimStore,
                InMemorySourceRecordStore,
            )
            from redops.contexts.method.infrastructure.repositories import (
                InMemoryMethodVersionRepository,
            )
            from redops.contexts.production.infrastructure.repositories import (
                InMemoryAuthorityAmplifierRepository,
                InMemoryBuildObjectRepository,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc

        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.dependencies = {
            get_gate_ledger_repository: InMemoryGateLedgerRepository,
            get_stage_run_repository: InMemoryStageRunRepository,
            get_client_workspace_store: InMemoryClientWorkspaceStore,
            get_source_record_store: InMemorySourceRecordStore,
            get_claim_store: InMemoryClaimStore,
            get_method_version_repository: InMemoryMethodVersionRepository,
            get_offer_version_repository: InMemoryOfferVersionRepository,
            get_campaign_message_repository: (
                InMemoryCampaignMessageRepository
            ),
            get_authority_amplifier_repository: (
                InMemoryAuthorityAmplifierRepository
            ),
            get_funnel_integration_repository: (
                InMemoryFunnelIntegrationRepository
            ),
            get_launch_qa_repository: InMemoryLaunchQARepository,
            get_build_object_repository: InMemoryBuildObjectRepository,
        }

    def setUp(self) -> None:
        self.app = self.create_app()
        for dependency, store_class in self.dependencies.items():
            store = store_class()
            self.app.dependency_overrides[dependency] = _override(store)
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_seed_creates_the_pilot_workspace_end_to_end(self) -> None:
        from redops.seed import (
            DEMO_TENANT,
            DEMO_WORKSPACE_ID,
            demo_builds,
            demo_claims,
            demo_sources,
            seed_pilot_workspace,
        )

        report = seed_pilot_workspace(self.client)

        self.assertEqual(DEMO_TENANT, report["tenant_id"])
        self.assertEqual(DEMO_WORKSPACE_ID, report["workspace_id"])
        self.assertTrue(report["workspace_created"])
        self.assertEqual(
            [source["source_id"] for source in demo_sources()],
            report["sources_created"],
        )
        self.assertEqual(
            [claim["claim_id"] for claim in demo_claims()],
            report["claims_created"],
        )
        self.assertEqual(
            [build["build_id"] for build in demo_builds()],
            report["builds_created"],
        )
        self.assertEqual(list(range(11)), report["gates_recorded"])
        self.assertEqual([], report["gates_already_approved"])

        response = self.client.get(
            "/red/clients", params={"tenant_id": DEMO_TENANT}
        )
        self.assertEqual(200, response.status_code, response.text)
        workspaces = response.json()["workspaces"]
        workspace = next(
            item
            for item in workspaces
            if item["workspace_id"] == DEMO_WORKSPACE_ID
        )
        self.assertTrue(
            all("demo" in entry["actor"] for entry in workspace["authorities"])
        )

        response = self.client.get(
            "/red/decisions", params={"tenant_id": DEMO_TENANT}
        )
        self.assertEqual(200, response.status_code, response.text)
        decisions = response.json()["decisions"]
        self.assertEqual(11, len(decisions))
        self.assertEqual(
            list(range(11)), [item["stage_number"] for item in decisions]
        )
        self.assertTrue(
            all(item["disposition"] == "approved" for item in decisions)
        )
        self.assertTrue(
            all("demo" in item["rationale"].lower() for item in decisions)
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        template = stage_zero_to_ten_template()
        self.assertEqual(
            [stage.checkpoint for stage in template.stages],
            [item["checkpoint"] for item in decisions],
        )

        response = self.client.get(f"/red/clients/{DEMO_TENANT}/sources")
        self.assertEqual(200, response.status_code, response.text)
        source_ids = {
            item["source_id"] for item in response.json()["sources"]
        }
        self.assertTrue(
            {source["source_id"] for source in demo_sources()} <= source_ids
        )

        response = self.client.get(
            "/red/claims", params={"tenant_id": DEMO_TENANT}
        )
        self.assertEqual(200, response.status_code, response.text)
        claims = response.json()["claims"]
        self.assertTrue(
            {claim["claim_id"] for claim in demo_claims()}
            <= {item["claim_id"] for item in claims}
        )
        self.assertTrue(
            all("demo" in item["statement"].lower() for item in claims)
        )

        response = self.client.get(
            "/red/builds", params={"tenant_id": DEMO_TENANT}
        )
        self.assertEqual(200, response.status_code, response.text)
        builds = response.json()["builds"]
        self.assertTrue(
            {build["build_id"] for build in demo_builds()}
            <= {item["build_id"] for item in builds}
        )
        self.assertTrue(
            all(
                "demo" in item["owner"].lower()
                and "demo" in item["purpose"].lower()
                for item in builds
            )
        )

    def test_a_rerun_changes_nothing(self) -> None:
        from redops.seed import DEMO_TENANT, seed_pilot_workspace

        first = seed_pilot_workspace(self.client)
        self.assertTrue(first["workspace_created"])

        def snapshot():
            clients = self.client.get(
                "/red/clients", params={"tenant_id": DEMO_TENANT}
            ).json()
            sources = self.client.get(
                f"/red/clients/{DEMO_TENANT}/sources"
            ).json()
            claims = self.client.get(
                "/red/claims", params={"tenant_id": DEMO_TENANT}
            ).json()
            builds = self.client.get(
                "/red/builds", params={"tenant_id": DEMO_TENANT}
            ).json()
            decisions = self.client.get(
                "/red/decisions", params={"tenant_id": DEMO_TENANT}
            ).json()
            return clients, sources, claims, builds, decisions

        before = snapshot()
        second = seed_pilot_workspace(self.client)
        after = snapshot()

        self.assertFalse(second["workspace_created"])
        self.assertEqual([], second["sources_created"])
        self.assertEqual([], second["claims_created"])
        self.assertEqual([], second["builds_created"])
        self.assertEqual([], second["gates_recorded"])
        self.assertEqual(list(range(11)), second["gates_already_approved"])
        self.assertEqual(before, after)

    def test_seed_from_env_requires_a_database_url(self) -> None:
        from redops.seed import SeedConfigurationError, seed_from_env

        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SeedConfigurationError):
                seed_from_env()


@unittest.skipUnless(RUN_POSTGRES, SKIP_REASON)
class PostgresPilotSeedRoundTripTests(unittest.TestCase):
    """The seed is idempotent against the real PostgreSQL schema."""

    @classmethod
    def setUpClass(cls) -> None:
        from alembic import command
        from alembic.config import Config

        config = Config(str(REPO_ROOT / "alembic.ini"))
        config.set_main_option(
            "script_location",
            str(REPO_ROOT / "backend/redops/shared/persistence/migrations"),
        )
        config.set_main_option("sqlalchemy.url", DATABASE_URL)
        command.upgrade(config, "head")

    def test_seed_from_env_is_idempotent_on_postgres(self) -> None:
        from fastapi.testclient import TestClient
        from redops.api.app import create_app
        from redops.seed import (
            DEMO_TENANT,
            DEMO_WORKSPACE_ID,
            seed_from_env,
        )

        seed_from_env(environ={"DATABASE_URL": DATABASE_URL})
        second = seed_from_env(environ={"DATABASE_URL": DATABASE_URL})

        self.assertFalse(second["workspace_created"])
        self.assertEqual([], second["sources_created"])
        self.assertEqual([], second["claims_created"])
        self.assertEqual([], second["builds_created"])
        self.assertEqual([], second["gates_recorded"])

        client = TestClient(create_app())
        response = client.get(
            "/red/clients", params={"tenant_id": DEMO_TENANT}
        )
        self.assertEqual(200, response.status_code, response.text)
        workspace_ids = {
            item["workspace_id"] for item in response.json()["workspaces"]
        }
        self.assertIn(DEMO_WORKSPACE_ID, workspace_ids)


if __name__ == "__main__":
    unittest.main()

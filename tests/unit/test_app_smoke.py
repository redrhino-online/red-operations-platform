"""Smoke tests for the RED FastAPI entry point (reuse layer).

SPEC.md section 6 requires the API entry point to be a thin adapter over the
domain, and ADR 0008 makes OpenExecutive a pinned dependency composed through
composition rather than edited. These tests exercise the smallest composition:
the RED app answers its own routes and mounts the reused OpenExecutive shell.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter (no third-party
packages) runs the suite, and runs under the vendored core environment.
"""

from __future__ import annotations

import unittest


class AppSmokeTest(unittest.TestCase):
    """The RED app boots, serves its routes and composes OpenExecutive."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from redops.api.app import create_app
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.app = create_app()

    def setUp(self) -> None:
        from fastapi.testclient import TestClient

        self.client = TestClient(self.app)

    def test_health_reports_ok(self) -> None:
        response = self.client.get("/red/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_stages_returns_the_canonical_zero_to_ten_template(self) -> None:
        response = self.client.get("/red/stages")

        self.assertEqual(response.status_code, 200)
        stages = response.json()
        self.assertEqual([stage["stage_number"] for stage in stages], list(range(11)))
        self.assertEqual(stages[0]["name"], "Intake")
        self.assertEqual(stages[0]["checkpoint"], "Production Ready")
        self.assertEqual(stages[10]["name"], "Launch")
        self.assertIn("live-campaign", stages[10]["required_asset_kinds"])

    def test_openexecutive_shell_is_mounted_not_edited(self) -> None:
        mounted = {
            route.path
            for route in self.app.routes
            if getattr(route, "path", None) is not None
        }

        self.assertIn("/openexecutive", mounted)

    def test_gate_ledger_dependency_defaults_to_the_process_local_adapter(
        self,
    ) -> None:
        import os

        from redops.api.routes import get_gate_ledger_repository
        from redops.contexts.governance.infrastructure.repositories import (
            InMemoryGateLedgerRepository,
        )

        previous = os.environ.pop("DATABASE_URL", None)
        try:
            repository = next(get_gate_ledger_repository())
            self.assertIsInstance(
                repository, InMemoryGateLedgerRepository
            )
        finally:
            if previous is not None:
                os.environ["DATABASE_URL"] = previous

    def test_stage_run_dependency_defaults_to_the_process_local_adapter(
        self,
    ) -> None:
        import os

        from redops.api.routes import get_stage_run_repository
        from redops.contexts.governance.infrastructure.repositories import (
            InMemoryStageRunRepository,
        )

        previous = os.environ.pop("DATABASE_URL", None)
        try:
            repository = next(get_stage_run_repository())
            self.assertIsInstance(repository, InMemoryStageRunRepository)
        finally:
            if previous is not None:
                os.environ["DATABASE_URL"] = previous

    def test_method_version_dependency_defaults_to_the_process_local_adapter(
        self,
    ) -> None:
        import os

        from redops.api.routes import get_method_version_repository
        from redops.contexts.method.infrastructure.repositories import (
            InMemoryMethodVersionRepository,
        )

        previous = os.environ.pop("DATABASE_URL", None)
        try:
            repository = next(get_method_version_repository())
            self.assertIsInstance(repository, InMemoryMethodVersionRepository)
        finally:
            if previous is not None:
                os.environ["DATABASE_URL"] = previous

    def test_offer_version_dependency_defaults_to_the_process_local_adapter(
        self,
    ) -> None:
        import os

        from redops.api.routes import get_offer_version_repository
        from redops.contexts.commercial.infrastructure.repositories import (
            InMemoryOfferVersionRepository,
        )

        previous = os.environ.pop("DATABASE_URL", None)
        try:
            repository = next(get_offer_version_repository())
            self.assertIsInstance(repository, InMemoryOfferVersionRepository)
        finally:
            if previous is not None:
                os.environ["DATABASE_URL"] = previous

    def test_campaign_message_dependency_defaults_to_the_process_local_adapter(
        self,
    ) -> None:
        import os

        from redops.api.routes import get_campaign_message_repository
        from redops.contexts.commercial.infrastructure.repositories import (
            InMemoryCampaignMessageRepository,
        )

        previous = os.environ.pop("DATABASE_URL", None)
        try:
            repository = next(get_campaign_message_repository())
            self.assertIsInstance(
                repository, InMemoryCampaignMessageRepository
            )
        finally:
            if previous is not None:
                os.environ["DATABASE_URL"] = previous

    def test_authority_amplifier_dependency_defaults_to_the_process_local_adapter(
        self,
    ) -> None:
        import os

        from redops.api.routes import get_authority_amplifier_repository
        from redops.contexts.production.infrastructure.repositories import (
            InMemoryAuthorityAmplifierRepository,
        )

        previous = os.environ.pop("DATABASE_URL", None)
        try:
            repository = next(get_authority_amplifier_repository())
            self.assertIsInstance(
                repository, InMemoryAuthorityAmplifierRepository
            )
        finally:
            if previous is not None:
                os.environ["DATABASE_URL"] = previous

    def test_funnel_integration_dependency_defaults_to_the_process_local_adapter(
        self,
    ) -> None:
        import os

        from redops.api.routes import get_funnel_integration_repository
        from redops.contexts.execution.infrastructure.repositories import (
            InMemoryFunnelIntegrationRepository,
        )

        previous = os.environ.pop("DATABASE_URL", None)
        try:
            repository = next(get_funnel_integration_repository())
            self.assertIsInstance(
                repository, InMemoryFunnelIntegrationRepository
            )
        finally:
            if previous is not None:
                os.environ["DATABASE_URL"] = previous

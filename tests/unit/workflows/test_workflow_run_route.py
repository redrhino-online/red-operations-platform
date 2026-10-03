"""HTTP-boundary behavioral tests for the workflow run route (SPEC.md §7).

SPEC.md section 7 exposes ``/workflows/{id}`` and requires status to stream by
polling with stable event IDs; SPEC.md section 9 requires every tenant resource
query to carry ``tenant_id``; SPEC.md section 11 requires a waiting workflow to
survive a restart. These tests drive the real FastAPI app against a fresh
in-memory ``WorkflowRunStore`` (substituted through the overridable dependency),
so the route cannot bypass the tenant boundary and can only project the durable
aggregate.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest
from datetime import date

TENANT = "client-3f"
OTHER_TENANT = "client-other"
RUN_ID = "run-3f"
ON = date(2026, 10, 3)


class WorkflowRunRouteTests(unittest.TestCase):
    """The workflow run is served only through the store port and its scope."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient
            from redops.api.app import create_app
            from redops.api.routes import get_workflow_run_store
            from redops.workflows.infrastructure.repositories import (
                InMemoryWorkflowRunStore,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.store_dependency = staticmethod(get_workflow_run_store)
        cls.store_class = staticmethod(InMemoryWorkflowRunStore)

    def setUp(self) -> None:
        self.app = self.create_app()
        self.store = self.store_class()
        self.app.dependency_overrides[self.store_dependency] = lambda: self.store
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def url(self, tenant_id: str = TENANT, run_id: str = RUN_ID) -> str:
        return f"/red/clients/{tenant_id}/workflows/{run_id}"

    @staticmethod
    def definition():
        from redops.workflows.domain.value_objects import (
            WorkflowDefinition,
            WorkflowStep,
            WorkflowStepKind,
        )

        return WorkflowDefinition(
            definition_id="amplifier-build",
            version="2026.1",
            steps=(
                WorkflowStep("draft-script"),
                WorkflowStep("approve-script", WorkflowStepKind.APPROVAL),
            ),
        )

    def started_run(self, tenant_id: str = TENANT):
        from redops.workflows.domain.entities import WorkflowRun

        run = WorkflowRun(
            run_id=RUN_ID,
            tenant_id=tenant_id,
            definition=self.definition(),
        )
        run.start(
            actor="worker-1",
            reason="run started",
            on=ON,
            correlation_id="corr-1",
        )
        return run

    def test_a_running_run_reports_its_pinned_definition_and_event_id(self) -> None:
        self.store.save(self.started_run())

        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(RUN_ID, body["run_id"])
        self.assertEqual(TENANT, body["tenant_id"])
        self.assertEqual("amplifier-build", body["definition_id"])
        self.assertEqual("2026.1", body["definition_version"])
        self.assertEqual("running", body["status"])
        self.assertEqual([], body["completed_steps"])
        self.assertIsNone(body["in_progress_step"])
        self.assertEqual("draft-script", body["next_step"])
        self.assertEqual(f"{RUN_ID}:1", body["event_id"])
        self.assertEqual(1, len(body["transitions"]))
        event = body["transitions"][0]
        self.assertEqual(f"{RUN_ID}:1", event["event_id"])
        self.assertEqual("worker-1", event["actor"])
        self.assertEqual("pending", event["old_status"])
        self.assertEqual("running", event["new_status"])
        self.assertEqual("corr-1", event["correlation_id"])

    def test_a_waiting_approval_is_preserved_with_a_stable_event_id(self) -> None:
        run = self.started_run()
        run.begin_step(
            actor="worker-1", reason="draft", on=ON, correlation_id="corr-2"
        )
        run.commit_step(
            actor="worker-1", reason="drafted", on=ON, correlation_id="corr-3"
        )
        run.await_approval(
            actor="worker-1", reason="awaiting review", on=ON, correlation_id="corr-4"
        )
        self.store.save(run)

        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual("awaiting_approval", body["status"])
        self.assertEqual(["draft-script"], body["completed_steps"])
        self.assertEqual("approve-script", body["pending_approval"])
        self.assertEqual("approve-script", body["next_step"])
        self.assertEqual(f"{RUN_ID}:2", body["event_id"])
        self.assertEqual(2, len(body["transitions"]))

    def test_a_run_is_not_visible_to_another_client(self) -> None:
        self.store.save(self.started_run())

        response = self.client.get(self.url(tenant_id=OTHER_TENANT))

        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(
            "WorkflowRunNotFoundError", response.json()["detail"]["error"]
        )

    def test_an_unknown_run_is_a_not_found(self) -> None:
        response = self.client.get(self.url(run_id="missing-run"))

        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(
            "WorkflowRunNotFoundError", response.json()["detail"]["error"]
        )


if __name__ == "__main__":
    unittest.main()

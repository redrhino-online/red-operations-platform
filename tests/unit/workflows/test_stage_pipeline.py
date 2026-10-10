"""Behavioral tests for the stage 0-10 pipeline as cockpit workflows (K11).

SPEC.md section 14 condition 8 requires the pipeline to be registered as
versioned cockpit workflow definitions, Jobs to list it, and a started run's
transitions to appear in the workflow run detail screen. These tests pin:

* the versioned definition is derived from the canonical ``stage_zero_to_ten_
  template()`` — one task step per stage followed by one approval gate — so it
  cannot drift from the template the gates are evaluated against;
* the registry resolves it and refuses an unknown name;
* the runtime composes the ``RunWorkflowHandler`` with the injected store;
* the vendor Jobs catalog lists the pipeline and mirrors the template;
* a run started through the API pauses at the first gate and its transitions
  are readable at the workflow run detail read.

The API test imports FastAPI, so it skips cleanly when the app dependencies are
unavailable.
"""

from __future__ import annotations

import unittest

from redops.workflows.pipeline import (
    PIPELINE_DEFINITION_ID,
    PIPELINE_DEFINITION_VERSION,
    red_workflow_definition,
    stage_pipeline_definition,
)


class StagePipelineDefinitionTests(unittest.TestCase):
    """The definition is the gated template, versioned and resolvable."""

    def test_definition_is_one_task_and_one_gate_per_stage(self) -> None:
        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )
        from redops.workflows.domain.value_objects import WorkflowStepKind

        definition = stage_pipeline_definition()
        template = stage_zero_to_ten_template()

        self.assertEqual(definition.definition_id, PIPELINE_DEFINITION_ID)
        self.assertEqual(definition.version, PIPELINE_DEFINITION_VERSION)
        self.assertEqual(len(definition.steps), 2 * len(template.stages))
        for index, stage in enumerate(template.stages):
            task = definition.step_at(2 * index)
            gate = definition.step_at(2 * index + 1)
            self.assertEqual(task.name, f"stage-{stage.stage_number}")
            self.assertIs(task.kind, WorkflowStepKind.TASK)
            self.assertEqual(gate.name, f"gate-{stage.stage_number}")
            self.assertIs(gate.kind, WorkflowStepKind.APPROVAL)

    def test_registry_resolves_the_pipeline_and_refuses_unknown(self) -> None:
        self.assertEqual(
            red_workflow_definition(PIPELINE_DEFINITION_ID),
            stage_pipeline_definition(),
        )
        with self.assertRaises(KeyError):
            red_workflow_definition("not-a-red-workflow")

    def test_runtime_composes_the_handler_with_the_injected_store(self) -> None:
        from redops.workflows.infrastructure.repositories import (
            InMemoryWorkflowRunStore,
        )

        from redops.workflows.pipeline import pipeline_runtime_from_env

        store = InMemoryWorkflowRunStore()
        handler, definition = pipeline_runtime_from_env({}, store=store)
        self.assertEqual(definition, red_workflow_definition(PIPELINE_DEFINITION_ID))
        self.assertEqual(handler._store, store)


class VendorJobsSurfaceTests(unittest.TestCase):
    """Jobs lists the pipeline and the mirror cannot drift from the template."""

    def test_jobs_lists_the_red_pipeline(self) -> None:
        from openexecutive.workflows import list_workflows

        names = [workflow.name for workflow in list_workflows()]
        self.assertIn("red_stage_0_10_pipeline", names)

    def test_vendor_mirror_matches_the_canonical_template(self) -> None:
        from openexecutive.workflows.redops_pipeline import RED_PIPELINE_STAGES
        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        template = stage_zero_to_ten_template()
        mirrored = tuple(
            (f"stage-{stage.stage_number}", stage.name, stage.checkpoint)
            for stage in template.stages
        )
        self.assertEqual(RED_PIPELINE_STAGES, mirrored)

    def test_vendor_steps_match_the_red_definition_stages(self) -> None:
        from openexecutive.workflows import get_workflow

        workflow = get_workflow("red_stage_0_10_pipeline")
        definition = red_workflow_definition(PIPELINE_DEFINITION_ID)
        self.assertEqual(
            [step.id for step in workflow.steps()],
            [name for name in definition.step_names if name.startswith("stage-")],
        )


class StartPipelineRunRouteTests(unittest.TestCase):
    """A run started through the API pauses at the first gate and is readable."""

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
            raise unittest.SkipTest(f"app dependencies unavailable: {exc}") from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        from redops.api.routes import get_workflow_step_executor
        from redops.contexts.execution.infrastructure.connectors import (
            IdempotentConnector,
            RecordingConnectorTransport,
            external_operation_store_from_env,
        )
        from redops.workflows.infrastructure.executors import ConnectorStepExecutor

        cls.store_dependency = staticmethod(get_workflow_run_store)
        cls.executor_dependency = staticmethod(get_workflow_step_executor)
        cls.store_class = staticmethod(InMemoryWorkflowRunStore)
        cls.executor = ConnectorStepExecutor(
            connector=IdempotentConnector(
                store=external_operation_store_from_env(None),
                transport=RecordingConnectorTransport(),
            ),
            connector_name="redop",
        )

    def setUp(self) -> None:
        self.app = self.create_app()
        self.store = self.store_class()
        self.app.dependency_overrides[self.store_dependency] = lambda: self.store
        self.app.dependency_overrides[self.executor_dependency] = lambda: self.executor
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_started_run_pauses_at_the_first_gate_and_is_readable(self) -> None:
        response = self.client.post(
            "/red/clients/3fmindset/workflows/red-stage-0-10-pipeline",
            json={"actor": "production manager"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        payload = response.json()
        self.assertEqual(payload["definition_id"], PIPELINE_DEFINITION_ID)
        self.assertEqual(payload["definition_version"], PIPELINE_DEFINITION_VERSION)
        self.assertEqual(payload["status"], "awaiting_approval")
        self.assertEqual(payload["completed_steps"], ["stage-0"])
        self.assertEqual(payload["pending_approval"], "gate-0")
        self.assertGreaterEqual(len(payload["transitions"]), 2)

        read = self.client.get(
            f"/red/clients/3fmindset/workflows/{payload['run_id']}"
        )
        self.assertEqual(read.status_code, 200, read.text)
        self.assertEqual(read.json()["run_id"], payload["run_id"])
        self.assertEqual(read.json()["transitions"], payload["transitions"])

    def test_unknown_definition_is_refused(self) -> None:
        response = self.client.post(
            "/red/clients/3fmindset/workflows/not-a-red-workflow",
            json={"actor": "production manager"},
        )
        self.assertEqual(response.status_code, 404, response.text)

    def test_blank_actor_is_refused(self) -> None:
        response = self.client.post(
            "/red/clients/3fmindset/workflows/red-stage-0-10-pipeline",
            json={"actor": "   "},
        )
        self.assertEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()

"""Behavioral tests for binding the workflow human gates to RED approvals (K12).

SPEC.md section 14 condition 8: a run pauses at a ``wait_for_human`` gate that
corresponds to a RED approval request and resumes only after that approval is
recorded, and the approval inbox and the cockpit Review queue are one approval
experience with the exact version diff. These tests pin:

* the gate-step binding maps a pipeline ``gate-<stage>`` step to its stage and
  leaves every other step unbound;
* the handler refuses to resume a bound gate whose stage has no passing RED
  approval, and resumes it once the approval is recorded;
* the adapter answers from the tenant's durable gate ledger;
* the API refuses an unapproved resume, resumes an approved one, and the
  awaiting-approval read lists the waiting run with its exact pinned version.

The API test imports FastAPI, so it skips cleanly when the app dependencies are
unavailable.
"""

from __future__ import annotations

import unittest
from datetime import date

from redops.workflows.application.handlers import RunWorkflowHandler
from redops.workflows.application.ports import (
    StageGateApprovalPort,
    WorkflowRunStore,
    WorkflowStepExecutor,
)
from redops.workflows.domain.entities import WorkflowRun
from redops.workflows.domain.errors import ApprovalNotRecordedError
from redops.workflows.domain.policies import GateStepBinding
from redops.workflows.domain.value_objects import (
    WorkflowDefinition,
    WorkflowStep,
    WorkflowStepKind,
)

TODAY = date(2026, 10, 3)
CORRELATION = "corr-1"
TENANT = "3fmindset"


def pipeline_definition() -> WorkflowDefinition:
    """The K11 pipeline shape reduced to its first gate."""

    return WorkflowDefinition(
        definition_id="red-stage-0-10-pipeline",
        version="1.0",
        steps=(
            WorkflowStep("stage-0"),
            WorkflowStep("gate-0", WorkflowStepKind.APPROVAL),
            WorkflowStep("stage-1"),
        ),
    )


class RecordingExecutor(WorkflowStepExecutor):
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, run: WorkflowRun, step) -> None:
        self.executed.append(step.name)


class FakeGateApprovals(StageGateApprovalPort):
    def __init__(self, approved: set[int]) -> None:
        self.approved = set(approved)

    def has_passing_decision(self, *, tenant_id: str, stage_number: int) -> bool:
        return stage_number in self.approved


class InMemoryRunStore(WorkflowRunStore):
    def __init__(self) -> None:
        self.runs: dict[str, WorkflowRun] = {}

    def save(self, run: WorkflowRun) -> None:
        import copy

        self.runs[run.run_id] = copy.deepcopy(run)

    def get(self, run_id: str, *, tenant_id: str) -> WorkflowRun | None:
        import copy

        run = self.runs.get(run_id)
        if run is None or run.tenant_id != tenant_id:
            return None
        return copy.deepcopy(run)

    def list_resumable(self, *, tenant_id: str) -> tuple[str, ...]:
        return tuple(
            run_id
            for run_id, run in self.runs.items()
            if run.tenant_id == tenant_id and run.resume_step() is not None
        )

    def list_awaiting_approval(self, *, tenant_id: str) -> tuple[str, ...]:
        return tuple(
            run_id
            for run_id, run in self.runs.items()
            if run.tenant_id == tenant_id
            and run.status.value == "awaiting_approval"
        )

    def close(self) -> None:
        pass


class GateStepBindingTests(unittest.TestCase):
    def test_a_pipeline_gate_step_binds_to_its_stage(self) -> None:
        self.assertEqual(GateStepBinding.from_step_name("gate-3").stage_number, 3)
        self.assertEqual(GateStepBinding.from_step_name("gate-10").stage_number, 10)

    def test_a_non_gate_step_binds_to_nothing(self) -> None:
        self.assertIsNone(GateStepBinding.from_step_name("stage-3"))
        self.assertIsNone(GateStepBinding.from_step_name("approve-script"))
        self.assertIsNone(GateStepBinding.from_step_name("gate-"))
        self.assertIsNone(GateStepBinding.from_step_name(""))


class GateApprovalBindingTests(unittest.TestCase):
    """A bound gate resumes only after its RED approval is recorded."""

    def setUp(self) -> None:
        self.store = InMemoryRunStore()
        self.handler = RunWorkflowHandler(
            store=self.store,
            executor=RecordingExecutor(),
            gate_approvals=FakeGateApprovals(approved=set()),
        )

    def started_run(self) -> WorkflowRun:
        return self.handler.start(
            definition=pipeline_definition(),
            tenant_id=TENANT,
            run_id="run-1",
            actor="production manager",
            reason="start the pipeline",
            on=TODAY,
            correlation_id=CORRELATION,
        )

    def test_the_run_pauses_at_the_bound_gate(self) -> None:
        run = self.started_run()
        self.assertEqual(run.status.value, "awaiting_approval")
        self.assertEqual(run.pending_approval, "gate-0")
        self.assertEqual(run.completed_steps, ("stage-0",))

    def test_resuming_a_bound_gate_without_the_red_approval_is_refused(self) -> None:
        self.started_run()
        with self.assertRaises(ApprovalNotRecordedError):
            self.handler.approve(
                "run-1",
                tenant_id=TENANT,
                actor="client authority",
                reason="approve the gate",
                on=TODAY,
                correlation_id=CORRELATION,
            )

    def test_resuming_a_bound_gate_after_the_red_approval_is_recorded(self) -> None:
        self.started_run()
        self.handler._gate_approvals = FakeGateApprovals(approved={0})
        run = self.handler.approve(
            "run-1",
            tenant_id=TENANT,
            actor="client authority",
            reason="approve the gate",
            on=TODAY,
            correlation_id=CORRELATION,
        )
        self.assertEqual(run.pending_approval, None)
        self.assertIn("gate-0", run.completed_steps)
        self.assertEqual(run.status.value, "completed")

    def test_an_unbound_step_keeps_the_generic_behavior(self) -> None:
        definition = WorkflowDefinition(
            definition_id="amplifier",
            version="1.0",
            steps=(
                WorkflowStep("draft"),
                WorkflowStep("approve-script", WorkflowStepKind.APPROVAL),
            ),
        )
        self.handler.start(
            definition=definition,
            tenant_id=TENANT,
            run_id="run-2",
            actor="production manager",
            reason="start",
            on=TODAY,
            correlation_id=CORRELATION,
        )
        run = self.handler.approve(
            "run-2",
            tenant_id=TENANT,
            actor="client authority",
            reason="approve",
            on=TODAY,
            correlation_id=CORRELATION,
        )
        self.assertEqual(run.status.value, "completed")


class StageGateApprovalRepositoryTests(unittest.TestCase):
    """The adapter answers from the tenant's durable gate ledger."""

    def test_answers_whether_the_stage_approval_is_recorded(self) -> None:
        from redops.workflows.infrastructure.approvals import (
            StageGateApprovalRepository,
        )

        recorded: dict[tuple[str, int], bool] = {}

        class FakeLedger:
            def has_passing_decision(self, stage_number: int, *, on: date) -> bool:
                return recorded.get((stage_number, on), False)

        class FakeRepository:
            def load(self, template, tenant_id: str):
                self.tenant_id = tenant_id
                return FakeLedger()

        repository = FakeRepository()
        adapter = StageGateApprovalRepository(repository)
        self.assertFalse(
            adapter.has_passing_decision(tenant_id=TENANT, stage_number=0)
        )
        recorded[(0, date.today())] = True
        self.assertTrue(
            adapter.has_passing_decision(tenant_id=TENANT, stage_number=0)
        )
        self.assertEqual(repository.tenant_id, TENANT)


class WorkflowApprovalRouteTests(unittest.TestCase):
    """The API refuses an unapproved resume and lists what is waiting."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient
            from redops.api.app import create_app
            from redops.api.routes import (
                get_stage_gate_approvals,
                get_workflow_run_store,
                get_workflow_step_executor,
            )
            from redops.workflows.infrastructure.repositories import (
                InMemoryWorkflowRunStore,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(f"app dependencies unavailable: {exc}") from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.store_dependency = staticmethod(get_workflow_run_store)
        cls.executor_dependency = staticmethod(get_workflow_step_executor)
        cls.gates_dependency = staticmethod(get_stage_gate_approvals)
        cls.store_class = staticmethod(InMemoryWorkflowRunStore)

    def setUp(self) -> None:
        self.app = self.create_app()
        self.store = self.store_class()
        self.app.dependency_overrides[self.store_dependency] = lambda: self.store
        self.app.dependency_overrides[self.executor_dependency] = lambda: (
            RecordingExecutor()
        )
        self.gates = FakeGateApprovals(approved=set())
        self.app.dependency_overrides[self.gates_dependency] = lambda: self.gates
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def _start(self) -> str:
        response = self.client.post(
            "/red/clients/3fmindset/workflows/red-stage-0-10-pipeline",
            json={"actor": "production manager"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["run_id"]

    def test_awaiting_approval_read_lists_the_waiting_run(self) -> None:
        run_id = self._start()
        response = self.client.get(
            "/red/clients/3fmindset/workflows/awaiting-approval"
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["runs"][0]["run_id"], run_id)
        self.assertEqual(payload["runs"][0]["pending_approval"], "gate-0")
        self.assertEqual(payload["runs"][0]["definition_version"], "1.0")

    def test_approval_route_refuses_until_the_red_approval_is_recorded(self) -> None:
        run_id = self._start()
        response = self.client.post(
            f"/red/clients/3fmindset/workflows/{run_id}/approval",
            json={"actor": "client authority"},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("ApprovalNotRecordedError", response.text)

    def test_approval_route_resumes_once_the_red_approval_is_recorded(self) -> None:
        run_id = self._start()
        self.gates.approved.add(0)
        response = self.client.post(
            f"/red/clients/3fmindset/workflows/{run_id}/approval",
            json={"actor": "client authority"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["status"], "awaiting_approval")
        self.assertIn("gate-0", payload["completed_steps"])
        self.assertIn("stage-1", payload["completed_steps"])
        self.assertEqual(payload["pending_approval"], "gate-1")


if __name__ == "__main__":
    unittest.main()

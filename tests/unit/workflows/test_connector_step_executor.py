"""Behavioral tests for the connector-backed workflow step executor.

SPEC.md section 7: "Persist run state before side effects; resume from committed
steps." SPEC.md section 11: "duplicate delivery creates one external operation"
and "restarting worker preserves a waiting workflow". ADR 0005: "Make workflow
resumption idempotent."

The workflow resume use case depends on the ``WorkflowStepExecutor`` port. The
concrete ``ConnectorStepExecutor`` is the adapter that performs a task step's
external effect through the replay-safe ``ConnectorPort`` seam, so a step re-run
after an interruption resolves to the one recorded external operation instead of
sending a second effect. An approval step is a human gate and is refused rather
than executed (SPEC.md section 4: an agent cannot confer human approval upon
itself).
"""

from __future__ import annotations

import unittest
from datetime import date

from redops.contexts.execution.infrastructure.connectors import (
    IdempotentConnector,
    InMemoryExternalOperationStore,
    RecordingConnectorTransport,
)
from redops.workflows.application.handlers import (
    ResumeDueRunsHandler,
    RunWorkflowHandler,
)
from redops.workflows.application.ports import WorkflowStepExecutor
from redops.workflows.domain.entities import WorkflowRun
from redops.workflows.domain.errors import WorkflowStepExecutionError
from redops.workflows.domain.value_objects import (
    WorkflowDefinition,
    WorkflowRunStatus,
    WorkflowStep,
    WorkflowStepKind,
)
from redops.workflows.infrastructure.executors import ConnectorStepExecutor
from redops.workflows.infrastructure.repositories import InMemoryWorkflowRunStore

TODAY = date(2026, 10, 6)
CORRELATION = "corr-1"
TENANT = "3fmindset"


def definition() -> WorkflowDefinition:
    return WorkflowDefinition(
        definition_id="authority-amplifier",
        version="1.0.0",
        steps=(
            WorkflowStep("extract-claims"),
            WorkflowStep("client-approval", WorkflowStepKind.APPROVAL),
            WorkflowStep("publish-asset"),
        ),
    )


def task_only_definition() -> WorkflowDefinition:
    return WorkflowDefinition(
        definition_id="authority-amplifier",
        version="1.0.0",
        steps=(
            WorkflowStep("extract-claims"),
            WorkflowStep("publish-asset"),
        ),
    )


class _CrashAfterEffect(WorkflowStepExecutor):
    """An executor that performs the effect then crashes before the run commits."""

    def __init__(self, inner: WorkflowStepExecutor) -> None:
        self._inner = inner

    def execute(self, run: WorkflowRun, step: WorkflowStep) -> None:
        self._inner.execute(run, step)
        raise RuntimeError("simulated crash after the effect was delivered")


class ConnectorStepExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = RecordingConnectorTransport()
        self.operations = InMemoryExternalOperationStore()
        self.connector = IdempotentConnector(
            store=self.operations, transport=self.transport
        )
        self.executor = ConnectorStepExecutor(
            connector=self.connector, connector_name="crm"
        )

    def _running_run(self, run_id: str = "run-1") -> WorkflowRun:
        run = WorkflowRun(
            run_id=run_id, tenant_id=TENANT, definition=definition()
        )
        run.start(
            actor="worker", reason="begin", on=TODAY, correlation_id=CORRELATION
        )
        return run

    def test_a_task_step_delivers_one_tenant_scoped_effect(self) -> None:
        run = self._running_run()
        step = run.begin_step(
            actor="worker", reason="begin", on=TODAY, correlation_id=CORRELATION
        )

        self.executor.execute(run, step)

        self.assertEqual(1, len(self.transport.sent))
        effect = self.transport.sent[0]
        self.assertEqual(TENANT, effect.tenant_id)
        self.assertEqual("crm", effect.connector)
        self.assertEqual("extract-claims", effect.target)
        self.assertEqual("run-1:extract-claims", effect.idempotency_key)

    def test_re_executing_an_interrupted_step_sends_no_second_effect(self) -> None:
        run = self._running_run()
        step = run.begin_step(
            actor="worker", reason="begin", on=TODAY, correlation_id=CORRELATION
        )

        self.executor.execute(run, step)
        # A resume re-runs the same interrupted step; the recorded operation
        # answers it, so the transport is not called a second time.
        self.executor.execute(run, step)

        self.assertEqual(1, len(self.transport.sent))

    def test_two_runs_do_not_share_an_idempotency_key(self) -> None:
        first = self._running_run("run-1")
        self.executor.execute(
            first,
            first.begin_step(
                actor="worker", reason="begin", on=TODAY, correlation_id=CORRELATION
            ),
        )
        second = self._running_run("run-2")
        self.executor.execute(
            second,
            second.begin_step(
                actor="worker", reason="begin", on=TODAY, correlation_id=CORRELATION
            ),
        )

        self.assertEqual(2, len(self.transport.sent))
        self.assertNotEqual(
            self.transport.sent[0].idempotency_key,
            self.transport.sent[1].idempotency_key,
        )

    def test_an_approval_step_is_refused_and_sends_nothing(self) -> None:
        run = self._running_run()
        approval = definition().step_at(1)

        with self.assertRaises(WorkflowStepExecutionError):
            self.executor.execute(run, approval)

        self.assertEqual(0, len(self.transport.sent))

    def test_a_blank_connector_name_is_refused(self) -> None:
        with self.assertRaises(WorkflowStepExecutionError):
            ConnectorStepExecutor(connector=self.connector, connector_name="   ")


class ConnectorStepExecutorResumeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryWorkflowRunStore()
        self.transport = RecordingConnectorTransport()
        self.connector = IdempotentConnector(
            store=InMemoryExternalOperationStore(), transport=self.transport
        )
        self.executor = ConnectorStepExecutor(
            connector=self.connector, connector_name="crm"
        )

    def test_a_restarting_worker_does_not_repeat_a_committed_effect(self) -> None:
        handler = RunWorkflowHandler(store=self.store, executor=self.executor)
        run = handler.start(
            definition=definition(),
            tenant_id=TENANT,
            run_id="run-1",
            actor="worker",
            reason="begin",
            on=TODAY,
            correlation_id=CORRELATION,
        )
        self.assertEqual(WorkflowRunStatus.AWAITING_APPROVAL, run.status)
        self.assertEqual(1, len(self.transport.sent))

        restarted = RunWorkflowHandler(store=self.store, executor=self.executor)
        resumed = restarted.resume(
            "run-1",
            tenant_id=TENANT,
            actor="worker-2",
            reason="restart",
            on=TODAY,
            correlation_id="corr-2",
        )
        self.assertEqual(WorkflowRunStatus.AWAITING_APPROVAL, resumed.status)
        self.assertEqual(1, len(self.transport.sent))

        approved = restarted.approve(
            "run-1",
            tenant_id=TENANT,
            actor="client-authority",
            reason="approved",
            on=TODAY,
            correlation_id="corr-3",
        )
        self.assertEqual(WorkflowRunStatus.COMPLETED, approved.status)
        self.assertEqual(2, len(self.transport.sent))

    def test_the_worker_pass_resumes_a_due_run_without_a_second_effect(self) -> None:
        crashing = _CrashAfterEffect(self.executor)
        handler = RunWorkflowHandler(store=self.store, executor=crashing)
        with self.assertRaises(RuntimeError):
            handler.start(
                definition=task_only_definition(),
                tenant_id=TENANT,
                run_id="run-1",
                actor="worker",
                reason="begin",
                on=TODAY,
                correlation_id=CORRELATION,
            )
        persisted = self.store.get("run-1", tenant_id=TENANT)
        self.assertEqual(WorkflowRunStatus.RUNNING, persisted.status)
        self.assertEqual("extract-claims", persisted.in_progress_step)
        self.assertEqual(1, len(self.transport.sent))

        worker = ResumeDueRunsHandler(store=self.store, executor=self.executor)
        advanced = worker.resume_due(
            tenant_id=TENANT,
            actor="worker-2",
            reason="restart",
            on=TODAY,
            correlation_id="corr-2",
        )

        self.assertEqual(1, len(advanced))
        self.assertEqual(WorkflowRunStatus.COMPLETED, advanced[0].status)
        # The interrupted step resolved to its recorded operation; only the
        # remaining step produced a new effect.
        self.assertEqual(2, len(self.transport.sent))
        self.assertEqual(
            ["extract-claims", "publish-asset"],
            [effect.target for effect in self.transport.sent],
        )


if __name__ == "__main__":
    unittest.main()

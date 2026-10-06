"""Behavioral tests for the RED background worker entrypoint (W1).

SPEC.md section 6: a durable queue or transactional outbox with worker
idempotency, and a modular monolith whose API and workers call use cases rather
than mutating persistence directly. SPEC.md section 7: "Persist run state before
side effects; resume from committed steps." SPEC.md section 11: "restarting
worker preserves a waiting workflow" and "duplicate delivery creates one external
operation". ADR 0005: one scheduler, one worker, gated so a single claim path
exists; resumption is idempotent.

``python -m redops.worker`` is the composition consumer of the workflow resume
use case. It composes ``ResumeDueRunsHandler`` with the durable
``WorkflowRunStore`` and the connector-backed ``ConnectorStepExecutor``, then
advances the in-flight runs that are due for its configured clients, one client
at a time. These tests exercise the loop and the composition root without a
database: the reference adapter is the process-local store, exactly as the
durable PostgreSQL adapter implements the same ports.
"""

from __future__ import annotations

import threading
import unittest
from datetime import date
from unittest import mock

from redops.contexts.execution.infrastructure.connectors import (
    IdempotentConnector,
    InMemoryExternalOperationStore,
    RecordingConnectorTransport,
)
from redops.workflows.application.ports import WorkflowStepExecutor
from redops.workflows.domain.entities import WorkflowRun
from redops.workflows.domain.value_objects import (
    WorkflowDefinition,
    WorkflowRunStatus,
    WorkflowStep,
    WorkflowStepKind,
)
from redops.workflows.infrastructure.executors import ConnectorStepExecutor
from redops.workflows.infrastructure.repositories import InMemoryWorkflowRunStore
from redops import worker as worker_module

TODAY = date(2026, 10, 6)
TENANT = "3fmindset"
OTHER_TENANT = "client-other"


def definition() -> WorkflowDefinition:
    return WorkflowDefinition(
        definition_id="authority-amplifier",
        version="1.0.0",
        steps=(
            WorkflowStep("extract-claims"),
            WorkflowStep("publish-asset"),
        ),
    )


def approval_definition() -> WorkflowDefinition:
    return WorkflowDefinition(
        definition_id="authority-amplifier",
        version="1.0.0",
        steps=(
            WorkflowStep("extract-claims"),
            WorkflowStep("client-approval", WorkflowStepKind.APPROVAL),
            WorkflowStep("publish-asset"),
        ),
    )


def interrupted_run(run_id: str, tenant_id: str) -> WorkflowRun:
    """A running run whose in-progress side effect had not committed."""
    run = WorkflowRun(run_id=run_id, tenant_id=tenant_id, definition=definition())
    run.start(actor="api", reason="begin", on=TODAY, correlation_id="corr-setup")
    run.begin_step(
        actor="api", reason="extract began", on=TODAY, correlation_id="corr-setup"
    )
    return run


def waiting_run(run_id: str, tenant_id: str) -> WorkflowRun:
    """A run parked on a human approval step, as a restart would find it."""
    run = WorkflowRun(
        run_id=run_id, tenant_id=tenant_id, definition=approval_definition()
    )
    run.start(actor="api", reason="begin", on=TODAY, correlation_id="corr-setup")
    run.begin_step(
        actor="api", reason="extract began", on=TODAY, correlation_id="corr-setup"
    )
    run.commit_step(
        actor="api", reason="extract done", on=TODAY, correlation_id="corr-setup"
    )
    run.await_approval(
        actor="api", reason="awaiting sign-off", on=TODAY, correlation_id="corr-setup"
    )
    return run


class _FailingExecutor(WorkflowStepExecutor):
    """Fails for one client so the loop's resilience can be observed."""

    def __init__(self, *, fail_for: str, inner: WorkflowStepExecutor) -> None:
        self._fail_for = fail_for
        self._inner = inner

    def execute(self, run: WorkflowRun, step: WorkflowStep) -> None:
        if run.tenant_id == self._fail_for:
            raise RuntimeError(f"connector refused the effect for {run.tenant_id}")
        self._inner.execute(run, step)


def _connector_executor() -> tuple[ConnectorStepExecutor, RecordingConnectorTransport]:
    transport = RecordingConnectorTransport()
    connector = IdempotentConnector(
        store=InMemoryExternalOperationStore(), transport=transport
    )
    return (
        ConnectorStepExecutor(connector=connector, connector_name="crm"),
        transport,
    )


class WorkflowWorkerLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryWorkflowRunStore()
        self.executor, self.transport = _connector_executor()
        self.worker = worker_module.build_worker(
            store=self.store, executor=self.executor, tenants=(TENANT,)
        )

    def test_a_due_run_is_resumed_and_completes(self) -> None:
        self.store.save(interrupted_run("run-1", TENANT))

        advanced = self.worker.run_once(on=TODAY)

        self.assertEqual(("run-1",), tuple(run.run_id for run in advanced))
        self.assertEqual(WorkflowRunStatus.COMPLETED, advanced[0].status)
        self.assertEqual(
            ["extract-claims", "publish-asset"],
            [effect.target for effect in self.transport.sent],
        )

    def test_a_waiting_approval_is_left_for_its_human(self) -> None:
        self.store.save(waiting_run("run-wait", TENANT))

        advanced = self.worker.run_once(on=TODAY)

        self.assertEqual((), advanced)
        waiting = self.store.get("run-wait", tenant_id=TENANT)
        self.assertEqual(WorkflowRunStatus.AWAITING_APPROVAL, waiting.status)
        self.assertEqual("client-approval", waiting.pending_approval)
        self.assertEqual([], self.transport.sent)

    def test_only_the_configured_clients_runs_are_scanned(self) -> None:
        self.store.save(interrupted_run("run-1", TENANT))
        self.store.save(interrupted_run("run-other", OTHER_TENANT))

        advanced = self.worker.run_once(on=TODAY)

        self.assertEqual(("run-1",), tuple(run.run_id for run in advanced))
        untouched = self.store.get("run-other", tenant_id=OTHER_TENANT)
        self.assertEqual(WorkflowRunStatus.RUNNING, untouched.status)
        self.assertEqual("extract-claims", untouched.in_progress_step)

    def test_a_failing_client_does_not_stop_the_pass_or_lose_its_run(self) -> None:
        self.store.save(interrupted_run("run-1", TENANT))
        self.store.save(interrupted_run("run-other", OTHER_TENANT))
        failing = _FailingExecutor(fail_for=TENANT, inner=self.executor)
        worker = worker_module.build_worker(
            store=self.store, executor=failing, tenants=(TENANT, OTHER_TENANT)
        )

        advanced = worker.run_once(on=TODAY)

        # The other client still advanced; the failing client's run is left
        # in progress (persisted before the side effect) for the next pass.
        self.assertEqual(("run-other",), tuple(run.run_id for run in advanced))
        left = self.store.get("run-1", tenant_id=TENANT)
        self.assertEqual(WorkflowRunStatus.RUNNING, left.status)
        self.assertEqual("extract-claims", left.in_progress_step)

    def test_serve_runs_a_pass_and_stops_on_the_event(self) -> None:
        calls: list[date | None] = []
        stop = threading.Event()

        class _StubHandler:
            def resume_due(self, *, tenant_id: str, actor: str, reason: str, on, correlation_id):
                calls.append(on)
                stop.set()
                return ()

        worker = worker_module.WorkflowWorker(
            handler=_StubHandler(), tenants=(TENANT,)
        )
        worker.serve(stop=stop, interval_seconds=0.01)

        self.assertEqual(1, len(calls))


class WorkerTenantRosterTests(unittest.TestCase):
    def test_a_comma_separated_roster_is_parsed_in_order(self) -> None:
        self.assertEqual(
            ("3fmindset", "client-b"),
            worker_module.parse_tenant_roster("3fmindset, client-b"),
        )

    def test_a_missing_roster_falls_back_to_the_pilot_client(self) -> None:
        self.assertEqual((worker_module.DEFAULT_TENANT,), worker_module.parse_tenant_roster(None))

    def test_a_blank_or_malformed_roster_is_refused(self) -> None:
        for raw in ("   ", "a,,b", ",a", "a,", "a,a"):
            with self.subTest(raw=raw):
                with self.assertRaises(worker_module.WorkerConfigurationError):
                    worker_module.parse_tenant_roster(raw)


class WorkerCompositionTests(unittest.TestCase):
    def test_a_durable_configuration_without_a_transport_is_refused(self) -> None:
        with self.assertRaises(worker_module.WorkerConfigurationError):
            worker_module.worker_from_env(
                {"DATABASE_URL": "postgresql://redops:redops@db:5432/redops"}
            )

    def test_a_reference_configuration_builds_a_worker_for_the_pilot(self) -> None:
        worker = worker_module.worker_from_env({})

        self.assertEqual((worker_module.DEFAULT_TENANT,), worker.tenants)
        self.assertEqual((), worker.run_once(on=TODAY))

    def test_an_injected_transport_composes_the_connector_executor(self) -> None:
        transport = RecordingConnectorTransport()
        store = InMemoryWorkflowRunStore()
        store.save(interrupted_run("run-1", TENANT))

        # The composition root wires the run store, the replay-safe connector
        # over the injected transport, and the connector step executor together.
        with mock.patch.object(
            worker_module, "workflow_run_store_from_env", return_value=store
        ):
            worker = worker_module.worker_from_env(
                {"REDOP_WORKER_TENANTS": TENANT}, transport=transport
            )
        advanced = worker.run_once(on=TODAY)

        self.assertEqual(WorkflowRunStatus.COMPLETED, advanced[0].status)
        self.assertEqual(
            ["extract-claims", "publish-asset"],
            [effect.target for effect in transport.sent],
        )

    def test_main_builds_a_worker_and_serves_until_stopped(self) -> None:
        served: list[object] = []

        class _Worker:
            def serve(self, *, stop, interval_seconds=None):
                served.append(stop)

        with mock.patch.object(
            worker_module, "worker_from_env", return_value=_Worker()
        ) as build, mock.patch.object(
            worker_module.signal, "signal"
        ) as register:
            exit_code = worker_module.main()

        self.assertEqual(0, exit_code)
        build.assert_called_once()
        self.assertEqual(1, len(served))
        self.assertGreaterEqual(register.call_count, 2)


if __name__ == "__main__":
    unittest.main()

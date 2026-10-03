"""Cross-tenant isolation for the background worker layer.

SPEC.md section 13 condition 3 requires the cross-tenant security suite to cover
the background worker, and SPEC.md section 9 requires cross-client access to be
tested at "API, retrieval, background worker, and artifact URL layers". SPEC.md
section 11 requires a "restarting worker [to] preserve a waiting workflow".

These tests exercise ``ResumeDueRunsHandler`` -- the worker's per-client resume
pass -- over the tenant-scoped ``WorkflowRunStore`` reference adapter. The pass
holds one client at a time: its store scan returns only that client's due runs
and every resume is re-checked against the same tenant, so a worker for one
client cannot read, list or advance another client's run, and it still leaves an
approval wait for its human. The durable PostgreSQL adapter implements the same
``list_resumable`` query; it is exercised with ``DATABASE_URL`` in
``tests/unit/workflows/test_workflow_run_store.py``.
"""

from __future__ import annotations

import unittest
from datetime import date

from redops.workflows.application.handlers import ResumeDueRunsHandler
from redops.workflows.application.ports import WorkflowStepExecutor
from redops.workflows.domain.entities import WorkflowRun
from redops.workflows.domain.errors import CrossTenantWorkflowRunError
from redops.workflows.domain.value_objects import (
    WorkflowDefinition,
    WorkflowRunStatus,
    WorkflowStep,
    WorkflowStepKind,
)
from redops.workflows.infrastructure.repositories import InMemoryWorkflowRunStore

TENANT = "3fmindset"
OTHER_TENANT = "client-other"
ON = date(2026, 10, 3)
CORRELATION = "corr-worker-isolation"


def definition() -> WorkflowDefinition:
    return WorkflowDefinition(
        definition_id="authority-amplifier",
        version="1.0.0",
        steps=(
            WorkflowStep("extract-claims"),
            WorkflowStep("publish-asset"),
        ),
    )


def interrupted_run(run_id: str, tenant_id: str) -> WorkflowRun:
    """A run whose side effect had not committed before the worker died."""
    run = WorkflowRun(run_id=run_id, tenant_id=tenant_id, definition=definition())
    run.start(actor="worker", reason="begin", on=ON, correlation_id=CORRELATION)
    run.begin_step(
        actor="worker", reason="extract began", on=ON, correlation_id=CORRELATION
    )
    return run


def waiting_run(run_id: str, tenant_id: str) -> WorkflowRun:
    """A run parked on a human approval step, as a restart would find it."""
    approval = WorkflowDefinition(
        definition_id="authority-amplifier",
        version="1.0.0",
        steps=(
            WorkflowStep("extract-claims"),
            WorkflowStep("client-approval", WorkflowStepKind.APPROVAL),
            WorkflowStep("publish-asset"),
        ),
    )
    run = WorkflowRun(run_id=run_id, tenant_id=tenant_id, definition=approval)
    run.start(actor="worker", reason="begin", on=ON, correlation_id=CORRELATION)
    run.begin_step(
        actor="worker", reason="extract began", on=ON, correlation_id=CORRELATION
    )
    run.commit_step(
        actor="worker", reason="extract done", on=ON, correlation_id=CORRELATION
    )
    run.await_approval(
        actor="worker", reason="awaiting sign-off", on=ON, correlation_id=CORRELATION
    )
    return run


class RecordingExecutor(WorkflowStepExecutor):
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, run: WorkflowRun, step: WorkflowStep) -> None:
        self.executed.append(f"{run.tenant_id}:{step.name}")


class WorkerIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryWorkflowRunStore()
        self.executor = RecordingExecutor()
        self.worker = ResumeDueRunsHandler(store=self.store, executor=self.executor)
        self.store.save(interrupted_run("run-3f", TENANT))
        self.store.save(interrupted_run("run-other", OTHER_TENANT))

    def _resume_due(self, tenant_id: str) -> tuple[WorkflowRun, ...]:
        return self.worker.resume_due(
            tenant_id=tenant_id,
            actor="worker",
            reason="resume due runs",
            on=ON,
            correlation_id=CORRELATION,
        )

    def test_worker_resumes_only_its_own_clients_runs(self) -> None:
        advanced = self._resume_due(TENANT)

        self.assertEqual(("run-3f",), tuple(run.run_id for run in advanced))
        self.assertEqual(
            ["3fmindset:extract-claims", "3fmindset:publish-asset"],
            self.executor.executed,
        )

    def test_another_clients_run_is_never_read_or_advanced(self) -> None:
        self._resume_due(TENANT)

        untouched = self.store.get("run-other", tenant_id=OTHER_TENANT)
        self.assertEqual(WorkflowRunStatus.RUNNING, untouched.status)
        self.assertEqual("extract-claims", untouched.in_progress_step)
        self.assertEqual(
            ("run-other",), self.store.list_resumable(tenant_id=OTHER_TENANT)
        )

    def test_worker_scan_is_scoped_to_the_requested_client(self) -> None:
        self.assertEqual(("run-3f",), self.store.list_resumable(tenant_id=TENANT))
        self.assertEqual(
            ("run-other",), self.store.list_resumable(tenant_id=OTHER_TENANT)
        )

    def test_worker_leaves_a_waiting_run_for_its_human(self) -> None:
        self.store.save(waiting_run("run-waiting", TENANT))

        advanced = self._resume_due(TENANT)

        self.assertEqual(("run-3f",), tuple(run.run_id for run in advanced))
        waiting = self.store.get("run-waiting", tenant_id=TENANT)
        self.assertEqual(WorkflowRunStatus.AWAITING_APPROVAL, waiting.status)
        self.assertEqual("client-approval", waiting.pending_approval)

    def test_worker_resumes_the_same_client_independently_of_the_other(self) -> None:
        self._resume_due(OTHER_TENANT)

        self.assertEqual(
            ["client-other:extract-claims", "client-other:publish-asset"],
            self.executor.executed,
        )
        mine = self.store.get("run-3f", tenant_id=TENANT)
        self.assertEqual(WorkflowRunStatus.RUNNING, mine.status)
        self.assertEqual("extract-claims", mine.in_progress_step)

    def test_worker_refuses_an_unscoped_pass(self) -> None:
        with self.assertRaises(CrossTenantWorkflowRunError):
            self._resume_due("   ")


if __name__ == "__main__":
    unittest.main()

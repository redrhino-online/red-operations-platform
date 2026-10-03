"""Behavioral tests for durable RED workflow runs (SPEC.md sections 4, 7, 11; ADR 0005).

Rules under test:
- "Persist run state before side effects; resume from committed steps" and a
  versioned definition (SPEC.md section 7).
- "restarting worker preserves a waiting workflow" (SPEC.md section 11).
- "Make workflow resumption idempotent and persist run state before side
  effects" (ADR 0005).
- Illegal transitions are rejected, not coerced (SPEC.md section 4).
"""

import copy
import unittest
from datetime import date

from redops.workflows.application.handlers import RunWorkflowHandler
from redops.workflows.application.ports import (
    WorkflowRunStore,
    WorkflowStepExecutor,
)
from redops.workflows.domain.entities import WorkflowRun
from redops.workflows.domain.errors import (
    IllegalWorkflowTransitionError,
    InvalidWorkflowDefinitionError,
    UnknownWorkflowStepError,
    WorkflowRunNotFoundError,
    WorkflowStepOrderError,
)
from redops.workflows.domain.value_objects import (
    WorkflowDefinition,
    WorkflowRunStatus,
    WorkflowStep,
    WorkflowStepKind,
)

TODAY = date(2026, 10, 3)
CORRELATION = "corr-1"


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


class InMemoryRunStore(WorkflowRunStore):
    """A durable-ish store that copies on the boundary like a real adapter."""

    def __init__(self) -> None:
        self.runs: dict[str, WorkflowRun] = {}
        self.saves = 0

    def save(self, run: WorkflowRun) -> None:
        self.saves += 1
        self.runs[run.run_id] = copy.deepcopy(run)

    def get(self, run_id: str, *, tenant_id: str) -> WorkflowRun | None:
        run = self.runs.get(run_id)
        if run is None or run.tenant_id != tenant_id:
            return None
        return copy.deepcopy(run)


class RecordingExecutor(WorkflowStepExecutor):
    def __init__(self, fail_on: str | None = None) -> None:
        self.executed: list[str] = []
        self.fail_on = fail_on

    def execute(self, run: WorkflowRun, step: WorkflowStep) -> None:
        self.executed.append(step.name)
        if step.name == self.fail_on:
            raise RuntimeError("simulated crash mid step")


class WorkflowResumeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryRunStore()
        self.executor = RecordingExecutor()
        self.handler = RunWorkflowHandler(store=self.store, executor=self.executor)

    def _start(self, run_id: str = "run-1") -> WorkflowRun:
        return self.handler.start(
            definition=definition(),
            tenant_id="client-3f",
            run_id=run_id,
            actor="worker",
            reason="begin",
            on=TODAY,
            correlation_id=CORRELATION,
        )

    def test_start_persists_state_before_effects_and_waits_at_approval(self) -> None:
        run = self._start()
        self.assertEqual(run.status, WorkflowRunStatus.AWAITING_APPROVAL)
        self.assertEqual(run.completed_steps, ("extract-claims",))
        self.assertEqual(run.pending_approval, "client-approval")
        self.assertIsNone(run.in_progress_step)
        self.assertEqual(self.executor.executed, ["extract-claims"])
        stored = self.store.get("run-1", tenant_id="client-3f")
        self.assertIsNotNone(stored)
        self.assertEqual(stored.status, WorkflowRunStatus.AWAITING_APPROVAL)

    def test_restart_preserves_a_waiting_workflow(self) -> None:
        self._start()
        restarted = RunWorkflowHandler(store=self.store, executor=self.executor)
        run = restarted.resume(
            "run-1",
            tenant_id="client-3f",
            actor="worker-2",
            reason="restart",
            on=TODAY,
            correlation_id="corr-2",
        )
        self.assertEqual(run.status, WorkflowRunStatus.AWAITING_APPROVAL)
        self.assertEqual(run.pending_approval, "client-approval")
        self.assertEqual(self.executor.executed, ["extract-claims"])

    def test_approval_resumes_from_committed_steps_without_repeating_effects(self) -> None:
        self._start()
        restarted = RunWorkflowHandler(store=self.store, executor=self.executor)
        run = restarted.approve(
            "run-1",
            tenant_id="client-3f",
            actor="client-authority",
            reason="approved",
            on=TODAY,
            correlation_id="corr-2",
        )
        self.assertEqual(run.status, WorkflowRunStatus.COMPLETED)
        self.assertEqual(
            run.completed_steps,
            ("extract-claims", "client-approval", "publish-asset"),
        )
        self.assertEqual(self.executor.executed, ["extract-claims", "publish-asset"])

    def test_interrupted_step_is_recovered_idempotently_on_resume(self) -> None:
        crashing = RecordingExecutor(fail_on="publish-asset")
        handler = RunWorkflowHandler(store=self.store, executor=crashing)
        handler.start(
            definition=definition(),
            tenant_id="client-3f",
            run_id="run-1",
            actor="worker",
            reason="begin",
            on=TODAY,
            correlation_id=CORRELATION,
        )
        with self.assertRaises(RuntimeError):
            handler.approve(
                "run-1",
                tenant_id="client-3f",
                actor="client-authority",
                reason="approved",
                on=TODAY,
                correlation_id="corr-2",
            )
        persisted = self.store.get("run-1", tenant_id="client-3f")
        self.assertEqual(persisted.status, WorkflowRunStatus.RUNNING)
        self.assertEqual(persisted.in_progress_step, "publish-asset")
        self.assertEqual(
            persisted.completed_steps, ("extract-claims", "client-approval")
        )

        healthy = RecordingExecutor()
        restarted = RunWorkflowHandler(store=self.store, executor=healthy)
        run = restarted.resume(
            "run-1",
            tenant_id="client-3f",
            actor="worker-2",
            reason="restart",
            on=TODAY,
            correlation_id="corr-3",
        )
        self.assertEqual(run.status, WorkflowRunStatus.COMPLETED)
        self.assertEqual(healthy.executed, ["publish-asset"])
        self.assertEqual(
            run.completed_steps,
            ("extract-claims", "client-approval", "publish-asset"),
        )

    def test_duplicate_resume_does_not_repeat_committed_effects(self) -> None:
        self._start()
        restarted = RunWorkflowHandler(store=self.store, executor=self.executor)
        restarted.approve(
            "run-1",
            tenant_id="client-3f",
            actor="client-authority",
            reason="approved",
            on=TODAY,
            correlation_id="corr-2",
        )
        before = list(self.executor.executed)
        run = restarted.resume(
            "run-1",
            tenant_id="client-3f",
            actor="worker-3",
            reason="restart",
            on=TODAY,
            correlation_id="corr-3",
        )
        self.assertEqual(run.status, WorkflowRunStatus.COMPLETED)
        self.assertEqual(self.executor.executed, before)

    def test_resume_is_tenant_scoped(self) -> None:
        self._start()
        restarted = RunWorkflowHandler(store=self.store, executor=self.executor)
        with self.assertRaises(WorkflowRunNotFoundError):
            restarted.resume(
                "run-1",
                tenant_id="client-other",
                actor="worker-2",
                reason="restart",
                on=TODAY,
                correlation_id="corr-2",
            )

    def test_failed_run_is_terminal_and_not_resumed(self) -> None:
        self._start()
        restarted = RunWorkflowHandler(store=self.store, executor=self.executor)
        restarted.fail(
            "run-1",
            tenant_id="client-3f",
            reason="connector timeout",
            actor="worker-2",
            on=TODAY,
            correlation_id="corr-2",
        )
        run = restarted.resume(
            "run-1",
            tenant_id="client-3f",
            actor="worker-3",
            reason="restart",
            on=TODAY,
            correlation_id="corr-3",
        )
        self.assertEqual(run.status, WorkflowRunStatus.FAILED)
        self.assertEqual(self.executor.executed, ["extract-claims"])


class WorkflowRunDomainTests(unittest.TestCase):
    def test_definition_refuses_a_repeated_step_name(self) -> None:
        with self.assertRaises(InvalidWorkflowDefinitionError):
            WorkflowDefinition(
                definition_id="dup",
                version="1.0.0",
                steps=(WorkflowStep("a"), WorkflowStep("a")),
            )

    def test_definition_refuses_an_empty_step_list(self) -> None:
        with self.assertRaises(InvalidWorkflowDefinitionError):
            WorkflowDefinition(definition_id="empty", version="1.0.0", steps=())

    def test_step_at_rejects_an_out_of_range_index(self) -> None:
        with self.assertRaises(UnknownWorkflowStepError):
            definition().step_at(3)

    def test_begin_refuses_an_approval_step(self) -> None:
        approval_first = WorkflowDefinition(
            definition_id="approval-first",
            version="1.0.0",
            steps=(
                WorkflowStep("approve", WorkflowStepKind.APPROVAL),
                WorkflowStep("act"),
            ),
        )
        run = WorkflowRun(
            run_id="r", tenant_id="t", definition=approval_first
        )
        run.start(actor="w", reason="begin", on=TODAY, correlation_id=CORRELATION)
        with self.assertRaises(WorkflowStepOrderError):
            run.begin_step(
                actor="w", reason="begin", on=TODAY, correlation_id=CORRELATION
            )

    def test_commit_requires_an_in_progress_step(self) -> None:
        run = WorkflowRun(run_id="r", tenant_id="t", definition=definition())
        run.start(actor="w", reason="begin", on=TODAY, correlation_id=CORRELATION)
        with self.assertRaises(WorkflowStepOrderError):
            run.commit_step(
                actor="w", reason="done", on=TODAY, correlation_id=CORRELATION
            )

    def test_approve_requires_a_waiting_run(self) -> None:
        run = WorkflowRun(run_id="r", tenant_id="t", definition=definition())
        run.start(actor="w", reason="begin", on=TODAY, correlation_id=CORRELATION)
        with self.assertRaises(WorkflowStepOrderError):
            run.approve(
                actor="a", reason="ok", on=TODAY, correlation_id=CORRELATION
            )

    def test_start_twice_is_an_illegal_transition(self) -> None:
        run = WorkflowRun(run_id="r", tenant_id="t", definition=definition())
        run.start(actor="w", reason="begin", on=TODAY, correlation_id=CORRELATION)
        with self.assertRaises(IllegalWorkflowTransitionError):
            run.start(
                actor="w", reason="again", on=TODAY, correlation_id=CORRELATION
            )

    def test_fail_requires_a_reason(self) -> None:
        run = WorkflowRun(run_id="r", tenant_id="t", definition=definition())
        run.start(actor="w", reason="begin", on=TODAY, correlation_id=CORRELATION)
        with self.assertRaises(WorkflowStepOrderError):
            run.fail(reason="", actor="w", on=TODAY, correlation_id=CORRELATION)

    def test_resume_step_is_none_while_awaiting_approval(self) -> None:
        run = WorkflowRun(run_id="r", tenant_id="t", definition=definition())
        run.start(actor="w", reason="begin", on=TODAY, correlation_id=CORRELATION)
        run.begin_step(actor="w", reason="begin", on=TODAY, correlation_id=CORRELATION)
        run.commit_step(actor="w", reason="done", on=TODAY, correlation_id=CORRELATION)
        run.await_approval(
            actor="w", reason="wait", on=TODAY, correlation_id=CORRELATION
        )
        self.assertIsNone(run.resume_step())

    def test_transitions_record_actor_reason_and_correlation(self) -> None:
        run = WorkflowRun(run_id="r", tenant_id="t", definition=definition())
        run.start(actor="worker", reason="begin", on=TODAY, correlation_id=CORRELATION)
        self.assertEqual(len(run.transitions), 1)
        transition = run.transitions[0]
        self.assertEqual(transition.old_status, WorkflowRunStatus.PENDING)
        self.assertEqual(transition.new_status, WorkflowRunStatus.RUNNING)
        self.assertEqual(transition.actor, "worker")
        self.assertEqual(transition.correlation_id, CORRELATION)


if __name__ == "__main__":
    unittest.main()

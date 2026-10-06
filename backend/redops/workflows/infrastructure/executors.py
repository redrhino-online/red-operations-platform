"""Concrete ``WorkflowStepExecutor`` adapters for RED durable workflow runs.

SPEC.md section 6 calls connectors "outbound adapters with explicit scopes and
replay safe operations", and SPEC.md section 7 requires a workflow to "resume
from committed steps". The workflow resume use case depends on the
``WorkflowStepExecutor`` port; this module supplies the concrete adapter that
performs a task step's external effect through the replay-safe ``ConnectorPort``
seam, so a step re-run after an interruption resolves to the one recorded
external operation instead of sending a second effect (SPEC.md section 11:
"duplicate delivery creates one external operation"; ADR 0005).

The adapter derives a deterministic effect from the run and step: the run id and
step name form the idempotency key, the pinned definition version and step name
form the content digest, and the run's tenant scopes the effect. The same
interrupted step therefore produces the same effect on every resume, while a
different run or step produces a distinct one. An approval step is a human gate
and is refused rather than executed (SPEC.md section 4).
"""

from __future__ import annotations

import hashlib
from datetime import date

from redops.contexts.execution.application.ports import ConnectorPort
from redops.contexts.execution.domain.connector import ConnectorEffect
from redops.workflows.application.ports import WorkflowStepExecutor
from redops.workflows.domain.entities import WorkflowRun
from redops.workflows.domain.errors import WorkflowStepExecutionError
from redops.workflows.domain.value_objects import WorkflowStep, WorkflowStepKind


def _step_payload_digest(run: WorkflowRun, step: WorkflowStep) -> str:
    """Pin the exact definition version and step an effect was requested for.

    The digest is stable across a resume of the same run and step, so a retry
    matches the recorded operation; it changes if the definition version or step
    changes, so a reused key with different content is refused rather than
    silently overwriting the record (SPEC.md section 11).
    """

    material = f"{run.definition.definition_id}@{run.definition.version}:{step.name}"
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


class ConnectorStepExecutor(WorkflowStepExecutor):
    """Perform a task step's effect through the replay-safe connector seam.

    The adapter is idempotent by construction: the effect it derives from a run
    and step is identical on every execution, so the ``ConnectorPort`` resolves a
    re-run of an interrupted step to the one recorded external operation instead
    of sending a second effect (SPEC.md section 11).
    """

    def __init__(self, *, connector: ConnectorPort, connector_name: str) -> None:
        if not isinstance(connector_name, str) or not connector_name.strip():
            raise WorkflowStepExecutionError(
                "a connector step executor requires a non-blank connector name"
            )
        self._connector = connector
        self._connector_name = connector_name

    def execute(self, run: WorkflowRun, step: WorkflowStep) -> None:
        """Deliver the step's effect at most once for the run's client."""
        if step.kind is not WorkflowStepKind.TASK:
            raise WorkflowStepExecutionError(
                f"workflow step {step.name!r} is an approval and must wait for a "
                "human, not be executed as a side effect"
            )
        effect = ConnectorEffect(
            tenant_id=run.tenant_id,
            idempotency_key=f"{run.run_id}:{step.name}",
            connector=self._connector_name,
            target=step.name,
            payload_digest=_step_payload_digest(run, step),
            requested_on=date.today(),
        )
        self._connector.deliver(effect)

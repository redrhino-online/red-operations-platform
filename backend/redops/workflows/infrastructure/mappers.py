"""Map the workflows ``WorkflowRun`` aggregate to and from a durable payload.

SPEC.md section 6 keeps mapping in the infrastructure layer: the domain must not
know about JSONB or table columns. A run is stored as a JSONB payload plus a few
indexed columns and rebuilt through ``WorkflowRun.__post_init__`` on load, then
its transition log is restored without replaying the state machine (SPEC.md
section 4: history is append-only and a reload must not re-run transitions).

The pinned ``WorkflowDefinition`` is serialised with the run so an in-flight run
keeps the exact definition version it started on after a restart (SPEC.md
section 10). A round trip that dropped the definition, the completed-step list,
the in-progress or pending step, the failure reason or the transition actor and
reason would let a reloaded run re-run a committed step or lose the human record
of an approval, so every one of those fields is emitted.

Canon: not applicable. This is a persistence mapper for a platform aggregate,
not a method artifact, so no reference-model file informs its shape.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from redops.workflows.domain.entities import WorkflowRun
from redops.workflows.domain.value_objects import (
    WorkflowDefinition,
    WorkflowRunStatus,
    WorkflowRunTransition,
    WorkflowStep,
    WorkflowStepKind,
)

_KIND_BY_VALUE = {kind.value: kind for kind in WorkflowStepKind}
_STATUS_BY_VALUE = {status.value: status for status in WorkflowRunStatus}


def _date_to_text(value: date) -> str:
    return value.isoformat()


def _date_from_text(value: str) -> date:
    return date.fromisoformat(value)


def _step_to_payload(step: WorkflowStep) -> dict[str, Any]:
    return {"name": step.name, "kind": step.kind.value}


def _step_from_payload(payload: Mapping[str, Any]) -> WorkflowStep:
    return WorkflowStep(
        name=payload["name"],
        kind=_KIND_BY_VALUE[payload["kind"]],
    )


def _definition_to_payload(definition: WorkflowDefinition) -> dict[str, Any]:
    return {
        "definition_id": definition.definition_id,
        "version": definition.version,
        "steps": [_step_to_payload(step) for step in definition.steps],
    }


def _definition_from_payload(payload: Mapping[str, Any]) -> WorkflowDefinition:
    return WorkflowDefinition(
        definition_id=payload["definition_id"],
        version=payload["version"],
        steps=tuple(_step_from_payload(step) for step in payload["steps"]),
    )


def _transition_to_payload(transition: WorkflowRunTransition) -> dict[str, Any]:
    return {
        "actor": transition.actor,
        "reason": transition.reason,
        "occurred_at": _date_to_text(transition.occurred_at),
        "old_status": transition.old_status.value,
        "new_status": transition.new_status.value,
        "correlation_id": transition.correlation_id,
    }


def _transition_from_payload(
    payload: Mapping[str, Any],
) -> WorkflowRunTransition:
    return WorkflowRunTransition(
        actor=payload["actor"],
        reason=payload["reason"],
        occurred_at=_date_from_text(payload["occurred_at"]),
        old_status=_STATUS_BY_VALUE[payload["old_status"]],
        new_status=_STATUS_BY_VALUE[payload["new_status"]],
        correlation_id=payload["correlation_id"],
    )


def workflow_run_to_payload(run: WorkflowRun) -> dict[str, Any]:
    """Serialise a ``WorkflowRun`` into the JSONB payload the table stores."""
    return {
        "run_id": run.run_id,
        "tenant_id": run.tenant_id,
        "definition": _definition_to_payload(run.definition),
        "status": run.status.value,
        "completed_steps": list(run.completed_steps),
        "in_progress_step": run.in_progress_step,
        "pending_approval": run.pending_approval,
        "failure_reason": run.failure_reason,
        "transitions": [
            _transition_to_payload(transition) for transition in run.transitions
        ],
    }


def workflow_run_from_payload(payload: Mapping[str, Any]) -> WorkflowRun:
    """Rebuild a run, re-validating through the aggregate and restoring history.

    The rehydrated run is constructed through ``WorkflowRun.__post_init__`` so a
    stored row the aggregate would reject raises on load rather than being read
    back as a valid run (SPEC.md section 4). The persisted transition log is then
    restored with ``restore_history`` without replaying the state machine, so the
    audit history survives without re-applying transitions.
    """
    transitions = tuple(
        _transition_from_payload(transition)
        for transition in payload["transitions"]
    )
    run = WorkflowRun(
        run_id=payload["run_id"],
        tenant_id=payload["tenant_id"],
        definition=_definition_from_payload(payload["definition"]),
        status=_STATUS_BY_VALUE[payload["status"]],
        completed_steps=tuple(payload["completed_steps"]),
        in_progress_step=payload["in_progress_step"],
        pending_approval=payload["pending_approval"],
        failure_reason=payload["failure_reason"],
    )
    run.restore_history(transitions)
    return run

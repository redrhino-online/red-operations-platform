"""The stage 0-10 pipeline as versioned cockpit workflow definitions (K11;
SPEC.md sections 4, 7 and 14 condition 8).

SPEC.md section 4 defines the default production template as a gated dependency
graph: a stage is complete only when its required assets exist, pass a defined
checkpoint and receive approval for downstream use. This module turns that
template into a versioned ``WorkflowDefinition`` so the pipeline drives cockpit
workflows: one task step per stage (the stage's production work) followed by one
approval step per stage (the stage gate, a ``wait_for_human`` gate a named human
advances — SPEC.md section 4: an agent cannot confer human approval upon
itself). The steps are derived from ``stage_zero_to_ten_template()`` so the
definition cannot drift from the canonical template the gates are evaluated
against.

The definition is registered in ``RED_WORKFLOW_DEFINITIONS`` and resolved by
``red_workflow_definition``; ``pipeline_runtime_from_env`` composes the
``RunWorkflowHandler`` with the same durable run store and connector-backed
executor the worker uses, so a run started through the API and a run resumed by
the worker share one database (SPEC.md section 10). It approves nothing, spends
nothing and deploys nothing.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from redops.contexts.execution.infrastructure.connectors import (
    IdempotentConnector,
    external_operation_store_from_env,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.workflows.application.handlers import RunWorkflowHandler
from redops.workflows.application.ports import WorkflowRunStore
from redops.workflows.domain.value_objects import (
    WorkflowDefinition,
    WorkflowStep,
    WorkflowStepKind,
)
from redops.workflows.infrastructure.executors import ConnectorStepExecutor
from redops.workflows.infrastructure.repositories import workflow_run_store_from_env
from redops.workflows.sop_library import ops_workflow_definitions
from redops.worker import connector_transport_from_env

PIPELINE_DEFINITION_ID = "red-stage-0-10-pipeline"
PIPELINE_DEFINITION_VERSION = "1.0"
DEFAULT_CONNECTOR_NAME = "redop"


def stage_pipeline_definition(
    version: str = PIPELINE_DEFINITION_VERSION,
) -> WorkflowDefinition:
    """The 0-10 pipeline as a versioned definition: stage work, then its gate.

    Each stage contributes a ``stage-N`` task step (the production work the
    stage's accountable domain owns) and a ``gate-N`` approval step (the stage
    gate a designated human approves), in template order, so the run's step
    sequence is the gated pipeline and nothing else.
    """

    template = stage_zero_to_ten_template()
    steps: list[WorkflowStep] = []
    for stage in template.stages:
        steps.append(
            WorkflowStep(name=f"stage-{stage.stage_number}", kind=WorkflowStepKind.TASK)
        )
        steps.append(
            WorkflowStep(
                name=f"gate-{stage.stage_number}", kind=WorkflowStepKind.APPROVAL
            )
        )
    return WorkflowDefinition(
        definition_id=PIPELINE_DEFINITION_ID,
        version=version,
        steps=tuple(steps),
    )


RED_WORKFLOW_DEFINITIONS: dict[str, WorkflowDefinition] = {
    PIPELINE_DEFINITION_ID: stage_pipeline_definition(),
    # The canon SOPs and playbooks (K14): the same durable, gate-bound run
    # machinery drives an imported operating procedure.
    **ops_workflow_definitions(),
}


def red_workflow_definition(name: str) -> WorkflowDefinition:
    """Resolve a registered RED workflow definition by name."""

    definition = RED_WORKFLOW_DEFINITIONS.get(name)
    if definition is None:
        raise KeyError(f"Unknown RED workflow definition: {name}")
    return definition


def pipeline_step_executor_from_env(
    environ: Mapping[str, str] | None = None,
) -> ConnectorStepExecutor:
    """The step executor a pipeline run uses, composed like the worker's.

    The same ``DATABASE_URL`` selects the durable external-operation store and
    the transport, so a step executed by an API-started run and one resumed by
    the worker resolve to the same recorded operations (SPEC.md section 11).
    """

    environ = os.environ if environ is None else environ
    connector = IdempotentConnector(
        store=external_operation_store_from_env(environ.get("DATABASE_URL")),
        transport=connector_transport_from_env(environ),
    )
    return ConnectorStepExecutor(
        connector=connector,
        connector_name=environ.get("REDOP_CONNECTOR_NAME") or DEFAULT_CONNECTOR_NAME,
    )


def pipeline_runtime_from_env(
    environ: Mapping[str, str] | None = None,
    *,
    store: WorkflowRunStore | None = None,
) -> tuple[RunWorkflowHandler, WorkflowDefinition]:
    """Compose the run handler with the durable store and the pipeline definition.

    The store is injectable for tests; without one the same ``DATABASE_URL``
    that selects the worker's durable store selects this one, so an
    API-started run and a worker-resumed run share one database.
    """

    environ = os.environ if environ is None else environ
    run_store = store if store is not None else workflow_run_store_from_env(
        environ.get("DATABASE_URL")
    )
    handler = RunWorkflowHandler(
        store=run_store,
        executor=pipeline_step_executor_from_env(environ),
    )
    return handler, red_workflow_definition(PIPELINE_DEFINITION_ID)

"""RED stage 0-10 pipeline as a cockpit workflow (K11; SPEC.md section 14
condition 8). Additive file (ADR 0014; the workflows subtree is a RED-owned
surface per the owner-approved exception recorded in docs/fork_inventory.md).

The stage 0-10 pipeline is RED's gated production template (SPEC.md section 4).
This workflow mirrors it as a cockpit catalog entry so the Jobs page lists the
pipeline: one step per stage, titled with the stage name and described by the
checkpoint that stage's gate evaluates. The durable runs that drive the pipeline
are RED's versioned workflow runs (``backend/redops/workflows``, started through
RED's workflow API and read by the workflow run detail screen); this catalog
entry holds no RED business logic, drives no stage work and approves nothing.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from openexecutive.knowledge.store import ChromaDBStore
from openexecutive.workflows.base import (
    Workflow,
    WorkflowEvent,
    WorkflowSection,
    WorkflowStepDef,
)

# The gated 0-10 stage sequence, mirrored from RED's canonical production
# template (SPEC.md section 4). A repo test holds this mirror in sync with
# `stage_zero_to_ten_template()`, so a template change that is not reflected
# here fails the build rather than drifting silently.
RED_PIPELINE_STAGES: tuple[tuple[str, str, str], ...] = (
    ("stage-0", "Intake", "Production Ready"),
    ("stage-1", "Diagnose", "Avatar Locked"),
    ("stage-2", "Position", "Currency Locked"),
    ("stage-3", "Model", "Diagnostic Model Approved"),
    ("stage-4", "Package IP", "IP Architecture Locked"),
    ("stage-5", "Productize", "Offer Locked"),
    ("stage-6", "Message", "Campaign Message Approved"),
    ("stage-7", "Produce", "Authority Amplifier Approved"),
    ("stage-8", "Integrate", "Funnel Complete"),
    ("stage-9", "QA", "Launch Approved"),
    ("stage-10", "Launch", "Performance Baseline Established"),
)


class RedPipelineInputs(BaseModel):
    """The pipeline catalog entry takes the client it is planned for."""

    tenant_id: str = Field(description="The client tenant the pipeline is for")


class RedStagePipelineWorkflow(Workflow):
    """The gated 0-10 pipeline as a Jobs catalog entry.

    `run` renders the pipeline plan — every stage with the checkpoint its gate
    evaluates and the accountable work — as the artifact. The stage work itself
    is RED's domain work and the gates are RED's durable approval gates, so this
    workflow starts no run, executes no stage and approves nothing.
    """

    name = "red_stage_0_10_pipeline"
    title = "RED stage 0-10 pipeline"
    description = (
        "The gated 0-10 production pipeline: each stage's work is followed by "
        "the stage gate a designated human approves before dependent work is "
        "released."
    )
    section = WorkflowSection.RED
    estimated_minutes = 1

    def input_model(self) -> type[BaseModel]:
        return RedPipelineInputs

    def steps(self) -> list[WorkflowStepDef]:
        return [
            WorkflowStepDef(
                id=step_id,
                title=title,
                description=f"Stage gate checkpoint: {checkpoint}",
            )
            for step_id, title, checkpoint in RED_PIPELINE_STAGES
        ]

    async def run(
        self,
        inputs: BaseModel,
        store: ChromaDBStore,
    ) -> Any:
        for step_id, title, _checkpoint in RED_PIPELINE_STAGES:
            yield WorkflowEvent(type="step_start", step_id=step_id, step_title=title)
            yield WorkflowEvent(
                type="step_done",
                step_id=step_id,
                summary=f"{title}: the stage gate is a RED approval gate",
            )
        lines = ["# RED stage 0-10 pipeline", ""]
        lines.append(
            "The gated production pipeline for the client. Each stage's work is "
            "RED domain work; each stage gate is a RED approval gate a designated "
            "human advances."
        )
        lines.append("")
        for step_id, title, checkpoint in RED_PIPELINE_STAGES:
            lines.append(f"- **{title}** (`{step_id}`) — gate checkpoint: {checkpoint}")
        lines.append("")
        lines.append(
            "Durable runs of this pipeline are RED versioned workflow runs, "
            "started through RED's workflow API and read by the workflow run "
            "detail screen. This catalog entry drives no stage work and approves "
            "nothing."
        )
        yield WorkflowEvent(type="artifact", content="\n".join(lines))
        yield WorkflowEvent(type="done", run_id="red-stage-0-10-pipeline")

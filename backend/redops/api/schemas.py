"""HTTP request schemas for RED write endpoints.

These models are the entry-point adapter described in SPEC.md section 6: the API
calls use cases and never mutates persistence directly. They shape and type
inbound HTTP data only and carry no domain rule. Every integrity rule -- the
canonical intake asset kinds, exact positive asset versions, named owners and
the designated approver on the same workspace, directly sourced evidence and the
tenant boundary -- stays in the Engagement, Governance and Knowledge domains and
is surfaced as a named error, not validated here. Mapping these inputs to domain
value objects happens in the route so a malformed or unauthorized request is
refused by the domain, not accepted by the transport layer.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class SourceCitationInput(BaseModel):
    """A checksum and location based reference to an exact source location."""

    source_id: str
    checksum: str
    location: str


class ClaimInput(BaseModel):
    """A statement with an explicit provenance class and citations."""

    claim_id: str
    statement: str
    provenance: str
    confidence_note: str = ""
    citations: list[SourceCitationInput] = Field(default_factory=list)


class ClientAuthorityInput(BaseModel):
    """A named actor and the authority they hold in a client workspace."""

    actor: str
    authority: str


class IntakeAssetInput(BaseModel):
    """One stage 0 intake asset with a kind, exact version, owner and source."""

    asset_id: str
    kind: str
    version: int
    owner: str
    summary: str
    evidence_claim_ids: list[str]


class RecordStageZeroGateRequest(BaseModel):
    """The stage 0 "Production Ready" gate request (SPEC.md section 4).

    The caller supplies the real intake assets, the workspace authority registry,
    the supporting claims and the decision metadata. The route builds the
    canonical gate from these through the use case; it deliberately accepts no
    pre-built gate, so owner authority and sourced evidence cannot be bypassed.
    """

    workspace_id: str
    authorities: list[ClientAuthorityInput]
    intake_package_id: str
    assets: list[IntakeAssetInput]
    claims: list[ClaimInput]
    stage_owner: str
    approver: str
    scope: str
    checkpoint_evidence: str
    rationale: str
    assigned_owner: str
    due_on: date
    on: date
    correlation_id: str
    proposed_by: str | None = None
    next_action: str = ""


class AssetVersionResponse(BaseModel):
    """One exact asset version pinned or approved for a stage."""

    asset_id: str
    version: int


class MetricMovementResponse(BaseModel):
    """A measured before and after of one approved stage 10 improvement."""

    improvement_id: str
    before: float
    after: float
    measured_on: date


class MetricReportingResponse(BaseModel):
    """One observed metric row of the production view's METRICS dimension.

    The Measurement context owns the metric registry and observations; this is
    its typed projection onto the read model, so a placeholder figure never
    appears as verified progress (SPEC.md section 4).
    """

    metric_id: str
    tenant_id: str
    name: str
    funnel_step: str
    unit: str
    direction: str
    value: float
    window_start: date
    window_end: date
    sample_size: int
    source: str
    recorded_on: date
    basis: str
    movement: MetricMovementResponse | None = None


class StageProductionViewResponse(BaseModel):
    """One stage of the production-manager view (SPEC.md section 4).

    Answers what should exist, what is present and approved, what is missing,
    who is accountable, which dependency blocks work and what approval is next.
    """

    stage_number: int
    name: str
    checkpoint: str
    status: str
    required_asset_kinds: list[str]
    approved_assets: list[AssetVersionResponse]
    missing_asset_kinds: list[str]
    accountable_role: str
    approver_role: str
    dependencies: list[int]
    blocking_dependencies: list[int]
    assigned_owner: str | None = None
    recorded_approver: str | None = None
    due_on: date | None = None
    next_action: str = ""
    blockers: list[str] = []
    entered_at: date | None = None
    is_approved: bool


class PipelineProgressResponse(BaseModel):
    """Verified progress across the pipeline, kept apart from activity."""

    approved_gates: int
    total_gates: int
    verified_post_launch_milestones: int
    activity_entries: int
    verified_progress: int
    gates_remaining: int


class EngagementProductionViewResponse(BaseModel):
    """The production-manager view for one client engagement (SPEC.md section 4).

    The eight reporting dimensions are reported separately: assets,
    checkpoints, owner, dependency, status and due date per stage; milestones
    and metrics at the engagement level. Activity is reported apart from gate
    completion so progress is never shown as tasks checked off.
    """

    engagement: str
    tenant_id: str
    template_version: str
    current_stage_number: int | None
    next_approval_stage_number: int | None
    blocked_stage_numbers: list[int]
    progress: PipelineProgressResponse
    stages: list[StageProductionViewResponse]
    metric_reporting: list[MetricReportingResponse]

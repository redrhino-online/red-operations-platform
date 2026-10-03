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

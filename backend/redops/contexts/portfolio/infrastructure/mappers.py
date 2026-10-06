"""Row serialisation for the Portfolio opportunity register (SPEC.md section 6).

A stored opportunity is re-validated through the ``Opportunity`` value object on
load rather than trusted as stored, so a malformed row -- including one recorded
as an already-approved expansion -- cannot be read back as a client fact (SPEC.md
sections 1 and 5). Keeping the mapping here separates the durability concern from
the pure domain value object.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.value_objects import (
    ClientAuthority,
    EngagementLifecycle,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import StageAssetVersion
from redops.contexts.portfolio.domain.value_objects import (
    BusinessTarget,
    LaunchMapSection,
    Opportunity,
    OpportunityKind,
    OpportunityState,
    QuarterlyReview,
    UmbrellaPlan,
    UmbrellaSection,
)


def opportunity_to_payload(opportunity: Opportunity) -> dict[str, Any]:
    """Serialise an opportunity proposal for durable storage."""

    return {
        "opportunity_id": opportunity.opportunity_id,
        "tenant_id": opportunity.tenant_id,
        "title": opportunity.title,
        "kind": opportunity.kind.value,
        "source": {
            "asset_id": opportunity.source.asset_id,
            "tenant_id": opportunity.source.tenant_id,
            "kind": opportunity.source.kind,
            "version": opportunity.source.version,
        },
        "investment_case": opportunity.investment_case,
        "expected_outcome": opportunity.expected_outcome,
        "owner": opportunity.owner,
        "next_action": opportunity.next_action,
        "captured_on": opportunity.captured_on.isoformat(),
        "state": opportunity.state.value,
    }


def opportunity_from_payload(payload: Mapping[str, Any]) -> Opportunity:
    """Rebuild an opportunity proposal from its stored payload."""

    source = payload["source"]
    return Opportunity(
        opportunity_id=payload["opportunity_id"],
        tenant_id=payload["tenant_id"],
        title=payload["title"],
        kind=OpportunityKind(payload["kind"]),
        source=StageAssetVersion(
            asset_id=source["asset_id"],
            tenant_id=source["tenant_id"],
            kind=source["kind"],
            version=source["version"],
        ),
        investment_case=payload["investment_case"],
        expected_outcome=payload["expected_outcome"],
        owner=payload["owner"],
        next_action=payload["next_action"],
        captured_on=date.fromisoformat(payload["captured_on"]),
        state=OpportunityState(payload.get("state", "proposed")),
    )


def umbrella_plan_to_payload(plan: UmbrellaPlan) -> dict[str, Any]:
    """Serialise a canon umbrella plan for durable storage.

    The plan embeds a ``ClientWorkspace`` and a versioned ``StageTemplate``. The
    workspace is serialised inline (identity, authorities and lifecycle) so the
    portfolio adapter stays self-contained, and the template is stored by its
    version because it is read-only reference data, not state the plan owns; the
    canonical template for that version is rebuilt on load (SPEC.md sections 4 and
    6). Sections, targets and the ordered review history round-trip so a reload is
    re-validated through the aggregate rather than trusted as stored.
    """

    return {
        "plan_id": plan.plan_id,
        "tenant_id": plan.tenant_id,
        "owner": plan.owner,
        "created_on": plan.created_on.isoformat(),
        "workspace": {
            "workspace_id": plan.workspace.workspace_id,
            "tenant_id": plan.workspace.tenant_id,
            "authorities": [
                {"actor": entry.actor, "authority": entry.authority}
                for entry in plan.workspace.authorities
            ],
            "lifecycle": plan.workspace.lifecycle.value,
        },
        "template_version": plan.template.version,
        "sections": [
            {
                "section": section.section.value,
                "stages": list(section.stages),
                "objective": section.objective,
            }
            for section in plan.sections
        ],
        "targets": [
            {
                "target_id": target.target_id,
                "name": target.name,
                "metric": target.metric,
                "goal": target.goal,
                "due_on": target.due_on.isoformat(),
            }
            for target in plan.targets
        ],
        "reviews": [
            {
                "reviewed_on": review.reviewed_on.isoformat(),
                "next_review_on": review.next_review_on.isoformat(),
                "actor": review.actor,
            }
            for review in plan.reviews
        ],
    }


def umbrella_plan_from_payload(payload: Mapping[str, Any]) -> UmbrellaPlan:
    """Rebuild a canon umbrella plan from its stored payload.

    The workspace and the canonical template are reconstructed from the stored
    identity and version, then the aggregate re-validates the tenant boundary, the
    four launch-map sections, the specific targets and the ordered 90-day review
    history, so a malformed row raises on load rather than being read back as a
    client plan (SPEC.md sections 1 and 5).
    """

    workspace_payload = payload["workspace"]
    workspace = ClientWorkspace(
        workspace_id=workspace_payload["workspace_id"],
        tenant_id=workspace_payload["tenant_id"],
        authorities=tuple(
            ClientAuthority(actor=entry["actor"], authority=entry["authority"])
            for entry in workspace_payload["authorities"]
        ),
        lifecycle=EngagementLifecycle(
            workspace_payload.get("lifecycle", EngagementLifecycle.INTAKE.value)
        ),
    )
    return UmbrellaPlan(
        plan_id=payload["plan_id"],
        tenant_id=payload["tenant_id"],
        owner=payload["owner"],
        workspace=workspace,
        template=stage_zero_to_ten_template(payload["template_version"]),
        sections=tuple(
            UmbrellaSection(
                section=LaunchMapSection(entry["section"]),
                stages=tuple(entry["stages"]),
                objective=entry["objective"],
            )
            for entry in payload["sections"]
        ),
        targets=tuple(
            BusinessTarget(
                target_id=entry["target_id"],
                name=entry["name"],
                metric=entry["metric"],
                goal=entry["goal"],
                due_on=date.fromisoformat(entry["due_on"]),
            )
            for entry in payload["targets"]
        ),
        reviews=tuple(
            QuarterlyReview(
                reviewed_on=date.fromisoformat(entry["reviewed_on"]),
                next_review_on=date.fromisoformat(entry["next_review_on"]),
                actor=entry["actor"],
            )
            for entry in payload["reviews"]
        ),
        created_on=date.fromisoformat(payload["created_on"]),
    )

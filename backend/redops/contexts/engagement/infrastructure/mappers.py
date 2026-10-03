"""Row serialisation for the ``ClientWorkspaceStore`` port (SPEC.md section 6).

The durable and process-local adapters share one payload shape so a reload is
re-validated through the ``ClientWorkspace`` aggregate rather than trusted as
stored: authorities, the engagement lifecycle, the attached child registry, the
paused-from state and the append-only lifecycle transition log all round-trip
(SPEC.md sections 3 and 4). A stored workspace the aggregate would reject raises
on load instead of being read back as a real client.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.value_objects import (
    ClientAuthority,
    EngagementLifecycle,
    LifecycleTransition,
)


def workspace_to_payload(workspace: ClientWorkspace) -> dict[str, Any]:
    """Serialise a workspace, including its private registries and history."""

    return {
        "workspace_id": workspace.workspace_id,
        "tenant_id": workspace.tenant_id,
        "authorities": [
            {"actor": entry.actor, "authority": entry.authority}
            for entry in workspace.authorities
        ],
        "lifecycle": workspace.lifecycle.value,
        "children": dict(workspace._children),
        "paused_from": (
            workspace._paused_from.value
            if workspace._paused_from is not None
            else None
        ),
        "transitions": [
            {
                "actor": transition.actor,
                "reason": transition.reason,
                "occurred_at": transition.occurred_at.isoformat(),
                "old_lifecycle": transition.old_lifecycle.value,
                "new_lifecycle": transition.new_lifecycle.value,
                "correlation_id": transition.correlation_id,
            }
            for transition in workspace.transitions
        ],
    }


def workspace_from_payload(payload: dict[str, Any]) -> ClientWorkspace:
    """Rebuild a workspace from a stored payload, re-validating its invariants."""

    workspace = ClientWorkspace(
        workspace_id=payload["workspace_id"],
        tenant_id=payload["tenant_id"],
        authorities=tuple(
            ClientAuthority(actor=entry["actor"], authority=entry["authority"])
            for entry in payload["authorities"]
        ),
        lifecycle=EngagementLifecycle(payload["lifecycle"]),
    )
    workspace._children = dict(payload.get("children", {}))
    paused_from = payload.get("paused_from")
    workspace._paused_from = (
        EngagementLifecycle(paused_from) if paused_from is not None else None
    )
    workspace._transitions = [
        LifecycleTransition(
            actor=entry["actor"],
            reason=entry["reason"],
            occurred_at=date.fromisoformat(entry["occurred_at"]),
            old_lifecycle=EngagementLifecycle(entry["old_lifecycle"]),
            new_lifecycle=EngagementLifecycle(entry["new_lifecycle"]),
            correlation_id=entry["correlation_id"],
        )
        for entry in payload.get("transitions", [])
    ]
    return workspace

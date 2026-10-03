"""Test helper: register a client workspace through the ``/clients`` route.

SPEC.md sections 3 and 4 make the stage 0 gate resolve its authority registry
from the persisted ``ClientWorkspace`` rather than a repeated request body, so a
route test must register the workspace through the real ``POST /red/clients``
surface before it posts the stage 0 gate. This helper keeps that setup in one
place; it adds no rule the domain and route do not already enforce.
"""

from __future__ import annotations


def register_workspace(
    client,
    *,
    tenant_id: str,
    owner: str,
    approver: str,
    workspace_id: str = "ws-3f",
    with_approver: bool = True,
):
    """Register the tenant workspace and its authority registry over HTTP."""

    authorities = [{"actor": owner, "authority": "production-owner"}]
    if with_approver:
        authorities.append(
            {
                "actor": approver,
                "authority": "client-designated-authority",
            }
        )
    response = client.post(
        "/red/clients",
        json={
            "workspace_id": workspace_id,
            "tenant_id": tenant_id,
            "authorities": authorities,
        },
    )
    assert response.status_code == 201, response.text
    return response

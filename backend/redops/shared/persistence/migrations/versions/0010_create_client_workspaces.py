"""create the client_workspaces table

Revision ID: 0010_client_workspaces
Revises: 0009_workflow_runs
Create Date: 2026-10-03

ADR 0003 makes RED's durable records live in PostgreSQL. SPEC.md section 3 makes
the ClientWorkspace the tenant root every client-owned resource attaches to, and
the ``/clients`` API surface (SPEC.md section 7) must list and create it. The
workspace aggregate exists in ``backend/redops/contexts/engagement/``; this table
gives it the durable store the ``ClientWorkspaceStore`` port names. ``tenant_id``
is NOT NULL (SPEC.md section 3) and the unique key scopes one workspace id per
client; the full workspace (authorities, lifecycle, attached children, paused
state and append-only lifecycle transition log) lives in a ``workspace`` JSONB
payload so a reload is re-validated through the aggregate rather than trusted as
stored. Row-level security is a deliberate follow-up (ADR 0004, SPEC.md section
9); this migration establishes the tenant column the policy will build on, and
the adapter refuses an unscoped read or write.
"""

from __future__ import annotations

from alembic import op

revision = "0010_client_workspaces"
down_revision = "0009_workflow_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE client_workspaces (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            workspace_id TEXT NOT NULL CHECK (btrim(workspace_id) <> ''),
            workspace JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT client_workspaces_tenant_workspace_key
                UNIQUE (tenant_id, workspace_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE client_workspaces")

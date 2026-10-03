"""create the funnel_integrations table

Revision ID: 0007_funnel_integrations
Revises: 0006_authority_amplifiers
Create Date: 2026-10-03

ADR 0003 makes RED's records durable in PostgreSQL; SPEC.md section 3 makes the
stage 8 ``FunnelIntegration`` a reviewed production asset and section 4 requires
a passing gate to pin the exact approved asset versions and intended use. The
stage 9 and 10 gates ground on the stage 8 funnel that passed "Funnel Complete"
(a test prospect routed every capture, engagement and conversion handoff), so
that funnel must survive a restart and be shared across the API and worker
processes rather than being re-stated from the request body. ``tenant_id`` is
NOT NULL (SPEC.md section 3) and the unique key scopes one completed funnel per
client and integration id; the full funnel (its thirteen canonical asset
references, its pinned prospect path dry run and its grounding stage 7
authority amplifier) lives in a ``funnel`` JSONB payload so a reload is
re-validated through the aggregate rather than trusted as stored. Row-level
security is a deliberate follow-up (ADR 0004, SPEC.md section 9); this migration
establishes the tenant column the policy will build on, and the adapter refuses
an unscoped write.
"""

from __future__ import annotations

from alembic import op

revision = "0007_funnel_integrations"
down_revision = "0006_authority_amplifiers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE funnel_integrations (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            integration_id TEXT NOT NULL CHECK (btrim(integration_id) <> ''),
            funnel JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT funnel_integrations_tenant_integration_key
                UNIQUE (tenant_id, integration_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX funnel_integrations_tenant_integration_idx
            ON funnel_integrations (tenant_id, integration_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE funnel_integrations")

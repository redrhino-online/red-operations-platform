"""create the launch_qas table

Revision ID: 0008_launch_qas
Revises: 0007_funnel_integrations
Create Date: 2026-10-03

ADR 0003 makes RED's records durable in PostgreSQL; SPEC.md section 3 makes the
stage 9 ``LaunchQA`` a reviewed production asset and section 4 requires a passing
gate to pin the exact approved asset versions and intended use. The stage 10 gate
grounds on the stage 9 QA whose "Launch Approved" checkpoint authorized traffic
by the designated human authority (grounded on the completed stage 8 funnel and a
reviewed compliance package), so that authorization must survive a restart and be
shared across the API and worker processes rather than being re-stated from the
request body. ``tenant_id`` is NOT NULL (SPEC.md section 3) and the unique key
scopes one authorized QA per client and QA id; the full QA (its grounded stage 8
funnel, its sixteen canonical check set, its compliance package and its pinned
traffic authorization) lives in a ``qa`` JSONB payload so a reload is re-validated
through the aggregate rather than trusted as stored. Row-level security is a
deliberate follow-up (ADR 0004, SPEC.md section 9); this migration establishes the
tenant column the policy will build on, and the adapter refuses an unscoped write.
"""

from __future__ import annotations

from alembic import op

revision = "0008_launch_qas"
down_revision = "0007_funnel_integrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE launch_qas (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            qa_id TEXT NOT NULL CHECK (btrim(qa_id) <> ''),
            qa JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT launch_qas_tenant_qa_key
                UNIQUE (tenant_id, qa_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX launch_qas_tenant_qa_idx
            ON launch_qas (tenant_id, qa_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE launch_qas")

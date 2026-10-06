"""create the portfolio umbrella plan register table

Revision ID: 0019_umbrella_plans
Revises: 0018_external_operations
Create Date: 2026-10-06

ADR 0003 makes RED's durable records live in PostgreSQL. SPEC.md section 12.5
records the canon umbrella plan (the Online Business Launch Map and the one-page
Bulletproof Business Plan, canon files 00 and 01) as a planning decision over the
whole stage 0-10 pipeline, revisited every 90 days, and SPEC.md section 4 requires
the production view to carry it as a tenant-scoped read-model projection. The
register holds the plan's identity, owner, workspace, template version, launch-map
sections, specific targets and ordered review history. ``tenant_id`` and
``plan_id`` are NOT NULL (SPEC.md sections 3 and 9) and together they form the
append-only key, so one client cannot hold two plans under the same id. The plan
payload lives in JSONB and is re-validated through the aggregate on load rather
than trusted as stored. Row level security is a deliberate follow-up (ADR 0004,
SPEC.md section 9); this migration establishes the tenant column the policy will
build on, and the adapter refuses an unscoped read or write.
"""

from __future__ import annotations

from alembic import op

revision = "0019_umbrella_plans"
down_revision = "0018_external_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE umbrella_plans (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            plan_id TEXT NOT NULL CHECK (btrim(plan_id) <> ''),
            plan JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT umbrella_plans_key
                UNIQUE (tenant_id, plan_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE umbrella_plans")

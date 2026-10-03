"""create the method_versions table

Revision ID: 0003_method_versions
Revises: 0002_stage_runs
Create Date: 2026-10-03

ADR 0003 makes RED's records durable in PostgreSQL; SPEC.md section 3 makes
``MethodVersion`` a core aggregate and section 4 requires a passing gate to pin
an exact approved method version and intended use. The stage 6 to 10 gates
resolve the method a prior gate approved, so that approval must survive a restart
and be shared across the API and worker processes rather than living only in the
process that accepted it. ``tenant_id`` is NOT NULL (SPEC.md section 3) and the
unique key scopes one version per client, method and semantic version; the full
approved method (the approval, the pinned stage 2 primary currency, stage 3
diagnostic model and stage 4 Signature Solution) lives in a ``method`` JSONB
payload so a reload is re-validated through the aggregate rather than trusted as
stored. Row-level security is a deliberate follow-up (ADR 0004, SPEC.md section
9); this migration establishes the tenant column the policy will build on, and
the adapter refuses an unscoped write.
"""

from __future__ import annotations

from alembic import op

revision = "0003_method_versions"
down_revision = "0002_stage_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE method_versions (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            method_id TEXT NOT NULL CHECK (btrim(method_id) <> ''),
            semantic_version TEXT NOT NULL
                CHECK (btrim(semantic_version) <> ''),
            method JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT method_versions_tenant_method_version_key
                UNIQUE (tenant_id, method_id, semantic_version)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX method_versions_tenant_method_idx
            ON method_versions (tenant_id, method_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE method_versions")

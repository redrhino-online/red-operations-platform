"""create the stage_runs table

Revision ID: 0002_stage_runs
Revises: 0001_gate_decisions
Create Date: 2026-10-03

ADR 0003 makes RED's gate and decision records durable in PostgreSQL; SPEC.md
section 3 makes ``StageRun`` a core aggregate and section 4 requires a stage to
complete only through an accepted gate, recording every transition. The gate
decision ledger alone cannot report a Working stage's owner or the instant it
was entered, so the run is stored in its own table behind the
``StageRunRepository`` port. ``tenant_id`` is NOT NULL (SPEC.md section 3) and
the unique key scopes one run per client, engagement, template version and
stage; the full run (status, timestamps, pinned decisions and transition log)
lives in a ``run`` JSONB payload so a reload is re-validated through the
aggregate rather than trusted as stored. Row-level security is a deliberate
follow-up (ADR 0004, SPEC.md section 9); this migration establishes the tenant
column the policy will build on, and the adapter refuses an unscoped write.
"""

from __future__ import annotations

from alembic import op

revision = "0002_stage_runs"
down_revision = "0001_gate_decisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE stage_runs (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            engagement TEXT NOT NULL CHECK (btrim(engagement) <> ''),
            template_version TEXT NOT NULL
                CHECK (btrim(template_version) <> ''),
            stage_number INTEGER NOT NULL CHECK (stage_number >= 0),
            status TEXT NOT NULL,
            assigned_owner TEXT NOT NULL CHECK (btrim(assigned_owner) <> ''),
            entered_at DATE,
            exited_at DATE,
            run JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT stage_runs_tenant_engagement_stage_key
                UNIQUE (tenant_id, engagement, template_version, stage_number)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX stage_runs_tenant_engagement_stage_idx
            ON stage_runs (tenant_id, engagement, stage_number)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE stage_runs")

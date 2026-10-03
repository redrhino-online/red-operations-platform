"""create the workflow_runs table

Revision ID: 0009_workflow_runs
Revises: 0008_launch_qas
Create Date: 2026-10-03

ADR 0003 makes RED's durable records live in PostgreSQL and ADR 0005 requires
workflow run state to persist before side effects so a restarting worker
resumes from committed steps and preserves a waiting approval (SPEC.md sections
7 and 11). The pure workflow contract exists in ``backend/redops/workflows/``;
this table gives it the durable store the ``WorkflowRunStore`` port names.
``tenant_id`` is NOT NULL (SPEC.md section 3) and the unique key scopes one run
per client; the full run (pinned definition, status, current step, failure
reason and append-only transition log) lives in a ``run`` JSONB payload so a
reload is re-validated through the aggregate rather than trusted as stored.
``definition_id`` and ``definition_version`` are duplicated as indexed columns
so a run can be located by its pinned definition without opening the payload.
Row-level security is a deliberate follow-up (ADR 0004, SPEC.md section 9); this
migration establishes the tenant column the policy will build on, and the
adapter refuses an unscoped write.
"""

from __future__ import annotations

from alembic import op

revision = "0009_workflow_runs"
down_revision = "0008_launch_qas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE workflow_runs (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            run_id TEXT NOT NULL CHECK (btrim(run_id) <> ''),
            status TEXT NOT NULL,
            definition_id TEXT NOT NULL CHECK (btrim(definition_id) <> ''),
            definition_version TEXT NOT NULL
                CHECK (btrim(definition_version) <> ''),
            run JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT workflow_runs_tenant_run_key
                UNIQUE (tenant_id, run_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX workflow_runs_tenant_definition_idx
            ON workflow_runs (tenant_id, definition_id, definition_version)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE workflow_runs")

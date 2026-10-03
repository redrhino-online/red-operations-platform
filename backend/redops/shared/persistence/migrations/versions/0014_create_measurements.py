"""create the metric registry tables

Revision ID: 0014_measurements
Revises: 0013_build_objects
Create Date: 2026-10-03

ADR 0003 makes RED's durable records live in PostgreSQL. SPEC.md section 7 lists
``/measurements`` and SPEC.md section 3 makes a Measurement aggregate "metric
definition, window, baseline, observation, source" whose invariant keeps
observations distinct from causal conclusions; the stage 10 metric registry and
the ``/measurements`` API surface must read and write it. The value objects exist
in ``backend/redops/contexts/measurement/``; these two tables give them the
durable store the ``MeasurementRegistry`` port names. ``tenant_id`` is NOT NULL
(SPEC.md section 3) and the unique keys scope one metric version and one
observation id per client. A registered metric version and a recorded observation
are append-only, so the definition and record payloads live in JSONB and are
re-validated through the value objects on load rather than trusted as stored. Row
level security is a deliberate follow-up (ADR 0004, SPEC.md section 9); this
migration establishes the tenant column the policy will build on, and the adapter
refuses an unscoped read or write.
"""

from __future__ import annotations

from alembic import op

revision = "0014_measurements"
down_revision = "0013_build_objects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE metric_definitions (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            metric_id TEXT NOT NULL CHECK (btrim(metric_id) <> ''),
            version INTEGER NOT NULL CHECK (version > 0),
            definition JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT metric_definitions_tenant_metric_version_key
                UNIQUE (tenant_id, metric_id, version)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE measurement_records (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            record_id TEXT NOT NULL CHECK (btrim(record_id) <> ''),
            record JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT measurement_records_tenant_record_key
                UNIQUE (tenant_id, record_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE measurement_records")
    op.execute("DROP TABLE metric_definitions")

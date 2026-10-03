"""create the source_records table

Revision ID: 0011_source_records
Revises: 0010_client_workspaces
Create Date: 2026-10-03

ADR 0003 makes RED's durable records live in PostgreSQL. SPEC.md section 3 makes
a SourceRecord the immutable original a claim cites, and the
``/clients/{id}/sources`` API surface (SPEC.md section 7) must ingest and list it.
The value object exists in ``backend/redops/contexts/knowledge/``; this table
gives it the durable store the ``SourceRecordStore`` port names. ``tenant_id`` is
NOT NULL (SPEC.md section 3) and the unique key scopes one source id per client;
the locator, checksum, capture time and access rule live in a ``source`` JSONB
payload so a reload is re-validated through the value object rather than trusted
as stored. An original is immutable (SPEC.md section 3), so the adapter refuses a
same-key body with different contents. Row-level security is a deliberate
follow-up (ADR 0004, SPEC.md section 9); this migration establishes the tenant
column the policy will build on, and the adapter refuses an unscoped read or
write.
"""

from __future__ import annotations

from alembic import op

revision = "0011_source_records"
down_revision = "0010_client_workspaces"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE source_records (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            source_id TEXT NOT NULL CHECK (btrim(source_id) <> ''),
            source JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT source_records_tenant_source_key
                UNIQUE (tenant_id, source_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE source_records")

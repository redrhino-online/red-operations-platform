"""create the external_operations table

Revision ID: 0018_external_operations
Revises: 0017_opportunities
Create Date: 2026-10-03

ADR 0003 makes RED's durable records live in PostgreSQL. SPEC.md section 6 calls
connectors "outbound adapters with explicit scopes and replay safe operations"
and SPEC.md section 11 requires "duplicate delivery creates one external
operation". The process-local ``InMemoryExternalOperationStore`` cannot keep that
guarantee across a process restart, so this table gives the ``ExternalOperationStore``
port its durable store. ``tenant_id`` and ``idempotency_key`` are NOT NULL
(SPEC.md sections 3 and 9) and together they form the append-only key, so a
recorded operation is found again after a restart and a spent key is never
reused with different content. The full operation (effect identity, external
reference and delivery date) lives in JSONB and is re-validated through the value
objects on load rather than trusted as stored. ``connector`` and ``target`` are
duplicated as indexed columns so operations can be located without opening the
payload. Row level security is a deliberate follow-up (ADR 0004, SPEC.md section
9); this migration establishes the tenant column the policy will build on, and
the adapter refuses an unscoped read or write.
"""

from __future__ import annotations

from alembic import op

revision = "0018_external_operations"
down_revision = "0017_opportunities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE external_operations (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            idempotency_key TEXT NOT NULL CHECK (btrim(idempotency_key) <> ''),
            connector TEXT NOT NULL CHECK (btrim(connector) <> ''),
            target TEXT NOT NULL CHECK (btrim(target) <> ''),
            payload_digest TEXT NOT NULL CHECK (btrim(payload_digest) <> ''),
            operation JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT external_operations_key
                UNIQUE (tenant_id, idempotency_key)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX external_operations_tenant_connector_idx
            ON external_operations (tenant_id, connector)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE external_operations")

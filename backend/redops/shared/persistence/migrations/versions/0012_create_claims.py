"""create the claims table

Revision ID: 0012_claims
Revises: 0011_source_records
Create Date: 2026-10-03

ADR 0003 makes RED's durable records live in PostgreSQL. SPEC.md section 7 lists
``/claims`` and SPEC.md section 3 makes a Claim a statement with an explicit
provenance class, citations and a confidence note; the ``/claims`` API surface
must write and read it. The aggregate exists in
``backend/redops/contexts/knowledge/``; this table gives it the durable store the
``ClaimStore`` port names. ``tenant_id`` is NOT NULL (SPEC.md section 3) and the
unique key scopes one claim id per client; the statement, provenance, citations
and append-only revision history live in a ``claim`` JSONB payload so a reload is
re-validated through the value objects rather than trusted as stored. Claim
provenance changes are recorded revisions (SPEC.md sections 3 and 4), so the
adapter grows a stored claim's revision history and refuses a same-id
non-append-only re-statement. Row-level security is a deliberate follow-up
(ADR 0004, SPEC.md section 9); this migration establishes the tenant column the
policy will build on, and the adapter refuses an unscoped read or write.
"""

from __future__ import annotations

from alembic import op

revision = "0012_claims"
down_revision = "0011_source_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE claims (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            claim_id TEXT NOT NULL CHECK (btrim(claim_id) <> ''),
            claim JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT claims_tenant_claim_key
                UNIQUE (tenant_id, claim_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE claims")

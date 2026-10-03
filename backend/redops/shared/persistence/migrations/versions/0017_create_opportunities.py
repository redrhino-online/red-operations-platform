"""create the portfolio opportunity register table

Revision ID: 0017_opportunities
Revises: 0016_intervention_dismissals
Create Date: 2026-10-03

ADR 0003 makes RED's durable records live in PostgreSQL. SPEC.md section 7 lists
``/opportunities`` and SPEC.md section 1 puts portfolio expansion in the product
contract; the canon's Grow motion splits the foundation offer into smaller offers
that are new entry points and raise customer lifetime value (canon files 11 and
12; SPEC.md section 12.3). The register holds only proposals: an opportunity stays
proposed until a human investment authority acts, so the platform never stores a
proposal as client approved fact (SPEC.md sections 1 and 5). ``tenant_id`` and
``opportunity_id`` are NOT NULL (SPEC.md sections 3 and 9) and together they form
the append-only key, so one client cannot hold two records under the same id. The
opportunity payload (kind, exact source asset version, investment case, expected
outcome, owner, next action, capture date and state) lives in JSONB and is
re-validated through the value object on load rather than trusted as stored. Row
level security is a deliberate follow-up (ADR 0004, SPEC.md section 9); this
migration establishes the tenant column the policy will build on, and the adapter
refuses an unscoped read or write.
"""

from __future__ import annotations

from alembic import op

revision = "0017_opportunities"
down_revision = "0016_intervention_dismissals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE opportunities (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            opportunity_id TEXT NOT NULL CHECK (btrim(opportunity_id) <> ''),
            opportunity JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT opportunities_key
                UNIQUE (tenant_id, opportunity_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE opportunities")

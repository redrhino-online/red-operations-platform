"""create the intervention dismissal table

Revision ID: 0016_intervention_dismissals
Revises: 0015_journey_releases
Create Date: 2026-10-03

ADR 0003 makes RED's durable records live in PostgreSQL. SPEC.md section 7 lets
the command center surface intervention cards and dismiss one with rationale, and
SPEC.md section 9 requires no operator decision to be lost. The cards themselves
are derived on every read from the Governance production view, so this table
stores only the human dismissal decision. ``tenant_id``, ``client``, ``reason``
and ``subject`` are NOT NULL (SPEC.md sections 3 and 9) and together they form the
card deduplication key, so one client cannot hold two dismissals for the same
surfaced card. The dismissal payload (rationale, actor and date) lives in JSONB
and is re-validated through the value object on load rather than trusted as
stored. Row level security is a deliberate follow-up (ADR 0004, SPEC.md section
9); this migration establishes the tenant column the policy will build on, and
the adapter refuses an unscoped read or write.
"""

from __future__ import annotations

from alembic import op

revision = "0016_intervention_dismissals"
down_revision = "0015_journey_releases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE intervention_dismissals (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            client TEXT NOT NULL CHECK (btrim(client) <> ''),
            reason TEXT NOT NULL CHECK (btrim(reason) <> ''),
            subject TEXT NOT NULL CHECK (btrim(subject) <> ''),
            dismissal JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT intervention_dismissals_key
                UNIQUE (tenant_id, client, reason, subject)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE intervention_dismissals")

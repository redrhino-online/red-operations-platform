"""create the authority_amplifiers table

Revision ID: 0006_authority_amplifiers
Revises: 0005_campaign_messages
Create Date: 2026-10-03

ADR 0003 makes RED's records durable in PostgreSQL; SPEC.md section 3 makes the
stage 7 ``AuthorityAmplifier`` a reviewed production asset and section 4 requires
a passing gate to pin the exact approved asset versions and intended use. The
stage 8 to 10 gates ground on the stage 7 amplifier that received both approvals
(script before visual, then creative acceptance) at "Authority Amplifier
Approved", so that amplifier must survive a restart and be shared across the API
and worker processes rather than being re-stated from the request body.
``tenant_id`` is NOT NULL (SPEC.md section 3) and the unique key scopes one
approved amplifier per client and amplifier id; the full amplifier (its canonical
script, proof claims, visual package, both approvals and its grounding stage 6
message) lives in an ``amplifier`` JSONB payload so a reload is re-validated
through the aggregate rather than trusted as stored. Row-level security is a
deliberate follow-up (ADR 0004, SPEC.md section 9); this migration establishes the
tenant column the policy will build on, and the adapter refuses an unscoped write.
"""

from __future__ import annotations

from alembic import op

revision = "0006_authority_amplifiers"
down_revision = "0005_campaign_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE authority_amplifiers (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            amplifier_id TEXT NOT NULL CHECK (btrim(amplifier_id) <> ''),
            amplifier JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT authority_amplifiers_tenant_amplifier_key
                UNIQUE (tenant_id, amplifier_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX authority_amplifiers_tenant_amplifier_idx
            ON authority_amplifiers (tenant_id, amplifier_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE authority_amplifiers")

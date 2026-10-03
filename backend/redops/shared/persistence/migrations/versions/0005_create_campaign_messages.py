"""create the campaign_messages table

Revision ID: 0005_campaign_messages
Revises: 0004_offer_versions
Create Date: 2026-10-03

ADR 0003 makes RED's records durable in PostgreSQL; SPEC.md section 3 makes the
stage 6 ``CampaignMessage`` a core approved asset and section 4 requires a passing
gate to pin the exact approved asset versions and intended use. The stage 7 to 10
gates ground on the stage 6 message a prior gate approved at "Campaign Message
Approved", so that message must survive a restart and be shared across the API and
worker processes rather than being re-stated from the request body. ``tenant_id``
is NOT NULL (SPEC.md section 3) and the unique key scopes one approved message per
client and message id; the full message (its state, its grounding stage 5 offer
and all twelve canonical message parts) lives in a ``message`` JSONB payload so a
reload is re-validated through the aggregate rather than trusted as stored.
Row-level security is a deliberate follow-up (ADR 0004, SPEC.md section 9); this
migration establishes the tenant column the policy will build on, and the adapter
refuses an unscoped write.
"""

from __future__ import annotations

from alembic import op

revision = "0005_campaign_messages"
down_revision = "0004_offer_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE campaign_messages (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            message_id TEXT NOT NULL CHECK (btrim(message_id) <> ''),
            message JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT campaign_messages_tenant_message_key
                UNIQUE (tenant_id, message_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX campaign_messages_tenant_message_idx
            ON campaign_messages (tenant_id, message_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE campaign_messages")

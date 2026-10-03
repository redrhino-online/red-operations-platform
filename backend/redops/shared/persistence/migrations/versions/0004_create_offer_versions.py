"""create the offer_versions table

Revision ID: 0004_offer_versions
Revises: 0003_method_versions
Create Date: 2026-10-03

ADR 0003 makes RED's records durable in PostgreSQL; SPEC.md section 3 makes
``OfferVersion`` a core aggregate and section 4 requires a passing gate to pin
the exact approved asset versions and intended use. The stage 6 to 10 gates
ground on the production ready stage 5 offer a prior gate pinned, so that offer
must survive a restart and be shared across the API and worker processes rather
than being re-stated from the request body. ``tenant_id`` is NOT NULL (SPEC.md
section 3) and the unique key scopes one production ready offer per client and
offer id; the full offer (its state, its pinned method references and the
complete stage 5 delivery specification grounded on the locked Signature
Solution) lives in an ``offer`` JSONB payload so a reload is re-validated through
the aggregate rather than trusted as stored. Row-level security is a deliberate
follow-up (ADR 0004, SPEC.md section 9); this migration establishes the tenant
column the policy will build on, and the adapter refuses an unscoped write.
"""

from __future__ import annotations

from alembic import op

revision = "0004_offer_versions"
down_revision = "0003_method_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE offer_versions (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            offer_id TEXT NOT NULL CHECK (btrim(offer_id) <> ''),
            offer JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT offer_versions_tenant_offer_key
                UNIQUE (tenant_id, offer_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX offer_versions_tenant_offer_idx
            ON offer_versions (tenant_id, offer_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE offer_versions")

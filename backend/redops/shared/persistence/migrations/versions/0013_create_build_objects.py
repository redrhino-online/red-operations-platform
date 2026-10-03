"""create the build_objects table

Revision ID: 0013_build_objects
Revises: 0012_claims
Create Date: 2026-10-03

ADR 0003 makes RED's durable records live in PostgreSQL. SPEC.md section 7 lists
``/builds`` and SPEC.md section 3 makes a BuildObject the unit of production work
whose invariant is that an active build always has an owner and a next action;
the build board and the ``/builds`` API surface must read and write it. The
aggregate exists in ``backend/redops/contexts/production/``; this table gives it
the durable store the ``BuildObjectRepository`` port names. ``tenant_id`` is NOT
NULL (SPEC.md section 3) and the unique key scopes one build id per client; the
purpose, audience, owner, next action, state, blockers, refs and the append-only
transition history live in a ``build`` JSONB payload so a reload is re-validated
through the aggregate rather than trusted as stored. A build is a live aggregate,
so the adapter upserts the current snapshot per ``(tenant_id, build_id)``. Row
level security is a deliberate follow-up (ADR 0004, SPEC.md section 9); this
migration establishes the tenant column the policy will build on, and the adapter
refuses an unscoped read or write.
"""

from __future__ import annotations

from alembic import op

revision = "0013_build_objects"
down_revision = "0012_claims"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE build_objects (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            build_id TEXT NOT NULL CHECK (btrim(build_id) <> ''),
            build JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT build_objects_tenant_build_key
                UNIQUE (tenant_id, build_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE build_objects")

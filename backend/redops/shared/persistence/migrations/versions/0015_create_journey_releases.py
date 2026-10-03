"""create the journey release table

Revision ID: 0015_journey_releases
Revises: 0014_measurements
Create Date: 2026-10-03

ADR 0003 makes RED's durable records live in PostgreSQL. SPEC.md section 3 names
``JourneyRelease`` (assets, routing, configuration digest, rollback ref) as a core
aggregate whose invariant is "launch needs signed readiness and authorized
release", and SPEC.md section 7 lists ``/journeys``. The aggregate exists in
``backend/redops/contexts/execution/domain/journey_release.py``; this table gives
the ``JourneyReleaseRepository`` port the durable store the ``/journeys`` API
surface reads and writes. ``tenant_id`` and ``release_id`` are NOT NULL (SPEC.md
sections 3 and 9) and the unique key scopes one release id per client. An
authorized release is append-only, so the release payload (grounding launch QA
and exact released asset versions included) lives in JSONB and is re-validated
through the aggregate on load rather than trusted as stored. Row level security
is a deliberate follow-up (ADR 0004, SPEC.md section 9); this migration
establishes the tenant column the policy will build on, and the adapter refuses
an unscoped read or write.
"""

from __future__ import annotations

from alembic import op

revision = "0015_journey_releases"
down_revision = "0014_measurements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE journey_releases (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            release_id TEXT NOT NULL CHECK (btrim(release_id) <> ''),
            release JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT journey_releases_tenant_release_key
                UNIQUE (tenant_id, release_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE journey_releases")

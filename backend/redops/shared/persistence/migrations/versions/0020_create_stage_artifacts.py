"""create the stage artifact archive table

Revision ID: 0020_stage_artifacts
Revises: 0019_umbrella_plans
Create Date: 2026-10-10

ADR 0003 makes RED's durable records live in PostgreSQL. docs/specs/
stage-artifact-archive.md section 1 makes the platform the collection and
archiving source for every artifact of every stage, dropped as text markdown.
The archive holds the artifact's fields as typed columns rather than a JSONB
payload because the fields are queried and rendered individually: the review
surfaces organize by stage sequence and list per workspace, kind and asset.
``tenant_id``, ``workspace_id``, ``stage_number``, ``kind``, ``asset_id``,
``version``, ``markdown``, ``owner`` and ``dropped_on`` are NOT NULL and the
non-identity text columns carry non-blank CHECKs; ``note`` is the only nullable
column. ``(tenant_id, workspace_id, asset_id, version)`` forms the named
append-only key, so one client cannot hold two drops of one asset under the
same version and an identical replay is idempotent while a different body under
the same key is refused by the adapter. The listing index orders the review
read (stage, kind, asset, newest version first). The table is INSERT-only: no
update or delete path exists. Row level security is a deliberate follow-up
(ADR 0004, SPEC.md section 9); this migration establishes the tenant column the
policy will build on, and the adapter refuses an unscoped read or write.
"""

from __future__ import annotations

from alembic import op

revision = "0020_stage_artifacts"
down_revision = "0019_umbrella_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE stage_artifacts (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            workspace_id TEXT NOT NULL CHECK (btrim(workspace_id) <> ''),
            stage_number INTEGER NOT NULL CHECK (
                stage_number BETWEEN 0 AND 10
            ),
            kind TEXT NOT NULL CHECK (btrim(kind) <> ''),
            asset_id TEXT NOT NULL CHECK (btrim(asset_id) <> ''),
            version INTEGER NOT NULL CHECK (version > 0),
            markdown TEXT NOT NULL CHECK (btrim(markdown) <> ''),
            owner TEXT NOT NULL CHECK (btrim(owner) <> ''),
            dropped_on DATE NOT NULL,
            note TEXT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT stage_artifacts_key
                UNIQUE (tenant_id, workspace_id, asset_id, version)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX stage_artifacts_listing_idx
            ON stage_artifacts (
                tenant_id, workspace_id, stage_number, kind, asset_id,
                version DESC
            )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE stage_artifacts")

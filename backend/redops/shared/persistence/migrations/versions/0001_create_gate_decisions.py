"""create the gate_decisions table

Revision ID: 0001_gate_decisions
Revises:
Create Date: 2026-10-03

ADR 0003 makes RED's gate and decision records durable in PostgreSQL. This is
the first RED table: the append-only store of Governance ``GateDecision`` rows
behind the ``GateLedgerRepository`` port. SPEC.md section 3 requires every
tenant resource to carry ``tenant_id`` and section 4 requires a passing gate to
pin the exact evidence and intended downstream use; section 3 makes decision
history append-only. The table therefore has ``tenant_id`` as a NOT NULL column
with a composite index that scopes every ledger load, and keeps the full,
version-pinned decision (required asset versions, checkpoint evidence, per-asset
approvals, waiver, dependencies, blockers) in a ``decision`` JSONB payload so a
reloaded ledger can be re-validated through the domain aggregate rather than
trusted as stored.

``id BIGSERIAL`` is the append order: it is the only total order a ledger load
needs, and it lets a superseding decision be stored alongside the one it
supersedes instead of editing it. Row-level security is a deliberate follow-up
(ADR 0004, SPEC.md section 9); this migration establishes the tenant column and
index that the policy will build on, and the adapter refuses an unscoped write.
"""

from __future__ import annotations

from alembic import op

revision = "0001_gate_decisions"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE gate_decisions (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL CHECK (btrim(tenant_id) <> ''),
            template_version TEXT NOT NULL
                CHECK (btrim(template_version) <> ''),
            stage_number INTEGER NOT NULL CHECK (stage_number >= 0),
            disposition TEXT NOT NULL,
            decided_on DATE NOT NULL,
            due_on DATE NOT NULL,
            decision JSONB NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX gate_decisions_tenant_template_stage_idx
            ON gate_decisions (tenant_id, template_version, stage_number, id)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE gate_decisions")

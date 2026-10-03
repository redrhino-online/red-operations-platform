# 3. Storage strategy: keep SQLite and ChromaDB for the pilot

- Status: Proposed
- Date: 2026-10-03
- Owner: RED principal

## Context

`SPEC.md` §3 assumed PostgreSQL with row-level security and PostgreSQL
full-text/vector retrieval. The verified fork reality (`docs/fork_inventory.md`)
is a single SQLite file for episodic memory, alerts and audit, plus embedded
ChromaDB for vector retrieval. The scheduler claims due actions with
`UPDATE … RETURNING` in that single file, and per-client state is saved and
restored through `clients/slots.py`.

RED's governance artifacts (`GateDecision`, `StageRun`, `ApprovalRequest`, the
`GateLedger`) are currently pure domain and have no persistence. The pilot is a
single RED engagement (3F), so concurrent multi-tenant load is not expected.

## Decision (proposed)

Keep SQLite for the pilot as the durable store for workflow state, the audit
trail, and RED's run and decision records, with ChromaDB for retrieval. Define
repository ports so PostgreSQL remains a future adapter behind the same
interface. Revisit before onboarding a second simultaneous client or before any
requirement for concurrent writers.

## Consequences

- No migration project blocks the pilot; RED persistence reuses the fork's store.
- The write path is single-instance (see ADR 0005); no horizontal writer scaling.
- Row-level security is not available; tenant isolation relies on the slot model
  and application-scoped queries (see ADR 0004).
- A future Postgres migration is a repository-adapter swap plus a data migration;
  keeping ports clean now is the cost of that option.

## Alternatives considered

- Migrate to PostgreSQL now: rejected for the pilot — large effort, unproven need
  at single-engagement scale, and the fork's scheduler/slot logic assumes SQLite.
- New append-only event store for RED decisions: deferred — the audit log plus
  version-pinned decision records already give an append-only trail.

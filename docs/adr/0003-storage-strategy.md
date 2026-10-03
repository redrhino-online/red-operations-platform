# 3. Storage strategy: PostgreSQL container deployed with the app, on truenas PVs

- Status: Accepted
- Date: 2026-10-03
- Owner: RED principal
- Supersedes: the earlier "keep SQLite for the pilot" proposal

## Context

`SPEC.md` §3 assumed PostgreSQL with row-level security. The verified OpenExecutive
reality (`docs/fork_inventory.md`) is a single SQLite file for episodic memory,
decisions and audit, plus embedded ChromaDB for retrieval. The Atlas cluster
provides persistent volumes backed by truenas NFS shares (StorageClass
`truenas-nfs`), which the hosted instance already uses for `/data`.

## Decision

RED's persistence is **PostgreSQL, deployed as a new container alongside the
application** in the app's chart, with its data volume on truenas-backed PVs
(`truenas-nfs`). RED's aggregates (`GateLedger`, `StageRun`, `GateDecision`,
`SourceRecord`, `Claim`, approvals, RED's audit trail) live there behind
repository ports.

OpenExecutive's own internal stores stay as they are (SQLite episodic memory +
ChromaDB on the `/data` PVC), keeping changes to the dependency minimal; a later
decision may migrate OpenExec's internal memory to PostgreSQL. ChromaDB stays on
the `/data` PV for retrieval.

The chart ships the PostgreSQL container (image pinned, one instance for the
pilot), its PVC on `truenas-nfs`, a `ClusterIP` service, and connection
credentials as a SealedSecret. Schema changes ship as migrations committed with
the code.

## Consequences

- RED's gate and decision records are durable and queryable from the start, and
  the production manager view, audit trail, and future worker processes share one
  store.
- Row-level policies are available for tenant isolation (see ADR 0004).
- One PostgreSQL instance for the pilot; scaling/redundancy is a later decision.
- The backup target is still open (truenas snapshots are the candidate); restore
  drills must run before client data.
- OpenExec's internal SQLite remains a second store; RED must not treat the two
  as interchangeable.

## Alternatives considered

- Keep SQLite for RED's domain too: rejected — the requirement is a relational
  store with tenant isolation and multi-process access.
- Hosted/managed PostgreSQL outside the cluster: rejected — the cluster's
  truenas-backed PVs are the required backing.

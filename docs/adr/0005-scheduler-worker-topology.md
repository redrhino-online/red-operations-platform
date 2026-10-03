# 5. Scheduler and worker topology: single instance, gated workers

- Status: Accepted
- Date: 2026-10-03
- Owner: RED principal

## Context

The fork's scheduler claims due actions from the single SQLite file with
`UPDATE … RETURNING`, so it is not safe to run two schedulers, and the API must
run as a single instance to avoid duplicate scheduling. `SPEC.md` §6 describes a
FastAPI HTTP service plus worker processes sharing a versioned domain package and
a durable queue/outbox with idempotent workers.

RED's stage gates include `wait_for_human` approvals that must survive worker
restarts, and the pilot runs on a home k3s cluster where availability, not scale,
is the concern.

## Decision (proposed)

For the pilot, run one API instance and one scheduler, and run RED workflow
workers as separate processes only if the scheduler is gated so a single claim
path exists. Do not scale the API or scheduler horizontally until a durable claim
mechanism (queue or outbox) replaces the SQLite claim. Make workflow resumption
idempotent and persist run state before side effects.

## Consequences

- Single-instance deployment; node restart must resume in-flight approval waits.
- No horizontal scaling for the pilot; a restart-during-approval test is required.
- A future queue/outbox ADR is the gate for horizontal scaling.

## Alternatives considered

- Horizontal API/scheduler now: rejected — the SQLite claim path would double-run
  jobs and corrupt scheduling.
- Externalize scheduling to a queue immediately: deferred — more moving parts
  than the pilot needs, and it changes the fork's execution model.

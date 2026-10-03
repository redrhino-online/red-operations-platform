# 7. RED domain logic stays Python; TypeScript is UI only

- Status: Accepted
- Date: 2026-10-03
- Owner: RED principal

## Context

RED was specified and prototyped in Python in the planning repository, and its
Governance domain has been ported into this fork at
`packages/core/openexecutive/redops/` (see ADR 0002). The question arose whether
to rewrite RED in TypeScript to "stay compatible" with OpenExecutive.

The fork's core is Python: FastAPI, the orchestrator, the `workflows` engine
(including the `wait_for_human` gate primitives), the specialist `agents`, the
knowledge/RAG layer, episodic memory, the scheduler, and the append-only audit
log, all SQLite-backed. TypeScript exists only in `packages/ui` (Next.js 16).
There is no Node backend service.

## Decision

RED's domain, application, infrastructure and API logic stay in Python under
`packages/core/openexecutive/redops/`, integrated with the fork's Python core so
that the gate, decision, workflow and persistence invariants are enforced by the
same backend that runs the orchestrator, workflows, scheduler and audit trail.
TypeScript is used only for the Next.js UI and portfolio command center, which
calls the backend API and contains no RED business logic.

## Consequences

- Each RED invariant (version-pinned approvals, `GateLedger`, stage completion
  only on a passing decision, expired-prerequisite blocking) is implemented once,
  in Python, and enforced server-side.
- The UI is a thin client; it cannot grant approval or bypass a gate.
- The `redops` port proceeds in Python and is held to the fork's `ruff`, `mypy`
  and `pytest` gates.
- A TypeScript logic layer is explicitly out of scope; UI work stays in
  `packages/ui`.

## Alternatives considered

- Move RED logic to a TypeScript layer: rejected — a second implementation,
  disconnected from the Python orchestrator/workflows/scheduler and unable to
  enforce backend invariants.
- Full-stack TypeScript rewrite of the fork's backend: rejected — abandons the
  fork's working Python core and the "built on top of OpenExecutive" premise.

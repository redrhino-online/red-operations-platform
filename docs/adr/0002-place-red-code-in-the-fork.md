# 2. Place RED code inside the OpenExecutive fork

- Status: Superseded by ADR 0008 (RED code lives in the app repository)
- Date: 2026-10-03
- Owner: RED principal

## Context

RED was specified and prototyped in the planning repository
(`redrhino-online/red-operations-platform`), which holds `SPEC.md`, the
implementation plan, the licensed reference canon, and a pure-domain
`backend/redops` package (~1,600 tests). The product, however, is meant to be
built on top of OpenExecutive: it must use the fork's FastAPI/Next.js shell,
orchestrator and specialist routing, `wait_for_human` workflow gates, SQLite
episodic memory, append-only audit log, single-instance scheduler, and slot-based
client isolation.

The open question was where RED-specific code lives: inside this fork, kept in
the planning repo and consumed as a dependency, or a hybrid.

## Decision

Port RED code into this fork as `packages/core/openexecutive/redops/`
(importable as `openexecutive.redops`), following the onion layout in
`docs/context_map.md`. This fork is the primary build and deploy target. The
planning repository stays the spec and plan authority and is not a runtime
dependency.

## Consequences

- One distribution: RED code ships with `openexecutive` and can import the
  fork's modules; no separate package release or version skew.
- Existing `redops.*` imports become `openexecutive.redops.*` during the port.
- RED must respect the fork's gates (`ruff`, `mypy`, `pytest`, `make check`,
  `scripts/pr_checks.py`), not only the planning repo's unittest suite.
- The planning repository and this fork can drift; the plan records the mapping
  and the port is tracked as staged work.

## Alternatives considered

- Keep `redops` in the planning repo and consume it as a dependency: rejected —
  a second distribution, a release step, and awkward access to fork internals.
- Fresh rewrite of the domain in the fork: rejected — discards verified,
  tested domain work.

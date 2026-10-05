# 8. RED lives in the app repository; OpenExecutive is a pinned dependency

- Status: Accepted
- Date: 2026-10-03
- Owner: RED principal
- Supersedes: ADR 0002
- Amended by: ADR 0011 (vendor edits go through a re-triggerable overlay)

## Context

The first attempt to build on OpenExecutive ported RED's domain into the fork at
`packages/core/openexecutive/redops/` and made the fork the cycle target. That
diverged the dependency from upstream, so future upstream updates would be
expensive to merge, and it split the app across two repositories.

RED is meant to build on top of OpenExecutive while keeping the dependency
reusable and updatable, with maximum reuse and extendability.

## Decision

The application is `redrhino-online/red-operations-platform`; cycles target that
repository. RED code lives here under `backend/redops/` — RED's extension of the
OpenExecutive system — together with the RED backend entry points and frontend.
OpenExecutive is a pinned dependency, vendored as a git submodule at
`vendor/openexecutive/`, and is consumed through ports and composition; it stays
close to upstream, so changes to it are minimal (ideally none). The ported RED
code and RED docs are removed from the fork.

## Consequences

- Upstream OpenExecutive updates stay cheap: the fork carries little or no RED
  divergence.
- RED's code, docs and tests live in one app repository with the spec and plan.
- Reuse is explicit through ports: RED imports the fork's orchestrator,
  workflows, agents and infrastructure rather than editing them.
- ADR 0011 amends the "minimal (ideally none)" vendor-edit stance: where the
  fork's own mechanism requires in-package artifacts (ADR 0006 agent
  registration), edits are allowed but only through the committed,
  re-triggerable `vendor/overlay/` applied by `scripts/apply_vendor_overlay.sh`.
- The `openexecutive` package must be available to this repository's backend
  (a path dependency on the vendored submodule) or accessed over its API.
- TypeScript remains UI-only (ADR 0007), now rooted in this app's frontend,
  which reuses OpenExecutive's UI where possible.

## Alternatives considered

- Write RED into the fork and target it (ADR 0002): rejected — diverges the
  dependency and splits the app.
- Copy OpenExecutive modules into this repository: rejected — loses upstream
  updates and the reuse contract.

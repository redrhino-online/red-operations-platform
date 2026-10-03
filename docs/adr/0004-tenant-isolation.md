# 4. Tenant isolation: one active engagement at a time for the pilot

- Status: Proposed
- Date: 2026-10-03
- Owner: RED principal

## Context

`SPEC.md` §1/§9 call for multiple isolated client workspaces, server-side RBAC
with client membership, and cross-tenant access tests at every layer. The fork
implements slot-based, single-active-client isolation (`clients/slots.py`):
per-client SQLite tables are saved and restored, the vector store is rebuilt, and
one client is active at a time. There is no concurrent multi-tenancy and no
server-side cross-tenant RBAC.

The pilot is one RED engagement (3F) with client approvers and read-limited
collaborators.

## Decision (proposed)

For the pilot, treat a RED `ClientWorkspace` as the fork's active slot and rely
on slot isolation: one workspace active per process, with every query scoped to
the active tenant and the workspace authority registry supplying named approvers
and owners. Defer concurrent multi-tenant isolation and row-level security until
a second simultaneous client is onboarded, and gate that step on a follow-up ADR
and security tests at the API, retrieval, worker and artifact-URL layers.

## Consequences

- The pilot ships on the existing slot model; no new tenancy substrate required.
- Concurrent clients are explicitly out of scope for the pilot.
- RED must still enforce same-tenant checks in the domain (every artifact carries
  `tenant_id`, cross-tenant references are rejected) so the slot model is not the
  only defence and a later substrate can build on it.
- Security regression tests at the slot/workspace boundary are required before
  real client data.

## Alternatives considered

- Build concurrent multi-tenancy now: rejected — significant new work with no
  pilot need; the slot model is acceptable for a single engagement.
- One deployment per client: deferred — possible later isolation boundary, but
  operationally heavier than needed for the pilot.

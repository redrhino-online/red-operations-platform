# 4. Tenancy: client-scoped views, operator full view, advocates, concurrent engagements

- Status: Accepted
- Date: 2026-10-03
- Owner: RED principal

## Context

`SPEC.md` §1/§9 call for multiple isolated client workspaces and server-side RBAC.
OpenExecutive implements slot-based, single-active-client isolation; there is no
concurrent multi-tenancy and no cross-tenant RBAC. RED's needs differ in shape:
operators must see everything, clients must see only their own, and some RED team
members work a narrowed caseload.

## Decision

- **Clients** see only their own workspace. Every client-scoped query is filtered
  by tenant, enforced at the application boundary and in PostgreSQL (row-level
  policies as defence in depth).
- **Operators** (RED staff) see the full cross-client view — the portfolio command
  center, all workspaces, all gates.
- **Advocates** are RED team members assigned to specific cases with narrowed
  views of the team's data (their assigned engagements only), not full operator
  access.
- **One active engagement per client is the default shape, not a limit.** A
  long-term or enterprise client may have multiple engagements and multiple assets
  in flight at once; the domain and data model must support that fan-out and must
  not cap engagements per client.

The hosted pilot keeps OpenExec's slot model (one active client per process) as
an infrastructure constraint for a single engagement; it does not leak into RED's
domain model. Removing that constraint for enterprise scale is a follow-up
infrastructure decision.

## Consequences

- RED's data model keys every artifact by `tenant_id` and treats engagements as
  per-client collections that may be many.
- Roles are explicit: `client`, `advocate`, `operator`. Advocates' queries are
  scoped to their assigned cases; operators' are not.
- Isolation tests must cover all three roles at the API, repository, and
  (later) row-policy layers.
- OpenExec's slot isolation cannot serve the client-facing surface once more than
  one client is live; a hosting ADR is required before that step.

## Alternatives considered

- Strict one-engagement-per-client: rejected — enterprise clients need
  concurrent work.
- Full multi-tenant infrastructure from day one: deferred — the pilot runs one
  engagement; the domain model carries the tenancy, the host catches up.

# 1. Record architecture decisions

- Status: Accepted
- Date: 2026-10-03
- Owner: RED principal

## Context

The RED Operations Platform is built on top of the OpenExecutive fork. Until
now, decisions lived in code review and the planning repository. As RED adds
bounded contexts, storage, tenancy and delivery on top of an existing codebase,
the reasoning behind each choice must be durable and reviewable.

## Decision

Record architecturally significant decisions as numbered Markdown ADRs in
`docs/adr/`, one file per decision, using: Status, Date, Owner, Context,
Decision, Consequences, Alternatives. A decision touched by later work gets a
new superseding ADR rather than an edit to history.

## Consequences

- Decisions and their rationale survive reorganisation and handover.
- ADRs are ordinary docs and do not trip the architecture-doc drift check.

## Alternatives considered

- A single running `docs/decisions.md`: rejected — hard to review and supersede.

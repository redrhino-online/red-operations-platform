# Contributing

## Golden rules

- **Spec wins.** `SPEC.md` governs product, authority, tenancy, security,
  persistence and delivery. Where the canon conflicts, the spec wins.
- **No draft as fact.** Never represent a draft or model inference as
  client-approved. Approval is a human, version-specific act.
- **Onion discipline.** `domain/` stays pure. New external effects go behind a
  port with an in-memory reference adapter and a contract test.
- **Tenant always.** Every resource and query is tenant-scoped.
- **Reversible migrations.** Every migration has a working `downgrade()` (ADR 0010).
- **Vendor edits only via the overlay** (ADR 0011). Never hand-edit
  `vendor/openexecutive/`.

## Workflow

1. Pick the highest-value ready item (the plan's "Current cycle status" names it).
2. Write a failing behavioural test for a new rule, then the smallest passing
   change.
3. `make check` must pass. For a new method artifact, encode the canon-informed
   shape as value objects, invariants, named errors and tests.
4. Update `IMPLEMENTATION_PLAN.md` (cycle record, completed item, next ready item).
5. Commit with a Conventional Commit; the harness/you push to `origin`.

## Conventional Commits

`type(scope): imperative summary` (≤72 chars), blank line, then a body explaining
**why**: the problem, constraints, alternatives rejected, dependencies and
downstream effects. Types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`,
`build`, `ci`, `chore`, `style`, `revert`.

## Architecture Decision Records

Durable decisions live in `docs/adr/` as numbered Markdown files: context,
decision, consequences, alternatives. Add an ADR for a cross-cutting or
hard-to-reverse choice; supersede rather than silently rewrite.

## Maintaining these docs

- **Every noun gets a row** in [Nouns and their RED significance](architecture/nouns.md).
  A cycle that adds an aggregate, seam, env var or pipeline concept adds its row.
- One page per topic under `docs/`. New files are auto-included by MkDocs; add a
  `nav` entry in `mkdocs.yml` only if it belongs in the sidebar.
- Preview with `make docs-serve`; the workflow publishes on push to `main`.

## Adding an agent

Follow SPEC §5 and the fork's specialist procedure: a charter in
`docs/agents/`, a `RedAgentSpec` row, and (for a core specialist) the vendor
overlay registration. Reserved capability slots stay proposal-only with no tools.

## Adding a canon-informed asset kind

Add the typed value object + `as_stage_asset(version=)`, wire the kind through the
`StageTemplate` factory in stage order, add gate-integrity tests that pin exact
versions, and record it in the canon gap register and [Nouns](architecture/nouns.md).

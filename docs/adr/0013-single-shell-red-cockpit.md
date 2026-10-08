# 13. Single shell: the cockpit is the RED Operations Director

- Status: Accepted
- Date: 2026-10-08
- Owner: RED principal
- Amends: ADR 0012 (the two-app state is a stepping stone only; the adoption deepens into one shell)
- Amends: ADR 0008's UI-root wording (the RED UI root moves into the vendored cockpit)
- Amended by: ADR 0014 (the fork is absorbed; vendor changes are additive, not overlay-declared)

## Context

The prototype definition of done (SPEC.md section 13) passes and the deployed
system runs two user-facing UIs: the rebranded OpenExecutive cockpit at `/` and
the twelve-screen thin client at `/screens/*`, cross-linked by the cockpit's RED
Operations nav group. The owner reports the result reads as a bolt-on: the
purpose-built screens do not share the cockpit's theme or components, and they
render errors or empty states because every screen carries its own free-text
tenant/engagement form whose defaults (`3fmindset`) do not exist in the deployed
database, so several RED endpoints answer 404/422 on first load.

ADR 0012 already rejected two cross-linked apps as the end state and declared
the deeper adoption: bring the cockpit in, rebranded RED, and replace the
generic surfaces with RED's agents. The owner's 2026-10-08 directive makes that
the active phase, including the product-level overhaul: the cockpit's home,
departments, knowledge and workflows take on the context and fundamentals of the
RED system and its reference canon.

## Decision

1. **Single shell end state.** The rebranded OpenExecutive cockpit is the only
   user-facing web UI. The twelve section 8 screens become native cockpit pages
   at `/operations/*`, implemented as additive files under
   `vendor/openexecutive/packages/ui/src/app/operations/` (ADR 0014), styled
   with the cockpit's own Tailwind v4 semantic tokens and component patterns
   rather than the thin client's bespoke palette.
2. **Shared client context.** A workspace/engagement picker in the shell
   persists the selected client and engagement and drives every RED screen; the
   per-screen free-text tenant/engagement forms are removed. Screens read the
   RED API same-origin at `/red` (routed by ingress to the RED API), with a
   local-development proxy for `next dev`.
3. **The thin client is retired** after the port passes verification:
   `frontend/`, `Dockerfile.ui`, the `redop-ui` Deployment and the `/screens`
   ingress route are removed, and the section 13 condition 6 gate is rewritten
   to exercise the cockpit pages instead.
4. **Home is the portfolio command center.** The landing surface is the RED
   command center (SPEC.md section 2's "Rework into portfolio command center" is
   satisfied natively); Briefing is retargeted to RED's daily brief.
5. **Product-level RED overhaul continues in the same phase:** the canon corpus
   is ingested into the cockpit Knowledge domain repeatably (the 2026-10-07
   initialization seeded it manually; the seed becomes a verifiable script and
   grounding eval); the runtime Departments/Council/People stores are seeded
   with RED's nine agents plus the chartered proposal-only slots 10 and 11
   (ADR 0006); and the stage 0-10 pipeline is registered as cockpit workflow
   definitions whose `wait_for_human` gates bind to RED approvals, surfaced in
   Jobs and bridged to the RED approval inbox.
6. **The harness gate extends.** `make done` gains a `[7/7]` single-shell check
   (`scripts/check_cockpit_overhaul.sh`) implementing SPEC.md section 14; the
   section 13 checks remain prerequisites. The phase is tracked as the K queue
   in `IMPLEMENTATION_PLAN.md`.

Absorbing the fork ("standard executive install, then rewrite the source in
place") was first rejected here in favor of the overlay; ADR 0014, adopted the
same day, reverses that: the fork is absorbed into this repository, RED changes
inside it stay additive, and upstream remains reachable through the recorded
pin. The capability gain is the same; the update path is preserved by the
additive rule rather than by the submodule.

## Consequences

- One theme, one chrome, one navigation source, one UI deployment; the
  two-app brand and context drift disappears.
- The vendor tree gains the twelve pages plus their tests as additive files;
  the additive gate (`scripts/check_vendor_additive.sh`, ADR 0014) keeps the
  RED-side divergence reviewable.
- The cockpit image grows (more routes, test dev dependencies); the Gitea CI
  build memory stays a watch item (the build already caps the Node heap).
- Two data stores coexist as before: the cockpit's OpenExecutive SQLite/Chroma
  state and RED's PostgreSQL.
- ADR 0007 stands: TypeScript stays UI-only; ported screens carry no RED
  business logic and cannot approve, release or authorize anything.
- The section 13 gate keeps passing throughout the phase; the new `[7/7]` fails
  until the K queue completes, which stops a premature `.ralph/DONE`.

## Alternatives considered

- Keep two apps and restyle the thin client to match the cockpit: rejected as
  the end state (ADR 0012 already rejected it); not chosen even as an interim
  because the context fix and the port share most of their work.
- Hard-fork rewrite of the vendor source with RED agents, workflows and
  departments: rejected — same user-visible result, but it severs upstream
  updates and re-splits the app across repositories (the ADR 0008 lesson).
- Embed the thin client in an iframe inside the cockpit: rejected — two chrome
  shells, broken navigation context, no shared theme, and the sidebar linkage
  stays a bolt-on.

# 12. Adopt the OpenExecutive cockpit UI as the prototype shell (declared vision)

- Status: Accepted (vision; scheduled after the prototype definition of done)
- Date: 2026-10-05
- Owner: RED principal
- Amends: ADR 0008 (reuse the fork's UI where possible)
- Amended by: ADR 0013 (single shell), ADR 0014 (the overlay rebrand is absorbed into the committed baseline)

## Context

The prototype definition of done (SPEC.md section 13) passes: the RED API and UI
are deployed on Atlas, condition 9 is met, and the twelve section 8 screens are
live. The RED frontend is a thin Next.js client (ADR 0007) with a landing
dashboard and a persistent sidebar (Q51), but it is not the full product
experience the owner expects.

The vendored OpenExecutive UI (`vendor/openexecutive/packages/ui`) is a complete
Next.js cockpit: Briefing/Today, Chats, Council, Departments, People, Knowledge,
Memories, Skills, Jobs, Watchlist, Audit, Review, Goals and Settings, with a
single navigation source (`components/shell/navConfig.ts`) and an "OE"
`BrandMark`. It is not deployed. The RED API already mounts the whole
OpenExecutive ASGI app at `/openexecutive` (`backend/redops/api/app.py`), so the
cockpit backend is reachable; only the UI and its ingress/proxy route are
missing.

The owner's directive (2026-10-05): bring the OpenExecutive cockpit experience
in, rebranded RED, with navigation following the current OpenExecutive UI, and
declare the adoption as a vision phase between the prototype definition of done
and the production-readiness phase. The immediate navigation work (Q51) is done;
this ADR records the larger adoption.

Constraints: ADR 0011 requires every vendor edit to be overlay-declared and
re-triggerable; ADR 0006 retires the generic C-suite personas; SPEC.md section 13
condition 8 requires no OpenExecutive branding in user-facing surfaces; the owner
chose auth disabled and internal-only, and the cockpit keeping its own
OpenExecutive SQLite/Chroma state.

## Decision

Adopt the vendored OpenExecutive UI as the prototype shell in a phase that sits
between the prototype definition of done and the production-readiness phase:

- **Shell**: build and deploy `vendor/openexecutive/packages/ui` as the UI,
  rebranded RED through the ADR 0011 overlay (BrandMark OE to RED, titles, copy
  and navigation labels).
- **Navigation**: keep the OpenExecutive groups and add a **RED Operations**
  group linking the twelve section 8 screens (the Q51 single source of truth).
- **Personas**: replace the generic C-suite Departments/Council/People surfaces
  with RED's nine agents plus capability slots 10 and 11 (ADR 0006).
- **Auth**: disabled, internal-only behind the `10.0.0.0/8` ingress allowlist,
  matching the current shell.
- **Backend**: the cockpit runs against the already-mounted `/openexecutive`
  backend; add the `/api/backend` proxy and ingress route. The cockpit keeps its
  own OpenExecutive SQLite/Chroma state on the `redop-data` PVC; the RED screens
  keep using `/red` and PostgreSQL.
- **Integrity**: every vendor edit is overlay-declared (condition 7) and no
  OpenExecutive branding remains in user-facing surfaces (condition 8).

SPEC.md section 2's "Cockpit: Rework into portfolio command center" is satisfied
by this adoption: the OpenExecutive cockpit is reworked into the RED portfolio
command center with a RED Operations group. If the wording is read to forbid
reusing the cockpit, amend that clause rather than silently diverging.

This phase is explicitly **not** part of the current prototype definition of
done, which already passes; it is declared work for the interval before
production readiness.

## Consequences

- The prototype keeps passing `make done`; the cockpit adoption is additive and
  gated by its own items.
- The vendor overlay surface grows from core-only to include UI files, so an
  upstream submodule bump must re-apply and re-verify more (ADR 0011's cost).
- The generic personas are replaced, closing ADR 0006's remaining follow-up.
- Two data stores coexist: RED's PostgreSQL and the cockpit's OpenExecutive
  SQLite/Chroma.
- Auth stays disabled for the prototype; the identity provider remains a
  production-phase decision.

## Alternatives considered

- Rebuild the cockpit experience natively in RED's frontend against
  `/openexecutive` (Option C): rejected for now - reimplements a large UI rather
  than reusing the fork's, against ADR 0008's reuse intent.
- Run the cockpit and the RED frontend as two cross-linked apps (Option B):
  rejected as the end state; may serve as a stepping stone.
- Skip the cockpit and keep only the twelve-screen client (Option 4): rejected by
  the owner, who wants the OpenExecutive experience.

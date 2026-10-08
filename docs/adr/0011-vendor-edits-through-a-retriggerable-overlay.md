# 11. Vendor edits go through a re-triggerable overlay

- Status: Superseded by ADR 0014 (the fork is absorbed; the overlay machinery is retired)
- Date: 2026-10-04
- Owner: RED principal
- Amends: ADR 0008 (the "minimal (ideally none)" vendor-edit stance)

## Context

ADR 0008 keeps OpenExecutive a pinned git submodule at `vendor/openexecutive/`
and states that changes to it are "minimal (ideally none)". SPEC.md section 13
condition 7 required "the vendored OpenExecutive is unmodified" and DoD `[4/6]`
failed `make done` on any local change to the submodule. Every RED gap was to be
closed in `backend/redops/` through ports, adapters and composition.

ADR 0006 (RED agent registration over the specialist registry) requires RED's
agents to be registered through the fork's own mechanism, whose mandatory
artifacts live inside the vendored package: `agents/`, `prompts/domain_prompts.py`,
`orchestrator/router.py` (`SPECIALIST_REGISTRY`), `orchestrator/answer_sources.py`
(`_AREAS`), `knowledge/`, and `evals/_scenarios/`. Queue item Q3 therefore cannot
be done without editing the vendor tree, and Q3 blocks condition 5's
deterministic agent path (and Q30). The zero-edit rule and ADR 0006 were in
direct tension, which stopped the build loop.

## Decision

Allow vendor edits, but only through a committed, idempotent, re-triggerable
overlay owned by this repository:

1. RED-authored vendor additions live in this repository under `vendor/overlay/`
   (new files under `vendor/overlay/files/` mirroring the vendor layout, plus
   marked insertion snippets under `vendor/overlay/hooks/`). The app repository
   stays the source of truth; the submodule is a derived target.
2. `scripts/apply_vendor_overlay.sh` applies the overlay onto
   `vendor/openexecutive/` idempotently. Re-running it is a no-op; after an
   upstream submodule bump it re-applies the same overlay onto the new commit.
   In-place hooks are spliced between explicit `RED-OVERLAY:BEGIN/END` markers, so
   apply removes and re-inserts its own block rather than appending duplicates.
3. `scripts/apply_vendor_overlay.sh --check` proves the vendor working tree equals
   the overlay applied onto the pinned commit, and that no tracked or untracked
   vendor change is outside the overlay. It fails loudly when an upstream change
   moves a hook anchor, so drift is caught rather than silently lost.
4. SPEC.md section 13 condition 7 and DoD `[4/6]` change from "the submodule is
   clean" to "every vendor change is overlay-declared and reproducible from this
   repository". RED's own domain, app and frontend code still lives in
   `backend/redops/` and `frontend/` through ports, adapters and composition;
   only the fork-integration seams ADR 0006 names are overlaid.

## Consequences

- Q3 is unblocked: RED agents can be registered through the fork's specialist
  mechanism without hand-editing the submodule, and condition 5's deterministic
  agent path can be built.
- Upstream updates become a two-step operation: bump the submodule, re-run
  `scripts/apply_vendor_overlay.sh`, and fix the overlay if a hook anchor moved.
  The overlay is the merge unit, not a hand-resolved diff.
- The vendor diff stays attributable and small: it is exactly the overlay
  manifest, so a reviewer reads `vendor/overlay/`, not the submodule.
- The zero-vendor-edit guarantee is replaced by a reproducibility guarantee.
  This is weaker than byte-identical upstream, and that is the deliberate cost of
  the fork-integration requirement in ADR 0006.
- DoD `[4/6]` is now `scripts/apply_vendor_overlay.sh --check` (plus the existing
  `check_vendor_overlay` semantics), not `git status` on the submodule.

## Alternatives considered

- Keep zero vendor edits and inject agents from `backend/redops/` only: rejected
  by the owner because the fork's mandatory specialist artifacts (registry,
  prompt module, knowledge, evals, `_AREAS`) live in the package and its CI
  checks them; a composition-only adapter would not use the fork's mechanism.
- A committed patch file applied with `git apply --3way`: rejected by the owner —
  line-shift fragility; the practical mechanism is an idempotent apply script.
- Commit RED changes directly into the fork and track a fork branch: rejected —
  diverges the dependency and splits the app (the reason ADR 0008 superseded
  ADR 0002).
- Vendor the package by copy instead of submodule: rejected — loses upstream
  updates and the reuse contract.

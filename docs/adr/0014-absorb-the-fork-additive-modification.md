# 14. Absorb the OpenExecutive fork into this repository; RED changes inside it are additive

- Status: Accepted
- Date: 2026-10-08
- Owner: RED principal
- Supersedes: ADR 0011 (the overlay edit mechanism is retired)
- Amends: ADR 0008 (pinned submodule dependency becomes an absorbed tracked tree), ADR 0012 (the rebrand arrives via the overlay no longer; it is the absorbed baseline), ADR 0013 (overlay-file wording and its rejection of absorbing the fork)

## Context

The single-shell cockpit overhaul (ADR 0013, SPEC.md section 14) may require
substantial modification of the vendored OpenExecutive source. The standing
rules — the vendor "stays close to upstream" with minimal (ideally none)
changes (ADR 0008) and every edit arrives only through the committed
re-triggerable overlay (ADR 0011) — were written for a lightly-adapted
dependency, not for a product the owner intends to reshape. Whole-file
copy-on-write overlays fight deep rewrites, and the submodule pointer carries a
permanently dirty working tree.

The owner's directive (2026-10-08): absorb the fork so it can be modified as
first-class code, while keeping upstream reachable and keeping RED's own
changes inside the vendor tree from churning upstream's untouched files.

## Decision

1. **The fork is absorbed.** The `vendor/openexecutive` gitlink is removed and
   the tree is committed to this repository as ordinary tracked files. The
   absorbed baseline is upstream commit `31e55338db7f7a0eb7ff30b4cb8942a1ece551bd`
   (v0.4.6) with the previously applied RED overlay content (rebrand, nav
   group, RED agent registration, prompt and knowledge additions) already in
   place: those become the committed baseline.
2. **Upstream stays reachable.** The upstream URL and pinned commit are
   recorded in `docs/fork_inventory.md`. Taking upstream updates is an
   owner-driven merge against the absorbed tree, recorded in the fork diff
   register; afterwards `make vendor-pin` re-baselines the manifest. Upstream is
   reference, not a tracking dependency.
3. **RED changes inside the vendor tree are additive by default.** Cycles add
   new files (the `/operations/*` screen pages, `redops_*` modules, tests) and
   do not modify other files. Two classes are exempt from the lock:
   - **RED-adopted surfaces** — the files the applied overlay already modified
     or added at absorption (nav, brand, proxy, registration splices, RED
     agent/prompt/knowledge modules). RED owns these; they are listed in
     `vendor/red-owned-files.txt` and stay freely editable.
   - **Owner-approved exceptions** — any other modification requires a
     named-owner decision recorded in `docs/fork_inventory.md` followed by a
     deliberate `make vendor-pin` re-baseline. Unattended cycles never re-pin
     and never approve exceptions.
4. **The machine gate.** `vendor/upstream-files.txt` lists every
   upstream-origin path (the pinned commit's tree); `vendor/upstream-manifest.sha256`
   records the sha256 of each locked file at the baseline;
   `scripts/check_vendor_additive.sh` (DoD step `[4/7]`) fails when a locked
   file's bytes differ from the manifest. New files and red-owned files are
   unrestricted.
5. **The overlay machinery is retired:** `vendor/overlay/`,
   `scripts/apply_vendor_overlay.sh`, `scripts/vendor_overlay.py` and their
   test are removed; Dockerfiles build from the absorbed tree directly.

## Consequences

- Deep cockpit work (the K queue) iterates directly in the vendor tree instead
  of through whole-file overlay copies; the dirty-submodule pointer problem
  disappears because the tree is this repository's own committed state.
- Upstream updates cost a real merge against an absorbed tree (the ADR 0008
  concern, now accepted): the recorded pin keeps the merge possible, and the
  additive gate makes RED-side divergence reviewable.
- The existing rebrand and agent registration are grandfathered; re-splicing
  them after an upstream merge uses the exception path.
- Component tests for the ported screens live in the repo-side
  `tests/cockpit-ui/` suite rather than inside the vendor `package.json`
  (additive by definition; no upstream file edit needed).
- LICENSE and NOTICE retention and the no-OpenExecutive-branding rule are
  unchanged.

## Alternatives considered

- Keep the submodule and overlay, drop only the "minimal change" rule:
  rejected — the copy-on-write pattern is the obstacle, not the minimality
  rule; deep rewrites would still be funneled through whole-file overlay
  copies.
- Keep the submodule and allow direct edits: rejected — a permanently dirty
  submodule loses the pointer's meaning and the integrity gate.
- Absorb with no modification rule at all: rejected — the additive lock keeps
  upstream merges reviewable and preserves exactly which lines are ours.

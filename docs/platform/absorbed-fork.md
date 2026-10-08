# The absorbed fork and the additive rule

OpenExecutive is no longer a submodule. The fork is **absorbed** into this
repository: `vendor/openexecutive/` is ordinary tracked source, baselined at
upstream commit `31e55338db7f7a0eb7ff30b4cb8942a1ece551bd` (v0.4.6) with the
RED adoption (rebrand, navigation, agent registration, prompts, knowledge)
already in place (ADR 0014).

## The rule

RED changes inside the vendor tree are **additive by default**:

- Cycles **add new files** (the `/operations/*` screen pages, `redops_*`
  modules, tests) and never modify other files.
- **RED-adopted surfaces** — the files the adoption already changed or added at
  absorption, listed in `vendor/red-owned-files.txt` — stay freely editable.
  These are the cockpit nav, brand, proxy and middleware, the specialist
  registry and answer-source splices, and the RED agent, prompt, knowledge and
  eval modules.
- Any other modification of an upstream-origin file needs a **named-owner
  decision** recorded in `docs/fork_inventory.md` followed by a deliberate
  `make vendor-pin` re-baseline. Unattended cycles never re-pin and never
  approve exceptions.

## The gate

`vendor/upstream-files.txt` lists every upstream-origin path at the baseline;
`vendor/upstream-manifest.sha256` records the sha256 of each locked file.
`scripts/check_vendor_additive.sh` (DoD `[4/7]`) re-hashes the locked files and
fails on any difference. New files and red-owned files are unrestricted.

## Commands

```sh
# verify the additive rule holds
scripts/check_vendor_additive.sh

# owner action only: re-baseline after an approved exception or an upstream merge
make vendor-pin
```

## Taking upstream updates

Upstream is reference, not a tracking dependency. To pull an upstream change:

1. Fetch upstream (URL recorded in `docs/fork_inventory.md`) and merge the
   desired commit into the absorbed tree by hand.
2. Resolve conflicts, keeping RED-owned surfaces intact.
3. Record the merge (commit, decision, owner) in `docs/fork_inventory.md`.
4. `make vendor-pin` to re-baseline the manifest for the new upstream state.
5. `scripts/check_vendor_additive.sh` and `make done` must pass.

## Boundaries

- LICENSE and NOTICE under `vendor/openexecutive/` are retained (Apache-2.0).
- No OpenExecutive branding in user-facing surfaces (DoD `[5/7]`).
- RED domain logic stays in `backend/redops/` (ADR 0007); the vendor tree hosts
  UI surfaces and fork-mechanism artifacts, never RED business rules.

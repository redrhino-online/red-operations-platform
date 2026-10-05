# Vendor overlay

OpenExecutive is a pinned git submodule at `vendor/openexecutive/` (ADR 0008).
Its **internals are out of scope** for these docs — but the **overlay that edits
it is in scope**: RED-authorised changes to the submodule are allowed only
through the committed, re-triggerable overlay (ADR 0011).

## Why an overlay exists

The fork's own specialist mechanism (ADR 0006) requires artifacts that live
*inside* the package: agent classes, a prompt module, the `SPECIALIST_REGISTRY`
entry, `_AREAS`, knowledge and eval scenarios. Registering RED agents through that
mechanism means editing the vendored tree. The overlay makes those edits declared,
reproducible and cheap to re-apply after an upstream bump.

## How it works

```text
vendor/overlay/
  files/    ← mirrors the vendor layout; each file is copied verbatim
  hooks/    ← manifest.txt + snippets spliced into existing vendor files
scripts/apply_vendor_overlay.sh   ← apply, or --check
scripts/vendor_overlay.py         ← the logic
```

- **Overlay file** — a file under `vendor/overlay/files/<path>` is copied onto
  `vendor/openexecutive/<path>`.
- **Hook snippet** — a snippet listed in `hooks/manifest.txt`
  (`<target> <snippet> <marker>`) is spliced into the target between
  `# RED-OVERLAY:BEGIN <marker>` and `# RED-OVERLAY:END <marker>`. Re-applying
  replaces its own block, so apply is idempotent.

Current overlay content registers the nine core RED specialists:
`agents/redops_agents.py`, `prompts/redops_prompts.py`, knowledge, one eval
scenario, and hooks into `orchestrator/router.py` and
`orchestrator/answer_sources.py`.

## Commands

```sh
# apply after a fresh checkout or an upstream bump
git submodule update --init vendor/openexecutive
scripts/apply_vendor_overlay.sh

# verify: vendor tree == overlay applied onto the pinned commit, no extra change
scripts/apply_vendor_overlay.sh --check
```

`make done` `[4/6]` runs apply then `--check`; `scripts/check_vendor_overlay.sh`
semantics are enforced by the overlay check itself. An unaccounted vendor change,
a missing file, or a moved hook anchor fails loudly.

## Bumping upstream

1. Bump the submodule to the new commit.
2. `scripts/apply_vendor_overlay.sh`.
3. If a hook anchor moved, the apply fails loudly — fix the hook or target.
4. `scripts/apply_vendor_overlay.sh --check` must pass.

## Adding an overlay change

1. Put new vendor files under `vendor/overlay/files/<same path>`.
2. For an in-place edit, add a snippet under `vendor/overlay/hooks/` and a line in
   `hooks/manifest.txt`; splice imports of RED code at the very end of the file
   using the marker guard (the guarded block degrades safely if RED code is
   absent).
3. `scripts/apply_vendor_overlay.sh`, then `--check`.
4. Update [Nouns](../architecture/nouns.md) §17.

## Boundaries

- Never hand-edit `vendor/openexecutive/` outside the overlay; the check fails.
- Never touch anything outside this repository beyond the sanctioned overlay
  targets (see the deploy and harness rules).
- The generic corporate personas remain registered; retiring them is a separate
  characterised change (ADR 0006).

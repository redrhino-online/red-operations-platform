# RED vendor overlay

This directory is the committed source of truth for every local change RED makes
to the vendored OpenExecutive submodule (`vendor/openexecutive/`). See ADR 0011.

- `files/` mirrors the vendor layout. Each file is copied verbatim onto
  `vendor/openexecutive/<same path>`.
- `hooks/manifest.txt` lists in-place insertions. Each snippet is spliced into an
  existing vendor file between `# RED-OVERLAY:BEGIN <marker>` and
  `# RED-OVERLAY:END <marker>`, so re-applying replaces the block instead of
  duplicating it.

Apply after checking out or bumping the submodule:

```sh
git submodule update --init vendor/openexecutive
scripts/apply_vendor_overlay.sh
```

Verify (also DoD `[4/6]`, SPEC.md section 13 condition 7):

```sh
scripts/apply_vendor_overlay.sh --check
```

Re-triggered on upstream change: bump the submodule, run the apply script, and if
a hook anchor moved the check fails loudly so the overlay is fixed rather than
silently losing the registration.

## Known follow-ups

- The generic corporate personas remain registered; retiring them is a separate
  characterised change (ADR 0006).
- Capability slots 10 and 11 are chartered (`docs/agents/`) but not registered as
  routable specialists, because SPEC.md section 5 reserves them as proposal-only
  with no execution permissions.

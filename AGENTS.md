# Agent Instructions

## Commits and pushing

- **Always push to `origin` after committing.** After any commit on this
  repository, immediately run `git push origin <branch>` (normally `main`) so
  the GitHub remote never lags the local branch. Do this automatically; do not
  wait to be asked.
- Only commit when the user asks or the task requires it. When you do commit,
  push to `origin` as part of the same step.
- Use Conventional Commits: `type(scope): imperative summary` (types: `feat`,
  `fix`, `refactor`, `perf`, `test`, `docs`, `build`, `ci`, `chore`, `style`,
  `revert`), subject under 72 characters, blank second line, then a body that
  explains why the change was made.
- The `atlas` remote (Gitea forge) is published by the Ralph harness
  (`ralph_cycle.sh`), including on the final cycle. Harness cycles push to
  `origin` only. **Any commit made at a user's request is pushed to both
  `origin` and `atlas`** as part of the same step (owner rule, 2026-10-10);
  a push to `atlas` `main` triggers the Gitea build workflow.
- Never push to `upstream`.

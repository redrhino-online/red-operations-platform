# 9. Prototype excludes backup and restore; deferred to a production phase

- Status: Accepted
- Date: 2026-10-03
- Owner: RED principal

## Context

SPEC.md section 9 sets pilot targets that include "recoverable database backup
with a 24 hour recovery point and 8 hour recovery time" and instructs operators
to "conduct restore drills before production". SPEC.md section 11 lists
"database backup restores the approval trail" as one of the ten minimum
acceptance scenarios, and section 13 condition 2 requires the section 11
acceptance suite to be green. Together these make a backup target and a restore
drill prerequisites for the prototype definition of done.

The prototype is explicitly not a production deployment: it is validated before
any production use. Requiring backup provisioning and a witnessed restore drill
now forces a storage/credential decision and cluster operations work ahead of
that validation, for data the prototype does not yet serve in production.

The deployment mechanism is separately decided (see the app repo's issue #3):
the Helm chart lives in this repository, the GitOps repository holds the Argo CD
Application and pinned values, and a release is a push to the forge that builds
and promotes an image. Release rollback remains in scope.

## Decision

Remove database backup and restore from the prototype definition of done and
defer them to a later production-readiness phase:

- Strike "database backup restores the approval trail" from the section 11
  minimum acceptance scenarios, leaving nine.
- Reclassify the section 9 backup, recovery-point, recovery-time and
  restore-drill targets as production requirements, not prototype acceptance
  criteria. The prototype keeps its data durable in PostgreSQL but provisions no
  backup and runs no restore drill.
- Keep the `gitops-revert-restores` scenario. Release rollback (revert the
  GitOps image digest and verify the previous compatible version serves) is
  retained because it proves the deployment and rollback mechanism the prototype
  is meant to validate.
- Record the backup target, RPO/RTO confirmation and restore drill as an open
  decision owned by the RED principal, to be settled in the production phase
  before any real client data is onboarded.

## Consequences

- DoD condition 2 now requires nine section 11 acceptance scenarios.
  `scripts/check_acceptance_coverage.sh` and `tests/acceptance/covered-scenarios.txt`
  no longer require `backup-restores-approval-trail`.
- Condition 2's only remaining deploy-gated scenario is `gitops-revert-restores`,
  so the deploy slice Q47-Q50 stays on the prototype critical path, and condition
  9 (deployed on the Atlas k3s cluster) is unchanged.
- The prototype needs no backup-target decision. The deploy slice's Q49 is the
  Argo CD Application plus migration-before-serve ordering, with no coupled
  backup work.
- Before production, a backup target, RPO/RTO and a witnessed restore drill must
  still be provided. Until then the prototype must not hold the sole copy of
  production client data.
- "No lost approval or decision records" is still met at the prototype by durable
  append-only PostgreSQL persistence; disaster recovery is the deferred part.

## Alternatives considered

- Keep backup in the prototype: rejected - blocks the prototype on storage and
  operations work for a system that is not yet production.
- Defer both deploy-only scenarios (backup and `gitops-revert-restores`):
  rejected - the GitOps revert is the evidence that the push-to-forge deployment
  and rollback mechanism works.
- Provide a backup but skip the restore drill: rejected - an undrilled backup is
  not evidence, and a partial claim would misrepresent readiness.

# 10. Reversible migrations; backup and rollback are production-readiness gates

- Status: Accepted
- Date: 2026-10-03
- Owner: RED principal

## Context

ADR 0009 removed the database backup and restore drill from the prototype
definition of done but kept the `gitops-revert-restores` scenario in the section
11 acceptance suite, on the reasoning that release rollback proves the
push-to-forge deployment mechanism. That left one deploy-gated acceptance
scenario keeping prototype condition 2 red until a cluster release existed.

The prototype is not a production deployment. The first cluster release
(condition 9) provides a real deployed release and GitOps chain to drill
against, but there may be several iterations and releases between that first
release and the point the system is considered production ready. The backup
restore drill and the GitOps rollback drill are the gates for that
production-readiness milestone, not prototype acceptance criteria.

Rollback safety also depends on migrations. SPEC.md section 10 requires database
migrations to be backward compatible with the old running image, and the
committed migrations already define `downgrade()` bodies. Nothing enforces that
every migration has a working downgrade, and the migration runner only ever
upgrades, so reversibility is currently convention rather than a checked
property.

## Decision

1. **Every migration is written for both directions.** A migration defines a
   working `downgrade()` that removes exactly what its `upgrade()` created. A
   per-cycle gate fails `make check` when a committed migration lacks a
   non-trivial downgrade, and the production-readiness rollback drill exercises
   the full `upgrade -> downgrade -> upgrade` round trip against a deployed
   database.

2. **The backup restore drill and the GitOps rollback drill are
   production-readiness gates.** They move out of the prototype definition of
   done into a production-readiness phase that begins once the first cluster
   release exists, may span several further iterations and releases, and must
   complete before any production client data is onboarded. The phase owns:
   choosing a database backup target and passing a witnessed restore drill; and
   passing the rollback drill (revert the GitOps image digest, prove the
   previous compatible version serves, and prove migrations are backward
   compatible and reversible).

The `gitops-revert-restores` acceptance scenario is removed from the section 11
minimum acceptance scenarios (eight remain). This supersedes the part of ADR
0009 that kept it in the prototype suite; ADR 0009's deferral of backup and
restore stands.

## Consequences

- Condition 2 now requires eight section 11 scenarios, all currently covered, so
  the acceptance-coverage gate passes without a deployment.
- `make done` is no longer blocked by condition 2. Its remaining prototype
  blockers are condition 1 (stage 0-10 e2e, gated on Q3/ADR 0006), condition 5's
  live provider half (an OpenRouter key) and condition 9 (the Atlas deployment).
- The deploy slice Q47-Q50 stays required: condition 9 is the first cluster
  release and the prerequisite for the production-readiness drills.
- Migration authoring is stricter: a new migration without a working downgrade
  fails `make check`.
- The production-readiness phase is recorded as open work owned by the RED
  principal and is not part of the prototype stop condition.

## Alternatives considered

- Keep the rollback scenario in the prototype: rejected - it is a live
  operations drill that needs a deployed release, and the prototype's acceptance
  suite should stay offline-verifiable.
- Tie the drills to the first cluster release as the immediate next step:
  rejected - the first release only makes the drills possible; production
  readiness may be several releases later.
- Enforce reversibility by convention only: rejected - an unenforced rule
  regresses silently, and every committed migration already satisfies it, so the
  gate is cheap.
- Require only backward compatibility, not a downgrade: rejected - SPEC.md
  section 10's rollback needs the schema to move back with the image; a working
  downgrade is the evidence.

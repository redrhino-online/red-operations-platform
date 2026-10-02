# RED Operations Platform: Implementation Plan

Version: 0.2, September 27, 2026. Planning basis: the accompanying SPEC.md. This is a fork implementation plan, not a claim that the OpenExecutive repository or home cluster has been inspected.

## Current cycle status

- Cycle timestamp: 2026-10-02T13:05:10Z (Ralph cycle 20).
- Selected item: pin the canonical checkpoint rubric onto the gate record so
  `StageGate.from_template` derives it from `StageDefinition.checkpoint`,
  `GateDecision` persists it, and a passing gate or decision whose checkpoint
  does not match the template's rubric is rejected (SPEC.md section 4, "Gate
  record and production manager view": persist the checkpoint rubric for every
  stage). This was the prior cycle's explicit next item. It was selected over
  starting the stage 4 Signature Solution aggregate because it was the last
  unaddressed field of the SPEC.md section 4 gate record, it is pure domain, and
  it extends the existing template-version/asset-package pinning rather than
  adding a new data path.
- Outcome: completed and verified.
- Evidence: new `tests/unit/governance/test_gate_checkpoint.py` (9 tests) first
  failed for the right reason (`ImportError: cannot import name
  'CheckpointMismatchError'`). `StageGate` (mutable) gained a `checkpoint` field
  populated by `from_template` from the stage definition; immutable
  `GateDecision` gained a required `checkpoint` field populated by `from_gate`
  from the gate and rejects a missing rubric; `GateLedger.record` and
  `GateIntegrityPolicy` reject a passing gate/decision whose checkpoint differs
  from the template, via named `CheckpointMismatchError`. Command:
  `PYTHONPATH=backend python3 -m unittest discover -s tests -p 'test_*.py'`
  (184 passed, up from 175, 9 new); `python3 -m pyflakes` on the three touched
  governance domain modules and the five touched test modules clean. `ruff` and
  `mypy` remain uninstalled.
- New findings: the SPEC.md section 4 gate record fields (template version,
  required assets with exact versions, checkpoint rubric, test evidence, gate
  state, owner, approver, due date, dependencies, rationale, next action) are now
  represented in the governance domain. The next backbone gap is cross-context:
  the stage 2 `PrimaryCurrency` and stage 3 `DiagnosticModel` domain values are
  not yet referenced by a `MethodVersion`, so an approved Signature Solution does
  not pin the exact, tenant-checked upstream stage 2/3 assets, and there is still
  no stage 4 Signature Solution aggregate. No repository defect was found that
  should outrank closing that dependency.
- Blockers: unchanged named-owner decisions — where RED code lives (already de
  facto `backend/redops`), storage strategy given the SQLite reality, tenant
  model given slot-based single-active-client isolation, scheduler/worker
  topology, and the client-designated approver identities. No fork or cluster
  facts invented; no `docs/`, fork checkout, `kubectl`, `helm`, or `argocd`
  present.
- Highest priority ready next item: wire the stage 2 `PrimaryCurrency` and stage
  3 `DiagnosticModel` into `MethodVersion` so an approved Signature Solution pins
  the exact upstream currency and diagnostic model, rejects mixing another
  tenant's assets, and drops them from any revised version (SPEC.md section 3
  aggregate table for MethodVersion; section 4 stages 2-4 gate dependency).
  Prerequisites: none; pure domain, extending the existing `MethodVersion`
  fields and `revised`. Pipeline mapping: stages 2 "Currency Locked" and 3
  "Diagnostic Model Approved" feed stage 4 "IP Architecture Locked"; required
  assets = `primary-currency`, `profit-pyramid-levels`; checkpoint = each stage's
  canonical rubric; approver = each stage's designated approver role (client
  identity still an open decision); blocked downstream dependency = the stage 4
  Signature Solution cannot pin its approved stage 2/3 assets until this is
  wired. Persistence of `MethodVersion`, `DiagnosticModel`, `SourceRecord`/
  `Claim`, `OfferVersion`, `PrimaryCurrency` and the gate ledger, and
  cross-tenant retrieval isolation, remain blocked on the storage ADR.

## Product priority: the gated production engagement

Implement a versioned stage 0 to 10 template from intake through campaign launch. Each stage is a collection of required asset versions, a checkpoint rubric, dependencies, owner, approver, milestone, and gate decision. A task being marked done does not pass its stage. An approved gate pins the exact versions authorized for downstream use. Preserve the distinction between these production stages and the three phase, nine step client Signature Solution.

The first usable vertical slice is stages 0 and 1: establish scope, access and baseline, then produce an approved avatar and diagnosis. Subsequent slices implement currency and Profit Pyramid, method and offer, campaign message and Authority Amplifier, funnel integration and launch QA, then performance baseline and optimization. An existing asset can satisfy a stage only through an evidence and approval review. A waived requirement has a named human risk owner and does not become a fabricated asset.

## Engineering method and delivery gates

Every post fork behavior change uses TDD: write a failing test that expresses a domain or user observable rule, implement the smallest passing behavior, refactor, then run impacted contract and integration suites. Characterize reused upstream behavior before changing it. Each pull request states the bounded context, aggregate invariants, ports, migration effect, security boundary, test evidence, and rollback. Code review rejects domain logic in routes, direct ORM access across contexts, untyped agent outputs, unversioned prompts, and mutations without an authority check.

Test layers: domain unit tests for transitions and policy; application tests with fake ports for commands; adapter contract tests against PostgreSQL, object storage, queue, and model gateway; integration tests with real services; workflow tests for retries, approval waits and resume; browser tests for critical approval and launch paths; security tests for cross client isolation and authority bypass; Helm template validation and deployment smoke tests. Prefer meaningful behavioral tests over implementation mirroring. Keep a small end to end suite and avoid a fragile screenshot gate.

Domain driven design: publish a ubiquitous language glossary, event catalog, context map, aggregate invariants, and ADRs before building new data paths. SOLID and onion enforcement: import rules prevent `domain` from importing `infrastructure`, `api`, framework or model SDK packages; ports are defined by application needs; policy objects remain composable; adapters satisfy contract tests. CI checks formatting, type checking, import boundaries, tests, migration consistency, dependency vulnerabilities, and container/chart validity.

## Phase 0: inspect and establish the fork

Inputs: OpenExecutive repository URL and permissible fork terms, access credentials where required, cluster inventory. Actions: pin upstream commit, inspect code and license, run existing tests, map candidate features to actual modules, document data model and behavior, review secrets, security posture, background execution and existing deployment. Capture baseline test and build results. Create `docs/fork_inventory.md`, context map, ADRs for modular monolith and tenant model, dependency manifest, and a fork diff register. Do not merge domain replacement until the baseline builds locally.

Exit: reproducible local setup, known upstream commit and license, verified reuse matrix, passing baseline or documented existing failures, named owner for each architectural decision. If fork rights or availability fail, pause implementation and choose a clean implementation path through an explicit decision.

## Phase 1: delivery skeleton and authority core

Build: context package boundaries, typed IDs, migrations, tenant scoped repositories, identity and permissions, source record storage, immutable audit trail, outbox, versioned approvals, BuildObject and StageRun state machines, GateDecision, and a seeded versioned 0 to 10 template. Replace generic labels in the UI only after domain semantics exist. Start local containers for dependencies. Add a GitOps staging environment and chart skeleton, without live client data.

TDD examples: approving version A cannot approve version B; writer cannot approve own proposal under a separation policy; tenant A cannot read tenant B's BuildObject; missing asset prevents gate completion; activity without approval leaves stage Working; a scoped waiver records risk owner without creating an asset; illegal state transition returns a named error; audit entry remains after approval is superseded. Implement unit then database integration tests, with security regression tests at HTTP boundary.

Exit: reviewer can create a client workspace, register a traced build, see stage 0 requirements and missing items, request and record an exact version approval, and see an audit trail in staging. Cross client isolation tests pass.

## Phase 2: knowledge and discovery vertical slice

Build: stage 0 intake and baseline capture, stage 1 business and avatar diagnosis, upload and parse supported source formats, checksum and location based citations, claim provenance classes, extraction review, unknowns register, discovery workflow and enterprise brief. Use a client scoped retrieval adapter with measurable recall checks. Preserve original bytes. A RED operator corrects extraction before a client approved diagnosis.

TDD examples: an unsupported fact remains Proposed or Unknown; a claim citation opens the exact source location; conflicting statements are both retained; retrieval cannot cross tenants; parser failure leaves a retryable record without a false success.

Exit: a real pilot source set yields a reviewed, traceable enterprise brief; stage 0 Production Ready and stage 1 Avatar Locked decisions cite exact asset versions. Track extraction correction rate and missing source rate.

## Phase 3: method, offers, and dependency graph

Build: stage 2 primary currency and Million Dollar Message, stage 3 observable Profit Pyramid, stage 4 three phase and nine step Signature Solution, stage 5 Perfect Product; method and offer versioning, transformation milestones, currency and audience fields, approval diff, dependency links, downstream impact analysis. Encode the RED methodology as versioned templates and examples, not as hard coded universal truth. The 3F pilot needs an explicit distinction between existing technical support work and a completed RED method engagement.

TDD examples: currency gate rejects an unspecified audience or unmeasured outcome; pyramid levels require observable differences; offer cannot become production ready without approved method; changing one approved milestone identifies dependent offers and assets; a rejected method proposal does not alter approved version; workflow resumes at the client gate after restart.

Exit: stage 2 Currency Locked, stage 3 Diagnostic Model Approved, stage 4 IP Architecture Locked, and stage 5 Offer Locked have human decisions with the exact approved versions. An upstream change creates a complete review queue.

## Phase 4: asset production and customer journey

Build: stage 6 congruent campaign message, stage 7 Authority Amplifier with script approval before visual production and final creative approval, stage 8 funnel integration, stage 9 three part launch QA; production briefs, template registry, claim check, asset review, release package, customer journey configuration, staging connectors, dry run and launch checklist, incident and rollback records. Implement first the smallest complete pilot journey. Keep external sending or publishing behind a human authorized release action.

TDD examples: campaign message conflicting with the offer blocks approval; visual Authority Amplifier production cannot be authorized by an unapproved script; unsupported proof is flagged; duplicate event does not send duplicate message; failed prospect routing prevents Funnel Complete; failed message, technical or commercial QA prevents Launch Approved; connector timeout creates a visible retry or incident rather than a success state.

Exit: stages 6 through 9 have exact version approvals; one complete 3F journey passes staged customer path tests including opt in, tagging, Authority Amplifier, follow up, qualification, booking, reminders, incomplete assessment, missed appointment and sales handoff. The release has a named human owner, rollback plan, budget decision and acceptance record. Stage 9 shows Ready for Traffic, not live or completed.

## Phase 5: measurement, operations, and portfolio

Build: stage 10 live traffic milestones and baseline, metric registry, event instrumentation, observations and experiment records, command center intervention queries, notification deduplication, health signals, portfolio opportunity register. Track spend, leads, lead cost, page conversion, Authority Amplifier engagement, applications, bookings, shows, closes, acquisition cost, revenue attribution and issues where instrumentation and consent permit. Rank interventions by blocked gate and downstream effects, actual commitments and dependencies, and show evidence behind each recommendation. Use a first improvement cycle to validate whether these views change operator decisions.

TDD examples: launch alone cannot complete the engagement; traffic, lead, qualified appointment and sale are distinct observed milestones; missing baseline blocks a before and after claim; low sample size keeps causal claim as interpretation; stale gate approval produces one owned intervention; dismissal records reason; opportunity remains proposed until investment authority acts.

Exit: stage 10 establishes an evidence backed performance baseline after qualified traffic, with later milestones pending until observed; a performance review records baseline and observed result, one improvement is approved and measured, and operators can resolve a blocked gate from the command center without searching multiple systems. Engagement remains in Optimization until explicit completion criteria are met.

## Phase 6: hardening and production cutover

Perform threat modeling, tenant penetration tests, data export and deletion drill, load tests for expected concurrent workflows, backup and restore exercise, disconnected home network exercise, node restart and worker resume exercise, alert routing and runbook review. Promote images by digest through reviewed GitOps changes. Keep staging and production namespaces, secrets, backups, and database credentials separate. Roll out one RED internal engagement before onboarding additional clients.

Exit: complete security and recovery evidence, production SLO dashboard, named incident owner, signed pilot acceptance, rehearsed rollback, no unresolved high severity access issues. Archive the exact release manifest and prompt versions.

## Sequencing and deliverable ownership

| Sequence | Increment | Depends on | Demonstrable artifact |
| --- | --- | --- | --- |
| 0 | Fork inventory | Upstream access | Reuse matrix and baseline |
| 1 | Authority core | 0 | Approved version with audit |
| 2 | Intake and diagnosis, stages 0 and 1 | 1 | Production Ready and Avatar Locked |
| 3 | Position, model, package, productize, stages 2 through 5 | 2 | Approved currency, diagnostic, method and offer |
| 4 | Message, produce, integrate, QA, stages 6 through 9 | 3 | Approved campaign, creative, funnel and launch readiness |
| 5 | Launch and optimize, stage 10 onward | 4 | Qualified traffic, baseline and improvement cycle |
| 6 | Production cutover | 1 through 5 | Restorable GitOps release |

Do not promise calendar duration before fork and cluster discovery. Estimate each phase after Phase 0 using story slices and staffing, then publish a forecast with confidence ranges. Each increment is usable in isolation and has an explicit acceptance review.

## GitOps and release implementation checklist

Repositories: fork source and separate GitOps environment repository. Branch protection requires code review and CI; images are built once and promoted by immutable digest. Helm values describe staging and production, with no plain secret values in Git. Argo CD owns synchronization. Migration job runs with a scoped account; use expand, migrate, contract changes across releases. Configure health probes, resource limits, network policies, certificate renewal, logs and metrics. Test chart rendering for each environment, policy validation, admission, deployment smoke, rollback and data restore. Document DNS, VPN, registry reachability and the consequences of home power or internet loss.

CI gate order: format and types, domain and application tests, adapter contracts, migration check, API and security tests, frontend checks, image scan and build, Helm lint and render, ephemeral integration test, staged Argo CD reconciliation, smoke test. Production promotion records human approval and produces a Git commit in the GitOps repository. Never treat a green AI response as authorization to deploy.

## Initial backlog by vertical slice

1. Pin upstream commit and record license, environment and component inventory.
2. Write domain glossary, context map, permission matrix and ten ADRs only as decisions arise, with no arbitrary ADR quota.
3. Add tenant boundary and authority tests around forked storage and retrieval.
4. Implement SourceRecord, Claim, approval, decision, BuildObject, StageRun and GateDecision aggregates. [DONE 2026-10-02: Governance `StageGate` + `GateIntegrityPolicy` — missing exact asset version, unapproved dependency, self-approval, and waiver-without-asset all block gate approval; verified by `tests/unit/governance/test_gate_integrity.py`. DONE 2026-10-02 (Ralph cycle 2): version-specific `ApprovalRequest` (exact version + scope, designated approver, expiry) and append-only `Decision` / `DecisionLog`; verified by `tests/unit/governance/test_approval_record.py`. DONE 2026-10-02 (Ralph cycle 3): `StageRun` completes only via an accepted gate for the same stage, never via activity, with `StageStatus` / `StageTransition` and a `StageTransitionPolicy` that rejects illegal transitions; verified by `tests/unit/governance/test_stage_run.py`. DONE 2026-10-02 (Ralph cycle 4): `BuildObject` in the Production context requires an owner and next action while active and rejects illegal lifecycle transitions; verified by `tests/unit/production/test_build_object.py`. DONE 2026-10-02 (Ralph cycle 5): versioned stage 0–10 `StageTemplate` seeded in Governance and `GateIntegrityPolicy` rejects gates that omit a canonical prerequisite, under-declare required asset kinds, or pin a different template version; verified by `tests/unit/governance/test_stage_template.py`. DONE 2026-10-02 (Ralph cycle 6): `StageGate.from_template` derives dependencies, template version and required asset kinds from the canonical template so gate evidence is not self-declared; verified by `tests/unit/governance/test_gate_factory.py`. DONE 2026-10-02 (Ralph cycle 7): immutable `GateDecision` / `GateDisposition` records the stage, pinned required asset versions, checkpoint evidence, reviewer, scope, disposition, rationale and next action, and `GateDecision.from_gate` refuses an approval for a non-approvable gate; verified by `tests/unit/governance/test_gate_decision.py`. DONE 2026-10-02 (Ralph cycle 8): `StageRun.complete` now requires a passing, same-stage, same-template-version `GateDecision` and pins it as immutable `accepted_decision`, replacing the transient `StageGate`; verified by `tests/unit/governance/test_stage_run.py`. DONE 2026-10-02 (Ralph cycle 9): `GateLedger` derives prerequisite state from durable `GateDecision`s and refuses a passing decision while a prerequisite stage lacks a passing decision, so the dependency map is no longer caller-supplied; verified by `tests/unit/governance/test_gate_ledger.py`. DONE 2026-10-02 (Ralph cycle 10): `GateDecision.from_gate` now requires a `GateLedger` and reads prerequisite state and the canonical template only from the ledger, removing the caller-supplied `dependency_states` map from the decision boundary; verified by `tests/unit/governance/test_gate_decision.py` and `test_gate_ledger.py`. DONE 2026-10-02 (Ralph cycle 11): Knowledge `SourceRecord` (frozen original: locator, checksum, capture time, access rule; `cite` returns a checksum-pinned citation) and `Claim` (statement, `Known`/`Derived`/`Proposed`/`Unknown`, citations, confidence note) with `reclassify` records an audited `ClaimRevision`, refuses `Known` without a direct citation, and preserves the original so Derived/Proposed never silently become Known; verified by `tests/unit/knowledge/test_source_record.py` and `test_claim.py`. DONE 2026-10-02 (Ralph cycle 12): Method `SemanticVersion` / `MethodVersion` / `MethodApproval` pin an exact semantic version and intended use, revisions must advance the version and drop the old approval, and `MethodChangeImpactPolicy` emits an owned review queue (offer, brief, asset, journey, claim with human owner and due date) for a change to an approved method, rejecting unapproved or non-advancing or cross-tenant changes; verified by `tests/unit/method/test_method_version.py` and `test_method_impact.py`. DONE 2026-10-02 (Ralph cycle 13): Commercial Design `MethodReference` / `OfferVersion` records audience, promise, eligibility, price hypothesis and at least one exact method reference, and `OfferReadinessPolicy` refuses production readiness unless every reference is an approved `MethodVersion` of the same tenant at the exact version and intended use; `mark_review_required` drops readiness after an upstream change and a terminal offer cannot be revived; verified by `tests/unit/commercial/test_offer_version.py`. DONE 2026-10-02 (Ralph cycle 15): `GateLedger.record` refuses a passing `GateDecision` whose pinned asset kinds do not exactly match the canonical `StageTemplate` required package for the stage (under-declared or substituted), closing the durable boundary previously checked only at the `from_gate` factory; ledger fixtures now use canonical kinds; verified by `tests/unit/governance/test_gate_ledger.py`. DONE 2026-10-02 (Ralph cycle 16): `GateIntegrityPolicy._template_reasons` now applies the same exact asset-package rule as the durable ledger, rejecting a gate that declares a non-canonical extra asset kind as well as one that omits a canonical kind, so `GateDecision.from_gate` can no longer produce a passing decision the `GateLedger` must refuse and gate evaluation and durable recording are consistent; verified by `tests/unit/governance/test_stage_template.py`. DONE 2026-10-02 (Ralph cycle 18): `GateDecision` now persists the assigned work owner and due date for every stage and rejects a decision that omits either, closing the SPEC.md section 4 gate-record gap where the production view must answer who is accountable and when the next approval is due; verified by `tests/unit/governance/test_gate_decision.py` (with `from_gate` factory passthrough). DONE 2026-10-02 (Ralph cycle 20): `StageGate` and `GateDecision` now pin the canonical checkpoint rubric derived from `StageDefinition.checkpoint`, and `GateLedger` and `GateIntegrityPolicy` reject a passing gate or decision whose checkpoint differs from the template, closing the last SPEC.md section 4 gate-record field; verified by `tests/unit/governance/test_gate_checkpoint.py`. Remaining: SourceRecord, Claim, MethodVersion and OfferVersion repository adapters blocked on the storage ADR.]
5. Implement stages 0 and 1 from intake to approved avatar and diagnosis.
6. Implement stages 2 and 3 from primary currency to observable Profit Pyramid. [DONE 2026-10-02 (Ralph cycle 17): Method `PrimaryCurrency` value object requires a specific audience, distinct current/desired measures, and a distinct mechanism, rejecting an unspecified person or unmeasured outcome, so the stage 2 "Currency Locked" checkpoint rule is met by a real domain value; verified by `tests/unit/method/test_primary_currency.py`. DONE 2026-10-02 (Ralph cycle 19): Method `ProfitPyramidLevel` and `DiagnosticModel` require each level's observable measures, symptoms, behaviors and problems and reject adjacent levels that cannot be told apart by an observable difference, so the stage 3 "Diagnostic Model Approved" checkpoint rule is met by a real domain value; verified by `tests/unit/method/test_diagnostic_model.py`. Stage 3 wiring into the stage 3 `GateDecision` remains.]
7. Implement stages 4 and 5 from grounded Signature Solution to offer approval. [DONE 2026-10-02 (Ralph cycle 14): commercial `OfferVersion` requires an accountable owner and `OfferChangeImpactPolicy` discovers dependent offers from an approved method change and marks them review required, so the SPEC.md section 11 "changing a method version identifies dependents" acceptance test is met by a real aggregate; verified by `tests/unit/commercial/test_offer_change_impact.py`. Stage 2/3 currency and Profit Pyramid, and the stage 4/5 gate wiring, remain.]
8. Implement stages 6 and 7 with message congruence and script approval before creative production.
9. Implement stages 8 and 9 with complete prospect path and three part QA.
10. Implement stage 10 baseline, command center and improvement loop.
11. Complete operational security, backup, GitOps and acceptance drills.

## Risks and decisions

Major risks: fork internals may differ from the prior description; upstream license may limit use; latent cross tenant leakage; AI output may be mistaken for approval; home cluster may lack durable storage or reliable ingress; connector side effects may duplicate on retries; migrating live workflows may strand approval gates. Mitigations are respectively inventory, license review, isolation tests, explicit human authority, restore drills, idempotency keys, and version pinned workflow definitions.

Decisions requiring a named owner: fork URL and license, Kubernetes distribution and capacity, identity provider, database and storage operator, backup target, external access path, model provider data handling, client approval roles, pilot acceptance metrics, 3F launch scope, and the remaining two agent charters. Record these as unresolved until verified. Any work requiring these decisions may proceed to a reviewable proposal and tests, but may not assume authorization from missing information.

# RED Operations Platform: Implementation Plan

Version: 0.2, September 27, 2026. Planning basis: the accompanying SPEC.md. This is a fork implementation plan, not a claim that the OpenExecutive repository or home cluster has been inspected.

## Current cycle status

- Cycle 2026-10-03T173254Z (Ralph cycle, this run): selected item was the HTTP
  route that exposes the stage 10 "Performance Baseline Established" gate. The
  prior cycle named it the highest priority ready next item: the
  `StageTenGateAssembler` / `StageTenGateRecorder`, the
  `RecordStageTenGateCommand` / `RecordStageTenGateHandler` and the Execution
  `PerformanceBaselinePackage` all exist, but only stages 0 through 9 had write
  routes, so the canonical 0-10 API surface stopped at stage 9 and DoD condition 1
  stayed unreachable. It outranked the `ClientProcess` canon gap (a
  methodology-owner decision) and the durable `MethodVersion`/offer store (a
  larger integrity item), because completing the canonical gate surface through
  the real use cases is the pipeline backbone.
- Outcome: new `POST /red/clients/{tenant_id}/stages/10/gate` in
  `backend/redops/api/routes.py`, mapping the typed request to the Execution
  `PerformanceBaselinePackage` and running `RecordStageTenGateHandler` through
  `get_gate_ledger_repository` and `get_stage_run_repository`, mirroring the stage
  9 route. The stage 9 compliance/QA construction was extracted into a shared
  module-level `_authorize_launch_qa`, now used by the stage 9 and stage 10 routes
  (the stage 10 baseline grounds on the ready-for-traffic stage 9 launch QA), so
  the two cannot drift. New request schemas in `backend/redops/api/schemas.py`:
  `MilestoneObservationInput`, `LaunchAssetPackageInput`,
  `PerformanceBaselineInput`, `RecordStageTenGateRequest`. The route rebuilds the
  reviewed baseline on the rebuilt authorized stage 9 QA and drives `establish`,
  so the domain's `PerformanceBaselinePolicy` -- not the transport layer -- decides
  whether the twelve canonical kinds may be pinned as passing evidence. The route
  computes no rule: the grounded stage 9 dependency, the distinct
  observed-or-pending milestones, the observed-first-qualified-traffic rule, the
  milestone ordering, the canonical kinds, exact versions, owner/approver
  authority, the stage 9 prerequisite and the tenant boundary stay enforced by the
  domain, and errors map to a named 422 (SPEC.md section 4, stage 10; canon files
  22, 23, 29-31, 33 and 34 per section 12.3).
- Evidence: `tests/unit/test_stage_ten_gate_route.py` (7) pass: stages 0 through 9
  are seeded through their own routes (reusing the stage 9 test's payload builders
  so the suites cannot drift), then a passing stage 10 decision pins the twelve
  canonical baseline kinds at version 1, the stage 10 run persists COMPLETE with
  its owner, a stage 10 gate with no passing stage 9 is refused, a pending first
  qualified traffic milestone prevents establishment with
  `PerformanceBaselineIncompleteError` and no write, an omitted milestone is
  refused the same way, an unauthorized approver is refused with no write, and the
  decision is invisible to another tenant. The reworked stage 9 route still passes
  its own 7 tests. `uv run pytest -q` green via `make check`/`make done`: 1723
  passed, 1 skipped, 632 subtests; `python3 -m pyflakes backend tests` clean. The
  canonical 0-10 gate write surface is now complete.
- New findings: extracting `_authorize_launch_qa` proved the stage 9 QA
  construction is reusable without behaviour change. The API-boundary integrity
  limitation is unchanged: the caller supplies the approved
  method/offer/message/amplifier/funnel/QA and their approval metadata because no
  read model or store is exposed, so the "approved dependency" is data, not a
  durable governance record. `make done` still fails at step 2 (`tests/e2e`
  absent), so DoD 1 is not met.
- Blockers: Tier 2 facts unchanged; no request idempotency key on the gate routes
  and a repeated gate POST after COMPLETE returns 422; RLS remains WHERE-clause
  only (ADR 0004); no `MethodVersion`/offer/funnel/QA store behind the API; the
  stage 0-10 e2e suite (DoD 1, Q30) and the migration deployment step (separate
  GitOps chart) are absent from this repo.
- Highest priority ready next item: the `tests/e2e` stage 0-10 suite that drives
  one client from intake to "Performance Baseline Established" through the REST
  API, which is DoD condition 1 (SPEC.md section 13) and the only reason `make
  done` still fails. Prerequisites: the full 0-10 gate write surface (now done) and
  the production-view read route. Alternative: the `ClientProcess` design artifact
  from the canon gap register, if a methodology-owner decision is preferred; or a
  durable `MethodVersion`/offer store so the gates stop re-stating upstream
  approvals.

### Prior cycle (2026-10-03T173026Z)

- Cycle 2026-10-03T173026Z: selected item was the HTTP
  route that exposes the stage 9 "Launch Approved" gate. The prior cycle named it
  the highest priority ready next item: the `StageNineGateAssembler` /
  `StageNineGateRecorder`, the `RecordStageNineGateCommand` /
  `RecordStageNineGateHandler` and the Execution `LaunchQAPackage` all exist, but
  only stages 0 through 8 had write routes, so the canonical 0-10 API surface
  stopped at stage 8 and DoD condition 1 stayed unreachable. It outranked the
  stage 10 route (which depends on it) and the `ClientProcess` canon gap (a
  methodology-owner decision), because gate visibility through the real use case
  is the pipeline backbone.
- Outcome: new `POST /red/clients/{tenant_id}/stages/9/gate` in
  `backend/redops/api/routes.py`, mapping the typed request to the Execution
  `LaunchQAPackage` and running `RecordStageNineGateHandler` through
  `get_gate_ledger_repository` and `get_stage_run_repository`, mirroring the stage
  8 route. New request schemas in `backend/redops/api/schemas.py`:
  `QACheckInput`, `ComplianceAssetInput`, `ComplianceWaiverInput`,
  `CompliancePackageInput`, `TrafficAuthorizationInput`, `LaunchQAInput`,
  `RecordStageNineGateRequest`. The stage 8 funnel construction was extracted
  into a shared module-level `_complete_stage_eight_funnel`, now used by the
  stage 8 and stage 9 routes, so the two cannot drift. The route rebuilds the
  reviewed launch QA on the rebuilt complete stage 8 funnel and drives
  `authorize_traffic`, so the domain's `LaunchApprovedPolicy` and
  `ComplianceRequiredPolicy` -- not the transport layer -- decide whether the
  sixteen canonical kinds may be pinned as passing evidence. The route computes
  no rule: the complete same-tenant check set, the critical path outcomes, the
  compliance package, the grounded stage 8 dependency, the canonical kinds, exact
  versions, owner/approver authority, the stage 8 prerequisite and the tenant
  boundary stay enforced by the domain, and errors map to a named 422. Stage 9
  carries claims only because the amplified stage 8 dependency must still be
  rebuilt (SPEC.md section 4, stage 9; canon files 01, 08, 21, 22 and 24 per
  section 12.3).
- Evidence: `tests/unit/test_stage_nine_gate_route.py` (7) pass: stages 0 through
  8 are seeded through their own routes (reusing the stage 8 test's payload
  builders so the suites cannot drift), then a passing stage 9 decision pins the
  sixteen canonical launch kinds at version 1, the stage 9 run persists COMPLETE
  with its owner, a stage 9 gate with no passing stage 8 is refused, a failed
  critical path QA check prevents approval with `LaunchQAIncompleteError` and no
  write, a missing launch-blocking compliance asset prevents approval with
  `MissingComplianceAssetError` and no write, an unauthorized approver is refused
  with no write, and the decision is invisible to another tenant. The reworked
  stage 8 route still passes its own 6 tests. `uv run pytest -q` green: 1716
  passed, 1 skipped, 632 subtests; `uv run pyflakes backend tests` clean.
- New findings: extracting `_complete_stage_eight_funnel` proved the stage 8
  funnel construction is reusable without behaviour change, so the stage 10 route
  can reuse it the same way. The API-boundary integrity limitation is unchanged:
  the caller supplies the approved method/offer/message/amplifier/funnel and their
  approval metadata because no read model or store is exposed, so the "approved
  dependency" is data, not a durable governance record. `make done` still fails at
  step 2 (`tests/e2e` absent), so DoD 1 is not met.
- Blockers: Tier 2 facts unchanged; no request idempotency key on the gate routes
  and a repeated gate POST after COMPLETE returns 422; RLS remains WHERE-clause
  only (ADR 0004); no `MethodVersion`/offer/funnel store behind the API; the stage
  0-10 e2e suite (DoD 1, Q30) and the migration deployment step (separate GitOps
  chart) are absent from this repo.

### Prior cycle (2026-10-03T172823Z)

- Cycle 2026-10-03T172823Z: selected item was the HTTP
  route that exposes the stage 8 "Funnel Complete" gate. The prior cycle named it
  the highest priority ready next item: the `StageEightGateAssembler` /
  `StageEightGateRecorder`, the `RecordStageEightGateCommand` /
  `RecordStageEightGateHandler` and the Execution `FunnelIntegrationPackage` all
  exist, but only stages 0 through 7 had write routes, so the canonical 0-10 API
  surface stopped at stage 7 and DoD condition 1 stayed unreachable. It outranked
  the stage 9 route (which depends on it) and the `ClientProcess` canon gap (a
  methodology-owner decision), because gate visibility through the real use case
  is the pipeline backbone.
- Outcome: new `POST /red/clients/{tenant_id}/stages/8/gate` in
  `backend/redops/api/routes.py`, mapping the typed request to the Execution
  `FunnelIntegrationPackage` and running `RecordStageEightGateHandler` through
  `get_gate_ledger_repository` and `get_stage_run_repository`, mirroring the stage
  7 route. New request schemas in `backend/redops/api/schemas.py`:
  `FunnelAssetPackageInput`, `HandoffRecordInput`, `ProspectPathDryRunInput`,
  `FunnelIntegrationInput`, `RecordStageEightGateRequest`. The route grounds the
  reviewed `FunnelIntegration` on the approved stage 7 amplifier and drives
  `mark_funnel_complete` with the prospect path dry run, so the domain's
  `FunnelCompletionPolicy` -- not the transport layer -- decides whether the
  thirteen canonical kinds may be pinned as passing evidence. The route computes
  no rule: the funnel's own completion, the grounded stage 7 dependency, the
  canonical kinds, exact versions, owner/approver authority, the stage 7
  prerequisite and the tenant boundary stay enforced by the domain, and errors map
  to a named 422. Stage 8 carries claims only because the amplified stage 7
  dependency must still be rebuilt and re-proved (SPEC.md section 4, stage 8;
  canon files 13, 14, 21 and 22 per section 12.3).
- Evidence: `tests/unit/test_stage_eight_gate_route.py` (6) pass: stages 0
  through 7 are seeded through their own routes (reusing the stage 7 test's
  payload builders so the suites cannot drift), then a passing stage 8 decision
  pins the thirteen canonical funnel kinds at version 1, the stage 8 run persists
  COMPLETE with its owner, a stage 8 gate with no passing stage 7 is refused, a
  failed conversion handoff prevents completion with `FunnelIncompleteError` and
  no write, an unauthorized approver is refused with no write, and the decision is
  invisible to another tenant. `uv run pytest -q` green: 1709 passed, 1 skipped,
  632 subtests; `uv run pyflakes backend tests` clean.
- New findings: the stage 7 amplifier construction was extracted into a shared
  module-level `_approve_authority_amplifier`, now used by the stage 7 and stage 8
  routes, proving it reusable without behaviour change so stages 9 and 10 can
  reuse it the same way. The API-boundary integrity limitation is unchanged: the
  caller supplies the approved method/offer/message/amplifier and their approval
  metadata because no read model or store is exposed, so the "approved dependency"
  is data, not a durable governance record. `make done` still fails at step 2
  (`tests/e2e` absent), so DoD 1 is not met.
- Blockers: Tier 2 facts unchanged; no request idempotency key on the gate routes
  and a repeated gate POST after COMPLETE returns 422; RLS remains WHERE-clause
  only (ADR 0004); no `MethodVersion`/offer store behind the API; the stage 0-10
  e2e suite (DoD 1, Q30) and the migration deployment step (separate GitOps chart)
  are absent from this repo.
- Highest priority ready next item: expose the stage 9 "Launch Approved" gate by
  `POST /red/clients/{tenant_id}/stages/9/gate`, mapping a typed request to the
  Execution `LaunchQAPackage` and running `RecordStageNineGateHandler` through the
  ledger and stage run ports, reusing `_approve_method_offer_message` and
  `_approve_authority_amplifier` and mirroring the stage 8 route (stage 9's
  prerequisite is a passing stage 8 decision; the checkpoint requires every
  critical path QA check to pass, exceptions to have owners, a reviewed compliance
  package and the designated human authority to authorize traffic).
  Prerequisites: the `StageNineGateAssembler`/`StageNineGateRecorder`,
  `RecordStageNineGateCommand`/`RecordStageNineGateHandler` and `LaunchQAPackage`
  (all present), the stage 8 route (done), and a passing stage 8 decision in the
  ledger (enforced by governance). This advances the stage 0-10 API surface toward
  DoD 1. Alternative: the `ClientProcess` design artifact from the canon gap
  register, if a methodology-owner decision is preferred; or a durable
  `MethodVersion`/offer store so the gates stop re-stating upstream approvals.

### Prior cycle (2026-10-03T172603Z)

- Cycle 2026-10-03T172603Z: selected item was the HTTP
  route that exposes the stage 7 "Authority Amplifier Approved" gate. The prior
  cycle named it the highest priority ready next item: the
  `StageSevenGateAssembler` / `StageSevenGateRecorder`, the
  `RecordStageSevenGateCommand` / `RecordStageSevenGateHandler` and the Production
  `AuthorityAmplifierPackage` all exist, but only stages 0 through 6 had write
  routes, so the canonical 0-10 API surface stopped at stage 6 and DoD condition 1
  stayed unreachable. It outranked the stage 8 route (which depends on it) and the
  `ClientProcess` canon gap (a methodology-owner decision), because gate
  visibility through the real use case is the pipeline backbone.
- Outcome: new `POST /red/clients/{tenant_id}/stages/7/gate` in
  `backend/redops/api/routes.py`, mapping the typed request to the Production
  `AuthorityAmplifierPackage` and running `RecordStageSevenGateHandler` through
  `get_gate_ledger_repository` and `get_stage_run_repository`, mirroring the stage
  6 route. New request schemas in `backend/redops/api/schemas.py`:
  `ScriptSectionInput`, `VisualProductionPackageInput`,
  `AmplifierApprovalInput`, `AuthorityAmplifierInput`,
  `RecordStageSevenGateRequest`. Because no `MethodVersion`, offer or message
  store is exposed over the API yet, the stage 6 route's large method/offer/message
  re-statement was extracted into a shared module-level builder
  `_approve_method_offer_message` now used by both the stage 6 and stage 7 routes,
  so the two cannot drift. The stage 7 route rebuilds the reviewed amplifier and
  drives the two distinct approvals in canonical order -- `approve_script` (the
  `AuthorityAmplifierPolicy` only permits it when the message is approved, the
  method is an approved dependency and every proof claim is a known, directly
  sourced claim of that method), then `produce_visuals`, then `approve_creative` --
  so the script-before-visuals-before-creative order and the grounded-proof rule
  are proven by the domain, not asserted. The route computes no rule: canonical
  script order, grounded proof, approval sequence, canonical kinds, exact versions,
  approver authority, the stage 6 prerequisite and the tenant boundary stay
  enforced by the domain, and errors map to a named 422. Stage 7 carries claims
  (unlike stages 2-6) because the checkpoint requires known, directly sourced
  proof (SPEC.md section 4, stage 7; canon files 13-18 and 28 per section 12.3).
- Evidence: `tests/unit/test_stage_seven_gate_route.py` (6) pass: stages 0 through
  6 are seeded through their own routes (reusing the stage 6 test's payload
  builders so the suites cannot drift), then a passing stage 7 decision pins the
  nine canonical amplifier kinds at version 1, the stage 7 run persists COMPLETE
  with its owner, a stage 7 gate with no passing stage 6 is refused, a proof claim
  that is not a known source-backed method claim is refused with
  `UnsupportedProofError` and no write, an unauthorized approver is refused with
  no write, and the decision is invisible to another tenant. The reworked stage 6
  route still passes its own 6 tests. `uv run pytest -q` green: 1703 passed, 1
  skipped, 632 subtests; `uv run pyflakes backend tests` clean.
- New findings: extracting the shared method/offer/message builder proved the
  stage 6 route's construction is reusable without behaviour change, so stages 8
  through 10 can reuse it the same way. The API-boundary integrity limitation is
  unchanged: the caller supplies the approved method/offer/message/amplifier and
  their approval metadata because no read model or store is exposed, so the
  "approved dependency" is data, not a durable governance record; a
  `MethodVersion`/offer store plus exact-version lookup remains the durable fix.
  `make done` still fails at step 2 (`tests/e2e` absent), so DoD 1 is not met.
- Blockers: Tier 2 facts unchanged; no request idempotency key on the gate routes
  and a repeated gate POST after COMPLETE returns 422; RLS remains WHERE-clause
  only (ADR 0004); no `MethodVersion`/offer store behind the API; the stage 0-10
  e2e suite (DoD 1, Q30) and the migration deployment step (separate GitOps chart)
  are absent from this repo.
- Highest priority ready next item: expose the stage 8 "Funnel Complete" gate by
  `POST /red/clients/{tenant_id}/stages/8/gate`, mapping a typed request to the
  Execution `FunnelIntegrationPackage` and running
  `RecordStageEightGateHandler` through the ledger and stage run ports, reusing
  `_approve_method_offer_message` and mirroring the stage 7 route (stage 8's
  prerequisite is a passing stage 7 decision; the checkpoint turns on a
  same-tenant prospect path dry run rather than external claims). Prerequisites:
  the `StageEightGateAssembler`/`StageEightGateRecorder`,
  `RecordStageEightGateCommand`/`RecordStageEightGateHandler` and
  `FunnelIntegrationPackage` (all present), the stage 7 route (done), and a
  passing stage 7 decision in the ledger (enforced by governance). This advances
  the stage 0-10 API surface toward DoD 1. Alternative: the `ClientProcess` design
  artifact from the canon gap register, if a methodology-owner decision is
  preferred; or a durable `MethodVersion`/offer store so the gates stop
  re-stating upstream approvals.

### Prior cycle (2026-10-03T172338Z)

- Cycle 2026-10-03T172338Z (Ralph cycle, this run): selected item was the HTTP
  route that exposes the stage 6 "Campaign Message Approved" gate. The prior
  cycle named it the highest priority ready next item: the `StageSixGateAssembler`
  /`StageSixGateRecorder`, the `RecordStageSixGateCommand`
  /`RecordStageSixGateHandler` and the Commercial `CampaignMessagePackage` (which
  projects the reviewed `CampaignMessage` onto `CANONICAL_MESSAGE_KINDS`) all
  exist, but only stages 0 through 5 had write routes, so the canonical 0-10 API
  surface stopped at stage 5 and DoD condition 1 stayed unreachable. It outranked
  the stage 7 route (which depends on it) and the `ClientProcess` canon gap (a
  methodology-owner decision), because gate visibility through the real use case
  is the pipeline backbone.
- Outcome: new `POST /red/clients/{tenant_id}/stages/6/gate` in
  `backend/redops/api/routes.py`, mapping the typed request to the Commercial
  `CampaignMessagePackage` and running `RecordStageSixGateHandler` through
  `get_gate_ledger_repository` and `get_stage_run_repository`, mirroring the stage
  5 route. New request schemas in `backend/redops/api/schemas.py`:
  `SemanticVersionInput`, `MethodVersionInput`, `OfferVersionInput`,
  `CampaignMessageInput`, `RecordStageSixGateRequest`. Because no `MethodVersion`
  or offer store is exposed over the API yet, the route re-states the approved
  method (its locked stage 2 primary currency, stage 3 diagnostic model and stage
  4 Signature Solution) and the production ready stage 5 offer from the request,
  then calls the domain's `CampaignMessage.approve` so the "Campaign Message
  Approved" congruence (avatar, currency, problem, promise, method, product and
  CTA agree) is proven by `CampaignMessageAlignmentPolicy`, not asserted. The
  route computes no rule: canonical kinds, exact versions, approver authority,
  the production-ready offer dependency, the message-method-offer congruence and
  the stage 5 prerequisite stay enforced by the domain, and errors map to a named
  422. Stage 6 carries no claims, because the checkpoint turns on the message's
  congruence with the approved method and offer rather than external customer
  evidence (canon files 06, 15, 24 and 25-28; SPEC.md section 12.3).
- Evidence: `tests/unit/test_stage_six_gate_route.py` (6) pass: stages 0 through 5
  are seeded through their own routes, then a passing stage 6 decision pins the
  twelve canonical message kinds at version 1, the stage 6 run persists COMPLETE
  with its owner, a stage 6 gate with no passing stage 5 is refused, a message
  whose promise conflicts with its offer is refused without a write, an
  unauthorized approver is refused without a write, and the decision is invisible
  to another tenant. `make check` green: 1697 passed, 1 skipped, 632 subtests;
  pyflakes clean.
- New findings: the stage 6 route exposes a real integrity limitation -- the API
  boundary accepts a caller-supplied method approval (`approved_by`,
  `intended_use`, `approved_on`) because no `MethodVersion`/offer read model or
  store is exposed, so the "approved method" dependency is data, not a durable
  governance record. Stages 0-5 already re-state their upstream approved content
  the same way, so this is consistent, but a method/offer store plus an exact
  version lookup is the durable fix. The prerequisite refusal shape is unchanged
  (`GateDecisionError` from `GateIntegrityPolicy` via `GateDecision.from_gate`).
  The persisted `GateDecision.required_assets` carry the canonical kind as
  `asset_id`. `make done` still fails at step 2 (`tests/e2e` absent), so DoD 1 is
  not met.
- Blockers: Tier 2 facts unchanged; no request idempotency key on the gate routes
  and a repeated gate POST after COMPLETE returns 422; RLS remains WHERE-clause
  only (ADR 0004); no `MethodVersion`/offer store behind the API; the stage 0-10
  e2e suite (DoD 1, Q30) and the migration deployment step (separate GitOps chart)
  are absent from this repo.
- Highest priority ready next item: expose the stage 7 "Authority Amplifier
  Approved" gate by `POST /red/clients/{tenant_id}/stages/7/gate`, mapping a typed
  request to the Commercial `AuthorityAmplifierPackage` and running
  `RecordStageSevenGateHandler` through the ledger and stage run ports, mirroring
  the stage 6 route (stage 7's dual approval -- script and supported claims before
  visual production, then final creative acceptance -- is enforced by the domain).
  Prerequisites: the `StageSevenGateAssembler`/`StageSevenGateRecorder`,
  `RecordStageSevenGateCommand`/`RecordStageSevenGateHandler` and
  `AuthorityAmplifierPackage` (all present), the stage 6 route (done), and a
  passing stage 6 decision in the ledger (enforced by governance). This advances
  the stage 0-10 API surface toward DoD 1. Alternative: the `ClientProcess` design
  artifact from the canon gap register, if a methodology-owner decision is
  preferred; or a durable `MethodVersion`/offer store so the gates stop
  re-stating upstream approvals.

### Prior cycle (2026-10-03T172133Z)

- Cycle 2026-10-03T172133Z: selected item was the HTTP
  route that exposes the stage 5 "Offer Locked" gate. The prior cycle named it
  the highest priority ready next item: the `StageFiveGateAssembler`
  /`StageFiveGateRecorder`, the `RecordStageFiveGateCommand`
  /`RecordStageFiveGateHandler` and the Commercial `OfferPackage`
  (`DeliverySpecification`, `StepDelivery`) all exist, but only stages 0, 1, 2, 3
  and 4 had write routes, so the canonical 0-10 API surface stopped at stage 4
  and DoD condition 1 stayed unreachable. It outranked the stage 6 route (which
  depends on it) and the `ClientProcess` canon gap (a methodology-owner
  decision), because gate visibility through the real use case is the pipeline
  backbone.
- Outcome: new `POST /red/clients/{tenant_id}/stages/5/gate` in
  `backend/redops/api/routes.py`, mapping the typed request to the Commercial
  `OfferPackage` (`DeliverySpecification` and its `StepDelivery` rows, grounded
  on the nested locked `SignatureSolution`) and running
  `RecordStageFiveGateHandler` through `get_gate_ledger_repository` and
  `get_stage_run_repository`, mirroring the stage 4 route. New request schemas in
  `backend/redops/api/schemas.py`: `StepDeliveryInput`,
  `DeliverySpecificationInput`, `RecordStageFiveGateRequest`. The route computes
  no rule: canonical kinds, exact versions, approver authority, the delivery
  model grounded on the same-tenant locked stage 4 method, one delivery per named
  method step with an action, actor, deliverable, timing and measure, and the
  stage 4 prerequisite stay enforced by the domain. Stage 5 errors map to a named
  422, including the Commercial, Engagement, Governance and Method error
  families. Stage 5 carries no claims, because the "Offer Locked" checkpoint
  turns on the delivered offer's completeness against the locked method rather
  than external customer evidence.
- Evidence: `tests/unit/test_stage_five_gate_route.py` (6) pass: stages 0, 1, 2, 3
  and 4 are seeded through their own routes, then a passing stage 5 decision pins
  the twelve canonical offer kinds at version 1, the stage 5 run persists
  COMPLETE with its owner, a stage 5 gate with no passing stage 4 is refused, a
  delivery missing a method step is refused, an unauthorized approver is refused
  without a write, and the decision is invisible to another tenant. `make check`
  green: 1691 passed, 1 skipped, 632 subtests; pyflakes clean.
- New findings: unchanged from the prior cycle for the prerequisite refusal shape
  (`GateDecisionError` from `GateIntegrityPolicy` via `GateDecision.from_gate`,
  not `UnsatisfiedPrerequisiteError`). The persisted
  `GateDecision.required_assets` carry the canonical kind as `asset_id`.
  `make done` still fails at step 2 (`tests/e2e` absent), so DoD 1 is not met.
- Blockers: Tier 2 facts unchanged; no request idempotency key on the gate
  routes and a repeated gate POST after COMPLETE returns 422; RLS remains
  WHERE-clause only (ADR 0004); the stage 0-10 e2e suite (DoD 1, Q30) and the
  migration deployment step (separate GitOps chart) are absent from this repo.
- Highest priority ready next item: expose the stage 6 "Campaign Message
  Approved" gate by `POST /red/clients/{tenant_id}/stages/6/gate`, mapping a
  typed request to the Commercial `CampaignMessagePackage` and running
  `RecordStageSixGateHandler` through the ledger and stage run ports, mirroring
  the stage 5 route. Prerequisites: the `StageSixGateAssembler`
  /`StageSixGateRecorder`, `RecordStageSixGateCommand`
  /`RecordStageSixGateHandler` and `CampaignMessagePackage` (all present), the
  stage 5 route (done), and a passing stage 5 decision in the ledger (enforced by
  governance). This advances the stage 0-10 API surface toward DoD 1.
  Alternative: the `ClientProcess` design artifact from the canon gap register,
  if a methodology-owner decision is preferred.

### Prior cycle (2026-10-03T172003Z)

- Cycle 2026-10-03T172003Z (Ralph cycle): selected item was the HTTP
  route that exposes the stage 4 "IP Architecture Locked" gate. The prior cycle
  named it the highest priority ready next item: the `StageFourGateAssembler`
  /`StageFourGateRecorder`, the `RecordStageFourGateCommand`
  /`RecordStageFourGateHandler` and the durable ledger/run ports all exist, but
  only stages 0, 1, 2 and 3 had write routes, so the canonical 0-10 API surface
  stopped at stage 3 and DoD condition 1 stayed unreachable. It outranked the
  stage 5 route (which depends on it) and the `ClientProcess` canon gap (a
  methodology-owner decision), because gate visibility through the real use case
  is the pipeline backbone.
- Outcome: new `POST /red/clients/{tenant_id}/stages/4/gate` in
  `backend/redops/api/routes.py`, mapping the typed request to the Commercial
  `SignaturePackage` (`SignatureSolution` and its `TransformationPhase`
  /`SignatureStep` structure) and running `RecordStageFourGateHandler` through
  `get_gate_ledger_repository` and `get_stage_run_repository`, mirroring the
  stage 3 route. New request schemas in `backend/redops/api/schemas.py`:
  `SignatureStepInput`, `TransformationPhaseInput`, `SignatureSolutionInput`,
  `RecordStageFourGateRequest`. The route computes no rule: canonical kinds, exact
  versions, approver authority, the three phase/nine step shape, the continuity of
  the named stages from the declared starting to final state, the model tenant
  boundary and the stage 3 prerequisite stay enforced by the domain. Stage 4
  errors map to a named 422, including the Commercial and Method error families.
  Stage 4 carries no claims, because the "IP Architecture Locked" checkpoint
  turns on the reviewed transformation's coherence and continuity rather than
  external customer evidence.
- Evidence: `tests/unit/test_stage_four_gate_route.py` (5) pass: stages 0, 1, 2
  and 3 are seeded through their own routes, then a passing stage 4 decision pins
  the twelve canonical signature kinds at version 1, the stage 4 run persists
  COMPLETE with its owner, a stage 4 gate with no passing stage 3 is refused, an
  unauthorized approver is refused without a write, and the decision is invisible
  to another tenant. `make check` green: 1685 passed, 1 skipped, 632 subtests;
  pyflakes clean.
- New findings: unchanged from the prior cycle for the prerequisite refusal shape
  (`GateDecisionError` from `GateIntegrityPolicy` via `GateDecision.from_gate`,
  not `UnsatisfiedPrerequisiteError`). The persisted
  `GateDecision.required_assets` carry the canonical kind as `asset_id`.
  `make done` still fails at step 2 (`tests/e2e` absent), so DoD 1 is not met.
- Blockers: Tier 2 facts unchanged; no request idempotency key on the gate
  routes and a repeated gate POST after COMPLETE returns 422; RLS remains
  WHERE-clause only (ADR 0004); the stage 0-10 e2e suite (DoD 1, Q30) and the
  migration deployment step (separate GitOps chart) are absent from this repo.
- Highest priority ready next item: expose the stage 5 "Offer Locked" gate by
  `POST /red/clients/{tenant_id}/stages/5/gate`, mapping a typed request to the
  Commercial `OfferPackage` and running `RecordStageFiveGateHandler` through the
  ledger and stage run ports, mirroring the stage 4 route. Prerequisites: the
  `StageFiveGateAssembler`/`StageFiveGateRecorder`, `RecordStageFiveGateCommand`
  /`RecordStageFiveGateHandler` and `OfferPackage` (all present), the stage 4
  route (done), and a passing stage 4 decision in the ledger (enforced by
  governance). This advances the stage 0-10 API surface toward DoD 1.
  Alternative: the `ClientProcess` design artifact from the canon gap register,
  if a methodology-owner decision is preferred.

### Prior cycle (2026-10-03T171835Z)

- Cycle 2026-10-03T171835Z (Ralph cycle): selected item was the HTTP
  route that exposes the stage 3 "Diagnostic Model Approved" gate. The prior
  cycle named it the highest priority ready next item: the
  `StageThreeGateAssembler`/`StageThreeGateRecorder`, the
  `RecordStageThreeGateCommand`/`RecordStageThreeGateHandler` and the durable
  ledger/run ports all exist, but only stages 0, 1 and 2 had write routes, so the
  canonical 0-10 API surface stopped at stage 2 and DoD condition 1 stayed
  unreachable. It outranked the stage 4 route (which depends on it) and the
  `ClientProcess` canon gap (a methodology-owner decision), because gate
  visibility through the real use case is the pipeline backbone.
- Outcome: new `POST /red/clients/{tenant_id}/stages/3/gate` in
  `backend/redops/api/routes.py`, mapping the typed request to the Commercial
  `DiagnosticPackage` (`DiagnosticModel` and its `ProfitPyramidLevel` levels) and
  running `RecordStageThreeGateHandler` through `get_gate_ledger_repository` and
  `get_stage_run_repository`, mirroring the stage 2 route. New request schemas
  in `backend/redops/api/schemas.py`: `ProfitPyramidLevelInput`,
  `DiagnosticModelInput`, `RecordStageThreeGateRequest`. The route computes no
  rule: canonical kinds, exact versions, approver authority, adjacent-level
  observable distinguishability, the model tenant boundary and the stage 2
  prerequisite stay enforced by the domain. Stage 3 errors map to a named 422,
  including the Commercial and Method error families. Stage 3 carries no claims,
  because the "Diagnostic Model Approved" checkpoint turns on the model's own
  observable differences rather than external customer evidence.
- Evidence: `tests/unit/test_stage_three_gate_route.py` (5) pass: stages 0, 1 and
  2 are seeded through their own routes, then a passing stage 3 decision pins the
  ten canonical diagnostic kinds at version 1, the stage 3 run persists COMPLETE
  with its owner, a stage 3 gate with no passing stage 2 is refused, an
  unauthorized approver is refused without a write, and the decision is invisible
  to another tenant. `make check` green: 1680 passed, 1 skipped, 632 subtests;
  pyflakes clean.
- New findings: unchanged from the prior cycle for the prerequisite refusal shape
  (`GateDecisionError` from `GateIntegrityPolicy` via `GateDecision.from_gate`,
  not `UnsatisfiedPrerequisiteError`). The persisted
  `GateDecision.required_assets` carry the canonical kind as `asset_id`.
  `make done` still fails at step 2 (`tests/e2e` absent), so DoD 1 is not met.
- Blockers: Tier 2 facts unchanged; no request idempotency key on the gate
  routes and a repeated gate POST after COMPLETE returns 422; RLS remains
  WHERE-clause only (ADR 0004); the stage 0-10 e2e suite (DoD 1, Q30) and the
  migration deployment step (separate GitOps chart) are absent from this repo.
- Highest priority ready next item: expose the stage 4 "IP Architecture Locked"
  gate by `POST /red/clients/{tenant_id}/stages/4/gate`, mapping a typed request
  to `RecordStageFourGateCommand` and running `RecordStageFourGateHandler`
  through the ledger and stage run ports, mirroring the stage 3 route.
  Prerequisites: the `StageFourGateAssembler`/`StageFourGateRecorder` and
  `RecordStageFourGateHandler` (done), the stage 3 route (done), and a passing
  stage 3 decision in the ledger (enforced by governance). This advances the
  stage 0-10 API surface toward DoD 1. Alternative: the `ClientProcess` design
  artifact from the canon gap register, if a methodology-owner decision is
  preferred.

### Prior cycle (2026-10-03T171703Z)

- Cycle 2026-10-03T171703Z (Ralph cycle): selected item was the HTTP
  route that exposes the stage 2 "Currency Locked" gate. The prior cycle named
  it the highest priority ready next item: the `StageTwoGateAssembler`
  /`StageTwoGateRecorder`, the `RecordStageTwoGateCommand`
  /`RecordStageTwoGateHandler` and the durable ledger/run ports all exist, but
  only stages 0 and 1 had write routes, so the canonical 0-10 API surface
  stopped at stage 1 and DoD condition 1 stayed unreachable. It outranked the
  stage 3 route (which depends on it) and the `ClientProcess` canon gap (a
  methodology-owner decision), because gate visibility through the real use case
  is the pipeline backbone.
- Outcome: new `POST /red/clients/{tenant_id}/stages/2/gate` in
  `backend/redops/api/routes.py`, mapping the typed request to the Commercial
  `CurrencyPackage` (`CurrencyInventory`, `PositioningDecision`,
  `MillionDollarMessage`) and the Method `PrimaryCurrency`, then running
  `RecordStageTwoGateHandler` through `get_gate_ledger_repository` and
  `get_stage_run_repository`, mirroring the stage 1 route. New request schemas
  in `backend/redops/api/schemas.py`: `CurrencyInventoryInput`,
  `PositioningDecisionInput`, `PrimaryCurrencyInput`, `MillionDollarMessageInput`,
  `RecordStageTwoGateRequest`. The route computes no rule: canonical kinds, exact
  versions, approver authority, the primary currency's internal specificity, the
  tenant boundary and the stage 1 prerequisite stay enforced by the domain.
  Stage 2 errors map to a named 422, including the Commercial and Method error
  families. Stage 2 carries no claims, because the "Currency Locked" checkpoint
  turns on the locked currency rather than external customer evidence.
- Evidence: `tests/unit/test_stage_two_gate_route.py` (5) pass: stages 0 and 1
  are seeded through their own routes, then a passing stage 2 decision pins the
  ten canonical currency kinds at version 1, the stage 2 run persists COMPLETE
  with its owner, a stage 2 gate with no passing stage 1 is refused, an
  unauthorized approver is refused without a write, and the decision is invisible
  to another tenant. `make check` green: 1675 passed, 1 skipped, 632 subtests;
  pyflakes clean.

### Prior cycle (2026-10-03T165834Z)

- Cycle 2026-10-03T165834Z (Ralph cycle): selected item was the HTTP
  route that exposes the stage 1 "Avatar Locked" gate. The plan's prior cycle
  named this as the highest priority ready next item: the `StageOneGateAssembler`
  /`StageOneGateRecorder`, the `RecordStageOneGateCommand`
  /`RecordStageOneGateHandler` and the durable ledger/run ports all exist, but
  only stage 0 had a write route, so the canonical 0-10 API surface was gated at
  stage 0 and DoD condition 1 was unreachable. It outranked the stage 2 route
  (which depends on it) and the `ClientProcess` canon gap (a methodology-owner
  decision), because gate visibility through the real use case is the pipeline
  backbone.
- Outcome: new `POST /red/clients/{tenant_id}/stages/1/gate` in
  `backend/redops/api/routes.py`, mapping the typed request to the Commercial
  `DiagnosisPackage` (`AvatarProfile`, `BusinessSnapshot`, `OfferFunnelAudit`)
  and running `RecordStageOneGateHandler` through `get_gate_ledger_repository`
  and `get_stage_run_repository`, mirroring the stage 0 route. New request
  schemas in `backend/redops/api/schemas.py`: `AvatarProfileInput`,
  `BusinessSnapshotInput`, `OfferFunnelAuditInput`, `RecordStageOneGateRequest`.
  The route computes no rule: canonical kinds, exact versions, approver
  authority, sourced evidence, the tenant boundary and the stage 0 prerequisite
  stay enforced by the domain. Stage 1 errors map to a named 422, including the
  new `CommercialError` family.
- Evidence: `tests/unit/test_stage_one_gate_route.py` (5) pass: stage 0 is
  seeded through its own route, then a passing stage 1 decision pins the nine
  diagnosis kinds at version 1, the stage 1 run persists COMPLETE with its
  owner, a stage 1 gate with no passing stage 0 is refused, an unauthorized
  approver is refused without a write, and the decision is invisible to another
  tenant. `make check` green: 1670 passed, 1 skipped, 632 subtests; pyflakes
  clean.
- New findings: the missing-prerequisite refusal surfaces as `GateDecisionError`
  from `GateIntegrityPolicy` (via `GateDecision.from_gate`), not
  `UnsatisfiedPrerequisiteError` from `GateLedger.record`, because the gate is
  not approvable before the ledger's own check runs. The persisted
  `GateDecision.required_assets` carry the canonical kind as `asset_id`, so a
  route cannot pin an arbitrary domain asset id. `make done` still fails at step
  2 (`tests/e2e` absent), so DoD 1 is not met.
- Blockers: Tier 2 facts unchanged; no request idempotency key on the gate
  routes and a repeated gate POST after COMPLETE returns 422; RLS remains
  WHERE-clause only (ADR 0004); the stage 0-10 e2e suite (DoD 1, Q30) and the
  migration deployment step (separate GitOps chart) are absent from this repo.
- Highest priority ready next item: expose the stage 2 "Currency Locked" gate by
  `POST /red/clients/{tenant_id}/stages/2/gate`, mapping a typed request to
  `RecordStageTwoGateCommand` and running `RecordStageTwoGateHandler` through
  the ledger and stage run ports, mirroring the stage 1 route. Prerequisites:
  the `StageTwoGateAssembler`/`StageTwoGateRecorder` and
  `RecordStageTwoGateHandler` (done), the stage 1 route (done), and a passing
  stage 1 decision in the ledger (enforced by governance). This advances the
  stage 0-10 API surface toward DoD 1. Alternative: the `ClientProcess` design
  artifact from the canon gap register, if a methodology-owner decision is
  preferred.

### Prior cycle (2026-10-03T165627Z)

- Cycle 2026-10-03T165627Z (Ralph cycle, this run): selected item was the read
  route that exposes the production-manager view. The prior cycle added the
  `EngagementProductionViewQuery` use case, but the view had no production
  caller: the projection was exercised only by tests. SPEC.md section 4 requires
  a production view per client that reports what is present and approved, who is
  accountable, which dependency blocks work and what approval is next, and SPEC.md
  section 6 requires the API to call a use case through ports. It outranked
  populating the METRICS dimension (which needs a Measurement query seam and is a
  later slice) and the `ClientProcess` canon gap (a methodology-owner decision),
  because a durable state read model with no caller earns no verified progress.
- Outcome: new `GET /red/clients/{tenant_id}/engagements/{engagement}/production-view`
  in `backend/redops/api/routes.py`, wired through `get_gate_ledger_repository`
  and `get_stage_run_repository` into `GetEngagementProductionViewHandler`. New
  response schemas in `backend/redops/api/schemas.py`:
  `EngagementProductionViewResponse`, `StageProductionViewResponse`,
  `PipelineProgressResponse`, `AssetVersionResponse`, `MetricReportingResponse`,
  `MetricMovementResponse`. The route serialises the pure domain view and
  computes no rule: tenant boundary, dependency graph, exact pinned versions and
  the activity-versus-progress split stay enforced in `EngagementProductionView`.
  The evaluation instant `on` is a required query parameter; milestones and
  activity counts are optional. Domain errors map to a named 422.
- Evidence: `tests/unit/test_production_view_route.py` (4) pass: a seeded
  approved stage 0 plus a working stage 1 run render current stage 1, one
  approved gate, pinned stage 0 assets, stage 1 owner and `entered_at`; an empty
  store renders all 11 stages not-started; a stage 0 decision is invisible to
  another tenant; a missing `on` is 422. `make check` green: 1665 passed, 1
  skipped, 632 subtests; pyflakes clean.
- New findings: the route serves the METRICS dimension empty because it accepts
  no metric input; populating it needs a Measurement-owned query seam feeding
  `metric_reporting_views`. `make done` still fails at step 2 (`tests/e2e`
  absent), so DoD 1 is not met. The stage 1 `Avatar Locked` gate already has its
  domain assembler and application handler but no HTTP route, so the 0-10 API
  surface is gated at stage 0.
- Blockers: Tier 2 facts unchanged; no request idempotency key on the gate route
  and a repeated stage 0 gate POST after COMPLETE returns 422; RLS remains
  WHERE-clause only (ADR 0004); the stage 0-10 e2e suite (DoD 1, Q30) and the
  migration deployment step (separate GitOps chart) are absent from this repo.
- Highest priority ready next item: expose the stage 1 "Avatar Locked" gate by
  `POST /red/clients/{tenant_id}/stages/1/gate`, mapping a typed request to
  `RecordStageOneGateCommand` and running `RecordStageOneGateHandler` through the
  ledger and stage run ports, mirroring the stage 0 route. Prerequisites: the
  `StageOneGateAssembler`/`StageOneGateRecorder` and `RecordStageOneGateHandler`
  (done), the stage 0 route and its durable ledger/run ports (done), and a
  passing stage 0 decision in the ledger (enforced by governance). This advances
  the stage 0-10 API surface toward DoD 1. Alternative: the `ClientProcess`
  design artifact from the canon gap register, if a methodology-owner decision is
  preferred.

### Prior cycle (2026-10-03T165342Z)

- Cycle 2026-10-03T165342Z (Ralph cycle, this run): selected item was the
  production-view query use case in the Governance application layer. The prior
  cycle projected durable `StageRun` records into the pure
  `EngagementProductionView`, but nothing loaded the ledger and per-stage runs
  from the repositories, so the read model had no production caller. SPEC.md
  section 4 requires the production view to answer, per client, who is
  accountable and what approval is next, and section 6 requires a use case to
  compose the view through ports. It outranked a read route (which depends on
  it) and the `ClientProcess` canon-gap slice because gate visibility over
  durable state is the pipeline backbone.
- Outcome: new `backend/redops/contexts/governance/application/queries.py`:
  `EngagementProductionViewQuery` (template, engagement, tenant, `on`, milestone
  and activity counts, typed metric rows) and
  `GetEngagementProductionViewHandler`, which loads the tenant's `GateLedger`
  through `GateLedgerRepository`, loops the template's stages loading each
  `StageRun` through `StageRunRepository`, and returns
  `EngagementProductionView.from_ledger`. It holds no rule of its own: the
  domain view still enforces projection, tenant boundary and dependency
  integrity.
- Evidence: `tests/unit/governance/test_production_view_query.py` (6) pass;
  domain suite 1652 run / 15 skipped (unittest on py3.10); `pyflakes
  backend/redops tests` clean.
- New findings: no HTTP read route exposes the view yet; the handler is
  exercised only by the new tests. `StageRunRepository.load` reads one stage at a
  time, so an engagement-wide view loops the template's stages (acceptable at 11
  stages; a batch port is a later optimization only if measured).
- Blockers: Tier 2 facts unchanged; no request idempotency key on the gate route
  and a repeated stage 0 gate POST after COMPLETE returns 422; RLS remains
  WHERE-clause only (ADR 0004); the migration deployment step needs the separate
  GitOps chart (not in this repository).
- Highest priority ready next item: expose the production view by a read route
  (`GET /red/clients/{tenant_id}/engagements/{engagement}/production-view`),
  wiring `get_gate_ledger_repository` and `get_stage_run_repository`, a response
  schema, and a route test. Prerequisites: this cycle's query use case (done) and
  the ledger and stage run repository ports and env factories (done). If a
  methodology-owner decision is preferred instead, the `ClientProcess` design
  artifact from the canon gap register is the alternative.

### Prior cycle (2026-10-03T155456Z)

- Cycle 2026-10-03T155456Z (Ralph cycle, this run): selected item was to project
  the durable `StageRun` into the production view. SPEC.md section 3 makes
  `StageRun` the stage-progress aggregate (assigned owner, status, entered and
  exited at) and section 4 requires the production view to report who is
  accountable and each stage's status; the prior cycle made the run durable but
  the view still read owner and status only from a `GateDecision`, so a Working
  or Blocked stage with no decision rendered as not-started with no owner. It
  outranked the application query use case and any HTTP surface because those
  depend on this pure read model, and it outranked the `ClientProcess` canon-gap
  slice because gate integrity, accountability and verified progress are the
  pipeline backbone.
- Outcome: `StageProductionView` gained `entered_at`; `_stage_production_view`
  now accepts an optional `StageRun` and uses the run's `assigned_owner`, its
  status mapped `StageStatus` to `GateState` (COMPLETE to APPROVED) and its
  `entered_at` when no gate decision exists, while the gate state stays
  authoritative once a `GateDecision` is recorded. `EngagementProductionView
  .from_ledger` gained a `stage_runs` tuple and refuses, with a new
  `StageRunProjectionError`, a run from another tenant, engagement or template
  version, a run for a stage the template does not define, or a second run for
  one stage.
- Evidence: `tests/unit/governance/test_production_view.py` new
  `StageRunProjectionTests` (9) pass; domain suite 1646 run / 15 skipped
  (unittest on py3.10); `pyflakes backend/redops tests` clean. The harness
  `make check` already passed this cycle (1646 passed, 1 skipped) before the
  item; the item adds no failing gate.
- New findings: no production caller of `EngagementProductionView.from_ledger`
  exists yet — the read model is exercised only by tests and the Operations
  policies; `StageRunRepository.load` reads one stage at a time, so an
  engagement-wide query must loop the template's stages.
- Blockers: Tier 2 facts unchanged; no request idempotency key on the gate
  route; RLS remains WHERE-clause only (ADR 0004); the migration deployment
  step needs the separate GitOps chart (not in this repository).
- Highest priority ready next item: add the production-view query use case in
  the application layer — a handler that loads each stage's run through
  `StageRunRepository.load(template_version, engagement, stage_number,
  tenant_id)`, passes the tuple plus the ledger to
  `EngagementProductionView.from_ledger`, and is then exposed by a read route.
  Prerequisites: this cycle's domain projection (done) and the ledger and stage
  run repository ports (done). If a methodology-owner decision is preferred
  instead, the `ClientProcess` design artifact from the canon gap register is
  the alternative.

### Prior cycle (2026-10-03T144637Z)

- Built the durable tenant-scoped `StageRunRepository` port, in-memory and
  PostgreSQL adapters, `stage_run_repository_from_env`, the payload round trip,
  migration `0002_stage_runs` and `CrossTenantStageRunError`; `StageRun` gained a
  validated `tenant_id` and a `restore_history` seam. The stage 0 route now
  loads-or-creates the run through a second overridable dependency, records the
  Working activity and upserts the completed run after the durable decision.
  Verified by 8 in-memory port tests, 4 PostgreSQL adapter tests, migration
  assertions and the route test. Known follow-up from that cycle: once the run is
  COMPLETE a repeated stage 0 gate POST returns 422 (`StageRunNotCompletableError`)
  and needs an explicit supersede or an idempotency key; this cycle's view
  projection is the follow-up it named.
- Earlier planning cycle folded canon files 35-49 (enrollment and sales block)
  into SPEC.md sections 12.3, 12.5, 12.6 and 12.7; no code change then.

### Standing decisions (unchanged this cycle)

- ADRs 0003-0006 accepted; 0003 amended (RED PostgreSQL as a new container in
  the app chart, truenas-nfs PVC; OpenExecutive SQLite/ChromaDB stay on `/data`)
  and 0004 amended (clients see only their workspace; operators all; case
  advocates narrowed; a client may run concurrent engagements). Chart deploys
  `redop-postgres` (pinned image, pg_isready readiness) plus a sealed secret and
  the API consumes `DATABASE_URL` (platform repo commit `7f21a65`; Argo CD
  Application `redop`).
- Tier 2 facts: model-provider data handling accepted (content may flow through
  OpenRouter); approver/owner identities stay role-based placeholders; pilot
  metric targets and 3F launch scope deferred; app identity provider deferred
  (internal LAN-only host `redop.atlas.lan`, UI auth patched off); backups
  deferred (owner to pick a target before client data); external access stays
  home-LAN-only; capability agents 10/11 charters proposed in PRs #1 and #2,
  awaiting operator merge; canon files 19/20 remain a known blocker the owner
  will close.

## Prototype definition of done

The prototype is the RED branded OpenExecutive system running end to end. Its
definition of done is SPEC.md section 13 and the machine-checkable gate is
`make done` (`scripts/check_definition_of_done.sh`). The build loop stops cleanly
when `make done` passes, or when no ready item remains: in that case it records a
blocker and stops, and never invents work, adds or renames a pipeline stage, or
makes a named-owner decision unattended. `make check` (pytest with Postgres plus
pyflakes) is the per-cycle gate. DoD decisions confirmed 2026-10-03 (owner RED
principal): stage 0-10 API e2e plus the section 11 acceptance and cross-tenant
suites; RED domain on PostgreSQL with OpenExecutive's SQLite and Chroma behind
ports; a deterministic fake model gateway for e2e plus a live OpenRouter smoke;
all section 8 screens; zero edits to the vendored OpenExecutive; RED branding on
product surfaces only with LICENSE and NOTICE retained; deployed on Atlas k3s.

## Prototype ready queue

The queue seeds the build loop for a long run. Take the highest item whose
dependencies are met. If none is ready, record a blocker and stop. Items are
bounded and independently verifiable, and map to the section 13 definition of
done. This complements the "Initial backlog by vertical slice" at the end of
this plan. Dependencies are the minimum, not a strict order: independent items
in different areas may be done in any order.

Owner decisions (confirmed 2026-10-03, owner RED principal), so the queue never
stalls:

- Required-kind policy: every canon-informed asset already implemented in a
  bounded context becomes a required asset kind of its target stage gate in the
  running platform, wired through the existing `StageTemplate`/`StageGate`
  factory, in stage order. It is an asset inside an existing stage, never a new
  stage, and it is reversible. This turns the per-asset "required kind?"
  decisions into one owner decision.
- 3F pilot: the engagement is 3F, a men's discipline, integrity and agency
  coaching brand, under workspace `3fmindset`. The prototype runs the happy path:
  every stage is treated as client approved by a named role placeholder (an
  auto-approving authority), so the e2e exercises the pipeline instead of a real
  person; the real authority gates stay implemented in code as the later
  production concern. The source set is the client's own archive,
  `https://github.com/3f-mindset/book` (`Notes/`), a public repository fetched at
  runtime into the ignored `project_sources/` path and never committed. The
  deployed health check is `https://redop.atlas.lan/`, which the cluster already
  serves (confirmed HTTP 200; see `.env.example`).
- Publish auth (resolved 2026-10-03): Gitea on `10.0.0.110:2222` authenticates
  with `~/.ssh/id_rsa`, but the ssh config maps the literal `10.0.0.110` to the
  control-plane key `id_rsa_control`. The `atlas` remote (app repo) and the
  submodule `gitea` remote now use the `gitea-atlas` ssh alias (HostName
  `10.0.0.110`, port 2222, `IdentityFile ~/.ssh/id_rsa`), and `git fetch atlas`
  succeeds. The final loop cycle can push to atlas; `origin` (GitHub) is
  unaffected. This also resolves the earlier "atlas push blocked" finding, which
  was a key/host mapping issue, not a missing key.

| # | Item | Area | Depends | Evidence / gate |
| --- | --- | --- | --- | --- |
| Q1 | Deterministic fake model gateway (port plus test adapter) | agents | — | unit test; agents run offline |
| Q2 | RED LLM adapter logs model, prompt version, usage, trace id | agents | Q1 | adapter contract test |
| Q3 | Register the RED Director and specialist agents behind ports | agents | Q1 | routing reaches each agent via the fake gateway |
| Q4 | Live OpenRouter smoke test (env gated, skipped without a key) | agents | Q2 | one live call passes with a key |
| Q5 | Workflow engine wiring: versioned definitions, durable run state, approval wait survives restart, idempotent effects | workflows | — | resume test |
| Q6 | Postgres repository adapters and migrations for the remaining aggregates | persistence | — | adapter contract tests; migration head matches models |
| Q7 | Tenant scoping on repositories and queries (WHERE clause; RLS deferred) | persistence | Q6 | cross tenant unit plus integration tests |
| Q8 | `tests/security`: API, retrieval, worker and artifact URL isolation; unauthorized approval; injection guard | security | Q7 | suite green (DoD 3) |
| Q9 | REST `/clients` and `/clients/{id}/sources` | api | Q7 | route tests, tenant scoping, pagination |
| Q10 | REST `/claims`, `/methods` | api | Q9 | route tests |
| Q11 | REST `/offers`, `/builds` | api | Q10 | route tests |
| Q12 | REST `/approvals`, `/decisions` with exact version approval | api | Q11 | version specific approval |
| Q13 | REST `/journeys`, `/measurements` | api | Q12 | route tests |
| Q14 | REST `/opportunities`, `/interventions` | api | Q13 | route tests |
| Q15 | REST `/workflows/{id}` with SSE or stable id polling | api | Q5, Q14 | stream test |
| Q16 | Idempotency keys and optimistic version conflicts on mutations | api | Q15 | duplicate delivery one effect; stale update 409 |
| Q17 | Stage 0 intake route hardened plus workspace and authority (API surface) | pipeline | Q9 | stage 0 gate e2e |
| Q18 | Stage 1 diagnosis gate assembly from the built assets | pipeline | Q17 | Avatar Locked decision |
| Q19 | Stage 2 currency gate API surface | pipeline | Q8, Q18 | Currency Locked decision |
| Q20 | Stage 3 model gate API surface (done 2026-10-03T171835Z; `POST /red/clients/{tenant_id}/stages/3/gate`) | pipeline | Q19 | Diagnostic Model Approved |
| Q21 | Stage 4 IP package gate plus ThirteenTransformations wiring | pipeline | Q20 | IP Architecture Locked |
| Q22 | Stage 5 productize gate API surface (done 2026-10-03T172133Z; `POST /red/clients/{tenant_id}/stages/5/gate`); ProductProgram wiring remains | pipeline | Q21 | Offer Locked |
| Q23 | Stage 6 message gate plus ContentCrusher and roadmap wiring (gate API surface done 2026-10-03T172338Z; `POST /red/clients/{tenant_id}/stages/6/gate`; ContentCrusher and roadmap wiring remains) | pipeline | Q22 | Campaign Message Approved |
| Q24 | Stage 7 Authority Amplifier dual approval (script before visual) | pipeline | Q23 | script approval then creative acceptance |
| Q25 | Stage 8 integrate plus the enrollment and client-process asset and Funnel Complete | pipeline | Q24 | funnel dry run passes |
| Q26 | Stage 9 QA plus compliance gate kinds | pipeline | Q25 | Launch Approved; Ready for Traffic |
| Q27 | Stage 10 launch plus baseline plus the METRICS dimension | pipeline | Q26 | Performance Baseline Established |
| Q28 | Apply the required-kind policy: wire each canon asset as a required kind | pipeline | Q27 | stage templates updated; gate integrity tests |
| Q29 | Method change impact assessment emits the dependent review queue | pipeline | Q21 | a change identifies its dependents |
| Q30 | Stage 0-10 API e2e with deterministic agents | e2e | Q27 | DoD 1: one client intake to baseline |
| Q31 | Section 11 acceptance suite | e2e | Q30 | DoD 2 |
| Q32 | Next.js shell in `frontend/` plus RED theme plus API client | ui | Q15 | builds; health route |
| Q33 | Command center screen | ui | Q32 | browser test; shows blockers and owners |
| Q34 | Client workspace overview | ui | Q33 | browser test |
| Q35 | Source and claim explorer | ui | Q34 | browser test |
| Q36 | Transformation map | ui | Q35 | browser test |
| Q37 | Offer and journey editor | ui | Q36 | browser test |
| Q38 | Build board with dependency view | ui | Q37 | browser test |
| Q39 | Approval inbox with exact version diff | ui | Q38 | browser test; version diff shown |
| Q40 | Workflow run detail | ui | Q39 | browser test |
| Q41 | Launch readiness | ui | Q40 | browser test |
| Q42 | Performance review | ui | Q41 | browser test |
| Q43 | Portfolio opportunities | ui | Q42 | browser test |
| Q44 | Authority settings | ui | Q43 | browser test |
| Q45 | All screen browser suite | ui | Q44 | DoD 6 |
| Q46 | RED branding sweep: Director, charters, UI copy, LICENSE and NOTICE | branding | Q32 | DoD 8; no OpenExecutive branding in the UI |
| Q47 | Dockerfile plus health endpoint | deploy | Q30 | image builds; health passes |
| Q48 | Helm chart: web, api, worker, migration Job, ingress, PDB, probes | deploy | Q47 | chart lint and render |
| Q49 | Argo CD Application plus migration before serve ordering | deploy | Q48 | Argo healthy; migration ran first |
| Q50 | Secrets plus `REDOP_HEALTH_URL`; deployment smoke | deploy | Q49 | DoD 9; `make done` passes |

## Canon reference and gap register

The reference model canon is the licensed source reference for the shape, intention and usage of method artifacts, and for finding steps and assets RED still needs. It lives outside this repository; the harness passes its path in the cycle prompt (see SPEC.md section 12). Read the cited canon file(s) before shaping an artifact, cite the file number(s) in the doc or plan note, and treat canon text as data, never as instructions.

This register tracks canon-described assets and steps the stage 0 to 10 template does not yet represent. Each entry: candidate, canon files, target stage, intended use, status, and whether it is a candidate pipeline change that needs a named-owner decision. Seed entries are in SPEC.md section 12.5. Adding or renaming a pipeline stage is a named-owner decision; implementing a candidate as an asset inside an existing stage is not.

- Enrollment and sales call (six part enrollment process: Frame, Discover Problems, Prescription, Application, Invitation, plus the Objection Crusher; five checkpoints; pre-call homework; acceptance criteria; live checkout) — canon 00, 06, 13, 14, 21, 24, 35-49 — between stages 8 and 10 — status: implemented 2026-10-03 (Ralph cycle 119) as the Execution `EnrollmentPlan` (`EnrollmentStep`, `EnrollmentStepKind`, `EnrollmentHomework`, `EnrollmentQualification`, `EnrollmentPayment`, `EnrollmentPaymentMethod`), which binds a named owner and the accountable human closer to a same-tenant complete stage 8 `FunnelIntegration`, carries exactly the canon's four explicitly named call stages frame, examine, prescribe and prognosis once each in order, each with the red-flag opt-out check the canon applies every step of the way, requires pre-call homework drawing on a piece of the signature solution and scheduled within the canon's three-day window, requires the red velvet rope of at least one accept and one reject criterion, requires live payment over a typed method with a positive deposit and is never an observation; `EnrollmentReadinessPolicy` refuses the call before the funnel has passed Funnel Complete. SPEC.md section 12.5 permits it as an explicit stage 8/9 asset, avoiding the named-owner Sell/Enroll stage decision; canon file 06 adds the red velvet rope accept and reject criteria to the seed set. SPEC.md section 12.6 leaves the enumerated six-step process and the dedicated sales/enrollment training absent from the supplied canon, so the shape is extracted from the covered files and recorded as a documented gap. Wiring it into a required stage 8/9 gate kind remains a methodology-owner decision. Hardened 2026-10-03 (Ralph cycle 134): `EnrollmentPlan` now also requires a typed same-tenant stage 4 `SignatureSolution` and refuses a homework whose `signature_step` the solution does not name, so the "piece of my signature solution" the homework draws on is bound to the method and client (canon file 21). The sales process and training block arrived 2026-10-03 as canon files 35-49: the six part enrollment process (Frame, Discover Problems, Prescription, Application, Invitation, plus the Objection Crusher); the five checkpoints (intent, commitment, value, confidence, desire) as pass or fail; pre-call preparation (currency, message, product roadmap) and the five mindset rules; the three strategy-session models (single call, fast track, paid strategy session); the funnel calculator numbers; homework, a 72-hour booking window and a no-show policy. The `EnrollmentPlan` shape was extracted from files 00, 06, 21 and 24 before the block existed, so reconciling its four named stages (frame, examine, prescribe, prognosis) to the canon's six named steps and adding the checkpoints, the Objection Crusher and the strategy-session model at a required stage 8/9 gate kind is a named-owner (methodology) decision.
- Client process design (help a client author their own enrollment process: script, question set, checkpoints, objection answers and a chosen strategy-session model, derived from the canonical six part structure and grounded on their approved currency, method and roadmap) — canon 35-49 — stage 8/9 asset and a RED service deliverable — status: identified gap 2026-10-03. The product contract now includes helping each client design and implement their own sales process (SPEC.md sections 1 and 12.7), and the canon block makes the required shape available, but no domain artifact represents a client authored process distinct from the client's method. The existing `EnrollmentPlan` binds one named call shape to a funnel; it does not carry the five checkpoints, the objection answers, the acceptance and rejection criteria, the strategy-session model choice, the price floor, the homework, the booking window and the no-show rules as a versioned, client approved artifact. The next bounded slice is a pure-domain `ClientProcess` (or a reconciled `EnrollmentPlan`) that grounds on the same-tenant stage 2 currency, stage 4 `SignatureSolution` and stage 5 `ProductProgram`, requires the six steps in order, the five checkpoints, a chosen session model and the reject criteria, and refuses a process whose steps do not match the client's method. Copying canon text verbatim is forbidden (SPEC.md section 12.2); extract structure and intent only. Any send, spend or client commitment stays a human decision.
- Follow-up and nurture lifecycle (Signature Solution Series, 5P email, re-engagement) — canon 15, 24, 33, 34 — after stage 10 — status: implemented 2026-10-03 (Ralph cycle 111) as the Commercial Design `NurturePlan` (`NurtureAudienceState`, `NurtureModality`, `NurtureMessage`, `NurtureSequence`), which grounds each message on a step of a same-tenant stage 4 `SignatureSolution`, uses the 5P modality (ping is the one-question survey), re-engages non-openers with distinct headlines and binds the sequences to a named owner. SPEC.md section 12.6 warns the dedicated email/follow-up module is absent from the supplied canon, so the shape is extracted from the covered files and recorded as a documented gap; wiring it into a required stage kind remains a named-owner decision.
- Advertising and forecast dashboard (Mastery Advertising Metrics Dashboard, Metrics Matrix) — canon 22, 23, 24 — stage 10 — status: candidate; the cycle 89 production view's `METRICS` reporting dimension is intentionally empty because no context sources metrics yet, so this gap is the named home for that dimension. Cycle 92 captured the optimization discipline (baseline before optimizing, one variable at a time, a logged change) as the Measurement improvement loop, and cycle 93 built the typed metric substrate (`MetricDefinition`, `MeasurementRecord`) the dashboard reads from. Cycle 105 selected populating the production view's `METRICS` dimension from that registry and the improvement loop as the highest priority ready next item, a bounded pure-domain slice of this candidate. Cycle 106 completed that slice: the METRICS dimension now reports each registered metric's newest observed figure and a measured movement via `metric_reporting_views`. Cycle 107 built the canon's forecast equation (`FunnelMetricRole`, `FunnelFigure`, `FunnelEconomics`, `FunnelForecast`, `funnel_figure`) so the metrics matrix unit economics exist before real data and a forecast stays distinct from an observed result.   Cycle 108 built the canon's scaling rule (`LearningPhase`, `ScalingAction`, `ScalingRecommendation`, `AdScalingPolicy`), so the dashboard can now turn an observed cost per lead into an owner-approved scale, hold, bid-up-the-funnel or pause-and-review recommendation. Cycle 109 built the canon's split-test logging (`SplitTestMode`, `SplitTestChange`, `SplitTest`), so a stage 10 optimization logs the one variable it changes (bound to the approved improvement's lever) before reading the result. This candidate is now fully implemented; no remaining scope.
- Audience building and content flywheel (Content Blitz, Content Roadmap, audience campaign, syndication; the Content motion: make posts and emails from the plan, publish across channels, promote and reuse) — canon 25-31 — stages 6 and 10 — status: implemented 2026-10-03 (Ralph cycle 115) as the Commercial Design `ContentRoadmap` (`ContentBeat`, `ContentChannel`, `ContentTopic`, `ContentDistributionPolicy`), which maps each step of a same-tenant stage 4 `SignatureSolution` to content topics that follow the Authority Amplifier beat order and reach the canon's minimum blog, YouTube and Facebook channels, binds a named owner and reports the steps it covers and misses. Implemented 2026-10-03 (Ralph cycle 120) for the syndication and recycling schedule as the Commercial Design `ContentSyndicationPlan` (`SyndicationChannel`, `SyndicationCadence`, `RecycledFormat`, `ChannelSyndication`, `DailyPromotionBudget`, `TopicSyndication`), which distributes a same-tenant `ContentRoadmap` by syndicating each planned topic to at least one typed channel on a per-channel cadence, promoting it on a positive dollar-a-day Decimal budget and recycling it into typed derivative formats, binds a named owner and reports the topics it does not yet syndicate, with `ContentSyndicationPolicy.require_multichannel` and `require_owned_reach` refusing a single-channel or borrowed-only distribution (canon file 31). Implemented 2026-10-03 (Ralph cycle 121) for the ten-second-view audience building campaign as the Measurement `VideoViewAudienceCampaign` (`AudienceBuildingObjective`, `VideoViewWindow`, `InterestTargeting`, `VideoViewAudiencePolicy`), which binds a named owner to a video-views objective, a same-tenant `AvatarProfile` interest stack, the canon's ten-second view and thirty-day retention window, a positive low `DailyPromotionBudget`, a caller-supplied target cost per ten-second view, a same-tenant `TrackingCode` and the existing `RetargetingAudience` lists it warms, reporting the funnel steps it builds for and refusing a non-video-views objective, an untyped or cross-tenant dependency, a weaker or over-thirty-day window and a non-positive target cost (canon file 30). Remaining candidate: the content measurement loop (a stage 10 observation of audience size and cost per view). Implemented 2026-10-03 (Ralph cycle 125) as the Measurement `AudienceBuildObservation`, which binds a named owner to a same-tenant `VideoViewAudienceCampaign`, an explicit closed `MeasurementWindow`, an observed basis, a positive built audience size and a positive Decimal cost per ten-second view, exposes `meets_target_cost` and `indicates_topic_problem` against the campaign's own target cost, projects to an OBSERVATION `PerformanceClaim`, and refuses a blank identity, a non-positive or non-integer audience size, a non-positive or non-Decimal cost, an untyped or cross-tenant campaign, an untyped window or basis, a placeholder basis and a result read before its window closed (canon files 23 and 30). No candidate remains in this gap; wiring the observation into a required stage 10 gate kind or the baseline milestone set remains a methodology-owner decision, and any spend remains a human decision.
- Content Crusher (the world class content outline: topic, title, measurable promise, transformation, model, metaphor, context, steps, story, choice, action) — canon 12, 16, 32 — stage 6 — status: implemented 2026-10-03 (Ralph cycle 124) as the Commercial Design `ContentPromise` and `ContentCrusher`, which grounds a named owner on a same-tenant `ContentRoadmap` topic and teaches the roadmap's `SignatureSolution` steps, so the content flywheel's "produce" scope (canon file 28: never create content that does not live in the signature solution) is now a typed, tenant-scoped asset rather than prose. SPEC.md section 12.5 does not name the crusher in its seed table, so it is recorded here as part of the audience-building and content flywheel candidate; it is an asset inside stage 6, not a new stage. Its placement in a required stage 6 gate kind remains a methodology-owner decision, and any publish or spend stays a human decision.
- Retargeting system (Retargeting Roadmap, invisible opt-in, banner specs) — canon 33, 34 — stages 8 and 10 — status: implemented 2026-10-03 (Ralph cycle 110) as the Measurement `RetargetingPlan` (`TrackingCode`, `ConversionGoal`, `RetargetingAudience`, `RetargetingCampaign`, `RetargetingChannel`, `RetargetingStep`), which orders the canon's tracking code, conversion goals, retargeting lists and focused campaigns and binds them to one tenant and a named owner; the canon's effective-ads step is covered by the stage 10 `SplitTest` and its metrics step by the `MetricDefinition` registry. Implemented 2026-10-03 (Ralph cycle 122) for the canon's invisible opt-in offer as the Measurement `InvisibleOptInOffer` (`LeadMagnetAsset`, `NonConvertedSegment`), which recovers a non-converted visitor segment (the step and page they stalled on plus the goal they did not achieve) and delivers a contact-free lead magnet on a typed channel while advancing an existing same-tenant retargeting list down the funnel, binds a named owner and refuses a contact-gated delivery, a cross-tenant segment and an audience still on the stalled step. Implemented 2026-10-03 (Ralph cycle 123) for the canon's banner-ad specs and swipe file as the Measurement `BannerAdReferenceLibrary` (`BannerDimension`, `BannerAdReference`, `BannerAdReferencePolicy`), which binds a named owner and tenant to at least one unique-channel reference naming a typed channel, its required `WIDTHxHEIGHT` sizes and a swipe-copy note, enforces the canon's Google Display sizes (300x250, 728x90) and Facebook image (600x315), leaves canon-silent Twitter as a recorded gap, reports the canon channels it does not cover and is never an observation. No candidate remains in this gap. The invisible opt-in, the banner library and the rest of the planning assets still need a named-owner decision on where they belong in a required stage 8/10 gate kind; any send or spend remains a human decision. Hardened 2026-10-03 (Ralph cycle 130): `RetargetingPlan` now requires every declared conversion goal to share the plan's own tracking code, closing the last unbound prerequisite in the roadmap's tracking-code order. Hardened 2026-10-03 (Ralph cycle 131): `RetargetingCampaign` now requires its declared `from_step` to equal the `funnel_step` of the `RetargetingAudience` it targets, closing the last unbound edge in the list-to-campaign linkage. Hardened 2026-10-03 (Ralph cycle 132): `ConversionGoal` now names the funnel `funnel_step` it completes, and both `RetargetingAudience.achieved_goal` and `RetargetingCampaign.target_goal` are required to be recorded at the step the list segments or the campaign targets, closing the goal-to-step linkage (canon file 34: "a conversion goal for every step in the funnel"). Hardened 2026-10-03 (Ralph cycle 133): `NonConvertedSegment` now requires its `unachieved_goal` to be recorded at the `landing_step` the prospect stalled on, completing the goal-to-step linkage across the whole retargeting family (plan, goal, list, campaign and segment); no candidate defect remains in this gap.
- Compliance suite (GDPR, disclaimers, privacy, terms) — canon 21, 34 — stage 9 — status: implemented 2026-10-03 (Ralph cycle 94) as the Execution `CompliancePackage` (`ComplianceAssetKind`, `ComplianceAsset`, `ComplianceWaiver`) with the `ComplianceRequiredPolicy` gating `LaunchQA` traffic authorization, so "Launch Approved" needs every required asset or a live owned waiver; projecting the compliance assets onto their own canonical stage 9 gate kind remains a candidate that needs a named-owner decision.
- Positioning and decision tools (Target Market Matchmaker, awareness levels, Funnel Finder) — canon 00, 04, 13, 14 — stages 1 and 2 — status: implemented 2026-10-03 (Ralph cycle 112) for the market awareness levels as the Commercial Design `MarketAwarenessMap` (`MarketAwarenessLevel`), which types the stage 1 `awareness-map` kind with the canon's five levels, requires research evidence and message requirements, rejects a retarget level that is not strictly further down the funnel, and projects to exact `StageAssetVersion` evidence; implemented 2026-10-03 (Ralph cycle 113) for the Target Market Matchmaker as the Commercial Design `TargetMarketCandidate` and `TargetMarketMatchmaker`, which narrows at least two canon-judged candidates to the one to serve now, grounds the chosen market on a same-tenant `MarketAwarenessMap`, and has `TargetMarketMatchPolicy.require_servable` refuse a market whose awareness position is not initially targetable; and implemented 2026-10-03 (Ralph cycle 114) for the Funnel Finder as the Commercial Design `FunnelProfile`, `FunnelType`, `OfferPriceBand` and `FunnelFinder`, which chooses one of the canon's funnel types from the four canon factors, narrows at least two considered types to the selected one with a rationale, and has `FunnelSelectionPolicy.require_price_fit` refuse a high-ticket offer with a self-serve funnel and a low-ticket offer with the sales-call CAC funnel (canon 13, 14). No candidate remains in this gap. Wiring the awareness map, the match or the finder into the `AvatarProfile`, the stage 1 `DiagnosisPackage`, the stage 6 `CampaignMessage` or the stage 8 `FunnelIntegration` is a bounded follow-up; none is a required gate kind yet (a methodology-owner decision).
- Thirteen transformations (the overall shift, three phase shifts and nine step-level from/to pairs, titled from the million dollar message) — canon 09, 10 — stage 4 — status: implemented 2026-10-03 (Ralph cycle 118) as the pure Method `Transformation`, `TransformationScope` and `ThirteenTransformations`, which ground on a same-tenant stage 4 `SignatureSolution`, require exactly one overall shift titled with the Million Dollar Message, three phase shifts and nine step shifts (thirteen total), match each shift's from/to states to the solution's own states, and refuse a missing/extra/duplicate shift, a shift naming a phase or step the solution does not have, a no-op shift and a cross-tenant solution or shift, and never represent the structure as an observation. It is a method structure asset, not a new required stage 4 gate kind; wiring it into the `SignaturePackage` bridge or a required kind remains a bounded follow-up and a methodology-owner decision.
- Product Matrix and perfect product (the seven business models, group consulting, pricing on outcomes not time and materials, the six-to-twelve week program, one module per signature step, Monday training and Thursday coaching) — canon 11, 12 — stage 5 — status: implemented 2026-10-03 (Ralph cycle 126) as the pure Commercial Design `ProductProgram` (`ProductMatrixModel`, `ProgramPricingBasis`, `ProgramCadence`, `ProductModule`), which chooses one of the canon's seven business models, binds a named owner and the same-tenant stage 4 `SignatureSolution`, requires outcome-and-value pricing (refusing time and materials), a six-to-twelve week duration on the Monday training and Thursday coaching cadence, and one module per method step with an outcome and a deliverable, refuses an untyped model, basis or cadence, a foreign or absent method, a duplicate module, two modules for one step, a module for a step the method does not name, more weekly modules than weeks and a cross-tenant method or module, reports the covered and missing steps and is never an observation. This asset is inside stage 5, not a new stage; SPEC.md section 12.5 did not seed it, so it is recorded here as a newly identified gap because the stage 5 `DeliverySpecification` left the delivery model and pricing as free text. Wiring it into a required stage 5 gate kind remains a bounded follow-up and a methodology-owner decision, and any spend or client commitment stays a human decision.
- Umbrella planning (Online Business Launch Map, Bulletproof Business Plan) — canon 00, 01 — over stages 0 to 10 — status: implemented 2026-10-03 (Ralph cycle 116) as the new Portfolio `UmbrellaPlan` (`LaunchMapSection`, `UmbrellaSection`, `BusinessTarget`, `QuarterlyReview`), which binds a named owner, a same-tenant `ClientWorkspace` and a versioned `StageTemplate` to exactly the canon's four launch-map sections (Foundation, Signature Solution, Funnel, Floodgates) covering every template stage exactly once, requires at least one specific measurable business target and an ordered 90-day revisit history, and has `UmbrellaReviewPolicy.require_current` refuse an overdue plan. Mapping the canon's four strategy parts onto stages 0-2/3-5/6-9/10 is a documented intentional deviation from the canon's 12-week calendar. Wiring the plan into the production view or a required gate kind remains a bounded follow-up and a methodology-owner decision.
- Swimlanes channel model — canon 13, 14, 33, 34 — cross-cutting stages 8 to 10 — status: implemented 2026-10-03 (Ralph cycle 117) as the pure Execution `SwimlanesPlan` (`SwimlaneChannel`, `SwimlaneMove`), which types the canon's five channels (messages, ads, human outreach, offline and direct mail, content), maps each stalled funnel step to a distinct next step with a vehicle and one action, grounds on a same-tenant stage 8 `FunnelIntegration`, binds a named owner and reports the channels it covers and misses, and has `SwimlaneCoveragePolicy.require_all_channels` refuse a single-source plan (canon file 34: "you can't be single source dependent"). It lives in Execution because Commercial cannot import the Execution `FunnelIntegration` without a production-commercial-execution import cycle. Wiring it into the production view, the command center or a stage 8/10 kind remains a bounded follow-up and a methodology-owner decision, so it stays a planning asset rather than a required gate kind.
- Audience sizing and market research (Facebook Audience Insights, LinkedIn search; "one source and audience size"; specific experts/authors/books/tools/publications/associations as interest signals) — canon 02, 03 — stage 1 — status: implemented 2026-10-03 (Ralph cycle 127) as the pure Commercial Design `AudienceReachEstimate` (`AudienceDefinition`, `InterestSignal`, `ResearchPlatform`, `InterestKind`) with the caller-invoked `MarketReachPolicy`, which records the platform, the audience location, age, gender and at least one typed specific interest signal, a positive integer estimated reach, a source note and capture date, binds a named owner, refuses blank or untyped or duplicate content, reports `is_litmus_test`/`is_plan` and is never an observation; `MarketReachPolicy.require_reachable` refuses a market below the caller's minimum viable audience and `require_multiplatform` refuses a single-network litmus or a confirmation spanning more than one client with the named `MarketReachBoundaryError` (hardened in Ralph cycle 128), so the canon's Market gate that "the market is big enough, reachable" now has a typed research input with a tenant boundary. SPEC.md section 12.5 did not seed this asset, so it is recorded here as a newly identified gap; it is an asset inside stage 1, not a new stage. Wiring it into the `TargetMarketCandidate`, the stage 1 `DiagnosisPackage` or a required stage 1 gate kind remains a bounded follow-up and a methodology-owner decision. Google keyword research is named at the end of canon file 02 but its session is absent from the supplied canon, so it is recorded as a gap.
- Missing canon files 19 and 20; promised sales/enrollment and email/follow-up modules absent — status: unresolved, request from license owner.
- Service and partnership lines (kickoff checklist, module production standard, session guide, client scorecard, case study template; renewal and win-back, next-offer path, referral and partner plan, community rules, reputation track) — canon internal/service-ops and internal/stations docs — after stage 10 (service delivery and portfolio expansion) — status: identified gap 2026-10-03 (Ralph cycle 130; canon stations and method map updated 2026-10-03). The canon map now has nine stations (Plan, Market, Message, Offer, Funnel, Traffic, Content, Retargeting, Enroll) whose build line is a 12-week program, and the third phase's motions are Extract, Content, Expand; Serve is the client's own delivery and Grow splits the foundation offer into smaller offers that raise customer lifetime value. The back half of the client life is still thin, so RED defines the service line (deliver one module a week, teach one day and coach another, track attendance and results, collect a case study when results land) and the partnership line (retain, grow, refer, renew, reputation). SPEC.md section 1 puts "portfolio expansion" in the product contract and section 3 names the Portfolio context (opportunity and roadmap), but no stage 0-10 asset or required gate kind represents delivery progress, the case study as sourced proof, or the renewal, referral and reputation clocks. These are candidate pipeline additions that need a named-owner decision (adding or renaming a stage is not an agent decision); the case study is also constrained by SPEC.md section 1 (no unreviewed testimonials or performance claims) and section 4 (client-approved, version-scoped claims). Any publish, send, spend or client commitment remains a human decision.
- Extract (pull key ideas from the signature solution: FAQs, problems, process, reviews and praise; group themes around the one currency; build an email and social content plan) — n/a, our layer (feeds 25-28) — service layer ahead of stage 10 content operations, a stage 6/10 asset — status: identified gap 2026-10-03 (canon stations and method map updated). The canon's third phase starts with Extract, which turns the signature solution into a content plan before the Content motion makes posts and emails; no stage 0-10 asset represents this plan. The bounded slice is a pure-domain `ContentPlan` grounded on the same-tenant stage 4 `SignatureSolution`, grouping themes around the stage 2 currency and binding a named owner. Not a new stage; any publish stays a human decision.
- Serve and Grow (Serve is the client's own delivery of the offer; Grow splits the foundation offer into smaller offers that are new entry points and raise customer lifetime value, expanding the RED Portfolio) — canon 11, 12 — after stage 10, Portfolio context — status: identified gap 2026-10-03 (canon stations and method map updated). SPEC.md section 1 puts portfolio expansion in the product contract and section 3 names the Portfolio context, but no stage 0-10 asset represents the smaller offers as entry points or the lifetime value they raise. A candidate pipeline addition needing a named-owner decision; any client commitment stays a human decision.

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
4. Implement SourceRecord, Claim, approval, decision, BuildObject, StageRun and GateDecision aggregates. [DONE 2026-10-02: Governance `StageGate` + `GateIntegrityPolicy` — missing exact asset version, unapproved dependency, self-approval, and waiver-without-asset all block gate approval; verified by `tests/unit/governance/test_gate_integrity.py`. DONE 2026-10-02 (Ralph cycle 2): version-specific `ApprovalRequest` (exact version + scope, designated approver, expiry) and append-only `Decision` / `DecisionLog`; verified by `tests/unit/governance/test_approval_record.py`. DONE 2026-10-02 (Ralph cycle 3): `StageRun` completes only via an accepted gate for the same stage, never via activity, with `StageStatus` / `StageTransition` and a `StageTransitionPolicy` that rejects illegal transitions; verified by `tests/unit/governance/test_stage_run.py`. DONE 2026-10-02 (Ralph cycle 4): `BuildObject` in the Production context requires an owner and next action while active and rejects illegal lifecycle transitions; verified by `tests/unit/production/test_build_object.py`. DONE 2026-10-02 (Ralph cycle 5): versioned stage 0–10 `StageTemplate` seeded in Governance and `GateIntegrityPolicy` rejects gates that omit a canonical prerequisite, under-declare required asset kinds, or pin a different template version; verified by `tests/unit/governance/test_stage_template.py`. DONE 2026-10-02 (Ralph cycle 6): `StageGate.from_template` derives dependencies, template version and required asset kinds from the canonical template so gate evidence is not self-declared; verified by `tests/unit/governance/test_gate_factory.py`. DONE 2026-10-02 (Ralph cycle 7): immutable `GateDecision` / `GateDisposition` records the stage, pinned required asset versions, checkpoint evidence, reviewer, scope, disposition, rationale and next action, and `GateDecision.from_gate` refuses an approval for a non-approvable gate; verified by `tests/unit/governance/test_gate_decision.py`. DONE 2026-10-02 (Ralph cycle 8): `StageRun.complete` now requires a passing, same-stage, same-template-version `GateDecision` and pins it as immutable `accepted_decision`, replacing the transient `StageGate`; verified by `tests/unit/governance/test_stage_run.py`. DONE 2026-10-02 (Ralph cycle 9): `GateLedger` derives prerequisite state from durable `GateDecision`s and refuses a passing decision while a prerequisite stage lacks a passing decision, so the dependency map is no longer caller-supplied; verified by `tests/unit/governance/test_gate_ledger.py`. DONE 2026-10-02 (Ralph cycle 10): `GateDecision.from_gate` now requires a `GateLedger` and reads prerequisite state and the canonical template only from the ledger, removing the caller-supplied `dependency_states` map from the decision boundary; verified by `tests/unit/governance/test_gate_decision.py` and `test_gate_ledger.py`. DONE 2026-10-02 (Ralph cycle 11): Knowledge `SourceRecord` (frozen original: locator, checksum, capture time, access rule; `cite` returns a checksum-pinned citation) and `Claim` (statement, `Known`/`Derived`/`Proposed`/`Unknown`, citations, confidence note) with `reclassify` records an audited `ClaimRevision`, refuses `Known` without a direct citation, and preserves the original so Derived/Proposed never silently become Known; verified by `tests/unit/knowledge/test_source_record.py` and `test_claim.py`. DONE 2026-10-02 (Ralph cycle 12): Method `SemanticVersion` / `MethodVersion` / `MethodApproval` pin an exact semantic version and intended use, revisions must advance the version and drop the old approval, and `MethodChangeImpactPolicy` emits an owned review queue (offer, brief, asset, journey, claim with human owner and due date) for a change to an approved method, rejecting unapproved or non-advancing or cross-tenant changes; verified by `tests/unit/method/test_method_version.py` and `test_method_impact.py`. DONE 2026-10-02 (Ralph cycle 13): Commercial Design `MethodReference` / `OfferVersion` records audience, promise, eligibility, price hypothesis and at least one exact method reference, and `OfferReadinessPolicy` refuses production readiness unless every reference is an approved `MethodVersion` of the same tenant at the exact version and intended use; `mark_review_required` drops readiness after an upstream change and a terminal offer cannot be revived; verified by `tests/unit/commercial/test_offer_version.py`. DONE 2026-10-02 (Ralph cycle 15): `GateLedger.record` refuses a passing `GateDecision` whose pinned asset kinds do not exactly match the canonical `StageTemplate` required package for the stage (under-declared or substituted), closing the durable boundary previously checked only at the `from_gate` factory; ledger fixtures now use canonical kinds; verified by `tests/unit/governance/test_gate_ledger.py`. DONE 2026-10-02 (Ralph cycle 16): `GateIntegrityPolicy._template_reasons` now applies the same exact asset-package rule as the durable ledger, rejecting a gate that declares a non-canonical extra asset kind as well as one that omits a canonical kind, so `GateDecision.from_gate` can no longer produce a passing decision the `GateLedger` must refuse and gate evaluation and durable recording are consistent; verified by `tests/unit/governance/test_stage_template.py`. DONE 2026-10-02 (Ralph cycle 18): `GateDecision` now persists the assigned work owner and due date for every stage and rejects a decision that omits either, closing the SPEC.md section 4 gate-record gap where the production view must answer who is accountable and when the next approval is due; verified by `tests/unit/governance/test_gate_decision.py` (with `from_gate` factory passthrough). DONE 2026-10-02 (Ralph cycle 20): `StageGate` and `GateDecision` now pin the canonical checkpoint rubric derived from `StageDefinition.checkpoint`, and `GateLedger` and `GateIntegrityPolicy` reject a passing gate or decision whose checkpoint differs from the template, closing the last SPEC.md section 4 gate-record field; verified by `tests/unit/governance/test_gate_checkpoint.py`. DONE 2026-10-02 (Ralph cycle 32): a passing `GateDecision` and an approvable `StageGate` must pin exactly one exact version per required asset kind; an ambiguous multi-version package (for example two versions of `authority-amplifier-script`) is refused by `GateDecision.__post_init__`, `GateIntegrityPolicy.evaluate` and `GateLedger.record` via the new `duplicate_asset_kinds` helper and `AmbiguousAssetPackageError`, so the exact asset pin required by SPEC.md sections 3 and 4 cannot be defeated by a package that identifies no single approved version; verified by `tests/unit/governance/test_gate_asset_exactness.py`. DONE 2026-10-02 (Ralph cycle 34): a passing `GateDecision` now pins the durable per-asset `ApprovalRequest`s and refuses construction unless every pinned asset version is covered by an approved, in-scope, unexpired request, so a self-declared approved asset set can no longer pass a gate and a stage cannot complete without a recorded per-asset approval; `GateDecision.from_gate` takes the approvals and `UnapprovedAssetError` names the uncovered versions; verified by `tests/unit/governance/test_asset_approval.py` and the updated governance fixtures. DONE 2026-10-02 (Ralph cycle 35): `StageGate.approved_assets` is now a derived, read-only set evidenced by recorded version-specific `ApprovalRequest`s (`record_asset_approval` refuses an approval outside the pinned package and another version does not evidence the asset), so `GateIntegrityPolicy` evaluates the same recorded evidence a passing `GateDecision` pins and the self-managed field cannot be assigned; verified by `tests/unit/governance/test_gate_asset_evidence.py`. DONE 2026-10-02 (Ralph cycle 36): `GateDecision.from_gate` records the gate's own `asset_approvals` and no longer accepts a caller-supplied approval set, so a passing decision can only pin the evidence the gate recorded and the policy evaluated; the decision validates that evidence against its own scope and date and refuses a gate whose recorded approvals do not cover the decision scope; verified by `tests/unit/governance/test_gate_asset_evidence.py` with updated fixtures in `test_asset_approval.py`, `test_gate_decision.py`, `test_gate_ledger.py` and `test_gate_checkpoint.py`. DONE 2026-10-02 (Ralph cycle 37): `StageGate.approved_assets`/`missing_assets`/`authorizes_downstream` and `GateIntegrityPolicy.evaluate` now require an explicit evaluation instant and treat an approval already expired at that instant as not evidencing its asset, so the gate and the policy agree with the durable `GateDecision`'s expiry check; verified by `tests/unit/governance/test_gate_asset_evidence.py` (`GateApprovalExpiryTests`). DONE 2026-10-02 (Ralph cycle 38): `StageGate.approved_assets`/`missing_assets`/`authorizes_downstream` and `GateIntegrityPolicy.evaluate` now take the intended downstream scope and derive evidenced assets through `ApprovalRequest.authorizes`, and `GateDecision.from_gate` threads its scope into the policy and gate, so the gate, policy and durable decision agree on version, scope and expiry; verified by `tests/unit/governance/test_gate_asset_evidence.py` (`GateApprovalScopeTests`). DONE 2026-10-02 (Ralph cycle 39): `GateDecision` exposes `unapproved_assets_at(on)`/`authorizes_downstream_at(on)`, `GateLedger.has_passing_decision`/`dependency_states` take a required `on` instant and report a passing prerequisite whose pinned approvals have expired as `BLOCKED`, and `GateLedger.record`/`GateDecision.from_gate` plus `PipelineProgress.from_ledger` evaluate at that instant, so "a failed or expired prerequisite blocks dependent authorization until resolved" holds across the dependency graph; verified by `tests/unit/governance/test_gate_prerequisite_expiry.py`. DONE 2026-10-02 (Ralph cycle 41): `GateLedger.has_passing_decision(stage, on=...)` and `dependency_states` now traverse the template's prerequisite chain transitively, so a stage whose own approvals are current is not reported passing while any upstream stage has lapsed; `dependency_states` reports every stage behind an expired chain as `BLOCKED` and `PipelineProgress.from_ledger` stops counting those gates, closing the transitive half of the SPEC.md section 4 rule; verified by `tests/unit/governance/test_gate_prerequisite_expiry.py` (`GateLedgerTransitivePrerequisiteExpiryTests`). DONE 2026-10-02 (Ralph cycle 43): `StageRun.complete` now requires the accepted `GateDecision` to be the stage's current durable `GateLedger` decision (by identity) before transitioning, so a transient passing decision the ledger never recorded, or an earlier pass later superseded by a durable non-passing entry, can no longer complete a stage; verified by `tests/unit/governance/test_stage_run.py` (`StageCompletionDurabilityTests`). DONE 2026-10-02 (Ralph cycle 44): `Waiver` requires a non-empty set of `downstream_effects` of non-blank identifiers, so a waivered `GateDecision` records the concrete downstream stages/assets/journeys it affects rather than acting as a blanket bypass; verified by `tests/unit/governance/test_gate_decision.py` (`WaiverScopeTests`). DONE 2026-10-02 (Ralph cycle 45): `GateDecision.__post_init__` now requires a waived decision to name a non-blank intended downstream `scope` and refuses any `Waiver.downstream_effects` outside that scope, so a waiver cannot claim an impact surface broader than the gate it decided; verified by `tests/unit/governance/test_gate_decision.py` (`WaiverDecisionScopeTests`). DONE 2026-10-02 (Ralph cycle 46): `GateDecision.from_gate` now requires a waived disposition to name the gate's designated approver as its reviewer, refuses a waiver recorded by any other actor, refuses a gate with no designated approver, and refuses the gate's author waiving their own gate, so a waiver is a real human authority decision rather than a self-issued bypass of a missing asset; verified by `tests/unit/governance/test_gate_decision.py` (`WaiverAuthorityTests`). DONE 2026-10-02 (Ralph cycle 47): `GateDecision.__post_init__` now requires every disposition — not only a passing one — to pin a non-empty required asset package with exactly one exact version per kind, so a BLOCKED, CHANGES_REQUIRED, WAIVED or SUPERSEDED decision cannot hide the exact versions at issue behind its disposition; verified by `tests/unit/governance/test_gate_asset_exactness.py` (`GateDecisionAssetPackageRequiredTests`). DONE 2026-10-02 (Ralph cycle 48): `GateLedger.record` enforces the canonical required asset kinds and canonical checkpoint for every `GateDecision` disposition, so a BLOCKED, CHANGES_REQUIRED, WAIVED or SUPERSEDED decision cannot contradict the template the production view derives requirements from; verified by `tests/unit/governance/test_gate_ledger_canonical_package.py`. DONE 2026-10-02 (Ralph cycle 53): `GateDecision.__post_init__` now refuses to record a `WAIVED` decision whose scoped `Waiver` is already expired at `decided_on`, so the durable record and the `StageRun` mirror agree that a lapsed risk acceptance is never a current disposition and the production view cannot read an expired waiver as live; verified by `tests/unit/governance/test_gate_decision.py` (`WaiverExpiryDecisionTests`). DONE 2026-10-03 (Ralph cycle 2026-10-03T144637Z): the Governance `StageRun` is now durable behind the tenant-scoped `StageRunRepository` port (in-memory and PostgreSQL adapters, migration `0002_stage_runs`, `stage_run_to_payload`/`from_payload`, `CrossTenantStageRunError`), and the stage 0 route loads-or-creates and upserts the run so a stage's assigned owner, status, entered/exited timestamps, pinned decision and transition log survive a restart; verified by `tests/unit/governance/test_stage_run_repository.py` and `PostgresStageRunRepositoryTests`. Remaining: SourceRecord, Claim, MethodVersion and OfferVersion repository adapters remain blocked on the storage ADR.]
5. Implement stages 0 and 1 from intake to approved avatar and diagnosis. [DONE 2026-10-02 (Ralph cycle 54): Commercial Design `AvatarProfile` is a frozen reject-only value object requiring the stage 1 avatar's demographics, psychographics, pains, goals, consequences of inaction, awareness, customer evidence and voice notes, so the "Avatar Locked" checkpoint ("a stranger can recognize who the customer is, what matters, and why now") is met by a real asset; `AvatarLockedPolicy.require_locked` refuses to lock an avatar whose customer evidence is not a same-tenant, known, directly sourced Knowledge claim; verified by `tests/unit/commercial/test_avatar_profile.py`. DONE 2026-10-02 (Ralph cycle 55): Commercial Design `BusinessSnapshot` and `OfferFunnelAudit` are frozen reject-only value objects requiring the stage 1 diagnosis current-state and audit packages (business model, current offers, lead sources, constraints, narrative; offer findings, funnel steps, conversion evidence, gaps, narrative) and recording the Knowledge claim ids that evidence them, and `DiagnosisEvidencePolicy` refuses to evidence either asset with an unsourced, derived, proposed, foreign or absent claim, so all three stage 1 asset kinds are now real, source-checked values; the shared `sourced_claim_ids` helper also backs `AvatarLockedPolicy`; verified by `tests/unit/commercial/test_diagnosis_assets.py`. DONE 2026-10-02 (Ralph cycle 56): Engagement `ClientWorkspace` is the stage 0 tenant root named in the SPEC.md section 3 aggregate table, requiring an opaque id, tenant and duplicate-free named-authority registry and enforcing "every child resource belongs to exactly one client" by refusing a blank child, a duplicate attachment and a foreign-tenant child; it records the engagement lifecycle from SPEC.md section 4 with a forward-only canonical progression, pause/resume and terminal Completed, recording actor, reason, timestamp, old/new state and correlation id; DONE 2026-10-02 (Ralph cycle 57): Engagement `IntakeAssetKind`, `IntakeAsset` and `IntakePackage` are frozen reject-only values for the full stage 0 "Intake" package, the kind list provably matches the canonical stage 0 template, a package rejects a duplicate kind and a foreign-tenant asset and reports its missing kinds, and `ProductionReadyPolicy` refuses an incomplete package, an asset owner who is not a designated workspace authority, and evidence that is not a known, directly sourced, same-tenant claim; the `sourced_claim_ids` rule moved to `knowledge/domain/policies.py` and is now shared with commercial; verified by `tests/unit/engagement/test_intake_package.py`. DONE 2026-10-02 (Ralph cycle 58): Governance `StageAssetVersion` represents a real stage asset at one exact version (unique id, owning tenant, canonical kind, positive version) and `pin(tenant_id=...)` maps it to an `AssetVersionRef(keyed by kind)` while refusing a version-less asset (`VersionlessAssetError`) and a cross-tenant asset (`CrossTenantAssetError`), and the pinned refs build a canonical `StageGate.from_template` package; verified by `tests/unit/governance/test_asset_version_pin.py`. DONE 2026-10-02 (Ralph cycle 59): Governance `StageGate.from_assets(template, stage_number, *, tenant_id, assets)` assembles a stage's canonical gate from real `StageAssetVersion`s, pinning each for the workspace tenant so a cross-tenant asset (`CrossTenantAssetError`), a second version of one kind (`AmbiguousAssetPackageError`), a missing or extra canonical kind (`AssetPackageMismatchError`) and an unknown stage (`UnknownStageError`) are all refused instead of silently pinned; verified by `tests/unit/governance/test_stage_asset_package.py`. The new finding is that the Engagement stage 0 `IntakeAsset` still carries no typed exact version, so a complete package cannot yet yield the assets `from_assets` pins; that bridge is the highest priority ready next item. DONE 2026-10-02 (Ralph cycle 59): Engagement stage 0 `IntakeAsset` now carries a typed positive integer `version` (rejecting a versionless or non-positive asset) and a `canonical_kind` equal to the governance template asset kind, and `IntakePackage.stage_asset_versions()` projects the package's real assets onto governance `StageAssetVersion`s; a complete twelve-kind package assembles the canonical stage 0 gate via `StageGate.from_assets` and a partial package is refused by `AssetPackageMismatchError`; verified by `tests/unit/engagement/test_intake_package.py`. DONE 2026-10-02 (Ralph cycle 61): Engagement `GateApproverAuthorityPolicy.require(gate, workspace)` refuses a stage gate whose designated approver is absent or is not a named authority on the `ClientWorkspace`, raising `GateApproverNotAuthorizedError`, so a stage gate (including stage 0 "Production Ready") can only be approved by a client-designated human; it checks against the gate's own workspace and never invents a concrete approver identity or authority role; verified by `tests/unit/engagement/test_gate_approver_authority.py`. DONE 2026-10-02 (Ralph cycle 62): Engagement `StageZeroGateAssembler` composes `ProductionReadyPolicy`, `StageGate.from_assets` and `GateApproverAuthorityPolicy` so a stage 0 gate is handed downstream only when the intake package is complete, every asset owner is a named workspace authority, every asset is evidenced by a same-tenant directly sourced claim, the gate pins the template's exact twelve asset versions, and the designated approver is a named workspace authority; verified by `tests/unit/engagement/test_stage_zero_gate_assembly.py`. DONE 2026-10-02 (Ralph cycle 63): Engagement `StageZeroGateRecorder.record` closes the stage 0 "Production Ready" checkpoint end to end in pure domain: it takes the `StageZeroGateAssembler` output, issues and approves one exact-version `ApprovalRequest` per required asset (twelve) through the workspace's designated approver, refuses a gate for another stage (`NotStageZeroGateError`), a gate with no author (`GateAuthorRequiredError`), an absent or non-authority approver (`GateApproverNotAuthorizedError`) and a self-approving author (`SelfApprovalError`), records the immutable passing `GateDecision` in a `GateLedger`, and lets `PipelineProgress` report one approved gate; an under-declared asset package is still refused by `GateDecision.from_gate`/the ledger; verified by `tests/unit/engagement/test_stage_zero_gate_recording.py`. DONE 2026-10-02 (Ralph cycle 64): Engagement's first application use case `RecordStageZeroGateHandler` (with typed `RecordStageZeroGateCommand`) composes `StageZeroGateAssembler` and `StageZeroGateRecorder` so the canonical stage 0 "Production Ready" gate is built from the real `IntakePackage` at the application boundary; a caller cannot hand the recorder a hand-built gate, so `ProductionReadyPolicy` owner-authority and sourced-evidence checks cannot be bypassed, and the use case records a passing exact-version decision for all twelve assets (or lands nothing when a package, owner, evidence source or approver is invalid); verified by `tests/unit/engagement/test_record_stage_zero_gate.py`. DONE 2026-10-02 (Ralph cycle 65): the same `RecordStageZeroGateHandler` now closes the stage 0 `StageRun` from the durable ledger decision in one atomic application operation, so a passing `GateDecision` can no longer be written while the stage stays open and `PipelineProgress` (approved gates) and stage status agree; `RecordStageZeroGateCommand` carries the stage 0 `StageRun` and a correlation id, a run for another stage or template version is refused (`StageRunNotStageZeroError`), and a Not Started/Changes Required/Blocked/Waived/Complete/Superseded run is refused before any decision is written (`StageRunNotCompletableError`); verified by `tests/unit/engagement/test_record_stage_zero_gate.py`. The stage 1 gate wiring and the stage 1 nine-kind/three-asset representation mismatch remain, the latter the top named-owner blocker. DONE 2026-10-03 (Ralph cycle 69): the nine-kind/three-asset mismatch is resolved by a pure Commercial `DiagnosisPackage` that projects the three reviewed stage 1 values onto the nine canonical kinds as exact `StageAssetVersion` evidence, so the projected assets assemble a canonical stage 1 gate via `StageGate.from_assets`; verified by `tests/unit/commercial/test_diagnosis_package.py`. Stage 1 gate wiring is now the top ready next item. DONE 2026-10-03 (Ralph cycle 70): the stage 1 "Avatar Locked" gate is wired end to end with Engagement `StageOneGateAssembler` (validates the `DiagnosisPackage` with `AvatarLockedPolicy` and `DiagnosisEvidencePolicy`, pins the canonical gate via `StageGate.from_assets`, binds the approver to the workspace), `StageOneGateRecorder` (one approved exact-version request per kind and the durable passing `GateDecision`, refusing a foreign stage, absent author, unauthorized approver or unaccountable owner), `RecordStageOneGateCommand` and `RecordStageOneGateHandler` (closes the stage 1 `StageRun` from the durable decision, refusing a run for another stage or version and a not-completable run; governance refuses the pass until stage 0 has passed); verified by `tests/unit/engagement/test_record_stage_one_gate.py` (26 tests). Stage 1 can now close, so stage 2 "Currency Locked" is unblocked.]
6. Implement stages 2 and 3 from primary currency to observable Profit Pyramid. [DONE 2026-10-02 (Ralph cycle 17): Method `PrimaryCurrency` value object requires a specific audience, distinct current/desired measures, and a distinct mechanism, rejecting an unspecified person or unmeasured outcome, so the stage 2 "Currency Locked" checkpoint rule is met by a real domain value; verified by `tests/unit/method/test_primary_currency.py`. DONE 2026-10-02 (Ralph cycle 19): Method `ProfitPyramidLevel` and `DiagnosticModel` require each level's observable measures, symptoms, behaviors and problems and reject adjacent levels that cannot be told apart by an observable difference, so the stage 3 "Diagnostic Model Approved" checkpoint rule is met by a real domain value; verified by `tests/unit/method/test_diagnostic_model.py`. DONE 2026-10-02 (Ralph cycle 21): `MethodVersion` pins the exact tenant-checked stage 2 `PrimaryCurrency` and stage 3 `DiagnosticModel`, refuses approval without both pins, rejects a cross-tenant pin, and drops both pins on `revised`; verified by `tests/unit/method/test_method_dependencies.py`. DONE 2026-10-03 (Ralph cycle 71): Commercial `CurrencyInventory`, `PositioningDecision`, `MillionDollarMessage` and the `CurrencyPackage` bridge (canon 04, 05, 06) project the four reviewed stage 2 values onto the ten canonical stage 2 kinds as exact   `StageAssetVersion` evidence, refusing a blank identity, a versionless asset or a cross-tenant value, so the stage 2 "Currency Locked" gate can now be assembled; verified by `tests/unit/commercial/test_currency_package.py` (22 tests). DONE 2026-10-03 (Ralph cycle 72): Engagement `StageTwoGateAssembler`, `StageTwoGateRecorder`, `RecordStageTwoGateCommand` and `RecordStageTwoGateHandler` wire the stage 2 "Currency Locked" `GateDecision` end to end, binding the reviewed `CurrencyPackage` to the workspace tenant and authority registry, issuing one exact-version approval per required kind, writing the durable decision, and closing the stage 2 `StageRun`; stage 2 depends on stage 1, so the ledger must already hold a passing stage 1 decision; verified by `tests/unit/engagement/test_record_stage_two_gate.py` (22 tests). DONE 2026-10-03 (Ralph cycle 73): Commercial `DiagnosticPackage` bridge (canon 07, 08) completes the Method `DiagnosticModel` with the SPEC-required `visual` and `explanatory_copy` and projects the reviewed model onto the ten canonical stage 3 kinds as exact `StageAssetVersion` evidence, so the stage 3 "Diagnostic Model Approved" gate can now be assembled; verified by `tests/unit/commercial/test_diagnostic_package.py` (10 tests) plus two `DiagnosticModel` field tests. DONE 2026-10-03 (Ralph cycle 74): Engagement `StageThreeGateAssembler`, `StageThreeGateRecorder`, `RecordStageThreeGateCommand` and `RecordStageThreeGateHandler` wire the stage 3 "Diagnostic Model Approved" `GateDecision` end to end, binding the reviewed `DiagnosticPackage` to the workspace tenant and authority registry, issuing one exact-version approval per required kind, writing the durable decision, and closing the stage 3 `StageRun`; stage 3 depends on stage 2, so the ledger must already hold a passing stage 2 decision; verified by `tests/unit/engagement/test_record_stage_three_gate.py` (22 tests). DONE 2026-10-03 (Ralph cycle 75): Commercial `SignaturePackage` bridge (canon 09, 10) projects the reviewed Method `SignatureSolution` onto the twelve canonical stage 4 kinds as exact `StageAssetVersion` evidence, so the stage 4 "IP Architecture Locked" gate can now be assembled; verified by `tests/unit/commercial/test_signature_package.py` (10 tests). The stage 4 `GateDecision` wiring remains.]
7. Implement stages 4 and 5 from grounded Signature Solution to offer approval. [DONE 2026-10-02 (Ralph cycle 14): commercial `OfferVersion` requires an accountable owner and `OfferChangeImpactPolicy` discovers dependent offers from an approved method change and marks them review required, so the SPEC.md section 11 "changing a method version identifies dependents" acceptance test is met by a real aggregate; verified by `tests/unit/commercial/test_offer_change_impact.py`. DONE 2026-10-02 (Ralph cycle 22): Method `SignatureStep`, `TransformationPhase` and frozen `SignatureSolution` require exactly three phases and nine steps, a process inventory, transformation map, narrative and visual, one continuous chain of named stages, and declared starting/final states that are the ends of that chain, so the stage 4 "IP Architecture Locked" checkpoint rule is met by a real domain value; verified by `tests/unit/method/test_signature_solution.py`. DONE 2026-10-02 (Ralph cycle 23): `MethodVersion` pins the exact tenant-checked stage 4 `SignatureSolution`, refuses approval without it, rejects a cross-tenant pin, and drops the pin on `revised`, so an approved method must carry its locked stage 4 structure; verified by `tests/unit/method/test_method_dependencies.py`. DONE 2026-10-02 (Ralph cycle 24): commercial `StepDelivery` and `DeliverySpecification` require every locked stage 4 method step to carry an action, actor, deliverable, timing and measure, record the full stage 5 asset package, and reject a missing or extra method step, a duplicate delivery, a foreign-tenant method or step delivery, and any missing package field, so the stage 5 "Offer Locked" checkpoint rule is met by a real value; verified by `tests/unit/commercial/test_delivery_specification.py`. DONE 2026-10-02 (Ralph cycle 25): `OfferVersion` pins the tenant-checked stage 5 `DeliverySpecification`, refuses production readiness without it, and `revised` drops the delivery specification and readiness (including when the method reference changes) so an approved offer must carry a complete stage 5 delivery package; verified by `tests/unit/commercial/test_offer_version.py` with a shared fixture in `tests/unit/commercial/fixtures.py`. DONE 2026-10-02 (Ralph cycle 26): `OfferReadinessPolicy` refuses production readiness when the stage 5 `DeliverySpecification.signature_solution` is not equal to the `SignatureSolution` pinned by an approved method reference, so a stage 5 package cannot describe a different transformation than the approved stage 4 method; verified by `tests/unit/commercial/test_offer_version.py`. DONE 2026-10-03 (Ralph cycle 76): Engagement `StageFourGateAssembler`, `StageFourGateRecorder`, `RecordStageFourGateCommand` and `RecordStageFourGateHandler` wire the stage 4 "IP Architecture Locked" `GateDecision` end to end, binding the reviewed `SignaturePackage` to the workspace tenant and authority registry, issuing one exact-version approval per required kind, writing the durable decision, and closing the stage 4 `StageRun`; stage 4 depends on stage 3, so the ledger must already hold a passing stage 3 decision; verified by `tests/unit/engagement/test_record_stage_four_gate.py` (22 tests). DONE 2026-10-03 (Ralph cycle 77): the Commercial `OfferPackage` bridge (canon 11, 12) projects the reviewed stage 5 `DeliverySpecification` onto the twelve canonical kinds as exact `StageAssetVersion` evidence; verified by `tests/unit/commercial/test_offer_package.py` (10 tests). DONE 2026-10-03 (Ralph cycle 78): Engagement `StageFiveGateAssembler`, `StageFiveGateRecorder`, `RecordStageFiveGateCommand` and `RecordStageFiveGateHandler` wire the stage 5 "Offer Locked" `GateDecision` end to end, binding the reviewed `OfferPackage` to the workspace tenant and authority registry, issuing one exact-version approval per required kind, writing the durable decision, and closing the stage 5 `StageRun`; stage 5 depends on stage 4, so the ledger must already hold a passing stage 4 decision; verified by `tests/unit/engagement/test_record_stage_five_gate.py` (22 tests). The stage 6 reviewed-asset bridge remains.]
8. Implement stages 6 and 7 with message congruence and script approval before creative production. [DONE 2026-10-02 (Ralph cycle 27): commercial `CampaignMessage` records the stage 6 asset package, requires each message field, and rejects a cross-tenant offer at construction; `CampaignMessageAlignmentPolicy` refuses the "Campaign Message Approved" checkpoint unless the message is grounded on a production ready stage 5 offer and its avatar, promise, product, method, currency and problem agree with the offer and the approved method's locked stage 2 primary currency and stage 3 diagnostic model, so Phase 4's "campaign message conflicting with the offer blocks approval" example is met by a real aggregate; verified by `tests/unit/commercial/test_campaign_message.py`. DONE 2026-10-02 (Ralph cycle 28): Production `AuthorityAmplifier` records the canonical Promise, Proof, Problems, Steps, Context, Action script and the full stage 7 visual/video package, requires at least one proof claim, and rejects a cross-tenant stage 6 message at construction; `AuthorityAmplifierPolicy` refuses script approval unless the message is approved and the method is an approved dependency, and flags proof claims not backed by a known, directly sourced Knowledge claim; visual production and creative acceptance both refuse before script approval and creative acceptance also requires the complete visual package, so Phase 4's "visual Authority Amplifier production cannot be authorized by an unapproved script" and "unsupported proof is flagged" examples are met by a real aggregate; verified by `tests/unit/production/test_authority_amplifier.py`. Stage 7 wiring into a governance `GateDecision` remains, blocked on the asset-version representation decision.] DONE 2026-10-03 (Ralph cycle 79): built the Commercial `CampaignMessagePackage` bridge (canon-informed, SPEC.md section 12.3 stage 6 files 06, 15, 24, 25-28) projecting the reviewed stage 6 `CampaignMessage` onto the twelve canonical stage 6 kinds as exact `StageAssetVersion` evidence; verified by `tests/unit/commercial/test_campaign_message_package.py` (10 tests), so the stage 6 gate is now assembleable. DONE 2026-10-03 (Ralph cycle 80): wired the stage 6 "Campaign Message Approved" `GateDecision` end to end with `StageSixGateAssembler`, `StageSixGateRecorder`, `RecordStageSixGateCommand` and `RecordStageSixGateHandler`, plus named errors `NotStageSixGateError`, `StageRunNotStageSixError` and `CampaignMessageNotApprovedError`, refusing an unapproved message so the congruence checkpoint cannot be bypassed, binding the reviewed `CampaignMessagePackage` to the workspace tenant and authority registry and closing the stage 6 `StageRun` from the durable decision; verified by `tests/unit/engagement/test_record_stage_six_gate.py` (24 tests), so stage 6 can now close. DONE 2026-10-03 (Ralph cycle 81): built the Production `AuthorityAmplifierPackage` bridge (canon-informed, SPEC.md section 12.3 stage 7 files 13-18, 28) projecting the reviewed stage 7 `AuthorityAmplifier` onto the nine canonical stage 7 kinds as exact `StageAssetVersion` evidence and refusing an amplifier without its visual package, so the stage 7 gate is now assembleable; verified by `tests/unit/production/test_authority_amplifier_package.py` (12 tests). DONE 2026-10-03 (Ralph cycle 82): wired the stage 7 "Authority Amplifier Approved" `GateDecision` end to end with `StageSevenGateAssembler`, `StageSevenGateRecorder`, `RecordStageSevenGateCommand` and `RecordStageSevenGateHandler`, plus named errors `NotStageSevenGateError`, `StageRunNotStageSevenError` and `AuthorityAmplifierNotApprovedError`, refusing an amplifier without final creative acceptance (the second of the two stage 7 approvals) so the checkpoint cannot be bypassed, binding the reviewed `AuthorityAmplifierPackage` to the workspace tenant and authority registry and closing the stage 7 `StageRun` from the durable decision; verified by `tests/unit/engagement/test_record_stage_seven_gate.py` (24 tests), so stage 7 can now close and stage 8 is unblocked pending its reviewed-asset bridge.
9. Implement stages 8 and 9 with complete prospect path and three part QA. [DONE 2026-10-02 (Ralph cycle 29): Execution `FunnelIntegration` records the complete stage 8 asset package, is grounded on the approved stage 7 `AuthorityAmplifier`, and rejects a cross-tenant amplifier at construction; `FunnelCompletionPolicy` refuses "Funnel Complete" unless the amplifier has creative acceptance and a same-tenant `ProspectPathDryRun` routed every capture, engagement and conversion handoff exactly once with a reliable record and named owner, so Phase 4's "failed prospect routing prevents Funnel Complete" example is met by a real aggregate; verified by `tests/unit/execution/test_funnel_integration.py`. DONE 2026-10-02 (Ralph cycle 30): Execution `LaunchQA` records the full stage 9 check set, requires an owner and a designated human authority distinct from the owner, is grounded on the completed stage 8 `FunnelIntegration`, and rejects a cross-tenant funnel at construction; `LaunchApprovedPolicy` refuses "Launch Approved" unless the funnel is complete, every canonical check is present, every critical-path check passed (payment and dashboard may be excepted with a named owner), and the designated authority authorizes traffic, and `TrafficAuthorization` reports readiness rather than live traffic, so Phase 4's "failed message, technical or commercial QA prevents Launch Approved" example is met by a real aggregate; verified by `tests/unit/execution/test_launch_qa.py`. Stage 8 and 9 wiring into a governance `GateDecision` remain, blocked on the asset-version representation decision. DONE 2026-10-03 (Ralph cycle 83): built the Execution `FunnelIntegrationPackage` bridge (canon-informed, SPEC.md section 12.3 stage 8 files 13, 14, 21, 22) projecting the reviewed stage 8 `FunnelIntegration` onto the thirteen canonical stage 8 kinds as exact `StageAssetVersion` evidence and refusing a funnel that has not passed Funnel Complete; verified by `tests/unit/execution/test_funnel_integration_package.py` (12 tests), so the stage 8 "Funnel Complete" gate is now assembleable and its `GateDecision` wiring is the next step. DONE 2026-10-03 (Ralph cycle 84): wired the stage 8 "Funnel Complete" `GateDecision` end to end with `StageEightGateAssembler`, `StageEightGateRecorder`, `RecordStageEightGateCommand` and `RecordStageEightGateHandler`, plus named errors `NotStageEightGateError` and `StageRunNotStageEightError` (canon-informed, SPEC.md section 12.3 stage 8 files 13, 14, 21, 22), binding the reviewed `FunnelIntegrationPackage` to the workspace tenant and authority registry, issuing one exact-version approval per canonical kind and closing the stage 8 `StageRun`; verified by `tests/unit/engagement/test_record_stage_eight_gate.py` (22 tests), so stage 8 can now close and stage 9 is unblocked pending its reviewed-asset bridge. DONE 2026-10-03 (Ralph cycle 85): built the Execution `LaunchQAPackage` bridge (canon-informed, SPEC.md section 12.3 stage 9 files 01, 08, 21, 22, 24) projecting the reviewed stage 9 `LaunchQA` onto the sixteen canonical stage 9 kinds as exact `StageAssetVersion` evidence, with a `CANONICAL_LAUNCH_KIND_CHECKS` map covering every `QACheckKind` exactly once and refusing a QA that has not passed Launch Approved; verified by `tests/unit/execution/test_launch_qa_package.py` (13 tests), so the stage 9 "Launch Approved" gate is now assembleable and its `GateDecision` wiring is the next step. DONE 2026-10-03 (Ralph cycle 86): wired the stage 9 "Launch Approved" `GateDecision` end to end with `StageNineGateAssembler`, `StageNineGateRecorder`, `RecordStageNineGateCommand` and `RecordStageNineGateHandler`, plus named errors `NotStageNineGateError` and `StageRunNotStageNineError` (canon-informed, SPEC.md section 12.3 stage 9 files 01, 08, 21, 22, 24), binding the reviewed `LaunchQAPackage` to the workspace tenant and authority registry, issuing one exact-version approval per canonical kind and closing the stage 9 `StageRun`; verified by `tests/unit/engagement/test_record_stage_nine_gate.py` (22 tests), so stage 9 can now close and the stage 10 reviewed-asset bridge is the next step. DONE 2026-10-03 (Ralph cycle 94): built the Execution stage 9 launch compliance and consent package (`ComplianceAssetKind`, `ComplianceAsset`, `ComplianceWaiver`, `CompliancePackage`, `ComplianceRequiredPolicy`; canon-informed, SPEC.md section 12.3 stage 9 files 21 and 34 and section 4 "consent where applicable") and wired it into `LaunchQA.authorize_traffic`, so the "Launch Approved" checkpoint refuses traffic when a required compliance asset is absent or its waiver has expired, and a ready QA now necessarily pins its reviewed package; verified by `tests/unit/execution/test_compliance_package.py` (25 tests), so the launch gate now enforces the canon compliance suite without adding a canonical gate kind.]
10. Implement stage 10 baseline, command center and improvement loop. [DONE 2026-10-02 (Ralph cycle 31): Execution `PerformanceBaseline` records the full stage 10 asset package and the distinct first-qualified-traffic, lead, appointment and sale milestones as observed or pending, is grounded on the stage 9 `LaunchQA`, and rejects a cross-tenant QA or milestone at construction; `PerformanceBaselinePolicy` refuses "Performance Baseline Established" unless the launch QA is `READY_FOR_TRAFFIC`, every canonical milestone is recorded, and first qualified traffic is observed, so Phase 5's "launch alone cannot complete the engagement" example is met by a real aggregate; `MilestoneObservation` forbids fabricating a pending observation, and `PerformanceClaim` / `PerformanceClaimPolicy` keep observations distinct from causal conclusions (causal needs an established same-tenant baseline and an adequate caller-supplied sample, and a low-sample movement can be recorded as an interpretation), so Phase 5's milestone-distinctness, missing-baseline and low-sample examples are met; verified by `tests/unit/execution/test_performance_baseline.py`. DONE 2026-10-02 (Ralph cycle 33): pure Governance `PipelineProgress` reports verified progress as the count of approved stage gates derived from the durable `GateLedger` plus caller-supplied verified post-launch milestones, reports activity separately, revokes a gate when a later non-passing decision supersedes it, and rejects negative counts or approved gates exceeding total gates, so SPEC.md section 4's "Display progress as approved gates and verified post launch milestones, never as tasks checked off" is met by a real value; verified by `tests/unit/governance/test_pipeline_progress.py`. DONE 2026-10-03 (Ralph cycle 87): built the Execution `PerformanceBaselinePackage` bridge projecting the reviewed stage 10 baseline onto the twelve canonical kinds. DONE 2026-10-03 (Ralph cycle 88): wired the stage 10 "Performance Baseline Established" `GateDecision` end to end (`StageTenGateAssembler`, `StageTenGateRecorder`, `RecordStageTenGateCommand`, `RecordStageTenGateHandler`), so all eleven gates of the canonical 0-10 template now have a write path; verified by `tests/unit/engagement/test_record_stage_ten_gate.py` (22 tests). Command center intervention ranking is DONE 2026-10-03 (Ralph cycle 90): built the pure Operations `Intervention` card and `InterventionRankingPolicy` ranking blocked critical path, overdue approvals, failed live journeys and nearing commitments with explainable surfacing, dismissal with rationale and deduplication (SPEC.md section 7); verified by `tests/unit/operations/test_intervention_ranking.py` (18 tests). The notification/quiet-hours policy is DONE 2026-10-03 (Ralph cycle 91); verified by `tests/unit/operations/test_notification_policy.py` (22 tests). The improvement loop is DONE 2026-10-03 (Ralph cycle 92): built the Measurement `ImprovementProposal`, `ImprovementApproval`, `ImprovementOutcome` and the approval-gated policies so an optimization stays a proposal until its named owner approves it and is then measured as two observations grounded on an established same-tenant baseline, keeping the movement distinct from a causal conclusion (SPEC.md section 4; Phase 5 "one improvement is approved and measured"; canon files 23 and 24); verified by `tests/unit/measurement/test_improvement_loop.py` (26 tests). The metric registry is DONE 2026-10-03 (Ralph cycle 93): built the Measurement `MetricDefinition`, `MetricUnit`, `MetricDirection`, `MetricFunnelStep`, `MeasurementWindow`, `MeasurementBasis`, `MeasurementRecord` and `MetricBaselinePolicy` so a stage 10 observation pins a typed, versioned, tenant-scoped metric over an explicit window with a placeholder-or-observed basis, value, source and sample, a placeholder cannot establish a baseline and an undersized observed sample is refused (SPEC.md sections 3 and 4; Phase 5 "metric registry"; canon files 23 and 24 inform the metric set); verified by `tests/unit/measurement/test_metric_registry.py` (24 tests); DONE 2026-10-03 (Ralph cycle 95): grounded the improvement loop on that registry -- `ImprovementProposal.metric` and `ImprovementOutcome.metric` are required same-tenant `MetricDefinition`s whose name the subject must match, and the measurement policy refuses an outcome measuring a different metric identity or version (SPEC.md section 3; canon files 23 and 24); verified by the `ImprovementMetricGroundingTests` in `tests/unit/measurement/test_improvement_loop.py` (10 tests), so a stage 10 optimization cannot be proposed or measured against a free-text metric; the next ready item is grounding the outcome's before/after on registered `MeasurementRecord`s.]
11. Complete operational security, backup, GitOps and acceptance drills.

## Risks and decisions

Major risks: fork internals may differ from the prior description; upstream license may limit use; latent cross tenant leakage; AI output may be mistaken for approval; home cluster may lack durable storage or reliable ingress; connector side effects may duplicate on retries; migrating live workflows may strand approval gates. Mitigations are respectively inventory, license review, isolation tests, explicit human authority, restore drills, idempotency keys, and version pinned workflow definitions.

Decisions resolved (2026-10-03, owner RED principal): fork and license
(OpenExecutive upstream v0.4.6 pinned as a submodule, Apache-2.0); code location
(ADR 0008, app is this repository); storage (ADR 0003, PostgreSQL container on
truenas-backed PVs); tenancy (ADR 0004); scheduler topology (ADR 0005); RED agent
registration (ADR 0006); model provider (OpenRouter, OPENROUTER_ENABLED, and the
owner accepts client material flowing through it); Kubernetes platform (Atlas
k3s). Approver and owner identities are role-based placeholders until real names
are supplied. External access is home-LAN-only.

Decisions still open, each with a named owner (the RED principal unless noted):
app identity provider for client-facing auth (the UI auth gate is currently
patched off); pilot metric targets and 3F launch scope; backup target and restore
drills for truenas PVs, PostgreSQL and /data; charters for capability agents 10
and 11 (proposed now: PR #1 Client Success and Engagement Health, PR #2
Assurance, Risk and Compliance, both open and blocked awaiting the operator's
merge); acquisition of canon
files 19/20 (sales/enrollment and email/follow-up modules) — a known blocker the
owner will close when the content arrives; the sales/enrollment block arrived
2026-10-03 as canon files 35-49, so only files 19/20 and the promised
email/follow-up sequence remain missing; and per-stage required-kind decisions
for the planning assets (enrollment, client process design, content roadmap,
retargeting, dashboards).
Any work requiring these decisions may proceed to a reviewable proposal and
tests, but may not assume authorization from missing information.

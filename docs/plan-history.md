# Implementation plan history

Cycle records older than the two current entries in `IMPLEMENTATION_PLAN.md`. Newest archived entry first.

### Cycle 20261009T021605Z: K3 — port command center, client workspace and approval inbox to `/operations/*`

- **Selected item:** K3 (port the command center, client workspace and approval
  inbox as native cockpit pages at `/operations/*`), the highest-value ready
  item: K2 is done, so K3 is the first port of the single-shell line and it
  unblocks K4-K8 and K12; `[7/7]` conditions 2 and 3 need the native routes and
  the shared context driving them. K9/K10 are independent but lower value.
- **Outcome:** the three screens are additive files in the absorbed cockpit tree
  (ADR 0014): `src/lib/redOperationsApi.ts` (typed same-origin `/red` reads for
  interventions, the engagement production view and approvals),
  `src/components/operations/{CommandCenter,ClientWorkspaceOverview,ApprovalInbox}.tsx`
  (pure presentational views) and their `*Screen.tsx` containers, plus native
  routes `src/app/operations/{command-center,client-workspace,approval-inbox}/page.tsx`.
  The containers read the shared workspace/engagement selection from
  `useRedClient()` (K2) instead of per-screen free-text tenant/engagement inputs,
  and surface real loading, error and empty states. The repo-side
  `tests/cockpit-ui/operationsScreens.test.tsx` suite (vitest +
  testing-library; vendor `package.json` untouched) covers the presentational
  views and the context-driven containers.
- **Evidence:** `tests/cockpit-ui` 15 passed (6 K2 + 9 K3); `make check` 2730
  passed / 3 skipped / 799 subtests; `scripts/check_vendor_additive.sh` ok (1225
  locked files match); `tsc --noEmit` in the vendor UI clean; `[7/7]` still fails
  at `[14.1]` (the thin client is retired in K7), as expected.
- **Not done (deliberately):** the remaining nine `/operations/*` routes, the nav
  rewrite and the thin-client retirement are K4-K7; no send, spend, publication
  or client commitment is authorized (SPEC.md sections 4 and 9); `.ralph/DONE` is
  not touched because `make done` still fails `[7/7]`.
- **Next ready item:** K4 (port build board, workflow run detail and launch
  readiness to `/operations/*`), unblocked by K3; K5 is also unblocked by K3;
  K9 and K10 are independent.
- **Blockers:** none.

### Cycle 20261009T021022Z: K2 — shared client context in the cockpit (with the absorbed-fork tracking fix)

- **Selected item:** K2 (shared workspace/engagement context in the cockpit), the
  highest-value ready item: it unblocks K3-K8 and K11/K12 (the whole single-shell
  context line) and `[7/7]` condition 3 needs it. K9/K10 are independent but
  lower value.
- **Blocker found and fixed:** K2's additive cockpit files could not be
  committed. `vendor/openexecutive` was still an unresolvable gitlink (no
  `.gitmodules`, no nested `.git`, target commit `31e5533` absent from the object
  store), so git ignored the whole tree and `git add` refused every path inside
  it. ADR 0014 decision 1 requires the tree to be ordinary tracked files.
  Removed the gitlink and committed the baseline tree (1266 files) as tracked
  source; the working tree is unchanged, so `scripts/check_vendor_additive.sh`
  still reports 1225 locked files matching the baseline.
- **Outcome:** the shared RED client context (SPEC.md section 14 condition 3) is
  additive files in the cockpit tree: `src/lib/redClientApi.ts` (tenant-scoped
  `GET /red/clients` listing), `src/components/workspace/redClientSelection.ts`
  (pure persistence/resolution), `RedClientContext.tsx` (provider + `useRedClient`
  hook, persisted to `localStorage`), and `RedClientPicker.tsx` (shell picker).
  The RED-owned `src/app/layout.tsx` mounts the provider and `AppShell.tsx`
  renders the picker in the TopBar. The ported `/operations/*` screens (K3-K6)
  read the selection from `useRedClient()` instead of per-screen free-text
  defaults. The repo-side `tests/cockpit-ui/` suite (vitest + testing-library;
  vendor `package.json` untouched) covers the listing load, persistence, restore,
  picker change and the pure selection rules.
- **Evidence:** `tests/cockpit-ui` 6 passed; `make check` 2730 passed / 3 skipped
  / 799 subtests; `scripts/check_vendor_additive.sh` ok (1225 locked files match);
  `tsc --noEmit` in the vendor UI clean; `[7/7]` still fails at `[14.1]` (the
  thin client is retired in K7), as expected.
- **Not done (deliberately):** the `/operations/*` pages, the nav rewrite and the
  thin-client retirement are K3-K7; no send, spend, publication or client
  commitment is authorized (SPEC.md sections 4 and 9); `.ralph/DONE` is not
  touched because `make done` still fails `[7/7]`.
- **Next ready item:** K3 (port command center, client workspace and approval
  inbox to `/operations/*`), unblocked by K2; K9 and K10 are independent.
- **Blockers:** none.

### Owner decision 2026-10-08: single-shell cockpit overhaul phase opened (K queue)

- **Selected item:** none (planning entry, no cycle). The owner reviewed the
  deployed two-app state and directed the next phase: the rebranded
  OpenExecutive cockpit becomes the only RED UI, and the cockpit takes on the
  context and fundamentals of the RED system and canon (ADR 0013, SPEC.md
  section 14).
- **Outcome:** planning foundation plus the vendor-absorption mechanics.
  ADR 0013 records the single-shell decision; SPEC.md section 2 (cockpit row)
  and the new section 14 record the phase definition of done; the K queue below
  tracks the work; `make done` gained the `[7/7]` single-shell gate
  (`scripts/check_cockpit_overhaul.sh`) so `.ralph/DONE` cannot be touched
  while the phase is open; the stale prototype `.ralph/DONE` marker is removed
  at handoff. Same-day owner decision on the vendor rule: the fork is absorbed
  into this repository as ordinary tracked source (submodule and ADR 0011
  overlay retired, ADR 0014), upstream stays reachable through the recorded
  pin, RED changes inside the vendor tree are additive by default with
  RED-adopted surfaces free and owner-approved exceptions recorded in
  `docs/fork_inventory.md`, and the DoD `[4/7]` step now runs
  `scripts/check_vendor_additive.sh` against the baseline manifest.
- **Evidence:** the owner's 2026-10-08 review found the enforcement spec too
  tight for the vision: substantial cockpit modification must be allowed, so
  the minimal-vendor-change stance (ADR 0008/0011) is revised rather than
  respected. The live findings that motivated the phase: the cockpit's RED
  Operations group links out to a second app at `/screens/*` (ADR 0012 called
  this a stepping stone, rejected as the end state); the twelve screens carry
  per-screen free-text tenant/engagement forms defaulting to `3fmindset`, which
  does not exist in the deployed database (`GET /red/clients?tenant_id=3fmindset`
  returned zero workspaces), so screens render raw 404/422 errors or silent
  empty states; and the thin client's bespoke palette shares nothing with the
  cockpit's Tailwind v4 tokens.
- **Not done (deliberately):** no code change in this entry; R1/R2 stay
  deferred and are not picked up unattended; no send, spend, publication or
  client commitment is authorized (SPEC.md sections 4 and 9).
- **Next ready item:** K1 (seed the 3F pilot workspace end to end) — it unblocks
  the context work and makes every later screen verification meaningful.
- **Blockers:** none.



Older cycle notes and decisions: `docs/plan-history.md`. Keep only the latest two cycle entries here; older entries are archived by the Ralph harness.
### OpenExecutive initialization 2026-10-07: RED agency profile, team workspace, full canon

- The deployed OpenExecutive (cockpit backend) was initialized as RED's own
  agency via the AI interview (`/onboard/interview/*` through the cockpit
  proxy). The draft was committed with owner `dave@redrhino.online`, producing
  the company profile: name RED; a growth agency for coaches and consultants
  (high-ticket funnels and client acquisition); target customer coaches and
  consultants who want a predictable flow of new customers; departments Client
  Delivery, Growth Operations, Client Pipeline; leadership Dave, Founder &
  Principal Operator.
- Workspace set to `team`, `America/New_York`, owner role (company domain
  `redrhino.online`).
- Knowledge: the full canon ingested as company documents (domain `general`) —
  the 151 `framework-canon` transcripts plus the RED Method/ops docs and
  `internal/`, 252 documents / ~3,100 chunks indexed. Most went through the
  proxy; 28 that the proxy timed out on were re-uploaded directly to the
  backend.
- Verified: `GET /company-profile` returns RED; `GET /documents` = 252;
  `GET /workspace` = team; a chat turn answers grounded on the RED profile
  ("RED is a done-with-you growth agency that runs coaches and consultants
  through a proven client-getting system — the RED Method"); the deployed
  health gate passes.
- Note: the interview and embeddings make model calls; the profile is stored at
  `/data/company/profile.yaml` and the docs under `/data/company/docs/` on the
  `redop-data` PVC.



Older cycle notes and decisions: `docs/plan-history.md`. Keep only the latest two cycle entries here; older entries are archived by the Ralph harness.
### Cycle 20261007T000114Z: W1 deploy slice verified — `redop-worker` Deployment healthy

- **Selected item:** verify the deployed `redop-worker` Deployment is
  Running/healthy after the atlas publish and build (the next ready item recorded
  by cycle 2026-10-06T175247Z). It is the only ready item: G8/G9 are closed, C4
  is done, Q16 is complete, and R1/R2 stay deferred and must not be picked up
  unattended.
- **Outcome:** no code change. The atlas publish and Gitea build completed and
  promoted the worker-enabled chart, so the live verification the previous cycle
  deferred now passes. The `redop-worker` Deployment exists and is 1/1 Ready on
  image `registry.atlas.lan/atlas-admin/redop-api:sha-de44d86`; the pod is
  Running with 0 restarts and logs `RED workflow worker started for clients
  3fmindset`. W1 is complete.
- **Evidence:** `git ls-remote atlas refs/heads/main` = `de44d86` (matches local
  HEAD); the Gitea build workflow built and pushed `sha-de44d86` and promoted it
  to the GitOps repo as commit `d9104eb` (`ci: promote redop sha-de44d86`);
  Argo CD Application `redop` is Synced/Healthy at revision `d9104eb`; the
  migration Job `redop-migrate-b2v4d` Completed before the API served;
  `kubectl -n redop get deploy redop-worker` -> 1/1 Ready, image
  `...redop-api:sha-de44d86`; `kubectl -n redop logs deploy/redop-worker` ->
  `RED workflow worker started for clients 3fmindset`; the worker env carries
  `REDOP_WORKER_TENANTS=3fmindset` and command `python -m redops.worker`;
  `make done` -> DONE-GATE PASS (all six checks, including the deployed RED
  health check at `https://redop.atlas.lan/`).
- **Not done (deliberately):** no send, spend, publish or client commitment is
  authorized (SPEC.md sections 4 and 9). The worker runs the interim fail-on-send
  transport, so it resumes durable workflows but refuses every send.
- **Next ready item:** none. The post-prototype queue is exhausted: G1-G7 done,
  G8/G9 closed, C4 done, Q16 done, W1 complete. R1/R2 remain deferred and are not
  picked up unattended.
- **Blockers:** none. `.ralph/DONE` touched: `make done` passes and no ready work
  remains.

### Cycle 2026-10-06T175247Z: W1 deploy slice — fail-on-send connector transport, worker enabled

- **Selected item:** W1's deploy slice (configure the interim fail-on-send
  connector transport and `REDOP_WORKER_TENANTS`, set `worker.enabled: true`,
  verify the chart's worker Deployment is healthy), the only remaining item and
  now ready after the owner's 2026-10-06 connector-inventory decision. It
  outranks every alternative: G8/G9 are closed, C4 is done, Q16 is complete, and
  R1/R2 stay deferred and must not be picked up unattended.
- **Outcome:** new `FailOnSendConnectorTransport`
  (`backend/redops/contexts/execution/infrastructure/connectors.py`) and named
  `ConnectorSendRefusedError` (`.../domain/errors.py`): the interim connector
  refuses every send loudly and records no external operation, so nothing leaves
  the box. `connector_transport_from_env` now selects it when `DATABASE_URL` is
  set (instead of raising `WorkerConfigurationError`), so `worker_from_env` builds
  and the worker starts and resumes durable workflows; a step that would send
  raises, is caught per client, and the run stays persisted for a later retry with
  a real connector. The chart enables the worker by default (`worker.enabled:
  true`) and passes `REDOP_WORKER_TENANTS: "3fmindset"`; the worker Deployment
  renders with the roster env. Reversible: a real connector replaces the transport
  with no caller change.
- **Evidence:** `tests/unit/execution/test_fail_on_send_transport.py` (2 tests)
  proves the refusal is a named error and records no operation;
  `tests/unit/workflows/test_worker_entrypoint.py` (14 tests) proves the durable
  configuration selects the fail-on-send transport, builds a worker, and leaves a
  refused run persisted; `tests/unit/shared/test_red_helm_chart.py` proves the
  worker renders with the roster and can be disabled. `make check` 2716 passed, 3
  skipped, 799 subtests; `make done` -> DONE-GATE PASS.
- **Not done (deliberately):** the live worker Deployment health. The live image
  (`sha-3c2c482`) predates the worker entrypoint, so the worker deploys only after
  the harness publishes this commit to `atlas`, the Gitea build promotes the chart
  (now `worker.enabled: true`) and a new image, and Argo CD syncs. No send, spend,
  publish or client commitment is authorized (SPEC.md sections 4 and 9).
- **Next ready item:** verify the deployed `redop-worker` Deployment is
  Running/healthy after the atlas publish and build.
- **Blockers:** none for the code+chart slice; the live verification waits on the
  atlas publish/build. `.ralph/DONE` touched: `make done` passes.

Older cycle notes and decisions: `docs/plan-history.md`. Keep only the latest two cycle entries here; older entries are archived by the Ralph harness.
### Cycle 2026-10-06T163236Z: W1 deploy slice blocked on the connector-inventory owner decision

- **Selected item:** W1's deploy slice (configure a connector transport and
  `REDOP_WORKER_TENANTS`, set `worker.enabled: true`, verify the chart's worker
  Deployment is healthy), the only remaining item. It is **not ready**: the
  worker refuses to start with `DATABASE_URL` set and no connector transport
  (`WorkerConfigurationError`, `backend/redops/worker.py`), and choosing a
  transport is the open connector-inventory decision (SPEC.md section 11).
  Enabling the Deployment now would crashloop and break the Argo CD health that
  condition 9 requires. No other item is ready: Q16 is complete (connector
  idempotency, optimistic-version conflict and store-level CAS all done), G8/G9
  are closed (owner 2026-10-06), C4 is done, and R1/R2 are deferred and must not
  be picked up unattended.
- **Outcome:** no code change. The deploy slice is blocked on a named-owner
  decision, so the loop records the blocker rather than invent work or make the
  connector-inventory decision unattended.
- **Evidence:** `make done` -> `DONE-GATE PASS` (all six checks green, including
  the deployed RED health check at `https://redop.atlas.lan/`);
  `backend/redops/worker.py` `connector_transport_from_env` raises
  `WorkerConfigurationError` when `DATABASE_URL` is set and no transport is
  configured; `deploy/charts/redop/values.yaml` keeps `worker.enabled: false` and
  `templates/deployment-worker.yaml` is gated on it.
- **Not done (deliberately):** enabling the chart's worker Deployment and wiring
  `REDOP_WORKER_TENANTS`; both wait on the connector-inventory owner decision. No
  send, spend, publish or client commitment is authorized (SPEC.md sections 4 and
  9).
- **Next ready item:** none unblocked. The deploy slice waits on the
  connector-inventory owner decision (SPEC.md section 11): the owner names the
  connector(s)/transport, or directs a fail-on-send transport that keeps the
  worker honest without a connector.
- **Blockers:** connector-inventory owner decision (SPEC.md section 11).
  `.ralph/DONE` touched: `make done` passes and no ready work remains.

### Cycle 2026-10-06T162634Z: W1 worker entrypoint (`python -m redops.worker`)

- **Selected item:** W1's worker entrypoint, the next ready item after the
  connector-backed executor (owner decision 2026-10-06; SPEC.md sections 6, 7 and
  9; ADR 0005). It outranks every alternative: G8's required-kind half and G9 are
  closed, C4 is done, R1/R2 are deferred and must not be picked up unattended, and
  no other non-canon item is ready. The entrypoint is the composition consumer the
  resume use case has lacked since the worker isolation layer landed.
- **Outcome:** new `backend/redops/worker.py`, runnable as
  `python -m redops.worker`. `build_worker` is the single composition point that
  wires the `WorkflowRunStore` to `ResumeDueRunsHandler` and the connector-backed
  `ConnectorStepExecutor`. `worker_from_env` selects the run store and the
  external-operation store from one `DATABASE_URL` (so a resume and an API status
  read share one database), builds the replay-safe `IdempotentConnector` over an
  injected transport, and reads the client roster from `REDOP_WORKER_TENANTS`
  (default pilot client `3fmindset`). `WorkflowWorker` scans each configured
  client's due runs one client at a time; a failure for one client is logged and
  swallowed so the rest advance and the process survives, and the failed run stays
  persisted (SPEC.md sections 7 and 11). A durable configuration without a real
  connector transport refuses to start with the new named `WorkerConfigurationError`
  rather than record an external operation it cannot send (SPEC.md section 6). No
  stage 0-10 template, required asset kind, migration, route or gate changed; the
  chart worker stays `enabled: false`.
- **Evidence:** `tests/unit/workflows/test_worker_entrypoint.py` (12 tests, 5
  subtests) proves a due run resumes to completion through the connector executor,
  a waiting approval is left for its human with no effect, only configured clients
  are scanned, a failing client does not stop the pass or lose its run, the loop
  stops on the signal event, the roster/transport configuration refusals, and the
  composition-root wiring; `make check` 2712 passed, 3 skipped, 799 subtests; `uv
  run pyflakes backend tests` clean; `make done` still PASS. Independent `verify`
  subagent: PASS on all six criteria (test-strength caveats only).
- **Not done (deliberately):** enabling the chart's worker Deployment. Enabling it
  needs a configured connector transport (the connector inventory is an open
  SPEC.md section 11 decision) and the client roster as env; enabling it now would
  fail fast and break the Argo CD health condition 9 requires. No send, spend,
  publish or client commitment is authorized (SPEC.md sections 4 and 9).
- **Next ready item:** W1's deploy slice: configure a connector transport and
  `REDOP_WORKER_TENANTS`, set `worker.enabled: true`, and verify the chart's worker
  Deployment is healthy.
- **Blockers:** none for this slice. The deploy slice waits on the connector
  transport / connector-inventory owner decision. `.ralph/DONE` not touched: the
  prototype DoD still passes but the owner reopened the loop for post-prototype
  work (plan history, 2026-10-06) and ready work remains.

### Cycle 2026-10-06T162338Z: W1 concrete connector-backed workflow step executor

- **Selected item:** W1's unblocking prerequisite, the concrete
  `WorkflowStepExecutor` adapter, the highest-value ready item. The owner
  decision 2026-10-06 unblocked W1 by directing a concrete `WorkflowStepExecutor`
  port and adapter (the connector seam is a `ConnectorPort`, not a step executor),
  and W1 is the next ready item; G8's required-kind half and G9 are closed, and
  R1/R2 stay deferred. The adapter is the smallest passing change that lets the
  worker entrypoint be built next.
- **Outcome:** new `ConnectorStepExecutor`
  (`backend/redops/workflows/infrastructure/executors.py`) implements the existing
  `WorkflowStepExecutor` port over the replay-safe `ConnectorPort`. It derives a
  deterministic `ConnectorEffect` from the run and step: idempotency key
  `{run_id}:{step_name}`, connector from configuration, target the step name, and
  a `sha256` digest of the pinned definition `id@version:step`, scoped to the
  run's tenant. A re-run of an interrupted step therefore resolves to the one
  recorded external operation instead of sending a second effect (SPEC.md section
  11; ADR 0005). An approval step is refused with the new named
  `WorkflowStepExecutionError` rather than executed (SPEC.md section 4). No stage
  0-10 template, required asset kind, migration, route or gate changed; the chart
  worker stays disabled until the entrypoint lands.
- **Evidence:** `tests/unit/workflows/test_connector_step_executor.py` (7 tests)
  passes, including a restarting-worker resume and a `ResumeDueRunsHandler` pass
  that re-runs an interrupted step without a second effect; `uv run pyflakes`
  clean; `make check` 2700 passed, 3 skipped, 794 subtests. Independent `verify`
  subagent: PASS.
- **Not done (deliberately):** the worker entrypoint (`python -m redops.worker`)
  and enabling the chart's worker Deployment are the next bounded slice of W1; no
  send, spend, publish or client commitment is authorized (SPEC.md sections 4 and
  9).
- **Next ready item:** W1's worker entrypoint, now unblocked by this adapter:
  compose `ResumeDueRunsHandler` with the durable `WorkflowRunStore` and the
  `ConnectorStepExecutor`, then enable the chart worker.



Older cycle notes and decisions: `docs/plan-history.md`. Keep only the latest two cycle entries here; older entries are archived by the Ralph harness.
### Cycle 2026-10-06T155319Z: Q16 store-level compare-and-swap on the build store

- **Selected item:** Q16 (store-level compare-and-swap hardening), the
  highest-value ready item. It outranks W1 (worker entrypoint), blocked on a
  concrete `WorkflowStepExecutor` (the connector seam is a `ConnectorPort`, not a
  step executor), and G8's required-kind half and G9, blocked on owner input. The
  previous cycle left this as the bounded, unblocked follow-up: the optimistic
  check was application-level read-check-write, so two truly concurrent writers
  could both pass.
- **Outcome:** `BuildObjectRepository.save` now accepts an optional keyword
  `expected_version`. With it the write is a compare-and-swap: the PostgreSQL
  adapter issues `UPDATE ... WHERE (build_objects.build->>'version')::int = %s`
  and raises `BuildObjectVersionConflictError` (rolling back) when no row matches,
  so two writers that read the same version cannot both pass; without it the write
  stays an unconditional upsert for a new build. The in-memory adapter now stores
  and returns independent snapshots (through the payload mapper) and enforces the
  same predicate, so the CAS is testable without a database. The transition route
  passes `expected_version=body.expected_version` to `save`, making the store the
  authoritative backstop behind the domain `require_version`. No stage 0-10
  template, required asset kind, migration or gate changed.
- **Evidence:** new CAS tests in `tests/unit/production/test_build_object_store.py`
  (3) and `tests/unit/production/test_build_object_postgres.py` (3, run with
  `DATABASE_URL`) pass; `make check` 2693 passed, 3 skipped, 794 subtests.
  Independent `verify` subagent: PASS.
- **Not done (deliberately):** no send, spend, publish or client commitment is
  authorized (SPEC.md sections 4 and 9).
- **Next ready item:** none unblocked. W1 stays blocked on a concrete
  `WorkflowStepExecutor`; G8's required-kind half and G9 stay blocked on owner
  input. The loop stops and records the blocker.

Older cycle notes and decisions: `docs/plan-history.md`. Keep only the latest two cycle entries here; older entries are archived by the Ralph harness.
### Cycle 2026-10-06T154157Z: Q16 optimistic-version conflict on the live build aggregate

- **Selected item:** Q16 (optimistic-version conflict half), the highest-value
  ready non-canon item. It outranks W1 (worker entrypoint), which is blocked on a
  concrete `WorkflowStepExecutor` (the connector seam is a `ConnectorPort`, not a
  step executor, so a worker would have no honest effect to run), and G8's
  remaining required-kind half, which is blocked on the RED principal's open
  per-stage required-kind decision. Q16 is a SPEC.md section 7 requirement
  ("optimistic version checking returns conflict on stale updates") and the last
  open half of a listed remaining implementation gap.
- **Outcome:** the live Production `BuildObject` now carries a monotonic
  `version` (starts at 1, advances on every mutation and lifecycle transition)
  and a `require_version(expected)` guard that raises the new
  `BuildObjectVersionConflictError` on a stale write before any mutation. A new
  version-carrying mutation route `POST /red/builds/{build_id}/transition` loads
  the tenant-scoped build, refuses a stale `expected_version` with a named 409,
  then drives the existing `BuildTransitionPolicy` through a new public
  `transition_to`; an unknown or foreign build is a 404 and an illegal target
  state is a 422. The version round-trips through `build_to_payload` /
  `build_from_payload` (defaulting to 1 for older rows), and
  `BuildObjectResponse` exposes it. No stage 0-10 template, required asset kind,
  migration or gate changed.
- **Evidence:** `tests/unit/production/test_build_object_version.py` (8 tests)
  and the new route tests in `tests/unit/production/test_builds_route.py` (5
  tests) pass; the full `tests/unit/production` suite passes (109 passed, 13
  subtests); `uv run pyflakes` clean on the changed files; `make check` 2671
  passed, 3 skipped, 793 subtests. Independent `verify` subagent: PASS on all 6
  acceptance criteria.
- **Not done (deliberately):** the optimistic check is application-level
  read-check-write; the PostgreSQL `save` remains a blind upsert, so two truly
  concurrent writers can both pass. A store-level compare-and-swap (a version
  predicate in the `ON CONFLICT` update) is a concurrency-hardening follow-up,
  not part of the sequential stale-write acceptance criterion. No send, spend,
  publish or client commitment is authorized (SPEC.md sections 4 and 9).
- **Next ready item:** G8's production-view route projection (supply the
  `UmbrellaPlanReportingView` from a Portfolio `UmbrellaPlan` port and
  persistence) is bounded and unblocked; W1 (worker entrypoint) stays blocked on
  a concrete `WorkflowStepExecutor`; G8's required-kind half and G9 stay blocked
  on owner input.

### Cycle 2026-10-06T153729Z: G8 umbrella plan wired into the production view

- **Selected item:** G8 (wiring follow-ups), the last open Canon gap backlog
  item, bounded to its authorized "into the production view" slice. G8's
  required-kind half (retargeting family, banner library) is blocked by the RED
  principal's open per-stage required-kind decision (`Decisions still open`,
  below), which the loop must not decide unattended; the `UmbrellaPlan` is
  explicitly "not a new required gate kind" (its own docstring), so surfacing it
  in the production view is the reversible, authorized slice. It outranks W1
  (worker entrypoint), which is not bounded because no concrete
  `WorkflowStepExecutor` exists, and Q16, which is partial.
- **Outcome:** the Governance production view now carries the canon umbrella plan
  (SPEC.md sections 4 and 12.5; canon files 00, 01) as a caller-supplied,
  tenant-scoped read-model projection. New frozen `UmbrellaPlanReportingView`
  (plan identity, owning client, accountable owner, covered stages, review and
  next-review dates) with `is_current`/`is_overdue` for the 90-day revisit;
  `EngagementProductionView` gains an optional `umbrella_plan` and refuses a
  cross-tenant row (`UmbrellaPlanReportingTenantBoundaryError`), a row that does
  not cover exactly the view's stages (`UmbrellaPlanCoverageError`) and a
  malformed row (`UmbrellaPlanReportingError`); `EngagementProductionViewQuery`
  and the handler pass it through. No stage 0-10 template, required asset kind,
  route, persistence or migration changed, so the wiring is reversible and
  authorizes no production, spend or traffic.
- **Evidence:** `tests/unit/governance/test_production_view_umbrella.py` (8
  tests, 9 subtests) passes; the full `tests/unit/governance` suite passes (311
  passed, 1 skipped, 76 subtests); `uv run pyflakes` clean on the changed files;
  `make check` 2658 passed, 3 skipped, 790 subtests.
- **Not done (deliberately):** the required-kind half of G8 (retargeting family,
  banner library) stays blocked on the RED principal's per-stage required-kind
  decision; the production-view route does not yet supply the projection (it
  needs a Portfolio port and persistence, a bounded follow-up). No send, spend,
  publish or client commitment is authorized (SPEC.md sections 4 and 9).
- **Next ready item:** none unblocked in the Canon gap backlog: G8's remaining
  half and G9 are blocked on owner input. W1 (worker entrypoint) and Q16
  (optimistic-version conflict) remain open non-canon items; W1 needs a concrete
  `WorkflowStepExecutor` and Q16 needs a version-carrying mutation route.

### Cycle 2026-10-06T151009Z: G6 partnership line and certification implemented

- **Selected item:** G6 (partnership line and certification), the highest Canon
  gap backlog item whose dependency is met. G5 completed last cycle, so G6 is
  unblocked and outranks G7 because the backlog is ordered and G6 is higher. It is
  a bounded pure-domain artifact that types the client's retention and expansion
  path (the four-offer path, the partnership loop, referral, community, reputation
  and certification).
- **Outcome:** implemented the Portfolio `PartnershipPlan` (canon files 11, 12;
  Certification; Live Sessions 5, 12; High Ticket Funnels 19; synthesized
  `ops/playbooks/partnership.md`, `certification.md`,
  `ops/sops/certification-exam.md`). It grounds on a same-tenant stage 5
  `ProductProgram` and types the canon four-offer path (entry, mid, core, partner)
  as an ordered, duplicate-free set, the partnership loop (retain, grow, refer,
  renew) in order, a regular check-in with a cadence and owner, a referral plan
  that must ask after a win and name the plan's partner offer, simple unique
  community rules, a reputation track covering reviews, stories and press, and a
  short certification standard (at most six skills, a clear pass mark, a yearly
  recheck). Its `certify` gate refuses an operator with no real result or a failed
  exam. It is a post-launch plan, never an observation. New named errors:
  `InvalidPartnershipPlanError`, `PartnershipTenantBoundaryError`,
  `PartnershipDependencyError`, `PartnershipFormatError`, `PartnershipGateError`,
  `PartnershipObservationError`, `CertificationStandardError`,
  `CertificationProofError`.
- **Evidence:** `tests/unit/portfolio/test_partnership.py` (53 tests, 3 subtests)
  passes; the full `tests/unit/portfolio` suite passes (148 tests, 24 subtests);
  `uv run pyflakes` clean on the changed files; `make check` 2591 passed, 3
  skipped, 764 subtests.
- **Not done (deliberately):** wiring the plan into a required post-launch gate
  kind is a methodology-owner decision (SPEC.md section 12.5), so it stays a
  planning asset. No send, spend, publish or client commitment is authorized
  (SPEC.md sections 4 and 9).
- **Next ready item:** G7 (service-line artifacts), no unmet dependency; the case
  study claim refuses an unapproved or unsourced testimonial. G8 (wiring
  follow-ups) is also ready; G9 is blocked on owner input.



Older cycle notes and decisions: `docs/plan-history.md`. Keep only the latest two cycle entries here; older entries are archived by the Ralph harness.
### Cycle 2026-10-06T150726Z: G5 delivery ladder implemented

- **Selected item:** G5 (delivery ladder and ascension), the highest Canon gap
  backlog item whose dependency is met. G3 completed last cycle, so G5 is the
  highest ready item; it outranks G7 because the backlog is ordered and G5 is
  higher, and G6 depends on G5. It is a bounded pure-domain artifact that types
  the client's own delivery (Serve) and the next-offer path.
- **Outcome:** implemented the Portfolio `DeliveryLadder` (canon files 11, 12;
  Certification; Live Sessions 5, 12; synthesized `ops/playbooks/delivery.md`). It
  grounds on a same-tenant stage 5 `ProductProgram` and types the canon rungs
  (one-to-one, live cohort, evergreen) as an ordered, duplicate-free subsequence
  beginning at one-to-one. It requires exactly one deliverable per program step in
  program order, at least one 90-day roadmap audit whose next audit is exactly one
  quarter later, at least one kickoff success goal, and at least one ascension
  offer tied to a program step. Its `close` gate refuses to close until a
  caller-supplied result meets every goal. It is a post-launch plan, never an
  observation. New named errors: `InvalidDeliveryLadderError`,
  `DeliveryLadderDependencyError`, `DeliveryLadderTenantBoundaryError`,
  `DeliveryLadderFormatError`, `DeliveryAuditCadenceError`,
  `DeliveryAuditOrderError`, `DeliveryGateError`,
  `DeliveryLadderObservationError`.
- **Evidence:** `tests/unit/portfolio/test_delivery_ladder.py` (39 tests, 3
  subtests) passes; the full `tests/unit/portfolio` suite passes (95 tests, 21
  subtests); `uv run pyflakes` clean on the changed files; `make check` 2538
  passed, 3 skipped, 761 subtests.
- **Not done (deliberately):** wiring the ladder into a required post-launch gate
  kind is a methodology-owner decision (SPEC.md section 12.5), so it stays a
  planning asset. No send, spend, publish or client commitment is authorized
  (SPEC.md sections 4 and 9).
- **Next ready item:** G6 (partnership line and certification), whose dependency
  G5 is now met; G7 (service-line artifacts) is also ready. G6 outranks G7 because
  the backlog is ordered and G6 is higher.



Older cycle notes and decisions: `docs/plan-history.md`. Keep only the latest two cycle entries here; older entries are archived by the Ralph harness.
### Cycle 2026-10-06T150309Z: G3 webinar kit implemented

- **Selected item:** G3 (webinar kit), the highest Canon gap backlog item whose
  dependency is now met. G4 (its dependency) completed last cycle, so G3 is
  unblocked and outranks G5/G7 because the backlog is ordered and G3 is the
  highest ready item; it is a bounded pure-domain artifact that types the scaled
  enrollment path and closes a canon gap the stage 6/8/10 funnel needs before
  traffic.
- **Outcome:** implemented the Execution `WebinarKit` (canon file 32; Winning
  Webinar 01-13; synthesized `ops/playbooks/webinar.md`,
  `ops/checklists/webinar-run-of-show.md`, `ops/sops/webinar-build.md`). It grounds
  on a same-tenant stage 4 `SignatureSolution`, types the scaled path
  (`EnrollmentPath.SCALED`) and requires the simple path proven first. It requires
  the six-phase run of show (frame, teach, shift, sell, show, close) in order on an
  about-60-minute clock, three teach blocks matching the three signature-solution
  phases in order, one offer, the five-page set (sign up, train, webinar, replay,
  order), the 5P email sequence (problem, promise, proof, ping, promotion), a 3 to
  5 day closing sequence, the replay to everyone and at least one retargeting
  group. It refuses automation below the ten-and-ten bar (ten live runs at 10% or
  better) and never presents an automated webinar as live. It is a plan, never an
  observation. New named errors: `InvalidWebinarError`, `WebinarDependencyError`,
  `WebinarTenantBoundaryError`, `WebinarFormatError`, `WebinarAutomationError`,
  `WebinarObservationError`.
- **Evidence:** `tests/unit/execution/test_webinar.py` (34 tests, 2 subtests)
  passes; the full `tests/unit/execution` suite passes (366 tests, 123 subtests);
  `uv run pyflakes` clean on the changed files.
- **Not done (deliberately):** wiring the kit into a required stage 6/8/10 gate
  kind is a methodology-owner decision (SPEC.md section 12.5), so the kit stays an
  enrollment planning asset. No send, spend, publish or client commitment is
  authorized (SPEC.md sections 4 and 9).
- **Next ready item:** G5 (delivery ladder), no unmet dependency; represents the
  client's own delivery (Serve) and the next-offer path. G7 (service-line
  artifacts) is also ready; G6 depends on G5.



Older cycle notes and decisions: `docs/plan-history.md`. Keep only the latest two cycle entries here; older entries are archived by the Ralph harness.
### Cycle 2026-10-06T144439Z: G2 authority-video kit implemented

- **Selected item:** G2 (authority-video kit), the next Canon gap backlog item
  with no unmet dependency. It outranks G4/G5/G7 because the backlog is ordered
  and G2 is the highest ready item; it is a bounded pure-domain artifact that
  extends the stage 7 `AuthorityAmplifier` and closes a canon gap the stage 7
  production pack needs before traffic.
- **Outcome:** implemented the Production `AuthorityVideoKit` (canon files 13-18;
  High Ticket Funnels 05, 06, 08; synthesized `ops/playbooks/authority-video.md`,
  `ops/sops/authority-video-build.md`). It extends a same-tenant stage 7
  `AuthorityAmplifier` that has produced its video (the canon gate checks the
  script before the slides), reuses that amplifier's six-block script, and names
  the nine steps of a same-tenant stage 4 `SignatureSolution`. It types the
  flagship and step video kinds, requires one flagship video of 8 to 20 minutes
  with one clear action, exactly nine step videos, one per signature-solution
  step, each no longer than the flagship, and refuses a step video whose step the
  solution does not name, a repeated step, a cross-tenant amplifier, solution or
  step video, and a kit with no produced video. It is a plan, never an
  observation. New named errors: `InvalidAuthorityVideoKitError`,
  `AuthorityVideoKitDependencyError`, `AuthorityVideoKitTenantBoundaryError`,
  `AuthorityVideoKitFormatError`, `AuthorityVideoKitObservationError`.
- **Evidence:** `tests/unit/production/test_authority_video_kit.py` (16 tests, 4
  subtests) passes; the full `tests/unit/production` suite passes (96 tests, 13
  subtests); `uv run pyflakes` clean on the changed files. `make check` during
  this cycle first exposed the prompt test trying to acquire the active cycle
  lock. Fixed in `834cae7` by testing against a temporary repo with a live
  fixture lock; rerun after the cycle: 2442 passed, 3 skipped, 754 subtests.
- **Not done (deliberately):** wiring the kit into a required stage 7 gate kind is
  a methodology-owner decision (SPEC.md section 12.5), so the kit stays a
  production planning asset. No publish or spend is authorized (SPEC.md sections
  4 and 9).
- **Next ready item:** G4 (strategy-session kit), no unmet dependency; a third
  enrollment model that refuses a price below the floor. G5 (delivery ladder) and
  G7 (service-line artifacts) are also ready; G3 depends on G4.



Older cycle notes and decisions: `docs/plan-history.md`. Keep only the latest two cycle entries here; older entries are archived by the Ralph harness.
### Cycle 2026-10-06T132216Z: G1 lead-magnet kit implemented

- **Selected item:** G1 (lead-magnet kit), the first Canon gap backlog item with
  no unmet dependency. It outranks G2/G4/G5/G7 because the backlog is ordered and
  G1 is the highest ready item; it is a bounded pure-domain artifact that closes a
  canon gap the stage 6/8 funnel needs before traffic.
- **Outcome:** implemented the Commercial Design `LeadMagnetKit` (canon files
  High Ticket Funnels 03, 04; Live Sessions 15; 14D Step 7; synthesized
  `ops/playbooks/lead-magnet.md`, `ops/checklists/lead-magnet-pdf.md`). It grounds
  on a same-tenant stage 4 `SignatureSolution` and stage 2 `PrimaryCurrency`,
  names and reports the one hot step it is built from, and refuses a hot step the
  solution does not name. It types the canon's allowed formats (cheat sheet,
  template, checklist, script, roadmap), requires the name to imply its format,
  requires the seven-element PDF exactly once, the two-step opt in, email
  delivery (not the thank-you page), and the ten-minute rule. It is a plan, never
  an observation. New named errors: `InvalidLeadMagnetKitError`,
  `LeadMagnetKitDependencyError`, `LeadMagnetKitTenantBoundaryError`,
  `LeadMagnetKitFormatError`, `LeadMagnetKitObservationError`.
- **Evidence:** `tests/unit/commercial/test_lead_magnet_kit.py` (14 tests, 9
  subtests) passes; the full `tests/unit/commercial` suite passes (453 tests, 278
  subtests); `pyflakes` clean on the changed files.
- **Not done (deliberately):** wiring the kit into a required stage 8 gate kind is
  a methodology-owner decision (SPEC.md section 12.5), so the kit stays a planning
  asset. No publish or spend is authorized (SPEC.md sections 4 and 9).
- **Next ready item:** G2 (authority-video kit), no unmet dependency; it extends
  the stage 7 `AuthorityAmplifier` and refuses a step video whose step the
  solution does not name. G4 (strategy-session kit) and G7 (service-line
  artifacts) are also ready.

Older cycle notes and decisions: `docs/plan-history.md`. Keep only the latest two cycle entries here; older entries are archived by the Ralph harness.
### Cockpit adoption 2026-10-05: the OpenExecutive cockpit is deployed (ADR 0012)

- The vendored OpenExecutive UI now serves the root (`/`) as the prototype
  shell, rebranded RED through the ADR 0011 overlay: metadata title, BrandMark,
  and 22 files of user-facing copy; the Auth.js gate is disabled (internal-only)
  and the `/api/backend` proxy treats every request as the principal, forwarding
  to the mounted OpenExecutive backend at `/openexecutive` with `x-api-key`.
- Navigation keeps the OpenExecutive groups and adds a RED Operations group
  linking the twelve section 8 screens, now served under `/screens` (the RED
  frontend builds with `NEXT_PUBLIC_RED_BASE_PATH=/screens`). The generic
  C-suite persona nav entries (Departments, People, Agent Council) are removed;
  the backend replacement with RED's agents remains a follow-up.
- Chart: `redop-cockpit` Deployment/Service; ingress `/red` -> api,
  `/screens` -> ui, `/api/backend` and `/` -> cockpit. CI builds
  `redop-cockpit` and syncs the chart templates into the GitOps repo.
- Verified live: `/` carries `RED Operations` (no `Open Executive`), `/screens`
  and `/screens/command-center` 200, `/api/backend/health` 200, `/red/health`
  200, health gate passes; Argo `redop` Synced/Healthy.
- Findings and follow-ups:
  - The Postgres password contained `/`, which broke `DATABASE_URL` parsing
    (psycopg read host `redops`) and alembic's configparser (`%2F`). Fixed by
    making the password URL-safe and escaping `%` for alembic (`_alembic_url`).
    The source SealedSecret `gitops/sealed/redop-postgres.yaml` still holds the
    old value and should be re-sealed.
  - The Gitea Actions runner OOM-kills the cockpit `next build`; the cockpit
    image was built locally and pushed via an in-cluster skopeo pod. The runner
    needs more memory (or `NODE_OPTIONS=--max-old-space-size`) before CI can
    build the cockpit.
  - The GitOps repo keeps its own chart copy; CI now syncs the templates, but
    the chart's source of truth is the app repo (ADR 0012).

### Owner directive 2026-10-05: navigation shell (Q51) and the cockpit-adoption vision (ADR 0012)

- The owner reported the deployed prototype had no navigable screens: the Q32
  home page listed the twelve section 8 screens as plain text, said they were
  "not yet implemented" (false), and nothing linked to them. Condition 6 only
  ever required each screen to exist with a browser test, so navigation was
  never built.
- Outcome (Q51): a landing dashboard and a persistent sidebar built from one
  source of truth (`frontend/src/shared/nav/screens.ts`), grouping the twelve
  screens by area (Command, Knowledge & Method, Commercial & Production,
  Governance, Delivery & Insight); the false copy is gone. `npm run build` and
  `npm test` (102 tests, +4) pass; `check_frontend_screens.sh` and
  `check_frontend_build.sh` pass.
- Declared vision (ADR 0012): adopt the vendored OpenExecutive cockpit UI as the
  prototype shell in a phase between the prototype DoD and production readiness -
  rebranded via the ADR 0011 overlay, navigation = OpenExecutive groups plus a
  RED Operations group, generic C-suite personas replaced with RED's agents,
  auth disabled internal-only, cockpit on its own OpenExecutive state. Recorded
  as the Cockpit adoption phase below; not part of the current prototype DoD.

### Deploy fix 2026-10-05: CI credentials, submodule init, overlay in the API image

- The first push to `atlas` failed CI at checkout: the repo's `REGISTRY_USER`/
  `REGISTRY_TOKEN` Actions secrets were stale (set 2026-10-03). Re-set them from
  the Argo CD repo token (`repo-gitea-atlas`); Gitea 1.27 expects the raw secret
  value, not base64.
- The next run failed building the API image: the CI checkout never initialized
  the vendored submodule, so `vendor/openexecutive/packages/core` was absent.
  Fixed by pointing `.gitmodules` at the public HTTPS upstream (the in-cluster
  runner reaches GitHub over HTTPS but has no SSH key), initializing the
  submodule in the workflow, and applying the ADR 0011 overlay inside
  `Dockerfile.api`.
- Result: build run 6 (`7744a1e`) succeeded, promoted `sha-7744a1e` into
  `apps/redop/chart/values.yaml`, and Argo CD synced `redop` to `8ba1add`
  (Synced/Healthy). The deployed UI now serves the navigation shell (all twelve
  links, no false copy); the health gate passes.
- Doc correction: the registry pull secret is `gitea-registry` (created from the
  sealed file `redop-registry.yaml`), not `redop-registry`.

### Owner directive 2026-10-05 (highest priority): comprehensive developer docs site

- **Directive (owner):** build and maintain a comprehensive developer
  documentation of the whole system — every noun and its significance to RED —
  excluding the vendored OpenExecutive internals but **including the vendor
  overlay script**. It must be easy to build and maintain and publish to GitHub
  Pages with a workflow. The owner marked it the highest priority, above the Q28
  stage 9/10 slices and the Q47-Q50 deploy slice.
- **Outcome:** a MkDocs Material site at the repo root (`mkdocs.yml`,
  `requirements-docs.txt`) with pages under `docs/`: `index.md`,
  `architecture/{overview,contexts,nouns,seams}.md`,
  `pipeline/{stages-and-gates,agents}.md`,
  `platform/{api,frontend,deploy,vendor-overlay}.md`,
  `operations/harness-and-tests.md`, `contributing.md`, plus the existing
  `DEVELOPER_GUIDE.md`, `context_map.md`, `fork_inventory.md`, all ADRs and all
  agent charters in the nav. The centrepiece `docs/architecture/nouns.md` defines
  every domain, architecture, pipeline, delivery, overlay and harness noun with
  its RED significance, in nineteen sections.
- **Ease and publishing:** `make docs` (strict build) and `make docs-serve`
  (live preview) via `uv run --with mkdocs-material`;
  `.github/workflows/docs.yml` builds on push to `main` (paths `docs/**`,
  `mkdocs.yml`) and deploys to GitHub Pages at
  `https://redrhino-online.github.io/red-operations-platform/`. New pages are
  auto-included; `validation.omitted_files: ignore` keeps the build clean.
- **Evidence:** `uv run --with mkdocs-material mkdocs build --strict` is clean
  (0 warnings). Vendor internals are excluded; `platform/vendor-overlay.md`
  documents the in-scope overlay (`vendor/overlay/`,
  `scripts/apply_vendor_overlay.sh`).
- **Maintenance rule:** a cycle that adds a noun (aggregate, seam, env var,
  pipeline concept) adds its row to `docs/architecture/nouns.md`.

### Cycle 2026-10-05T052159Z (this run)

- Cycle 2026-10-05T052159Z (Ralph cycle, this run): selected item was the
  last-mile of the Q49/Q50 deploy slice: make the RED chart's
  migration-before-serve ordering actually work on the live cluster so SPEC.md
  section 13 condition 9 passes. It is the highest value ready item because
  condition 9 is the only unmet prototype condition, the Argo CD Application
  already reconciles the RED chart, and the release was stuck one bug away from
  Healthy. It outranks all non-condition work and the production-readiness phase
  (which begins only after the first cluster release exists).
- Outcome: fixed the `wait-for-migration` initContainer in
  `deploy/charts/redop/templates/deployment-api.yaml`. It grepped the brittle
  `"succeeded":1`, but the Kubernetes API returns pretty-printed JSON
  (`"succeeded": 1` with a space), so the pattern never matched and the API pod
  hung in `Init:0/1` until the 600s deadline. The check now tolerates optional
  whitespace (`grep -Eq '"succeeded"[[:space:]]*:[[:space:]]*[1-9]'`). Added
  `test_wait_for_migration_tolerates_pretty_printed_job_json` to
  `tests/unit/shared/test_red_helm_chart.py`. Also restored the CI-promoted
  `apiTag`/`uiTag` (`v0.1.0-redop.1`) in the GitOps chart
  (`apps/redop/chart/values.yaml` in `atlas-admin/atlas`) after a chart copy
  clobbered them with empty strings, which had rendered `redop-api:0.1.0`
  (Chart.AppVersion) and caused `ImagePullBackOff` on the migration Job. The
  local chart keeps empty tags by design; the GitOps repo carries the promoted
  tags.
- Evidence: `make done` -> `DONE-GATE PASS: the prototype meets the section 13
  definition of done`; `[6/6] deployed RED app on Atlas k3s (Argo CD healthy;
  migration ran before the API served)`; `deployed RED health ok:
  https://redop.atlas.lan/ carries RED Operations`. Argo CD Application `redop`
  is `Synced`/`Healthy` at revision `b4595df`; the migration Job
  `redop-migrate-rj9t5` completed before the API pod became ready;
  `https://redop.atlas.lan/red/health` -> HTTP 200 `{"status":"ok"}`; the UI
  serves `<title>RED Operations Platform</title>` with the `RED Operations`
  marker. `make check` -> 2408 passed, 3 skipped, 741 subtests (was 2404; +4
  from the chart tests). `helm template` renders and `kubectl apply
  --dry-run=server` validates.
- New findings: the Kubernetes API server returns pretty-printed JSON for a
  plain `curl` GET with no `Accept` header, so any in-cluster JSON grep must
  tolerate whitespace. Argo CD PreSync hook Jobs are not re-rendered while a
  sync operation is stuck; aborting the operation
  (`DELETE /api/v1/applications/redop/operation`) and letting auto-sync re-run
  is what picked up the corrected revision. The `redop` Application uses
  `helm.valueFiles: [values.yaml]` under `apps/redop/chart`; the promoted tags
  live there, not in the app repo chart.
- Blockers: none for the prototype. Condition 9 is met and `make done` passes.
  The owner's "api + ui + worker" first-release scope still lacks a deployed
  RED worker entrypoint; tracked as W1 below, not a prototype condition.
- The prototype queue is complete, but post-prototype iteration is active by
  owner instruction: C4 is implemented and verified; G1-G9 track canon gaps;
  W1 tracks the worker scope and Q16 tracks stale-version conflict behavior.
  R1/R2 remain deferred and must not be picked up unattended.

### Cycle 2026-10-05T041656Z

- Cycle 2026-10-05T041656Z (Ralph cycle, this run): selected item was Q48, the
  RED Helm chart under `deploy/` (SPEC.md sections 6, 10 and 13 condition 9;
  owner decision 2026-10-04). It is the highest value ready item: condition 9 is
  the only unmet prototype condition, Q47 (images + CI) is met, and Q48 is the
  next smallest independently verifiable slice. It outranks Q49 (Argo CD
  Application) and Q50 (secrets + deployment smoke), which depend on it, and all
  non-condition work. It advances missing gate integrity and exact asset
  versions, which the cycle instructions rank first.
- Outcome: new chart `deploy/charts/redop/` (`Chart.yaml`, `values.yaml`,
  `templates/{_helpers.tpl,serviceaccount.yaml,migration-job.yaml,
  deployment-api.yaml,deployment-ui.yaml,deployment-worker.yaml,service.yaml,
  ingress.yaml,pdb.yaml,NOTES.txt}`). It replaces the OpenExecutive shell in
  namespace `redop` with the RED API and UI, reuses the existing
  `redop-postgres` database and `redop-secrets` (provisions no database), and
  routes `/red` to the API and `/` to the UI same-origin. Migration-before-serve
  is enforced three ways: the migration Job is a Helm pre-install/pre-upgrade
  hook at weight -5 and an Argo CD PreSync hook at sync-wave -1; the API
  Deployment is sync-wave 0; and the API has a `wait-for-migration` initContainer
  that polls the Job's success through the Kubernetes API (new ServiceAccount,
  Role and RoleBinding granting `get` on jobs only). The worker Deployment is
  present but `worker.enabled: false` by default because no RED worker entrypoint
  exists yet (plan line 886); enabling it before the entrypoint lands would
  crashloop and break the Argo CD health condition 9 requires. New
  `tests/unit/shared/test_red_helm_chart.py` (8 tests: structural guards plus
  `helm template` render assertions, skipped when helm is absent).
- Evidence: `helm lint deploy/charts/redop` -> 0 failed; `helm template redop
  deploy/charts/redop --namespace redop` exit 0; `kubectl apply --dry-run=server`
  on the rendered manifests validates every resource against the live cluster
  (PDB, ServiceAccount, Role, RoleBinding, Service, Deployment, Ingress,
  Middleware, Job) with no schema errors; `make check` -> 2404 passed, 3 skipped,
  741 subtests (was 2396; +8); `uv run pyflakes` clean. `make done` still stops
  at `[6/6]`: `redop.atlas.lan` still serves the OpenExecutive shell, so
  condition 9 is honestly unmet.
- New findings: the live `redop` namespace already has the `redop-ipallow`
  Traefik Middleware (`10.0.0.0/8`), the `redop-tls` secret, the `redop-data`
  PVC and the `redop-postgres` Deployment/Service/secret; the chart reproduces
  the middleware and reuses the rest. The existing ingress routes only `/` to
  the UI; the RED chart adds the `/red` API path. The API image already carries
  `alembic` and `alembic.ini`, so the migration Job needs no extra image.
- Blockers: condition 9 remains unmet. Q49 (Argo CD Application pointing at the
  RED chart with migration-before-serve ordering) and Q50 (secrets,
  `REDOP_HEALTH_URL` and the deployment smoke) follow. The worker entrypoint is
  still missing, so the owner's "api + ui + worker" first-release scope is only
  two-thirds deployable; record it as a candidate item, not a silent omission.
- Highest priority ready next item: Q49, the Argo CD Application (SPEC.md
  section 10; owner decision 2026-10-04). Prerequisites: Q48 met. Required
  artifact: an Application (or GitOps repo chart source) that reconciles
  `deploy/charts/redop` into namespace `redop` with the migration Job ordered
  before the API serves. Checkpoint: Argo CD reports the release Synced/Healthy
  and the migration Job ran before the API served. Approver: the RED principal
  for the cluster release. Blocked downstream dependency: Q50 and condition 9.

### Cycle 2026-10-05T040540Z

- Cycle 2026-10-05T040540Z (Ralph cycle, this run): selected item was Q47, the
  RED API and UI container images plus the Gitea build/promote workflow (SPEC.md
  sections 10 and 13 condition 9; owner decision 2026-10-04). It is the highest
  value ready item: condition 9 is the only unmet prototype condition, and Q47 is
  its first and smallest independently verifiable slice. The owner decision
  unblocked the whole Q47-Q50 slice for the build loop, and the loop now has
  cluster access (kubectl via the git-ignored `.env` `KUBECONFIG`), a working
  Docker daemon and a reachable registry, so the prior "no cluster context"
  blocker is stale. It outranks Q48-Q50 (larger, follow this slice) and all
  non-condition work.
- Outcome: new `Dockerfile.api` (python:3.12-slim; `uv sync --locked` from the
  committed root lock with the editable OpenExecutive source present;
  `PYTHONPATH=/app/backend`; `uvicorn redops.api.app:app`), `Dockerfile.ui`
  (node:22-alpine multi-stage Next.js standalone), `.dockerignore` (keeps the
  pinned submodule's ~1.9 GB local `.venv` and tool caches out of the build
  context), `.gitea/workflows/build.yaml` (modeled on the platform reference
  workflow `examples/demo-app/.gitea/workflows/build.yaml`; builds and pushes
  `redop-api` and `redop-ui` to `registry.atlas.lan` and promotes `apiTag`/
  `uiTag` into `apps/redop/chart/values.yaml` in the Gitea GitOps repo
  `atlas-admin/atlas`), and `tests/unit/shared/test_deploy_artifacts.py` (six
  structural guards). No domain, gate, approval, pipeline stage, vendored file,
  migration or method artifact changed.
- Evidence: `docker build -f Dockerfile.api` exit 0; the container's
  `/red/health` returns `{"status":"ok"}` HTTP 200; `docker build -f
  Dockerfile.ui` exit 0; the UI container's `/` returns `<title>RED Operations
  Platform</title>` and carries the `RED Operations` marker; `make check` ->
  2396 passed, 3 skipped, 741 subtests (was 2390; +6); `uv run pyflakes` clean.
  `make done` still stops at `[6/6]`: `redop.atlas.lan` still serves the
  OpenExecutive shell (`<title>Open Executive</title>`, no RED marker), so
  condition 9 is honestly unmet.
- New findings: the Atlas cluster is reachable from the loop and the existing
  `redop` deployment is the OpenExecutive shell (images
  `registry.atlas.lan/atlas-admin/redop-api|redop-ui:v0.4.6-redop.2`) with an
  Argo CD Application `redop` Synced/Healthy pointing at Gitea
  `atlas-admin/atlas` path `apps/redop/chart`; the existing chart is
  `apps/redop/chart` in the GitOps repo and already exposes `apiTag`/`uiTag`.
  The reference build/promote workflow is
  `examples/demo-app/.gitea/workflows/build.yaml`. The workflow cannot be
  exercised unattended because the harness publishes the `atlas` remote only on
  the final loop cycle; the images themselves are verified locally.
- Blockers: condition 9 remains unmet. Q48 (RED Helm chart under `deploy/`,
  replacing the OpenExecutive chart in the same namespace/ingress/release), Q49
  (Argo CD Application with migration-before-serve ordering) and Q50 (secrets,
  `REDOP_HEALTH_URL` and the deployment smoke) follow. No prototype condition
  other than 9 is unmet.
- Highest priority ready next item: Q48, the RED Helm chart (SPEC.md section 10;
  owner decision 2026-10-04). Prerequisites: Q47 met. Required artifact: a chart
  with api/ui/worker, a migration Job that runs before the API serves, ingress,
  probes, PDB, resources, reusing the existing `redop-postgres` and
  `redop-secrets`. Checkpoint: `helm template` renders and the migration-before-
  serve ordering is enforced. Approver: the RED principal for the cluster
  release. Blocked downstream dependency: Q49/Q50 and condition 9.

### Cycle 2026-10-05T034410Z

- Cycle 2026-10-05T034410Z (Ralph cycle, this run): selected item was the last
  slice of Q28: wire the canon follow-up and nurture lifecycle as a required
  stage 10 "Performance Baseline Established" kind (SPEC.md sections 4, 12.3 and
  12.5; canon files 15, 24, 33 and 34; owner decision 2026-10-04, P2). It is the
  smallest independently verifiable ready item and it completes the Q28
  required-kind policy: every canon-informed asset already implemented in a
  bounded context is now a required kind of its target stage gate. It outranks
  the Q47-Q50 deploy slice (condition 9), which is not a single bounded item and
  cannot be verified unattended because the harness publishes `atlas` only on the
  final loop cycle. It advances missing gate integrity and exact asset versions,
  which the cycle instructions rank first.
- Outcome: `NurturePlan` gained `NURTURE_PLAN_KIND = "nurture-plan"` and
  `as_stage_asset(version=)`, which refuses a version below 1 with the existing
  named `InvalidNurtureError`. The kind joined `CANONICAL_BASELINE_KINDS` (12 ->
  13) and the stage 10 `StageTemplate` package. `PerformanceBaselinePackage`
  gained same-tenant typed `nurture` plus a positive `nurture_version`,
  projecting the `nurture-plan` kind from the plan's own identity and version
  (not the baseline identity). `RecordStageTenGateRequest` gained `nurture` (a
  `NurturePlanInput` with nested sequence and message inputs) and
  `nurture_version`; the stage 10 route rebuilds the reviewed `NurturePlan` over
  the approved stage 4 Signature Solution the route already rebuilds, so a stage
  10 gate cannot pass without a reviewed, same-tenant follow-up lifecycle. This
  is an asset inside an existing stage, never a new or renamed stage (owner
  decision 2026-10-04).
- Evidence: `tests/unit/commercial/test_nurture_lifecycle.py` (`as_stage_asset`
  identity and version refusal), `tests/unit/execution/test_performance_baseline_package.py`
  (thirteen kinds, nurture identity/version, cross-tenant and versionless
  refusal), `tests/unit/engagement/test_record_stage_ten_gate.py` (thirteen pins),
  `tests/unit/test_stage_ten_gate_route.py` and
  `tests/e2e/test_stage_zero_to_ten_e2e.py` (stage 10 payload carries the nurture
  plan) all green. `make check` -> 2390 passed, 3 skipped, 741 subtests;
  `uv run pyflakes backend tests` clean. `make done` passes `[1/6]` through
  `[5/6]` and stops at `[6/6]`: the deployed RED health check still fails because
  `redop.atlas.lan` serves OpenExecutive, not RED.
- New findings: the Q28 required-kind policy is now fully applied across stages
  1-10; no canon-informed asset remains unwired. The only remaining prototype
  condition is 9 (deploy), which needs image builds, a Helm chart and an Argo
  Application and cannot be verified unattended.
- Blockers (head unchanged): condition 9's deploy slice (Q47-Q50) needs image
  builds, a Helm chart and an Argo Application, and the harness publishes `atlas`
  only on the final loop cycle, so no unattended cycle can verify the deploy.
  Condition 5 is met (operator ran the live smoke 2026-10-04). No prototype
  condition other than 9 is unmet.
- Highest priority ready next item: the Q47-Q50 deploy slice (condition 9;
  SPEC.md sections 10 and 13). Prerequisites: a Dockerfile plus health endpoint
  (Q47), a Helm chart (Q48), an Argo CD Application with migration-before-serve
  ordering (Q49), secrets plus `REDOP_HEALTH_URL` and the deployment smoke (Q50).
  Checkpoint: `make done` `[6/6]` passes against a RED image on Atlas. Approver:
  the RED principal for the cluster release. Blocked downstream dependency: none
  in the prototype; the production-readiness phase (R1/R2) begins once the first
  cluster release exists.

### Cycle 2026-10-05T030017Z

- Cycle 2026-10-05T030017Z (Ralph cycle, this run): selected item was the next
  slice of Q28 after the 2026-10-04 methodology-owner placement decision: wire the
  canon client-authored enrollment process as a required stage 9 "Launch Approved"
  kind (SPEC.md sections 4, 12.5 and 12.7; canon files 35-49; owner decision
  2026-10-04, E2). It is the smallest independently verifiable ready item. It
  outranks the stage 10 `nurture-plan` slice because it closes the last stage 9
  canon kind and completes the stage 9 required-kind set, and it outranks the
  Q47-Q50 deploy slice (condition 9), which is not a single bounded item and
  cannot be verified unattended. It advances missing gate integrity and exact
  asset versions, which the cycle instructions rank first.
- Outcome: `ClientProcess` gained `CLIENT_PROCESS_KIND = "client-process"` and
  `as_stage_asset(version=)`, which refuses a version below 1 with the existing
  named `InvalidClientProcessError`. The kind joined `CANONICAL_LAUNCH_KINDS`
  (19 -> 20) and the stage 9 `StageTemplate` package. `LaunchQAPackage` gained
  same-tenant typed `client_process` plus a positive `client_process_version`,
  projecting the `client-process` kind from the process's own identity and version
  (not the QA identity). `RecordStageNineGateRequest` gained `product_program`
  (the stage 5 `ProductProgramInput`, because `ClientProcess` grounds on the stage
  5 program the stage 9 route did not previously rebuild), `client_process` and
  `client_process_version`; the stage 9 route rebuilds the reviewed
  `ClientProcess` over the approved stage 2 primary currency, stage 3 diagnostic
  model, stage 4 Signature Solution and the rebuilt stage 5 product program, so a
  stage 9 gate cannot pass without a reviewed, same-tenant client process. This is
  an asset inside an existing stage, never a new or renamed stage (owner decision
  2026-10-04).
- Evidence: `tests/unit/execution/test_client_process.py` (`as_stage_asset`
  identity and version refusal), `tests/unit/execution/test_launch_qa_package.py`
  (twenty kinds, client-process identity/version, cross-tenant and versionless
  refusal), `tests/unit/engagement/test_record_stage_nine_gate.py` (twenty pins),
  `tests/unit/test_stage_nine_gate_route.py` and `test_stage_ten_gate_route.py`
  and `tests/e2e/test_stage_zero_to_ten_e2e.py` (stage 9 payload carries the
  product program and client process) all green. `make check` -> 2385 passed, 3
  skipped, 737 subtests; `uv run pyflakes backend/redops tests` clean. `make done`
  passes `[1/6]` through `[5/6]` and stops at `[6/6]`: the deployed RED health
  check still fails because `redop.atlas.lan` serves OpenExecutive, not RED.
- New findings: the `ClientProcess` class docstring previously asserted it was
  "not a new required gate kind"; the 2026-10-04 owner decision E2 supersedes that
  and the docstring now records the stage 9 placement. The stage 9 required-kind
  set is now complete (twenty kinds). The only remaining Q28 wiring is the stage
  10 `nurture-plan` kind (a Commercial Design asset, cross-context), or the
  Q47-Q50 deploy slice.
- Blockers (head unchanged): condition 9's deploy slice (Q47-Q50) needs image
  builds, a Helm chart and an Argo Application, and the harness publishes `atlas`
  only on the final loop cycle, so no unattended cycle can verify the deploy.
  Condition 5 is met (operator ran the live smoke 2026-10-04). No prototype
  condition other than 9 is unmet.
- Highest priority ready next item: the stage 10 `nurture-plan` Q28 slice
  (SPEC.md sections 4, 12.3 and 12.5; owner decision 2026-10-04, P2). Prerequisites:
  a `NurturePlan` asset in the Commercial Design context with its policy and
  `as_stage_asset(version=)` projection, the `CANONICAL_LAUNCH_KINDS`-equivalent
  stage 10 kind set and stage 10 `StageTemplate` addition, a `NurturePlanInput`
  schema on the stage 10 request, the route builder, and gate-integrity tests
  pinning the exact version. Checkpoint: the stage 10 gate pins all required kinds
  from typed, same-tenant, versioned assets and refuses a missing or foreign plan.
  Approver: the client-designated authority on the gate. Blocked downstream
  dependency: condition 9's deploy slice. Alternative ready item if the
  cross-context payload must be avoided: the Q47-Q50 deploy slice.

### Cycle 2026-10-05T023927Z (this run)

- Cycle 2026-10-05T023927Z (Ralph cycle, this run): selected item was the
  smallest independently verifiable slice of the Q28 stage 9 work: wire the canon
  enrollment and sales call as a required stage 9 "Launch Approved" kind
  (SPEC.md sections 4, 12.3 and 12.5; canon files 00, 06, 13, 14, 21 and 24;
  owner decision 2026-10-04, E2). It outranks the combined
  `client-process` + `enrollment-plan` slice because `ClientProcess` grounds on
  the stage 2/3/5 Commercial assets (`PrimaryCurrency`, `DiagnosticModel`,
  `ProductProgram`) that the stage 9 request does not yet carry, so it needs a new
  cross-context `ProductProgram` payload; the enrollment half grounds only on the
  completed stage 8 funnel and the approved stage 4 Signature Solution, both
  already rebuilt by the stage 9 route. It also outranks the stage 10
  `nurture-plan` slice and condition 9's deploy slice (Q47-Q50), which is not a
  single bounded item. It advances missing gate integrity and exact asset
  versions, which the cycle instructions rank first.
- Outcome: `CANONICAL_LAUNCH_KINDS` grew by `enrollment-plan` (18 -> 19), and
  `LaunchQAPackage` gained same-tenant typed `enrollment` plus a positive
  `enrollment_version`, projecting the `enrollment-plan` kind from the plan's own
  identity and version (not the QA identity). `EnrollmentPlan` gained
  `ENROLLMENT_PLAN_KIND` and `as_stage_asset(version=)`. The kind was added to the
  stage 9 `StageTemplate` package, and `RecordStageNineGateRequest` gained
  `enrollment` and `enrollment_version`; the stage 9 route rebuilds the reviewed
  `EnrollmentPlan` over the same completed stage 8 funnel and the approved stage 4
  Signature Solution, so a stage 9 gate cannot pass without a reviewed,
  same-tenant enrollment and sales call. This is an asset inside an existing
  stage, never a new or renamed stage (owner decision 2026-10-04).
- Evidence: `tests/unit/execution/test_launch_qa_package.py` (nineteen kinds,
  enrollment identity/version, cross-tenant and versionless refusal),
  `tests/unit/engagement/test_record_stage_nine_gate.py` (nineteen pins),
  `tests/unit/test_stage_nine_gate_route.py` and `test_stage_ten_gate_route.py`
  and `tests/e2e/test_stage_zero_to_ten_e2e.py` (stage 9 payload carries the
  enrollment plan) all green. `make check` -> 2380 passed, 3 skipped, 732
  subtests; `uv run pyflakes backend/redops tests` clean. `make done` passes
  `[1/6]` through `[5/6]` and stops at `[6/6]`: the deployed RED health check
  still fails because `redop.atlas.lan` serves OpenExecutive, not RED.
- New findings: the `EnrollmentPlan` class docstring now records the E2 placement
  (it previously asserted "not a new required gate kind"). The `ClientProcess`
  docstring still asserts the same and must be updated when that kind is wired.
  The stage 9 `client-process` kind remains; it needs a new `ProductProgram`
  request payload because `ClientProcess` grounds on stage 2/3/5 Commercial
  assets the stage 9 route does not rebuild. The remaining Q28 wiring after this
  cycle: stage 9 `client-process`, and stage 10 `nurture-plan` (cross-context,
  Commercial) or the Q47-Q50 deploy slice.
- Blockers (head unchanged): condition 9's deploy slice (Q47-Q50) needs image
  builds, a Helm chart and an Argo Application, and the harness publishes `atlas`
  only on the final loop cycle, so no unattended cycle can verify the deploy.
  Condition 5 is met (operator ran the live smoke 2026-10-04). No prototype
  condition other than 9 is unmet.
- Highest priority ready next item: the stage 9 `client-process` Q28 slice
  (SPEC.md sections 4, 12.5 and 12.7; owner decision 2026-10-04, E2).
  Prerequisites: `ClientProcess` already exists in the Execution context with its
  policy; required artifacts are the `as_stage_asset(version=)` projection and
  kind constant, the `CANONICAL_LAUNCH_KINDS`/stage 9 template additions, a new
  `ClientProcessInput` schema plus a `ProductProgramInput` on the stage 9 request
  (rebuilding the grounded stage 2/3/5 Commercial assets), the route builder, and
  gate-integrity tests pinning the exact version. Checkpoint: the stage 9 gate
  pins all required kinds from typed, same-tenant, versioned assets and refuses a
  missing or foreign process. Approver: the client-designated authority on the
  gate. Blocked downstream dependency: the stage 10 `nurture-plan` slice and then
  condition 9's deploy slice. Alternative ready item if the larger cross-context
  payload must be avoided: the narrower stage 10 `nurture-plan` slice.

### Cycle 2026-10-05T015336Z

- Cycle 2026-10-05T015336Z (Ralph cycle, this run): selected item was the next
  slice of Q28 after the 2026-10-04 methodology-owner placement decision: wire the
  canon Swimlanes channel model as a required stage 9 "Launch Approved" kind
  (SPEC.md sections 4, 12.3 and 12.5; canon files 13, 14, 33 and 34). It is the
  smallest independently verifiable ready item. It outranks the alternative
  condition 9 deploy slice because that slice is not a single bounded item: the
  repo still has no Dockerfile, Helm chart or Argo Application, the API image
  pulls in the vendored 1.9 GB `openexecutive` core with torch, chromadb and
  sentence-transformers, and the harness pushes the `atlas` remote only on the
  final cycle, so no unattended cycle can build and verify the deploy. Cluster
  access (kubectl, `registry.atlas.lan`, Gitea) is now reachable, but building the
  multi-GB image and promoting it is a multi-cycle effort (Q47-Q50). It also
  outranks the stage 9 `enrollment-plan`/`client-process` halves, which need new
  cross-context request schemas (currency, model, program rebuild) and the
  stage 10 `nurture-plan` slice. It advances missing gate integrity and exact
  asset versions, which the cycle instructions rank first.
- Outcome: `CANONICAL_LAUNCH_KINDS` grew by `swimlanes-plan`, and
  `LaunchQAPackage` gained same-tenant typed `swimlanes` plus a positive
  `swimlanes_version`, projecting the `swimlanes-plan` kind from the plan's own
  identity and version (not the QA identity). The kind was added to the stage 9
  `StageTemplate` package, and `RecordStageNineGateRequest` gained `swimlanes`
  and `swimlanes_version`; the stage 9 route rebuilds the reviewed
  `SwimlanesPlan` over the same completed stage 8 funnel (reusing the stage 8
  pattern), so a stage 9 gate cannot pass without a reviewed, same-tenant
  recovery strategy. This is an asset inside an existing stage, never a new or
  renamed stage (owner decision 2026-10-04).
- Evidence: `tests/unit/execution/test_launch_qa_package.py` (eighteen kinds,
  swimlanes identity/version, cross-tenant and versionless refusal),
  `tests/unit/engagement/test_record_stage_nine_gate.py` (eighteen pins),
  `tests/unit/test_stage_nine_gate_route.py` and `test_stage_ten_gate_route.py`
  and `tests/e2e/test_stage_zero_to_ten_e2e.py` (stage 9 payload carries the
  swimlanes plan) all green. `make check` -> 2377 passed, 3 skipped, 730
  subtests; `uv run pyflakes backend/redops tests` clean. `make done` passes
  `[1/6]` through `[5/6]` and stops at `[6/6]`: the deployed RED health check
  still fails because `redop.atlas.lan` serves OpenExecutive, not RED.
- New findings: the `EnrollmentPlan` and `ClientProcess` class docstrings still
  assert they are "not a new required gate kind"; the 2026-10-04 owner decision
  E2 supersedes that for stage 9, so those docstrings must be updated when those
  two kinds are wired. The stage 9 `enrollment-plan` and `client-process` kinds
  remain; they need new request schemas because no durable stores exist for the
  plans and `ClientProcess` grounds on stage 2/3/5 Commercial assets that the
  stage 9 route would have to rebuild. The remaining Q28 wiring after this cycle:
  stage 9 `enrollment-plan` and `client-process`, and stage 10 `nurture-plan`
  (cross-context, Commercial) or the Q47-Q50 deploy slice.
- Blockers (head unchanged): condition 9's deploy slice (Q47-Q50) needs image
  builds, a Helm chart and an Argo Application, and the harness publishes `atlas`
  only on the final loop cycle, so no unattended cycle can verify the deploy.
  Condition 5 is met (operator ran the live smoke 2026-10-04). No prototype
  condition other than 9 is unmet.
- Highest priority ready next item: the stage 9 `client-process` +
  `enrollment-plan` Q28 slice (SPEC.md sections 4, 12.5 and 12.7; owner decision
  2026-10-04, E2). Prerequisites: `EnrollmentPlan` and `ClientProcess` already
  exist in the Execution context with their policies; required artifacts are the
  two `as_stage_asset(version=)` projections and kind constants, the
  `CANONICAL_LAUNCH_KINDS`/stage 9 template additions, the new
  `RecordStageNineGateRequest` schemas plus route builders (rebuilding the
  grounded Commercial assets), and gate-integrity tests pinning exact versions.
  Checkpoint: the stage 9 gate pins all required kinds from typed, same-tenant,
  versioned assets and refuses a missing or foreign plan. Approver: the
  client-designated authority on the gate. Blocked downstream dependency: the
  stage 10 `nurture-plan` slice and then condition 9's deploy slice. Alternative
  ready item if the larger cross-context payload must be avoided: the narrower
  stage 10 `nurture-plan` slice.

### Owner decision 2026-10-04: Atlas deploy architecture (Q47-Q50)

- The operator settled the deploy architecture (app repo issue #3), unblocking
  the whole Q47-Q50 slice:
  1. Execution: the build loop runs Q47-Q50 end-to-end with cluster access
     (kubectl + registry + Gitea push), then verifies condition 9; the operator
     reviews after.
  2. Image build: Gitea Actions on the app repo (`atlas-admin/red-operations-platform`);
     a push to the `atlas` remote triggers the build and pushes to
     `registry.atlas.lan`.
  3. Condition 9 surface: deploy the RED UI + API so `/` carries the
     `RED Operations` marker `scripts/check_deployed_red_health.sh` requires.
  4. PostgreSQL: in-cluster Postgres on the `truenas-nfs` storage class
     (StatefulSet + PVC); the migration Job runs before the API serves.
  5. Release topology: replace the OpenExecutive shell in namespace `redop`
     (same namespace, ingress and release name; new chart source).
  6. Secrets: reuse the existing `redop-secrets` (`BACKEND_SHARED_SECRET`,
     `AUTH_SECRET`, `OPENROUTER_API_KEY`) and `gitea-registry` (registry pull;
     created from the sealed file `redop-registry.yaml`).
  7. First-release scope: api + ui + worker (full chart including migration Job,
     ingress, PDB, probes).
- Prerequisites for end-to-end execution: kubectl on PATH and
  `KUBECONFIG=~/.kube/atlas-admin.yaml` in the harness environment; the `atlas`
  remote configured (it is); a Gitea Actions workflow plus registry push
  credentials in the app repo (Q47 adds `.gitea/workflows/build.yaml`; the
  existing `atlas-admin/redop` workflow is the reference); write access to the
  GitOps repo (`211lab/atlas`) for the digest/values update, or the operator
  performs that promotion (SPEC.md section 10 manual approval).
- Effect: Q47 is now executable as the next ready item; Q48-Q50 follow. Condition
  9 remains the only prototype condition not met.
- Q47/Q48 implementation choices (2026-10-04): reuse the `redop-api`/`redop-ui`
  image names; semver release tags (`v0.1.0-redop.N`); build on push to `main`
  (the `atlas` remote) with an automatic GitOps digest update in `211lab/atlas`
  (note: the harness pushes `atlas` only on the final cycle of a `make loop`, so
  use `make loop` or push `atlas` to trigger CI); same-origin ingress routing
  (`/red/*` -> api, `/` -> ui, `NEXT_PUBLIC_RED_API_BASE` empty); API on
  `python:3.12-slim` built with `uv`, UI on `node:22-alpine` Next standalone;
  in-cluster Postgres 16 with a 10Gi `truenas-nfs` PVC. Loop cluster access is
  provided via the git-ignored `.env` (`KUBECONFIG=~/.kube/atlas-admin.yaml`,
  `~/.local/bin` on PATH); verified `kubectl -n redop` reaches the cluster.
- Additional deploy choices (2026-10-04): Argo CD auto-sync + self-heal; reuse
  the `redop.atlas.lan` ingress with `atlas-ca` TLS and the `10.0.0.0/8`
  allowlist; one replica each for api/ui/worker with small requests; **reuse the
  existing `redop-postgres`** in namespace `redop` (Deployment
  `postgres:16.4-alpine`, Service `redop-postgres:5432`, 10Gi `truenas-nfs` PVC,
  secret `redop-postgres` with `DATABASE_URL`) so Q48 provisions no new
  database; the migration Job runs on every deploy (idempotent, ADR 0010); object
  storage deferred; prototype auth disabled and internal-only. Retention/export/
  deletion policy and the identity provider are deferred to the production phase.

### Owner decision 2026-10-04: Q28 stage 8-10 required-kind placement

- The methodology owner ruled (app repo issue #6): **E2** - `EnrollmentPlan` and
  `ClientProcess` become required kinds of the **stage 9 Launch Approved** gate;
  **P2** (interpreted as P1 plus NurturePlan) - `SwimlanesPlan` is wired into the
  stage 8/9 gates and `NurturePlan` becomes a required kind of the **stage 10
  Performance Baseline Established** gate. Post-stage-10 Serve/Grow portfolio
  effects stay out of required kinds (Portfolio context).
- Effect: Q28 is now unblocked and fully specified; the next cycle wires
  `enrollment-plan`, `client-process`, `swimlanes-plan` and `nurture-plan` as
  required kinds pinned from their typed assets with gate-integrity tests. The
  only other open prototype item is the Q47-Q50 deploy slice (condition 9).

### Cycle 2026-10-05T011149Z (this run)

- Cycle 2026-10-05T011149Z (Ralph cycle, this run): selected item was the first
  slice of Q28 after the 2026-10-04 methodology-owner placement decision: wire the
  canon Swimlanes channel model as a required stage 8 "Funnel Complete" kind
  (SPEC.md sections 4, 12.3 and 12.5; canon files 13, 14, 33 and 34). It is the
  highest value ready item. It has no prerequisite: the owner ruled the placement
  on 2026-10-04, the `SwimlanesPlan` asset and its policy already exist in the
  Execution context, and the stage 8 gate, template and route already exist. It
  advances missing gate integrity and exact asset versions, which the cycle
  instructions rank above the downstream deploy feature Q47-Q50 and above
  dashboards. It outranks the alternatives: Q47-Q50 (the only other open
  prototype item, condition 9) is deploy tooling that cannot be completed or
  verified unattended here (no dry-run cluster apply, no image push, and the
  loop must not alter external systems); Q4 needs a live key; the remaining Q28
  stage 9 (enrollment-plan, client-process, swimlanes-plan) and stage 10
  (nurture-plan) slices are larger and follow this pattern; the canon gap
  register has no smaller ready pipeline item.
- Outcome: `SwimlanesPlan` gained `SWIMLANES_PLAN_KIND = "swimlanes-plan"` and
  `as_stage_asset(version=)`, which refuses a version below 1 with the existing
  named `InvalidSwimlanesError`. The kind was added to `CANONICAL_FUNNEL_KINDS`
  and to the stage 8 template package, and stage 8's reviewed
  `FunnelIntegrationPackage` now carries a typed same-tenant `SwimlanesPlan` plus
  a positive `swimlanes_version` and projects the `swimlanes-plan` kind from the
  plan's own identity (tenant- and version-checked) rather than from the funnel,
  because the recovery plan is a distinct asset. The stage 8 gate request schema
  (`SwimlaneMoveInput`, `SwimlanesPlanInput`) and `record_stage_eight_gate` build
  and validate the plan over the same completed funnel, so a stage 8 gate cannot
  pass without a reviewed, same-tenant recovery strategy. The change is an asset
  inside an existing stage, not a new or renamed stage, per the owner decision.
- Evidence: new/updated behavioral tests in
  `tests/unit/execution/test_swimlanes.py` (`as_stage_asset` identity and
  version refusal), `tests/unit/execution/test_funnel_integration_package.py`
  (fourteen canonical kinds, per-asset versions and identity, cross-tenant and
  versionless swimlanes refusal), and
  `tests/unit/engagement/test_record_stage_eight_gate.py` (fourteen pins,
  per-kind versions); `tests/unit/test_stage_eight_gate_route.py` now posts the
  swimlanes plan and the stage 9/10 route tests and the stage 0-10 e2e reuse that
  payload. `make check` -> 2374 passed, 3 skipped, 728 subtests, `uv run pyflakes`
  clean. `make done` still stops before condition 9 (the Atlas deploy); condition
  9 is unchanged and unmet.
- New findings: the `SwimlanesPlan` class docstring and `test_swimlanes.py`
  previously asserted the plan was deliberately "not a required gate kind"; the
  2026-10-04 owner decision supersedes that stance, so both now record the
  required-kind placement. The remaining Q28 wiring is stage 9 (`enrollment-plan`,
  `client-process` and the same `swimlanes-plan` kind, all Execution-context
  assets) and stage 10 (`nurture-plan`, a Commercial Design asset), each an
  independent slice that follows this established bridge-and-package pattern.
- Blockers (head unchanged): condition 5's live OpenRouter smoke needs
  `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1` (Q4). Condition 9
  fails honestly because the Atlas host serves OpenExecutive, not RED; the
  Q47-Q50 deploy slice and a cluster context are operator work and out of an
  unattended cycle's scope.
- Highest priority ready next item: the stage 9 Q28 slice, wire
  `EnrollmentPlan` and `ClientProcess` (and the stage 9 `swimlanes-plan`) as
  required kinds of the stage 9 "Launch Approved" gate (SPEC.md sections 4 and
  12.5; owner decision 2026-10-04, E2). Required artifacts: the stage 9
  `LaunchQAPackage` bridge gains the typed plans (each with a positive version)
  and projects their kinds from their own identities, the stage 9 template and
  `RecordStageNineGateRequest` gain the corresponding fields and route builders,
  and gate-integrity tests pin the exact versions. Checkpoint: the stage 9 gate
  pins all required kinds from typed, same-tenant, versioned assets and refuses a
  missing or foreign plan. Approver: the client-designated authority on the gate
  (unchanged); the placement itself is already owner-decided. Blocked downstream
  dependency: the stage 10 `nurture-plan` slice and then condition 9's deploy
  slice. Alternative unblocker if a cycle must avoid the larger stage 9 payload:
  the stage 10 `nurture-plan` slice, smaller but cross-context (Commercial into
  Execution). No unattended alternative exists for the live key or the deploy.

### Operator input 2026-10-04: live OpenRouter smoke executed; condition 5 met (Q4 done)

- The operator supplied the OpenRouter key (stored in the cluster secret
  `redop-secrets` in namespace `redop`); it was copied into the git-ignored
  `.env` (`OPENROUTER_API_KEY` only; `.gitignore` covers `.env`, the key is
  never committed). `REDOP_LIVE_OPENROUTER_SMOKE` is deliberately not set in
  `.env`, so unattended cycles do not spend.
- Evidence: `REDOP_LIVE_OPENROUTER_SMOKE=1 uv run pytest
  tests/unit/agents/test_live_openrouter_smoke.py -q` -> 1 passed (one live
  call through `ForkProviderModelGateway.from_fork_registry()` plus
  `LoggingModelGateway`, asserting the section 6 attribution).
  `tests/unit/agents/covered-provider-paths.txt` now declares
  `live-openrouter-smoke` covered; `scripts/check_provider_path_coverage.sh`
  -> "provider path coverage ok: 3 condition 5 parts declared with tests";
  the provider-path honesty test was updated to pin the passing state.
- Effect on the queue: condition 5 is met. `make done` now passes `[1/6]`
  through `[5/6]` (2370+ tests green, frontend builds, overlay ok) and fails
  only at `[6/6]`: condition 9, the Atlas deployment. The head blocker is now
  the Q47-Q50 deploy slice alone. Q28 (methodology-owner placement decision)
  remains the only other open item, plus the production-readiness drills R1/R2.

### Cycle 2026-10-04T050209Z (this run)

- Cycle 2026-10-04T050209Z (Ralph cycle, this run): selected item was
  hardening the prototype definition-of-done condition 9 gate (SPEC.md section 13
  condition 9). It is the highest value ready item: `make done` was run and it
  stops at `[2/6]` on condition 5 (the paid live OpenRouter smoke, Q4, needs a
  real key); conditions 1, 2 and 5's deterministic half pass. While reassessing,
  the `[6/6]` deployed-health check was found to pass on any HTTP 200. The Atlas
  host `redop.atlas.lan` actually serves the OpenExecutive shell: `<title>Open
  Executive</title>` and no RED route (`/red/health`, `/command-center`,
  `/client-workspace`, `/authority-settings`, `/launch-readiness`,
  `/source-explorer` all return 404). So condition 9 was a false pass. Fixing
  that false pass is a missing-gate-integrity defect and outranks the deploy
  artifacts Q47-Q50 (the repo still has no Dockerfile or `deploy/`; the deployed
  app is not RED) and the non-ready alternatives: Q28 stages 8-10 required kinds
  stay blocked on the named methodology-owner placement decision; Q4 needs a live
  key; Q47-Q50 need a RED image, Helm chart and Argo Application, which are build
  and deploy work the cycle may not perform unattended (no cluster context;
  `kubectl` has none; deploy is out of scope). The canon gap register has no
  ready pipeline item.
- Outcome: new `scripts/check_deployed_red_health.sh` replaces the bare curl in
  DoD `[6/6]`. It fetches `REDOP_HEALTH_URL` (default
  `https://redop.atlas.lan/`) and requires the response body to carry the RED
  identity marker `RED Operations` (`REDOP_RED_MARKER` overrides it), failing on
  a non-2xx response or a body without the marker. A wrong app or any bare 200
  can no longer certify condition 9. The Makefile and `.env.example` comments now
  state the marker requirement. No route, gate rule, approval authority, pipeline
  stage, vendored file, migration or method artifact changed.
- Evidence: new `tests/unit/shared/test_deployed_health_check.py` (4 tests) runs
  the gate script against a local stub server: a RED body passes, and an
  OpenExecutive body, a marker-less body and an HTTP 500 each fail. `make check`
  -> 2370 passed, 3 skipped, 724 subtests (was 2366; +4), `uv run pyflakes` clean.
  Run against the real host, the gate now fails honestly:
  `./scripts/check_deployed_red_health.sh` -> "response from
  https://redop.atlas.lan/ does not carry the RED identity marker 'RED
  Operations'; the deployed app is not RED (condition 9 unmet)" (exit 1).
  `make done` still stops at `[2/6]` condition 5, unchanged.
- New findings: condition 9 is not met. The health URL `redop.atlas.lan`
  resolves to the OpenExecutive frontend, not RED, so the prototype is not the
  RED-branded system deployed end to end. The deploy queue Q47-Q50 (Dockerfile,
  Helm chart, Argo Application, secrets and smoke) is not started: there is no
  `Dockerfile` and no `deploy/` in the repository, and no cluster context is
  configured here, so a cycle cannot build or deploy them. Condition 9's stronger
  evidence (Argo CD healthy release, migration Job ran before the API served)
  still needs cluster access and a real RED image.
- Blockers (head unchanged; new condition 9 blocker recorded): condition 5's live
  OpenRouter smoke needs `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`
  (Q4). Condition 9 now honestly fails because the Atlas host serves
  OpenExecutive, not RED; satisfying it needs the Q47-Q50 deploy slice and a
  cluster context, both operator work. Q28 stages 8-10 required kinds remain
  blocked on the named methodology-owner placement decision. Conditions 1-4 and
  6-8 are met by their gates.
- Highest priority ready next item: Q47, the Dockerfile plus health endpoint
  (SPEC.md section 13 condition 9; PREREQUISITE Q30 met). Required artifact: a
  container image that builds the RED API (`redops.api.app:app`, `/red/health`)
  and, per the queue, passes a local container health check; note the vendored
  `vendor/openexecutive` is ~1.9 GB and needs a `.dockerignore`. Checkpoint:
  image builds and the container `/red/health` returns `{"status":"ok"}`.
  Approver: none for the image build; the Atlas deploy and promotion remain the
  RED principal/operator's manual approval (SPEC.md section 10). Blocked
  downstream dependency: Q48-Q50 and condition 9 (a RED image, Helm chart, Argo
  Application and the migration-before-serve ordering). Alternative unblocker if
  a cycle must avoid image size: none unattended; the live key and the
  methodology-owner placement decision are owner inputs.

### Owner decision 2026-10-04: vendor edits go through a re-triggerable overlay (ADR 0011)

- The RED principal resolved the ADR 0006 / zero-vendor-edit tension that had
  stopped the loop: vendor edits are allowed, but only through a committed,
  idempotent, re-triggerable overlay owned by this repository. RED-authored
  vendor additions live under `vendor/overlay/`; `scripts/apply_vendor_overlay.sh`
  applies them onto `vendor/openexecutive/` (idempotent; re-run after any upstream
  submodule bump), and `scripts/apply_vendor_overlay.sh --check` proves the tree
  equals the overlay with no unaccounted vendor change
  (`docs/adr/0011-vendor-edits-through-a-retriggerable-overlay.md`, which amends
  ADR 0008's "minimal (ideally none)" stance).
- Effect on the contract: SPEC.md section 13 condition 7 and DoD `[4/6]` change
  from "the submodule is clean" to "every vendor change is overlay-declared and
  reproducible from this repository". SPEC.md section 2 records the overlay rule.
- Superseded blockers in the cycle record below that say a change was rejected
  because "DoD condition 7 requires zero vendor edits" (the agent-registration and
  routing seams in the Q3/Q30 lineage) are resolved by this decision: such edits
  are now allowed through the overlay. The ADR 0006 tension is closed; the live
  key (Q4) and the Atlas cluster (Q47-Q50/condition 9) remain.

- Cycle 2026-10-04 (Ralph cycle, this run): selected item was Q3, register the RED
  Director and specialist agents behind ports (SPEC.md section 5; ADR 0006),
  now unblocked by ADR 0011. It is the highest priority ready item: it closes the
  last architectural blocker on condition 5's deterministic agent path.
- Outcome: the RED agent roster is a pure-domain registry in
  `backend/redops/agents/` — `RedAgentSpec` (charter, routing key, prompt version,
  authority class) for the Director plus capability slots 1-11, with slots 10/11
  proposal-only and tool-less by construction; `RedAgentRegistry` (duplicate and
  unknown-key refusal); and `RedAgentRouter`, which routes every agent through the
  `ModelGateway` port carrying tenant, model, prompt version, trace id and context
  references. The vendor overlay registers RED's nine core specialists through the
  fork's own mechanism (`agents/redops_agents.py`, `prompts/redops_prompts.py`,
  knowledge, an eval scenario, and marked hooks merging
  `SPECIALIST_REGISTRY`/`SPECIALIST_DESCRIPTIONS`/`SPECIALIST_TOOLS` enum and
  `_AREAS`). The generic personas remain registered; retiring them stays a
  separate characterised change (ADR 0006).
- Evidence: `scripts/apply_vendor_overlay.sh --check` ->
  "vendor overlay check ok" and re-apply is a no-op;
  `tests/unit/agents/test_red_agent_registry.py` (18 tests) pins the roster,
  registry and routing; `tests/unit/shared/test_vendor_overlay.py` (6 tests) pins
  idempotent apply, unaccounted-change failure, missing-anchor failure and the
  real repository; the stage 0-10 e2e now also drives all twelve RED agents
  through `DeterministicFakeModelGateway` and proves the fork registry exposes the
  nine RED specialists. `tests/unit/agents/covered-provider-paths.txt` declares
  `deterministic-e2e`, so `check_provider_path_coverage.sh` reports condition 5's
  only remaining part as the paid live smoke (Q4).
- Blocker (make done head): condition 5's live OpenRouter smoke needs
  `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1` (Q4), and condition 9
  needs the Atlas cluster. No unattended item is ready, so `.ralph/DONE` is
  touched and the loop stops rather than inventing work or making a named-owner
  decision.

### Owner decision 2026-10-03: backup and restore deferred (ADR 0009)


- The prototype definition of done no longer requires a database backup or a
  restore drill; both move to a production-readiness phase
  (`docs/adr/0009-prototype-defers-backup-and-restore.md`). SPEC.md section 11
  now names nine minimum acceptance scenarios, section 9 keeps the RPO/RTO and
  restore-drill targets as production requirements, and the section 13 condition
  2 evidence is updated. `scripts/check_acceptance_coverage.sh` and
  `tests/acceptance/covered-scenarios.txt` no longer require
  `backup-restores-approval-trail`.
- Effect on the queue: the only remaining deploy-gated acceptance scenario is
  `gitops-revert-restores` (the push-to-forge GitOps revert drill, Q49), so the
  deploy slice Q47-Q50 stays on the critical path. No backup-target decision is
  needed for the prototype. The operator also confirmed the deployment
  mechanism (app repo issue #3): the Helm chart lives in this repository and the
  GitOps repo holds the Argo CD Application and pinned values. (The rollback
  scenario was later superseded by ADR 0010; see the next decision.)
- Superseded blockers in the cycle record below that name a "chosen backup
  target" are resolved by this decision; the ADR 0006, live-key and Q28 blockers
  remain.

### Owner decision 2026-10-03: reversible migrations; backup and rollback are production-readiness gates (ADR 0010)

- Every migration is written for both directions: a working `downgrade()` that
  removes exactly what `upgrade()` created, enforced per cycle by
  `tests/unit/shared/test_migrate.py::MigrationReversibilityTests` (static, no
  database) plus a linear revision-chain check. The live
  `upgrade -> downgrade -> upgrade` round trip runs in the production-readiness
  rollback drill (`MigrationRoundTripTests`, opt-in via
  `REDOP_MIGRATION_ROUNDTRIP=1`). SPEC.md section 6 records the rule; section 10
  makes release rollback depend on it.
- The database restore drill and the GitOps rollback drill move out of the
  prototype definition of done into the production-readiness phase, which begins
  once the first cluster release exists, may span several further iterations and
  releases, and must complete before production client data (ADR 0009, ADR 0010).
  `gitops-revert-restores` is removed from the section 11 acceptance scenarios
  (eight remain, all covered), superseding that part of ADR 0009.
- Effect on the queue: condition 2 now passes (eight of eight scenarios
  covered), so `make done` is no longer blocked by it. The remaining prototype
  blockers are condition 1 (stage 0-10 e2e, gated on Q3/ADR 0006), condition 5's
  live provider half (a key) and condition 9 (the Atlas deployment, still the
  prerequisite for the production-readiness drills).

- Cycle 2026-10-03T210728Z (Ralph cycle, this run): selected item was Q8, the
  prompt-injection guard (SPEC.md sections 5, 9 and 11; distinct from the four
  condition 3 isolation layers). It is the highest priority ready item: it has
  no prerequisite (no cluster, no owner decision), and it closes the last named
  part of the SPEC.md section 5 injection guard. It outranks alternatives:
  condition 2's two remaining scenarios are deploy-gated (Atlas cluster, chosen
  backup target Q49); condition 5's deterministic e2e is blocked on Q3 (ADR 0006
  / zero-vendor-edit tension) and the live smoke on a key; Q16's remaining
  optimistic-version half has no mutation route carrying a version; Q28 stage
  8-10 required kinds stay blocked on the named methodology-owner placement
  decision; Q47-Q50 need the Atlas cluster. The canon gap register has no ready
  pipeline item.
- Outcome: new shared prompt-injection guard under
  `backend/redops/shared/security/`: pure-domain `ContentTrust`, `AuthorityBasis`
  (with `confers_authority` true only for an operator decision or an approved
  gate), frozen `IngestedMaterial` (always untrusted, client-scoped, source-
  pinned), `ProposedToolCall` and `ProposedGateChange`, the named
  `UntrustedContentError` / `UntrustedAuthorityError` /
  `InjectionTenantBoundaryError`, and `InjectionGuardPolicy`; the
  `InjectionGuard` application port (`ingest`, `authorize_tool_call`,
  `authorize_gate_change`) and the process-local `InMemoryInjectionGuard`
  reference adapter bound to one active client. Ingested client material is
  admitted only as untrusted data; a tool call or gate change grounded on model
  output or ingested material is refused, while an operator decision or an
  approved gate is allowed. No route, gate rule, approval authority, pipeline
  stage, vendored file, migration or method artifact changed. A durable adapter
  is a later composition consumer, exactly as the worker and connector seams
  preceded theirs.
- Evidence: new `tests/security/test_injection_guard.py` (18 tests) proves
  instruction-shaped client material is admitted as untrusted, client-scoped,
  source-pinned data that confers no authority; that an ingested or model-output
  basis cannot direct a tool call or change a gate while an operator decision or
  approved gate can; that a cross-client tool call, gate change or blank guard
  session is refused; and that malformed material and calls are refused at
  construction. `make check` -> 2338 passed, 2 skipped, 706 subtests (was 2320;
  +18); `uv run pyflakes backend tests` clean. `make done` still stops at
  `[2/6]` condition 2 (deploy-gated), unchanged.
- New findings: the injection guard is enforceable as a pure policy plus a
  client-scoped port with no route and no durable adapter; the authority line is
  the value object (`AuthorityBasis.confers_authority`) and the policy, so an
  ingested chunk that says "approve the gate" stays data by construction. This
  guard is distinct from condition 3 and is not one of its four required layers,
  so it is deliberately not declared in `tests/security/covered-layers.txt`.
- No ready item remains. Every dependency-met queue item is externally gated:
  Q3 (ADR 0006 / zero-vendor-edit tension), Q4 (live key), Q16 remaining half
  (no version-carrying mutation route), Q28 (named methodology-owner placement
  decision), Q30 (needs Q3), Q31/Q47-Q50 (Atlas cluster; Q49 backup target).
  There is no completable unattended unblocker inside the current dependency
  graph, so `.ralph/DONE` is touched and the loop stops rather than inventing
  work or making a named-owner decision.
- Blocker (make done head): condition 2 is the head blocker; its two remaining
  scenarios are deploy-gated (Atlas cluster, chosen backup target Q49).
- Highest priority ready next action (operator/owner input required, not a cycle
  decision): the single most useful unblocker is to settle the deploy and
  architecture inputs the loop cannot make unattended: (a) Atlas cluster access
  plus the backup target and restore drill for Q47-Q50 and condition 9 (first
  doable increment after that is Q47, the Dockerfile plus backend health
  endpoint, whose declared dependency on Q30 could be relaxed once the operator
  confirms an unverified image is acceptable); (b) the ADR 0006 / zero-vendor-
  edit resolution so Q3 agent registration can satisfy Q30 and condition 5's
  deterministic e2e; (c) a live `OPENROUTER_API_KEY` plus
  `REDOP_LIVE_OPENROUTER_SMOKE=1` for Q4. Until one of these is supplied, no
  unattended item is ready.

### Prior cycle (2026-10-03T210459Z)

- Cycle 2026-10-03T210459Z (Ralph cycle, this run): selected item was Q46, the
  condition 8 RED branding and notice sweep (SPEC.md sections 5 and 13 condition
  8). It is the highest priority ready item: after condition 3 closed, the
  remaining ready work is agent-charter and branding evidence, while the
  pipeline-critical alternatives stay blocked. It outranks alternatives: Q29
  (method change impact) is domain-complete and tested
  (`MethodChangeImpactPolicy` / `ImpactAssessment`), so it is not an open defect;
  Q28 stage 8-10 required kinds stay blocked on the named methodology-owner
  placement decision; Q3/Q4 and condition 5's deterministic e2e need the ADR
  0006 / zero-vendor-edit resolution and a live key; Q47-Q50 and condition 2's
  two remaining scenarios need the Atlas cluster and a chosen backup target
  (Q49). The canon gap register has no ready pipeline item.
- Outcome: added the nine core agent charters SPEC.md section 5 requires, in the
  existing charter format (`docs/agents/charter-01-discovery-diagnosis.md`
  through `charter-09-ip-portfolio.md`), each carrying the section 5 contract:
  mission, responsibilities, allowed tools, inputs, outputs, evidence policy,
  context budget, quality rubric, escalation rules, budget limit, delivery
  pipeline mapping and canon reference. Added `docs/agents/agent-charters.txt`
  (slots 1-11), the data-driven `scripts/check_agent_charters.sh` and
  `scripts/check_branding_and_notice.sh` (RED Director name, no OpenExecutive
  branding under `frontend/`, vendored `LICENSE`/`NOTICE` retained), and wired
  both into DoD `[5/6]`, replacing the old inline frontend branding scan. No
  route, gate rule, approval authority, pipeline stage, vendored file, migration
  or method artifact changed.
- Evidence: new `tests/unit/shared/test_branding_gate.py` (9 tests) proves the
  charter gate passes on a complete manifest and refuses a missing directory, a
  missing charter file, a missing required section and a duplicate slot, and that
  the branding gate refuses a missing NOTICE and a non-RED Director name, with
  the repository charters and branding honest (11 chartered agents).
  `scripts/check_agent_charters.sh docs/agents` -> "agent charters ok: 11
  chartered agents"; `scripts/check_branding_and_notice.sh frontend
  vendor/openexecutive` -> ok. `make check` -> 2320 passed, 2 skipped, 706
  subtests (was 2311; +9); `uv run pyflakes backend tests` clean. `make done`
  still stops at `[2/6]` condition 2 (deploy-gated), unchanged; DoD `[5/6]` now
  also proves the condition 8 charters and notices.
- New findings: all eleven agent charters now exist and pass the section 5
  contract under the gate, so condition 8's "agent charters are RED" evidence is
  complete. The charters are `Proposed` and remain proposal-only; they grant no
  execution permission. `check_branding_and_notice.sh` checks the vendored
  `LICENSE`/`NOTICE` because the app repo has no root copies and the dependency
  is vendored (ADR 0008).
- Blockers (unchanged head): condition 2 is the `make done` head blocker and its
  two remaining scenarios need the Atlas cluster and a chosen backup target
  (Q49). Condition 5 needs the deterministic agent e2e (Q3/ADR 0006 tension) and
  a live key. Q3 agent registration blocked on the ADR 0006 / vendor-edit
  tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q47-Q50 need the Atlas cluster. Every other
  condition (1, 3, 4, 6, 7, 8) is met by its gate.
- Highest priority ready next item: the Q8 injection-guard coverage (SPEC.md
  sections 5, 9 and 11; the prompt-injection guard, distinct from the four
  condition 3 layers). Required asset: a tenant-scoped injection-guard policy or
  port with an in-memory reference adapter and a `tests/security/` test proving
  ingested material is treated as data and cannot change a gate or direct a tool
  call. Prerequisite: none (no cluster or owner decision). Checkpoint: none;
  approver: none. Blocked downstream dependency: it hardens condition 3's suite
  and SPEC.md section 9's ingestion boundary; it does not gate a stage. The
  pipeline-critical alternatives (Q3/ADR 0006, object-store provisioner, backup
  target, Atlas cluster) remain named-owner or operator decisions a cycle must
  not make unattended.

### Prior cycle (2026-10-03T210152Z)

- Cycle 2026-10-03T210152Z (Ralph cycle, this run): selected item was the
  condition 3 artifact-URL isolation layer (Q8; SPEC.md sections 3, 6, 9 and 13
  condition 3). It is the highest priority ready item: it is the last of the four
  condition 3 layers, has no prerequisite (a reference adapter needs no cluster or
  object-store decision), and it closes SPEC.md section 9's "cross client access
  at ... artifact URL" at a port seam before any serving route exists. It
  outranks alternatives: the artifact-URL layer is the only remaining condition 3
  layer; condition 2's two remaining scenarios are deploy-gated (Atlas cluster,
  chosen backup target Q49); Q28 stage 8-10 required kinds stay blocked on the
  named methodology-owner placement decision; Q3/Q4 and condition 5's
  deterministic e2e need the ADR 0006 / zero-vendor-edit resolution and a live
  key; Q47-Q50 need the Atlas cluster. The canon gap register has no ready
  pipeline item.
- Outcome: new shared artifact-access layer under `backend/redops/shared/
  artifacts/`: pure-domain `ArtifactRef` value object and the named
  `InvalidArtifactRefError` / `ArtifactTenantBoundaryError`; the
  `ArtifactUrlResolver` application port (`mint` / `resolve`); and the
  process-local `InMemoryArtifactUrlResolver` reference adapter. A URL minted for
  one client resolves only for that client; an unknown or forged URL returns
  `None` (no existence disclosure); a blank tenant is refused on resolve and an
  unscoped artifact is refused at construction. No route, gate rule, approval
  authority, pipeline stage, vendored file or migration changed. The durable
  private-object-store adapter is deferred until the object-store provisioner
  decision (SPEC.md section 11); a serving route is the later composition
  consumer, exactly as the worker and connector seams preceded theirs.
- Evidence: new `tests/security/test_artifact_url_isolation.py` (7 tests) proves
  own-URL resolution to the exact reference, cross-tenant non-resolution, scoping
  to the requested client, forged/unknown URLs resolving to nothing, blank-tenant
  refusal on resolve and unscoped-artifact refusal. `tests/security/
  covered-layers.txt` now declares the `artifact-url` layer, and
  `tests/unit/shared/test_security_coverage_check.py::test_repository_suite_is_
  honest` now expects the gate to pass. `scripts/check_security_coverage.sh
  tests/security` -> "security coverage ok: 4 condition 3 layers declared with
  tests" (was exit 1 naming `artifact-url`). `make check` -> 2311 passed, 2
  skipped, 706 subtests passed (was 2304; +7). `uv run pyflakes backend tests`
  clean. `make done` still stops at `[2/6]` condition 2 (deploy-gated),
  unchanged; condition 3 is now fully covered by the suite gate.
- New findings: the artifact URL layer is enforceable at a port without a route
  because `ArtifactRef` already carries the tenant and checksum, so resolution is
  a pure tenant comparison; the serving route and durable object-store adapter
  remain pending consumers. This closes condition 3: all four named layers (api,
  retrieval, worker, artifact-url) now have a declared isolation test and the
  `[3/6]` coverage gate passes.
- Blockers (unchanged head): condition 2 is the `make done` head blocker and its
  two remaining scenarios need the Atlas cluster and a chosen backup target
  (Q49). Condition 5 needs the deterministic agent e2e (Q3/ADR 0006 tension) and
  a live key. Q3 agent registration blocked on the ADR 0006 / vendor-edit
  tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q47-Q50 need the Atlas cluster. Every other
  condition (1, 3, 4, 6, 7, 8) is met by its gate.
- Highest priority ready next item: Q46, the condition 8 RED branding and notice
  sweep (prerequisite Q32 met; no decision blocked). The frontend slice already
  passes (all 12 screens declared, `check_frontend_screens.sh` and
  `check_frontend_build.sh` green, no OpenExecutive branding under `frontend/`),
  and the vendor root retains `LICENSE` and `NOTICE`. The concrete gap to close
  is the missing RED charters for the nine core agents: SPEC.md section 5 requires
  every agent to have a versioned charter, and `docs/agents/` holds only
  `charter-10-client-success.md` and `charter-11-assurance-compliance.md`.
  Smallest independently verifiable first step: add the nine core agent charters
  in the existing charter format and a branding/notice verification gate so
  condition 8's evidence is complete. Checkpoint: none; approver: none (branding
  and charter copy, no client authority). Blocked downstream dependency: none
  directly; it hardens an already-passing `[5/6]`. Note the alternative
  pipeline-critical unblockers (object-store provisioner, backup target, ADR
  0006) are all named-owner or operator decisions that a cycle must not make
  unattended.

### Prior cycle (2026-10-03T205830Z)

- Cycle 2026-10-03T205830Z (Ralph cycle, this run): selected item was the
  background-worker isolation layer (Q8 worker layer; SPEC.md sections 7, 9 and
  13 condition 3). It is the highest priority ready item: after the retrieval
  layer landed, the worker was the one remaining condition 3 layer that could be
  built from an existing seam, and it closes SPEC.md section 11's "restarting
  worker preserves a waiting workflow" at the worker boundary. It outranks
  alternatives: condition 2's remaining scenarios are deploy-gated (Atlas
  cluster, chosen backup target, Q49); condition 3's artifact-URL layer is the
  other candidate but was left for the next cycle (see below); Q28 stages 8-10
  required kinds stay blocked on the named methodology-owner placement
  decision; Q3/Q4 need the ADR 0006 resolution and a live key; Q47-Q50 need the
  Atlas cluster. The canon gap register has no ready pipeline item.
- Outcome: new abstract `WorkflowRunStore.list_resumable(*, tenant_id)` in
  `.../workflows/application/ports.py` (a tenant-scoped scan for runs with a
  step due); implementations in `InMemoryWorkflowRunStore` (filter by tenant
  and `resume_step() is not None`) and `PostgresWorkflowRunStore` (`WHERE
  tenant_id = %s AND status = 'running' ORDER BY id`); and the new
  `ResumeDueRunsHandler` application use case in
  `.../workflows/application/handlers.py`, the worker's per-client pass that
  lists the client's due runs and resumes each through `RunWorkflowHandler`. No
  route, gate rule, approval authority, pipeline stage, vendored file or
  migration changed; the existing run store contract and every run status
  transition are unchanged.
- Evidence: new `tests/security/test_worker_isolation.py` (6 tests) proves the
  worker pass resumes only its client's interrupted run, never reads, lists or
  advances another client's run, leaves a waiting approval for its human, is
  scoped per requested client, and refuses a blank tenant.
  `tests/unit/workflows/test_workflow_run_store.py` gained 4 adapter-contract
  tests for `list_resumable` (in-memory and the real PostgreSQL schema), and the
  `test_repository_suite_is_honest` gate test now expects only `artifact-url`
  missing. `make check` -> 2304 passed, 2 skipped, 706 subtests passed (was
  2294; +10). `scripts/check_security_coverage.sh tests/security` now reports
  only the `artifact-url` layer missing (was worker and artifact-url). `make
  done` still stops at `[2/6]` condition 2 (deploy-gated), unchanged.
- New findings: the worker's store scan is now a first-class tenant-scoped
  query, so "a worker for one client never reads another client's run" is
  enforced at the seam and tested (SPEC.md section 9). The PostgreSQL scan
  filters on `status = 'running'` and the only index is the `(tenant_id,
  run_id)` unique key, so a large per-tenant scan would benefit from a
  `(tenant_id, status)` index in a later migration; a performance follow-up,
  not a correctness gap. The worker use case has no composition consumer (no
  `backend/redops/worker` process) yet, exactly as the connector seam preceded
  its consumer; the layer is exercised by its adapter and security tests.
- Blockers (unchanged head): condition 2 is the `make done` head blocker and its
  remaining two scenarios need the Atlas cluster and a chosen backup target
  (Q49). Condition 3 needs only the artifact-URL layer. Condition 5 needs the
  deterministic agent e2e (Q3, ADR 0006 tension) and a live key. Q28 stage 8-10
  required kinds blocked on the named methodology-owner placement decision; Q3
  agent registration blocked on the ADR 0006 / vendor-edit tension; Q4 live
  smoke needs `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q47-Q50
  need the Atlas cluster.
- Highest priority ready next item: the condition 3 artifact-URL isolation layer
  (SPEC.md sections 9 and 13 condition 3). Required asset: a tenant-scoped
  artifact access port (an `ArtifactUrlResolver`/`ArtifactStore`) with an
  in-memory reference adapter and `tests/security/test_artifact_url_isolation.py`,
  plus the `artifact-url` layer declared in `tests/security/covered-layers.txt`,
  so a URL or reference minted for one client's artifact never resolves for
  another. Build it at the port/adapter seam like the connector and worker
  layers; the durable object-store adapter follows once the object-store
  provisioner decision (SPEC.md section 11: a decision to settle after
  inspecting the cluster) is made. Checkpoint: none (seam, not a gate);
  approver: none. Blocked downstream dependency: condition 3 (then condition
  2's cross-client coverage). Prerequisite: none (the reference adapter needs no
  cluster decision). Alternative ready item: none cleanly; Q16's
  optimistic-version-conflict half has no mutation route carrying a version yet.

### Prior cycle (2026-10-03T205006Z)

- Cycle 2026-10-03T205006Z (Ralph cycle, this run): selected item was the
  durable PostgreSQL `ExternalOperationStore` adapter and migration
  `0018_external_operations` (Q16 completion; SPEC.md sections 6, 7, 9 and 11;
  DoD conditions 2 and 4). It is the highest priority ready item: it is the only
  remaining cleanly-ready increment whose prerequisites are all met, it completes
  the connector seam's durability so "duplicate delivery creates one external
  operation" holds across a process restart (SPEC.md section 11), and it follows
  the established durable-adapter pattern (Q6/Q9/Q11) with a committed migration.
  It outranks alternatives: condition 2's two remaining acceptance scenarios are
  deploy-gated (gitops-revert-restores needs the GitOps recovery drill;
  backup-restores-approval-trail needs a chosen backup target, a Tier 2 owner
  decision); condition 3's worker and artifact-URL layers need a worker entry
  point and an artifact-serving route, neither of which exists (the artifact
  store provisioner is an open section 11 decision); condition 5's
  deterministic-e2e part is coupled to Q3 agent registration, blocked on the ADR
  0006 / zero-vendor-edit tension; Q28 stage 8-10 required kinds remain blocked
  on the named methodology-owner placement decision; Q3/Q4 need the ADR 0006
  resolution and a live key; Q47-Q50 need the Atlas cluster. The canon gap
  register has no ready pipeline item: its remaining entries are implemented or
  are candidate pipeline additions awaiting a named-owner decision.
- Outcome: new `PostgresExternalOperationStore` and
  `external_operation_store_from_env` in
  `.../contexts/execution/infrastructure/connectors.py`, plus the named
  `ConnectorConfigurationError`; new `external_operation_to_payload` /
  `external_operation_from_payload` in `.../infrastructure/mappers.py`; and
  migration `0018_external_operations` (unique `(tenant_id, idempotency_key)`,
  indexed `(tenant_id, connector)`, NOT NULL tenant and key). The store is
  append-only per `(tenant_id, idempotency_key)`: a same-body replay is
  idempotent, a reused key with different content is refused, the same key for a
  different tenant is independent, and a blank tenant is refused on read and
  write. No route, gate rule, approval authority, pipeline stage or vendored
  file changed; the in-memory reference adapter and the `IdempotentConnector`
  wrapper are unchanged.
- Evidence: `tests/unit/execution/test_external_operation_postgres.py` (6 tests)
  exercises the real schema created by `0018_external_operations` and proves a
  recorded operation survives a reload, a duplicate record creates one row, a
  reused key with changed content raises `ConnectorIdempotencyConflictError` and
  does not overwrite, the same key for another tenant is independent, and a blank
  tenant is refused. `tests/unit/shared/test_migrate.py` now asserts head
  `0018_external_operations` and the `external_operations` table. `make check` ->
  2294 passed, 2 skipped, 706 subtests passed (was 2288; +6). `uv run pyflakes
  backend tests` -> clean. `check_acceptance_coverage.sh`,
  `check_provider_path_coverage.sh` and `check_security_coverage.sh` are
  unchanged (the durable store flips no DoD gate; `make done` still stops at
  `[2/6]` condition 2).
- New findings: the connector seam's duplicate-delivery guarantee was
  process-local until now; with migration `0018_external_operations` the recorded
  operation is durable, so a restarted process resolves a retry to the same
  operation instead of sending a second effect. The store still has no
  composition consumer (`WorkflowStepExecutor` has no adapter), so it is
  exercised by adapter tests like every other durable store; a
  `ConnectorStepExecutor` remains blocked on a step-to-effect mapping the
  workflow step type does not yet carry. Newly surfaced and now tracked:
  condition 5's `deterministic-e2e` provider-path part is a real blocker coupled
  to Q3, and the artifact-URL layer is blocked on the object-store provisioner
  decision (SPEC.md section 11).
- Blockers (unchanged head): condition 2 is the `make done` head blocker and its
  remaining two scenarios need the Atlas cluster and a chosen backup target
  (Q49). Condition 3 needs the worker and artifact-URL layers. Condition 5 needs
  the deterministic agent e2e (Q3, ADR 0006 tension) and a live key. Q28 stage
  8-10 required kinds blocked on the named methodology-owner placement decision;
  Q3 agent registration blocked on the ADR 0006 / vendor-edit tension; Q4 live
  smoke needs `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q47-Q50
  need the Atlas cluster.
- Highest priority ready next item: the condition 3 worker isolation layer
  (SPEC.md sections 6, 9 and 13 condition 3). Required asset: a background worker
  entry point over the tenant-scoped `WorkflowRunStore` that resumes in-flight
  runs, plus `tests/security/test_worker_isolation.py` and the `worker` layer
  declared in `tests/security/covered-layers.txt`, so a worker for one client
  never reads or advances another client's run. Checkpoint: none (seam, not a
  gate); approver: none. Blocked downstream dependency: condition 3 (then
  condition 2's worker-restart integrity). Prerequisite: the workflow engine and
  ADR 0005 (done). Alternative ready item: the artifact-URL isolation layer,
  which needs an artifact-serving route and is blocked on the open object-store
  provisioner decision (SPEC.md section 11).

### Prior cycle (2026-10-03T204037Z)

- Cycle 2026-10-03T204037Z (Ralph cycle, this run): selected item was the
  idempotency-keyed Execution connector seam (Q16 connector half, SPEC.md
  sections 6, 7, 9 and 11; DoD condition 2). It is the highest priority ready
  item: it closes the `duplicate-delivery-one-effect` section 11 scenario, the
  last non-deploy blocker on condition 2, and its only dependency Q15 is done.
  It outranks alternatives: condition 2's two remaining scenarios
  (`gitops-revert-restores`, `backup-restores-approval-trail`) are deploy-gated
  on Q49 and a chosen backup target; the condition 3 worker and artifact-URL
  layers need a worker entry point (ADR 0005 is a proposed topology) and an
  artifact-serving route, neither of which exists; Q28 stage 8-10 required kinds
  remain blocked on the named methodology-owner placement decision; Q3/Q4 need
  the ADR 0006 resolution and a live key; Q47-Q50 need the Atlas cluster. The
  canon gap register has no ready pipeline item: its remaining entries are
  implemented or are candidate pipeline additions awaiting a named-owner
  decision, so no canon-covered method artifact outranks this gate work.
- Outcome: new Execution `ConnectorPort`, `ConnectorTransport` and
  `ExternalOperationStore` ports in `.../application/ports.py`; pure-domain
  `ConnectorEffect` and `ExternalOperation` in `.../domain/connector.py`; named
  errors `ConnectorError`, `InvalidConnectorEffectError`,
  `ConnectorIdempotencyConflictError` and `ConnectorTenantBoundaryError` in
  `.../domain/errors.py`; and the replay-safe `IdempotentConnector` adapter plus
  `InMemoryExternalOperationStore` and `RecordingConnectorTransport` in
  `.../infrastructure/connectors.py`. The store is append-only per
  `(tenant_id, idempotency_key)`: a repeat of the same effect returns the
  recorded operation without a second send, and a reused key with different
  content or a different connector is refused rather than silently suppressed.
  `tests/acceptance/covered-scenarios.txt` now maps
  `duplicate-delivery-one-effect` to the new test. No route, gate rule,
  approval authority, store contract or pipeline stage changed; the vendored
  OpenExecutive is untouched.
- Evidence: `tests/unit/execution/test_connector_idempotency.py` (10 tests)
  proves a first delivery sends once and records one operation, a duplicate
  delivery creates one external operation (the transport is not called again),
  a reused key with changed content or a different connector raises the conflict
  with no second send, the key is scoped per client, and a blank tenant or
  idempotency key is refused. `make check` -> 2288 passed, 2 skipped, 706
  subtests passed (was 2278; +10). `check_acceptance_coverage.sh
  tests/acceptance` still exits 1, now naming only `gitops-revert-restores` and
  `backup-restores-approval-trail`. `make done` still stops at `[2/6]` condition
  2 (now only the two deploy-gated scenarios). `test_acceptance_coverage_check`
  honesty test updated to the new missing set.
- New findings: the `WorkflowStepExecutor` port already documented an
  idempotency requirement but had no adapter; the connector seam now supplies
  the replay-safe outbound effect the executor was written to need
  (`workflow-run-engine` memory). The connector's guarantee is only
  process-local today: an in-memory store does not survive a restart, so the
  duplicate-delivery rule is not yet durable. Q16's optimistic-version-conflict
  half (stale update 409) is also not built; no mutation route carries an
  optimistic version check yet, so it has no ready consumer.
- Blockers (unchanged head): condition 2 is the `make done` head blocker and its
  remaining two scenarios need the Atlas cluster and a chosen backup target
  (Q49). Condition 3 needs the worker and artifact-URL layers. Q28 stage 8-10
  required kinds blocked on the named methodology-owner placement decision; Q3
  agent registration blocked on the ADR 0006 / vendor-edit tension; Q4 live
  smoke needs `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q47-Q50
  need the Atlas cluster.
- Highest priority ready next item: the durable PostgreSQL
  `ExternalOperationStore` adapter plus migration (Q16 completion, SPEC.md
  sections 6, 7, 9 and 11; DoD condition 4 and condition 2's worker-restart
  integrity). Required asset: a `PostgresExternalOperationStore` implementing
  the port with a unique `(tenant_id, idempotency_key)` constraint and migration
  `0018_external_operations`, so an already-recorded external operation cannot
  be re-sent after a process restart (SPEC.md section 11 duplicate delivery
  across restarts, SPEC.md section 9 tenant scoping). Checkpoint: none (seam,
  not a gate); approver: none. Blocked downstream dependency: none directly; it
  hardens condition 2's duplicate-delivery and worker-restart guarantees once a
  worker exists. Prerequisite: this cycle's connector seam (done). Alternative
  ready item: the condition 3 worker isolation layer, which needs a worker entry
  point (ADR 0005 proposed), larger than the durable store.

### Prior cycle (2026-10-03T203755Z)

- Cycle 2026-10-03T203755Z (Ralph cycle, this run): selected item was the
  Knowledge retrieval port and its tenant-scoped isolation test (Q8, SPEC.md
  sections 3, 5, 6, 9 and 13 conditions 2 and 3). It is the highest priority
  ready item: it closes the condition 3 retrieval layer and the condition 2
  `cross-client-retrieval-empty` scenario, both of which name retrieval as their
  missing seam, and its only dependency Q7 is done. It outranks alternatives:
  condition 2 is the `make done` head blocker and its other two ready seams are
  larger (Q16 connector idempotency needs a new connector port; gitops-revert and
  backup-restore are deploy-gated on Q49); the condition 3 worker and artifact-URL
  layers need a worker entry point and an artifact-serving route, neither of which
  exists; Q28 stage 8-10 required kinds remain blocked on the named
  methodology-owner placement decision; Q3/Q4 need the ADR 0006 resolution and a
  live key; Q47-Q50 need the Atlas cluster. The canon gap register has no ready
  pipeline item: its remaining entries are implemented or are candidate pipeline
  additions awaiting a named-owner decision, so no canon-covered method artifact
  outranks this gate work.
- Outcome: new `KnowledgeRetriever` port in
  `backend/redops/contexts/knowledge/application/ports.py` and the process-local
  `InMemoryKnowledgeRetriever` reference adapter in `.../infrastructure/
  repositories.py`, which composes the append-only tenant-scoped `ClaimStore` and
  returns a client's claims (with their source citations) whose statement matches
  the query. New named `UnscopedRetrievalError`; a blank tenant is refused rather
  than answered unscoped. `tests/security/covered-layers.txt` now declares the
  `retrieval` layer and `tests/acceptance/covered-scenarios.txt` maps
  `cross-client-retrieval-empty` to the new test. No route, gate rule, approval
  authority, store contract or pipeline stage changed; the vendored OpenExecutive
  is untouched.
- Evidence: `tests/security/test_retrieval_isolation.py` (6 tests) proves a
  client retrieves its own claim with source attribution, another client's
  matching claim is never returned, a query matching only the other client's
  archive produces no result, retrieval is scoped to the requested client, and a
  blank tenant is refused. `PYTHONPATH=backend python3 -m unittest
  tests.security.test_retrieval_isolation` -> 6 passed. `make check` -> 2278
  passed, 2 skipped, 706 subtests passed (was 2272; +6). Two coverage-honesty
  tests in `tests/unit/shared/test_security_coverage_check.py` and
  `test_acceptance_coverage_check.py` were updated to the new state: retrieval is
  no longer a missing layer or an uncovered scenario. `check_security_coverage.sh
  tests/security` still exits 1, now naming only `worker artifact-url`;
  `check_acceptance_coverage.sh tests/acceptance` still exits 1, now naming only
  `duplicate-delivery-one-effect`, `gitops-revert-restores` and
  `backup-restores-approval-trail`. `make done` still stops at `[2/6]` condition
  2 (as expected: three scenarios remain).
- New findings: the knowledge context had a durable `ClaimStore` but no retrieval
  seam; the fork's `openexecutive/knowledge/retriever.py` exists behind the
  pinned submodule and is not needed for RED's reference seam (condition 7 keeps
  the fork unmodified). The retrieval layer's isolation is enforced at the port
  boundary and inherits the store's tenant scoping, so a durable PostgreSQL
  full-text adapter can implement the same port without changing callers.
- Blockers (unchanged head): condition 2 is the `make done` head blocker and its
  remaining three scenarios need a connector idempotency seam (Q16:
  duplicate-delivery-one-effect) or the Atlas cluster and a chosen backup target
  (Q49: gitops-revert-restores, backup-restores-approval-trail). Condition 3 now
  needs only the worker and artifact-URL layers. Q28 stage 8-10 required kinds
  blocked on the named methodology-owner placement decision; Q3 agent
  registration blocked on the ADR 0006 / vendor-edit tension; Q4 live smoke needs
  `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q47-Q50 need the
  Atlas cluster.
- Highest priority ready next item: Q16, the connector idempotency seam (SPEC.md
  sections 4, 6 and 11; DoD conditions 2 and 4). Required asset: an Execution
  connector port with a replay-safe, idempotency-keyed effect adapter, wired so
  "duplicate delivery creates one external operation", plus the
  `duplicate-delivery-one-effect` acceptance test (the request-idempotency half
  of SPEC.md section 7 mutation support). Checkpoint: none (seam, not a gate);
  approver: none. Blocked downstream dependency: condition 2
  duplicate-delivery-one-effect (then the remaining deploy-gated scenarios).
  Prerequisite: Q15 (done). Alternative ready item: the condition 3 worker
  isolation layer, which needs a worker entry point (ADR 0005 is a proposed
  topology, so this is larger than the connector seam).

### Prior cycle (2026-10-03T203620Z)

- Cycle 2026-10-03T203620Z (Ralph cycle, this run): selected item was Q44, the
  authority settings screen (SPEC.md sections 3, 4, 7, 8 and 13 condition 6;
  queue item Q44). It is the highest priority ready item: its only dependency
  Q43 is done, and it is the last canonical section 8 screen, so it closes the
  condition 6 screen manifest (the largest unstarted DoD condition). It outranks
  alternatives: once Q44 lands the condition 6 screen, build and branding gates
  all pass; Q28 stage 8-10 required kinds are still blocked on the named
  methodology-owner placement decision; Q16 needs a connector idempotency seam;
  Q3/Q4 need the ADR 0006 resolution and a live key; condition 2's remaining
  scenarios are deploy-gated (gitops-revert, backup-restore; Q49) or need the
  retrieval (Q8) and connector (Q16) seams; condition 3 needs the retrieval,
  worker and artifact-URL seams; Q47-Q50 need the Atlas cluster. The canon gap
  register has no ready pipeline item: its remaining entries are implemented or
  are candidate pipeline additions awaiting a named-owner decision, so no
  canon-covered method artifact outranks this gate work.
- Outcome: new `frontend/src/features/authority-settings/` feature.
  `AuthoritySettings.tsx` is a presentational view over two tenant-scoped reads:
  the client workspace authority registry (`GET /red/clients`) and the
  engagement production view (`GET /red/clients/{tenant}/engagements/{engagement}/
  production-view`). Helpers `authorityHolders` flatten each workspace's
  `(actor, authority)` registry with its owning workspace, and `approvalScopes`
  maps each stage to its accountable role, required approver role
  (`client-designated-authority`) and the human who recorded the decision
  (`approverLabel` renders a missing record as "not recorded"). It grants no
  authority, invents no authority role and approves no gate. The `/authority-
  settings` route binds the `authority-settings` screen id now declared in
  `frontend/dod-screens.txt` (twelfth and last screen). The API client's stale
  `ClientSummary`/`listClients` was corrected to the real `ClientWorkspaceList`
  projection (`ClientAuthority`, `ClientWorkspace`). No backend route, gate rule,
  approval authority or pipeline stage changed.
- Evidence: `frontend/src/features/authority-settings/AuthoritySettings.test.tsx`
  (7 tests) pins `authorityHolders`, `approvalScopes`, `approverLabel`, the
  rendered authorities and per-stage scopes (including an unrecorded approver and
  an approved gate), the empty registry, loading/error, and a stubbed-fetch
  screen read asserting both tenant-scoped paths (2 fetches). `npm test` -> 12
  files, 98 passed (7 new). `npm run build` -> compiled, `/authority-settings`
  route emitted. `make check` -> 2272 passed, 2 skipped, 706 subtests passed.
  `bash scripts/check_frontend_build.sh frontend` -> exit 0.
  `bash scripts/check_frontend_screens.sh frontend` -> exit 0 (all 12 section 8
  screens declared with pages and a browser suite; condition 6's screen gate now
  passes). `[5/6]` branding scan -> no OpenExecutive branding in `frontend/`.
  `make done` still stops at `[2/6]` condition 2 (unchanged; the remaining
  scenarios are not UI work).
- New findings: the `/red/clients` response was already the full
  `ClientWorkspaceListResponse` with the authority registry, so Q44 needed no new
  backend route; only the client's stale `listClients` type was wrong and is now
  fixed. The production view already carries each stage's `approver_role`
  (`client-designated-authority` for every stage) and `recorded_approver`, so the
  gate approval scope is readable without a new route. Closing Q44 also satisfies
  Q45 (the all-screen browser suite): condition 6's screen, build and branding
  gates all pass; Q45 has no further code scope. `make done` remains blocked
  before condition 6 because `[2/6]` runs first.
- Blockers (unchanged): condition 2 is the `make done` head blocker and its
  remaining scenarios need the retrieval port (Q8: cross-client-retrieval-empty),
  a connector idempotency seam (Q16: duplicate-delivery-one-effect), or the Atlas
  cluster and a chosen backup target (Q49: gitops-revert-restores,
  backup-restores-approval-trail). Condition 3 needs the retrieval, worker and
  artifact-URL seams. Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q3 agent registration blocked on the ADR
  0006 / vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q47-Q50 need the Atlas cluster.
- Highest priority ready next item: the Knowledge retrieval port and its
  tenant-scoped isolation test (Q8 retrieval layer, SPEC.md sections 3, 6 and 9;
  DoD conditions 2 and 3). Required asset: a retrieval port in the Knowledge
  context with a tenant-scoped adapter, wired so a different client's retrieval
  returns no result, plus the `cross-client-retrieval-empty` acceptance test and
  the `tests/security` retrieval layer declaration; checkpoint: none (seam, not a
  gate); approver: none. Blocked downstream dependency: condition 2
  cross-client-retrieval-empty and condition 3 retrieval layer (then conditions
  2, 3, 4, 5, 7, 8). Prerequisite: Q7 (done). Alternative ready item: Q16
  connector idempotency, needed by condition 2's duplicate-delivery scenario.

### Prior cycle (2026-10-03T203428Z)

- Cycle 2026-10-03T203428Z (Ralph cycle, this run): selected item was Q43, the
  portfolio opportunities screen (SPEC.md sections 3 and 8 and 13 condition 6;
  queue item Q43). It is the highest priority ready item: its only dependency
  Q42 is done, and it is now the head of the Q43-Q44 chain for condition 6, the
  largest unstarted DoD condition. It outranks alternatives: Q44 depends on
  Q43; Q28 stage 8-10 required kinds are still blocked on the named
  methodology-owner placement decision; Q16 needs a workflow write route and a
  connector seam; Q3/Q4 need the ADR 0006 resolution and a live key; Q8 layer
  coverage and the condition 2 cross-client-retrieval scenario have no
  retrieval/worker/artifact seam yet; Q47-Q50 need the Atlas cluster. Q31 also
  blocks condition 2 on a connector idempotency seam and the deploy-only
  scenarios. The canon gap register has no ready pipeline item: its remaining
  entries are implemented or are candidate pipeline additions awaiting a
  named-owner decision, so no canon-covered method artifact outranks this gate
  work.
- Outcome: new `frontend/src/features/portfolio-opportunities/` feature.
  `PortfolioOpportunities.tsx` is a presentational view over the tenant-scoped
  portfolio opportunity register (`GET /red/opportunities`, Q14): it groups each
  proposal by the canon's two Grow effects (canon files 11 and 12; SPEC.md
  section 12.3, entry point vs lifetime value) and shows, per proposal, its
  state, its exact pinned grounding source (`source_asset_id@vN`, source kind),
  expected outcome, investment case, named owner, next action and capture date.
  It approves no investment and starts no spend or launch. The API client gained
  the `PortfolioOpportunity`/`OpportunityList` types and `listOpportunities`;
  the `/portfolio-opportunities` route binds the `portfolio-opportunities`
  screen id now declared in `frontend/dod-screens.txt`. No backend route, gate
  rule, approval authority or pipeline stage changed.
- Evidence: `frontend/src/features/portfolio-opportunities/PortfolioOpportunities.test.tsx`
  (7 tests) pins `groundingVersion`, the `byKind` Grow grouping, `isProposal`,
  the rendered proposals with pinned grounding/owner, the empty register,
  loading/error, and a stubbed-fetch screen read asserting the tenant-scoped
  `/red/opportunities` path (1 fetch). `npm test` -> 11 files, 91 passed (7 new).
  `npm run build` -> compiled, `/portfolio-opportunities` route emitted.
  `make check` -> 2272 passed, 2 skipped, 706 subtests passed.
  `bash scripts/check_frontend_build.sh frontend` -> exit 0.
  `bash scripts/check_frontend_screens.sh frontend` -> still exit 1, now 1
  remaining section 8 id (authority-settings; condition 6 needs Q44). `make
  done` still fails first at `[2/6]` condition 2.
- New findings: the `/red/opportunities` register route and its response already
  exposed everything the screen needs (Q14), so Q43 needed no new backend route
  and no new client read beyond `listOpportunities`. The register is
  proposal-only by domain invariant (`OpportunityState.PROPOSED`), and the API
  response flattens the source to `source_asset_id`/`source_kind`/
  `source_version`, so the view renders the pinned version directly. No
  dedicated tenant-scoped authority read was found in the client seam, so Q44
  may need a new read route rather than a pure UI feature (unverified).
- Blockers (unchanged): `frontend/` Q44 is the last path to DoD condition 6;
  Q8's retrieval, worker and artifact-URL isolation coverage and the condition 2
  cross-client-retrieval scenario are blocked until those seams exist; Q28 stage
  8-10 required kinds blocked on the named methodology-owner placement decision;
  Q16 idempotency keys blocked on a workflow write route and a connector seam;
  Q3 agent registration blocked on the ADR 0006 / vendor-edit tension; Q4 live
  smoke needs `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q31's
  deploy-only scenarios need the Atlas cluster and a chosen backup target.
- Highest priority ready next item: Q44, the authority settings screen (the last
  section 8 screen for condition 6). Required asset: a read-only authority
  settings view at a declared route showing the tenant-scoped designated
  authorities and the approval scope each gate approves against (SPEC.md
  sections 3, 4 and 8: "designated approver identity" and "authority registry a
  gate approves against"), plus its browser test; checkpoint: none (UI, not a
  gate); approver: none. Blocked downstream dependency: condition 6 close (then
  conditions 3, 4, 5, 7, 8, 9). Prerequisite: Q43 (done this cycle). The read
  seam is unverified: a new tenant-scoped authority/registry route may be
  required (see New findings).

### Prior cycle (2026-10-03T203157Z)

- Selected item was Q42, the
  performance review screen (SPEC.md sections 4 and 8 and 13 condition 6; queue
  item Q42). It was the highest priority ready item: its only dependency Q41 was
  done, and it was the head of the Q42-Q45 chain for condition 6, the largest
  unstarted DoD condition. It outranked alternatives: Q43-Q45 each depended on
  Q42; Q28 stage 8-10 required kinds were still blocked on the named
  methodology-owner placement decision; Q16 needed a workflow write route and a
  connector seam; Q3/Q4 needed the ADR 0006 resolution and a live key; Q8 layer
  coverage and the condition 2 cross-client-retrieval scenario had no
  retrieval/worker/artifact seam yet; Q47-Q50 needed the Atlas cluster. Q31 also
  blocked condition 2 on a connector idempotency seam and the deploy-only
  scenarios. The canon gap register had no ready pipeline item: its remaining
  entries are implemented or are candidate pipeline additions awaiting a
  named-owner decision, so no canon-covered method artifact outranked this gate
  work.
- Outcome: new `frontend/src/features/performance-review/` feature.
  `PerformanceReview.tsx` is a presentational view over two tenant-scoped reads:
  `baselineStage`/`baselinePins` surface the stage 10 "Performance Baseline
  Established" gate row (state, checkpoint, exact pinned baseline asset versions,
  missing kinds, owner, due date, next action, blockers) from the engagement
  production view, and `milestoneStates` maps each of SPEC.md section 4's four
  distinct stage 10 milestones (first qualified traffic, lead, appointment, sale)
  to the funnel step the canon's Metrics Matrix solves down (canon files 22-24:
  audience, lead, appointment, customer) and marks a milestone observed only when
  an observed (non-placeholder) `/red/measurements` record exists, otherwise
  pending, so a missing observation is shown pending rather than guessed.
  `PerformanceReviewScreen.tsx` owns the parallel tenant-scoped reads
  (`getProductionView` + `listMeasurements`); route `/performance-review`
  (`src/app/performance-review/page.tsx`) binds the `performance-review` screen
  id now declared in `frontend/dod-screens.txt`. The API client gained the
  `MeasurementRecord`/`MeasurementList`/`MetricDefinitionSummary` types and
  `listMeasurements`. No product authority, gate decision or pipeline stage
  changed; a read approves no baseline and starts no optimization.
- Evidence: `frontend/src/features/performance-review/PerformanceReview.test.tsx`
  (10 tests) pins `baselineStage`/`baselinePins`, `milestoneStates` (observed vs
  pending, newest-record selection, placeholder stays pending, the sale/customer
  mapping), the rendered baseline state/pins/owner, the milestone rows, the empty
  baseline and no-observation states, loading/error, and a stubbed-fetch screen
  read asserting both tenant-scoped paths (2 fetches). `npm test` -> 10 files, 84
  passed (10 new). `npm run build` -> compiled, `/performance-review` route
  emitted. `make check` -> 2272 passed, 2 skipped, 706 subtests passed.
  `bash scripts/check_frontend_build.sh frontend` -> exit 0.
  `bash scripts/check_frontend_screens.sh frontend` -> still exit 1, now 2
  remaining section 8 ids (portfolio-opportunities, authority-settings;
  condition 6 needs Q43-Q44). `make done` still fails first at `[2/6]` condition
  2.
- New findings: the stage 10 measurement registry route `GET /red/measurements`
  already existed (Q13), so this screen needed no new backend route; however the
  production-view route does not populate its `metric_reporting` field (it is
  passed empty through the query), so the METRICS reporting dimension is not
  readable from the production view and the screen reads the measurement registry
  directly. The stage 10 baseline's milestone observations are not durably stored
  -- the gate decision pins only the twelve canonical kinds at the baseline
  version -- so observed/pending is derived from the measured funnel steps, a
  documented projection, not a stored stage 10 milestone state.
- Blockers (unchanged): `frontend/` Q43-Q44 are the path to DoD condition 6;
  Q8's retrieval, worker and artifact-URL isolation coverage and the condition 2
  cross-client-retrieval scenario are blocked until those seams exist; Q28 stage
  8-10 required kinds blocked on the named methodology-owner placement decision;
  Q16 idempotency keys blocked on a workflow write route and a connector seam;
  Q3 agent registration blocked on the ADR 0006 / vendor-edit tension; Q4 live
  smoke needs `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q31's
  deploy-only scenarios need the Atlas cluster and a chosen backup target.
- Highest priority ready next item: Q43, the portfolio opportunities screen.
  Required asset: a portfolio opportunities view at a declared route showing the
  tenant-scoped stage 10/portfolio `Opportunity` proposals and their exact
  pinned grounding asset versions over the tenant-scoped `/opportunities` read
  (SPEC.md sections 3, 8 and 13 condition 6), plus its browser test; checkpoint:
  none (UI, not a gate); approver: none. Blocked downstream dependency: Q44-Q45.
  Prerequisite: Q42 (done this cycle).

### Prior cycle (2026-10-03T202836Z)

- Cycle 2026-10-03T202836Z (Ralph cycle, this run): selected item was Q41, the
  launch readiness screen (SPEC.md sections 4, 7, 8 and 13 condition 6; queue
  item Q41). It is the highest priority ready item: its only dependency Q40 is
  done, and it is now the head of the Q41-Q45 chain for condition 6, the largest
  unstarted DoD condition. It outranks alternatives: Q42-Q45 each depend on Q41;
  Q28 stage 8-10 required kinds are still blocked on the named methodology-owner
  placement decision; Q16 needs a workflow write route and a connector seam;
  Q3/Q4 need the ADR 0006 resolution and a live key; Q8 layer coverage and the
  condition 2 cross-client-retrieval scenario have no retrieval/worker/artifact
  seam yet; Q47-Q50 need the Atlas cluster. Q31 also blocks condition 2 on a
  connector idempotency seam and the deploy-only scenarios. The canon gap
  register has no ready pipeline item: its remaining entries are implemented or
  are candidate pipeline additions awaiting a named-owner decision, so no
  canon-covered method artifact outranks this gate work.
- Outcome: the launch readiness screen required a read the platform did not
  have. Stage 9 launch QAs are durable and tenant-scoped, but the read seam only
  exposed `get`, so no route could list a client's authorized QAs. This cycle
  added the narrow `LaunchQARepository.list` port method with in-memory and
  PostgreSQL implementations, a read-only paginated `GET /red/launch-qas` route
  projecting each QA's state, its checks (kind, outcome, evidence, owner and
  `is_critical_path`) and the designated human's pinned traffic authorization,
  and a new `frontend/src/features/launch-readiness/` feature.
  `LaunchReadiness.tsx` is a presentational view with the `checksWithOutcome`,
  `criticalFailures`, `exceptions` and `isAuthorized` helpers: it surfaces the
  stage 9 QA state, the critical-path failures and excepted checks that block or
  qualify "Launch Approved", and the exact `authorized_by`, `intended_use` and
  `authorized_on` (SPEC.md section 4, stage 9). `LaunchReadinessScreen.tsx` owns
  the tenant-scoped read; route `/launch-readiness`
  (`src/app/launch-readiness/page.tsx`) binds the `launch-readiness` screen id
  now declared in `frontend/dod-screens.txt`. No product authority, gate
  decision or pipeline stage changed; a read authorizes no traffic.
- Evidence: `tests/unit/execution/test_launch_qas_route.py` (5 tests) drives the
  real app against an in-memory QA store: it pins the tenant-scoped listing, the
  exact check projection (18 checks in canonical order with outcomes and
  `is_critical_path`), the off-critical exception with its named owner, the
  other-tenant empty read, the required tenant parameter and pagination.
  `tests/unit/execution/test_launch_qa_repository.py` gained 2 tests for `list`
  ordering and the blank-tenant refusal (19 total). `npm test` -> 9 files, 74
  passed (9 new). `npm run build` -> compiled, `/launch-readiness` route
  emitted. `make check` -> 2272 passed, 2 skipped, 706 subtests passed.
  `bash scripts/check_frontend_build.sh frontend` -> exit 0.
  `bash scripts/check_frontend_screens.sh frontend` -> still exit 1, now 3
  remaining section 8 ids (performance-review, portfolio-opportunities,
  authority-settings; condition 6 needs Q42-Q44). `make done` still fails first
  at `[2/6]` condition 2.
- New findings: the `LaunchQA` aggregate and its durable store already existed
  (migration `0008_launch_qas`) and already carried the complete stage 9
  evidence, but the read seam exposed only `get`, so the launch readiness screen
  was the first UI item that needed a new backend route. The store only holds
  QAs that passed "Launch Approved" (a non-ready QA is refused on save), so
  every listed QA is ready-for-traffic and pins an authorization;
  `is_critical_path` is derived from the check kind, not stored, so the route
  projects it from the domain enum.
- Blockers (unchanged): `frontend/` Q42-Q44 are the path to DoD condition 6;
  Q8's retrieval, worker and artifact-URL isolation coverage and the condition 2
  cross-client-retrieval scenario are blocked until those seams exist; Q28 stage
  8-10 required kinds blocked on the named methodology-owner placement decision;
  Q16 idempotency keys blocked on a workflow write route and a connector seam;
  Q3 agent registration blocked on the ADR 0006 / vendor-edit tension; Q4 live
  smoke needs `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q31's
  deploy-only scenarios need the Atlas cluster and a chosen backup target.
- Highest priority ready next item: Q42, the performance review screen.
  Required asset: a performance review at a declared route showing the
  tenant-scoped stage 10 baseline state and its post-launch milestones over the
  tenant-scoped stage 10 / production-view reads (SPEC.md sections 4 and 8),
  plus its browser test; checkpoint: none (UI, not a gate); approver: none.
  Blocked downstream dependency: Q43-Q45. Prerequisite: Q41 (done this cycle).

### Prior cycle (2026-10-03T202643Z)

- Cycle 2026-10-03T202643Z (Ralph cycle, this run): selected item was Q40, the
  workflow run detail (SPEC.md sections 4, 7, 8 and 13 condition 6; queue item
  Q40). It is the highest priority ready item: its only dependency Q39 is done,
  and it is now the head of the Q40-Q45 chain for condition 6, the largest
  unstarted DoD condition. It outranks alternatives: Q41-Q45 each depend on Q40;
  Q28 stage 8-10 required kinds are still blocked on the named methodology-owner
  placement decision; Q16 needs a workflow write route and a connector seam;
  Q3/Q4 need the ADR 0006 resolution and a live key; Q8 layer coverage and the
  condition 2 cross-client-retrieval scenario have no retrieval/worker/artifact
  seam yet; Q47-Q50 need the Atlas cluster. Q31 also blocks condition 2 on a
  connector idempotency seam and the deploy-only scenarios. The canon gap
  register has no ready pipeline item: its remaining entries are implemented or
  are candidate pipeline additions awaiting a named-owner decision, so no
  canon-covered method artifact outranks this gate work.
- Outcome: new `frontend/src/features/workflow-run/` feature.
  `WorkflowRunDetail.tsx` is a presentational detail over the tenant-scoped
  durable run from `GET /red/clients/{tenant_id}/workflows/{run_id}`: it shows
  the run status, the exact pinned definition version (SPEC.md section 10), the
  completed step prefix, the in-progress step, pending approval, next step and
  failure reason, the stable run `event_id`, and the append-only event log
  ordered by the `eventOrdinal` parsed from each transition `event_id`, with
  every transition's actor, reason, timestamp, old and new status and
  correlation id (SPEC.md section 4). `WorkflowRunDetailScreen.tsx` owns the
  tenant- plus run-scoped read; route `/workflow-run-detail`
  (`src/app/workflow-run-detail/page.tsx`) binds the `workflow-run-detail`
  screen id now declared in `frontend/dod-screens.txt`. The API client's
  `WorkflowRunView` was an inaccurate minimal stub (never used by a screen) and
  was corrected to the actual route projection, adding `WorkflowRunTransition`.
  No product authority, gate decision or pipeline stage changed; the detail can
  advance no run.
- Evidence: `frontend/src/features/workflow-run/WorkflowRunDetail.test.tsx` (10
  tests) pins `eventOrdinal`, `orderedTransitions` ordering and no-ordinal
  handling, the rendered run state/definition/event id/completed/progress
  fields, the exact per-transition log fields and order, the failure-only
  reason, the prompt/loading/error/empty states, and a stubbed-fetch screen read
  asserting the tenant-scoped run path. `npm test` -> 8 files, 65 passed (10
  new). `npm run build` -> compiled, `/workflow-run-detail` route emitted.
  `make check` -> 2265 passed, 2 skipped, 704 subtests passed.
  `bash scripts/check_frontend_build.sh frontend` -> exit 0.
  `bash scripts/check_frontend_screens.sh frontend` -> still exit 1, now 4
  remaining section 8 ids (launch-readiness, performance-review,
  portfolio-opportunities, authority-settings; condition 6 needs Q41-Q45).
  `make done` still fails first at `[2/6]` condition 2.
- New findings: `GET /red/clients/{tenant_id}/workflows/{run_id}` already
  projects the full run state and its append-only transition log with a stable
  `event_id`, so the detail needed only a corrected client type and the
  presentational screen; no backend route was needed. The run `event_id` is
  `{run_id}:{len(transitions)}` and each transition `event_id` is
  `{run_id}:{index}` (1-based), so the event log order is derivable from the id
  alone and no wall clock is trusted.
- Blockers (unchanged): `frontend/` Q41-Q45 are the path to DoD condition 6;
  Q8's retrieval, worker and artifact-URL isolation coverage and the condition 2
  cross-client-retrieval scenario are blocked until those seams exist; Q28 stage
  8-10 required kinds blocked on the named methodology-owner placement decision;
  Q16 idempotency keys blocked on a workflow write route and a connector seam;
  Q3 agent registration blocked on the ADR 0006 / vendor-edit tension; Q4 live
  smoke needs `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q31's
  deploy-only scenarios need the Atlas cluster and a chosen backup target.
- Highest priority ready next item: Q41, the launch readiness screen.
  Required asset: a launch readiness at a declared route showing the
  tenant-scoped stage 9 launch QA state, its required checks, exceptions and
  traffic authorization (SPEC.md sections 4 and 8) over the tenant-scoped stage
  9 / production-view reads, plus its browser test; checkpoint: none (UI, not a
  gate); approver: none. Blocked downstream dependency: Q42-Q45. Prerequisite:
  Q40 (done this cycle).

### Prior cycle (2026-10-03T202445Z)

- Cycle 2026-10-03T202445Z (Ralph cycle, this run): selected item was Q39, the
  approval inbox with exact version diff (SPEC.md sections 3, 4, 8 and 13
  condition 6; queue item Q39). It is the highest priority ready item: its only
  dependency Q38 is done, and it is now the head of the Q39-Q45 chain for
  condition 6, the largest unstarted DoD condition. It outranks alternatives:
  Q40-Q45 each depend on Q39; Q28 stage 8-10 required kinds are still blocked on
  the named methodology-owner placement decision; Q16 needs a workflow write
  route and a connector seam; Q3/Q4 need the ADR 0006 resolution and a live key;
  Q8 layer coverage and the condition 2 cross-client-retrieval scenario have no
  retrieval/worker/artifact seam yet; Q47-Q50 need the Atlas cluster. Q31 also
  blocks condition 2 on a connector idempotency seam and the deploy-only
  scenarios. The canon gap register has no ready pipeline item: its remaining
  entries are implemented or are candidate pipeline additions awaiting a
  named-owner decision, so no canon-covered method artifact outranks this gate
  work.
- Outcome: new `frontend/src/features/approval-inbox/` feature.
  `ApprovalInbox.tsx` is a presentational inbox over the tenant-scoped
  version-specific approvals from `GET /red/approvals`: it groups each approval
  by its pinned asset kind with the `approvalHistories` helper, surfaces the
  `latest` exact version with `exactVersion`, orders each history ascending with
  a stable `orderKey`, finds the `priorApproval` and renders the exact
  `approvalDiff` field-by-field (version, scope, outcome, approver,
  requested_by, expires_on, stage_number, decided_on) against the previous
  version of the same asset, showing a baseline approval when none exists;
  `ApprovalInboxScreen.tsx` owns the tenant-scoped read; route `/approval-inbox`
  (`src/app/approval-inbox/page.tsx`) binds the `approval-inbox` screen id now
  declared in `frontend/dod-screens.txt`. The API client gained `ApprovalRecord`,
  `ApprovalList` and `listApprovals`. No product authority, gate decision or
  pipeline stage changed; the inbox can approve nothing.
- Evidence: `frontend/src/features/approval-inbox/ApprovalInbox.test.tsx` (12
  tests) pins `exactVersion`, `approvalHistories` grouping/ordering/latest,
  `priorApproval` for a successor and a baseline, `approvalDiff` exact
  prior-to-current entries, baseline and no-change handling, the rendered latest
  version and diff, the loading/error states, the empty state, and a
  stubbed-fetch screen read asserting the tenant-scoped request path. `npm test`
  -> 7 files, 55 passed (12 new). `npm run build` -> compiled, `/approval-inbox`
  route emitted. `make check` -> 2265 passed, 2 skipped, 704 subtests passed.
  `bash scripts/check_frontend_build.sh frontend` -> exit 0.
  `bash scripts/check_frontend_screens.sh frontend` -> still exit 1, now 5
  remaining section 8 ids (workflow-run-detail, launch-readiness,
  performance-review, portfolio-opportunities, authority-settings; condition 6
  needs Q40-Q45). `make done` still fails first at `[2/6]` condition 2.
- New findings: `GET /red/approvals` already projects the exact asset version,
  scope, requester, designated approver, outcome and expiry per approval, and
  `asset_id` in that projection is the pinned asset *kind* (an `AssetVersionRef`
  keyed by kind), so grouping the append-only approvals by `asset_id` yields a
  real per-asset version history. The diff is derived only from those records;
  it resolves no asset content and asserts no approval rule. No backend route
  was needed.
- Blockers (unchanged): `frontend/` Q40-Q45 are the path to DoD condition 6;
  Q8's retrieval, worker and artifact-URL isolation coverage and the condition 2
  cross-client-retrieval scenario are blocked until those seams exist; Q28 stage
  8-10 required kinds blocked on the named methodology-owner placement decision;
  Q16 idempotency keys blocked on a workflow write route and a connector seam;
  Q3 agent registration blocked on the ADR 0006 / vendor-edit tension; Q4 live
  smoke needs `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q31's
  deploy-only scenarios need the Atlas cluster and a chosen backup target.
- Highest priority ready next item: Q40, the workflow run detail screen.
  Required asset: a workflow run detail at a declared route showing the
  tenant-scoped run state and stable append-only event log with the polled
  `event_id` (SPEC.md sections 7 and 8) over the tenant-scoped `GET
  /red/clients/{tenant_id}/workflows/{run_id}` read, plus its browser test;
  checkpoint: none (UI, not a gate); approver: none. Blocked downstream
  dependency: Q41-Q45. Prerequisite: Q39 (done this cycle).

### Prior cycle (2026-10-03T202254Z)

- Cycle 2026-10-03T202254Z (Ralph cycle, this run): selected item was Q38, the
  build board with dependency view (SPEC.md sections 3, 4, 8 and 13 condition 6;
  queue item Q38). It is the highest priority ready item: its only dependency
  Q37 is done, and it is now the head of the Q38-Q45 chain for condition 6, the
  largest unstarted DoD condition. It outranks alternatives: Q39-Q45 each depend
  on Q38; Q28 stage 8-10 required kinds are still blocked on the named
  methodology-owner placement decision; Q16 needs a workflow write route and a
  connector seam; Q3/Q4 need the ADR 0006 resolution and a live key; Q8 layer
  coverage and the condition 2 cross-client-retrieval scenario have no
  retrieval/worker/artifact seam yet; Q47-Q50 need the Atlas cluster. Q31 also
  blocks condition 2 on a connector idempotency seam and the deploy-only
  scenarios. The canon gap register has no ready pipeline item: its remaining
  entries are implemented or are candidate pipeline additions awaiting a
  named-owner decision, so no canon-covered method artifact outranks this gate
  work.
- Outcome: new `frontend/src/features/build-board/` feature. `BuildBoard.tsx`
  is a presentational board over the tenant-scoped production work items from
  `GET /red/builds`: it groups each BuildObject into its SPEC.md section 4
  lifecycle state column using the `boardStates` canonical-order helper, and
  renders per build the type, purpose, audience, owner, next action, the
  `dependencyRefs` it declares and its blockers, with a dependency view listing
  the `blockedBuilds`; `BuildBoardScreen.tsx` owns the tenant-scoped read;
  route `/build-board` (`src/app/build-board/page.tsx`) binds the `build-board`
  screen id now declared in `frontend/dod-screens.txt`. The API client gained
  `BuildObject`, `BuildList` and `listBuilds`. No product authority, gate
  decision or pipeline stage changed; the board can transition no build.
- Evidence: `frontend/src/features/build-board/BuildBoard.test.tsx` (11 tests)
  pins `boardStates` canonical ordering and unknown-state handling,
  `buildsInState` filtering and ordering, `dependencyRefs`, `blockedBuilds`,
  build field/owner/next/refs/blocker rendering, the blocked dependency view,
  the loading/error states, the empty states, and a stubbed-fetch screen read
  asserting the tenant-scoped request path. `npm test` -> 6 files, 43 passed (11
  new). `npm run build` -> compiled, `/build-board` route emitted.
  `make check` -> 2265 passed, 2 skipped, 704 subtests passed.
  `bash scripts/check_frontend_build.sh frontend` -> exit 0.
  `bash scripts/check_frontend_screens.sh frontend` -> still exit 1, now 6
  remaining section 8 ids (approval-inbox, workflow-run-detail,
  launch-readiness, performance-review, portfolio-opportunities,
  authority-settings; condition 6 needs Q39-Q45). `make done` still fails first
  at `[2/6]` condition 2.
- New findings: `GET /red/builds` already returns a fully typed BuildObject
  (state, owner, next_action, is_active, is_blocked, blockers, refs), so the
  board needed only client types and `listBuilds` and no new backend route. The
  dependency view is read-only and derives only ordering and grouping from the
  build's own `refs`/`blockers`; it resolves no asset and asserts no state
  transition, so it re-derives no production rule.
- Blockers (unchanged): `frontend/` Q39-Q45 are the path to DoD condition 6;
  Q8's retrieval, worker and artifact-URL isolation coverage and the condition 2
  cross-client-retrieval scenario are blocked until those seams exist; Q28 stage
  8-10 required kinds blocked on the named methodology-owner placement decision;
  Q16 idempotency keys blocked on a workflow write route and a connector seam;
  Q3 agent registration blocked on the ADR 0006 / vendor-edit tension; Q4 live
  smoke needs `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q31's
  deploy-only scenarios need the Atlas cluster and a chosen backup target.
- Highest priority ready next item: Q39, the approval inbox with exact version
  diff. Required asset: an approval inbox at a declared route showing the
  tenant-scoped version-specific approvals and their exact asset versions with
  the version diff (SPEC.md sections 3, 4 and 8) over the tenant-scoped
  approval read, plus its browser test; checkpoint: none (UI, not a gate);
  approver: none. Blocked downstream dependency: Q40-Q45. Prerequisite: Q38
  (done this cycle).

### Prior cycle (2026-10-03T202056Z)

- Cycle 2026-10-03T202056Z (Ralph cycle, prior): selected item was Q37, the
  offer and journey editor screen (SPEC.md sections 3, 5, 7 and 8; section 13
  condition 6; queue item Q37). It is the highest priority ready item: its only
  dependency Q36 is done, and it is now the head of the Q37-Q45 chain for
  condition 6, the largest unstarted DoD condition. It outranks alternatives:
  Q38-Q45 each depend on Q37; Q28 stage 8-10 required kinds are still blocked on
  the named methodology-owner placement decision; Q16 needs a workflow write
  route and a connector seam; Q3/Q4 need the ADR 0006 resolution and a live key;
  Q8 layer coverage and the condition 2 cross-client-retrieval scenario have no
  retrieval/worker/artifact seam yet; Q47-Q50 need the Atlas cluster. Q31 also
  blocks condition 2 on a connector idempotency seam and the deploy-only
  scenarios. The canon gap register has no ready pipeline item: its remaining
  entries are implemented or are candidate pipeline additions awaiting a
  named-owner decision, so no canon-covered method artifact outranks this gate
  work.
- Outcome: new `frontend/src/features/offer-journey/` feature.
  `OfferJourneyEditor.tsx` is a presentational view over the tenant-scoped
  approved offers and authorized journey releases: it renders each stage 5
  production-ready offer (audience, promise, eligibility, price hypothesis,
  owner, state and the exact method versions it pins, with a visible warning when
  no method dependency is pinned) and each stage 8/9 journey release (routing,
  configuration digest, rollback ref, released kinds and the exact pinned asset
  versions), with the `pinnedMethodRefs` and `releasedAssetKinds` helpers
  stabilizing display order; `OfferJourneyEditorScreen.tsx` owns the two
  tenant-scoped reads from `GET /red/offers?tenant_id=` and
  `GET /red/journeys?tenant_id=` in parallel; route `/offer-and-journey`
  (`src/app/offer-and-journey/page.tsx`) binds the `offer-and-journey-editor`
  screen id now declared in `frontend/dod-screens.txt`. The API client gained
  `MethodReference`, `OfferVersion`, `OfferList`, `JourneyReleaseAsset`,
  `JourneyRelease`, `JourneyReleaseList`, `listOffers` and `listJourneys`. No
  product authority, gate decision or pipeline stage changed; the UI can approve
  no offer and authorize no traffic. The stage 5 shape follows canon files 11 and
  12 and the routing shape canon files 13, 14, 21 and 22, cited in the component
  docstring (SPEC.md section 12.4).
- Evidence: `frontend/src/features/offer-journey/OfferJourneyEditor.test.tsx`
  (9 tests) pins `pinnedMethodRefs` ordering and empty handling,
  `releasedAssetKinds` sorting, offer field and pinned-method rendering, the
  missing-method warning, journey routing/digest/rollback/kinds/asset rendering,
  the loading/error states, both empty states, and a stubbed-fetch screen read
  asserting both tenant-scoped request paths. `npm test` -> 5 files, 32 passed
  (9 new). `npm run build` -> compiled, `/offer-and-journey` route emitted.
  `make check` -> 2265 passed, 2 skipped, 704 subtests passed.
  `bash scripts/check_frontend_build.sh frontend` -> exit 0.
  `bash scripts/check_frontend_screens.sh frontend` -> still exit 1, now 7
  remaining section 8 ids (build-board, approval-inbox, workflow-run-detail,
  launch-readiness, performance-review, portfolio-opportunities,
  authority-settings; condition 6 needs Q38-Q45). `make done` still fails first
  at `[2/6]` condition 2.
- New findings: both reads are tenant-query-scoped (`GET /red/offers?tenant_id=`
  and `GET /red/journeys?tenant_id=`) and read-only, matching SPEC.md section 7
  and the backend's required-scope rule, so the editor needed only client types
  and methods and no new backend route. An offer already returns its pinned
  `method_refs` (method id, version, intended use) and a release already returns
  its `released_kinds` and exact asset versions, so the editor re-derives no
  offer-readiness or release-authorization rule; a release only exists after the
  stage 9 launch QA is signed ready and authorized, and the offer only lists
  production-ready versions, so the screen shows approved structure only.
- Blockers (unchanged): `frontend/` Q38-Q45 are the path to DoD condition 6;
  Q8's retrieval, worker and artifact-URL isolation coverage and the condition 2
  cross-client-retrieval scenario are blocked until those seams exist; Q28 stage
  8-10 required kinds blocked on the named methodology-owner placement decision;
  Q16 idempotency keys blocked on a workflow write route and a connector seam;
  Q3 agent registration blocked on the ADR 0006 / vendor-edit tension; Q4 live
  smoke needs `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q31's
  deploy-only scenarios need the Atlas cluster and a chosen backup target.
- Highest priority ready next item: Q38, the build board with dependency view.
  Required asset: a build board at a declared route showing the tenant-scoped
  build objects with their dependency view and per-build owner, state and next
  action (SPEC.md sections 3, 4 and 8) over the tenant-scoped build read, plus
  its browser test; checkpoint: none (UI, not a gate); approver: none. Blocked
  downstream dependency: Q39-Q45. Prerequisite: Q37 (done this cycle).

### Prior cycle (2026-10-03T201934Z)

- Cycle 2026-10-03T201934Z (Ralph cycle, prior): selected item was Q36, the
  transformation map screen (SPEC.md sections 3, 4 and 8; section 13 condition
  6; queue item Q36). It is the highest priority ready item: its only dependency
  Q35 is done, and it is the head of the Q37-Q45 chain for condition 6, the
  largest unstarted DoD condition. It outranks alternatives: Q37-Q45 each depend
  on Q36; Q28 stage 8-10 required kinds are still blocked on the named
  methodology-owner placement decision; Q16 needs a workflow write route and
  connector seam; Q3/Q4 need the ADR 0006 resolution and a live key; Q8 layer
  coverage and the condition 2 cross-client-retrieval scenario have no
  retrieval/worker/artifact seam yet; Q47-Q50 need the Atlas cluster. Q31 now
  also blocks condition 2 on a connector idempotency seam and the deploy-only
  scenarios. The canon gap register has no ready pipeline item: its remaining
  entries are implemented or are candidate pipeline additions awaiting a
  named-owner decision, so no canon-covered method artifact outranks this gate
  work.
- Outcome: new `frontend/src/features/transformation-map/` feature.
  `TransformationMap.tsx` is a presentational view over the tenant-scoped
  approved methods: it renders each method's pinned stage 4 Signature Solution
  (transformation map, declared starting and final state, narrative, three
  phases, nine named steps by phase) and each step's start/end state and
  inputs/actions/outputs, with the `transformationSteps` helper flattening the
  phases into the nine-stage order; `TransformationMapScreen.tsx` owns the
  tenant-scoped read from `GET /red/methods?tenant_id=`; route
  `/transformation-map` (`src/app/transformation-map/page.tsx`) binds the
  `transformation-map` screen id now declared in `frontend/dod-screens.txt`.
  Backend: `MethodVersionResponse` gained a `signature_solution` projection
  (`SignatureSolutionResponse` with nested `TransformationPhaseResponse` and
  `SignatureStepResponse`), built by the existing public
  `signature_solution_to_payload` mapper, so the read returns the exact pinned
  structure rather than re-deriving it. The API client gained
  `SignatureStep`, `TransformationPhase`, `SignatureSolution`, `MethodVersion`,
  `MethodVersionList` and `listMethods`. No product authority, gate decision or
  pipeline stage changed; the UI can approve or release nothing.
- Evidence: `frontend/src/features/transformation-map/TransformationMap.test.tsx`
  (7 tests) pins `transformationSteps` ordering and null handling, the pinned
  map/states/phase-and-step counts, per-step state and inputs/actions/outputs
  rendering, the loading/error states, the empty state, and a stubbed-fetch
  screen read asserting the tenant-scoped request path.
  `tests/unit/method/test_methods_route.py::test_the_pinned_signature_solution_is_projected_for_the_map`
  asserts the route projects three phases and nine steps with exact states and
  lists. `uv run pytest tests/unit/method/test_methods_route.py -q` -> 6 passed.
  `npm test` -> 4 files, 23 passed (7 new). `npm run build` -> compiled,
  `/transformation-map` route emitted. `make check` -> 2265 passed, 2 skipped,
  704 subtests passed. `bash scripts/check_frontend_build.sh frontend` -> exit
  0. `bash scripts/check_frontend_screens.sh frontend` -> still exit 1, now 8
  remaining section 8 ids (offer-and-journey-editor, build-board,
  approval-inbox, workflow-run-detail, launch-readiness, performance-review,
  portfolio-opportunities, authority-settings; condition 6 needs Q37-Q45).
  `make done` still fails first at `[2/6]` condition 2.
- New findings: the method list read already carried
  `signature_solution_id`, and the shared `signature_solution_to_payload` mapper
  already existed for the commercial offer seam, so projecting the pinned
  structure needed only a schema/serializer addition and no new mapper or
  route. The stage 4 structure is stored on the approved method itself, so the
  screen reads the exact approved version and needs no separate asset lookup.
- Blockers (unchanged): `frontend/` Q37-Q45 are the path to DoD condition 6;
  Q8's retrieval, worker and artifact-URL isolation coverage and the condition 2
  cross-client-retrieval scenario are blocked until those seams exist; Q28 stage
  8-10 required kinds blocked on the named methodology-owner placement decision;
  Q16 idempotency keys blocked on a workflow write route and a connector seam;
  Q3 agent registration blocked on the ADR 0006 / vendor-edit tension; Q4 live
  smoke needs `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q31's
  deploy-only scenarios need the Atlas cluster and a chosen backup target.
- Highest priority ready next item: Q37, the offer and journey editor screen.
  Required asset: an offer and journey editor at a declared route showing the
  approved stage 5 offer version and its journey routing (SPEC.md sections 3, 5
  and 8) over the tenant-scoped offer read, plus its browser test; checkpoint:
  none (UI, not a gate); approver: none. Blocked downstream dependency: Q38-Q45.
  Prerequisite: Q36 (done this cycle).

### Prior cycle (2026-10-03T201635Z)

- Cycle 2026-10-03T201635Z (Ralph cycle, prior): selected item was Q35, the
  source and claim explorer screen (SPEC.md sections 3, 7 and 8; section 13
  condition 6; queue item Q35). It is the highest priority ready item: its only
  dependency Q34 is done, and it is now the head of the Q35-Q45 chain for
  condition 6, the largest unstarted DoD condition. It outranks alternatives:
  Q36-Q45 each depend on Q35; Q28 stage 8-10 required kinds are still blocked on
  the named methodology-owner placement decision; Q16 needs a workflow write
  route and connector seam; Q3/Q4 need the ADR 0006 resolution and a live key;
  Q8 layer coverage and the condition 2 cross-client-retrieval scenario have no
  retrieval/worker/artifact seam yet; Q47-Q50 need the Atlas cluster. The canon
  gap register has no ready pipeline item: its remaining entries are all
  implemented or are candidate pipeline additions awaiting a named-owner
  decision (Serve and Grow; service and partnership lines), so no canon-covered
  method artifact outranks this gate work.
- Outcome: new `frontend/src/features/source-explorer/` feature.
  `SourceClaimExplorer.tsx` is a presentational view over the tenant-scoped
  sources and claims: it renders each source's provenance (locator, checksum,
  capture time, access rule) and the claims it grounds, and each claim's
  statement, provenance class, direct-source flag, confidence note and exact
  source citations, with helpers `claimsForSource` and `groundedClaims`;
  `SourceClaimExplorerScreen.tsx` owns the tenant-scoped read and fetches
  `GET /red/clients/{tenant}/sources` and `GET /red/claims?tenant_id=` in
  parallel; route `/source-explorer` (`src/app/source-explorer/page.tsx`) binds
  the `source-and-claim-explorer` screen id now declared in
  `frontend/dod-screens.txt`. The API client gained `SourceRecord`,
  `SourceRecordList`, `ClaimCitation`, `Claim`, `ClaimList`, `listSources` and
  `listClaims`. No product authority, gate decision or pipeline stage changed;
  the UI can set no provenance, add no citation and approve nothing.
- Evidence: `frontend/src/features/source-explorer/SourceClaimExplorer.test.tsx`
  (6 tests) pins `claimsForSource` grounding, `groundedClaims` direct-source
  filtering, source provenance plus citation rendering, the
  directly-sourced-vs-unsourced split, the loading/error states, and a
  stubbed-fetch screen read asserting both tenant-scoped request paths.
  `npm test` -> 3 files, 16 passed (6 new). `npm run build` -> compiled,
  `/source-explorer` route emitted. `bash scripts/check_frontend_build.sh
  frontend` -> exit 0. `bash scripts/check_frontend_screens.sh frontend` ->
  still exit 1, now 9 remaining section 8 ids (honest red; condition 6 needs
  Q36-Q45). `make done` still fails first at `[2/6]` condition 2 (four section
  11 scenarios uncovered).
- New findings: the source list read is tenant-path-scoped
  (`/red/clients/{tenant_id}/sources?limit=&offset=`) while the claim list read
  is tenant-query-scoped (`/red/claims?tenant_id=&limit=&offset=`); both match
  the SPEC.md section 7 resource set and the backend's required-scope rule, so
  the explorer needs no new backend route. A claim carries
  `is_directly_sourced` and a per-citation checksum/location the backend already
  verified against the stored immutable source, so the UI can show grounding
  without re-deriving it.
- Blockers (unchanged): `frontend/` Q36-Q45 are the path to DoD condition 6;
  Q8's retrieval, worker and artifact-URL isolation coverage and the condition 2
  cross-client-retrieval scenario are blocked until those seams exist; Q28 stage
  8-10 required kinds blocked on the named methodology-owner placement decision;
  Q16 idempotency keys blocked on a workflow write route and a connector seam;
  Q3 agent registration blocked on the ADR 0006 / vendor-edit tension; Q4 live
  smoke needs `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q31's
  deploy-only scenarios need the Atlas cluster and a chosen backup target.
- Highest priority ready next item: Q36, the transformation map screen.
  Required asset: a transformation map at a declared route showing the stage 4
  Signature Solution's three phases, nine steps and stage transitions (SPEC.md
  sections 3 and 8) reading the tenant-scoped `/red/methods` endpoint, plus its
  browser test; checkpoint: none (UI, not a gate); approver: none. Blocked
  downstream dependency: Q37-Q45. Prerequisite: Q35 (done this cycle).

### Prior cycle (2026-10-03T201337Z)

- Cycle 2026-10-03T201337Z (Ralph cycle, prior): selected item was Q33, the
  portfolio command center screen plus the frontend browser runner (SPEC.md
  sections 7 and 8; section 13 condition 6; queue item Q33). It is the highest
  priority ready item: its only dependency Q32 (the Next.js shell) is done, and
  it is the head of the Q33-Q45 dependency chain for condition 6, the largest
  unstarted DoD condition. The prior cycle hardened `[5/6]`
  (`scripts/check_frontend_build.sh`) to require a runnable `npm test`, so Q33
  also had to choose the browser runner and wire it, or the gate would stay
  honestly red. It outranks alternatives: Q34-Q45 each depend on Q33; Q28
  stage 8-10 required kinds are blocked on the named methodology-owner
  placement decision; Q16 needs a workflow write route and connector seam;
  Q3/Q4 need the ADR 0006 resolution and a live key; Q8 layer coverage and the
  condition 2 cross-client-retrieval scenario have no retrieval/worker/artifact
  seam yet; Q47-Q50 need the Atlas cluster.
- Outcome: new `frontend/src/features/command-center/` feature. Presentational
  `CommandCenter.tsx` renders the ranked `GET /red/interventions` cards (SPEC.md
  section 7 fields: severity, reason, subject, explanation, owner, next action,
  due date, affected builds) and filters dismissed cards; container
  `CommandCenterScreen.tsx` owns the tenant-scoped read with a tenant/engagement/
  date form; route `/command-center` (`src/app/command-center/page.tsx`) binds
  the `portfolio-command-center` screen id declared in the new
  `frontend/dod-screens.txt`. Chose Vitest + jsdom + Testing Library as the
  browser runner (`vitest.config.ts`, `npm test` -> `vitest run`); the API client
  gained `InterventionCard`/`InterventionList` types and `listInterventions`.
  No product authority, gate decision or pipeline stage changed; the UI can
  approve or release nothing.
- Evidence: `frontend/src/features/command-center/CommandCenter.test.tsx` (5
  tests) renders two active cards and asserts reasons, owners, next actions and
  affected builds appear, drops a dismissed card (count 0), and covers the
  loading/error states plus a stubbed-fetch screen read asserting the
  `/red/interventions?tenant_id=3fmindset` request. `npm test` -> 5 passed;
  `npm run build` -> compiled, TypeScript finished, `/command-center` route
  emitted. `bash scripts/check_frontend_build.sh frontend` -> exit 0
  ("build compiled and the browser suite ran"), the prior cycle's red gate now
  green. `bash scripts/check_frontend_screens.sh frontend` -> still exit 1 with
  the 11 remaining section 8 screen ids missing (honest red; condition 6 needs
  Q34-Q45). `make done` still fails first at `[2/6]` condition 2.
- New findings: `next build` (Turbopack) type-checks and ignores the co-located
  `*.test.tsx` (build is clean with the vitest imports present). Vitest needs a
  `resolve.alias` for the `@/*` tsconfig path or the container import fails to
  resolve; the config now maps `@` to `./src`. npm blocked the esbuild
  postinstall, but esbuild 0.28 ships its platform binary as an optional
  dependency, so Vitest ran without approving install scripts.
- Blockers (unchanged): `frontend/` Q34-Q45 are the path to DoD condition 6;
  Q8's retrieval, worker and artifact-URL isolation coverage and the condition 2
  cross-client-retrieval scenario are blocked until those seams exist; Q28 stage
  8-10 required kinds blocked on the named methodology-owner placement decision;
  Q16 idempotency keys blocked on a workflow write route and a connector seam;
  Q3 agent registration blocked on the ADR 0006 / vendor-edit tension; Q4 live
  smoke needs `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q31's
  deploy-only scenarios need the Atlas cluster and a chosen backup target.
- Highest priority ready next item: Q34, the client workspace overview screen.
  Required asset: the workspace overview at a declared route showing the client
  workspace state, provenance, dependencies and next action (SPEC.md section 8),
  reading a tenant-scoped backend endpoint, plus its browser test; checkpoint:
  none (UI, not a gate); approver: none. Blocked downstream dependency: Q35-Q45.
  Prerequisite: Q33 (done this cycle).

### Prior cycle (2026-10-03T201148Z)

- Cycle 2026-10-03T201148Z (Ralph cycle, prior): selected item was hardening
  the prototype definition-of-done gate so DoD condition 6 (all section 8
  screens render, SPEC.md section 13) can no longer pass without the frontend
  actually building and its browser suite running. `[5/6]` ran only
  `scripts/check_frontend_screens.sh`, which proves a screen/route manifest and
  the existence of a browser test file, but never compiles the UI nor runs the
  suite. Once Q33-Q44 land real screens, that check could pass on placeholder
  pages and a no-op test, turning `make done` green with a non-compiling UI or
  an unrun suite -- the same class of false stop condition the prior cycles
  closed for `[2/6]`, `[3/6]` and condition 5. It outranks starting Q33 (the
  command center screen): the task prioritizes missing gate integrity over
  downstream dashboards, and Q45 ("all screen browser suite") only adds the
  suite; it does not make the gate require it. No ready method-artifact or
  stage-gate item remained: Q28 stage 8-10 required kinds are blocked on the
  named methodology-owner placement decision, Q16 is blocked on a workflow
  write route and a connector seam, Q3/Q4 are blocked on the ADR 0006 tension
  and a live key, Q8's retrieval/worker/artifact-URL layers have no seam yet,
  and Q47-Q50 need the Atlas cluster.
- Outcome: new standalone `scripts/check_frontend_build.sh` closes the gap. It
  refuses a `frontend/` without `package.json`, requires the package to declare
  both a `build` and a `test` script, and runs `npm run build` then `npm test`
  inside `frontend/`, failing by name if either is missing or fails. `[5/6]` now
  runs it after `check_frontend_screens.sh`, so a green condition 6 requires the
  UI to compile and its browser suite to run, not merely exist. No product
  authority, gate decision or pipeline stage changed.
- Evidence: new `tests/unit/shared/test_frontend_build_check.py` (7 tests) pins
  a complete frontend passing, missing `frontend/`, missing `package.json`, a
  missing `build` script, a missing `test` script, a failing build (which skips
  the suite), and a failing suite; the tests inject a fake `npm` on `PATH` so
  they run without a real toolchain. `make check` -> 2264 passed, 2 skipped, 704
  subtests (was 2257; +7). `bash scripts/check_frontend_build.sh frontend`
  against the real shell -> exit 1
  `frontend/package.json declares no 'test' script; the browser suite is not
  runnable` (honest red; the shell has no browser runner yet). `make done` still
  fails first at `[2/6]` condition 2 (four section 11 scenarios uncovered),
  before reaching `[5/6]`.
- New findings: the real `frontend/package.json` declares `build` but no `test`
  script and ships no browser test runner, so the new gate keeps condition 6
  unmet until Q33+ chooses a runner and wires `npm test`. The first cut parsed
  the package path with `require()` before resolving it, so a relative argument
  (`frontend`) silently read as "no build script"; the script now resolves
  `package.json` with `realpath` first (this was caught by running it against
  the real frontend, not only the absolute-path temp fixtures).
- Blockers (unchanged): `frontend/` Q33-Q45 are the path to DoD condition 6 and
  Q33 now also carries the browser-runner choice; Q8's retrieval, worker and
  artifact-URL isolation coverage and the condition 2 cross-client-retrieval
  scenario are blocked until those seams exist; Q28 stage 8-10 required kinds
  blocked on the named methodology-owner placement decision; Q16 idempotency
  keys blocked on a workflow write route and a connector seam; Q3 agent
  registration blocked on the ADR 0006 / vendor-edit tension; Q4 live smoke
  needs `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q31's
  deploy-only scenarios need the Atlas cluster and a chosen backup target.
- Highest priority ready next item: Q33, the portfolio command center screen,
  now safe to start because the shell (Q32) builds, serves and exposes a typed
  `/red` client, and because `[5/6]` now requires the screen's browser test to
  actually run. Required asset: the command center screen at a declared route
  showing blockers and owners from the `GET /red/interventions` cards (SPEC.md
  sections 7 and 8), plus the browser test runner and `npm test` wiring the
  hardened `[5/6]` gate now demands; checkpoint: none (UI, not a gate);
  approver: none. Blocked downstream dependency: Q34-Q45. Prerequisite: Q32
  (done).

### Prior cycle (2026-10-03T200524Z)

- Cycle 2026-10-03T200524Z (Ralph cycle, prior): selected item was Q32, the
  Next.js shell in `frontend/` plus the RED theme and API client (SPEC.md section
  8; section 13 condition 6; queue item Q32). It is the plan's highest priority
  ready item and its only dependency, Q15 (`/workflows/{id}` polling read), is
  done. Gate integrity is complete: the prior four cycles closed the last
  entirely unchecked DoD condition (condition 5) and the conditions 2, 3 and 6
  gates, so condition 6 (all section 8 screens render) is now the largest
  unstarted dependency chain (Q32-Q45). Q32 outranks Q33-Q45 because each of
  those depends on it, and outranks the blocked alternatives: Q28 stage 8-10
  required kinds need the named methodology-owner placement decision, Q16 needs
  a workflow write route and a connector idempotency seam, Q8 needs the
  retrieval, worker and artifact-serving seams, Q3 needs the ADR 0006
  vendor-edit resolution, Q4 needs a live `OPENROUTER_API_KEY`, and Q47-Q50 need
  the Atlas cluster. Starting the frontend is the only ready path toward DoD
  condition 6.
- Outcome: new self-contained Next.js 16 (React 19, TypeScript) app under
  `frontend/`, built as a thin client carrying no RED business logic (ADR 0007).
  `frontend/package.json` pins `next`/`react`/`react-dom` and a `build` script;
  `next.config.ts` sets `output: "standalone"` and `reactStrictMode`;
  `src/app/layout.tsx` renders the RED-branded shell (RED Operations Director
  banner; `globals.css` RED palette as CSS variables); `src/app/page.tsx` lists
  the twelve section 8 surfaces as not yet implemented; `src/app/health/route.ts`
  serves a liveness probe; `src/shared/api/client.ts` is the typed,
  tenant-scoped client over the `/red` REST surface (SPEC.md section 7), raising
  `RedApiError` on a non-2xx and carrying `tenant_id` on every read. No section 8
  screen is declared in `frontend/dod-screens.txt` yet, so the condition 6 gate
  stays red, correctly.
- Evidence: `npm install` added 28 packages; `npm run build` -> Next.js 16.3.8
  compiled successfully, TypeScript clean, routes `/`, `/_not-found` and
  `/health`; `npm run start` + `curl http://localhost:3000/health` ->
  `{"status":"ok","service":"red-operations-ui"}`, root `/` -> HTTP 200;
  `./scripts/check_frontend_screens.sh frontend` -> exit 1
  `missing frontend/dod-screens.txt` (honest red, no false green); `make check`
  -> 2257 passed, 2 skipped, 704 subtests (unchanged). Next rewrote
  `frontend/tsconfig.json` (jsx `react-jsx`, include `.next/dev/types/**/*.ts`);
  kept as committed.
- New findings: the vendored OpenExecutive UI
  (`vendor/openexecutive/packages/ui`, Next 16 / React 19 / Tailwind 4, tests via
  `node --test scripts/*.test.mjs`) is the reuse target ADR 0008 names, but
  copying it is rejected by that ADR, so Q32 builds RED's own minimal app and
  Q33+ chooses a browser test runner. The condition 6 gate today only checks that
  a test file exists and does not run the frontend build or suite, so a green
  `[5/6]` will still depend on Q45 actually running the build and browser suite.
  No RED authority, gate decision or pipeline stage changed.
- Blockers (unchanged): `frontend/` Q33-Q45 are the path to DoD condition 6;
  Q8's retrieval, worker and artifact-URL isolation coverage and the condition 2
  cross-client-retrieval scenario are blocked until those seams exist; Q28 stage
  8-10 required kinds blocked on the named methodology-owner placement decision;
  Q16 idempotency keys blocked on a workflow write route and a connector seam;
  Q3 agent registration blocked on the ADR 0006 / vendor-edit tension (and
  condition 5's deterministic-e2e part); Q4 live smoke needs
  `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q31's deploy-only
  scenarios (GitOps revert, backup restore) need the Atlas cluster and a chosen
  backup target.
- Highest priority ready next item: Q33, the portfolio command center screen, now
  safe to start because the shell (Q32) builds, serves and exposes a typed `/red`
  client. Required asset: the command center screen at a declared route showing
  blockers and owners from the `GET /red/interventions` cards (SPEC.md sections 7
  and 8); checkpoint: none (UI, not a gate); approver: none. Blocked downstream
  dependency: Q34-Q45. Prerequisite: Q32 (done).

### Prior cycle (2026-10-03T200255Z)

- Cycle 2026-10-03T200255Z (Ralph cycle, prior): selected item was hardening
  the prototype definition-of-done gate so DoD condition 5 (the agent provider
  path, SPEC.md section 13) can no longer pass unverified. The gate `[1/6]`-`[6/6]`
  never checked condition 5 at all: `[2/6]` ran the stage 0-10 e2e and the
  section 11 acceptance coverage (conditions 1 and 2), but nothing asserted "a
  deterministic fake model gateway drives the e2e; a separate live OpenRouter
  smoke passes and the LLM adapter logs model, prompt version, usage and trace
  id". The stage 0-10 e2e drives no agent or model path today (`tests/e2e` uses
  no `ModelGateway`), so once conditions 2, 3, 6 and 9 were met `make done` could
  have turned green with condition 5 absent entirely. It is the same class of
  false stop condition the prior three cycles closed for `[5/6]`, `[3/6]` and
  `[2/6]`, and it outranks starting Q32: Q32-Q45 are downstream dashboards, and
  the task prioritizes missing gate integrity over downstream features. No ready
  method-artifact or stage-gate item remained: Q28 stage 8-10 required kinds are
  blocked on the named methodology-owner placement decision, Q29 is
  domain-complete and tested, Q16 is blocked on a workflow write route and a
  connector idempotency seam, Q3/Q4 are blocked on the ADR 0006 tension and a
  live key, and Q8's remaining retrieval, worker and artifact-URL layers have no
  seam yet.
- Outcome: new standalone `scripts/check_provider_path_coverage.sh` enforces
  condition 5 against a data-driven contract. `tests/unit/agents/covered-provider-
  paths.txt` declares each of the three canonical condition 5 parts as `<part-id>
  <test-file>` (repo-root relative) or `<part-id> uncovered <reason>`; every
  canonical id (`deterministic-e2e`, `live-openrouter-smoke`, `attribution-log`)
  must be declared exactly once, each covered file must exist and contain at least
  one test, and any part still `uncovered` is a named failure listing every
  uncovered part with its reason. `[2/6]` now runs it after the e2e suite and the
  acceptance coverage check (`[2/6]` is relabeled "conditions 1, 2 and 5").
  `attribution-log` is covered by `tests/unit/agents/test_llm_gateway.py`;
  `deterministic-e2e` (no agent path in the e2e) and `live-openrouter-smoke` (paid,
  env-gated human proof) are honestly `uncovered`, so condition 5 is unmet and the
  gate fails. No product authority, gate decision or pipeline stage changed.
- Evidence: `make check` -> 2257 passed, 2 skipped, 704 subtests; pyflakes clean.
  New `tests/unit/shared/test_provider_path_coverage_check.py` (10 tests) covers a
  complete suite passing, a missing directory, a missing manifest, an uncovered
  part, an undeclared part, an unknown part, a duplicate part, a declared file
  that is missing, a declared file with no test, and the real suite failing with
  `deterministic-e2e` and `live-openrouter-smoke` named. `make done` still fails
  at `[2/6]`, first at the section 11 acceptance coverage (condition 2) and then,
  once that is closed, at the provider-path coverage (condition 5).
- New findings: condition 5 was the last entirely unchecked DoD condition. Its
  deterministic-e2e half is unmet because the stage 0-10 e2e is a pure REST gate
  driver with no agent/model call; wiring an agent path into the e2e is blocked on
  Q3 agent registration (the ADR 0006 fork-registration vs DoD condition 7
  zero-vendor-edit tension). The live-smoke half is a paid, env-gated human proof
  (Q4).
- Blockers (unchanged): `frontend/` screens Q32-Q45 are the path to `make done`
  condition 6; Q8's retrieval, worker and artifact-URL isolation coverage and the
  condition 2 cross-client-retrieval scenario are blocked until the retrieval,
  worker and artifact-serving seams exist; Q28 stage 8-10 required kinds blocked
  on the named methodology-owner placement decision; Q16 idempotency keys (and the
  condition 2 duplicate-delivery scenario) blocked on a workflow write route and a
  connector seam; Q3 agent registration blocked on the ADR 0006 / vendor-edit
  tension (and now also blocks condition 5's deterministic-e2e part); Q4 live
  smoke needs `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q31's
  deploy-only scenarios (GitOps revert, backup restore) need the Atlas cluster and
  a chosen backup target.
- Highest priority ready next item: Q32, the Next.js shell in `frontend/` plus
  the RED theme and API client, now safe to start because `make done` cannot pass
  on a screens-less shell (`[5/6]`), an API-only security suite (`[3/6]`), a
  suite-less condition 2 (`[2/6]`) or an unproven provider path (condition 5).
  Required asset: the Next.js app shell that consumes the complete SPEC.md section
  7 REST surface; checkpoint: none (UI, not a gate); approver: none. Blocked
  downstream dependency: Q33-Q45. The stage 0-10 e2e Q30 is already green.

### Prior cycle (2026-10-03T200006Z)

- Cycle 2026-10-03T200006Z (Ralph cycle, prior): selected item was hardening
  the prototype definition-of-done gate so DoD condition 2 (the section 11
  acceptance suite) can no longer pass unverified. `scripts/check_definition_of_
  done.sh` `[2/6]` ran only `tests/e2e` (condition 1); condition 2 ("the section
  11 acceptance scenarios pass; the acceptance suite is green", SPEC.md section
  13) had no suite and no gate check, so once conditions 3, 5, 6 and 9 were met
  `make done` could have turned green with no section 11 acceptance suite. It is
  the same class of false stop condition the prior two cycles closed for `[3/6]`
  and `[5/6]`, and it outranks starting Q32: Q32-Q45 are downstream dashboards,
  and the task prioritizes missing gate integrity over downstream features. No
  ready method-artifact or stage-gate item remained: Q28 stage 8-10 required
  kinds are blocked on the named methodology-owner placement decision, Q29
  (method change impact) is domain-complete and tested, Q16 is blocked on a
  workflow write route, Q3/Q4 are blocked on the ADR 0006 tension and a live key,
  and Q8's remaining retrieval, worker and artifact-URL layers have no seam yet.
- Outcome: new standalone `scripts/check_acceptance_coverage.sh` enforces
  condition 2 against a data-driven contract. `tests/acceptance/covered-
  scenarios.txt` declares each of the ten canonical SPEC.md section 11 scenarios
  as `<scenario-id> <test-file>` (repo-root relative) or `<scenario-id> uncovered
  <reason>`; every canonical id must be declared exactly once, each covered file
  must exist and contain at least one test, and any scenario still `uncovered` is
  a named failure that lists every uncovered scenario with its reason. `[2/6]`
  now runs it after the e2e suite; the gate fails honestly today (four scenarios
  uncovered), so a green condition 2 requires real tests for duplicate delivery,
  cross-client retrieval, the GitOps revert and the backup restore. No product
  authority, gate decision or pipeline stage changed.
- Evidence: `make check` -> 2247 passed, 2 skipped, 704 subtests; pyflakes clean.
  New `tests/unit/shared/test_acceptance_coverage_check.py` (10 tests) covers a
  complete suite passing, a missing directory, a missing manifest, an uncovered
  scenario, an undeclared scenario, an unknown scenario, a duplicate scenario, a
  declared file that is missing, a declared file with no test, and the real suite
  failing with the four uncovered scenarios named. `make done` now fails at
  `[2/6]` with "the section 11 acceptance suite is not covered; condition 2 is
  unmet" after `[1/6]` and the condition 1 e2e pass.
- New findings: condition 2 was the third approximated DoD condition. The ten
  section 11 scenarios are declared by the suite, not hard-coded by the gate
  check, so a future cycle adds coverage without editing the gate. Four scenarios
  are genuinely uncovered: cross-client retrieval is the same missing retrieval
  seam condition 3 needs, duplicate delivery needs a connector idempotency seam
  (Q16), and the GitOps revert and backup restore are deploy-only (Q49). The
  condition cannot pass until those exist, which is correct: condition 2 is
  unmet, not merely under-tested.
- Blockers (unchanged): `frontend/` screens Q32-Q45 are the path to `make done`
  condition 6; Q8's retrieval, worker and artifact-URL isolation coverage and the
  condition 2 cross-client-retrieval scenario are blocked until the retrieval,
  worker and artifact-serving seams exist; Q28 stage 8-10 required kinds blocked
  on the named methodology-owner placement decision; Q16 idempotency keys (and
  the condition 2 duplicate-delivery scenario) blocked on a workflow write route
  and a connector seam; Q3 agent registration blocked on the ADR 0006 /
  vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q31's deploy-only scenarios (GitOps revert,
  backup restore) need the Atlas cluster and a chosen backup target.
- Highest priority ready next item: Q32, the Next.js shell in `frontend/` plus
  the RED theme and API client, now safe to start because `make done` cannot pass
  on a screens-less shell (`[5/6]`) or an API-only security suite (`[3/6]`) or a
  suite-less condition 2 (`[2/6]`). Required asset: the Next.js app shell that
  consumes the complete SPEC.md section 7 REST surface; checkpoint: none (UI, not
  a gate); approver: none. Blocked downstream dependency: Q33-Q45. The stage 0-10
  e2e Q30 is already green.

### Prior cycle (2026-10-03T195801Z)

- Cycle 2026-10-03T195801Z (Ralph cycle): selected item was hardening
  the prototype definition-of-done gate so DoD `[3/6]` can no longer pass on an
  API-only security suite. `scripts/check_definition_of_done.sh` `[3/6]` ran
  `pytest tests/security`, and the suite covers only the API layer, so condition
  3 ("a security suite covers API, retrieval, background worker and artifact
  URL", SPEC.md sections 9 and 13) was unmet while the gate passed: once the
  Q32-Q45 screens landed, `make done` could have turned green with three of the
  four named isolation layers untested. It is the same class of false stop
  condition the prior cycle closed for `[5/6]`, and it outranks starting Q32:
  Q32-Q45 are downstream dashboards, and the task prioritizes missing gate
  integrity over downstream features. No ready method-artifact or stage-gate item
  remained: Q28 stage 8-10 required kinds are blocked on the named
  methodology-owner placement decision, Q29 (method change impact) is
  domain-complete and tested, Q16 is blocked on a workflow write route, Q3/Q4 are
  blocked on the ADR 0006 tension and a live key, and the remaining Q8 layers
  (retrieval, worker, artifact URL) have no seam to test yet.
- Outcome: new standalone `scripts/check_security_coverage.sh` enforces condition
  3 against a data-driven contract. `tests/security/covered-layers.txt` declares
  each covered layer as `<layer-id> <test-file>`; every canonical layer id
  (`api`, `retrieval`, `worker`, `artifact-url`) must be declared, each declared
  file must exist under `tests/security/` and contain at least one test, and an
  unknown or duplicate layer id is refused. `[3/6]` now calls it before running
  the suite; a missing layer is a named failure that lists what is absent. The
  gate now fails honestly today (`retrieval worker artifact-url` uncovered), so a
  green `[3/6]` requires real per-layer isolation tests. No product authority,
  gate decision or pipeline stage changed.
- Evidence: `make check` -> 2237 passed, 2 skipped, 704 subtests; pyflakes clean.
  New `tests/unit/shared/test_security_coverage_check.py` (8 tests) covers a
  complete suite passing, a missing directory, a missing manifest, an uncovered
  layer, an unknown layer, a declared file that is missing, a declared file with
  no test, and the real suite failing with the three absent layers named.
  `make done` still fails, now at `[3/6]` with "the cross-tenant security suite
  does not cover all four condition 3 layers" (after `[1/6]`-`[2/6]` pass).
- New findings: `[3/6]` was the second approximated DoD condition. The four
  condition 3 layers are declared by the suite, not hard-coded by the gate check,
  so a future cycle adds retrieval, worker and artifact-URL coverage without
  editing the gate. The condition cannot pass until those seams exist, which is
  correct: condition 3 is unmet, not merely under-tested.
- Blockers (unchanged): `frontend/` screens Q32-Q45 are the path to `make done`
  condition 6; Q8's retrieval, worker and artifact-URL isolation coverage is
  blocked until those seams are built; Q28 stage 8-10 required kinds blocked on
  the named methodology-owner placement decision; Q16 idempotency keys blocked on
  a workflow write route; Q3 agent registration blocked on the ADR 0006 /
  vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q31's section 11 acceptance suite is blocked
  in part on the deploy-only scenarios (GitOps revert, backup restore).
- Highest priority ready next item: Q32, the Next.js shell in `frontend/` plus
  the RED theme and API client, now safe to start because `make done` cannot pass
  on a screens-less shell (`[5/6]`) or an API-only security suite (`[3/6]`).
  Required asset: the Next.js app shell that consumes the complete SPEC.md
  section 7 REST surface; checkpoint: none (UI, not a gate); approver: none.
  Blocked downstream dependency: Q33-Q45. The stage 0-10 e2e Q30 is already
  green.

### Prior cycle (2026-10-03T195507Z)

- Cycle 2026-10-03T195507Z (Ralph cycle): selected item was hardening
  the prototype definition-of-done gate so a screens-less `frontend/` cannot
  falsely pass condition 6. It outranks starting Q32: `scripts/check_definition_of_done.sh`
  [5/6] passed on `frontend/` merely existing with no `OpenExecutive` string, so
  the moment Q32 landed the gate would turn green and the loop would stop with
  the command center and the other eleven section 8 screens unbuilt. Several
  prior cycles declined Q32 for exactly this reason, so the loop was deadlocked
  behind a dishonest stop condition. SPEC.md section 13 condition 6 is "All
  section 8 screens render" with browser tests, not "a directory exists".
- Outcome: new standalone `scripts/check_frontend_screens.sh` enforces the
  condition against a data-driven contract. The frontend declares each
  implemented screen and its route in `frontend/dod-screens.txt`
  (`<screen-id> <route>`), every one of the twelve canonical section 8 screen
  ids must be declared, each declared route must resolve to a page
  (`frontend/src/app/<route>/page.*` or the pages-router equivalent), and at
  least one browser test spec must exist; a missing screen, page or suite is a
  named failure that lists what is absent. `[5/6]` now calls it before the
  branding scan. The gate still fails today (no `frontend/`), so no premature
  stop; it becomes honest as Q33-Q45 add the screens. No product authority, gate
  decision or pipeline stage changed.
- Evidence: `make check` -> 2229 passed, 2 skipped, 704 subtests; pyflakes clean.
  New `tests/unit/shared/test_frontend_screens_check.py` (7 tests) covers a
  complete frontend passing, a missing frontend, a missing manifest, an
  undeclared screen, a declared screen without a page, a missing browser suite,
  and a root-route page. `make done` still fails only `[5/6]`, now with
  "the section 8 screens are not rendered; condition 6 is unmet" after
  `[1/6]`-`[4/6]` pass.
- New findings: the DoD's six bundled conditions hide three very different
  states (per-cycle check, e2e, security, branding, screens, deployment); the
  screens condition was the only approximated one. The route contract is
  declared by the frontend, not hard-coded by the gate, so future cycles pick
  their own routes while the twelve SPEC.md section 8 screens stay mandatory.
- Blockers (unchanged): `frontend/` screens Q32-Q45 remain the only path to
  `make done`; Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q16 idempotency keys blocked on a
  workflow write route; Q3 agent registration blocked on the ADR 0006 /
  vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q31's section 11 acceptance suite is blocked
  in part on the deploy-only scenarios (GitOps revert, backup restore).
- Highest priority ready next item: Q32, the Next.js shell in `frontend/` plus
  the RED theme and API client, now safe to start because `make done` can no
  longer pass on a screens-less shell. Q32's own scope stays a shell plus the
  command center (Q33); the gate will keep failing until all twelve screens and
  a browser suite exist. Required asset: the Next.js app shell that consumes the
  complete SPEC.md section 7 REST surface; checkpoint: none (UI, not a gate);
  approver: none. Blocked downstream dependency: Q33-Q45. The stage 0-10 e2e Q30
  is already green.

### Prior cycle (2026-10-03T195052Z)

- Cycle 2026-10-03T195052Z (Ralph cycle, this run): selected item was the
  `/opportunities` half of Q14, the tenant-scoped Portfolio opportunity register
  (prerequisite Q13 met; `/interventions` landed last cycle). It outranks the
  `frontend/` Q32: SPEC.md section 7 lists `/opportunities`, SPEC.md sections 1
  and 3 put portfolio expansion and the Portfolio context (opportunity and
  roadmap) in the product contract, and Phase 5's TDD example pins "opportunity
  remains proposed until investment authority acts", but no Portfolio
  opportunity store or route existed. The `frontend/` Q32 shell would falsely
  pass DoD [5/6] while condition 6 (Q45) is far off.
- Outcome: new pure-domain `Opportunity` value object (tenant, id, title, typed
  `OpportunityKind`, exact same-tenant `StageAssetVersion` source, investment
  case, expected outcome, owner, next action, capture date, and an
  `OpportunityState` fixed to `PROPOSED`) with named `InvalidOpportunityError`,
  `OpportunityTenantBoundaryError`, `OpportunityAuthorityError` and
  `OpportunityConflictError`; new Portfolio application port
  `OpportunityRepository` (`get`/`list`/`save`/`close`); in-memory and PostgreSQL
  adapters, `opportunity_repository_from_env`, `OpportunityConfigurationError`
  and payload mappers; migration `0017_opportunities` (NOT NULL
  `tenant_id`/`opportunity_id` and an append-only unique key); and tenant-scoped
  routes `GET /red/opportunities` (paginated register) and `POST
  /red/opportunities` (record one proposal). The value object refuses any
  approved state, so the register holds proposals only and recording one
  authorizes no investment, spend or launch. SPEC.md section 7's REST resource
  set is now complete.
- Evidence: `make check` -> 2222 passed, 2 skipped, 704 subtests; pyflakes clean.
  New tests `tests/unit/portfolio/test_opportunity.py` (10),
  `test_opportunity_repository.py` (7) and `test_opportunities_route.py` (8),
  plus `test_opportunity_postgres.py` (4, run against the live compose
  database); `tests/unit/shared/test_migrate.py` pins head `0017_opportunities`
  and the new table. `make done` still fails only [5/6] (`frontend/` missing,
  Q32); [1/6]-[4/6] and [6/6] pass.
- New findings: canon files 11 and 12 (Perfect Product) govern the opportunity's
  shape only at the level of the Grow effect (a new entry point or a lifetime
  value offer), so the register grounds each proposal on an exact stage asset
  version, a named owner and a next action rather than inventing a canon sales
  model; the canon's Grow as a pipeline addition stays the named-owner decision
  recorded in the gap register. A same-id re-statement is a named 409 and an
  exact replay is idempotent, matching the append-only register used by the other
  Q13/Q14 stores.
- Blockers: `frontend/` (DoD condition 6, Q32) remains multi-cycle and must not
  land shell-only; Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q16 idempotency keys blocked on a
  workflow write route; Q3 agent registration blocked on the ADR 0006 /
  vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`; Q31's section 11 acceptance suite is blocked
  in part on the deploy-only scenarios (GitOps revert, backup restore) that
  need the cluster.
- Highest priority ready next item: Q32, the Next.js shell in `frontend/` plus
  the RED theme, the API client and the first real screen (command center Q33)
  with a browser test. It is gated on not landing shell-only: DoD [5/6] passes on
  `frontend/` merely existing with no `OpenExecutive` string, while condition 6
  (Q45, all section 8 screens) is far off, so a screens-less shell would falsely
  turn `make done` green and stop the loop. Required asset: the Next.js app shell
  that consumes the now-complete SPEC.md section 7 REST surface; checkpoint: none
  (UI, not a gate); approver: none. Blocked downstream dependency: Q33-Q45. The
  stage 0-10 e2e Q30 is already green.

### Prior cycle (2026-10-03T194645Z)

- Cycle 2026-10-03T194645Z (Ralph cycle, this run): selected item was the
  `/interventions` half of Q14, the tenant-scoped command center intervention
  read and durable dismissal surface over the existing Operations
  `InterventionRankingPolicy` (prerequisite Q13 met by the prior cycle). It
  outranks the `/opportunities` half of Q14 and the `frontend/` Q32: SPEC.md
  section 7 ("Command center intervention fields") fully specifies the card and
  the domain already encodes all four reasons, the field set, deduplication and
  dismissal, so this closes a real gap (SPEC.md section 7 lists `/interventions`,
  but no store and no route existed) at low design risk; `/opportunities` needs a
  new Portfolio `Opportunity` aggregate whose shape the canon only sketches (the
  Serve and Grow entry is a named-owner pipeline decision), and `frontend/` is
  the downstream dashboard whose shell-only form would falsely pass DoD [5/6]
  while condition 6 (Q45) is far off. `/interventions` is the visible command
  center's core content and the last high-value SPEC.md section 7 resource short
  of `/opportunities`.
- Outcome: new pure-domain `InterventionDismissal` value object (tenant, client,
  typed reason, subject, rationale, actor, dismissed-on) with named
  `InvalidInterventionDismissalError`; new Operations application port
  `InterventionDismissalRepository` (`list`/`save`/`close`); in-memory and
  PostgreSQL adapters, `intervention_dismissal_repository_from_env`,
  `InterventionDismissalConfigurationError`, `InterventionDismissalConflictError`
  and `InterventionDismissalTenantBoundaryError`, payload mappers; migration
  `0016_intervention_dismissals` (NOT NULL `tenant_id`/`client`/`reason`/`subject`
  and a unique card key); and tenant-scoped routes `GET /red/interventions`
  (ranked cards for a client engagement, derived from the production view) and
  `POST /red/interventions/dismiss`. The derived cards are recomputed on every
  read; only the operator decision is durable, and a stored dismissal is applied
  to the matching surfaced card (a dismissal whose card no longer surfaces is
  inert). A same-key dismissal with different content is a named 409. Recording a
  dismissal resolves no blocker and takes no production action.
- Evidence: `make check` -> 2193 passed, 2 skipped, 697 subtests; pyflakes clean.
  New tests `tests/unit/operations/test_intervention_dismissal.py` (5),
  `test_intervention_dismissal_repository.py` (6) and
  `test_intervention_dismissal_postgres.py` (4, run against the live compose
  database) and `test_interventions_route.py` (6); `tests/unit/shared/test_migrate.py`
  pins head `0016_intervention_dismissals` and the new table. `make done` still
  fails only [5/6] (`frontend/` missing, Q32); [1/6]-[4/6] and [6/6] pass.
- New findings: the intervention cards are derived from the Governance production
  view on every read, so no card table is needed; the store holds only the
  human dismissal keyed by `(tenant_id, client, reason, subject)`. The two
  signals the platform itself derives (blocked critical path, overdue approval)
  are served; failed live journeys and nearing commitments stay caller-supplied
  signals the Execution, Measurement and Engagement contexts own, so their own
  surfaces remain a documented follow-up rather than fabricated cards. A blocked
  stage with a past due date legitimately surfaces two cards (blocked and
  overdue), which the route returns as two ranked cards.
- Blockers: `frontend/` (DoD condition 6, Q32) remains multi-cycle and must not
  land shell-only; Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q16 idempotency keys blocked on a
  workflow write route; Q3 agent registration blocked on the ADR 0006 /
  vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: the `/opportunities` half of Q14, the
  tenant-scoped Portfolio opportunity surface. Required asset: a Portfolio
  `Opportunity` aggregate (the derivative/expansion opportunity SPEC.md section 3
  names) exposed through a tenant-scoped route; because its shape is canon-thin
  (canon 11, 12 Serve/Grow; SPEC.md section 12.5 records the expansion candidate
  as needing a named-owner stage decision), the smallest safe slice is a typed
  read/write aggregate inside the existing Portfolio context, not a new stage.
  Checkpoint: none (API surface, not a gate); approver: none. Blocked downstream
  dependency: Q14 completes the SPEC.md section 7 REST resource set, then the
  `frontend/` screens Q32-Q45. The stage 0-10 e2e Q30 is already green.

### Prior cycle (2026-10-03T194326Z)

- Cycle 2026-10-03T194326Z (Ralph cycle, this run): selected item was the
  `/journeys` half of Q13, the tenant-scoped journey release store and REST
  surface over the Execution `JourneyRelease` aggregate (prerequisite met by the
  prior cycle). It outranks the alternatives: no stage 0-10 gate-integrity item is
  ready (Q28 stage 8-10 required-kind placement stays a named-owner decision;
  Q3/Q16/Q4 remain blocked), and the `frontend/` Q32 is the downstream dashboard
  whose shell-only form would falsely pass DoD [5/6] while condition 6 (Q45) is
  far off. `/journeys` is the last open SPEC.md section 7 REST resource before
  `/opportunities` and `/interventions` (Q14), it closes a real persistence gap
  (SPEC.md section 3 names `JourneyRelease`, section 7 lists `/journeys`, but the
  new aggregate had no store, no migration and no route), and it makes the
  launch-integrity release legible to the command center and the stage 10 e2e.
- Outcome: new Execution application port `JourneyReleaseRepository`
  (`get`/`list`/`save`/`close`), in-memory and PostgreSQL adapters,
  `journey_release_repository_from_env`, `JourneyReleaseConfigurationError`, new
  domain errors `JourneyReleaseVersionConflictError` and
  `JourneyReleaseVersionTenantBoundaryError`, payload mappers
  (`journey_release_to_payload`/`from_payload`, which serialise the grounding QA
  through `launch_qa_to_payload`), migration `0015_journey_releases`
  (`journey_releases`, NOT NULL `tenant_id` and unique `(tenant_id, release_id)`),
  and tenant-scoped routes `GET /red/journeys` (paginated list) and
  `POST /red/journeys`. The create route resolves the named launch QA from the
  durable `LaunchQARepository` by exact id (a missing QA is a named 404) rather
  than trusting a repeated QA body, maps the released assets to exact same-tenant
  `StageAssetVersion` evidence, and lets the `JourneyRelease` aggregate enforce the
  signed-ready/authorized QA, the non-blank routing, configuration digest and
  rollback reference, and exactly one exact version per kind. The store is
  append-only: an identical replay is idempotent, a same-id re-statement with
  different content is a named 409, and a later release is a new identity.
  Recording a release authorizes no traffic and confers no human approval.
- Evidence: `make check` -> 2172 passed, 2 skipped, 692 subtests; pyflakes clean.
  New tests `tests/unit/execution/test_journey_release_repository.py` (7),
  `tests/unit/execution/test_journeys_route.py` (7) and
  `tests/unit/execution/test_journey_release_postgres.py` (4, run against the live
  compose database); `tests/unit/shared/test_migrate.py` pins head
  `0015_journey_releases` and the new table. `make done` still fails only [5/6]
  (`frontend/` missing, Q32); [1/6]-[4/6] and [6/6] pass.
- New findings: the release route mirrors the stage 9/10 gate pattern of
  resolving upstream evidence by exact identity from a durable store rather than
  re-declaring it, so `RecordJourneyReleaseRequest` carries only a `qa_id` and the
  released assets, not a full QA body. `JourneyRelease` embeds a full `LaunchQA`,
  so the release payload nests the QA payload; the mapper reuses
  `launch_qa_to_payload`/`from_payload` so the two cannot drift. A cross-tenant
  release cannot be constructed (the aggregate refuses a foreign QA or asset), so
  the cross-tenant store tests assert an empty foreign `list` rather than
  inserting a foreign row.
- Blockers: `frontend/` (DoD condition 6, Q32) remains multi-cycle and must not
  land shell-only; Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q16 idempotency keys blocked on a
  workflow write route; Q3 agent registration blocked on the ADR 0006 / vendor-edit
  tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: Q14, the tenant-scoped REST surface for
  `/opportunities` and `/interventions` (prerequisite Q13 now met). Required
  asset: an opportunity and an intervention store/aggregate exposed through
  tenant-scoped routes; checkpoint: none (API surface, not a gate); approver: none
  (no gate decides). Blocked downstream dependency: Q14 completes the SPEC.md
  section 7 REST resource set, then the `frontend/` screens Q32-Q45. The stage 0-10
  e2e Q30 is already green.

### Prior cycle (2026-10-03T194013Z)

- Cycle 2026-10-03T194013Z (Ralph cycle): selected item was the
  Execution `JourneyRelease` core aggregate (SPEC.md section 3), the spec-named
  aggregate the remaining `/journeys` half of Q13 needs. It outranks the
  alternatives: every stage 0-10 gate-integrity item is closed or blocked on a
  named-owner decision (Q28 stage 8-10 required-kind placement, Q3 vendor agent
  registration, Q16 workflow write route), and the `frontend/` Q32 is a
  downstream dashboard whose shell-only form would falsely pass DoD [5/6] while
  condition 6 (Q45) is far off. `JourneyRelease` was absent from the codebase
  (grep confirmed), it is launch-integrity (invariant "launch needs signed
  readiness and authorized release"), it is a SPEC.md section 3 core aggregate,
  and it is the prerequisite for `/journeys` (Q13) and then `/opportunities`,
  `/interventions` (Q14). It does not require the JourneyRelease-vs-stage-8
  `FunnelIntegration` owner decision the prior status named: the SPEC names
  `JourneyRelease` and the canon is silent on it, so the SPEC governs the shape
  (SPEC.md section 12.1); projecting the existing `FunnelIntegration` instead
  remains available to the owner as an intentional deviation and is not
  foreclosed.
- Outcome: new pure-domain `JourneyRelease` (`release_id`, `tenant_id`, `qa`,
  `assets`, `routing`, `configuration_digest`, `rollback_ref`) in
  `backend/redops/contexts/execution/domain/journey_release.py`, with named
  `JourneyReleaseError` / `InvalidJourneyReleaseError` /
  `JourneyReleaseDependencyError` / `JourneyReleaseReadinessError` /
  `JourneyReleaseAuthorityError` / `JourneyReleaseTenantBoundaryError`. It
  refuses to exist without a same-tenant ready-for-traffic `LaunchQA` carrying a
  `TrafficAuthorization` by that QA's designated authority (both halves of the
  section 3 invariant), and it refuses a blank routing, configuration digest or
  rollback reference and a released package that is not exactly one exact
  `StageAssetVersion` per kind. It exposes `released_kinds`, `is_signed_ready`
  and `is_authorized`; it is frozen so a later release is a new identity and a
  previous deployed release stays historically identifiable. It authorizes no
  traffic (a stage 10 observation) and confers no human approval.
- Evidence: `make check` -> 2151 passed, 2 skipped, 690 subtests; pyflakes
  clean. New `tests/unit/execution/test_journey_release.py` (12 tests, 4
  subtests). `make done` still fails only [5/6] (`frontend/` missing, Q32);
  [1/6]-[4/6] and [6/6] pass.
- New findings: the stage 9 `LaunchQA` already carries the signed human
  `TrafficAuthorization` when it reaches `READY_FOR_TRAFFIC`, so "signed
  readiness and authorized release" maps onto the existing stage 9 evidence
  rather than a second authority path; the release re-verifies the authorizer
  against the QA's designated authority rather than trusting the
  `LaunchApprovedPolicy` that ran when the QA was authorized, so a directly
  constructed ready QA cannot smuggle a rogue authorizer into a release.
- Blockers: `frontend/` (DoD condition 6, Q32) remains multi-cycle and must not
  land shell-only; Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q16 idempotency keys blocked on a
  workflow write route; Q3 agent registration blocked on the ADR 0006 /
  vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: the Q13 `/journeys` route and durable store
  over this `JourneyRelease` (prerequisite met this cycle). Required asset: a
  tenant-scoped `JourneyReleaseRepository` (in-memory and PostgreSQL adapters,
  migration) plus `GET`/`POST /red/journeys`. Checkpoint: none (API surface, not
  a gate); approver: none (no gate decides). Blocked downstream dependency: Q14
  `/opportunities`, `/interventions`; then the `frontend/` screens Q32-Q45. The
  stage 0-10 e2e Q30 is already green.

### Prior cycle (2026-10-03T193641Z)

- Cycle 2026-10-03T193641Z (Ralph cycle): selected item was the
  `/measurements` half of Q13, the tenant-scoped stage 10 metric registry
  (prerequisite Q12 met). It outranks the `/journeys` half because it closes a
  real persistence gap: SPEC.md section 3 names the Measurement aggregate
  ("metric definition, window, baseline, observation, source") and SPEC.md
  section 7 lists `/measurements`, but `MetricDefinition` and `MeasurementRecord`
  were pure values with no tenant-scoped store, no migration and no route, so DoD
  condition 4 ("RED aggregates ... persist in PostgreSQL") was false for the
  measurement registry and the production view's METRICS dimension had no durable
  source to read. The `frontend/` shell Q32 was again rejected: the DoD [5/6]
  script passes on `frontend/` merely existing with no `OpenExecutive` string, so
  a screens-less shell would falsely turn `make done` green while condition 6
  (Q45) is far off.
- Outcome: new Measurement application port `MeasurementRegistry`
  (`list_metrics`/`get_metric`/`list_records`/`get_record`/`save_metric`/
  `save_record`), in-memory and PostgreSQL adapters,
  `measurement_registry_from_env`, `MeasurementConfigurationError`,
  `UnscopedMeasurementError` and `MeasurementConflictError`, payload mappers,
  migration `0014_measurements` (`metric_definitions`, `measurement_records`,
  both NOT NULL `tenant_id`), and tenant-scoped routes `GET /red/measurements`
  (paginated list of observations) and `POST /red/measurements` (register one
  exact metric version and record its observation). Both writes are append-only:
  an identical replay is idempotent and a same-key re-statement is a named 409.
  Recording an observation is not a gate and grants no authority; a material
  optimization still needs the owner approval of SPEC.md section 4.
- Evidence: `make check` -> 2139 passed, 2 skipped, 686 subtests; pyflakes clean.
  New tests `tests/unit/measurement/test_measurement_registry.py` (24) and
  `tests/unit/measurement/test_measurements_route.py` (9);
  `tests/unit/shared/test_migrate.py` pins head `0014_measurements` and the two
  tables, and the new PostgreSQL adapter tests ran against the live database.
  `make done` still fails only [5/6] (`frontend/` missing, Q32); [1/6]-[4/6] pass.
- New findings: the Measurement domain already refuses a blank tenant at
  construction, so the store's unscoped read/write guard is defense-in-depth; the
  metric registry had no store at all, so the cycle 106 METRICS projection was
  only caller-supplied. `MetricDefinition` is keyed by
  `(tenant_id, metric_id, version)` and a stored definition is append-only, so a
  redefinition is a new version and an observation pins the exact metric identity.
  SPEC.md section 3 also names `JourneyRelease` (assets, routing, configuration
  digest, rollback ref), which is not implemented; `/journeys` needs either that
  aggregate or a named decision to expose the stage 8 `FunnelIntegration` instead.
- Blockers: `frontend/` (DoD condition 6, Q32) remains multi-cycle and must not
  land shell-only; Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q16 idempotency keys blocked on a
  workflow write route; Q3 agent registration blocked on the ADR 0006 / vendor-edit
  tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: the `/journeys` half of Q13 (prereq Q12 done).
  Required asset: the journey release exposed through a tenant-scoped route. The
  design question that gates it is whether to build the SPEC.md section 3
  `JourneyRelease` aggregate or map `/journeys` onto the durable stage 8
  `FunnelIntegration`; that is a named-owner decision, so the bounded next action
  is to resolve it and expose the chosen store. Checkpoint: none (API surface, not
  a gate); approver: none (no gate decides). Blocked downstream dependency: Q14
  from Q13; then the `frontend/` screens Q32-Q45. The stage 0-10 e2e Q30 is
  already green.

### Prior cycle (2026-10-03T193430Z)

- Cycle 2026-10-03T193430Z (Ralph cycle): selected item was Q12, the
  tenant-scoped REST surface for `/approvals` and `/decisions` (prerequisite Q11
  met). No gate-integrity item is ready: Q17-Q27 closed the caller-supplied
  authority defect across every stage 0-10 gate and Q29's method change impact is
  domain-complete, while Q28 stays blocked on the named methodology-owner
  placement decision. Q12 outranks the Q13-Q14 chain because it is the next
  product-backbone REST resource of SPEC.md section 7 and it makes the
  append-only governance decision log and its exact-version approvals legible,
  which the approval inbox (Q39) and the stage 0-10 e2e (Q30) read. The
  `frontend/` shell Q32 was again rejected: the DoD [5/6] script passes on
  `frontend/` merely existing with no `OpenExecutive` string, so a screens-less
  shell would falsely turn `make done` green while condition 6 (Q45) is far off.
- Outcome: new tenant-scoped read routes `GET /red/decisions` and
  `GET /red/approvals` in `backend/redops/api/routes.py`, projected from the
  durable `GateLedgerRepository`. `/decisions` lists the append-only gate
  decisions in canonical stage order, each with disposition, reviewer, intended
  scope, rationale, exact pinned asset versions and next action; `/approvals`
  flattens the per-asset `ApprovalRequest`s those decisions recorded, surfacing
  the exact asset version and scope, requester, designated approver, outcome and
  expiry. Both are read-only over the existing ledger: a decision is recorded
  through its stage gate and a direct write would let a caller confer the
  approval governance owns (SPEC.md section 4), and listing an approval never
  authorizes production or traffic.
- Evidence: `make check` -> 2111 passed, 2 skipped, 686 subtests; pyflakes
  clean. New tests `tests/unit/governance/test_governance_read_routes.py` (6):
  the decision is listed for its tenant with exact versions; another tenant sees
  nothing; the approvals list carries exact version, scope, approver and outcome;
  approvals are tenant scoped; the tenant parameter is required on both routes
  (422); pagination applies after scoping. `make done` still fails only [5/6]
  (`frontend/` missing, Q32); [1/6]-[4/6] pass.
- New findings: the durable governance decision record already exists as the
  stage `GateDecision`, which seals its per-asset approvals, so Q12 needed no new
  store and no migration; `/decisions` and `/approvals` are read projections, not
  a second authority path. `ApprovalRequest` still carries no `tenant_id` of its
  own because it is stored inside its decision and inherits the decision's
  tenant; the tenant-scoped ledger is the enforcement seam. There is no
  standalone pending-approval write path: gates issue and decide approvals during
  recording, so `/approvals` reads decided approvals until a lighter-approval
  policy (SPEC.md section 4) specifies a pending queue.
- Blockers: `frontend/` (DoD condition 6, Q32) remains multi-cycle and must not
  land shell-only; Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q16 idempotency keys blocked on a
  workflow write route; Q3 agent registration blocked on the ADR 0006 /
  vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: Q13, REST `/journeys` and `/measurements`
  (prereq Q12 done). Required asset: the journey release and measurement records
  exposed through tenant-scoped routes; checkpoint: none (API surface, not a
  gate); approver: none (no gate decides). Blocked downstream dependency: Q14
  from it; then the stage 0-10 e2e Q30 and the `frontend/` screens Q32-Q45.

### Prior cycle (2026-10-03T193035Z)

- Cycle 2026-10-03T193035Z (Ralph cycle): selected item was Q11, the
  tenant-scoped REST surface for `/offers` and `/builds` (prerequisite Q10 met).
  Q17-Q27 closed the caller-supplied-authority defect across every stage 0-10
  gate, so no gate-integrity item is ready (Q28 is blocked on the named
  methodology-owner placement decision). Q11 outranks the remaining alternatives
  because it is the next product-backbone step of SPEC.md section 7 and it closed
  a real persistence gap: SPEC.md section 3 names `BuildObject` as a required
  aggregate and the ClientWorkspace invariant makes every child resource belong to
  exactly one client, but the Production `BuildObject` had no `tenant_id`, no
  store and no migration, so Q6's "every named aggregate is durable" claim was
  false for builds. The `frontend/` shell Q32 was again rejected: the DoD [5/6]
  script passes on `frontend/` merely existing with no `OpenExecutive` string, so
  a screens-less shell would falsely turn `make done` green while condition 6
  (Q45) is far off.
- Outcome: `BuildObject` now carries a required `tenant_id` (SPEC.md sections 3
  and 9). New Production `BuildObjectRepository` port with `get`/`list`/`save`,
  `build_to_payload`/`build_from_payload` mapper preserving the append-only
  transition history, in-memory and PostgreSQL adapters, `BuildConfigurationError`
  and `BuildTenantBoundaryError`, and migration `0013_build_objects` (upsert per
  `(tenant_id, build_id)` because a build is a live aggregate). New routes
  `GET /red/offers` and `GET`/`POST /red/builds`: offers are a tenant-scoped,
  paginated read over the existing offer store, deliberately read-only because an
  offer becomes production ready through the stage 5 "Offer Locked" gate and a
  direct write would let a caller confer readiness governance owns (SPEC.md
  sections 3 and 4); builds are a tenant-scoped paginated list plus a create that
  records an Identified proposal, not a gate.
- Evidence: `make check` -> 2105 passed, 2 skipped, 686 subtests; pyflakes clean.
  New tests `tests/unit/production/test_build_object_store.py`,
  `tests/unit/production/test_builds_route.py`,
  `tests/unit/production/test_build_object_postgres.py` and
  `tests/unit/commercial/test_offers_route.py`; `tests/unit/production/test_build_object.py`
  now covers the blank-tenant refusal; `tests/unit/shared/test_migrate.py` pins
  head `0013_build_objects` and the `build_objects` table. `make done` still fails
  only [5/6] (`frontend/` missing, Q32); [1/6]-[4/6] pass.
- New findings: `BuildObject` had no tenant, so it could not be a tenant-scoped
  child resource of a `ClientWorkspace`; its store's write guard is now
  defense-in-depth because the aggregate refuses a blank tenant at construction.
  `/offers` exposes no write path, so the offer surface cannot be used to bypass
  the stage 5 gate.
- Blockers: `frontend/` (DoD condition 6, Q32) remains multi-cycle and must not
  land shell-only; Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q16 idempotency keys blocked on a
  workflow write route; Q3 agent registration blocked on the ADR 0006 /
  vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: Q12, REST `/approvals` and `/decisions`
  (prereq Q11 done). Required asset: the governance approval queue and decision
  log exposed through tenant-scoped routes with exact version approval; stage 8-10
  gate / "exact version approval"; checkpoint: none (API surface, not a gate);
  approver: none (no gate decides). Blocked downstream dependency: Q13-Q14 chain
  from it; then the stage 0-10 e2e Q30 and the `frontend/` screens Q32-Q45.

### Prior cycle (2026-10-03T192641Z)

- Cycle 2026-10-03T192641Z (Ralph cycle, this run): selected item was Q10, the
  tenant-scoped REST surface for `/claims` and `/methods` (prerequisite Q9 met).
  Q17-Q27 closed the caller-supplied-authority defect across every stage 0-10
  gate, so no gate-integrity item is ready (Q28 is blocked on the named
  methodology-owner placement decision). Q10 outranks the remaining alternatives
  because it is the next product-backbone step of SPEC.md section 7 and feeds the
  stage 0-10 e2e (Q30) and the section 8 screens (Q32-Q45); it is more than a
  surface, because before this cycle the Section 3 invariant "a Known claim must
  cite a direct source" had no durable store and no route that verified a
  citation against the immutable original a claim points at. The `frontend/`
  shell Q32 was again rejected: the DoD [5/6] script passes on `frontend/`
  merely existing with no `OpenExecutive` string, so a screens-less shell would
  falsely turn `make done` green while condition 6 (Q45) is far off. Q29 is
  domain-complete, Q16 is blocked on a workflow write route and Q3/Q4 are
  blocked on the ADR 0006 tension and a live key, so Q10 is the ready item.
- Outcome: new Knowledge `ClaimStore` port, `claim_to_payload`/`claim_from_payload`
  mapper, in-memory and PostgreSQL adapters, `claim_store_from_env` and migration
  `0012_claims`. The claim store is append-only per `(tenant_id, claim_id)`: a
  claim's statement is immutable, a provenance change must append a recorded
  `ClaimRevision`, and a same-id content change that recorded no revision is
  refused. New routes `GET`/`POST /red/claims` and `GET /red/methods`. The
  `/claims` create route resolves every citation against the same tenant's
  `SourceRecordStore` and refuses an unknown source id or a checksum that does
  not match the stored original, so a Known claim cannot be asserted against a
  fabricated citation (SPEC.md sections 3 and 11). `/methods` is a tenant-scoped,
  paginated read over the approved-method store (`MethodVersionRepository.list`
  added to the port and both adapters); it is deliberately read-only, because a
  method is born approved through its stage gate and a direct write would let a
  caller confer the approval governance owns (SPEC.md section 4).
- Evidence: `make check` -> 2082 passed, 2 skipped, 686 subtests; pyflakes
  clean. New tests `tests/unit/knowledge/test_claim_store.py` (in-memory, mapper
  and PostgreSQL cases), `tests/unit/knowledge/test_claims_route.py` and
  `tests/unit/method/test_methods_route.py`; `tests/unit/shared/test_migrate.py`
  now pins head `0012_claims` and the `claims` table. `make done` still fails
  only [5/6] (`frontend/` missing, Q32); [1/6]-[4/6] pass.
- New findings: `Claim` excludes its `_revisions` tuple from dataclass equality,
  so a store guard based on `==` cannot detect a dropped revision history; the
  claim store therefore compares content with revisions stripped plus a
  revision-prefix check. `/claims` now verifies citations against the durable
  source store, closing the fabricated-citation path that the domain alone cannot
  check (a `SourceCitation` carries no tenant). `/methods` exposes no write path
  by design.
- Blockers: `frontend/` (DoD condition 6, Q32) remains multi-cycle and must not
  land shell-only; Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q16 idempotency keys blocked on a
  workflow write route; Q3 agent registration blocked on the ADR 0006 /
  vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: Q11, REST `/offers` and `/builds` (prereq
  Q10 done). Required asset: the offer and build records exposed through
  tenant-scoped routes reusing the existing durable offer store and the
  Production `BuildObject`; checkpoint: none (API surface, not a gate);
  approver: none (no gate decides). Blocked downstream dependency: Q12-Q14 chain
  from it; then the stage 0-10 e2e Q30 and the `frontend/` screens Q32-Q45.

### Prior cycle (2026-10-03T192509Z)

- Cycle 2026-10-03T192509Z (Ralph cycle, this run): selected item was Q27
  hardening, the stage 10 "Performance Baseline Established" gate route hardened
  against the caller-supplied-authority defect (prerequisite Q26 met). Q17-Q26
  closed the defect on stages 0-9, but the stage 10 route still rebuilt
  `ClientWorkspace` from `body.authorities`, so a caller could name itself the
  client designated approver and the final gate -- the one that pins the live
  campaign, spend, lead, conversion, engagement, booking, close, acquisition-cost,
  attribution and issue-log assets against a reviewed baseline -- would approve
  against a transient registry rather than the persisted tenant root (SPEC.md
  sections 3, 4 and 11). Stage 10 is the last gate in the pipeline, so closing it
  means every gate 0-10 resolves its tenant root and authority registry from
  durable stores. Chosen over the ready Q10-Q14 REST surface and the `frontend/`
  shell Q32 because caller-supplied gate authority outranks surface breadth, and
  the Q32 shell was again rejected: the DoD [5/6] script passes on `frontend/`
  merely existing with no `OpenExecutive` string, so a screens-less shell would
  falsely turn `make done` green while condition 6 (Q45) is far off. Q28 stays
  blocked on the named methodology-owner placement decision.
- Outcome: `RecordStageTenGateRequest` drops `authorities`.
  `record_stage_ten_gate` now depends on `get_client_workspace_store`, resolves
  the workspace by `(tenant_id, body.workspace_id)` through the
  `ClientWorkspaceStore` port, and approves against the persisted registry; an
  unregistered workspace is a named 404 `ClientWorkspaceNotFoundError`, not a
  gate built from caller-supplied authorities.
  `tests/unit/test_stage_ten_gate_route.py` drops the `authorities` key from its
  payload and adds two behavioral tests: an unregistered workspace is a 404 with
  no ledger write, and the identical request is a 422
  `GateApproverNotAuthorizedError` when the persisted registry omits the client
  authority. The stage 10 payload now carries no authority list anywhere.
- Evidence: `make check` -> 2050 passed, 2 skipped, 684 subtests; pyflakes
  clean. `make done` still fails only [5/6] (`frontend/` missing, Q32);
  [1/6]-[4/6] pass.
- New findings: no stage 0-10 gate route rebuilds `ClientWorkspace` from
  `body.authorities` anymore; the caller-supplied-authority defect is closed
  across the whole 0-10 pipeline. The remaining gate-integrity work is Q28's
  canon required-kind placements (`audience-reach-estimate`, `target-market-match`
  and stages 2-10 kinds), blocked on the named methodology-owner placement
  decision, so no gate-integrity item is ready.
- Blockers: `frontend/` (DoD condition 6, Q32) remains multi-cycle and must not
  land shell-only; Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q16 idempotency keys blocked on a
  workflow write route; Q3 agent registration blocked on the ADR 0006 /
  vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: Q10, REST `/claims` and `/methods` (prereq
  Q9 done). Required asset: the knowledge claim and approved method records
  exposed read-and-write through tenant-scoped routes; checkpoint: none (API
  surface, not a gate); approver: none (no gate decides). Blocked downstream
  dependency: Q11-Q14 chain from it; then the `frontend/` screens Q32-Q45.

### Prior cycle (2026-10-03T192319Z)

- Cycle 2026-10-03T192319Z: selected item was Q26
  hardening, the stage 9 "Launch Approved" gate route hardened against the
  caller-supplied-authority defect (prerequisite Q25 met). Q17-Q25 closed the
  defect on stages 0-8, but the stage 9 route still rebuilt `ClientWorkspace`
  from `body.authorities`, so a caller could name itself the client designated
  approver and the gate that carries the launch QA and reviewed compliance
  package and authorizes traffic would approve against a transient registry
  rather than the persisted tenant root (SPEC.md sections 3, 4 and 11). Stage 9
  is the next dependent gate after the now-hardened stage 8, so closing it keeps
  gate integrity ahead of the remaining stage (Q27), the REST surface (Q10-Q14)
  and UI (Q32-Q45). The `frontend/` shell Q32 was again rejected: the DoD [5/6]
  script passes on `frontend/` merely existing with no `OpenExecutive` string, so
  a screens-less shell would falsely turn `make done` green while condition 6
  (Q45) is far off. Q28 stays blocked on the named methodology-owner placement
  decision.
- Outcome: `RecordStageNineGateRequest` drops `authorities`.
  `record_stage_nine_gate` now depends on `get_client_workspace_store`, resolves
  the workspace by `(tenant_id, body.workspace_id)` through the
  `ClientWorkspaceStore` port, and approves against the persisted registry; an
  unregistered workspace is a named 404 `ClientWorkspaceNotFoundError`, not a
  gate built from caller-supplied authorities.
  `tests/unit/test_stage_nine_gate_route.py` drops the `authorities` key from its
  payload and adds two behavioral tests: an unregistered workspace is a 404 with
  no ledger write, and the identical request is a 422
  `GateApproverNotAuthorizedError` when the persisted registry omits the client
  authority. Because the stage 10 schema still requires `authorities` (Q27 not
  yet done), `tests/unit/test_stage_ten_gate_route.py` now inlines its own
  authority list instead of borrowing `nine["authorities"]`.
- Evidence: `make check` -> 2048 passed, 2 skipped, 684 subtests; pyflakes
  clean. `make done` still fails only [5/6] (`frontend/` missing, Q32);
  [1/6]-[4/6] pass.
- New findings: with Q17-Q26 done, stages 0-9 resolve their tenant root and
  authority registry from durable stores, but the stage 10 gate route still
  builds `ClientWorkspace` from `body.authorities` (for example
  `record_stage_ten_gate` at `backend/redops/api/routes.py`), so the
  caller-supplied-authority defect remains on one route. The stage 10 test's
  inlined authority list can be dropped once Q27 hardens that route.
- Blockers: `frontend/` (DoD condition 6, Q32) remains multi-cycle and must not
  land shell-only; Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q16 idempotency keys blocked on a
  workflow write route; Q3 agent registration blocked on the ADR 0006 /
  vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: Q27 hardening, extend the Q17-Q26 hardening
  to the stage 10 "Performance Baseline Established" gate (resolve the persisted
  `ClientWorkspace` and its authority registry, 404 when unregistered, drop
  `authorities` from `RecordStageTenGateRequest`, the stage 10 route and the
  stage 10 test's inline authority list). Prerequisite: Q26 (done this cycle).
  Required asset: the stage 10 live campaign measurement package with the
  distinct observed-or-pending milestones; checkpoint: Performance Baseline
  Established; designated approver: the client designated authority in the
  persisted registry. Blocked downstream dependency: none further in the
  pipeline; then Q10-Q14 (remaining REST resources) and the `frontend/` screens
  Q32-Q45.

### Prior cycle (2026-10-03T192102Z)

- Cycle 2026-10-03T192102Z: selected item was Q25
  hardening, the stage 8 "Funnel Complete" gate route hardened against the
  caller-supplied-authority defect (prerequisite Q24 met). Q17-Q24 closed the
  defect on stages 0-7, but the stage 8 route still rebuilt `ClientWorkspace`
  from `body.authorities`, so a caller could name itself the client designated
  approver and the gate that carries the funnel integration package and its
  test-prospect dry run would approve against a transient registry rather than
  the persisted tenant root (SPEC.md sections 3, 4 and 11). Stage 8 is the next
  dependent gate after the now-hardened stage 7, so closing it keeps gate
  integrity ahead of the remaining stages (Q26-Q27), the REST surface
  (Q10-Q14) and UI (Q32-Q45).
- Outcome: `RecordStageEightGateRequest` drops `authorities`.
  `record_stage_eight_gate` now depends on `get_client_workspace_store`,
  resolves the workspace by `(tenant_id, body.workspace_id)` through the
  `ClientWorkspaceStore` port, and approves against the persisted registry; an
  unregistered workspace is a named 404 `ClientWorkspaceNotFoundError`, not a
  gate built from caller-supplied authorities.
  `tests/unit/test_stage_eight_gate_route.py` drops the `authorities` key from
  its payload and adds two behavioral tests: an unregistered workspace is a 404
  with no ledger write, and the identical request is a 422
  `GateApproverNotAuthorizedError` when the persisted registry omits the client
  authority. Because the stage 9-10 schemas still require `authorities`
  (Q26-Q27 not yet done), `tests/unit/test_stage_nine_gate_route.py` now inlines
  its own authority list; the stage 10 payload that borrows
  `nine["authorities"]` inherits it unchanged.
- Evidence: `make check` -> 2046 passed, 2 skipped, 684 subtests; pyflakes
  clean. `make done` still fails only [5/6] (`frontend/` missing, Q32);
  [1/6]-[4/6] pass.
- New findings: with Q17-Q25 done, stages 0-8 resolve their tenant root and
  authority registry from durable stores, but stages 9-10 gate routes still
  build `ClientWorkspace` from `body.authorities` (for example
  `record_stage_nine_gate` at `backend/redops/api/routes.py`), so the
  caller-supplied-authority defect remains on two routes. The stage 9 test's
  inlined authority list can be dropped once Q26 hardens that route, and the
  stage 10 payload that borrows `nine["authorities"]` must be updated in the
  same step.
- Blockers: `frontend/` (DoD condition 6, Q32) remains multi-cycle and must not
  land shell-only; Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q16 idempotency keys blocked on a
  workflow write route; Q3 agent registration blocked on the ADR 0006 /
  vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: Q26 hardening, extend the Q17-Q25 hardening
  to the stage 9 "Launch Approved" gate (resolve the persisted `ClientWorkspace`
  and its authority registry, 404 when unregistered, drop `authorities` from
  `RecordStageNineGateRequest`, the stage 9 route and the stage 9 test's inline
  authority list). Prerequisite: Q25 (done this cycle). Required asset: the
  stage 9 launch QA package with all critical path checks and the designated
  human authorization; checkpoint: Launch Approved; designated approver: the
  client designated authority in the persisted registry. Blocked downstream
  dependency: the stage 10 "Performance Baseline Established" gate. Then Q27
  hardening, Q10-Q14 (remaining REST resources) and the `frontend/` screens
  Q32-Q45.

### Prior cycle (2026-10-03T191920Z)

- Cycle 2026-10-03T191920Z: selected item was Q24 hardening, the stage 7
  "Authority Amplifier Approved" gate route hardened against the
  caller-supplied-authority defect. `RecordStageSevenGateRequest` dropped
  `authorities`; the route resolved the workspace from the durable
  `ClientWorkspaceStore`, returning a named 404 when unregistered and a 422
  domain error otherwise. Q25 was recorded as the next ready item.

### Earlier cycle (2026-10-03T191741Z)

- Cycle 2026-10-03T191741Z (Ralph cycle, this run): selected item was Q23
  hardening, the stage 6 "Campaign Message Approved" / "Content Plan Locked"
  gate route hardened against the caller-supplied-authority defect
  (prerequisite Q22 met). It outranked the alternatives for these reasons.
  Q17-Q22 closed the caller-supplied-authority defect on stages 0-5, but the
  stage 6 route still rebuilt `ClientWorkspace` from `body.authorities`, so a
  caller could name itself the client designated approver and the first gate
  that carries the approved message, content roadmap, content crusher and
  content plan would approve against a transient registry rather than the
  persisted tenant root (SPEC.md sections 3, 4 and 11). Stage 6 is the next
  dependent gate after the now-hardened stage 5, so closing it keeps gate
  integrity ahead of the remaining stages (Q24-Q27), the REST surface
  (Q10-Q14) and UI (Q32-Q45). The `frontend/` shell Q32 was again rejected:
  the DoD [5/6] script passes on `frontend/` merely existing with no
  `OpenExecutive` string, so a screens-less shell would falsely turn
  `make done` green while condition 6 (Q45) is far off. Q28 stays blocked on
  the named methodology-owner placement decision.
- Outcome: `RecordStageSixGateRequest` drops `authorities`. `record_stage_six_gate`
  now depends on `get_client_workspace_store`, resolves the workspace by
  `(tenant_id, body.workspace_id)` through the `ClientWorkspaceStore` port, and
  approves against the persisted registry; an unregistered workspace is a named
  404 `ClientWorkspaceNotFoundError`, not a gate built from caller-supplied
  authorities. `tests/unit/test_stage_six_gate_route.py` drops the `authorities`
  key from its payload and its `_authorities` helper, and adds two behavioral
  tests: an unregistered workspace is a 404 with no ledger write, and the
  identical request is a 422 `GateApproverNotAuthorizedError` when the persisted
  registry omits the client authority. `tests/unit/test_stage_seven_gate_route.py`
  no longer borrows `_authorities` for its own stage 7 payload (stage 7 is not
  yet hardened, so its schema still requires the field); the authorities are
  inlined there. The stage 7-10 payloads that chain through `six.payload()`
  inherit the dropped key unchanged because pydantic ignores the extra field.
- Evidence: `make check` -> 2042 passed, 2 skipped, 684 subtests; pyflakes
  clean. `make done` still fails only [5/6] (`frontend/` missing, Q32);
  [1/6]-[4/6] pass.
- New findings: with Q17-Q23 done, stages 0-6 resolve their tenant root and
  authority registry from durable stores, but stages 7-10 gate routes still
  build `ClientWorkspace` from `body.authorities` (for example
  `record_stage_seven_gate` at `backend/redops/api/routes.py`), so the
  caller-supplied-authority defect remains on four routes. The stage 7-10 route
  tests and their chained payload builders still carry `authorities` for their
  own un-hardened schemas; each must be hardened alongside its asset assembly,
  and the stage 7 test's inline authorities can then be dropped.
- Blockers: `frontend/` (DoD condition 6, Q32) remains multi-cycle and must not
  land shell-only; Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q16 idempotency keys blocked on a
  workflow write route; Q3 agent registration blocked on the ADR 0006 /
  vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: Q24 hardening, extend the Q17-Q23 hardening
  to the stage 7 "Authority Amplifier Approved" gate (resolve the persisted
  `ClientWorkspace` and its authority registry, 404 when unregistered, drop
  `authorities` from `RecordStageSevenGateRequest` and the stage 7 route test's
  inline authorities). Prerequisite: Q23 (done this cycle). Required asset: the
  stage 7 `AuthorityAmplifierPackage` plus the wired claims and the dual
  script/creative approvals; checkpoint: Authority Amplifier Approved;
  designated approver: the client designated authority in the persisted
  registry. Blocked downstream dependency: the stage 8 "Funnel Complete" gate.
  Then Q25-Q27 hardening for the remaining stages and Q10-Q14 (remaining REST
  resources) and the `frontend/` screens Q32-Q45.

### Prior cycle (2026-10-03T191558Z)

- Cycle 2026-10-03T191558Z (Ralph cycle): selected item was Q22 hardening, the
  stage 5 "Offer Locked" gate route hardened against the
  caller-supplied-authority defect. Q17-Q21 closed the defect on stages 0-4, but
  the stage 5 route still rebuilt `ClientWorkspace` from `body.authorities`, so a
  caller could name itself the client designated approver and the first gate that
  carries the priced product program would approve against a transient registry
  rather than the persisted tenant root (SPEC.md sections 3, 4 and 11). Outcome:
  `RecordStageFiveGateRequest` dropped `authorities`; `record_stage_five_gate`
  resolved the workspace from the `ClientWorkspaceStore` and added a named 404
  for an unregistered workspace, with two behavioral tests. Evidence: `make
  check` -> 2040 passed, 2 skipped, 684 subtests; `make done` failed only [5/6].

### Prior cycle (2026-10-03T191400Z)

- Cycle 2026-10-03T191400Z (Ralph cycle, this run): selected item was Q21, the
  stage 4 "IP Architecture Locked" gate route hardened against the
  caller-supplied-authority defect (prerequisite Q20 met). It outranked the
  alternatives for these reasons. Q17-Q20 closed the caller-supplied-authority
  defect on stages 0-3, but the stage 4 route still rebuilt `ClientWorkspace`
  from `body.authorities`, so a caller could name itself the client designated
  approver and the first gate that carries the reviewed transformation would
  approve against a transient registry rather than the persisted tenant root
  (SPEC.md sections 3, 4 and 11). Stage 4 is the next dependent gate after the
  now-hardened stage 3, so closing it keeps gate integrity ahead of the remaining
  REST surface (Q10-Q14) and UI (Q32-Q45). The `frontend/` shell Q32 was again
  rejected: the DoD [5/6] script passes on `frontend/` merely existing with no
  `OpenExecutive` string, so a screens-less shell would falsely turn `make done`
  green while condition 6 (Q45) is far off. Q28 stays blocked on the named
  methodology-owner placement decision.
- Outcome: `RecordStageFourGateRequest` drops `authorities`.
  `record_stage_four_gate` now depends on `get_client_workspace_store`,
  resolves the workspace by `(tenant_id, body.workspace_id)` through the
  `ClientWorkspaceStore` port, and approves against the persisted registry; an
  unregistered workspace is a named 404 `ClientWorkspaceNotFoundError`, not a
  gate built from caller-supplied authorities.
  `tests/unit/test_stage_four_gate_route.py` drops the `authorities` key from
  its stage 1, stage 2, stage 3 and stage 4 payloads and its `_authorities`
  helper, and adds two behavioral tests: an unregistered workspace is a 404 with
  no ledger write, and the identical request is a 422
  `GateApproverNotAuthorizedError` when the persisted registry omits the client
  authority. The reused stage 4 payload in `tests/unit/test_stage_six_gate_route.py`
  (which the e2e chains back through) also drops the field; the stage 5 and
  stage 6 payloads keep their `authorities` key because those schemas are not yet
  hardened (Q22-Q23).
- Evidence: `make check` -> 2038 passed, 2 skipped, 684 subtests; pyflakes
  clean. `make done` still fails only [5/6] (`frontend/` missing, Q32);
  [1/6]-[4/6] pass.
- New findings: with Q17-Q21 done, stages 0-4 resolve their tenant root and
  authority registry from durable stores, but stages 5-10 gate routes still build
  `ClientWorkspace` from `body.authorities` (for example `record_stage_five_gate`
  at `backend/redops/api/routes.py`), so the caller-supplied-authority defect
  remains on six routes. The fix is the identical pattern and each stage should
  get it alongside its asset assembly. Pydantic ignores the now-unused
  `authorities` key in the stage 5-10 route test payloads, so those tests pass
  unchanged, but the field is dead and should be removed as each route is
  hardened.
- Blockers: `frontend/` (DoD condition 6, Q32) remains multi-cycle and must not
  land shell-only; Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q16 idempotency keys blocked on a
  workflow write route; Q3 agent registration blocked on the ADR 0006 /
  vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: Q22 hardening, extend the Q17-Q21 hardening
  to the stage 5 "Offer Locked" gate (resolve the persisted `ClientWorkspace`
  and its authority registry, 404 when unregistered, drop `authorities` from
  `RecordStageFiveGateRequest` and the stage 5 route test payload). Prerequisite:
  Q21 (done this cycle). Required asset: the stage 5 `OfferPackage` plus the
  wired `thirteen-transformations` kind; checkpoint: Offer Locked; designated
  approver: the client designated authority in the persisted registry. Blocked
  downstream dependency: the stage 6 "Message Locked" / "Content Plan Locked"
  gate. Then Q23-Q27 hardening for the remaining stages and Q10-Q14 (remaining
  REST resources) and the `frontend/` screens Q32-Q45.

### Prior cycle (2026-10-03T191236Z)

- Cycle 2026-10-03T191236Z (Ralph cycle, this run): selected item was Q20, the
  stage 3 "Diagnostic Model Approved" gate route hardened against the
  caller-supplied-authority defect (prerequisite Q19 met). It outranked the
  alternatives for these reasons. Q17-Q19 closed the caller-supplied-authority
  defect on stages 0-2, but the stage 3 route still rebuilt `ClientWorkspace`
  from `body.authorities`, so a caller could name itself the client designated
  approver and the first gate whose checkpoint turns on the model's own
  observable structure would approve against a transient registry rather than
  the persisted tenant root (SPEC.md sections 3, 4 and 11). Stage 3 is the next
  dependent gate after the now-hardened stage 2, so closing it keeps gate
  integrity ahead of the remaining REST surface (Q10-Q14) and UI (Q32-Q45). The
  `frontend/` shell Q32 was again rejected: the DoD [5/6] script passes on
  `frontend/` merely existing with no `OpenExecutive` string, so a screens-less
  shell would falsely turn `make done` green while condition 6 (Q45) is far off.
  Q28 stays blocked on the named methodology-owner placement decision.
- Outcome: `RecordStageThreeGateRequest` drops `authorities`.
  `record_stage_three_gate` now depends on `get_client_workspace_store`,
  resolves the workspace by `(tenant_id, body.workspace_id)` through the
  `ClientWorkspaceStore` port, and approves against the persisted registry; an
  unregistered workspace is a named 404 `ClientWorkspaceNotFoundError`, not a
  gate built from caller-supplied authorities.
  `tests/unit/test_stage_three_gate_route.py` drops the `authorities` key from
  its stage 1, stage 2 and stage 3 payloads and its `_authorities` helper, and
  adds two behavioral tests: an unregistered workspace is a 404 with no ledger
  write, and the identical request is a 422 `GateApproverNotAuthorizedError`
  when the persisted registry omits the client authority. The reused stage 3
  payload in `tests/unit/test_stage_six_gate_route.py` (which the e2e chains back
  through) also drops the field.
- Evidence: `make check` -> 2036 passed, 2 skipped, 684 subtests; pyflakes
  clean. `make done` still fails only [5/6] (`frontend/` missing, Q32);
  [1/6]-[4/6] pass.
- New findings: with Q17-Q20 done, stages 0-3 resolve their tenant root and
  authority registry from durable stores, but stages 4-10 gate routes still build
  `ClientWorkspace` from `body.authorities` (for example `record_stage_four_gate`
  at `backend/redops/api/routes.py`), so the caller-supplied-authority defect
  remains on seven routes. The fix is the identical pattern and each stage should
  get it alongside its asset assembly. Pydantic ignores the now-unused
  `authorities` key in the stage 4-10 route test payloads, so those tests pass
  unchanged, but the field is dead and should be removed as each route is
  hardened.
- Blockers: `frontend/` (DoD condition 6, Q32) remains multi-cycle and must not
  land shell-only; Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q16 idempotency keys blocked on a
  workflow write route; Q3 agent registration blocked on the ADR 0006 /
  vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: Q21 hardening, extend the Q17-Q20 hardening
  to the stage 4 "IP Architecture Locked" gate (resolve the persisted
  `ClientWorkspace` and its authority registry, 404 when unregistered, drop
  `authorities` from `RecordStageFourGateRequest` and the stage 4 route test
  payload). Prerequisite: Q20 (done this cycle). Required asset: the stage 4
  `IPArchitecturePackage` plus the wired `thirteen-transformations` kind;
  checkpoint: IP Architecture Locked; designated approver: the client designated
  authority in the persisted registry. Blocked downstream dependency: the stage 5
  "Offer Locked" gate. Then Q22-Q27 hardening for the remaining stages and
  Q10-Q14 (remaining REST resources) and the `frontend/` screens Q32-Q45.

### Prior cycle (2026-10-03T191057Z)

- Cycle 2026-10-03T191057Z (Ralph cycle, this run): selected item was Q19,
  extend the Q17/Q18 persisted-workspace/authority hardening to the stage 2
  "Currency Locked" gate (prerequisites Q8 and Q18 met). It outranked the
  alternatives for these reasons. Q17 and Q18 closed the
  caller-supplied-authority defect on stages 0 and 1, but the stage 2 route still
  rebuilt `ClientWorkspace` from `body.authorities`, so a caller could name itself
  the client designated approver and the first gate with a currency checkpoint
  would approve against a transient registry rather than the persisted tenant
  root (SPEC.md sections 3, 4 and 11). Stage 2 is the next dependent gate, so
  closing it keeps gate integrity ahead of the remaining REST surface (Q10-Q14)
  and UI (Q32-Q45). The `frontend/` shell Q32 was again rejected: the DoD [5/6]
  script passes on `frontend/` merely existing with no `OpenExecutive` string, so
  a screens-less shell would falsely turn `make done` green while condition 6
  (Q45) is far off. Q28 stays blocked on the named methodology-owner placement
  decision.
- Outcome: `RecordStageTwoGateRequest` drops `authorities`.
  `record_stage_two_gate` now depends on `get_client_workspace_store`, resolves
  the workspace by `(tenant_id, body.workspace_id)` through the
  `ClientWorkspaceStore` port, and approves against the persisted registry; an
  unregistered workspace is a named 404 `ClientWorkspaceNotFoundError`, not a
  gate built from caller-supplied authorities.
  `tests/unit/test_stage_two_gate_route.py` drops the `authorities` key from its
  stage 1 and stage 2 payloads and its `_authorities` helper, and adds two
  behavioral tests: an unregistered workspace is a 404 with no ledger write, and
  the identical request is a 422 `GateApproverNotAuthorizedError` when the
  persisted registry omits the client authority. The reused stage 2 payload in
  `tests/unit/test_stage_six_gate_route.py` (which the e2e chains back through)
  also drops the field.
- Evidence: `make check` -> 2034 passed, 2 skipped, 684 subtests; pyflakes
  clean. `make done` still fails only [5/6] (`frontend/` missing, Q32);
  [1/6]-[4/6] pass.
- New findings: with Q17-Q19 done, stages 0-2 resolve their tenant root and
  authority registry from durable stores, but stages 3-10 gate routes still build
  `ClientWorkspace` from `body.authorities` (for example `record_stage_three_gate`
  at `backend/redops/api/routes.py`), so the caller-supplied-authority defect
  remains on seven routes. The fix is the identical pattern and each stage should
  get it alongside its asset assembly. Pydantic ignores the now-unused
  `authorities` key in the stage 3-10 route test payloads, so those tests pass
  unchanged, but the field is dead and should be removed as each route is
  hardened.
- Blockers: `frontend/` (DoD condition 6, Q32) remains multi-cycle and must not
  land shell-only; Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q16 idempotency keys blocked on a
  workflow write route; Q3 agent registration blocked on the ADR 0006 /
  vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: Q20 hardening, extend the Q17/Q18/Q19
  hardening to the stage 3 "Diagnostic Model Approved" gate (resolve the
  persisted `ClientWorkspace` and its authority registry, 404 when unregistered,
  drop `authorities` from `RecordStageThreeGateRequest` and the stage 3 route
  test payload). Prerequisite: Q19 (done this cycle). Required asset: the stage 3
  `ProfitPyramidPackage`; checkpoint: Diagnostic Model Approved; designated
  approver: the client designated authority in the persisted registry. Blocked
  downstream dependency: the stage 4 "IP Architecture Locked" gate. Then Q21-Q27
  hardening for the remaining stages and Q10-Q14 (remaining REST resources) and
  the `frontend/` screens Q32-Q45.

### Prior cycle (2026-10-03T190410Z)

- Cycle 2026-10-03T190410Z (Ralph cycle, this run): selected item was Q17, the
  stage 0 intake route hardened plus the workspace and authority registry
  (dependency Q9 met). It outranked the alternatives for these reasons. The stage
  0-10 pipeline is the product backbone and its gates exist, but every gate
  rebuilt its `ClientWorkspace` -- and so its authority registry -- from the
  request body, so a caller could name itself the designated approver and the
  "Production Ready" gate approved against a transient registry rather than the
  persisted tenant root (SPEC.md sections 3, 4 and 11). Q17 closes that on stage
  0, the gate every later stage depends on. Q10-Q14 REST resources rank below:
  they are API surface, not gate integrity. `frontend/` (Q32) was again
  rejected: the DoD [5/6] script passes on `frontend/` merely existing with no
  `OpenExecutive` string, so a screens-less shell would falsely satisfy
  `make done` while condition 6 (Q45) is far off. Q28 stays blocked on the named
  methodology-owner placement decision.
- Outcome: `RecordStageZeroGateRequest` drops `authorities` (the body no longer
  carries a registry). `record_stage_zero_gate` now depends on
  `get_client_workspace_store`, resolves the workspace by
  `(tenant_id, body.workspace_id)` through the `ClientWorkspaceStore` port, and
  approves against the persisted registry; an unregistered workspace is a named
  404 `ClientWorkspaceNotFoundError` (new Engagement domain error), never a gate
  built from caller-supplied authorities. `get_client_workspace_store` and
  `get_source_record_store` were moved beside the other request dependencies so
  the earlier stage route can bind the store at definition time. No new endpoint
  was added: the `/clients` workspace and authority write surface already landed
  with Q9.
- Evidence: `make check` -> 2030 passed, 2 skipped, 684 subtests; pyflakes
  clean. `tests/unit/test_stage_zero_gate_route.py` registers the workspace
  through the real `POST /red/clients` and adds two tests: an unregistered
  workspace is a 404 with no write, and the identical request is a 422
  `GateApproverNotAuthorizedError` when the persisted registry omits the client
  authority. A new `tests/unit/workspace_fixture.py` registers the tenant
  workspace for the stage 0-10 route tests; the cross-tenant security suite
  registers the other client's workspace so its approver test stays an authority
  refusal rather than a missing-workspace 404. `make done` still fails only
  [5/6] (`frontend/` missing, Q32); [1/6]-[4/6] pass.
- New findings: the stage 1-10 gate routes still build their `ClientWorkspace`
  and authority registry from the request body (for example
  `record_stage_one_gate`), so the caller-supplied-authority defect Q17 fixed on
  stage 0 remains on stages 1-10. The fix is the identical pattern -- resolve the
  store, 404 when unregistered, drop `authorities` from the request -- and each
  stage should get it alongside its asset assembly. With Q9 and Q17 both done,
  the stage 0 tenant root and its authority registry now resolve from durable
  stores.
- Blockers: `frontend/` (DoD condition 6, Q32) remains multi-cycle and must not
  land shell-only; Q28 stage 8-10 required kinds blocked on the named
  methodology-owner placement decision; Q16 idempotency keys blocked on a
  workflow write route; Q3 agent registration blocked on the ADR 0006 /
  vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: Q18, extend the Q17 hardening to the stage 1
  "Avatar Locked" gate (resolve the persisted `ClientWorkspace` and its
  authority registry, 404 when unregistered, drop `authorities` from
  `RecordStageOneGateRequest`) and assemble the stage 1 diagnosis gate from the
  built assets. Prerequisite: Q17 (done this cycle). Required asset: the stage 1
  `DiagnosisPackage`; checkpoint: Avatar Locked; designated approver: the client
  designated authority in the stage 0 registry. Blocked downstream dependency:
  the stage 2 "Currency Locked" gate. Then Q10-Q14 (remaining REST resources)
  and the `frontend/` screens Q32-Q45.

### Prior cycle (2026-10-03T190017Z)

- Cycle 2026-10-03T190017Z (Ralph cycle, this run): selected item was Q9, the
  REST `/clients` and `/clients/{id}/sources` surface (dependencies Q6/Q7 met).
  It outranked the alternatives for these reasons. The stage 0-10 pipeline is
  the product backbone and its API gates already exist for every stage, but the
  stage 0 client workspace and the immutable source records claims cite had no
  persistence and no read/write surface, so the pipeline's tenant root was
  re-synthesised from a request body on every call instead of resolved from a
  durable store (SPEC.md sections 3, 4 and 7). Q9 is the last ready backend
  surface before the UI and is the prerequisite for Q17 (stage 0 route hardened
  to resolve the stored workspace and authority registry rather than trust a
  repeated body) and Q10-Q14. The `frontend/` shell Q32 was rejected this cycle:
  the DoD gate script `[5/6]` passes on the mere existence of `frontend/` plus
  the absence of the string `OpenExecutive`, so landing only a shell with no
  section 8 screens would prematurely turn `make done` green and stop the loop
  while condition 6 (all screens render, Q45) is still far off. Q28 stage 8-10
  required kinds stay blocked on the named methodology-owner placement decision,
  and the workflow start/approve write route still needs a definition registry
  and a `WorkflowStepExecutor` adapter (Q16).
- Outcome: new `ClientWorkspaceStore` port
  (`backend/redops/contexts/engagement/application/ports.py`) with
  `InMemoryClientWorkspaceStore` and `PostgresClientWorkspaceStore` plus
  `client_workspace_store_from_env` and a payload mapper in
  `contexts/engagement/infrastructure/`, and new `SourceRecordStore` port with
  the same adapter pair in `contexts/knowledge/infrastructure/`. Migrations
  `0010_client_workspaces` and `0011_source_records` create
  `client_workspaces(tenant_id NOT NULL, workspace_id, workspace JSONB,
  UNIQUE(tenant_id, workspace_id))` and
  `source_records(tenant_id NOT NULL, source_id, source JSONB,
  UNIQUE(tenant_id, source_id))`. `backend/redops/api/routes.py` adds
  `GET /red/clients?tenant_id=&limit=&offset=` (tenant required as a query
  parameter, never an optional filter, so no portfolio-wide read), `POST
  /red/clients` (workspace tenant from the body, since it is being created),
  `GET /red/clients/{tenant_id}/sources` and `POST
  /red/clients/{tenant_id}/sources` (path tenant authoritative). The store
  refuses an unscoped read or write (`UnscopedClientWorkspaceError`,
  `UnscopedSourceRecordError`) and a rewritten original
  (`SourceRecordImmutableError`, served as 409); a stored row is re-validated
  through the aggregate on load.
- Evidence: `make check` -> 2028 passed, 2 skipped, 684 subtests; pyflakes
  clean. New `tests/unit/engagement/test_client_workspace_store.py` (in-memory
  plus PostgreSQL: round-trip, lifecycle/transition reload, paused resume,
  stored copy independent of later caller mutation, tenant scoping, unscoped
  refusal, mapper re-validation), `tests/unit/knowledge/test_source_record_store.py`
  (immutability, ordering, tenant scoping, unscoped refusal) and
  `tests/unit/engagement/test_clients_route.py` (8 route tests: create/list,
  tenant scoping, required tenant param, blank-authority 422, source create/list,
  path-tenant scoping, rewrite 409, pagination). `tests/unit/shared/test_migrate.py`
  now asserts both new tables and alembic head `0011_source_records`. `make done`
  still fails only [5/6] (`frontend/` missing, Q32); [1/6]-[4/6] pass.
- New findings: the stage 0-10 gate routes still build `ClientWorkspace` from the
  request body (for example `record_stage_zero_gate`), so the authority registry
  a gate approves against is caller-supplied rather than the persisted workspace;
  Q17 is now unblocked and is the next gate-integrity step. The system has no
  aggregate now lacking a durable store among the stage 0-10 assets.
- Blockers: `frontend/` (DoD condition 6, Q32) remains multi-cycle and must not
  be started as a shell only, or it would falsely satisfy `make done` [5/6]; Q28
  stage 8-10 required kinds blocked on the named methodology-owner placement
  decision; Q16 idempotency keys blocked on a workflow write route; Q3 agent
  registration blocked on the ADR 0006 / vendor-edit tension; Q4 live smoke needs
  `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: Q17, harden the stage 0 intake route to
  resolve the persisted `ClientWorkspace` and its authority registry through the
  new `ClientWorkspaceStore` instead of trusting the request body, so the
  "Production Ready" gate approves against the real client authorities and owner
  registry (SPEC.md sections 3, 4 and 11). Then Q10-Q14 (remaining REST
  resources) and the `frontend/` screens Q32-Q45. Required owner input for the
  pipeline: the stage 8/9/10 canon placement decision; approver for any wired
  kind: the client designated authority; blocked downstream dependency: the
  stage 9 gate.

### Prior cycle (2026-10-03T185701Z)

- Cycle 2026-10-03T185701Z (Ralph cycle): selected item was Q15, the
  REST `/workflows/{id}` polling read — `GET
  /red/clients/{tenant_id}/workflows/{run_id}` — the workflow engine's entry
  point and the named prerequisite for Q32 (`frontend/`, the only failing DoD
  checkpoint, condition 6; SPEC.md sections 7 and 11). It outranked the
  alternatives for these reasons. The prior cycle's named next item, a fork
  `resumer.py` adapter behind the `WorkflowStepExecutor` port, was re-examined
  and rejected as mis-specified: `vendor/openexecutive/packages/core/openexecutive/workflows/resumer.py`
  is an 809-line background polling loop bound to the fork's SQLite rows,
  `WaitForHumanResolution` and artifact delivery, not a per-step executor;
  adapting it to RED's port would either edit the vendor (violating DoD
  condition 7) or fabricate a mapping, so RED's `WorkflowStepExecutor` seam is
  better served by connector adapters (Q16). Q9-Q14 REST resource routes rank
  below because they need new ClientWorkspace/SourceRecord persistence and the
  durable workflow store was unwired, so the read route was the smaller real
  unblocker of the only failing DoD condition. Q24 stage 7 dual approval is
  already enforced (`_approve_authority_amplifier` drives approve_script ->
  produce_visuals -> approve_creative, domain-order, in `routes.py`), so it is
  not open work. Q28 stages 8-10 stay blocked on the named methodology-owner
  placement decision.
- Outcome: `backend/redops/api/routes.py` adds `get_workflow_run_store` (the
  configured durable seam, chosen once from `DATABASE_URL` through
  `workflow_run_store_from_env`, closed per request) and `GET
  /red/clients/{tenant_id}/workflows/{run_id}`. The route is the polling read
  SPEC.md section 7 allows: it resolves the run through the tenant-scoped
  `WorkflowRunStore` port and returns 404 `WorkflowRunNotFoundError` for a
  missing or foreign run, so a foreign run is indistinguishable from an absent
  one (SPEC.md section 9). It projects only the durable aggregate — pinned
  definition id/version (SPEC.md section 10), status, completed steps,
  in-progress step, pending approval, failure reason, next step, an append-only
  stable `event_id` (`{run_id}:{transition_count}`) and the transition log with
  per-event stable ids, actor, reason, timestamp, old/new status and correlation
  id (SPEC.md section 4). `WorkflowRunStore` gains a default no-op `close()`.
- Evidence: `make check` -> 1994 passed, 2 skipped, 680 subtests; pyflakes
  clean. New `tests/unit/workflows/test_workflow_run_route.py` (4 tests) drives
  the real FastAPI app against a fresh in-memory store: a running run reports
  its pinned definition id/version and stable event id; a waiting approval is
  preserved across the store round-trip with a stable event id; a run is 404 for
  another tenant; an unknown run is 404. `make done` still fails only [5/6]
  (`frontend/` missing, Q32); [1/6]-[4/6] pass.
- New findings: the `workflows/infrastructure` mapper round-trip preserves the
  append-only transition log, so the stable event id survives a reload (SPEC.md
  section 11). The workflow engine is still constructed by no production entry
  point except this read route; a start/approve write route needs a definition
  registry and a `WorkflowStepExecutor` adapter (Q16), so the frontend "workflow
  run detail" screen can render a run but nothing in the running platform starts
  one yet.
- Blockers: `frontend/` (DoD condition 6, Q32) now has its workflow read route
  but still needs every section 8 screen, so it stays multi-cycle; Q16
  idempotency keys blocked on a workflow write route; Q28 stage 8-10 required
  kinds blocked on the named methodology-owner placement decision; Q9-Q14 need
  ClientWorkspace/SourceRecord persistence; Q3 agent registration blocked on the
  ADR 0006 / vendor-edit tension; Q4 live smoke needs `OPENROUTER_API_KEY` and
  `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: Q9 REST `/clients` and `/clients/{id}/sources`
  (dependency Q7 met) to begin the API surface the section 8 screens consume,
  then Q10-Q14, then the `frontend/` shell Q32 (DoD condition 6); alternatively
  the workflow start/approve write route once a definition registry and
  `WorkflowStepExecutor` adapter exist. Required owner input for the pipeline:
  the stage 8/9/10 canon placement decision; approver for any wired kind: the
  client designated authority; blocked downstream dependency: the stage 9 gate.

### Prior cycle (2026-10-03T185523Z)

- Cycle 2026-10-03T185523Z (Ralph cycle, this run): selected item was the next
  Q5 workflow-engine slice, the durable PostgreSQL `WorkflowRunStore` adapter
  plus migration (SPEC.md sections 7 and 11; ADR 0003; ADR 0005; implementation
  plan Q5). It is the plan's named highest-priority ready item and the smallest
  dependency-satisfied slice that makes durable run state real across a process
  restart. It outranked the alternatives for these reasons. The prior cycle left
  the pure workflow contract with only an in-memory reference store, so SPEC.md
  section 11's "restarting worker preserves a waiting workflow" held only inside
  one process; the adapter is the bounded change that makes it hold across a
  real restart and is the prerequisite for the fork `resumer.py` adapter and the
  REST `/workflows/{id}` route (Q15) that eventually unblocks Q32
  (`frontend/`, the only failing DoD checkpoint, condition 6). The stage 8-10
  canon required-kind wiring (Q28) is still blocked on the named
  methodology-owner placement decision (`EnrollmentPlan`, `ClientProcess`,
  `SwimlanesPlan`), and the task forbids making that decision unattended. The
  Next.js `frontend/` shell (Q32) remains blocked on the workflow route and is
  far larger than one cycle, so building only its proxy would misrepresent
  completion. Q9-Q14 REST resource routes are ready but are API surface, not the
  last DoD blocker, so they rank below the store. No smaller gate-integrity
  defect with satisfied prerequisites remained.
- Outcome: new package `backend/redops/workflows/infrastructure/`. `mappers.py`
  serialises a `WorkflowRun` to a JSONB payload (pinned `WorkflowDefinition`
  with step names/kinds, status, completed steps, in-progress step, pending
  approval, failure reason and the full transition log) and rebuilds it through
  `WorkflowRun.__post_init__`, then `restore_history`, so a reload re-validates
  through the aggregate without replaying the state machine (SPEC.md section 4;
  the pinned version keeps an in-flight run on its start definition, SPEC.md
  section 10). `repositories.py` adds the `InMemoryWorkflowRunStore` reference
  adapter (round-trips through the mapper so it copies like a real adapter),
  `PostgresWorkflowRunStore`, and `workflow_run_store_from_env` (durable when
  `DATABASE_URL` is set, in-memory when blank, `WorkflowRunConfigurationError`
  when set without psycopg). Reads are tenant scoped by the WHERE clause and a
  NOT NULL `tenant_id`, so a foreign run is indistinguishable from a missing one
  (SPEC.md section 9). New domain error `CrossTenantWorkflowRunError` refuses an
  unscoped read or write. Migration `0009_workflow_runs` (down_revision
  `0008_launch_qas`) creates `workflow_runs(tenant_id NOT NULL, run_id, status,
  definition_id, definition_version, run JSONB, recorded_at, UNIQUE(tenant_id,
  run_id))`.
- Evidence: `make check` -> 1990 passed, 2 skipped, 680 subtests; pyflakes
  clean. New adapter contract tests
  `tests/unit/workflows/test_workflow_run_store.py` (14 tests: 9 in-memory, 5
  PostgreSQL) prove a waiting run keeps its pending approval and pinned
  definition version across a reload, an interrupted `in_progress_step` is
  persisted for `resume_step`, a resave upserts without losing the append-only
  transition log, a stored run is independent of later caller mutation, a run is
  not read back for another tenant, an unscoped save/get raises the named error,
  the env factory picks the right adapter, and a stored row the aggregate would
  reject raises on load. `tests/unit/shared/test_migrate.py` now asserts the
  `workflow_runs` table and alembic head `0009_workflow_runs`; the PostgreSQL
  subset ran against the compose database (17 passed including the migration
  runner). `make done` still fails only [5/6] (`frontend/` missing, Q32).
- New findings: durable run state is now real, so the remaining Q5 slices are the
  fork `vendor/openexecutive/packages/core/openexecutive/workflows/resumer.py`
  adapter behind the `WorkflowStepExecutor` port (zero vendor edits, DoD
  condition 7) and the REST `/workflows/{id}` route. The store is not yet wired
  into any entry point (no API route or worker constructs it); `from_env` is the
  seam an entry point will call. `WorkflowStepExecutor` remains the idempotency
  seam connector steps and outbox dedup (Q16) plug into. The unresolved Q3
  architecture tension remains (ADR 0006 registers RED agents through the fork's
  `orchestrator/router.py` while DoD condition 7 requires zero vendor edits);
  that is a named-owner/architecture decision.
- Blockers: the Q28 stage 8/9/10 required-kind placement decision (named-owner);
  `frontend/` (DoD condition 6, Q32) blocked on Q15; request idempotency (Q16)
  blocked on the same; RLS is a WHERE clause only (ADR 0004); the condition 3
  retrieval, background worker and artifact-URL layers are unbuilt; Q3 agent
  registration blocked on the ADR 0006 versus vendor-edit tension; Q4's live call
  needs an `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: the next Q5 slice, the fork
  `workflows/resumer.py` adapter behind the `WorkflowStepExecutor` port
  (dependency-satisfied now that the durable store lands; proves zero vendor
  edits for DoD condition 7), then the REST `/workflows/{id}` route (Q15) and the
  `frontend/` shell (Q32, DoD condition 6). Required owner input for the
  pipeline: the stage 8/9/10 canon placement decision; approver for any wired
  kind: the client designated authority; blocked downstream dependency: the
  stage 9 gate.

### Prior cycle (2026-10-03T184653Z)

- Cycle 2026-10-03T184653Z (Ralph cycle, this run): selected item was the
  smallest independently verifiable slice of queue Q5, the workflow engine: the
  pure durable run-state contract plus the resume use case, proven by a
  restart/idempotency test (SPEC.md sections 6 and 7; SPEC.md section 11
  "restarting worker preserves a waiting workflow"; ADR 0005; implementation
  plan Q5). Q5 is the plan's highest priority ready item and the only remaining
  implementable gap on the last failing DoD checkpoint: it is a prerequisite for
  Q15 (`/workflows/{id}`) -> Q32 (`frontend/`, DoD condition 6). It outranked the
  alternatives for these reasons. The stage 8-10 canon required-kind wiring
  (Q28) is still blocked on the named methodology-owner placement decision
  (`EnrollmentPlan`, `ClientProcess`, `SwimlanesPlan` between the stage 8
  "Funnel Complete" gate and a later stage 9/10 gate), and the task forbids
  making that decision unattended. The Next.js `frontend/` shell (DoD condition
  6, Q32) would make `make done`'s [5/6] pass, but its substance (all section 8
  screens, DoD condition 6) is far larger than a shell, so building one only to
  clear the proxy gate would misrepresent completion; Q32 remains blocked on the
  workflow route Q15 per the plan. Q29 (method change impact emission) is
  domain-complete and tested (`MethodChangeImpactPolicy` / `ImpactAssessment`),
  so it is not an open defect. No smaller gate-integrity defect with satisfied
  prerequisites remained.
- Outcome: new bounded module `backend/redops/workflows/`. Pure domain
  (`WorkflowDefinition`, `WorkflowStep`, `WorkflowStepKind`, `WorkflowRunStatus`,
  `WorkflowRunTransition`, the `WorkflowRun` entity, `WorkflowTransitionPolicy`
  and named errors) plus application (`WorkflowRunStore` and
  `WorkflowStepExecutor` ports and `RunWorkflowHandler`). A run pins the exact
  definition version it started on (SPEC.md section 10), advances one step at a
  time, persists state before a side effect (`begin_step` sets
  `in_progress_step`), commits only the in-progress step, and records
  actor/reason/old and new status/correlation on each status change.
  `RunWorkflowHandler` is the only place that orders persistence and effects: it
  saves before executing, re-runs only an interrupted step idempotently on
  resume, leaves a `wait_for_human` approval in `AWAITING_APPROVAL`, and scopes
  every run read by tenant. Onion rule respected: domain imports no web, ORM,
  queue or vendor code; the use case depends on ports.
- Evidence: `make check` -> 1976 passed, 2 skipped, 680 subtests; pyflakes
  clean. New behavioral tests `tests/unit/workflows/test_workflow_resume.py`
  (17 tests): start persists before effects and waits at approval; a second
  handler over the same durable store preserves the waiting run and re-runs no
  committed step; approval resumes from committed steps without repeating
  effects; a crash mid-step leaves `in_progress_step` persisted and resume
  re-runs only that step; duplicate resume is a no-op; resume is tenant scoped;
  a failed run is terminal; plus definition/transition/order domain rules.
  `make done` clears [1/6]-[4/6] and still fails [5/6] (`frontend/` missing,
  Q32).
- New findings: the RED workflow contract is now testable without the fork or
  PostgreSQL, so the next Q5 slices are the PostgreSQL `WorkflowRunStore` adapter
  plus migration, the fork `workflows/resumer.py` adapter behind the same port
  (DoD condition 7: zero vendor edits), and the REST `/workflows/{id}` route
  (Q15). `WorkflowStepExecutor` is the seam that must be idempotent, so connector
  steps and outbox dedup (Q16) plug in there. The unresolved Q3 architecture
  tension remains: ADR 0006 registers RED agents through the fork's
  `orchestrator/router.py` while DoD condition 7 requires zero vendor edits; that
  is a named-owner/architecture decision.
- Blockers: the Q28 stage 8/9/10 required-kind placement decision (named-owner);
  `frontend/` (DoD condition 6, Q32) blocked on Q15; request idempotency (Q16)
  blocked on the same; RLS is a WHERE clause only (ADR 0004); the condition 3
  retrieval, background worker and artifact-URL layers are unbuilt; Q3 agent
  registration blocked on the ADR 0006 versus vendor-edit tension; Q4's live call
  needs an `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: the next Q5 slice, the PostgreSQL
  `WorkflowRunStore` adapter plus migration (durable run state in PostgreSQL, so
  a real process restart resumes), then the REST `/workflows/{id}` route (Q15)
  once the store lands; Q15 unblocks Q16 and Q32. The adapter is the smaller,
  dependency-satisfied item and unblocks the SPEC.md section 11 restart
  scenario. Required owner input for the pipeline: the stage 8/9/10 canon
  placement decision; approver for any wired kind: the client designated
  authority; blocked downstream dependency: the stage 9 gate.

### Prior cycle (2026-10-03T184450Z)

- Cycle 2026-10-03T184450Z (Ralph cycle, this run): selected item was queue Q4,
  the env-gated live OpenRouter smoke test (SPEC.md sections 6 and 13 condition
  5; implementation plan Q4). Q4 is the highest ready item whose prerequisites
  are met: Q2 landed the live `ForkProviderModelGateway` adapter in the prior
  cycle, so the seam exists and the smoke is the queue's next
  dependency-satisfied item. It outranked the alternatives for these reasons.
  The stage 8-10 canon required-kind wiring (Q28) is still blocked on the named
  methodology-owner placement decision (`EnrollmentPlan`, `ClientProcess`,
  `SwimlanesPlan` between the stage 8 "Funnel Complete" gate and a later stage
  9/10 gate), and the task forbids making that decision unattended. The Next.js
  `frontend/` shell (DoD condition 6, Q32) is blocked on the workflow engine Q5
  via Q15, and Q5 is a multi-cycle adaptation of the fork's workflow/resumer
  substrate, so it is not the smallest completable item. The pipeline backbone
  is complete through stage 10 at the gate routes, so there was no smaller
  gate-integrity defect with satisfied prerequisites. Q4 closes the last
  section 13 condition 5 gap that is implementable without a credential: before
  this cycle the real provider path had an adapter but no test that exercised it
  end to end. Alternatives rejected: another canon asset outside the stage order
  (post-stage-10 assets do not block the pipeline) and the REST resource routes
  Q9-Q14 (ready but surface, not DoD blocking).
- Outcome: new env-gated test
  `tests/unit/agents/test_live_openrouter_smoke.py`. It skips unless
  `OPENROUTER_API_KEY` is set and `REDOP_LIVE_OPENROUTER_SMOKE` is truthy, then
  drives one live call through `ForkProviderModelGateway.from_fork_registry()`
  (max_tokens=16, model overridable by `REDOP_SMOKE_MODEL`, default
  `claude-haiku-4-5`) wrapped by `LoggingModelGateway`, and asserts the section
  6 attribution survives the live path: non-empty text, the request's model,
  prompt version, trace id and context references, non-negative usage, and a
  `redops.agents.model` INFO record carrying the trace id, model and tenant and
  never the prompt or response text. `setUp`/`tearDown` set and restore
  `OPENROUTER_ENABLED`/`EXEC_EMAIL_ADDRESS` and reset the fork registry
  singleton so the smoke never leaks provider or env state. The explicit opt-in
  is a deliberate safety deviation from the plan's "skipped without a key"
  wording: a live call spends money, and gating only on the key would turn every
  `make check` into a paid call for a developer with a key in their shell.
- Evidence: `make check` -> 1959 passed, 2 skipped (the smoke is the second
  skip), 680 subtests; pyflakes clean. The gate is an AND, proven by three runs:
  opt-in only (no key) skips, key only (no opt-in) skips, and both set with an
  unreachable `OPENROUTER_BASE_URL` runs the live chain and fails on
  `httpx.ConnectTimeout` instead of skipping, so the test body really reaches
  the provider seam. `make done` clears [1/6]-[4/6] and still fails [5/6]
  (`frontend/` missing, Q32).
- New findings: section 13 condition 5 now has the offline fake (Q1), the live
  adapter and attribution log (Q2), and the live smoke (Q4); the only piece that
  cannot be completed here is executing the smoke, which needs a real
  `OPENROUTER_API_KEY`. The fork's `get_settings()` constructs `Settings()` on
  every call (not cached) and requires `EXEC_EMAIL_ADDRESS`, so the smoke sets
  it in `setUp`; `OPENROUTER_ENABLED=true` is required for routing and is set
  per test, not globally. The unresolved Q3 architecture tension remains: ADR
  0006 registers RED agents through the fork's `orchestrator/router.py` while
  DoD condition 7 requires zero vendor edits; that is a named-owner/architecture
  decision, not a Q4 blocker.
- Blockers: the Q28 stage 8/9/10 required-kind placement decision (named-owner);
  `frontend/` (DoD condition 6, Q32) blocked on Q5 via Q15; request idempotency
  (Q16) blocked on the same; RLS is a WHERE clause only (ADR 0004); the
  condition 3 retrieval, background worker and artifact-URL layers are unbuilt;
  Q3 agent registration blocked on the ADR 0006 versus vendor-edit tension; Q4's
  live call needs an `OPENROUTER_API_KEY` and `REDOP_LIVE_OPENROUTER_SMOKE=1`.
- Highest priority ready next item: the Q5 workflow engine slice (versioned
  definition, durable run state, approval wait survives a restart, idempotent
  effects), the single most useful unblocker for the last failing DoD
  checkpoint; it unblocks Q15 -> Q32 and the SPEC.md section 11 "restarting
  worker preserves a waiting workflow" acceptance scenario. It is larger than
  one bounded item, so the next cycle should take its smallest independently
  verifiable slice (durable run state persisted before side effects with a
  resume test). Required owner input for the pipeline: the stage 8/9/10 canon
  placement decision; approver for any wired kind: the client designated
  authority; blocked downstream dependency: the stage 9 gate.

### Prior cycle (2026-10-03T184310Z)

- Cycle 2026-10-03T184310Z (Ralph cycle, this run): selected item was queue Q2,
  the live RED LLM adapter that satisfies the `ModelGateway` port, wraps the
  fork's provider registry, and logs model, prompt version, context references,
  usage and trace id (SPEC.md sections 5, 6 and 13 condition 5; implementation
  plan Q2). Q2 is the highest ready item whose prerequisites are met: Q1 (the
  deterministic fake gateway and the `ModelGateway` port) landed in the prior
  cycle, so the port exists and the live adapter is the next dependency-satisfied
  queue item. It outranked the alternatives for these reasons. The stage 8-10
  canon required-kind wiring (Q28) is still blocked on the named
  methodology-owner placement decision the prior cycles recorded (`EnrollmentPlan`,
  `ClientProcess`, `SwimlanesPlan` between the stage 8 "Funnel Complete" gate and
  a later stage 9/10 gate), and the task forbids making that decision unattended.
  The Next.js `frontend/` shell (DoD condition 6, Q32) is blocked on the workflow
  engine Q5 via Q15, and Q5 is a multi-cycle adaptation of the fork's
  workflow/resumer substrate, so it is not the smallest completable item. The
  pipeline backbone is complete through stage 10 at the gate routes, so there was
  no smaller gate-integrity defect with satisfied prerequisites. Q2 is a real,
  currently undetected DoD gap: section 13 condition 5 requires the LLM adapter to
  log model, prompt version, usage and trace id and to prove the real provider
  path, and before this cycle the seam had only the offline fake. Alternatives
  rejected: another canon asset outside the stage order (post-stage-10 assets do
  not block the pipeline) and the REST resource routes Q9-Q14 (ready but surface,
  not DoD blocking).
- Outcome: new module
  `backend/redops/agents/infrastructure/llm_gateway.py` with two adapters behind
  the port. `ForkProviderModelGateway(provider_for, runner=None, max_tokens=...)`
  selects the provider for the request's model through an injected lookup,
  translates the typed `ModelRequest` into an Anthropic-shaped
  `messages_create(model, max_tokens, messages)` call, runs it through an
  injected runner (`asyncio.run` by default), and joins the text blocks back into
  a `ModelResponse` that preserves the request's model, prompt version, trace id
  and context references with a typed `ModelUsage`. `from_fork_registry()` lazily
  binds the fork's `openexecutive.providers.registry.get_provider`, so the agent
  package does not import the fork at module load. A new named error
  `ModelGatewayRuntimeError` (`agents/domain/errors.py`) makes the adapter refuse
  inside a running event loop instead of deadlocking. `LoggingModelGateway` is a
  decorator over any `ModelGateway` that emits one structured INFO record per call
  with the tenant, model, prompt version, trace id, context references and
  input/output tokens, and never the prompt or response text (SPEC.md section 9),
  so both the offline fake and the live adapter get the section 6 attribution log
  without a second implementation. Onion rule respected: the adapter lives in
  infrastructure and the logging decorator uses only stdlib; domain imports no
  vendor code.
- Evidence: `make check` -> 1959 passed, 1 skipped, 680 subtests; pyflakes clean.
  New behavioral tests `tests/unit/agents/test_llm_gateway.py` (12 tests): the
  adapter is a `ModelGateway`; it translates the request to the Anthropic shape
  and back with preserved attribution and usage; it selects the provider by
  request model; it joins multiple text blocks; it refuses a provider without
  `messages_create`; it refuses inside a running loop; `from_fork_registry` binds
  the fork's `get_provider`; the logging decorator delegates and returns the
  delegate response, logs model, prompt version, trace id, tenant, context
  references and input/output tokens, never logs the prompt or response text,
  rejects a non-gateway delegate, and honors a supplied logger. `make done`
  clears [1/6]-[4/6] and still fails [5/6] (`frontend/` missing, Q32).
- New findings: section 13 condition 5's offline half (Q1) and the logging and
  real-provider-adapter half (Q2) are now both implemented; the remaining piece
  is the env-gated live OpenRouter smoke (Q4), which needs a key and proves one
  live call. The fork provider is async while the RED port is synchronous, so the
  adapter bridges with `asyncio.run` and raises `ModelGatewayRuntimeError` inside
  a running loop; if a later worker runs inside an event loop the composition
  layer must supply a thread/loop runner or make the port async. The unresolved
  Q3 architecture tension remains: ADR 0006 registers RED agents through the
  fork's `orchestrator/router.py` while DoD condition 7 requires zero vendor
  edits; that is a named-owner/architecture decision, not a Q2 blocker.
- Blockers: the Q28 stage 8/9/10 required-kind placement decision (named-owner);
  `frontend/` (DoD condition 6, Q32) blocked on Q5 via Q15; request idempotency
  (Q16) blocked on the same; RLS is a WHERE clause only (ADR 0004); the condition
  3 retrieval, background worker and artifact-URL layers are unbuilt; Q3 agent
  registration blocked on the ADR 0006 versus vendor-edit tension; the live
  OpenRouter smoke (Q4) needs an `OPENROUTER_API_KEY` to run.
- Highest priority ready next item: the Q4 live OpenRouter smoke test, an
  env-gated test that skips without a key and, with a key, proves one live call
  through `ForkProviderModelGateway` and the section 6 attribution log (Q2 now
  supplies the adapter). In parallel, the single most useful unblocker for the
  last failing DoD checkpoint remains the Q5 workflow engine slice (versioned
  definition, durable run state, approval wait survives a restart, idempotent
  effects), which unblocks Q15 -> Q32 and the SPEC.md section 11 "restarting
  worker preserves a waiting workflow" acceptance scenario; it is larger than one
  bounded canon-adjacent item and was not selected this cycle. Required owner
  input for the pipeline: the stage 8/9/10 canon placement decision; approver for
  any wired kind: the client designated authority; blocked downstream dependency:
  the stage 9 gate.

### Prior cycle (2026-10-03T183929Z)

- Cycle 2026-10-03T183929Z (Ralph cycle, the prior cycle): selected item was queue Q1,
  the deterministic fake model gateway (a `ModelGateway` port plus an offline
  test adapter) in a new `backend/redops/agents/` bounded package (SPEC.md
  sections 5 and 6, section 13 condition 5; implementation plan Q1). Q1 is the
  highest ready item in the Prototype ready queue: its dependency list is empty,
  it is the queue's number-one seed item, and nothing else ready precedes it.
  It outranked the alternatives for these reasons. The stage 8-10 canon
  required-kind wiring (Q28) is blocked on the named methodology-owner placement
  decision the prior cycle recorded (the register leaves the home of
  `EnrollmentPlan`, `ClientProcess` and `SwimlanesPlan` open between the stage 8
  "Funnel Complete" gate and a later stage 9/10 gate), and the task forbids
  making that decision unattended. The Next.js `frontend/` shell (DoD condition
  6, Q32) is blocked on the workflow engine Q5 via Q15, and Q5 is a multi-cycle
  adaptation of the fork's workflow/resumer substrate, so it is not the smallest
  completable item. The pipeline backbone itself is complete through stage 10 at
  the gate routes, so there was no smaller gate-integrity defect with satisfied
  prerequisites. Q1 is a real, currently undetected DoD gap: section 13 condition
  5 requires a deterministic fake model gateway and the loop has no model seam
  at all, so no agent can run offline and the "real provider path" has no
  interface to prove against. Alternatives rejected: another canon asset outside
  the stage order (the register's remaining unimplemented assets, Serve/Grow and
  the service and partnership lines, sit after stage 10 and do not block the
  pipeline) and the REST resource routes Q9-Q14 (ready but surface, not DoD
  blocking).
- Outcome: new package `backend/redops/agents/` with `domain/errors.py`,
  `domain/value_objects.py`, `application/ports.py` and
  `infrastructure/fake_gateway.py`. `ModelRequest` pins the tenant, model,
  prompt, prompt version, trace id and duplicate-free context references (SPEC.md
  sections 6 and 9); `ModelUsage` holds non-negative integer token counts;
  `ModelResponse` carries the text plus the same model, prompt version, trace id
  and context references and a typed usage, and refuses blank text or a missing
  usage. The abstract `ModelGateway.generate(request) -> ModelResponse` port is
  the seam agent use cases depend on. `DeterministicFakeModelGateway` answers
  offline and deterministically: a configured prompt-to-text map wins, otherwise
  the text is derived from the prompt version and prompt; it records each call's
  attribution and holds no credentials, so nothing secret can appear in a
  request or response. Onion rule respected: domain imports no framework, ORM,
  queue, vendor or model SDK code; the port is defined by the application need.
- Evidence: `make check` -> 1947 passed, 1 skipped, 680 subtests; pyflakes
  clean. New behavioral tests `tests/unit/agents/test_model_gateway.py` (13
  tests, 5 subtests): request identity and blank/duplicate context refusals,
  usage refusal of negative/bool/string counts, response refusal of blank text
  and untyped usage, determinism (same request equal, distinct prompts distinct),
  configured response lookup, attribution passthrough, the call log, and no
  secret leakage, plus `isinstance(fake, ModelGateway)`. `make done` clears
  [1/6]-[4/6] and still fails [5/6] (`frontend/` missing, Q32).
- New findings: the loop has no model seam despite section 13 condition 5
  requiring a deterministic fake gateway and a proven live provider path; Q1 now
  supplies the offline half. Context map and ADR 0006 place RED agents over the
  fork's specialist/provider machinery, and this port is resolution-agnostic, so
  the Q2 live OpenRouter adapter can wrap the fork's `providers` behind it
  without touching the vendor. An unresolved architecture tension remains for Q3
  agent registration: ADR 0006 registers RED agents through the fork's
  `orchestrator/router.py` while DoD condition 7 requires zero vendor edits;
  that conflict is a named-owner/architecture decision, not a Q1 blocker.
- Blockers: the Q28 stage 8/9/10 required-kind placement decision (named-owner);
  `frontend/` (DoD condition 6, Q32) blocked on Q5 via Q15; request idempotency
  (Q16) blocked on the same; RLS is a WHERE clause only (ADR 0004); the
  condition 3 retrieval, background worker and artifact-URL layers are unbuilt;
  Q3 agent registration blocked on the ADR 0006 versus vendor-edit tension.
- Highest priority ready next item: the Q2 live RED LLM adapter that satisfies
  the new `ModelGateway` port, wraps the fork's provider registry, and logs
  model, prompt version, context references, usage and trace id, with a
  contract test and an env-gated live OpenRouter smoke (Q4). It is the next
  dependency-satisfied queue item after Q1. In parallel, the single most useful
  unblocker for the last failing DoD checkpoint remains the Q5 workflow engine
  slice (versioned definition, durable run state, approval wait survives a
  restart, idempotent effects), which unblocks Q15 -> Q32 and the SPEC.md
  section 11 "restarting worker preserves a waiting workflow" acceptance
  scenario; it is larger than one bounded canon-adjacent item and was not
  selected this cycle. Required owner input for the pipeline: the stage 8/9/10
  canon placement decision; approver for any wired kind: the client designated
  authority; blocked downstream dependency: the stage 9 gate.

### Prior cycle (2026-10-03T183643Z)

- Cycle 2026-10-03T183643Z (Ralph cycle, the prior cycle): selected item was wiring the
  canon Extract `ContentPlan` as a required stage 6 "Campaign Message Approved"
  kind (queue Q28; owner decision 2026-10-03; SPEC.md sections 4, 12.3 and 12.5;
  canon files 25, 27 and 28). The typed `ContentPlan` was implemented (Ralph
  cycle 2026-10-03T174319Z) but not a required asset kind and not carried by the
  stage 6 `CampaignMessagePackage`, so the gate's declared package recorded the
  fourteen kinds and never the canon plan the message's content is extracted
  from; the "Campaign Message Approved" checkpoint could pass without a content
  plan. It outranked the stage 7-10 canon assets because those come later in the
  Q28 stage-ordered queue, and the stage 6 content family (roadmap, crusher) was
  already gate-required; `ContentPlan` is the last stage 6 content candidate. It
  grounds on the stage 4 `SignatureSolution` already resolved by the stage 6
  route and on a `PrimaryCurrency` the request can carry, so the added
  resolution surface is bounded to the currency input. Alternatives rejected:
  the Next.js `frontend/` shell (DoD condition 6, blocked on Q5 via Q15), request
  idempotency (Q16, blocked on the same) and jumping to the stage 7-10 canon
  assets out of stage order.
- Outcome: `ContentPlan`
  (`backend/redops/contexts/commercial/domain/value_objects.py`) gained
  `CONTENT_PLAN_KIND = "content-plan"` and `as_stage_asset(version=...)` that
  refuses a versionless projection. The kind joined `CANONICAL_MESSAGE_KINDS`
  and the stage 6 template `required_asset_kinds` in
  `governance/domain/templates.py` (fourteen kinds to fifteen).
  `CampaignMessagePackage` now carries `plan` + `plan_version`, type-checks and
  tenant-checks it, refuses a versionless one, and projects `content-plan` from
  the plan's own identity at its exact version while the twelve message kinds
  still pin the `CampaignMessage`, `content-roadmap` pins the roadmap and
  `content-crusher` pins the crusher. The stage 6 route accepts a nested
  `ContentPlanInput` (`api/schemas.py`, `ContentThemeInput`, `ContentIdeaInput`)
  carrying the locked `PrimaryCurrency`, builds the typed plan grounded on the
  resolved approved method's own Signature Solution, and passes it to the
  package.
- Evidence: `make check` -> 1934 passed, 1 skipped, 675 subtests; pyflakes
  clean. New behavioral tests:
  `tests/unit/commercial/test_campaign_message_package.py` (fifteen kinds, the
  `content-plan` kind pinned from `plan-3f` at its own version while the twelve
  message kinds pin `message-3f`, cross-tenant and untyped and versionless plan
  refusals); `tests/unit/engagement/test_record_stage_six_gate.py` (15
  exact-version refs and 15 approvals); and
  `tests/unit/test_stage_six_gate_route.py` (plan accepted in the stage 6
  payload; the versionless-roadmap 422 test still holds). `make done` clears
  [1/6]-[4/6] and still fails [5/6] (`frontend/` missing, Q32).
- New findings: the stage 6 gate now records the canon Extract content plan at an
  exact version, so the "Campaign Message Approved" checkpoint cannot pass on the
  message, roadmap and crusher kinds alone. Stage 6 is now canon-complete at
  fifteen required kinds for the roadmap, crusher and plan; the stage 7-10 canon
  assets stay unwired.
- Blockers: `frontend/` (DoD condition 6, Q32) is blocked on the workflow
  engine Q5 via Q15; request idempotency (Q16) blocked on the same; RLS is a
  WHERE clause only (ADR 0004); the condition 3 retrieval, background worker and
  artifact-URL layers are unbuilt; the stage 8/9/10 canon gap register entries
  need named-owner decisions.
- Highest priority ready next item: continue Q28 at stage 8, where the canon
  `EnrollmentPlan`, `ClientProcess` and `SwimlanesPlan` are implemented but not
  yet required gate kinds (canon files 06, 13, 14, 21, 24, 35-49). Stage 7 is
  already canon-covered: the `AuthorityAmplifierPackage` projects the stage 7
  script-through-player kinds, and no gap-register entry targets stage 7. The
  stage 8 candidates each need a named methodology-owner decision on whether
  their home is the stage 8 "Funnel Complete" gate or a later stage 9 gate
  (adding or placing an asset is an owner decision, and the register leaves the
  placement open). The smallest ready slice is `SwimlanesPlan` (grounded on a
  same-tenant stage 8 `FunnelIntegration`), which would ride the existing
  `FunnelIntegration` package bridge like the stage 6 content family. Required
  asset: the typed plan and its `as_stage_asset` projection; approver: the client
  designated authority; blocked downstream dependency: the stage 9 gate.
  Prerequisite: the completed stage 6 fifteen-kind set and the owner placement
  decision. Canon gap register updated: the Extract entry now records the wired
  stage 6 `content-plan` source.

### Prior cycle (2026-10-03T183447Z)

- Cycle 2026-10-03T183447Z (Ralph cycle, the prior cycle): selected item was wiring the
  canon content crusher as a required stage 6 "Campaign Message Approved" kind
  (queue Q28; owner decision 2026-10-03; SPEC.md sections 4, 12.3 and 12.5;
  canon files 12, 16 and 32). The typed `ContentCrusher` was implemented (Ralph
  cycle 124) but not a required asset kind and not carried by the stage 6
  `CampaignMessagePackage`, so the gate's declared package recorded the
  thirteen kinds and never the canon crusher the message's content depends on;
  the "Campaign Message Approved" checkpoint could pass without a content
  crusher. It outranked `ContentPlan` because the crusher grounds directly on
  the `ContentRoadmap` topic already carried by the package (the roadmap joined
  the same package last cycle), so it needs no new upstream asset resolution and
  is the smallest independently verifiable next slice; it is stage 6, the active
  stage in the Q28 stage-ordered queue after the roadmap. Alternatives rejected:
  `ContentPlan` (also stage 6, but the upstream Extract step, larger because it
  would add method- and currency-resolution surface) and the Next.js
  `frontend/` shell (DoD condition 6, blocked on Q5 via Q15).
- Outcome: `ContentCrusher`
  (`backend/redops/contexts/commercial/domain/value_objects.py`) gained
  `CONTENT_CRUSHER_KIND = "content-crusher"` and `as_stage_asset(version=...)`
  that refuses a versionless projection. The kind joined
  `CANONICAL_MESSAGE_KINDS` and the stage 6 template `required_asset_kinds` in
  `governance/domain/templates.py` (thirteen kinds to fourteen).
  `CampaignMessagePackage` now carries `crusher` + `crusher_version`,
  type-checks and tenant-checks it, refuses a versionless one, and projects
  `content-crusher` from the crusher's own identity at its exact version while
  the twelve message kinds still pin the `CampaignMessage` and `content-roadmap`
  pins the roadmap. The stage 6 route accepts a nested `ContentCrusherInput`
  (`api/schemas.py`), builds the typed crusher grounded on the roadmap it also
  builds from the request (so the crusher topic and Signature Solution steps are
  validated against the same roadmap), and passes it to the package.
- Evidence: `make check` -> 1930 passed, 1 skipped, 673 subtests; pyflakes
  clean. New behavioral tests:
  `tests/unit/commercial/test_campaign_message_package.py` (fourteen kinds, the
  `content-crusher` kind pinned from `crusher-3f` at its own version while the
  twelve message kinds pin `message-3f`, cross-tenant and untyped and versionless
  crusher refusals); `tests/unit/engagement/test_record_stage_six_gate.py` (14
  exact-version refs and 14 approvals); and
  `tests/unit/test_stage_six_gate_route.py` (crusher accepted in the stage 6
  payload; the versionless-roadmap 422 test still holds). `make done` clears
  [1/6]-[4/6] and still fails [5/6] (`frontend/` missing, Q32).
- New findings: the stage 6 gate now records the canon content crusher at an
  exact version, so the "Campaign Message Approved" checkpoint cannot pass on
  the roadmap and the twelve message kinds alone. Stage 6 is now canon-complete
  for the roadmap and the crusher at fourteen required kinds; `ContentPlan`
  (canon 25, 27, 28) stays unwired, as do the stage 8/9/10 canon assets.
- Blockers: `frontend/` (DoD condition 6, Q32) is blocked on the workflow
  engine Q5 via Q15; request idempotency (Q16) blocked on the same; RLS is a
  WHERE clause only (ADR 0004); the condition 3 retrieval, background worker and
  artifact-URL layers are unbuilt; the stage 8/9/10 canon gap register entries
  need named-owner decisions.
- Highest priority ready next item: continue Q28 by wiring the `ContentPlan`
  (canon files 25, 27, 28) as a fourteenth/fifteenth stage 6 kind, then continue
  to the stage 7-10 canon assets. `ContentPlan` grounds on a same-tenant stage 4
  `SignatureSolution` and the stage 2 `PrimaryCurrency`, so it needs those
  resolved in the stage 6 route before it can join the package. Required asset:
  the typed plan and its `as_stage_asset` projection; approver: the client
  designated authority; blocked downstream dependency: the stage 7 gate.
  Prerequisite: the completed stage 6 fourteen-kind set. Canon gap register
  updated: the audience-building and content flywheel entry and the Content
  Crusher entry now record the wired stage 6 `content-crusher` source.

### Prior cycle (2026-10-03T183151Z)

- Cycle 2026-10-03T183151Z (Ralph cycle, the prior cycle): selected item was wiring the
  canon content roadmap as a required stage 6 "Campaign Message Approved" kind
  (queue Q23/Q28; owner decision 2026-10-03; SPEC.md sections 4, 12.3 and 12.5;
  canon files 25-28). The typed `ContentRoadmap` was implemented (Ralph cycle
  115) but not a required asset kind and not carried by the stage 6
  `CampaignMessagePackage`, so the gate's declared package recorded the twelve
  message kinds and never the canon roadmap the message depends on; the
  "Campaign Message Approved" checkpoint could pass without a content roadmap.
  It outranked `ContentCrusher` and `ContentPlan` because the roadmap is the
  upstream asset both ground on and stage 6 is the next stage in the Q28
  stage-ordered queue after stage 5. Alternatives rejected: the Next.js
  `frontend/` shell (DoD condition 6, blocked on Q5 via Q15) and request
  idempotency (Q16, blocked on the same).
- Outcome: `ContentRoadmap`
  (`backend/redops/contexts/commercial/domain/value_objects.py`) gained
  `CONTENT_ROADMAP_KIND = "content-roadmap"` and `as_stage_asset(version=...)`
  that refuses a versionless projection. The kind joined
  `CANONICAL_MESSAGE_KINDS` and the stage 6 template `required_asset_kinds` in
  `governance/domain/templates.py` (twelve kinds to thirteen).
  `CampaignMessagePackage` now carries `roadmap` + `roadmap_version`,
  type-checks and tenant-checks it, refuses a versionless one, and projects
  `content-roadmap` from the roadmap's own identity at its exact version while
  the twelve message kinds still pin the `CampaignMessage`. The stage 6 route
  accepts a nested `ContentRoadmapInput`/`ContentTopicInput`
  (`api/schemas.py`), grounds the roadmap on the resolved approved method's own
  Signature Solution, and derives the fixed Authority Amplifier script beats
  from the canonical order.
- Evidence: `make check` -> 1926 passed, 1 skipped, 671 subtests; pyflakes
  clean. New behavioral tests:
  `tests/unit/commercial/test_campaign_message_package.py` (thirteen kinds, the
  `content-roadmap` kind pinned from `roadmap-3f` at its own version while the
  twelve message kinds pin `message-3f` at the message version, cross-tenant and
  untyped and versionless roadmap refusals);
  `tests/unit/engagement/test_record_stage_six_gate.py` (13 exact-version refs
  and 13 approvals); and `tests/unit/test_stage_six_gate_route.py` (versionless
  roadmap rejected as a 422 with no write). `make done` clears [1/6]-[4/6] and
  still fails [5/6] (`frontend/` missing, Q32).
- New findings: the stage 6 gate now records the canon content roadmap at an
  exact version, so the "Campaign Message Approved" checkpoint cannot pass on
  the message's twelve kinds alone. Stage 6 is now canon-complete for the
  roadmap at thirteen required kinds; `ContentCrusher` (canon 12, 16, 32) and
  `ContentPlan` (canon 25, 27, 28) stay unwired, as do the stage 8/9/10 canon
  assets.
- Blockers: `frontend/` (DoD condition 6, Q32) is blocked on the workflow
  engine Q5 via Q15; request idempotency (Q16) blocked on the same; RLS is a
  WHERE clause only (ADR 0004); the condition 3 retrieval, background worker and
  artifact-URL layers are unbuilt; the stage 8/9/10 canon gap register entries
  need named-owner decisions.
- Highest priority ready next item: continue Q28 by wiring the next
  canon-informed asset that maps to a stage 6 kind in stage order. The
  `ContentCrusher` (canon files 12, 16, 32) grounds on a roadmap topic and the
  `ContentPlan` (canon files 25, 27, 28) is the upstream Extract step; either
  can join the stage 6 package as a fourteenth required kind under the same
  required-kind policy. Required asset: the typed asset and its `as_stage_asset`
  projection; approver: the client designated authority; blocked downstream
  dependency: the stage 7 gate. Prerequisite: the completed stage 6
  thirteen-kind set. Canon gap register updated: the audience-building and
  content flywheel entry now records the wired stage 6 `content-roadmap`
  source.

### Prior cycle (2026-10-03T182409Z)

- Cycle 2026-10-03T182409Z (Ralph cycle, the prior cycle): selected item was wiring
  the canon Product Matrix program as a required stage 5 kind (queue Q28; owner
  decision 2026-10-03; SPEC.md sections 4, 12.3 and 12.5; canon files 11 and
  12). The typed `ProductProgram` was implemented (cycle 126) but not a required
  asset kind, so the stage 5 "Offer Locked" gate's declared required set did not
  record the canon's product matrix model, outcome pricing, six-to-twelve week
  structure and per-step modules; a free-text delivery model and pricing could
  satisfy the delivery package without them. It outranked the stage 4
  `ThirteenTransformations` wiring (canon 09, 10) and the stage 6 content assets
  (`ContentPlan`/`ContentCrusher`/`ContentRoadmap`): the stage 5 slice touches
  fewer route payload builders (stage 5 and 6) than a stage 4 kind would (stage
  4, 5 and 6), so it is the smallest independently verifiable next slice.
  Alternatives also rejected: the `frontend/` shell (DoD condition 6, blocked on
  Q5 via Q15) and request idempotency (Q16, blocked on Q5).
- Outcome: `ProductProgram`
  (`backend/redops/contexts/commercial/domain/value_objects.py`) gained
  `PRODUCT_PROGRAM_KIND` and `as_stage_asset(version=...)` that refuses a
  versionless projection. The kind joined `CANONICAL_OFFER_KINDS` and the stage 5
  template `required_asset_kinds` in `governance/domain/templates.py` (twelve
  kinds to thirteen). `OfferPackage` now type-checks and tenant-checks a carried
  `ProductProgram`, refuses a versionless one, and projects `product-program` from
  the program's own identity at its exact version while the twelve delivery kinds
  still pin the `DeliverySpecification`. The stage 5 route accepts a nested
  `ProductProgramInput`/`ProductModuleInput` (`api/schemas.py`) and builds the
  typed program, grounded on the route's stage 4 signature solution, in
  `record_stage_five_gate`.
- Evidence: `make check` -> 1914 passed, 1 skipped, 665 subtests; pyflakes clean.
  New behavioral tests: `tests/unit/commercial/test_product_program.py`
  (`as_stage_asset` exact-kind projection and versionless rejection) and
  `tests/unit/commercial/test_offer_package.py` (thirteen kinds, the
  product-program kind pinned from `program-3f` at the program version, the
  delivery kinds still pinned from `delivery-3f`, cross-tenant program refusal).
  The stage 5 gate and recorder tests now assert 13 required assets and 13
  exact-version approvals. `make done` clears [1/6]-[4/6] and still fails [5/6]
  (`frontend/` missing).
- New findings: the stage 5 gate now declares and pins the canon Product Matrix
  program, so a gate cannot pass on a free-text delivery model and pricing alone.
  Stage 5 is now canon-complete at thirteen required kinds. Stages 4, 6, 8, 9
  and 10 canon-informed assets stay unwired; each needs its target kind.
- Blockers: `frontend/` (DoD condition 6, Q32) is blocked on the workflow engine
  Q5 via Q15; request idempotency (Q16) blocked on the same; RLS is a WHERE
  clause only (ADR 0004); the condition 3 retrieval, background worker and
  artifact-URL layers are unbuilt; the remaining canon gap register entries need
  named-owner decisions.
- Highest priority ready next item: continue Q28 by wiring the next
  canon-informed asset that maps cleanly to a stage kind in order. The stage 4
  `transformation-map`/`ThirteenTransformations` (canon files 09 and 10) through
  the `SignaturePackage` bridge is the next stage in order; the stage 6 content
  assets (`ContentPlan`/`ContentCrusher`/`ContentRoadmap`, canon files 12, 16,
  25-28, 32) are the alternative. Required asset: the typed asset and its
  `as_stage_asset` projection; approver: the client designated authority; blocked
  downstream dependency: the next stage gate in order. Prerequisite: the
  completed stage 5 thirteen-kind set. Canon gap register updated: the Product
  Matrix and perfect product entry now records the wired stage 5
  `product-program` source.

### Prior cycle (2026-10-03T182015Z)

- Cycle 2026-10-03T182015Z (Ralph cycle, this run): selected item was wiring the
  canon compliance suite as a required stage 9 kind (queue Q28; owner decision
  2026-10-03; SPEC.md sections 4, 12.3 and 12.5; canon files 21 and 34). The
  reviewed `CompliancePackage` already gated "Launch Approved" through
  `ComplianceRequiredPolicy` and was carried by the ready-for-traffic
  `LaunchQA`, but it was not a required asset kind of the stage 9 template, so
  the gate's declared required set did not record the exact compliance evidence
  it relied on. Wiring it as the required `compliance-package` kind makes the
  stage 9 gate pin the reviewed compliance package as exact evidence. It
  outranked the stage 4 `transformation-map`/`SignaturePackage` wiring of
  `ThirteenTransformations` and the stage 5 `ProductProgram` wiring: those need
  new nested request schemas and edits across the seven stage route payload
  builders, whereas the compliance package is already a field of the stage 9
  request, so this is the smallest independently verifiable slice that still
  closes a canon gap blocking a gate. Alternatives also rejected: the
  `frontend/` shell (DoD condition 6, blocked on Q5 via Q15) and request
  idempotency (Q16, blocked on Q5).
- Outcome: `CompliancePackage`
  (`backend/redops/contexts/execution/domain/value_objects.py`) gained
  `COMPLIANCE_PACKAGE_KIND` and `as_stage_asset(version=...)` that refuses a
  versionless projection. The kind joined `CANONICAL_LAUNCH_KINDS` and the stage
  9 template `required_asset_kinds` in `governance/domain/templates.py`
  (sixteen kinds to seventeen). `LaunchQAPackage` now type-checks and
  tenant-checks the carried compliance package, refuses a ready QA whose
  compliance package is absent, and projects `compliance-package` from the
  package's own identity at the reviewed QA version rather than pinning it as
  the QA identity. The package is the pinning unit, not the six canonical
  compliance assets, because a required asset may be met by a live scoped human
  waiver and SPEC.md section 4 keeps a waiver from making an absent asset appear
  present.
- Evidence: `make check` -> 1909 passed, 1 skipped, 661 subtests; pyflakes
  clean. New behavioral tests: `tests/unit/execution/test_compliance_package.py`
  (`as_stage_asset` exact-kind projection and versionless rejection) and
  `tests/unit/execution/test_launch_qa_package.py` (seventeen kinds, the
  compliance kind pinned from `compliance-3f` at the QA version, the QACheckKind
  mapping now disjoint from the compliance kind). The stage 9 gate and recorder
  tests now assert 17 required assets and 17 exact-version approvals.
  `make done` clears [1/6]-[4/6] and still fails [5/6] (`frontend/` missing).
- New findings: the stage 9 gate now declares the compliance package it already
  enforced at traffic authorization, so a gate cannot pass without recording the
  compliance evidence. Stages 4, 5, 6, 8 and the remaining stage 9/10
  canon-informed assets stay unwired; each needs its target kind. The
  `ThirteenTransformations` and `ProductProgram` wirings are larger because they
  add nested request schemas and touch the stage route payload builders.
- Blockers: `frontend/` (DoD condition 6, Q32) is blocked on the workflow engine
  Q5 via Q15; request idempotency (Q16) blocked on the same; RLS is a WHERE
  clause only (ADR 0004); the condition 3 retrieval, background worker and
  artifact-URL layers are unbuilt; the remaining canon gap register entries need
  named-owner decisions.
- Highest priority ready next item: continue Q28 by wiring the next
  canon-informed asset that maps cleanly to an existing stage kind. The stage 4
  `transformation-map` can be pinned from the typed `ThirteenTransformations`
  (canon files 09 and 10) through the `SignaturePackage` bridge, but that needs
  a new transformations request schema and edits to the seven stage route
  payload builders; the stage 5 `delivery-model`/`pricing-payments` can be
  pinned from the typed `ProductProgram` (canon files 11 and 12) at the same
  size. Required asset: the typed asset and its `as_stage_asset` projection;
  approver: the client designated authority; blocked downstream dependency: the
  next stage gate in order. Prerequisite: the completed stage 9 seventeen-kind
  set. Canon gap register updated: the compliance suite entry now records the
  wired stage 9 `compliance-package` source.

### Prior cycle (2026-10-03T181744Z)

- Cycle 2026-10-03T181744Z (Ralph cycle, this run): selected item was the last
  remaining implemented stage 1 canon asset under the required-kind policy (queue
  Q28; owner decision 2026-10-03; SPEC.md sections 4, 12.3 and 12.5; canon file
  00). The typed Commercial `TargetMarketMatchmaker` already enforced the canon's
  candidate narrowing (two or more typed candidates, one selected, same-tenant
  awareness map) but the stage 1 "Avatar Locked" gate did not require it, so the
  canon's defensible choice of target market could be absent from a passing gate,
  or replaced with prose, without being flagged. Wiring it as the required
  `target-market-match` kind completes the stage 1 required-kind set and outranks
  the Next.js `frontend/` shell (DoD condition 6, blocked on the workflow engine
  Q5 via Q15) and request idempotency (Q16, blocked on Q5): the loop prioritizes
  exact approved asset versions and dependency enforcement over downstream
  features.
- Outcome: `TargetMarketMatchmaker`
  (`backend/redops/contexts/commercial/domain/value_objects.py`) gained the named
  `TARGET_MARKET_MATCH_KIND` and `as_stage_asset(version=...)` that refuses a
  versionless projection; the kind joined `CANONICAL_DIAGNOSIS_KINDS` and the
  stage 1 template `required_asset_kinds` in `governance/domain/templates.py`
  (ten kinds to eleven). `DiagnosisPackage` carries `target_market_match` +
  `target_market_match_version`, type-checks and tenant-checks the match, refuses
  a versionless one, and projects `target-market-match` at the exact version.
  `StageOneGateAssembler` now invokes
  `TargetMarketMatchPolicy().require_servable`, so a gate whose chosen market is
  the completely unaware cannot assemble. The stage 1 route (`api/routes.py`)
  accepts `TargetMarketMatchmakerInput` (`TargetMarketCandidateInput`,
  `api/schemas.py`) and maps it to the typed match, reusing the already-built
  stage 1 awareness map. Reusing one researched map rather than accepting a second
  is an intentional narrowing of the canon (SPEC.md section 12.4) that prevents
  two divergent awareness positions inside one diagnosis.
- Evidence: `make check` -> 1906 passed, 1 skipped, 659 subtests; pyflakes clean.
  New behavioral tests: `tests/unit/commercial/test_target_market_matchmaker.py`
  (exact-kind projection and versionless rejection) and
  `tests/unit/commercial/test_diagnosis_package.py` (target-market-match
  projection from the typed match, versionless and cross-tenant rejection);
  `tests/unit/engagement/test_record_stage_one_gate.py` now asserts 11 required
  assets and 11 exact-version approvals. The six stage route payload builders
  (`test_stage_one..six_gate_route.py`) supply the typed match. `make done` clears
  [1/6]-[4/6] and still fails [5/6] (`frontend/` missing).
- New findings: stage 1 is now canon-complete at eleven required kinds; every
  implemented stage 1 canon asset (`MarketAwarenessMap`, `AudienceReachEstimate`,
  `TargetMarketMatchmaker`) is pinned from its typed value at an exact version.
  Stages 2-10 required-kind wiring is the remaining Q28 body of work; stage 2
  `CurrencyPackage` already projects its ten template kinds, so the remaining
  wiring concerns canon-informed assets implemented but not yet gate-required
  (for example `FunnelFinder`, the `ContentPlan`/`ContentCrusher` stage 6 assets,
  the `CompliancePackage` at stage 9), each needing its target kind and, where the
  target stage is not already fixed by SPEC.md section 12.3, a methodology-owner
  decision.
- Blockers: `frontend/` (DoD condition 6, Q32) is blocked on the workflow engine
  Q5 via Q15; request idempotency (Q16) blocked on the same; RLS is a WHERE clause
  only (ADR 0004); the condition 3 retrieval, background worker and artifact-URL
  layers are unbuilt; the remaining canon gap register entries need named-owner
  decisions.
- Highest priority ready next item: continue Q28 in stage order by auditing the
  stages 2-10 canon-informed assets that are implemented but not gate-required and
  wiring the first one that maps cleanly to its stage's template kind. The
  `FunnelFinder` (positioning and decision tools gap, canon files 13 and 14) is a
  named stage 8 pre-selection asset and a candidate, but neither its stage kind nor
  the stage 6 content assets are yet fixed as required kinds, so the audit must
  confirm the target kind before wiring. Required asset: the typed asset and its
  `as_stage_asset` projection; approver: the client designated authority; blocked
  downstream dependency: the next stage gate in order. Prerequisite: the completed
  stage 1 eleven-kind set. Alternatives rejected this cycle: the Next.js
  `frontend/` shell (blocked on Q5 via Q15) and request idempotency (blocked on
  Q5). Canon gap register updated: the positioning and decision tools entry now
  records the target market match as the wired stage 1 `target-market-match`
  source.

### Prior cycle (2026-10-03T181518Z)

- Cycle 2026-10-03T181518Z (Ralph cycle): selected item was the next
  stage 1 slice of the required-kind policy (queue Q28; owner decision
  2026-10-03; SPEC.md sections 4, 12.3 and 12.5; canon files 02 and 03). The
  typed Commercial `AudienceReachEstimate` already existed with its research
  platform, sized audience, positive reach, source note and named owner, but the
  stage 1 "Avatar Locked" gate did not require it, so the market sizing the
  canon's Market station treats as a stage 1 input was not pinned as gate
  evidence. Wiring it as the required `audience-reach-estimate` kind outranks
  the Next.js `frontend/` shell (DoD 6, blocked on the workflow engine Q5 via
  Q15) and request idempotency (Q16, blocked on Q5), and is smaller than wiring
  both remaining stage 1 canon assets because it needs no nested awareness-map
  dependency. The loop prioritizes exact approved asset versions and dependency
  enforcement over downstream features.
- Outcome: `AudienceReachEstimate`
  (`backend/redops/contexts/commercial/domain/value_objects.py`) gained a named
  `AUDIENCE_REACH_ESTIMATE_KIND` and `as_stage_asset(version=...)` that refuses a
  versionless projection; the kind joined `CANONICAL_DIAGNOSIS_KINDS` and the
  stage 1 template `required_asset_kinds` in `governance/domain/templates.py`
  (nine kinds to ten). `DiagnosisPackage` carries
  `audience_reach_estimate` + `audience_reach_estimate_version`, type-checks and
  tenant-checks the estimate, refuses a versionless one, and projects
  `audience-reach-estimate` at the exact version. The stage 1 route
  (`api/routes.py`) accepts a new `AudienceReachEstimateInput`
  (`InterestSignalInput`, `AudienceDefinitionInput`,
  `api/schemas.py`) and maps it to the typed estimate with `ResearchPlatform`,
  `AudienceDefinition` and `InterestSignal`. `MarketReachPolicy` stays
  caller-invoked (no universal audience floor); the typed value already enforces
  a positive reach and the gate pins the exact version.
- Evidence: `make check` -> 1903 passed, 1 skipped, 658 subtests; pyflakes clean.
  New behavioral tests: `test_diagnosis_package.py` (audience-reach projection
  from the typed estimate, versionless and cross-tenant rejection) and
  `test_record_stage_one_gate.py` (10 required assets and 10 exact-version
  approvals). The six stage route payload builders now supply the typed estimate.
  `make done` clears [1/6]-[4/6] and still fails [5/6] (`frontend/` missing).
- New findings: stage 1 now has ten required kinds. `TargetMarketMatchmaker`
  (`target-market-match`) is the last implemented stage 1 canon asset with no
  gate kind; it is a nested matchmaker carrying its own awareness map, so wiring
  it is a slightly larger schema/route slice. Stages 2-10 required-kind wiring
  remains untouched.
- Blockers: `frontend/` (DoD condition 6, Q32) is blocked on the workflow engine
  Q5 via Q15; request idempotency (Q16) blocked on the same; RLS is a WHERE clause
  only (ADR 0004); the condition 3 retrieval, background worker and artifact-URL
  layers are unbuilt; the remaining canon gap register entries need named-owner
  decisions.
- Highest priority ready next item: continue Q28 in stage order by wiring the last
  remaining implemented stage 1 canon asset `TargetMarketMatchmaker`
  (`target-market-match`) as a required kind, then proceed stage by stage.
  Required asset: the typed Commercial `TargetMarketMatchmaker` with its
  `TargetMarketCandidate` set and the package's awareness map; approver: the
  client designated authority; blocked downstream dependency: the stage 2
  Currency Locked gate. Prerequisite: the stage 1 typed awareness map and
  audience reach estimate now in place. Alternatives rejected this cycle: the
  Next.js `frontend/` shell (blocked on Q5 via Q15) and request idempotency
  (blocked on Q5). Canon gap register updated: the positioning and decision tools
  entry now records the audience reach estimate as the wired stage 1
  `audience-reach-estimate` source.

### Prior cycle (2026-10-03T181228Z)

- Cycle 2026-10-03T181228Z (Ralph cycle): selected item was the stage 1
  slice of the required-kind policy (queue Q28; owner decision 2026-10-03; SPEC.md
  sections 4, 12.4 and 12.5). The stage 1 "awareness-map" required kind was
  satisfied by the avatar's free-text `awareness` string even though the typed
  canon-informed `MarketAwarenessMap` asset already existed with its research
  evidence and message requirements. That is a gate-integrity hole: the ledger
  pinned untyped prose as the awareness asset. The loop prioritizes exact approved
  asset versions and dependency enforcement over downstream features, so this
  smallest independently verifiable Q28 slice outranked the Next.js `frontend/`
  shell (DoD 6, blocked on the workflow engine Q5 via Q15), request idempotency
  (Q16, blocked on Q5) and the larger stages 2-10 required-kind wiring.
- Outcome: the `awareness-map` gate kind is now pinned from the typed
  `MarketAwarenessMap`. `DiagnosisPackage`
  (`backend/redops/contexts/commercial/domain/value_objects.py`) carries
  `awareness_map` and `awareness_map_version`, type-checks and tenant-checks it,
  refuses a versionless map, and projects `awareness-map` through the map's own
  `as_stage_asset`; `awareness-map` is removed from `_AVATAR_DIAGNOSIS_KINDS`.
  `StageOneGateAssembler`
  (`backend/redops/contexts/engagement/domain/assemblies.py`) now runs
  `MarketAwarenessPolicy().require_targetable`, so a completely-unaware map cannot
  assemble the "Avatar Locked" gate. The stage 1 route (`api/routes.py`) accepts a
  new `AwarenessMapInput` (`api/schemas.py`) and maps it to `MarketAwarenessMap`.
  The canonical stage 1 kind count stays nine.
- Evidence: `make check` -> 1902 passed, 1 skipped, 657 subtests; pyflakes clean.
  New behavioral tests: `test_diagnosis_package.py` (typed-map projection, and
  cross-tenant / versionless map rejection), `test_record_stage_one_gate.py`
  (`MarketAwarenessTargetingError` for a completely-unaware map), and the six
  stage route payload builders now supply the typed map. `tests/e2e` still clears
  DoD condition 1.
- New findings: `awareness-map` is now sourced from the canonical asset. The
  remaining stage 1 canon assets `AudienceReachEstimate`
  (`audience-reach-estimate`) and `TargetMarketMatchmaker` (`target-market-match`)
  still have no gate kind and need new template kinds plus package/route fields;
  they are the next Q28 slice, but they enlarge the stage 1 asset package so they
  were not folded into this cycle.
- Blockers: `frontend/` (DoD condition 6, Q32) is blocked on the workflow engine
  Q5 via Q15; request idempotency (Q16) blocked on the same; RLS is a WHERE clause
  only (ADR 0004); the condition 3 retrieval, background worker and artifact-URL
  layers are unbuilt; the remaining canon gap register entries need named-owner
  decisions.
- Highest priority ready next item: continue Q28 in stage order by wiring the
  remaining implemented stage 1 canon assets as required kinds
  (`audience-reach-estimate` from `AudienceReachEstimate` and `target-market-match`
  from `TargetMarketMatchmaker`), then proceed stage by stage. Required assets:
  both typed Commercial values; approver: the client designated authority; blocked
  downstream dependency: the stage 2 Currency Locked gate. Prerequisite: the stage
  1 typed awareness map now in place. Alternatives rejected this cycle: the Next.js
  `frontend/` shell (blocked on Q5 via Q15) and request idempotency (blocked on
  Q5). Canon gap register updated: the positioning and decision tools entry now
  records the awareness map as the wired stage 1 `awareness-map` source.

### Prior cycle (2026-10-03T180944Z)

- Cycle 2026-10-03T180944Z (Ralph cycle, this run): selected item was the durable
  `LaunchQARepository` for the Execution context (port, mapper, migration and
  PostgreSQL adapter) plus the resolve-not-restate rule for the stage 9 QA, the
  exact next item the prior cycle named (SPEC.md sections 3, 4, 6 and 9; queue
  Q6). The stage 10 route re-stated the ready-for-traffic stage 9 `LaunchQA` from
  the request body, so a later gate could silently declare a different launch QA
  after the stage 9 "Launch Approved" checkpoint. It outranked the Next.js
  `frontend/` shell (DoD 6, blocked on the workflow engine Q5 via Q15), the larger
  required-kind wiring (Q28, which changes every stage's asset package and route)
  and the still-open gate-integrity items. The loop prioritizes exact approved
  asset versions and persistence over downstream features. This closes Q6: the
  funnel and launch-QA aggregates were the last two named there.
- Outcome: new Execution application port `LaunchQARepository`
  (`backend/redops/contexts/execution/application/ports.py`) and the Execution
  `infrastructure` mappers/repositories extended in the same shape as the funnel
  store. `launch_qa_to_payload`/`..._from_payload` round-trip the full authorized
  QA (state, the pinned `TrafficAuthorization`, the complete `CompliancePackage`
  with assets, waivers and target markets, the full check set, and the grounding
  stage 8 `FunnelIntegration` via the funnel mapper), so the QA cannot drift from
  the funnel shape and a reload re-validates through `LaunchQA.__post_init__`.
  `InMemoryLaunchQARepository` and `PostgresLaunchQARepository` refuse a QA without
  traffic authorization (`LaunchQAReadinessError`), a same-id different-body
  re-statement (`LaunchQAVersionConflictError`) and a blank tenant
  (`LaunchQAVersionTenantBoundaryError`). Migration `0008_launch_qas` creates
  `launch_qas(id, tenant_id NOT NULL, qa_id, qa JSONB, recorded_at,
  UNIQUE(tenant_id, qa_id))`. `api/routes.py::get_launch_qa_repository` is an
  env-selected generator like the method, offer, message, amplifier and funnel
  stores, and `_authorize_launch_qa(..., qa_repository=)` now resolves the QA: the
  stage 9 gate stores the authorized candidate, the stage 10 gate reuses the
  stored QA, and a different same-id body is refused (422). Both stage 9 and 10
  routes take the new dependency.
- Evidence: `make check` -> 1900 passed, 1 skipped, 656 subtests; pyflakes clean.
  New `tests/unit/execution/test_launch_qa_repository.py` (7 plus 3 mapper tests)
  and `test_launch_qa_postgres.py` (8, against the compose DB, exercising the real
  migration), a stage 10 re-statement refusal test in
  `tests/unit/test_stage_ten_gate_route.py`, an app-smoke QA-dep default test, and
  `tests/unit/shared/test_migrate.py` head now `0008_launch_qas`. The stage nine
  and ten route tests thread the QA dep override through the composed
  StageEight/Nine setUpClass chain. `make done` clears [1/6]-[4/6] and still fails
  at [5/6] (`frontend/` missing).
- New findings: the durable QA store now satisfies DoD condition 4 for
  `LaunchQA`; the stage 9 launch QA is tenant-scoped, immutable and shared across
  processes, and stage 10 grounds on it. Q6 is complete for every aggregate it
  named. The resolve-not-restate rule now covers stages 6, 7, 8 and 9; the only
  pipeline gate left without it is stage 10 itself, which is terminal in the
  prototype and is not consumed by a later gate.
- Blockers: `frontend/` (DoD condition 6, Q32) is blocked on the workflow engine
  Q5 via Q15; request idempotency (Q16) blocked on the same; RLS is a WHERE clause
  only (ADR 0004); the condition 3 retrieval, background worker and artifact-URL
  layers are unbuilt; the remaining canon gap register entries need named-owner
  decisions.
- Highest priority ready next item: wire the implemented canon-informed assets as
  required asset kinds of their target stage gates (queue Q28; owner decision
  2026-10-03), the larger required-kind policy item the last several cycles have
  repeatedly deferred as the alternative. It advances gate integrity and
  dependency enforcement across stages 1 to 10 by pinning each implemented asset
  as exact gate evidence through the existing `StageTemplate`/`StageGate` factory,
  in stage order, without adding or renaming a stage (SPEC.md sections 4 and
  12.5). Stage 1 first; required assets: the `MarketAwarenessMap`,
  `AudienceReachEstimate` and `TargetMarketCandidate`; approver: the client
  designated authority; blocked downstream dependency: the stage 2 Currency
  Locked gate. Prerequisite: none beyond the assets already in place. Alternatives
  rejected this cycle: the Next.js `frontend/` shell (DoD 6, blocked on Q5 via
  Q15) and request idempotency (Q16, blocked on Q5). Canon gap register unchanged
  this cycle; no new gap identified.

### Prior cycle (2026-10-03T180725Z)

- Cycle 2026-10-03T180725Z (Ralph cycle): selected item was the durable
  `FunnelIntegrationRepository` for the Execution context (port, mapper,
  migration and PostgreSQL adapter) plus the resolve-not-restate rule for the
  stage 9 and 10 gates, the exact next item the prior cycle named (SPEC.md
  sections 3, 4, 6 and 9; queue Q6). The stage 9 and 10 routes re-stated the
  completed stage 8 funnel from the request body, so a later gate could silently
  declare a different funnel after the stage 8 "Funnel Complete" checkpoint. It
  outranked the Next.js `frontend/` shell (DoD 6, blocked on the workflow engine
  Q5 via Q15), the larger required-kind wiring (Q28, which changes every stage's
  asset package and route) and the stage 9 launch QA store (the next re-stated
  asset after the funnel). The loop prioritizes exact approved asset versions and
  persistence over downstream features.
- Outcome: new Execution application port `FunnelIntegrationRepository`
  (`backend/redops/contexts/execution/application/ports.py`) and a new Execution
  `infrastructure` layer (`mappers.py`, `repositories.py`) in the same shape as
  the Commercial, Method and Production stores. `funnel_integration_to_payload`/
  `..._from_payload` round-trip the full completed funnel (state, the pinned
  `ProspectPathDryRun` with every handoff record and owner, all thirteen
  canonical asset references and the grounding stage 7 `AuthorityAmplifier`, via
  the Production `authority_amplifier...` helpers), so the funnel cannot drift
  from the amplifier shape and a reload re-validates through
  `FunnelIntegration.__post_init__`. `InMemoryFunnelIntegrationRepository` and
  `PostgresFunnelIntegrationRepository` refuse a funnel without completion
  (`FunnelReadinessError`), a same-id different-body re-statement
  (`FunnelVersionConflictError`) and a blank tenant
  (`FunnelVersionTenantBoundaryError`). Migration `0007_funnel_integrations`
  creates `funnel_integrations(id, tenant_id NOT NULL, integration_id, funnel
  JSONB, recorded_at, UNIQUE(tenant_id, integration_id))`.
  `api/routes.py::get_funnel_integration_repository` is an env-selected generator
  like the method, offer, message and amplifier stores, and
  `_complete_stage_eight_funnel(..., funnel_repository=)` now resolves the
  funnel: the stage 8 gate stores the completed candidate, a later gate reuses
  the stored funnel, a different same-id body is refused (422). All three stage
  8 to 10 routes take the new dependency.
- Evidence: `make check` -> 1880 passed, 1 skipped, 654 subtests; pyflakes clean.
  New `tests/unit/execution/test_funnel_integration_repository.py` (7 plus 3
  mapper tests) and `test_funnel_integration_postgres.py` (8, against the compose
  DB, exercising the real migration), a stage 9 re-statement refusal test in
  `tests/unit/test_stage_nine_gate_route.py`, an app-smoke funnel-dep default
  test, and `tests/unit/shared/test_migrate.py` head now
  `0007_funnel_integrations`. The stage 9 and 10 route tests thread the funnel
  dep override through the composed StageEight/Nine setUpClass chain. `make done`
  clears [1/6]-[4/6] and still fails at [5/6] (`frontend/` missing).
- New findings: the durable funnel store now satisfies DoD condition 4 for
  `FunnelIntegration`; the stage 8 funnel is tenant-scoped, immutable and shared
  across processes, and stage 9 and 10 ground on it. The stage 9 launch QA is
  still re-stated from the request (no store), so the resolve-not-restate rule
  for the stage 9 launch QA remains open. Execution now has its first
  application and infrastructure layers; the launch QA store will extend them in
  the same shape (nests the completed funnel).
- Blockers: `frontend/` (DoD condition 6, Q32) is blocked on the workflow engine
  Q5 via Q15; request idempotency (Q16) blocked on the same; RLS is a WHERE clause
  only (ADR 0004); no durable launch-QA store; the condition 3 retrieval,
  background worker and artifact-URL layers are unbuilt; the remaining canon gap
  register entries need named-owner decisions.
- Highest priority ready next item: apply the same resolve-not-restate rule to
  the stage 9 `LaunchQA` -- a durable launch-QA store (port, mapper, migration and
  adapter in the Execution context) so the stage 10 gate grounds on the exact
  ready-for-traffic stage 9 QA instead of a re-stated request body (SPEC.md
  sections 3, 4; DoD condition 1). Stage 9 "QA"; required asset: the approved
  `LaunchQA` at "Launch Approved"; approver: the designated human authority;
  blocked downstream dependency: the stage 10 Performance Baseline Established
  gate. Prerequisite: none beyond the method, offer, message, amplifier and
  funnel stores now in place. The QA nests the completed stage 8
  `FunnelIntegration`, so its mapper will reuse the funnel mapper. Alternative
  gate-integrity item: wire the implemented canon assets as required gate kinds
  (Q28) -- larger, changes the stage asset packages and routes. Canon gap
  register unchanged this cycle; no new gap identified.

### Prior cycle (2026-10-03T180150Z)

- Cycle 2026-10-03T180150Z (Ralph cycle): selected item was the durable
  `AuthorityAmplifierRepository` for the Production context (port, mapper,
  migration and PostgreSQL adapter) plus the resolve-not-restate rule for the
  stage 8 to 10 gates, the exact next item the prior cycle named (SPEC.md
  sections 3, 4, 6 and 9; queue Q6). The stage 8 to 10 routes re-stated the
  approved stage 7 amplifier from the request body, so a later gate could
  silently declare a different amplifier after the stage 7 "Authority Amplifier
  Approved" checkpoint (script approval then creative acceptance). It outranked
  the Next.js `frontend/` shell (DoD 6, blocked on the workflow engine Q5 via
  Q15), the larger required-kind wiring (Q28, which changes every stage's asset
  package and route) and the stage 8 funnel store (the next re-stated asset after
  the amplifier). The loop prioritizes exact approved asset versions and
  persistence over downstream features.
- Outcome: new Production application port `AuthorityAmplifierRepository`
  (`backend/redops/contexts/production/application/ports.py`) and a new Production
  `infrastructure` layer (`mappers.py`, `repositories.py`) mirroring the
  Commercial stores. `authority_amplifier_to_payload`/`..._from_payload`
  round-trip the full approved amplifier (state, pinned stage 6 `CampaignMessage`
  via the Commercial `campaign_message...` helpers, the canonical six-section
  script in order, the proof claim ids, the complete `VisualProductionPackage`
  and both distinct approvals), so the amplifier cannot drift from the message
  shape and a reload re-validates through `AuthorityAmplifier.__post_init__`.
  `InMemoryAuthorityAmplifierRepository` and
  `PostgresAuthorityAmplifierRepository` refuse an amplifier without creative
  acceptance (`AuthorityAmplifierReadinessError`), a same-id different-body
  re-statement (`AuthorityAmplifierVersionConflictError`) and a blank tenant
  (`AuthorityAmplifierVersionTenantBoundaryError`). Migration
  `0006_authority_amplifiers` creates `authority_amplifiers(id, tenant_id NOT
  NULL, amplifier_id, amplifier JSONB, recorded_at, UNIQUE(tenant_id,
  amplifier_id))`. `api/routes.py::get_authority_amplifier_repository` is an
  env-selected generator like the method, offer and message stores, and
  `_approve_authority_amplifier(..., amplifier_repository=)` now resolves the
  amplifier: the stage 7 gate stores the approved candidate, a later gate reuses
  the stored amplifier, a different same-id body is refused (422). All four stage
  7 to 10 routes take the new dependency.
- Evidence: `make check` -> 1860 passed, 1 skipped, 652 subtests; pyflakes clean.
  New `tests/unit/production/test_authority_amplifier_repository.py` (7 plus 3
  mapper tests) and `test_authority_amplifier_postgres.py` (8, against the
  compose DB, exercising the real migration), a stage 8 re-statement refusal test
  in `tests/unit/test_stage_eight_gate_route.py`, an app-smoke amplifier-dep
  default test, and `tests/unit/shared/test_migrate.py` head now
  `0006_authority_amplifiers`. The stage 7 to 10 route tests thread the amplifier
  dep override and the e2e reuses them. `make done` clears [1/6]-[4/6] and still
  fails at [5/6] (`frontend/` missing).
- New findings: the durable amplifier store now satisfies DoD condition 4 for
  `AuthorityAmplifier`; the stage 7 amplifier is tenant-scoped, immutable and
  shared across processes, and stage 8 to 10 ground on it. The stage 8 funnel and
  stage 9 launch QA are still re-stated from the request (no store), so the
  resolve-not-restate rule for the stage 8 funnel remains open. Production now
  has its first application and infrastructure layers; the funnel and launch QA
  are Execution aggregates, so their stores will introduce Execution
  application/infrastructure layers in the same shape.
- Blockers: `frontend/` (DoD condition 6, Q32) is blocked on the workflow engine
  Q5 via Q15; request idempotency (Q16) blocked on the same; RLS is a WHERE clause
  only (ADR 0004); no durable funnel or launch-QA store; the condition 3
  retrieval, background worker and artifact-URL layers are unbuilt; the remaining
  canon gap register entries need named-owner decisions.
- Highest priority ready next item: apply the same resolve-not-restate rule to
  the stage 8 `FunnelIntegration` -- a durable funnel store (port, mapper,
  migration and adapter in the Execution context) so the stage 9 and 10 gates
  ground on the exact completed stage 8 funnel instead of a re-stated request
  body (SPEC.md sections 3, 4; DoD condition 1). Stage 8 "Integrate"; required
  asset: the approved `FunnelIntegration` at "Funnel Complete"; approver: the
  client designated authority; blocked downstream dependency: the stage 9 Launch
  Approved gate. Prerequisite: none beyond the method, offer, message and
  amplifier stores now in place. The funnel nests the approved stage 7
  `AuthorityAmplifier`, so its mapper will reuse the amplifier mapper. Alternative
  gate-integrity item: wire the implemented canon assets as required gate kinds
  (Q28) -- larger, changes the stage asset packages and routes. Canon gap
  register unchanged this cycle; no new gap identified.

### Prior cycle (2026-10-03T175842Z)

- Cycle 2026-10-03T175842Z (Ralph cycle): selected item was the durable
  `CampaignMessageRepository` for the Commercial context (port, mapper, migration
  and PostgreSQL adapter) plus the resolve-not-restate rule for the stage 7 to 10
  gates, the exact next item the prior cycle named (SPEC.md sections 3, 4, 6 and
  9; queue Q6). The stage 7 to 10 routes re-stated the approved stage 6 message
  from the request body, so a later gate could silently declare a different
  message after the stage 6 "Campaign Message Approved" checkpoint. It outranked
  the Next.js `frontend/` shell (DoD 6, blocked on the workflow engine Q5 via
  Q15), the larger required-kind wiring (Q28, which changes every stage's asset
  package and route) and the stage 7 amplifier store (the next re-stated asset
  after the message). The loop prioritizes exact approved asset versions and
  persistence over downstream features.
- Outcome: new Commercial application port `CampaignMessageRepository`
  (`backend/redops/contexts/commercial/application/ports.py`);
  `campaign_message_to_payload`/`campaign_message_from_payload` in the Commercial
  mapper round-trip the full approved message (state, pinned `MethodReference`,
  all twelve canonical message parts and the nested grounding `OfferVersion`,
  serialised through the existing `offer_to_payload`/`offer_from_payload` helpers
  so the two shapes cannot drift). `InMemoryCampaignMessageRepository` and
  `PostgresCampaignMessageRepository` refuse a non-approved message
  (`CampaignMessageReadinessError`), a same-id different-body re-statement
  (`CampaignMessageVersionConflictError`) and a blank tenant
  (`CampaignMessageVersionTenantBoundaryError`). Migration
  `0005_campaign_messages` creates `campaign_messages(id, tenant_id NOT NULL,
  message_id, message JSONB, recorded_at, UNIQUE(tenant_id, message_id))`.
  `api/routes.py::get_campaign_message_repository` is an env-selected generator
  like the method and offer stores, and `_approve_method_offer_message` now
  resolves the message: the first gate stores the approved candidate, a later gate
  reuses the stored message, a different same-id body is refused (422). All five
  stage 6 to 10 routes take the new dependency.
- Evidence: `make check` -> 1840 passed, 1 skipped, 650 subtests; pyflakes clean.
  New `tests/unit/commercial/test_campaign_message_repository.py` (7 plus 3
  mapper tests) and `test_campaign_message_postgres.py` (8, against the compose
  DB, exercising the real migration), a stage 6 re-statement refusal test in
  `tests/unit/test_stage_six_gate_route.py`, an app-smoke message-dep default
  test, and `tests/unit/shared/test_migrate.py` head now `0005_campaign_messages`.
  The stage 7 to 10 route tests thread the message dep override. `make done`
  clears [1/6]-[4/6] and still fails at [5/6] (`frontend/` missing).
- New findings: the durable message store now satisfies DoD condition 4 for
  `CampaignMessage`; the stage 6 message is tenant-scoped, immutable and shared
  across processes, and stage 7 to 10 ground on it. The Authority Amplifier, the
  funnel and launch QA are still re-stated from the request (no store), so the
  resolve-not-restate rule for the stage 7 amplifier remains open. The offer
  store and the message store both nest one aggregate inside another (the message
  payload embeds the offer) and both round-trip through the same mapper helpers.
- Blockers: `frontend/` (DoD condition 6, Q32) is blocked on the workflow engine
  Q5 via Q15; request idempotency (Q16) blocked on the same; RLS is a WHERE clause
  only (ADR 0004); no durable amplifier, funnel or launch-QA store; the condition
  3 retrieval, background worker and artifact-URL layers are unbuilt; the
  remaining canon gap register entries need named-owner decisions.
- Highest priority ready next item: apply the same resolve-not-restate rule to
  the stage 7 `AuthorityAmplifier` -- a durable amplifier store (port, mapper,
  migration and adapter) so the stage 8 to 10 gates ground on the exact approved
  stage 7 amplifier (its dual script-before-visual approval) instead of a
  re-stated request body (SPEC.md sections 3, 4; DoD condition 1). Stage 7
  "Authority Amplifier"; required asset: the approved `AuthorityAmplifier`
  (checkpoint "Authority Amplifier Approved"; approver: script and creative
  authorities per canon 21); blocked downstream dependency: the stage 8 Funnel
  Complete gate. Prerequisite: none beyond the method, offer and message stores
  now in place. The amplifier nests the approved `CampaignMessage` and the
  approved method, so its mapper will reuse the message and method mappers.
  Alternative gate-integrity item: wire the implemented canon assets as required
  gate kinds (Q28) -- larger, changes the stage asset packages and routes. Canon
  gap register unchanged this cycle; no new gap identified.

### Prior cycle (2026-10-03T175505Z)

- Cycle 2026-10-03T175505Z (Ralph cycle): selected item was the durable
  `OfferVersionRepository` for the Commercial context (port, mapper, migration and
  PostgreSQL adapter) plus the resolve-not-restate rule for the stage 6 to 10
  gates, the exact next item the prior cycle named (SPEC.md sections 3, 4, 6 and
  9; queue Q6). The stage 6 to 10 routes re-stated the production ready stage 5
  offer from the request body, so a later gate could silently declare a different
  offer after the stage 5 "Offer Locked" checkpoint. It outranked the Next.js
  `frontend/` shell (DoD 6, blocked on the workflow engine Q5 via Q15) and the
  larger required-kind wiring (Q28, which changes every stage's asset package and
  route). The loop prioritizes exact approved asset versions and persistence over
  downstream features.
- Outcome: new Commercial application port `OfferVersionRepository`
  (`backend/redops/contexts/commercial/application/ports.py`); the Commercial
  infrastructure layer is split into `mappers.py` and `repositories.py`.
  `offer_to_payload`/`offer_from_payload` round-trip the full production ready
  offer (state, pinned `MethodReference` tuple and the complete stage 5
  `DeliverySpecification` including the locked Signature Solution, serialised via
  new public `signature_solution_to_payload`/`..._from_payload` helpers in the
  Method mapper). `InMemoryOfferVersionRepository` and
  `PostgresOfferVersionRepository` refuse a non-production-ready offer
  (`OfferReadinessError`), a same-id different-body re-statement
  (`OfferVersionConflictError`) and a blank tenant
  (`OfferVersionTenantBoundaryError`). Migration `0004_offer_versions` creates
  `offer_versions(id, tenant_id NOT NULL, offer_id, offer JSONB, recorded_at,
  UNIQUE(tenant_id, offer_id))`. `api/routes.py::get_offer_version_repository` is
  an env-selected generator like the method store, and
  `_approve_method_offer_message` now resolves the offer: the first gate stores
  the approved candidate, a later gate reuses the stored offer, a different
  same-id body is refused (422).
- Evidence: `make check` -> 1820 passed, 1 skipped, 648 subtests; pyflakes clean.
  New `tests/unit/commercial/test_offer_version_repository.py` (9 plus mapper
  tests) and `test_offer_version_postgres.py` (8, against the compose DB,
  exercising the real migration), a stage 6 re-statement refusal test in
  `tests/unit/test_stage_six_gate_route.py`, an app-smoke offer-dep default test,
  and `tests/unit/shared/test_migrate.py` head now `0004_offer_versions`. The
  stage 7 to 10 route tests thread the offer dep override. `make done` clears
  [1/6]-[4/6] and still fails at [5/6] (`frontend/` missing).
- New findings: the durable offer store now satisfies DoD condition 4 for
  `OfferVersion`; the stage 5 offer is tenant-scoped, immutable and shared across
  processes, and stage 6 to 10 ground on it. `CampaignMessage`, the Authority
  Amplifier, the funnel and launch QA are still re-stated from the request (no
  store), so the resolve-not-restate rule for the stage 6 message remains open.
  The offer store keys on `(tenant, offer_id)` because `OfferVersion` carries no
  separate version field; a change is a new revision with a new id.
- Blockers: `frontend/` (DoD condition 6, Q32) is blocked on the workflow engine
  Q5 via Q15; request idempotency (Q16) blocked on the same; RLS is a WHERE clause
  only (ADR 0004); no durable message, funnel or launch-QA store; the condition 3
  retrieval, background worker and artifact-URL layers are unbuilt; the remaining
  canon gap register entries need named-owner decisions.
- Highest priority ready next item: apply the same resolve-not-restate rule to the
  stage 6 `CampaignMessage` -- a durable message store (port, mapper, migration and
  adapter) so the stage 7 to 10 gates ground on the exact approved stage 6 message
  instead of a re-stated request body (SPEC.md sections 3, 4; DoD condition 1).
  Stage 6 "Message"; required asset: the approved `CampaignMessage` (gate
  "Campaign Message Approved"; approver: the client designated authority);
  blocked downstream dependency: the stage 7 Authority Amplifier dual approval.
  Prerequisite: none beyond the method and offer stores now in place. Alternative
  gate-integrity item: wire the implemented canon assets as required gate kinds
  (Q28) -- larger, changes the stage asset packages and routes. Canon gap register
  unchanged this cycle; no new gap identified.

### Prior cycle (2026-10-03T175228Z)

- Cycle 2026-10-03T175228Z (Ralph cycle): selected item was the
  durable PostgreSQL `MethodVersionRepository` plus mapper, migration and
  factory, the exact next item the prior cycle named (SPEC.md sections 3, 4, 6
  and 9; queue Q6). The prior cycle wired the resolve-not-restate rule but held
  the approved method store on the FastAPI `app.state`, so an approved method
  version did not survive a restart and was not shared across the API and worker
  processes. The stage 6 to 10 gates resolve the method a prior gate approved,
  so that approval must be durable. It outranked the Next.js `frontend/` shell
  (blocked on the workflow engine Q5 via Q15) and the larger required-kind
  wiring (Q28, which changes every stage's asset package and route). The loop
  prioritizes exact approved asset versions and persistence over downstream
  features.
- Outcome: new `backend/redops/contexts/method/infrastructure/mappers.py` with
  `method_to_payload`/`method_from_payload`, round-tripping the full aggregate
  (semantic version, `MethodApproval`, pinned `PrimaryCurrency`,
  `DiagnosticModel` with its levels, and `SignatureSolution` with its phases and
  steps) so a reload re-validates through `MethodVersion.__post_init__` rather
  than trusting storage. `method/infrastructure/repositories.py` gains
  `PostgresMethodVersionRepository` and
  `method_version_repository_from_env`, plus
  `MethodVersionConfigurationError`. Migration `0003_method_versions` creates
  `method_versions(id, tenant_id NOT NULL, method_id, semantic_version, method
  JSONB, recorded_at, UNIQUE(tenant_id, method_id, semantic_version))`.
  `api/routes.py::get_method_version_repository` is now an env-selected
  generator (like the gate ledger and stage run deps), so a set-but-unusable
  `DATABASE_URL` raises instead of silently using the process-local store.
- Evidence: `make check` -> 1800 passed, 1 skipped, 646 subtests; pyflakes
  clean. New `tests/unit/method/test_method_version_postgres.py` (8, against the
  compose DB; they exercise the real migration), new `MethodVersionMapperTests`
  in `tests/unit/method/test_method_version_repository.py` (3), an updated
  `tests/unit/shared/test_migrate.py` head assertion (`0003_method_versions`),
  and a method-dep default test in `tests/unit/test_app_smoke.py`. The stage 6
  to 10 route tests now override the method dependency with a fresh in-memory
  adapter so they stay DB-independent. `make done` clears [1/6]-[4/6] and still
  fails at [5/6] (`frontend/` missing).
- New findings: the durable method store now satisfies DoD condition 4 for
  `MethodVersion`; the tenant boundary and immutability rules are proven against
  real PostgreSQL. `OfferVersion` and `CampaignMessage` are still re-stated from
  the request (no offer/message store), so the resolve-not-restate rule for the
  stage 5 offer remains open. The stage 6 to 10 route docstrings still describe
  the old re-statement behavior for the offer and message and should be updated
  when those stores land.
- Blockers: `frontend/` (DoD condition 6, Q32) is blocked on the workflow engine
  Q5 via Q15; request idempotency (Q16) is blocked on the same; RLS is still a
  WHERE clause only (ADR 0004); no durable offer, funnel or launch-QA store; the
  condition 3 retrieval, background worker and artifact-URL layers are unbuilt;
  the remaining canon gap register entries need named-owner decisions.
- Highest priority ready next item: apply the same resolve-not-restate rule to
  the stage 5 `OfferVersion` -- a durable offer store (port, mapper, migration
  and adapter) so the stage 6 to 10 gates ground on the exact approved stage 5
  offer instead of a re-stated request body (SPEC.md sections 3, 4; DoD condition
  1). Prerequisite: none beyond the method store now in place. Alternative
  gate-integrity item: wire the implemented canon assets as required gate kinds
  (Q28) -- larger, changes the stage asset packages and routes.

### Prior cycle (2026-10-03T174702Z)

- Cycle 2026-10-03T174702Z (Ralph cycle, this run): selected item was the durable
  approved method version store, the gate-integrity item the prior cycles named as
  the next alternative to the dashboard work (SPEC.md sections 3, 4, 6 and 9).
  The stage 6 to 10 routes re-stated the approved method from the request body and
  trusted caller-supplied `approved_by`/`intended_use`/`approved_on`, so a later
  gate could silently declare a different method under an approved identity. It
  outranked the Next.js `frontend/` shell, whose queue dependency Q15 (the
  `/workflows/{id}` route) is unmet through the unbuilt workflow engine Q5, and
  the larger required-kind wiring (Q28, which changes every stage's asset package
  and route). The loop prioritizes exact approved asset versions over downstream
  features.
- Outcome: new Method application port `MethodVersionRepository`
  (`backend/redops/contexts/method/application/ports.py`) and reference adapter
  `InMemoryMethodVersionRepository`
  (`backend/redops/contexts/method/infrastructure/repositories.py`); two named
  errors `MethodVersionConflictError` and `MethodVersionTenantBoundaryError` in
  `method/domain/errors.py` (the store also refuses an unapproved draft with the
  existing `MethodApprovalError`). `api/routes.py` gains an app-state-scoped,
  overridable `get_method_version_repository` dependency, and
  `_approve_method_offer_message` now resolves the exact approved method by
  `(tenant, method id, semantic version)`: absent, it stores the approved
  candidate; identical, it reuses the stored version; a same-identity but
  different body raises `MethodVersionConflictError` (422). The five stage 6 to
  10 routes pass the repository through.
- Evidence: `make check` -> 1788 passed, 1 skipped, 646 subtests; pyflakes clean.
  New `tests/unit/method/test_method_version_repository.py` (7) and
  `test_re_stating_the_approved_method_with_different_content_is_refused` in
  `tests/unit/test_stage_six_gate_route.py`. `make done` clears [1/6]-[4/6] (per
  cycle check, stage 0-10 e2e, cross-tenant security, vendor clean) and still
  fails at [5/6] (`frontend/` missing).
- New findings: this is a port-first slice. The reference adapter is held on the
  FastAPI `app.state`, so the immutability rule is live within one app instance
  and isolated per test app, but there is no durable PostgreSQL adapter or
  migration yet, so method versions do not survive a restart and `make check`
  without an override gets no cross-process durability. `OfferVersion` and
  `CampaignMessage` are still re-stated from the request (no offer/message store),
  so the same resolve-not-restate rule for the stage 5 offer remains open. The
  stage 6 to 10 route docstrings still describe the old re-statement behavior and
  should be updated when the store is fully wired.
- Blockers: `frontend/` (DoD condition 6, Q32) is blocked on the workflow engine
  Q5 via Q15; request idempotency (Q16) is blocked on the same; RLS is still a
  WHERE clause only (ADR 0004); no durable offer, funnel or launch-QA store; the
  condition 3 retrieval, background worker and artifact-URL layers are unbuilt;
  the remaining canon gap register entries need named-owner decisions.
- Highest priority ready next item: extend the same store -- add the PostgreSQL
  `MethodVersionRepository` adapter plus a migration (mirroring the gate ledger
  and stage run adapters), then apply the resolve-not-restate rule to
  `OfferVersion` so the stage 6 to 10 gates ground on the exact approved stage 5
  offer (SPEC.md sections 3, 4; DoD condition 1). Prerequisite: none beyond the
  port and reference adapter now in place. Alternative gate-integrity item: wire
  the implemented canon assets as required gate kinds (Q28) -- larger, changes the
  stage asset packages and routes.

### Prior cycle (2026-10-03T174319Z)

- Cycle 2026-10-03T174319Z (Ralph cycle): selected item was the
  Extract content plan (Commercial Design `ContentPlan`), the bounded slice named
  by the canon gap register entry "Extract" (SPEC.md section 12.5; canon files
  25, 27, 28). It outranked the Next.js `frontend/` shell (a downstream
  dashboard; the loop prioritizes gate integrity and canon method artifacts over
  downstream features) and the larger gate-integrity items (a durable
  `MethodVersion`/offer store, request idempotency Q16 whose queue dependency
  Q15/Q5 is unmet) because it is a ready, independently verifiable, canon-
  informed asset with no unmet dependency, and it closes an open content gap
  ahead of the stage 6 and stage 10 content operations the pipeline feeds.
- Outcome: new pure-domain `ContentPlan`, `ContentTheme`, `ContentIdea`,
  `ContentIdeaSource`, `ContentPlanChannel` and the `CONTENT_PLAN_CANON_REFERENCE`
  in `backend/redops/contexts/commercial/domain/value_objects.py`, plus five
  named errors (`InvalidContentPlanError`, `ContentPlanDependencyError`,
  `ContentPlanTenantBoundaryError`, `ContentPlanThemeError`,
  `ContentPlanObservationError`) in `commercial/domain/errors.py`. It encodes the
  Extract shape as value objects and invariants: ground on a same-tenant stage 4
  `SignatureSolution` and stage 2 `PrimaryCurrency`; extract ideas with a typed
  source (faq, problem, process, review_and_praise); every idea maps to a step the
  solution names and to a declared theme; each theme advances either the current
  or the desired measure of the one locked currency; unique theme and idea ids;
  the plan must build both an email and a social delivery; it binds a named owner,
  reports covered and missing steps, is a plan and is never an observation.
- Evidence: `make check` (`uv run pytest -q`) -> 1780 passed, 1 skipped, 644
  subtests passed; `uv run pyflakes backend tests` clean. New
  `tests/unit/commercial/test_content_plan.py` (22 tests). `make done` clears
  steps [1/6]-[4/6] (per-cycle check, stage 0-10 e2e, cross-tenant security,
  vendored tree clean) and still fails at [5/6] (`frontend/` missing).
- New findings: Extract is RED's own layer, not a numbered canon file (SPEC.md
  section 12.5), so its shape is extracted from the Content Blitz files 25, 27 and
  28 and the SPEC's own wording. `ContentPlan` is distinct from the existing
  `ContentRoadmap` (canon 26, 27): the roadmap maps solution steps to publishable
  topics with the Authority Amplifier beats, while the plan extracts ideas by
  source and currency-aligned theme and declares the email and social deliveries
  before the roadmap. Both are stage 6 planning assets; reconciling them into one
  flow is a bounded follow-up. Wiring `ContentPlan` into a required stage 6 gate
  kind remains a methodology-owner decision (SPEC.md section 12.5).
- Blockers: unchanged Tier 2 facts; the missing `frontend/` (DoD 5, condition 6)
  is still the next `make done` failure; request idempotency, RLS WHERE-clause
  only (ADR 0004) and no durable MethodVersion/offer/funnel/QA store remain; the
  condition 3 retrieval, worker and artifact-URL layers are unbuilt.
- Highest priority ready next item: the Next.js `frontend/` shell plus RED theme
  plus API client (queue Q32; SPEC.md sections 8 and 13 condition 6), the next
  `make done` failure. Prerequisites: the read API and the 0-10 route surface are
  done. Alternative gate-integrity items: build the durable `MethodVersion`/offer
  store so the gates stop re-stating upstream approvals; wire `ContentPlan` into
  the stage 6 gate as a required kind (a methodology-owner decision); or the
  idempotency key (Q16) when its Q15/Q5 workflow dependency lands.

### Prior cycle (2026-10-03T173909Z)

- Cycle 2026-10-03T173909Z (Ralph cycle): selected item was the
  client-authored enrollment process (`ClientProcess` in the Execution domain),
  the next bounded slice named by the canon gap register entry "Client process
  design" (SPEC.md sections 1 and 12.7; canon files 35-49). It outranked the
  Next.js `frontend/` shell (a downstream dashboard; the loop prioritizes gate
  integrity and canon method artifacts over downstream features) and a durable
  `MethodVersion`/offer store (a larger integrity item), because it is a product
  contract capability the canon now covers completely and it closes an open canon
  gap as an asset inside an existing stage, which is not a named-owner decision
  (SPEC.md section 12.5).
- Outcome: new pure-domain `ClientProcess`
  (`backend/redops/contexts/execution/domain/client_process.py`), a
  `ClientProcessReadinessPolicy` (`execution/domain/policies.py`) and five named
  errors (`ClientProcessError`, `InvalidClientProcessError`,
  `ClientProcessDependencyError`, `ClientProcessTenantBoundaryError`,
  `ClientProcessObservationError`). It encodes SPEC.md section 12.7's required
  shape: the six canon parts in order (frame, discover problems, prescription,
  application, invitation, objection crusher), the five pass-or-fail checkpoints
  in order (intent, commitment, value, confidence, desire) each with the client's
  own question and fail action, the acceptance and rejection line (both required,
  no overlap), at least one answered objection, the typed strategy-session model
  (single call, fast track, paid strategy session), a positive price floor,
  pre-call homework drawing on a named method step with a booking window inside
  the canon's 72 hours, and duplicate-free no-show rules. It is grounded on the
  same-tenant stage 2 currency, stage 3 model, stage 4 Signature Solution and
  stage 5 product program, refuses an author approving their own process and is
  never an observation. The readiness policy refuses a process whose stage 5
  program does not deliver every method step.
- Evidence: `make check` (`uv run pytest -q`) -> 1758 passed, 1 skipped, 632
  subtests; pyflakes clean. New `tests/unit/execution/test_client_process.py` (28
  tests). Domain suite `PYTHONPATH=backend python3 -m unittest discover -s tests`
  -> 1680 run, OK (28 skipped).
- New findings: the supplied canon (files 35-49) does carry the six part process
  and the five checkpoints SPEC.md section 12.6 previously recorded as missing.
  The earlier `EnrollmentPlan` (canon files 00/21, four medical stages, bound to
  one funnel) remains a distinct per-funnel call; `ClientProcess` is the client's
  own authored process. Both coexist; reconciling them is a bounded follow-up.
  SPEC.md section 12.7 lists five checkpoints (intent, commitment, value,
  confidence, desire) while the canon gates four named phases plus the problems
  phase (file 41) for value; the artifact carries the SPEC's five.
- Blockers: unchanged Tier 2 facts; the missing `frontend/` (DoD 5, condition 6)
  is still the next `make done` failure; request idempotency, RLS WHERE-clause
  only (ADR 0004) and no durable MethodVersion/offer/funnel/QA store remain; the
  condition 3 retrieval, worker and artifact-URL layers are unbuilt.
- Highest priority ready next item: the Next.js `frontend/` shell plus RED theme
  plus API client (queue Q32; SPEC.md sections 8 and 13 condition 6), the next
  `make done` failure, now that the canon process gap is closed. Prerequisites:
  the read API and the 0-10 route surface are done. Alternative: wire
  `ClientProcess` into the stage 8/9 gate as a required kind (a methodology-owner
  decision), reconcile `ClientProcess` with `EnrollmentPlan`, or build a durable
  `MethodVersion`/offer store so the gates stop re-stating upstream approvals.

### Prior cycle (2026-10-03T173628Z)

- Cycle 2026-10-03T173628Z (Ralph cycle, this run): selected item was the
  `tests/security` cross-tenant isolation suite, the next `make done` failure
  (step [3/6]) and SPEC.md section 13 condition 3. It outranked the
  `ClientProcess` canon gap (a methodology-owner decision) and a durable
  `MethodVersion`/offer store (a larger integrity item) because it is the
  machine-checkable next `make done` gate and it locks the tenancy boundary the
  spec makes non-negotiable (SPEC.md section 9; the canon has no authority over
  tenancy).
- Outcome: new `tests/security/` package with
  `tests/security/test_cross_tenant_isolation.py` (6 tests) driving the real
  FastAPI app over HTTP. It proves: (1) a client with the full 0-10 pipeline
  approved is invisible to another client's production-view read (0 approved
  gates, 0 approved assets, a non-null current stage); (2) a stage gate
  prerequisite is scoped per client, so one client's approvals never satisfy
  another's gate (a stage 1 gate is refused with `GateDecisionError` when the
  other tenant has no passing stage 0); (3) no gate decision leaks through
  another client's ledger; (4) no stage run leaks through another client's run
  store; (5) the repositories refuse a blank-tenant (unscoped) read with
  `CrossTenantGateError` / `CrossTenantStageRunError`; and (6) an unauthorized
  approver is rejected over the API with `GateApproverNotAuthorizedError` and no
  write (SPEC.md section 11, "unauthorized approval is rejected").
- Coverage finding and open gap: condition 3 names the API, retrieval,
  background worker and artifact URL layers, but only the API layer exists in the
  running platform (no retrieval port, worker entry point or artifact-serving
  route). The suite therefore covers the API layer and the plan records
  retrieval, worker and artifact URL as an open condition-3 gap to be covered
  when those seams are built (queue items Q5, Q15 and the artifact routes); the
  suite does not fake coverage it cannot exercise.
- Evidence: `uv run pytest tests/security -q` -> 6 passed. `make check` green:
  1730 passed, 1 skipped, 632 subtests; `pyflakes` clean. `make done` now clears
  steps [1/6]-[4/6] and fails at [5/6] (`frontend/` missing); the prior
  `make done` failed at [3/6].
- New findings: the chain of route tests reused as a fixture (established by the
  e2e cycle) also supplies the stage 0 and stage 1 payloads the security suite
  needs, so no new shared payload module was required. The vendored OpenExecutive
  tree is clean at step [4/6]. The API-boundary gate integrity limitation is
  unchanged: the caller still supplies upstream approval metadata because no
  durable read model is exposed.
- Blockers: Tier 2 facts unchanged; the missing `frontend/` (DoD 5, condition 6)
  is now the next `make done` failure, followed by the migration deployment and
  Atlas health (DoD 9); the condition 3 retrieval, worker and artifact-URL layers
  remain unbuilt; request idempotency, RLS WHERE-clause-only (ADR 0004) and no
  durable `MethodVersion`/offer/funnel/QA store remain.
- Highest priority ready next item: the Next.js `frontend/` shell plus RED theme
  plus API client (queue Q32; SPEC.md sections 8 and 13 condition 5), the next
  `make done` failure. Prerequisites: the section 8 screens need the read API,
  and the stage 0-10 route surface plus the production-view route are both done.
  Alternative: the `ClientProcess` design artifact from the canon gap register,
  if a methodology-owner decision is preferred; or a durable
  `MethodVersion`/offer store so the gates stop re-stating upstream approvals; or
  building the retrieval, worker and artifact-URL seams so condition 3 can be
  fully covered.

### Prior cycle (2026-10-03T173449Z)

- Cycle 2026-10-03T173449Z (Ralph cycle): selected item was the
  `tests/e2e` stage 0-10 suite that drives one client from intake to
  "Performance Baseline Established" through the REST API -- SPEC.md section 13
  definition-of-done condition 1 and the next highest priority ready item named
  by the prior cycle. The prior cycle had completed the canonical 0-10 gate write
  surface, so the only remaining `make done` failure gate integrity work could
  address was the missing e2e proof. It outranked the `ClientProcess` canon gap
  (a methodology-owner decision) and a durable `MethodVersion`/offer store (a
  larger integrity item), because condition 1 is the machine-checkable stop
  condition and the pipeline backbone proof.
- Outcome: new `tests/e2e/test_stage_zero_to_ten_e2e.py` (plus the
  `tests/e2e/__init__.py` package marker). It drives the real FastAPI app over
  HTTP: seeds stages 0 through 9 through their own routes via the stage 10 route
  test's shared payload chain, records stage 10 through
  `RecordStageTenGateHandler`, then reads the production-manager view back
  through `GetEngagementProductionViewHandler` and inspects the tenant-scoped
  `GateLedger`. It asserts all 11 stages are approved with no missing asset
  kinds, the production view reports 11 approved gates / 0 remaining and no
  current or next-approval stage (post-launch measurement, not completion), and
  every one of the eleven durable gate decisions pins a non-empty exact-version
  (version 1) asset set whose asset approvals are all approved. The stage 0-9
  payload builders are reused from `tests/unit/test_stage_ten_gate_route.py`
  (itself chained through the earlier stage route tests) so the e2e cannot drift
  from the pipelined upstream content. The HTTP boundary, application handlers,
  domain policies and tenant-scoped repository ports are real; only the outer
  infrastructure adapters are the in-memory reference implementations, so the
  suite is deterministic and database-free (the durable PostgreSQL adapter stays
  covered by `tests/unit/governance/test_gate_ledger_postgres.py`, DoD 4).
- Evidence: `uv run pytest tests/e2e -q` -> 1 passed. `make check` green: 1724
  passed, 1 skipped, 632 subtests; pyflakes clean. `make done` now clears step
  [2/6] and fails at step [3/6] (`tests/security` absent). The prior `make done`
  failed at [2/6].
- New findings: the e2e could reuse the unit route-test payload chain without a
  new shared module, confirming the existing DRY convention scales to the API
  level. The e2e proves gate integrity over the whole 0-10 surface, not just the
  final gate. The API-boundary integrity limitation is unchanged: the caller
  supplies upstream approval metadata because no durable read model is exposed.
- Blockers: Tier 2 facts unchanged; `tests/security` cross-tenant suite (DoD 3)
  is now the only remaining test-suite blocker, followed by the absent
  `frontend/` (DoD 5), the migration deployment step and Atlas health (DoD 9);
  request idempotency, RLS WHERE-clause-only (ADR 0004) and no durable
  MethodVersion/offer/funnel/QA store remain.
- Highest priority ready next item: the `tests/security` cross-tenant suite
  (SPEC.md sections 9 and 13 condition 3), the next `make done` failure: at
  minimum the API layer over the stage gate and production-view routes and the
  retrieval layer, with worker and artifact-URL coverage added as those seams
  exist. Prerequisites: the 0-10 route surface and the production-view read route
  (both done). Alternative: the `ClientProcess` design artifact from the canon
  gap register, if a methodology-owner decision is preferred; or a durable
  `MethodVersion`/offer store so the gates stop re-stating upstream approvals.

### Prior cycle (2026-10-03T173254Z)

- Cycle 2026-10-03T173254Z: selected item was the HTTP
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

### Canon expansion and C4 2026-10-06: re-read, gaps registered, loop reopened

- The reference canon (`canon/`) was re-read after the owner reported it may have
  been updated. It has grown to **151 transcripts**: the 48 numbered sessions
  (00-49) plus **103 transcripts in nine new series** (High Ticket Funnels, 14D
  HTCLF, Winning Webinar, Youtube Content, Live Sessions, High Ticket Course
  Launch, Perfect Offer, Certification, High Ticket Launch Accelerator), and it
  now ships RED-authored synthesis: `docs/` (the RED Method, the operations
  manual: playbooks, checklists, SOPs) and `internal/` (`corpus-map.md`,
  `canon-to-docs-map.md`, `stations.md`, `cadence.md`, `service-ops.md`,
  `ops-spec.md`). SPEC.md section 12 was already reconciled to this in commit
  `15ec87d`; this cycle reconciles the implementation plan.
- **Files 19 and 20 are no longer missing**: they arrived in the High Ticket
  Launch Accelerator series. The dedicated sales/enrollment training is supplied
  (35-49) and deepened. The **one genuine source gap left is the emailed
  follow-up and nurture source module**; only a synthesized playbook exists
  (`ops/playbooks/email-nurture.md`, from the 5P and 27-part nurture material).
  Requested from the license owner and recorded as an open decision.
- **New gaps registered** (see the Canon gap register and the new Canon gap
  backlog below): the Lead-magnet kit, the Authority-video kit, the Webinar kit
  (the scaled enrollment path), the Strategy-session kit, the Delivery ladder,
  the Partnership line and certification, and the Service-line artifacts
  (kickoff, module production, session guide, client scorecard, case study). All
  are to be implemented as bounded, tenant-scoped, versioned artifacts under the
  existing required-kind pattern.
- **Deploy follow-ups resolved or made actionable.** Both cockpit follow-ups the
  2026-10-05 deploy note left open were advanced:
  - `gitops/sealed/redop-postgres.yaml` was re-sealed with a URL-safe password
    (`8b55c47`) and is live: the cluster Secret `redop-postgres` now holds a hex
    password with no `/`. A sealing runbook was added (`214375d`).
  - The Gitea Actions DinD init container is live with a 4Gi memory limit
    (`98fc205`, `helm/values/gitea-actions.yaml`); `kubectl` confirms
    `initContainers[name=dind].resources.limits.memory=4Gi`. The Argo CD
    `gitea-actions` Application still reports `OutOfSync` from API-defaulted
    StatefulSet fields, but its actual DinD limit matches Git. Added
    `NODE_OPTIONS=--max-old-space-size=3072` to the cockpit build stage for
    additional headroom. `docker build -f Dockerfile.cockpit` passed locally;
    the next hosted CI run is the remaining confirmation. The `gitea-actions`
    Application reports `OutOfSync` despite its live DinD limit matching Git.
- **R1 and R2 deferred** (owner): the backup/restore drill and the GitOps
  rollback drill move behind the canon-gap backlog and C4. They are not
  prototype conditions and remain in the production-readiness phase.
- **Loop reopened:** `.ralph/DONE` is removed so the build loop resumes against
  the Canon gap backlog, the remaining implementation items, and C4. The
  prototype definition of done still passes (`make done`); this is post-prototype
  work and is explicitly not a prototype condition.

# Spec: Asset review and approval in the cockpit

Status: proposed — 2026-10-10
Owner request: "I need those [stage assets] somehow in the UI for me to actually
approve them or review what has been approved in the past."

## 1. Goal

Give the client-designated authority (the owner) two capabilities the cockpit
lacks today:

1. **Review** — for every asset pin shown in the client workspace
   (e.g. `access-checklist@v1`), see in one place what was approved: the
   approval records, the gate decision that pinned it (rationale, checkpoint
   evidence), and the asset's stored content where content exists.
2. **Act** — approve pending work from the UI: approve workflow runs that are
   waiting for approval, and record stage gates (submitting the stage's assets
   and approving them) for stages whose assets were never recorded.

## 2. Background facts this spec is built on (verified)

- Pins in the client workspace "Approved assets" column are
  `asset_id@v{version}` strings rendered by
  `vendor/openexecutive/packages/ui/src/components/operations/ClientWorkspaceOverview.tsx:23-26`
  from the production view's `approved_assets`. They are **already-approved**
  kind pins; the backend pins the canonical kind name as `asset_id`
  (`backend/redops/contexts/governance/domain/value_objects.py:694`).
- Approval provenance exists and is readable: `GET /red/approvals`
  (`routes.py:4669`) and `GET /red/decisions` (`routes.py:4607`). The UI never
  shows it per-asset.
- Content reality per asset kind:
  - Readable today: methods (`/red/methods`), offers (`/red/offers`),
    claims (`/red/claims`), launch QAs (`/red/launch-qas`),
    journeys (`/red/journeys`), sources, builds.
  - Stored but **write-only** (no GET route): campaign messages
    (`campaign_messages` table), authority amplifiers incl. script sections
    (`authority_amplifiers` table), funnel integrations (`funnel_integrations`
    table).
  - **Not persisted after the gate**: stage 0 intake assets (only the gate
    decision's approvals/rationale/evidence remain) and stage 1–4 typed assets
    (avatar, snapshot, awareness map, … — submitted in gate bodies, never
    stored in a readable repository).
- The cockpit UI is read-only: `redOperationsApi.ts` has only `redGet`; no
  mutation exists in any operations screen.
- Approval write paths that exist unused by the UI:
  - `POST /red/clients/{tenant_id}/workflows/{run_id}/approval` with
    `{actor, reason}` (`routes.py:3831`) — resumes a run whose gate is passed.
  - `POST /red/clients/{tenant_id}/stages/{n}/gate` for n=0..10
    (`routes.py:1301` … `:3430`) — records a full gate decision; the request
    embeds the stage's typed asset content.
- Authority model: `approver`/`actor` are strings validated against the
  workspace's persisted authority registry
  (`engagement/domain/policies.py:132-162`); self-approval is refused. The
  registry is readable via `GET /red/clients` (`routes.py:4026-4034`).
- Vendor constraint (ADR 0014): the `/operations/*` screens,
  `redOperationsApi.ts` and their tests are RED-added new files (free to
  modify); `navConfig.ts`/`AppShell.tsx` are RED-owned surfaces; everything
  else upstream is byte-locked. `scripts/check_vendor_additive.sh` must stay
  green.

## 3. User-visible behavior

### 3.1 Asset detail panel (client workspace)

- Every pin in a stage's "Approved assets" cell renders as a clickable
  control (button styled as the existing pin text; keyboard accessible).
- Clicking a pin opens a detail panel (in-page expandable panel or dialog;
  implementer picks one pattern and applies it consistently) showing, for that
  `asset_id`:
  1. **Approvals** — every record from `GET /red/approvals?tenant_id=…` with
     `asset_id` equal to the pin: version, scope, requested_by, approver,
     outcome, decided_on, expires_on, stage_number.
  2. **Gate decisions** — every decision from `GET /red/decisions?tenant_id=…`
     whose `required_assets` include the pin: stage_number, checkpoint,
     disposition, reviewer, scope, rationale, checkpoint evidence.
  3. **Content** — resolved through the kind→source mapping in §5:
     the tenant's entities of the matching group, each rendered with its
     identifying fields and full human-readable content (method narrative and
     diagnostic model, offer promise/eligibility/price, claim statements,
     message story/hook/angles/landing message, amplifier script sections and
     visual refs, funnel assets/routing). Entities whose approval state is
     approved are marked. Kinds with no content source show a fixed note:
     "No stored content for this asset kind — the approval records above are
     the record of what was approved."
- Loading and error states follow the screen's existing patterns; an empty
  approvals list renders an explicit "no approval records found" state, never
  a blank panel.

### 3.2 Approve a pending workflow run (approval inbox)

- In the approval inbox "Pending gate approvals" section, each waiting run
  gains an **Approve** control.
- Activating it opens a small form: **actor** (dropdown of the workspace's
  authorities from `GET /red/clients`, with free-text fallback) and
  **reason** (text, required).
- Submit calls `POST /red/clients/{tenant_id}/workflows/{run_id}/approval`
  with `{actor, reason}`. On success the screen refreshes and the run leaves
  the pending list. On domain refusal (e.g. the run's stage has no passing
  gate decision) the backend error message is rendered next to the form; no
  optimistic state changes.

### 3.3 Record a stage gate (client workspace)

- Each stage row gains a **Record gate** action. It is rendered for every
  stage 0–10; the backend remains the sole enforcer of prerequisites
  (dependencies, expiry, authority), and its errors are surfaced per §3.4.
- Activating it opens a schema-driven form built from a new backend endpoint
  (§4.2):
  - `GET /red/stages/{n}/gate-schema` returns the JSON Schema of that stage's
    `RecordStageNGateRequest` Pydantic model.
  - The form renders every schema property: labeled inputs (label derived
    from the field name), enums as selects, booleans as checkboxes, arrays of
    objects as add/remove row editors, nested objects one level deep.
  - Defaults prefilled where derivable: `workspace_id` = current workspace,
    `asset_id` = the required kind name for asset rows, `version` = 1,
    `on` = today, `stage_owner`/`assigned_owner`/`approver` = chosen from the
    workspace authorities, `proposed_by` distinct from `approver` (the domain
    refuses self-approval; the form warns when they match).
  - Submit calls `POST /red/clients/{tenant_id}/stages/{n}/gate` with the
    assembled body. On success the production view refreshes and the stage's
    new pins appear. On failure the backend error is rendered inline and no
    local state changes.

### 3.4 Error surfacing (both actions)

Domain validation failures (unauthorized approver, self-approval, missing or
mismatched assets, unmet dependencies, expired prerequisites) must render the
backend's error detail verbatim next to the offending form. The UI never
silently swallows a refusal and never re-implements approval rules.

## 4. Backend changes

### 4.1 Read endpoints for hidden content

New tenant-scoped list routes following the `_method_payload` pattern
(`routes.py:4339-4367`):

- `GET /red/messages?tenant_id=…` — the tenant's campaign messages with full
  content: `message_id`, owner, avatar, currency, problem, promise, cta,
  problem_hierarchy, desired_outcome, proof_objections, story,
  method_explanation, lead_magnet, hook, angles, landing_message,
  authority_amplifier_outline, product_offer_id, and any refs the aggregate
  carries.
- `GET /red/amplifiers?tenant_id=…` — the tenant's authority amplifiers:
  `amplifier_id`, method/offer references, script sections
  (`kind`, `content`), visual refs (storyboard, recording, edited_video,
  hosted_video, player assets, …), and approval state fields the aggregate
  exposes.
- `GET /red/funnels?tenant_id=…` — the tenant's funnel integrations: funnel
  id, the thirteen canonical asset references, routing (prospect-path dry
  run), and state flags the aggregate exposes. DEVIATION (accepted
  2026-10-10): `configuration_digest`, `rollback_ref` and `released_kinds`
  are NOT included — they belong to the `JourneyRelease` aggregate and are
  already served by `GET /red/journeys`; the `FunnelIntegration` aggregate
  does not carry them.
- Additionally, `GET /red/decisions` now includes `checkpoint_evidence`
  (backward-compatible addition) so §3.1 can render the gate's checkpoint
  evidence.

All three: unknown tenant → empty list (matching existing list-route
behavior); no cross-tenant rows ever; pagination parameters consistent with
sibling routes.

### 4.2 Gate schema endpoint

- `GET /red/stages/{n}/gate-schema` for n in 0..10 returns
  `RecordStageNGateRequest(n).model_json_schema()` (internal `$defs` allowed;
  the UI resolves them). Unknown n → 404. The returned schema must describe
  exactly the body `POST /red/clients/{tenant_id}/stages/{n}/gate` accepts.

## 5. Kind → content source mapping (authoritative for §3.1)

Derived from `governance/domain/templates.py:63-301`. Kinds not listed render
the provenance-only note.

| Kind group (template kinds) | Content source |
| --- | --- |
| `method`-group stage 3 kinds (`profit-pyramid-levels`, `observable-measures`, `level-symptoms`, `level-behaviors`, `level-problems`, `progression`, `qualification-logic`, `diagnostic-model-name`, `diagnostic-model-visual`, `diagnostic-model-copy`) | `/red/methods` (diagnostic model + signature solution) |
| stage 5 offer kinds (`delivery-model`, `duration`, `modules`, `responsibilities`, `support-cadence`, `stage-deliverables`, `outcome-measures`, `pricing-payments`, `scope`, `guarantee-decision`, `eligibility`, `offer-stack`, `product-program`) | `/red/offers` |
| stage 6 message kinds (`promise`, `problem-hierarchy`, `desired-outcome`, `proof-objections`, `story`, `method-explanation`, `cta`, `lead-magnet`, `hook`, `angles`, `landing-message`, `authority-amplifier-outline`, `content-roadmap`, `content-crusher`, `content-plan`) | `/red/messages` (new) |
| stage 7 amplifier kinds (`authority-amplifier-script`, `aa-storyboard`, `brand-treatment`, `aa-presentation`, `aa-speaker-notes`, `aa-recording`, `aa-edited-video`, `aa-hosted-video`, `aa-player-assets`) | `/red/amplifiers` (new) |
| stage 8 funnel kinds (`campaign-architecture`, `pages`, `forms`, `qualification`, `booking`, `sequences`, `crm`, `tags`, `automation`, `analytics`, `tracking`, `sales-handoff`, `sops`, `swimlanes-plan`) | `/red/funnels` (new) |
| stage 9 QA kinds (`recorded-message`, `technical-tests`, … `compliance-package`) | `/red/launch-qas` |
| stage 10 measurement kinds (`live-campaign`, `spend-records`, …) | `/red/measurements` |
| stage 1 diagnose kinds, stage 2 position kinds, stage 0 intake kinds | none — provenance only |

ASSUMPTION: pin→entity linkage is by kind group plus approval state; gate
decisions do not record content entity ids, so where a tenant holds several
entities of a group the panel lists them all with approved ones marked. A
durable pin→entity reference is a follow-up, not this spec.

## 6a. Addendum (2026-10-10): definitive per-stage content truth

Owner requirement: state clearly per artifact whether text content exists in
the platform, and make every piece of stored content readable in the UI.
Persistence trace of the stage 0-4 gate routes (validate-and-decide: they
build typed packages, validate, append a `GateDecision`, upsert a `StageRun`):

| Stage | Submitted content | In durable storage? | Readable before this addendum |
| --- | --- | --- | --- |
| 0 Intake (the 12 kinds) | intake asset summaries, owners, evidence refs | **NO — discarded after validation**; only approval refs + rationale + checkpoint evidence persist | provenance only (correct) |
| 1 Diagnose | avatar, business snapshot, funnel audit, awareness map, reach estimate, market match | **NO — discarded** | provenance only (correct) |
| 2 Position | currency package | **NO at gate time**; survives only via the stage 6-10 `method` field → `method_versions.method` | `primary-currency` stored full but exposed as a string only |
| 3 Model | diagnostic model | **NO at gate time**; survives via stage 6-10 `method` field | stored full but exposed as an id only |
| 4 Package IP | signature solution / transformation map | survives via stage 6-10 `method`/`offer.delivery.signature_solution` | readable (`/red/methods`, TransformationMap) but not mapped in the panel |
| 5 Productize | offer + full delivery specification | YES (`offer_versions.offer`) | delivery spec not exposed by `/red/offers` |
| 6-10 | message / amplifier / funnel / QA / measurements | YES | readable (this spec's §4.1) |

Gaps closed by this addendum (stored but unreadable):

- **M1** `GET /red/methods` exposes the FULL stored `primary_currency` object
  (currency, version, audience, current_measure, desired_measure, mechanism)
  and the FULL stored `diagnostic_model` (model_id, version, name, levels with
  observable_measures/symptoms/behaviors/problems, progression,
  qualification_logic, visual, explanatory_copy) — additive fields, mirroring
  `method/infrastructure/mappers.py:238-275`.
- **M2** `GET /red/offers` exposes the FULL stored `delivery` specification
  (delivery_model, duration, modules, responsibilities, support_cadence,
  step_deliveries, outcome_measures, pricing_payments, scope,
  guarantee_decision, eligibility, offer_stack, signature_solution) —
  mirroring `commercial/infrastructure/mappers.py:92-115`.
- **M3** Panel mapping fix: stage 3 kinds → methods (diagnostic model), stage 4
  kinds → methods (signature solution), stage 2 `primary-currency` → methods
  (primary currency). The other stage 2 kinds stay provenance-only — their
  content is genuinely not stored. Method/offer renderers render the new
  sections.

Stage 0 and 1 content remains non-existent in the platform (nothing to
render); persisting it at gate time is a separate follow-up requiring new
tables and write-path changes, not part of this spec.

## 6. Non-goals

- No HTTP authentication layer or authenticated-user→actor binding (existing
  posture: same-origin cockpit + authority-registry validation).
- No object storage / artifact bytes (SPEC §3 stays future work).
- Persisting stage 0–4 asset content after the gate (new tables + write-path
  changes) — follow-up spec if wanted.
- Editing or revising approved assets (domain immutability stands).
- Spend approvals, publishing, deployment (never platform actions).
- Visual design polish beyond consistent use of existing screen patterns.

## 7. Acceptance criteria

Backend (pytest, `uv run pytest`):

- **B1** `GET /red/messages?tenant_id=T` returns the tenant's messages with
  the content fields of §4.1; unknown tenant → empty list; a second tenant's
  messages never appear (extend `tests/security/test_cross_tenant_isolation.py`).
- **B2** Same for `/red/amplifiers` (script sections with kind+content and
  visual refs present) and `/red/funnels` (asset refs, routing, digest).
- **B3** `GET /red/stages/{n}/gate-schema` returns a schema for each n=0..10
  whose properties match that stage's request model; unknown n → 404; a
  payload valid per the schema is accepted by the stage's Pydantic request
  model (round-trip test).
- **B4** New routes follow existing tenant-scoping and are covered by tests
  mirroring `tests/unit/governance/test_governance_read_routes.py`.

Cockpit UI (vitest, `tests/cockpit-ui/`):

- **U1** Clicking a pin in the client workspace opens the detail panel
  showing that asset's approvals and decisions (asserted from mocked API
  data) and, for a kind with a content source, the matching content; for a
  kind without one, the provenance-only note.
- **U2** The approval inbox renders an Approve control per pending run; the
  dialog collects actor + reason; submitting calls the workflow approval
  endpoint with exactly `{actor, reason}`; a backend refusal renders its
  error message; a success refreshes the pending list.
- **U3** The client workspace renders a Record gate action per stage; the
  form fetches the stage schema and renders inputs for its properties; for
  each stage 0–10, assembling the form with the equivalent of that stage's
  `seed.py` payload produces a POST body Pydantic-equal to it (the seed
  payloads are the fixtures).
- **U4** A domain refusal from either action renders the backend error
  inline and records nothing.
- **U5** `scripts/check_vendor_additive.sh` passes (only RED-owned/new files
  touched).

Integration gate: `make check` passes; `cd tests/cockpit-ui && npx vitest
run` passes.

## 8. Verification plan

1. Backend: new/updated pytest files green; `make check` green.
2. UI: new vitest suites green; existing `operationsScreens*.test.tsx`
   untouched suites still green.
3. Vendor gate: `scripts/check_vendor_additive.sh` green.
4. Manual smoke (optional, local): `make seed` against Postgres, run the API
   and cockpit, open `/operations/client-workspace`, click
   `access-checklist@v1`, verify provenance panel; record a stage gate on a
   fresh workspace; approve a pending workflow run.

## 9. Rollback

All changes are additive (new routes, new UI components, additions to
RED-owned/new files). Reverting the feature commits restores prior behavior;
no migrations are required (no schema changes).

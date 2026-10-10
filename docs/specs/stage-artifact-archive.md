# Spec: Stage artifact archive and sequence-based review

Status: proposed — 2026-10-10
Owner direction: "The platform is supposed to act as the collection and
archiving source for every artifact of every stage. I absolutely want space
for these artifacts to be dropped as text markdown format compatible." And:
review "falls in the sequence of the stations and the production order" — if
the date selector is in the way, "reconsider the functionality or just remove
the date picker."

This spec supersedes the follow-up note in
`docs/specs/asset-review-and-approval-ui.md` §6a about persisting stage 0-2
content at gate time: the archive below is the mechanism, and it is
stage-wide rather than gate-coupled.

## 0. Product principle (recorded)

The platform is the collection and archiving source for every artifact of
every stage. Collection (dropping an artifact) and approval (recording a
gate) remain separate acts — "work done is not the same as work approved"
(SPEC.md §1). Review surfaces organize by stage sequence, not by calendar
date.

## 1. Part A — the artifact archive (backend)

### 1.1 Aggregate

`StageArtifact` — new bounded context `backend/redops/contexts/archive/`
(domain value objects + entity, application port, infrastructure in-memory +
Postgres repositories and mappers), following the small-context patterns of
`commercial`/`knowledge`:

- `tenant_id` (from the request path, never the body)
- `workspace_id` (non-blank; must exist in the engagement workspace store)
- `stage_number` (0-10)
- `kind` (non-blank free text; the stage template's canonical kinds are
  offered as options in the UI but extra kinds are allowed — the archive
  collects everything)
- `asset_id` (non-blank; defaults to `kind` when omitted)
- `version` (positive integer; when omitted on create, the next free version
  for `(tenant_id, workspace_id, asset_id)`)
- `markdown` (non-blank TEXT — the artifact content itself)
- `owner` (non-blank; collection attribution, not domain-validated authority)
- `note` (optional)
- `dropped_on` (date; defaults to today)

Append-only: no update or delete path exists. Saving an identical
`(tenant_id, workspace_id, asset_id, version)` with identical content is an
idempotent success; the same key with different content raises a named
conflict (drop a new version instead) — the campaign-message repository
pattern (`commercial/infrastructure/repositories.py:287-304`).

### 1.2 Storage

Migration `0020_create_stage_artifacts` (typed columns, not a JSONB payload —
the fields are queried and rendered individually):

- columns: `tenant_id`, `workspace_id`, `stage_number`, `kind`, `asset_id`,
  `version`, `markdown TEXT`, `owner`, `note NULL`, `dropped_on`
- CHECKs: non-blank text fields, `stage_number BETWEEN 0 AND 10`,
  `version > 0`
- named UNIQUE `(tenant_id, workspace_id, asset_id, version)`
- index `(tenant_id, workspace_id, stage_number, kind, asset_id, version DESC)`
- reversible `downgrade()`

### 1.3 API

- `POST /red/clients/{tenant_id}/artifacts` → 201. Tenant from the path;
  workspace resolved through the engagement store (unknown → 404); domain
  validation errors → 422 with the named error; version conflict → 409.
  Body: `workspace_id`, `stage_number`, `kind`, `asset_id?`, `version?`,
  `markdown`, `owner`, `note?`, `dropped_on?`.
- `GET /red/clients/{tenant_id}/artifacts` → tenant-scoped list including
  full `markdown`, with optional filters `workspace_id`, `stage_number`,
  `kind`, `asset_id` and `limit`/`offset` pagination (sources-route pattern,
  `routes.py:4162-4197`). Sorted by stage, kind, asset, version DESC.

### 1.4 Seed

`make seed` adds demo artifacts for the 3fmindset pilot (e.g. `signed-scope`
and `intake-questionnaire` v1 with `Demo:`-marked markdown) through the real
API route, idempotent like the rest of the seed — so the example client shows
a populated archive.

## 2. Part B — sequence-based review (dates leave the review surfaces)

- Backend: the `on` query parameter becomes **optional with a default of
  today** on `GET /red/clients/{t}/engagements/{e}/production-view`
  (`routes.py:3739-3744`) and `GET /red/interventions` (`routes.py:5455-5465`).
  Expiry semantics are unchanged — an explicit `on` still works; omitting it
  evaluates the current instant.
- UI: remove the four date pickers (`CommandCenterScreen.tsx:57-62`,
  `ClientWorkspaceScreen.tsx:164-169`, `PerformanceReviewScreen.tsx:65-70`,
  `AuthoritySettingsScreen.tsx:58-63`); the screens call the API without
  `on`. The gate recording form keeps its decision-date field (prefilled
  today) — that records *when a gate was decided*, which is gate metadata,
  not a review filter.

## 3. Part C — the archive in the cockpit

- **Drop form**: each stage row in the client workspace gains an
  **Add artifact** action (beside Record gate) opening a form: kind (select
  of the stage's required kinds plus a custom entry), asset_id (defaults to
  kind), version (blank = next free), markdown textarea (the artifact text),
  owner (authority dropdown), optional note. Submit → POST; success refreshes
  the workspace data; backend refusals render verbatim; nothing is recorded
  on refusal.
- **Reading**: the asset detail panel lists the archived artifacts for the
  clicked `asset_id` (newest version first), each rendered as markdown via
  `react-markdown` + `remark-gfm` — the existing `MarkdownArticle` pattern
  (`vendor/openexecutive/packages/ui/src/components/ArtifactViewer.tsx:20-48`)
  with the `Message.tsx` URL-transform guard — headed by version, owner,
  dropped_on and note. No archived artifact → explicit empty state; the
  typed-content and provenance sections stay as they are.
- **API client**: `dropArtifact(...)` and `listArtifacts(...)` in
  `redOperationsApi.ts`.

## 4. Acceptance criteria

Backend (pytest):

- **A1** POST creates an artifact; omitted `asset_id` defaults to the kind;
  omitted `version` takes the next free version; identical replay succeeds;
  changed content at the same key → named 409; unknown workspace → 404;
  blank/invalid fields → 422; a body-supplied tenant cannot override the
  path tenant.
- **A2** GET returns only the querying tenant's artifacts with markdown
  included; filters (workspace, stage, kind, asset) work; pagination works;
  covered in `tests/security/test_cross_tenant_isolation.py`.
- **A3** production-view and `/red/interventions` answer **without** `on`
  (evaluated at today) and still honour an explicit `on`; existing tests
  updated, not weakened.
- **A4** Migration up/down round-trips; Postgres adapter tests prove
  append-only immutability, tenant isolation and blank-tenant refusal.
- **A5** Seed produces the demo artifacts idempotently.

Cockpit UI (vitest):

- **U1** The Add artifact form renders per stage, posts the expected body,
  refreshes on success, renders refusals verbatim and records nothing on
  refusal.
- **U2** The detail panel renders an archived artifact's markdown (headings,
  lists, bold render as markup), with version/owner/dropped_on/note
  metadata, newest first, and an explicit empty state when none exist.
- **U3** The four date pickers are gone; the screens fetch current data with
  no date param; all existing suites stay green.
- **U4** `scripts/check_vendor_additive.sh` stays green (no locked file
  touched — `react-markdown`/`remark-gfm` are already in the locked
  baseline).

Gates: `make check` (the single pre-existing canon-drift failure excepted),
`cd tests/cockpit-ui && npx vitest run`, vendor gate.

## 5. Non-goals

- File/blob uploads — markdown text only; the object store stays future work
  (SPEC §3).
- Editing or deleting archived artifacts (append-only by design).
- Auto-archiving typed gate content as markdown — stages 3-10 keep their
  typed stores; the archive is the markdown drop space, and both render in
  the panel.
- Gate approval of archived artifacts — gates are unchanged; pinning
  archived versions into a gate is a possible follow-up.
- Removing dates from the domain (expiry semantics stay; only the review
  surfaces stop asking).

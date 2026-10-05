# REST API

The API is a thin adapter over application use cases. All RED routes are under
`/red/*` and composed in `backend/redops/api/app.py`; the reused OpenExecutive
shell is mounted at `/openexecutive`. Domain rules live in the domain, not the
routes.

## Route surface

| Method + path | Purpose |
| --- | --- |
| `GET /red/health` | RED liveness (`{"status":"ok"}`). |
| `GET /red/stages` | The canonical stage 0-10 template (read-only reference data). |
| `POST /red/clients` | Create a `ClientWorkspace`. |
| `GET /red/clients` | Tenant-scoped paginated list. |
| `GET/POST /red/clients/{tenant_id}/sources` | `SourceRecord` ingest/list. |
| `GET/POST /red/clients/{tenant_id}/stages/{0..10}/gate` | Record a stage gate decision. |
| `GET /red/clients/{tenant_id}/engagements/{engagement}/production-view` | The production-manager view (what exists / is missing / is next). |
| `GET /red/clients/{tenant_id}/workflows/{run_id}` | Workflow run polling (stable event id). |
| `GET/POST /red/claims` | Grounded `Claim` list/create (citations verified against the tenant's sources). |
| `GET /red/methods` | Tenant-scoped paginated approved methods. |
| `GET /red/offers` | Tenant-scoped paginated offers. |
| `GET/POST /red/builds` | `BuildObject` list/create. |
| `GET /red/decisions` | The append-only gate decision ledger, canonical stage order. |
| `GET /red/approvals` | Version-specific `ApprovalRequest`s, flattened. |
| `GET/POST /red/measurements` | Metric definitions + observations (append-only). |
| `GET/POST /red/journeys` | `JourneyRelease` grounded on a stage 9 launch QA. |
| `GET/POST /red/launch-qas` | Stage 9 launch QA packages. |
| `GET /red/interventions` | Ranked command-center cards. |
| `POST /red/interventions/dismiss` | Record a durable operator dismissal. |
| `GET/POST /red/opportunities` | Portfolio opportunities (proposal-only). |

## Contract rules

- **Tenant is explicit.** Every read and write carries `tenant_id` (query param or
  path/body); an unscoped access is refused. This is the tenancy boundary
  (SPEC §9, ADR 0004).
- **Idempotency.** Mutations that can be retried accept a request identity /
  idempotency key; a duplicate creates one effect (see `IdempotentConnector`).
- **Optimistic versions.** A stale update returns `409 Conflict`.
- **Pagination.** List endpoints are paginated.
- **Named errors.** Missing or foreign resources return named `404`s (e.g.
  `ClientWorkspaceNotFoundError`), invalid payloads `422`, re-statements `409`.
- **Read models are projected, not authoritative.** `/decisions`, `/approvals`,
  `/offers`, `/methods`, `/launch-qas` are read-only projections over durable
  stores because approval is gate-owned; listing never grants authority.

## Schemas and tests

Request/response models are in `backend/redops/api/schemas.py`. Route behaviour is
covered by tests under `tests/unit/**/*_route.py`; the stage 0-10 e2e drives the
whole pipeline over HTTP with `TestClient` (`tests/e2e/`).

## Running locally

```sh
# with Postgres from docker-compose
docker compose up -d postgres
export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
uv run uvicorn redops.api.app:app --reload   # http://localhost:8000
# curl /red/health -> {"status":"ok"}
```

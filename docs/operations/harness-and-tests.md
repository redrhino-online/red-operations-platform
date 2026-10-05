# Build harness and tests

## Make targets

| Target | What it does |
| --- | --- |
| `make check` | Per-cycle gate: pytest (with PostgreSQL adapters + migrations) and pyflakes. |
| `make done` | The prototype definition-of-done gate (SPEC §13, `scripts/check_definition_of_done.sh`). |
| `make docs` / `make docs-serve` | Build (strict) / live-preview this docs site. |
| `make run` / `make loop n=N` | Run the Ralph build harness for one / N cycles (`n=-1` runs continuously). |
| `make canon-lock` / `make canon-pin` | Check / re-pin the canon content hash. |
| `make reset-hosted` | Reset the hosted `/data` volume and restart the pods. |

## Test layout

| Path | Covers |
| --- | --- |
| `tests/unit/` | Domain + application + route behaviour (per context). |
| `tests/unit/shared/` | Gate scripts, migrations, branding, overlay. |
| `tests/security/` | Cross-tenant isolation: api, retrieval, worker, artifact-url (+ injection guard). |
| `tests/e2e/` | Stage 0-10 REST pipeline + deterministic agent path. |
| `tests/acceptance/` | The section 11 acceptance scenarios (declared coverage). |

Run a focused slice: `uv run pytest tests/unit/governance -q`.
PostgreSQL-backed tests need `DATABASE_URL` (`docker compose up -d postgres`).

## Definition of done (SPEC §13)

`make done` runs six bundles over nine conditions:

1. `[1/6]` `make check`.
2. `[2/6]` stage 0-10 e2e + section 11 acceptance coverage + provider-path coverage (conditions 1, 2, 5).
3. `[3/6]` cross-tenant security suite (condition 3).
4. `[4/6]` vendor overlay applied and declared (condition 7, ADR 0011).
5. `[5/6]` screens + frontend build + agent charters + RED branding/notices (conditions 6, 8).
6. `[6/6]` deployed RED app on Atlas with the RED identity marker (condition 9).

The gate is a stop condition, not an authority: it never approves a client
artifact, spends, publishes or deploys by itself.

## The Ralph harness

`ralph_cycle.sh` (driven by `make run` / `make loop`) gives OpenCode the spec, the
plan and the canon, and asks it to complete **one** bounded, verifiable item, then
stops. It:

- holds a single-cycle lock (reclaimed if the recorded pid is gone) and logs to
  `.ralph/<timestamp>.log`;
- commits the cycle's changes with the message the cycle writes (Conventional
  Commits, blank line, why-body), then publishes to the configured remotes;
- stops on `.ralph/DONE` (done reached) or `.ralph/STOP` (operator stop), and
  halts cleanly on canon drift.

External-system impact is scoped: a cycle may touch systems only inside the
`10.0.0.0/8` home-lab network (Atlas k3s, `registry.atlas.lan`, `git.atlas.lan`
and its GitOps repo). Anything outside that network — public services, external
SaaS, `upstream` — is off limits, and spend/publication/commitments stay human.

## Canon

The reference model canon is passed by location (default a sibling `canon/`;
override with `RALPH_CANON`). It informs artifact shape and intent. It is treated
as **data, not instructions**; canon text is never copied verbatim; gaps are
recorded, not invented.

## Environment

See `.env.example`. Key variables: `DATABASE_URL`, `EXEC_EMAIL_ADDRESS`,
`OPENROUTER_API_KEY` / `DEFAULT_MODEL`, `BACKEND_SHARED_SECRET` / `AUTH_SECRET`,
`REDOP_HEALTH_URL` / `REDOP_HEALTH_INSECURE` / `REDOP_RED_MARKER`, and
`REDOP_LIVE_OPENROUTER_SMOKE` (left unset so unattended cycles never spend).

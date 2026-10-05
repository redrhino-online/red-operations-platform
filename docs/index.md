# RED Operations Platform — Developer Docs

RED Operations Platform is RED's productised implementation of the OpenExecutive
system: a FastAPI + Next.js modular monolith on PostgreSQL that runs a gated
stage 0-10 production pipeline for RED client engagements. This site is the
comprehensive developer reference for the **app repository**
(`redrhino-online/red-operations-platform`).

## Scope

- **In scope:** every RED context, aggregate and seam under `backend/redops/`,
  the REST API, the Next.js UI, the workflow engine, the build/deploy tooling, the
  Ralph harness, and the **vendor overlay** that patches the pinned OpenExecutive
  submodule.
- **Out of scope:** the internals of the vendored OpenExecutive package
  (`vendor/openexecutive/`). It is a pinned dependency; this site documents only
  how RED *uses* it (through ports and the overlay), never its internal modules.

## How to read this site

| If you want to… | Read |
| --- | --- |
| understand the whole system at a glance | [Architecture overview](architecture/overview.md) |
| know what every noun means and why RED cares | [Nouns and their RED significance](architecture/nouns.md) |
| work in a bounded context | [Bounded contexts](architecture/contexts.md) + [Seams](architecture/seams.md) |
| touch the pipeline | [Stages and gates](pipeline/stages-and-gates.md), [Agent roster](pipeline/agents.md) |
| build the API or UI | [REST API](platform/api.md), [Frontend](platform/frontend.md) |
| patch the pinned OpenExecutive | [Vendor overlay](platform/vendor-overlay.md) |
| build, test or run the loop | [Build harness and tests](operations/harness-and-tests.md) |
| deploy | [Deployment on Atlas](platform/deploy.md) |

## Repository map

```text
backend/redops/
  contexts/{engagement,knowledge,method,commercial,production,
            execution,measurement,portfolio,governance,operations}/
    domain/          pure entities, value objects, policies, errors
    application/     commands, queries, ports, handlers
    infrastructure/  repositories, adapters, mappers
    api/             thin routes and schemas
  agents/            RED agent roster, registry, router, model gateway seam
  workflows/         versioned workflow definitions and durable run state
  shared/            artifacts, persistence (migrations), security
  api/               application factory and composition root
frontend/src/        Next.js UI (thin client, no RED business logic)
docs/                this documentation (source)
scripts/             gates, checks and the vendor overlay
deploy/              Helm chart and GitOps (see Deployment)
vendor/openexecutive pinned submodule (out of scope) + vendor/overlay (in scope)
tests/               unit, contract, integration, workflow, e2e, security
```

## Build and publish the docs

This site is [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

```sh
# preview with live reload (needs mkdocs-material)
make docs-serve

# build the static site into site/ (strict)
make docs
```

Publishing is automatic: `.github/workflows/docs.yml` builds on every push to
`main` that touches `docs/**` or `mkdocs.yml` and deploys to GitHub Pages at
<https://redrhino-online.github.io/red-operations-platform/>. Enable it once in
**Settings → Pages → Source: GitHub Actions**.

## How to maintain these docs

- One page per topic under `docs/`. New pages are picked up automatically; add a
  `nav` entry in `mkdocs.yml` only if you want it in the sidebar.
- Every **noun** the system uses must have an entry in
  [Nouns and their RED significance](architecture/nouns.md). When a cycle adds a
  noun (a new aggregate, seam, env var or pipeline concept), add its row there.
- Keep code examples and commands verbatim and current.

## Related authority documents

- `SPEC.md` — the product and engineering specification (the product constraint).
- `IMPLEMENTATION_PLAN.md` — the living plan and cycle record.
- `docs/DEVELOPER_GUIDE.md` — repo layout, conventions, hosted deployment.
- `AGENTS.md` — instructions for agents working in this repo.

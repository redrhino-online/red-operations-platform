# Architecture overview

## The shape in one picture

```text
                 ┌───────────────────────────────┐
   browser ────▶ │ Next.js UI  (frontend/)        │  thin client, no RED logic
                 └───────────────┬───────────────┘
                                 │ REST /red/*
                 ┌───────────────▼───────────────┐
                 │ FastAPI app (backend/redops)   │
                 │  api/  → application → domain  │
                 │  contexts/ + agents/ +         │
                 │  workflows/ + shared/          │
                 └───────┬───────────────┬───────┘
                         │ ports         │ ports
                 ┌───────▼──────┐  ┌─────▼──────────┐
                 │ PostgreSQL   │  │ OpenExecutive  │  pinned dependency
                 │ (RED stores) │  │ (orchestrator, │  reused via ports +
                 │              │  │  RAG, memory)  │  the vendor overlay
                 └──────────────┘  └────────────────┘
```

## Principles

- **Modular monolith, not microservices (SPEC §6).** One deployable API process
  and one worker share a versioned domain package and PostgreSQL. Split only when
  measured need justifies it.
- **Onion dependency rule.** `domain` depends on nothing (no web, ORM, queue, LLM
  or vendor code). `application` depends on `domain` and defines ports.
  `infrastructure` implements ports. `api` and workers call use cases and never
  mutate persistence directly.
- **Each bounded context owns its write model.** Cross-context change happens
  through explicit commands and durable domain events, not cross-context ORM.
- **Every output is sourced, versioned, owned and gated.** Nothing is represented
  as client-approved unless a human gate approved that exact version (SPEC §1).
- **OpenExecutive is a pinned dependency, not a copy (ADR 0008).** RED extends it
  through ports, with the fork absorbed and RED changes additive ([the absorbed fork](../platform/absorbed-fork.md)).

## The four moving parts

| Part | Location | Responsibility |
| --- | --- | --- |
| **Domain + application** | `backend/redops/contexts/*/domain`, `.../application` | Pure rules, aggregates, policies, use cases, ports |
| **Infrastructure** | `backend/redops/contexts/*/infrastructure`, `shared/` | Repositories, adapters, mappers, migrations |
| **Entry points** | `backend/redops/api/`, `frontend/src/` | Thin HTTP routes and UI screens |
| **Cross-cutting** | `backend/redops/agents/`, `workflows/`, `shared/` | Agent roster + model seam, workflow engine, artifacts, security, persistence |

## Request path

1. The UI calls a REST route under `/red/*` (tenant is always explicit).
2. The route validates the request schema and calls one application use case.
3. The use case loads aggregates through repository ports, applies domain
   policies, and records durable state (often a `GateDecision`).
4. Infrastructure adapters write to PostgreSQL (RED's relational store) and,
   where relevant, to OpenExecutive's SQLite/Chroma stores behind ports.
5. The response carries the persisted, version-pinned record.

## What RED adds over OpenExecutive

| Concern | RED implementation |
| --- | --- |
| Gated stage 0-10 pipeline | `governance` `StageTemplate` / `StageGate` / `GateDecision` / `GateLedger` |
| Version-pinned approvals | `ApprovalRequest` bound to an exact asset version and scope |
| Grounded claims | `knowledge` `SourceRecord` / `Claim` with Known/Derived/Proposed/Unknown |
| RED agent roster | `agents/` `RedAgentSpec` / `RedAgentRegistry` / `RedAgentRouter` over a `ModelGateway` |
| Relational persistence | PostgreSQL adapters and reversible migrations |
| Tenant isolation | `tenant_id` on every resource/query + RLS-ready design |

See also: [Bounded contexts](contexts.md), [Nouns](nouns.md), [Seams](seams.md),
and the [ADR set](../adr/0001-record-architecture-decisions.md).

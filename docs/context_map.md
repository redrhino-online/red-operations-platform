# RED Operations Platform — Bounded Context Map

Phase 0/1 artifact per `docs/fork_inventory.md` and the planning repository's
`SPEC.md` §3 and `IMPLEMENTATION_PLAN.md`. This map defines RED's bounded
contexts, the aggregates each owns, how they relate, and how they land on top of
the existing OpenExecutive fork. It is the starting point for porting the RED
domain into this repository.

## Why a context map

RED is a gated production pipeline (stages 0–10). Each stage produces an exact,
versioned asset that must pass a human gate before downstream work is released.
OpenExecutive already provides the app shell (FastAPI + Next.js), the
orchestrator and specialist routing, a multi-step workflow engine with
`wait_for_human` gates, SQLite episodic memory, an append-only audit log, a
single-instance scheduler, and slot-based client isolation. RED adds the method
substance — the gated pipeline, the version-pinned approvals, and the RED
asset model — as new bounded contexts that plug into those existing mechanisms
through ports, not by rewriting the shell.

## Bounded contexts

Each context owns its write model. Cross-context changes happen through explicit
commands and durable domain events. Domain code depends on no web, ORM, queue,
LLM or vendor package.

| Context | Owns | Core aggregates | RED stage focus |
| --- | --- | --- | --- |
| **Engagement** | client, contract scope, stakeholders, workspace lifecycle, authority registry | `ClientWorkspace` | 0 Intake |
| **Knowledge** | source, claim, provenance, relationship, retrieval | `SourceRecord`, `Claim` | 1 Diagnose (grounding) |
| **Method** | transformation and approved Signature Solution | `PrimaryCurrency`, `DiagnosticModel`, `SignatureSolution`, `MethodVersion` | 2–4 Position/Model/Package |
| **Commercial Design** | audience, offer, assessment, journey | `AvatarProfile`, `BusinessSnapshot`, `OfferVersion`, `DeliverySpecification`, `CampaignMessage` | 1, 5–6 Diagnose/Productize/Message |
| **Production** | brief, build, asset, review | `BuildObject`, `AuthorityAmplifier` | 7 Produce |
| **Execution** | launch, connector, event, incident | `FunnelIntegration`, `LaunchQA`, `PerformanceBaseline` | 8–10 Integrate/QA/Launch |
| **Measurement** | metric, baseline, observation, experiment | `MetricDefinition`, `MeasurementRecord` | 10 Measure |
| **Portfolio** | opportunity and roadmap | opportunity register | post-10 expansion |
| **Governance** | identity, authority, decision, approval, version | `StageGate`, `GateDecision`, `GateLedger`, `ApprovalRequest`, `StageRun`, `PipelineProgress` | cross-cutting (every gate) |
| **Operations** | queues, reminders, intervention | intervention queue | cross-cutting (command center) |

## Relationships and direction

```
Engagement ──owns tenant/authority──▶ every context
Knowledge ──sourced claims──▶ Method / Commercial / Production
Method ──approved versions──▶ Commercial ──approved offer──▶ Production
Production ──approved asset──▶ Execution ──observed milestones──▶ Measurement
Governance ──gate decisions/ledger──▶ every stage transition (HARD dependency)
Operations ──reads gates/metrics──▶ intervention queue (no writes to domains)
```

- **Governance is upstream of every stage transition.** A stage may not complete
  on activity; it needs a passing, version-pinned `GateDecision` in the
  `GateLedger` for that exact stage and template version.
- **Knowledge is the grounding source.** Method, Commercial and Production
  artifacts that make claims must resolve them to same-tenant, known,
  directly-sourced `Claim`s.
- **Method versions flow downstream.** An approved upstream change marks
  dependent offers, messages, assets and journeys review-required with an owner
  and due date.

## Landing on the OpenExecutive fork

| RED context | Plugs into (fork module) | Mechanism |
| --- | --- | --- |
| Engagement | `clients/slots.py` (slot lifecycle), `people/`, `departments/` (authorities), `api/` | Slot activation becomes workspace activation; department `AuthorityLevel` + charter seeds the workspace authority registry |
| Knowledge | `knowledge/` (ChromaDB + RAG), `memory/` (SQLite episodic) | Retrieval adapter must be workspace-scoped and return checksum-pinned citations; original bytes stay in object storage |
| Method | `prompts/domain_prompts.py`, `knowledge/builtin/`, `evals/` | Method becomes versioned built-in knowledge + evals, not hard-coded truth |
| Commercial / Production / Execution | `agents/` + `orchestrator/router.py`, `workflows/` | RED agents are registered through the specialist registry; stage work runs as versioned workflows |
| Governance | `workflows/gate.py`, `workflows/approval*.py`, `workflows/resumer.py`, `audit/logger.py` | `wait_for_human`/`ApprovalGateStepSpec` and the append-only audit log are the substrate; RED adds version-pinned `GateDecision`/`ApprovalRequest` and a durable `GateLedger` |
| Measurement / Portfolio / Operations | `scheduler/`, `alerts/`, `briefing/`, `monitoring/` | Metric registry feeds the command center; interventions are ranked by blocked gate and due date |
| All contexts | `api/` (FastAPI routes), `packages/ui` (Next.js) | Thin route/UI adapters call application use cases; domain logic never lives in routes |

## Onion layers (per context)

```
domain/         entities, value_objects, policies, errors   (pure, no I/O)
application/    commands, queries, ports, handlers          (depends on domain)
infrastructure/ repositories, adapters, mappers             (implements ports)
api/            routes, schemas                             (thin, calls use cases)
```

Import rule: `domain` imports nothing from `application`, `infrastructure`,
`api`, framework, ORM, queue, LLM or vendor packages. Ports are defined by
application needs; adapters satisfy contract tests.

## Language and layer split (see ADR 0007)

OpenExecutive's core is Python (FastAPI, orchestrator, workflows, agents, RAG,
memory, scheduler, audit — SQLite-backed); TypeScript is only the Next.js UI.
RED follows the same split: the domain, application, infrastructure and API
logic is Python under `backend/redops/` in this app repository, reusing the
OpenExecutive dependency through ports, so gate and decision invariants are
enforced by the same backend that runs the orchestrator and workflows.
TypeScript is used only for the Next.js UI and command center, which call the
backend API and hold no RED business logic.

## Code placement (see ADR 0008)

RED code lives in the app repository `redrhino-online/red-operations-platform`
under `backend/redops/` (RED's extension of the OpenExecutive system). The
OpenExecutive fork is a pinned dependency, vendored at `vendor/openexecutive/`
and reused through ports, kept close to upstream so updates stay cheap. This
repository is both the app and the spec/plan/canon authority.

## Open decisions

The contexts above are stable, but four cross-cutting decisions gate real client
data (see `docs/adr/`):

- ADR 0003 — storage strategy given the SQLite/ChromaDB reality.
- ADR 0004 — tenant isolation given slot-based single-active-client switching.
- ADR 0005 — scheduler/worker topology given the single-instance scheduler.
- ADR 0006 — RED agent registration over the specialist registry.

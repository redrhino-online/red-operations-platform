# Bounded contexts

RED is a gated production pipeline (stages 0-10). Each stage produces an exact,
versioned asset that must pass a human gate before downstream work is released.
RED adds the method substance as new bounded contexts that plug into
OpenExecutive's shell through ports. This page is the canonical map; it mirrors
[`docs/context_map.md`](../context_map.md) and SPEC §3.

## The ten contexts

| Context | Owns | Core aggregates | Stage focus |
| --- | --- | --- | --- |
| **Engagement** | client, contract scope, stakeholders, workspace lifecycle, authority registry | `ClientWorkspace` | 0 Intake |
| **Knowledge** | source, claim, provenance, relationship, retrieval | `SourceRecord`, `Claim` | 1 Diagnose (grounding) |
| **Method** | transformation and approved Signature Solution | `PrimaryCurrency`, `DiagnosticModel`, `SignatureSolution`, `MethodVersion` | 2-4 |
| **Commercial Design** | audience, offer, assessment, journey | `AvatarProfile`, `BusinessSnapshot`, `OfferFunnelAudit`, `OfferVersion`, `DeliverySpecification`, `CampaignMessage` | 1, 5-6 |
| **Production** | brief, build, asset, review | `BuildObject`, `AuthorityAmplifierPackage` | 7 Produce |
| **Execution** | launch, connector, event, incident | `FunnelIntegrationPackage`, `LaunchQAPackage`, `JourneyRelease` | 8-10 |
| **Measurement** | metric, baseline, observation, experiment | `MetricDefinition`, `MeasurementRecord` | 10 Measure |
| **Portfolio** | opportunity and roadmap | `Opportunity` | post-10 expansion |
| **Governance** | identity, authority, decision, approval, version | `StageTemplate`, `StageGate`, `GateDecision`, `GateLedger`, `ApprovalRequest`, `StageRun` | every gate |
| **Operations** | queues, reminders, intervention | `Intervention`, `InterventionDismissal` | command center |

## Relationships and direction

```text
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
- **Method versions flow downstream.** An approved upstream change marks dependent
  offers, messages, assets and journeys review-required with an owner and due
  date.

## Where each context lands on OpenExecutive

| RED context | Reuses (fork mechanism) | Mechanism |
| --- | --- | --- |
| Engagement | slot lifecycle, people/departments, `api/` | workspace activation + authority registry |
| Knowledge | ChromaDB + RAG, SQLite episodic memory | workspace-scoped retrieval, checksum-pinned citations |
| Method | domain prompts, built-in knowledge, evals | versioned knowledge + evals |
| Commercial / Production / Execution | specialist registry, workflow engine | RED agents registered, stage work as versioned workflows |
| Governance | approval gates, append-only audit log | RED adds version-pinned decisions and a durable ledger |
| Measurement / Portfolio / Operations | scheduler, alerts, briefing, monitoring | metric registry feeds the command center |
| All | FastAPI routes, Next.js UI | thin adapters only; domain logic never in routes |

## Per-context layout (onion)

```text
domain/         entities, value_objects, policies, errors   (pure, no I/O)
application/    commands, queries, ports, handlers          (depends on domain)
infrastructure/ repositories, adapters, mappers             (implements ports)
api/            routes, schemas                             (thin, calls use cases)
```

Import rule: `domain` imports nothing from `application`, `infrastructure`,
`api`, framework, ORM, queue, LLM or vendor packages.

## Open decisions

The contexts are stable; the cross-cutting decisions live in the
[ADR set](../adr/0001-record-architecture-decisions.md) (storage, tenant
isolation, worker topology, agent registration, backup/restore deferral,
reversible migrations).

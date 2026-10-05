# Seams, ports and adapters

A **port** is an interface defined by an application need. An **adapter** is an
infrastructure implementation. The domain never imports an adapter; the
composition root chooses one. This is how RED reuses OpenExecutive and how tests
run offline.

## The onion rule

```text
domain/          pure: entities, value objects, policies, errors   (no I/O)
application/     use cases + ports                                 (depends on domain)
infrastructure/  repositories, adapters, mappers                    (implements ports)
api/             thin routes/schemas                                (calls use cases)
```

`domain` imports nothing from the layers above it, nor any framework, ORM, queue,
LLM or vendor package. This is enforced by review and by the shape of the code
(there is no `fastapi`, `psycopg`, `openexecutive` or `redis` import in a
`domain/` module).

## The ports RED defines

| Port | Context / location | Adapters | Why it exists |
| --- | --- | --- | --- |
| **ModelGateway** | `agents/application/ports.py` | `DeterministicFakeModelGateway`, `ForkProviderModelGateway`, `LoggingModelGateway` | Abstract the model; keep the agent path deterministic offline and live in prod. |
| **Spokes repositories** (`ClientWorkspaceStore`, `SourceRecordStore`, `ClaimStore`, `MethodVersionRepository`, `OfferVersionRepository`, `BuildObjectRepository`, `GateLedgerRepository`, `JourneyReleaseRepository`, `MeasurementRegistry`, `OpportunityRepository`, `InterventionDismissalRepository`, `ExternalOperationStore`, `WorkflowRunStore`) | `contexts/*/application/ports.py` | In-memory + PostgreSQL (`infrastructure/`) | Persist each aggregate behind an interface; tenancy enforced in the adapter. |
| **KnowledgeRetriever** | `contexts/knowledge/application/ports.py` | `InMemoryKnowledgeRetriever` (over `ClaimStore`) | Tenant-scoped retrieval; a foreign client returns nothing. |
| **InjectionGuard** | `shared/security/application/ports.py` | `InMemoryInjectionGuard` | Treat ingested material as data; refuse tool calls / gate changes grounded on it. |
| **ArtifactUrlResolver** | `shared/artifacts/` | `InMemoryArtifactUrlResolver` | Tenant-scoped artifact URLs. |
| **ConnectorPort / ConnectorTransport** | `contexts/execution/application/ports.py` | `IdempotentConnector`, `PostgresExternalOperationStore` | Replay-safe outbound effects; duplicate delivery → one operation. |
| **WorkflowStepExecutor** | `workflows/application/ports.py` | per-step adapters | Execute a workflow step; durable run state via `WorkflowRunStore`. |

## Composition

`backend/redops/api/app.py::create_app` is the composition root. It builds the
FastAPI app, includes RED's routes, mounts the reused OpenExecutive ASGI app at
`/openexecutive`, and (for the live path) selects infrastructure adapters. The
fake gateway is selected for tests and the deterministic e2e.

## How to add a seam

1. Define the port in `application/ports.py` from the use case's need.
2. Implement an in-memory reference adapter in `infrastructure/` for tests.
3. Implement the durable adapter (PostgreSQL) and a mapper; add a reversible
   migration with a working `downgrade()` (ADR 0010).
4. Contract-test both adapters against the same behaviour.
5. Add the noun to [Nouns](nouns.md) and, if it is a condition 3 layer, to
   `tests/security/covered-layers.txt`.

# Nouns and their RED significance

The system's ubiquitous language. Every noun RED uses in code, the plan or the
API appears here with what it is and why RED cares. When a cycle adds a noun, add
its row.

**RED significance** is the answer to "why does this exist / what breaks if it is
wrong". RED is a gated pipeline that must never present a draft as client-approved
fact, so most nouns exist to make provenance, version, authority or tenancy
explicit.

## 1. System identity

| Noun | What it is | RED significance |
| --- | --- | --- |
| **RED Operations Platform** | RED's productised OpenExecutive: the app in this repo. | The deliverable. Builds on a pinned dependency, never a fork divergence. |
| **RED Operations Director** | The single coordinating agent / visible interface of the platform. | One accountable coordinator instead of a faceless agent swarm; owns prioritisation and handoffs (SPEC §5). |
| **RED Method** | RED's licensed implementation of the reference model. | RED's commercial IP; the pipeline exists to produce it for clients. |
| **Reference model / canon** | The predecessor framework's source material (`canon/`): `framework-canon/` transcripts (48 numbered plus 103 in nine series), RED's synthesized `docs/`, and RED's `internal/` operator maps. | Shapes artifacts' intent; treated as data, never instructions, never copied verbatim (SPEC §12). |
| **SPEC.md** | The product and engineering specification. | The product constraint; wins over the canon on authority, approval, tenancy, security. |
| **IMPLEMENTATION_PLAN.md** | The living plan and per-cycle record. | How the build loop stays honest about progress, blockers and next work. |

## 2. Tenancy and authority

| Noun | What it is | RED significance |
| --- | --- | --- |
| **ClientWorkspace** | The Engagement aggregate: tenant root with lifecycle and a named-authority registry. | Every child resource belongs to exactly one client (SPEC §3); the tenancy boundary. |
| **tenant_id** | Opaque tenant identifier on every tenant resource and query. | Cross-tenant access is a security failure; required on reads and writes. |
| **3F pilot / `3fmindset`** | The first engagement (stage 0-10 happy path). | The prototype's end-to-end proof client. |
| **Authority registry** | The workspace's named authorities (who may approve what). | Approval is never self-granted; a real identity must own each gate. |
| **Designated authority / approver** | The human permitted to approve a given scope. | Gates pin an approver identity; agents cannot impersonate it (SPEC §4). |

## 3. Knowledge and claims

| Noun | What it is | RED significance |
| --- | --- | --- |
| **SourceRecord** | An immutable ingested source: bytes reference, checksum, locator, capture time, access rule. | Original is immutable and retrievable; every claim traces back to it. |
| **Claim** | A statement with trust class, citations and confidence note. | The unit of grounding. Derived/Proposed can never silently become Known (SPEC §3). |
| **Known / Derived / Proposed / Unknown** | The four claim trust classes. | Prevents inference being sold as fact — the core anti-fabrication rule. |
| **Citation / provenance** | The source reference backing a claim. | Makes an artifact traceable to its source and approved method (SPEC §1). |
| **Checksum / locator** | Hash and address of a source's original bytes. | Verifies the source has not changed; retrieval returns checksum-pinned citations. |
| **UnknownRegister** | The list of essential facts with no source. | Records gaps instead of inventing them; each gap names the decision it blocks. |

## 4. Method

| Noun | What it is | RED significance |
| --- | --- | --- |
| **SignatureSolution** | The client's three-phase, nine-step transformation (stage 4). | The method artifact RED licenses and productises; distinct from the production stages. |
| **PrimaryCurrency** | The one primary outcome RED commits to moving (stage 2). | Forces a defensible single currency; drives the Million Dollar Message. |
| **DiagnosticModel** | The Profit Pyramid model of observable levels (stage 3). | Lets a prospect recognise their current and next level. |
| **MethodVersion** | A versioned, approved method. | Approval pins an exact version and intended use; change emits an impact assessment. |
| **Transformation map / ThirteenTransformations** | The structured transformations behind the method. | Canon-shaped stage 4 asset; makes the method explainable without listing tactics. |

## 5. Commercial design

| Noun | What it is | RED significance |
| --- | --- | --- |
| **AvatarProfile** | The stage 1 customer avatar (demographics, psychographics, pains, goals, evidence). | "Avatar Locked" requires a real, source-grounded avatar, not a persona guess. |
| **BusinessSnapshot / OfferFunnelAudit** | Stage 1 diagnosis of the current business and funnel. | Diagnosis is sourced; derived/proposed evidence is refused. |
| **OfferVersion** | The versioned offer (audience, promise, eligibility, price hypothesis, method refs). | Production requires approved dependencies; offer is pinned by version. |
| **DeliverySpecification** | How the offer is delivered (duration, modules, cadence, outcomes). | "Offer Locked" needs every method step to have an actor, action, deliverable, timing and measure. |
| **CampaignMessage / CampaignMessagePackage** | The stage 6 message and its package. | "Campaign Message Approved" requires avatar, currency, problem, promise, method, product and CTA to agree. |
| **MarketAwarenessMap** | Stage 1 awareness-level map. | A canon-informed required kind of the stage 1 gate. |
| **ProductProgram** | Stage 5 productised programme. | A required stage 5 kind, grounded on the method. |
| **ContentRoadmap / ContentCrusher / ContentPlan** | Stage 6 content assets. | Canon-informed required kinds that turn the method into a content plan. |
| **EnrollmentPlan** | The client's designed enrollment/sales process (SPEC §12.7). | A stage 9 required kind: the client runs it, RED measures it. |
| **ClientProcess** | The versioned client-authored sales process. | Client-approved, version-scoped artifact RED produces as a service. |
| **NurturePlan** | The follow-up/nurture lifecycle plan. | A stage 10 required kind for keeping non-converting prospects warm. |
| **LeadMagnetKit** | The canon lead-magnet kit built from one hot step of the method (canon files 03, 04). | A stage 6/8 asset: one step, one currency, paired with the authority video, one clear action, never an ebook or quiz. |
| **SwimlanesPlan** | The multi-channel recovery strategy (messages, ads, outreach, offline, content). | Required at stage 8 and 9 so recovery is not single-channel. |

## 6. Production

| Noun | What it is | RED significance |
| --- | --- | --- |
| **BuildObject** | A unit of production work: type, purpose, audience, state, owner, next action, blockers. | Active builds always have an owner and next action (SPEC §3). |
| **Build state machine** | Identified → Source Required → Ready → In Development → … → Deployed → Measuring → Optimizing → … | Illegal transitions are rejected, not coerced. |
| **AuthorityAmplifier / AuthorityAmplifierPackage** | The stage 7 video asset and its package. | Two approvals: script/claims before visual production, then final creative. |
| **AuthorityVideoKit / AuthorityStepVideo** | The canon authority-video 10-pack: one flagship video plus nine step videos cut from the six-block script (canon files 13-18). | A stage 7 asset that extends the produced `AuthorityAmplifier`; refuses a step video whose step the solution does not name. |
| **Promise, Proof, Problems, Steps, Context, Action** | The Authority Amplifier script order. | Canon-shaped sequence; keeps the message grounded and the next action clear. |

## 7. Execution

| Noun | What it is | RED significance |
| --- | --- | --- |
| **FunnelIntegration / FunnelIntegrationPackage** | The stage 8 built funnel with its typed assets. | "Funnel Complete" pins every asset by exact version. |
| **LaunchQA / LaunchQAPackage** | The stage 9 QA package and its checks. | "Launch Approved" requires all critical-path checks and a named operator. |
| **CompliancePackage** | Stage 9 compliance artifacts (GDPR/FTC/income disclaimers, privacy, terms). | Protects ad accounts and satisfies legal duties before traffic. |
| **JourneyRelease** | A launchable journey release with routing, config digest and rollback ref. | Launch needs signed readiness and an authorised release, not just activation. |
| **ConnectorEffect / ExternalOperation / idempotency key** | A recorded outbound effect keyed to prevent duplicates. | Duplicate delivery must create exactly one external operation. |

## 8. Measurement

| Noun | What it is | RED significance |
| --- | --- | --- |
| **MetricDefinition** | A metric's definition and version. | Observations pin the exact metric version; re-statement is a conflict. |
| **MeasurementRecord** | A windowed observation against a baseline. | Observations are distinct from causal conclusions (SPEC §3). |
| **PerformanceBaseline** | The stage 10 first-qualified-traffic baseline. | The engagement moves into optimisation; launch alone does not complete it. |

## 9. Portfolio

| Noun | What it is | RED significance |
| --- | --- | --- |
| **Opportunity** | A derivative/expansion proposal grounded on an exact stage asset version. | Stays `proposed`; investment and launch require human authority. |

## 10. Governance (gates)

| Noun | What it is | RED significance |
| --- | --- | --- |
| **StageTemplate** | The canonical, versioned stage 0-10 definition and its required asset kinds. | The default pipeline; versioned so in-flight runs keep their definition. |
| **StageGate** | A gate for one stage, derived from the template. | Dependencies and required kinds are not self-declared; derived from the template. |
| **GateDecision** | An immutable decision: stage, pinned asset versions, checkpoint evidence, reviewer, scope, disposition, rationale, next action. | Passing a gate pins exact evidence and intended downstream use. |
| **GateLedger** | The durable, append-only record of gate decisions. | The authoritative history; not lost across restarts. |
| **ApprovalRequest** | A version-specific approval for a designated approver with scope and expiry. | Author cannot impersonate approver; approval is version-specific. |
| **StageRun** | One stage's execution (assigned owner, status, entered/exited at). | A stage completes only via an accepted gate, never on activity. |
| **Gate state** | Not Started, Working, In Review, Approved, Changes Required, Blocked, Waived, Superseded. | Distinguishes activity from gate completion (SPEC §4). |
| **Checkpoint** | The named pass condition for a stage (e.g. "Avatar Locked"). | The concrete thing that must be true before downstream work releases. |
| **Waiver** | A scoped human decision to let a gate pass without an asset. | Never makes an absent asset appear present; carries reason, risk owner, expiry. |
| **Exact asset version** | The pinned version of an asset in a gate decision. | "Approved" is meaningless without the exact version it refers to. |
| **Disposition** | The gate outcome (approved / changes required / …). | The recorded verdict that gates or blocks dependents. |

## 11. Operations

| Noun | What it is | RED significance |
| --- | --- | --- |
| **Intervention** | A ranked command-center card (blocked path, overdue approval, failed journey, near commitment). | Shows *why* it surfaced; the operator's work queue. |
| **InterventionDismissal** | A durable operator dismissal with rationale. | Cards are derived on read; only the dismissal is stored. |

## 12. Agents and the model seam

| Noun | What it is | RED significance |
| --- | --- | --- |
| **Director** | The coordinating agent (registry key `director`). | Owns prioritisation/handoffs; routes the council. |
| **Specialist agent** | One of the nine core section 5 agents (discovery, ip_structuring, offer_journey, knowledge, governance, asset_production, campaign_execution, insight, ip_portfolio). | Bounded domain ownership; each has a charter and a versioned prompt. |
| **Capability slots 10/11** | `client_success`, `assurance`: proposal-only, **no tools**. | Reserved capabilities that can never execute, by construction. |
| **Agent charter** | The prose contract for an agent (`docs/agents/charter-*.md`). | Mandatory fields, allowed tools, evidence policy, escalation, budget. |
| **RedAgentSpec** | Pure-domain spec: slot, key, name, mission, owns, outputs, escalations, tools, proposal-only flag, model, prompt version, charter ref. | The machine-readable section 5 contract; reserved slots cannot declare tools. |
| **RedAgentRegistry** | The validated roster. | Refuses duplicate slots/keys and unknown routing keys. |
| **RedAgentRouter** | Routes a task to an agent through the model gateway port. | Routing reaches every agent without depending on a concrete provider. |
| **ModelGateway** | Port for model completions, keyed by a typed request. | Abstracts model choice; the seam that makes the agent path deterministic in tests. |
| **ModelRequest / ModelResponse / ModelUsage** | Typed model call, completion and token counts. | Carry tenant, model, prompt version, trace id and context refs for attribution. |
| **DeterministicFakeModelGateway** | Offline, repeatable model gateway. | Drives the e2e path with no network (DoD condition 5). |
| **ForkProviderModelGateway** | Live adapter over the fork's provider registry. | The real provider path (OpenRouter), proven separately. |
| **LoggingModelGateway** | Decorator that logs attribution (never prompt/response text). | Satisfies the log-model/prompt/usage/trace rule without leaking client text. |

## 13. Workflows and reliability

| Noun | What it is | RED significance |
| --- | --- | --- |
| **WorkflowDefinition** | A versioned, typed workflow (steps, gates, retry/timeout policy, output schema, rollback). | In-flight runs keep their original definition. |
| **WorkflowRun** | The durable run state machine. | Persisted before side effects so runs resume from committed steps. |
| **WorkflowStepExecutor / WorkflowRunStore** | Ports for executing a step and storing run state. | Restarting a worker preserves a waiting workflow. |
| **Outbox / durable queue** | Transactional outbox for async work. | Worker idempotency; no lost effects. |
| **Optimistic version checking** | Conflict-on-stale-update. | Prevents silent lost updates on concurrent edits. |
| **Idempotency key** | Request identity for retried mutations. | Duplicate delivery creates exactly one operation. |

## 14. Architecture and infrastructure

| Noun | What it is | RED significance |
| --- | --- | --- |
| **Bounded context** | A context that owns its write model. | Keeps models from bleeding; cross-context via commands/events only. |
| **Aggregate** | A consistency boundary (e.g. `ClientWorkspace`, `Claim`, `GateDecision`). | Enforces its invariants in one place. |
| **Value object** | An immutable typed value (e.g. `ModelRequest`, `ArtifactRef`). | Reject-only construction; invalid states are unrepresentable. |
| **Policy** | A pure rule object (e.g. `GateIntegrityPolicy`). | Domain decisions stay testable and I/O-free. |
| **Named error** | A specific exception (e.g. `UntrustedContentError`). | Failures are explicit and greppable, not silent. |
| **Port** | An application-defined interface for an external effect. | Dependency inversion; adapters are swappable. |
| **Adapter** | An infrastructure implementation of a port. | Concrete I/O lives outside the domain. |
| **Repository** | A port for loading/saving an aggregate. | Tenancy and persistence rules enforced uniformly. |
| **Mapper** | Converts domain ↔ row payload. | Keeps ORM/vendor types out of the domain. |
| **Migration** | A versioned schema change with `upgrade()` **and** `downgrade()`. | Reversibility is enforced per cycle (ADR 0010); rollback needs a working downgrade. |
| **PostgreSQL / `DATABASE_URL`** | RED's relational store and its connection string. | Aggregate, gate and ledger persistence (condition 4). |
| **Object store** | Private storage for original/generated bytes. | Metadata in PostgreSQL, bytes in object storage (SPEC §3). |
| **RLS (row-level security)** | Database-enforced tenant isolation. | Defense in depth alongside `tenant_id` filters. |
| **KnowledgeRetriever** | Tenant-scoped retrieval port. | A different client's retrieval must return nothing (acceptance scenario). |
| **ArtifactRef / ArtifactUrlResolver** | Typed artifact reference and a tenant-scoped URL resolver. | Artifact URLs must not leak across tenants (condition 3). |
| **InjectionGuard / ContentTrust / AuthorityBasis / IngestedMaterial / ProposedToolCall / ProposedGateChange** | The prompt-injection boundary: ingested material is always untrusted data. | An agent cannot confer approval on itself; text cannot direct a tool call or gate change (SPEC §5). |

## 15. Pipeline stages and checkpoints

Stages are **production checkpoints**, not the client's nine-step transformation
(SPEC §4).

| Stage | Checkpoint |
| --- | --- |
| 0 Intake | Production Ready |
| 1 Diagnose | Avatar Locked |
| 2 Position | Currency Locked |
| 3 Model | Diagnostic Model Approved |
| 4 Package IP | IP Architecture Locked |
| 5 Productize | Offer Locked |
| 6 Message | Campaign Message Approved |
| 7 Produce | Authority Amplifier Approved (script + creative) |
| 8 Integrate | Funnel Complete |
| 9 QA | Launch Approved |
| 10 Launch | Performance Baseline Established |

## 16. Delivery and deployment

| Noun | What it is | RED significance |
| --- | --- | --- |
| **Atlas k3s** | The home-lab Kubernetes cluster. | The prototype's delivery target (condition 9). |
| **Argo CD** | GitOps controller reconciling the Helm release. | Declarative, reversible deploys; health is part of the gate. |
| **Gitea forge** (`git.atlas.lan`) | Self-hosted Git + Actions + registry on the lab network. | Builds and stores RED images. |
| **image registry** (`registry.atlas.lan`) | The forge's OCI registry. | Source of the deployed `redop-api`/`redop-ui` images. |
| **GitOps repo** (`211lab/atlas`) | Holds `apps/redop/chart` and `gitops/apps/redop.yaml`. | The desired state Argo reconciles; a release pins an image digest/tag here. |
| **Helm chart** (`deploy/charts/redop`) | api/ui/worker, migration Job, ingress, PDB, probes. | The deployable unit; authored in the app repo (Q48). |
| **`Dockerfile.api` / `Dockerfile.ui`** | Multi-stage images: the RED API (`uv sync --locked`, `redops.api.app:app`) and the Next.js standalone UI. | The buildable units CI pushes to the registry (Q47). |
| **build workflow** (`.gitea/workflows/build.yaml`) | Gitea Actions job that builds/pushes both images and promotes `apiTag`/`uiTag` into the GitOps chart. | Turns a push to the `atlas` remote into a reconciled release (Q47). |
| **migration Job** | Runs `alembic upgrade head` before the API serves; Helm pre-install/pre-upgrade hook and Argo CD PreSync at sync-wave -1, with an API initContainer that waits for its success. | Condition 9 requires migration-before-serve ordering. |
| **SealedSecret** | Encrypted Kubernetes secret committed to Git. | Secrets never land in Git in plaintext. |
| **ingress / Traefik / cert-manager (`atlas-ca`)** | HTTP entry, router, internal CA. | Serves `redop.atlas.lan` on the lab network only. |
| **`redop.atlas.lan`** | The deployed host. | The health gate fetches it and requires the RED identity marker. |
| **REDOP_RED_MARKER** | The identity marker the deployed health gate requires (default `RED Operations`). | Prevents a bare 200 from the OpenExecutive shell passing condition 9. |

## 17. Vendor overlay (in scope)

| Noun | What it is | RED significance |
| --- | --- | --- |
| **vendor/openexecutive** | Pinned git submodule (upstream OpenExecutive). | Reused dependency, **internals out of scope**; kept close to upstream (ADR 0008). |
| **vendor overlay** | Committed RED-authored changes to the submodule under `vendor/overlay/`. | The only sanctioned way to edit the vendor (ADR 0011). |
| **overlay file** | A file under `vendor/overlay/files/` copied verbatim onto the submodule. | New vendor-side files (agent classes, prompts, knowledge, evals). |
| **hook snippet** | A snippet under `vendor/overlay/hooks/` spliced into an existing vendor file. | In-place edits (registry/area registration) without hand-editing the submodule. |
| **RED-OVERLAY marker** | `# RED-OVERLAY:BEGIN <marker>` / `END` guard around a hook. | Makes apply idempotent and re-triggerable after an upstream bump. |
| **apply_vendor_overlay.sh** | Applies or (`--check`) verifies the overlay. | `make done` `[4/6]` requires the tree to equal the overlay with no unaccounted change. |

## 18. Harness, process and the definition of done

| Noun | What it is | RED significance |
| --- | --- | --- |
| **ralph_cycle.sh** | The one-cycle build harness driving OpenCode. | Builds one bounded, verifiable item per cycle and commits it with a written why. |
| **.ralph/** | Run logs, the cycle lock, `DONE`/`STOP` markers and commit messages (gitignored). | Auditable per-cycle record; `DONE` is the clean stop. |
| **canon.lock** | Pinned canon content hash. | Detects canon drift and halts cleanly. |
| **`make check`** | The per-cycle gate: pytest (with Postgres) + pyflakes. | Must pass every cycle. |
| **`make done`** | The prototype definition-of-done gate (SPEC §13). | The success stop condition; never approves, spends or deploys by itself. |
| **Definition of done (DoD)** | The nine section 13 conditions. | The machine-checkable bar that ends the build loop. |
| **ADR** | Architecture Decision Record (`docs/adr/`). | Durable, dated decisions with context and alternatives. |
| **Charter** | An agent's operating contract (`docs/agents/charter-*.md`). | The prose half of the section 5 agent contract. |

## 19. Environment variables

| Variable | Meaning |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection for RED persistence and migrations. |
| `EXEC_EMAIL_ADDRESS` | Required by the reused OpenExecutive shell; no default. |
| `OPENROUTER_API_KEY` / `DEFAULT_MODEL` | Live model provider and default model. |
| `BACKEND_SHARED_SECRET` / `AUTH_SECRET` | Reused shell API and auth secrets. |
| `REDOP_HEALTH_URL` | Deployed health URL for `make done` `[6/6]` (default `https://redop.atlas.lan/`). |
| `REDOP_HEALTH_INSECURE` | Skip CA verification for the internal `atlas-ca`. |
| `REDOP_RED_MARKER` | Required RED identity marker in the deployed response. |
| `REDOP_LIVE_OPENROUTER_SMOKE` | Opt-in flag to run the paid live smoke (kept unset so cycles don't spend). |
| `REDOP_NAMESPACE`, `REDOP_PVC`, `REDOP_API_DEPLOY`, `REDOP_UI_DEPLOY`, `REDOP_ARGO_APP`, `REDOP_ARGO_NAMESPACE`, `REDOP_ASSUME_YES` | Inputs to the hosted reset/deploy tooling. |

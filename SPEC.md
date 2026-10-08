# RED Operations Platform: Product and Engineering Specification

Version: 0.5, October 8, 2026. Status: implementation baseline, subject to fork inventory and client authority decisions. Section 12 (canon reference) updated for the expanded canon: 151 source transcripts in ten series, plus RED's synthesized public method docs and internal operator maps. Section 14 (cockpit overhaul definition of done) added by the 2026-10-08 single-shell decision (ADR 0013); the vendor disposition revised the same day by the fork-absorption decision (ADR 0014).

## 1. Product contract

RED Operations Platform coordinates RED client work from discovery through approved intellectual property, offers, assets, live customer journeys, measured results, and portfolio expansion. It also helps each client design and implement their own sales process, in the client's voice, following the licensed reference model, as a versioned artifact under the same approval rules. Its visible interface is the RED Operations Director. Specialist agents operate within bounded domains. Every output has a source, status, owner, next action, and applicable approval. The platform never represents a draft or model inference as client approved fact.

Primary users: RED principal, production manager, specialists, client approvers, and read limited client collaborators. Initial pilot: one RED engagement and the 3F journey, with real client approval before publication. Later: multiple isolated client workspaces and a practice wide command center.

Success criteria for pilot: a production engagement progresses through the stage 0 to 10 gate contract defined below; each stage produces an approved asset or explicit exception before dependent work is released; an asset can be traced to its source and approved method; a complete journey passes a prospect path dry run; the command center identifies missing assets, blockers, and owners; an approved change reports affected downstream assets; first qualified traffic establishes a performance baseline and begins optimization rather than ending the engagement.

Out of scope for the first release: autonomous financial commitments, autonomous public publishing, unreviewed testimonials or performance claims, a general knowledge graph database, and fully autonomous campaign optimization. Capability agents 10 and 11 are chartered (see section 5) but proposal-only with no execution permissions. The existing VP descriptions remain proposals for domain responsibilities, not evidence of currently staffed departments.

## 2. Fork baseline and disposition

Fork OpenExecutive at a pinned upstream commit and record license, dependencies, migrations, service boundaries, actual interfaces, and deployment manifests. The conversation describes FastAPI, Next.js, an orchestrator, specialists, client slots, RAG, workflows, approvals, memory, scheduling, and a cockpit. These are candidate reuse targets, not verified repository facts. No upstream URL or checkout was supplied for this specification.

| Candidate component | Intended treatment | Verification gate |
| --- | --- | --- |
| FastAPI and Next.js shells | Keep when compatible | Identify routes, auth, state ownership, build and test commands |
| Orchestration and specialist runner | Adapt behind ports | Inspect tool permissions, retries, context isolation, cancellation |
| Client storage and retrieval | Adapt per tenant | Verify namespace enforcement and source citation behavior |
| Workflow engine and persistence | Adapt to RED definitions | Verify resumability, version pinning, gate semantics, idempotence |
| Approvals, audit, alerts, scheduling | Preserve behavior where sound | Verify actor identity, immutable records, delivery and retry behavior |
| Executive persona, generic departments | Replace with RED's nine required agents | Ship all nine agents (section 5); retire the OpenExecutive generic C-suite registry; remove obsolete labels and incompatible permissions |
| Cockpit | Adopt as the single RED shell, rebranded RED (ADR 0012, ADR 0013) | The OpenExecutive cockpit is the only user-facing UI: the section 8 screens are native cockpit pages at `/operations/*` through the ADR 0011 overlay, the separate `/screens` thin client is retired, a shared workspace/engagement context drives the screens, the landing surface is the portfolio command center, and the canon, departments and stage workflows are RED's (section 14) |

Retain upstream notices and licensing obligations. Keep a fork diff register with upstream commit, local decision, owner, migration note, and regression evidence. Never delete a working upstream path until its replacement has passed characterization tests. The fork is absorbed into this repository (ADR 0014): `vendor/openexecutive` is ordinary tracked source, absorbed at upstream commit `31e55338db7f7a0eb7ff30b4cb8942a1ece551bd` (v0.4.6) with the previously applied RED rebrand and agent registration as the committed baseline. Upstream updates arrive through owner-driven merges recorded in the fork diff register (`docs/fork_inventory.md`), followed by a deliberate `make vendor-pin` re-baseline. RED changes inside the vendor tree are additive: cycles add new files and never modify a locked upstream-origin file; the two exemptions are RED-adopted surfaces (`vendor/red-owned-files.txt`, the files the adoption already changed) and owner-approved exceptions recorded in the fork diff register. `scripts/check_vendor_additive.sh` (DoD `[4/7]`) enforces the rule.

## 3. Domain boundaries

Bounded contexts: Engagement (client, contract scope, stakeholders, health); Knowledge (source, claim, provenance, relationship, retrieval); Method (transformation and approved Signature Solution); Commercial Design (audience, offer, assessment, journey); Production (brief, build, asset, review); Execution (launch, connector, event, incident); Measurement (metric, baseline, observation, experiment); Portfolio (opportunity and roadmap); Governance (identity, authority, decision, approval, version); Operations (queues, reminders, intervention). Each context owns its write model. Cross context changes occur through explicit commands and durable domain events.

Core aggregates and invariants:

| Aggregate | Required fields | Invariant |
| --- | --- | --- |
| ClientWorkspace | id, tenant, authorities, lifecycle | Every child resource belongs to exactly one client |
| SourceRecord | original bytes reference, checksum, locator, capture time, access rule | Original is immutable and retrievable to authorized users |
| Claim | statement, Known/Derived/Proposed/Unknown, citations, confidence note | Derived and Proposed cannot silently become Known |
| Decision | subject, choice, rationale, actor, timestamp, affected version | Decision history is append only |
| MethodVersion | parent method, stages, currency, claims, semantic version | Approval pins an exact version and intended use |
| OfferVersion | audience, promise, eligibility, price hypothesis, method refs | Production requires approved dependencies |
| BuildObject | type, purpose, audience, state, owner, next action, blockers, refs | Active builds have owner and next action |
| StageRun | engagement, stage number, template version, assigned owner, status, entered and exited at | Stage completion requires gate acceptance, not merely activity |
| GateDecision | stage, required asset versions, checkpoint evidence, reviewer, scope, disposition | Passing a gate pins the exact evidence and intended downstream use |
| ApprovalRequest | proposed version hash, scope, approver, outcome, expiry | Author cannot impersonate approver; approval is version specific |
| JourneyRelease | assets, routing, configuration digest, rollback ref | Launch needs signed readiness and authorized release |
| MeasurementRecord | metric definition, window, baseline, observation, source | Observations are distinct from causal conclusions |

Use globally unique opaque IDs and tenant_id on every tenant resource and query. Relational foreign keys and row level policies provide defense in depth. Keep object bytes in a private object store with metadata in PostgreSQL. Start with PostgreSQL full text and vector retrieval if the fork supports it, then add specialized search only if measured requirements justify it. No graph database is required for a relational relationship table and traversals at pilot scale.

## 4. State machines and gates

Engagement: Intake, Diagnosis, Positioning, Diagnostic Modeling, IP Packaging, Productization, Campaign Messaging, Authority Amplifier Production, Funnel Integration, Launch QA, First Campaign Launch, Optimization, Expansion, Paused, Completed. This is a summary state; parallel BuildObjects can be in different states. Build: Identified, Source Required, Ready, In Development, Internal Review, Client Review, Changes Requested, Approved, Production Ready, Deployed, Measuring, Optimizing, Superseded, Archived. Information: Raw, Working, Proposed, Approved, Superseded, Archived. Record transition actor, reason, timestamp, old and new version, and correlation ID. Reject illegal transitions rather than silently coercing state.

Gates: discovery sufficiency requires sourced diagnosis and explicit unknowns; method approval requires client designated authority; offer readiness requires approved method and delivery feasibility; production acceptance requires source mapping and functional checks; launch requires integration checks, customer path dry run, consent where applicable, named operator, rollback; performance recommendations require evidence and owner approval before material changes. Governance can flag or block transitions, but an agent cannot confer human approval upon itself. Client approved information is scoped to a version and intended use.

Changing an approved upstream method emits an impact assessment: dependent offers, briefs, assets, journeys, and claims are marked review required, with human owners and due dates. Previous deployed releases stay historically identifiable. Routine editorial changes may use a lighter approval policy if the designated authority matrix allows it.

### RED production engagement: stages 0 through 10

The default production template is a gated dependency graph. A stage is complete only when its required assets exist, pass a defined checkpoint, and receive approval for downstream use. Work can be drafted in parallel when useful, but an unapproved dependency cannot be represented as approved or used to authorize production or traffic. The pipeline is a default template, not a claim that every client enters with no existing assets. Previously approved client assets may satisfy a gate only after source, authority, version, and fit are checked and a gate decision is recorded.

| Stage | Objective and required asset package | Gate and checkpoint | Accountable domain |
| --- | --- | --- | --- |
| 0. Intake | Client record, signed scope, billing confirmation, questionnaire, existing and brand asset inventories, access checklist, baseline measures, workspace, communication channel, timeline, responsibilities, launch definition | Production Ready: building for whom, success measure, owners, boundaries, and prerequisites are explicit | Engagement and Governance |
| 1. Diagnose | Business snapshot, offer and funnel audit, avatar with demographics and psychographics, pains, goals, consequences of inaction, awareness, customer evidence and voice notes | Avatar Locked: a stranger can recognize who the customer is, what matters, and why now | Discovery and Diagnosis |
| 2. Position | Category, currency inventory and primary currency, current and desired measures, horizon, qualifications, transformation statement, core problem and Million Dollar Message | Currency Locked: one primary outcome connects a specific person, measurable movement, and distinct mechanism | Discovery, IP Structuring, Commercial Design |
| 3. Model | Profit Pyramid levels, observable measures, symptoms, behaviors and problems per level, progression, qualification logic, name, visual and explanatory copy | Diagnostic Model Approved: a prospect can recognize their current level and desired next level using observable differences | IP Structuring and Commercial Design |
| 4. Package IP | Transformation map, process inventory, three phases, nine steps, named stages, starting and final states, inputs, actions, outputs, narrative and visual | IP Architecture Locked: the transformation is coherent and explainable without listing every tactic | IP Structuring |
| 5. Productize | Delivery model, duration, modules, responsibilities, support cadence, stage deliverables, outcome measures, pricing and payments, scope, guarantee decision, eligibility and offer stack | Offer Locked: every method step has an action, actor, deliverable, timing and measure | Offer and Journey Design |
| 6. Message | Promise, problem hierarchy, desired outcome, proof and objections, story, method explanation, CTA, lead magnet, hook, angles, landing message, Authority Amplifier outline | Campaign Message Approved: avatar, currency, problem, promise, method, product and CTA agree | Offer and Journey Design, Business Asset Production |
| 7. Produce | Approved Authority Amplifier script in Promise, Proof, Problems, Steps, Context, Action order; storyboard, brand treatment, presentation, speaker notes, recording, edited and hosted video, player assets | Authority Amplifier Approved: message and supported proof pass review before visual or video production; final asset gives a credible next action | Business Asset Production |
| 8. Integrate | Campaign architecture, pages, forms, qualification, booking, sequences, CRM, tags, automation, analytics, tracking, sales handoff and SOPs | Funnel Complete: a test prospect completes capture, engagement and conversion handoffs with reliable records and ownership | Campaign and Journey Execution |
| 9. QA | Recorded message, technical and commercial tests on desktop and mobile, forms, CRM, email, automation, booking, tracking, payment when relevant, handoff, client approval, budget, creative, dashboard and launch decision | Launch Approved: all critical path checks pass, exceptions have owners, and the designated human authorizes traffic | Campaign and Journey Execution, Governance |
| 10. Launch | Live campaign, spend and lead records, conversion and engagement measures, application, booking, show, close, acquisition cost, attribution and issue log | Performance Baseline Established: first qualified traffic and subsequent lead, appointment and sale are distinct observed milestones, with missing observations shown as pending | Campaign and Journey Execution, Insight and Performance |

The 3 phase and 9 step Signature Solution structure is a methodological template for stage 4. The 0 to 10 stages are production checkpoints, so their numbering must never be confused with the client's nine step transformation. The canon's public method map (three phases, nine motions, 27 steps) and its five stages (Build, Launch, Serve, Grow, Partner) are the client-facing framing of the same work; they are not the 0 to 10 production pipeline and must not be conflated with it. Stage 7 has two distinct approvals: script and supported claims before visual production, then final creative acceptance. Stage 9 distinguishes Ready for Traffic from live traffic. Stage 10 begins post launch measurement and optimization; campaign activation alone does not complete an engagement.

### Gate record and production manager view

For every stage, persist template version, required assets and their exact versions, checkpoint rubric, test evidence, gate state, assigned work owner, designated approver, due date, dependencies, blockers, decision rationale and next action. Gate states: Not Started, Working, In Review, Approved, Changes Required, Blocked, Waived, Superseded. A waiver is a scoped human decision with reason, risk owner, expiry or review trigger, and downstream effects. It never makes an absent asset appear present. A failed or expired prerequisite blocks dependent authorization until resolved.

The production view answers, for each client: current stage, what should exist, what is present and approved, what is missing, who is accountable, which dependency blocks work, what approval is next, and when it is due. Separate eight reporting dimensions: assets, milestones, checkpoints, metrics, owner, dependency, status and due date. Count activity separately from gate completion. Display progress as approved gates and verified post launch milestones, never as tasks checked off.

## 5. Agent operating contracts

Every agent has a versioned charter, allowed tools, input schema, output schema, context budget, evidence policy, quality rubric, escalation rules, and budget limit. Agent output is a proposal or an authorized internal action, never an implicit grant of authority. The Director coordinates the council, owns prioritization and handoffs, and presents sourced reasons for interventions.

| Agent | Owns | Main outputs | Must escalate |
| --- | --- | --- | --- |
| Discovery and Diagnosis | intake, diagnosis, gaps | enterprise brief, asset inventory | missing essential evidence |
| IP Structuring | Signature Solution, milestones | method version, terminology | material change to client method |
| Offer and Journey Design | offer and customer path | offer specification, routing | pricing and positioning decisions |
| Knowledge Management | ingestion, indexing, retrieval | source index, asset catalog | disputed authority |
| Governance and Approval | states, gates, change impact | approval queue, decision log | client substantive decision |
| Business Asset Production | briefs and asset quality | traced deliverables | missing approved prerequisites |
| Campaign and Journey Execution | implementation and launch checks | release, verification, incident | external launch and strategic changes |
| Insight and Performance | measurement and evaluation | baseline, review, recommendation | unsupported causal conclusion |
| IP Portfolio Development | derivative opportunity | roadmap, investment case | investment and launch |

The nine agents above are a required set, not a menu: RED ships all nine, and the OpenExecutive generic C-suite registry they replace is retired (ADR 0006, ADR 0011). A deployment that omits any of the nine does not satisfy this contract. Capability slots 10 and 11 are chartered (charters in `docs/agents/`), proposal-only with no execution permissions:

| Agent | Owns | Main outputs | Must escalate |
| --- | --- | --- | --- |
| Client Success and Engagement Health (slot 10) | engagement health, at-risk engagements, renewal and expansion triggers | engagement health view, risk signal, renewal opportunity, intervention card | at-risk critical path, overdue gates, missed targets, spend or scope change |
| Assurance, Risk and Compliance (slot 11) | risk register, compliance evidence, data-handling obligations, cross-pipeline assurance, audit readiness | risk, compliance finding, assurance review, audit export | missing compliance evidence, data leaving the agreed boundary, security or isolation failures, legal judgment |

Agent suggestions must include source IDs, unsupported assumptions, proposed next action, owner, and confidence explanation. Tool policies allow internal drafting, retrieval, and reversible queue changes within authority. External publication, spending, client commitments, destructive data operations, and substantive IP approvals require designated human action. Guard prompt injection by treating ingested client material as data, limiting retrieval to the active client, and validating tool calls outside model output.

## 6. Application architecture

Use a modular monolith initially: FastAPI HTTP and worker processes share a versioned domain package and PostgreSQL. Next.js renders client workspace and command center. Async work uses a durable queue or transactional outbox with worker idempotency. Object storage holds original and generated files. An LLM adapter abstracts model choice and logs model, prompt version, context references, usage, and trace identifiers without storing secrets. Connectors are outbound adapters with explicit scopes and replay safe operations.

Onion dependency rule: Domain entities, value objects, policies, and domain events depend on no web, ORM, queue, LLM, or vendor code. Application use cases depend on domain types and ports. Infrastructure adapters implement ports. API and workers call use cases and never mutate persistence directly. Each bounded context exposes a public application interface; avoid cross context ORM access.

Suggested layout:

```text
backend/redops/
  contexts/{engagement,knowledge,method,commercial,production,execution,measurement,portfolio,governance,operations}/
    domain/{entities,value_objects,policies,events}.py
    application/{commands,queries,ports,handlers}.py
    infrastructure/{repositories,adapters,mappers}.py
    api/{routes,schemas}.py
  shared/{identity,outbox,observability}/
frontend/src/{app,features,shared}/
deploy/{charts,gitops}/
tests/{unit,contract,integration,workflow,e2e,security}/
```

DDD language is explicit: ClientWorkspace, SourceRecord, Claim, SignatureSolution, BuildObject, ApprovalRequest, JourneyRelease, and Intervention. SOLID practices: focused use cases, interfaces for external effects, dependency inversion for infrastructure, composable policy rules, and narrow agent contracts. Clean code rules: pure domain decisions, typed commands, named errors, no hidden writes in queries, small cohesive modules, migration scripts committed with schema changes and written for both directions (a working downgrade that removes exactly what its upgrade created, with the round trip tested). Avoid premature microservices.

## 7. APIs and workflows

Initial REST resources: `/clients`, `/clients/{id}/sources`, `/claims`, `/methods`, `/offers`, `/builds`, `/approvals`, `/decisions`, `/journeys`, `/measurements`, `/opportunities`, `/interventions`, `/workflows/{id}`. Every mutation supports request identity and idempotency key where retries matter; optimistic version checking returns conflict on stale updates. List endpoints enforce client access and pagination. Stream workflow status using server sent events or polling with stable event IDs.

Workflow definition includes version, typed inputs, steps, gate requirements, retry and timeout policy, output schema, and rollback or compensation. Persist run state before side effects; resume from committed steps. Signature Solution: gather sources, extract grounded claims, market context, draft stages, critique, human approve, register version, schedule next build. Authority Amplifier: load approved method, select step, Promise, Proof, Problems, Steps, Context, Action, review claim support, client approval, production package. Each run records parent source and prompt versions. Approval wait must survive worker restarts.

Command center intervention fields: client, severity, reason, evidence, owner, next action, due time, state, affected builds. Ranking favors blocked critical path, overdue approvals, failed live journeys, and nearing commitments. Show why each card is surfaced and allow dismissal with rationale. Notifications are deduplicated and respect owner and quiet hours.

## 8. User experience

Screens: portfolio command center, client workspace overview, source and claim explorer, transformation map, offer and journey editor, build board with dependency view, approval inbox with exact version diff, workflow run detail, launch readiness, performance review, portfolio opportunities, and authority settings. A client approver sees only approved scope and review items assigned to them. Each artifact view shows state, provenance, dependencies, version history, and next action. No silent state change after AI generated content appears.

## 9. Security, reliability, and privacy

Authenticate through an identity provider with OIDC if supported by the fork. Enforce server side RBAC with client membership and designated approver identity on every command and query. Separate service credentials from users; redact sensitive content in operational logs; encrypt traffic, database and object storage; rotate secrets. Record immutable audit events for approvals, permission changes, exports, launches, and deletions. Treat client material as confidential. Define retention, export, and deletion policies before onboarding production clients. Test cross client access at API, retrieval, background worker, and artifact URL layers.

Targets for pilot, to confirm with operators: 99.5 percent application availability excluding home network outages; no lost approval or decision records; every workflow failure visible to an owner. Database backup, a 24 hour recovery point, an 8 hour recovery time and a restore drill are production-readiness gates (ADR 0009, ADR 0010): they belong to the production-readiness phase, which begins once the first cluster release exists, may span several further iterations, and must complete before production client data is onboarded. The prototype keeps its data durable in PostgreSQL but provisions no backup and runs no restore drill. Instrument traces, queue lag, workflow errors, retrieval failures, spend, approval latency, and journey failures. Use graceful degradation: readonly access to approved material when the AI provider fails, if data tier remains available.

## 10. Home network Kubernetes delivery

Separate application repository from a GitOps environment repository. CI builds pinned container images, runs required gates, publishes to an image registry reachable by the cluster, and proposes a digest update to the GitOps repo. Argo CD reconciles a Helm release per environment. Protect production sync policy and use manual approval for image promotion and schema migrations until rollback is proven. Keep secrets outside Git using an operator backed by encrypted secret material or an external secret provider; the chosen mechanism needs a documented recovery path.

Helm chart components: web, api, worker, migration Job, ingress, service accounts, config, network policies, PodDisruptionBudget where replicas justify it, health probes, resource requests and limits. Pin chart and image versions. Database, object store, ingress controller, DNS, TLS, backup, and observability are cluster dependencies with explicit ownership. Make database migration backward compatible with the old running image and reversible (ADR 0010), then promote app, then clean up old schema in a later release. Argo CD health checks must wait for migrations and rollout readiness. Use internal DNS, secure remote access via VPN or equivalent, and avoid exposing Argo CD or admin endpoints publicly. UPS and outage recovery are operational dependencies of a home hosted cluster.

Release rollback: revert the GitOps image digest, preserve event and schema compatibility, and redeploy. The rollback drill and data restoration are production-readiness gates (ADR 0009, ADR 0010), run in the production-readiness phase after the first cluster release and before production client data; data restoration requires a tested backup. Version workflow definitions so in flight runs continue on their original definition. Maintain a release record of image digest, chart version, migration, prompt versions, and verification result.

## 11. Acceptance tests and open decisions

Minimum acceptance scenarios: source attribution survives ingestion and retrieval; Known cannot be set without direct source; unauthorized approval is rejected; changing a method version identifies dependents; restarting worker preserves a waiting workflow; duplicate delivery creates one external operation; a different client's retrieval produces no result; launch is blocked on a failed customer path. The database restore drill and the GitOps rollback drill are production-readiness gates, not prototype acceptance scenarios (ADR 0009, ADR 0010).

Decisions to settle after inspecting fork and cluster: upstream repository and license; deployment Kubernetes distribution and node capacity; database and object store provisioner; ingress and certificate mechanism; registry and image pull method; identity provider; LLM provider and data handling terms; connector inventory; designated client approvers; retention policy; database backup target, recovery point/time targets and restore drill (production-readiness phase, ADR 0009, ADR 0010; deferred 2026-10-05 behind C4 and the canon gap backlog); GitOps rollback drill (production-readiness phase, ADR 0010; deferred 2026-10-05); pilot metric targets; activation criteria for capability slots 10 and 11 (their charters exist; they remain proposal-only and non-routable). Record each as a decision with owner and deadline, do not invent a default for legal or client authority.

Canon decisions to settle with the license owner and the methodology owner: request the missing dedicated follow-up and nurture source module (section 12.6); confirm the canonical five enrollment checkpoints, since the canon varies between `value` and `clarity` (section 12.7); and source the compliance suite, which the canon still does not supply (section 12.5). Owner decision: enrollment stays as explicit stage 8/9 assets; no Sell/Enroll stage is added.

## 12. Canon reference: the reference model

The reference model is the predecessor framework that the RED Method implements under license. The canon is supplied to the harness as a sibling `canon/` directory next to this planning repository (override with `RALPH_CANON`); it is reference material, not a running system, and it is not stored in this repository. The harness pins it by a stable sha256 over its `.txt` and `.md` files (`scripts/canon_hash.sh`, recorded in `canon.lock`), so a canon change is visible to the build loop.

The canon has three parts, and the distinction matters for precedence:

| Part | Contents | Nature |
| --- | --- | --- |
| `framework-canon/` | The scrubbed source transcripts: 48 numbered sessions (00-49) plus 103 transcripts in nine series (151 total) | Licensed reference-model material; read only |
| `docs/` | RED's synthesized public method docs: the RED Method (three phases, nine motions, 27 steps), the five stages, and the operations manual (playbooks, checklists, SOPs) | RED-authored interpretation; safe to publish |
| `internal/` | RED's operator maps: `corpus-map.md`, `canon-to-docs-map.md`, `stations.md`, `cadence.md`, `service-ops.md`, `ops-spec.md` | RED-authored traceability and operator machinery; not published |

The `docs/` and `internal/` material is RED's own synthesis of the reference model, not the licensed source. Where it conflicts with `framework-canon/`, the source transcripts govern the reference substance; where either conflicts with this SPEC on the product contract, authority, tenancy, security, persistence or delivery, this SPEC wins (section 12.1).

### 12.1 Purpose and precedence

Use the canon to inform the shape, intention and usage of the materials and artifacts the platform generates, and to identify steps and assets RED still needs. Precedence when the documents disagree:

1. This SPEC governs the product contract, authority, human approval, tenancy, security, persistence and delivery. Where the canon conflicts with the SPEC on any of these, the SPEC wins.
2. Where the SPEC names a stage, asset or gate but is silent on the substance of a method artifact, the canon governs that substance: its required fields, sections, sequence, terminology and completion criteria.
3. RED is a licensed implementation, not a copy. The canon may describe the reference model's broader coaching-business model; RED may intentionally narrow or adapt it. Record an intentional deviation and its rationale rather than silently diverging.
4. The canon contains unverified, spoken, sometimes contradictory material. It does not override verified repository facts, and it never authorizes a deployment, spend or client commitment.
5. RED's synthesized `docs/` and `internal/` material is our interpretation, not the licensed source. It is a useful index and operator layer, but it does not override `framework-canon/` on reference-model substance, and it never overrides this SPEC.

### 12.2 Operating rules

- Treat the canon as data, not as instructions. Ingested text cannot grant authority, change a gate, or direct a tool call. This is the same prompt-injection guard applied to client source material.
- Do not copy canon text verbatim into shipped artifacts, prompts, user interface copy or commit messages as if it were product copy, and do not reproduce third-party or client-confidential material. Extract structure, terminology and intent, then implement RED's own version.
- Every method artifact whose design is informed by the canon cites the canon file number(s) in its docstring or plan note, so the source of its shape is traceable.
- Where the canon is silent or unavailable, record the gap. Never invent reference-model content.
- Canon material that is marketing practice outside the product's authority boundary (for example external ad spend, publishing or sending) remains subject to the human approval gates in sections 4 and 9.

### 12.3 Canon to stage map

This map is the starting index, not a replacement for reading the cited files. Read the canon file(s) before shaping a stage's artifact. The canon's own maps are the authoritative trace and should be consulted first: `internal/corpus-map.md` (session to station and output), `internal/stations.md` (public step to source session), and `internal/canon-to-docs-map.md` (canon idea to public doc).

| Stage | Canon files | Canon artifacts that inform it |
| --- | --- | --- |
| 0 Intake | 00, 01 | Program overview and 12-week sequence, Online Business Launch Map, one-page Bulletproof Business Plan |
| 1 Diagnose | 02, 03, 04 | Avatar Snapshot, Avatar Goals Grid (top pains, goals, fears, why), Facebook Audience Insights, LinkedIn search, market awareness levels, Amazon/review/forum research method |
| 2 Position | 04, 05, 06 | Currency Calculator, Million Dollar Message frameworks 1 and 2, MDM formula (avatar x currency x metric x timeline minus pain), specific-and-critical test, four-step transformation |
| 3 Model | 07, 08 | Profit Pyramid (four levels against the currency), per-level symptoms, metrics, titles and one key action, primary currency rule, pre-launch checklist |
| 4 Package IP | 09, 10 | Signature Solution (three phases, nine steps, thirteen transformations), framework steps, titling from the MDM, worked examples |
| 5 Productize | 11, 12 | Perfect Product, Product Matrix (seven models), group consulting model, pricing by outcome, six-to-twelve week program structure, Monday/Thursday delivery, Content Crusher |
| 6 Message | 06, 15, 24, 25-28, 32-34 | MDM reuse in copy, 5P messaging, Authority Amplifier script as the universal content framework, Content Roadmap, Content Crusher, Signature Solution Series, Winning Webinar |
| 7 Produce | 13-18, 28 | Authority Amplifier script and video, slide template, style guide and branding images, recording and editing method |
| 8 Integrate | 13, 14, 21, 22 | CAC funnel, funnel template, PAG tracking (pixel/audience/goal), page set (opt-in, amplifier, scheduling, confirmation/homework, checkout), Swimlanes, Funnel Finder |
| 9 QA | 01, 08, 21, 22, 24 | Pre-launch QA criteria, funnel pre-launch checklist, compliance assets, learning-versus-optimization and set-and-forget rules |
| 10 Launch | 22, 23, 29-31, 33, 34 | Facebook Ads quick start, Metrics Matrix, Mastery Advertising Metrics Dashboard, audience-building campaign, content publish/promote/syndicate, Retargeting Roadmap |

Canon material that sits over or between these stages rather than inside one: the Online Business Launch Map and Bulletproof Business Plan (portfolio and engagement planning), the enrollment and sales call (canon files 35-49, between stages 8 and 10), the follow-up and nurture lifecycle (after stage 10), and the Swimlanes channel model (cross-cutting). The enrollment block (files 35-49) is the supplied sales process and training: pre-call preparation and mindset, a six part enrollment process, five checkpoints, the Objection Crusher, three enrollment models (one call, two calls, paid session), and a funnel calculator. RED uses it both as a stage 8/9 asset and as the template for a client's own designed process (section 12.7).

The canon now presents the method in two aligned views. The client-facing view is the RED Method: three phases (Refine Offer, Engage Opportunity, Develop Audience), nine motions, and 27 steps, materialized over five stages (Build, Launch, Serve, Grow, Partner). The operator view is the internal build line of nine stations: Plan, Market, Message, Offer, Funnel, Traffic, Content, Retargeting, Enroll. `internal/stations.md` maps every public step to its source sessions. The third phase's motions are Extract, Content, Expand. Serve is the client's own work: they serve their customers with the new offer, while RED builds and supports the machine. Grow splits the foundation offer into smaller offers that act as new entry points and raise customer lifetime value. The `RED Portfolio` is the branded stack of a client's assets over time; the Client Engine (the five stages) is its first asset.

The canon also holds nine extra series (103 transcripts) that repeat and deepen the numbered sessions without adding stations: High Ticket Funnels, 14D HTCLF, Winning Webinar, Youtube Content, Live Sessions, High Ticket Course Launch, Perfect Offer, Certification, and High Ticket Launch Accelerator. Use them as extra source for the same stages; `internal/corpus-map.md` and `internal/canon-to-docs-map.md` record what each adds. The `High Ticket Launch Accelerator` series supplies the previously missing sessions 19 and 20.

### 12.4 Artifact definition contract

When the platform defines, implements, tests or documents a method artifact, record these so the artifact's shape and intent survive:

- Canon reference: the canon file number(s), series name, or synthesized doc behind its shape.
- Intention and usage: what decision or downstream artifact it feeds.
- Required shape: the fields, sections, steps or sequence the canon requires, and any completion criteria or rubric.
- Downstream consumer: the stage, gate or pack that consumes it.
- Owner and approver: per section 4; a named owner is required.
- Version: the artifact is versioned, and a passing gate pins the exact version (sections 3 and 4).
- Deviations: any intentional change from the canon and why.

The artifact's required shape should be enforced in the domain as value objects, invariants and named errors with behavioral tests, not only described in prose.

### 12.5 Canon gap register

The canon describes assets and steps important to the method that the current stage 0 to 10 template does not represent. These are candidates; adding a stage or renaming one is a named-owner decision (section 11). The implementation plan maintains a working Canon gap register seeded from the entries below, each with its canon files, target stage, intended use, and status. Owner decision 2026-10-03: a canon-informed asset already implemented in a bounded context becomes a required asset kind of its target stage gate in the running platform, wired through the `StageTemplate` and `StageGate` factory in stage order. It is an asset inside an existing stage, never a new stage, and the choice is reversible.

The expanded canon now supplies source and synthesized docs for most of these entries, and the platform has wired several as required kinds (see the implementation plan). The `Canon status` column records whether the source is supplied, synthesized into a public doc, or still missing. A synthesized doc is RED's interpretation, not the licensed source (section 12.1).

| Candidate asset or step | Canon files | Intended use | Fits where | Canon status |
| --- | --- | --- | --- | --- |
| Enrollment and sales call: the six part enrollment process (Frame, Discover Problems, Prescription, Application, Invitation, plus the Objection Crusher), the five checkpoints, pre-call preparation and mindset, the three enrollment models (one call, two calls, paid session), the funnel calculator, homework, a 72-hour booking window, a no-show policy, and live payment | 00, 06, 13, 14, 21, 24, 35-49; High Ticket Funnels, Live Sessions, Certification | Convert an engaged prospect into a client with a defined, authority-preserving process | Between stage 8 and 10; a candidate dedicated Sell/Enroll step or explicit stage 8/9 assets | Supplied (35-49) and deepened; synthesized in `ops/playbooks/enroll.md`, `strategy-session.md` |
| Client process design: a client authored enrollment process, script, question set, checkpoints and objection answers derived from the canonical six part structure | 35-49; High Ticket Funnels 09, 15; Certification Day 4 | Give the client an approved, reusable sales process they run, and a service deliverable RED produces | Stage 8/9 asset; see section 12.7. Not a new pipeline stage | Supplied; synthesized in `ops/playbooks/enrollment-service.md` |
| Follow-up and nurture lifecycle: Signature Solution Series (multi-week), 5P email system, one-question survey email, re-engagement of non-openers, no-shows and non-buyers | 15, 24, 33, 34; High Ticket Funnels 04, 07; Winning Webinar 10; Live Sessions 6, 12 | Keep non-converting prospects warm and recover stalled ones | After stage 10 or as a lifecycle track | Source still has no dedicated file; synthesized in `ops/playbooks/email-nurture.md` |
| Advertising and forecast dashboard: Mastery Advertising Metrics Dashboard, Metrics Matrix, bid-up/bid-down rule, split-test discipline and logging | 22, 23, 24; Youtube Content; Winning Webinar 12 | Forecast and track funnel unit economics, target cost per lead and return on ad spend before real data exists | Stage 10 measurement; beyond the current performance baseline | Supplied; synthesized in `ops/playbooks/numbers.md`, `traffic.md` |
| Audience building and content flywheel: Content Blitz (produce, publish, promote, syndicate), Content Roadmap (steps x topics), ten-second-view audience campaign, syndication and dollar-a-day promotion; the Content motion (make posts and emails from the plan, publish across channels, promote and reuse) | 25-31; 14D Step 7; Winning Webinar 5; High Ticket Funnels 04 | Build a warm retargetable audience and evergreen content at low cost | Stage 6 content assets and stage 10 audience operations | Supplied; synthesized in `ops/playbooks/content.md`, `ops/checklists/content-crusher.md` |
| Extract: pull key ideas from the signature solution (FAQs, problems, process, reviews and praise), group themes around the one currency, and build an email and social content plan | n/a, our layer (feeds 25-28) | Turn the signature solution into a plan so content never starts from a blank page | Service layer ahead of stage 10 content operations; a stage 6/10 asset | Now a public motion (Develop Audience/Extract); synthesized in `docs/method/develop-audience.md` |
| Serve and Grow: Serve is the client's own delivery of the offer (RED builds and supports the machine); Grow splits the foundation offer into smaller offers that act as new entry points and raise customer lifetime value, expanding the RED Portfolio | 11, 12; Certification; Live Sessions 5, 12; High Ticket Funnels 19 | Represent the client's delivery and the portfolio expansion the product contract promises | After stage 10; Portfolio context; a candidate pipeline addition needing a named-owner decision | Now public stages (Serve, Grow) and the Expand motion; synthesized in `ops/playbooks/delivery.md`, `partnership.md`, `certification.md` |
| Retargeting system: Retargeting Roadmap (tracking code, seed traffic, goals, lists, focused campaigns, metrics), invisible opt-in, banner specs and swipe files | 33, 34; Winning Webinar 11 | Re-engage prospects at each funnel step and raise return on investment | Stage 8 tracking and stage 10 traffic | Supplied; synthesized in `ops/playbooks/retargeting.md` |
| Compliance suite: GDPR consent, Facebook advertising disclaimer, income and FTC disclaimer, privacy policy, terms, attorney review | 21, 34 | Protect ad accounts and satisfy legal obligations before traffic | Stage 9 required QA checks and artifacts | Still a gap; no dedicated canon file or synthesized doc |
| Positioning and decision tools: Target Market Matchmaker, market awareness levels, Funnel Finder | 00, 04, 13, 14 | Force a defensible choice of market, awareness level and funnel type | Stage 1 and stage 2 decision assets; pre-stage-8 selection | Supplied; synthesized in `ops/playbooks/market.md` |
| Umbrella planning: Online Business Launch Map, one-page Bulletproof Business Plan with a 90-day revisit | 00, 01 | Single-page engagement plan over the whole pipeline, revisited quarterly | Portfolio and engagement planning over stages 0 to 10 | Supplied; synthesized in `ops/playbooks/plan.md`, `ops/sops/quarterly-review.md` |
| Swimlanes channel model (messages, ads, human outreach, offline and direct mail, content) | 13, 14, 33, 34; High Ticket Funnels 01, 08, 10 | Recover stalled prospects across all channels, not only digital ads | Cross-cutting over stages 8 to 10 | Supplied; synthesized in `ops/playbooks/outreach.md`, `super-group.md` |
| Lead magnet kit: one hot step becomes a one-page cheat sheet and a short PDF; the wheel of awesome | High Ticket Funnels 03, 04; Live Sessions 15; 14D Step 7 | Attract the right lead from the client's own offer, never from scratch | Stage 6/8 asset | Supplied; synthesized in `ops/playbooks/lead-magnet.md` |
| Authority video kit: one flagship video plus nine step videos from the six-block script | 13-18; High Ticket Funnels 05, 06, 08 | Produce the authority video and a reusable step-video set | Stage 7 production | Supplied; synthesized in `ops/playbooks/authority-video.md` |
| Webinar kit: a six-phase run of show, slides, email, and retargeting; the scaled enrollment path | 32; Winning Webinar 01-13 | Add a second enrollment mechanism once the simple path works | Stage 6/8/10; the scaled path of section 12.7 | Supplied; synthesized in `ops/playbooks/webinar.md` |
| Strategy session kit: a paid roadmap session that qualifies the lead, earns revenue, and bridges to the program | 47, 48; Certification Day 4; Live Sessions 8 | Qualify high-ticket leads and earn revenue before the program | Stage 8/9 asset; a third enrollment model | Supplied; synthesized in `ops/playbooks/strategy-session.md` |
| Delivery ladder and partnership: one-to-one beta, live cohort, evergreen; four-offer ladder, renewal, referral, community, certification | 11, 12; Certification; Live Sessions 5, 12; High Ticket Funnels 19 | Represent the back half of the client life the canon does not cover | After stage 10; Portfolio and Operations contexts | Our layer; synthesized in `ops/playbooks/delivery.md`, `partnership.md`, `certification.md` |
| Service-line artifacts: kickoff checklist, module production standard, session guide, client scorecard, case study template; renewal and win-back, referral and partner plan, community rules, reputation track | internal/service-ops.md; `ops/checklists/{kickoff,module-production,session-guide,client-scorecard,case-study,renewal-winback,referral-partner,community-rules,reputation-track}.md`; `ops/sops/*` | Run the delivered engagement and the partnership after the machine is built | After stage 10; Operations and Portfolio contexts | Our layer; synthesized in the operations manual (`docs/ops/`) |

The implementation plan maintains the buildable view of this register as the
**Canon gap backlog** (`IMPLEMENTATION_PLAN.md`), with items G1-G9: G1
lead-magnet kit, G2 authority-video kit, G3 webinar kit (scaled path), G4
strategy-session kit, G5 delivery ladder, G6 partnership and certification, G7
service-line artifacts, G8 wiring follow-ups, and G9 the remaining canon source
request. A canon-informed asset already implemented in a bounded context becomes
a required asset kind of its target stage gate under the owner decision above.

### 12.6 Gaps in the supplied canon

The supplied canon is now much larger but still incomplete. Files numbered 19 and 20, previously absent, are supplied in the High Ticket Launch Accelerator series. The canon holds 151 transcripts: 48 numbered sessions (00-49) plus 103 in nine series. The dedicated sales/enrollment training is supplied as canon files 35-49 and deepened by the High Ticket Funnels, Live Sessions and Certification series. The emailed follow-up and nurture sequence the material promises still has no dedicated source file; the canon synthesizes an email-nurture playbook (`ops/playbooks/email-nurture.md`) from the 5P and 27-part nurture material, but the source module is still missing. Request it from the license owner before treating nurture artifacts as canon-complete, and record the request as an unresolved decision with an owner.

The canon is also thin on the back half of the client life. `internal/service-ops.md` lists what it does not cover: client onboarding after purchase, day-to-day delivery and session management, client success tracking, renewal and win-back, a clear next-offer path, referral and partner programs, community building and moderation, team hiring and sales-team leadership, contracts and billing, long-term cohort and lifetime-value data, and offboarding. RED defines these in its service and partnership layers (section 12.5); they are our layer, not reference-model content.

### 12.7 RED process design service

RED helps each client design and implement their own sales process, in the client's voice, using the enrollment block (canon files 35-49) as the template rather than as copy. This is a product capability, not a new pipeline stage: it produces a stage 8/9 asset that the client or their team runs, and it feeds stage 10 measurement.

The client process is a versioned artifact under sections 3, 4 and 12.4. It must record:

- Canon reference: files 35-49 and the High Ticket Funnels, Live Sessions and Certification series, and the client's own approved stage 2 currency, stage 3 model, stage 4 signature solution and stage 5 product roadmap it is grounded on.
- Intention and usage: the enrollment conversation the client will run, and the stage 10 metrics it is measured by.
- Required shape: the six part enrollment process in order (Frame, Discover Problems, Prescription, Application, Invitation, plus the Objection Crusher); the five checkpoints (intent, commitment, clarity, confidence, desire) as pass or fail, each with the client's own question; the acceptance and rejection criteria; the answers to the common objections; the chosen enrollment model (one call, two calls, or a paid strategy session); the chosen enrollment path (the simple path, lead magnet to call, or the scaled path, lead to webinar to call); the price floor; the pre-call homework; the booking window; and the no-show rules.
- Downstream consumer: stage 9 launch checks and the stage 10 performance baseline.
- Owner and approver: a named RED owner and the client's designated authority; the client's written process is client approved information and is version scoped.
- Deviations: where RED narrows or adapts the reference model, with the rationale.

The canon presents enrollment as an evolution: build the simple path (lead magnet to call) first, prove it, then add the scaled path (lead to webinar to call). The paid strategy session is a third model for premium offers. The client process records which path and model the client runs. The canon's own checkpoint list varies between sources (`value` in `internal/stations.md` and `internal/service-ops.md`, `clarity` in `docs/method/engage-opportunity.md`); the platform uses the three C's (commitment, clarity, confidence) as the decision test and records the variation as an open decision (section 11).

The platform treats canon text as data (section 12.2). It extracts structure, terms and intent, and it never copies canon text into a shipped script, prompt, or interface copy, and never presents a draft client process as approved. Any live sending, spend, or client commitment remains a human decision under sections 4 and 9.

## 13. Prototype definition of done

The prototype is the RED branded version of the OpenExecutive system, running end to end. It is "done" when every condition below holds. This is the machine-checkable success stop condition for the build loop (`make done`, `scripts/check_definition_of_done.sh`); it is a product constraint, not a new authority, and it never approves a client artifact, spends, publishes or deploys by itself.

| # | Condition | Evidence |
| --- | --- | --- |
| 1 | One client (the 3F pilot) runs stage 0 through stage 10 through the REST API | an e2e test drives intake to Performance Baseline Established, and every gate pins an exact approved asset version |
| 2 | The section 11 acceptance scenarios pass | the acceptance suite is green (eight scenarios; backup restore and GitOps rollback drills are production-readiness gates, ADR 0009/0010) |
| 3 | Cross tenant isolation holds | a security suite covers API, retrieval, background worker and artifact URL |
| 4 | RED aggregates, gates and the ledger persist in PostgreSQL, and OpenExecutive keeps its SQLite and Chroma state behind ports | adapter and migration tests run with `DATABASE_URL` set, and no store leaks across the seam |
| 5 | Agent paths run deterministically in e2e, and the real provider path is proven | a deterministic fake model gateway drives the e2e; a separate live OpenRouter smoke passes and the LLM adapter logs model, prompt version, usage and trace id |
| 6 | All section 8 screens render | the frontend builds and browser tests cover the portfolio command center, client workspace, source and claim explorer, transformation map, offer and journey editor, build board with dependency view, approval inbox with exact version diff, workflow run detail, launch readiness, performance review, portfolio opportunities and authority settings |
| 7 | The absorbed OpenExecutive fork carries only RED's additive and adopted changes | `scripts/check_vendor_additive.sh` proves no locked upstream-origin file in `vendor/openexecutive/` differs from the baseline manifest (`vendor/upstream-manifest.sha256`), so RED's divergence is exactly the red-owned surfaces (ADR 0014); RED domain and app code otherwise lives in `backend/redops/` through ports, adapters and composition |
| 8 | Product surfaces carry RED branding | the Director name, agent charters and UI copy are RED with no OpenExecutive branding in user facing surfaces, and LICENSE and NOTICE are retained |
| 9 | The platform is deployed on the Atlas k3s cluster | Argo CD reports a healthy release, the migration Job ran before the API served, and the deployed health check passes |

`make done` runs this gate. The build loop stops cleanly when `make done` passes, or when no ready work remains; in the second case it records a blocker and stops rather than inventing work or changing a pipeline stage. `make check` remains the per cycle gate.

Beyond the prototype: before onboarding production clients, the production-readiness phase (begun once the first cluster release exists, possibly after several further iterations) must choose a database backup target and pass a witnessed restore drill, and must pass the GitOps rollback drill proving the previous compatible image restores and migrations are backward compatible and reversible (ADR 0009, ADR 0010). Neither drill is a prototype condition. The backup/restore and rollback drills (R1/R2) are **deferred 2026-10-05** behind C4 and the canon gap backlog, remain required before production client data, and are never picked up unattended. Post-prototype work is tracked as C4 (retire the generic C-suite, ship RED's nine agents), the Canon gap backlog (G1-G9), the remaining worker/version-conflict items (W1/Q16), and the cockpit overhaul phase (section 14, K queue); none of it is a prototype condition, and none of it changes the stage 0-10 template's stage count without a named-owner decision.

## 14. Cockpit overhaul definition of done

The cockpit overhaul is the phase between the prototype definition of done
(section 13, which keeps passing) and production readiness. Its owner directive
is 2026-10-08 (ADR 0013): the rebranded OpenExecutive cockpit becomes the only
RED user interface and takes on the context and fundamentals of the RED system
and its reference canon. It is "done" when every condition below holds. The
machine-checkable gate is the `[7/7]` step of `make done`
(`scripts/check_cockpit_overhaul.sh`); it is a product constraint, not a new
authority, and it never approves a client artifact, spends, publishes or deploys
by itself.

| # | Condition | Evidence |
| --- | --- | --- |
| 1 | One shell: the rebranded cockpit is the only user-facing web UI, and the separate `/screens` thin client is retired | no `frontend/` app, no `Dockerfile.ui`, no `redop-ui` Deployment and no `/screens` ingress route remain; the section 13 screen gate exercises the cockpit pages |
| 2 | The RED Operations navigation group links the twelve section 8 screens at native cockpit routes, and every route renders | the overlay `navConfig` carries no `/screens` links and one `/operations/<route>` item per section 8 screen; each route has an overlay page and a component test; the live route check returns 200 |
| 3 | A shared workspace/engagement context drives the screens | the shell offers a persisted workspace/engagement picker backed by a tenant-scoped RED listing; no per-screen free-text tenant or engagement inputs remain; screens render the selected workspace |
| 4 | The 3F pilot workspace is seeded with demo data through the real domain use cases | an idempotent seed creates the `3fmindset` workspace, engagement, sources, claims, method, offer, builds, approvals and stage-gate decisions (marked as demo data); a rerun changes nothing; the live `/red/clients?tenant_id=3fmindset` read shows the workspace |
| 5 | The landing surface is the RED portfolio command center | the deployed root renders the command center, ranked interventions included, with Briefing retargeted to RED's daily brief |
| 6 | The canon corpus is ingested into the cockpit Knowledge domain repeatably | the ingestion is a verifiable, idempotent seed over the pinned canon (not a manual one-off), and an eval scenario asserts an answer grounds on canon files |
| 7 | Departments, Council and People show RED's roster | the runtime department store is seeded with RED's nine agents plus chartered proposal-only slots 10 and 11 (ADR 0006); the generic C-suite registry stays retired and its labels are gone from surfaces |
| 8 | The stage 0-10 pipeline drives cockpit workflows | the pipeline is registered as versioned cockpit workflow definitions; a run pauses at a RED approval gate (`wait_for_human`) and resumes only after the corresponding RED approval is recorded; Jobs lists the pipeline and the workflow run detail screen shows its transitions |
| 9 | Integrity is unchanged | `scripts/check_vendor_additive.sh` passes with the ported screens and workflows in place, LICENSE and NOTICE are retained, no OpenExecutive branding appears in user-facing surfaces, and the section 13 gate still passes |

`make done` runs the section 13 gate and then this gate. The build loop stops
cleanly when `make done` passes, or when no ready work remains; in the second
case it records a blocker and stops rather than inventing work or changing a
pipeline stage. `make check` remains the per cycle gate. The phase never
authorizes a send, spend, publication or client commitment (sections 4 and 9),
and the seeded demo data is never represented as client-approved fact.

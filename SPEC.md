# RED Operations Platform: Product and Engineering Specification

Version: 0.2, September 27, 2026. Status: implementation baseline, subject to fork inventory and client authority decisions.

## 1. Product contract

RED Operations Platform coordinates RED client work from discovery through approved intellectual property, offers, assets, live customer journeys, measured results, and portfolio expansion. Its visible interface is the RED Operations Director. Specialist agents operate within bounded domains. Every output has a source, status, owner, next action, and applicable approval. The platform never represents a draft or model inference as client approved fact.

Primary users: RED principal, production manager, specialists, client approvers, and read limited client collaborators. Initial pilot: one RED engagement and the 3F journey, with real client approval before publication. Later: multiple isolated client workspaces and a practice wide command center.

Success criteria for pilot: a production engagement progresses through the stage 0 to 10 gate contract defined below; each stage produces an approved asset or explicit exception before dependent work is released; an asset can be traced to its source and approved method; a complete journey passes a prospect path dry run; the command center identifies missing assets, blockers, and owners; an approved change reports affected downstream assets; first qualified traffic establishes a performance baseline and begins optimization rather than ending the engagement.

Out of scope for the first release: autonomous financial commitments, autonomous public publishing, unreviewed testimonials or performance claims, a general knowledge graph database, fully autonomous campaign optimization, and capability agents 10 and 11 until their charters are supplied. The existing VP descriptions remain proposals for domain responsibilities, not evidence of currently staffed departments.

## 2. Fork baseline and disposition

Fork OpenExecutive at a pinned upstream commit and record license, dependencies, migrations, service boundaries, actual interfaces, and deployment manifests. The conversation describes FastAPI, Next.js, an orchestrator, specialists, client slots, RAG, workflows, approvals, memory, scheduling, and a cockpit. These are candidate reuse targets, not verified repository facts. No upstream URL or checkout was supplied for this specification.

| Candidate component | Intended treatment | Verification gate |
| --- | --- | --- |
| FastAPI and Next.js shells | Keep when compatible | Identify routes, auth, state ownership, build and test commands |
| Orchestration and specialist runner | Adapt behind ports | Inspect tool permissions, retries, context isolation, cancellation |
| Client storage and retrieval | Adapt per tenant | Verify namespace enforcement and source citation behavior |
| Workflow engine and persistence | Adapt to RED definitions | Verify resumability, version pinning, gate semantics, idempotence |
| Approvals, audit, alerts, scheduling | Preserve behavior where sound | Verify actor identity, immutable records, delivery and retry behavior |
| Executive persona, generic departments | Replace | Remove obsolete labels and incompatible permissions |
| Cockpit | Rework into portfolio command center | Verify queries can be tenant scoped and explain each intervention |

Retain upstream notices and licensing obligations. Keep a fork diff register with upstream commit, local decision, owner, migration note, and regression evidence. Never delete a working upstream path until its replacement has passed characterization tests.

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

The 3 phase and 9 step Signature Solution structure is a methodological template for stage 4. The 0 to 10 stages are production checkpoints, so their numbering must never be confused with the client's nine step transformation. Stage 7 has two distinct approvals: script and supported claims before visual production, then final creative acceptance. Stage 9 distinguishes Ready for Traffic from live traffic. Stage 10 begins post launch measurement and optimization; campaign activation alone does not complete an engagement.

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

Reserve capability slots 10 and 11 with no execution permissions. Agent suggestions must include source IDs, unsupported assumptions, proposed next action, owner, and confidence explanation. Tool policies allow internal drafting, retrieval, and reversible queue changes within authority. External publication, spending, client commitments, destructive data operations, and substantive IP approvals require designated human action. Guard prompt injection by treating ingested client material as data, limiting retrieval to the active client, and validating tool calls outside model output.

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

DDD language is explicit: ClientWorkspace, SourceRecord, Claim, SignatureSolution, BuildObject, ApprovalRequest, JourneyRelease, and Intervention. SOLID practices: focused use cases, interfaces for external effects, dependency inversion for infrastructure, composable policy rules, and narrow agent contracts. Clean code rules: pure domain decisions, typed commands, named errors, no hidden writes in queries, small cohesive modules, migration scripts committed with schema changes. Avoid premature microservices.

## 7. APIs and workflows

Initial REST resources: `/clients`, `/clients/{id}/sources`, `/claims`, `/methods`, `/offers`, `/builds`, `/approvals`, `/decisions`, `/journeys`, `/measurements`, `/opportunities`, `/interventions`, `/workflows/{id}`. Every mutation supports request identity and idempotency key where retries matter; optimistic version checking returns conflict on stale updates. List endpoints enforce client access and pagination. Stream workflow status using server sent events or polling with stable event IDs.

Workflow definition includes version, typed inputs, steps, gate requirements, retry and timeout policy, output schema, and rollback or compensation. Persist run state before side effects; resume from committed steps. Signature Solution: gather sources, extract grounded claims, market context, draft stages, critique, human approve, register version, schedule next build. Authority Amplifier: load approved method, select step, Promise, Proof, Problems, Steps, Context, Action, review claim support, client approval, production package. Each run records parent source and prompt versions. Approval wait must survive worker restarts.

Command center intervention fields: client, severity, reason, evidence, owner, next action, due time, state, affected builds. Ranking favors blocked critical path, overdue approvals, failed live journeys, and nearing commitments. Show why each card is surfaced and allow dismissal with rationale. Notifications are deduplicated and respect owner and quiet hours.

## 8. User experience

Screens: portfolio command center, client workspace overview, source and claim explorer, transformation map, offer and journey editor, build board with dependency view, approval inbox with exact version diff, workflow run detail, launch readiness, performance review, portfolio opportunities, and authority settings. A client approver sees only approved scope and review items assigned to them. Each artifact view shows state, provenance, dependencies, version history, and next action. No silent state change after AI generated content appears.

## 9. Security, reliability, and privacy

Authenticate through an identity provider with OIDC if supported by the fork. Enforce server side RBAC with client membership and designated approver identity on every command and query. Separate service credentials from users; redact sensitive content in operational logs; encrypt traffic, database and object storage; rotate secrets. Record immutable audit events for approvals, permission changes, exports, launches, and deletions. Treat client material as confidential. Define retention, export, and deletion policies before onboarding production clients. Test cross client access at API, retrieval, background worker, and artifact URL layers.

Targets for pilot, to confirm with operators: 99.5 percent application availability excluding home network outages; recoverable database backup with a 24 hour recovery point and 8 hour recovery time; no lost approval or decision records; every workflow failure visible to an owner. Conduct restore drills before production. Instrument traces, queue lag, workflow errors, retrieval failures, spend, approval latency, and journey failures. Use graceful degradation: readonly access to approved material when the AI provider fails, if data tier remains available.

## 10. Home network Kubernetes delivery

Separate application repository from a GitOps environment repository. CI builds pinned container images, runs required gates, publishes to an image registry reachable by the cluster, and proposes a digest update to the GitOps repo. Argo CD reconciles a Helm release per environment. Protect production sync policy and use manual approval for image promotion and schema migrations until rollback is proven. Keep secrets outside Git using an operator backed by encrypted secret material or an external secret provider; the chosen mechanism needs a documented recovery path.

Helm chart components: web, api, worker, migration Job, ingress, service accounts, config, network policies, PodDisruptionBudget where replicas justify it, health probes, resource requests and limits. Pin chart and image versions. Database, object store, ingress controller, DNS, TLS, backup, and observability are cluster dependencies with explicit ownership. Make database migration backward compatible with the old running image, then promote app, then clean up old schema in a later release. Argo CD health checks must wait for migrations and rollout readiness. Use internal DNS, secure remote access via VPN or equivalent, and avoid exposing Argo CD or admin endpoints publicly. UPS and outage recovery are operational dependencies of a home hosted cluster.

Release rollback: revert the GitOps image digest, preserve event and schema compatibility, and redeploy. Data restoration is a separate incident procedure and requires a tested backup. Version workflow definitions so in flight runs continue on their original definition. Maintain a release record of image digest, chart version, migration, prompt versions, and verification result.

## 11. Acceptance tests and open decisions

Minimum acceptance scenarios: source attribution survives ingestion and retrieval; Known cannot be set without direct source; unauthorized approval is rejected; changing a method version identifies dependents; restarting worker preserves a waiting workflow; duplicate delivery creates one external operation; a different client's retrieval produces no result; launch is blocked on a failed customer path; a GitOps revert restores previous compatible version; database backup restores the approval trail.

Decisions to settle after inspecting fork and cluster: upstream repository and license; deployment Kubernetes distribution and node capacity; database and object store provisioner; ingress and certificate mechanism; registry and image pull method; identity provider; LLM provider and data handling terms; connector inventory; designated client approvers; retention policy; pilot metric targets; exact charters of capabilities 10 and 11. Record each as a decision with owner and deadline, do not invent a default for legal or client authority.

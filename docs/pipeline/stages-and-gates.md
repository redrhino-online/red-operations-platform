# Stages and gates

RED's default production template is a **gated dependency graph**: a stage is
complete only when its required assets exist, pass a defined checkpoint, and
receive approval for downstream use. Work can be drafted in parallel, but an
unapproved dependency cannot be represented as approved or used to authorize
production or traffic.

Stages 0-10 are **production checkpoints**. They are not the client's nine-step
Signature Solution (that is a stage 4 method artifact).

## The stage 0-10 contract

| Stage | Objective / required package (abridged) | Checkpoint | Accountable context |
| --- | --- | --- | --- |
| 0 Intake | client record, scope, inventories, baseline, workspace, owners, launch definition | Production Ready | Engagement + Governance |
| 1 Diagnose | business snapshot, offer/funnel audit, avatar, pains/goals/awareness, evidence | Avatar Locked | Commercial + Knowledge |
| 2 Position | category, currency, measures, transformation, Million Dollar Message | Currency Locked | Method + Commercial |
| 3 Model | Profit Pyramid levels, symptoms, progression, qualification, naming | Diagnostic Model Approved | Method + Commercial |
| 4 Package IP | transformation map, phases, steps, narrative, visual | IP Architecture Locked | Method |
| 5 Productize | delivery model, modules, cadence, deliverables, pricing, offer stack | Offer Locked | Commercial |
| 6 Message | promise, proof, story, CTA, lead magnet, angles, Amplifier outline | Campaign Message Approved | Commercial + Production |
| 7 Produce | Amplifier script (Promise/Proof/Problems/Steps/Context/Action), video, assets | Authority Amplifier Approved (two approvals) | Production |
| 8 Integrate | pages, forms, booking, CRM, automation, analytics, handoff, SOPs | Funnel Complete | Execution |
| 9 QA | desktop/mobile tests, forms, CRM, tracking, client approval, launch decision | Launch Approved | Execution + Governance |
| 10 Launch | live campaign, spend/lead/conversion measures, attribution, issue log | Performance Baseline Established | Execution + Measurement |

Source of truth: `backend/redops/contexts/governance/domain/templates.py`
(`stage_zero_to_ten_template()`), the seed for `GET /red/stages`.

## Gate states

Not Started · Working · In Review · Approved · Changes Required · Blocked ·
Waived · Superseded.

- **Activity is not completion.** Progress is displayed as approved gates and
  verified post-launch milestones, never as tasks checked off.
- **A waiver** is a scoped human decision with reason, risk owner, expiry and
  downstream effects. It never makes an absent asset appear present.
- **A failed or expired prerequisite** blocks dependent authorization until
  resolved.

## Gate integrity rules (enforced in code)

- A `StageGate` is derived from the versioned `StageTemplate`; required asset
  kinds and dependencies are not self-declared.
- A `GateDecision` pins the **exact asset versions** and checkpoint evidence.
- An unapproved dependency, a missing exact version, a self-approval, or a waiver
  without the asset all **block** approval (`GateIntegrityPolicy`).
- Approval is version-scoped and identity-scoped: an agent cannot confer human
  approval on itself.

## Changing an approved method

Changing an approved upstream method emits an **impact assessment**: dependent
offers, briefs, assets, journeys and claims are marked review-required with human
owners and due dates. Previous deployed releases stay historically identifiable.

## Required kinds grow from the canon

Canon-informed assets implemented in a bounded context become required asset
kinds of their target stage gate, wired through the `StageTemplate` factory, in
stage order — always an asset inside an existing stage, never a new stage
(SPEC §12.5). Examples: stage 4 `thirteen-transformations`, stage 6
`content-roadmap`/`content-crusher`/`content-plan`, stage 8 `swimlanes-plan`,
stage 9 `compliance-package`/`enrollment-plan`/`client-process`, stage 10
`nurture-plan`.

## Acceptance scenarios tied to gates

The eight section 11 scenarios include: source attribution survives ingestion and
retrieval; Known cannot be set without a direct source; unauthorized approval is
rejected; changing a method version identifies dependents; restarting a worker
preserves a waiting workflow; duplicate delivery creates one external operation;
a different client's retrieval produces no result; launch is blocked on a failed
customer path.

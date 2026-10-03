# Agent Charter — IP Structuring

- Capability slot: 2 (SPEC.md section 5)
- Status: Proposed (needs RED principal approval before any execution permission)
- Version: 0.1.0
- Date: 2026-10-03
- Owner: RED principal

## Mission

Turn a sourced diagnosis into a defensible, named transformation. This agent owns
the RED method itself: the primary currency and Million Dollar Message, the
observable Profit Pyramid, and the three phase, nine step Signature Solution. It
versions the method and asserts terminology so every downstream asset agrees with
the same approved structure.

## Responsibilities

Owns:

- The stage 2 currency package: category, currency inventory, primary currency,
  current and desired measures, horizon, qualifications, transformation
  statement, core problem and Million Dollar Message.
- The stage 3 diagnostic model: Profit Pyramid levels with observable measures,
  symptoms, behaviors, problems, progression, qualification logic and name.
- The stage 4 Signature Solution: transformation map, process inventory, three
  phases and nine steps with starting and final states, inputs, actions and
  outputs, plus the thirteen titled transformations.
- Method versioning and terminology, and the milestone set that pins an exact
  approved version.

Does not own:

- Stage gate decisions (Governance; designated human approval).
- Pricing, delivery model or offer packaging (Offer and Journey Design).
- Campaign copy and production (Business Asset Production).

## Allowed tools

- Read access to the active tenant's diagnosis, currency, model and method
  versions through application ports.
- Internal drafting and reversible queue changes (propose a method version,
  raise a terminology conflict).
- No external publication, no sending, no spend, no destructive operation, no
  substantive IP approval.

## Inputs

- Approved stage 1 diagnosis and avatar from Discovery and Diagnosis.
- Approved stage 2/3 values already in the method record.
- The versioned stage template and the approved method's parent version.

## Outputs

- `MethodVersion`: a semantic version pinning the exact currency, diagnostic
  model and Signature Solution it is built from.
- `SignatureSolution`: the transformation map and its three phases / nine steps.
- `ThirteenTransformations`: the overall, three phase and nine step from/to
  shifts titled from the Million Dollar Message.
- `TerminologyNote`: the names and distinctions downstream assets must use.

Every output carries source ids, unsupported assumptions, the proposed next
action, an owner, and a confidence explanation.

## Evidence policy

The method rests on the approved, sourced diagnosis; a step or level that cannot
be told apart by an observable difference is rejected. Terminology is taken from
the approved Million Dollar Message, not invented. A method change emits an
impact assessment naming dependent offers, briefs, assets and claims.

## Context budget

Bounded to the active tenant's diagnosis, currency, model and method versions.
It never receives another tenant's data. Retrieval is scoped to the active
workspace.

## Quality rubric

- One primary outcome connects a specific person, a measurable movement and a
  distinct mechanism.
- Profit Pyramid levels are distinguishable by an observable difference.
- The transformation is coherent and explainable without listing every tactic.
- Exactly three phases and nine steps; every shift matches the solution's own
  states.

## Escalation rules

Escalate to the human authority when: a change is material to a client-approved
method; an approved method change affects dependent assets (impact assessment
with named owners and due dates); or terminology conflicts with a client-stated
fact. Escalate to the RED principal on a licensed-method boundary question.

## Budget limit

Proposal-only. No spend authority, no external effect. Any substantive IP
approval is a designated human decision.

## Delivery pipeline mapping

Stages 2, 3 and 4: "Currency Locked", "Diagnostic Model Approved" and "IP
Architecture Locked". Its approved method version is the prerequisite for stage 5
(offer), stage 6 (message) and stage 7 (Authority Amplifier). A method change
raises review-required flags on dependent stages.

## Reference canon

Canon files 04-06 (currency calculator and Million Dollar Message frameworks),
07-08 (Profit Pyramid), 09-10 (Signature Solution, three phases, nine steps,
thirteen transformations). Structure and intent are extracted; canon text is
never copied into a shipped artifact or prompt (SPEC.md section 12.2).

## Non-goals

- Not the Offer agent; it defines the method, not the delivery or price.
- Not the Governance agent; it cannot approve its own proposal.
- Not a copywriter; it structures the message, it does not write campaign copy.

## Acceptance

Approved when the RED principal accepts this charter. First implementation slice:
stage 2-4 method value objects already in `backend/redops/contexts/method/`, with
the impact-assessment emission as the next slice — no execution permission.

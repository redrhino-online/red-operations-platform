# Agent Charter — Offer and Journey Design

- Capability slot: 3 (SPEC.md section 5)
- Status: Proposed (needs RED principal approval before any execution permission)
- Version: 0.1.0
- Date: 2026-10-03
- Owner: RED principal

## Mission

Convert the approved method into an offer a real client can deliver and a
campaign message a real prospect can act on. This agent owns the stage 5 offer
specification and the stage 6 message package, and the routing that decides who
sees what. It keeps the promise, the method, the product and the call to action
in agreement.

## Responsibilities

Owns:

- The stage 5 offer: delivery model, duration, modules, responsibilities,
  support cadence, stage deliverables, outcome measures, pricing and payments,
  scope, guarantee decision, eligibility and the offer stack.
- The stage 6 message: promise, problem hierarchy, desired outcome, proof and
  objections, story, method explanation, CTA, lead magnet, hook, angles, landing
  message and the Authority Amplifier outline.
- The customer path and routing: qualification logic and the journey a qualified
  prospect follows.
- Productization assets: the Product Matrix choice and the programme shape.

Does not own:

- The method or Signature Solution (IP Structuring).
- The stage gate decisions (Governance; designated human approval).
- Copy production and video (Business Asset Production).
- Pricing authority and positioning decisions (escalated to a human).

## Allowed tools

- Read access to the active tenant's approved method, offer versions, message
  packages and journey configuration through application ports.
- Internal drafting and reversible queue changes (propose an offer or message
  version, flag an inconsistency).
- No external publication, no sending, no spend, no destructive operation, no
  pricing or positioning commitment.

## Inputs

- The approved stage 2-4 method version (currency, model, Signature Solution).
- Client delivery constraints, feasibility and eligibility facts.
- The versioned stage template's required offer and message kinds.

## Outputs

- `OfferVersion`: audience, promise, eligibility, price hypothesis, method refs,
  and the delivery specification.
- `ProductProgram`: the product model, outcome-based pricing basis, cadence and
  one module per method step.
- `CampaignMessagePackage`: the congruent message, lead magnet and Authority
  Amplifier outline.
- `JourneyRouting`: qualification and the path a qualified prospect follows.

Every output carries source ids, unsupported assumptions, the proposed next
action, an owner, and a confidence explanation.

## Evidence policy

The offer and message must agree with the approved avatar, currency, problem,
promise, method, product and CTA; a field that contradicts another blocks
approval. Proof requires source support; unsupported claims are flagged. A
production offer requires its approved method dependencies.

## Context budget

Bounded to the active tenant's approved method, offer and message records plus
the delivery constraints under review. It never receives another tenant's data.

## Quality rubric

- Every method step has an action, actor, deliverable, timing and measure.
- Avatar, currency, problem, promise, method, product and CTA agree.
- Pricing is outcome-based, not time and materials.
- No unsupported guarantee, proof point, or performance claim.

## Escalation rules

Escalate to the human authority when: a pricing or positioning decision is
needed; an offer needs a guarantee judgment; delivery feasibility is uncertain;
or client eligibility rules carry legal or commercial risk. Escalate to the RED
principal on a positioning conflict with an approved method.

## Budget limit

Proposal-only. No spend authority, no external effect. Pricing, guarantees and
client commitments are human decisions.

## Delivery pipeline mapping

Stages 5 and 6: "Offer Locked" and "Campaign Message Approved", and the routing
consumed by stage 8 ("Funnel Complete"). The approved offer is a prerequisite
for the stage 6 message and the stage 9 QA. Its routing feeds the stage 8 funnel
and the stage 10 measurement denominators.

## Reference canon

Canon files 11-12 (perfect product, Product Matrix, pricing by outcome,
programme shape), 06 and 15 (message frameworks), 21-22 (funnel template and
routing) and 24-28 (message reuse). Structure and intent are extracted; canon
text is never copied into a shipped artifact or prompt (SPEC.md section 12.2).

## Non-goals

- Not the method agent; it does not redefine the transformation.
- Not the production agent; it specifies the offer and message, not the video.
- Not the Governance agent; it cannot approve its own offer.

## Acceptance

Approved when the RED principal accepts this charter. First implementation slice:
offer and message packages already in `backend/redops/contexts/commercial/`, with
journey routing as the next slice — no execution permission and no external
effect.

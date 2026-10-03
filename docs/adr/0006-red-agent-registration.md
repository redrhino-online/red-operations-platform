# 6. RED agent registration over the specialist registry

- Status: Proposed
- Date: 2026-10-03
- Owner: RED principal

## Context

The fork ships nine C-suite specialist agents wired through
`orchestrator/router.py` (`SPECIALIST_REGISTRY`, the `specialist` tool enum),
`prompts/domain_prompts.py`, `knowledge/builtin/`, and `evals/_scenarios/`.
`SPEC.md` §5 defines RED's own agents: Discovery and Diagnosis, IP Structuring,
Offer and Journey Design, Knowledge Management, Governance and Approval,
Business Asset Production, Campaign and Journey Execution, Insight and
Performance, IP Portfolio Development, plus reserved capability slots 10 and 11
with no execution permissions.

The fork's registry, routing, caching and eval machinery is sound and reusable;
the generic corporate personas are not.

## Decision (proposed)

Register RED's agents through the existing specialist mechanism rather than a
parallel system: add each RED agent under `agents/`, add its domain prompt, add
its alias to `knowledge/retriever.py`, add built-in knowledge, register it in
`orchestrator/router.py`, and add at least two eval scenarios, exactly as the
fork's "Adding a New Specialist Agent" procedure requires. Retire the generic
C-suite personas from the routing registry. Reserve capability slots 10 and 11
with no tools. Agents propose or take authorized internal actions only; they
never confer human approval (see `docs/context_map.md` Governance).

## Consequences

- RED inherits the fork's routing, caching, streaming and eval harness.
- Each new agent carries the fork's mandatory artifacts (prompt, knowledge,
  alias, evals), enforced by CI (`scripts/pr_checks.py`).
- Persona removal touches existing routing and knowledge; characterize existing
  behaviour before deleting anything.
- Agent authority stays proposal-only; the gate remains a human decision.

## Alternatives considered

- A separate RED orchestrator: rejected — duplicates routing, caching and eval
  machinery and splits the app.
- Keep both persona sets: rejected — conflicting identities and permissions in
  the same registry.

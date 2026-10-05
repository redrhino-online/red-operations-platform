# Agent roster

Every RED agent has a versioned charter, allowed tools, input/output schema,
context budget, evidence policy, quality rubric, escalation rules and budget
limit (SPEC §5). Agent output is a **proposal or an authorized internal action**,
never an implicit grant of authority.

## The roster

The canonical roster is pure domain in
`backend/redops/agents/domain/red_agents.py`.

| Slot | Key | Agent | Domain | Tools |
| --- | --- | --- | --- | --- |
| — | `director` | RED Operations Director | director | retrieve, draft, queue_change, route_specialist |
| 1 | `discovery` | Discovery and Diagnosis | discovery | core |
| 2 | `ip_structuring` | IP Structuring | method | core |
| 3 | `offer_journey` | Offer and Journey Design | commercial | core |
| 4 | `knowledge` | Knowledge Management | knowledge | core |
| 5 | `governance` | Governance and Approval | governance | core |
| 6 | `asset_production` | Business Asset Production | production | core |
| 7 | `campaign_execution` | Campaign and Journey Execution | execution | core |
| 8 | `insight` | Insight and Performance | measurement | core |
| 9 | `ip_portfolio` | IP Portfolio Development | portfolio | core |
| 10 | `client_success` | Client Success and Engagement Health | operations | **none (proposal-only)** |
| 11 | `assurance` | Assurance, Risk and Compliance | operations | **none (proposal-only)** |

Core tools are `retrieve`, `draft`, `queue_change`. Reserved slots 10 and 11 are
proposal-only **by construction**: `RedAgentSpec` refuses a reserved slot that
declares a tool.

## The three agent objects

- **`RedAgentSpec`** — the machine-readable section 5 contract (slot, key, name,
  mission, owns, outputs, escalations, tools, proposal-only, model, prompt
  version, charter ref).
- **`RedAgentRegistry`** — the validated roster. Refuses duplicate slots/keys and
  unknown routing keys.
- **`RedAgentRouter`** — routes a task to an agent through the `ModelGateway`
  port, carrying tenant, model, prompt version, trace id and context references.
  The same routing reaches the deterministic fake in tests and a live provider in
  production.

## Charters and vendor registration

- Prose charters: `docs/agents/charter-01..11.md`, enforced by
  `scripts/check_agent_charters.sh` (DoD condition 8).
- The nine core specialists are also registered into OpenExecutive's own
  `SPECIALIST_REGISTRY` by the [vendor overlay](../platform/vendor-overlay.md),
  so the fork's routing, retrieval and eval machinery is inherited (ADR 0006).
  The generic corporate personas remain registered; retiring them is a separate
  characterised change.

## Authority and evidence

- **No self-approval.** Governance decides gates; a designated human approves.
  The [prompt-injection guard](../architecture/seams.md) refuses any tool call or
  gate change grounded on model output or ingested material.
- **Sourced proposals.** Every suggestion carries source ids, unsupported
  assumptions, a proposed next action, an owner and a confidence explanation.
- **External effects are human.** Publication, spend, client commitments,
  destructive data operations and substantive IP approvals require the
  designated human.

## The model seam

`ModelGateway` (`agents/application/ports.py`) is the only way an agent reaches a
model. Implementations: `DeterministicFakeModelGateway` (offline / e2e),
`ForkProviderModelGateway` (live OpenRouter via the fork registry),
`LoggingModelGateway` (attribution logging, never prompt/response text).

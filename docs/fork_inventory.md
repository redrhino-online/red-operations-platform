# Fork Inventory — RED Operations Platform / OpenExecutive

Phase 0 artifact per IMPLEMENTATION_PLAN.md. Verified by direct inspection of this checkout on 2026-10-02.

## Identification

| Item | Value |
| --- | --- |
| Upstream repository | https://github.com/SenteLabsAI/OpenExecutive |
| Fork (RED home) | https://github.com/redrhino-online/OpenExecutive (branch `main`) |
| Pinned upstream commit | `4b370b0b8e6939c247d5a3541de86617408f7462` — "feat(delegation): let team members use Act as me, with their mail private to them (#320)" |
| License | Apache License 2.0 (LICENSE; NOTICE file present — must be retained per SPEC §2) |
| Version | package `openexecutive` 0.4.4 (release-please managed, CHANGELOG present) |
| Fork inventory date | 2026-10-02 |

## License disposition

Apache-2.0 is permissive: commercial use, modification, distribution, and private use are all allowed. Obligations for RED: retain LICENSE and NOTICE, state significant changes, do not use upstream contributor names for endorsement. No copyleft contagion. Fork rights: **verified** — Phase 0's license blocker is resolved. Remaining decision (owner: RED principal): none required for license; repository location is already `redrhino-online/OpenExecutive`.

## Stack as built (actual facts, not assumptions)

| Layer | Reality in this checkout |
| --- | --- |
| Backend | Python (requires >=3.11; venv resolved 3.12.13), FastAPI, `uv` package manager, pydantic v2 |
| Frontend | Next.js 15 App Router + Tailwind, Node 22.6+ (22.23.0 present) |
| LLM | Anthropic Claude API (`claude-sonnet-5` default, `claude-opus-5` deep reasoning); providers/ has a provider registry (adapter layer exists) |
| Vector store | ChromaDB, embedded, `./chroma_db` (NOT PostgreSQL) |
| Relational store | SQLite (`episodic_memory.db` — episodic memory + alerts + audit in one file) (NOT PostgreSQL) |
| Persistence | Single-file SQLite; scheduler claims due actions via `UPDATE … RETURNING`; **API must run as a single instance** (scheduler not horizontally scalable) |
| Auth | Optional `BACKEND_SHARED_SECRET` gate on API; Auth.js Google sign-in (OIDC) with local-loopback fallback; signed caller assertions (Ed25519, `api/caller.py`); local login binds to 127.0.0.1 against DNS rebinding |
| Audit | SQLite-backed append-only audit trail (`audit/logger.py`), failure-swallowing by design |
| Tests | pytest (7,266 collected), pytest-asyncio, pytest-xdist; `make check` = ruff + mypy + unit + integration + UI build + PR rules |
| CI | GitHub Actions: ci.yml, release-please, release-images, automated Claude code review (fork PRs need maintainer `claude-review` label) |
| Docs discipline | `scripts/pr_checks.py` enforces architecture-doc updates when documented modules change (`Arch-Docs: n/a` waiver exists) |

## Repo layout (top level)

`packages/core/openexecutive/` — orchestrator, agents, knowledge, memory, onboarding, prompts, api, integrations, scheduler, alerts, audit, workflows, delegation, departments, people, personas, clients, briefing, guide, evals, mcp_server, monitoring, providers, attunement, utils, cli. `packages/ui/` — Next.js. `evals/`, `fixtures/`, `scripts/`, `docker/`, `docs/`.

## Reuse matrix (SPEC §2 table, verified against code)

| SPEC candidate component | Actual state | Verification result | Treatment |
| --- | --- | --- | --- |
| FastAPI + Next.js shells | Present and healthy (334 source files typed, routes well factored) | Baseline suite passes | Keep as shell |
| Orchestration + specialist runner | `orchestrator/` routes via Anthropic tool use to 9 registered specialists; `agents/base.py` BaseAgent contract; provider registry abstracts models | Routed, parallel, synthesized; agent addition is registry + prompt + knowledge + evals | Adapt: register RED's 9 agents in place of CSO/CFO/… persona set; keep routing/caching machinery |
| Client storage and retrieval | ChromaDB collections (`builtin`, `company_docs`, `drive_docs`); retrieval is client-scoped by active slot | Retrieval scoping works per active client | Adapt: RED needs per-workspace scoping plus provenance citation; verify retrieval cannot cross slots |
| Workflow engine + persistence | `workflows/` has `wait_for_human` primitive, `ApprovalGateStepSpec`, `gate.py`, `gate_delivery.py`, `resumer.py`; run state persisted in SQLite; SSE to UI; resume survives restart (per docs/architecture.md:368) | Gate/resume primitives exist and are tested | Adapt to RED gate semantics (SPEC §4); verify restart-resume tests exist before relying on them |
| Approvals, audit, alerts, scheduling | `audit/logger.py` append-only; `alerts/`; `scheduler/` single-instance; departments carry `AuthorityLevel` (auto_execute / propose_only / escalate) + charter model | Authority-level concept maps well to RED charters | Preserve behavior; add immutable version-pinned approval records |
| Executive persona, generic departments | 9 C-suite agents + departments/people modules with charters, goals, OKR cadences | Generic corporate personas — to be replaced | Replace persona set; departments framework (charter + authority + cadence) is reusable scaffolding |
| Cockpit | `today.py`, `briefing/`, morning brief, SSE updates | Single-principal cockpit | Rework into portfolio command center |
| Multi-client isolation | `clients/slots.py` implements per-client slots with engagement statuses (active/paused/winding_down/completed), save/restore of per-client SQLite tables, active-client switching, vector rebuild, Honcho workspace mapping | **Slot-based, single-active-client isolation — not concurrent multi-tenancy.** No server-side RBAC across tenants | Significant new work for SPEC's multi-workspace requirement; acceptable for the single-engagement pilot |

## Key divergences from SPEC assumptions

1. **PostgreSQL assumed, SQLite actual.** SPEC §3 calls for PostgreSQL with row-level policies. Actual: one SQLite file. Pilot impact: acceptable single-engagement; the multi-client isolation and durable outbox requirements need re-decision (ADR) before onboarding real clients. ChromaDB likewise deviates from "PostgreSQL full text and vector retrieval" but satisfies pilot retrieval needs.
2. **Multi-tenancy is slot-based, not concurrent.** `clients/slots.py` swaps one active client's state in and out. SPEC's "multiple isolated client workspaces" and cross-tenant security tests have no direct substrate yet.
3. **Scheduler/API must be single-instance.** SPEC's FastAPI HTTP + worker process split needs review against this constraint (worker processes would need scheduler gating first).
4. **Human-gate workflow primitives already exist** (`wait_for_human`, ApprovalGateStepSpec, resumer) — stronger than SPEC assumed. Gate semantics (version-pinned approvals, waivers, impact assessment) still must be built; the cycle-1 governance domain (planning repo) can port onto these.
5. **Approval authority exists as a model** (departments' AuthorityLevel + charters) but has no immutable version-specific approval records — that is RED's GateDecision/ApprovalRequest work.

## Baseline verification (recorded evidence)

| Gate | Command | Result |
| --- | --- | --- |
| Python | `uv run python --version` | 3.12.13 (>= 3.11 required) |
| Unit tests | `env -u BACKEND_SHARED_SECRET -u OE_PUBLIC_DEPLOYMENT uv run pytest tests/unit/ -n auto --dist loadfile -q` | **7213 passed, 1 skipped** in 411 s (16 workers) |
| Integration tests | same env, `pytest tests/integration/ -n auto --dist loadfile -q` | **52 passed** in 40 s |
| Lint | `uv run ruff check openexecutive/` | All checks passed |
| Types | `uv run mypy openexecutive/` | Success: no issues in 334 source files |
| UI build/tests | `npm run build` / `npm test` in packages/ui | **Not run in this inventory** (node_modules not installed; CI runs it) |
| Full `make check` | includes UI build + pr_checks.py | Not run end to end (same UI caveat) |

Environment notes: first `uv sync` pulls heavy ML deps (torch, ChromaDB); checkout lives on a Windows/WSL-mounted drive where per-test I/O is slow — a WSL-native clone is materially faster for test cycles.

## Phase 0 exit criteria status

| Exit criterion (plan) | Status |
| --- | --- |
| Reproducible local setup | Mostly: `uv sync` + pytest verified. `.env` creation and `make dev` boot not exercised in this inventory |
| Known upstream commit and license | Done (this document) |
| Verified reuse matrix | Done above |
| Passing baseline or documented failures | Done — all green |
| Named owner per architectural decision | Open — RED principal must own: storage migration strategy (SQLite → PostgreSQL or not), tenant model, scheduler topology, model provider data handling |
| Context map + ADRs | Not yet written |

## Recommended next actions

1. Write `docs/context_map.md` and initial ADRs: (a) storage strategy given SQLite reality, (b) tenant model given slot-based isolation, (c) scheduler/worker topology, (d) RED agent registration approach over the specialist registry.
2. Run `make check` end to end and one `make dev` boot to complete "reproducible local setup."
3. Map RED governance domain (cycle 1 in the planning repo) onto `workflows/gate.py` + departments' AuthorityLevel.
4. Decide where RED-specific code lives: a `redops/` context package inside this fork (SPEC §6 layout) vs. keeping the planning repo as spec-authority only.

## Absorption record (ADR 0014, 2026-10-08)

| Item | Value |
| --- | --- |
| Decision | ADR 0014: the fork is absorbed into this repository; the submodule and the ADR 0011 overlay machinery are retired |
| Upstream repository | https://github.com/SenteLabsAI/OpenExecutive |
| Absorbed upstream commit | `31e55338db7f7a0eb7ff30b4cb8942a1ece551bd` (v0.4.6) |
| Absorbed baseline | the upstream tree plus the applied RED adoption (rebrand, nav group, RED agent registration splices, `redops_agents.py`, `redops_prompts.py`, `knowledge/redops/`, one eval scenario) |
| RED-owned surfaces | listed in `vendor/red-owned-files.txt` (the files the adoption modified or added); freely editable |
| Locked upstream-origin files | listed in `vendor/upstream-files.txt`; hashed in `vendor/upstream-manifest.sha256`; byte-stable unless an owner-approved exception is recorded here and `make vendor-pin` re-baselines |
| Enforcement | `scripts/check_vendor_additive.sh`, DoD `[4/7]` |
| Upstream updates | owner-driven merges only; record the merge here (commit, decision, owner), then `make vendor-pin` |
| License | Apache-2.0; LICENSE and NOTICE retained under `vendor/openexecutive/` |
| Owner | RED principal |

Unattended cycles never re-pin and never approve exceptions. A cycle that needs
a locked-file modification records the proposal in the plan and stops.

### Exception record 2026-10-10 (owner-approved via the approved overhaul plan; ADR 0014 escape hatch)

| Item | Value |
| --- | --- |
| Decision | The Knowledge and Workflows subtrees become RED-owned surfaces: K9 (canon corpus, repeatable ingest + grounding eval) and K11/K12 (stage 0-10 pipeline as cockpit workflow definitions bound to RED approvals) cannot be implemented additively alone — they must modify `packages/core/openexecutive/knowledge/` (loader, retriever, documents) and `packages/core/openexecutive/workflows/` (`__init__.py` registry) |
| Basis | Owner-approved single-shell overhaul plan (ADR 0013 decision 5, K9-K12 in IMPLEMENTATION_PLAN.md); recorded here by the operator during the owner-ordered 20-cycle batch |
| Scope | Every upstream-origin path under `packages/core/openexecutive/knowledge/` and `packages/core/openexecutive/workflows/` |
| Effect | Those paths move to `vendor/red-owned-files.txt` and leave the locked manifest; `make vendor-pin` re-baselined 2026-10-10 |
| Owner | RED principal (veto window: revert this record and re-pin) |

### Single-shell disposition (K7, 2026-10-10; ADR 0013)

The rebranded cockpit is the only user-facing RED UI. The separate `/screens`
thin client is retired: the repo-side `frontend/` app, `Dockerfile.ui`, the
chart's `redop-ui` Deployment/Service/PDB and the ingress `/screens` route are
gone, and the section 13 condition 6 gate exercises the cockpit pages. The
retirement removed no vendor file — the thin client was RED's own repo-side
app — so the absorbed vendor tree and its baseline manifest are unchanged by it;
the vendor `packages/ui` gained the RED overlay additively (native
`/operations/*` pages, shared workspace context, RED-first navigation, landing
rewrite) under the additive rule and the owner-approved RED-owned surfaces.

"""The RED agent roster as pure domain values (SPEC.md section 5; queue Q3).

SPEC.md section 5 gives every agent a versioned charter, allowed tools, input and
output schema, evidence policy, quality rubric, escalation rules and budget
limit, and reserves capability slots 10 and 11 as proposal-only with no execution
permissions. ``RedAgentSpec`` is the machine-readable half of that contract: the
charter document in ``docs/agents/`` carries the prose, and this value carries
the routing key, the prompt version and the authority class the registry and
router enforce.

The roster is the nine core agents of the section 5 table, the ten capability
slots (1-11), and the Director that coordinates the council. A reserved slot
(slot 10 or 11) is proposal-only by construction: it can never declare a tool, so
no execution permission can be attached to it in code. The specs are deliberately
free of prompt text; the fork overlay holds the vendor-side prompt module
(ADR 0011) so the two stay separable.
"""

from __future__ import annotations

from dataclasses import dataclass

from redops.agents.domain.errors import InvalidRedAgentSpecError

DIRECTOR_SLOT = 0
RESERVED_SLOTS = (10, 11)


def _require_text(label: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidRedAgentSpecError(f"a RED agent spec requires {label}")
    return value


@dataclass(frozen=True)
class RedAgentSpec:
    """One chartered RED agent (SPEC.md section 5)."""

    slot: int
    key: str
    name: str
    domain: str
    mission: str
    owns: tuple[str, ...]
    outputs: tuple[str, ...]
    must_escalate: tuple[str, ...]
    tools: tuple[str, ...]
    proposal_only: bool
    model: str
    prompt_version: str
    charter_ref: str
    canon_files: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.slot, int) or isinstance(self.slot, bool) or self.slot < 0:
            raise InvalidRedAgentSpecError("the RED agent slot must be a non-negative integer")
        _require_text("a routing key", self.key)
        if self.key != self.key.strip().lower() or " " in self.key:
            raise InvalidRedAgentSpecError(
                f"the RED agent routing key {self.key!r} must be a lowercase token"
            )
        _require_text("a name", self.name)
        _require_text("a domain", self.domain)
        _require_text("a mission", self.mission)
        _require_text("a model", self.model)
        _require_text("a prompt version", self.prompt_version)
        _require_text("a charter reference", self.charter_ref)
        for label, values in (
            ("owns", self.owns),
            ("outputs", self.outputs),
            ("must escalate", self.must_escalate),
            ("tools", self.tools),
            ("canon files", self.canon_files),
        ):
            for value in values:
                _require_text(f"a {label} entry", value)
        reserved = self.slot in RESERVED_SLOTS
        if reserved and not self.proposal_only:
            raise InvalidRedAgentSpecError(
                f"capability slot {self.slot} must be proposal-only (SPEC.md section 5)"
            )
        if reserved and self.tools:
            raise InvalidRedAgentSpecError(
                f"capability slot {self.slot} must declare no tools (SPEC.md section 5)"
            )
        if not reserved and self.proposal_only:
            raise InvalidRedAgentSpecError(
                f"slot {self.slot} is a core agent and cannot be proposal-only"
            )
        if not reserved and not self.tools:
            raise InvalidRedAgentSpecError(
                f"slot {self.slot} is a core agent and needs at least one tool"
            )

    @property
    def is_reserved(self) -> bool:
        """True for the proposal-only capability slots 10 and 11."""
        return self.slot in RESERVED_SLOTS


_CORE_TOOLS = ("retrieve", "draft", "queue_change")

DIRECTOR = RedAgentSpec(
    slot=DIRECTOR_SLOT,
    key="director",
    name="RED Operations Director",
    domain="director",
    mission=(
        "Coordinate the agent council, own prioritisation and handoffs, and "
        "present sourced reasons for every intervention."
    ),
    owns=("council coordination", "prioritisation", "handoffs", "interventions"),
    outputs=("prioritised work", "handoff decision", "intervention rationale"),
    must_escalate=("client substantive decision", "external launch", "spend"),
    tools=("retrieve", "draft", "queue_change", "route_specialist"),
    proposal_only=False,
    model="claude-sonnet-5",
    prompt_version="red-director-1",
    charter_ref="SPEC.md section 5",
)

SPECIALISTS: tuple[RedAgentSpec, ...] = (
    RedAgentSpec(
        slot=1,
        key="discovery",
        name="Discovery and Diagnosis",
        domain="discovery",
        mission=(
            "Establish what is true about a client's business before RED commits "
            "to a method: intake, diagnosis, avatar and the unknowns register."
        ),
        owns=("intake", "diagnosis", "gaps"),
        outputs=("enterprise brief", "diagnosis package", "asset inventory"),
        must_escalate=("missing essential evidence",),
        tools=_CORE_TOOLS,
        proposal_only=False,
        model="claude-sonnet-5",
        prompt_version="red-discovery-1",
        charter_ref="docs/agents/charter-01-discovery-diagnosis.md",
        canon_files=("00", "01", "02", "03", "04"),
    ),
    RedAgentSpec(
        slot=2,
        key="ip_structuring",
        name="IP Structuring",
        domain="method",
        mission=(
            "Turn the diagnosed truth into the Signature Solution and its "
            "versioned milestones without materially changing the client method."
        ),
        owns=("Signature Solution", "milestones", "method version"),
        outputs=("method version", "terminology"),
        must_escalate=("material change to client method",),
        tools=_CORE_TOOLS,
        proposal_only=False,
        model="claude-sonnet-5",
        prompt_version="red-ip-structuring-1",
        charter_ref="docs/agents/charter-02-ip-structuring.md",
        canon_files=("07", "08", "09", "10"),
    ),
    RedAgentSpec(
        slot=3,
        key="offer_journey",
        name="Offer and Journey Design",
        domain="commercial",
        mission=(
            "Design the offer specification and the customer path from the "
            "approved method, audience and currency."
        ),
        owns=("offer", "customer path"),
        outputs=("offer specification", "routing"),
        must_escalate=("pricing and positioning decisions",),
        tools=_CORE_TOOLS,
        proposal_only=False,
        model="claude-sonnet-5",
        prompt_version="red-offer-journey-1",
        charter_ref="docs/agents/charter-03-offer-journey-design.md",
        canon_files=("11", "12"),
    ),
    RedAgentSpec(
        slot=4,
        key="knowledge",
        name="Knowledge Management",
        domain="knowledge",
        mission=(
            "Own ingestion, indexing and retrieval so every claim traces to an "
            "immutable source scoped to the active client."
        ),
        owns=("ingestion", "indexing", "retrieval"),
        outputs=("source index", "asset catalog"),
        must_escalate=("disputed authority",),
        tools=_CORE_TOOLS,
        proposal_only=False,
        model="claude-sonnet-5",
        prompt_version="red-knowledge-1",
        charter_ref="docs/agents/charter-04-knowledge-management.md",
    ),
    RedAgentSpec(
        slot=5,
        key="governance",
        name="Governance and Approval",
        domain="governance",
        mission=(
            "Own states, gates and change impact, and keep approval a human "
            "decision that is version scoped."
        ),
        owns=("states", "gates", "change impact"),
        outputs=("approval queue", "decision log"),
        must_escalate=("client substantive decision",),
        tools=_CORE_TOOLS,
        proposal_only=False,
        model="claude-sonnet-5",
        prompt_version="red-governance-1",
        charter_ref="docs/agents/charter-05-governance-approval.md",
    ),
    RedAgentSpec(
        slot=6,
        key="asset_production",
        name="Business Asset Production",
        domain="production",
        mission=(
            "Produce briefs and traced deliverables whose every claim is "
            "grounded on an approved prerequisite."
        ),
        owns=("briefs", "asset quality"),
        outputs=("traced deliverables",),
        must_escalate=("missing approved prerequisites",),
        tools=_CORE_TOOLS,
        proposal_only=False,
        model="claude-sonnet-5",
        prompt_version="red-asset-production-1",
        charter_ref="docs/agents/charter-06-asset-production.md",
        canon_files=("13", "14", "15", "16", "17", "18"),
    ),
    RedAgentSpec(
        slot=7,
        key="campaign_execution",
        name="Campaign and Journey Execution",
        domain="execution",
        mission=(
            "Implement the funnel and run launch checks, returning a release, "
            "verification or incident rather than publishing."
        ),
        owns=("implementation", "launch checks"),
        outputs=("release", "verification", "incident"),
        must_escalate=("external launch and strategic changes",),
        tools=_CORE_TOOLS,
        proposal_only=False,
        model="claude-sonnet-5",
        prompt_version="red-campaign-execution-1",
        charter_ref="docs/agents/charter-07-campaign-execution.md",
        canon_files=("13", "14", "21", "22"),
    ),
    RedAgentSpec(
        slot=8,
        key="insight",
        name="Insight and Performance",
        domain="measurement",
        mission=(
            "Measure and evaluate, keep observation distinct from causal "
            "conclusion, and recommend only with evidence and an owner."
        ),
        owns=("measurement", "evaluation"),
        outputs=("baseline", "review", "recommendation"),
        must_escalate=("unsupported causal conclusion",),
        tools=_CORE_TOOLS,
        proposal_only=False,
        model="claude-sonnet-5",
        prompt_version="red-insight-1",
        charter_ref="docs/agents/charter-08-insight-performance.md",
        canon_files=("22", "23", "29", "30", "31"),
    ),
    RedAgentSpec(
        slot=9,
        key="ip_portfolio",
        name="IP Portfolio Development",
        domain="portfolio",
        mission=(
            "Identify derivative opportunities and frame the investment case "
            "without committing spend or a launch."
        ),
        owns=("derivative opportunity",),
        outputs=("roadmap", "investment case"),
        must_escalate=("investment and launch",),
        tools=_CORE_TOOLS,
        proposal_only=False,
        model="claude-sonnet-5",
        prompt_version="red-ip-portfolio-1",
        charter_ref="docs/agents/charter-09-ip-portfolio.md",
        canon_files=("11", "12"),
    ),
    RedAgentSpec(
        slot=10,
        key="client_success",
        name="Client Success and Engagement Health",
        domain="operations",
        mission=(
            "Watch engagement health, surface at-risk critical paths and "
            "propose renewal or intervention cards."
        ),
        owns=("engagement health", "renewal and expansion triggers"),
        outputs=("health view", "risk signal", "intervention card"),
        must_escalate=("overdue gates", "missed targets", "spend or scope change"),
        tools=(),
        proposal_only=True,
        model="claude-sonnet-5",
        prompt_version="red-client-success-1",
        charter_ref="docs/agents/charter-10-client-success.md",
    ),
    RedAgentSpec(
        slot=11,
        key="assurance",
        name="Assurance, Risk and Compliance",
        domain="operations",
        mission=(
            "Keep the risk register and compliance evidence, and check that data "
            "stays inside the agreed boundary."
        ),
        owns=("risk register", "compliance evidence", "audit readiness"),
        outputs=("risk", "compliance finding", "assurance review"),
        must_escalate=(
            "missing compliance evidence",
            "data leaving the agreed boundary",
            "security or isolation failures",
        ),
        tools=(),
        proposal_only=True,
        model="claude-sonnet-5",
        prompt_version="red-assurance-1",
        charter_ref="docs/agents/charter-11-assurance-compliance.md",
    ),
)


def red_agent_specs() -> tuple[RedAgentSpec, ...]:
    """The Director followed by the eleven capability slots, in slot order."""
    return (DIRECTOR, *SPECIALISTS)

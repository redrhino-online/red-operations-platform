"""Behavioral tests for the RED agent roster, registry and router (queue Q3).

SPEC.md section 5 gives every agent a versioned charter and bounds its authority,
and reserves capability slots 10 and 11 as proposal-only with no execution
permissions. SPEC.md section 13 condition 5 requires the agent path to run
through a deterministic model gateway. These tests pin the roster (Director plus
eleven slots, slots 10/11 tool-less and proposal-only) and prove routing reaches
every chartered agent through the ``ModelGateway`` port, carrying the tenant,
model, prompt version and trace id attribution.
"""

import unittest

from redops.agents.application.registry import RedAgentRegistry
from redops.agents.application.router import (
    RedAgentRouter,
    build_agent_prompt,
)
from redops.agents.domain.errors import (
    AgentModelError,
    InvalidRedAgentSpecError,
    UnknownRedAgentError,
)
from redops.agents.domain.red_agents import (
    DIRECTOR,
    RESERVED_SLOTS,
    SPECIALISTS,
    RedAgentSpec,
    red_agent_specs,
)
from redops.agents.infrastructure.fake_gateway import DeterministicFakeModelGateway

TENANT = "3fmindset"


def spec(**overrides):
    values = {
        "slot": 1,
        "key": "discovery",
        "name": "Discovery and Diagnosis",
        "domain": "discovery",
        "mission": "Establish what is true before RED commits.",
        "owns": ("intake",),
        "outputs": ("brief",),
        "must_escalate": ("missing evidence",),
        "tools": ("retrieve", "draft"),
        "proposal_only": False,
        "model": "claude-sonnet-5",
        "prompt_version": "red-discovery-1",
        "charter_ref": "docs/agents/charter-01-discovery-diagnosis.md",
    }
    values.update(overrides)
    return RedAgentSpec(**values)


class RedAgentRosterTests(unittest.TestCase):
    def test_director_plus_eleven_capability_slots(self):
        specs = red_agent_specs()
        self.assertEqual(12, len(specs))
        self.assertEqual("director", DIRECTOR.key)
        self.assertEqual(11, len(SPECIALISTS))
        isinstance(SPECIALISTS, tuple)
        self.assertEqual(tuple(range(1, 12)), tuple(s.slot for s in SPECIALISTS))

    def test_every_agent_names_its_charter_and_prompt_version(self):
        for agent in red_agent_specs():
            self.assertTrue(agent.charter_ref.strip(), agent.key)
            self.assertTrue(agent.prompt_version.strip(), agent.key)

    def test_reserved_slots_are_proposal_only_with_no_tools(self):
        reserved = [s for s in red_agent_specs() if s.is_reserved]
        self.assertEqual(list(RESERVED_SLOTS), [s.slot for s in reserved])
        for agent in reserved:
            self.assertTrue(agent.proposal_only, agent.key)
            self.assertEqual((), agent.tools, agent.key)

    def test_core_agents_have_tools_and_are_not_proposal_only(self):
        for agent in red_agent_specs():
            if agent.is_reserved:
                continue
            self.assertFalse(agent.proposal_only, agent.key)
            self.assertTrue(agent.tools, agent.key)

    def test_rejects_a_reserved_slot_that_declares_a_tool(self):
        with self.assertRaises(InvalidRedAgentSpecError):
            spec(slot=10, key="client_success", proposal_only=True, tools=("draft",))

    def test_rejects_a_core_slot_marked_proposal_only(self):
        with self.assertRaises(InvalidRedAgentSpecError):
            spec(slot=1, proposal_only=True)

    def test_rejects_a_blank_routing_key(self):
        with self.assertRaises(InvalidRedAgentSpecError):
            spec(key=" ")

    def test_rejects_a_non_token_routing_key(self):
        with self.assertRaises(InvalidRedAgentSpecError):
            spec(key="Discovery Diagnosis")


class RedAgentRegistryTests(unittest.TestCase):
    def test_canonical_registry_holds_the_whole_roster(self):
        registry = RedAgentRegistry.canonical()
        self.assertEqual(12, len(registry))
        self.assertEqual(10, len(registry.routable()))
        self.assertEqual(2, len(registry.reserved()))

    def test_unknown_agent_is_refused(self):
        registry = RedAgentRegistry.canonical()
        with self.assertRaises(UnknownRedAgentError):
            registry.get("nope")

    def test_duplicate_key_or_slot_is_refused(self):
        first = spec()
        with self.assertRaises(InvalidRedAgentSpecError):
            RedAgentRegistry([first, spec(name="Other")])
        with self.assertRaises(InvalidRedAgentSpecError):
            RedAgentRegistry([first, spec(key="other")])

    def test_rejects_a_non_spec_value(self):
        with self.assertRaises(InvalidRedAgentSpecError):
            RedAgentRegistry(["not-a-spec"])


class RedAgentRouterTests(unittest.TestCase):
    def setUp(self):
        self.gateway = DeterministicFakeModelGateway()
        self.router = RedAgentRouter(self.gateway)

    def test_requires_a_model_gateway(self):
        with self.assertRaises(AgentModelError):
            RedAgentRouter(object())

    def test_routes_to_every_agent_through_the_gateway(self):
        responses = self.router.route_all(
            "draft the stage 1 avatar note", tenant_id=TENANT, trace_id="trace-e2e"
        )
        registry = RedAgentRegistry.canonical()
        self.assertEqual(set(registry.keys()), set(responses))
        self.assertEqual(len(registry), len(self.gateway.calls))
        for key, response in responses.items():
            agent = registry.get(key)
            self.assertEqual(agent.model, response.model, key)
            self.assertEqual(agent.prompt_version, response.prompt_version, key)
            self.assertEqual("trace-e2e", response.trace_id, key)
            self.assertTrue(response.text.strip(), key)

    def test_route_prompt_carries_the_mission_and_the_query(self):
        spec = RedAgentRegistry.canonical().get("discovery")
        prompt = build_agent_prompt(spec, "who is the customer")
        self.assertIn(spec.mission, prompt)
        self.assertIn("who is the customer", prompt)

    def test_route_refuses_a_blank_query(self):
        with self.assertRaises(AgentModelError):
            self.router.route(
                "discovery", " ", tenant_id=TENANT, trace_id="trace-1"
            )

    def test_route_refuses_an_unknown_agent(self):
        with self.assertRaises(UnknownRedAgentError):
            self.router.route(
                "nope", "hi", tenant_id=TENANT, trace_id="trace-1"
            )

    def test_a_request_stays_within_the_active_client(self):
        self.router.route(
            "insight", "review the baseline", tenant_id=TENANT, trace_id="trace-1"
        )
        # The fake returns the model and version it was asked for; the tenant
        # never appears in a response, so it cannot leak another client's scope.
        self.assertEqual(1, len(self.gateway.calls))
        self.assertEqual("red-insight-1", self.gateway.calls[0].prompt_version)


if __name__ == "__main__":
    unittest.main()

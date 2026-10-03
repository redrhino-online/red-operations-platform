"""Behavioral tests for the live RED LLM adapter (queue Q2).

SPEC.md section 6 requires that an LLM adapter abstracts model choice and logs
model, prompt version, context references, usage and trace identifiers without
storing secrets. SPEC.md section 13 condition 5 requires the real provider path
to be proven and the adapter to log that attribution, while the deterministic
fake gateway drives the offline end-to-end path. These tests pin the contract
of the adapter that wraps the fork's provider registry behind the RED
``ModelGateway`` port, and of the logging decorator that records the
attribution every call carries. No network or API key is used here: a
provider-shaped fake stands in for the fork provider.
"""

import asyncio
import logging
import types
import unittest

from openexecutive.providers.registry import get_provider

from redops.agents.application.ports import ModelGateway
from redops.agents.domain.errors import (
    AgentModelError,
    ModelGatewayRuntimeError,
)
from redops.agents.domain.value_objects import (
    ModelRequest,
    ModelResponse,
    ModelUsage,
)
from redops.agents.infrastructure.llm_gateway import (
    ForkProviderModelGateway,
    LoggingModelGateway,
)


def request(**overrides):
    values = {
        "tenant_id": "3fmindset",
        "model": "openrouter/anthropic/claude-sonnet-5",
        "prompt": "draft the stage 1 avatar note",
        "prompt_version": "avatar-note-v1",
        "trace_id": "trace-1",
        "context_references": ("source-1", "claim-1"),
    }
    values.update(overrides)
    return ModelRequest(**values)


def anthropic_shaped_message(text, input_tokens, output_tokens):
    block = types.SimpleNamespace(type="text", text=text)
    usage = types.SimpleNamespace(
        input_tokens=input_tokens, output_tokens=output_tokens
    )
    return types.SimpleNamespace(content=[block], usage=usage)


class FakeProvider:
    """A fork ``LLMProvider``-shaped backend that records its call kwargs."""

    def __init__(self, message):
        self._message = message
        self.calls = []

    async def messages_create(self, **kwargs):
        self.calls.append(kwargs)
        return self._message


class ForkProviderModelGatewayTests(unittest.TestCase):
    def test_is_a_model_gateway(self):
        gateway = ForkProviderModelGateway(lambda model: FakeProvider(None))
        self.assertIsInstance(gateway, ModelGateway)

    def test_translates_request_to_anthropic_shape_and_back(self):
        provider = FakeProvider(anthropic_shaped_message("hello", 12, 3))
        gateway = ForkProviderModelGateway(
            lambda model: provider, max_tokens=256
        )
        response = gateway.generate(request())

        self.assertEqual(
            provider.calls[0],
            {
                "model": "openrouter/anthropic/claude-sonnet-5",
                "max_tokens": 256,
                "messages": [
                    {"role": "user", "content": "draft the stage 1 avatar note"}
                ],
            },
        )
        self.assertEqual(response.text, "hello")
        self.assertEqual(response.model, "openrouter/anthropic/claude-sonnet-5")
        self.assertEqual(response.prompt_version, "avatar-note-v1")
        self.assertEqual(response.trace_id, "trace-1")
        self.assertEqual(response.context_references, ("source-1", "claim-1"))
        self.assertEqual(response.usage, ModelUsage(input_tokens=12, output_tokens=3))

    def test_selects_the_provider_for_the_request_model(self):
        seen = []
        provider = FakeProvider(anthropic_shaped_message("ok", 1, 1))

        def provider_for(model):
            seen.append(model)
            return provider

        ForkProviderModelGateway(provider_for).generate(
            request(model="google/gemini-3.8-flash")
        )
        self.assertEqual(seen, ["google/gemini-3.8-flash"])

    def test_joins_multiple_text_blocks(self):
        message = types.SimpleNamespace(
            content=[
                types.SimpleNamespace(type="text", text="one "),
                types.SimpleNamespace(type="tool_use", text=None),
                types.SimpleNamespace(type="text", text="two"),
            ],
            usage=types.SimpleNamespace(input_tokens=1, output_tokens=2),
        )
        gateway = ForkProviderModelGateway(lambda model: FakeProvider(message))
        self.assertEqual(gateway.generate(request()).text, "one two")

    def test_refuses_a_provider_without_messages_create(self):
        gateway = ForkProviderModelGateway(lambda model: object())
        with self.assertRaises(AgentModelError):
            gateway.generate(request())

    def test_refuses_to_run_inside_a_running_event_loop(self):
        provider = FakeProvider(anthropic_shaped_message("ok", 1, 1))
        gateway = ForkProviderModelGateway(lambda model: provider)

        async def main():
            return gateway.generate(request())

        with self.assertRaises(ModelGatewayRuntimeError):
            asyncio.run(main())

    def test_from_fork_registry_wraps_the_fork_provider_registry(self):
        gateway = ForkProviderModelGateway.from_fork_registry()
        self.assertIsInstance(gateway, ForkProviderModelGateway)
        self.assertIs(gateway.provider_for, get_provider)


class LoggingModelGatewayTests(unittest.TestCase):
    def setUp(self):
        self.delegate = FakeModelGateway()
        self.gateway = LoggingModelGateway(self.delegate)

    def test_is_a_model_gateway_and_delegates(self):
        self.assertIsInstance(self.gateway, ModelGateway)
        response = self.gateway.generate(request())
        self.assertEqual(self.delegate.requests, [request()])
        self.assertEqual(response.text, "model output")

    def test_logs_model_prompt_version_usage_trace_and_context(self):
        with self.assertLogs("redops.agents.model", level="INFO") as captured:
            self.gateway.generate(request())
        record = captured.records[0]
        self.assertEqual(record.redops_model, "openrouter/anthropic/claude-sonnet-5")
        self.assertEqual(record.redops_prompt_version, "avatar-note-v1")
        self.assertEqual(record.redops_trace_id, "trace-1")
        self.assertEqual(record.redops_tenant, "3fmindset")
        self.assertEqual(
            record.redops_context_references, ["source-1", "claim-1"]
        )
        self.assertEqual(record.redops_input_tokens, 3)
        self.assertEqual(record.redops_output_tokens, 2)

    def test_never_logs_prompt_or_response_text(self):
        with self.assertLogs("redops.agents.model", level="INFO") as captured:
            self.gateway.generate(request())
        message = captured.records[0].getMessage()
        for value in captured.records[0].__dict__.values():
            rendered = repr(value)
            self.assertNotIn("draft the stage 1 avatar note", rendered)
            self.assertNotIn("model output", rendered)
        self.assertNotIn("draft the stage 1 avatar note", message)

    def test_rejects_a_non_gateway_delegate(self):
        with self.assertRaises(AgentModelError):
            LoggingModelGateway(object())

    def test_uses_the_supplied_logger(self):
        logger = logging.getLogger("redops.agents.model.test.custom")
        custom = LoggingModelGateway(self.delegate, logger=logger)
        self.assertIs(custom.logger, logger)


class FakeModelGateway(ModelGateway):
    def __init__(self):
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return ModelResponse(
            text="model output",
            model=request.model,
            prompt_version=request.prompt_version,
            usage=ModelUsage(input_tokens=3, output_tokens=2),
            trace_id=request.trace_id,
            context_references=request.context_references,
        )


if __name__ == "__main__":
    unittest.main()

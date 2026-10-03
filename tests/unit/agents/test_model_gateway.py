"""Behavioral tests for the deterministic fake model gateway (queue Q1).

SPEC.md section 6 requires an LLM adapter that abstracts model choice and logs
model, prompt version, context references, usage and trace identifiers without
storing secrets. SPEC.md section 13 condition 5 requires a deterministic fake
model gateway so the end-to-end path runs offline against a known model, while
the real OpenRouter path is proven separately. These tests pin the port
contract: a request must name the tenant, model, prompt version and trace id;
the fake adapter answers deterministically, offline, and returns the model,
prompt version, usage and trace id it was given so downstream agent use cases
can depend on the seam rather than a concrete provider.
"""

import unittest

from redops.agents.application.ports import ModelGateway
from redops.agents.domain.errors import (
    InvalidModelRequestError,
    InvalidModelResponseError,
    InvalidModelUsageError,
)
from redops.agents.domain.value_objects import (
    ModelRequest,
    ModelResponse,
    ModelUsage,
)
from redops.agents.infrastructure.fake_gateway import (
    DeterministicFakeModelGateway,
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


class ModelRequestTests(unittest.TestCase):
    def test_names_tenant_model_prompt_version_and_trace(self):
        req = request()
        self.assertEqual(req.tenant_id, "3fmindset")
        self.assertEqual(req.prompt_version, "avatar-note-v1")
        self.assertEqual(req.trace_id, "trace-1")
        self.assertEqual(req.context_references, ("source-1", "claim-1"))

    def test_rejects_a_blank_identity_field(self):
        for field in (
            "tenant_id",
            "model",
            "prompt",
            "prompt_version",
            "trace_id",
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidModelRequestError):
                    request(**{field: "   "})

    def test_rejects_a_blank_or_duplicate_context_reference(self):
        with self.assertRaises(InvalidModelRequestError):
            request(context_references=("source-1", " "))
        with self.assertRaises(InvalidModelRequestError):
            request(context_references=("source-1", "source-1"))


class ModelUsageTests(unittest.TestCase):
    def test_accepts_non_negative_token_counts(self):
        usage = ModelUsage(input_tokens=10, output_tokens=4)
        self.assertEqual(usage.input_tokens, 10)
        self.assertEqual(usage.output_tokens, 4)

    def test_rejects_a_negative_or_non_integer_count(self):
        with self.assertRaises(InvalidModelUsageError):
            ModelUsage(input_tokens=-1, output_tokens=0)
        with self.assertRaises(InvalidModelUsageError):
            ModelUsage(input_tokens=True, output_tokens=0)
        with self.assertRaises(InvalidModelUsageError):
            ModelUsage(input_tokens=1, output_tokens="2")


class ModelResponseTests(unittest.TestCase):
    def test_rejects_a_blank_text_or_missing_usage(self):
        with self.assertRaises(InvalidModelResponseError):
            ModelResponse(
                text="  ",
                model="m",
                prompt_version="v1",
                usage=ModelUsage(input_tokens=1, output_tokens=1),
                trace_id="t",
                context_references=(),
            )
        with self.assertRaises(InvalidModelResponseError):
            ModelResponse(
                text="ok",
                model="m",
                prompt_version="v1",
                usage="not-usage",
                trace_id="t",
                context_references=(),
            )


class DeterministicFakeModelGatewayTests(unittest.TestCase):
    def test_is_a_model_gateway(self):
        self.assertIsInstance(DeterministicFakeModelGateway(), ModelGateway)

    def test_same_request_produces_the_same_response(self):
        gateway = DeterministicFakeModelGateway()
        first = gateway.generate(request())
        second = gateway.generate(request())
        self.assertEqual(first, second)

    def test_distinct_prompts_produce_distinct_text(self):
        gateway = DeterministicFakeModelGateway()
        first = gateway.generate(request(prompt="draft the avatar"))
        second = gateway.generate(request(prompt="draft the offer"))
        self.assertNotEqual(first.text, second.text)

    def test_returns_a_configured_response_for_a_prompt(self):
        gateway = DeterministicFakeModelGateway(
            responses={"draft the avatar": "Avatar: men rebuilding agency."}
        )
        response = gateway.generate(request(prompt="draft the avatar"))
        self.assertEqual(response.text, "Avatar: men rebuilding agency.")

    def test_response_carries_model_prompt_version_trace_and_context(self):
        gateway = DeterministicFakeModelGateway()
        req = request()
        response = gateway.generate(req)
        self.assertEqual(response.model, req.model)
        self.assertEqual(response.prompt_version, req.prompt_version)
        self.assertEqual(response.trace_id, req.trace_id)
        self.assertEqual(response.context_references, req.context_references)
        self.assertGreaterEqual(response.usage.output_tokens, 0)

    def test_records_each_call_for_logging(self):
        gateway = DeterministicFakeModelGateway()
        self.assertEqual(gateway.calls, ())
        gateway.generate(request(trace_id="trace-a"))
        gateway.generate(request(trace_id="trace-b"))
        self.assertEqual(
            [call.trace_id for call in gateway.calls],
            ["trace-a", "trace-b"],
        )

    def test_does_not_leak_a_secret_that_was_never_supplied(self):
        secret = "sk-live-should-never-appear"
        gateway = DeterministicFakeModelGateway()
        response = gateway.generate(request(prompt="hello"))
        self.assertNotIn(secret, response.text)
        self.assertFalse(hasattr(response, "api_key"))


if __name__ == "__main__":
    unittest.main()

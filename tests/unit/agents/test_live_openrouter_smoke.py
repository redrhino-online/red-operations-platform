"""Live OpenRouter smoke test for the RED model adapter (queue Q4).

SPEC.md section 13 condition 5 requires the real provider path to be proven
separately from the deterministic fake that drives the offline end-to-end path,
and SPEC.md section 6 requires the adapter to log model, prompt version, context
references, usage and trace identifiers without storing secrets. This test
proves the full live chain once, end to end:

    ModelRequest -> ForkProviderModelGateway -> fork get_provider
    -> OpenRouterProvider -> OpenRouter -> ModelResponse

wrapped in ``LoggingModelGateway`` so the section 6 attribution record is
emitted on the live path too. It reuses the adapter from queue Q2 rather than a
second implementation.

The test is env gated and never runs by accident. It skips unless
``OPENROUTER_API_KEY`` is set *and* ``REDOP_LIVE_OPENROUTER_SMOKE`` is truthy, so
``make check`` and the build loop stay offline. A live call spends money, so the
explicit opt-in keeps a stray key in a developer shell from turning every cycle
into a paid network call. The model is overridable with ``REDOP_SMOKE_MODEL``.

    OPENROUTER_API_KEY=sk-... REDOP_LIVE_OPENROUTER_SMOKE=1 \
        PYTHONPATH=backend uv run pytest \
        tests/unit/agents/test_live_openrouter_smoke.py -q
"""

from __future__ import annotations

import os
import unittest

import openexecutive.providers.registry as fork_registry

from redops.agents.domain.value_objects import ModelRequest
from redops.agents.infrastructure.llm_gateway import (
    ForkProviderModelGateway,
    LoggingModelGateway,
)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPT_IN = os.environ.get("REDOP_LIVE_OPENROUTER_SMOKE", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
SMOKE_MODEL = os.environ.get("REDOP_SMOKE_MODEL", "claude-haiku-4-5")
RUN = bool(OPENROUTER_API_KEY) and OPT_IN
SKIP_REASON = (
    "live OpenRouter smoke requires OPENROUTER_API_KEY and "
    "REDOP_LIVE_OPENROUTER_SMOKE=1; set both to prove the real provider path"
)


@unittest.skipUnless(RUN, SKIP_REASON)
class LiveOpenRouterSmokeTests(unittest.TestCase):
    """One paid call through the real provider, gated behind an explicit opt-in."""

    def setUp(self) -> None:
        self._saved = {
            "OPENROUTER_ENABLED": os.environ.get("OPENROUTER_ENABLED"),
            "EXEC_EMAIL_ADDRESS": os.environ.get("EXEC_EMAIL_ADDRESS"),
        }
        os.environ["OPENROUTER_ENABLED"] = "true"
        os.environ.setdefault("EXEC_EMAIL_ADDRESS", "redops-smoke@example.invalid")
        fork_registry._reset_for_tests()

    def tearDown(self) -> None:
        for name, value in self._saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        fork_registry._reset_for_tests()

    def test_one_live_call_reaches_openrouter_and_logs_attribution(self) -> None:
        request = ModelRequest(
            tenant_id="3fmindset",
            model=SMOKE_MODEL,
            prompt="Reply with the single word: pong",
            prompt_version="smoke-v1",
            trace_id="live-smoke-1",
            context_references=("smoke-source",),
        )
        gateway = LoggingModelGateway(
            ForkProviderModelGateway.from_fork_registry(max_tokens=16)
        )

        with self.assertLogs("redops.agents.model", level="INFO") as captured:
            response = gateway.generate(request)

        self.assertTrue(
            response.text.strip(), "the live provider returned no text"
        )
        self.assertEqual(response.model, SMOKE_MODEL)
        self.assertEqual(response.prompt_version, "smoke-v1")
        self.assertEqual(response.trace_id, "live-smoke-1")
        self.assertEqual(response.context_references, ("smoke-source",))
        self.assertGreaterEqual(response.usage.input_tokens, 0)
        self.assertGreaterEqual(response.usage.output_tokens, 0)

        record = captured.records[0]
        self.assertEqual(record.redops_trace_id, "live-smoke-1")
        self.assertEqual(record.redops_model, SMOKE_MODEL)
        self.assertEqual(record.redops_tenant, "3fmindset")
        for value in record.__dict__.values():
            self.assertNotIn("pong", repr(value))


if __name__ == "__main__":
    unittest.main()

"""Deterministic fake model gateway (queue Q1; SPEC.md section 13 condition 5).

The end-to-end path needs a model that answers the same way every time, offline,
so agent behavior is reproducible and no test depends on a live provider. This
adapter satisfies the ``ModelGateway`` port deterministically: a caller may
configure exact prompt-to-text responses, otherwise it returns a stable,
prompt-derived completion. It records the attribution every call carries
(model, prompt version, usage, trace id, context references) for logging
(SPEC.md section 6) and holds no credentials, so nothing secret can appear in a
request or response. The live OpenRouter adapter is a separate Q2 concern; this
adapter is never selected for production traffic.
"""

from __future__ import annotations

from collections.abc import Mapping

from redops.agents.application.ports import ModelGateway
from redops.agents.domain.value_objects import (
    ModelRequest,
    ModelResponse,
    ModelUsage,
)


class DeterministicFakeModelGateway(ModelGateway):
    """A model gateway with no network and no nondeterminism."""

    def __init__(self, responses: Mapping[str, str] | None = None) -> None:
        self._responses = dict(responses or {})
        self._calls: list[ModelResponse] = []

    @property
    def calls(self) -> tuple[ModelResponse, ...]:
        """The responses returned so far, in call order, for assertions/logging."""
        return tuple(self._calls)

    def generate(self, request: ModelRequest) -> ModelResponse:
        text = self._responses.get(request.prompt)
        if text is None:
            text = f"[{request.prompt_version}] {request.prompt}"
        response = ModelResponse(
            text=text,
            model=request.model,
            prompt_version=request.prompt_version,
            usage=ModelUsage(
                input_tokens=len(request.prompt.split()),
                output_tokens=len(text.split()),
            ),
            trace_id=request.trace_id,
            context_references=request.context_references,
        )
        self._calls.append(response)
        return response

"""Application ports for the RED agent model seam (SPEC.md sections 5 and 6).

A port is defined by an application need: agent use cases must call a model
without knowing whether the backend is the deterministic fake (offline tests
and the end-to-end path) or the live OpenRouter adapter (SPEC.md section 13
condition 5). The adapter is chosen in the composition layer, so the use case
depends on this interface, not a concrete provider.
"""

from __future__ import annotations

import abc

from redops.agents.domain.value_objects import ModelRequest, ModelResponse


class ModelGateway(abc.ABC):
    """Seam for model completions, keyed by the typed request.

    ``generate`` returns a completion attributed to the request's model, prompt
    version, context references and trace id so the caller can log them
    (SPEC.md section 6). Implementations must stay within the request's tenant
    material (SPEC.md section 9) and must not place credentials in a request or
    response.
    """

    @abc.abstractmethod
    def generate(self, request: ModelRequest) -> ModelResponse:
        """Return a completion for the request."""

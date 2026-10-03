"""Value objects for the RED agent model seam (SPEC.md sections 5 and 6).

The reference model is reached only through these typed values. A
``ModelRequest`` names the tenant whose material is in scope (SPEC.md section
9: retrieval is limited to the active client), the model and prompt version
(SPEC.md section 6: the adapter logs model and prompt version), the context
references the answer is grounded on, and the trace id that ties the call to
its workflow run. A ``ModelResponse`` returns the text plus the same model,
prompt version, trace id and context references, and a non-negative token
``ModelUsage``. Secrets are not part of any value: credentials live in the
adapter's configuration, never in a request or response (SPEC.md section 6,
"without storing secrets").
"""

from __future__ import annotations

from dataclasses import dataclass

from redops.agents.domain.errors import (
    InvalidModelRequestError,
    InvalidModelResponseError,
    InvalidModelUsageError,
)


def _require_text(label: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidModelRequestError(f"{label} is required")
    return value


@dataclass(frozen=True)
class ModelRequest:
    """A single model call: who, which model, which version, and why."""

    tenant_id: str
    model: str
    prompt: str
    prompt_version: str
    trace_id: str
    context_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text("the model request tenant id", self.tenant_id)
        _require_text("the model request model", self.model)
        _require_text("the model request prompt", self.prompt)
        _require_text("the model request prompt version", self.prompt_version)
        _require_text("the model request trace id", self.trace_id)
        seen: set[str] = set()
        for reference in self.context_references:
            _require_text(
                "a model request context reference", reference
            )
            if reference in seen:
                raise InvalidModelRequestError(
                    f"model request context reference {reference!r} is duplicated"
                )
            seen.add(reference)


@dataclass(frozen=True)
class ModelUsage:
    """Non-negative prompt and completion token counts (SPEC.md section 6)."""

    input_tokens: int
    output_tokens: int

    def __post_init__(self) -> None:
        for label, value in (
            ("input", self.input_tokens),
            ("output", self.output_tokens),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise InvalidModelUsageError(
                    f"the model {label} token count must be a non-negative "
                    "integer"
                )


@dataclass(frozen=True)
class ModelResponse:
    """A model completion with the attribution the seam must preserve."""

    text: str
    model: str
    prompt_version: str
    usage: ModelUsage
    trace_id: str
    context_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip():
            raise InvalidModelResponseError("the model response text is required")
        for label, value in (
            ("model", self.model),
            ("prompt version", self.prompt_version),
            ("trace id", self.trace_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise InvalidModelResponseError(
                    f"the model response {label} is required"
                )
        if not isinstance(self.usage, ModelUsage):
            raise InvalidModelResponseError(
                "the model response usage must be a ModelUsage"
            )
